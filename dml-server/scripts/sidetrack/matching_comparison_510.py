"""
matching_comparison_510.py — per-register vs per-session 매칭 비교 (5/10 데이터)

per-register (현행 score_mapper):
  학습 데이터 (singer, song, register) pairs → percentile 매핑
  → 5/10 raw indicator에 직접 적용

per-session (정의 A: within-singer z-score):
  학습 데이터 (singer, song) session 내 3 register indicator를 z-score 정규화
  → (z-score, trainer_score) pair로 percentile 매핑 학습
  → 5/10 within-singer z-score에 적용

비교 단위: (singer, register), n=63
지표: Pearson correlation (모델 점수 vs 평가자 5명 평균)

⚠ 한계: 학습 데이터의 cpp/spectral_centroid는 register-invariant (per-file)
  → 호흡식별/전방공명/연구개위치는 per-session z-score 모두 0 → 매핑 불가
  → per-session 효과는 cq_mean(흉성두성)/cq_peak(접촉강도)/spectral_tilt(상압하압) 3항목만 의미

부수 진단:
  전방공명 (spectral_centroid_mean) 분포 — 학습 vs 5/10 비교 → 클리핑 원인
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/home/dmlserver/projects/egg_prediction")
AI_SCORES_JSON  = ROOT / "data/vocal_academy/results/ai_scores.json"
INFER_DIR       = ROOT / "data/vocal_academy/results/sidetrack/inference_510"
TRAINER_510_CSV = ROOT / "data/vocal_academy/trainer_scores_510.csv"
OUT_DIR         = ROOT / "data/vocal_academy/results/sidetrack"

# 9항목 → indicator field (analysis_pipeline.registers.* 필드명)
ITEM_TO_FIELD = {
    "흉성두성": ("cq_mean",         True),   # register-aware
    "접촉강도": ("cq_peak",          True),
    "호흡식별": ("cpp",              False),  # register-invariant (학습 시 file global)
    "전방공명": ("spectral_centroid", False),
    "연구개위치": (None,              False),  # nasal_ratio - 5/10 분석 결과 없음
    "비강사용":  (None,              False),  # nasal_ratio - 5/10 분석 결과 없음
    "상압하압":  ("spectral_tilt",    True),
}
SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]
REGISTERS = ["low", "mid", "high"]


# ── 0. 공용 유틸 ─────────────────────────────────────────────────────

def within_session_zscore(values: dict) -> dict:
    """
    values: {register: indicator_value} (None 가능)
    Returns: {register: z_score} — std=0이면 모두 0.
    """
    arr = [v for v in values.values() if v is not None]
    if len(arr) < 2:
        return {r: 0.0 for r in values}
    mu = sum(arr) / len(arr)
    sd = (sum((v - mu) ** 2 for v in arr) / len(arr)) ** 0.5
    if sd < 1e-10:
        return {r: 0.0 for r in values}
    return {r: ((v - mu) / sd if v is not None else None) for r, v in values.items()}


def apply_mapping(ai_val: float | None, mapping: dict) -> float | None:
    """score_mapper.apply_mapping과 동일 로직 (간소화)."""
    if ai_val is None or mapping.get("method") == "skip":
        return None
    thr = mapping.get("thresholds", {})
    if not thr:
        return None
    scores = sorted(int(k) for k in thr.keys())
    vals = [thr[str(s)] for s in scores]
    if len(vals) < 2:
        return float(scores[0])
    increasing = vals[-1] > vals[0]
    if increasing:
        if ai_val <= vals[0]: return float(scores[0])
        if ai_val >= vals[-1]: return float(scores[-1])
        for i in range(len(vals) - 1):
            if vals[i] <= ai_val <= vals[i + 1]:
                frac = (ai_val - vals[i]) / (vals[i + 1] - vals[i] + 1e-10)
                return float(scores[i] + frac * (scores[i + 1] - scores[i]))
    else:
        if ai_val >= vals[0]: return float(scores[0])
        if ai_val <= vals[-1]: return float(scores[-1])
        for i in range(len(vals) - 1):
            if vals[i] >= ai_val >= vals[i + 1]:
                frac = (vals[i] - ai_val) / (vals[i] - vals[i + 1] + 1e-10)
                return float(scores[i] + frac * (scores[i + 1] - scores[i]))
    return None


# ── 1. 학습 데이터에서 per-session 매핑 학습 ────────────────────────

def learn_session_mappings(ai_scores_json: dict) -> dict:
    """
    학습 데이터(99 entries) → (singer, song) session별 z-score 매핑.
    register-aware item만 매핑 산출 (cq_mean/cq_peak/spectral_tilt).
    """
    entries = ai_scores_json.get("scores", [])
    sessions: dict = defaultdict(dict)   # (singer, song) → {register: entry}
    for e in entries:
        sessions[(e["singer_id"], e["song_id"])][e["register"]] = e

    session_pairs: dict[str, list] = defaultdict(list)   # item → [(z, trainer_score)]
    for (sid, song), regs in sessions.items():
        if len(regs) < 2:
            continue
        for item, (field, register_aware) in ITEM_TO_FIELD.items():
            if field is None or not register_aware:
                continue
            # 같은 session 3 register의 indicator
            ind_by_reg = {r: regs[r]["ai_raw_values"].get(item) for r in regs}
            zs = within_session_zscore(ind_by_reg)
            for r, z in zs.items():
                t_score = regs[r]["trainer_avg"].get(item)
                if z is not None and t_score is not None:
                    session_pairs[item].append((z, t_score))

    mappings: dict = {}
    print("\n[per-session 매핑 학습 (학습 데이터)]")
    for item in ITEM_TO_FIELD:
        pairs = session_pairs.get(item, [])
        field, ra = ITEM_TO_FIELD[item]
        if not ra or field is None:
            mappings[item] = {"method": "skip", "reason": "register-invariant or N/A"}
            print(f"  {item:8s}: skip ({mappings[item]['reason']})")
            continue
        if len(pairs) < 5:
            mappings[item] = {"method": "skip", "n_pairs": len(pairs)}
            print(f"  {item:8s}: skip (n={len(pairs)} < 5)")
            continue

        zs = np.array([p[0] for p in pairs])
        ts = np.array([p[1] for p in pairs])
        corr = float(np.corrcoef(ts, zs)[0, 1]) if zs.std() > 1e-10 else 0.0

        # percentile 임계값 (score_mapper 동일 로직)
        thr: dict = {}
        for s in range(6):
            mask = np.abs(ts - s) <= 0.5
            if mask.sum() > 0:
                thr[s] = float(np.median(zs[mask]))
        # 보간
        known = sorted(thr)
        if len(known) >= 2:
            for s in range(6):
                if s not in thr:
                    lo = max((k for k in known if k <= s), default=known[0])
                    hi = min((k for k in known if k >= s), default=known[-1])
                    if lo == hi:
                        thr[s] = thr[lo]
                    else:
                        f = (s - lo) / (hi - lo)
                        thr[s] = thr[lo] * (1 - f) + thr[hi] * f
        mappings[item] = {
            "method":      "session_zscore",
            "n_pairs":     len(pairs),
            "correlation": round(corr, 4),
            "thresholds":  {str(k): float(v) for k, v in sorted(thr.items())},
        }
        print(f"  {item:8s}: n={len(pairs)}  corr(z,t)={corr:+.3f}  "
              f"thresholds={ {k: round(v,3) for k,v in thr.items()} }")
    return mappings


# ── 2. 5/10 inference 결과 로드 + 점수 산출 ─────────────────────────

def load_inference_510() -> dict:
    """singer_id → {registers: {low/mid/high: dict of indicators}, indicators: {...}, scores: {...}}"""
    out: dict = {}
    for p in sorted(INFER_DIR.glob("*.json")):
        out[p.stem] = json.loads(p.read_text())
    return out


def compute_per_register_scores(infer_data: dict, register_mappings: dict) -> dict:
    """
    5/10 (singer, register, item) → per-register 점수.
    register_mappings: 기존 ai_scores.json의 mappings (register 합산 학습)
    """
    scores: dict = {}   # (singer, register, item) → score
    for sid, data in infer_data.items():
        regs = data.get("registers") or {}
        for reg in REGISTERS:
            r = regs.get(reg) or {}
            for item, (field, _ra) in ITEM_TO_FIELD.items():
                if field is None:
                    scores[(sid, reg, item)] = None
                    continue
                ai_val = r.get(field)
                m = register_mappings.get(item)
                if m is None or ai_val is None:
                    scores[(sid, reg, item)] = None
                    continue
                scores[(sid, reg, item)] = apply_mapping(ai_val, m)
    return scores


def compute_per_session_scores(infer_data: dict, session_mappings: dict) -> dict:
    """
    5/10 (singer, register, item) → per-session z-score 매핑 점수.
    register-aware 항목만 산출.
    """
    scores: dict = {}
    for sid, data in infer_data.items():
        regs = data.get("registers") or {}
        for item, (field, ra) in ITEM_TO_FIELD.items():
            if not ra or field is None:
                for reg in REGISTERS:
                    scores[(sid, reg, item)] = None
                continue
            # within-singer z-score
            ind_by_reg = {r: (regs.get(r) or {}).get(field) for r in REGISTERS}
            zs = within_session_zscore(ind_by_reg)
            m = session_mappings.get(item)
            for reg, z in zs.items():
                if m is None or z is None:
                    scores[(sid, reg, item)] = None
                else:
                    scores[(sid, reg, item)] = apply_mapping(z, m)
    return scores


# ── 3. 평가자 평균 (5명) ─────────────────────────────────────────────

def load_trainer_avgs() -> dict:
    """(singer_id, register, item) → 5 raters 평균"""
    by_key: dict = defaultdict(list)
    with open(TRAINER_510_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key_base = (row["singer_id"], row["register"])
            for item in SCORE_COLS:
                v = row.get(item, "").strip()
                if v:
                    try:
                        by_key[(*key_base, item)].append(float(v))
                    except ValueError:
                        pass
    return {k: float(np.mean(v)) for k, v in by_key.items() if v}


# ── 4. corr 비교 ─────────────────────────────────────────────────────

def pearson(xs: list, ys: list) -> tuple[float | None, int]:
    paired = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(paired) < 3:
        return None, len(paired)
    xa = np.array([p[0] for p in paired])
    ya = np.array([p[1] for p in paired])
    if xa.std() < 1e-10 or ya.std() < 1e-10:
        return None, len(paired)
    return float(np.corrcoef(xa, ya)[0, 1]), len(paired)


def compare_corrs(per_reg: dict, per_sess: dict, trainer: dict) -> list[dict]:
    """항목별 corr 비교 → list of dicts."""
    out = []
    for item in SCORE_COLS:
        # 모든 (singer, register) 키 수집
        keys = sorted({k[:2] for k in trainer if k[2] == item})
        t_vals = [trainer.get((s, r, item)) for s, r in keys]
        pr_vals = [per_reg.get((s, r, item))  for s, r in keys]
        ps_vals = [per_sess.get((s, r, item)) for s, r in keys]
        pr_corr, pr_n = pearson(pr_vals, t_vals)
        ps_corr, ps_n = pearson(ps_vals, t_vals)

        # 채택 결정
        if pr_corr is None and ps_corr is None:
            decision = "n/a"
        elif ps_corr is None:
            decision = "per-register"
        elif pr_corr is None:
            decision = "per-session"
        elif ps_corr > pr_corr + 0.03:    # 의미있는 개선만 채택
            decision = "per-session"
        else:
            decision = "per-register"

        out.append({
            "item": item,
            "per_register_corr": round(pr_corr, 4) if pr_corr is not None else None,
            "per_register_n":    pr_n,
            "per_session_corr":  round(ps_corr, 4) if ps_corr is not None else None,
            "per_session_n":     ps_n,
            "delta":             round((ps_corr or 0) - (pr_corr or 0), 4)
                                 if (pr_corr is not None and ps_corr is not None) else None,
            "decision":          decision,
        })
    return out


# ── 5. 신뢰도 재분류 (K-8) ───────────────────────────────────────────

ICC_510_AB = {       # icc_510_ab.json 결과
    "비강사용": 0.796, "흉성두성": 0.805, "접촉강도": 0.898, "호흡식별": 0.796,
    "전방공명": 0.762, "연구개위치": 0.643, "공명개방": 0.728, "혀경직도": 0.802,
    "상압하압": 0.910,
}


def reclassify(comparisons: list[dict]) -> list[dict]:
    """ICC + 채택 corr → high/medium/unavailable"""
    out = []
    for c in comparisons:
        item = c["item"]
        icc = ICC_510_AB.get(item)
        chosen = c["per_session_corr"] if c["decision"] == "per-session" else c["per_register_corr"]
        if chosen is None:
            tier = "unavailable"
            reason = "no AI indicator"
        elif icc is None:
            tier = "unavailable"
            reason = "no ICC"
        elif icc >= 0.8 and abs(chosen) >= 0.7:
            tier = "high"
            reason = f"ICC {icc:.2f} ≥0.8 + |corr| {abs(chosen):.2f} ≥0.7"
        elif icc >= 0.7 and abs(chosen) >= 0.5:
            tier = "medium"
            reason = f"ICC {icc:.2f} ≥0.7 + |corr| {abs(chosen):.2f} ≥0.5"
        else:
            tier = "unavailable"
            reason = f"ICC {icc:.2f} or |corr| {abs(chosen):.2f} 부족"
        out.append({"item": item, "icc": icc,
                    "chosen_corr": round(chosen, 3) if chosen is not None else None,
                    "matching": c["decision"], "tier": tier, "reason": reason})
    return out


# ── 6. 부수: 전방공명 spectral_centroid 분포 진단 ───────────────────

def diagnose_centroid(ai_scores_json: dict, infer_data: dict):
    train_vals = [
        e["ai_raw_values"].get("전방공명")
        for e in ai_scores_json.get("scores", [])
        if e["ai_raw_values"].get("전방공명") is not None
    ]
    five_vals = [
        ((d.get("indicators") or {}).get("spectral_centroid_mean"))
        for d in infer_data.values()
    ]
    five_vals = [v for v in five_vals if v is not None]
    print("\n[전방공명 spectral_centroid 분포 비교]")
    print(f"  학습(99 entries): n={len(train_vals)}  "
          f"min={min(train_vals):.0f}  max={max(train_vals):.0f}  "
          f"mean={st.mean(train_vals):.0f}  median={st.median(train_vals):.0f}")
    print(f"  5/10  (21명):     n={len(five_vals)}  "
          f"min={min(five_vals):.0f}  max={max(five_vals):.0f}  "
          f"mean={st.mean(five_vals):.0f}  median={st.median(five_vals):.0f}")
    print(f"  ↑ 5/10 분포가 학습 분포보다 낮으면 매핑이 모두 0 클리핑")

    # 학습 매핑 임계값 위치
    m = ai_scores_json.get("mappings", {}).get("전방공명", {})
    thr = m.get("thresholds", {})
    if thr:
        ts = [thr[str(s)] for s in range(6) if str(s) in thr]
        print(f"  학습 매핑 임계값: {[round(t,0) for t in ts]}  (점수 0→5)")
        # 5/10 mean이 어느 점수 사이?
        m5 = st.mean(five_vals)
        for i in range(len(ts) - 1):
            lo, hi = ts[i], ts[i + 1]
            if (lo <= m5 <= hi) or (hi <= m5 <= lo):
                print(f"  5/10 mean({m5:.0f}) ≈ 점수 {i}~{i+1} 구간")
                break
        else:
            if m5 < min(ts):
                print(f"  5/10 mean({m5:.0f}) < 임계값 최소({min(ts):.0f}) → 모두 점수 0 클리핑")
            elif m5 > max(ts):
                print(f"  5/10 mean({m5:.0f}) > 임계값 최대({max(ts):.0f}) → 모두 점수 5 클리핑")


# ── main ─────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1] 학습 데이터(ai_scores.json) 로드")
    ai_data = json.loads(AI_SCORES_JSON.read_text())
    register_mappings = ai_data.get("mappings", {})
    print(f"  register 매핑: {[k for k,m in register_mappings.items() if m.get('method')!='skip']}")

    print("\n[2] per-session 매핑 학습")
    session_mappings = learn_session_mappings(ai_data)

    print("\n[3] 5/10 추론 결과 로드")
    infer = load_inference_510()
    print(f"  21명 ({sorted(infer.keys())[:3]}...)")

    print("\n[4] per-register / per-session 점수 산출")
    pr_scores = compute_per_register_scores(infer, register_mappings)
    ps_scores = compute_per_session_scores(infer, session_mappings)

    print("\n[5] 평가자 5명 평균 로드 (trainer_scores_510.csv)")
    trainer = load_trainer_avgs()
    print(f"  trainer keys: {len(trainer)}")

    print("\n[6] 항목별 corr 비교")
    comparisons = compare_corrs(pr_scores, ps_scores, trainer)
    print(f"\n  {'항목':10s}  {'per-register':>16s}  {'per-session':>16s}  "
          f"{'Δ':>6s}  채택")
    for c in comparisons:
        pr = f"{c['per_register_corr']:+.3f} (n={c['per_register_n']})" if c['per_register_corr'] is not None else "n/a"
        ps = f"{c['per_session_corr']:+.3f} (n={c['per_session_n']})"   if c['per_session_corr']  is not None else "n/a"
        d  = f"{c['delta']:+.3f}" if c['delta'] is not None else "—"
        print(f"  {c['item']:10s}  {pr:>16s}  {ps:>16s}  {d:>6s}  {c['decision']}")

    # CSV 저장
    csv_path = OUT_DIR / "matching_comparison_510.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item","per_register_corr","per_register_n",
                                          "per_session_corr","per_session_n","delta","decision"])
        w.writeheader(); w.writerows(comparisons)
    print(f"\n저장: {csv_path}")

    # 신뢰도 재분류
    print("\n[7] 신뢰도 재분류")
    reliability = reclassify(comparisons)
    print(f"  {'항목':10s}  {'ICC':>6s}  {'chosen corr':>12s}  {'매칭':>14s}  {'tier':>10s}  reason")
    for r in reliability:
        icc_s = f"{r['icc']:.3f}" if r['icc'] is not None else "n/a"
        cc_s  = f"{r['chosen_corr']:+.3f}" if r['chosen_corr'] is not None else "n/a"
        print(f"  {r['item']:10s}  {icc_s:>6s}  {cc_s:>12s}  {r['matching']:>14s}  "
              f"{r['tier']:>10s}  {r['reason']}")
    csv_path = OUT_DIR / "reliability_510.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item","icc","chosen_corr","matching","tier","reason"])
        w.writeheader(); w.writerows(reliability)
    print(f"\n저장: {csv_path}")

    # 부수: 전방공명 진단
    diagnose_centroid(ai_data, infer)


if __name__ == "__main__":
    main()
