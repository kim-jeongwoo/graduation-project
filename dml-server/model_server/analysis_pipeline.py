"""
analysis_pipeline.py — Single-wav acoustic analysis pipeline (L-1)
====================================================================
Stateless analysis function. All heavy state (model, mappings) is
passed in via AnalysisPipeline class to support server-side caching.

Usage:
    pipeline = AnalysisPipeline(checkpoint_path, criteria_path, mappings_path)
    result = pipeline.analyze(audio_bytes_or_path)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from functools import lru_cache
from typing import Dict, Optional, Tuple

import librosa
import numpy as np
import parselmouth
import soundfile as sf
import torch
from parselmouth.praat import call

# ── paths ──────────────────────────────────────────────────────────
_SERVER_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SERVER_DIR)
_AI_MODEL_DIR = os.path.join(_PROJECT_ROOT, "ai-model")
if _AI_MODEL_DIR not in sys.path:
    sys.path.insert(0, _AI_MODEL_DIR)

from model.efficient_egg import build_efficient_model   # noqa: E402

# score_mapper_v2 통합 (D3-2). _PROJECT_ROOT = dml-server/
_SIDETRACK_DIR = os.path.join(_PROJECT_ROOT, "scripts", "sidetrack")
_SIDETRACK_DIR = os.path.abspath(_SIDETRACK_DIR)
if os.path.exists(_SIDETRACK_DIR) and _SIDETRACK_DIR not in sys.path:
    sys.path.insert(0, _SIDETRACK_DIR)
try:
    from score_mapper_v2 import ScoreMapperV2  # noqa: E402
    SCORE_MAPPER_V2_AVAILABLE = True
except Exception as _e:
    SCORE_MAPPER_V2_AVAILABLE = False
    _v2_import_err = str(_e)

# ── constants ──────────────────────────────────────────────────────
TARGET_SR    = 16000
N_FFT        = 1024
HOP          = 256
F0_FLOOR     = 75
F0_CEIL      = 600
WINDOW_SIZE  = 16384
HOP_SIZE     = 8192
MIN_VOICED_S = 5.0      # minimum voiced seconds; shorter → SilentInputError → 200 no_voice

EXP20_CONFIG = {
    "channels": 128, "n_layers": 30, "kernel_size": 5,
    "n_stacks": 5, "dropout": 0.05,
}

# Reliability classification (from Phase I/J validation results)
HIGH_RELIABILITY   = ["3_vocal_fold_contact", "4_breathiness"]
MEDIUM_RELIABILITY = [
    "1_nasal_oral_ratio", "2_chest_head_voice",
    "5_forward_resonance", "6_soft_palate", "9_pressure_balance",
]
UNAVAILABLE = ["7_larynx_tongue_root", "8_tongue_tension"]

# CSV column → criteria key
CSV_TO_CRITERIA = {
    "비강사용":  "1_nasal_oral_ratio",
    "흉성두성":  "2_chest_head_voice",
    "접촉강도":  "3_vocal_fold_contact",
    "호흡식별":  "4_breathiness",
    "전방공명":  "5_forward_resonance",
    "연구개위치": "6_soft_palate",
    "공명개방":  "7_larynx_tongue_root",
    "혀경직도":  "8_tongue_tension",
    "상압하압":  "9_pressure_balance",
}
CRITERIA_KEYS = list(CSV_TO_CRITERIA.values())


# ── exceptions ─────────────────────────────────────────────────────

class SilentInputError(Exception):
    """Raised when audio has no usable vocal content (guard A or B)."""
    def __init__(self, reason: str, guard: str, audio_info: dict,
                 elapsed_ms: float = 0.0, cpp_mean: Optional[float] = None):
        super().__init__(reason)
        self.reason = reason
        self.guard = guard          # "A" (no voiced frames) | "B" (periodic noise)
        self.audio_info = audio_info
        self.elapsed_ms = elapsed_ms
        self.cpp_mean = cpp_mean


# ── helpers ────────────────────────────────────────────────────────

def _load_audio_bytes(data: bytes) -> Tuple[np.ndarray, float]:
    """Load audio from bytes, resample to 16 kHz, z-score normalize."""
    buf = io.BytesIO(data)
    audio, sr = sf.read(buf, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sr
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    std = audio.std()
    if std > 1e-8:
        audio = (audio - audio.mean()) / std
    return audio, duration


def _generate_vad(audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    2-stage VAD: RMS energy + parselmouth F0.
    Returns: (vad_mask [n_frames], f0_vals [n_f0], f0_times [n_f0])
    """
    frame_len = HOP * 2
    n_frames = max(0, (len(audio) - frame_len) // HOP + 1)
    rms = np.array([
        np.sqrt(np.mean(audio[i*HOP:i*HOP+frame_len]**2))
        for i in range(n_frames)
    ], dtype=np.float32)
    p90 = np.percentile(rms, 90)
    rms_mask = rms >= p90 * 0.10

    # Parselmouth operates on float32 array
    snd = parselmouth.Sound(audio, sampling_frequency=TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_f0 = call(pitch, "Get number of frames")
    f0_vals = np.zeros(n_f0); f0_times = np.zeros(n_f0)
    for i in range(1, n_f0 + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals[i-1] = f if f == f else 0.0
        f0_times[i-1] = t

    frame_times = np.array([(i*HOP + frame_len/2) / TARGET_SR for i in range(n_frames)])
    f0_mask = np.zeros(n_frames, dtype=bool)
    for i, t in enumerate(frame_times):
        idx = np.argmin(np.abs(f0_times - t))
        f0_mask[i] = f0_vals[idx] > 0

    return rms_mask & f0_mask, f0_vals, f0_times


def _split_registers(f0_vals: np.ndarray) -> dict:
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 200.0, "mid_max": 300.0, "f0_min": None, "f0_max": None, "f0_mean": None}
    return {
        "low_max": float(np.percentile(voiced, 33)),
        "mid_max": float(np.percentile(voiced, 66)),
        "f0_min": float(voiced.min()),
        "f0_max": float(voiced.max()),
        "f0_mean": float(voiced.mean()),
    }


def _predict_egg(model, audio: np.ndarray, device) -> np.ndarray:
    """Windowed EGG inference with overlap-add."""
    total = len(audio)
    if total < WINDOW_SIZE:
        pad = np.zeros(WINDOW_SIZE, dtype=np.float32)
        pad[:total] = audio
        x = torch.from_numpy(pad).float().unsqueeze(0).unsqueeze(0).to(device)
        with torch.no_grad():
            return model(x).squeeze().cpu().numpy()[:total]
    out = np.zeros(total, dtype=np.float32)
    cnt = np.zeros(total, dtype=np.float32)
    starts = list(range(0, total - WINDOW_SIZE + 1, HOP_SIZE))
    if starts and starts[-1] + WINDOW_SIZE < total:
        starts.append(total - WINDOW_SIZE)
    with torch.no_grad():
        for s in starts:
            x = torch.from_numpy(audio[s:s+WINDOW_SIZE]).float().unsqueeze(0).unsqueeze(0).to(device)
            pred = model(x).squeeze().cpu().numpy()
            out[s:s+WINDOW_SIZE] += pred
            cnt[s:s+WINDOW_SIZE] += 1.0
    return out / np.maximum(cnt, 1e-8)


def _cq_frame(egg: np.ndarray, i: int) -> float:
    frame_len = HOP * 2
    s = i * HOP
    frame = egg[s:s+frame_len] if s+frame_len <= len(egg) else egg[s:]
    if len(frame) == 0: return np.nan
    return float((frame > 0).sum() / len(frame))


def _cpp_frame(audio: np.ndarray, i: int) -> float:
    s = i * HOP
    raw = audio[s:s+N_FFT]
    if len(raw) < N_FFT:
        padded = np.zeros(N_FFT, dtype=np.float32)
        padded[:len(raw)] = raw
        raw = padded
    frame = raw * np.hanning(N_FFT)
    if np.abs(frame).max() < 1e-8: return np.nan
    spec = np.abs(np.fft.rfft(frame))
    log_spec = np.log(spec + 1e-10)
    cepstrum = np.fft.irfft(log_spec)
    q_min = int(TARGET_SR / F0_CEIL); q_max = min(int(TARGET_SR / F0_FLOOR), len(cepstrum)//2)
    if q_min >= q_max: return np.nan
    seg = cepstrum[q_min:q_max]
    pk_idx = np.argmax(seg)
    x = np.arange(len(seg), dtype=float)
    coeff = np.polyfit(x, seg, 1) if len(x) > 2 else [0, seg.mean()]
    return float(seg[pk_idx] - np.polyval(coeff, x[pk_idx]))


def _spectral_tilt(S_mag: np.ndarray, frame_idx: int) -> float:
    freqs = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
    col = S_mag[:, frame_idx]
    log_mag = np.log10(col + 1e-10)
    valid = freqs > 0
    coeff = np.polyfit(np.log10(freqs[valid]), log_mag[valid], 1) if valid.sum() > 2 else [0, 0]
    return float(coeff[0])


def _h1_h2(audio: np.ndarray, i: int, f0: float) -> float:
    s = i * HOP
    raw = audio[s:s+N_FFT]
    if len(raw) < N_FFT:
        padded = np.zeros(N_FFT, dtype=np.float32); padded[:len(raw)] = raw; raw = padded
    frame = raw * np.hanning(N_FFT)
    spec_db = 20 * np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
    freqs = np.fft.rfftfreq(N_FFT, 1.0/TARGET_SR)
    sr_bin = TARGET_SR / N_FFT
    h1i = int(f0/sr_bin); h1r = max(1, int(100/sr_bin))
    h2i = int(2*f0/sr_bin)
    h1 = spec_db[max(0, h1i-h1r):h1i+h1r+1]
    h2 = spec_db[max(0, h2i-h1r):h2i+h1r+1]
    return float(h1.max() - h2.max()) if len(h1) > 0 and len(h2) > 0 else np.nan


def _extract_user_f0(snd: parselmouth.Sound, frame_hz: int = 25) -> dict:
    """25Hz sparse null 포맷 F0 추출. voiced→freq_hz(float), unvoiced→None."""
    pitch = snd.to_pitch(time_step=1.0 / frame_hz, pitch_floor=50, pitch_ceiling=600)
    freq_array = pitch.selected_array['frequency']  # 0.0 = unvoiced
    values = [float(f) if f > 0 else None for f in freq_array]
    return {"frame_hz": frame_hz, "values": values}


def _aggregate(vals):
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) == 0: return None, None
    return float(arr.mean()), float(np.percentile(arr, 90))


def _safe_mean(vals):
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    return float(arr.mean()) if len(arr) > 0 else None


def _reg_for_frame(f0: float, boundaries: dict) -> Optional[str]:
    if f0 <= 0: return None
    if f0 <= boundaries["low_max"]: return "low"
    if f0 <= boundaries["mid_max"]: return "mid"
    return "high"


def _apply_mapping(ai_val: float, mapping: dict) -> Optional[float]:
    """Apply learned threshold mapping to get 0~5 score."""
    thresh = mapping.get("thresholds", {})
    if not thresh: return None
    vals = [float(thresh[str(i)]) for i in range(6)]
    scores = list(range(6))
    increasing = vals[-1] > vals[0]
    if increasing:
        if ai_val <= vals[0]: return 0.0
        if ai_val >= vals[-1]: return 5.0
        for i in range(5):
            if vals[i] <= ai_val <= vals[i+1]:
                frac = (ai_val - vals[i]) / (vals[i+1] - vals[i] + 1e-10)
                return float(i) + frac
    else:
        if ai_val >= vals[0]: return 0.0
        if ai_val <= vals[-1]: return 5.0
        for i in range(5):
            if vals[i] >= ai_val >= vals[i+1]:
                frac = (vals[i] - ai_val) / (vals[i] - vals[i+1] + 1e-10)
                return float(i) + frac
    diffs = [abs(ai_val - v) for v in vals]
    return float(np.argmin(diffs))


def _score_to_zone(score: Optional[float]) -> Optional[str]:
    if score is None: return None
    s = round(score)
    if s <= 1: return "insufficient"
    if s <= 3: return "appropriate"
    return "excessive"


# ── Main pipeline class ────────────────────────────────────────────

class AnalysisPipeline:
    """
    Holds all heavy state (EGG model, criteria, mappings).
    Instantiate once at server startup, call analyze() per request.
    """

    def __init__(self, checkpoint_path: str, criteria_path: str, mappings_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # EGG model
        self.model = build_efficient_model(EXP20_CONFIG)
        ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device).eval()
        self._val_corr = ckpt.get("val_corr")

        # Criteria (evaluation rubric v3)
        with open(criteria_path, encoding="utf-8") as f:
            self.criteria = json.load(f)

        # Learned score mappings
        with open(mappings_path, encoding="utf-8") as f:
            ai_scores_data = json.load(f)
        self.mappings: dict = ai_scores_data.get("mappings", {})

        # csv_col → criteria_key → mapping
        self._col_mapping: dict = {}
        for csv_col, crit_key in CSV_TO_CRITERIA.items():
            self._col_mapping[crit_key] = self.mappings.get(csv_col)

        # ai_source per criteria_key
        self._ai_source: dict = {
            crit_key: self.criteria.get("items", {}).get(crit_key, {}).get("ai_source")
            for crit_key in CRITERIA_KEYS
        }

        # score_mapper_v2 인스턴스 (D3-2: 4 표시 + 2 academic 항목)
        self.v2 = None
        if SCORE_MAPPER_V2_AVAILABLE:
            try:
                self.v2 = ScoreMapperV2()
                print(f"  ScoreMapperV2 loaded: {len(self.v2.params['models'])} models")
            except Exception as e:
                print(f"  ScoreMapperV2 load failed: {e}")

        print(
            f"[AnalysisPipeline] Ready: device={self.device}, val_corr={self._val_corr}, "
            f"params={sum(p.numel() for p in self.model.parameters()):,}"
        )

    def analyze(self, audio_data: bytes, min_voiced_s: float = MIN_VOICED_S) -> dict:
        """
        Full analysis pipeline. Returns structured result dict.

        Raises:
            ValueError: audio too short (voiced < MIN_VOICED_S)
        """
        t0 = time.perf_counter()

        # 1) Load + preprocess
        audio, duration = _load_audio_bytes(audio_data)

        # 2) VAD
        vad_mask, f0_vals, f0_times = _generate_vad(audio)
        n_frames = len(vad_mask)
        voiced_frames = int(vad_mask.sum())
        voiced_s = voiced_frames * HOP / TARGET_SR
        voiced_ratio = voiced_frames / n_frames if n_frames > 0 else 0.0

        _audio_info_base = {
            "duration_s": round(duration, 2),
            "sample_rate": TARGET_SR,
            "voiced_ratio": round(voiced_ratio, 4),
            "voiced_duration_s": round(voiced_s, 2),
            "f0_min": None, "f0_max": None, "f0_mean": None,
        }

        # Guard A: no voiced frames
        if voiced_s < min_voiced_s:
            raise SilentInputError(
                reason="음성이 감지되지 않았습니다. 마이크 입력을 확인하고 다시 녹음해주세요.",
                guard="A",
                audio_info=_audio_info_base,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
            )

        # Guard B: nearly all frames "voiced" but CPP too low → periodic noise / hum
        if voiced_ratio > 0.95:
            cpp_pre = [_cpp_frame(audio, i) for i in range(n_frames) if vad_mask[i]]
            cpp_pre = [v for v in cpp_pre if not np.isnan(v)]
            cpp_pre_mean = float(np.mean(cpp_pre)) if cpp_pre else 0.0
            if cpp_pre_mean < 0.15:
                raise SilentInputError(
                    reason="잡음만 녹음되었습니다. 마이크는 동작하지만 사람 목소리가 감지되지 않았습니다. 다시 녹음해주세요.",
                    guard="B",
                    audio_info=_audio_info_base,
                    elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
                    cpp_mean=cpp_pre_mean,
                )

        # 3) Register boundaries
        boundaries = _split_registers(f0_vals)

        # 4) EGG inference
        egg_pred = _predict_egg(self.model, audio, self.device)

        # 5) STFT for spectral features
        S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP)
        S_mag = np.abs(S)
        freqs = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
        centroid_arr = librosa.feature.spectral_centroid(S=S_mag, sr=TARGET_SR, n_fft=N_FFT)[0]
        mask_2k4k = (freqs >= 2000) & (freqs <= 4000)

        # Frame-level metrics
        frame_times = np.array([(i*HOP + HOP) / TARGET_SR for i in range(n_frames)])
        stft_n = S_mag.shape[1]

        # Per-register accumulators
        reg_data: dict = {r: {k: [] for k in [
            "cq_mean","cq_peak","cpp","hnr","spectral_centroid",
            "spectral_tilt","h1_h2","singers_formant_ratio","a1_p0"
        ]} for r in ["low","mid","high"]}

        # User F0 (25Hz sparse null) — snd_raw 생성 직후 추출
        snd_raw = parselmouth.Sound(audio, sampling_frequency=TARGET_SR)
        user_f0 = _extract_user_f0(snd_raw)

        # HNR via parselmouth (compute globally)
        try:
            harm = call(snd_raw, "To Harmonicity (cc)", 0.01, F0_FLOOR, 0.1, 1.0)
            n_h = call(harm, "Get number of frames")
            hnr_vals_arr = np.array([
                call(harm, "Get value in frame", i)
                for i in range(1, n_h + 1)
            ])
            hnr_times_arr = np.array([
                call(harm, "Get time from frame number", i)
                for i in range(1, n_h + 1)
            ])
            hnr_vals_arr = np.where(np.isnan(hnr_vals_arr), np.nan, hnr_vals_arr)
        except Exception:
            hnr_vals_arr = np.array([]); hnr_times_arr = np.array([])

        # A1-P0 (single global value, replicated per voiced frame)
        try:
            formant = call(snd_raw, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
            n_f = call(formant, "Get number of frames")
            a1p0_list = []
            window_h = np.hanning(N_FFT)
            fqs_rfft = np.fft.rfftfreq(N_FFT, 1.0/TARGET_SR)
            sr_bin = TARGET_SR / N_FFT
            for ii in range(1, n_f + 1):
                t = call(formant, "Get time from frame number", ii)
                f1 = call(formant, "Get value at time", 1, t, "Hertz", "Linear")
                if not (f1 == f1) or f1 <= 0: continue
                fi = int(t * TARGET_SR) - N_FFT//2
                if fi < 0 or fi + N_FFT > len(audio): continue
                frame = audio[fi:fi+N_FFT] * window_h
                spec_db = 20*np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
                f1_idx = int(f1/sr_bin); f1r = max(1, int(100/sr_bin))
                p0_idx = int(250/sr_bin); p0r = max(1, int(50/sr_bin))
                a1 = spec_db[max(0,f1_idx-f1r):f1_idx+f1r+1].max()
                p0 = spec_db[max(0,p0_idx-p0r):p0_idx+p0r+1].max()
                a1p0_list.append(a1 - p0)
            a1_p0_global = float(np.mean(a1p0_list)) if a1p0_list else None
        except Exception:
            a1_p0_global = None

        # Per-frame loop
        for i, t in enumerate(frame_times):
            if i >= len(vad_mask) or not vad_mask[i]: continue
            fi_f0 = np.argmin(np.abs(f0_times - t))
            f0 = f0_vals[fi_f0]
            reg = _reg_for_frame(f0, boundaries)
            if reg is None: continue

            cq = _cq_frame(egg_pred, i)
            cpp_v = _cpp_frame(audio, i)

            si = min(int(t * TARGET_SR / HOP), stft_n - 1)
            tilt = _spectral_tilt(S_mag, si)
            hh = _h1_h2(audio, i, f0) if f0 > 0 else np.nan
            sc = float(centroid_arr[si])

            # HNR
            if len(hnr_times_arr) > 0:
                hi = np.argmin(np.abs(hnr_times_arr - t))
                hnr_v = hnr_vals_arr[hi] if not np.isnan(hnr_vals_arr[hi]) else np.nan
            else:
                hnr_v = np.nan

            # Singer's formant
            total_e = (S_mag[:, si]**2).sum()
            sf_e = (S_mag[mask_2k4k, si]**2).sum()
            sfr = float(sf_e / (total_e + 1e-10))

            reg_data[reg]["cq_mean"].append(cq)
            reg_data[reg]["cq_peak"].append(cq)
            reg_data[reg]["cpp"].append(cpp_v)
            reg_data[reg]["spectral_centroid"].append(sc)
            reg_data[reg]["spectral_tilt"].append(tilt)
            reg_data[reg]["h1_h2"].append(hh)
            reg_data[reg]["singers_formant_ratio"].append(sfr)
            if not np.isnan(hnr_v): reg_data[reg]["hnr"].append(hnr_v)
            if a1_p0_global is not None: reg_data[reg]["a1_p0"].append(a1_p0_global)

        # Aggregate per register
        def reg_stats(reg: str) -> dict:
            d = reg_data[reg]
            cq_m, cq_p = _aggregate(d["cq_mean"])
            cpp_m, _ = _aggregate(d["cpp"])
            hnr_m, _ = _aggregate(d["hnr"])
            sc_m, _ = _aggregate(d["spectral_centroid"])
            tilt_m, _ = _aggregate(d["spectral_tilt"])
            h1h2_m, _ = _aggregate(d["h1_h2"])
            sfr_m, _ = _aggregate(d["singers_formant_ratio"])
            a1p0_m, _ = _aggregate(d["a1_p0"])
            return {
                "n_frames": len(d["cq_mean"]),
                "cq_mean": cq_m, "cq_peak": cq_p, "cpp": cpp_m, "hnr": hnr_m,
                "spectral_centroid": sc_m, "spectral_tilt": tilt_m,
                "h1_h2": h1h2_m, "singers_formant_ratio": sfr_m, "a1_p0": a1p0_m,
            }

        registers = {r: reg_stats(r) for r in ["low","mid","high"]}

        # Global indicators (all voiced)
        all_cq = sum((reg_data[r]["cq_mean"] for r in ["low","mid","high"]), [])
        global_cq_m, global_cq_p = _aggregate(all_cq)
        all_cpp = sum((reg_data[r]["cpp"] for r in ["low","mid","high"]), [])
        all_hnr = sum((reg_data[r]["hnr"] for r in ["low","mid","high"]), [])
        all_sc  = sum((reg_data[r]["spectral_centroid"] for r in ["low","mid","high"]), [])
        all_tilt = sum((reg_data[r]["spectral_tilt"] for r in ["low","mid","high"]), [])
        all_h1h2 = sum((reg_data[r]["h1_h2"] for r in ["low","mid","high"]), [])
        all_sfr  = sum((reg_data[r]["singers_formant_ratio"] for r in ["low","mid","high"]), [])

        indicators = {
            "cq_mean": global_cq_m, "cq_peak": global_cq_p,
            "cpp_mean": _safe_mean(all_cpp), "hnr_mean": _safe_mean(all_hnr),
            "spectral_centroid_mean": _safe_mean(all_sc),
            "spectral_tilt_mean": _safe_mean(all_tilt),
            "h1_h2_mean": _safe_mean(all_h1h2),
            "singers_formant_ratio_mean": _safe_mean(all_sfr),
            "a1_p0_mean": a1_p0_global,
            "nasal_ratio": None,  # unavailable without nasal mic
        }

        # 8) Score mapping: use "all" register metrics for integration
        # Map each csv_col → ai indicator value
        def _get_indicator_val(csv_col: str) -> Optional[float]:
            if csv_col == "비강사용":   return None
            if csv_col == "흉성두성":   return global_cq_m
            if csv_col == "접촉강도":   return global_cq_p
            if csv_col == "호흡식별":   return indicators["cpp_mean"]
            if csv_col == "전방공명":   return indicators["spectral_centroid_mean"]
            if csv_col == "연구개위치":  return None
            if csv_col == "공명개방":   return None
            if csv_col == "혀경직도":   return None
            if csv_col == "상압하압":   return indicators["spectral_tilt_mean"]
            return None

        scores: dict = {}
        feedback: dict = {}

        for csv_col, crit_key in CSV_TO_CRITERIA.items():
            ai_val = _get_indicator_val(csv_col)
            mapping = self.mappings.get(csv_col)
            ci = self.criteria.get("items", {}).get(crit_key, {})
            ai_src = ci.get("ai_source")

            # Score
            if ai_val is not None and mapping and mapping.get("method") != "skip":
                ai_score = _apply_mapping(ai_val, mapping)
                rounded = min(5, max(0, round(ai_score))) if ai_score is not None else None
            else:
                ai_score = None
                rounded = None

            zone = _score_to_zone(ai_score)
            conf = (
                "high" if crit_key in HIGH_RELIABILITY else
                "medium" if crit_key in MEDIUM_RELIABILITY else
                "unavailable"
            )
            scores[crit_key] = {
                "ai_score": round(ai_score, 2) if ai_score is not None else None,
                "rounded_score": rounded,
                "zone": zone,
                "confidence": conf,
            }

            # Feedback
            score_desc = ci.get("scores", {}).get(str(rounded), {}).get("description", "") if rounded is not None else ""
            fb_text = ci.get("feedback_rules", {}).get(zone, "") if zone else "AI 측정 불가"
            zone_label = {"insufficient":"미달","appropriate":"적절","excessive":"과함"}.get(zone or "", "")
            feedback[crit_key] = {
                "name_ko": ci.get("name_ko", csv_col),
                "ai_score": round(ai_score, 2) if ai_score is not None else None,
                "score_description": score_desc,
                "feedback_text": fb_text,
                "zone": zone,
                "zone_label": zone_label,
                "ai_indicator": {
                    "name": ai_src,
                    "value": round(ai_val, 4) if ai_val is not None else None,
                },
            }

        # ── score_mapper_v2 적용 (D3-2): 4 표시 항목 + 2 academic ──
        v2_scores: dict = {}
        v2_meta: dict = {}
        v2_academic: dict = {}
        v2_version = None
        if self.v2 is not None:
            try:
                KOR_TO_KEY = {
                    "비강사용":"1_nasal_oral_ratio", "흉성두성":"2_chest_head_voice",
                    "접촉강도":"3_vocal_fold_contact","호흡식별":"4_breathiness",
                    "전방공명":"5_forward_resonance","연구개위치":"6_soft_palate",
                    "공명개방":"7_larynx_tongue_root","혀경직도":"8_tongue_tension",
                    "상압하압":"9_pressure_balance",
                }
                # v2 indicator 산출에는 raw audio 사용 (z-score 정규화 전).
                # indicators_v2 의 amplitude 기반 함수(HNR/shimmer/h1_*) 가
                # mean/std 정규화 영향을 받음.
                import soundfile as _sf, io as _io
                _raw_audio, _raw_sr = _sf.read(_io.BytesIO(audio_data), dtype="float32")
                if _raw_audio.ndim > 1:
                    _raw_audio = _raw_audio.mean(axis=1)
                if _raw_sr != TARGET_SR:
                    _raw_audio = librosa.resample(_raw_audio, orig_sr=_raw_sr, target_sr=TARGET_SR)
                v2_raw = self.v2.score_from_audio(_raw_audio, TARGET_SR)
                for kor, item in v2_raw.items():
                    key = KOR_TO_KEY.get(kor, kor)
                    tier = item.get("tier")
                    if tier in ("high", "high_star"):
                        v2_scores[key] = item["ai_score"]
                        v2_meta[key] = {
                            "tier": tier,
                            "caveats": item.get("caveats", []),
                            "display_mark": "asterisk" if tier == "high_star" else None,
                            "tooltip": "외부 데이터에서 신뢰도 확보, 학습 내부 검증 약함 (모니터링 중)"
                                       if tier == "high_star" else None,
                            "rounded_score": item.get("rounded_score"),
                            "icc": item.get("icc"),
                            "icc_ratio": item.get("icc_ratio"),
                        }
                    elif tier == "academic_only":
                        v2_academic[key] = {
                            "ai_score": item["ai_score"],
                            "caveats": item.get("caveats", []),
                            "note": "sign_reversed 학술 분석 전용 (앱 표시 X)",
                        }
                v2_version = self.v2.params.get("version", "v2")
            except Exception as v2_err:
                # v2 실패해도 v1 응답은 유지
                v2_scores = {}; v2_meta = {}; v2_academic = {}

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "processing_time_ms": round(elapsed_ms, 1),
            "audio_info": {
                "duration_s": round(duration, 2),
                "sample_rate": TARGET_SR,
                "voiced_ratio": round(voiced_ratio, 4),
                "voiced_duration_s": round(voiced_s, 2),
                "f0_min": boundaries.get("f0_min"),
                "f0_max": boundaries.get("f0_max"),
                "f0_mean": boundaries.get("f0_mean"),
            },
            "register_boundaries": {
                "low_max": boundaries["low_max"],
                "mid_max": boundaries["mid_max"],
            },
            "registers": registers,
            "indicators": indicators,
            "scores": scores,                       # v1 9항목 (legacy 호환)
            "scores_v2": v2_scores,                 # D3-2: 4 표시 항목 (v2)
            "scores_meta": v2_meta,                 # D3-3: tier/caveats/display_mark
            "academic_analysis_scores": v2_academic,# D3-3: 학술 분석 2 항목
            "score_mapper_version": v2_version,     # D3-4: "v2"
            "feedback": feedback,
            "reliability": {
                "high_reliability":   HIGH_RELIABILITY,
                "medium_reliability": MEDIUM_RELIABILITY,
                "unavailable":        UNAVAILABLE,
                # v2 분류
                "shown_v2":           ["3_vocal_fold_contact","4_breathiness",
                                       "6_soft_palate","8_tongue_tension"],
                "shown_v2_tiers": {
                    "3_vocal_fold_contact": "high",
                    "4_breathiness":        "high_star",
                    "6_soft_palate":        "high_star",
                    "8_tongue_tension":     "high_star",
                },
                "academic_only_v2":   ["1_nasal_oral_ratio","5_forward_resonance"],
                "deferred_v2":        ["2_chest_head_voice","7_larynx_tongue_root",
                                       "9_pressure_balance"],
            },
            "user_f0": user_f0,
        }
