#!/usr/bin/env python3
"""
j1_theory_based_mapping.py
Diagnose mapping directions + create theory-forced score_mapper.
Results: results/theory_mapping_diagnosis.json
         results/validation_comparison_theory.json
"""
import os, sys, json, csv, numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from score_mapper import (ITEM_MAP, REGISTER_MAP, EXCLUDE_PAIRS, RESULTS_DIR as SM_RESULTS_DIR,
                          load_analysis_data, load_trainer_scores, apply_mapping)
from scipy import stats as scipy_stats

# ── Theory-defined directions ──────────────────────────────────────
# True = AI indicator ↑ should map to score ↑
# False = AI indicator ↑ should map to score ↓
THEORY_DIRECTION = {
    "비강사용":  False,  # nasal_ratio ↑ → nasal heavy → score 0~1 (미달)
    "흉성두성":  True,   # CQ ↑ → chest heavy → score 4~5 (과함)
    "접촉강도":  True,   # CQ_peak ↑ → tight → score 4~5
    "호흡식별":  True,   # CPP ↑ → compressed → score 4~5
    "전방공명":  False,  # centroid ↑ → forward → score 0~1 (전방과다)
    "연구개위치": False,  # nasal_ratio ↑ → open soft palate → score 0~1 (하강)
    "상압하압":  True,   # tilt ↑ (less negative) → more compressed → score 4~5
}

THEORY_NOTES = {
    "비강사용":  "nasal_ratio↑=비강과다=미달(0). 방향:역",
    "흉성두성":  "CQ↑=흉성강함=과함(4~5). 방향:정(현재 역으로 학습됨!)",
    "접촉강도":  "CQ_peak↑=강한접촉=과함(4~5). 방향:정",
    "호흡식별":  "CPP↑=압축된발성=과함(4~5). 방향:정",
    "전방공명":  "centroid↑=전방과다=미달(0~1). 방향:역",
    "연구개위치": "nasal_ratio↑=연구개하강=미달(0~1). 방향:역",
    "상압하압":  "spectral_tilt↑(less negative)=하압강함=과함(4~5). 방향:정",
}


def monotone_mapper_force(ai_vals, trainer_vals, force_positive):
    """
    Build thresholds for score 0~5 where direction is forced.
    Divides trainer score groups and computes AI median per group.
    If force_positive=True, ensure thresholds are non-decreasing.
    """
    from scipy.stats import percentileofscore
    ai = np.array(ai_vals); tv = np.array(trainer_vals)

    # Collect AI values per trainer score bin
    bins = {i: [] for i in range(6)}
    for a, t in zip(ai, tv):
        s = min(5, max(0, round(t)))
        bins[s].append(a)

    # Compute median per bin, interpolate missing
    raw_thresh = {}
    for s in range(6):
        if bins[s]:
            raw_thresh[s] = float(np.median(bins[s]))

    # Fill gaps
    known = sorted(raw_thresh.keys())
    for s in range(6):
        if s not in raw_thresh and known:
            lower = max([k for k in known if k <= s], default=known[0])
            upper = min([k for k in known if k >= s], default=known[-1])
            if lower == upper:
                raw_thresh[s] = raw_thresh[lower]
            else:
                frac = (s - lower) / (upper - lower)
                raw_thresh[s] = raw_thresh[lower] * (1-frac) + raw_thresh[upper] * frac

    # Force monotonicity
    thresh = [raw_thresh[i] for i in range(6)]
    if force_positive:
        for i in range(1, 6):
            if thresh[i] < thresh[i-1]:
                thresh[i] = thresh[i-1]
    else:
        for i in range(1, 6):
            if thresh[i] > thresh[i-1]:
                thresh[i] = thresh[i-1]

    return {str(i): float(thresh[i]) for i in range(6)}


