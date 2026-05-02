#!/usr/bin/env python3
"""
compare_scores.py — AI vs 트레이너 점수 일치도 분석
=====================================================
ai_scores.json vs trainer_scores.csv 비교:
  - 항목별 Pearson 상관계수
  - 항목별 MAE
  - ±1 정확도
  - 3구간 일치율

결과: data/vocal_academy/results/ai_vs_trainer.json
시각화: figures/ai_vs_trainer_*.png
"""
import os
import sys
import json
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(FONT_PATH):
    FPROP = fm.FontProperties(fname=FONT_PATH, size=11)
    FPROP_T = fm.FontProperties(fname=FONT_PATH, size=13)
    FPROP_S = fm.FontProperties(fname=FONT_PATH, size=9)
else:
    FPROP = FPROP_T = FPROP_S = None

ITEMS = ["비강사용", "흉성두성", "접촉강도", "호흡식별", "전방공명", "연구개위치", "상압하압"]
ITEM_LABELS = {
    "비강사용": "비강 사용",
    "흉성두성": "흉성/두성",
    "접촉강도": "접촉 강도",
    "호흡식별": "호흡 식별",
    "전방공명": "전방 공명",
    "연구개위치": "연구개 위치",
    "상압하압": "상압/하압",
}


def score_to_zone(s):
    if s is None:
        return None
    r = round(s)
    if r <= 1:
        return "insufficient"
    elif r <= 3:
        return "appropriate"
    else:
        return "excessive"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    with open(os.path.join(RESULTS_DIR, "ai_scores.json"), encoding="utf-8") as f:
        ai_data = json.load(f)

    scores_list = ai_data["scores"]
    print(f"Loaded {len(scores_list)} entries")

    # Collect paired data per item
    item_data = {col: {"trainer": [], "ai": []} for col in ITEMS}

    for entry in scores_list:
        for col in ITEMS:
            t = entry["trainer_avg"].get(col)
            a = entry["ai_scores"].get(col)
            if t is not None and a is not None:
                item_data[col]["trainer"].append(t)
                item_data[col]["ai"].append(a)

    # Compute metrics
    results = {}
    for col in ITEMS:
        t = np.array(item_data[col]["trainer"])
        a = np.array(item_data[col]["ai"])
        n = len(t)

        if n < 3:
            results[col] = {"n_pairs": n, "note": "too few pairs"}
            continue

        # Pearson correlation
        corr = np.corrcoef(t, a)[0, 1] if np.std(t) > 0 and np.std(a) > 0 else 0.0

        # MAE
        mae = np.mean(np.abs(t - a))

        # ±1 accuracy (rounded AI score within ±1 of rounded trainer score)
        t_round = np.round(t)
        a_round = np.round(a)
        within_1 = np.mean(np.abs(t_round - a_round) <= 1)

        # Zone agreement
        t_zones = [score_to_zone(v) for v in t]
        a_zones = [score_to_zone(v) for v in a]
        zone_agree = np.mean([tz == az for tz, az in zip(t_zones, a_zones)])

        results[col] = {
            "n_pairs": int(n),
            "pearson_corr": round(float(corr), 4),
            "mae": round(float(mae), 4),
            "accuracy_pm1": round(float(within_1), 4),
            "zone_agreement": round(float(zone_agree), 4),
            "trainer_mean": round(float(t.mean()), 3),
            "ai_mean": round(float(a.mean()), 3),
        }

        print(f"  {col:8s}: n={n:3d}, corr={corr:.3f}, MAE={mae:.2f}, "
              f"±1 acc={within_1:.1%}, zone={zone_agree:.1%}")

    # Save JSON
    output = {
        "description": "AI vs Trainer score comparison",
        "items": results,
    }
    json_path = os.path.join(RESULTS_DIR, "ai_vs_trainer.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")

    # ── Figure 1: Correlation bar chart ───────────────────────────
    valid_items = [c for c in ITEMS if results[c].get("pearson_corr") is not None]
    corrs = [results[c]["pearson_corr"] for c in valid_items]
    labels = [ITEM_LABELS.get(c, c) for c in valid_items]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2196F3" if c >= 0 else "#F44336" for c in corrs]
    bars = ax.barh(range(len(labels)), corrs, color=colors, edgecolor="white", height=0.6)

    ax.set_yticks(range(len(labels)))
    if FPROP:
        ax.set_yticklabels(labels, fontproperties=FPROP)
        ax.set_xlabel("Pearson Correlation", fontproperties=FPROP)
        ax.set_title("AI vs 트레이너 점수 상관계수", fontproperties=FPROP_T)
    else:
        ax.set_yticklabels(labels)
        ax.set_xlabel("Pearson Correlation")
        ax.set_title("AI vs Trainer Score Correlation")

    ax.axvline(x=0, color="gray", linewidth=0.5)
    ax.set_xlim(-1, 1)
    ax.grid(axis="x", alpha=0.3)

    for i, (bar, c) in enumerate(zip(bars, corrs)):
        ax.text(c + 0.02 if c >= 0 else c - 0.08, i, f"{c:.3f}",
                va="center", fontsize=9)

    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, "ai_vs_trainer_correlation.png")
    fig.savefig(fig_path, dpi=300)
    plt.close()
    print(f"📊 Saved: {fig_path}")

    # ── Figure 2: Scatter plots ───────────────────────────────────
    n_items = len(valid_items)
    n_cols = min(4, n_items)
    n_rows = (n_items + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
    if n_rows == 1 and n_cols == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes[np.newaxis, :]
    elif n_cols == 1:
        axes = axes[:, np.newaxis]

    for idx, col in enumerate(valid_items):
        r, c = divmod(idx, n_cols)
        ax = axes[r][c]

        t = np.array(item_data[col]["trainer"])
        a = np.array(item_data[col]["ai"])
        corr_val = results[col]["pearson_corr"]

        ax.scatter(t, a, alpha=0.5, s=30, c="#2196F3", edgecolors="white", linewidth=0.5)
        ax.plot([0, 5], [0, 5], "k--", alpha=0.3, linewidth=1)

        # Regression line
        if len(t) > 2 and np.std(t) > 0:
            m, b = np.polyfit(t, a, 1)
            x_line = np.linspace(0, 5, 50)
            ax.plot(x_line, m * x_line + b, "r-", alpha=0.5, linewidth=1)

        ax.set_xlim(-0.2, 5.2)
        ax.set_ylim(-0.2, 5.2)
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)

        label = ITEM_LABELS.get(col, col)
        if FPROP:
            ax.set_title(f"{label}\nr={corr_val:.3f}", fontproperties=FPROP_S)
            ax.set_xlabel("트레이너", fontproperties=FPROP_S)
            ax.set_ylabel("AI", fontproperties=FPROP_S)
        else:
            ax.set_title(f"{col}\nr={corr_val:.3f}", fontsize=9)
            ax.set_xlabel("Trainer", fontsize=8)
            ax.set_ylabel("AI", fontsize=8)

    # Hide unused axes
    for idx in range(n_items, n_rows * n_cols):
        r, c = divmod(idx, n_cols)
        axes[r][c].set_visible(False)

    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, "ai_vs_trainer_scatter.png")
    fig.savefig(fig_path, dpi=300)
    plt.close()
    print(f"📊 Saved: {fig_path}")

    # ── Figure 3: Accuracy summary table ──────────────────────────
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis("off")

    table_data = []
    col_labels = ["항목", "N", "상관계수", "MAE", "±1 정확도", "구간 일치"]
    for col in valid_items:
        r = results[col]
        table_data.append([
            ITEM_LABELS.get(col, col),
            str(r["n_pairs"]),
            f"{r['pearson_corr']:.3f}",
            f"{r['mae']:.2f}",
            f"{r['accuracy_pm1']:.1%}",
            f"{r['zone_agreement']:.1%}",
        ])

    table = ax.table(cellText=table_data, colLabels=col_labels,
                     loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    # Style header
    for j in range(len(col_labels)):
        cell = table[0, j]
        cell.set_facecolor("#2196F3")
        cell.set_text_props(color="white", weight="bold")
        if FPROP:
            cell.set_text_props(fontproperties=FPROP_S, color="white", weight="bold")

    # Style body with Korean font
    if FPROP:
        for i in range(len(table_data)):
            for j in range(len(col_labels)):
                table[i + 1, j].set_text_props(fontproperties=FPROP_S)

    if FPROP_T:
        ax.set_title("AI vs 트레이너 점수 비교 요약", fontproperties=FPROP_T, pad=20)
    else:
        ax.set_title("AI vs Trainer Score Comparison Summary", pad=20)

    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, "ai_vs_trainer_summary.png")
    fig.savefig(fig_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {fig_path}")


if __name__ == "__main__":
    main()
