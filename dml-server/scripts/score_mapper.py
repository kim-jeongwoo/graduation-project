#!/usr/bin/env python3
"""
score_mapper.py — AI 지표를 0~5점 척도로 변환
================================================
트레이너 점수(trainer_scores.csv)를 ground truth로 사용하여,
AI 지표의 값 범위를 0~5 점수에 매핑하는 기준치를 데이터 기반으로 수립.

매핑 방법:
  1. 각 (singer, song, register) 조합에 대해 트레이너 5명 평균 점수 산출
  2. 해당 조합의 AI 지표값 추출
  3. 트레이너 평균 점수 구간별(0~5) AI 지표 분포를 분석
  4. 선형 보간 또는 분위수 기반으로 지표→점수 매핑 함수 생성

결과: data/vocal_academy/results/ai_scores.json
"""
import os
import sys
import json
import csv
import numpy as np
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")

# ── CSV column → evaluation_criteria item mapping ─────────────────
# CSV column name → (criteria_key, ai_source, analysis_json, data_key, register_key)
ITEM_MAP = {
    "비강사용": {
        "criteria_key": "1_nasal_oral_ratio",
        "analysis_file": "nasal_analysis.json",
        "extract_fn": "nasal_ratio",
    },
    "흉성두성": {
        "criteria_key": "2_chest_head_voice",
        "analysis_file": "egg_analysis.json",
        "extract_fn": "cq_mean",
    },
    "접촉강도": {
        "criteria_key": "3_vocal_fold_contact",
        "analysis_file": "egg_analysis.json",
        "extract_fn": "cq_peak",
    },
    "호흡식별": {
        "criteria_key": "4_breathiness",
        "analysis_file": "extra_metrics.json",
        "extract_fn": "cpp",  # CPP is better than HNR for breathiness (Maryn 2010)
    },
    "전방공명": {
        "criteria_key": "5_forward_resonance",
        "analysis_file": "extra_metrics.json",
        "extract_fn": "spectral_centroid",  # Higher centroid = more forward resonance
    },
    "연구개위치": {
        "criteria_key": "6_soft_palate",
        "analysis_file": "nasal_analysis.json",
        "extract_fn": "nasal_ratio",
    },
    "상압하압": {
        "criteria_key": "9_pressure_balance",
        "analysis_file": "spectral_analysis.json",
        "extract_fn": "spectral_tilt",
    },
}

REGISTER_MAP = {"저": "low", "중": "mid", "고": "high"}

# Pairs to exclude from score mapping (insufficient audio quality)
EXCLUDE_PAIRS = {(6, 8)}  # Singer 6 Song 8: nearly silent


