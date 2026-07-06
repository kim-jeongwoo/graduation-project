"""
test_ws_realtime.py — /ws/realtime WebSocket 검증

Usage:
    conda activate EGGDML
    python dml-server/scripts/test_ws_realtime.py [wav_path] [song_id]

기본값:
    wav_path = data/vocal_academy/validation_t2/test_11.wav
    song_id  = 004

검증 항목:
  1. pitch_match 응답 수신 (200ms마다) + latency 측정
  2. breathiness_chunk 응답 수신 (5초마다)
  3. chunk 호흡 평균 vs HTTP /analyze 전체 결과 비교 (일관성 < 0.5점)
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import deque
from pathlib import Path

import librosa
import numpy as np
import requests
import soundfile as sf
import websockets

_ROOT      = Path(__file__).parents[2]   # scripts/ → dml-server/ → egg_prediction/
HOST       = "localhost"
PORT       = 8001
WS_URI     = f"ws://{HOST}:{PORT}/ws/realtime?song_id={{song_id}}"
HTTP_URL   = f"http://{HOST}:{PORT}/analyze"

TARGET_SR  = 16000
CHUNK_SAMP = 3200   # 200ms @ 16kHz


# ── 오디오 로드 ──────────────────────────────────────────────────────

def _load_wav(path: str) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    return audio


# ── HTTP 전체 분석 (비교 기준) ───────────────────────────────────────

def http_analyze(wav_path: str, song_id: str) -> dict:
    with open(wav_path, "rb") as f:
        resp = requests.post(
            HTTP_URL,
            params={"song_id": song_id},
            files={"file": ("test.wav", f, "audio/wav")},
            timeout=120,
        )
    return resp.json()


# ── WebSocket 테스트 ─────────────────────────────────────────────────

async def ws_test(wav_path: str, song_id: str) -> tuple[list, list]:
    """
    Returns: (pitch_latencies_ms, breath_results)
    """
    audio    = _load_wav(wav_path)
    n_chunks = min(len(audio) // CHUNK_SAMP, 50)   # 10초 (50 × 200ms) — latency 실측용

    print(f"[WS] uri={WS_URI.format(song_id=song_id)}")
    print(f"     wav={Path(wav_path).name}  chunks={n_chunks} ({n_chunks*0.2:.1f}s)\n")

    pitch_latencies: list[float] = []
    breath_results:  list[dict]  = []
    send_times:      deque       = deque()

    n_pitch_done   = 0
    n_breath_done  = 0
    n_breath_exp   = n_chunks // 25  # 5초마다 1개

    async with websockets.connect(WS_URI.format(song_id=song_id)) as ws:
        # 메타 전송
        await ws.send(json.dumps({"type": "meta", "sample_rate": TARGET_SR, "start_timestamp": 0.0}))

        # ── 송신 태스크 ──────────────────────────────────────────────
        async def sender():
            for i in range(n_chunks):
                chunk     = audio[i * CHUNK_SAMP:(i + 1) * CHUNK_SAMP]
                chunk_i16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
                t_send    = time.perf_counter()
                await ws.send(chunk_i16.tobytes())
                send_times.append(t_send)
                await asyncio.sleep(0.18)  # 실시간 pacing (~200ms 간격 시뮬레이션)

        # ── 수신 태스크 ──────────────────────────────────────────────
        async def receiver():
            nonlocal n_pitch_done, n_breath_done
            while n_pitch_done < n_chunks or n_breath_done < n_breath_exp:
                try:
                    raw    = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    t_recv = time.perf_counter()
                    resp   = json.loads(raw)
                except asyncio.TimeoutError:
                    print("  [WARN] recv timeout")
                    break

                if resp["type"] == "pitch_match":
                    t_send = send_times.popleft() if send_times else None
                    lat    = (t_recv - t_send) * 1000 if t_send else 0.0
                    pitch_latencies.append(lat)
                    n_pitch_done += 1
                    # 처음 3개 + 매 25번째 출력
                    if n_pitch_done <= 3 or n_pitch_done % 25 == 0:
                        print(f"  [pitch #{n_pitch_done:3d}] "
                              f"t={resp['timestamp']:.1f}s  "
                              f"user={resp['user_midi']}  "
                              f"guide={resp['guide_midi']}  "
                              f"match={resp['match_score']}  "
                              f"latency={lat:.1f}ms")

                elif resp["type"] == "breathiness_chunk":
                    breath_results.append(resp)
                    n_breath_done += 1
                    print(f"  [BREATH #{n_breath_done}] "
                          f"{resp['start_sec']:.1f}~{resp['end_sec']:.1f}s  "
                          f"ai_score={resp['ai_score']}  zone={resp['zone']}")

        await asyncio.gather(sender(), receiver())

    return pitch_latencies, breath_results


# ── 메인 ─────────────────────────────────────────────────────────────

async def main(wav_path: str, song_id: str):
    # 1. HTTP 전체 분석
    print("[HTTP /analyze] 전체 wav 분석 중 (비교 기준)...")
    t0   = time.perf_counter()
    full = http_analyze(wav_path, song_id)
    print(f"  완료 ({(time.perf_counter()-t0)*1000:.0f}ms)")
    full_item  = (full.get("scores") or {}).get("4_breathiness") or {}
    full_score = full_item.get("ai_score")
    full_zone  = full_item.get("zone")
    print(f"  호흡식별: ai_score={full_score}  zone={full_zone}\n")

    # 2. WebSocket 테스트
    pitch_lats, breath_results = await ws_test(wav_path, song_id)

    # 3. 결과 요약
    print("\n" + "="*60)
    if pitch_lats:
        arr = np.array(pitch_lats)
        print(f"[음정 latency]  mean={arr.mean():.1f}ms  "
              f"p95={np.percentile(arr,95):.1f}ms  max={arr.max():.1f}ms")
    else:
        print("[음정 latency]  데이터 없음")

    if breath_results:
        scores = [r["ai_score"] for r in breath_results if r["ai_score"] is not None]
        if scores:
            chunk_mean = float(np.mean(scores))
            print(f"[호흡 chunk]    n={len(breath_results)}  "
                  f"scores={[round(s,2) for s in scores]}  mean={chunk_mean:.2f}")
            if full_score is not None:
                diff = abs(chunk_mean - full_score)
                ok   = diff < 0.5
                print(f"[일관성]        전체={full_score:.2f}  chunk평균={chunk_mean:.2f}  "
                      f"차이={diff:.2f}  {'✓ OK (<0.5)' if ok else '⚠ 불일치 (≥0.5)'}")
        else:
            print("[호흡 chunk]    n=0 (모두 null — voiced 부족)")
    else:
        print("[호흡 chunk]    수신 없음")
    print("="*60)


if __name__ == "__main__":
    wav = sys.argv[1] if len(sys.argv) > 1 else \
        str(_ROOT / "data/vocal_academy/validation_t2/test_11.wav")
    sid = sys.argv[2] if len(sys.argv) > 2 else "004"
    asyncio.run(main(wav, sid))
