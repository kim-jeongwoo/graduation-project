#!/usr/bin/env python3
"""vocal-fit 배포 아키텍처 — 포트폴리오용 화이트 · 컴팩트 스타일."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FP = FontProperties(fname=NOTO)


def fp(size, weight="normal"):
    f = FP.copy()
    f.set_size(size)
    f.set_weight(weight)
    return f


INK = "#141821"
MUTE = "#6B7383"
DIM = "#98A0AE"
LINE = "#E1E5EC"

STAGES = [
    dict(color="#3B6FF0", step="01", name="vocal-app", role="모바일 앱",
         tech="Expo · React Native", desc="녹음 · 업로드 · 결과 확인"),
    dict(color="#DB7712", step="02", name="Cloudflare", role="공개 엣지 · 터널",
         tech="HTTPS · WSS", desc="api · dml.vocal-fit.com"),
    dict(color="#0E8B7D", step="03", name="vocal-server", role="API 서버",
         tech="FastAPI · PostgreSQL", desc="인증 · 세션 · 결과 저장"),
    dict(color="#6E42C8", step="04", name="dml-server", role="AI 추론 서버",
         tech="PyTorch · RTX 5080", desc="EGG 추정 · 발성 점수 산출"),
]

FLOW = ["업로드", "라우팅", "분석 요청"]
RESULTS = ["호흡 소리 식별", "성대 접촉 강도", "연구개 위치", "혀 · 구강 경직도"]

fig, ax = plt.subplots(figsize=(13, 4.42))
ax.set_xlim(0, 100)
ax.set_ylim(0, 34)
ax.axis("off")
fig.patch.set_facecolor("white")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)


def text(x, y, s, size=11, color=INK, weight="normal", ha="center", va="center",
         zorder=5):
    return ax.text(x, y, s, fontproperties=fp(size, weight), color=color,
                   ha=ha, va=va, zorder=zorder, linespacing=1.45)


# ─────────────────────── 헤더 (좌측 정렬) ───────────────────────
ax.add_patch(FancyBboxPatch((0.3, 28.2), 0.55, 4.6,
                            boxstyle="round,pad=0,rounding_size=0.27",
                            linewidth=0, facecolor="#3B6FF0", zorder=3))
text(2.1, 31.5, "가창 발성 평가 시스템  ·  배포 아키텍처", 16, INK, "bold", ha="left")
text(2.1, 28.9, "사용자 음성 한 번의 업로드로 EGG를 추정하고 발성 점수를 돌려주는 4단 구성",
     9.6, MUTE, ha="left")
text(99.4, 31.2, "EfficientEGGNet", 10.5, "#6E42C8", "bold", ha="right")
text(99.4, 28.9, "Test Corr 0.8249", 9.6, MUTE, ha="right")

# ─────────────────────── 단계 카드 (내용에 밀착) ───────────────────────
CW, GAP, Y0, CH = 21.2, 4.9, 13.2, 12.0
xs = [0.3 + i * (CW + GAP) for i in range(4)]

for x, st in zip(xs, STAGES):
    cx, c = x + CW / 2, st["color"]
    ax.add_patch(FancyBboxPatch(
        (x, Y0), CW, CH, boxstyle="round,pad=0,rounding_size=0.8",
        linewidth=1.3, edgecolor=LINE, facecolor="#FFFFFF", zorder=2))
    # 컬러 헤더 칩
    ax.add_patch(FancyBboxPatch(
        (x + 0.75, Y0 + 8.15), CW - 1.5, 3.1,
        boxstyle="round,pad=0,rounding_size=0.6",
        linewidth=0, facecolor=c, zorder=3))
    text(x + 2.3, Y0 + 9.7, st["step"], 8.2, "#FFFFFF", "bold", ha="left")
    text(cx + 0.9, Y0 + 9.7, st["name"], 12.2, "#FFFFFF", "bold")

    text(cx, Y0 + 5.85, st["role"], 10.2, INK)
    text(cx, Y0 + 3.55, st["tech"], 9.2, MUTE)
    text(cx, Y0 + 1.5, st["desc"], 8.6, DIM)

# ─────────────────────── 단계 사이 화살표 ───────────────────────
for i, lab in enumerate(FLOW):
    x1, x2 = xs[i] + CW + 0.75, xs[i + 1] - 0.75
    ax.add_patch(FancyArrowPatch(
        (x1, Y0 + 6.2), (x2, Y0 + 6.2), arrowstyle="-|>", mutation_scale=14,
        linewidth=1.7, color="#A6AEBD", zorder=3))
    text((x1 + x2) / 2, Y0 + 8.1, lab, 8.4, MUTE)

# ─────────────────────── 결과 반환 경로 ───────────────────────
rx_from, rx_to, ry = xs[3] + CW / 2, xs[0] + CW / 2, 10.0
ax.plot([rx_from, rx_from, rx_to], [Y0, ry, ry], color="#C2C9D4", lw=1.5,
        linestyle=(0, (5, 3)), solid_capstyle="round", zorder=1)
ax.add_patch(FancyArrowPatch(
    (rx_to, ry), (rx_to, Y0 - 0.12), arrowstyle="-|>", mutation_scale=14,
    linewidth=1.5, color="#C2C9D4", zorder=1))
t = text(50, ry, "  분석 결과 반환  ", 8.4, DIM)
t.set_bbox(dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none"))

# ─────────────────────── 결과 항목 (한 줄 스트립) ───────────────────────
BX, BW, BY, BH = 0.3, 99.1, 1.6, 5.6
ax.add_patch(FancyBboxPatch(
    (BX, BY), BW, BH, boxstyle="round,pad=0,rounding_size=0.8",
    linewidth=1.3, edgecolor=LINE, facecolor="#F7F9FC", zorder=2))
text(BX + 2.4, BY + BH / 2, "OUTPUT", 8.4, "#6E42C8", "bold", ha="left")
ax.plot([BX + 12.5, BX + 12.5], [BY + 1.3, BY + BH - 1.3],
        color=LINE, lw=1.2, zorder=3)

start, span = 15.0, 82.0
for i, item in enumerate(RESULTS):
    cx = start + span * i / len(RESULTS)
    ax.scatter([cx], [BY + BH / 2], s=22, color=STAGES[3]["color"],
               zorder=5, linewidths=0)
    text(cx + 1.2, BY + BH / 2, item, 10.2, INK, "bold", ha="left")

out = Path("/home/dmlserver/projects/egg_prediction/docs/deployment_architecture.png")
fig.savefig(out, dpi=165, facecolor="white", bbox_inches="tight", pad_inches=0.1)
print("saved:", out)
