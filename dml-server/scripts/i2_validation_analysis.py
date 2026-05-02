#!/usr/bin/env python3
"""
i2_validation_analysis.py
Extract acoustic metrics from validation/test_01~11.wav
Using same pipeline as training (intersect VAD, voiced frames, EGG model).
Validation wav = single microphone (treated as phone-equivalent).

Results: results/validation_metrics.json
"""
import os
import sys
import json
import re
import glob
import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_MODEL_DIR = os.path.join(PROJECT_ROOT, "ai-model")
sys.path.insert(0, AI_MODEL_DIR)
from model.efficient_egg import build_efficient_model

VOCAL_DIR   = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
VAL_DIR     = os.path.join(VOCAL_DIR, "validation")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
MASK_DIR    = os.path.join(RESULTS_DIR, "vad_masks")
CHECKPOINT  = os.path.join(PROJECT_ROOT, "checkpoints", "exp20_progressive", "best_model.pt")

TARGET_SR = 16000
N_FFT     = 1024
HOP       = 256
F0_FLOOR  = 75
F0_CEIL   = 600
WINDOW_SIZE = 16384
HOP_SIZE    = 8192

EXP20_CONFIG = {
    "channels": 128, "n_layers": 30, "kernel_size": 5,
    "n_stacks": 5, "dropout": 0.05,
}


