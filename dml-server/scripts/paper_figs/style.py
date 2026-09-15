"""
style.py — KSC 논문 그림 공통 스타일 (2단 조판 한 열 폭 규격)
==============================================================
규격: 폭 8.6cm, 300dpi, 흰 배경, 연회색 그리드, 검정 테두리 0.8pt,
      Times 계열(Nimbus Roman) 영문 전용, 축 라벨 8pt / 눈금 7pt / 범례 7pt.
색:   실측 파랑 C_MEAS, 추정 주황 C_PRED, 음수 상관 빨강 C_NEG, 기준선 회색 점선.
사용: from style import apply_style, savefig, CM_W, C_MEAS, ...
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CM = 1 / 2.54
CM_W = 8.6 * CM                # 2단 한 열 폭 (inch)
DPI = 300

C_MEAS = "#1f77b4"             # 실측 (파랑)
C_PRED = "#ff7f0e"             # 추정 (주황)
C_NEG = "#d62728"              # 음수 상관 (빨강)
C_BASE = "#7f7f7f"             # 기준선 (회색 점선용)
GRID = {"color": "#d9d9d9", "linewidth": 0.5}

FIG_DIR = Path(__file__).resolve().parents[2] / "figures" / "paper_figs"


def apply_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Nimbus Roman", "Liberation Serif", "STIXGeneral"],
        "mathtext.fontset": "stix",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": "black",
        "axes.linewidth": 0.8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.grid": True,
        "grid.color": GRID["color"],
        "grid.linewidth": GRID["linewidth"],
        "axes.axisbelow": True,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "lines.linewidth": 1.0,
    })


def savefig(fig, name: str):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / name
    fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.02)
    print(f"[saved] {out}")
    return out
