"""
s6_oral_vs_phone.py — 작업 6: 도메인 갭 손실량 정량화 (학습 코호트 paired).

동일 (가수,곡) 에 대해 oral / phone 동시 녹음이 있는 unit 을 사용.
  조건 A: oral indicator 직접 입력
  조건 B: phone indicator → phone_to_oral_mapper_v2 경유 (배포 경로와 동일한 변환)
  조건 C: phone indicator 원본 그대로 (mapper 없음) — 참고
같은 라벨·같은 모델 그리드·같은 화자 GroupKFold 중첩 CV 로 corr 비교.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from common import (ITEMS9, REDIAG, ROOT, load_params, load_training_indicators,
                    load_train_labels_by_unit, pearson)
from rebuild import RES, _v1_tables
from grid import GRID

P = load_params()
FO = P["feature_order"]
RAW = [f for f in FO if not f.endswith("_sm")]
TRANS = P["feature_translation"]
TR = load_training_indicators()
LAB = load_train_labels_by_unit()
MP = pickle.load(open(ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
MFEAT = MP[next(iter(MP))]["features"]
em, sa = _v1_tables()
egg = {(e["singer_id"], str(e["song_id"])): e
       for e in json.load(open(RES / "egg_analysis.json"))["results"]}

paired = sorted({(k[0], k[1]) for k in TR if k[2] == "oral"} & {(k[0], k[1]) for k in TR if k[2] == "phone"})
units = [u for u in paired if (u in LAB or (u[0], "") in LAB)]
print(f"paired unit {len(paired)} 중 라벨 보유 {len(units)}  (화자 {len({u[0] for u in units})}명)")
print(f"  라벨 없는 unit: {sorted(set(paired)-set(units))}\n")

_EM = {"cpp_sm": "cpp", "spectral_centroid_sm": "spectral_centroid", "a1_p0_sm": "a1_p0"}
_SA = {"spectral_tilt_sm": "spectral_tilt", "sfr_sm": "singers_formant_ratio"}


def X_oral():
    """조건 A — 33 raw = oral indicator, 5 _sm = oral v1 측정치 (학습 X 와 동일 구성)."""
    X = np.full((len(units), len(FO)), np.nan)
    for i, u in enumerate(units):
        d = TR[(u[0], u[1], "oral")]
        for f in RAW:
            X[i, FO.index(f)] = d.get(f, np.nan)
        for f in _EM:
            e = em.get(u); X[i, FO.index(f)] = e[_EM[f]]["mean"] if e else np.nan
        for f in _SA:
            e = sa.get(u); X[i, FO.index(f)] = e[_SA[f]]["all_voiced"]["mean"] if e else np.nan
    return X


def X_phone(via_mapper: bool):
    """조건 B/C — 33 raw = phone indicator, _sm = mapper 추정(B) / mapper 미적용(C)."""
    X = np.full((len(units), len(FO)), np.nan)
    for i, u in enumerate(units):
        ph = TR[(u[0], u[1], "phone")]
        for f in RAW:
            X[i, FO.index(f)] = ph.get(f, np.nan)
        if via_mapper:
            x = np.array([ph.get(f, 0.0) if np.isfinite(ph.get(f, np.nan)) else 0.0 for f in MFEAT])
            for f in [k for k in FO if k.endswith("_sm")]:
                t = TRANS[f].replace("__mapped", "")
                m = MP[t]
                xs = (x - np.array(m["scaler_mean"])) / np.array(m["scaler_scale"])
                X[i, FO.index(f)] = float(np.dot(np.array(m["ridge_coef"]), xs) + m["ridge_intercept"])
        else:
            # phone 원본에서 직접 얻을 수 있는 것만 (sfr 은 indicators_v2 에 존재)
            X[i, FO.index("sfr_sm")] = ph.get("singers_formant_ratio", np.nan)
            X[i, FO.index("a1_p0_sm")] = ph.get("a1_p0", np.nan)
            for f in ["cpp_sm", "spectral_centroid_sm", "spectral_tilt_sm"]:
                X[i, FO.index(f)] = np.nan          # phone 직접 산출 경로 없음 → s5 에서 별도 처리
    return X


def impute(X):
    X = X.copy()
    for j in range(X.shape[1]):
        m = ~np.isfinite(X[:, j])
        if m.all():
            X[:, j] = 0.0
        elif m.any():
            X[m, j] = np.nanmean(X[:, j])
    return X


Y = {it: np.array([LAB.get(u, LAB.get((u[0], "")))[it] for u in units]) for it in ITEMS9}
G = np.array([u[0] for u in units])
NSPK = len(set(G))


def nested_cv(X, y, groups, k_out=5):
    Xz = (X - X.mean(0)) / np.where(X.std(0, ddof=0) < 1e-12, 1.0, X.std(0, ddof=0))
    gk = GroupKFold(n_splits=k_out)
    oof = np.full(len(y), np.nan)
    for tr, te in gk.split(Xz, y, groups):
        ng = len(set(groups[tr]))
        gi = GroupKFold(n_splits=min(5, ng))
        sc = np.zeros(len(GRID)); cnt = np.zeros(len(GRID))
        for itr, ite in gi.split(Xz[tr], y[tr], groups[tr]):
            for kk, (lab, f) in enumerate(GRID):
                e = f(); e.fit(Xz[tr][itr], y[tr][itr])
                c = pearson(e.predict(Xz[tr][ite]), y[tr][ite])
                if np.isfinite(c):
                    sc[kk] += c; cnt[kk] += 1
        avg = np.where(cnt > 0, sc / np.maximum(cnt, 1), np.nan)
        if not np.isfinite(avg).any():
            continue
        kk = int(np.nanargmax(np.abs(avg)))
        e = GRID[kk][1](); e.fit(Xz[tr], y[tr])
        oof[te] = e.predict(Xz[te]) * (np.sign(avg[kk]) or 1.0)
    m = np.isfinite(oof)
    return pearson(oof[m], y[m])


XA, XB, XC = impute(X_oral()), impute(X_phone(True)), impute(X_phone(False))
print(f"조건 A(oral 직접) / B(phone→mapper) / C(phone raw) — X {XA.shape}, 화자 {NSPK}명, "
      f"화자 GroupKFold({min(5,NSPK)}) 중첩 CV\n")
print(f"{'item':10s}{'A: oral 직접':>14s}{'B: phone→mapper':>18s}{'C: phone raw':>15s}{'A−B (갭 손실)':>16s}")
rep = {}
for it in ITEMS9:
    a = nested_cv(XA, Y[it], G); b = nested_cv(XB, Y[it], G); c = nested_cv(XC, Y[it], G)
    rep[it] = {"A_oral_direct": a, "B_phone_mapper": b, "C_phone_raw": c,
               "gap_A_minus_B": float(a - b)}
    print(f"{it:10s}{a:+14.4f}{b:+18.4f}{c:+15.4f}{a-b:+16.4f}")

va = np.array([rep[i]["A_oral_direct"] for i in ITEMS9])
vb = np.array([rep[i]["B_phone_mapper"] for i in ITEMS9])
vc = np.array([rep[i]["C_phone_raw"] for i in ITEMS9])
print(f"\n9항목 평균: A={va.mean():+.4f}  B={vb.mean():+.4f}  C={vc.mean():+.4f}"
      f"   → 도메인 갭 평균 손실 A−B = {va.mean()-vb.mean():+.4f}")
rep["_summary"] = {"n_units": len(units), "n_speakers": NSPK,
                   "mean_A": float(va.mean()), "mean_B": float(vb.mean()),
                   "mean_C": float(vc.mean()), "mean_gap": float(va.mean() - vb.mean())}
(REDIAG / "s6_oral_vs_phone.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s6_oral_vs_phone.json'}")
