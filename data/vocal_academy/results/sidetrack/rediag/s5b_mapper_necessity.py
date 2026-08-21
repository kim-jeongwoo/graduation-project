"""
s5b_mapper_necessity.py — 작업 5 후반부: mapper 경유가 실제로 이득인가.

비교 조건 (X_train 은 양쪽 동일 = oral 측정 _sm → 계수도 동일):
  MAPPER : X_val 의 5개 _sm = phone_to_oral_mapper_v2 Ridge 추정치 (배포 경로)
  DIRECT : X_val 의 5개 _sm = phone 오디오에서 v1 알고리즘으로 직접 산출 (s5a)

산출:
  (1) 학습 paired 코호트에서 mapper 추정치 / 직접 산출치 각각이 oral 실측을 얼마나 맞히나
      (mapper 학습에 쓰인 25쌍 = in-sample, 제외된 4쌍 = out-of-sample)
  (2) 5/10 검증셋에서 두 조건의 배포모델 corr / 중첩 CV corr
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, load_params, pearson
from rebuild import build_train, build_val, RES, _v1_tables, FO
from common import load_training_indicators
from grid import GRID

RNG = np.random.default_rng(20260726)
P = load_params()
SM = [f for f in FO if f.endswith("_sm")]
DIRECT_KEY = {"cpp_sm": "cpp", "spectral_centroid_sm": "spectral_centroid",
              "spectral_tilt_sm": "spectral_tilt", "sfr_sm": "singers_formant_ratio",
              "a1_p0_sm": "a1_p0"}

dv = json.loads((REDIAG / "s5a_direct_val510.json").read_text())
dtp = json.loads((REDIAG / "s5a_direct_train_phone.json").read_text())

# ══ (1) 학습 paired 코호트: mapper vs 직접산출, 대상은 oral 실측 ══
import pickle
from common import ROOT
MP = pickle.load(open(ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
MFEAT = MP[next(iter(MP))]["features"]
TR = load_training_indicators()
em, sa = _v1_tables()
_EM = {"cpp_sm": "cpp", "spectral_centroid_sm": "spectral_centroid", "a1_p0_sm": "a1_p0"}
_SA = {"spectral_tilt_sm": "spectral_tilt", "sfr_sm": "singers_formant_ratio"}
TRANS = P["feature_translation"]
HELDOUT = {(6, '8'), (9, '10'), (13, '4'), (15, '2')}

paired = sorted({(k[0], k[1]) for k in TR if k[2] == "oral"} & {(k[0], k[1]) for k in TR if k[2] == "phone"})
print("[1] 학습 paired 코호트 — oral 실측 대비 재현 정확도 (Pearson r)")
print(f"{'_sm feature':24s}{'n':>4s}{'mapper(전체29)':>16s}{'direct(전체29)':>16s}"
      f"{'mapper(OOS 4)':>16s}{'direct(OOS 4)':>16s}")
rep1 = {}
for f in SM:
    truth, mp_est, dr_est, oos = [], [], [], []
    for u in paired:
        e = em.get(u) if f in _EM else sa.get(u)
        if e is None:
            continue
        t = e[_EM[f]]["mean"] if f in _EM else e[_SA[f]]["all_voiced"]["mean"]
        ph = TR[(u[0], u[1], "phone")]
        x = np.array([ph.get(k, 0.0) if np.isfinite(ph.get(k, np.nan)) else 0.0 for k in MFEAT])
        m = MP[TRANS[f].replace("__mapped", "")]
        xs = (x - np.array(m["scaler_mean"])) / np.array(m["scaler_scale"])
        pred = float(np.dot(np.array(m["ridge_coef"]), xs) + m["ridge_intercept"])
        d = dtp.get(f"{u[0]}-{u[1]}", {}).get(DIRECT_KEY[f])
        if d is None:
            continue
        truth.append(t); mp_est.append(pred); dr_est.append(d); oos.append(u in HELDOUT)
    truth = np.array(truth); mp_est = np.array(mp_est); dr_est = np.array(dr_est); oos = np.array(oos)
    r_m, r_d = pearson(mp_est, truth), pearson(dr_est, truth)
    r_mo = pearson(mp_est[oos], truth[oos]) if oos.sum() >= 3 else np.nan
    r_do = pearson(dr_est[oos], truth[oos]) if oos.sum() >= 3 else np.nan
    rep1[f] = {"n": len(truth), "mapper_all": r_m, "direct_all": r_d,
               "mapper_oos": r_mo, "direct_oos": r_do, "n_oos": int(oos.sum())}
    print(f"{f:24s}{len(truth):4d}{r_m:+16.4f}{r_d:+16.4f}{r_mo:+16.4f}{r_do:+16.4f}")
print(f"  (OOS = mapper 학습에서 제외된 {int(oos.sum())}쌍: {sorted(HELDOUT)})")

# ══ (2) 5/10 검증: MAPPER vs DIRECT ══
X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd
Xv, Yv, subs, leaked, grp = build_val()
NL = ~leaked

Xv_direct = Xv.copy()
for i, s in enumerate(subs):
    for f in SM:
        v = dv[s][DIRECT_KEY[f]]
        Xv_direct[i, FO.index(f)] = v if v is not None else Xv[i, FO.index(f)]

print("\n[2-0] 5/10 검증셋: mapper 추정치 vs 직접 산출치 자체의 일치도")
for f in SM:
    j = FO.index(f)
    print(f"  {f:24s} r={pearson(Xv[:,j], Xv_direct[:,j]):+.4f}   "
          f"mapper mean={Xv[:,j].mean():10.4f}  direct mean={Xv_direct[:,j].mean():10.4f}  "
          f"train(oral) mean={mu[j]:10.4f}")

Xvs_m = (Xv - mu) / sd
Xvs_d = (Xv_direct - mu) / sd


def nested(preds, y, nrep=20, k=5):
    n = len(y)
    fin = np.array([np.isfinite(pearson(p[NL], y[NL])) for p in preds])
    outs = []
    for _ in range(nrep):
        order = RNG.permutation(n)
        oof = np.full(n, np.nan)
        for te in np.array_split(order, k):
            tr = np.setdiff1d(np.arange(n), te)
            cs = np.array([pearson(preds[i][tr], y[tr]) if fin[i] else np.nan
                           for i in range(len(preds))])
            if not np.isfinite(cs).any():
                continue
            i = int(np.nanargmax(np.abs(cs)))
            oof[te] = preds[i][te] * (np.sign(cs[i]) or 1.0)
        m = np.isfinite(oof)
        outs.append(pearson(oof[m & NL], y[m & NL]))
    return float(np.nanmean(outs)), float(np.nanstd(outs))


print(f"\n[2] 항목별 corr — MAPPER vs DIRECT")
print(f"{'item':10s}{'배포모델 MAPPER':>17s}{'배포모델 DIRECT':>17s}"
      f"{'nested MAPPER':>16s}{'nested DIRECT':>16s}{'Δnested':>10s}")
rep2 = {}
for it in ITEMS9:
    pm = [], []
    Pm, Pd = [], []
    for lab, f in GRID:
        e = f(); e.fit(Xs, Y[it])
        Pm.append(e.predict(Xvs_m)); Pd.append(e.predict(Xvs_d))
    Pm, Pd = np.array(Pm), np.array(Pd)
    if it in P["models"]:
        info = P["models"][it]
        if "coefficients" in info:
            c = np.array(info["coefficients"]); b = info["intercept"]
            dm = pearson((Xvs_m @ c + b)[NL], Yv[it][NL])
            dd = pearson((Xvs_d @ c + b)[NL], Yv[it][NL])
        else:
            tm = pickle.load(open(info["tree_model_pkl"], "rb"))
            dm = pearson(tm["model"].predict(Xvs_m)[NL], Yv[it][NL])
            dd = pearson(tm["model"].predict(Xvs_d)[NL], Yv[it][NL])
    else:
        dm = dd = np.nan
    nm, nms = nested(Pm, Yv[it]); nd, nds = nested(Pd, Yv[it])
    rep2[it] = {"deployed_mapper": dm, "deployed_direct": dd,
                "nested_mapper": nm, "nested_mapper_sd": nms,
                "nested_direct": nd, "nested_direct_sd": nds,
                "delta_nested": nd - nm}
    print(f"{it:10s}{dm:+17.4f}{dd:+17.4f}{nm:+16.4f}{nd:+16.4f}{nd-nm:+10.4f}")

nm = np.array([rep2[i]["nested_mapper"] for i in ITEMS9])
nd = np.array([rep2[i]["nested_direct"] for i in ITEMS9])
print(f"\n9항목 nested 평균: MAPPER={nm.mean():+.4f}  DIRECT={nd.mean():+.4f}  Δ={nd.mean()-nm.mean():+.4f}")
sh = ["접촉강도", "호흡식별", "연구개위치", "혀경직도"]
nm4 = np.array([rep2[i]["nested_mapper"] for i in sh]); nd4 = np.array([rep2[i]["nested_direct"] for i in sh])
print(f"표시 4항목 nested 평균: MAPPER={nm4.mean():+.4f}  DIRECT={nd4.mean():+.4f}  Δ={nd4.mean()-nm4.mean():+.4f}")

(REDIAG / "s5b_mapper_necessity.json").write_text(json.dumps(
    {"reconstruction_accuracy": rep1, "val_comparison": rep2,
     "summary": {"nested_mean_mapper": float(nm.mean()), "nested_mean_direct": float(nd.mean()),
                 "shown4_mapper": float(nm4.mean()), "shown4_direct": float(nd4.mean())}},
    ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s5b_mapper_necessity.json'}")
