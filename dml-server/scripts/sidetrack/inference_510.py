"""
inference_510.py — 5/10 데이터 21명 EfficientEGGNet 일괄 추론

- A그룹 10명 (validation_510/) + B그룹 11명 (control_pre_510/)
- pipeline.analyze() 직접 호출 (HTTP 우회 → 빠름, GPU 메모리 1회 로드)
- 결과: results/sidetrack/inference_510/{A1..A10,B1..B11}.json
  - 9항목 ai_score + indicators(cq_peak, cpp_mean...) + audio_info
- 통계 요약: 9항목 분포, voiced_ratio, 처리 시간
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# pipeline 임포트
_SERVER_DIR = "/home/dmlserver/projects/egg_prediction/dml-server/model_server"
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)
from analysis_pipeline import AnalysisPipeline, SilentInputError  # noqa: E402

ROOT = Path("/home/dmlserver/projects/egg_prediction")
CHECKPOINT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRITERIA   = ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPPINGS   = ROOT / "data/vocal_academy/results/ai_scores.json"

A_DIR = ROOT / "data/vocal_academy/validation_510"
B_DIR = ROOT / "data/vocal_academy/control_pre_510"
OUT_DIR = ROOT / "data/vocal_academy/results/sidetrack/inference_510"

SCORE_KEYS = [
    "1_nasal_oral_ratio", "2_chest_head_voice", "3_vocal_fold_contact",
    "4_breathiness", "5_forward_resonance", "6_soft_palate",
    "7_larynx_tongue_root", "8_tongue_tension", "9_pressure_balance",
]
SCORE_LABELS = {
    "1_nasal_oral_ratio":     "비강사용",
    "2_chest_head_voice":     "흉성두성",
    "3_vocal_fold_contact":   "접촉강도",
    "4_breathiness":          "호흡식별",
    "5_forward_resonance":    "전방공명",
    "6_soft_palate":          "연구개위치",
    "7_larynx_tongue_root":   "공명개방",
    "8_tongue_tension":       "혀경직도",
    "9_pressure_balance":     "상압하압",
}


def singer_id_from(name: str) -> str:
    """B6(앱).wav → B6 / A1.wav → A1"""
    base = name.rsplit(".", 1)[0]
    return re.sub(r"\(.+?\)", "", base).strip()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[load] AnalysisPipeline ...")
    t_load = time.perf_counter()
    pipeline = AnalysisPipeline(str(CHECKPOINT), str(CRITERIA), str(MAPPINGS))
    print(f"  로드 완료 ({(time.perf_counter()-t_load)*1000:.0f}ms)\n")

    wavs: list[tuple[str, Path]] = []
    for d in (A_DIR, B_DIR):
        for w in sorted(d.glob("*.wav")):
            sid = singer_id_from(w.name)
            wavs.append((sid, w))
    print(f"[inference] 21명 일괄 추론 시작 ({len(wavs)}개 wav)\n")

    results: list[dict] = []
    failed:  list[dict] = []
    t_total = time.perf_counter()

    for i, (sid, wav_path) in enumerate(wavs, 1):
        try:
            audio_bytes = wav_path.read_bytes()
            t0 = time.perf_counter()
            result = pipeline.analyze(audio_bytes)
            elapsed = (time.perf_counter() - t0) * 1000

            # JSON 저장 (slim — 핵심 필드만)
            slim = {
                "singer_id":          sid,
                "wav_filename":       wav_path.name,
                "audio_info":         result.get("audio_info"),
                "register_boundaries": result.get("register_boundaries"),
                "registers":          result.get("registers"),
                "indicators":         result.get("indicators"),
                "scores":             result.get("scores"),
                "feedback":           None,         # 빠른 분석 위해 생략
                "processing_time_ms": round(elapsed, 1),
            }
            (OUT_DIR / f"{sid}.json").write_text(
                json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            ai = result.get("audio_info") or {}
            scores = result.get("scores") or {}
            print(f"  [{i:2d}/21] {sid:5s}  {elapsed:>6.0f}ms  "
                  f"voiced={ai.get('voiced_ratio'):.2f}  "
                  f"voiced_s={ai.get('voiced_duration_s'):.1f}s")
            results.append(slim)

        except SilentInputError as e:
            failed.append({"singer_id": sid, "reason": "no_voice", "msg": e.reason})
            print(f"  [{i:2d}/21] {sid:5s}  ❌ no_voice: {e.reason}")
        except Exception as e:
            failed.append({"singer_id": sid, "reason": "error", "msg": str(e)})
            print(f"  [{i:2d}/21] {sid:5s}  ❌ {type(e).__name__}: {e}")

    total_ms = (time.perf_counter() - t_total) * 1000
    print(f"\n총 처리 시간: {total_ms/1000:.1f}s "
          f"(평균 {total_ms/max(1,len(results)):.0f}ms/곡, n={len(results)})")
    if failed:
        print(f"\n[실패 {len(failed)}건]")
        for f in failed:
            print(f"  {f['singer_id']}: {f['reason']} — {f['msg']}")

    # ── 통계 요약 ────────────────────────────────────────────────────
    if not results:
        print("\n[ERR] 성공 결과 없음.")
        return

    print("\n" + "=" * 80)
    print("9항목 ai_score 분포 (n=" + str(len(results)) + ")")
    print("=" * 80)
    print(f"  {'항목':10s}  {'min':>6s}  {'max':>6s}  {'mean':>6s}  {'median':>7s}  {'n_ok':>5s}")
    for k in SCORE_KEYS:
        vals = []
        for r in results:
            s = (r.get("scores") or {}).get(k) or {}
            v = s.get("ai_score")
            if v is not None:
                vals.append(v)
        if vals:
            import statistics
            mn, mx = min(vals), max(vals)
            me = statistics.mean(vals)
            md = statistics.median(vals)
            print(f"  {SCORE_LABELS[k]:10s}  {mn:>6.2f}  {mx:>6.2f}  {me:>6.2f}  "
                  f"{md:>7.2f}  {len(vals):>4d}/{len(results)}")
        else:
            print(f"  {SCORE_LABELS[k]:10s}  (모두 null)")

    # ── voiced_ratio 분포 + 신뢰도 의심 ──────────────────────────────
    print("\n" + "=" * 80)
    print("voiced_ratio / voiced_duration 분포")
    print("=" * 80)
    vrs = [(r["singer_id"],
            (r.get("audio_info") or {}).get("voiced_ratio"),
            (r.get("audio_info") or {}).get("voiced_duration_s"))
           for r in results]
    vr_only = [v for _, v, _ in vrs if v is not None]
    vd_only = [d for _, _, d in vrs if d is not None]
    if vr_only:
        print(f"  voiced_ratio:    min={min(vr_only):.3f}  max={max(vr_only):.3f}  "
              f"mean={sum(vr_only)/len(vr_only):.3f}")
        print(f"  voiced_duration: min={min(vd_only):.1f}s  max={max(vd_only):.1f}s  "
              f"mean={sum(vd_only)/len(vd_only):.1f}s")
    # 의심 케이스
    print("\n  [의심 케이스 — voiced_ratio < 0.3 또는 voiced_s < 30s]")
    sus = [(s, v, d) for s, v, d in vrs if (v is not None and v < 0.3) or (d is not None and d < 30)]
    if sus:
        for s, v, d in sus:
            print(f"    {s}: voiced_ratio={v:.3f}  voiced_s={d:.1f}s")
    else:
        print("    (없음 — 모두 정상)")

    # ── indicators 분포 (cq_peak=cq_p90, cpp_mean) ───────────────────
    print("\n" + "=" * 80)
    print("indicators 분포 (cq_p90 = 접촉강도 원본 / cpp_mean = 호흡식별 원본)")
    print("=" * 80)
    for key in ("cq_peak", "cpp_mean"):
        vals = []
        for r in results:
            v = (r.get("indicators") or {}).get(key)
            if v is not None:
                vals.append(v)
        if vals:
            import statistics
            mn, mx = min(vals), max(vals)
            me = statistics.mean(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
            # outlier: |z| > 2.5
            outliers = []
            for r in results:
                v = (r.get("indicators") or {}).get(key)
                if v is None:
                    continue
                z = (v - me) / sd if sd > 0 else 0
                if abs(z) > 2.5:
                    outliers.append((r["singer_id"], v, z))
            label = "cq_p90" if key == "cq_peak" else key
            print(f"  {label:10s}: min={mn:.4f}  max={mx:.4f}  mean={me:.4f}  std={sd:.4f}")
            if outliers:
                print(f"    [outlier |z|>2.5]:", end=" ")
                print(", ".join(f"{s}({v:.3f},z={z:+.1f})" for s, v, z in outliers))
            else:
                print(f"    [outlier 없음]")

    print(f"\n출력 디렉토리: {OUT_DIR}")
    print(f"실패: {len(failed)}건  /  성공: {len(results)}건")


if __name__ == "__main__":
    main()