# ── Load analysis data ────────────────────────────────────────────
def load_analysis_data():
    data = {}
    for fname in ["egg_analysis.json", "nasal_analysis.json",
                  "spectral_analysis.json", "extra_metrics.json"]:
        path = os.path.join(RESULTS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            data[fname] = json.load(f)
    return data


def get_ai_value(analysis_data, item_info, singer_id, song_id, register):
    """Extract AI indicator value for a specific (singer, song, register)."""
    fname = item_info["analysis_file"]
    extract_fn = item_info["extract_fn"]
    reg_en = REGISTER_MAP.get(register, register)

    results = analysis_data[fname].get("results", [])

    # Find matching result
    for r in results:
        if r["singer_id"] == singer_id and r["song_id"] == song_id:
            if extract_fn == "nasal_ratio":
                reg_data = r.get("nasal_ratio_by_register", {}).get(reg_en, {})
                return reg_data.get("mean")
            elif extract_fn == "cq_mean":
                reg_data = r.get("cq_by_register", {}).get(reg_en, {})
                return reg_data.get("mean")
            elif extract_fn == "cq_peak":
                reg_data = r.get("cq_by_register", {}).get(reg_en, {})
                return reg_data.get("peak")
            elif extract_fn == "hnr":
                reg_data = r.get("hnr", {}).get(reg_en, {})
                return reg_data.get("mean")
            elif extract_fn == "singers_formant":
                reg_data = r.get("singers_formant_ratio", {}).get(reg_en, {})
                return reg_data.get("mean")
            elif extract_fn == "spectral_tilt":
                reg_data = r.get("spectral_tilt", {}).get(reg_en, {})
                return reg_data.get("mean")
            elif extract_fn == "cpp":
                # extra_metrics: per-file (not per-register) — use global value
                return r.get("cpp", {}).get("mean")
            elif extract_fn == "spectral_centroid":
                return r.get("spectral_centroid", {}).get("mean")
    return None


# ── Load trainer scores ───────────────────────────────────────────
def load_trainer_scores():
    """Load CSV, compute 5-rater average per (singer, song, register)."""
    path = os.path.join(VOCAL_DIR, "trainer_scores.csv")
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Clean column names (strip whitespace)
    score_cols = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
                  "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

    # Group by (singer, song, register) — skip excluded pairs
    # Stage2 rows may have empty song → use 0
    groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        song_raw = r.get("song", "").strip()
        song_id = int(song_raw) if song_raw.isdigit() else 0
        key = (int(r["singer"]), song_id, r["register"].strip())
        if (key[0], key[1]) in EXCLUDE_PAIRS:
            continue
        for col in score_cols:
            val = r.get(col, "").strip()
            if not val:
                # Try with stripped key
                val = r.get(col.strip(), "").strip()
            if val:
                groups[key][col].append(int(val))

    # Compute averages
    averages = {}
    for key, scores_dict in groups.items():
        averages[key] = {}
        for col in score_cols:
            vals = scores_dict.get(col, [])
            averages[key][col] = np.mean(vals) if vals else None
    return averages


# ── Build mapping: data-driven thresholds ─────────────────────────
def build_score_mapping(trainer_avgs, analysis_data):
    """
    For each AI item, collect (trainer_avg_score, ai_indicator_value) pairs,
    then derive a linear mapping from indicator → 0~5 score.
    
    Strategy: 
      - Collect all paired data points
      - Fit linear regression: ai_value = a * trainer_score + b
      - Invert: ai_score = (ai_value - b) / a, clipped to [0, 5]
      - If correlation is very low, fall back to percentile-based mapping
    """
    mappings = {}

    for csv_col, item_info in ITEM_MAP.items():
        pairs = []  # (trainer_score, ai_value)

        for (singer, song, register), trainer_scores in trainer_avgs.items():
            t_score = trainer_scores.get(csv_col)
            if t_score is None:
                continue
            ai_val = get_ai_value(analysis_data, item_info, singer, song, register)
            if ai_val is None:
                continue
            pairs.append((t_score, ai_val))

        if len(pairs) < 5:
            print(f"  {csv_col}: Too few pairs ({len(pairs)}), skipping")
            mappings[csv_col] = {"method": "skip", "n_pairs": len(pairs)}
            continue

        t_scores = np.array([p[0] for p in pairs])
        ai_vals = np.array([p[1] for p in pairs])

        # Pearson correlation
        corr = np.corrcoef(t_scores, ai_vals)[0, 1] if np.std(ai_vals) > 1e-10 else 0.0

        # Linear regression: ai_val = slope * t_score + intercept
        if np.std(t_scores) > 1e-10:
            slope, intercept = np.polyfit(t_scores, ai_vals, 1)
        else:
            slope, intercept = 0, np.mean(ai_vals)

        # Percentile-based mapping as fallback/complement
        # Map score 0→p5, 1→p20, 2→p40, 3→p60, 4→p80, 5→p95
        percentile_thresholds = {}
        for score in range(6):
            mask = np.abs(t_scores - score) <= 0.5
            if mask.sum() > 0:
                percentile_thresholds[score] = float(np.median(ai_vals[mask]))

        # Fill gaps with linear interpolation
        known_scores = sorted(percentile_thresholds.keys())
        if len(known_scores) >= 2:
            for s in range(6):
                if s not in percentile_thresholds:
                    # Interpolate from nearest known
                    lower = max([k for k in known_scores if k <= s], default=known_scores[0])
                    upper = min([k for k in known_scores if k >= s], default=known_scores[-1])
                    if lower == upper:
                        percentile_thresholds[s] = percentile_thresholds[lower]
                    else:
                        frac = (s - lower) / (upper - lower)
                        percentile_thresholds[s] = (
                            percentile_thresholds[lower] * (1 - frac)
                            + percentile_thresholds[upper] * frac
                        )

        mappings[csv_col] = {
            "method": "linear" if abs(corr) > 0.2 else "percentile",
            "n_pairs": len(pairs),
            "correlation": float(corr),
            "linear": {"slope": float(slope), "intercept": float(intercept)},
            "thresholds": {str(k): float(v) for k, v in sorted(percentile_thresholds.items())},
            "ai_range": {"min": float(ai_vals.min()), "max": float(ai_vals.max()),
                         "mean": float(ai_vals.mean()), "std": float(ai_vals.std())},
            "trainer_range": {"min": float(t_scores.min()), "max": float(t_scores.max()),
                              "mean": float(t_scores.mean())},
        }

        print(f"  {csv_col}: n={len(pairs)}, corr={corr:.3f}, "
              f"method={'linear' if abs(corr) > 0.2 else 'percentile'}, "
              f"slope={slope:.4f}")

    return mappings


def apply_mapping(ai_val, mapping_info):
    """Convert an AI indicator value to 0~5 score using the mapping."""
    if ai_val is None or mapping_info.get("method") == "skip":
        return None

    thresholds = mapping_info.get("thresholds", {})
    if not thresholds:
        return None

    # Find the closest score by interpolating between threshold values
    scores = sorted(int(k) for k in thresholds.keys())
    vals = [thresholds[str(s)] for s in scores]

    # Check if the mapping is monotonically increasing or decreasing
    if len(vals) >= 2:
        increasing = vals[-1] > vals[0]
    else:
        return float(scores[0])

    # Interpolate: find where ai_val falls
    if increasing:
        if ai_val <= vals[0]:
            return float(scores[0])
        if ai_val >= vals[-1]:
            return float(scores[-1])
        for i in range(len(vals) - 1):
            if vals[i] <= ai_val <= vals[i + 1]:
                frac = (ai_val - vals[i]) / (vals[i + 1] - vals[i] + 1e-10)
                return float(scores[i] + frac * (scores[i + 1] - scores[i]))
    else:  # decreasing
        if ai_val >= vals[0]:
            return float(scores[0])
        if ai_val <= vals[-1]:
            return float(scores[-1])
        for i in range(len(vals) - 1):
            if vals[i] >= ai_val >= vals[i + 1]:
                frac = (vals[i] - ai_val) / (vals[i] - vals[i + 1] + 1e-10)
                return float(scores[i] + frac * (scores[i + 1] - scores[i]))

    # Fallback: nearest neighbor
    diffs = [abs(ai_val - v) for v in vals]
    return float(scores[np.argmin(diffs)])


# ── Main ──────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading data...")
    analysis_data = load_analysis_data()
    trainer_avgs = load_trainer_scores()
    print(f"  Trainer combos: {len(trainer_avgs)}")

    print("\nBuilding score mappings...")
    mappings = build_score_mapping(trainer_avgs, analysis_data)

    print("\nApplying mappings to all recordings...")
    all_scores = []

    # For each (singer, song, register) in trainer data
    for (singer, song, register), trainer_scores in sorted(trainer_avgs.items()):
        entry = {
            "singer_id": singer,
            "song_id": song,
            "register": register,
            "trainer_avg": {},
            "ai_scores": {},
            "ai_raw_values": {},
        }

        for csv_col, item_info in ITEM_MAP.items():
            # Trainer average
            t_avg = trainer_scores.get(csv_col)
            entry["trainer_avg"][csv_col] = round(t_avg, 2) if t_avg is not None else None

            # AI raw value
            ai_val = get_ai_value(analysis_data, item_info, singer, song, register)
            entry["ai_raw_values"][csv_col] = round(ai_val, 4) if ai_val is not None else None

            # AI score (mapped)
            if ai_val is not None and csv_col in mappings:
                ai_score = apply_mapping(ai_val, mappings[csv_col])
                entry["ai_scores"][csv_col] = round(ai_score, 2) if ai_score is not None else None
            else:
                entry["ai_scores"][csv_col] = None

        # Also include non-AI items as None
        for col in ["공명개방", "혀경직도"]:
            entry["trainer_avg"][col] = round(trainer_scores.get(col, 0), 2) if trainer_scores.get(col) else None
            entry["ai_scores"][col] = None
            entry["ai_raw_values"][col] = None

        all_scores.append(entry)

    # Summary stats
    n_total = len(all_scores)
    n_with_ai = sum(1 for e in all_scores if any(v is not None for v in e["ai_scores"].values()))

    output = {
        "description": "AI indicator → 0~5 score mapping results",
        "mappings": mappings,
        "n_entries": n_total,
        "n_with_ai_scores": n_with_ai,
        "scores": all_scores,
    }

    json_path = os.path.join(RESULTS_DIR, "ai_scores.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved: {json_path}")
    print(f"   {n_total} entries, {n_with_ai} with AI scores")

    # Print mapping summary
    print("\n=== Mapping Summary ===")
    for col, m in mappings.items():
        if m.get("method") == "skip":
            print(f"  {col}: SKIPPED (too few pairs)")
        else:
            print(f"  {col}: corr={m['correlation']:.3f}, method={m['method']}, "
                  f"n={m['n_pairs']}")


if __name__ == "__main__":
    main()
