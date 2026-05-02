#!/usr/bin/env python3
"""
batch_analyze.py — 보컬 학원 phone.wav 배치 EGG 추정 + CQ 분석
================================================================
phone.wav 파일에 대해:
  1. EGG 추정 (Exp20 모델, 로컬 추론)
  2. CQ(Contact Quotient) 프레임 단위 추출 (VAD 마스크 적용)
  3. F0 추출 (parselmouth) → 저/중/고 음역대 분리
  4. 음역대별 CQ 통계 (cq_mean + cq_peak for differentiation)

결과: data/vocal_academy/results/egg_analysis.json
"""
import os
import sys
import json
import glob
import re

import numpy as np
import librosa
import soundfile as sf
import torch
import parselmouth
from parselmouth.praat import call

# ── paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MODEL_DIR = os.path.join(PROJECT_ROOT, "ai-model")
sys.path.insert(0, AI_MODEL_DIR)

from model.efficient_egg import build_efficient_model

VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
MASK_DIR = os.path.join(RESULTS_DIR, "vad_masks")
CHECKPOINT = os.path.join(PROJECT_ROOT, "checkpoints", "exp20_progressive", "best_model.pt")

TARGET_SR = 16000
WINDOW_SIZE = 16384
HOP_SIZE = 8192  # 50% overlap for inference
CQ_HOP = 256    # ~16ms frames for CQ
F0_FLOOR = 75
F0_CEIL = 600

# Pairs to exclude: voiced data insufficient for reliable analysis
EXCLUDE_PAIRS = {(6, 8)}  # Singer 6 Song 8: phone=0%, oral/nasal=18%

EXP20_CONFIG = {
    "channels": 128, "n_layers": 30, "kernel_size": 5,
    "n_stacks": 5, "dropout": 0.05,
}


# ── Model loading ─────────────────────────────────────────────────
def load_model(device):
    model = build_efficient_model(EXP20_CONFIG)
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    print(f"Model loaded: val_corr={ckpt.get('val_corr'):.4f}, device={device}")
    return model


# ── Preprocessing (same as training) ──────────────────────────────
def preprocess_wav(wav_path):
    """Load wav → 16kHz mono float32 → z-score."""
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    std = audio.std()
    if std > 1e-8:
        audio = (audio - audio.mean()) / std
    return audio


# ── Windowed inference ────────────────────────────────────────────
@torch.no_grad()
def predict_egg(model, audio, device):
    """Windowed inference with overlap-add."""
    total_len = len(audio)
    if total_len < WINDOW_SIZE:
        padded = np.zeros(WINDOW_SIZE, dtype=np.float32)
        padded[:total_len] = audio
        x = torch.from_numpy(padded).float().unsqueeze(0).unsqueeze(0).to(device)
        pred = model(x).squeeze().cpu().numpy()
        return pred[:total_len]

    output = np.zeros(total_len, dtype=np.float32)
    count = np.zeros(total_len, dtype=np.float32)

    for start in range(0, total_len - WINDOW_SIZE + 1, HOP_SIZE):
        chunk = audio[start:start + WINDOW_SIZE]
        x = torch.from_numpy(chunk).float().unsqueeze(0).unsqueeze(0).to(device)
        pred = model(x).squeeze().cpu().numpy()
        output[start:start + WINDOW_SIZE] += pred
        count[start:start + WINDOW_SIZE] += 1.0

    # Handle tail
    if count[-1] == 0:
        last_start = total_len - WINDOW_SIZE
        if last_start >= 0:
            chunk = audio[last_start:last_start + WINDOW_SIZE]
            x = torch.from_numpy(chunk).float().unsqueeze(0).unsqueeze(0).to(device)
            pred = model(x).squeeze().cpu().numpy()
            output[last_start:last_start + WINDOW_SIZE] += pred
            count[last_start:last_start + WINDOW_SIZE] += 1.0

    count = np.maximum(count, 1.0)
    return output / count


