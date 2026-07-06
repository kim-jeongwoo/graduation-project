#!/usr/bin/env python3
"""
chest_head_indicators.py — 흉성두성 매핑용 신규 CQ 지표 후보 탐색

현재 cq_mean 매핑: r=-0.282 (학습), r=-0.215 (검증) → 음의 상관 문제
가설: 음역대 간 CQ 변동 패턴이 더 유효한 지표일 수 있음

지표 정의:
  1. cq_high_minus_low : cq_high_mean - cq_low_mean
  2. cq_high_low_ratio : cq_high_mean / cq_low_mean
  3. cq_variance        : variance([cq_low, cq_mid, cq_high])
  4. cq_high_normalized : cq_high_mean / cq_global_mean

실행:
  conda activate EGGDML
  cd ~/projects/egg_prediction
  python dml-server/scripts/sidetrack/chest_head_indicators.py
"""

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"
RESULTS_DIR  = VOCAL_DIR / "results"

EGG_ANALYSIS    = RESULTS_DIR / "egg_analysis.json"
TRAINER_TRAIN   = VOCAL_DIR / "trainer_scores.csv"
TRAINER_VALID   = VOCAL_DIR / "trainer_scores_validation.csv"
ANALYZE_T2      = RESULTS_DIR / "analyze_t2.json"

EXCLUDE_PAIRS = {(6, 8)}  # 원곡과 같은 이유로 제외


# ── 지표 계산 ────────────────────────────────────────────────────

def compute_indicators(cq_low: float, cq_mid: float, cq_high: float,
                       cq_global: float) -> dict:
    """4개 신규 지표 + 기준선 cq_mean 계산"""
    vals = np.array([cq_low, cq_mid, cq_high])
    return {
        "cq_mean_global":      cq_global,
        "cq_high_minus_low":   cq_high - cq_low,
        "cq_high_low_ratio":   cq_high / cq_low if cq_low > 0 else None,
        "cq_variance":         float(np.var(vals)),
        "cq_high_normalized":  cq_high / cq_global if cq_global > 0 else None,
    }


# ── 학습 데이터 로드 ─────────────────────────────────────────────

