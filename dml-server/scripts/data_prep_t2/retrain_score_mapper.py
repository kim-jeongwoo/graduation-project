#!/usr/bin/env python3
"""
retrain_score_mapper.py — 기존 + T2 데이터 합산해 score_mapper 재학습

작동 방식:
  - 기존: trainer_scores_v2.csv + egg/nasal/extra_metrics analysis JSONs (singer_01~22)
  - 신규: trainer_scores_t2.csv + analyze_t2.json (revalidate.py 출력)
  - 합산 후 percentile 임계값 재계산 → ai_scores.json 갱신

실행:
  python retrain_score_mapper.py [--dry-run]
"""

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"
RESULTS_DIR  = VOCAL_DIR / "results"

AI_SCORES_PATH    = RESULTS_DIR / "ai_scores.json"
V2_CSV            = VOCAL_DIR / "trainer_scores_v2.csv"
T2_CSV            = VOCAL_DIR / "trainer_scores_t2.csv"
ANALYZE_T2_PATH   = RESULTS_DIR / "analyze_t2.json"

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

# 기존 analysis JSON → 항목 매핑 (score_mapper.py 기준)
ITEM_MAP = {
    "비강사용":  ("nasal_analysis.json",  "nasal_ratio"),
    "흉성두성":  ("egg_analysis.json",    "cq_mean"),
    "접촉강도":  ("egg_analysis.json",    "cq_peak"),
    "호흡식별":  ("extra_metrics.json",   "cpp"),
    "전방공명":  ("extra_metrics.json",   "spectral_centroid"),
    "연구개위치": ("nasal_analysis.json",  "nasal_ratio"),
    "상압하압":  ("spectral_analysis.json", "spectral_tilt"),
}

# /analyze 응답 indicators 키 → SCORE_COLS 매핑
ANALYZE_INDICATOR_MAP = {
    "비강사용":  "nasal_ratio",
    "흉성두성":  "cq_mean",
    "접촉강도":  "cq_peak",
    "호흡식별":  "cpp_mean",
    "전방공명":  "spectral_centroid_mean",
    "연구개위치": "nasal_ratio",
    "상압하압":  "spectral_tilt_mean",
}


def load_csv_means(csv_path: Path) -> dict:
    """singer_id → register → item → mean(5명 점수)"""
    raw: dict = {}
    if not csv_path.exists():
        return raw
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row["singer_id"]
            reg = row["register"]
            raw.setdefault(sid, {}).setdefault(reg, {col: [] for col in SCORE_COLS})
            for col in SCORE_COLS:
                val = row.get(col, "")
                if val:
                    try:
                        raw[sid][reg][col].append(float(val))
                    except ValueError:
                        pass
    result: dict = {}
    for sid, regs in raw.items():
        result[sid] = {}
        for reg, items in regs.items():
            result[sid][reg] = {col: float(np.mean(v)) if v else None
                                for col, v in items.items()}
    return result


def load_existing_ai_indicators() -> dict:
    """기존 analysis JSONs에서 singer_id → register → indicator_name → value 로드"""
    combined: dict = {}
    for fname in ["egg_analysis.json", "nasal_analysis.json",
                  "extra_metrics.json", "spectral_analysis.json"]:
        path = RESULTS_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # 구조: {singer_id: {register: {metric: value}}} 또는 유사
        for sid, regs in data.items():
            combined.setdefault(sid, {})
            if isinstance(regs, dict):
                for reg, metrics in regs.items():
                    combined[sid].setdefault(reg, {}).update(metrics if isinstance(metrics, dict) else {})
    return combined


def load_t2_ai_indicators() -> dict:
    """analyze_t2.json에서 wav_id → indicators (global) 로드"""
    if not ANALYZE_T2_PATH.exists():
        return {}
    with open(ANALYZE_T2_PATH, encoding="utf-8") as f:
        data = json.load(f)
    result: dict = {}
    for entry in data.get("raw", []):
        wav_id = entry["wav_id"]
        resp   = entry.get("response")
        if not resp:
            continue
        indicators = resp.get("indicators", {})
        result[wav_id] = indicators
    return result


def build_pairs(col: str, trainer_v2: dict, trainer_t2: dict,
                ai_v2: dict, ai_t2: dict) -> list[tuple[float, float]]:
    """(ai_indicator_value, trainer_mean) 쌍 목록 생성"""
    pairs = []

    # 기존 데이터 (v2): analysis JSON 기반
    ai_fname, ai_key = ITEM_MAP.get(col, (None, None))
    if ai_fname and ai_key:
        for sid, regs in trainer_v2.items():
            for reg, items in regs.items():
                t_val = items.get(col)
                if t_val is None:
                    continue
                ai_val = ai_v2.get(sid, {}).get(reg, {}).get(ai_key)
                if ai_val is None:
                    continue
                pairs.append((float(ai_val), float(t_val)))

    # T2 데이터: /analyze indicators 기반
    ind_key = ANALYZE_INDICATOR_MAP.get(col)
    if ind_key:
        for wav_id, indicators in ai_t2.items():
            ai_val = indicators.get(ind_key)
            if ai_val is None:
                continue
            # 트레이너 평균: register 전체 평균
            t_data = trainer_t2.get(wav_id, {})
            t_vals = [v for reg in t_data.values()
                      if (v := reg.get(col)) is not None]
            if not t_vals:
                continue
            t_mean = float(np.mean(t_vals))
            pairs.append((float(ai_val), t_mean))

    return pairs


