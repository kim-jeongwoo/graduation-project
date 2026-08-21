"""
s2_speaker_bootstrap.py — 작업 2: 화자 단위 재집계 + 화자 클러스터 부트스트랩 95% CI.

전제 확인: 배포 val corr 의 n 이 63(21명×3register)인지 21/17인지 실증.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, VA, load_params, load_val_indicators, pearson
from rebuild import build_train, build_val

import csv

RNG = np.random.default_rng(20260726)
NB = 1000
P = load_params()

# ── 0. n 확인 ──
VAL, VMETA = load_val_indicators()
n_ind_rows = sum(len(v) for v in VAL.values())
raw = list(csv.DictReader(open(VA / "trainer_scores_510.csv")))
print("[0] 검증 corr 의 표본 단위 확인")
print(f"  indicators_v2_validation_510.csv : {len(VAL)} 화자 × 33 indicator = {n_ind_rows} 행")
print(f"    → register 컬럼 값 = {sorted({m for s in VAL for m in ['all_voiced']})} (화자당 1값, register 분해 없음)")
print(f"  trainer_scores_510.csv           : {len(raw)} 행 = 5 rater × 21 화자 × 3 register")
print(f"  ⇒ 지표가 화자당 1값이므로 corr 의 n 은 화자 수. 63행 기준 corr 은 **산출 불가능**.")
print(f"    배포 JSON n: val_A=9, val_B=8, val_total=17(비누설), val_full21=21 — s0 에서 재현 확인 완료.\n")

X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xv, Yv, subs, leaked, grp = build_val()
Xvs = (Xv - mu) / sd
NL = ~leaked


def predict(item):
    info = P["models"][item]
    if "coefficients" in info:
        return Xvs @ np.array(info["coefficients"]) + info["intercept"]
    tm = pickle.load(open(info["tree_model_pkl"], "rb"))
    return tm["model"].predict(Xvs)


def boot(pred, y, mask, nb=NB):
    idx = np.where(mask)[0]
    out = np.empty(nb)
    for b in range(nb):
        s = RNG.choice(idx, size=len(idx), replace=True)   # 화자 클러스터 리샘플
        out[b] = pearson(pred[s], y[s])
    out = out[np.isfinite(out)]
    return out


print(f"[1] 화자 클러스터 부트스트랩 {NB}회 — 95% 백분위 CI")
print(f"{'item':9s}{'tier':11s}{'cohort':11s}{'n':>4s}{'corr':>9s}{'95% CI':>22s}{'CI∋0':>7s}{'p(부호반대)':>12s}")
rep = {}
for it in ITEMS9:
    if it not in P["models"]:
        rep[it] = {"status": "no_deployed_model"}
        continue
    pred = predict(it)
    rep[it] = {"tier": P["models"][it]["tier"], "cohorts": {}}
    for cname, m in [("val_total(17)", NL), ("val_full21(21)", np.ones(len(subs), bool))]:
        r = pearson(pred[m], Yv[it][m])
        bs = boot(pred, Yv[it], m)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        contains0 = bool(lo <= 0 <= hi)
        psign = float((bs * np.sign(r) <= 0).mean())
        rep[it]["cohorts"][cname] = {"n": int(m.sum()), "corr": r,
                                     "ci95": [float(lo), float(hi)],
                                     "ci_contains_zero": contains0,
                                     "p_sign_flip": psign,
                                     "boot_mean": float(bs.mean()),
                                     "boot_std": float(bs.std())}
        print(f"{it:9s}{P['models'][it]['tier']:11s}{cname:11s}{int(m.sum()):4d}{r:+9.4f}"
              f"  [{lo:+.3f}, {hi:+.3f}]{'   예' if contains0 else '  아니오':>9s}{psign:12.3f}")

print("\n[2] 표시 4항목 요약 (val_total, 비누설 17명)")
for it in ["접촉강도", "호흡식별", "연구개위치", "혀경직도"]:
    c = rep[it]["cohorts"]["val_total(17)"]
    v = "❌ CI 가 0 포함 → 통계적 유의성 없음" if c["ci_contains_zero"] else "✅ CI 가 0 미포함"
    print(f"  {it:8s} r={c['corr']:+.4f}  CI=[{c['ci95'][0]:+.3f},{c['ci95'][1]:+.3f}]  {v}")

(REDIAG / "s2_speaker_bootstrap.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s2_speaker_bootstrap.json'}")
