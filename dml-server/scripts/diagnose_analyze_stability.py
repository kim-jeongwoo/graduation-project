#!/usr/bin/env python3
"""
diagnose_analyze_stability.py — model_server /analyze 연속 호출 안정성 진단

목적: test_05 422 에러 재현 및 패턴 판정 (5월 10일 일괄 분석 전 안정성 확보)

동작:
  1. warm-up 1회 (짧은 wav)
  2. validation/test_01~11 순서대로 N 라운드 반복 호출
  3. 응답 시간, status, GPU 메모리, 에러 기록
  4. 422 발생 패턴 분석 → 권고사항 출력

실행:
  conda activate EGGDML
  cd ~/projects/egg_prediction
  python dml-server/scripts/diagnose_analyze_stability.py
  python dml-server/scripts/diagnose_analyze_stability.py --rounds 3 --delay 0
  python dml-server/scripts/diagnose_analyze_stability.py --host http://localhost:8001 --out results/stability.json
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_DIR    = PROJECT_ROOT / "data" / "vocal_academy" / "validation"
RESULTS_DIR  = PROJECT_ROOT / "dml-server" / "results"

TEST_IDS = [f"test_{i:02d}" for i in range(1, 12)]  # test_01 ~ test_11

# 422 건수 이상 시 패턴으로 판정
PATTERN_THRESHOLD = 2


def gpu_memory_mb() -> dict:
    """nvidia-smi로 GPU 메모리 사용량(MB) 반환. 실패 시 None."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total",
             "--format=csv,noheader,nounits"],
            timeout=5,
        ).decode().strip().split(",")
        used, free, total = [int(x.strip()) for x in out]
        return {"used_mb": used, "free_mb": free, "total_mb": total}
    except Exception:
        return {"used_mb": None, "free_mb": None, "total_mb": None}


