"""
s4a_scaler_forensics.py — 배포 JSON의 scaler_mean/scale 이 어떤 데이터에서 나왔는지 역추적.

목적: 학습 feature matrix X_train 이
  (a) training oral 채널   (b) training phone 채널   (c) 혼합
  중 무엇이었는지 판정. 이후 3/5/6번 작업의 전제가 된다.
"""
from __future__ import annotations

import json
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (SIDE, REDIAG, load_params, load_training_indicators,
                    load_val_indicators)

P = load_params()
FO = P["feature_order"]
TR = load_training_indicators()
VAL, VMETA = load_val_indicators()

# ── 1. scaler_mean 이 6개 모델 간 동일한지 ──
means = {k: np.array(v["scaler_mean"]) for k, v in P["models"].items()}
scales = {k: np.array(v["scaler_scale"]) for k, v in P["models"].items()}
ks = list(means)
ident_mean = all(np.allclose(means[ks[0]], means[k], atol=1e-9) for k in ks)
ident_scale = all(np.allclose(scales[ks[0]], scales[k], atol=1e-9) for k in ks)
print(f"[1] scaler_mean 6모델 동일: {ident_mean}   scaler_scale 동일: {ident_scale}")
if not ident_mean:
    for k in ks:
        print("    ", k, np.round(means[k][:4], 4))
MU = means[ks[0]]
SD = scales[ks[0]]

# ── 2. 후보 코호트별 indicator 평균/표준편차 ──
def cohort_stats(keys):
    """keys: list of TR keys"""
    out = {}
    inds = set()
    for k in keys:
        inds |= set(TR[k])
    for ind in inds:
        v = np.array([TR[k].get(ind, np.nan) for k in keys], dtype=float)
        v = v[np.isfinite(v)]
        if len(v):
            out[ind] = (float(v.mean()), float(v.std(ddof=0)))
    return out

oral_keys = [k for k in TR if k[2] == "oral"]
phone_keys = [k for k in TR if k[2] == "phone"]
paired_oral = [k for k in oral_keys if (k[0], k[1], "phone") in TR]
paired_phone = [(k[0], k[1], "phone") for k in paired_oral]

COH = {
    "train_oral_all(34)":     cohort_stats(oral_keys),
    "train_phone_all(29)":    cohort_stats(phone_keys),
    "train_oral_paired(29)":  cohort_stats(paired_oral),
}
# val 510 phone
val_stats = {}
inds = set()
for s in VAL:
    inds |= set(VAL[s])
for ind in inds:
    v = np.array([VAL[s].get(ind, np.nan) for s in VAL], dtype=float)
    v = v[np.isfinite(v)]
    if len(v):
        val_stats[ind] = (float(v.mean()), float(v.std(ddof=0)))
COH["val510_phone(21)"] = val_stats

# ── 3. feature_order 38개 중 raw indicator 31개만 비교 (_sm 7개는 mapper 산출이라 제외) ──
raw_feats = [f for f in FO if not f.endswith("_sm")]
sm_feats = [f for f in FO if f.endswith("_sm")]
print(f"[2] feature_order {len(FO)} = raw {len(raw_feats)} + _sm {len(sm_feats)}")
print(f"    _sm: {sm_feats}")

rows = []
print(f"\n[3] scaler_mean vs 코호트 평균 — 상대오차 |Δ|/|scaler_mean| (raw 31개)")
hdr = f"{'feature':32s}{'scaler_mean':>14s}" + "".join(f"{c:>24s}" for c in COH)
print(hdr)
summary = {c: [] for c in COH}
for f in raw_feats:
    i = FO.index(f)
    mu = MU[i]
    line = f"{f:32s}{mu:14.5f}"
    for c, st in COH.items():
        if f in st:
            m = st[f][0]
            rel = abs(m - mu) / (abs(mu) + 1e-12)
            summary[c].append(rel)
            line += f"{m:16.5f}({rel*100:5.1f}%)"
        else:
            line += f"{'--':>24s}"
    print(line)
    rows.append(f)

print(f"\n[4] 코호트별 상대오차 중앙값 / 평균 / <1% 개수 (raw {len(raw_feats)}개)")
best = None
for c, v in summary.items():
    v = np.array(v)
    n1 = int((v < 0.01).sum()); n5 = int((v < 0.05).sum())
    print(f"  {c:24s} median={np.median(v)*100:7.2f}%  mean={v.mean()*100:7.2f}%  <1%:{n1:3d}/{len(v)}  <5%:{n5:3d}/{len(v)}")
    if best is None or np.median(v) < best[1]:
        best = (c, float(np.median(v)))
print(f"\n  → 가장 근접한 코호트: {best[0]} (median rel.err {best[1]*100:.2f}%)")

# ── 4. scaler_scale 도 동일 비교 ──
print(f"\n[5] scaler_scale vs 코호트 std — 상대오차 중앙값")
for c, st in COH.items():
    v = []
    for f in raw_feats:
        i = FO.index(f)
        if f in st and abs(SD[i]) > 1e-12:
            v.append(abs(st[f][1] - SD[i]) / abs(SD[i]))
    v = np.array(v)
    print(f"  {c:24s} median={np.median(v)*100:7.2f}%  <1%:{int((v<0.01).sum()):3d}/{len(v)}")

# ── 5. 저장 ──
out = {
    "scaler_identical_across_models": bool(ident_mean and ident_scale),
    "n_features": len(FO), "n_raw": len(raw_feats), "n_sm": len(sm_feats),
    "sm_features": sm_feats,
    "cohort_median_rel_err_mean": {c: float(np.median(v)) for c, v in summary.items()},
    "closest_cohort": best[0],
    "per_feature": {
        f: {"scaler_mean": float(MU[FO.index(f)]), "scaler_scale": float(SD[FO.index(f)]),
            **{c: (COH[c][f] if f in COH[c] else None) for c in COH}}
        for f in raw_feats},
}
(REDIAG / "s4a_scaler_forensics.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s4a_scaler_forensics.json'}")
