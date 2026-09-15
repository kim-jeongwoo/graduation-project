"""
fig_cq_variants.py — (f) EGG 기반 CQ 변형별 corr vs acoustic 기준선
데이터: dml-server/results/sidetrack/egg_gate_contact_summary.csv (external17 행)
  acoustic(v2_pred) 0.7328 기준선, CQ 변형 6종 0.1167~0.5624
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_BASE, C_PRED, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "dml-server/results/sidetrack/egg_gate_contact_summary.csv"

LABELS = {                       # 논문용 영문 라벨 (약어: criterion-level / aggregate)
    "cq_sign_mean":  "sign, mean",
    "cq_sign_p90":   "sign, p90",
    "cq_thr25_mean": "25%, mean",
    "cq_thr25_p90":  "25%, p90",
    "cq_thr50_mean": "50%, mean",
    "cq_thr50_p90":  "50%, p90",
}

rows = {}
base = None
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["cohort"] != "external17":
            continue
        if r["predictor"] == "v2_pred":
            base = float(r["pearson_r"])
        elif r["predictor"] in LABELS:
            rows[r["predictor"]] = float(r["pearson_r"])

order = sorted(rows, key=rows.get)
vals = [rows[k] for k in order]

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))

ax.bar(range(len(order)), vals, width=0.62, color=C_PRED,
       edgecolor="black", linewidth=0.6)
ax.axhline(base, color=C_BASE, linestyle="--", linewidth=0.9)
ax.text(len(order) - 0.45, base + 0.012, f"acoustic baseline ({base:.3f})",
        ha="right", fontsize=7, color="#404040")

for x, v in enumerate(vals):
    ax.text(x, v + 0.012, f"{v:.3f}", ha="center", va="bottom", fontsize=7)

ax.set_xticks(range(len(order)))
ax.set_xticklabels([LABELS[k] for k in order], fontsize=7, rotation=20, ha="right")
ax.set_ylabel("Pearson correlation ($n$ = 17)")
ax.set_ylim(0, 0.82)
ax.grid(axis="x", visible=False)

savefig(fig, "fig_cq_variants.png")
