"""
fig_item_forest.py — (g 대체) v2 표시 4항목 forest plot (r + 95% CI)
데이터: score_mapper_v2_predictions_21.csv external17 재계산
        (score_mapper_v2_validation.csv val_total_corr와 ±0.0001 일치 검증됨)
CI: Fisher z 변환 — z = atanh(r), SE = 1/sqrt(n-3),
    CI = tanh(z ± 1.96/sqrt(n-3)).  n=17 → SE=1/sqrt(14).
"""
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_MEAS, C_NEG, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv"

EN = {
    "접촉강도": "Vocal fold contact",
    "혀경직도": "Tongue tension",
    "호흡식별": "Breathiness",
    "연구개위치": "Soft palate position",
}

data: dict[str, list] = {}
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["item"] in EN and r["is_leaked"] == "False":
            data.setdefault(r["item"], []).append(
                (float(r["evaluator_avg"]), float(r["predicted_score"])))

order = ["접촉강도", "혀경직도", "호흡식별", "연구개위치"]  # 위→아래
stats = []
for item in order:
    a = np.array([p[0] for p in data[item]])
    b = np.array([p[1] for p in data[item]])
    n = len(a)
    r = float(np.corrcoef(a, b)[0, 1])
    z = math.atanh(r)                      # Fisher z
    se = 1 / math.sqrt(n - 3)
    lo, hi = math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)
    stats.append((item, r, lo, hi, n))

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.58))

ys = np.arange(len(stats))[::-1]  # 첫 항목이 맨 위
for y, (item, r, lo, hi, n) in zip(ys, stats):
    col = C_NEG if r < 0 else C_MEAS
    ax.plot([lo, hi], [y, y], color=col, linewidth=1.2, solid_capstyle="butt")
    ax.plot([lo, lo], [y - 0.12, y + 0.12], color=col, linewidth=1.0)
    ax.plot([hi, hi], [y - 0.12, y + 0.12], color=col, linewidth=1.0)
    ax.plot(r, y, marker="o", ms=4, color=col, mec="black", mew=0.4)
    ax.text(1.02, y, f"{r:+.3f}", fontsize=7, va="center", ha="left")

ax.axvline(0, color="#7f7f7f", linestyle="--", linewidth=0.8)
ax.set_yticks(ys)
ax.set_yticklabels([EN[s[0]] for s in stats], fontsize=7.5)
ax.set_xlabel("Pearson correlation with trainer rating ($n$ = 17, 95% CI)")
ax.set_xlim(-1.0, 1.0)
ax.set_ylim(-0.5, len(stats) - 0.3)
ax.grid(axis="y", visible=False)

savefig(fig, "fig_item_forest.png")
