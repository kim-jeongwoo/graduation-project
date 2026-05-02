#!/usr/bin/env python3
"""
validate_icc.py — 신규 트레이너 점수 ICC(2,k) 자동 계산

실행:
  python validate_icc.py [--csv <trainer_scores_t2.csv>] [--out <icc_t2.json>]

ICC(2,k): Two-way mixed, absolute agreement, multiple raters
  → 연구 도구의 신뢰도를 평가하는 표준 지표
"""

import argparse
import json
import csv
from pathlib import Path

import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

ICC_THRESHOLDS = {"poor": 0.5, "moderate": 0.75, "good": 0.9}


def load_scores(csv_path: Path) -> dict:
    """singer_id → register → rater → {item: score}"""
    data: dict = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["singer_id"]
            reg = row["register"]
            rtr = int(row["rater"])
            data.setdefault(sid, {}).setdefault(reg, {})[rtr] = {
                col: float(row[col]) if row[col] else None
                for col in SCORE_COLS
            }
    return data


def compute_icc2k(matrix: np.ndarray) -> dict:
    """
    matrix: (n_subjects × n_raters)
    Returns: ICC value, F-statistic, p-value, 95% CI
    """
    n, k = matrix.shape
    if n < 2 or k < 2:
        return {"icc": None, "p": None, "ci_low": None, "ci_high": None}

    grand_mean = matrix.mean()
    row_means  = matrix.mean(axis=1)
    col_means  = matrix.mean(axis=0)

    ss_r = k * np.sum((row_means - grand_mean) ** 2)
    ss_c = n * np.sum((col_means - grand_mean) ** 2)
    ss_t = np.sum((matrix - grand_mean) ** 2)
    ss_e = ss_t - ss_r - ss_c

    ms_r = ss_r / (n - 1)
    ms_e = ss_e / ((n - 1) * (k - 1))

    if ms_e == 0:
        return {"icc": 1.0, "p": 0.0, "ci_low": 1.0, "ci_high": 1.0}

    icc = (ms_r - ms_e) / ms_r  # ICC(2,k)
    icc = float(np.clip(icc, -1, 1))

    # F-검정 (p-value)
    f_stat = ms_r / ms_e
    df1    = n - 1
    df2    = (n - 1) * (k - 1)
    p_val  = float(1 - stats.f.cdf(f_stat, df1, df2))

    # 95% CI (Shrout & Fleiss 1979)
    alpha = 0.05
    f_low  = f_stat / stats.f.ppf(1 - alpha / 2, df1, df2)
    f_high = f_stat * stats.f.ppf(1 - alpha / 2, df2, df1)
    ci_low  = float((f_low  - 1) / f_low)
    ci_high = float((f_high - 1) / f_high)

    return {"icc": round(icc, 4), "p": round(p_val, 4),
            "ci_low": round(ci_low, 4), "ci_high": round(ci_high, 4)}


def interpret(icc: float | None) -> str:
    if icc is None:
        return "N/A"
    if icc < ICC_THRESHOLDS["poor"]:
        return "poor"
    if icc < ICC_THRESHOLDS["moderate"]:
        return "moderate"
    if icc < ICC_THRESHOLDS["good"]:
        return "good"
    return "excellent"


def run(csv_path: Path, out_path: Path) -> None:
    data = load_scores(csv_path)

    # item → (singer, register) 쌍별 rater×score 행렬 구성
    all_raters = sorted({r for sid in data.values()
                         for reg in sid.values() for r in reg.keys()})
    k = len(all_raters)

    results = {}
    warnings = []

    print(f"평가자 수: {k}명  |  피험자 수: {len(data)}명\n")

    for col in SCORE_COLS:
        rows = []
        for sid in sorted(data):
            for reg in sorted(data[sid]):
                rater_data = data[sid][reg]
                scores = []
                for r in all_raters:
                    val = rater_data.get(r, {}).get(col)
                    scores.append(val)
                # 모든 평가자가 값이 있는 행만 사용
                if all(s is not None for s in scores):
                    rows.append(scores)

        if len(rows) < 2:
            results[col] = {"icc": None, "p": None, "ci_low": None,
                            "ci_high": None, "n": len(rows), "grade": "N/A"}
            warnings.append(f"{col}: 데이터 부족 ({len(rows)}행)")
            continue

        mat = np.array(rows, dtype=float)
        icc_result = compute_icc2k(mat)
        grade = interpret(icc_result["icc"])

        results[col] = {**icc_result, "n": len(rows), "grade": grade}

        icc_v = icc_result["icc"]
        p_v   = icc_result["p"]
        flag  = "⚠" if icc_v is not None and icc_v < ICC_THRESHOLDS["poor"] else " "
        print(f"  {flag} {col:8s}: ICC={icc_v:.3f}  p={p_v:.4f}  "
              f"CI=[{icc_result['ci_low']:.3f}, {icc_result['ci_high']:.3f}]  "
              f"({grade})  n={len(rows)}")

        if icc_v is not None and icc_v < ICC_THRESHOLDS["poor"]:
            warnings.append(f"{col}: ICC={icc_v:.3f} < 0.5 (poor)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"n_raters": k, "items": results}, f, ensure_ascii=False, indent=2)

    print(f"\n출력: {out_path}")
    if warnings:
        print("\n[경고]")
        for w in warnings:
            print(f"  {w}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(VOCAL_DIR / "trainer_scores_t2.csv"))
    ap.add_argument("--out", default=str(VOCAL_DIR / "results" / "icc_t2.json"))
    args = ap.parse_args()
    run(Path(args.csv), Path(args.out))


if __name__ == "__main__":
    main()
