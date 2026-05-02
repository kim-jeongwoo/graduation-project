#!/usr/bin/env python3
"""Quick smoke test for analysis_pipeline without the server overhead."""
import io, sys, os, time, json
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ai-model'))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINT  = os.path.join(PROJECT_ROOT, 'checkpoints', 'exp20_progressive', 'best_model.pt')
CRITERIA    = os.path.join(PROJECT_ROOT, 'data', 'vocal_academy', 'evaluation_criteria.json')
MAPPINGS    = os.path.join(PROJECT_ROOT, 'data', 'vocal_academy', 'results', 'ai_scores.json')
VAL_WAV     = os.path.join(PROJECT_ROOT, 'data', 'vocal_academy', 'validation', 'test_01.wav')

from analysis_pipeline import AnalysisPipeline

print("Loading pipeline...")
t0 = time.perf_counter()
pipeline = AnalysisPipeline(CHECKPOINT, CRITERIA, MAPPINGS)
print(f"  Load time: {time.perf_counter()-t0:.1f}s")

# Use 15 seconds of test_01.wav
audio, sr = sf.read(VAL_WAV, dtype='float32')
audio_15s = audio[:15*sr]
buf = io.BytesIO()
sf.write(buf, audio_15s, sr, format='WAV')
wav_bytes = buf.getvalue()
print(f"Input: 15s slice = {len(wav_bytes):,} bytes")

print("Running analysis...")
t1 = time.perf_counter()
result = pipeline.analyze(wav_bytes)
elapsed = time.perf_counter() - t1

print(f"\n✅ Analysis complete: {elapsed:.1f}s")
print(f"  pipeline_ms reported: {result['processing_time_ms']:.0f}")
print(f"  voiced: {result['audio_info']['voiced_ratio']:.1%} ({result['audio_info']['voiced_duration_s']:.1f}s)")
print(f"  f0_mean: {result['audio_info']['f0_mean']}")
print()
print("Scores:")
for k, v in result['scores'].items():
    sc = v.get('ai_score'); conf = v.get('confidence')
    sc_str = f'{sc:.2f}' if sc is not None else 'N/A '
    zone = v.get('zone') or 'N/A'
    print(f"  {k:32s}: {sc_str} | {zone:12s} | [{conf}]")

print()
print("Feedback sample (4_breathiness):")
fb = result['feedback'].get('4_breathiness', {})
print(f"  score: {fb.get('ai_score')}")
print(f"  description: {fb.get('score_description')}")
print(f"  feedback: {fb.get('feedback_text')}")
print(f"  indicator: {fb.get('ai_indicator')}")
print()
resp_size = len(json.dumps(result).encode())
print(f"Response JSON size: {resp_size:,} bytes")
print()

# Validation
assert 'audio_info' in result
assert 'scores' in result
assert 'feedback' in result
assert 'reliability' in result
assert 'high_reliability' in result['reliability']
for key in ['3_vocal_fold_contact', '4_breathiness']:
    assert result['scores'][key].get('ai_score') is not None, f"Missing score for {key}"
for key in ['7_larynx_tongue_root', '8_tongue_tension']:
    assert result['scores'][key].get('ai_score') is None, f"Should be null for {key}"
print("✅ All assertions passed")
