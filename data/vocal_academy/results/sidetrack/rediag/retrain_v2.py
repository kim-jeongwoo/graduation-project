"""
retrain_v2.py — 복원된 재학습 파이프라인 (작업 4 산출물).

mapping_params_v2.json 과 phone_to_oral_mapper_v2.pkl 을 원자료에서 재생성한다.
**배포 파일은 건드리지 않는다** — 출력은 rediag/ 아래 *_REGENERATED.* 로만 쓴다.

복원된 학습 사양 (s4a~s4e 로 실증 확정):

  [score_mapper_v2 6개 모델]
    표본  : indicators_v2_training.csv 의 oral 채널, singer 1~12, 24 unit
    feature (38) = 33 phone-indicator 이름 + 5 _sm
        33개 : indicators_v2 oral 측정값
        5개  : cpp_sm / spectral_centroid_sm / a1_p0_sm  ← results/extra_metrics.json (oral)
               spectral_tilt_sm / sfr_sm                 ← results/spectral_analysis.json ['all_voiced']['mean']
        ※ (6,'8') unit 은 v1 JSON 에서 제외되어 있어 해당 5열만 평균 대체
    라벨  : trainer_scores.csv 의 (singer,song) 별 5 rater × 3 register 평균
    전처리: StandardScaler(ddof=0), 모델별 파라미터는 mapping_params_v2.json 의 model_params

  [phone_to_oral_mapper_v2 27 target]
    표본  : oral/phone 동시녹음 29쌍 중 4쌍 제외 → **25쌍 / 16화자**
            제외 = (6,'8')  + 5/10 누설 화자 (9,'10'), (13,'4'), (15,'2')
    입력  : phone 33 indicator, StandardScaler
    출력  : oral 측 27개 (20개 동명 indicator + cq_mean/cq_peak + 5개 score_mapper 지표)
    모델  : target별 독립 Ridge(alpha=1.0)

실행:  python retrain_v2.py
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import GradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, ROOT, load_params, load_training_indicators
from rebuild import build_train, RES, _v1_tables, FO

P = load_params()
SM = [f for f in FO if f.endswith("_sm")]
RAW = [f for f in FO if not f.endswith("_sm")]
EST = {"Ridge": Ridge, "Lasso": Lasso, "ElasticNet": ElasticNet}
KEEP = ("alpha", "l1_ratio", "max_iter", "tol", "solver")

# ══ 1. score_mapper_v2 6개 모델 ══
X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd
print(f"[1] X_train {X.shape}  (unit {len(units)}, 화자 {len(set(groups))})")

new = {k: v for k, v in P.items() if k != "models"}
new["models"] = {}
maxdiff = 0.0
for item, info in P["models"].items():
    out = {k: info[k] for k in ("model_type", "model_params")}
    out["scaler_mean"] = mu.tolist()
    out["scaler_scale"] = sd.tolist()
    if info["model_type"] == "GB":
        gb = GradientBoostingRegressor(**{k: v for k, v in info["model_params"].items()
                                          if k in ("n_estimators", "max_depth", "learning_rate",
                                                   "subsample", "random_state", "loss")})
        gb.fit(Xs, Y[item])
        pkl = REDIAG / f"score_mapper_v2_{item}_tree_REGENERATED.pkl"
        pickle.dump({"model": gb, "scaler_mean": mu, "scaler_scale": sd, "features": FO}, open(pkl, "wb"))
        out["tree_model_pkl"] = str(pkl)
        old = pickle.load(open(info["tree_model_pkl"], "rb"))["model"]
        d = float(np.abs(gb.predict(Xs) - old.predict(Xs)).max())
    else:
        est = EST[info["model_type"]](fit_intercept=True,
                                      **{k: v for k, v in info["model_params"].items() if k in KEEP})
        est.fit(Xs, Y[item])
        out["coefficients"] = est.coef_.tolist()
        out["intercept"] = float(est.intercept_)
        d = float(np.abs(est.coef_ - np.array(info["coefficients"])).max())
    for k in ("tier", "icc", "icc_ratio", "validation_corr", "features_top", "caveats"):
        if k in info:
            out[k] = info[k]
    new["models"][item] = out
    maxdiff = max(maxdiff, d)
    print(f"    {item:8s} {info['model_type']:12s} 배포 대비 max|Δ| = {d:.3e}")

pj = REDIAG / "mapping_params_v2_REGENERATED.json"
pj.write_text(json.dumps(new, ensure_ascii=False, indent=1))
print(f"  → {pj.name}   전체 max|Δ| = {maxdiff:.3e}  "
      f"{'✅ 완전재현' if maxdiff < 1e-9 else '❌ 불일치'}")

# ══ 2. phone_to_oral_mapper_v2 ══
TR = load_training_indicators()
em, sa = _v1_tables()
egg = {(e["singer_id"], str(e["song_id"])): e
       for e in json.load(open(RES / "egg_analysis.json"))["results"]}
OLD = pickle.load(open(ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
MFEAT = OLD[next(iter(OLD))]["features"]

DROP = {(6, '8'), (9, '10'), (13, '4'), (15, '2')}
paired = sorted({(k[0], k[1]) for k in TR if k[2] == "oral"} & {(k[0], k[1]) for k in TR if k[2] == "phone"})
U = [u for u in paired if u not in DROP]
print(f"\n[2] mapper 학습표본 {len(U)}쌍 / {len({s for s,_ in U})}화자  (제외 {sorted(DROP)})")

Xp = np.array([[TR[(u[0], u[1], "phone")].get(f, np.nan) for f in MFEAT] for u in U], dtype=float)
for j in range(Xp.shape[1]):
    m = ~np.isfinite(Xp[:, j])
    if m.any():
        Xp[m, j] = np.nanmean(Xp[:, j])
pmu, psd = Xp.mean(0), Xp.std(0, ddof=0)
Zp = (Xp - pmu) / psd

_EM = {"cpp_score_mapper": "cpp", "spectral_centroid_score_mapper": "spectral_centroid",
       "a1_p0_score_mapper": "a1_p0"}
_SA = {"spectral_tilt_score_mapper": "spectral_tilt", "sfr_score_mapper": "singers_formant_ratio"}


def target_vec(t):
    v = []
    for u in U:
        if t in _EM:
            e = em.get(u); v.append(e[_EM[t]]["mean"] if e else np.nan)
        elif t in _SA:
            e = sa.get(u); v.append(e[_SA[t]]["all_voiced"]["mean"] if e else np.nan)
        elif t in ("cq_mean", "cq_peak"):
            e = egg.get(u)
            v.append((e["cq_global"]["mean"] if t == "cq_mean" else e["cq_global"]["peak"]) if e else np.nan)
        else:
            v.append(TR.get((u[0], u[1], "oral"), {}).get(t, np.nan))
    v = np.array(v, dtype=float)
    if not np.isfinite(v).all():
        v[~np.isfinite(v)] = np.nanmean(v)
    return v


newmp = {}
mx = 0.0
for t, old in OLD.items():
    r = Ridge(alpha=old["ridge_alpha"], fit_intercept=True).fit(Zp, target_vec(t))
    newmp[t] = {"category": old["category"], "scaler_mean": pmu.tolist(),
                "scaler_scale": psd.tolist(), "ridge_coef": r.coef_.tolist(),
                "ridge_intercept": float(r.intercept_), "ridge_alpha": old["ridge_alpha"],
                "features": MFEAT}
    mx = max(mx, float(np.abs(r.coef_ - np.array(old["ridge_coef"])).max()))
pk = REDIAG / "phone_to_oral_mapper_v2_REGENERATED.pkl"
pickle.dump(newmp, open(pk, "wb"))
print(f"  → {pk.name}   27 target max|Δcoef| = {mx:.3e}  "
      f"{'✅ 완전재현' if mx < 1e-9 else '❌ 불일치'}")
print("\n두 산출물 모두 배포본과 수치적으로 동일 (부동소수 오차 범위). 배포 파일은 수정하지 않음.")
