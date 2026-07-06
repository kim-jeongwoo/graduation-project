"""
F4 vocal-app schema 명세용: /analyze 응답 raw JSON 추출.
B1.wav 앞 20초만 slice → synthetic LRC 2줄 → timeline 포함 응답 조립.
"""
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path("/home/dmlserver/projects/egg_prediction")
sys.path.insert(0, str(ROOT / "dml-server/model_server"))
sys.path.insert(0, str(ROOT / "dml-server/scripts/sidetrack"))
sys.path.insert(0, str(ROOT / "dml-server/ai-model"))

from analysis_pipeline import AnalysisPipeline
from services.timeline_analysis import analyze_with_timeline

WAV  = ROOT / "data/vocal_academy/control_pre_510/B1.wav"
CKPT = ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRIT = ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPS = ROOT / "data/vocal_academy/results/ai_scores.json"
OUT  = ROOT / "data/vocal_academy/results/sidetrack/sample_response_analyze.json"


def main():
    pipe = AnalysisPipeline(str(CKPT), str(CRIT), str(MAPS))

    # B1.wav 앞 20초만 slice (전체 분석 비용 최소화)
    audio, sr = sf.read(WAV, dtype="float32")
    if audio.ndim > 1: audio = audio.mean(axis=1)
    n = int(20.0 * sr)
    audio = audio[:n]
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    audio_bytes = buf.getvalue()

    # /analyze 전체 분석
    result = pipe.analyze(audio_bytes)

    # synthetic LRC 2줄 (7s × 2 = 14s, 5초~19초)
    lrc = [
        {"time_start": 5.0,  "time_end": 12.0, "text": "synthetic_line_0"},
        {"time_start": 12.0, "time_end": 19.0, "text": "synthetic_line_1"},
    ]
    ts, meta = analyze_with_timeline(audio_bytes, lrc, pipe)

    # server.py /analyze 응답과 동일 조립
    response = {
        "run_id": "sample_b1_20s",
        "status": "success",
        **result,
        "timeline_scores":   ts,
        "timeline_metadata": meta,
    }

    # user_f0 reduce — 너무 김
    if response.get("user_f0") and isinstance(response["user_f0"], dict):
        v = response["user_f0"].get("values", [])
        response["user_f0"] = {
            "frame_hz":  response["user_f0"].get("frame_hz"),
            "n_values":  len(v),
            "values_preview": v[:20],
            "_note":     "전체 values는 25Hz sparse null array (None=unvoiced)",
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(response, ensure_ascii=False, indent=2))
    print(f"[saved] {OUT}  ({OUT.stat().st_size} bytes)")
    print(f"[keys top-level] {list(response.keys())}")
    print(f"[keys result.scores_v2] {list((response.get('scores_v2') or {}).keys())}")
    print(f"[keys result.scores_meta] {list((response.get('scores_meta') or {}).keys())}")
    print(f"[keys reliability] {list((response.get('reliability') or {}).keys())}")
    print(f"[timeline_scores n] {len(ts)}")
    print(f"[timeline_scores[0] keys] {list(ts[0].keys())}")
    print(f"[timeline_scores[0].scores keys] {list(ts[0]['scores'].keys())}")


if __name__ == "__main__":
    main()
