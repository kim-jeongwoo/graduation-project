#!/usr/bin/env python3
"""
extra_metrics.py — 추가 음향 지표 추출
========================================
G-2 항목:
  1. CPP (Cepstral Peak Prominence) — 기식성(breathiness) 지표 → ④호흡식별 후보
  2. Spectral Centroid — 전방 공명 지표 → ⑤전방공명 후보
  3. A1-P0 (비강성 정량화) — ①비강사용 후보

모든 지표:
- oral.wav 기준 (phone 없는 가수도 분석 가능)
- intersect VAD 마스크 적용 (voiced 프레임에서만 계산)
- (6, 8) 제외

결과: results/extra_metrics.json
"""
import os
import sys
import glob
import re
import json

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR    = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR  = os.path.join(VOCAL_DIR, "results")
MASK_DIR     = os.path.join(RESULTS_DIR, "vad_masks")

TARGET_SR = 16000
N_FFT     = 1024
HOP       = 256
F0_FLOOR  = 75
F0_CEIL   = 600

EXCLUDE_PAIRS = {(6, 8)}


def load_audio(wav_path):
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    return audio


def load_vad_mask(singer_id, song_id):
    """Load intersect mask, fallback to oral mask."""
    p = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_intersect_vad.npy")
    if os.path.exists(p):
        return np.load(p)
    p = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_oral_vad.npy")
    if os.path.exists(p):
        return np.load(p)
    return None


