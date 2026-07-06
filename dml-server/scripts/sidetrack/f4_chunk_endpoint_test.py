"""
F4-3 단위 테스트: /analyze-chunk 응답 schema 직접 호출.
"""
import io, os, sys
from pathlib import Path
import soundfile as sf

ROOT = Path("/home/dmlserver/projects/egg_prediction")
sys.path.insert(0, str(ROOT / "dml-server/model_server"))
sys.path.insert(0, str(ROOT / "dml-server/scripts/sidetrack"))
sys.path.insert(0, str(ROOT / "dml-server/ai-model"))

from analysis_pipeline import AnalysisPipeline, SilentInputError
from services.chunk_analysis import prepare_chunk

WAV  = ROOT / "data/vocal_academy/control_pre_510/B1.wav"
CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRIT = ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPS = ROOT / "data/vocal_academy/results/ai_scores.json"

V2_KEYS  = ("3_vocal_fold_contact","4_breathiness","6_soft_palate","8_tongue_tension")
V2_TIERS = {"3_vocal_fold_contact":"high","4_breathiness":"high_star",
            "6_soft_palate":"high_star","8_tongue_tension":"high_star"}

def _zone(ai):
    if ai is None: return None
    s = round(ai)
    if s <= 1: return "insufficient"
    if s <= 3: return "appropriate"
    return "excessive"


def simulate_endpoint(pipeline, audio_bytes, start, end):
    """server.py /analyze-chunk 응답 조립 동일 로직."""
    wav_bytes, duration, min_voiced_s, confidence = prepare_chunk(
        audio_bytes, start_sec=start, end_sec=end)
    result = pipeline.analyze(wav_bytes, min_voiced_s=min_voiced_s)

    # legacy v1 2항목
    scores_out = {}
    for key in ("3_vocal_fold_contact","4_breathiness"):
        s = (result.get("scores") or {}).get(key) or {}
        scores_out[key] = {
            "ai_score":      s.get("ai_score"),
            "rounded_score": s.get("rounded_score"),
            "zone":          s.get("zone"),
            "confidence":    confidence if s.get("ai_score") is not None else "unavailable",
        }
    # v2 4항목
    v2_raw  = result.get("scores_v2")  or {}
    v2_meta = result.get("scores_meta") or {}
    scores_v2_out = {}
    for key in V2_KEYS:
        ai = v2_raw.get(key); m = v2_meta.get(key) or {}
        scores_v2_out[key] = {
            "ai_score": ai, "rounded_score": m.get("rounded_score"),
            "zone": _zone(ai),
            "confidence": confidence if ai is not None else "unavailable",
            "tier": m.get("tier") or V2_TIERS[key],
        }
    low_conf = ["4_breathiness","6_soft_palate","8_tongue_tension"] if duration < 5.0 else []
    return {
        "status":"success", "duration_sec":round(duration,2),
        "chunk_duration_s": round(duration,3),
        "scores": scores_out, "scores_v2": scores_v2_out,
        "scores_meta": v2_meta, "low_confidence_items": low_conf,
        "score_mapper_version": result.get("score_mapper_version"),
    }


def main():
    pipeline = AnalysisPipeline(str(CKPT), str(CRIT), str(MAPS))
    audio_bytes = open(WAV,"rb").read()

    for (start, end, label) in [(10.0,20.0,"10s chunk"), (10.0,13.5,"3.5s chunk")]:
        print(f"\n=== {label} ({start}~{end}) ===")
        resp = simulate_endpoint(pipeline, audio_bytes, start, end)
        print(f"  duration={resp['chunk_duration_s']}s")
        print(f"  score_mapper_version={resp['score_mapper_version']}")
        print(f"  low_confidence_items={resp['low_confidence_items']}")
        print(f"  legacy scores (v1):")
        for k,v in resp['scores'].items():
            print(f"    {k}: ai={v['ai_score']} round={v['rounded_score']} "
                  f"zone={v['zone']} conf={v['confidence']}")
        print(f"  scores_v2 (4 항목):")
        for k,v in resp['scores_v2'].items():
            print(f"    {k}: ai={v['ai_score']} round={v['rounded_score']} "
                  f"zone={v['zone']} conf={v['confidence']} tier={v['tier']}")

if __name__ == "__main__":
    main()
