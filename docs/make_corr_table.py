#!/usr/bin/env python3
"""항목별 상관 분석 — 포트폴리오 사이드 이미지용 2×2 카드 그리드 (520x500, 300dpi)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle

NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FP = FontProperties(fname=NOTO)

INK = "#141821"
MUTE = "#7A8290"
LINE = "#E3E7ED"
CARD_BG = "#FAFBFD"
OK = "#0B7A6E"
NO = "#C0392B"

# 출처: docs/research/40-rediag-selection-bias-2026-07.md §2-3
#   원p값     = p(단일모델 가정)  — 선택 편향 미보정
#   보정후p값 = p(배포모델)       — 21개 후보 중 최댓값 선택 반영
# 배치 순서: 좌상 → 우상 → 좌하 → 우하
ROWS = [
    ("성대 접촉 강도", "0.0014", "0.023", "유의", OK),
    ("혀 · 구강 경직도", "0.0019", "0.014", "유의", OK),
    ("연구개 위치", "0.0081", "0.054", "미확보", NO),
    ("호흡 소리 식별", "0.0015", "0.333", "미확보", NO),
]

W, H, DPI = 520, 500, 300
PX = 72 / DPI  # 픽셀 → 포인트

fig, ax = plt.subplots(figsize=(W / DPI, H / DPI), dpi=DPI)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor("white")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
fig.canvas.draw()
RD = fig.canvas.get_renderer()


def fp(px, weight="normal"):
    f = FP.copy()
    f.set_size(px * PX)
    f.set_weight(weight)
    return f


def draw(x, y, s, px, color=INK, weight="normal", ha="left"):
    """텍스트를 그리고 폭(px)을 돌려준다. 그림 좌표 1단위 = 1픽셀."""
    t = ax.text(x, y, s, fontproperties=fp(px, weight), color=color,
                ha=ha, va="center", zorder=6)
    return t.get_window_extent(RD).width


# ─────────── 제목 1줄 + 부제 2줄 ───────────
draw(14, 477, "항목별 상관 분석", 25, INK, "bold")
draw(14, 452, "n = 17  ·  후보 21개 중 val 최댓값 선택", 13.5, MUTE)
draw(14, 433, "permutation 10,000회로 선택 편향 보정", 13.5, MUTE)

# ─────────── 2×2 카드 그리드 ───────────
M, GAP = 10, 14                      # 바깥 여백, 카드 간격
CW = (W - 2 * M - GAP) / 2           # 카드 폭
GRID_TOP = 414
CH = (GRID_TOP - 12 - GAP) / 2       # 카드 높이
INSET = 21                           # 좌측 컬러바 뒤 텍스트 들여쓰기

for i, (item, raw, adj, verdict, color) in enumerate(ROWS):
    col, row = i % 2, i // 2
    left = M + col * (CW + GAP)
    top = GRID_TOP - row * (CH + GAP)
    bot = top - CH

    ax.add_patch(FancyBboxPatch(
        (left, bot), CW, CH, boxstyle="round,pad=0,rounding_size=8",
        linewidth=1.2, edgecolor=LINE, facecolor=CARD_BG, zorder=2))
    ax.add_patch(Rectangle((left, bot + 12), 5, CH - 24, facecolor=color,
                           zorder=4))

    tx = left + INSET

    # 1행 — 항목명
    draw(tx, top - 40, item, 20, INK, "bold")

    # 구분선
    ax.plot([tx, left + CW - 14], [top - 66, top - 66], color=LINE, lw=1.1,
            zorder=3)

    # 2행 — 원p값 → 보정후
    x = tx
    x += draw(x, top - 106, "원p값 ", 13, MUTE)
    x += draw(x, top - 106, raw, 16.5, INK)
    x += draw(x, top - 106, "  →  ", 13, MUTE)
    x += draw(x, top - 106, "보정후 ", 13, MUTE)
    x += draw(x, top - 106, adj, 16.5, color, "bold")
    if x > left + CW - 8:
        print(f"  ! 넘침 {item}: {x:.0f} > {left + CW - 8:.0f}")

    # 3행 — 판정 배지
    bx, by, bh = tx, top - 152, 28
    tw = draw(bx + 13, by, verdict, 14.5, color, "bold")
    for fc, a, z in ((color, 0.12, 4), ("none", 1.0, 5)):
        ax.add_patch(FancyBboxPatch(
            (bx, by - bh / 2), tw + 26, bh,
            boxstyle="round,pad=0,rounding_size=%.1f" % (bh / 2),
            linewidth=1.1, edgecolor=color, facecolor=fc, alpha=a, zorder=z))

out = Path("/home/dmlserver/projects/egg_prediction/docs/etc_성능_항목별corr표.png")
fig.savefig(out, dpi=DPI, facecolor="white")

# PDF 삽입 호환을 위해 알파 채널 제거 (RGBA -> RGB)
from PIL import Image
im = Image.open(out)
Image.alpha_composite(Image.new("RGBA", im.size, "white"), im.convert("RGBA")) \
     .convert("RGB").save(out, dpi=(DPI, DPI), optimize=True)
print("saved:", out, Image.open(out).size, Image.open(out).mode)
