"""
F4-5 검증: 21명 wav × analyze_with_timeline → 4 항목 chunk 점수 + 비용 측정.

산출: data/vocal_academy/results/sidetrack/timeline_scores_4items_validation.csv
      data/vocal_academy/results/sidetrack/timeline_scores_4items_summary.csv

검증 항목:
  - 4 항목 ai_score 0~5 범위
  - chunk_duration_s < 5s 시 low_confidence_items 동작
  - 곡 전체 v2 점수 (predictions_21.csv) vs chunk 평균 일치도
  - 곡당 비용 mean/std
"""
import csv
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

ROOT = Path("/home/dmlserver/projects/egg_prediction")
sys.path.insert(0, str(ROOT / "dml-server/model_server"))
sys.path.insert(0, str(ROOT / "dml-server/scripts/sidetrack"))
sys.path.insert(0, str(ROOT / "dml-server/ai-model"))

from analysis_pipeline import AnalysisPipeline
from services.timeline_analysis import analyze_with_timeline

CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRIT = ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPS = ROOT / "data/vocal_academy/results/ai_scores.json"
OUT  = ROOT / "data/vocal_academy/results/sidetrack/timeline_scores_4items_validation.csv"
SUM  = ROOT / "data/vocal_academy/results/sidetrack/timeline_scores_4items_summary.csv"
PRED = ROOT / "data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv"

A_DIR = ROOT / "data/vocal_academy/validation_510"
B_DIR = ROOT / "data/vocal_academy/control_pre_510"

ITEMS = ("3_vocal_fold_contact","4_breathiness","6_soft_palate","8_tongue_tension")
ITEM_KOR = {
    "3_vocal_fold_contact":"접촉강도", "4_breathiness":"호흡식별",
    "6_soft_palate":"연구개위치",     "8_tongue_tension":"혀경직도",
}


def list_wavs():
    """21명 wav 경로 반환 (A1~A10, B1~B11 — B는 raw 우선, 없으면 앱)."""
    out = []
    for i in range(1, 11):
        p = A_DIR / f"A{i}.wav"
        if p.exists(): out.append(("A", i, p))
    for i in range(1, 12):
        raw = B_DIR / f"B{i}.wav"
        app = B_DIR / f"B{i}(앱).wav"
        if   raw.exists(): out.append(("B", i, raw))
        elif app.exists(): out.append(("B", i, app))
    return out


def synth_lrc(duration_s: float, every: float = 7.0, intro_skip: float = 5.0) -> list:
    segs = []
    t = intro_skip; i = 0
    while t + every <= duration_s - 3.0:
        segs.append({"time_start":float(t),"time_end":float(t+every),"text":f"L{i:02d}"})
        t += every; i += 1
    return segs


