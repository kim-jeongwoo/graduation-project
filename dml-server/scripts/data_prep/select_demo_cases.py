#!/usr/bin/env python3
"""
select_demo_cases.py — 시연용 mock 응답 5종 케이스 선별 + /analyze 호출 + JSON 저장

케이스 정의:
  excellent_high        호흡식별/접촉강도 모두 2~3점 + 균형 잡힌 "잘 부른 사례"
  needs_work_breathing  호흡식별 1점 이하 (기식음 과다)
  needs_work_contact    접촉강도 3.5점 이상 (성대 과압박)
  needs_work_both       호흡+접촉 동시 양극단 (mid/high register)
  medium_quality        전 항목 2~3점 전반적 평균 수준

실행:
  conda activate EGGDML
  cd ~/projects/egg_prediction

  # 케이스 선별 리포트만 (model_server 불필요)
  python dml-server/scripts/data_prep/select_demo_cases.py --report-only

  # 선별 + /analyze 호출 + JSON 저장
  python dml-server/scripts/data_prep/select_demo_cases.py [--host http://localhost:8001]
"""

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"
VALID_DIR    = VOCAL_DIR / "validation"
RESULTS_DIR  = PROJECT_ROOT / "dml-server" / "results" / "demo_responses"
CSV_PATH     = VOCAL_DIR / "trainer_scores_validation.csv"

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

# 한국어 항목명 → /analyze 응답 scores 키 (앞 숫자 포함)
KO_TO_API_KEY = {
    "비강사용":  "1_nasal_oral_ratio",
    "흉성두성":  "2_chest_head_voice",
    "접촉강도":  "3_vocal_fold_contact",
    "호흡식별":  "4_breathiness",
    "전방공명":  "5_forward_resonance",
    "연구개위치": "6_soft_palate",
    "공명개방":  "7_larynx_tongue",
    "혀경직도":  "8_tongue_tension",
    "상압하압":  "9_pressure_balance",
}

# 5종 케이스 고정 선별 (트레이너 데이터 기반 확정)
DEMO_CASES = {
    "excellent_high": {
        "test_id":   "test_11",
        "rationale": "전 register 호흡/접촉 2~3점 균형. avg=2.55. 가장 '적절' 범위 일관",
        "highlight": "호흡식별 2.0/3.0/3.4, 접촉강도 2.2/2.4/3.2 (low/mid/high)",
        "case_description": "잘 부른 사례. 호흡식별/접촉강도 모두 적절 범위(2~3점). 모든 음역대 균형.",
        "expected_feedback_focus": [
            "4_breathiness:appropriate",
            "3_vocal_fold_contact:appropriate",
        ],
    },
    "needs_work_breathing": {
        "test_id":   "test_08",
        "rationale": "호흡식별 평균 1.13. 전 register 0.8/1.0/1.6 — 기식음 과다 명확",
        "highlight": "호흡식별이 모든 음역대에서 insufficient(0~1) 범위",
        "case_description": "기식음 과다(호흡식별 부족). 모든 음역대에서 호흡이 insufficient. 호흡 개선 필요.",
        "expected_feedback_focus": [
            "4_breathiness:insufficient",
        ],
    },
    "needs_work_contact": {
        "test_id":   "test_05",
        "rationale": "접촉강도 평균 3.47 (최고). high register 4.0 — 성대 과압박 케이스",
        "highlight": "접촉강도 2.6/3.8/4.0 (low/mid/high), 고음부로 갈수록 과압박 심화",
        "case_description": "성대 과압박(접촉강도 과잉). 고음부에서 접촉강도 4.0 — 완화 필요.",
        "expected_feedback_focus": [
            "3_vocal_fold_contact:excessive",
        ],
    },
    "needs_work_both": {
        "test_id":   "test_01",
        "rationale": "mid 호흡=4.0/접촉=3.6, high 호흡=4.2/접촉=4.0 — 양 항목 동시 과잉",
        "highlight": "저음부는 적절하나 중·고음부에서 호흡+접촉 모두 excessive(4+)",
        "case_description": "호흡식별+접촉강도 동시 과잉. 중·고음부에서 두 항목 모두 excessive(4+). 종합 개선 필요.",
        "expected_feedback_focus": [
            "4_breathiness:excessive",
            "3_vocal_fold_contact:excessive",
        ],
    },
    "medium_quality": {
        "test_id":   "test_10",
        "rationale": "avg=2.68. 전 항목 2~3점대. 101s로 /analyze 응답 빠름",
        "highlight": "가장 '평균적' 프로파일. 특이 항목 없음",
        "case_description": "전반적 평균 수준. 9개 항목 모두 2~3점대. 두드러지는 강점·약점 없음.",
        "expected_feedback_focus": [
            "4_breathiness:appropriate",
            "3_vocal_fold_contact:appropriate",
        ],
    },
}


