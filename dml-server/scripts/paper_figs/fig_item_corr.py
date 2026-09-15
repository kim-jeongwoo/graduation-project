"""
fig_item_corr.py — (g) v2 표시 4항목 external17 corr 막대 (음수 빨강)
데이터: data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv 재계산값
  (score_mapper_v2_validation.csv val_total_corr와 ±0.0001 일치 교차검증됨)
  접촉강도 +0.7328 / 혀경직도 +0.6937 / 호흡식별 +0.4342 / 연구개위치 -0.6237
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_MEAS, C_NEG, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv"

EN = {  # 평가 기준표 원문 항목의 영문 표기 (논문 표기와 통일할 것)
    "접촉강도": "Vocal fold\ncontact",
    "혀경직도": "Tongue\ntension",
    "호흡식별": "Breathiness",
    "연구개위치": "Soft palate\nposition",
}

vals = {}
data = {}
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["item"] in EN and r["is_leaked"] == "False":
            data.setdefault(r["item"], []).append(
                (float(r["evaluator_avg"]), float(r["predicted_score"])))
for item, pairs in data.items():
    a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
    vals[item] = float(np.corrcoef(a, b)[0, 1])

order = ["접촉강도", "혀경직도", "호흡식별", "연구개위치"]

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))

xs = range(len(order))
vs = [vals[k] for k in order]
colors = [C_NEG if v < 0 else C_MEAS for v in vs]
ax.bar(xs, vs, width=0.58, color=colors, edgecolor="black", linewidth=0.6)
ax.axhline(0, color="black", linewidth=0.8)

for x, v in zip(xs, vs):
    off = 0.03 if v >= 0 else -0.03
    va = "bottom" if v >= 0 else "top"
    ax.text(x, v + off, f"{v:+.3f}", ha="center", va=va, fontsize=7)

ax.set_xticks(list(xs))
ax.set_xticklabels([EN[k] for k in order], fontsize=7)
ax.set_ylabel("Pearson correlation ($n$ = 17)")
ax.set_ylim(-0.8, 0.9)
ax.grid(axis="x", visible=False)

savefig(fig, "fig_item_corr.png")
