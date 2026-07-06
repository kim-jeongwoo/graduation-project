#!/usr/bin/env python3
"""
visualize_matching_diagnosis.py — score_mapper 매칭 방식 진단 결과 시각화

출력:
  dml-server/results/sidetrack/matching_diagnosis_bars.png   (grouped bar)
  dml-server/results/sidetrack/matching_diagnosis_heatmap.png (heatmap)
  dml-server/results/sidetrack/matching_diagnosis_focus.png   (흉성두성 집중)

실행:
  conda activate EGGDML
  cd ~/projects/egg_prediction
  python dml-server/scripts/sidetrack/visualize_matching_diagnosis.py
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VDIR  = PROJECT_ROOT / "data" / "vocal_academy"
RDIR  = VDIR / "results"
OUT   = PROJECT_ROOT / "dml-server" / "results" / "sidetrack"
OUT.mkdir(parents=True, exist_ok=True)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_font = fm.FontProperties(fname=FONT_PATH) if os.path.exists(FONT_PATH) else None

def fp(size=10): return fm.FontProperties(fname=FONT_PATH, size=size) if _font else None
def tx(ax, *a, **kw):
    """ax text helper that injects fontproperties if available."""
    if _font and "fontproperties" not in kw:
        kw["fontproperties"] = fp(kw.pop("size", 10))
    return ax.text(*a, **kw)

EXCL = {(6, 8)}
REG_KR = {"저": "low", "중": "mid", "고": "high"}

ITEMS_ORDER = ["비강사용", "흉성두성", "접촉강도", "호흡식별", "전방공명", "연구개위치", "상압하압"]
ITEMS_SHORT = ["비강\n사용", "흉성\n두성", "접촉\n강도", "호흡\n식별", "전방\n공명", "연구개\n위치", "상압\n하압"]

# ── Data loading ──────────────────────────────────────────────────

def load_analysis():
    """Load all analysis JSONs, return per-(s,g,reg) and per-(s,g) dicts."""
    def _parse(fname, reg_field, val_field, global_field=None, global_val_field=None):
        path = RDIR / fname
        if not path.exists():
            return {}, {}
        with open(path) as f:
            entries = json.load(f)["results"]
        per_reg, per_sess = {}, {}
        for e in entries:
            s, g = e["singer_id"], e["song_id"]
            if (s, g) in EXCL:
                continue
            br = e.get(reg_field, {})
            vals = []
            for re in ["low", "mid", "high"]:
                v = br.get(re, {}).get(val_field)
                if v is not None:
                    per_reg[(s, g, re)] = v
                    vals.append(v)
            if global_field:
                gv = e.get(global_field, {}).get(global_val_field)
            else:
                gv = float(np.mean(vals)) if vals else None
            if gv is not None:
                per_sess[(s, g)] = gv
        return per_reg, per_sess

    egg_cq_r,  egg_cq_s  = _parse("egg_analysis.json",      "cq_by_register",          "mean", "cq_global", "mean")
    egg_pk_r,  egg_pk_s  = _parse("egg_analysis.json",      "cq_by_register",          "peak")
    nas_r,     nas_s     = _parse("nasal_analysis.json",    "nasal_ratio_by_register", "mean")
    spt_r,     spt_s     = _parse("spectral_analysis.json", "spectral_tilt",           "mean")

    cpp_s, sc_s = {}, {}
    path = RDIR / "extra_metrics.json"
    if path.exists():
        for e in json.load(open(path))["results"]:
            s, g = e["singer_id"], e["song_id"]
            if (s, g) in EXCL:
                continue
            if isinstance(e.get("cpp"), dict):
                cpp_s[(s, g)] = e["cpp"]["mean"]
            if isinstance(e.get("spectral_centroid"), dict):
                sc_s[(s, g)] = e["spectral_centroid"]["mean"]

    return {"egg_cq": (egg_cq_r, egg_cq_s), "egg_pk": (egg_pk_r, egg_pk_s),
            "nasal":  (nas_r,    nas_s),    "spt":    (spt_r,    spt_s),
            "cpp": ({}, cpp_s),             "sc": ({}, sc_s)}


def load_trainer_train():
    t_reg, t_sess = defaultdict(list), defaultdict(list)
    with open(VDIR / "trainer_scores.csv") as f:
        for row in csv.DictReader(f):
            g_raw = row.get("song", "").strip()
            if not g_raw.isdigit():
                continue
            s, g = int(row["singer"]), int(g_raw)
            if (s, g) in EXCL:
                continue
            re = REG_KR.get(row.get("register", "").strip())
            for col in ITEMS_ORDER:
                v = row.get(col, "").strip()
                if v:
                    if re:
                        t_reg[(s, g, re, col)].append(float(v))
                    t_sess[(s, g, col)].append(float(v))
    tr = {k: float(np.mean(v)) for k, v in t_reg.items()}
    ts = {k: float(np.mean(v)) for k, v in t_sess.items()}
    return tr, ts


def load_trainer_valid():
    tv = defaultdict(list)
    with open(VDIR / "trainer_scores_validation.csv") as f:
        for row in csv.DictReader(f):
            tid = row.get("test_id", "").strip()
            for col in ITEMS_ORDER:
                v = row.get(col, "").strip()
                if tid and v:
                    tv[(tid, col)].append(float(v))
    return {k: float(np.mean(v)) for k, v in tv.items()}


def load_analysis_t2():
    path = RDIR / "analyze_t2.json"
    if not path.exists():
        return {}
    ai = {}
    for e in json.load(open(path)).get("raw", []):
        wid = e["wav_id"]
        ind = e.get("response", {}).get("indicators", {})
        ai[wid] = ind
    return ai


# ── Correlation helpers ───────────────────────────────────────────

def pearson_ci(pairs):
    """Returns (r, ci_lo, ci_hi, n) or (None, None, None, n)."""
    n = len(pairs)
    if n < 4:
        return None, None, None, n
    x = np.array([a for a, _ in pairs])
    y = np.array([b for _, b in pairs])
    r, _ = stats.pearsonr(x, y)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    z_c = stats.norm.ppf(0.975)
    lo = float(np.tanh(z - z_c * se))
    hi = float(np.tanh(z + z_c * se))
    return float(r), lo, hi, n


def match_per_reg(ai_reg, t_reg, col):
    pairs = [(v, t_reg[(s, g, re, col)])
             for (s, g, re), v in ai_reg.items()
             if t_reg.get((s, g, re, col))]
    return pearson_ci(pairs)


def match_per_sess(ai_sess, t_sess, col):
    pairs = [(v, t_sess[(s, g, col)])
             for (s, g), v in ai_sess.items()
             if t_sess.get((s, g, col))]
    return pearson_ci(pairs)


def match_valid(ai_t2, tv, col, ind_key):
    pairs = [(ai_t2[wid][ind_key], tv[(wid, col)])
             for wid in ai_t2
             if ai_t2[wid].get(ind_key) is not None and tv.get((wid, col))]
    return pearson_ci(pairs)


# ── Compute all correlations ──────────────────────────────────────

ITEM_AI = {
    "비강사용":  ("nasal",  "cpp",   "nasal_ratio"),
    "흉성두성":  ("egg_cq", "cpp",   "cq_mean"),
    "접촉강도":  ("egg_pk", "cpp",   "cq_peak"),
    "호흡식별":  ("cpp",    "cpp",   "cpp_mean"),
    "전방공명":  ("sc",     "sc",    "spectral_centroid_mean"),
    "연구개위치": ("nasal",  "nasal", "nasal_ratio"),
    "상압하압":  ("spt",    "spt",   "spectral_tilt_mean"),
}


def compute_all():
    analysis = load_analysis()
    t_reg, t_sess = load_trainer_train()
    tv = load_trainer_valid()
    ai_t2 = load_analysis_t2()

    results = {}
    for col in ITEMS_ORDER:
        ai_src_reg, ai_src_sess, ind_key_v = ITEM_AI[col]
        ar, as_ = analysis[ai_src_reg]
        _, as2  = analysis[ai_src_sess]

        r_pr  = match_per_reg (ar,  t_reg,  col) if ar  else (None, None, None, 0)
        r_ps  = match_per_sess(as_, t_sess, col) if as_ else (None, None, None, 0)
        r_pss = match_per_sess(as2, t_sess, col) if as2 != as_ else r_ps
        r_val = match_valid   (ai_t2, tv, col, ind_key_v) if ai_t2 else (None, None, None, 0)

        # For items where per_reg is the same dict as per_sess (global-only: cpp, sc)
        if not ar:
            r_pr = (None, None, None, 0)

        results[col] = {
            "per_reg":   r_pr,
            "per_sess":  r_ps,
            "valid":     r_val,
        }
    return results


# ── Plot helpers ──────────────────────────────────────────────────

COLORS = {
    "per_reg":  "#E07070",   # coral red
    "per_sess": "#5B9BD5",   # steel blue
    "valid":    "#70B970",   # green
}
LABELS = {
    "per_reg":  "학습 per-register (현행)",
    "per_sess": "학습 per-session",
    "valid":    "검증 per-session (n≈11)",
}


def _apply_font(ax, title=None, xlabel=None, ylabel=None, title_size=13, label_size=11):
    if _font:
        if title:
            ax.set_title(title, fontproperties=fp(title_size))
        if xlabel:
            ax.set_xlabel(xlabel, fontproperties=fp(label_size))
        if ylabel:
            ax.set_ylabel(ylabel, fontproperties=fp(label_size))
    else:
        if title:
            ax.set_title(title, fontsize=title_size)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=label_size)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=label_size)


def _set_ticks(ax, labels, axis="x", size=9):
    if axis == "x":
        ax.set_xticklabels(labels,
                           fontproperties=fp(size) if _font else None,
                           fontsize=None if _font else size)
    else:
        ax.set_yticklabels(labels,
                           fontproperties=fp(size) if _font else None,
                           fontsize=None if _font else size)


def _legend(ax, handles, size=9):
    if _font:
        ax.legend(handles=handles, prop=fp(size))
    else:
        ax.legend(handles=handles, fontsize=size)


# ── Chart A: Grouped bar ──────────────────────────────────────────

def plot_bars(results, out_path):
    n_items = len(ITEMS_ORDER)
    x = np.arange(n_items)
    w = 0.26
    offsets = [-w, 0, w]
    contexts = ["per_reg", "per_sess", "valid"]

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.axhline(0, color="black", linewidth=0.8, zorder=0)

    handles = []
    for i, (ctx, off) in enumerate(zip(contexts, offsets)):
        rs, los, his = [], [], []
        for col in ITEMS_ORDER:
            r, lo, hi, n = results[col][ctx]
            rs.append(r if r is not None else np.nan)
            los.append((r - lo) if r is not None else 0)
            his.append((hi - r) if r is not None else 0)

        rs  = np.array(rs, dtype=float)
        err = np.array([los, his], dtype=float)

        valid_mask = ~np.isnan(rs)
        if valid_mask.any():
            bars = ax.bar(x[valid_mask] + off, rs[valid_mask],
                          width=w * 0.9, color=COLORS[ctx], alpha=0.85,
                          yerr=err[:, valid_mask], capsize=3,
                          error_kw={"elinewidth": 1.2, "capthick": 1.2},
                          label=LABELS[ctx], zorder=2)
            handles.append(mpatches.Patch(color=COLORS[ctx], label=LABELS[ctx]))

        # Mark N/A positions with small x
        for j, col in enumerate(ITEMS_ORDER):
            if np.isnan(rs[j]):
                ax.text(j + off, 0.02, "N/A", ha="center", va="bottom",
                        fontsize=7, color=COLORS[ctx], alpha=0.7)

    # Reference lines
    for yv, ls, alpha in [(0.3, "--", 0.4), (-0.3, "--", 0.4)]:
        ax.axhline(yv, color="gray", linewidth=0.7, linestyle=ls, alpha=alpha)

    ax.set_xticks(x)
    _set_ticks(ax, ITEMS_SHORT, "x", 10)
    ax.set_ylim(-0.8, 0.9)
    ax.set_yticks(np.arange(-0.8, 0.9, 0.2))
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(axis="y", linewidth=0.4, alpha=0.4, zorder=0)

    _apply_font(ax,
                title="score_mapper 매칭 방식별 Pearson r — 9개 발성 항목 (95% CI)",
                ylabel="Pearson r  (트레이너 평균 vs AI 지표)")
    _legend(ax, handles, size=9)

    # Highlight 흉성두성
    chest_idx = ITEMS_ORDER.index("흉성두성")
    ax.axvspan(chest_idx - 0.45, chest_idx + 0.45, alpha=0.08,
               color="gold", zorder=0, label="_")
    ax.text(chest_idx, 0.82, "★ 핵심 발견",
            ha="center", va="bottom", color="#B8860B",
            fontproperties=fp(8) if _font else None, fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {out_path}")


# ── Chart B: Heatmap ──────────────────────────────────────────────

def plot_heatmap(results, out_path):
    contexts = ["per_reg", "per_sess", "valid"]
    matrix = np.full((len(ITEMS_ORDER), len(contexts)), np.nan)
    n_mat  = np.zeros_like(matrix, dtype=int)

    for i, col in enumerate(ITEMS_ORDER):
        for j, ctx in enumerate(contexts):
            r, _, _, n = results[col][ctx]
            if r is not None:
                matrix[i, j] = r
            n_mat[i, j] = n

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=-0.8, vmax=0.8, aspect="auto")
    plt.colorbar(im, ax=ax, label="Pearson r", shrink=0.8)

    ax.set_xticks([0, 1, 2])
    col_labels = ["학습\nper-register\n(현행)", "학습\nper-session", "검증\nper-session"]
    _set_ticks(ax, col_labels, "x", 9)
    ax.set_yticks(range(len(ITEMS_ORDER)))
    _set_ticks(ax, ITEMS_ORDER, "y", 10)

    # Annotate cells
    for i in range(len(ITEMS_ORDER)):
        for j in range(len(contexts)):
            r = matrix[i, j]
            n = n_mat[i, j]
            if np.isnan(r):
                ax.text(j, i, "N/A", ha="center", va="center",
                        color="gray", fontsize=8)
            else:
                col_txt = "white" if abs(r) > 0.55 else "black"
                ax.text(j, i, f"{r:+.3f}\n(n={n})", ha="center", va="center",
                        color=col_txt, fontsize=8, fontweight="bold")

    # Highlight 흉성두성 row
    chest_idx = ITEMS_ORDER.index("흉성두성")
    for j in range(3):
        ax.add_patch(plt.Rectangle((j - 0.5, chest_idx - 0.5), 1, 1,
                                   fill=False, edgecolor="gold", linewidth=2.5))

    _apply_font(ax, title="매칭 방식별 Pearson r 히트맵\n(황색 테두리: 흉성두성 핵심 발견)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {out_path}")


# ── Chart C: Chest/head focus ─────────────────────────────────────

def plot_focus(results, out_path):
    col = "흉성두성"
    data = results[col]

    labels = ["학습\nper-register\n(현행 mapper)", "학습\nper-session\n(대안)", "검증\nper-session\n(n=11)"]
    colors = [COLORS["per_reg"], COLORS["per_sess"], COLORS["valid"]]
    contexts = ["per_reg", "per_sess", "valid"]

    rs, los, his, ns = [], [], [], []
    for ctx in contexts:
        r, lo, hi, n = data[ctx]
        rs.append(r if r is not None else np.nan)
        los.append(r - lo if r is not None else 0)
        his.append(hi - r if r is not None else 0)
        ns.append(n)

    fig, (ax_bar, ax_text) = plt.subplots(1, 2, figsize=(11, 5),
                                          gridspec_kw={"width_ratios": [3, 2]})

    # Bar subplot
    x = np.arange(3)
    err = np.array([los, his], dtype=float)
    for i, (r, c, n) in enumerate(zip(rs, colors, ns)):
        if not np.isnan(r):
            ax_bar.bar(i, r, color=c, alpha=0.85,
                       yerr=err[:, i:i+1], capsize=6,
                       error_kw={"elinewidth": 1.5, "capthick": 1.5})
            ax_bar.text(i, r + 0.04 * np.sign(r + 0.001), f"r={r:+.3f}",
                        ha="center", va="bottom" if r >= 0 else "top",
                        fontproperties=fp(10) if _font else None, fontsize=10,
                        fontweight="bold")
            ax_bar.text(i, -0.75, f"n={n}",
                        ha="center", va="bottom", color="gray",
                        fontproperties=fp(8) if _font else None, fontsize=8)

    ax_bar.axhline(0, color="black", linewidth=0.8)
    ax_bar.axhline(0.3,  color="gray", linewidth=0.7, linestyle="--", alpha=0.5)
    ax_bar.axhline(-0.3, color="gray", linewidth=0.7, linestyle="--", alpha=0.5)
    ax_bar.set_xticks(x)
    _set_ticks(ax_bar, labels, "x", 9)
    ax_bar.set_ylim(-0.85, 0.85)
    ax_bar.set_yticks(np.arange(-0.8, 0.9, 0.2))
    ax_bar.tick_params(axis="y", labelsize=9)
    ax_bar.grid(axis="y", linewidth=0.4, alpha=0.4)
    _apply_font(ax_bar,
                title="흉성두성 (chest/head voice)\n매칭 방식 아티팩트 시각화",
                ylabel="Pearson r")

    # Arrow annotation
    ax_bar.annotate("", xy=(1, rs[1] - 0.03), xytext=(0, rs[0] + 0.03),
                    arrowprops=dict(arrowstyle="->", color="darkred", lw=1.8))
    ax_bar.text(0.5, (rs[0] + rs[1]) / 2, "부호\n역전!",
                ha="center", color="darkred",
                fontproperties=fp(9) if _font else None, fontsize=9)

    # Text explanation subplot
    ax_text.axis("off")
    lines = [
        ("매칭 방식 아티팩트 원인", 0.95, 11, "bold", "#333333"),
        ("", 0.88, 1, "normal", "white"),
        ("● Per-register (현행):", 0.85, 9, "bold", "#C04040"),
        ("  같은 가수 내 음역대 변동이", 0.78, 9, "normal", "#555555"),
        ("  가수 간 차이로 오인됨", 0.72, 9, "normal", "#555555"),
        ("  → r = -0.282 (부호 역전)", 0.66, 9, "bold",  "#C04040"),
        ("", 0.60, 1, "normal", "white"),
        ("● Per-session (대안):", 0.56, 9, "bold", "#2060A0"),
        ("  가수당 1값으로 집계,", 0.49, 9, "normal", "#555555"),
        ("  음역대 변동 평균화", 0.43, 9, "normal", "#555555"),
        ("  → r = +0.139 (이론 방향 회복)", 0.37, 9, "bold", "#2060A0"),
        ("", 0.31, 1, "normal", "white"),
        ("● 검증 데이터 (n=11):", 0.27, 9, "bold", "#408040"),
        ("  → r = +0.554 (강한 양의 상관)", 0.20, 9, "bold", "#408040"),
        ("", 0.14, 1, "normal", "white"),
        ("→ 5월10일 T2 데이터로 재검증 예정", 0.08, 8, "normal", "#888888"),
    ]
    for text, y, size, weight, color in lines:
        ax_text.text(0.05, y, text, transform=ax_text.transAxes,
                     va="top", color=color, fontweight=weight,
                     fontproperties=fm.FontProperties(fname=FONT_PATH, size=size)
                     if _font else None,
                     fontsize=size if not _font else None)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {out_path}")


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("매칭 방식 진단 시각화 생성 중...")
    results = compute_all()

    print("\n진단 결과 요약:")
    print(f"  {'항목':8s}  {'per-reg':>10s}  {'per-sess':>10s}  {'검증':>10s}")
    print("  " + "─" * 50)
    for col in ITEMS_ORDER:
        r1, _, _, n1 = results[col]["per_reg"]
        r2, _, _, n2 = results[col]["per_sess"]
        r3, _, _, n3 = results[col]["valid"]
        s1 = f"{r1:+.3f}(n={n1})" if r1 is not None else "N/A"
        s2 = f"{r2:+.3f}(n={n2})" if r2 is not None else "N/A"
        s3 = f"{r3:+.3f}(n={n3})" if r3 is not None else "N/A"
        print(f"  {col:8s}  {s1:>12s}  {s2:>12s}  {s3:>12s}")

    print("\n차트 생성 중...")
    plot_bars   (results, OUT / "matching_diagnosis_bars.png")
    plot_heatmap(results, OUT / "matching_diagnosis_heatmap.png")
    plot_focus  (results, OUT / "matching_diagnosis_focus.png")

    print("\n완료. 출력 폴더:", OUT)


if __name__ == "__main__":
    main()
