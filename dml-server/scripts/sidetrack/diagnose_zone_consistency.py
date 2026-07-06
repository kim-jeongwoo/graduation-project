"""
diagnose_zone_consistency.py — 9항목 카드 zone vs chunk zone 불일치 진단
Usage:
    conda activate EGGDML
    python dml-server/scripts/sidetrack/diagnose_zone_consistency.py [wav_path] [song_id]

기본값:
    wav_path = data/vocal_academy/validation_t2/test_11.wav
    song_id  = 004
"""
import sys
import io
import json
from pathlib import Path

_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "dml-server" / "model_server"))

from analysis_pipeline import AnalysisPipeline, MIN_VOICED_S
from services.timeline_analysis import build_chunks, analyze_with_timeline, MIN_DUR, MAX_DUR

CHECKPOINT = _ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRITERIA   = _ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPPINGS   = _ROOT / "data/vocal_academy/results/ai_scores.json"
LRC_DIR    = _ROOT / "data/songs/lrc/parsed"

ITEMS = ["3_vocal_fold_contact", "4_breathiness"]
ITEM_KO = {"3_vocal_fold_contact": "접촉강도", "4_breathiness": "호흡식별"}


def load_lrc(song_id: str) -> list | None:
    for suffix in [f"{song_id}_aligned.json", f"{song_id}.json"]:
        p = LRC_DIR / suffix
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return None


def zone_label(z):
    return {"insufficient": "미달", "appropriate": "적절",
            "excessive": "과함", None: "n/a"}.get(z, str(z))


