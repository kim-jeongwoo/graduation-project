"""
s6b — 작업 6 정정판: 도메인 갭 손실량을 **누설 없이** 산출.

s6 의 조건 B 문제: phone_to_oral_mapper_v2.pkl 은 이 29쌍 중 25쌍으로 학습됨.
→ 배포 pkl 을 그대로 쓰면 mapper 가 정답(oral)을 이미 본 상태(in-sample).

정정: 외부 fold 마다 mapper 를 그 fold 의 학습 화자만으로 재적합.
  A  : oral indicator 직접 입력
  B' : phone → (fold 내 재적합 mapper) 경유
  C  : phone raw (mapper 없음)
모두 동일 화자 GroupKFold, 동일 config 그리드, 반복 10회(화자 배정 셔플).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, load_params, load_training_indicators, load_train_labels_by_unit, pearson
from rebuild import RES, _v1_tables, FO
from grid import GRID as _G
GRID = [g for g in _G if not g[0].startswith(("RF_","GB_"))]

RNG = np.random.default_rng(20260726)
NREP = 10
P = load_params()
RAW = [f for f in FO if not f.endswith("_sm")]
SM = [f for f in FO if f.endswith("_sm")]
TRANS = P["feature_translation"]
_EM = {"cpp_sm": "cpp", "spectral_centroid_sm": "spectral_centroid", "a1_p0_sm": "a1_p0"}
_SA = {"spectral_tilt_sm": "spectral_tilt", "sfr_sm": "singers_formant_ratio"}

TR = load_training_indicators()
LAB = load_train_labels_by_unit()
em, sa = _v1_tables()
units = sorted({(k[0], k[1]) for k in TR if k[2] == "oral"} & {(k[0], k[1]) for k in TR if k[2] == "phone"})
G = np.array([u[0] for u in units])
SPK = sorted(set(G))
print(f"paired {len(units)} unit / {len(SPK)} 화자, 반복 {NREP}회 × 화자 GroupKFold(5)\n")

# 원자료 행렬
PH = np.array([[TR[(u[0], u[1], "phone")].get(f, np.nan) for f in RAW] for u in units])
OR = np.array([[TR[(u[0], u[1], "oral")].get(f, np.nan) for f in RAW] for u in units])
SM_ORAL = np.full((len(units), len(SM)), np.nan)     # oral 실측 _sm (= mapper 의 정답)
for i, u in enumerate(units):
    for j, f in enumerate(SM):
        e = em.get(u) if f in _EM else sa.get(u)
        if e is not None:
            SM_ORAL[i, j] = e[_EM[f]]["mean"] if f in _EM else e[_SA[f]]["all_voiced"]["mean"]


def imp(M, ref=None):
    M = M.copy()
    src = ref if ref is not None else M
    for j in range(M.shape[1]):
        m = ~np.isfinite(M[:, j])
        if m.any():
            v = np.nanmean(src[:, j])
            M[m, j] = 0.0 if not np.isfinite(v) else v
    return M


PH, OR, SM_ORAL = imp(PH), imp(OR), imp(SM_ORAL)

# 조건 C 용: phone 에서 직접 얻을 수 있는 _sm (sfr / a1_p0) 만 채우고 나머지는 0
SM_RAW = np.zeros((len(units), len(SM)))
for j, f in enumerate(SM):
    src = {"sfr_sm": "singers_formant_ratio", "a1_p0_sm": "a1_p0"}.get(f)
    if src:
        SM_RAW[:, j] = [TR[(u[0], u[1], "phone")].get(src, np.nan) for u in units]
SM_RAW = np.nan_to_num(imp(SM_RAW), nan=0.0, posinf=0.0, neginf=0.0)
assert np.isfinite(PH).all() and np.isfinite(OR).all() and np.isfinite(SM_ORAL).all() \
    and np.isfinite(SM_RAW).all(), "NaN 잔존"
Y = {it: np.array([LAB.get(u, LAB.get((u[0], "")))[it] for u in units]) for it in ITEMS9}


def fit_mapper(tr):
    """tr 인덱스만으로 phone(33) → oral _sm(5) Ridge(alpha=1) 재적합."""
    mu, sd = PH[tr].mean(0), PH[tr].std(0, ddof=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    Z = (PH[tr] - mu) / sd
    Ms = [Ridge(alpha=1.0).fit(Z, SM_ORAL[tr, j]) for j in range(len(SM))]
    return mu, sd, Ms


def apply_mapper(mp, idx):
    mu, sd, Ms = mp
    Z = (PH[idx] - mu) / sd
    return np.column_stack([m.predict(Z) for m in Ms])


def build(cond, tr, te, mp=None):
    """조건별 X_train / X_test 반환 (38열)."""
    if cond == "A":
        return np.hstack([OR[tr], SM_ORAL[tr]]), np.hstack([OR[te], SM_ORAL[te]])
    if cond == "B":
        return (np.hstack([PH[tr], apply_mapper(mp, tr)]),
                np.hstack([PH[te], apply_mapper(mp, te)]))
    # C: phone raw — _sm 자리에 phone 에서 얻을 수 있는 것만, 나머지는 0
    return np.hstack([PH[tr], SM_RAW[tr]]), np.hstack([PH[te], SM_RAW[te]])


def run(cond, y, rep_seed):
    rng = np.random.default_rng(rep_seed)
    order = rng.permutation(SPK)
    folds = np.array_split(order, 5)
    oof = np.full(len(y), np.nan)
    for fs in folds:
        te = np.where(np.isin(G, fs))[0]
        tr = np.where(~np.isin(G, fs))[0]
        if len(te) < 1 or len(tr) < 6:
            continue
        mp = fit_mapper(tr) if cond == "B" else None
        Xtr, Xte = build(cond, tr, te, mp)
        mu, sd = Xtr.mean(0), Xtr.std(0, ddof=0)
        sd = np.where(sd < 1e-12, 1.0, sd)
        Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
        # 내부 화자 CV 로 config 선택
        itr_spk = np.array(sorted(set(G[tr])))
        ifolds = np.array_split(rng.permutation(itr_spk), min(4, len(itr_spk)))
        sc = np.zeros(len(GRID)); cnt = np.zeros(len(GRID))
        for ifs in ifolds:
            ite = np.where(np.isin(G[tr], ifs))[0]
            iit = np.where(~np.isin(G[tr], ifs))[0]
            if len(ite) < 2 or len(iit) < 5:
                continue
            for k, (lab, f) in enumerate(GRID):
                e = f(); e.fit(Ztr[iit], y[tr][iit])
                c = pearson(e.predict(Ztr[ite]), y[tr][ite])
                if np.isfinite(c):
                    sc[k] += c; cnt[k] += 1
        avg = np.where(cnt > 0, sc / np.maximum(cnt, 1), np.nan)
        if not np.isfinite(avg).any():
            continue
        k = int(np.nanargmax(np.abs(avg)))
        e = GRID[k][1](); e.fit(Ztr, y[tr])
        oof[te] = e.predict(Zte) * (np.sign(avg[k]) or 1.0)
    m = np.isfinite(oof)
    return pearson(oof[m], y[m])


print(f"{'item':10s}{'A: oral 직접':>16s}{'B: phone→mapper(재적합)':>24s}{'C: phone raw':>16s}{'A−B':>10s}")
rep = {}
for it in ITEMS9:
    a = [run("A", Y[it], 100 + r) for r in range(NREP)]
    b = [run("B", Y[it], 100 + r) for r in range(NREP)]
    c = [run("C", Y[it], 100 + r) for r in range(NREP)]
    am, bm, cm = np.nanmean(a), np.nanmean(b), np.nanmean(c)
    rep[it] = {"A_oral_direct": float(am), "A_sd": float(np.nanstd(a)),
               "B_phone_mapper_refit": float(bm), "B_sd": float(np.nanstd(b)),
               "C_phone_raw": float(cm), "C_sd": float(np.nanstd(c)),
               "gap_A_minus_B": float(am - bm)}
    print(f"{it:10s}{am:+11.4f}±{np.nanstd(a):.3f}{bm:+19.4f}±{np.nanstd(b):.3f}"
          f"{cm:+11.4f}±{np.nanstd(c):.3f}{am-bm:+10.4f}")

A = np.array([rep[i]["A_oral_direct"] for i in ITEMS9])
B = np.array([rep[i]["B_phone_mapper_refit"] for i in ITEMS9])
C = np.array([rep[i]["C_phone_raw"] for i in ITEMS9])
print(f"\n9항목 평균: A={A.mean():+.4f}  B={B.mean():+.4f}  C={C.mean():+.4f}")
print(f"도메인 갭 평균 손실 (A−B) = {A.mean()-B.mean():+.4f}")
sh = ["접촉강도", "호흡식별", "연구개위치", "혀경직도"]
print(f"표시 4항목: A={np.mean([rep[i]['A_oral_direct'] for i in sh]):+.4f}  "
      f"B={np.mean([rep[i]['B_phone_mapper_refit'] for i in sh]):+.4f}  "
      f"C={np.mean([rep[i]['C_phone_raw'] for i in sh]):+.4f}")
rep["_summary"] = {"n_units": len(units), "n_speakers": len(SPK), "n_repeat": NREP,
                   "mean_A": float(A.mean()), "mean_B": float(B.mean()), "mean_C": float(C.mean()),
                   "mean_gap_A_minus_B": float(A.mean() - B.mean())}
(REDIAG / "s6c_oral_vs_phone_linear.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s6c_oral_vs_phone_linear.json'}")
