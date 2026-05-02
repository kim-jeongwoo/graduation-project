#!/usr/bin/env python3
"""
i4_validation_compare.py
AI scores vs trainer scores for test_01~11.
"""
import os, csv, json
import numpy as np
from scipy import stats as scipy_stats
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures")

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FPROP   = fm.FontProperties(fname=FONT_PATH, size=10) if os.path.exists(FONT_PATH) else None
FPROP_T = fm.FontProperties(fname=FONT_PATH, size=12) if os.path.exists(FONT_PATH) else None
FPROP_S = fm.FontProperties(fname=FONT_PATH, size=8)  if os.path.exists(FONT_PATH) else None

SCORE_COLS  = ['비강사용','흉성두성','접촉강도','호흡식별','전방공명','연구개위치','공명개방','혀경직도','상압하압']
AI_COLS     = ['흉성두성','접촉강도','호흡식별','전방공명','상압하압']  # has AI scores
NO_AI_COLS  = ['비강사용','연구개위치','공명개방','혀경직도']
REGISTERS   = ["low", "mid", "high"]
REG_KO      = {"low": "저", "mid": "중", "high": "고"}
LABELS      = {"흉성두성":"흉성두성","접촉강도":"접촉강도","호흡식별":"호흡식별","전방공명":"전방공명","상압하압":"상압하압"}


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def zone(score):
    if score is None: return None
    s = round(float(score))
    if s <= 1: return "insufficient"
    elif s <= 3: return "appropriate"
    else: return "excessive"


