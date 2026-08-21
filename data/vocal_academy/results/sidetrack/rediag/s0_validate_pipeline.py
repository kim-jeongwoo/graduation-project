"""
s0_validate_pipeline.py — 재구성 파이프라인이 배포 JSON의 validation_corr 을 재현하는지 검증.
이후 1/2/3/5/6 작업의 전제 조건.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, load_params, pearson
from rebuild import build_train, build_val, FO

P = load_params()
X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xv, Yv, subs, leaked, grp = build_val()
Xvs = (Xv - mu) / sd

COH = {"val_A": (grp == "A") & ~leaked, "val_B": (grp == "B") & ~leaked,
       "val_total": ~leaked, "val_full21": np.ones(len(subs), bool)}
print(f"cohort n: " + "  ".join(f"{k}={int(v.sum())}" for k, v in COH.items()))
print()
print(f"{'item':10s}" + "".join(f"{c:>22s}" for c in COH))
rep = {}
for item, info in P["models"].items():
    if "coefficients" in info:
        pred = Xvs @ np.array(info["coefficients"]) + info["intercept"]
    else:
        tm = pickle.load(open(info["tree_model_pkl"], "rb"))
        pred = tm["model"].predict(Xvs)
    line = f"{item:10s}"
    rep[item] = {}
    for c, m in COH.items():
        got = pearson(pred[m], Yv[item][m])
        tgt = info["validation_corr"].get(c)
        line += f"{got:+8.4f}/{tgt:+8.4f}" + ("✅" if tgt is not None and abs(got - tgt) < 5e-4 else "❌")
        rep[item][c] = {"recomputed": got, "json": tgt}
    print(line + "   (재계산/JSON)")

(REDIAG / "s0_validate_pipeline.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s0_validate_pipeline.json'}")
