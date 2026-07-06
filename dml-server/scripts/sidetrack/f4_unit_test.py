"""
F4-1 단위 테스트: timeline_analysis.analyze_with_timeline 4 항목 schema 검증.

1개 wav (B1.wav)에 synthetic LRC 적용 → chunk별 4 항목 score + low_conf 확인.
"""
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path("/home/dmlserver/projects/egg_prediction")
sys.path.insert(0, str(ROOT / "dml-server/model_server"))
sys.path.insert(0, str(ROOT / "dml-server/scripts/sidetrack"))
sys.path.insert(0, str(ROOT / "dml-server/ai-model"))

from analysis_pipeline import AnalysisPipeline
from services.timeline_analysis import analyze_with_timeline, build_chunks

WAV    = ROOT / "data/vocal_academy/control_pre_510/B1.wav"
CKPT   = ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRIT   = ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPS   = ROOT / "data/vocal_academy/results/ai_scores.json"


def synth_lrc(duration_s: float, every: float = 7.0) -> list:
    """duration 동안 every초마다 짧은 LRC line 생성."""
    segs = []
    t = 5.0  # 5초 intro skip
    i = 0
    while t + every <= duration_s - 3.0:
        segs.append({
            "time_start": float(t),
            "time_end":   float(t + every),
            "text":       f"synthetic_line_{i:02d}",
        })
        t += every
        i += 1
    return segs


def main():
    print("[init] loading pipeline...")
    t0 = time.perf_counter()
    pipeline = AnalysisPipeline(str(CKPT), str(CRIT), str(MAPS))
    print(f"  loaded in {time.perf_counter()-t0:.1f}s, v2={'OK' if pipeline.v2 else 'MISSING'}")

    print(f"\n[wav] {WAV.name}")
    audio_bytes = open(WAV, "rb").read()
    sr_check, _ = sf.read(io.BytesIO(audio_bytes))
    audio_arr, sr0 = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    if audio_arr.ndim > 1: audio_arr = audio_arr.mean(axis=1)
    dur = len(audio_arr) / sr0
    print(f"  duration={dur:.1f}s, sr={sr0}")

    # synthetic LRC: chunk 7s × N (≥5s → high confidence)
    lrc7 = synth_lrc(dur, every=7.0)
    print(f"\n[run] synthetic LRC (n_lines={len(lrc7)}, 7s each)")
    t0 = time.perf_counter()
    ts7, meta7 = analyze_with_timeline(audio_bytes, lrc7, pipeline)
    print(f"  elapsed={time.perf_counter()-t0:.1f}s, n_chunks={meta7['n_chunks']}, "
          f"ok={meta7['n_ok']}, skip={meta7['n_skipped']}, "
          f"avg_chunk_ms={meta7['v2_chunk_cost_avg_ms']}")

    # synthetic LRC: chunk 3.5s × N (<5s → low_conf 표시)
    lrc35 = synth_lrc(dur, every=3.5)[:5]   # 5개만
    print(f"\n[run] synthetic LRC short (n_lines={len(lrc35)}, 3.5s each)")
    t0 = time.perf_counter()
    ts35, meta35 = analyze_with_timeline(audio_bytes, lrc35, pipeline)
    print(f"  elapsed={time.perf_counter()-t0:.1f}s, n_chunks={meta35['n_chunks']}, "
          f"ok={meta35['n_ok']}, skip={meta35['n_skipped']}")

    # ── 7s chunk: 4항목 점수 + low_conf 비어있어야 함 ──
    print("\n[check] 7s chunks — 4 scores per chunk, low_conf empty")
    for i, t in enumerate(ts7[:3]):
        print(f"  chunk[{i}] {t['start_sec']:.1f}~{t['end_sec']:.1f} "
              f"dur={t['chunk_duration_s']:.2f}s low_conf={t['low_confidence_items']}")
        for k in ("3_vocal_fold_contact","4_breathiness","6_soft_palate","8_tongue_tension"):
            v = t["scores"].get(k)
            if v:
                print(f"    {k:<22}: ai={v['ai_score']:.2f}  round={v['rounded_score']}  tier={v['tier']}")
            else:
                print(f"    {k:<22}: None")

    # ── 3.5s chunk: 3항목 (호흡/연구개/혀경직) low_conf 표시 ──
    print("\n[check] 3.5s chunks — high_star 3 items in low_conf")
    for i, t in enumerate(ts35[:3]):
        print(f"  chunk[{i}] dur={t['chunk_duration_s']:.2f}s low_conf={t['low_confidence_items']}")

    # ── range sanity check ──
    print("\n[check] score range 0~5")
    bad = 0
    for t in ts7:
        for k in ("3_vocal_fold_contact","4_breathiness","6_soft_palate","8_tongue_tension"):
            v = t["scores"].get(k)
            if v is None: continue
            ai = v["ai_score"]; rd = v["rounded_score"]
            if ai is None or not (0 <= ai <= 5):
                print(f"  BAD ai: {t['start_sec']:.1f}s {k}={ai}"); bad += 1
            if rd is None or not (0 <= rd <= 5):
                print(f"  BAD round: {t['start_sec']:.1f}s {k}={rd}"); bad += 1
    print(f"  out_of_range={bad}/{len(ts7)*4}")

    # ── tier 일관성 ──
    print("\n[check] tier consistency")
    for t in ts7[:2]:
        for k, v in t["scores"].items():
            if v: assert v["tier"] in ("high","high_star"), f"bad tier {v['tier']}"
    print("  tier OK")

    # ── metadata ──
    print("\n[meta] timeline_metadata")
    for k in ("shown_indicators","shown_indicators_meta","chunk_score_items",
              "low_confidence_threshold_s","score_mapper_version","v2_chunk_cost_avg_ms"):
        print(f"  {k}: {meta7[k]}")


if __name__ == "__main__":
    main()
