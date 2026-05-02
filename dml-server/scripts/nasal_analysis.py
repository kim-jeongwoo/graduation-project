#!/usr/bin/env python3
"""
nasal_analysis.py — 구강/비강 비율 분석
========================================
각 가수의 oral.wav + nasal.wav 쌍에 대해:
  1. RMS 에너지 프레임 단위 계산
  2. nasal_ratio = rms_nasal / (rms_oral + rms_nasal + eps)
  3. F0 기반 음역대 분리 → 음역대별 nasal_ratio 통계

결과: data/vocal_academy/results/nasal_analysis.json
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
HOP = 256       # ~16ms
FRAME_LEN = 512  # ~32ms
F0_FLOOR = 75
F0_CEIL = 600
EPS = 1e-8

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


def compute_rms_frames(audio, frame_len=FRAME_LEN, hop=HOP):
    """Frame-level RMS energy."""
    n_frames = max(0, (len(audio) - frame_len) // hop + 1)
    rms = np.zeros(n_frames, dtype=np.float32)
    times = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        start = i * hop
        frame = audio[start:start + frame_len]
        rms[i] = np.sqrt(np.mean(frame ** 2))
        times[i] = (start + frame_len / 2) / TARGET_SR
    return rms, times


def extract_f0(wav_path):
    """Extract F0 using parselmouth."""
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_frames = call(pitch, "Get number of frames")

    f0_vals = []
    f0_times = []
    for i in range(1, n_frames + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals.append(f if f == f else 0.0)
        f0_times.append(t)
    return np.array(f0_vals), np.array(f0_times)


def split_registers(f0_vals):
    """Split voiced F0 into 저/중/고 using 33/66 percentile."""
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 0, "mid_max": 0}
    p33 = np.percentile(voiced, 33)
    p66 = np.percentile(voiced, 66)
    return {
        "low_max": float(p33),
        "mid_max": float(p66),
        "f0_min": float(voiced.min()),
        "f0_max": float(voiced.max()),
        "f0_mean": float(voiced.mean()),
    }


def load_vad_mask(singer_id, song_id, mic_type):
    """Load intersect mask if available, else individual mask."""
    intersect_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_intersect_vad.npy")
    if os.path.exists(intersect_path):
        return np.load(intersect_path)
    mask_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_{mic_type}_vad.npy")
    if os.path.exists(mask_path):
        return np.load(mask_path)
    return None


def nasal_ratio_by_register(rms_oral, rms_nasal, rms_times,
                            f0_vals, f0_times, boundaries, vad_mask=None):
    """Compute nasal ratio per register. Uses VAD mask if provided."""
    nasal_ratio = rms_nasal / (rms_oral + rms_nasal + EPS)

    results = {"low": [], "mid": [], "high": [], "all_voiced": []}
    for i, t in enumerate(rms_times):
        # Apply VAD mask
        if vad_mask is not None and i < len(vad_mask) and not vad_mask[i]:
            continue
        idx = np.argmin(np.abs(f0_times - t))
        f0 = f0_vals[idx]
        if f0 <= 0:
            continue

        r = nasal_ratio[i]
        results["all_voiced"].append(r)

        if f0 <= boundaries.get("low_max", 0):
            results["low"].append(r)
        elif f0 <= boundaries.get("mid_max", 0):
            results["mid"].append(r)
        else:
            results["high"].append(r)

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


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Find all oral/nasal pairs
    oral_files = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*_oral.wav")))
    print(f"Found {len(oral_files)} oral recordings")

    all_results = []

    for oral_path in oral_files:
        nasal_path = oral_path.replace("_oral.wav", "_nasal.wav")
        if not os.path.exists(nasal_path):
            print(f"⚠️ No nasal pair for {oral_path}")
            continue

        fname = os.path.basename(oral_path)
        singer_dir = os.path.basename(os.path.dirname(oral_path))
        m = re.match(r'(\d+)-(\d+)', fname)
        singer_id = int(m.group(1)) if m else 0
        song_id = int(m.group(2)) if m else 0

        if (singer_id, song_id) in EXCLUDE_PAIRS:
            print(f"  [SKIP] Singer {singer_id} Song {song_id}: in EXCLUDE_PAIRS")
            continue

        print(f"\n{'='*50}")
        print(f"Processing: {singer_dir}/{fname.replace('_oral','_[oral+nasal]')} "
              f"(singer={singer_id}, song={song_id})")

        # Load and align
        audio_oral = load_audio(oral_path)
        audio_nasal = load_audio(nasal_path)

        # Ensure same length
        min_len = min(len(audio_oral), len(audio_nasal))
        audio_oral = audio_oral[:min_len]
        audio_nasal = audio_nasal[:min_len]
        print(f"  Duration: {min_len/TARGET_SR:.1f}s ({min_len} samples)")

        # Load VAD mask (use oral mask as reference)
        vad_mask = load_vad_mask(singer_id, song_id, "oral")
        if vad_mask is not None:
            print(f"  VAD: {vad_mask.sum()}/{len(vad_mask)} voiced ({vad_mask.sum()/len(vad_mask):.1%})")
        else:
            print(f"  VAD: mask not found, using all frames")

        # RMS
        rms_oral, rms_times = compute_rms_frames(audio_oral)
        rms_nasal, _ = compute_rms_frames(audio_nasal)

        # Global nasal ratio (VAD filtered)
        global_ratio = rms_nasal / (rms_oral + rms_nasal + EPS)
        if vad_mask is not None:
            min_mask = min(len(vad_mask), len(global_ratio))
            global_voiced = global_ratio[:min_mask][vad_mask[:min_mask]]
        else:
            global_voiced = global_ratio
        print(f"  Nasal ratio (voiced): mean={global_voiced.mean():.3f}, "
              f"std={global_voiced.std():.3f}" if len(global_voiced) > 0 else "  No voiced frames")

        # F0 from oral recording
        f0_vals, f0_times = extract_f0(oral_path)
        voiced_n = (f0_vals > 0).sum()
        print(f"  F0: {voiced_n}/{len(f0_vals)} voiced frames")

        # Register split
        boundaries = split_registers(f0_vals)
        ratio_stats = nasal_ratio_by_register(
            rms_oral, rms_nasal, rms_times, f0_vals, f0_times, boundaries,
            vad_mask=vad_mask
        )

        for reg in ["low", "mid", "high"]:
            s = ratio_stats[reg]
            if s["mean"] is not None:
                print(f"  Nasal {reg}: mean={s['mean']:.3f}, "
                      f"median={s['median']:.3f} (n={s['n_frames']})")

        result = {
            "singer_id": singer_id,
            "song_id": song_id,
            "oral_file": os.path.basename(oral_path),
            "nasal_file": os.path.basename(nasal_path),
            "duration_s": round(min_len / TARGET_SR, 2),
            "vad_applied": vad_mask is not None,
            "f0_stats": {
                "n_voiced": int(voiced_n),
                **boundaries,
            },
            "nasal_ratio_global": {
                "mean": float(global_voiced.mean()) if len(global_voiced) > 0 else None,
                "std": float(global_voiced.std()) if len(global_voiced) > 0 else None,
                "median": float(np.median(global_ratio)),
            },
            "nasal_ratio_by_register": ratio_stats,
        }
        all_results.append(result)

    output = {
        "description": "Oral/nasal ratio analysis for vocal academy recordings",
        "n_pairs": len(all_results),
        "results": all_results,
    }
    json_path = os.path.join(RESULTS_DIR, "nasal_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")
    print(f"   {len(all_results)} oral/nasal pairs analyzed")


if __name__ == "__main__":
    main()
