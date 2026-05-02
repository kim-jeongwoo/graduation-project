#!/usr/bin/env python3
"""
vad_preprocess.py — VAD(Voice Activity Detection) 마스크 생성
==============================================================
각 wav에 대해 2단계 필터링으로 voiced 프레임 마스크를 생성:
  1단계: RMS 에너지 기반 무음 제거 (파일별 적응 threshold)
  2단계: parselmouth F0 기반 무성음 제거

결과: data/vocal_academy/results/vad_masks/{singer}_{song}_{type}_vad.npy
"""
import os
import glob
import re
import json

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
HOP = 256
FRAME_LEN = 512  # 32ms
F0_FLOOR = 75
F0_CEIL = 600


def load_audio(wav_path):
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    return audio


def compute_rms_frames(audio):
    n_frames = max(0, (len(audio) - FRAME_LEN) // HOP + 1)
    rms = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        start = i * HOP
        frame = audio[start:start + FRAME_LEN]
        rms[i] = np.sqrt(np.mean(frame ** 2))
    return rms


def extract_f0_frames(wav_path):
    """Return (f0_values, f0_times) at parselmouth's own frame rate."""
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n = call(pitch, "Get number of frames")
    f0_vals = np.zeros(n)
    f0_times = np.zeros(n)
    for i in range(1, n + 1):
        f0_times[i - 1] = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals[i - 1] = f if f == f else 0.0
    return f0_vals, f0_times


def generate_vad_mask(audio, wav_path):
    """
    Generate frame-level VAD mask (True = voiced).
    Frame grid: hop=256, frame_len=512, sr=16000.
    
    Returns: mask [n_frames], frame_times [n_frames]
    """
    n_frames = max(0, (len(audio) - FRAME_LEN) // HOP + 1)
    frame_times = np.array([(i * HOP + FRAME_LEN / 2) / TARGET_SR for i in range(n_frames)])

    # Stage 1: RMS energy
    rms = compute_rms_frames(audio)
    # Adaptive threshold: 10% of p90 RMS
    p90 = np.percentile(rms, 90)
    rms_threshold = p90 * 0.10
    rms_mask = rms >= rms_threshold

    # Stage 2: F0-based voicing
    f0_vals, f0_times = extract_f0_frames(wav_path)
    f0_mask = np.zeros(n_frames, dtype=bool)
    for i, t in enumerate(frame_times):
        if len(f0_times) == 0:
            break
        idx = np.argmin(np.abs(f0_times - t))
        f0_mask[i] = f0_vals[idx] > 0

    # Combined: both RMS and F0 must pass
    vad_mask = rms_mask & f0_mask

    return vad_mask, frame_times, rms_threshold, p90


def mask_key(wav_path):
    """Generate mask filename from wav path: singer_song_type."""
    fname = os.path.basename(wav_path)
    # e.g. 2-3_phone.wav → 2_3_phone
    m = re.match(r'(\d+)-(\d+)_(\w+)\.wav', fname)
    if m:
        return f"{m.group(1)}_{m.group(2)}_{m.group(3)}"
    return fname.replace('.wav', '').replace('-', '_')


def main():
    os.makedirs(MASK_DIR, exist_ok=True)

    all_wavs = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*.wav")))
    print(f"Found {len(all_wavs)} wav files")

    summary = []
    for wav_path in all_wavs:
        fname = os.path.basename(wav_path)
        singer_dir = os.path.basename(os.path.dirname(wav_path))

        audio = load_audio(wav_path)
        total_samples = len(audio)
        total_dur = total_samples / TARGET_SR

        vad_mask, frame_times, rms_thr, p90 = generate_vad_mask(audio, wav_path)
        n_voiced = vad_mask.sum()
        n_total = len(vad_mask)
        ratio = n_voiced / n_total if n_total > 0 else 0

        key = mask_key(wav_path)
        npy_path = os.path.join(MASK_DIR, f"{key}_vad.npy")
        np.save(npy_path, vad_mask)

        print(f"  {singer_dir}/{fname}: {total_dur:.0f}s, "
              f"voiced={n_voiced}/{n_total} ({ratio:.1%}), "
              f"rms_thr={rms_thr:.5f}")

        summary.append({
            "file": fname,
            "singer_dir": singer_dir,
            "mask_file": os.path.basename(npy_path),
            "total_frames": int(n_total),
            "voiced_frames": int(n_voiced),
            "voiced_ratio": round(float(ratio), 4),
            "duration_s": round(total_dur, 1),
            "rms_p90": round(float(p90), 6),
            "rms_threshold": round(float(rms_thr), 6),
        })

    # Save summary
    summary_path = os.path.join(MASK_DIR, "vad_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"n_files": len(summary), "files": summary}, f,
                  ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(summary)} VAD masks to {MASK_DIR}")
    print(f"   Summary: {summary_path}")

    # Print stats
    ratios = [s["voiced_ratio"] for s in summary]
    print(f"   Voiced ratio: min={min(ratios):.1%}, max={max(ratios):.1%}, "
          f"mean={np.mean(ratios):.1%}")


if __name__ == "__main__":
    main()
