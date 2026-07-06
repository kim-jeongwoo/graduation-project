"""
test_silent_guard.py — K-3-1: 무음 가드 6종 합성 검증
Usage: conda activate EGGDML && python dml-server/scripts/test_silent_guard.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_ROOT / "dml-server" / "model_server"))

from analysis_pipeline import AnalysisPipeline, SilentInputError

CHECKPOINT = _ROOT / "checkpoints/exp20_progressive/best_model.pt"
CRITERIA   = _ROOT / "data/vocal_academy/evaluation_criteria.json"
MAPPINGS   = _ROOT / "data/vocal_academy/results/ai_scores.json"

CASES = [
    ("/tmp/test_silent.wav",       "A",    "no_voice"),
    ("/tmp/test_ambient.wav",      "A",    "no_voice"),
    ("/tmp/test_louder_noise.wav", "A",    "no_voice"),
    ("/tmp/test_hum.wav",          "B",    "no_voice"),
    (str(_ROOT / "data/vocal_academy/validation_t2/test_11.wav"), "none", "completed"),
    (str(_ROOT / "data/vocal_academy/singer_09/9-10_phone.wav"),  "none", "completed"),
]

pipeline = AnalysisPipeline(str(CHECKPOINT), str(CRITERIA), str(MAPPINGS))

print(f"\n{'케이스':<40} {'기대':^12} {'결과':^12} {'가드':^8} {'pass?'}")
print("-" * 80)
all_pass = True
for wav_path, expected_guard, expected_status in CASES:
    label = Path(wav_path).name[:38]
    with open(wav_path, "rb") as f:
        data = f.read()
    try:
        result = pipeline.analyze(data)
        actual_status = "completed"
        actual_guard  = "none"
        reason_short  = ""
    except SilentInputError as e:
        actual_status = "no_voice"
        actual_guard  = e.guard
        reason_short  = e.reason[:30]

    ok = (actual_status == expected_status) and \
         (expected_guard == "none" or actual_guard == expected_guard)
    all_pass = all_pass and ok
    mark = "✓" if ok else "✗"
    print(f"{label:<40} {expected_status:^12} {actual_status:^12} {actual_guard:^8} {mark}  {reason_short}")

print("-" * 80)
print(f"\n{'전체 PASS' if all_pass else '일부 FAIL'}\n")
sys.exit(0 if all_pass else 1)
