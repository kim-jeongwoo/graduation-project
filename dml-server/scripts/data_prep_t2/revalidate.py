#!/usr/bin/env python3
"""
revalidate.py — 신규 wav를 model_server /analyze로 분석 후 트레이너 점수와 비교

실행:
  python revalidate.py [--mode validation|control_pre|control_post|all]
                        [--host http://localhost:8001]
                        [--csv trainer_scores_t2.csv]
                        [--wav-dir <폴더>]
                        [--out results/analyze_t2.json]

wav 경로 규칙 (--wav-dir 미지정 시 기본값):
  validation  → data/vocal_academy/validation_t2/test_{id}.wav
  control_pre → data/vocal_academy/control_pre/singer_{id}.wav
  control_post→ data/vocal_academy/control_post/singer_{id}.wav
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import requests
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOCAL_DIR    = PROJECT_ROOT / "data" / "vocal_academy"
RESULTS_DIR  = VOCAL_DIR / "results"

SCORE_COLS = ["비강사용", "흉성두성", "접촉강도", "호흡식별",
              "전방공명", "연구개위치", "공명개방", "혀경직도", "상압하압"]

# /analyze 응답의 scores 키 → trainer CSV 컬럼 매핑
ITEM_KEY_MAP = {
    "1_nasal_oral_ratio":      "비강사용",
    "2_chest_head_voice":      "흉성두성",
    "3_vocal_fold_contact":    "접촉강도",
    "4_breathiness":           "호흡식별",
    "5_forward_resonance":     "전방공명",
    "6_soft_palate":           "연구개위치",
    "7_larynx_tongue":         "공명개방",
    "8_tongue_tension":        "혀경직도",
    "9_pressure_balance":      "상압하압",
}
REGISTER_MAP = {"low": "저", "mid": "중", "high": "고"}


def check_server(host: str, retries: int = 3) -> None:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(f"{host}/health", timeout=30)
            r.raise_for_status()
            print(f"[health] OK ({host})")
            return
        except Exception as e:
            if attempt < retries:
                print(f"[health] 시도 {attempt}/{retries} 실패, 재시도...", file=sys.stderr)
                time.sleep(5)
            else:
                print(f"[ERROR] model_server 응답 없음: {e}", file=sys.stderr)
                print("model_server 가동 후 재실행하세요.", file=sys.stderr)
                sys.exit(1)


def find_wavs(vocal_dir: Path, mode: str,
              wav_dir: Path | None = None) -> list[tuple[str, Path]]:
    """(id, wav_path) 목록 반환. wav_dir 지정 시 해당 폴더를 직접 스캔."""
    if wav_dir is not None:
        pattern = "test_*.wav" if mode == "validation" else "singer_*.wav"
        return [(wav.stem, wav) for wav in sorted(wav_dir.glob(pattern))]

    pairs = []
    if mode in ("validation", "all"):
        d = vocal_dir / "validation_t2"
        if d.exists():
            for wav in sorted(d.glob("test_*.wav")):
                pairs.append((wav.stem, wav))
    if mode in ("control_pre", "all"):
        d = vocal_dir / "control_pre"
        if d.exists():
            for wav in sorted(d.glob("singer_*.wav")):
                pairs.append((wav.stem, wav))
    if mode in ("control_post", "all"):
        d = vocal_dir / "control_post"
        if d.exists():
            for wav in sorted(d.glob("singer_*.wav")):
                pairs.append((wav.stem, wav))
    return pairs


def analyze_wav(host: str, wav_path: Path) -> dict | None:
    with open(wav_path, "rb") as f:
        try:
            r = requests.post(
                f"{host}/analyze",
                files={"file": (wav_path.name, f, "audio/wav")},
                timeout=120,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  [ERROR] {wav_path.name}: {e}", file=sys.stderr)
            return None


def load_trainer_means(csv_path: Path) -> dict:
    """singer_id → register → item → mean_score (5명 평균)"""
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
    means: dict = {}
    for sid, regs in raw.items():
        means[sid] = {}
        for reg, items in regs.items():
            means[sid][reg] = {col: float(np.mean(v)) if v else None
                               for col, v in items.items()}
    return means


def compute_correlations(analyze_results: list[dict],
                         trainer_means: dict) -> dict:
    """
    항목별 Pearson r 계산.
    분석 결과의 scores.{item_key}.ai_score vs 트레이너 mean.
    """
    # {col: [(ai_score, trainer_mean), ...]}
    pairs: dict = {col: [] for col in SCORE_COLS}

    for entry in analyze_results:
        wav_id   = entry["wav_id"]
        response = entry.get("response")
        if not response:
            continue

        scores = response.get("scores", {})
        regs   = response.get("registers", {})

        # 트레이너 점수 (register 포함 평균 또는 register별)
        t_data = trainer_means.get(wav_id, {})
        if not t_data:
            continue

        for item_key, col in ITEM_KEY_MAP.items():
            ai_item = scores.get(item_key)
            if not ai_item or ai_item.get("ai_score") is None:
                continue
            ai_score = ai_item["ai_score"]

            # 트레이너 평균: register 전체 평균 사용
            t_vals = [v for reg in t_data.values()
                      if (v := reg.get(col)) is not None]
            if not t_vals:
                continue
            t_mean = float(np.mean(t_vals))

            pairs[col].append((ai_score, t_mean))

    results = {}
    for col, xy in pairs.items():
        if len(xy) < 3:
            results[col] = {"r": None, "p": None, "n": len(xy)}
            continue
        ai_arr = np.array([x for x, _ in xy])
        tr_arr = np.array([y for _, y in xy])
        r, p = stats.pearsonr(ai_arr, tr_arr)
        results[col] = {"r": round(float(r), 4), "p": round(float(p), 4),
                        "n": len(xy)}
    return results


def run(host: str, mode: str, csv_path: Path, out_path: Path,
        wav_dir: Path | None = None) -> None:
    check_server(host)
    wavs = find_wavs(VOCAL_DIR, mode, wav_dir)

    if not wavs:
        print(f"[경고] {mode} 모드: wav 파일 없음.")
        print("  예상 경로:")
        print(f"    data/vocal_academy/validation_t2/test_*.wav")
        print(f"    data/vocal_academy/control_pre/singer_*.wav")
        print(f"    data/vocal_academy/control_post/singer_*.wav")
        return

    print(f"분석 대상: {len(wavs)}개 파일\n")
    analyze_results = []

    for wav_id, wav_path in wavs:
        print(f"  [{wav_id}] {wav_path.name} ...", end=" ", flush=True)
        t0 = time.time()
        resp = analyze_wav(host, wav_path)
        elapsed = time.time() - t0
        if resp:
            print(f"OK ({elapsed:.1f}s)")
        else:
            print("FAIL")
        analyze_results.append({"wav_id": wav_id, "wav_path": str(wav_path),
                                 "response": resp})

    # 트레이너 점수 로드 + 상관계수 계산
    trainer_means = load_trainer_means(csv_path)
    correlations  = compute_correlations(analyze_results, trainer_means)

    out = {
        "mode": mode,
        "n_wavs": len(wavs),
        "correlations": correlations,
        "raw": analyze_results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 상관계수 출력
    print(f"\n{'─'*55}")
    print(f" AI vs 트레이너 Pearson r (n={len(analyze_results)})")
    print(f"{'─'*55}")
    print(f"  {'항목':8s}  {'r':>6}  {'p':>7}  {'n':>4}")
    print(f"{'─'*55}")
    for col in SCORE_COLS:
        cr = correlations.get(col, {})
        r_v = cr.get("r")
        p_v = cr.get("p")
        n_v = cr.get("n", 0)
        if r_v is None:
            print(f"  {col:8s}  {'N/A':>6}  {'N/A':>7}  {n_v:>4}")
        else:
            print(f"  {col:8s}  {r_v:>6.3f}  {p_v:>7.4f}  {n_v:>4}")
    print(f"{'─'*55}")
    print(f"\n출력: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="all",
                    choices=["validation", "control_pre", "control_post", "all"])
    ap.add_argument("--host",    default="http://localhost:8001")
    ap.add_argument("--csv",     default=str(VOCAL_DIR / "trainer_scores_t2.csv"))
    ap.add_argument("--wav-dir", default=None,
                    help="wav 폴더 덮어쓰기 (기본: vocal_academy/validation_t2 또는 control_pre)")
    ap.add_argument("--out",     default=str(RESULTS_DIR / "analyze_t2.json"))
    args = ap.parse_args()
    wav_dir = Path(args.wav_dir) if args.wav_dir else None
    run(args.host, args.mode, Path(args.csv), Path(args.out), wav_dir)


if __name__ == "__main__":
    main()