def load_trainer_means() -> dict:
    """test_id → {overall: {col: mean}, per_register: {reg: {col: mean}}}"""
    raw: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = row["test_id"]
            reg = row["register"]
            for col in SCORE_COLS:
                val = row.get(col, "")
                if val:
                    try:
                        raw[tid][reg][col].append(float(val))
                    except ValueError:
                        pass

    result = {}
    for tid, regs in raw.items():
        per_reg = {}
        all_vals: dict = defaultdict(list)
        for reg, items in regs.items():
            per_reg[reg] = {col: round(float(np.mean(v)), 2)
                            for col, v in items.items() if v}
            for col, v in items.items():
                all_vals[col].extend(v)
        overall = {col: round(float(np.mean(v)), 2)
                   for col, v in all_vals.items() if v}
        result[tid] = {"overall": overall, "per_register": per_reg}
    return result


def wav_duration_sec(wav_path: Path) -> float:
    import wave
    try:
        with wave.open(str(wav_path)) as w:
            return round(w.getnframes() / w.getframerate(), 1)
    except Exception:
        return 0.0


def print_selection_report(trainer_means: dict) -> None:
    print("\n" + "═" * 70)
    print(" 시연용 mock 케이스 선별 리포트")
    print("═" * 70)

    for case_name, info in DEMO_CASES.items():
        tid  = info["test_id"]
        data = trainer_means.get(tid, {})
        overall = data.get("overall", {})
        per_reg = data.get("per_register", {})
        dur  = wav_duration_sec(VALID_DIR / f"{tid}.wav")

        breath  = overall.get("호흡식별", "?")
        contact = overall.get("접촉강도", "?")
        avg_all = round(float(np.mean([v for v in overall.values()])), 2) if overall else 0

        print(f"\n▶ [{case_name}]  →  {tid}  ({dur}s)")
        print(f"  이유: {info['rationale']}")
        print(f"  포인트: {info['highlight']}")
        print(f"  트레이너 전체 평균:  호흡식별={breath}  접촉강도={contact}  9항목 avg={avg_all}")

        # per-register 요약
        for reg in ["low", "mid", "high"]:
            if reg not in per_reg:
                continue
            r = per_reg[reg]
            vals = [r.get(c, 0) for c in SCORE_COLS]
            print(f"  {reg:4s}: 호흡={r.get('호흡식별','?'):4}  접촉={r.get('접촉강도','?'):4}  "
                  f"| {' '.join(f'{v:.1f}' for v in vals)}")

    print("\n" + "─" * 70)
    print(" 9항목 전체 평균 비교표")
    print(f"  {'케이스':24s} {'test':7s} " + " ".join(f"{c[:3]:>5s}" for c in SCORE_COLS))
    print("  " + "─" * 68)
    for case_name, info in DEMO_CASES.items():
        tid  = info["test_id"]
        overall = trainer_means.get(tid, {}).get("overall", {})
        vals = [overall.get(c, 0) for c in SCORE_COLS]
        print(f"  {case_name:24s} {tid:7s} " + " ".join(f"{v:5.2f}" for v in vals))
    print("═" * 70)


