"""
s4c_refit.py — 재구성한 X_train/y 로 배포 계수(coefficients) 재현 시도.
성공 시 mapping_params_v2.json 재생성 파이프라인이 복원된 것.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import GradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, load_params
from rebuild import build_train, FO

P = load_params()
X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd

EST = {"Ridge": Ridge, "Lasso": Lasso, "ElasticNet": ElasticNet}
rep = {}
print(f"{'item':10s}{'model':12s}{'max|Δcoef|':>13s}{'corr(coef)':>12s}{'Δintercept':>13s}  판정")
for item, info in P["models"].items():
    if "coefficients" not in info:
        rep[item] = {"model_type": info["model_type"], "status": "tree_pkl_not_linear"}
        continue
    y = Y[item]
    mt = info["model_type"]
    prm = dict(info["model_params"])
    prm.pop("copy_X", None); prm.pop("precompute", None); prm.pop("warm_start", None)
    prm.pop("positive", None); prm.pop("selection", None); prm.pop("random_state", None)
    prm.pop("fit_intercept", None)
    est = EST[mt](fit_intercept=True, **{k: v for k, v in prm.items()
                                         if k in ("alpha", "l1_ratio", "max_iter", "tol", "solver")})
    est.fit(Xs, y)
    tgt = np.array(info["coefficients"])
    d = float(np.abs(est.coef_ - tgt).max())
    c = float(np.corrcoef(est.coef_, tgt)[0, 1]) if np.std(tgt) > 0 else np.nan
    di = float(abs(est.intercept_ - info["intercept"]))
    ok = "✅ 완전재현" if d < 5e-4 else ("⚠️ 근사" if c > 0.99 else "❌ 불일치")
    print(f"{item:10s}{mt:12s}{d:13.3e}{c:12.4f}{di:13.3e}  {ok}")
    rep[item] = {"model_type": mt, "max_abs_coef_diff": d, "coef_corr": c,
                 "intercept_diff": di, "verdict": ok}

# ── 혀경직도 GB (pkl) ──
import pickle
gbp = P["models"]["혀경직도"]["tree_model_pkl"]
tm = pickle.load(open(gbp, "rb"))
print(f"\n혀경직도 GB pkl keys: {list(tm.keys())}")
gb = GradientBoostingRegressor(**{k: v for k, v in P["models"]["혀경직도"]["model_params"].items()
                                  if k in ("n_estimators", "max_depth", "learning_rate",
                                           "subsample", "random_state", "loss")})
gb.fit(Xs, Y["혀경직도"])
p_new = gb.predict(Xs)
p_old = tm["model"].predict(Xs)
d = float(np.abs(p_new - p_old).max())
c = float(np.corrcoef(p_new, p_old)[0, 1])
ok = "✅ 완전재현" if d < 1e-6 else ("⚠️ 근사" if c > 0.99 else "❌ 불일치")
print(f"{'혀경직도':10s}{'GB':12s}{d:13.3e}{c:12.4f}{'-':>13s}  {ok}  (train 예측값 비교)")
rep["혀경직도"] = {"model_type": "GB", "max_abs_pred_diff": d, "pred_corr": c, "verdict": ok}

(REDIAG / "s4c_refit.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s4c_refit.json'}")
