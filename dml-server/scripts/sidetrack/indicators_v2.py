"""
indicators_v2.py — Step B1-A: 9항목 신규 indicator 산출 함수 모음

설계:
  - 함수 시그니처: compute_X(audio, sr, snd=None, **kwargs) → Optional[float]
    audio  : float32 numpy array
    sr     : sample rate (16kHz 표준)
    snd    : parselmouth Sound 객체 (재사용용 cache)
  - nan/inf 처리: voiced frame 부족/0 division → None 반환 (CSV 저장 시 빈 셀)
  - file-level value (1 file → 1 value per indicator), register는 long-format CSV에서 "all_voiced"로 통일

산출 indicator 목록 (15+ functions):
  HNR / h1_h2 / h1_a1 / h1_a3
  F1 / F2 / F3 / F1_bw / F2_bw / F3_bw
  jitter_local / jitter_rap / shimmer_local / shimmer_apq3
  spectral_flatness (5 bands)
  sub_band_energy_ratio (low/mid/high)
  anti_formant_depth_250_500 / anti_formant_depth_500_800
  F2_F1_ratio / F2_F1_distance
  F2_stability / spectral_entropy
  f0_std / f0_range
  spectral_centroid_variability / formant_transition_speed
  a1_p0 / singers_formant_ratio
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import parselmouth
from parselmouth.praat import call

TARGET_SR  = 16000
F0_FLOOR   = 75
F0_CEIL    = 600
N_FFT      = 1024
HOP        = 256


# ── 공용: parselmouth Sound 캐싱 + safe call ────────────────────────

def make_sound(audio: np.ndarray, sr: int = TARGET_SR) -> parselmouth.Sound:
    """parselmouth Sound 객체 생성 (캐시용)."""
    return parselmouth.Sound(audio.astype(np.float32), sampling_frequency=float(sr))


def _safe(val) -> Optional[float]:
    """nan/inf → None"""
    if val is None: return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v): return None
        return v
    except (ValueError, TypeError):
        return None


# ── HNR ─────────────────────────────────────────────────────────────

def compute_hnr(audio, sr, snd=None) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    try:
        h = snd.to_harmonicity_cc(time_step=0.01, minimum_pitch=F0_FLOOR,
                                   silence_threshold=0.1, periods_per_window=4.5)
        vals = h.values[h.values != -200]
        if len(vals) == 0: return None
        return _safe(np.mean(vals))
    except Exception:
        return None


# ── FFT 기반 spectral indicators ────────────────────────────────────

def _voiced_mask(audio, sr):
    """RMS+F0 VAD: voiced frame mask (HOP 단위)."""
    frame_len = HOP * 2
    n_frames = max(0, (len(audio) - frame_len) // HOP + 1)
    if n_frames == 0: return None, None
    rms = np.array([np.sqrt(np.mean(audio[i*HOP:i*HOP+frame_len]**2))
                    for i in range(n_frames)], dtype=np.float32)
    p90 = np.percentile(rms, 90)
    rms_mask = rms >= p90 * 0.10

    snd = make_sound(audio, sr)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    n_f0 = call(pitch, "Get number of frames")
    f0_vals = np.zeros(n_f0); f0_times = np.zeros(n_f0)
    for i in range(1, n_f0 + 1):
        t = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        f0_vals[i-1] = f if f == f else 0.0
        f0_times[i-1] = t

    frame_times = np.array([(i*HOP + frame_len/2) / sr for i in range(n_frames)])
    f0_for_frame = np.zeros(n_frames)
    f0_mask = np.zeros(n_frames, dtype=bool)
    for i, t in enumerate(frame_times):
        idx = np.argmin(np.abs(f0_times - t))
        f0_for_frame[i] = f0_vals[idx]
        f0_mask[i] = f0_vals[idx] > 0
    return rms_mask & f0_mask, f0_for_frame


def _fft_spectrum(audio, idx, hann=None):
    """frame i의 magnitude spectrum"""
    s = idx * HOP
    raw = audio[s:s+N_FFT]
    if len(raw) < N_FFT:
        padded = np.zeros(N_FFT, dtype=np.float32)
        padded[:len(raw)] = raw; raw = padded
    if hann is None: hann = np.hanning(N_FFT)
    return np.abs(np.fft.rfft(raw * hann))


def compute_h1_h2(audio, sr, snd=None) -> Optional[float]:
    """H1-H2 (dB): 첫 harmonic vs 두 번째 harmonic amplitude."""
    mask, f0_arr = _voiced_mask(audio, sr)
    if mask is None or mask.sum() == 0: return None
    hann = np.hanning(N_FFT); freqs = np.fft.rfftfreq(N_FFT, 1.0/sr)
    sr_bin = sr / N_FFT
    vals = []
    for i in np.where(mask)[0]:
        f0 = f0_arr[i]
        if f0 <= 0: continue
        spec = 20 * np.log10(_fft_spectrum(audio, i, hann) + 1e-10)
        h1_i = int(f0/sr_bin); h2_i = int(2*f0/sr_bin)
        r = max(1, int(50/sr_bin))
        h1 = spec[max(0,h1_i-r):h1_i+r+1]; h2 = spec[max(0,h2_i-r):h2_i+r+1]
        if len(h1)>0 and len(h2)>0:
            vals.append(h1.max() - h2.max())
    return _safe(np.mean(vals)) if vals else None


def compute_h1_a1(audio, sr, snd=None, f1_hz=None) -> Optional[float]:
    """H1-A1: 첫 harmonic vs F1 영역 amplitude."""
    if f1_hz is None: f1_hz = compute_F_freq(audio, sr, snd, 1)
    if f1_hz is None or f1_hz <= 0: return None
    mask, f0_arr = _voiced_mask(audio, sr)
    if mask is None or mask.sum()==0: return None
    hann = np.hanning(N_FFT); sr_bin = sr / N_FFT
    vals = []
    for i in np.where(mask)[0]:
        f0 = f0_arr[i]
        if f0 <= 0: continue
        spec = 20 * np.log10(_fft_spectrum(audio, i, hann) + 1e-10)
        h1_i = int(f0/sr_bin); a1_i = int(f1_hz/sr_bin)
        r = max(1, int(50/sr_bin))
        h1 = spec[max(0,h1_i-r):h1_i+r+1]; a1 = spec[max(0,a1_i-r):a1_i+r+1]
        if len(h1)>0 and len(a1)>0:
            vals.append(h1.max() - a1.max())
    return _safe(np.mean(vals)) if vals else None


def compute_h1_a3(audio, sr, snd=None, f3_hz=None) -> Optional[float]:
    if f3_hz is None: f3_hz = compute_F_freq(audio, sr, snd, 3)
    if f3_hz is None or f3_hz <= 0: return None
    mask, f0_arr = _voiced_mask(audio, sr)
    if mask is None or mask.sum()==0: return None
    hann = np.hanning(N_FFT); sr_bin = sr / N_FFT
    vals = []
    for i in np.where(mask)[0]:
        f0 = f0_arr[i]
        if f0 <= 0: continue
        spec = 20 * np.log10(_fft_spectrum(audio, i, hann) + 1e-10)
        h1_i = int(f0/sr_bin); a3_i = int(f3_hz/sr_bin)
        r = max(1, int(50/sr_bin))
        h1 = spec[max(0,h1_i-r):h1_i+r+1]; a3 = spec[max(0,a3_i-r):a3_i+r+1]
        if len(h1)>0 and len(a3)>0:
            vals.append(h1.max() - a3.max())
    return _safe(np.mean(vals)) if vals else None


# ── Formants ────────────────────────────────────────────────────────

def compute_F_freq(audio, sr, snd=None, formant_n: int = 1) -> Optional[float]:
    """formant_n (1/2/3) frequency mean over voiced frames."""
    snd = snd or make_sound(audio, sr)
    try:
        fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5,
                                  maximum_formant=5500, window_length=0.025)
        t_max = snd.get_total_duration()
        ts = np.arange(0, t_max, 0.01)
        vals = []
        for t in ts:
            v = call(fm, "Get value at time", formant_n, t, "Hertz", "Linear")
            if v == v:  # not nan
                vals.append(v)
        return _safe(np.mean(vals)) if vals else None
    except Exception:
        return None


def compute_F_bw(audio, sr, snd=None, formant_n: int = 1) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    try:
        fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5,
                                  maximum_formant=5500, window_length=0.025)
        t_max = snd.get_total_duration()
        ts = np.arange(0, t_max, 0.01)
        vals = []
        for t in ts:
            v = call(fm, "Get bandwidth at time", formant_n, t, "Hertz", "Linear")
            if v == v: vals.append(v)
        return _safe(np.mean(vals)) if vals else None
    except Exception:
        return None


# ── Jitter / Shimmer ────────────────────────────────────────────────

def _make_pitch_pp(audio, sr, snd=None):
    snd = snd or make_sound(audio, sr)
    try:
        pitch = call(snd, "To Pitch (cc)", 0.0, F0_FLOOR, 15, "no", 0.03,
                     0.45, 0.01, 0.35, 0.14, F0_CEIL)
        pp = call(snd, "To PointProcess (periodic, cc)", F0_FLOOR, F0_CEIL)
        return snd, pp
    except Exception:
        return None, None


def compute_jitter_local(audio, sr, snd=None) -> Optional[float]:
    _, pp = _make_pitch_pp(audio, sr, snd)
    if pp is None: return None
    try:
        return _safe(call(pp, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3))
    except Exception:
        return None


def compute_jitter_rap(audio, sr, snd=None) -> Optional[float]:
    _, pp = _make_pitch_pp(audio, sr, snd)
    if pp is None: return None
    try:
        return _safe(call(pp, "Get jitter (rap)", 0.0, 0.0, 0.0001, 0.02, 1.3))
    except Exception:
        return None


def compute_shimmer_local(audio, sr, snd=None) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    _, pp = _make_pitch_pp(audio, sr, snd)
    if pp is None: return None
    try:
        return _safe(call([snd, pp], "Get shimmer (local)", 0.0, 0.0,
                          0.0001, 0.02, 1.3, 1.6))
    except Exception:
        return None


def compute_shimmer_apq3(audio, sr, snd=None) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    _, pp = _make_pitch_pp(audio, sr, snd)
    if pp is None: return None
    try:
        return _safe(call([snd, pp], "Get shimmer (apq3)", 0.0, 0.0,
                          0.0001, 0.02, 1.3, 1.6))
    except Exception:
        return None


# ── Spectral flatness 5 bands ───────────────────────────────────────

def _spectral_flatness_band(audio, sr, low_hz, high_hz, mask=None):
    """band 안에서 spectral flatness = geometric mean / arithmetic mean."""
    mask_vals, _ = _voiced_mask(audio, sr) if mask is None else (mask, None)
    if mask_vals is None or mask_vals.sum()==0: return None
    sr_bin = sr / N_FFT
    lo_i = max(1, int(low_hz / sr_bin)); hi_i = min(N_FFT//2, int(high_hz / sr_bin))
    if lo_i >= hi_i: return None
    hann = np.hanning(N_FFT)
    flats = []
    for i in np.where(mask_vals)[0]:
        spec = _fft_spectrum(audio, i, hann)
        band = spec[lo_i:hi_i]
        band = band[band > 1e-10]
        if len(band) < 3: continue
        gm = np.exp(np.mean(np.log(band)))
        am = np.mean(band)
        if am > 1e-10:
            flats.append(gm / am)
    return _safe(np.mean(flats)) if flats else None


def compute_flatness_b1(audio, sr, snd=None) -> Optional[float]:  # 200-500
    return _spectral_flatness_band(audio, sr, 200, 500)
def compute_flatness_b2(audio, sr, snd=None) -> Optional[float]:  # 500-1000
    return _spectral_flatness_band(audio, sr, 500, 1000)
def compute_flatness_b3(audio, sr, snd=None) -> Optional[float]:  # 1000-2000
    return _spectral_flatness_band(audio, sr, 1000, 2000)
def compute_flatness_b4(audio, sr, snd=None) -> Optional[float]:  # 2000-4000
    return _spectral_flatness_band(audio, sr, 2000, 4000)
def compute_flatness_b5(audio, sr, snd=None) -> Optional[float]:  # 4000-8000
    return _spectral_flatness_band(audio, sr, 4000, 8000)


# ── Sub-band energy ratios ──────────────────────────────────────────

def _band_energy(audio, sr, low_hz, high_hz):
    mask_vals, _ = _voiced_mask(audio, sr)
    if mask_vals is None or mask_vals.sum()==0: return None
    sr_bin = sr / N_FFT
    lo_i = max(0, int(low_hz / sr_bin)); hi_i = min(N_FFT//2, int(high_hz / sr_bin))
    if lo_i >= hi_i: return None
    hann = np.hanning(N_FFT)
    energies = []
    for i in np.where(mask_vals)[0]:
        spec = _fft_spectrum(audio, i, hann)
        energies.append(np.sum(spec[lo_i:hi_i] ** 2))
    return _safe(np.mean(energies)) if energies else None


def compute_band_ratio_low_mid(audio, sr, snd=None) -> Optional[float]:
    low = _band_energy(audio, sr, 80, 1000)
    mid = _band_energy(audio, sr, 1000, 3000)
    if low is None or mid is None or mid < 1e-10: return None
    return _safe(low / mid)


def compute_band_ratio_high_mid(audio, sr, snd=None) -> Optional[float]:
    high = _band_energy(audio, sr, 3000, 8000)
    mid = _band_energy(audio, sr, 1000, 3000)
    if high is None or mid is None or mid < 1e-10: return None
    return _safe(high / mid)


# ── Anti-formant depth ──────────────────────────────────────────────

def _spectral_notch_depth(audio, sr, low_hz, high_hz, surround_hz=200):
    """band 내 최저점과 surround (band 외 양쪽 surround_hz)의 평균 차이 (dB)."""
    mask_vals, _ = _voiced_mask(audio, sr)
    if mask_vals is None or mask_vals.sum() == 0: return None
    sr_bin = sr / N_FFT
    lo_i = max(0, int(low_hz / sr_bin)); hi_i = min(N_FFT//2, int(high_hz / sr_bin))
    surr_pre_lo = max(0, int((low_hz - surround_hz) / sr_bin))
    surr_pre_hi = lo_i
    surr_post_lo = hi_i
    surr_post_hi = min(N_FFT//2, int((high_hz + surround_hz) / sr_bin))
    if lo_i >= hi_i or surr_pre_lo >= surr_pre_hi: return None
    hann = np.hanning(N_FFT)
    depths = []
    for i in np.where(mask_vals)[0]:
        spec_db = 20 * np.log10(_fft_spectrum(audio, i, hann) + 1e-10)
        notch = spec_db[lo_i:hi_i]
        surr = np.concatenate([spec_db[surr_pre_lo:surr_pre_hi], spec_db[surr_post_lo:surr_post_hi]])
        if len(notch) < 2 or len(surr) < 2: continue
        depths.append(surr.mean() - notch.min())
    return _safe(np.mean(depths)) if depths else None


def compute_anti_formant_250_500(audio, sr, snd=None) -> Optional[float]:
    return _spectral_notch_depth(audio, sr, 250, 500)
def compute_anti_formant_500_800(audio, sr, snd=None) -> Optional[float]:
    return _spectral_notch_depth(audio, sr, 500, 800)


# ── F2/F1 derived + stability ───────────────────────────────────────

def compute_F2_F1_ratio(audio, sr, snd=None) -> Optional[float]:
    f1 = compute_F_freq(audio, sr, snd, 1); f2 = compute_F_freq(audio, sr, snd, 2)
    if not f1 or not f2 or f1 < 1: return None
    return _safe(f2 / f1)


def compute_F2_F1_distance(audio, sr, snd=None) -> Optional[float]:
    f1 = compute_F_freq(audio, sr, snd, 1); f2 = compute_F_freq(audio, sr, snd, 2)
    if not f1 or not f2: return None
    return _safe(f2 - f1)


def compute_F2_stability(audio, sr, snd=None) -> Optional[float]:
    """frame-wise F2의 std/mean."""
    snd = snd or make_sound(audio, sr)
    try:
        fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5,
                                  maximum_formant=5500, window_length=0.025)
        ts = np.arange(0, snd.get_total_duration(), 0.01)
        vals = []
        for t in ts:
            v = call(fm, "Get value at time", 2, t, "Hertz", "Linear")
            if v == v: vals.append(v)
        if len(vals) < 5: return None
        m = np.mean(vals); s = np.std(vals)
        if m < 1: return None
        return _safe(s / m)
    except Exception:
        return None


def compute_formant_transition_speed(audio, sr, snd=None) -> Optional[float]:
    """consecutive F2 frames Δ mean (Hz/frame)."""
    snd = snd or make_sound(audio, sr)
    try:
        fm = snd.to_formant_burg(time_step=0.01, max_number_of_formants=5,
                                  maximum_formant=5500, window_length=0.025)
        ts = np.arange(0, snd.get_total_duration(), 0.01)
        vals = []
        for t in ts:
            v = call(fm, "Get value at time", 2, t, "Hertz", "Linear")
            vals.append(v if v==v else np.nan)
        arr = np.array(vals)
        diffs = np.abs(np.diff(arr))
        diffs = diffs[~np.isnan(diffs)]
        if len(diffs) < 3: return None
        return _safe(np.mean(diffs))
    except Exception:
        return None


# ── Spectral entropy + centroid variability ─────────────────────────

def compute_spectral_entropy(audio, sr, snd=None) -> Optional[float]:
    mask_vals, _ = _voiced_mask(audio, sr)
    if mask_vals is None or mask_vals.sum() == 0: return None
    hann = np.hanning(N_FFT)
    entropies = []
    for i in np.where(mask_vals)[0]:
        spec = _fft_spectrum(audio, i, hann)
        p = spec / (spec.sum() + 1e-10)
        p = p[p > 1e-10]
        H = -np.sum(p * np.log2(p))
        entropies.append(H)
    return _safe(np.mean(entropies)) if entropies else None


def compute_spectral_centroid_variability(audio, sr, snd=None) -> Optional[float]:
    """frame-wise spectral centroid std."""
    mask_vals, _ = _voiced_mask(audio, sr)
    if mask_vals is None or mask_vals.sum() == 0: return None
    hann = np.hanning(N_FFT)
    freqs = np.fft.rfftfreq(N_FFT, 1.0/sr)
    centroids = []
    for i in np.where(mask_vals)[0]:
        spec = _fft_spectrum(audio, i, hann)
        total = spec.sum()
        if total > 1e-10:
            centroids.append(np.sum(freqs * spec) / total)
    if len(centroids) < 5: return None
    return _safe(np.std(centroids))


# ── F0 stability ────────────────────────────────────────────────────

def compute_f0_std(audio, sr, snd=None) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    try:
        pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
        n = call(pitch, "Get number of frames")
        vals = []
        for i in range(1, n+1):
            f = call(pitch, "Get value in frame", i, "Hertz")
            if f == f and f > 0: vals.append(f)
        if len(vals) < 5: return None
        return _safe(np.std(vals))
    except Exception:
        return None


def compute_f0_range(audio, sr, snd=None) -> Optional[float]:
    snd = snd or make_sound(audio, sr)
    try:
        pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
        n = call(pitch, "Get number of frames")
        vals = []
        for i in range(1, n+1):
            f = call(pitch, "Get value in frame", i, "Hertz")
            if f == f and f > 0: vals.append(f)
        if len(vals) < 5: return None
        return _safe(max(vals) - min(vals))
    except Exception:
        return None


# ── 기존 indicator 갱신: a1_p0, singers_formant_ratio ───────────────
# (이미 analysis_pipeline에 있지만 신규 산출 위해 일관성)

def compute_a1_p0(audio, sr, snd=None) -> Optional[float]:
    """A1 (F1 amplitude) - P0 (F0 amplitude). 기존 analysis_pipeline 함수 미러."""
    mask, f0_arr = _voiced_mask(audio, sr)
    if mask is None or mask.sum()==0: return None
    f1_hz = compute_F_freq(audio, sr, snd, 1)
    if f1_hz is None or f1_hz <= 0: return None
    hann = np.hanning(N_FFT); sr_bin = sr / N_FFT
    vals = []
    for i in np.where(mask)[0]:
        f0 = f0_arr[i]
        if f0 <= 0: continue
        spec = 20 * np.log10(_fft_spectrum(audio, i, hann) + 1e-10)
        p0_i = int(f0/sr_bin); a1_i = int(f1_hz/sr_bin)
        r = max(1, int(50/sr_bin))
        p0 = spec[max(0,p0_i-r):p0_i+r+1]; a1 = spec[max(0,a1_i-r):a1_i+r+1]
        if len(p0)>0 and len(a1)>0:
            vals.append(a1.max() - p0.max())
    return _safe(np.mean(vals)) if vals else None


def compute_singers_formant_ratio(audio, sr, snd=None) -> Optional[float]:
    """singers formant (2300~3500Hz) vs total spectral energy."""
    sf_energy = _band_energy(audio, sr, 2300, 3500)
    total = _band_energy(audio, sr, 0, sr//2)
    if sf_energy is None or total is None or total < 1e-10: return None
    return _safe(sf_energy / total)


# ── 마스터 함수: 모든 indicator 산출 ────────────────────────────────

INDICATORS = {
    "hnr":                  compute_hnr,
    "h1_h2":                compute_h1_h2,
    "h1_a1":                compute_h1_a1,
    "h1_a3":                compute_h1_a3,
    "F1":                   lambda a,s,sd: compute_F_freq(a,s,sd,1),
    "F2":                   lambda a,s,sd: compute_F_freq(a,s,sd,2),
    "F3":                   lambda a,s,sd: compute_F_freq(a,s,sd,3),
    "F1_bw":                lambda a,s,sd: compute_F_bw(a,s,sd,1),
    "F2_bw":                lambda a,s,sd: compute_F_bw(a,s,sd,2),
    "F3_bw":                lambda a,s,sd: compute_F_bw(a,s,sd,3),
    "jitter_local":         compute_jitter_local,
    "jitter_rap":           compute_jitter_rap,
    "shimmer_local":        compute_shimmer_local,
    "shimmer_apq3":         compute_shimmer_apq3,
    "flatness_b1_200_500":   compute_flatness_b1,
    "flatness_b2_500_1k":    compute_flatness_b2,
    "flatness_b3_1k_2k":     compute_flatness_b3,
    "flatness_b4_2k_4k":     compute_flatness_b4,
    "flatness_b5_4k_8k":     compute_flatness_b5,
    "band_ratio_low_mid":    compute_band_ratio_low_mid,
    "band_ratio_high_mid":   compute_band_ratio_high_mid,
    "anti_formant_250_500":  compute_anti_formant_250_500,
    "anti_formant_500_800":  compute_anti_formant_500_800,
    "F2_F1_ratio":           compute_F2_F1_ratio,
    "F2_F1_distance":        compute_F2_F1_distance,
    "F2_stability":          compute_F2_stability,
    "formant_transition_speed": compute_formant_transition_speed,
    "spectral_entropy":      compute_spectral_entropy,
    "spectral_centroid_variability": compute_spectral_centroid_variability,
    "f0_std":                compute_f0_std,
    "f0_range":              compute_f0_range,
    "a1_p0":                 compute_a1_p0,
    "singers_formant_ratio": compute_singers_formant_ratio,
}


def compute_all(audio: np.ndarray, sr: int = TARGET_SR) -> dict:
    """주어진 wav에서 모든 indicator 산출. nan은 None으로 반환."""
    snd = make_sound(audio, sr)
    out = {}
    for name, fn in INDICATORS.items():
        try:
            out[name] = fn(audio, sr, snd)
        except Exception:
            out[name] = None
    return out