def load_audio(wav_path):
    audio, sr = sf.read(wav_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    std = audio.std()
    if std > 1e-8:
        audio = (audio - audio.mean()) / std
    return audio


def generate_vad_mask(audio, wav_path):
    """2-stage VAD: RMS energy + F0."""
    FRAME_LEN = HOP * 2
    n_frames = max(0, (len(audio) - FRAME_LEN) // HOP + 1)
    frame_times = np.array([(i * HOP + FRAME_LEN / 2) / TARGET_SR for i in range(n_frames)])

    # Stage 1: RMS
    rms = np.array([np.sqrt(np.mean(audio[i*HOP:i*HOP+FRAME_LEN]**2)) for i in range(n_frames)])
    p90 = np.percentile(rms, 90)
    rms_mask = rms >= p90 * 0.10

    # Stage 2: F0
    snd = parselmouth.Sound(wav_path)
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_p = call(pitch, "Get number of frames")
    f0_vals = np.zeros(n_p); f0_times = np.zeros(n_p)
    for i in range(1, n_p + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals[i-1] = f if f == f else 0.0
        f0_times[i-1] = t

    f0_mask = np.zeros(n_frames, dtype=bool)
    for i, t in enumerate(frame_times):
        idx = np.argmin(np.abs(f0_times - t))
        f0_mask[i] = f0_vals[idx] > 0

    return rms_mask & f0_mask, f0_vals, f0_times


def extract_f0_voiced(f0_vals):
    """Split F0 into low/mid/high registers by 33/66 percentile."""
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 200, "mid_max": 300}
    p33 = float(np.percentile(voiced, 33))
    p66 = float(np.percentile(voiced, 66))
    return {"low_max": p33, "mid_max": p66,
            "f0_min": float(voiced.min()), "f0_max": float(voiced.max()),
            "f0_mean": float(voiced.mean())}


@torch.no_grad()
def predict_egg(model, audio, device):
    total_len = len(audio)
    if total_len < WINDOW_SIZE:
        padded = np.zeros(WINDOW_SIZE, dtype=np.float32); padded[:total_len] = audio
        x = torch.from_numpy(padded).float().unsqueeze(0).unsqueeze(0).to(device)
        return model(x).squeeze().cpu().numpy()[:total_len]
    output = np.zeros(total_len, dtype=np.float32)
    count = np.zeros(total_len, dtype=np.float32)
    starts = list(range(0, total_len - WINDOW_SIZE + 1, HOP_SIZE))
    if starts and starts[-1] + WINDOW_SIZE < total_len:
        starts.append(total_len - WINDOW_SIZE)
    for s in starts:
        chunk = audio[s:s + WINDOW_SIZE]
        x = torch.from_numpy(chunk).float().unsqueeze(0).unsqueeze(0).to(device)
        pred = model(x).squeeze().cpu().numpy()
        output[s:s + WINDOW_SIZE] += pred
        count[s:s + WINDOW_SIZE] += 1.0
    return output / np.maximum(count, 1e-8)


def compute_metrics_by_register(audio, egg_pred, vad_mask, f0_vals, f0_times, boundaries):
    """Compute all metrics per register (low/mid/high)."""
    FRAME_LEN = HOP * 2
    n_frames = max(0, (len(audio) - FRAME_LEN) // HOP + 1)
    frame_times = np.array([(i * HOP + FRAME_LEN / 2) / TARGET_SR for i in range(n_frames)])

    # STFT for spectral features
    S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP)
    S_mag = np.abs(S)
    stft_n = S_mag.shape[1]
    freqs = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
    centroid = librosa.feature.spectral_centroid(S=S_mag, sr=TARGET_SR, n_fft=N_FFT)[0]

    # Spectral tilt (log-mag slope)
    def spectral_tilt(frame_idx):
        if frame_idx >= stft_n: return np.nan
        log_mag = np.log10(S_mag[:, frame_idx] + 1e-10)
        valid = freqs > 0
        lf = np.log10(freqs[valid])
        y = log_mag[valid]
        coeff = np.polyfit(lf, y, 1) if len(lf) > 2 else [0, 0]
        return coeff[0]

    # H1-H2
    def h1_h2(i, f0):
        start = i * HOP
        frame = audio[start:start + N_FFT] * np.hanning(N_FFT)
        spec_db = 20 * np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
        fq = np.fft.rfftfreq(N_FFT, 1.0 / TARGET_SR)
        sr_bin = TARGET_SR / N_FFT
        h1_idx = int(f0 / sr_bin); h1_r = max(1, int(100 / sr_bin))
        h2_idx = int(2 * f0 / sr_bin); h2_r = max(1, int(100 / sr_bin))
        h1_r_s = spec_db[max(0, h1_idx - h1_r):h1_idx + h1_r + 1]
        h2_r_s = spec_db[max(0, h2_idx - h2_r):h2_idx + h2_r + 1]
        return h1_r_s.max() - h2_r_s.max() if len(h1_r_s) > 0 and len(h2_r_s) > 0 else np.nan

    # CPP
    window = np.hanning(N_FFT)
    def cpp(i):
        start = i * HOP
        frame = audio[start:start + N_FFT] * window
        if np.abs(frame).max() < 1e-8: return np.nan
        spec = np.abs(np.fft.rfft(frame))
        log_spec = np.log(spec + 1e-10)
        cepstrum = np.fft.irfft(log_spec)
        q_min = int(TARGET_SR / F0_CEIL); q_max = min(int(TARGET_SR / F0_FLOOR), len(cepstrum)//2)
        if q_min >= q_max: return np.nan
        seg = cepstrum[q_min:q_max]
        pk_idx = np.argmax(seg); pk_val = seg[pk_idx]
        x = np.arange(len(seg), dtype=float)
        coeff = np.polyfit(x, seg, 1) if len(x) > 2 else [0, seg.mean()]
        baseline = np.polyval(coeff, x[pk_idx])
        return pk_val - baseline

    # CQ (from EGG)
    cq_frame_len = HOP * 2
    def cq(i):
        start = i * HOP
        frame = egg_pred[start:start + cq_frame_len] if start + cq_frame_len <= len(egg_pred) else egg_pred[start:]
        if len(frame) == 0: return np.nan
        return (frame > 0).sum() / len(frame)

    # HNR from parselmouth — compute globally, then map to frames
    snd_raw = parselmouth.Sound(audio, sampling_frequency=TARGET_SR)
    try:
        harm = call(snd_raw, "To Harmonicity (cc)", 0.01, F0_FLOOR, 0.1, 1.0)
        n_h = call(harm, "Get number of frames")
        hnr_vals = []; hnr_times = []
        for ii in range(1, n_h + 1):
            t = call(harm, "Get time from frame number", ii)
            v = call(harm, "Get value in frame", ii)
            hnr_vals.append(v if v == v else np.nan)
            hnr_times.append(t)
        hnr_vals = np.array(hnr_vals); hnr_times = np.array(hnr_times)
    except Exception:
        hnr_vals = np.array([]); hnr_times = np.array([])

    # A1-P0 from parselmouth formant
    try:
        formant = call(snd_raw, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
        n_f = call(formant, "Get number of frames")
        a1p0_vals = []; a1p0_frames = []
        for ii in range(1, n_f + 1):
            t = call(formant, "Get time from frame number", ii)
            f1 = call(formant, "Get value at time", 1, t, "Hertz", "Linear")
            if not (f1 == f1) or f1 <= 0: continue
            fi = int(t * TARGET_SR) - N_FFT // 2
            if fi < 0 or fi + N_FFT > len(audio): continue
            frame = audio[fi:fi + N_FFT] * window
            spec_db = 20 * np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
            fq = np.fft.rfftfreq(N_FFT, 1.0 / TARGET_SR)
            sr_bin = TARGET_SR / N_FFT
            f1_idx = int(f1 / sr_bin); f1_r = max(1, int(100 / sr_bin))
            p0_idx = int(250 / sr_bin); p0_r = max(1, int(50 / sr_bin))
            a1 = spec_db[max(0, f1_idx - f1_r):f1_idx + f1_r + 1].max()
            p0 = spec_db[max(0, p0_idx - p0_r):p0_idx + p0_r + 1].max()
            a1p0_vals.append(a1 - p0)
            a1p0_frames.append(ii - 1)
    except Exception:
        a1p0_vals = []

    # Singers formant ratio
    sfm_ratio = []
    mask_2k4k = (freqs >= 2000) & (freqs <= 4000)

    # Aggregate by register
    registers = {"low": [], "mid": [], "high": []}
    metrics_keys = ["cq_mean", "cq_peak", "cpp", "hnr", "spectral_centroid",
                    "spectral_tilt", "h1_h2", "singers_formant_ratio", "a1_p0"]
    data = {k: {r: [] for r in registers} for k in metrics_keys}

    for i, t in enumerate(frame_times):
        if i >= len(vad_mask) or not vad_mask[i]: continue
        # F0 → register
        fi = np.argmin(np.abs(f0_times - t))
        f0 = f0_vals[fi]
        if f0 <= 0: continue
        if f0 <= boundaries["low_max"]:
            reg = "low"
        elif f0 <= boundaries["mid_max"]:
            reg = "mid"
        else:
            reg = "high"

        # CQ
        cq_v = cq(i)
        if not np.isnan(cq_v):
            data["cq_mean"][reg].append(cq_v)
            data["cq_peak"][reg].append(cq_v)  # stored separately for peak calc

        # CPP
        cpp_v = cpp(i)
        if not np.isnan(cpp_v): data["cpp"][reg].append(cpp_v)

        # HNR
        if len(hnr_times) > 0:
            hi = np.argmin(np.abs(hnr_times - t))
            hnr_v = hnr_vals[hi]
            if not np.isnan(hnr_v): data["hnr"][reg].append(hnr_v)

        # Spectral centroid
        si = min(int(t * TARGET_SR / HOP), len(centroid) - 1)
        data["spectral_centroid"][reg].append(centroid[si])

        # Spectral tilt
        tilt_v = spectral_tilt(si)
        if not np.isnan(tilt_v): data["spectral_tilt"][reg].append(tilt_v)

        # H1-H2
        hh = h1_h2(i, f0)
        if not np.isnan(hh): data["h1_h2"][reg].append(hh)

        # Singer's formant ratio
        if si < stft_n:
            total_e = (S_mag[:, si] ** 2).sum()
            sf_e = (S_mag[mask_2k4k, si] ** 2).sum()
            data["singers_formant_ratio"][reg].append(sf_e / (total_e + 1e-10))

    # A1-P0 (per file, distribute across all voiced frames equally)
    a1p0_mean = float(np.mean(a1p0_vals)) if a1p0_vals else None
    for reg in registers:
        if data["cq_mean"][reg]:
            n_reg = len(data["cq_mean"][reg])
            data["a1_p0"][reg] = [a1p0_mean] * n_reg if a1p0_mean else []

    def stats(vals, is_cq_peak=False):
        arr = np.array(vals) if vals else np.array([])
        if len(arr) == 0:
            return {"mean": None, "std": None, "median": None, "n": 0}
        return {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "median": float(np.median(arr)),
            "peak": float(np.percentile(arr, 90)) if is_cq_peak else None,
            "n": len(arr),
        }

    result = {}
    for reg in ["low", "mid", "high"]:
        result[reg] = {
            "cq_mean": stats(data["cq_mean"][reg]),
            "cq_peak": {"mean": float(np.percentile(data["cq_peak"][reg], 90)) if data["cq_peak"][reg] else None,
                        "n": len(data["cq_peak"][reg])},
            "cpp": stats(data["cpp"][reg]),
            "hnr": stats(data["hnr"][reg]),
            "spectral_centroid": stats(data["spectral_centroid"][reg]),
            "spectral_tilt": stats(data["spectral_tilt"][reg]),
            "h1_h2": stats(data["h1_h2"][reg]),
            "singers_formant_ratio": stats(data["singers_formant_ratio"][reg]),
            "a1_p0": stats(data["a1_p0"][reg]),
        }
    return result


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Load EGG model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficient_model(EXP20_CONFIG)
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    print(f"Model loaded: device={device}, val_corr={ckpt.get('val_corr'):.4f}")

    val_files = sorted(glob.glob(os.path.join(VAL_DIR, "test_*.wav")))
    print(f"Found {len(val_files)} validation files")

    all_results = {}

    for wav_path in val_files:
        fname = os.path.basename(wav_path)
        test_id = fname.replace(".wav", "")  # "test_01" etc.
        test_n = int(test_id.split("_")[1])

        print(f"\n{'='*50}")
        print(f"Processing: {fname}")

        audio = load_audio(wav_path)
        vad_mask, f0_vals, f0_times = generate_vad_mask(audio, wav_path)
        voiced_ratio = vad_mask.sum() / len(vad_mask) if len(vad_mask) > 0 else 0
        print(f"  VAD: {vad_mask.sum()}/{len(vad_mask)} voiced ({voiced_ratio:.1%})")

        boundaries = extract_f0_voiced(f0_vals)

        egg_pred = predict_egg(model, audio, device)
        print(f"  EGG: NaN={np.isnan(egg_pred).any()}, range=[{egg_pred.min():.2f}, {egg_pred.max():.2f}]")

        metrics = compute_metrics_by_register(audio, egg_pred, vad_mask, f0_vals, f0_times, boundaries)

        for reg, m in metrics.items():
            cq_v = m['cq_mean']['mean']; cpp_v = m['cpp']['mean']
            sc_v = m['spectral_centroid']['mean']
            print(f"  {reg}: CQ={'N/A' if cq_v is None else f'{cq_v:.3f}'}, "
                  f"CPP={'N/A' if cpp_v is None else f'{cpp_v:.3f}'}, "
                  f"centroid={'N/A' if sc_v is None else f'{sc_v:.0f}Hz'}")

        all_results[test_id] = {
            "test_n": test_n,
            "duration_s": round(len(audio) / TARGET_SR, 1),
            "voiced_ratio": round(voiced_ratio, 4),
            "f0_stats": boundaries,
            "metrics_by_register": metrics,
        }

    out_path = os.path.join(RESULTS_DIR, "validation_metrics.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "description": "Acoustic metrics for validation test_01~11",
            "note": "Single microphone (phone-equivalent). nasal_ratio unavailable.",
            "n_files": len(all_results),
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved: {out_path}")
    print(f"   {len(all_results)} files analyzed")


if __name__ == "__main__":
    main()
