#!/usr/bin/env python3
"""
rerun_with_new_scores.py — 새 평가 점수 도착 시 전체 파이프라인 재실행
=======================================================================
사용법:
  python rerun_with_new_scores.py --new_scores_csv /path/to/new_rater1.csv

자동 실행 단계:
  a. 새 CSV로 trainer_scores.csv 병합 (백업 후)
  b. ICC 재계산
  c. score_mapper.py 재실행
  d. compare_scores.py 재실행
  e. per_register_analysis.py 재실행
  f. before/after 비교표 출력

새 CSV 형식: rater, singer, gender, song, song_name, register, 9개 항목
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR    = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR  = os.path.join(VOCAL_DIR, "results")
SCRIPTS_DIR  = os.path.join(PROJECT_ROOT, "scripts")

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]
EXCLUDE_PAIRS = {(6, 8)}


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows, path, fieldnames):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_script(script_name):
    path = os.path.join(SCRIPTS_DIR, script_name)
    result = subprocess.run(
        [sys.executable, path],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        print(f"  ⚠️ {script_name} failed:\n{result.stderr[-500:]}")
    else:
        last_lines = result.stdout.strip().split("\n")[-5:]
        for ln in last_lines:
            print(f"  {ln}")
    return result.returncode == 0


def icc_21(data):
    """ICC(2,1) absolute agreement."""
    subjects = sorted(set(s for s, _, _ in data))
    raters   = sorted(set(r for _, r, _ in data))
    n, k = len(subjects), len(raters)
    if n < 2 or k < 2:
        return None
    sub_idx = {s: i for i, s in enumerate(subjects)}
    mat = np.full((n, k), np.nan)
    for s, r, v in data:
        ri = raters.index(r)
        mat[sub_idx[s]][ri] = float(v)
    row_m = np.nanmean(mat, axis=1)
    col_m = np.nanmean(mat, axis=0)
    grand = np.nanmean(mat)
    SS_r = k * np.nansum((row_m - grand)**2)
    SS_c = n * np.nansum((col_m - grand)**2)
    SS_tot = np.nansum((mat - grand)**2)
    SS_e = SS_tot - SS_r - SS_c
    df_r, df_c = n-1, k-1
    df_e = (n-1)*(k-1)
    MS_r = SS_r / df_r if df_r > 0 else 0
    MS_c = SS_c / df_c if df_c > 0 else 0
    MS_e = SS_e / df_e if df_e > 0 else 1e-10
    icc = (MS_r - MS_e) / (MS_r + (k-1)*MS_e + k*(MS_c - MS_e)/n)
    return float(icc)


def compute_icc(rows, col):
    data = []
    for row in rows:
        singer = row.get("singer", "")
        reg = row.get("register", "")
        rater = row.get("rater", "")
        v = row.get(col, "")
        if v and v.lstrip("-").isdigit():
            if (int(singer), int(row.get("song", 0))) not in EXCLUDE_PAIRS:
                data.append((f"{singer}_{reg}", rater, int(v)))
    return icc_21(data)


def load_ai_vs_trainer():
    """Load last compare_scores result."""
    path = os.path.join(RESULTS_DIR, "ai_vs_trainer.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", {})


def main():
    parser = argparse.ArgumentParser(description="Rerun pipeline with new rater scores")
    parser.add_argument("--new_scores_csv", required=True, help="New rater CSV path")
    args = parser.parse_args()

    if not os.path.exists(args.new_scores_csv):
        print(f"ERROR: {args.new_scores_csv} not found")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(VOCAL_DIR, "trainer_scores.csv")

    print("="*60)
    print("Rerun pipeline with new rater scores")
    print(f"New scores: {args.new_scores_csv}")
    print("="*60)

    # ── a. Backup + merge new CSV ──────────────────────────────
    backup_path = csv_path.replace(".csv", f"_backup_{ts}.csv")
    shutil.copy2(csv_path, backup_path)
    print(f"\na. Backed up: {os.path.basename(backup_path)}")

    existing = load_csv(csv_path)
    new_rows  = load_csv(args.new_scores_csv)

    # Remove existing rows from same rater (will be replaced)
    new_raters = set(r.get("rater", "") for r in new_rows)
    existing_filtered = [r for r in existing if r.get("rater", "") not in new_raters]
    merged = existing_filtered + new_rows
    fieldnames = list(existing[0].keys()) if existing else list(new_rows[0].keys())
    write_csv(merged, csv_path, fieldnames)
    print(f"   Merged: {len(existing)} → {len(merged)} rows (replaced rater(s): {new_raters})")

    # ── b. ICC ────────────────────────────────────────────────
    print("\nb. ICC(2,1) comparison:")
    icc_before = {col: compute_icc(existing, col) for col in SCORE_COLS}
    icc_after  = {col: compute_icc(merged, col)   for col in SCORE_COLS}
    print(f"  {'항목':8s} {'Before':>8s} {'After':>8s} {'Δ':>8s}")
    for col in SCORE_COLS:
        b = icc_before[col]
        a = icc_after[col]
        delta = (a - b) if b and a else None
        b_str = f"{b:.3f}" if b else "  N/A"
        a_str = f"{a:.3f}" if a else "  N/A"
        d_str = f"{delta:+.3f}" if delta else "  N/A"
        print(f"  {col:8s} {b_str:>8s} {a_str:>8s} {d_str:>8s}")

    # ── c-e. Re-run scripts ────────────────────────────────────
    print("\nc. Running score_mapper.py ...")
    run_script("score_mapper.py")

    print("\nd. Running compare_scores.py ...")
    before_corr = load_ai_vs_trainer()
    run_script("compare_scores.py")
    after_corr = load_ai_vs_trainer()

    print("\ne. Running per_register_analysis.py ...")
    run_script("per_register_analysis.py")

    # ── f. Before/after comparison ─────────────────────────────
    print("\nf. AI vs Trainer correlation change:")
    items = ["비강사용", "흉성두성", "접촉강도", "호흡식별", "전방공명", "연구개위치", "상압하압"]
    print(f"  {'항목':8s} {'Before corr':>12s} {'After corr':>12s} {'Δ':>8s}")
    for item in items:
        b = before_corr.get(item, {}).get("pearson_corr")
        a = after_corr.get(item, {}).get("pearson_corr")
        delta = (a - b) if b is not None and a is not None else None
        b_str = f"{b:.3f}" if b is not None else "   N/A"
        a_str = f"{a:.3f}" if a is not None else "   N/A"
        d_str = f"{delta:+.3f}" if delta is not None else "   N/A"
        print(f"  {item:8s} {b_str:>12s} {a_str:>12s} {d_str:>8s}")

    print(f"\n✅ Pipeline complete. Backup: {os.path.basename(backup_path)}")


if __name__ == "__main__":
    main()