def compute_percentile_thresholds(pairs: list[tuple]) -> dict:
    """
    트레이너 점수 구간(0~5)별 AI 지표 분위값 → 임계값 계산.
    기존 score_mapper.py와 동일한 percentile 방식.
    """
    from scipy import stats as scipy_stats

    ai_vals = np.array([x for x, _ in pairs])
    tr_vals = np.array([y for _, y in pairs])

    r, p = scipy_stats.pearsonr(ai_vals, tr_vals)

    thresholds = {}
    for score in range(6):
        mask = np.abs(tr_vals - score) < 0.5
        if mask.sum() > 0:
            thresholds[str(score)] = float(np.median(ai_vals[mask]))
        else:
            thresholds[str(score)] = float(np.median(ai_vals))

    return {
        "method":      "percentile",
        "n_pairs":     len(pairs),
        "correlation": round(float(r), 6),
        "thresholds":  thresholds,
        "ai_range":    {"min": float(ai_vals.min()), "max": float(ai_vals.max())},
    }


def run(dry_run: bool) -> None:
    trainer_v2 = load_csv_means(V2_CSV)
    trainer_t2 = load_csv_means(T2_CSV)
    ai_v2      = load_existing_ai_indicators()
    ai_t2      = load_t2_ai_indicators()

    n_v2 = sum(len(regs) for regs in trainer_v2.values())
    n_t2 = sum(len(regs) for regs in trainer_t2.values())
    print(f"트레이너 데이터: v2={n_v2}행, t2={n_t2}행")
    print(f"AI 지표:        v2={len(ai_v2)}명, t2={len(ai_t2)}명\n")

    # 기존 ai_scores.json 백업
    if AI_SCORES_PATH.exists() and not dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = AI_SCORES_PATH.with_name(f"ai_scores_backup_{ts}.json")
        shutil.copy2(AI_SCORES_PATH, backup)
        print(f"백업: {backup}")

    # 기존 파일 로드 (unmapped 항목 보존용)
    existing: dict = {}
    if AI_SCORES_PATH.exists():
        with open(AI_SCORES_PATH, encoding="utf-8") as f:
            existing = json.load(f)

    new_mappings = dict(existing.get("mappings", {}))
    total_pairs  = 0
    upgraded     = []

    print(f"{'─'*55}")
    print(f" {'항목':8s}  {'n_pairs':>8}  {'r':>6}  {'변화'}")
    print(f"{'─'*55}")

    for col in SCORE_COLS:
        if col not in ITEM_MAP and col not in ANALYZE_INDICATOR_MAP:
            print(f"  {col:8s}  (매핑 없음, skip)")
            continue

        pairs = build_pairs(col, trainer_v2, trainer_t2, ai_v2, ai_t2)
        if len(pairs) < 5:
            print(f"  {col:8s}  데이터 부족 ({len(pairs)}쌍)")
            continue

        new_entry = compute_percentile_thresholds(pairs)
        old_r = existing.get("mappings", {}).get(col, {}).get("correlation", 0)
        new_r = new_entry["correlation"]
        delta = new_r - old_r
        arrow = f"↑{delta:+.3f}" if abs(delta) > 0.01 else "→"

        print(f"  {col:8s}  {new_entry['n_pairs']:>8}  {new_r:>6.3f}  {arrow}")
        new_mappings[col] = new_entry
        total_pairs += new_entry["n_pairs"]

        if new_r > 0.5 and old_r <= 0.5:
            upgraded.append(col)

    print(f"{'─'*55}")
    print(f"총 데이터 포인트: {total_pairs}")

    if upgraded:
        print(f"\n🔔 상관계수 r > 0.5 신규 진입 항목: {upgraded}")

    if not dry_run:
        out = {
            "description": f"T2 재학습 ({datetime.now().strftime('%Y-%m-%d')})",
            "n_entries": total_pairs,
            "mappings": new_mappings,
        }
        with open(AI_SCORES_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n갱신 완료: {AI_SCORES_PATH}")
    else:
        print("\n[dry-run] 파일 변경 없음.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="계산만 하고 파일 갱신 안 함")
    args = ap.parse_args()
    run(args.dry_run)


if __name__ == "__main__":
    main()
