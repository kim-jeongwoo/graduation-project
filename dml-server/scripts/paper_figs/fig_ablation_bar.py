"""
fig_ablation_bar.py — (d) ablation 4단계 Test Corr
데이터(확정값): .claude/refs/experiments.md 성공 실험 표 / EXPERIMENT_REPORT.md
  Baseline 0.6662 / Exp3 0.7163 / Exp11 0.7484 / Exp20 0.8249
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_MEAS, C_PRED, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

STAGES = [
    ("Baseline\nWaveNet\n12 ms", 0.6662),
    ("Exp3\nnon-causal\n256 ms", 0.7163),
    ("Exp11\n5.99M\n512 ms", 0.7484),
    ("Exp20\nprogressive\n1024 ms", 0.8249),
]

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))

xs = range(len(STAGES))
vals = [v for _, v in STAGES]
colors = [C_MEAS] * 3 + [C_PRED]      # 최종 모델만 주황 강조
bars = ax.bar(xs, vals, width=0.62, color=colors, edgecolor="black", linewidth=0.6)

for x, v in zip(xs, vals):
    ax.text(x, v + 0.004, f"{v:.4f}", ha="center", va="bottom", fontsize=7)

ax.set_xticks(list(xs))
ax.set_xticklabels([n for n, _ in STAGES], fontsize=6.5)
ax.set_ylabel("Test correlation")
ax.set_ylim(0.60, 0.86)
ax.grid(axis="x", visible=False)

savefig(fig, "fig_ablation_bar.png")
