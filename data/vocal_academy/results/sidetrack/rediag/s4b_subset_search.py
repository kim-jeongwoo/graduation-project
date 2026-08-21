"""
s4b_subset_search.py — scaler_mean 을 정확히 재현하는 학습 subset 탐색.

sign_reversal_analysis.md 는 "학습 5-fold CV (n=24)" 라고 기술 → n=24 후보 우선 검증.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import (REDIAG, load_params, load_training_indicators,
                    load_train_labels_by_unit, load_val_indicators)

P = load_params()
FO = P["feature_order"]
RAW = [f for f in FO if not f.endswith("_sm")]
MU = np.array(P["models"]["접촉강도"]["scaler_mean"])
SD = np.array(P["models"]["접촉강도"]["scaler_scale"])
IDX = {f: FO.index(f) for f in RAW}

TR = load_training_indicators()
LAB = load_train_labels_by_unit()

oral = sorted([k for k in TR if k[2] == "oral"])
phone_units = {(k[0], k[1]) for k in TR if k[2] == "phone"}


def labelled(k):
    """(singer, song) 또는 (singer,'') 로 라벨이 존재하는지"""
    return (k[0], k[1]) in LAB or (k[0], "") in LAB


def stats(keys):
    mu = np.full(len(RAW), np.nan); sd = np.full(len(RAW), np.nan)
    for j, f in enumerate(RAW):
        v = np.array([TR[k].get(f, np.nan) for k in keys], dtype=float)
        v = v[np.isfinite(v)]
        if len(v):
            mu[j] = v.mean(); sd[j] = v.std(ddof=0)
    return mu, sd


def err(keys):
    mu, sd = stats(keys)
    tgt_mu = np.array([MU[IDX[f]] for f in RAW])
    tgt_sd = np.array([SD[IDX[f]] for f in RAW])
    m = np.isfinite(mu)
    e_mu = np.median(np.abs(mu[m] - tgt_mu[m]) / (np.abs(tgt_mu[m]) + 1e-12))
    e_sd = np.median(np.abs(sd[m] - tgt_sd[m]) / (np.abs(tgt_sd[m]) + 1e-12))
    return e_mu, e_sd


CANDS = {
    "oral_all(34)":                 oral,
    "oral_paired_with_phone(29)":   [k for k in oral if (k[0], k[1]) in phone_units],
    "oral_labelled":                [k for k in oral if labelled(k)],
    "oral_labelled_and_paired":     [k for k in oral if labelled(k) and (k[0], k[1]) in phone_units],
    "oral_singers_1_12":            [k for k in oral if k[0] <= 12],
    "oral_singers_13_22":           [k for k in oral if k[0] >= 13],
    "oral_not_leaked":              [k for k in oral if k[0] not in (4, 9, 13, 15)],
}
# 화자 단위 평균 버전
def speaker_avg(keys):
    by = {}
    for k in keys:
        by.setdefault(k[0], []).append(k)
    out = {}
    for s, ks in by.items():
        d = {}
        for f in RAW:
            v = np.array([TR[k].get(f, np.nan) for k in ks], dtype=float)
            v = v[np.isfinite(v)]
            if len(v):
                d[f] = v.mean()
        out[("SPK", s, "oral")] = d
    return out


print(f"target scaler_mean/scale from mapping_params_v2.json (raw {len(RAW)} feats)\n")
print(f"{'candidate':34s}{'n':>4s}{'median rel.err mean':>22s}{'median rel.err std':>22s}")
res = {}
for name, keys in CANDS.items():
    if not keys:
        continue
    e_mu, e_sd = err(keys)
    res[name] = (len(keys), e_mu, e_sd)
    print(f"{name:34s}{len(keys):4d}{e_mu*100:21.3f}%{e_sd*100:21.3f}%")

# 화자단위 평균 후보
for base, keys in [("oral_all", oral),
                   ("oral_paired", [k for k in oral if (k[0], k[1]) in phone_units])]:
    sp = speaker_avg(keys)
    TR.update(sp)
    ks = list(sp)
    e_mu, e_sd = err(ks)
    name = f"SPKavg_{base}"
    res[name] = (len(ks), e_mu, e_sd)
    print(f"{name:34s}{len(ks):4d}{e_mu*100:21.3f}%{e_sd*100:21.3f}%")

print("\n[탐욕 탐색] oral 34 unit 중 scaler_mean 을 최소화하는 subset (leave-one-out 반복)")
cur = list(oral)
best_e = err(cur)[0]
hist = [(len(cur), best_e)]
while len(cur) > 8:
    cands = [(err([k for k in cur if k != d])[0], d) for d in cur]
    e, d = min(cands)
    if e >= best_e:
        break
    cur = [k for k in cur if k != d]
    best_e = e
    hist.append((len(cur), e))
print(f"  최소 도달: n={len(cur)}  median rel.err={best_e*100:.4f}%")
print(f"  제외된 unit: {sorted(set(oral)-set(cur))}")
print(f"  경로: {[(n, round(e*100,3)) for n, e in hist]}")
e_mu, e_sd = err(cur)
print(f"  해당 subset 의 std 재현 오차: {e_sd*100:.3f}%")

out = {"candidates": {k: {"n": v[0], "median_rel_err_mean": v[1],
                          "median_rel_err_std": v[2]} for k, v in res.items()},
       "greedy_best": {"n": len(cur), "median_rel_err_mean": float(best_e),
                       "median_rel_err_std": float(e_sd),
                       "excluded_units": [list(map(str, k)) for k in sorted(set(oral) - set(cur))]}}
(REDIAG / "s4b_subset_search.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s4b_subset_search.json'}")
