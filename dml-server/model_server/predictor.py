"""
EGG Predictor — Exp20 EfficientEGGNet 모델 로드 및 추론
========================================================
- 서버 시작 시 한 번만 로드하고 메모리에 유지
- WAV 파일 → 16kHz mono z-score 정규화 → 윈도우 분할 → 추론 → EGG WAV 저장
"""
import os
import sys
import time

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample as scipy_resample

# ai-model/model, ai-model/utils를 import할 수 있도록 경로 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AI_MODEL_DIR = os.path.join(_PROJECT_ROOT, "ai-model")
if _AI_MODEL_DIR not in sys.path:
    sys.path.insert(0, _AI_MODEL_DIR)

from model.efficient_egg import build_efficient_model  # noqa: E402

# Exp20 하이퍼파라미터 (checkpoint에 config 미포함이므로 명시)
EXP20_CONFIG = {
    "channels": 128,
    "n_layers": 30,
    "kernel_size": 5,
    "n_stacks": 5,
    "dropout": 0.05,
}

TARGET_SR = 16000
WINDOW_SIZE = 16384    # ~1.024초
HOP_SIZE = 8192        # 50% overlap


class EGGPredictor:
    """EGG 추정 모델 래퍼. 서버 수명 동안 한 인스턴스만 유지."""

    def __init__(self, checkpoint_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 모델 생성
        self.model = build_efficient_model(EXP20_CONFIG)

        # 가중치 로드
        ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device).eval()

        self.val_corr = ckpt.get("val_corr")
        self.phase = ckpt.get("phase")
        print(
            f"[EGGPredictor] Loaded checkpoint: {checkpoint_path}\n"
            f"  device={self.device}, val_corr={self.val_corr}, phase={self.phase}\n"
            f"  params={sum(p.numel() for p in self.model.parameters()):,}"
        )

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def predict(self, audio_path: str, output_path: str) -> dict:
        """
        WAV 파일을 받아 EGG를 추정하고 결과를 저장한다.

        Returns
        -------
        dict with keys:
            egg_signal_uri, duration_ms, sample_rate, processing_time_ms
        """
        t0 = time.perf_counter()

        # 1) 오디오 로드
        audio, sr = sf.read(audio_path, dtype="float32")

        # 2) 스테레오 → 모노
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # 3) 리샘플링 → 16 kHz
        if sr != TARGET_SR:
            n_samples = int(len(audio) * TARGET_SR / sr)
            audio = scipy_resample(audio, n_samples).astype(np.float32)
            sr = TARGET_SR

        duration_ms = len(audio) / sr * 1000

        # 4) z-score 정규화
        std = audio.std()
        if std > 1e-8:
            audio = (audio - audio.mean()) / std

        # 5) 윈도우 분할 + 추론
        egg_signal = self._windowed_inference(audio)

        # 6) 결과 저장
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sf.write(output_path, egg_signal, TARGET_SR)

        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "egg_signal_uri": output_path,
            "duration_ms": round(duration_ms, 1),
            "sample_rate": TARGET_SR,
            "processing_time_ms": round(elapsed, 1),
        }

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------
    @torch.no_grad()
    def _windowed_inference(self, audio: np.ndarray) -> np.ndarray:
        """16384-sample 윈도우로 분할 → 추론 → overlap-add로 이어붙이기."""
        total_len = len(audio)
        if total_len < WINDOW_SIZE:
            # 패딩
            padded = np.zeros(WINDOW_SIZE, dtype=np.float32)
            padded[:total_len] = audio
            pred = self._forward_window(padded)
            return pred[:total_len]

        # overlap-add 버퍼
        output = np.zeros(total_len, dtype=np.float32)
        weight = np.zeros(total_len, dtype=np.float32)

        starts = list(range(0, total_len - WINDOW_SIZE + 1, HOP_SIZE))
        # 마지막 윈도우가 끝까지 닿도록
        if starts[-1] + WINDOW_SIZE < total_len:
            starts.append(total_len - WINDOW_SIZE)

        for s in starts:
            window = audio[s : s + WINDOW_SIZE]
            pred = self._forward_window(window)
            output[s : s + WINDOW_SIZE] += pred
            weight[s : s + WINDOW_SIZE] += 1.0

        # 겹친 부분 평균
        weight = np.maximum(weight, 1e-8)
        return output / weight

    def _forward_window(self, window: np.ndarray) -> np.ndarray:
        """단일 윈도우 [16384] → GPU 추론 → numpy [16384]."""
        x = torch.from_numpy(window).float().unsqueeze(0).unsqueeze(0).to(self.device)
        y = self.model(x).squeeze().cpu().numpy()
        return y
