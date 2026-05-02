#!/usr/bin/env python3
"""
generate_summary.py — 9개 항목 신뢰도 재분류 + 앱 갱신 알림

분류 규칙:
  high:             p < 0.01 AND r > 0.5 (양의 상관만)
                    또는: zone 일치율 >= 50%이면 high 우선
  medium:           p < 0.05 AND r > 0.3
  low_correlation:  r > 0 이지만 기준 미달
  unavailable:      AI 매핑 없음 또는 r < 0 (매핑 방향 오류 의심)

실행:
  python generate_summary.py [--analyze-t2 results/analyze_t2.json]
                              [--ai-scores results/ai_scores.json]
                              [--out results/reliability_t2.json]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"
RESULTS_DIR  = VOCAL_DIR / "results"

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

ITEM_KEY_MAP = {
    "1_nasal_oral_ratio":   "비강사용",
    "2_chest_head_voice":   "흉성두성",
    "3_vocal_fold_contact": "접촉강도",
    "4_breathiness":        "호흡식별",
    "5_forward_resonance":  "전방공명",
    "6_soft_palate":        "연구개위치",
    "7_larynx_tongue":      "공명개방",
    "8_tongue_tension":     "혀경직도",
    "9_pressure_balance":   "상압하압",
}

# 기존 신뢰도 분류 (schemas.py 기준 현재 상태)
CURRENT_HIGH   = {"접촉강도", "호흡식별"}
CURRENT_MEDIUM = {"비강사용", "흉성두성", "전방공명", "연구개위치", "상압하압"}
CURRENT_UNAVAILABLE = {"공명개방", "혀경직도"}


def classify(r: float | None, p: float | None,
             zone_match: float | None) -> str:
    if r is None or p is None:
        return "unavailable"
    if r < 0:
        return "unavailable"  # 음의 상관 = 매핑 방향 오류 의심
    if zone_match is not None and zone_match >= 0.5 and r > 0.3:
        return "high"
    if p < 0.01 and r > 0.5:
        return "high"
    if p < 0.05 and r > 0.3:
        return "medium"
    if r > 0:
        return "low_correlation"
    return "unavailable"


def compute_zone_match(analyze_data: list[dict], col: str,
                       item_key: str) -> float | None:
    """
    AI zone (insufficient/appropriate/excessive) vs 트레이너 점수 zone 일치율.
    트레이너 zone: score 0~1 = insufficient, 2~3 = appropriate, 4~5 = excessive
    """
    matches, total = 0, 0
    for entry in analyze_data:
        resp = entry.get("response")
        if not resp:
            continue
        ai_zone = resp.get("scores", {}).get(item_key, {}).get("zone")
        if not ai_zone:
            continue

        # 트레이너 점수에서 zone 역산 (analyze_t2.json에 저장된 raw 응답 이용)
        # 실제 트레이너 데이터가 있으면 활용, 없으면 skip
        total += 1
        # placeholder: 실제 데이터 도착 후 trainer_means와 매칭 구현

    return matches / total if total > 0 else None


def run(analyze_path: Path, ai_scores_path: Path, out_path: Path) -> None:
    # analyze_t2.json에서 per-item 상관계수 로드
    correlations: dict = {}
    if analyze_path.exists():
        with open(analyze_path, encoding="utf-8") as f:
            analyze_data = json.load(f)
        correlations = analyze_data.get("correlations", {})
        raw_entries  = analyze_data.get("raw", [])
    else:
        print("[경고] analyze_t2.json 없음. 기존 ai_scores.json만으로 분류.")
        raw_entries = []

    # ai_scores.json에서 매핑 유무 확인
    mapped_cols: set = set()
    if ai_scores_path.exists():
        with open(ai_scores_path, encoding="utf-8") as f:
            ai_scores = json.load(f)
        mapped_cols = set(ai_scores.get("mappings", {}).keys())

    results     = {}
    promotions  = []  # medium → high 승격
    demotions   = []  # high → medium/unavailable
    new_highs   = []  # 신규 high 진입

    print(f"\n{'─'*65}")
    print(f" {'항목':8s}  {'r':>6}  {'p':>7}  {'분류':>14}  {'변화'}")
    print(f"{'─'*65}")

    for col in SCORE_COLS:
        cr   = correlations.get(col, {})
        r_v  = cr.get("r")
        p_v  = cr.get("p")
        n_v  = cr.get("n", 0)

        # 매핑 없으면 강제 unavailable
        if col not in mapped_cols and col not in {"공명개방", "혀경직도"}:
            classification = "unavailable"
        else:
            zone_match = compute_zone_match(raw_entries, col,
                                            next((k for k, v in ITEM_KEY_MAP.items()
                                                  if v == col), None))
            classification = classify(r_v, p_v, zone_match)

        # 변화 감지
        if col in CURRENT_HIGH:
            prev = "high"
        elif col in CURRENT_MEDIUM:
            prev = "medium"
        elif col in CURRENT_UNAVAILABLE:
            prev = "unavailable"
        else:
            prev = "low_correlation"

        change = ""
        if classification == "high" and prev == "medium":
            change = "⬆ medium→high"
            promotions.append(col)
        elif classification == "high" and prev not in ("high", "medium"):
            change = "🆕 →high"
            new_highs.append(col)
        elif classification == "medium" and prev == "high":
            change = "⬇ high→medium"
            demotions.append(col)
        elif classification != prev:
            change = f"→{classification}"

        r_str = f"{r_v:.3f}" if r_v is not None else "N/A"
        p_str = f"{p_v:.4f}" if p_v is not None else "N/A"
        print(f"  {col:8s}  {r_str:>6}  {p_str:>7}  {classification:>14}  {change}")

        results[col] = {
            "classification": classification,
            "r": r_v, "p": p_v, "n": n_v,
            "prev": prev,
        }

    print(f"{'─'*65}")

    # 알림
    if promotions:
        print(f"\n🔔 [앱 갱신 신호] medium → high 승격: {promotions}")
        print("   → 앱 화면 신뢰도 배지 갱신 필요 (schemas.py ReliabilityInfo)")
    if new_highs:
        print(f"🆕 신규 high 진입: {new_highs}")
    if demotions:
        print(f"⬇  high → medium 강등: {demotions}")
    if not promotions and not new_highs and not demotions:
        print("\n변화 없음. 분류 현행 유지.")

    output = {
        "items":      results,
        "promotions": promotions,
        "demotions":  demotions,
        "new_highs":  new_highs,
        "high":   [c for c, v in results.items() if v["classification"] == "high"],
        "medium": [c for c, v in results.items() if v["classification"] == "medium"],
        "unavailable": [c for c, v in results.items()
                        if v["classification"] in ("unavailable", "low_correlation")],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n출력: {out_path}")

    if promotions:
        print("\n다음 단계: schemas.py의 ReliabilityInfo 주석 갱신 후 model_server 재시작.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze-t2",
                    default=str(RESULTS_DIR / "analyze_t2.json"))
    ap.add_argument("--ai-scores",
                    default=str(RESULTS_DIR / "ai_scores.json"))
    ap.add_argument("--out",
                    default=str(RESULTS_DIR / "reliability_t2.json"))
    args = ap.parse_args()
    run(Path(args.analyze_t2), Path(args.ai_scores), Path(args.out))


if __name__ == "__main__":
    main()