def run(wav_path: str, song_id: str):
    print(f"\n{'='*65}")
    print(f"  wav  : {Path(wav_path).name}")
    print(f"  song_id: {song_id}")
    print(f"{'='*65}")

    pipeline = AnalysisPipeline(str(CHECKPOINT), str(CRITERIA), str(MAPPINGS))

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    # ── 1. 전체 wav 분석 ─────────────────────────────────────────────
    full = pipeline.analyze(audio_bytes)
    print(f"\n[전체 wav] voiced_ratio={full['audio_info']['voiced_ratio']:.3f}  "
          f"voiced_s={full['audio_info']['voiced_duration_s']:.1f}s")
    for key in ITEMS:
        s = full["scores"][key]
        print(f"  {ITEM_KO[key]:6s}: ai_score={s['ai_score']}  zone={s['zone']}  "
              f"confidence={s['confidence']}")

    # ── 2. LRC 로드 + 청크 빌드 ──────────────────────────────────────
    lrc = load_lrc(song_id)
    if not lrc:
        print(f"\n[오류] LRC 없음: song_id={song_id}")
        return

    chunks = build_chunks(lrc)
    print(f"\n[청크 빌드] {len(chunks)}개  "
          f"(MIN_DUR={MIN_DUR}s, MAX_DUR={MAX_DUR}s, MIN_VOICED_S={MIN_VOICED_S}s)")

    # 청크 길이 분포
    durs = [c["end_sec"] - c["start_sec"] for c in chunks]
    short = sum(1 for d in durs if d < MIN_VOICED_S)
    print(f"  길이 분포: min={min(durs):.1f}s  mean={sum(durs)/len(durs):.1f}s  "
          f"max={max(durs):.1f}s")
    print(f"  < {MIN_VOICED_S}s (skip 예상): {short}개 ({short/len(durs)*100:.0f}%)")

    # ── 3. 청크별 타임라인 분석 ──────────────────────────────────────
    timeline_scores, meta = analyze_with_timeline(audio_bytes, lrc, pipeline)
    print(f"\n[타임라인] n_ok={meta['n_ok']}  n_skipped={meta['n_skipped']}  "
          f"total={meta['n_chunks']}")

    # ── 4. zone 분포 집계 ────────────────────────────────────────────
    for key in ITEMS:
        zones = []
        scores_ok = []
        for ts in timeline_scores:
            item = ts["scores"].get(key)
            if item is None:
                zones.append(None)
            else:
                zones.append(item.get("zone"))
                ai = item.get("ai_score")
                if ai is not None:
                    scores_ok.append(ai)

        n_total = len(zones)
        cnt = {z: zones.count(z) for z in [None, "insufficient", "appropriate", "excessive"]}

        print(f"\n  [{ITEM_KO[key]}]")
        print(f"    전체 평균: {full['scores'][key]['ai_score']}점  "
              f"→ zone={full['scores'][key]['zone']}")
        if scores_ok:
            print(f"    청크 평균: {sum(scores_ok)/len(scores_ok):.2f}점  "
                  f"(analyzed {len(scores_ok)}개 평균)")
        print(f"    zone 분포 ({n_total}개):")
        for z, k in [("appropriate","적절"), ("insufficient","미달"),
                     ("excessive","과함"), (None,"n/a")]:
            n = cnt[z]
            bar = "█" * int(n/n_total*30) if n_total else ""
            print(f"      {k:6s}: {n:3d}개 ({n/n_total*100:4.0f}%)  {bar}")

    # ── 5. 청크별 상세 (처음 10개) ───────────────────────────────────
    print(f"\n[청크별 상세 (처음 10개)]")
    print(f"  {'#':>3}  {'시작':>6}  {'끝':>6}  {'길이':>5}  "
          f"{'접촉(score)':>14}  {'호흡(score)':>14}  텍스트")
    for i, ts in enumerate(timeline_scores[:10]):
        dur = ts["end_sec"] - ts["start_sec"]
        vfc = ts["scores"].get("3_vocal_fold_contact")
        bth = ts["scores"].get("4_breathiness")
        vfc_str = f"{vfc['ai_score']}({vfc['zone'][:3]})" if vfc else "n/a"
        bth_str = f"{bth['ai_score']}({bth['zone'][:3]})" if bth else "n/a"
        print(f"  {i:>3}  {ts['start_sec']:>6.1f}  {ts['end_sec']:>6.1f}  "
              f"{dur:>4.1f}s  {vfc_str:>14}  {bth_str:>14}  "
              f"{ts['lrc_text'][:25]}")

    # ── 6. 가설 판정 ─────────────────────────────────────────────────
    print(f"\n[가설 판정]")
    na_rate = meta["n_skipped"] / meta["n_chunks"] if meta["n_chunks"] else 0
    print(f"  가설 1 (임계값 불일치): ✗ 제거 — 동일한 _score_to_zone() 사용 확인")
    print(f"  가설 2 (n/a 비율 높음): {'⚠ 유력' if na_rate > 0.25 else '□ 낮음'}  "
          f"n/a={na_rate*100:.0f}% (skip {meta['n_skipped']}/{meta['n_chunks']})")
    print(f"  가설 3 (chunk 단위 통계 불안정): 아래 청크 평균 vs 전체 평균 비교로 확인")
    for key in ITEMS:
        scores_ok = [ts["scores"][key]["ai_score"]
                     for ts in timeline_scores
                     if ts["scores"].get(key) and ts["scores"][key].get("ai_score") is not None]
        if scores_ok:
            chunk_avg = sum(scores_ok) / len(scores_ok)
            full_score = full["scores"][key]["ai_score"] or 0
            diff = full_score - chunk_avg
            print(f"    {ITEM_KO[key]}: 전체={full_score:.2f}  청크평균={chunk_avg:.2f}  "
                  f"차이={diff:+.2f}  {'⚠ 불일치' if abs(diff) > 0.5 else '□ 일치'}")
    print()


if __name__ == "__main__":
    wav = sys.argv[1] if len(sys.argv) > 1 else \
        str(_ROOT / "data/vocal_academy/validation_t2/test_11.wav")
    sid = sys.argv[2] if len(sys.argv) > 2 else "004"
    run(wav, sid)
