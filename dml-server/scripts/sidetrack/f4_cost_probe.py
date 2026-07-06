"""
F4 cost probe — 대응 1 vs 대응 2 실측.

P-1: parselmouth Sound.extract_part 검증
P-2: 곡 전체 indicator vs chunk slice indicator 비용 비교
P-3: chunk indicator 정확도 비교 (sample chunk)
"""
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa
import parselmouth

ROOT = Path("/home/dmlserver/projects/egg_prediction")
sys.path.insert(0, str(ROOT / "dml-server/scripts/sidetrack"))
sys.path.insert(0, str(ROOT / "dml-server/model_server"))
sys.path.insert(0, str(ROOT / "dml-server/ai-model"))

import indicators_v2 as iv

WAV = ROOT / "data/vocal_academy/control_pre_510/B1.wav"

def load_16k(path):
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    return audio, 16000


def main():
    audio, sr = load_16k(WAV)
    dur = len(audio) / sr
    print(f"[wav] {WAV.name}  duration={dur:.1f}s  samples={len(audio)}")

    # ── P-1: parselmouth Sound.extract_part 검증 ──
    print("\n[P-1] parselmouth Sound.extract_part")
    snd = parselmouth.Sound(audio.astype(np.float32), sampling_frequency=16000)
    t0 = time.perf_counter()
    sub = snd.extract_part(from_time=5.0, to_time=15.0, preserve_times=False)
    print(f"  extract_part OK  sub_dur={sub.get_total_duration():.3f}s  cost={1000*(time.perf_counter()-t0):.1f}ms")

    # ── P-2: 곡 전체 vs chunk slice indicator 비용 ──
    print("\n[P-2] cost full vs chunk")

    # 1) 곡 전체 compute_all
    t0 = time.perf_counter()
    full = iv.compute_all(audio, sr)
    full_cost = time.perf_counter() - t0
    n_valid = sum(1 for v in full.values() if v is not None)
    print(f"  full compute_all: {full_cost:.2f}s  ({n_valid}/{len(full)} non-None)")

    # 2) chunk slice (10s × N) — 대응 1
    chunk_len_s = 8.0
    starts = list(np.arange(0, dur - chunk_len_s, chunk_len_s))
    if len(starts) > 6: starts = starts[:6]   # 6 chunk만 측정
    print(f"  chunk slice (n={len(starts)}, chunk={chunk_len_s}s):")
    chunk_costs = []
    chunk_vals = []
    for s in starts:
        s_smp = int(s * sr); e_smp = int((s + chunk_len_s) * sr)
        chunk_audio = audio[s_smp:e_smp]
        t0 = time.perf_counter()
        ch = iv.compute_all(chunk_audio, sr)
        c = time.perf_counter() - t0
        chunk_costs.append(c)
        chunk_vals.append(ch)
        nv = sum(1 for v in ch.values() if v is not None)
        print(f"    [{s:.1f}~{s+chunk_len_s:.1f}s]  {c:.2f}s  non-None={nv}/{len(ch)}")
    total_chunk = sum(chunk_costs)
    print(f"  chunk total: {total_chunk:.2f}s ({total_chunk/len(starts):.2f}s avg)")
    print(f"  대응 1 추정 (N=20 chunk): {20 * np.mean(chunk_costs):.1f}s")

    # ── P-3: chunk indicator 값 비교 (전체 vs chunk slice) ──
    print("\n[P-3] indicator value compare (full vs chunk slice, sample chunk 1)")
    sample = chunk_vals[0]
    print(f"  {'indicator':<32}  {'full':>10}  {'chunk0':>10}  {'rel_diff':>10}")
    for key in ["hnr","jitter_local","shimmer_local","spectral_entropy",
                "F2_stability","spectral_centroid_variability","f0_std",
                "h1_h2","a1_p0","singers_formant_ratio","band_ratio_low_mid"]:
        fv = full.get(key); cv = sample.get(key)
        if fv is None or cv is None:
            print(f"  {key:<32}  {str(fv):>10}  {str(cv):>10}  {'-':>10}")
            continue
        rd = (cv - fv) / (abs(fv) + 1e-10) * 100
        print(f"  {key:<32}  {fv:>10.4f}  {cv:>10.4f}  {rd:>9.1f}%")


if __name__ == "__main__":
    main()