# ── VAD mask loading ──────────────────────────────────────────────
def load_vad_mask(singer_id, song_id, mic_type="phone"):
    """Load intersect mask if available, else individual mask."""
    intersect_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_intersect_vad.npy")
    if os.path.exists(intersect_path):
        return np.load(intersect_path)
    mask_path = os.path.join(MASK_DIR, f"{singer_id}_{song_id}_{mic_type}_vad.npy")
    if os.path.exists(mask_path):
        return np.load(mask_path)
    return None


# ── CQ extraction ─────────────────────────────────────────────────
def compute_cq_frames(egg_signal, sr=TARGET_SR, hop=CQ_HOP):
    """
    Frame-level CQ: fraction of samples > 0 in each frame.
    Returns: cq_values [n_frames], frame_times [n_frames]
    """
    frame_len = hop * 2  # ~32ms frame, 16ms hop
    n_frames = max(0, (len(egg_signal) - frame_len) // hop + 1)
    cqs = np.zeros(n_frames, dtype=np.float32)
    times = np.zeros(n_frames, dtype=np.float32)

    for i in range(n_frames):
        start = i * hop
        frame = egg_signal[start:start + frame_len]
        cqs[i] = (frame > 0).sum() / len(frame)
        times[i] = (start + frame_len / 2) / sr

    return cqs, times


# ── F0 extraction ─────────────────────────────────────────────────
def extract_f0(wav_path):
    """Extract F0 using parselmouth (Praat). Returns f0_values, f0_times."""
    snd = parselmouth.Sound(wav_path)
    # Resample to 16kHz for consistency
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_frames = call(pitch, "Get number of frames")

    f0_vals = []
    f0_times = []
    for i in range(1, n_frames + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals.append(f if f == f else 0.0)  # NaN → 0
        f0_times.append(t)

    return np.array(f0_vals), np.array(f0_times)


def split_registers(f0_vals):
    """
    Split voiced F0 into 저/중/고 using 33rd/66th percentile.
    Returns: boundaries dict, register labels.
    """
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 0, "mid_max": 0, "high_min": 0}, voiced

    p33 = np.percentile(voiced, 33)
    p66 = np.percentile(voiced, 66)
    return {
        "low_max": float(p33),
        "mid_max": float(p66),
        "high_min": float(p66),
        "f0_min": float(voiced.min()),
        "f0_max": float(voiced.max()),
        "f0_mean": float(voiced.mean()),
    }, voiced


def cq_by_register(cq_vals, cq_times, f0_vals, f0_times, boundaries, vad_mask=None):
    """Compute CQ stats per register by aligning CQ frames with F0.
    If vad_mask provided, only use voiced frames."""
    results = {"low": [], "mid": [], "high": []}

    for i, t in enumerate(cq_times):
        # Apply VAD mask if available
        if vad_mask is not None and i < len(vad_mask) and not vad_mask[i]:
            continue

        # Find nearest F0 frame
        idx = np.argmin(np.abs(f0_times - t))
        f0 = f0_vals[idx]
        if f0 <= 0:
            continue  # unvoiced

        if f0 <= boundaries["low_max"]:
            results["low"].append(cq_vals[i])
        elif f0 <= boundaries["mid_max"]:
            results["mid"].append(cq_vals[i])
        else:
            results["high"].append(cq_vals[i])

    stats = {}
    for reg in ["low", "mid", "high"]:
        arr = np.array(results[reg]) if results[reg] else np.array([])
        stats[reg] = {
            "n_frames": len(arr),
            "mean": float(arr.mean()) if len(arr) > 0 else None,
            "std": float(arr.std()) if len(arr) > 0 else None,
            "median": float(np.median(arr)) if len(arr) > 0 else None,
            "peak": float(np.percentile(arr, 90)) if len(arr) > 0 else None,
        }
    return stats


# ── Main ──────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(device)

    # Find all phone.wav files
    phone_files = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*_phone.wav")))
    print(f"\nFound {len(phone_files)} phone recordings")

    all_results = []

    for wav_path in phone_files:
        fname = os.path.basename(wav_path)
        singer_dir = os.path.basename(os.path.dirname(wav_path))
        m = re.match(r'(\d+)-(\d+)', fname)
        singer_id = int(m.group(1)) if m else 0
        song_id = int(m.group(2)) if m else 0

        if (singer_id, song_id) in EXCLUDE_PAIRS:
            print(f"  [SKIP] Singer {singer_id} Song {song_id}: in EXCLUDE_PAIRS")
            continue

        print(f"\n{'='*50}")
        print(f"Processing: {singer_dir}/{fname} (singer={singer_id}, song={song_id})")

        # Load VAD mask
        vad_mask = load_vad_mask(singer_id, song_id, "phone")
        if vad_mask is not None:
            voiced_ratio = vad_mask.sum() / len(vad_mask)
            print(f"  VAD: {vad_mask.sum()}/{len(vad_mask)} voiced ({voiced_ratio:.1%})")
        else:
            print(f"  VAD: mask not found, using all frames")

        # 1. Preprocess + EGG inference
        audio = preprocess_wav(wav_path)
        egg_pred = predict_egg(model, audio, device)
        print(f"  Audio: {len(audio)} samples ({len(audio)/TARGET_SR:.1f}s)")
        print(f"  EGG pred: range=[{egg_pred.min():.3f}, {egg_pred.max():.3f}], "
              f"NaN={np.isnan(egg_pred).any()}")

        # Save predicted EGG as npy
        npy_name = fname.replace('.wav', '_egg.npy')
        npy_path = os.path.join(RESULTS_DIR, npy_name)
        np.save(npy_path, egg_pred)

        # 2. CQ extraction
        cq_vals, cq_times = compute_cq_frames(egg_pred)

        # Apply VAD to CQ global stats
        if vad_mask is not None and len(vad_mask) == len(cq_vals):
            cq_voiced = cq_vals[vad_mask]
        elif vad_mask is not None:
            # Align lengths
            min_len = min(len(vad_mask), len(cq_vals))
            cq_voiced = cq_vals[:min_len][vad_mask[:min_len]]
        else:
            cq_voiced = cq_vals

        print(f"  CQ: {len(cq_voiced)} voiced frames (of {len(cq_vals)} total), "
              f"mean={cq_voiced.mean():.3f}" if len(cq_voiced) > 0 else f"  CQ: no voiced frames")

        # 3. F0 extraction
        f0_vals, f0_times = extract_f0(wav_path)
        voiced_mask = f0_vals > 0
        n_voiced = voiced_mask.sum()
        print(f"  F0: {n_voiced}/{len(f0_vals)} voiced frames")

        # 4. Register split + CQ by register (with VAD)
        boundaries, voiced_f0 = split_registers(f0_vals)
        cq_stats = cq_by_register(cq_vals, cq_times, f0_vals, f0_times, boundaries,
                                  vad_mask=vad_mask)

        for reg in ["low", "mid", "high"]:
            s = cq_stats[reg]
            if s["mean"] is not None:
                print(f"  CQ {reg}: mean={s['mean']:.3f}, peak={s['peak']:.3f}, "
                      f"std={s['std']:.3f} (n={s['n_frames']})")
            else:
                print(f"  CQ {reg}: no voiced frames")

        result = {
            "file": fname,
            "singer_id": singer_id,
            "song_id": song_id,
            "duration_s": round(len(audio) / TARGET_SR, 2),
            "egg_npy": npy_name,
            "vad_applied": vad_mask is not None,
            "f0_stats": {
                "n_voiced": int(n_voiced),
                "n_total": int(len(f0_vals)),
                **boundaries,
            },
            "cq_global": {
                "mean": float(cq_voiced.mean()) if len(cq_voiced) > 0 else None,
                "std": float(cq_voiced.std()) if len(cq_voiced) > 0 else None,
                "median": float(np.median(cq_voiced)) if len(cq_voiced) > 0 else None,
                "peak": float(np.percentile(cq_voiced, 90)) if len(cq_voiced) > 0 else None,
            },
            "cq_by_register": cq_stats,
        }
        all_results.append(result)

    # Save JSON
    output = {
        "description": "EGG estimation + CQ analysis (VAD filtered, voiced frames only)",
        "model": "Exp20 EfficientEGGNet (Corr=0.8249)",
        "n_files": len(all_results),
        "results": all_results,
    }
    json_path = os.path.join(RESULTS_DIR, "egg_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")
    print(f"   {len(all_results)} files analyzed")


if __name__ == "__main__":
    main()
