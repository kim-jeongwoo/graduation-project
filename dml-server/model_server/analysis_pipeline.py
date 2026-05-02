"""
analysis_pipeline.py — Single-wav acoustic analysis pipeline (L-1)
====================================================================
Stateless analysis function. All heavy state (model, mappings) is
passed in via AnalysisPipeline class to support server-side caching.

Usage:
    pipeline = AnalysisPipeline(checkpoint_path, criteria_path, mappings_path)
    result = pipeline.analyze(audio_bytes_or_path)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from functools import lru_cache
from typing import Dict, Optional, Tuple

import librosa
import numpy as np
import parselmouth
import soundfile as sf
import torch
from parselmouth.praat import call

# ── paths ──────────────────────────────────────────────────────────
_SERVER_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SERVER_DIR)
_AI_MODEL_DIR = os.path.join(_PROJECT_ROOT, "ai-model")
if _AI_MODEL_DIR not in sys.path:
    sys.path.insert(0, _AI_MODEL_DIR)

from model.efficient_egg import build_efficient_model   # noqa: E402

# ── constants ──────────────────────────────────────────────────────
TARGET_SR    = 16000
N_FFT        = 1024
HOP          = 256
F0_FLOOR     = 75
F0_CEIL      = 600
WINDOW_SIZE  = 16384
HOP_SIZE     = 8192
MIN_VOICED_S = 5.0      # minimum voiced seconds; shorter → 422

EXP20_CONFIG = {
    "channels": 128, "n_layers": 30, "kernel_size": 5,
    "n_stacks": 5, "dropout": 0.05,
}

# Reliability classification (from Phase I/J validation results)
HIGH_RELIABILITY   = ["3_vocal_fold_contact", "4_breathiness"]
MEDIUM_RELIABILITY = [
    "1_nasal_oral_ratio", "2_chest_head_voice",
    "5_forward_resonance", "6_soft_palate", "9_pressure_balance",
]
UNAVAILABLE = ["7_larynx_tongue_root", "8_tongue_tension"]

# CSV column → criteria key
CSV_TO_CRITERIA = {
    "비강사용":  "1_nasal_oral_ratio",
    "흉성두성":  "2_chest_head_voice",
    "접촉강도":  "3_vocal_fold_contact",
    "호흡식별":  "4_breathiness",
    "전방공명":  "5_forward_resonance",
    "연구개위치": "6_soft_palate",
    "공명개방":  "7_larynx_tongue_root",
    "혀경직도":  "8_tongue_tension",
    "상압하압":  "9_pressure_balance",
}
CRITERIA_KEYS = list(CSV_TO_CRITERIA.values())


# ── helpers ────────────────────────────────────────────────────────

def _load_audio_bytes(data: bytes) -> Tuple[np.ndarray, float]:
    """Load audio from bytes, resample to 16 kHz, z-score normalize."""
    buf = io.BytesIO(data)
    audio, sr = sf.read(buf, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sr
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    std = audio.std()
    if std > 1e-8:
        audio = (audio - audio.mean()) / std
    return audio, duration


def _generate_vad(audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    2-stage VAD: RMS energy + parselmouth F0.
    Returns: (vad_mask [n_frames], f0_vals [n_f0], f0_times [n_f0])
    """
    frame_len = HOP * 2
    n_frames = max(0, (len(audio) - frame_len) // HOP + 1)
    rms = np.array([
        np.sqrt(np.mean(audio[i*HOP:i*HOP+frame_len]**2))
        for i in range(n_frames)
    ], dtype=np.float32)
    p90 = np.percentile(rms, 90)
    rms_mask = rms >= p90 * 0.10

    # Parselmouth operates on float32 array
    snd = parselmouth.Sound(audio, sampling_frequency=TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_f0 = call(pitch, "Get number of frames")
    f0_vals = np.zeros(n_f0); f0_times = np.zeros(n_f0)
    for i in range(1, n_f0 + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals[i-1] = f if f == f else 0.0
        f0_times[i-1] = t

    frame_times = np.array([(i*HOP + frame_len/2) / TARGET_SR for i in range(n_frames)])
    f0_mask = np.zeros(n_frames, dtype=bool)
    for i, t in enumerate(frame_times):
        idx = np.argmin(np.abs(f0_times - t))
        f0_mask[i] = f0_vals[idx] > 0

    return rms_mask & f0_mask, f0_vals, f0_times


def _split_registers(f0_vals: np.ndarray) -> dict:
    voiced = f0_vals[f0_vals > 0]
    if len(voiced) < 10:
        return {"low_max": 200.0, "mid_max": 300.0, "f0_min": None, "f0_max": None, "f0_mean": None}
    return {
        "low_max": float(np.percentile(voiced, 33)),
        "mid_max": float(np.percentile(voiced, 66)),
        "f0_min": float(voiced.min()),
        "f0_max": float(voiced.max()),
        "f0_mean": float(voiced.mean()),
    }


def _predict_egg(model, audio: np.ndarray, device) -> np.ndarray:
    """Windowed EGG inference with overlap-add."""
    total = len(audio)
    if total < WINDOW_SIZE:
        pad = np.zeros(WINDOW_SIZE, dtype=np.float32)
        pad[:total] = audio
        x = torch.from_numpy(pad).float().unsqueeze(0).unsqueeze(0).to(device)
        with torch.no_grad():
            return model(x).squeeze().cpu().numpy()[:total]
    out = np.zeros(total, dtype=np.float32)
    cnt = np.zeros(total, dtype=np.float32)
    starts = list(range(0, total - WINDOW_SIZE + 1, HOP_SIZE))
    if starts and starts[-1] + WINDOW_SIZE < total:
        starts.append(total - WINDOW_SIZE)
    with torch.no_grad():
        for s in starts:
            x = torch.from_numpy(audio[s:s+WINDOW_SIZE]).float().unsqueeze(0).unsqueeze(0).to(device)
            pred = model(x).squeeze().cpu().numpy()
            out[s:s+WINDOW_SIZE] += pred
            cnt[s:s+WINDOW_SIZE] += 1.0
    return out / np.maximum(cnt, 1e-8)


def _cq_frame(egg: np.ndarray, i: int) -> float:
    frame_len = HOP * 2
    s = i * HOP
    frame = egg[s:s+frame_len] if s+frame_len <= len(egg) else egg[s:]
    if len(frame) == 0: return np.nan
    return float((frame > 0).sum() / len(frame))


def _cpp_frame(audio: np.ndarray, i: int) -> float:
    s = i * HOP
    raw = audio[s:s+N_FFT]
    if len(raw) < N_FFT:
        padded = np.zeros(N_FFT, dtype=np.float32)
        padded[:len(raw)] = raw
        raw = padded
    frame = raw * np.hanning(N_FFT)
    if np.abs(frame).max() < 1e-8: return np.nan
    spec = np.abs(np.fft.rfft(frame))
    log_spec = np.log(spec + 1e-10)
    cepstrum = np.fft.irfft(log_spec)
    q_min = int(TARGET_SR / F0_CEIL); q_max = min(int(TARGET_SR / F0_FLOOR), len(cepstrum)//2)
    if q_min >= q_max: return np.nan
    seg = cepstrum[q_min:q_max]
    pk_idx = np.argmax(seg)
    x = np.arange(len(seg), dtype=float)
    coeff = np.polyfit(x, seg, 1) if len(x) > 2 else [0, seg.mean()]
    return float(seg[pk_idx] - np.polyval(coeff, x[pk_idx]))


def _spectral_tilt(S_mag: np.ndarray, frame_idx: int) -> float:
    freqs = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
    col = S_mag[:, frame_idx]
    log_mag = np.log10(col + 1e-10)
    valid = freqs > 0
    coeff = np.polyfit(np.log10(freqs[valid]), log_mag[valid], 1) if valid.sum() > 2 else [0, 0]
    return float(coeff[0])


def _h1_h2(audio: np.ndarray, i: int, f0: float) -> float:
    s = i * HOP
    raw = audio[s:s+N_FFT]
    if len(raw) < N_FFT:
        padded = np.zeros(N_FFT, dtype=np.float32); padded[:len(raw)] = raw; raw = padded
    frame = raw * np.hanning(N_FFT)
    spec_db = 20 * np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
    freqs = np.fft.rfftfreq(N_FFT, 1.0/TARGET_SR)
    sr_bin = TARGET_SR / N_FFT
    h1i = int(f0/sr_bin); h1r = max(1, int(100/sr_bin))
    h2i = int(2*f0/sr_bin)
    h1 = spec_db[max(0, h1i-h1r):h1i+h1r+1]
    h2 = spec_db[max(0, h2i-h1r):h2i+h1r+1]
    return float(h1.max() - h2.max()) if len(h1) > 0 and len(h2) > 0 else np.nan


def _aggregate(vals):
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) == 0: return None, None
    return float(arr.mean()), float(np.percentile(arr, 90))


def _safe_mean(vals):
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    return float(arr.mean()) if len(arr) > 0 else None


def _reg_for_frame(f0: float, boundaries: dict) -> Optional[str]:
    if f0 <= 0: return None
    if f0 <= boundaries["low_max"]: return "low"
    if f0 <= boundaries["mid_max"]: return "mid"
    return "high"


def _apply_mapping(ai_val: float, mapping: dict) -> Optional[float]:
    """Apply learned threshold mapping to get 0~5 score."""
    thresh = mapping.get("thresholds", {})
    if not thresh: return None
    vals = [float(thresh[str(i)]) for i in range(6)]
    scores = list(range(6))
    increasing = vals[-1] > vals[0]
    if increasing:
        if ai_val <= vals[0]: return 0.0
        if ai_val >= vals[-1]: return 5.0
        for i in range(5):
            if vals[i] <= ai_val <= vals[i+1]:
                frac = (ai_val - vals[i]) / (vals[i+1] - vals[i] + 1e-10)
                return float(i) + frac
    else:
        if ai_val >= vals[0]: return 0.0
        if ai_val <= vals[-1]: return 5.0
        for i in range(5):
            if vals[i] >= ai_val >= vals[i+1]:
                frac = (vals[i] - ai_val) / (vals[i] - vals[i+1] + 1e-10)
                return float(i) + frac
    diffs = [abs(ai_val - v) for v in vals]
    return float(np.argmin(diffs))


def _score_to_zone(score: Optional[float]) -> Optional[str]:
    if score is None: return None
    s = round(score)
    if s <= 1: return "insufficient"
    if s <= 3: return "appropriate"
    return "excessive"


# ── Main pipeline class ────────────────────────────────────────────

class AnalysisPipeline:
    """
    Holds all heavy state (EGG model, criteria, mappings).
    Instantiate once at server startup, call analyze() per request.
    """

    def __init__(self, checkpoint_path: str, criteria_path: str, mappings_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # EGG model
        self.model = build_efficient_model(EXP20_CONFIG)
        ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device).eval()
        self._val_corr = ckpt.get("val_corr")

        # Criteria (evaluation rubric v3)
        with open(criteria_path, encoding="utf-8") as f:
            self.criteria = json.load(f)

        # Learned score mappings
        with open(mappings_path, encoding="utf-8") as f:
            ai_scores_data = json.load(f)
        self.mappings: dict = ai_scores_data.get("mappings", {})

        # csv_col → criteria_key → mapping
        self._col_mapping: dict = {}
        for csv_col, crit_key in CSV_TO_CRITERIA.items():
            self._col_mapping[crit_key] = self.mappings.get(csv_col)

        # ai_source per criteria_key
        self._ai_source: dict = {
            crit_key: self.criteria.get("items", {}).get(crit_key, {}).get("ai_source")
            for crit_key in CRITERIA_KEYS
        }

        print(
            f"[AnalysisPipeline] Ready: device={self.device}, val_corr={self._val_corr}, "
            f"params={sum(p.numel() for p in self.model.parameters()):,}"
        )

    def analyze(self, audio_data: bytes) -> dict:
        """
        Full analysis pipeline. Returns structured result dict.

        Raises:
            ValueError: audio too short (voiced < MIN_VOICED_S)
        """
        t0 = time.perf_counter()

        # 1) Load + preprocess
        audio, duration = _load_audio_bytes(audio_data)

        # 2) VAD
        vad_mask, f0_vals, f0_times = _generate_vad(audio)
        n_frames = len(vad_mask)
        voiced_frames = int(vad_mask.sum())
        voiced_s = voiced_frames * HOP / TARGET_SR
        voiced_ratio = voiced_frames / n_frames if n_frames > 0 else 0.0

        if voiced_s < MIN_VOICED_S:
            raise ValueError(
                f"Voiced audio too short: {voiced_s:.1f}s < {MIN_VOICED_S}s required"
            )

        # 3) Register boundaries
        boundaries = _split_registers(f0_vals)

        # 4) EGG inference
        egg_pred = _predict_egg(self.model, audio, self.device)

        # 5) STFT for spectral features
        S = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP)
        S_mag = np.abs(S)
        freqs = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
        centroid_arr = librosa.feature.spectral_centroid(S=S_mag, sr=TARGET_SR, n_fft=N_FFT)[0]
        mask_2k4k = (freqs >= 2000) & (freqs <= 4000)

        # Frame-level metrics
        frame_times = np.array([(i*HOP + HOP) / TARGET_SR for i in range(n_frames)])
        stft_n = S_mag.shape[1]

        # Per-register accumulators
        reg_data: dict = {r: {k: [] for k in [
            "cq_mean","cq_peak","cpp","hnr","spectral_centroid",
            "spectral_tilt","h1_h2","singers_formant_ratio","a1_p0"
        ]} for r in ["low","mid","high"]}

        # HNR via parselmouth (compute globally)
        snd_raw = parselmouth.Sound(audio, sampling_frequency=TARGET_SR)
        try:
            harm = call(snd_raw, "To Harmonicity (cc)", 0.01, F0_FLOOR, 0.1, 1.0)
            n_h = call(harm, "Get number of frames")
            hnr_vals_arr = np.array([
                call(harm, "Get value in frame", i)
                for i in range(1, n_h + 1)
            ])
            hnr_times_arr = np.array([
                call(harm, "Get time from frame number", i)
                for i in range(1, n_h + 1)
            ])
            hnr_vals_arr = np.where(np.isnan(hnr_vals_arr), np.nan, hnr_vals_arr)
        except Exception:
            hnr_vals_arr = np.array([]); hnr_times_arr = np.array([])

        # A1-P0 (single global value, replicated per voiced frame)
        try:
            formant = call(snd_raw, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
            n_f = call(formant, "Get number of frames")
            a1p0_list = []
            window_h = np.hanning(N_FFT)
            fqs_rfft = np.fft.rfftfreq(N_FFT, 1.0/TARGET_SR)
            sr_bin = TARGET_SR / N_FFT
            for ii in range(1, n_f + 1):
                t = call(formant, "Get time from frame number", ii)
                f1 = call(formant, "Get value at time", 1, t, "Hertz", "Linear")
                if not (f1 == f1) or f1 <= 0: continue
                fi = int(t * TARGET_SR) - N_FFT//2
                if fi < 0 or fi + N_FFT > len(audio): continue
                frame = audio[fi:fi+N_FFT] * window_h
                spec_db = 20*np.log10(np.abs(np.fft.rfft(frame)) + 1e-10)
                f1_idx = int(f1/sr_bin); f1r = max(1, int(100/sr_bin))
                p0_idx = int(250/sr_bin); p0r = max(1, int(50/sr_bin))
                a1 = spec_db[max(0,f1_idx-f1r):f1_idx+f1r+1].max()
                p0 = spec_db[max(0,p0_idx-p0r):p0_idx+p0r+1].max()
                a1p0_list.append(a1 - p0)
            a1_p0_global = float(np.mean(a1p0_list)) if a1p0_list else None
        except Exception:
            a1_p0_global = None

        # Per-frame loop
        for i, t in enumerate(frame_times):
            if i >= len(vad_mask) or not vad_mask[i]: continue
            fi_f0 = np.argmin(np.abs(f0_times - t))
            f0 = f0_vals[fi_f0]
            reg = _reg_for_frame(f0, boundaries)
            if reg is None: continue

            cq = _cq_frame(egg_pred, i)
            cpp_v = _cpp_frame(audio, i)

            si = min(int(t * TARGET_SR / HOP), stft_n - 1)
            tilt = _spectral_tilt(S_mag, si)
            hh = _h1_h2(audio, i, f0) if f0 > 0 else np.nan
            sc = float(centroid_arr[si])

            # HNR
            if len(hnr_times_arr) > 0:
                hi = np.argmin(np.abs(hnr_times_arr - t))
                hnr_v = hnr_vals_arr[hi] if not np.isnan(hnr_vals_arr[hi]) else np.nan
            else:
                hnr_v = np.nan

            # Singer's formant
            total_e = (S_mag[:, si]**2).sum()
            sf_e = (S_mag[mask_2k4k, si]**2).sum()
            sfr = float(sf_e / (total_e + 1e-10))

            reg_data[reg]["cq_mean"].append(cq)
            reg_data[reg]["cq_peak"].append(cq)
            reg_data[reg]["cpp"].append(cpp_v)
            reg_data[reg]["spectral_centroid"].append(sc)
            reg_data[reg]["spectral_tilt"].append(tilt)
            reg_data[reg]["h1_h2"].append(hh)
            reg_data[reg]["singers_formant_ratio"].append(sfr)
            if not np.isnan(hnr_v): reg_data[reg]["hnr"].append(hnr_v)
            if a1_p0_global is not None: reg_data[reg]["a1_p0"].append(a1_p0_global)

        # Aggregate per register
        def reg_stats(reg: str) -> dict:
            d = reg_data[reg]
            cq_m, cq_p = _aggregate(d["cq_mean"])
            cpp_m, _ = _aggregate(d["cpp"])
            hnr_m, _ = _aggregate(d["hnr"])
            sc_m, _ = _aggregate(d["spectral_centroid"])
            tilt_m, _ = _aggregate(d["spectral_tilt"])
            h1h2_m, _ = _aggregate(d["h1_h2"])
            sfr_m, _ = _aggregate(d["singers_formant_ratio"])
            a1p0_m, _ = _aggregate(d["a1_p0"])
            return {
                "n_frames": len(d["cq_mean"]),
                "cq_mean": cq_m, "cq_peak": cq_p, "cpp": cpp_m, "hnr": hnr_m,
                "spectral_centroid": sc_m, "spectral_tilt": tilt_m,
                "h1_h2": h1h2_m, "singers_formant_ratio": sfr_m, "a1_p0": a1p0_m,
            }

        registers = {r: reg_stats(r) for r in ["low","mid","high"]}

        # Global indicators (all voiced)
        all_cq = sum((reg_data[r]["cq_mean"] for r in ["low","mid","high"]), [])
        global_cq_m, global_cq_p = _aggregate(all_cq)
        all_cpp = sum((reg_data[r]["cpp"] for r in ["low","mid","high"]), [])
        all_hnr = sum((reg_data[r]["hnr"] for r in ["low","mid","high"]), [])
        all_sc  = sum((reg_data[r]["spectral_centroid"] for r in ["low","mid","high"]), [])
        all_tilt = sum((reg_data[r]["spectral_tilt"] for r in ["low","mid","high"]), [])
        all_h1h2 = sum((reg_data[r]["h1_h2"] for r in ["low","mid","high"]), [])
        all_sfr  = sum((reg_data[r]["singers_formant_ratio"] for r in ["low","mid","high"]), [])

        indicators = {
            "cq_mean": global_cq_m, "cq_peak": global_cq_p,
            "cpp_mean": _safe_mean(all_cpp), "hnr_mean": _safe_mean(all_hnr),
            "spectral_centroid_mean": _safe_mean(all_sc),
            "spectral_tilt_mean": _safe_mean(all_tilt),
            "h1_h2_mean": _safe_mean(all_h1h2),
            "singers_formant_ratio_mean": _safe_mean(all_sfr),
            "a1_p0_mean": a1_p0_global,
            "nasal_ratio": None,  # unavailable without nasal mic
        }

        # 8) Score mapping: use "all" register metrics for integration
        # Map each csv_col → ai indicator value
        def _get_indicator_val(csv_col: str) -> Optional[float]:
            if csv_col == "비강사용":   return None
            if csv_col == "흉성두성":   return global_cq_m
            if csv_col == "접촉강도":   return global_cq_p
            if csv_col == "호흡식별":   return indicators["cpp_mean"]
            if csv_col == "전방공명":   return indicators["spectral_centroid_mean"]
            if csv_col == "연구개위치":  return None
            if csv_col == "공명개방":   return None
            if csv_col == "혀경직도":   return None
            if csv_col == "상압하압":   return indicators["spectral_tilt_mean"]
            return None

        scores: dict = {}
        feedback: dict = {}

        for csv_col, crit_key in CSV_TO_CRITERIA.items():
            ai_val = _get_indicator_val(csv_col)
            mapping = self.mappings.get(csv_col)
            ci = self.criteria.get("items", {}).get(crit_key, {})
            ai_src = ci.get("ai_source")

            # Score
            if ai_val is not None and mapping and mapping.get("method") != "skip":
                ai_score = _apply_mapping(ai_val, mapping)
                rounded = min(5, max(0, round(ai_score))) if ai_score is not None else None
            else:
                ai_score = None
                rounded = None

            zone = _score_to_zone(ai_score)
            conf = (
                "high" if crit_key in HIGH_RELIABILITY else
                "medium" if crit_key in MEDIUM_RELIABILITY else
                "unavailable"
            )
            scores[crit_key] = {
                "ai_score": round(ai_score, 2) if ai_score is not None else None,
                "rounded_score": rounded,
                "zone": zone,
                "confidence": conf,
            }

            # Feedback
            score_desc = ci.get("scores", {}).get(str(rounded), {}).get("description", "") if rounded is not None else ""
            fb_text = ci.get("feedback_rules", {}).get(zone, "") if zone else "AI 측정 불가"
            zone_label = {"insufficient":"미달","appropriate":"적절","excessive":"과함"}.get(zone or "", "")
            feedback[crit_key] = {
                "name_ko": ci.get("name_ko", csv_col),
                "ai_score": round(ai_score, 2) if ai_score is not None else None,
                "score_description": score_desc,
                "feedback_text": fb_text,
                "zone": zone,
                "zone_label": zone_label,
                "ai_indicator": {
                    "name": ai_src,
                    "value": round(ai_val, 4) if ai_val is not None else None,
                },
            }

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "processing_time_ms": round(elapsed_ms, 1),
            "audio_info": {
                "duration_s": round(duration, 2),
                "sample_rate": TARGET_SR,
                "voiced_ratio": round(voiced_ratio, 4),
                "voiced_duration_s": round(voiced_s, 2),
                "f0_min": boundaries.get("f0_min"),
                "f0_max": boundaries.get("f0_max"),
                "f0_mean": boundaries.get("f0_mean"),
            },
            "register_boundaries": {
                "low_max": boundaries["low_max"],
                "mid_max": boundaries["mid_max"],
            },
            "registers": registers,
            "indicators": indicators,
            "scores": scores,
            "feedback": feedback,
            "reliability": {
                "high_reliability": HIGH_RELIABILITY,
                "medium_reliability": MEDIUM_RELIABILITY,
                "unavailable": UNAVAILABLE,
            },
        }
