#!/usr/bin/env python3
"""
spectral_analysis.py — 스펙트럼 기반 발성 지표 추출
====================================================
phone.wav (없으면 oral.wav)에서 프레임 단위로:
  1. Singer's Formant (2~4kHz 에너지 비율)
  2. Spectral Tilt (스펙트럼 기울기)
  3. H1-H2 (1st harmonic - 2nd harmonic amplitude)
  4. HNR (Harmonics-to-Noise Ratio, parselmouth)

결과: data/vocal_academy/results/spectral_analysis.json
"""
import os
import sys
import json
import glob
import re

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
MASK_DIR = os.path.join(RESULTS_DIR, "vad_masks")

TARGET_SR = 16000
N_FFT = 1024
HOP = 256
F0_FLOOR = 75
F0_CEIL = 600

# Pairs to exclude: voiced data insufficient for reliable analysis
EXCLUDE_PAIRS = {(6, 8)}  # Singer 6 Song 8: phone=0%, oral/nasal=18%


def load_audio(wav_path):
    """Load wav → 16kHz mono float32."""
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    return audio


def extract_f0(wav_path):
    """Extract F0 using parselmouth."""
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_frames = call(pitch, "Get number of frames")
    f0_vals, f0_times = [], []
    for i in range(1, n_frames + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals.append(f if f == f else 0.0)
        f0_times.append(t)
    return np.array(f0_vals), np.array(f0_times)


def split_registers(f0_vals):
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 0, "mid_max": 0}
    return {
        "low_max": float(np.percentile(voiced, 33)),
        "mid_max": float(np.percentile(voiced, 66)),
        "f0_min": float(voiced.min()),
        "f0_max": float(voiced.max()),
        "f0_mean": float(voiced.mean()),
    }


# ── Spectral features ────────────────────────────────────────────
def compute_singers_formant_ratio(S_mag, sr=TARGET_SR):
    """
    Singer's formant region (2~4kHz) energy ratio.
    Higher ratio → more forward resonance / projection.
    """
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    total_energy = (S_mag ** 2).sum(axis=0)
    mask_2k_4k = (freqs >= 2000) & (freqs <= 4000)
    sf_energy = (S_mag[mask_2k_4k] ** 2).sum(axis=0)
    ratio = sf_energy / (total_energy + 1e-10)
    return ratio  # [n_frames]


def compute_spectral_tilt(S_mag, sr=TARGET_SR):
    """
    Spectral tilt: slope of log-magnitude spectrum.
    Negative = energy concentrated in low frequencies (breathy/soft).
    Flat/positive = more high-frequency energy (pressed).
    """
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    log_mag = np.log10(S_mag + 1e-10)
    n_frames = S_mag.shape[1]
    tilts = np.zeros(n_frames, dtype=np.float32)

    # Use freq > 0 to avoid log(0)
    valid = freqs > 0
    log_freqs = np.log10(freqs[valid])

    for i in range(n_frames):
        if S_mag[:, i].max() < 1e-8:
            continue
        # Linear regression of log-mag on log-freq
        y = log_mag[valid, i]
        coeffs = np.polyfit(log_freqs, y, 1)
        tilts[i] = coeffs[0]  # slope

    return tilts


