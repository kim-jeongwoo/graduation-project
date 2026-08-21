"""
s4d_mapper_refit.py — phone_to_oral_mapper_v2.pkl 재현 시도 + 학습 규모 판정(작업 7).

mapper 구조: target별 독립 Ridge(alpha=1.0), 입력 33 phone indicator (StandardScaler).
scaler_mean(=phone 33개 평균)이 어떤 pair subset 에서 나왔는지로 학습집합 확정.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, ROOT
from common import load_training_indicators
from rebuild import RES, _v1_tables

MP = pickle.load(open(ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
FEAT = MP[next(iter(MP))]["features"]
TR = load_training_indicators()

oral_u = {(k[0], k[1]) for k in TR if k[2] == "oral"}
phone_u = {(k[0], k[1]) for k in TR if k[2] == "phone"}
paired = sorted(oral_u & phone_u)
print(f"paired (oral&phone) units = {len(paired)}, speakers = {len({s for s,_ in paired})}")

tmu = np.array(MP[next(iter(MP))]["scaler_mean"])
tsd = np.array(MP[next(iter(MP))]["scaler_scale"])
# 모든 target 이 같은 scaler 를 쓰는지
same = all(np.allclose(MP[t]["scaler_mean"], tmu, atol=1e-12) for t in MP)
print(f"27 target 간 scaler 동일: {same}")


def ph(u, f):
    return TR[(u[0], u[1], "phone")].get(f, np.nan)


def err(units):
    mu = np.array([np.nanmean([ph(u, f) for u in units]) for f in FEAT])
    sd = np.array([np.nanstd([ph(u, f) for u in units], ddof=0) for f in FEAT])
    return (float(np.median(np.abs(mu - tmu) / (np.abs(tmu) + 1e-12))),
            float(np.median(np.abs(sd - tsd) / (np.abs(tsd) + 1e-12))))


em, sa = _v1_tables()
CANDS = {
    "paired_all(29)": paired,
    "paired_s1_12": [u for u in paired if u[0] <= 12],
    "paired_s13_22": [u for u in paired if u[0] >= 13],
    "paired_in_v1_extra_metrics": [u for u in paired if u in em],
    "paired_in_v1_spectral": [u for u in paired if u in sa],
    "paired_in_both_v1": [u for u in paired if u in em and u in sa],
}
print(f"\n{'candidate':32s}{'n':>4s}{'spk':>5s}{'rel.err mean':>15s}{'rel.err std':>15s}")
res = {}
for n, u in CANDS.items():
    if not u:
        continue
    e = err(u)
    res[n] = {"n": len(u), "spk": len({s for s, _ in u}), "err_mean": e[0], "err_std": e[1]}
    print(f"{n:32s}{len(u):4d}{len({s for s,_ in u}):5d}{e[0]*100:14.4f}%{e[1]*100:14.4f}%")

# greedy: 정확히 맞는 subset 탐색
cur = list(paired)
be = err(cur)[0]
while len(cur) > 10:
    c = [(err([k for k in cur if k != d])[0], d) for d in cur]
    e, d = min(c)
    if e >= be - 1e-15:
        break
    cur = [k for k in cur if k != d]; be = e
print(f"\ngreedy 최소: n={len(cur)} spk={len({s for s,_ in cur})} rel.err mean={be*100:.5f}% std={err(cur)[1]*100:.5f}%")
print(f"  제외: {sorted(set(paired)-set(cur))}")

# ── 최적 후보로 Ridge 재적합 ──
best_name = min(res, key=lambda k: res[k]["err_mean"])
if err(cur)[0] < res[best_name]["err_mean"]:
    U, best_name = cur, "greedy"
else:
    U = CANDS[best_name]
print(f"\n재적합 대상 subset: {best_name} (n={len(U)})")

Xp = np.array([[ph(u, f) for f in FEAT] for u in U], dtype=float)
for j in range(Xp.shape[1]):
    m = ~np.isfinite(Xp[:, j])
    if m.any():
        Xp[m, j] = np.nanmean(Xp[:, j])
mu, sd = Xp.mean(0), Xp.std(0, ddof=0)
Xs = (Xp - mu) / sd

_EM = {"cpp_score_mapper": "cpp", "spectral_centroid_score_mapper": "spectral_centroid",
       "a1_p0_score_mapper": "a1_p0"}
_SA = {"spectral_tilt_score_mapper": "spectral_tilt", "sfr_score_mapper": "singers_formant_ratio"}
egg = {}
for e in json.load(open(RES / "egg_analysis.json"))["results"]:
    egg[(e["singer_id"], str(e["song_id"]))] = e


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
        else:                       # oral indicator 그대로
            v.append(TR.get((u[0], u[1], "oral"), {}).get(t, np.nan))
    v = np.array(v, dtype=float)
    if not np.isfinite(v).all():
        v[~np.isfinite(v)] = np.nanmean(v)
    return v


print(f"\n{'target':34s}{'max|Δcoef|':>13s}{'corr':>9s}{'Δintercept':>13s}  판정")
rep = {}
n_ok = 0
for t, m in MP.items():
    y = target_vec(t)
    r = Ridge(alpha=m["ridge_alpha"], fit_intercept=True).fit(Xs, y)
    d = float(np.abs(r.coef_ - np.array(m["ridge_coef"])).max())
    c = float(np.corrcoef(r.coef_, m["ridge_coef"])[0, 1])
    di = float(abs(r.intercept_ - m["ridge_intercept"]))
    ok = "✅" if d < 1e-6 else ("⚠️" if c > 0.95 else "❌")
    n_ok += ok == "✅"
    rep[t] = {"max_abs_coef_diff": d, "coef_corr": c, "intercept_diff": di, "verdict": ok}
    print(f"{t:34s}{d:13.3e}{c:9.4f}{di:13.3e}  {ok}")
print(f"\n완전재현 {n_ok}/{len(MP)}")

out = {"paired_units": len(paired), "paired_speakers": len({s for s, _ in paired}),
       "scaler_shared_across_targets": bool(same), "candidates": res,
       "greedy": {"n": len(cur), "spk": len({s for s, _ in cur}), "err_mean": be},
       "refit_subset": best_name, "n_exact": n_ok, "n_targets": len(MP), "per_target": rep}
(REDIAG / "s4d_mapper_refit.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"saved: {REDIAG/'s4d_mapper_refit.json'}")
