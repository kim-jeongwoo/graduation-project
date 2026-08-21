"""
rebuild.py — 배포 X_train / X_val 을 원자료에서 재구성 (진단 2단계 공용 모듈).

s4a/s4b 결과로 확정된 사실:
  - X_train = indicators_v2_training.csv 의 **oral 채널, singer 1~12, 24 unit**
    (scaler_mean/scale 33개 raw feature 를 오차 3e-13 으로 정확 재현)
  - _sm 5개는 v1 파이프라인 산출물에서 옴:
      cpp_sm / spectral_centroid_sm / a1_p0_sm ← results/extra_metrics.json (oral)
      spectral_tilt_sm / sfr_sm               ← results/spectral_analysis.json ['all_voiced']['mean']
    ※ spectral_analysis.json 은 phone pair 가 있으면 source='phone' 을 기록 → _sm 2개는
      학습 시점부터 phone 유래. (source='oral' 은 5 unit 뿐)
  - unit (6,'8') 은 v1 JSON 에서 누락 → 평균 대체(mean imputation)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import (ITEMS9, SIDE, VA, ROOT, load_params, load_training_indicators,
                    load_train_labels_by_unit, load_val_indicators, load_val_labels)

RES = ROOT / "data/vocal_academy/results"
P = load_params()
FO = P["feature_order"]
RAW = [f for f in FO if not f.endswith("_sm")]
SM = [f for f in FO if f.endswith("_sm")]

_EM_KEY = {"cpp_sm": "cpp", "spectral_centroid_sm": "spectral_centroid", "a1_p0_sm": "a1_p0"}
_SA_KEY = {"spectral_tilt_sm": "spectral_tilt", "sfr_sm": "singers_formant_ratio"}


def _v1_tables():
    em = {}
    for e in json.load(open(RES / "extra_metrics.json"))["results"]:
        if e["file"].endswith("_oral.wav"):
            em[(e["singer_id"], str(e["song_id"]))] = e
    sa = {}
    for e in json.load(open(RES / "spectral_analysis.json"))["results"]:
        sa[(e["singer_id"], str(e["song_id"]))] = e
    return em, sa


def build_train():
    """→ X (24,38), y {item: (24,)}, units, groups(화자)"""
    TR = load_training_indicators()
    LAB = load_train_labels_by_unit()
    em, sa = _v1_tables()

    units = sorted({(k[0], k[1]) for k in TR if k[2] == "oral" and k[0] <= 12})
    X = np.full((len(units), len(FO)), np.nan)
    for i, u in enumerate(units):
        d = TR[(u[0], u[1], "oral")]
        for f in RAW:
            X[i, FO.index(f)] = d.get(f, np.nan)
        for f in SM:
            if f in _EM_KEY:
                e = em.get(u)
                X[i, FO.index(f)] = e[_EM_KEY[f]]["mean"] if e else np.nan
            else:
                e = sa.get(u)
                X[i, FO.index(f)] = e[_SA_KEY[f]]["all_voiced"]["mean"] if e else np.nan
    # 평균 대체 (누락 unit 6-8)
    for j in range(X.shape[1]):
        m = ~np.isfinite(X[:, j])
        if m.any():
            X[m, j] = np.nanmean(X[:, j])

    y = {}
    for it in ITEMS9:
        y[it] = np.array([LAB.get((u[0], u[1]), LAB.get((u[0], "")))[it] for u in units])
    groups = np.array([u[0] for u in units])
    return X, y, units, groups


def build_val(mapper_pkl: str | None = None):
    """5/10 검증 21명 → X_val (21,38). 배포 경로와 동일하게 raw phone + Ridge mapper 사용."""
    import pickle
    VAL, VMETA = load_val_indicators()
    labs = load_val_labels()
    mp = pickle.load(open(mapper_pkl or
                          ROOT / "dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl", "rb"))
    mfeat = mp[next(iter(mp))]["features"]
    trans = P["feature_translation"]

    subs = sorted(VAL)
    X = np.full((len(subs), len(FO)), np.nan)
    for i, s in enumerate(subs):
        ph = VAL[s]
        x = np.array([ph.get(f, 0.0) if ph.get(f) is not None and np.isfinite(ph.get(f, np.nan))
                      else 0.0 for f in mfeat])
        mapped = {}
        for tgt, m in mp.items():
            xs = (x - np.array(m["scaler_mean"])) / np.array(m["scaler_scale"])
            mapped[f"{tgt}__mapped"] = float(np.dot(np.array(m["ridge_coef"]), xs) + m["ridge_intercept"])
        for f in FO:
            if f in trans:
                v = mapped.get(trans[f], 0.0)
            elif f + "__mapped" in mapped:
                v = mapped[f + "__mapped"]
            elif f in ph and np.isfinite(ph.get(f, np.nan)):
                v = ph[f]
            else:
                v = 0.0
            X[i, FO.index(f)] = v
    y = {it: np.array([labs[s][it] for s in subs]) for it in ITEMS9}
    leaked = np.array([VMETA[s]["is_leaked"] for s in subs])
    group = np.array([VMETA[s]["group"] for s in subs])
    return X, y, subs, leaked, group


if __name__ == "__main__":
    X, y, units, g = build_train()
    print(f"X_train {X.shape}  units={len(units)}  speakers={len(set(g))}")
    mu, sd = X.mean(0), X.std(0, ddof=0)
    tmu = np.array(P["models"]["접촉강도"]["scaler_mean"])
    tsd = np.array(P["models"]["접촉강도"]["scaler_scale"])
    print(f"scaler_mean  max|Δ| = {np.abs(mu-tmu).max():.3e}")
    print(f"scaler_scale max|Δ| = {np.abs(sd-tsd).max():.3e}")
    worst = int(np.argmax(np.abs(sd - tsd)))
    print(f"  worst scale feature: {FO[worst]}  got {sd[worst]:.6f} vs {tsd[worst]:.6f}")
    for it in ["접촉강도", "호흡식별", "연구개위치", "비강사용", "전방공명"]:
        print(f"  y[{it}] mean={y[it].mean():.10f}  json intercept={P['models'][it]['intercept']:.10f}")
    Xv, yv, subs, lk, gr = build_val()
    print(f"\nX_val {Xv.shape}  leaked={lk.sum()}  A={(gr=='A').sum()} B={(gr=='B').sum()}")
