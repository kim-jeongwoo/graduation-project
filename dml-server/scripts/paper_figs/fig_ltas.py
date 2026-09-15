"""
fig_ltas.py — (h) SVD 테스트 화자 vs 학원 phone 채널 평균 LTAS
================================================================
도메인 간극 시각화. 양쪽 동일 전처리:
  16 kHz 리샘플 → z-score → Welch PSD (nperseg=1024, hann) → dB
집계: 파일 PSD → 화자별 평균 → 집단 평균 (화자 가중 동일).
  - SVD: seed=42 테스트 split 70화자 전체 파일 (speech 채널, .nsp)
  - 학원: singer_XX phone 채널 wav (실사용 입력, 19명)
"""
import sys
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dml-server" / "ai-model"))
sys.path.insert(0, str(Path(__file__).parent))
from utils.dataset import speaker_split  # noqa: E402
from utils.nsp_reader import find_paired_files, read_nsp  # noqa: E402
from style import CM_W, C_MEAS, C_PRED, apply_style, savefig  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

SR = 16000
NPERSEG = 1024


def psd_z(sig, sr_in):
    if sig.ndim > 1:
        sig = sig.mean(axis=1)
    if sr_in != SR:
        sig = librosa.resample(sig, orig_sr=sr_in, target_sr=SR)
    if sig.std() > 1e-8:
        sig = (sig - sig.mean()) / sig.std()
    f, p = welch(sig, fs=SR, window="hann", nperseg=NPERSEG)
    return f, p


def main():
    # ── SVD test speakers (speech 채널) ──
    pairs = find_paired_files(str(ROOT / "data/SVD_healthy"))
    all_speakers = sorted(set(p[2] for p in pairs))
    _tr, _va, test_sp = speaker_split(all_speakers, seed=42)
    by_spk: dict[str, list] = {}
    freqs = None
    for nsp_path, _egg, spk in pairs:
        if spk not in test_sp:
            continue
        try:
            sig, _ = read_nsp(nsp_path)
            f, p = psd_z(sig, 50000)
            freqs = f
            by_spk.setdefault(spk, []).append(p)
        except Exception:
            continue
    svd_spk_means = [np.mean(v, axis=0) for v in by_spk.values()]
    svd_ltas = np.mean(svd_spk_means, axis=0)
    n_svd = len(svd_spk_means)

    # ── 학원 phone 채널 ──
    by_singer: dict[str, list] = {}
    for wav in sorted(ROOT.glob("data/vocal_academy/singer_*/[0-9]*phone*.wav")):
        singer = wav.parent.name
        sig, sr_in = sf.read(wav, dtype="float32")
        _f, p = psd_z(sig, sr_in)
        by_singer.setdefault(singer, []).append(p)
    ac_spk_means = [np.mean(v, axis=0) for v in by_singer.values()]
    ac_ltas = np.mean(ac_spk_means, axis=0)
    n_ac = len(ac_spk_means)
    print(f"[n] SVD test speakers={n_svd}, academy phone singers={n_ac}")

    apply_style()
    fig, ax = plt.subplots(figsize=(CM_W, CM_W * 0.68))
    ax.plot(freqs, 10 * np.log10(svd_ltas + 1e-12), color=C_MEAS,
            label=f"SVD test ($n$ = {n_svd} speakers)")
    ax.plot(freqs, 10 * np.log10(ac_ltas + 1e-12), color=C_PRED,
            label=f"Academy phone ($n$ = {n_ac} singers)")
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel("Power spectral density (dB)")
    ax.set_xlim(0, 8000)
    ax.set_xticks([0, 2000, 4000, 6000, 8000])
    ax.set_xticklabels(["0", "2", "4", "6", "8"])
    ax.legend(loc="upper right", frameon=True, edgecolor="black",
              fancybox=False, framealpha=1).get_frame().set_linewidth(0.6)
    savefig(fig, "fig_ltas.png")


if __name__ == "__main__":
    main()
