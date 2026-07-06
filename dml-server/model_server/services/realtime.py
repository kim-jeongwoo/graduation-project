"""
realtime.py — WebSocket 기반 실시간 발성 분석
==============================================
연결: ws://host:8001/ws/realtime?song_id=004

클라이언트 → 서버:
  [선택] 첫 text frame : {"type":"meta","sample_rate":16000,"start_timestamp":0.0}
                          생략 시 기본값 사용 (16kHz, t=0)
  이후  binary frame   : int16 LE PCM, mono, 200ms
                          16kHz 기준 3200 samples = 6400 bytes

서버 → 클라이언트:
  {"type":"pitch_match","timestamp":T,"user_midi":M or null,
   "guide_midi":G or null,"diff_semitones":D or null,"match_score":S or null}
   — guide_midi/diff/match = null: unvoiced guide segment 또는 song_id 미지정

  {"type":"breathiness_chunk","start_sec":A,"end_sec":B,
   "ai_score":X or null,"zone":Z or null,"rounded_score":R or null}
   — 5초 누적마다 전송. voiced 부족 시 null.
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import os
from typing import Any, Optional

import numpy as np
import parselmouth
import soundfile as sf
from fastapi import WebSocket, WebSocketDisconnect

TARGET_SR          = 16000
PITCH_FLOOR        = 75
PITCH_CEIL         = 600
CHUNK_DUR_S        = 5.0   # 호흡 누적 시간 (사후 분석 timeline과 동일 기준)
CHUNK_MIN_VOICED_S = 2.0   # pipeline.analyze min_voiced_s (cf. timeline_analysis.py)


# ── 피치 유틸 ────────────────────────────────────────────────────────

def _freq_to_midi(freq_hz: float) -> float:
    return 69.0 + 12.0 * math.log2(freq_hz / 440.0)


def _extract_f0(arr: np.ndarray, sample_rate: int) -> Optional[float]:
    """float32 PCM → F0 중앙값(Hz). Unvoiced → None."""
    if len(arr) < 100:
        return None
    snd = parselmouth.Sound(arr, sampling_frequency=float(sample_rate))
    pitch = snd.to_pitch(time_step=0.04, pitch_floor=PITCH_FLOOR, pitch_ceiling=PITCH_CEIL)
    freqs = pitch.selected_array["frequency"]
    voiced = freqs[freqs > 0]
    return float(np.median(voiced)) if len(voiced) > 0 else None


def _match_score(diff_st: float) -> float:
    """반음 차이 → 일치율 0~1. ±1 반음 ≈ 0.83, ±6 반음 = 0."""
    return max(0.0, 1.0 - abs(diff_st) / 6.0)


# ── 피치 가이드 ──────────────────────────────────────────────────────

def _load_guide_points(song_id: str, pitch_guide_dir: str) -> Optional[list]:
    """pitch_guide/{song_id}.json → points 배열 (100Hz frames)."""
    p = os.path.join(pitch_guide_dir, f"{song_id}.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("points")  # [{time, midi, voiced, ...}, ...]


def _guide_midi_at(points: list, timestamp: float) -> Optional[float]:
    """nearest-neighbor lookup. voiced=false 또는 midi=None → None."""
    lo, hi = 0, len(points) - 1
    while lo < hi:
        mid_i = (lo + hi) // 2
        if points[mid_i]["time"] < timestamp:
            lo = mid_i + 1
        else:
            hi = mid_i
    best = lo
    if lo > 0 and abs(points[lo - 1]["time"] - timestamp) < abs(points[lo]["time"] - timestamp):
        best = lo - 1
    pt = points[best]
    if not pt.get("voiced") or pt.get("midi") is None:
        return None
    return float(pt["midi"])


# ── WAV 변환 ─────────────────────────────────────────────────────────

def _to_wav_bytes(arr: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, arr, sample_rate, format="WAV", subtype="FLOAT")
    return buf.getvalue()


# ── 핸들러 ───────────────────────────────────────────────────────────

async def realtime_handler(
    websocket: WebSocket,
    song_id: Optional[str],
    pipeline: Any,
    pitch_guide_dir: str,
) -> None:
    """
    WebSocket 연결 하나를 처리.
    pipeline : AnalysisPipeline 인스턴스 (server.py startup에서 로드)
    pipeline.analyze()는 run_in_executor로 실행 → event loop 블로킹 방지
    """
    await websocket.accept()

    guide_points: Optional[list] = _load_guide_points(song_id, pitch_guide_dir) if song_id else None

    sample_rate   = TARGET_SR
    start_ts      = 0.0
    frame_count   = 0
    buf_f32: list[float] = []
    buf_start_sec = 0.0
    loop = asyncio.get_running_loop()

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            # ── text frame: meta ─────────────────────────────────────
            if "text" in msg:
                meta = json.loads(msg["text"])
                if meta.get("type") == "meta":
                    sample_rate = int(meta.get("sample_rate", TARGET_SR))
                    start_ts    = float(meta.get("start_timestamp", 0.0))
                continue

            # ── binary frame: int16 LE PCM ───────────────────────────
            data = msg.get("bytes")
            if not data:
                continue

            n_samples   = len(data) // 2              # int16 → sample 수
            frame_dur_s = n_samples / sample_rate     # 실제 duration (초)
            timestamp   = start_ts + frame_count * frame_dur_s
            frame_count += 1

            pcm_f32 = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0

            # ── 1. 음정 일치율 (매 frame) ────────────────────────────
            user_freq  = _extract_f0(pcm_f32, sample_rate)
            user_midi  = _freq_to_midi(user_freq) if user_freq is not None else None
            guide_midi = _guide_midi_at(guide_points, timestamp) if guide_points else None
            diff_st    = (user_midi - guide_midi) if (user_midi is not None and guide_midi is not None) else None
            match_sc   = _match_score(diff_st) if diff_st is not None else None

            await websocket.send_text(json.dumps({
                "type":           "pitch_match",
                "timestamp":      round(timestamp, 3),
                "user_midi":      round(user_midi, 2)  if user_midi  is not None else None,
                "guide_midi":     round(guide_midi, 2) if guide_midi is not None else None,
                "diff_semitones": round(diff_st, 3)    if diff_st    is not None else None,
                "match_score":    round(match_sc, 3)   if match_sc   is not None else None,
            }))

            # ── 2. 5초 버퍼 누적 → 호흡 chunk 분석 ─────────────────
            if not buf_f32:
                buf_start_sec = timestamp
            buf_f32.extend(pcm_f32.tolist())

            if len(buf_f32) / sample_rate >= CHUNK_DUR_S:
                chunk_end_sec = timestamp + frame_dur_s
                wav_bytes     = _to_wav_bytes(np.array(buf_f32, dtype=np.float32), sample_rate)
                buf_f32       = []   # 버퍼 리셋 (분석 시작 전)

                ai_score = zone = rounded = None
                try:
                    # run_in_executor: pipeline.analyze 동안 event loop 블로킹 방지
                    result   = await loop.run_in_executor(
                        None,
                        lambda wb=wav_bytes: pipeline.analyze(wb, min_voiced_s=CHUNK_MIN_VOICED_S),
                    )
                    item     = (result.get("scores") or {}).get("4_breathiness") or {}
                    ai_score = item.get("ai_score")
                    zone     = item.get("zone")
                    rounded  = item.get("rounded_score")
                except Exception:
                    pass  # voiced 부족 등 → null 점수

                await websocket.send_text(json.dumps({
                    "type":          "breathiness_chunk",
                    "start_sec":     round(buf_start_sec, 3),
                    "end_sec":       round(chunk_end_sec, 3),
                    "ai_score":      ai_score,
                    "zone":          zone,
                    "rounded_score": rounded,
                }))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
