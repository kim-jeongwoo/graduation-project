"""
s5a_direct_phone.py — 작업 5 전반부: phone 오디오에서 CPP / spectral_centroid /
spectral_tilt / singers_formant_ratio / a1_p0 를 **직접** 산출.

v1 파이프라인(extra_metrics.py, spectral_analysis.py)과 동일한 알고리즘·동일한 VAD 규칙을
그대로 재사용해, 학습시 사용된 oral 측정치(_sm)와 같은 척도가 되도록 한다.

대상:
  - 5/10 검증 21명 phone wav (validation_510/, control_pre_510/)
  - 학습 코호트 phone wav 29 unit (작업 6 용)
  - 학습 코호트 oral wav 24 unit (검산용 — extra_metrics.json 과 일치해야 함)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call

sys.path.insert(0, str(Path(__file__).parent))
from common import REDIAG, ROOT, VA

TARGET_SR, N_FFT, HOP, FRAME_LEN = 16000, 1024, 256, 512
F0_FLOOR, F0_CEIL = 75, 600


def load_audio(p):
    a, sr = sf.read(p, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != TARGET_SR:
        a = librosa.resample(a, orig_sr=sr, target_sr=TARGET_SR)
    return a


def vad_mask(audio, wav_path):
    """vad_preprocess.generate_vad_mask 와 동일 (RMS p90*0.10 ∧ F0>0)."""
    n = max(0, (len(audio) - FRAME_LEN) // HOP + 1)
    ft = np.array([(i * HOP + FRAME_LEN / 2) / TARGET_SR for i in range(n)])
    rms = np.array([np.sqrt(np.mean(audio[i*HOP:i*HOP+FRAME_LEN] ** 2)) for i in range(n)],
                   dtype=np.float32)
    rmask = rms >= np.percentile(rms, 90) * 0.10
    snd = parselmouth.Sound(str(wav_path))
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    pitch = call(snd, "To Pitch", 0.0, F0_FLOOR, F0_CEIL)
    nf = call(pitch, "Get number of frames")
    fv = np.zeros(nf); ft0 = np.zeros(nf)
    for i in range(1, nf + 1):
        ft0[i-1] = call(pitch, "Get time from frame number", i)
        f = call(pitch, "Get value in frame", i, "Hertz")
        fv[i-1] = f if f == f else 0.0
    fmask = np.zeros(n, dtype=bool)
    for i, t in enumerate(ft):
        if len(ft0):
            fmask[i] = fv[np.argmin(np.abs(ft0 - t))] > 0
    return rmask & fmask


def compute_cpp(audio, m):
    """extra_metrics.compute_cpp 동일."""
    n = max(0, (len(audio) - N_FFT) // HOP + 1)
    w = np.hanning(N_FFT); out = []
    qmin, qmax = int(TARGET_SR / F0_CEIL), int(TARGET_SR / F0_FLOOR)
    for i in range(n):
        if m is not None and i < len(m) and not m[i]:
            continue
        fr = audio[i*HOP:i*HOP+N_FFT]
        if len(fr) < N_FFT or np.abs(fr).max() < 1e-8:
            continue
        cep = np.fft.irfft(np.log(np.abs(np.fft.rfft(fr * w)) + 1e-10))
        qm = min(qmax, len(cep) // 2)
        if qmin >= qm:
            continue
        seg = cep[qmin:qm]; pi = int(np.argmax(seg))
        x = np.arange(len(seg), dtype=float)
        base = np.polyval(np.polyfit(x, seg, 1), x[pi]) if len(x) > 2 else seg.mean()
        out.append(seg[pi] - base)
    return float(np.mean(out)) if out else None


def compute_centroid(audio, m):
    S = np.abs(librosa.stft(audio, n_fft=N_FFT, hop_length=HOP))
    c = librosa.feature.spectral_centroid(S=S, sr=TARGET_SR, n_fft=N_FFT)[0]
    v = [c[i] for i in range(len(c)) if m is None or i >= len(m) or m[i]]
    return float(np.mean(v)) if v else None


def compute_tilt_sfr(audio, m):
    """spectral_analysis.compute_spectral_tilt / compute_singers_formant_ratio 동일."""
    S = np.abs(librosa.stft(audio, n_fft=N_FFT, hop_length=HOP))
    fr = librosa.fft_frequencies(sr=TARGET_SR, n_fft=N_FFT)
    valid = fr > 0
    lf = np.log10(fr[valid]); lm = np.log10(S + 1e-10)
    nfm = S.shape[1]
    tilt = np.full(nfm, np.nan)
    for i in range(nfm):
        if S[:, i].max() < 1e-8:
            continue
        tilt[i] = np.polyfit(lf, lm[valid, i], 1)[0]
    tot = (S ** 2).sum(axis=0)
    band = (fr >= 2000) & (fr <= 4000)
    sfr = (S[band] ** 2).sum(axis=0) / (tot + 1e-10)
    sel = np.array([m[i] if (m is not None and i < len(m)) else True for i in range(nfm)])
    t = tilt[sel & np.isfinite(tilt)]; s = sfr[sel]
    return (float(t.mean()) if len(t) else None, float(s.mean()) if len(s) else None)


def compute_a1_p0(wav_path, m):
    """extra_metrics.compute_a1_p0 동일 (A1 - P0, P0 = 250Hz 부근)."""
    snd = parselmouth.Sound(str(wav_path))
    if snd.sampling_frequency != TARGET_SR:
        snd = snd.resample(TARGET_SR)
    fm = call(snd, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
    audio = snd.values[0]; w = np.hanning(N_FFT)
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / TARGET_SR)
    n = max(0, (len(audio) - N_FFT) // HOP + 1)
    out = []
    for i in range(n):
        if m is not None and i < len(m) and not m[i]:
            continue
        t = (i * HOP + N_FFT / 2) / TARGET_SR
        f1 = call(fm, "Get value at time", 1, t, "Hertz", "Linear")
        if f1 != f1 or f1 <= 0:
            continue
        spec = 20 * np.log10(np.abs(np.fft.rfft(audio[i*HOP:i*HOP+N_FFT] * w)) + 1e-10)
        a1 = spec[np.argmin(np.abs(freqs - f1))]
        p0 = spec[np.argmin(np.abs(freqs - 250.0))]
        out.append(a1 - p0)
    return float(np.mean(out)) if out else None


def analyse(wav_path, with_a1p0=True):
    a = load_audio(wav_path)
    m = vad_mask(a, wav_path)
    tilt, sfr = compute_tilt_sfr(a, m)
    return {"cpp": compute_cpp(a, m), "spectral_centroid": compute_centroid(a, m),
            "spectral_tilt": tilt, "singers_formant_ratio": sfr,
            "a1_p0": compute_a1_p0(wav_path, m) if with_a1p0 else None,
            "n_voiced_frames": int(m.sum()), "dur_s": round(len(a) / TARGET_SR, 2)}


def nfc(s):
    return unicodedata.normalize("NFC", s)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "val"
    out = {}
    if which == "val":
        files = {}
        for d in [VA / "validation_510", VA / "control_pre_510"]:
            for p in sorted(d.glob("*.wav")):
                sid = re.match(r"([AB]\d+)", nfc(p.name)).group(1)
                files[sid] = p
        print(f"5/10 phone wav {len(files)}개")
        for sid, p in sorted(files.items()):
            out[sid] = analyse(p)
            print(f"  {sid:4s} cpp={out[sid]['cpp']:.4f} centroid={out[sid]['spectral_centroid']:8.2f} "
                  f"tilt={out[sid]['spectral_tilt']:+.4f} sfr={out[sid]['singers_formant_ratio']:.5f} "
                  f"a1_p0={out[sid]['a1_p0']:+.3f}  ({out[sid]['dur_s']}s)", flush=True)
        (REDIAG / "s5a_direct_val510.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        chan = which          # 'oral' | 'phone'
        ps = sorted(VA.glob(f"singer_*/*_{chan}.wav"))
        print(f"training {chan} wav {len(ps)}개")
        for p in ps:
            m = re.match(r"(\d+)-(\d+)_", p.name)
            k = f"{int(m.group(1))}-{m.group(2)}"
            out[k] = analyse(p, with_a1p0=True)
            g = lambda n: ("None" if out[k][n] is None else f"{out[k][n]:.5f}")
            print(f"  {k:8s} cpp={g('cpp')} centroid={g('spectral_centroid')} "
                  f"tilt={g('spectral_tilt')} sfr={g('singers_formant_ratio')} "
                  f"a1_p0={g('a1_p0')}  nv={out[k]['n_voiced_frames']}", flush=True)
            (REDIAG / f"s5a_direct_train_{chan}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("done")
