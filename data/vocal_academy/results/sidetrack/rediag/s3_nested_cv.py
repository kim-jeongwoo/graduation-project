"""
s3_nested_cv.py — 작업 3: 선택 절차를 포함한 정직한 추정 (중첩 CV).

3-A (주): 배포 절차의 편향을 직접 격리.
    계수는 고정된 학습 24 unit 에서만 적합 (val 과 무관) → 24 config 은 항목당 1회만 적합.
    편향의 유일한 출처는 "val 로 config 을 고른 것".
    외부 루프: 5/10 화자 GroupKFold(5) × 20 반복.
    내부(=외부 fold 제외 화자)에서만 |corr| 최대 config 선택 → 외부 fold 예측.
    OOF 예측 전체를 모아 corr 산출.

3-B: 학습 코호트 자체의 정직한 성능 (화자 GroupKFold 중첩 CV).
    기존 train_5fold_mean 은 unit 단위 KFold → 같은 화자가 train/test 에 동시 등장.
    이를 화자 단위로 바로잡은 값과 나란히 비교.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold, GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from common import ITEMS9, REDIAG, load_params, pearson
from rebuild import build_train, build_val
from grid import GRID, LABELS

RNG = np.random.default_rng(20260726)
N_REPEAT = 20
P = load_params()

X, Y, units, groups = build_train()
mu, sd = X.mean(0), X.std(0, ddof=0)
Xs = (X - mu) / sd
Xv, Yv, subs, leaked, grp = build_val()
Xvs = (Xv - mu) / sd
NL = ~leaked
NV = len(subs)

# ── 24 config 예측 (항목당 1회 적합; val 과 독립) ──
PRED = {}
for it in ITEMS9:
    ps = []
    for lab, f in GRID:
        e = f(); e.fit(Xs, Y[it])
        ps.append(e.predict(Xvs))
    PRED[it] = np.array(ps)

# ══ 3-A ══
print("[3-A] 5/10 화자 GroupKFold 중첩 선택 (외부 5-fold × 20 반복)")
print(f"{'item':9s}{'배포 val_total':>15s}{'nested val_total':>18s}{'Δ':>9s}{'nested full21':>16s}")
repA = {}
for it in ITEMS9:
    preds = PRED[it]
    fin = np.array([np.isfinite(pearson(p[NL], Yv[it][NL])) for p in preds])
    oof_all, oof21_all = [], []
    for rep in range(N_REPEAT):
        order = RNG.permutation(NV)
        folds = np.array_split(order, 5)
        oof = np.full(NV, np.nan)
        for te in folds:
            tr = np.setdiff1d(np.arange(NV), te)
            # 내부: 선택에 외부 fold 를 쓰지 않음
            cs = np.array([pearson(preds[k][tr], Yv[it][tr]) if fin[k] else np.nan
                           for k in range(len(preds))])
            if not np.isfinite(cs).any():
                continue
            k = int(np.nanargmax(np.abs(cs)))
            sgn = np.sign(cs[k]) or 1.0
            oof[te] = preds[k][te] * sgn          # 선택된 부호로 정렬
        m = np.isfinite(oof)
        oof_all.append(pearson(oof[m & NL], Yv[it][m & NL]))
        oof21_all.append(pearson(oof[m], Yv[it][m]))
    nested = float(np.nanmean(oof_all)); nested_sd = float(np.nanstd(oof_all))
    nested21 = float(np.nanmean(oof21_all))
    dep = P["models"][it]["validation_corr"]["val_total"] if it in P["models"] else None
    repA[it] = {"deployed_val_total": dep, "nested_val_total_mean": nested,
                "nested_val_total_std": nested_sd, "nested_full21_mean": nested21,
                "n_repeat": N_REPEAT}
    d = f"{nested-dep:+.3f}" if dep is not None else "-"
    ds = f"{dep:+.4f}" if dep is not None else "(모델없음)"
    print(f"{it:9s}{ds:>15s}{nested:+13.4f}±{nested_sd:.3f}{d:>9s}{nested21:+16.4f}")

# ══ 3-B ══
print("\n[3-B] 학습 코호트 정직 추정 — 화자 GroupKFold 중첩 CV vs 기존 unit-KFold")
print(f"{'item':9s}{'배포 train_5fold':>18s}{'unit-KFold(재현)':>18s}{'화자 nested CV':>17s}")
repB = {}
gk_out = GroupKFold(n_splits=6)
for it in ITEMS9:
    y = Y[it]
    # (a) 기존 방식 재현: unit 단위 KFold(5), 선택 없음 — 배포 config 사용
    naive = []
    if it in P["models"]:
        cfg = None
        mt, mp = P["models"][it]["model_type"], P["models"][it]["model_params"]
        for lab, f in GRID:
            e = f()
            if type(e).__name__ == mt and abs(getattr(e, "alpha", -1) - mp.get("alpha", -1)) < 1e-12 \
               and (not hasattr(e, "l1_ratio") or abs(e.l1_ratio - mp.get("l1_ratio", e.l1_ratio)) < 1e-12):
                cfg = f; break
        if cfg is None:
            cfg = GRID[0][1]
        for seed in range(N_REPEAT):
            kf = KFold(5, shuffle=True, random_state=seed)
            cs = []
            for tr, te in kf.split(Xs):
                e = cfg(); e.fit(Xs[tr], y[tr]); cs.append(pearson(e.predict(Xs[te]), y[te]))
            naive.append(np.nanmean(cs))
    naive_m = float(np.nanmean(naive)) if naive else np.nan

    # (b) 화자 GroupKFold 중첩 CV (내부에서 config 선택)
    oof = np.full(len(y), np.nan)
    for tr, te in gk_out.split(Xs, y, groups):
        gi = GroupKFold(n_splits=min(5, len(set(groups[tr]))))
        sc = np.zeros(len(GRID)); cnt = np.zeros(len(GRID))
        for itr, ite in gi.split(Xs[tr], y[tr], groups[tr]):
            for k, (lab, f) in enumerate(GRID):
                e = f(); e.fit(Xs[tr][itr], y[tr][itr])
                c = pearson(e.predict(Xs[tr][ite]), y[tr][ite])
                if np.isfinite(c):
                    sc[k] += c; cnt[k] += 1
        avg = np.where(cnt > 0, sc / np.maximum(cnt, 1), np.nan)
        if not np.isfinite(avg).any():
            continue
        k = int(np.nanargmax(np.abs(avg)))
        e = GRID[k][1](); e.fit(Xs[tr], y[tr])
        oof[te] = e.predict(Xs[te]) * (np.sign(avg[k]) or 1.0)
    m = np.isfinite(oof)
    nested = pearson(oof[m], y[m])
    dep = P["models"][it]["validation_corr"]["train_5fold_mean"] if it in P["models"] else None
    repB[it] = {"deployed_train_5fold": dep, "unit_kfold_reproduced": naive_m,
                "speaker_nested_cv": nested}
    ds = f"{dep:+.4f}" if dep is not None else "(모델없음)"
    print(f"{it:9s}{ds:>18s}{naive_m:+18.4f}{nested:+17.4f}")

(REDIAG / "s3_nested_cv.json").write_text(json.dumps(
    {"A_val_selection_nested": repA, "B_train_cohort_nested": repB},
    ensure_ascii=False, indent=1))
print(f"\nsaved: {REDIAG/'s3_nested_cv.json'}")
