#!/usr/bin/env python3
"""
per_register_analysis.py — 음역대별(저/중/고) AI vs 트레이너 상관 분석
========================================================================
결과: results/per_register_correlation.json
시각화: figures/per_register_correlation.png
"""
import os
import csv
import json
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR    = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR  = os.path.join(VOCAL_DIR, "results")
FIGURES_DIR  = os.path.join(PROJECT_ROOT, "figures")

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FPROP   = fm.FontProperties(fname=FONT_PATH, size=10) if os.path.exists(FONT_PATH) else None
FPROP_T = fm.FontProperties(fname=FONT_PATH, size=12) if os.path.exists(FONT_PATH) else None
FPROP_S = fm.FontProperties(fname=FONT_PATH, size=8)  if os.path.exists(FONT_PATH) else None

ITEMS = ["비강사용", "흉성두성", "접촉강도", "호흡식별", "전방공명", "연구개위치", "상압하압"]
ITEM_LABELS = {
    "비강사용": "비강사용", "흉성두성": "흉성두성", "접촉강도": "접촉강도",
    "호흡식별": "호흡식별", "전방공명": "전방공명", "연구개위치": "연구개위치", "상압하압": "상압하압",
}
REGISTERS = ["저", "중", "고"]
EXCLUDE_PAIRS = {(6, 8)}


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pearson_corr(x, y):
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    if len(x) < 3 or np.std(x) < 1e-10 or np.std(y) < 1e-10:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def mae(x, y):
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    return float(np.mean(np.abs(x - y))) if len(x) > 0 else None


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Load AI scores and trainer scores
    ai_data = json.load(open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8"))
    ai_scores_list = ai_data["scores"]

    # Filter exclude pairs
    ai_scores_list = [
        s for s in ai_scores_list
        if (s["singer_id"], s["song_id"]) not in EXCLUDE_PAIRS
    ]

    # Organize by (item, register): [(trainer_avg, ai_score)]
    data = {item: {reg: {"trainer": [], "ai": []} for reg in REGISTERS + ["all"]}
            for item in ITEMS}

    for entry in ai_scores_list:
        singer = entry["singer_id"]
        song = entry["song_id"]
        register = entry["register"]

        if (singer, song) in EXCLUDE_PAIRS:
            continue
        if register not in REGISTERS:
            continue

        for item in ITEMS:
            t = entry["trainer_avg"].get(item)
            a = entry["ai_scores"].get(item)
            if t is None or a is None:
                continue
            data[item][register]["trainer"].append(t)
            data[item][register]["ai"].append(a)
            data[item]["all"]["trainer"].append(t)
            data[item]["all"]["ai"].append(a)

    # Compute correlations
    results = {}
    print(f"\n{'='*85}")
    print(f"{'항목':12s}| {'저음역 corr':>10s} {'저음역 n':>8s} | {'중음역 corr':>10s} {'중음역 n':>8s} | {'고음역 corr':>10s} {'고음역 n':>8s} | {'통합 corr':>10s}")
    print("-"*85)

    for item in ITEMS:
        row = {}
        parts = []
        for reg in REGISTERS + ["all"]:
            t_vals = data[item][reg]["trainer"]
            a_vals = data[item][reg]["ai"]
            corr = pearson_corr(t_vals, a_vals)
            mae_val = mae(t_vals, a_vals)
            row[reg] = {"corr": round(corr, 3) if corr else None,
                        "mae": round(mae_val, 3) if mae_val else None,
                        "n": len(t_vals)}
            if reg != "all":
                c_str = f"{corr:.3f}" if corr is not None else "  N/A"
                parts.append(f"{c_str:>10s} {len(t_vals):>8d}")
        results[item] = row
        all_corr = row["all"]["corr"]
        all_str = f"{all_corr:.3f}" if all_corr is not None else "   N/A"
        label = ITEM_LABELS.get(item, item)
        print(f"{label:12s}| {' | '.join(parts)} | {all_str:>10s}")

    print("="*85)

    # Save JSON
    out = {"description": "Per-register correlation: AI vs Trainer", "items": results}
    json_path = os.path.join(RESULTS_DIR, "per_register_correlation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")

    # Visualization
    n_items = len(ITEMS)
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(n_items)
    width = 0.22
    colors = {"저": "#4C9BE8", "중": "#56B26C", "고": "#E8774C", "all": "#888888"}
    labels_ko = {"저": "저음역", "중": "중음역", "고": "고음역", "all": "통합"}

    for i, reg in enumerate(["저", "중", "고", "all"]):
        corrs = []
        for item in ITEMS:
            c = results[item][reg]["corr"]
            corrs.append(c if c is not None else 0)
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, corrs, width, label=labels_ko[reg],
                      color=colors[reg], alpha=0.85)

    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(x)
    if FPROP:
        ax.set_xticklabels([ITEM_LABELS.get(it, it) for it in ITEMS], fontproperties=FPROP)
        ax.set_ylabel("Pearson 상관계수", fontproperties=FPROP)
        ax.set_title("AI vs 트레이너 상관계수 — 음역대별", fontproperties=FPROP_T)
        leg = ax.legend(prop=FPROP_S)
    else:
        ax.set_xticklabels(ITEMS)
        ax.set_ylabel("Pearson r")
        ax.set_title("AI vs Trainer Correlation by Register")
        ax.legend()

    ax.set_ylim(-0.5, 0.7)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, "per_register_correlation.png")
    fig.savefig(fig_path, dpi=300)
    plt.close()
    print(f"📊 Saved: {fig_path}")


if __name__ == "__main__":
    main()