def extract_f0(wav_path):
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n = call(pitch, "Get number of frames")
    f0_vals, f0_times = [], []
    for i in range(1, n + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals.append(f if f == f else 0.0)
        f0_times.append(t)
    return np.array(f0_vals), np.array(f0_times)


# ── CPP (Cepstral Peak Prominence) ───────────────────────────────
def compute_cpp(audio, sr=TARGET_SR, n_fft=N_FFT, hop=HOP, vad_mask=None):
    """
    CPP: prominence of the first (F0) peak in the cepstrum.
    Higher CPP → more periodic / less breathy voice.
    """
    n_frames = max(0, (len(audio) - n_fft) // hop + 1)
    cpp_vals = []
    frame_times = []
    window = np.hanning(n_fft)

    for i in range(n_frames):
        if vad_mask is not None and i < len(vad_mask) and not vad_mask[i]:
            continue
        start = i * hop
        frame = audio[start:start + n_fft] * window
        if np.abs(frame).max() < 1e-8:
            continue
        # Log magnitude spectrum
        spec = np.abs(np.fft.rfft(frame))
        log_spec = np.log(spec + 1e-10)
        # Cepstrum (real cepstrum via IFFT)
        cepstrum = np.fft.irfft(log_spec)
        # Quefrency range for F0 (corresponding to 75~600 Hz)
        q_min = int(sr / F0_CEIL)   # ~27
        q_max = int(sr / F0_FLOOR)  # ~213
        q_max = min(q_max, len(cepstrum) // 2)
        if q_min >= q_max:
            continue
        segment = cepstrum[q_min:q_max]
        peak_idx = np.argmax(segment)
        peak_val = segment[peak_idx]
        # Regression line baseline (linear trend of log cepstrum in this range)
        x = np.arange(len(segment), dtype=float)
        if len(x) > 2:
            coeff = np.polyfit(x, segment, 1)
            baseline = np.polyval(coeff, x[peak_idx])
        else:
            baseline = np.mean(segment)
        cpp = peak_val - baseline
        cpp_vals.append(cpp)
        frame_times.append((start + n_fft / 2) / sr)

    arr = np.array(cpp_vals) if cpp_vals else np.array([])
    return {
        "mean": float(arr.mean()) if len(arr) > 0 else None,
        "std": float(arr.std()) if len(arr) > 0 else None,
        "median": float(np.median(arr)) if len(arr) > 0 else None,
        "n_frames": len(arr),
    }


# ── Spectral Centroid ─────────────────────────────────────────────
def compute_spectral_centroid(audio, sr=TARGET_SR, n_fft=N_FFT, hop=HOP, vad_mask=None):
    """
    Spectral centroid frequency (Hz). Higher = more forward/bright resonance.
    """
    S_mag = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop))
    centroid = librosa.feature.spectral_centroid(S=S_mag, sr=sr, n_fft=n_fft)[0]
    n_frames = len(centroid)

    voiced_vals = []
    for i in range(n_frames):
        if vad_mask is not None and i < len(vad_mask) and not vad_mask[i]:
            continue
        voiced_vals.append(centroid[i])

    arr = np.array(voiced_vals) if voiced_vals else np.array([])
    return {
        "mean": float(arr.mean()) if len(arr) > 0 else None,
        "std": float(arr.std()) if len(arr) > 0 else None,
        "median": float(np.median(arr)) if len(arr) > 0 else None,
        "n_frames": len(arr),
    }


# ── A1-P0 ─────────────────────────────────────────────────────────
def compute_a1_p0(wav_path, vad_mask=None):
    """
    A1-P0: amplitude of F1 minus amplitude near 250 Hz (nasal pole).
    More negative → stronger nasality.
    
    Approximate: extract F1 with parselmouth, compare peak dB at F1 vs ~250Hz.
    """
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)

    # Formant (F1)
    formant = call(snd, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
    n_frames = call(formant, "Get number of frames")

    freqs = np.fft.rfftfreq(N_FFT, 1.0 / TARGET_SR)
    audio = snd.values[0]
    window = np.hanning(N_FFT)
    hop = HOP

    a1_p0_vals = []
    for i in range(1, n_frames + 1):
        frame_idx = int(i - 1)  # approx alignment
        if vad_mask is not None and frame_idx < len(vad_mask) and not vad_mask[frame_idx]:
            continue

        f1 = call(formant, "Get value at time", 1, call(formant, "Get time from frame number", i),
                  "Hertz", "Linear")
        if not (f1 == f1) or f1 <= 0:  # NaN or invalid
            continue

        # Corresponding audio frame
        t = call(formant, "Get time from frame number", i)
        start_sample = max(0, int(t * TARGET_SR) - N_FFT // 2)
        if start_sample + N_FFT > len(audio):
            continue
        frame = audio[start_sample:start_sample + N_FFT] * window
        spec_db = 20 * np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)

        # A1: peak near F1 (±100 Hz)
        f1_idx = np.argmin(np.abs(freqs - f1))
        f1_range = max(1, int(100 / (TARGET_SR / N_FFT)))
        a1 = spec_db[max(0, f1_idx - f1_range):f1_idx + f1_range + 1].max()

        # P0: peak near 250 Hz nasal pole
        p0_freq = 250
        p0_idx = np.argmin(np.abs(freqs - p0_freq))
        p0_range = max(1, int(50 / (TARGET_SR / N_FFT)))
        p0 = spec_db[max(0, p0_idx - p0_range):p0_idx + p0_range + 1].max()

        a1_p0_vals.append(a1 - p0)

    arr = np.array(a1_p0_vals) if a1_p0_vals else np.array([])
    return {
        "mean": float(arr.mean()) if len(arr) > 0 else None,
        "std": float(arr.std()) if len(arr) > 0 else None,
        "median": float(np.median(arr)) if len(arr) > 0 else None,
        "n_frames": len(arr),
    }


# ── Main ──────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    oral_files = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*_oral.wav")))
    print(f"Found {len(oral_files)} oral files")

    # Deduplicate by (singer, song)
    seen = {}
    for path in oral_files:
        fname = os.path.basename(path)
        m = re.match(r'(\d+)-(\d+)', fname)
        if not m:
            continue
        singer_id, song_id = int(m.group(1)), int(m.group(2))
        key = (singer_id, song_id)
        if key not in seen:
            seen[key] = path

    all_results = []
    for (singer_id, song_id), wav_path in sorted(seen.items()):
        if (singer_id, song_id) in EXCLUDE_PAIRS:
            print(f"  [SKIP] Singer {singer_id} Song {song_id}: EXCLUDE_PAIRS")
            continue

        fname = os.path.basename(wav_path)
        print(f"\n{'='*50}")
        print(f"Processing: singer_{singer_id:02d}/{fname}")

        vad_mask = load_vad_mask(singer_id, song_id)
        if vad_mask is not None:
            print(f"  VAD: {vad_mask.sum()}/{len(vad_mask)} voiced ({vad_mask.sum()/len(vad_mask):.1%})")

        audio = load_audio(wav_path)

        # CPP
        cpp_stats = compute_cpp(audio, vad_mask=vad_mask)
        print(f"  CPP: mean={cpp_stats['mean']:.3f}" if cpp_stats['mean'] is not None else "  CPP: N/A")

        # Spectral Centroid
        sc_stats = compute_spectral_centroid(audio, vad_mask=vad_mask)
        print(f"  Spectral Centroid: mean={sc_stats['mean']:.1f} Hz" if sc_stats['mean'] is not None else "  Centroid: N/A")

        # A1-P0
        a1p0_stats = compute_a1_p0(wav_path, vad_mask=vad_mask)
        print(f"  A1-P0: mean={a1p0_stats['mean']:.2f} dB" if a1p0_stats['mean'] is not None else "  A1-P0: N/A")

        all_results.append({
            "singer_id": singer_id,
            "song_id": song_id,
            "file": fname,
            "cpp": cpp_stats,
            "spectral_centroid": sc_stats,
            "a1_p0": a1p0_stats,
        })

    output = {
        "description": "Extra acoustic metrics: CPP, spectral centroid, A1-P0 (oral.wav, voiced frames only)",
        "n_files": len(all_results),
        "results": all_results,
    }
    json_path = os.path.join(RESULTS_DIR, "extra_metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")
    print(f"   {len(all_results)} files analyzed")


if __name__ == "__main__":
    main()