def main():
    print("[init] loading pipeline...")
    pipe = AnalysisPipeline(str(CKPT), str(CRIT), str(MAPS))
    print(f"  v2={'OK' if pipe.v2 else 'MISSING'}")

    pred_df = pd.read_csv(PRED)
    print(f"[ref] predictions_21.csv rows={len(pred_df)}")

    wavs = list_wavs()
    print(f"[run] N={len(wavs)} wav files")

    rows: list[dict] = []
    summary: list[dict] = []
    elapsed_all: list[float] = []

    for cohort, idx, path in wavs:
        sid = f"{cohort}{idx}"
        try:
            audio, sr = sf.read(path, dtype="float32")
            if audio.ndim>1: audio = audio.mean(axis=1)
            dur = len(audio)/sr
            audio_bytes = open(path,"rb").read()
        except Exception as e:
            print(f"  [{sid}] load_err: {e}"); continue

        lrc = synth_lrc(dur, every=7.0)
        if not lrc:
            print(f"  [{sid}] dur={dur:.1f}s — too short, skip"); continue

        t0 = time.perf_counter()
        try:
            ts, meta = analyze_with_timeline(audio_bytes, lrc, pipe)
        except Exception as e:
            print(f"  [{sid}] analyze_err: {e}"); continue
        elapsed = time.perf_counter() - t0
        elapsed_all.append(elapsed)

        # row per chunk
        for ci, chunk in enumerate(ts):
            row = {
                "subject_id":          sid,
                "cohort":              cohort,
                "wav":                 path.name,
                "chunk_idx":           ci,
                "start_sec":           chunk["start_sec"],
                "end_sec":             chunk["end_sec"],
                "chunk_duration_s":    chunk["chunk_duration_s"],
                "low_confidence_n":    len(chunk["low_confidence_items"]),
                "low_confidence_items": ",".join(chunk["low_confidence_items"]),
            }
            for k in ITEMS:
                v = chunk["scores"].get(k)
                row[f"{k}__ai"]    = v["ai_score"]      if v else None
                row[f"{k}__round"] = v["rounded_score"] if v else None
                row[f"{k}__tier"]  = v["tier"]          if v else None
            rows.append(row)

        # summary per wav
        sum_row = {
            "subject_id": sid, "cohort": cohort,
            "duration_s": round(dur,1), "n_chunks": meta["n_chunks"],
            "n_ok": meta["n_ok"], "n_skipped": meta["n_skipped"],
            "elapsed_s": round(elapsed,1),
            "avg_chunk_ms": meta["v2_chunk_cost_avg_ms"],
        }
        for k in ITEMS:
            ai_vals = [c["scores"][k]["ai_score"] for c in ts
                       if c["scores"].get(k) and c["scores"][k]["ai_score"] is not None]
            sum_row[f"{k}__chunk_mean"] = round(np.mean(ai_vals),3) if ai_vals else None
            sum_row[f"{k}__chunk_std"]  = round(np.std(ai_vals),3)  if ai_vals else None
            # ref full-song v2 score from predictions_21.csv
            ref = pred_df[(pred_df.subject_id==sid) & (pred_df.item==ITEM_KOR[k])]
            sum_row[f"{k}__ref_full"] = float(ref.predicted_score.iloc[0]) if len(ref)>0 else None
        summary.append(sum_row)

        print(f"  [{sid}] dur={dur:.0f}s chunks={meta['n_chunks']} "
              f"elapsed={elapsed:.0f}s avg_chunk={meta['v2_chunk_cost_avg_ms']:.0f}ms")

    # ── 출력 ──
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["subject_id","cohort","wav","chunk_idx","start_sec","end_sec",
            "chunk_duration_s","low_confidence_n","low_confidence_items"]
    for k in ITEMS:
        cols += [f"{k}__ai", f"{k}__round", f"{k}__tier"]
    pd.DataFrame(rows, columns=cols).to_csv(OUT, index=False)

    sum_cols = ["subject_id","cohort","duration_s","n_chunks","n_ok","n_skipped",
                "elapsed_s","avg_chunk_ms"]
    for k in ITEMS:
        sum_cols += [f"{k}__chunk_mean", f"{k}__chunk_std", f"{k}__ref_full"]
    pd.DataFrame(summary, columns=sum_cols).to_csv(SUM, index=False)

    # ── 검증 통계 ──
    print(f"\n[CSV] rows: {OUT}  ({len(rows)} chunks)")
    print(f"[CSV] summary: {SUM}  ({len(summary)} wavs)")

    print(f"\n[stats] elapsed/song: mean={np.mean(elapsed_all):.1f}s  "
          f"std={np.std(elapsed_all):.1f}s  min={min(elapsed_all):.1f}  max={max(elapsed_all):.1f}")

    # range check
    bad = 0; tot = 0
    for r in rows:
        for k in ITEMS:
            ai = r[f"{k}__ai"]
            if ai is None: continue
            tot += 1
            if not (0 <= ai <= 5): bad += 1
    print(f"[range] out_of_range_ai = {bad}/{tot}  ({100*bad/max(tot,1):.2f}%)")

    # low_conf check
    short = sum(1 for r in rows if r["chunk_duration_s"] < 5.0)
    short_flagged = sum(1 for r in rows if r["chunk_duration_s"] < 5.0
                        and "4_breathiness" in r["low_confidence_items"])
    long_unflagged = sum(1 for r in rows if r["chunk_duration_s"] >= 5.0
                         and r["low_confidence_n"] == 0)
    long_n = sum(1 for r in rows if r["chunk_duration_s"] >= 5.0)
    print(f"[lowconf] short chunks (<5s): {short}, with flag: {short_flagged}/{short}")
    print(f"[lowconf] long chunks (≥5s): {long_n}, without flag: {long_unflagged}/{long_n}")

    # chunk_mean vs ref_full corr
    print(f"\n[consistency] chunk mean vs full-song ref")
    sdf = pd.DataFrame(summary)
    for k in ITEMS:
        cm = f"{k}__chunk_mean"; rf = f"{k}__ref_full"
        valid = sdf[[cm,rf]].dropna()
        if len(valid) < 3:
            print(f"  {k:<22}: n<3, skip"); continue
        corr = valid[cm].corr(valid[rf])
        mae  = (valid[cm] - valid[rf]).abs().mean()
        print(f"  {k:<22}: n={len(valid):2d} corr={corr:.3f}  MAE={mae:.3f}")


if __name__ == "__main__":
    main()