def analyze_wav(host: str, wav_path: Path) -> dict | None:
    if not HAS_REQUESTS:
        print("  [ERROR] requests 미설치", file=sys.stderr)
        return None
    with open(wav_path, "rb") as f:
        try:
            r = requests.post(
                f"{host}/analyze",
                files={"file": (wav_path.name, f, "audio/wav")},
                timeout=300,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [ERROR] {wav_path.name}: {e}", file=sys.stderr)
            return None


def check_server(host: str) -> bool:
    if not HAS_REQUESTS:
        return False
    try:
        r = requests.get(f"{host}/health", timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] model_server 응답 없음 ({host}): {e}", file=sys.stderr)
        return False


def build_trainer_scores_by_item(per_register: dict) -> dict:
    """
    {api_key: {register: mean_score}} 형태로 변환.
    앱이 트레이너 점수를 /analyze 응답 키와 직접 비교 가능하도록.
    """
    result = {}
    for ko, api_key in KO_TO_API_KEY.items():
        result[api_key] = {
            reg: per_register.get(reg, {}).get(ko)
            for reg in ["low", "mid", "high"]
        }
    return result


def run_analyze(host: str, trainer_means: dict) -> None:
    if not check_server(host):
        print("model_server 가동 후 재실행하세요.", file=sys.stderr)
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n[분석] model_server {host} 연결 확인")
    print(f"[분석] 출력 디렉토리: {RESULTS_DIR}\n")

    index_cases = {}
    results_summary = {}

    for case_name, info in DEMO_CASES.items():
        tid      = info["test_id"]
        wav_path = VALID_DIR / f"{tid}.wav"
        dur      = wav_duration_sec(wav_path)

        if not wav_path.exists():
            print(f"  [{case_name}] {tid}.wav 없음 — skip")
            results_summary[case_name] = {"status": "error", "msg": "wav 없음"}
            continue

        print(f"  [{case_name}] {tid} ({dur}s) 분석 중...", end=" ", flush=True)
        t0       = time.time()
        response = analyze_wav(host, wav_path)
        elapsed  = time.time() - t0

        if response is None:
            print("FAIL")
            results_summary[case_name] = {"status": "error", "msg": "analyze 실패"}
            continue

        print(f"OK ({elapsed:.1f}s)")

        analyzed_at       = datetime.now().isoformat()
        processing_time_ms = round(elapsed * 1000)
        per_reg            = trainer_means.get(tid, {}).get("per_register", {})
        overall            = trainer_means.get(tid, {}).get("overall", {})

        # 개별 케이스 JSON (전체 응답 포함)
        out = {
            "case_name":             case_name,
            "test_id":               tid,
            "case_description":      info["case_description"],
            "rationale":             info["rationale"],
            "wav_path":              str(wav_path.relative_to(PROJECT_ROOT)),
            "duration_sec":          dur,
            "analyzed_at":           analyzed_at,
            "processing_time_ms":    processing_time_ms,
            "trainer_overall":       overall,
            "trainer_per_register":  per_reg,
            "expected_feedback_focus": info["expected_feedback_focus"],
            "analyze_response":      response,
        }

        out_path = RESULTS_DIR / f"{case_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        results_summary[case_name] = {
            "status": "ok", "path": str(out_path),
            "elapsed_s": round(elapsed, 1),
        }

        # index 항목 (앱이 케이스 목록 탐색에 사용)
        index_cases[case_name] = {
            "test_id":                tid,
            "wav_path":               str(wav_path.relative_to(PROJECT_ROOT)),
            "duration_sec":           dur,
            "trainer_scores":         build_trainer_scores_by_item(per_reg),
            "trainer_overall":        {KO_TO_API_KEY[k]: v for k, v in overall.items()
                                       if k in KO_TO_API_KEY},
            "registers":              [r for r in ["low", "mid", "high"] if r in per_reg],
            "case_description":       info["case_description"],
            "expected_feedback_focus": info["expected_feedback_focus"],
            "analyzed_at":            analyzed_at,
            "processing_time_ms":     processing_time_ms,
        }

    # index.json
    index_path = RESULTS_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "model_server":  host,
            "cases":         index_cases,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n완료. index: {index_path}")
    for case_name, s in results_summary.items():
        status = "✓" if s["status"] == "ok" else "✗"
        msg    = s.get("elapsed_s", s.get("msg", ""))
        suffix = f"({msg}s)" if s["status"] == "ok" else f"[{msg}]"
        print(f"  {status} {case_name} {suffix}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host",        default="http://localhost:8001")
    ap.add_argument("--report-only", action="store_true",
                    help="선별 리포트만 출력 (model_server 호출 안 함)")
    args = ap.parse_args()

    trainer_means = load_trainer_means()
    print_selection_report(trainer_means)

    if args.report_only:
        return

    print(f"\n위 케이스로 /analyze 호출을 진행합니다. (host={args.host})")
    run_analyze(args.host, trainer_means)


if __name__ == "__main__":
    main()
