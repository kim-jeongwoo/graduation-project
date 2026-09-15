"""
fig_speaker_ecdf.py — (b) 테스트 70화자 corr ECDF + 중앙값 점선
데이터: results/exp20_progressive/per_speaker_corr.csv (재계산: median 0.8532,
        >=0.7 90.0% — 문서 확정값과 일치 확인됨)
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from style import CM_W, C_BASE, C_MEAS, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "results/exp20_progressive/per_speaker_corr.csv"

vals = np.sort([float(r["corr"]) for r in csv.DictReader(open(CSV))])
n = len(vals)
med = float(np.median(vals))
ecdf = np.arange(1, n + 1) / n

apply_style()
fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))

ax.step(vals, ecdf, where="post", color=C_MEAS, linewidth=1.1)
ax.axvline(med, color=C_BASE, linestyle="--", linewidth=0.9)
ax.text(med - 0.008, 0.06, f"median = {med:.4f}", rotation=90,
        fontsize=7, ha="right", va="bottom", color="#404040")

ax.set_xlabel(f"Per-speaker correlation ($n$ = {n} test speakers)")
ax.set_ylabel("Cumulative proportion")
ax.set_ylim(0, 1.02)
savefig(fig, "fig_speaker_ecdf.png")
