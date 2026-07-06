"""
chunk_analysis.py — Phase 4 단일 chunk 분석 전처리
==================================================
/analyze-chunk endpoint 전용 헬퍼.

처리 흐름:
  audio_bytes → load(16kHz mono float32) → optional slice(start/end) →
  duration 검증 → re-encode WAV → adaptive min_voiced_s 산출

duration < 3.0s   → ChunkTooShortError
duration ≥ 3.0s   → confidence="medium"
duration ≥ 5.0s   → confidence="high"
min_voiced_s      = duration × 0.4   (예: 5s→2.0s, 7s→2.8s, 10s→4.0s)
"""
from __future__ import annotations

import io
from typing import Optional

import librosa
import numpy as np
import soundfile as sf

TARGET_SR        = 16000
MIN_CHUNK_SEC    = 3.0   # 미만 시 ChunkTooShortError
HIGH_CONF_SEC    = 5.0   # 이상 시 confidence="high"
VOICED_FRACTION  = 0.4   # min_voiced_s = duration × 0.4


class ChunkTooShortError(Exception):
    """chunk duration < MIN_CHUNK_SEC."""
    def __init__(self, duration: float):
        super().__init__(f"chunk too short: {duration:.2f}s < {MIN_CHUNK_SEC}s")
        self.duration     = duration
        self.min_required = MIN_CHUNK_SEC


def prepare_chunk(
    audio_bytes: bytes,
    start_sec: Optional[float] = None,
    end_sec:   Optional[float] = None,
) -> tuple[bytes, float, float, str]:
    """
    Returns: (wav_bytes, duration_sec, min_voiced_s, confidence)
      wav_bytes      : 16kHz mono float WAV — pipeline.analyze 입력용
      duration_sec   : 최종 chunk 길이 (slice 후)
      min_voiced_s   : duration × 0.4
      confidence     : "high" | "medium"
    Raises: ChunkTooShortError 시 duration < 3.0s
    """
    audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR

    # optional slice
    if start_sec is not None or end_sec is not None:
        s = max(0,         int((start_sec or 0.0) * sr))
        e = min(len(audio), int((end_sec or len(audio) / sr) * sr))
        if e > s:
            audio = audio[s:e]

    duration = len(audio) / sr
    if duration < MIN_CHUNK_SEC:
        raise ChunkTooShortError(duration)

    min_voiced_s = duration * VOICED_FRACTION
    confidence   = "high" if duration >= HIGH_CONF_SEC else "medium"

    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    return buf.getvalue(), duration, min_voiced_s, confidence