def call_health(host: str) -> bool:
    try:
        r = requests.get(f"{host}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def call_analyze(host: str, wav_path: Path) -> dict:
    """POST /analyze. 항상 dict 반환 (에러 포함)."""
    gpu_before = gpu_memory_mb()
    t0 = time.perf_counter()
    try:
        with open(wav_path, "rb") as f:
            r = requests.post(
                f"{host}/analyze",
                files={"file": (wav_path.name, f, "audio/wav")},
                timeout=300,
            )
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        gpu_after  = gpu_memory_mb()
        return {
            "status_code": r.status_code,
            "ok": r.status_code == 200,
            "elapsed_ms": elapsed_ms,
            "gpu_before": gpu_before,
            "gpu_after": gpu_after,
            "body_snippet": r.text[:200] if r.status_code != 200 else "",
        }
    except requests.Timeout:
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        return {
            "status_code": "timeout",
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "gpu_before": gpu_before,
            "gpu_after": gpu_memory_mb(),
            "body_snippet": "timeout",
        }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        return {
            "status_code": "exception",
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "gpu_before": gpu_before,
            "gpu_after": gpu_memory_mb(),
            "body_snippet": str(e)[:200],
        }


def run(host: str, rounds: int, delay_s: float, out_path: Path) -> None:
    if not call_health(host):
        print(f"[ERROR] model_server 응답 없음: {host}", file=sys.stderr)
        sys.exit(1)

    print(f"[stability] model_server: {host}")
    print(f"[stability] rounds={rounds}, delay={delay_s}s, 대상={len(TEST_IDS)}곡\n")

    # ── Warm-up ────────────────────────────────────────────────────────
    warmup_id  = "test_10"  # 가장 짧은 파일 (101s)
    warmup_wav = VALID_DIR / f"{warmup_id}.wav"
    if warmup_wav.exists():
        print(f"[warm-up] {warmup_id} ...", end=" ", flush=True)
        res = call_analyze(host, warmup_wav)
        status_str = "OK" if res["ok"] else f"FAIL({res['status_code']})"
        print(f"{status_str} ({res['elapsed_ms']}ms)")
    else:
        print(f"[warm-up] {warmup_id}.wav 없음 — 건너뜀")

    if delay_s > 0:
        time.sleep(delay_s)

    # ── 본 실행 ───────────────────────────────────────────────────────
    call_log: list = []
    error_count: dict = {}  # status_code → count

    print(f"\n{'라운드':6s} {'test_id':10s} {'status':8s} {'ms':>7s}  "
          f"{'GPU_used':>9s}  {'GPU_free':>9s}  body_snippet")
    print("─" * 85)

    for rnd in range(1, rounds + 1):
        for tid in TEST_IDS:
            wav_path = VALID_DIR / f"{tid}.wav"
            if not wav_path.exists():
                print(f"  {rnd:4d}   {tid:10s} {'MISSING':8s}")
                continue

            res      = call_analyze(host, wav_path)
            sc       = res["status_code"]
            ok_str   = "OK" if res["ok"] else f"ERR:{sc}"
            used_mb  = res["gpu_after"].get("used_mb")
            free_mb  = res["gpu_after"].get("free_mb")
            used_str = f"{used_mb:>7d}MB" if used_mb is not None else "       N/A"
            free_str = f"{free_mb:>7d}MB" if free_mb is not None else "       N/A"
            snip     = res["body_snippet"][:60].replace("\n", " ")

            print(f"  {rnd:4d}   {tid:10s} {ok_str:8s} {res['elapsed_ms']:>7d}  "
                  f"{used_str}  {free_str}  {snip}")

            call_log.append({
                "round": rnd, "test_id": tid,
                "wav_path": str(wav_path.relative_to(PROJECT_ROOT)),
                **res,
            })

            if not res["ok"]:
                error_count[str(sc)] = error_count.get(str(sc), 0) + 1

            if delay_s > 0:
                time.sleep(delay_s)

    # ── 분석 ──────────────────────────────────────────────────────────
    total_calls   = len(call_log)
    ok_calls      = sum(1 for r in call_log if r["ok"])
    fail_calls    = total_calls - ok_calls
    times_ok      = [r["elapsed_ms"] for r in call_log if r["ok"]]
    avg_ms        = round(sum(times_ok) / len(times_ok)) if times_ok else 0
    max_ms        = max(times_ok) if times_ok else 0

    print("\n" + "═" * 85)
    print(f" 안정성 진단 결과")
    print(f"  총 호출: {total_calls}  성공: {ok_calls}  실패: {fail_calls}")
    print(f"  성공률: {ok_calls/total_calls*100:.1f}%")
    print(f"  응답시간 (성공): avg={avg_ms}ms  max={max_ms}ms")
    if error_count:
        print(f"  에러 분포: {error_count}")

    # 422 패턴 판정
    n_422 = error_count.get("422", 0)
    if n_422 >= PATTERN_THRESHOLD:
        print(f"\n⚠  [패턴 감지] 422 오류 {n_422}회 — 재현 가능한 안정성 문제")
        print("  권고 조치:")
        print("  1. model_server에 N회마다 torch.cuda.empty_cache() 호출 추가")
        print("  2. /analyze에 자동 1회 재시도 로직 추가")
        print("  3. 일괄 분석 시 wavs 간 delay_s >= 1 추가")
        pattern = "detected"
    elif n_422 > 0:
        print(f"\n  [주의] 422 오류 {n_422}회 — 패턴 미달 ({PATTERN_THRESHOLD}회 미만)")
        pattern = "marginal"
    else:
        print(f"\n  [정상] 422 오류 없음 — 안정적")
        pattern = "stable"

    print("═" * 85)

    # ── 저장 ──────────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at":   datetime.now().isoformat(),
        "host":           host,
        "rounds":         rounds,
        "delay_s":        delay_s,
        "total_calls":    total_calls,
        "ok_calls":       ok_calls,
        "fail_calls":     fail_calls,
        "success_rate":   round(ok_calls / total_calls, 4) if total_calls else 0,
        "avg_elapsed_ms": avg_ms,
        "max_elapsed_ms": max_ms,
        "error_count":    error_count,
        "pattern":        pattern,
        "calls":          call_log,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n출력: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host",   default="http://localhost:8001")
    ap.add_argument("--rounds", type=int, default=1,
                    help="전체 반복 횟수 (기본 1 = 11곡 1회)")
    ap.add_argument("--delay",  type=float, default=0.0,
                    help="호출 간 대기 시간(초). 0 = 대기 없음")
    ap.add_argument("--out",    default=str(RESULTS_DIR / "stability_report.json"))
    args = ap.parse_args()
    run(args.host, args.rounds, args.delay, Path(args.out))


if __name__ == "__main__":
    main()
