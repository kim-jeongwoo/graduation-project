"""
s4e_mapper_subset.py — mapper scaler_mean 을 정확히 재현하는 pair subset 전수 탐색.
문서(16명/25쌍) vs CSV(19명/29쌍) 판정 (작업 7).
"""
from __future__ import annotations

import itertools
import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, ROOT, load_training_indicators

MP = pickle.load(open(ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
FEAT = MP[next(iter(MP))]["features"]
TMU = np.array(MP[next(iter(MP))]["scaler_mean"])
TSD = np.array(MP[next(iter(MP))]["scaler_scale"])
TR = load_training_indicators()

paired = sorted({(k[0], k[1]) for k in TR if k[2] == "oral"} & {(k[0], k[1]) for k in TR if k[2] == "phone"})
M = np.array([[TR[(u[0], u[1], "phone")].get(f, np.nan) for f in FEAT] for u in paired], dtype=float)
for j in range(M.shape[1]):
    m = ~np.isfinite(M[:, j])
    if m.any():
        M[m, j] = np.nanmean(M[:, j])
spk = np.array([u[0] for u in paired])
SPK = sorted(set(spk))
print(f"paired units={len(paired)} speakers={len(SPK)} {SPK}")


def score(idx):
    if len(idx) < 2:
        return 9e9, 9e9
    mu = M[idx].mean(0); sd = M[idx].std(0, ddof=0)
    return (float(np.median(np.abs(mu - TMU) / (np.abs(TMU) + 1e-12))),
            float(np.median(np.abs(sd - TSD) / (np.abs(TSD) + 1e-12))))


best = []
# ── A. 화자 단위 제외 (0~4명 제외) ──
print("\n[A] 화자 제외 조합 전수 탐색")
for r in range(0, 5):
    bb = None
    for drop in itertools.combinations(SPK, r):
        idx = np.where(~np.isin(spk, drop))[0]
        e = score(idx)
        if bb is None or e[0] < bb[0][0]:
            bb = (e, drop, len(idx))
    print(f"  제외 {r}명: best rel.err mean={bb[0][0]*100:8.5f}%  std={bb[0][1]*100:8.5f}%  "
          f"n_units={bb[2]} spk={len(SPK)-r} drop={bb[1]}")
    best.append({"n_drop_spk": r, "err_mean": bb[0][0], "err_std": bb[0][1],
                 "n_units": bb[2], "n_spk": len(SPK) - r, "dropped": list(bb[1])})

# ── B. unit 단위 제외 (0~4개) ──
print("\n[B] unit 제외 조합 전수 탐색")
allidx = list(range(len(paired)))
for r in range(0, 5):
    bb = None
    for drop in itertools.combinations(allidx, r):
        idx = np.array([i for i in allidx if i not in drop])
        e = score(idx)
        if bb is None or e[0] < bb[0][0]:
            bb = (e, drop, len(idx))
    du = [paired[i] for i in bb[1]]
    print(f"  제외 {r}개: best rel.err mean={bb[0][0]*100:8.5f}%  std={bb[0][1]*100:8.5f}%  "
          f"n={bb[2]} spk={len({paired[i][0] for i in allidx if i not in bb[1]})} drop={du}")

# ── C. 화자 단위 평균 후 회귀 (unit 대신 speaker 사용) 가설 ──
print("\n[C] 화자 단위 평균 가설")
sp_rows = np.array([M[spk == s].mean(0) for s in SPK])
mu = sp_rows.mean(0); sd = sp_rows.std(0, ddof=0)
print(f"  전체 19명 화자평균: rel.err mean={np.median(np.abs(mu-TMU)/(np.abs(TMU)+1e-12))*100:.5f}%"
      f"  std={np.median(np.abs(sd-TSD)/(np.abs(TSD)+1e-12))*100:.5f}%")
bb = None
for r in range(0, 4):
    for drop in itertools.combinations(range(len(SPK)), r):
        sel = np.array([i for i in range(len(SPK)) if i not in drop])
        if len(sel) < 3:
            continue
        m2 = sp_rows[sel].mean(0); s2 = sp_rows[sel].std(0, ddof=0)
        e = float(np.median(np.abs(m2 - TMU) / (np.abs(TMU) + 1e-12)))
        if bb is None or e < bb[0]:
            bb = (e, drop, len(sel))
print(f"  최적(≤3명 제외): rel.err mean={bb[0]*100:.5f}%  n_spk={bb[2]} drop={[SPK[i] for i in bb[1]]}")

# ── D. 특정 feature 로 직접 검산 ──
print("\n[D] 개별 feature 검산 (paired 29 전체 기준)")
mu29 = M.mean(0)
for f in ["hnr", "shimmer_local", "F2", "spectral_entropy", "singers_formant_ratio"]:
    j = FEAT.index(f)
    print(f"  {f:24s} target={TMU[j]:12.6f}  paired29={mu29[j]:12.6f}  Δ={TMU[j]-mu29[j]:+.6f}")

# ── E. 확정 subset 으로 27 target Ridge 재적합 ──
from sklearn.linear_model import Ridge
from rebuild import RES, _v1_tables

DROP = [(6, '8'), (9, '10'), (13, '4'), (15, '2')]
U = [u for u in paired if u not in DROP]
idx = np.array([paired.index(u) for u in U])
print(f"\n[E] 확정 subset n={len(U)} spk={len({s for s,_ in U})} 으로 27 target 재적합")
Xs = (M[idx] - M[idx].mean(0)) / M[idx].std(0, ddof=0)

em, sa = _v1_tables()
egg = {(e["singer_id"], str(e["song_id"])): e
       for e in json.load(open(RES / "egg_analysis.json"))["results"]}
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


rep = {}; n_ok = 0
print(f"{'target':34s}{'max|Δcoef|':>13s}{'corr':>9s}  판정")
for t, m in MP.items():
    r = Ridge(alpha=m["ridge_alpha"], fit_intercept=True).fit(Xs, target_vec(t))
    d = float(np.abs(r.coef_ - np.array(m["ridge_coef"])).max())
    c = float(np.corrcoef(r.coef_, m["ridge_coef"])[0, 1])
    ok = "✅" if d < 1e-6 else ("⚠️" if c > 0.95 else "❌")
    n_ok += ok == "✅"
    rep[t] = {"max_abs_coef_diff": d, "coef_corr": c, "verdict": ok}
    print(f"{t:34s}{d:13.3e}{c:9.4f}  {ok}")
print(f"\n완전재현 {n_ok}/{len(MP)}")

def _s(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (list, tuple)): return [_s(x) for x in o]
    if isinstance(o, dict): return {str(k): _s(v) for k, v in o.items()}
    return o

out = {"paired_units": len(paired), "paired_speakers": len(SPK),
       "speaker_drop_search": best,
       "exact_subset": {"n_units": len(U), "n_speakers": len({s for s, _ in U}),
                        "dropped_units": [list(map(str, d)) for d in DROP]},
       "refit_exact": n_ok, "n_targets": len(MP), "per_target": rep}
(REDIAG / "s4e_mapper_subset.json").write_text(json.dumps(_s(out), ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s4e_mapper_subset.json'}")
