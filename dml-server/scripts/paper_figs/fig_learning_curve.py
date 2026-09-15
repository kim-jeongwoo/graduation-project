"""
fig_learning_curve.py — (c) exp20 progressive 학습 곡선
데이터: results/exp20_progressive/history.json (76 epochs, train/val corr)
        phase 경계: metrics.json phases (20 / 40 / 40 → 실제 76 = 20+40+16 early stop)
        체크포인트: epoch 61, val_corr 0.8218 (.claude/refs/experiments.md)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_BASE, C_MEAS, C_PRED, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
hist = json.load(open(ROOT / "results/exp20_progressive/history.json"))

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))

ep = range(1, len(hist["val_corr"]) + 1)
ax.plot(ep, hist["train_corr"], color=C_MEAS, label="Train corr")
ax.plot(ep, hist["val_corr"], color=C_PRED, label="Val corr")

# progressive phase 경계 (metrics.json: 20ep@4096, 40ep@8192, early-stop@16384)
for x in (20, 60):
    ax.axvline(x, color=C_BASE, linestyle="--", linewidth=0.7)
for x, lab in ((10, "4096"), (40, "8192"), (68, "16384")):
    ax.text(x, 0.575, lab, ha="center", va="bottom", fontsize=7, color="#404040")

# best checkpoint: epoch 61, val 0.8218
ax.plot(61, hist["val_corr"][60], marker="o", ms=3.5, mfc="none",
        mec="black", mew=0.8, linestyle="none", zorder=5)
ax.annotate("best (ep. 61)", xy=(61, hist["val_corr"][60]),
            xytext=(50, 0.86), fontsize=7,
            arrowprops=dict(arrowstyle="-", lw=0.6, color="black"))

ax.set_xlabel("Epoch")
ax.set_ylabel("Pearson correlation")
ax.set_xlim(0, 78)
ax.set_ylim(0.56, 0.9)
ax.legend(loc="lower right", frameon=True, edgecolor="black",
          fancybox=False, framealpha=1).get_frame().set_linewidth(0.6)

savefig(fig, "fig_learning_curve.png")
