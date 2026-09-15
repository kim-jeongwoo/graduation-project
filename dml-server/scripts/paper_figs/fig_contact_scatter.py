"""
fig_contact_scatter.py — (e) 성대 접촉 강도: 시스템 점수 vs 트레이너 평가 산점도
데이터: data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv
  external17 (is_leaked=False), item=접촉강도, predicted_score vs evaluator_avg
  r=0.7328 (p=.0008) — mapping_params_v2.json val_total 0.7327과 동일 정의
"""
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_BASE, C_MEAS, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "data/vocal_academy/results/sidetrack/score_mapper_v2_predictions_21.csv"

xs, ys = [], []
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["item"] == "접촉강도" and r["is_leaked"] == "False":
            xs.append(float(r["evaluator_avg"]))
            ys.append(float(r["predicted_score"]))
xs, ys = np.array(xs), np.array(ys)
r = float(np.corrcoef(xs, ys)[0, 1])
n = len(xs)

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.8))

# 회귀선 + 95% 신뢰대역 (평균 예측 CI: y_hat ± t(0.975,n-2)·s·sqrt(1/n+(x-x̄)²/Sxx))
b1, b0 = np.polyfit(xs, ys, 1)
gx = np.linspace(1.0, 3.8, 100)
gy = b1 * gx + b0
resid = ys - (b1 * xs + b0)
s = math.sqrt(float(resid @ resid) / (n - 2))
sxx = float(((xs - xs.mean()) ** 2).sum())
t975 = 2.131  # t(0.975, df=15)
half = t975 * s * np.sqrt(1 / n + (gx - xs.mean()) ** 2 / sxx)
ax.fill_between(gx, gy - half, gy + half, color="#bfbfbf", alpha=0.35,
                linewidth=0, zorder=1)
ax.plot(gx, gy, color=C_BASE, linestyle="--", linewidth=0.9, zorder=2)
ax.scatter(xs, ys, s=14, facecolor=C_MEAS, edgecolor="black",
           linewidth=0.4, zorder=3)

ax.text(0.04, 0.94, f"$r$ = {r:.3f} ($n$ = {n}, $p$ < .001)",
        transform=ax.transAxes, fontsize=7.5, va="top")

ax.set_xlabel("Trainer rating (mean of 5 raters $\\times$ 3 registers)")
ax.set_ylabel("System score (vocal fold contact)")
ax.set_xlim(1.0, 3.8)
ax.set_ylim(1.3, 3.5)

savefig(fig, "fig_contact_scatter.png")