def load_training_pairs() -> list[tuple[dict, float]]:
    """(indicators_dict, mean_흉성두성) 쌍 목록 — egg_analysis × trainer_scores.csv"""
    with open(EGG_ANALYSIS, encoding="utf-8") as f:
        analysis = json.load(f)["results"]

    # trainer_scores.csv → per (singer, song) mean 흉성두성
    trainer_raw: dict = {}  # (singer, song) → [scores]
    with open(TRAINER_TRAIN, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s_raw = row.get("singer", "").strip()
            g_raw = row.get("song", "").strip()
            if not s_raw:
                continue
            singer = int(s_raw)
            song   = int(g_raw) if g_raw.isdigit() else 0
            if (singer, song) in EXCLUDE_PAIRS:
                continue
            val = row.get("흉성두성", "").strip()
            if val:
                trainer_raw.setdefault((singer, song), []).append(float(val))

    trainer_mean = {k: float(np.mean(v)) for k, v in trainer_raw.items()}

    # egg_analysis → indicators
    pairs = []
    for entry in analysis:
        sid = entry["singer_id"]
        gid = entry["song_id"]
        if (sid, gid) in EXCLUDE_PAIRS:
            continue

        reg = entry.get("cq_by_register", {})
        low_d  = reg.get("low",  {})
        mid_d  = reg.get("mid",  {})
        high_d = reg.get("high", {})

        cq_low  = low_d.get("mean")
        cq_mid  = mid_d.get("mean")
        cq_high = high_d.get("mean")
        cq_glob = entry.get("cq_global", {}).get("mean")

        if any(v is None for v in [cq_low, cq_mid, cq_high, cq_glob]):
            continue

        indic = compute_indicators(cq_low, cq_mid, cq_high, cq_glob)

        # Match trainer score — try (sid, gid) first, fallback to (sid, 0)
        t_score = trainer_mean.get((sid, gid)) or trainer_mean.get((sid, 0))
        if t_score is None:
            continue

        pairs.append((indic, t_score))

    return pairs


def load_training_pairs_perregister() -> list[tuple[str, float, float]]:
    """
    기준선 비교용: per-(singer, song, register) cq_mean 쌍
    → score_mapper.py 와 동일한 57쌍 (empty-song 행 제외, fallback 없음)
    """
    with open(EGG_ANALYSIS, encoding="utf-8") as f:
        analysis = json.load(f)["results"]

    REG_MAP_KR = {"저": "low", "중": "mid", "고": "high"}

    # trainer_scores.csv → (singer, song, register_en) → mean 흉성두성
    # empty-song 행 (singers 13-22) 제외: score_mapper.py 방식과 동일
    trainer_raw: dict = {}
    with open(TRAINER_TRAIN, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s_raw = row.get("singer", "").strip()
            g_raw = row.get("song", "").strip()
            if not s_raw or not g_raw.isdigit():
                continue  # skip rows without song number
            singer = int(s_raw)
            song   = int(g_raw)
            if (singer, song) in EXCLUDE_PAIRS:
                continue
            reg_en = REG_MAP_KR.get(row.get("register", "").strip())
            if not reg_en:
                continue
            val = row.get("흉성두성", "").strip()
            if val:
                trainer_raw.setdefault((singer, song, reg_en), []).append(float(val))

    trainer_mean = {k: float(np.mean(v)) for k, v in trainer_raw.items()}

    pairs = []
    for entry in analysis:
        sid = entry["singer_id"]
        gid = entry["song_id"]
        if (sid, gid) in EXCLUDE_PAIRS:
            continue
        reg = entry.get("cq_by_register", {})
        for reg_en, reg_data in reg.items():
            cq_val = reg_data.get("mean")
            if cq_val is None:
                continue
            t_score = trainer_mean.get((sid, gid, reg_en))  # no fallback → 57 pairs
            if t_score is None:
                continue
            pairs.append((cq_val, t_score))

    return pairs


# ── 검증 데이터 로드 ─────────────────────────────────────────────

def load_validation_pairs() -> list[tuple[dict, float]]:
    """(indicators_dict, mean_흉성두성) — analyze_t2.json × trainer_scores_validation.csv"""
    if not ANALYZE_T2.exists():
        raise FileNotFoundError(f"{ANALYZE_T2} 없음. revalidate.py --mode validation 실행 필요")

    with open(ANALYZE_T2, encoding="utf-8") as f:
        t2 = json.load(f)

    # analyze_t2.json: raw entries
    t2_cq: dict = {}  # wav_id → indicator dict
    for entry in t2.get("raw", []):
        wav_id = entry["wav_id"]
        resp   = entry.get("response")
        if not resp:
            continue
        regs = resp.get("registers", {})
        low_d  = regs.get("low",  {})
        mid_d  = regs.get("mid",  {})
        high_d = regs.get("high", {})
        indic  = resp.get("indicators", {})

        cq_low  = low_d.get("cq_mean")
        cq_mid  = mid_d.get("cq_mean")
        cq_high = high_d.get("cq_mean")
        cq_glob = indic.get("cq_mean")

        if any(v is None for v in [cq_low, cq_mid, cq_high, cq_glob]):
            continue

        t2_cq[wav_id] = compute_indicators(cq_low, cq_mid, cq_high, cq_glob)

    # trainer_scores_validation.csv → per test_id mean 흉성두성
    trainer_raw: dict = {}
    with open(TRAINER_VALID, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = row.get("test_id", "").strip()
            val = row.get("흉성두성", "").strip()
            if tid and val:
                trainer_raw.setdefault(tid, []).append(float(val))

    trainer_mean = {k: float(np.mean(v)) for k, v in trainer_raw.items()}

    pairs = []
    for wav_id, indic in t2_cq.items():
        t_score = trainer_mean.get(wav_id)
        if t_score is None:
            continue
        pairs.append((indic, t_score))

    return pairs


def load_validation_pairs_perregister() -> list[tuple[float, float]]:
    """검증: per-register cq_mean vs 흉성두성 (11×3=33쌍 기준선)"""
    if not ANALYZE_T2.exists():
        return []

    with open(ANALYZE_T2, encoding="utf-8") as f:
        t2 = json.load(f)

    REG_MAP_KR = {"저": "low", "중": "mid", "고": "high",
                  "low": "low", "mid": "mid", "high": "high"}

    t2_cq_reg: dict = {}  # wav_id → {register_en: cq_mean}
    for entry in t2.get("raw", []):
        wav_id = entry["wav_id"]
        resp   = entry.get("response")
        if not resp:
            continue
        regs = resp.get("registers", {})
        t2_cq_reg[wav_id] = {
            r: regs.get(r, {}).get("cq_mean") for r in ["low", "mid", "high"]
        }

    trainer_raw: dict = {}
    with open(TRAINER_VALID, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = row.get("test_id", "").strip()
            reg_en = REG_MAP_KR.get(row.get("register", "").strip())
            val = row.get("흉성두성", "").strip()
            if tid and reg_en and val:
                trainer_raw.setdefault((tid, reg_en), []).append(float(val))

    trainer_mean = {k: float(np.mean(v)) for k, v in trainer_raw.items()}

    pairs = []
    for wav_id, reg_cq in t2_cq_reg.items():
        for reg_en, cq_val in reg_cq.items():
            if cq_val is None:
                continue
            t_score = trainer_mean.get((wav_id, reg_en))
            if t_score is None:
                continue
            pairs.append((cq_val, t_score))

    return pairs


# ── 상관 분석 ────────────────────────────────────────────────────

def pearson_ci(x: np.ndarray, y: np.ndarray, alpha: float = 0.05
               ) -> tuple[float, float, float, float]:
    """Pearson r, p, 95% CI (lower, upper) via Fisher z-transform."""
    n = len(x)
    if n < 4:
        return float("nan"), float("nan"), float("nan"), float("nan")
    r, p = stats.pearsonr(x, y)
    # Fisher z-transform CI
    z      = np.arctanh(r)
    se     = 1.0 / np.sqrt(n - 3)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    lo     = float(np.tanh(z - z_crit * se))
    hi     = float(np.tanh(z + z_crit * se))
    return float(r), float(p), lo, hi


def analyze_pairs(pairs: list[tuple], indicator_keys: list[str]
                  ) -> dict[str, dict]:
    """pairs: list of (indicators_dict, trainer_score). 각 지표별 Pearson r 계산."""
    results = {}
    for key in indicator_keys:
        xy = [(ind[key], t) for ind, t in pairs
              if ind.get(key) is not None]
        if len(xy) < 4:
            results[key] = {"r": None, "p": None, "ci_lo": None, "ci_hi": None, "n": len(xy)}
            continue
        x = np.array([v for v, _ in xy])
        y = np.array([v for _, v in xy])
        r, p, ci_lo, ci_hi = pearson_ci(x, y)
        results[key] = {"r": round(r, 4), "p": round(p, 4),
                        "ci_lo": round(ci_lo, 4), "ci_hi": round(ci_hi, 4),
                        "n": len(xy)}
    return results


# ── 출력 ─────────────────────────────────────────────────────────

INDICATOR_LABELS = {
    "cq_mean_global":      "cq_mean (기존, 전체)",
    "cq_high_minus_low":   "cq_high - cq_low",
    "cq_high_low_ratio":   "cq_high / cq_low",
    "cq_variance":         "cq variance (저/중/고)",
    "cq_high_normalized":  "cq_high / cq_global_mean",
}

INDICATOR_HYPOTHESIS = {
    "cq_mean_global":      "높을수록 흉성 → 양(+) 기대 (현재 음)",
    "cq_high_minus_low":   "흉성은 차이 작음(-) or 약간 양 → 부호 불명확",
    "cq_high_low_ratio":   "흉성은 비율 ≈1 → 부호 불명확",
    "cq_variance":         "흉성은 분산 작음 → 음(-) 상관 기대",
    "cq_high_normalized":  "흉성은 비율 ≈1 → 음(-) 상관 불명확",
}


def sign_str(r: float | None) -> str:
    if r is None:
        return "N/A"
    return "+" if r >= 0 else "-"


def print_table(title: str, results: dict, baseline_per_reg: tuple | None = None) -> None:
    print(f"\n{'═'*72}")
    print(f"  {title}")
    print(f"{'═'*72}")
    print(f"  {'지표':26s}  {'r':>7}  {'95% CI':>20}  {'p':>7}  {'n':>4}  부호")
    print(f"  {'─'*26}  {'─'*7}  {'─'*20}  {'─'*7}  {'─'*4}  {'─'*6}")

    # per-register cq_mean baseline (first row, italicized)
    if baseline_per_reg:
        r_b, p_b, ci_lo_b, ci_hi_b, n_b = baseline_per_reg
        ci_str = f"[{ci_lo_b:+.3f}, {ci_hi_b:+.3f}]"
        print(f"  {'cq_mean (per-register)':26s}  {r_b:+7.4f}  {ci_str:>20}  {p_b:7.4f}  {n_b:>4}  {sign_str(r_b)} ← 기준선(score_mapper 동일)")

    for key in INDICATOR_LABELS:
        if key not in results:
            continue
        res = results[key]
        r   = res["r"]
        if r is None:
            print(f"  {INDICATOR_LABELS[key]:26s}  {'N/A':>7}  {'':>20}  {'N/A':>7}  {res['n']:>4}")
            continue
        ci_str = f"[{res['ci_lo']:+.3f}, {res['ci_hi']:+.3f}]"
        marker = " ◀ 개선!" if (r > 0.3 and r > 0) else (" ◀ 약한 개선" if 0 < r <= 0.3 else "")
        print(f"  {INDICATOR_LABELS[key]:26s}  {r:+7.4f}  {ci_str:>20}  {res['p']:7.4f}  {res['n']:>4}  {sign_str(r)}{marker}")

    print(f"  {'─'*72}")


# ── 메인 ─────────────────────────────────────────────────────────

def main() -> None:
    KEYS = list(INDICATOR_LABELS.keys())

    print("=" * 72)
    print("  흉성두성 신규 CQ 지표 탐색 분석")
    print("=" * 72)

    # ── K-2: 학습 데이터 ─────────────────────────────────────────
    print("\n[K-2] 학습 데이터 (egg_analysis.json × trainer_scores.csv)")
    train_pairs = load_training_pairs()
    print(f"  → 매칭된 세션 수: {len(train_pairs)}")

    train_results = analyze_pairs(train_pairs, KEYS)

    # 기준선: per-register cq_mean (score_mapper 동일 방식)
    per_reg_train = load_training_pairs_perregister()
    if per_reg_train:
        x = np.array([v for v, _ in per_reg_train])
        y = np.array([v for _, v in per_reg_train])
        r_b, p_b, ci_lo_b, ci_hi_b = pearson_ci(x, y)
        baseline_train = (r_b, p_b, ci_lo_b, ci_hi_b, len(per_reg_train))
    else:
        baseline_train = None

    print_table("K-2 결과: 학습 데이터", train_results, baseline_train)

    # ── K-3: 검증 데이터 ─────────────────────────────────────────
    print("\n[K-3] 검증 데이터 (analyze_t2.json × trainer_scores_validation.csv)")
    try:
        valid_pairs = load_validation_pairs()
        print(f"  → 매칭된 test 수: {len(valid_pairs)}")

        valid_results = analyze_pairs(valid_pairs, KEYS)

        per_reg_valid = load_validation_pairs_perregister()
        if per_reg_valid:
            x = np.array([v for v, _ in per_reg_valid])
            y = np.array([v for _, v in per_reg_valid])
            r_b, p_b, ci_lo_b, ci_hi_b = pearson_ci(x, y)
            baseline_valid = (r_b, p_b, ci_lo_b, ci_hi_b, len(per_reg_valid))
        else:
            baseline_valid = None

        print_table("K-3 결과: 검증 데이터", valid_results, baseline_valid)

    except FileNotFoundError as e:
        print(f"  [건너뜀] {e}")
        valid_results = {}

    # ── K-4: 판정 ─────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("  K-4 판정")
    print("═" * 72)

    best_key  = None
    best_r    = -999.0
    for key in KEYS:
        train_r = train_results.get(key, {}).get("r")
        valid_r = valid_results.get(key, {}).get("r")
        if train_r is None:
            continue
        # 학습+검증 일관성 판단: 둘 다 양의 상관이면 좋음
        combined = (train_r if valid_r is None
                    else (train_r + valid_r) / 2)
        if combined > best_r:
            best_r   = combined
            best_key = key

    baseline_r = (baseline_train[0] if baseline_train else None)
    best_train_r = train_results.get(best_key, {}).get("r") if best_key else None
    best_valid_r = valid_results.get(best_key, {}).get("r") if best_key else None

    print(f"\n  기준선 (cq_mean per-register):  r_학습={baseline_r:+.4f}" if baseline_r else "  기준선 없음")
    print(f"  최우수 신규 지표: {INDICATOR_LABELS.get(best_key, best_key)}")
    if best_train_r is not None:
        print(f"    학습:  r={best_train_r:+.4f}  {'개선됨' if best_train_r > (baseline_r or 0) else '미개선'}")
    if best_valid_r is not None:
        print(f"    검증:  r={best_valid_r:+.4f}  {'개선됨' if best_valid_r > -0.215 else '미개선'} (기존 검증 -0.215)")

    if best_train_r is not None and best_valid_r is not None:
        if best_train_r > 0.3 and best_valid_r > 0.3:
            print("\n  ✅ 판정: 성공 (r>0.3 학습+검증 일관) → score_mapper 채택 검토")
            verdict = "success"
        elif best_train_r > 0 and best_valid_r > 0:
            print("\n  ⚠️  판정: 약한 개선 (양의 상관이나 r≤0.3) → 채택 보류")
            verdict = "weak"
        elif best_train_r > 0 or best_valid_r > 0:
            print("\n  ⚠️  판정: 불일치 (학습/검증 한쪽만 양) → 채택 보류")
            verdict = "inconsistent"
        else:
            print("\n  ❌ 판정: 실패 (여전히 음의 상관) → 졸업작품 한계로 명시")
            verdict = "fail"
    else:
        verdict = "insufficient_data"
        print("\n  ⚠️  판정: 데이터 부족")

    print()
    print("  가설 메모:")
    for key, hyp in INDICATOR_HYPOTHESIS.items():
        r = train_results.get(key, {}).get("r")
        print(f"    {INDICATOR_LABELS[key]:28s}: {hyp}")
        if r is not None:
            print(f"      → 실측 r={r:+.4f}")

    print("\n" + "=" * 72)
    return verdict


if __name__ == "__main__":
    main()
