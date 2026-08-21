"""
s1_selection_bias.py — 작업 1: 선택 편향 정량화.

  (a) 항목별 24개 config 의 val_total_corr 분포 (mean/std/max/히스토그램)
  (b) 선택된 모델 corr 의 분위
  (c) permutation null — val 라벨을 화자 단위로 셔플 후 동일 선택절차(max|corr|) 반복
      → 우연히 얻어지는 최대 val corr 분포 + 경험적 p값
  (d) 보조 null — train 라벨까지 셔플 후 재적합 (선택절차 전체 null)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, load_params, pearson
from rebuild import build_train, build_val
from grid import GRID, LABELS

RNG = np.random.default_rng(20260726)
N_VAL_PERM = 10000
N_FULL_PERM = 200

X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd
Xv, Yv, subs, leaked, grp = build_val()
Xvs = (Xv - mu) / sd
NL = ~leaked                      # val_total = 비누설 17명
P = load_params()

print(f"X_train {Xs.shape} (24 unit / 12 화자)   X_val {Xvs.shape}  val_total n={NL.sum()}")
print(f"permutation: val-label {N_VAL_PERM}회 / full-refit {N_FULL_PERM}회\n")

report = {}
for it in ITEMS9:
    y, yv = Y[it], Yv[it]
    # 24 config 예측 (실제 train 라벨로 적합)
    preds = []
    for lab, f in GRID:
        e = f(); e.fit(Xs, y)
        preds.append(e.predict(Xvs))
    preds = np.array(preds)
    corrs = np.array([pearson(p[NL], yv[NL]) for p in preds])
    fin = np.isfinite(corrs)

    # 배포/선택된 모델
    sel = np.nanargmax(np.abs(corrs))
    sel_c = corrs[sel]
    dep = P["models"][it]["validation_corr"]["val_total"] if it in P["models"] else None

    # (c) val 라벨 permutation null
    ynl = yv[NL]
    pnl = preds[:, NL][fin]
    nullmax = np.empty(N_VAL_PERM)
    for b in range(N_VAL_PERM):
        yp = RNG.permutation(ynl)
        cs = np.array([pearson(p, yp) for p in pnl])
        nullmax[b] = np.nanmax(np.abs(cs))
    p_sel = float((nullmax >= abs(sel_c)).mean())
    p_dep = float((nullmax >= abs(dep)).mean()) if dep is not None else None

    # 단일모델(선택 없음) null — 배포 모델 하나만 놓고 본 p값
    if dep is not None:
        di = LABELS.index({"Ridge": f"Ridge_{P['models'][it]['model_params'].get('alpha')}",
                           }.get(P["models"][it]["model_type"], "")) if False else None
    single = np.empty(N_VAL_PERM)
    pbest = preds[sel][NL]
    for b in range(N_VAL_PERM):
        single[b] = abs(pearson(pbest, RNG.permutation(ynl)))
    p_single = float((single >= abs(sel_c)).mean())

    hist, edges = np.histogram(np.abs(corrs[fin]), bins=np.arange(0, 1.05, 0.1))
    pct = float((np.abs(corrs[fin]) <= abs(sel_c)).mean() * 100)

    report[it] = {
        "n_configs_finite": int(fin.sum()), "n_configs": 24,
        "grid_val_total_corr": {"mean_abs": float(np.nanmean(np.abs(corrs))),
                                "std_abs": float(np.nanstd(np.abs(corrs))),
                                "max_abs": float(np.nanmax(np.abs(corrs))),
                                "min_abs": float(np.nanmin(np.abs(corrs))),
                                "signed_min": float(np.nanmin(corrs)),
                                "signed_max": float(np.nanmax(corrs))},
        "histogram_abs": {"edges": edges.tolist(), "counts": hist.tolist()},
        "selected": {"config": LABELS[sel], "corr": float(sel_c),
                     "percentile_within_grid": pct},
        "deployed_val_total": dep,
        "perm_null_max_abs": {"mean": float(nullmax.mean()), "std": float(nullmax.std()),
                              "p50": float(np.percentile(nullmax, 50)),
                              "p95": float(np.percentile(nullmax, 95)),
                              "p99": float(np.percentile(nullmax, 99)),
                              "max": float(nullmax.max())},
        "p_empirical_selected_vs_maxnull": p_sel,
        "p_empirical_deployed_vs_maxnull": p_dep,
        "p_empirical_single_model": p_single,
    }
    print(f"{it:8s} grid|r| mean={np.nanmean(np.abs(corrs)):.3f} max={np.nanmax(np.abs(corrs)):.3f} "
          f"| sel={LABELS[sel]:12s} r={sel_c:+.4f} ({pct:5.1f}분위) "
          f"| null max|r| p95={np.percentile(nullmax,95):.3f} "
          f"| p_sel={p_sel:.4f} p_single={p_single:.4f}")

# ── (d) full refit null ──
print(f"\n[d] full null: train+val 라벨 모두 셔플 후 24 config 재적합 ({N_FULL_PERM}회)")
full = {}
for it in ITEMS9:
    y, yv = Y[it], Yv[it]
    ynl = yv[NL]
    mx = np.empty(N_FULL_PERM)
    for b in range(N_FULL_PERM):
        yp_tr = RNG.permutation(y)            # 24 unit (화자 12명, unit 단위 셔플)
        yp_va = RNG.permutation(ynl)
        cs = []
        for lab, f in GRID:
            e = f(); e.fit(Xs, yp_tr)
            cs.append(pearson(e.predict(Xvs)[NL], yp_va))
        mx[b] = np.nanmax(np.abs(cs))
    sel_c = report[it]["selected"]["corr"]
    p = float((mx >= abs(sel_c)).mean())
    full[it] = {"mean": float(mx.mean()), "p95": float(np.percentile(mx, 95)),
                "p99": float(np.percentile(mx, 99)), "max": float(mx.max()),
                "p_empirical": p}
    report[it]["full_refit_null"] = full[it]
    print(f"  {it:8s} null max|r|: mean={mx.mean():.3f} p95={np.percentile(mx,95):.3f} "
          f"max={mx.max():.3f}  → p={p:.4f}")

(REDIAG / "s1_selection_bias.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s1_selection_bias.json'}")