def compute_metrics(trainer, ai):
    """Compute comparison metrics for paired lists."""
    ta = np.array(trainer, dtype=float); aa = np.array(ai, dtype=float)
    n = len(ta)
    if n < 3: return None

    # Pearson
    r, p = scipy_stats.pearsonr(ta, aa)
    # CI via Fisher z
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    ci_lo = float(np.tanh(z - 1.96 * se)); ci_hi = float(np.tanh(z + 1.96 * se))

    # Spearman
    rho, _ = scipy_stats.spearmanr(ta, aa)

    # MAE
    mae = float(np.mean(np.abs(ta - aa)))

    # ±1 accuracy
    pm1 = float(np.mean(np.abs(np.round(ta) - np.round(aa)) <= 1))

    # Zone agreement
    tz = [zone(v) for v in trainer]; az = [zone(v) for v in ai]
    zone_acc = float(np.mean([a == b for a, b in zip(tz, az)]))

    return {
        "n": n,
        "pearson_r": round(r, 4),
        "pearson_ci": (round(ci_lo, 4), round(ci_hi, 4)),
        "pearson_p": round(p, 4),
        "spearman_rho": round(float(rho), 4),
        "mae": round(mae, 4),
        "accuracy_pm1": round(pm1, 4),
        "zone_agreement": round(zone_acc, 4),
    }


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Load data
    trainer_rows = load_csv(os.path.join(VOCAL_DIR, "trainer_scores_validation.csv"))
    ai_rows = load_csv(os.path.join(RESULTS_DIR, "validation_ai_scores.csv"))

    # Build trainer avg by (test_id, register)
    t_groups = defaultdict(lambda: defaultdict(list))
    for r in trainer_rows:
        key = (r["test_id"], r["register"])
        for col in SCORE_COLS:
            v = r.get(col, "")
            if v.lstrip("-").isdigit():
                t_groups[key][col].append(float(v))
    t_avg = {k: {c: float(np.mean(v)) for c, v in d.items()} for k, d in t_groups.items()}

    # Build AI scores by (test_id, register)
    a_scores = {}
    for r in ai_rows:
        key = (r["test_id"], r["register"])
        a_scores[key] = {c: float(r[c]) if r.get(c, "") != "" else None for c in SCORE_COLS}

    # Collect all pairs
    combined_t = {col: {"all": [], "low": [], "mid": [], "high": []} for col in AI_COLS}
    combined_a = {col: {"all": [], "low": [], "mid": [], "high": []} for col in AI_COLS}

    for (test_id, reg), ta in t_avg.items():
        aa = a_scores.get((test_id, reg), {})
        for col in AI_COLS:
            tv = ta.get(col); av = aa.get(col)
            if tv is None or av is None: continue
            combined_t[col]["all"].append(tv); combined_a[col]["all"].append(av)
            combined_t[col][reg].append(tv); combined_a[col][reg].append(av)

    # Compute metrics
    results = {}
    print("\n=== Overall (저+중+고) ===")
    print(f"{'항목':12s} {'n':>4s} {'Pearson':>9s} {'95% CI':>20s} {'p':>7s} {'MAE':>6s} {'±1 acc':>8s} {'Zone':>7s}")
    print("-" * 80)
    for col in AI_COLS:
        m = compute_metrics(combined_t[col]["all"], combined_a[col]["all"])
        if m is None: continue
        results[col] = {"overall": m, "by_register": {}}
        ci = m["pearson_ci"]
        sig = "**" if m["pearson_p"] < 0.01 else ("*" if m["pearson_p"] < 0.05 else "")
        lbl = LABELS.get(col, col)
        print(f"{lbl:12s} {m['n']:>4d} {m['pearson_r']:>8.3f}{sig} "
              f"[{ci[0]:.3f},{ci[1]:.3f}]  {m['pearson_p']:>7.4f}  "
              f"{m['mae']:>5.2f}  {m['accuracy_pm1']:>7.1%}  {m['zone_agreement']:>6.1%}")

        for reg in REGISTERS:
            m_reg = compute_metrics(combined_t[col][reg], combined_a[col][reg])
            results[col]["by_register"][reg] = m_reg

    print("\n=== By Register ===")
    print(f"{'항목':12s} {'저음역':>10s} {'중음역':>10s} {'고음역':>10s}")
    print("-"*45)
    for col in AI_COLS:
        parts = []
        for reg in REGISTERS:
            m_r = results.get(col, {}).get("by_register", {}).get(reg)
            parts.append(f"{m_r['pearson_r']:>8.3f}" if m_r else "      N/A")
        lbl = LABELS.get(col, col)
        print(f"{lbl:12s} {' '.join(parts)}")

    # Save JSON
    out_j = os.path.join(RESULTS_DIR, "validation_comparison.json")
    with open(out_j, "w", encoding="utf-8") as f:
        json.dump({"description": "AI vs Trainer comparison on validation set",
                   "n_items": len(AI_COLS), "items": results}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {out_j}")

    # ── Figure 1: Correlation bars with CI ─────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(AI_COLS))
    r_vals = [results[c]["overall"]["pearson_r"] for c in AI_COLS]
    ci_lo  = [results[c]["overall"]["pearson_ci"][0] for c in AI_COLS]
    ci_hi  = [results[c]["overall"]["pearson_ci"][1] for c in AI_COLS]
    yerr_lo = [max(0, r - lo) for r, lo in zip(r_vals, ci_lo)]
    yerr_hi = [max(0, hi - r) for r, hi in zip(r_vals, ci_hi)]
    colors = ["#3498db" if r > 0 else "#e74c3c" for r in r_vals]
    ax.bar(x, r_vals, color=colors, alpha=0.85, width=0.6,
           yerr=[yerr_lo, yerr_hi], capsize=5, error_kw={"elinewidth": 1.5})
    ax.axhline(0, color="gray", linewidth=0.7)
    ax.set_xticks(x)
    xlabels = [LABELS.get(c, c) for c in AI_COLS]
    if FPROP:
        ax.set_xticklabels(xlabels, fontproperties=FPROP)
        ax.set_title("검증용 AI vs 트레이너 상관계수 (95% CI)", fontproperties=FPROP_T)
        ax.set_ylabel("Pearson r", fontproperties=FPROP)
    else:
        ax.set_xticklabels(xlabels); ax.set_title("Validation: AI vs Trainer Correlation")
    ax.set_ylim(-0.5, 1.0); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "validation_correlation_bars.png"), dpi=300)
    plt.close()
    print(f"📊 validation_correlation_bars.png")

    # ── Figure 2: Scatter plots ──────────────────────────────────
    n_ai = len(AI_COLS)
    fig, axes = plt.subplots(1, n_ai, figsize=(4 * n_ai, 4))
    if n_ai == 1: axes = [axes]
    for ax, col in zip(axes, AI_COLS):
        ta = combined_t[col]["all"]; aa = combined_a[col]["all"]
        ax.scatter(ta, aa, alpha=0.6, s=40, c="#3498db", edgecolors="white")
        ax.plot([0,5],[0,5],"k--",alpha=0.3)
        if len(ta) > 2:
            m, b = np.polyfit(ta, aa, 1)
            xl = np.linspace(0, 5, 50)
            ax.plot(xl, m*xl+b, "r-", alpha=0.5)
        ax.set_xlim(-0.2,5.2); ax.set_ylim(-0.2,5.2); ax.set_aspect("equal"); ax.grid(alpha=0.2)
        r_v = results.get(col,{}).get("overall",{}).get("pearson_r",0)
        lbl = LABELS.get(col, col)
        if FPROP:
            ax.set_title(f"{lbl}\nr={r_v:.3f}", fontproperties=FPROP_S)
            ax.set_xlabel("트레이너", fontproperties=FPROP_S)
            ax.set_ylabel("AI", fontproperties=FPROP_S)
        else:
            ax.set_title(f"{col}\nr={r_v:.3f}")
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "validation_scatter.png"), dpi=300)
    plt.close()
    print(f"📊 validation_scatter.png")

    # ── Figure 3: Per-register correlation ──────────────────────
    n_ai = len(AI_COLS)
    x = np.arange(n_ai); w = 0.26
    colors_reg = {"low":"#4C9BE8","mid":"#56B26C","high":"#E8774C"}
    reg_labels  = {"low":"저","mid":"중","high":"고"}
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, reg in enumerate(REGISTERS):
        rv = [results.get(c,{}).get("by_register",{}).get(reg,{}) or {} for c in AI_COLS]
        rvals = [r.get("pearson_r", 0) or 0 for r in rv]
        ax.bar(x + (i-1)*w, rvals, w, label=reg_labels[reg], color=colors_reg[reg], alpha=0.85)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.set_xticks(x)
    if FPROP:
        ax.set_xticklabels(xlabels, fontproperties=FPROP)
        ax.set_title("검증용 음역대별 AI vs 트레이너 상관계수", fontproperties=FPROP_T)
        ax.legend(prop=FPROP_S)
    else:
        ax.set_xticklabels(AI_COLS); ax.legend()
    ax.set_ylim(-0.7, 1.0); ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "validation_per_register.png"), dpi=300)
    plt.close()
    print(f"📊 validation_per_register.png")


if __name__ == "__main__":
    main()
