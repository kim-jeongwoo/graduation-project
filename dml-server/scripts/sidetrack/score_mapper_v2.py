"""
score_mapper_v2.py — phone wav → 6항목 점수 (4 표시 + 2 학술 분석)

표시 항목 (4):
  접촉강도 (tier=high), 호흡식별 (tier=high)
  연구개위치, 혀경직도 (tier=high_star, caveat=train_weak_external_only)

학술 분석 항목 (2, 앱 표시 X):
  비강사용, 전방공명 (tier=academic_only, caveat=sign_reversed)

배포 사용:
  from score_mapper_v2 import ScoreMapperV2
  sm = ScoreMapperV2()
  result = sm.score("/path/to/phone.wav")
  # → {"접촉강도": {"ai_score":2.7,"rounded_score":3,"tier":"high",...}, ...}

스크립트 실행:
  python score_mapper_v2.py <wav_path>
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import librosa

sys.path.insert(0, str(Path(__file__).parent))
import indicators_v2 as iv

ROOT        = Path("/home/dmlserver/projects/egg_prediction")
PARAMS_PATH = ROOT / "data/vocal_academy/results/sidetrack/mapping_params_v2.json"
MAPPER_PKL  = ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl"


class ScoreMapperV2:
    """phone wav → 6항목 점수 산출 (4 표시 + 2 학술)."""

    def __init__(self,
                 params_path: Optional[str] = None,
                 mapper_pkl: Optional[str]  = None):
        self.params = json.loads(Path(params_path or PARAMS_PATH).read_text())
        self.mapper = pickle.load(open(mapper_pkl or MAPPER_PKL, "rb"))
        self._tree_cache: dict = {}
        # mapper feature 순서 (33 phone indicator)
        self.mapper_features = self.mapper[next(iter(self.mapper))]["features"]

    # ── phone wav → 33 indicator ──
    def _compute_phone_indicators(self, wav_path: str) -> dict:
        audio, sr = sf.read(wav_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        return iv.compute_all(audio, sr)

    # ── audio np.ndarray 직접 입력 → 33 indicator (analysis_pipeline 통합용) ──
    def _compute_from_audio(self, audio: np.ndarray, sr: int = 16000) -> dict:
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        return iv.compute_all(audio.astype(np.float32), sr)

    # ── phone indicator → mapped oral indicator (27개) ──
    def _apply_mapper(self, phone_inds: dict) -> dict:
        x = np.array([phone_inds.get(f, 0.0) if phone_inds.get(f) is not None else 0.0
                      for f in self.mapper_features])
        mapped = {}
        for target, m in self.mapper.items():
            x_s = (x - np.array(m["scaler_mean"])) / np.array(m["scaler_scale"])
            pred = float(np.dot(np.array(m["ridge_coef"]), x_s) + m["ridge_intercept"])
            mapped[f"{target}__mapped"] = pred
        return mapped

    # ── feature vector (학습 feature 순서) ──
    def _build_feature_vector(self, phone_inds: dict, mapped: dict) -> np.ndarray:
        feat_order = self.params["feature_order"]
        feat_trans = self.params["feature_translation"]
        x = []
        for f in feat_order:
            if f in feat_trans:                       # score_mapper indicator → mapped
                v = mapped.get(feat_trans[f], 0.0)
            elif f + "__mapped" in mapped:
                v = mapped[f + "__mapped"]
            elif f in phone_inds and phone_inds[f] is not None:
                v = phone_inds[f]
            else:
                v = 0.0
            x.append(v)
        return np.array(x)

    # ── 6항목 점수 산출 (audio numpy) ──
    def score_from_audio(self, audio: np.ndarray, sr: int = 16000) -> dict:
        phone_inds = self._compute_from_audio(audio, sr)
        mapped     = self._apply_mapper(phone_inds)
        x_train    = self._build_feature_vector(phone_inds, mapped)
        return self._build_scores(x_train)

    # ── 6항목 점수 산출 (wav path) ──
    def score(self, wav_path: str) -> dict:
        phone_inds = self._compute_phone_indicators(wav_path)
        mapped     = self._apply_mapper(phone_inds)
        x_train    = self._build_feature_vector(phone_inds, mapped)
        return self._build_scores(x_train)

    def _build_scores(self, x_train: np.ndarray) -> dict:
        out = {}
        for item, info in self.params["models"].items():
            mean  = np.array(info["scaler_mean"])
            scale = np.array(info["scaler_scale"])
            x_s   = (x_train - mean) / scale

            if "coefficients" in info:           # linear
                coef = np.array(info["coefficients"])
                pred = float(np.dot(coef, x_s) + info["intercept"])
            else:                                # tree (lazy load)
                if item not in self._tree_cache:
                    self._tree_cache[item] = pickle.load(open(info["tree_model_pkl"], "rb"))
                tm = self._tree_cache[item]
                pred = float(tm["model"].predict(x_s.reshape(1, -1))[0])

            pred_clipped = max(0.0, min(5.0, pred))
            out[item] = {
                "ai_score":      round(pred_clipped, 2),
                "rounded_score": int(round(pred_clipped)),
                "raw_pred":      round(pred, 4),
                "tier":          info["tier"],
                "caveats":       info.get("caveats", []),
                "icc":           info["icc"],
                "icc_ratio":     info["icc_ratio"],
            }
        return out


def main():
    if len(sys.argv) < 2:
        print("usage: python score_mapper_v2.py <wav_path>")
        sys.exit(1)
    sm = ScoreMapperV2()
    result = sm.score(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
