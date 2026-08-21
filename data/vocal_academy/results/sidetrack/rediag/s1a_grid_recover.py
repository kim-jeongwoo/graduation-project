"""
s1a_grid_recover.py — multivariate_models_v3.csv 의 24개 모델 config 를 정확히 복원.
CSV 의 val_total_corr / train_5fold_mean 과 대조해 l1_ratio, RF/GB 하이퍼파라미터를 확정.
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, SIDE, REDIAG, pearson
from rebuild import build_train, build_val

X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd
Xv, Yv, subs, leaked, grp = build_val()
Xvs = (Xv - mu) / sd
NL = ~leaked

CSV = list(csv.DictReader(open(SIDE / "multivariate_models_v3.csv")))
rows_by_item = {}
for r in CSV:
    rows_by_item.setdefault(r["item"], []).append(r)

# 후보 config (CSV 순서 그대로: Lasso4, Ridge5, EN9, RF4, GB2)
def make(spec):
    kind, p = spec
    if kind == "Lasso":
        return Lasso(alpha=p, max_iter=10000)
    if kind == "Ridge":
        return Ridge(alpha=p)
    if kind == "EN":
        a, l1 = p
        return ElasticNet(alpha=a, l1_ratio=l1, max_iter=10000)
    if kind == "RF":
        return RandomForestRegressor(max_depth=p, n_estimators=100, random_state=42)
    if kind == "GB":
        return GradientBoostingRegressor(max_depth=p, n_estimators=100,
                                         learning_rate=0.1, random_state=42)


def evaluate(est, y):
    est.fit(Xs, y)
    return pearson(est.predict(Xvs)[NL], Yv[NL] if False else Yv), None


def val_corr(est, y, yv):
    est.fit(Xs, y)
    return pearson(est.predict(Xvs)[NL], yv[NL])


def cv5(est, y, seed=42):
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    cs = []
    for tr, te in kf.split(Xs):
        e = make_like(est)
        e.fit(Xs[tr], y[tr])
        cs.append(pearson(e.predict(Xs[te]), y[te]))
    return float(np.nanmean(cs))


def make_like(est):
    from sklearn.base import clone
    return clone(est)


# ── l1_ratio 후보 탐색: EN alpha=0.01 3종 val_total_corr 매칭 ──
item0 = "비강사용"
tgt_en = [float(r["val_total_corr"]) for r in rows_by_item[item0]
          if r["model"] == "ElasticNet" and r["params"] == "0.01"]
print(f"CSV {item0} EN alpha=0.01 3종 val_total_corr = {tgt_en}")
best = None
for combo in itertools.permutations([0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9], 3):
    got = [val_corr(ElasticNet(alpha=0.01, l1_ratio=l, max_iter=10000), Y[item0], Yv[item0])
           for l in combo]
    e = max(abs(a - b) for a, b in zip(got, tgt_en))
    if best is None or e < best[0]:
        best = (e, combo, got)
print(f"  best l1_ratio triple = {best[1]}  maxerr={best[0]:.2e}  got={[round(g,4) for g in best[2]]}")
L1 = sorted(best[1])

# ── RF depth / GB 확인 ──
tgt_rf = [(r["params"], float(r["val_total_corr"])) for r in rows_by_item[item0] if r["model"] == "RF"]
tgt_gb = [(r["params"], float(r["val_total_corr"])) for r in rows_by_item[item0] if r["model"] == "GB"]
print(f"\nCSV RF: {tgt_rf}")
for d in [3, 5, 7, None]:
    print(f"  RF depth={d}: {val_corr(RandomForestRegressor(max_depth=d, n_estimators=100, random_state=42), Y[item0], Yv[item0]):+.4f}")
print(f"CSV GB: {tgt_gb}")
for d in [3, 5]:
    print(f"  GB depth={d}: {val_corr(GradientBoostingRegressor(max_depth=d, n_estimators=100, learning_rate=0.1, random_state=42), Y[item0], Yv[item0]):+.4f}")

GRID = ([("Lasso", a) for a in [0.001, 0.01, 0.1, 1.0]]
        + [("Ridge", a) for a in [0.01, 0.1, 1.0, 10.0, 100.0]]
        + [("EN", (a, l)) for a in [0.01, 0.1, 1.0] for l in L1]
        + [("RF", d) for d in [3, 5, 7, None]]
        + [("GB", d) for d in [3, 5]])
print(f"\n복원 GRID = {len(GRID)} configs")

# ── 전체 9항목 × 24 config 검증 ──
print(f"\n{'item':10s}{'max|Δ val_total|':>18s}{'n exact(<1e-3)':>17s}")
rec = {}
for it in ITEMS9:
    tgt = [float(r["val_total_corr"]) for r in rows_by_item[it]]
    got = [val_corr(make(g), Y[it], Yv[it]) for g in GRID]
    d = [abs(a - b) for a, b in zip(got, tgt)]
    rec[it] = {"max_abs_diff": float(max(d)), "n_exact": int(sum(x < 1e-3 for x in d)),
               "recomputed": got, "csv": tgt}
    print(f"{it:10s}{max(d):18.2e}{sum(x<1e-3 for x in d):12d}/24")

(REDIAG / "s1a_grid_recover.json").write_text(json.dumps(
    {"l1_ratios": L1, "grid": [[g[0], g[1]] for g in GRID], "per_item": rec},
    ensure_ascii=False, indent=1, default=str))
print(f"\nsaved: {REDIAG/'s1a_grid_recover.json'}")