def apply_theory_mapping(ai_val, thresholds, force_positive):
    """Apply theory-forced mapping."""
    vals = [float(thresholds[str(i)]) for i in range(6)]
    scores = list(range(6))
    if force_positive:
        if ai_val <= vals[0]: return 0.0
        if ai_val >= vals[-1]: return 5.0
        for i in range(len(vals)-1):
            if vals[i] <= ai_val <= vals[i+1]:
                frac = (ai_val - vals[i]) / (vals[i+1] - vals[i] + 1e-10)
                return float(i + frac)
    else:
        if ai_val >= vals[0]: return 0.0
        if ai_val <= vals[-1]: return 5.0
        for i in range(len(vals)-1):
            if vals[i] >= ai_val >= vals[i+1]:
                frac = (vals[i] - ai_val) / (vals[i] - vals[i+1] + 1e-10)
                return float(i + frac)
    # fallback
    diffs = [abs(ai_val - v) for v in vals]
    return float(np.argmin(diffs))


def main():
    print("Loading data...")
    analysis_data = load_analysis_data()
    trainer_avgs  = load_trainer_scores()

    # Get current learned mapping
    with open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8") as f:
        ai_scores_data = json.load(f)
    learned_mappings = ai_scores_data["mappings"]

    # Collect (ai_val, trainer_score) pairs per column
    from score_mapper import get_ai_value
    pairs = defaultdict(lambda: {"ai":[], "trainer":[]})
    for (singer, song, register), trainer_scores in trainer_avgs.items():
        for csv_col, item_info in ITEM_MAP.items():
            t = trainer_scores.get(csv_col)
            if t is None: continue
            ai = get_ai_value(analysis_data, item_info, singer, song, register)
            if ai is None: continue
            pairs[csv_col]["ai"].append(ai)
            pairs[csv_col]["trainer"].append(t)

    # Build theory mappings + diagnosis
    theory_mappings = {}
    print("\n=== J-1: Mapping Direction Diagnosis ===")
    print(f"{'항목':12s} {'학습방향':15s} {'이론방향':15s} {'일치':>6s} {'학습corr':>10s}")
    print("-"*60)

    diagnosis = []
    for col in ITEM_MAP:
        if not pairs[col]["ai"]: continue
        force_pos = THEORY_DIRECTION.get(col, True)

        # Learned direction
        lm = learned_mappings.get(col, {})
        thresh = lm.get("thresholds", {})
        if thresh:
            t0 = float(thresh.get("0", 0)); t5 = float(thresh.get("5", 0))
            learned_dir = "AI↑→Score↑" if t5 > t0 else "AI↑→Score↓"
            learned_pos = (t5 > t0)
        else:
            learned_dir = "N/A"; learned_pos = None

        theory_dir = "AI↑→Score↑" if force_pos else "AI↑→Score↓"
        match = "✅" if learned_pos == force_pos else "⚠️ 역방향!"
        corr = lm.get("correlation", 0)

        print(f"  {col:10s}  {learned_dir:14s}  {theory_dir:14s}  {match:>6s}  {corr:>9.3f}")
        print(f"           NOTE: {THEORY_NOTES.get(col,'')}")

        # Build theory-forced thresholds
        t_thresh = monotone_mapper_force(
            pairs[col]["ai"], pairs[col]["trainer"], force_pos
        )
        theory_mappings[col] = {
            "thresholds": t_thresh,
            "force_positive": force_pos,
            "n_pairs": len(pairs[col]["ai"]),
            "ai_range": {"min": float(min(pairs[col]["ai"])),
                         "max": float(max(pairs[col]["ai"]))},
        }
        diagnosis.append({
            "col": col, "learned_dir": learned_dir, "theory_dir": theory_dir,
            "direction_match": learned_pos == force_pos, "learned_corr": corr,
            "note": THEORY_NOTES.get(col, ""),
        })

    # Apply theory mapping to all training data → compute corr
    print("\n=== Applying theory mapping to training data ===")
    print(f"{'항목':12s} {'기존corr':>10s} {'이론corr':>10s} {'개선':>8s}")
    print("-"*42)

    theory_scores = []
    for (singer, song, register), trainer_scores in sorted(trainer_avgs.items()):
        entry = {"singer_id": singer, "song_id": song, "register": register,
                 "trainer_avg": {}, "ai_scores_baseline": {}, "ai_scores_theory": {}}
        for csv_col in ITEM_MAP:
            t = trainer_scores.get(csv_col)
            entry["trainer_avg"][csv_col] = round(t, 2) if t else None
            ai_val = get_ai_value(analysis_data, ITEM_MAP[csv_col], singer, song, register)
            if ai_val is not None:
                # Baseline mapping
                b_score = apply_mapping(ai_val, learned_mappings.get(csv_col, {}))
                entry["ai_scores_baseline"][csv_col] = round(b_score, 2) if b_score is not None else None
                # Theory mapping
                if csv_col in theory_mappings:
                    fp = theory_mappings[csv_col]["force_positive"]
                    t_score = apply_theory_mapping(ai_val, theory_mappings[csv_col]["thresholds"], fp)
                    entry["ai_scores_theory"][csv_col] = round(t_score, 2)
                else:
                    entry["ai_scores_theory"][csv_col] = None
            else:
                entry["ai_scores_baseline"][csv_col] = None
                entry["ai_scores_theory"][csv_col] = None
        theory_scores.append(entry)

    # Compute corr for each col
    for csv_col in ITEM_MAP:
        base_t, base_a, theo_a = [], [], []
        for e in theory_scores:
            tv = e["trainer_avg"].get(csv_col)
            bv = e["ai_scores_baseline"].get(csv_col)
            tv2 = e["ai_scores_theory"].get(csv_col)
            if tv and bv: base_t.append(tv); base_a.append(bv)
            if tv and tv2: theo_a.append(tv2)
        base_r = float(np.corrcoef(base_t, base_a)[0,1]) if len(base_t) >= 3 else None
        theo_t = [e["trainer_avg"].get(csv_col) for e in theory_scores
                  if e["trainer_avg"].get(csv_col) and e["ai_scores_theory"].get(csv_col)]
        theo_a2 = [e["ai_scores_theory"].get(csv_col) for e in theory_scores
                   if e["trainer_avg"].get(csv_col) and e["ai_scores_theory"].get(csv_col)]
        theo_r = float(np.corrcoef(theo_t, theo_a2)[0,1]) if len(theo_t) >= 3 else None
        delta = (theo_r - base_r) if (base_r and theo_r) else None
        b_str = f"{base_r:.3f}" if base_r else "  N/A"
        t_str = f"{theo_r:.3f}" if theo_r else "  N/A"
        d_str = f"{delta:+.3f}" if delta else "   N/A"
        print(f"  {csv_col:10s}  {b_str:>9s}  {t_str:>9s}  {d_str:>7s}")

    # Save theory mappings + training scores
    out = {
        "description": "Theory-forced score mappings",
        "theory_direction": {k: "positive" if v else "negative" for k,v in THEORY_DIRECTION.items()},
        "diagnosis": diagnosis,
        "mappings": theory_mappings,
        "training_scores": theory_scores,
    }
    jp = os.path.join(RESULTS_DIR, "theory_mapping.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {jp}")

    # Apply to validation data
    val_metrics = json.load(open(os.path.join(RESULTS_DIR, "validation_metrics.json"), encoding="utf-8"))
    val_ai_scores = json.load(open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8"))

    def get_val_ai_raw(metrics_reg, col):
        if col == '흉성두성':    return metrics_reg.get('cq_mean', {}).get('mean')
        if col == '접촉강도':    return metrics_reg.get('cq_peak', {}).get('mean')
        if col == '호흡식별':    return metrics_reg.get('cpp', {}).get('mean')
        if col == '전방공명':    return metrics_reg.get('spectral_centroid', {}).get('mean')
        if col == '상압하압':    return metrics_reg.get('spectral_tilt', {}).get('mean')
        return None

    AI_COLS = ['흉성두성','접촉강도','호흡식별','전방공명','상압하압']
    val_rows_theory = []
    for test_id, entry in sorted(val_metrics["results"].items()):
        for reg in ["low","mid","high"]:
            m = entry.get("metrics_by_register", {}).get(reg, {})
            row = {"test_id": test_id, "register": reg}
            for col in AI_COLS:
                raw = get_val_ai_raw(m, col)
                if raw is not None and col in theory_mappings:
                    fp = theory_mappings[col]["force_positive"]
                    sc = apply_theory_mapping(raw, theory_mappings[col]["thresholds"], fp)
                    row[col] = round(sc, 2)
                else:
                    row[col] = None
            val_rows_theory.append(row)

    # Compare baseline vs theory on validation
    val_csv = list(csv.DictReader(open(os.path.join(RESULTS_DIR, "validation_ai_scores.csv"), encoding="utf-8")))
    val_train = list(csv.DictReader(open(os.path.join(VOCAL_DIR, "trainer_scores_validation.csv"), encoding="utf-8")))

    # Trainer avg by (test_id, register)
    t_groups = defaultdict(lambda: defaultdict(list))
    for r in val_train:
        key = (r["test_id"], r["register"])
        for col in AI_COLS:
            v = r.get(col,"")
            if v.lstrip("-").isdigit():
                t_groups[key][col].append(float(v))
    t_avg = {k:{c:np.mean(v) for c,v in d.items()} for k,d in t_groups.items()}

    # Baseline (from existing csv)
    baseline_scores = {}
    for r in val_csv:
        key = (r["test_id"], r["register"])
        baseline_scores[key] = {c: float(r[c]) if r.get(c,"")!="" else None for c in AI_COLS}

    # Theory scores by (test_id, register)
    theory_val = {(r["test_id"], r["register"]): r for r in val_rows_theory}

    print("\n=== Validation: Baseline vs Theory corr ===")
    print(f"{'항목':12s} {'Baseline r':>12s} {'Theory r':>10s} {'개선':>8s}")
    print("-"*45)

    comparison = {}
    for col in AI_COLS:
        bt, ba, tt, ta = [], [], [], []
        for key, ta_scores in t_avg.items():
            tv = ta_scores.get(col)
            bv = baseline_scores.get(key, {}).get(col)
            tv2 = theory_val.get(key, {}).get(col)
            if tv and bv: bt.append(tv); ba.append(bv)
            if tv and tv2: tt.append(tv); ta.append(tv2)
        br = float(np.corrcoef(bt, ba)[0,1]) if len(bt)>=3 else None
        tr = float(np.corrcoef(tt, ta)[0,1]) if len(tt)>=3 else None
        delta = (tr - br) if (br and tr) else None
        b_s = f"{br:.3f}" if br else "  N/A"
        t_s = f"{tr:.3f}" if tr else "  N/A"
        d_s = f"{delta:+.3f}" if delta else "   N/A"
        winner = "↑" if (delta and delta > 0.02) else ("↓" if (delta and delta < -0.02) else "≈")
        print(f"  {col:10s}  {b_s:>11s}  {t_s:>9s}  {d_s:>7s} {winner}")
        comparison[col] = {"baseline_r": br, "theory_r": tr, "delta": delta}

    out2 = {"description": "Validation: baseline vs theory mapping comparison",
            "items": comparison}
    jp2 = os.path.join(RESULTS_DIR, "theory_validation_comparison.json")
    with open(jp2, "w", encoding="utf-8") as f:
        json.dump(out2, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {jp2}")
    return theory_mappings, theory_val

if __name__ == "__main__":
    main()
PYEOF