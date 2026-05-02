#!/usr/bin/env python3
"""
i3_validation_scoring.py
Apply learned score mappings to validation metrics → AI scores 0~5.
Results: results/validation_ai_scores.csv
"""
import os, csv, json, numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Import apply_mapping from score_mapper
import sys; sys.path.insert(0, SCRIPTS_DIR)
from score_mapper import apply_mapping

SCORE_COLS = ['비강사용','흉성두성','접촉강도','호흡식별','전방공명','연구개위치','공명개방','혀경직도','상압하압']
REG_MAP = {"low": "low", "mid": "mid", "high": "high"}


def get_val_ai_value(metrics_reg, col):
    """Extract metric value for the validation score column."""
    m = metrics_reg
    if col == '비강사용':    return None  # nasal_ratio unavailable for single mic
    if col == '흉성두성':    return m.get('cq_mean', {}).get('mean')
    if col == '접촉강도':    return m.get('cq_peak', {}).get('mean')
    if col == '호흡식별':    return m.get('cpp', {}).get('mean')
    if col == '전방공명':    return m.get('spectral_centroid', {}).get('mean')
    if col == '연구개위치':  return None  # nasal_ratio unavailable
    if col == '공명개방':    return None  # no direct AI indicator
    if col == '혀경직도':    return None  # no direct AI indicator
    if col == '상압하압':    return m.get('spectral_tilt', {}).get('mean')
    return None


def main():
    with open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8") as f:
        mapper_data = json.load(f)
    mappings = mapper_data["mappings"]

    with open(os.path.join(RESULTS_DIR, "validation_metrics.json"), encoding="utf-8") as f:
        val_data = json.load(f)

    rows = []
    for test_id, entry in sorted(val_data["results"].items()):
        for reg in ["low", "mid", "high"]:
            metrics_reg = entry.get("metrics_by_register", {}).get(reg, {})
            row = {"test_id": test_id, "register": reg}
            for col in SCORE_COLS:
                raw_val = get_val_ai_value(metrics_reg, col)
                if raw_val is not None and col in mappings:
                    score = apply_mapping(raw_val, mappings[col])
                    row[col] = round(score, 2) if score is not None else ""
                else:
                    row[col] = ""
            rows.append(row)

    out = os.path.join(RESULTS_DIR, "validation_ai_scores.csv")
    fieldnames = ["test_id", "register"] + SCORE_COLS
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ validation_ai_scores.csv: {len(rows)} rows → {out}")
    # Sample
    for r in rows[:3]:
        print(f"  {r['test_id']} {r['register']}: " +
              ", ".join(f"{c}={r[c]}" for c in SCORE_COLS if r.get(c) != ""))


if __name__ == "__main__":
    main()
