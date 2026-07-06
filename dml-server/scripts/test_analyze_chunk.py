"""
test_analyze_chunk.py — POST /analyze-chunk 검증

Usage:
    conda activate EGGDML
    python dml-server/scripts/test_analyze_chunk.py

검증:
  case 1: 5s 정상 chunk          → 200 success, confidence=high
  case 2: 10s 정상 chunk         → 200 success, 시간 측정
  case 3: 2s chunk               → 400 chunk_too_short
  case 4: 7s 무음(silence)       → 200 no_voice (Guard A: voiced_s < dur×0.4)
  case 5: 7s 험(120Hz hum)       → 200 no_voice (Guard B: voiced_ratio>0.95+cpp<0.15)
  case 6: 5s + voiced 1.5s만     → 200 no_voice (40% 임계값 동작)
  case 7: 5s + voiced 2.5s       → 200 success (50% 통과)
  case 8: 일관성 — test_11 7~12s chunk vs 전체 분석 점수 차이 < 0.5
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from typing import Optional

import librosa
import numpy as np
import requests
import soundfile as sf

ROOT = Path(__file__).parents[2]
URL  = "http://localhost:8001/analyze-chunk"
TEST_WAV = ROOT / "data/vocal_academy/validation_t2/test_11.wav"
SR   = 16000


def _post(wav_bytes: bytes, **params) -> tuple[int, dict, float]:
    t0 = time.perf_counter()
    resp = requests.post(
        URL,
        params=params,
        files={"file": ("chunk.wav", wav_bytes, "audio/wav")},
        timeout=60,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return resp.status_code, resp.json(), elapsed_ms


def _wav_bytes(audio: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), sr, format="WAV", subtype="FLOAT")
    return buf.getvalue()


def _load_test_wav() -> np.ndarray:
    a, sr = sf.read(TEST_WAV, dtype="float32")
    if a.ndim > 1: a = a.mean(axis=1)
    if sr != SR: a = librosa.resample(a, orig_sr=sr, target_sr=SR)
    return a


# ── 합성 wav 생성 ────────────────────────────────────────────────────

def synth_silent(dur: float) -> np.ndarray:
    return np.zeros(int(dur * SR), dtype=np.float32)


def synth_hum(dur: float, freq: float = 120.0, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * amp).astype(np.float32)


def synth_partial_voice(dur: float, voiced_dur: float) -> np.ndarray:
    """
    합성: 앞부분 voiced_dur초만 test_11에서 voiced 구간 발췌, 나머지는 무음.
    """
    full = _load_test_wav()
    # test_11에서 t=75~80s가 voiced (이전 검증에서 확인)
    voiced_seg = full[75 * SR : 75 * SR + int(voiced_dur * SR)]
    silent_seg = np.zeros(int((dur - voiced_dur) * SR), dtype=np.float32)
    return np.concatenate([voiced_seg, silent_seg])


# ── 케이스 ───────────────────────────────────────────────────────────

def case(label: str, expect_status: int, expect_keys: dict,
         wav_bytes: bytes, **params):
    code, body, ms = _post(wav_bytes, **params)
    ok = (code == expect_status)
    for k, v in expect_keys.items():
        actual = body.get(k)
        if v == "_NOT_NULL_":
            ok = ok and actual is not None
        else:
            ok = ok and (actual == v)
    mark = "✓" if ok else "✗"
    summary = ", ".join(f"{k}={body.get(k)}" for k in list(expect_keys.keys())[:3])
    print(f"  {mark} {label:35s}  HTTP={code} ({ms:>5.0f}ms)  {summary}")
    if not ok:
        print(f"      expected: {expect_status} {expect_keys}")
        print(f"      got     : {body}")
    return body, ms


def run_all():
    print("=" * 80)
    print("[/analyze-chunk 검증]")
    print("=" * 80)

    test_audio = _load_test_wav()

    # case 1: 5s 정상 chunk (test_11 t=75~80s, 유성음 구간)
    chunk_5s = test_audio[75 * SR : 80 * SR]
    body1, ms1 = case(
        "case 1: 5s 정상 chunk",
        200, {"status": "success"},
        _wav_bytes(chunk_5s),
    )
    if body1.get("status") == "success":
        s = body1["scores"]
        for k in ("3_vocal_fold_contact", "4_breathiness"):
            print(f"      {k}: ai_score={s[k]['ai_score']}  zone={s[k]['zone']}  conf={s[k]['confidence']}")

    # case 2: 10s 정상 chunk
    chunk_10s = test_audio[75 * SR : 85 * SR]
    body2, ms2 = case(
        "case 2: 10s 정상 chunk",
        200, {"status": "success"},
        _wav_bytes(chunk_10s),
    )
    if body2.get("status") == "success":
        s = body2["scores"]
        for k in ("3_vocal_fold_contact", "4_breathiness"):
            print(f"      {k}: ai_score={s[k]['ai_score']}  zone={s[k]['zone']}  conf={s[k]['confidence']}")

    # case 3: 2s chunk → 400
    case(
        "case 3: 2s chunk → too_short",
        400, {"error": "chunk_too_short"},
        _wav_bytes(test_audio[75 * SR : 77 * SR]),
    )

    # case 4: 7s 무음
    case(
        "case 4: 7s silent → no_voice",
        200, {"status": "no_voice"},
        _wav_bytes(synth_silent(7.0)),
    )

    # case 5: 7s 120Hz 험
    case(
        "case 5: 7s hum(120Hz) → no_voice",
        200, {"status": "no_voice"},
        _wav_bytes(synth_hum(7.0)),
    )

    # case 6: 5s + voiced 1.5s만 (30%, 임계값 40% 미달)
    case(
        "case 6: 5s/voiced=1.5s → no_voice",
        200, {"status": "no_voice"},
        _wav_bytes(synth_partial_voice(5.0, 1.5)),
    )

    # case 7: 5s + voiced 3.5s (70%, 임계값 2.0s 명확히 통과)
    #         (2.5s는 자음·무성 구간으로 VAD 검출이 임계값에 근접 — 마진 확보)
    case(
        "case 7: 5s/voiced=3.5s → success",
        200, {"status": "success"},
        _wav_bytes(synth_partial_voice(5.0, 3.5)),
    )

    # case 8: 일관성 — test_11 7s chunk vs 전체 분석
    print("\n[일관성 검증]")
    print("  test_11.wav 75~82s (7s chunk) vs 전체 wav 분석 비교")
    chunk_7s_bytes = _wav_bytes(test_audio[75 * SR : 82 * SR])
    code8, body8, ms8 = _post(chunk_7s_bytes)
    if body8.get("status") == "success":
        s_chunk = body8["scores"]
        # 전체 wav /analyze
        with open(TEST_WAV, "rb") as f:
            r_full = requests.post(
                "http://localhost:8001/analyze",
                files={"file": ("full.wav", f, "audio/wav")},
                timeout=120,
            )
        full = r_full.json()
        s_full = full.get("scores") or {}
        print(f"  {'항목':25s}  {'chunk(7s)':>10s}  {'전체':>10s}  {'차이':>8s}  판정")
        for k in ("3_vocal_fold_contact", "4_breathiness"):
            c = s_chunk[k]["ai_score"]
            f_score = (s_full.get(k) or {}).get("ai_score")
            if c is not None and f_score is not None:
                diff = abs(c - f_score)
                ok = "✓" if diff < 0.5 else "✗"
                print(f"  {k:25s}  {c:>10.2f}  {f_score:>10.2f}  {diff:>+8.2f}  {ok}")
            else:
                print(f"  {k:25s}  {c}  {f_score}")

    # ── 처리 시간 요약 ───────────────────────────────────────────────
    print("\n[처리 시간]")
    print(f"  case 1 (5s):  {ms1:>6.0f}ms")
    print(f"  case 2 (10s): {ms2:>6.0f}ms")
    print(f"  목표 5000ms  → {'✓ OK' if max(ms1, ms2) < 5000 else '✗ 초과'}")


if __name__ == "__main__":
    run_all()