def compute_h1_h2(audio, f0_vals, f0_times, sr=TARGET_SR):
    """
    H1-H2: amplitude difference between 1st and 2nd harmonic.
    H1-H2 > 0 → breathy voice
    H1-H2 < 0 → pressed voice
    Uses frame-by-frame analysis aligned with F0.
    """
    frame_len = N_FFT
    hop = HOP
    n_frames = max(0, (len(audio) - frame_len) // hop + 1)
    h1_h2 = np.zeros(n_frames, dtype=np.float32)
    frame_times = np.array([(i * hop + frame_len / 2) / sr for i in range(n_frames)])

    window = np.hanning(frame_len)
    freqs = np.fft.rfftfreq(frame_len, 1.0 / sr)

    for i in range(n_frames):
        start = i * hop
        frame = audio[start:start + frame_len] * window

        # Find nearest F0
        t = frame_times[i]
        idx = np.argmin(np.abs(f0_times - t))
        f0 = f0_vals[idx]
        if f0 <= 0:
            h1_h2[i] = np.nan
            continue

        spectrum = np.abs(np.fft.rfft(frame))
        mag_db = 20 * np.log10(spectrum + 1e-10)

        # Find peaks near H1 (f0) and H2 (2*f0)
        h1_idx = np.argmin(np.abs(freqs - f0))
        h2_idx = np.argmin(np.abs(freqs - 2 * f0))

        # Search within ±3 bins for peak
        search = 3
        h1_region = mag_db[max(0, h1_idx - search):h1_idx + search + 1]
        h2_region = mag_db[max(0, h2_idx - search):h2_idx + search + 1]

        h1_h2[i] = h1_region.max() - h2_region.max() if len(h1_region) > 0 and len(h2_region) > 0 else np.nan

    return h1_h2, frame_times


def extract_hnr(wav_path):
    """HNR using parselmouth (Praat)."""
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    harmonicity = call(snd, "To Harmonicity (cc)", 0.01, F0_FLOOR, 0.1, 1.0)
    n_frames = call(harmonicity, "Get number of frames")
    hnr_vals, hnr_times = [], []
    for i in range(1, n_frames + 1):
        t = call(harmonicity, "Get time from frame number", i)
        v = call(harmonicity, "Get value in frame", i)
        hnr_vals.append(v if v == v else np.nan)
        hnr_times.append(t)
    return np.array(hnr_vals), np.array(hnr_times)


def load_vad_mask(singer_id, song_id, mic_type):
    """Load intersect mask if available, else individual mask."""
    intersect_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_intersect_vad.npy")
    if os.path.exists(intersect_path):
        return np.load(intersect_path)
    mask_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_{mic_type}_vad.npy")
    if os.path.exists(mask_path):
        return np.load(mask_path)
    return None


def stats_by_register(values, frame_times, f0_vals, f0_times, boundaries, vad_mask=None):
    """Compute stats per register, ignoring NaN. Uses VAD mask if provided."""
    results = {"low": [], "mid": [], "high": [], "all_voiced": []}
    for i, t in enumerate(frame_times):
        if np.isnan(values[i]):
            continue
        # Apply VAD mask
        if vad_mask is not None and i < len(vad_mask) and not vad_mask[i]:
            continue
        idx = np.argmin(np.abs(f0_times - t))
        f0 = f0_vals[idx]
        if f0 <= 0:
            continue
        results["all_voiced"].append(values[i])
        if f0 <= boundaries.get("low_max", 0):
            results["low"].append(values[i])
        elif f0 <= boundaries.get("mid_max", 0):
            results["mid"].append(values[i])
        else:
            results["high"].append(values[i])

    stats = {}
    for reg in ["low", "mid", "high", "all_voiced"]:
        arr = np.array(results[reg]) if results[reg] else np.array([])
        stats[reg] = {
            "n_frames": len(arr),
            "mean": float(arr.mean()) if len(arr) > 0 else None,
            "std": float(arr.std()) if len(arr) > 0 else None,
            "median": float(np.median(arr)) if len(arr) > 0 else None,
        }
    return stats


# ── Main ──────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # For each singer: prefer phone.wav, fallback to oral.wav
    singer_dirs = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*")))
    all_results = []

    for sdir in singer_dirs:
        singer_name = os.path.basename(sdir)
        wavs = sorted(glob.glob(os.path.join(sdir, "*.wav")))

        # Group by song_id
        songs = {}
        for w in wavs:
            m = re.match(r'(\d+)-(\d+)', os.path.basename(w))
            if m:
                song_key = f"{m.group(1)}-{m.group(2)}"
                if song_key not in songs:
                    songs[song_key] = {}
                if "_phone.wav" in w:
                    songs[song_key]["phone"] = w
                elif "_oral.wav" in w:
                    songs[song_key]["oral"] = w

        for song_key, paths in sorted(songs.items()):
            wav_path = paths.get("phone") or paths.get("oral")
            if not wav_path:
                continue

            source = "phone" if "phone" in paths else "oral"
            fname = os.path.basename(wav_path)
            m = re.match(r'(\d+)-(\d+)', fname)
            singer_id = int(m.group(1)) if m else 0
            song_id = int(m.group(2)) if m else 0

            if (singer_id, song_id) in EXCLUDE_PAIRS:
                print(f"  [SKIP] Singer {singer_id} Song {song_id}: in EXCLUDE_PAIRS")
                continue

            print(f"\n{'='*50}")
            print(f"Processing: {singer_name}/{fname} (source={source})")

            # Load VAD mask
            vad_mask = load_vad_mask(singer_id, song_id, source)
            if vad_mask is not None:
                print(f"  VAD: {vad_mask.sum()}/{len(vad_mask)} voiced ({vad_mask.sum()/len(vad_mask):.1%})")
            else:
                print(f"  VAD: mask not found, using all frames")

            audio = load_audio(wav_path)
            print(f"  Duration: {len(audio)/TARGET_SR:.1f}s")

            # STFT
            S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP)
            S_mag = np.abs(S)
            stft_times = librosa.frames_to_time(
                np.arange(S_mag.shape[1]), sr=TARGET_SR, hop_length=HOP
            )

            # F0
            f0_vals, f0_times = extract_f0(wav_path)
            boundaries = split_registers(f0_vals)

            # 1. Singer's formant ratio
            sf_ratio = compute_singers_formant_ratio(S_mag)
            sf_stats = stats_by_register(sf_ratio, stft_times, f0_vals, f0_times, boundaries, vad_mask=vad_mask)
            print(f"  Singer's formant (voiced): mean={sf_stats.get('all_voiced',{}).get('mean','N/A')}")

            # 2. Spectral tilt
            tilt = compute_spectral_tilt(S_mag)
            tilt_stats = stats_by_register(tilt, stft_times, f0_vals, f0_times, boundaries, vad_mask=vad_mask)
            print(f"  Spectral tilt: global mean={np.nanmean(tilt):.3f}")

            # 3. H1-H2
            h1h2, h1h2_times = compute_h1_h2(audio, f0_vals, f0_times)
            h1h2_stats = stats_by_register(h1h2, h1h2_times, f0_vals, f0_times, boundaries, vad_mask=vad_mask)
            valid_h1h2 = h1h2[~np.isnan(h1h2)]
            print(f"  H1-H2 (voiced): mean={h1h2_stats.get('all_voiced',{}).get('mean','N/A')}")

            # 4. HNR
            hnr_vals, hnr_times = extract_hnr(wav_path)
            hnr_stats = stats_by_register(hnr_vals, hnr_times, f0_vals, f0_times, boundaries, vad_mask=vad_mask)
            print(f"  HNR (voiced): mean={hnr_stats.get('all_voiced',{}).get('mean','N/A')}")

            result = {
                "file": fname,
                "source": source,
                "singer_id": singer_id,
                "song_id": song_id,
                "duration_s": round(len(audio) / TARGET_SR, 2),
                "vad_applied": vad_mask is not None,
                "f0_stats": boundaries,
                "singers_formant_ratio": sf_stats,
                "spectral_tilt": tilt_stats,
                "h1_h2": h1h2_stats,
                "hnr": hnr_stats,
            }
            all_results.append(result)

    output = {
        "description": "Spectral analysis for vocal academy recordings (VAD filtered, voiced frames only)",
        "features": [
            "singers_formant_ratio (2-4kHz energy ratio)",
            "spectral_tilt (log-mag slope)",
            "h1_h2 (1st-2nd harmonic dB difference)",
            "hnr (harmonics-to-noise ratio dB)",
        ],
        "n_files": len(all_results),
        "results": all_results,
    }
    json_path = os.path.join(RESULTS_DIR, "spectral_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")
    print(f"   {len(all_results)} files analyzed")


if __name__ == "__main__":
    main()
