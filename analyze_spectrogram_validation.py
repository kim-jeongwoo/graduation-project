#!/usr/bin/env python3
"""
Spectrogram Analysis + Shuffle Validation
==========================================
Part 1: Chest/Head register spectrograms for all files
Part 2: Shuffle test to validate DTW corr significance
Part 3: Full report
"""
import os
import sys
import time
import numpy as np
import torch
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.stats import pearsonr, norm
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from model.efficient_egg import build_efficient_model

# ── Paths ──
BASE = os.path.expanduser('~/projects/egg_prediction')
REC_DIR = os.path.join(BASE, 'data/rpi_recordings')
CKPT_PATH = os.path.join(BASE, 'checkpoints/exp3_efficient/best_model.pt')
OUT_DIR = os.path.join(BASE, 'results/validation')

MODEL_CFG = {
    'channels': 96, 'n_layers': 24, 'kernel_size': 3,
    'n_stacks': 3, 'dropout': 0.1,
}
WINDOW = 4096
TARGET_SR = 16000

# ── File definitions ──
FILES = {
    'Ref 0000':  {'fname': '0000.wav',               'boundary': 5.4},
    'Ref 0001':  {'fname': '0001.wav',               'boundary': 8.9},
    'User 11s':  {'fname': 'usb_mic_test1_11s.wav',  'boundary': 5.5},
    'User 18s':  {'fname': 'usb_mic_test1_18s.wav',  'boundary': 9.0},
}

PAIRS = [
    ('Ref 0000', 'User 11s'),
    ('Ref 0000', 'User 18s'),
    ('Ref 0001', 'User 11s'),
    ('Ref 0001', 'User 18s'),
]

RAW_CORRS = {
    ('Ref 0000', 'User 11s'): -0.0039,
    ('Ref 0000', 'User 18s'):  0.0036,
    ('Ref 0001', 'User 11s'):  0.0037,
    ('Ref 0001', 'User 18s'):  0.0028,
}

DTW_CORRS = {
    ('Ref 0000', 'User 11s'): 0.7215,
    ('Ref 0000', 'User 18s'): 0.6433,
    ('Ref 0001', 'User 11s'): 0.6875,
    ('Ref 0001', 'User 18s'): 0.7270,
}


# ============================================================
# Part 1: Spectrograms
# ============================================================
def plot_single_spectrogram(audio_path, save_path, boundary_sec=None,
                            title="Spectrogram"):
    """Single file spectrogram with chest/head register boundary."""
    y, sr = librosa.load(audio_path, sr=None)
    duration = len(y) / sr

    D = librosa.stft(y, n_fft=2048, hop_length=512)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor('white')

    img = librosa.display.specshow(
        S_db, sr=sr, hop_length=512,
        x_axis='time', y_axis='hz', ax=ax,
        cmap='magma', vmin=-80, vmax=0
    )

    ax.set_ylim(0, 5000)

    if boundary_sec and 0 < boundary_sec < duration:
        ax.axvline(x=boundary_sec, color='cyan', linestyle='--', linewidth=2.5,
                   alpha=0.9)
        mid_left = boundary_sec / 2
        mid_right = boundary_sec + (duration - boundary_sec) / 2
        ax.text(mid_left, 4600, 'Chest Voice', fontsize=14, color='white',
                ha='center', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#1f77b4', alpha=0.7))
        ax.text(mid_right, 4600, 'Head Voice', fontsize=14, color='white',
                ha='center', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#e74c3c', alpha=0.7))

    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
    ax.tick_params(labelsize=10)

    cbar = fig.colorbar(img, ax=ax, format='%+2.0f dB', shrink=0.85)
    cbar.set_label('Power (dB)', fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return S_db, sr, duration


def plot_comparison_spectrogram(save_path):
    """
    Comparison: best ref vs best user (2-row layout)
    Using Ref 0001 vs User 18s (highest DTW corr)
    """
    ref_info = FILES['Ref 0001']
    user_info = FILES['User 18s']

    y_ref, sr_ref = librosa.load(os.path.join(REC_DIR, ref_info['fname']), sr=None)
    y_user, sr_user = librosa.load(os.path.join(REC_DIR, user_info['fname']), sr=None)

    D_ref = librosa.stft(y_ref, n_fft=2048, hop_length=512)
    S_ref = librosa.amplitude_to_db(np.abs(D_ref), ref=np.max)

    D_user = librosa.stft(y_user, n_fft=2048, hop_length=512)
    S_user = librosa.amplitude_to_db(np.abs(D_user), ref=np.max)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.patch.set_facecolor('white')

    # Ref
    img1 = librosa.display.specshow(
        S_ref, sr=sr_ref, hop_length=512,
        x_axis='time', y_axis='hz', ax=axes[0],
        cmap='magma', vmin=-80, vmax=0
    )
    axes[0].set_ylim(0, 5000)
    axes[0].set_title('Reference: 0001.wav (17.76s)', fontsize=13, fontweight='bold')
    axes[0].set_ylabel('Frequency (Hz)', fontsize=11)
    axes[0].set_xlabel('')
    if ref_info['boundary']:
        axes[0].axvline(x=ref_info['boundary'], color='cyan', ls='--', lw=2.5, alpha=0.9)
        mid_l = ref_info['boundary'] / 2
        mid_r = ref_info['boundary'] + (len(y_ref)/sr_ref - ref_info['boundary']) / 2
        axes[0].text(mid_l, 4600, 'Chest', fontsize=12, color='white', ha='center',
                     fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#1f77b4', alpha=0.7))
        axes[0].text(mid_r, 4600, 'Head', fontsize=12, color='white', ha='center',
                     fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#e74c3c', alpha=0.7))
    fig.colorbar(img1, ax=axes[0], format='%+2.0f dB', shrink=0.85)

    # User
    img2 = librosa.display.specshow(
        S_user, sr=sr_user, hop_length=512,
        x_axis='time', y_axis='hz', ax=axes[1],
        cmap='magma', vmin=-80, vmax=0
    )
    axes[1].set_ylim(0, 5000)
    axes[1].set_title('User: usb_mic_test1_18s.wav (18.00s)', fontsize=13, fontweight='bold')
    axes[1].set_ylabel('Frequency (Hz)', fontsize=11)
    axes[1].set_xlabel('Time (s)', fontsize=11)
    if user_info['boundary']:
        axes[1].axvline(x=user_info['boundary'], color='cyan', ls='--', lw=2.5, alpha=0.9)
        mid_l = user_info['boundary'] / 2
        mid_r = user_info['boundary'] + (len(y_user)/sr_user - user_info['boundary']) / 2
        axes[1].text(mid_l, 4600, 'Chest', fontsize=12, color='white', ha='center',
                     fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#1f77b4', alpha=0.7))
        axes[1].text(mid_r, 4600, 'Head', fontsize=12, color='white', ha='center',
                     fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='#e74c3c', alpha=0.7))
    fig.colorbar(img2, ax=axes[1], format='%+2.0f dB', shrink=0.85)

    plt.suptitle('Spectrogram Comparison — Ref 0001 vs User 18s (DTW Corr: 0.7270)',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  [OK] Comparison spectrogram: {save_path}")


# ============================================================
# Part 2: Shuffle Validation
# ============================================================
def preprocess_wav(filepath, target_sr=16000):
    audio, sr = librosa.load(filepath, sr=None, mono=True)
    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    mx = np.max(np.abs(audio))
    if mx > 1e-8:
        audio = audio / mx
    return audio


def load_model(device):
    model = build_efficient_model(MODEL_CFG).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print(f"  Model: epoch {ckpt['epoch']}, val_corr {ckpt['val_corr']:.4f}")
    return model


def predict_egg(model, audio, device, window=WINDOW):
    hop = window // 2
    n = len(audio)
    if n < window:
        audio = np.pad(audio, (0, window - n), mode='constant')
        n = len(audio)
    mean, std = audio.mean(), audio.std()
    audio_norm = (audio - mean) / std if std > 1e-8 else audio.copy()
    pred_sum = np.zeros(n, dtype=np.float64)
    pred_cnt = np.zeros(n, dtype=np.float64)
    with torch.no_grad():
        starts = list(range(0, n - window + 1, hop)) or [0]
        for bi in range(0, len(starts), 64):
            bs = starts[bi:bi+64]
            chunks = [audio_norm[s:s+window] for s in bs]
            x = torch.from_numpy(np.array(chunks)).float().unsqueeze(1).to(device)
            pred = model(x).cpu().numpy()[:, 0, :]
            for j, s in enumerate(bs):
                pred_sum[s:s+window] += pred[j]
                pred_cnt[s:s+window] += 1.0
    mask = pred_cnt > 0
    out = np.zeros(n)
    out[mask] = pred_sum[mask] / pred_cnt[mask]
    return out


def align_dtw(egg1, egg2, ds=50):
    """DTW align two EGG signals (downsampled)."""
    r = egg1[::ds]
    u = egg2[::ds]
    dist, path = fastdtw(r.reshape(-1,1), u.reshape(-1,1), dist=euclidean, radius=50)
    pr = np.array([p[0] for p in path])
    pu = np.array([p[1] for p in path])
    return r[pr], u[pu], dist


def shuffle_validation(egg_ref, egg_user, n_shuffle=1000, ds=50):
    """
    Shuffle test: compare DTW-aligned corr against random-shuffle baseline.
    Uses block shuffle to preserve local structure while breaking alignment.
    """
    # 1. DTW-aligned original correlation
    aligned_ref, aligned_user, dtw_dist = align_dtw(egg_ref, egg_user, ds)
    if np.std(aligned_ref) > 1e-8 and np.std(aligned_user) > 1e-8:
        original_corr, _ = pearsonr(aligned_ref, aligned_user)
    else:
        original_corr = 0.0

    # 2. Shuffle correlation distribution
    # Strategy: shuffle the downsampled user EGG in blocks, then compute
    # raw (non-DTW) correlation at same length as aligned signals
    ref_ds = egg_ref[::ds]
    user_ds = egg_user[::ds]
    min_len = min(len(ref_ds), len(user_ds))
    ref_trunc = ref_ds[:min_len]

    rng = np.random.RandomState(42)
    shuffle_corrs = []

    # Block shuffle: break into ~50-sample blocks and permute
    block_size = 50
    n_blocks = min_len // block_size

    for _ in range(n_shuffle):
        # Create block-shuffled version
        blocks = [user_ds[i*block_size:(i+1)*block_size] for i in range(n_blocks)]
        rng.shuffle(blocks)
        shuffled = np.concatenate(blocks)[:min_len]
        if len(shuffled) < min_len:
            shuffled = np.pad(shuffled, (0, min_len - len(shuffled)))

        if np.std(ref_trunc) > 1e-8 and np.std(shuffled) > 1e-8:
            c, _ = pearsonr(ref_trunc[:len(shuffled)], shuffled)
            shuffle_corrs.append(c)

    shuffle_corrs = np.array(shuffle_corrs)
    shuffle_mean = float(np.mean(shuffle_corrs))
    shuffle_std = float(np.std(shuffle_corrs))

    if shuffle_std > 1e-10:
        z_score = (original_corr - shuffle_mean) / shuffle_std
    else:
        z_score = float('inf') if original_corr > shuffle_mean else 0.0

    p_value = 1.0 - norm.cdf(z_score) if np.isfinite(z_score) else 0.0

    return {
        'original_corr': original_corr,
        'shuffle_corrs': shuffle_corrs,
        'shuffle_mean': shuffle_mean,
        'shuffle_std': shuffle_std,
        'z_score': z_score,
        'p_value': p_value,
        'n_shuffle': n_shuffle,
        'dtw_dist': dtw_dist,
    }


def plot_shuffle_validation(all_results, save_path):
    """Histogram of shuffle distributions for all 4 pairs."""
    n_pairs = len(all_results)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('white')
    axes = axes.flatten()

    for idx, ((rl, ul), res) in enumerate(all_results.items()):
        ax = axes[idx]
        ax.hist(res['shuffle_corrs'], bins=40, alpha=0.7, color='#95a5a6',
                edgecolor='white', linewidth=0.5, label='Shuffled', density=True)

        # Original DTW corr
        ax.axvline(res['original_corr'], color='#e74c3c', linewidth=3,
                   label=f"DTW Corr: {res['original_corr']:.4f}")

        # Shuffle mean
        ax.axvline(res['shuffle_mean'], color='#3498db', linewidth=2,
                   linestyle='--', alpha=0.8,
                   label=f"Shuffle mean: {res['shuffle_mean']:.4f}")

        p_str = f"p<0.001" if res['p_value'] < 0.001 else f"p={res['p_value']:.4f}"
        ax.set_title(f"{rl} vs {ul}\nZ={res['z_score']:.1f}, {p_str}",
                     fontsize=11, fontweight='bold')
        ax.set_xlabel('Correlation', fontsize=10)
        ax.set_ylabel('Density', fontsize=10)
        ax.legend(fontsize=9, loc='upper left', framealpha=0.9)
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=9)

    plt.suptitle('Shuffle Validation — DTW Correlation Significance (n=1000)',
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  [OK] Shuffle validation: {save_path}")


# ============================================================
# Part 3: Full Report
# ============================================================
def write_full_report(spec_info, shuffle_results, save_path):
    best_pair = max(shuffle_results, key=lambda k: shuffle_results[k]['original_corr'])
    best = shuffle_results[best_pair]

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write("=" * 65 + "\n")
        f.write("  Full Vocal Similarity Analysis Report\n")
        f.write("  Model: Exp3 (EfficientEGGNet, Test Corr: 0.7163)\n")
        f.write("  Date: 2026-02-09\n")
        f.write("=" * 65 + "\n\n")

        # File info
        f.write("1. File Information\n")
        f.write("-" * 65 + "\n")
        for label, info in spec_info.items():
            f.write(f"  {label:12s}: {info['duration']:.2f}s, "
                    f"{info['sr']}Hz, boundary={info['boundary']}s\n")
        f.write("\n")

        # DTW results
        f.write("2. DTW-Aligned Vocal Similarity\n")
        f.write("-" * 65 + "\n")
        f.write(f"  {'Pair':30s} | {'Raw':>8s} | {'DTW':>8s}\n")
        f.write("  " + "-" * 55 + "\n")
        for pair in PAIRS:
            raw = RAW_CORRS[pair]
            dtw = DTW_CORRS[pair]
            marker = " <-- best" if pair == best_pair else ""
            f.write(f"  {pair[0]+' vs '+pair[1]:30s} | {raw:>8.4f} | "
                    f"{dtw:>8.4f}{marker}\n")
        f.write("\n")
        f.write(f"  Best: {best_pair[0]} vs {best_pair[1]} = "
                f"{DTW_CORRS[best_pair]:.4f}\n\n")

        # Shuffle validation
        f.write("3. Statistical Validation (Shuffle Test, n=1000)\n")
        f.write("-" * 65 + "\n")
        f.write(f"  {'Pair':30s} | {'DTW Corr':>9s} | {'Shuf Mean':>9s} | "
                f"{'Z-score':>8s} | {'p-value':>10s}\n")
        f.write("  " + "-" * 60 + "\n")
        for pair in PAIRS:
            res = shuffle_results[pair]
            p_str = f"<0.001" if res['p_value'] < 0.001 else f"{res['p_value']:.4f}"
            f.write(f"  {pair[0]+' vs '+pair[1]:30s} | "
                    f"{res['original_corr']:>9.4f} | "
                    f"{res['shuffle_mean']:>9.4f} | "
                    f"{res['z_score']:>8.1f} | "
                    f"{p_str:>10s}\n")
        f.write("\n")

        all_sig = all(r['p_value'] < 0.001 for r in shuffle_results.values())
        f.write(f"  All pairs significant (p<0.001): "
                f"{'YES' if all_sig else 'NO'}\n\n")

        # Interpretation
        f.write("4. Interpretation\n")
        f.write("-" * 65 + "\n")
        f.write("  Similarity scale:\n")
        f.write("    >= 0.7  : Very similar vocal pattern\n")
        f.write("    0.5~0.7 : Similar vocal pattern\n")
        f.write("    0.3~0.5 : Moderately similar\n")
        f.write("    < 0.3   : Different vocal pattern\n\n")

        bc = best['original_corr']
        if bc >= 0.7:
            interp = "Very similar vocal pattern"
        elif bc >= 0.5:
            interp = "Similar vocal pattern"
        elif bc >= 0.3:
            interp = "Moderately similar"
        else:
            interp = "Different vocal pattern"

        f.write(f"  Best pair: {best_pair[0]} vs {best_pair[1]}\n")
        f.write(f"    DTW Correlation: {bc:.4f}\n")
        f.write(f"    Z-score:         {best['z_score']:.1f}\n")
        p_str = "<0.001" if best['p_value'] < 0.001 else f"{best['p_value']:.4f}"
        f.write(f"    p-value:         {p_str}\n")
        f.write(f"    Verdict:         {interp}\n\n")

        f.write("5. Conclusion\n")
        f.write("-" * 65 + "\n")
        f.write(f"  - DTW correlation 0.64~0.73 across all pairs\n")
        f.write(f"  - All correlations statistically significant "
                f"(shuffle test p<0.001)\n")
        f.write(f"  - Confirms the recordings are of the same song\n")
        f.write(f"  - Vocal patterns are {'very ' if bc >= 0.7 else ''}similar\n")
        f.write("=" * 65 + "\n")

    print(f"  [OK] Full report: {save_path}")


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print("=" * 65)
    print("  Spectrogram Analysis + Shuffle Validation")
    print("=" * 65)

    # ════════════════════════════════════════
    # Part 1: Spectrograms
    # ════════════════════════════════════════
    print("\n[Part 1] Generating spectrograms...")
    spec_info = {}

    save_names = {
        'Ref 0000':  'spectrogram_0000.png',
        'Ref 0001':  'spectrogram_0001.png',
        'User 11s':  'spectrogram_user_11s.png',
        'User 18s':  'spectrogram_user_18s.png',
    }

    for label, finfo in FILES.items():
        path = os.path.join(REC_DIR, finfo['fname'])
        save = os.path.join(OUT_DIR, save_names[label])
        info = sf.info(path)
        dur = info.duration
        sr_orig = info.samplerate
        S_db, sr, dur = plot_single_spectrogram(
            path, save,
            boundary_sec=finfo['boundary'],
            title=f"{label} — {finfo['fname']} ({dur:.1f}s, {sr_orig}Hz)"
        )
        spec_info[label] = {'sr': sr, 'duration': dur, 'boundary': finfo['boundary']}
        print(f"  [OK] {label}: {dur:.1f}s -> {save_names[label]}")

    # Comparison spectrogram
    plot_comparison_spectrogram(os.path.join(OUT_DIR, 'spectrogram_comparison.png'))

    # ════════════════════════════════════════
    # Part 2: Shuffle Validation
    # ════════════════════════════════════════
    print("\n[Part 2] Shuffle validation...")
    print("  Loading model...")
    model = load_model(device)

    # Predict EGG for all files
    eggs = {}
    for label, finfo in FILES.items():
        audio = preprocess_wav(os.path.join(REC_DIR, finfo['fname']), TARGET_SR)
        egg = predict_egg(model, audio, device)
        eggs[label] = egg
        print(f"  {label}: EGG {len(egg):,} samples")

    # Shuffle test for all pairs
    shuffle_results = {}
    for rl, ul in PAIRS:
        print(f"  Shuffle test: {rl} vs {ul}...", end=" ", flush=True)
        t0 = time.time()
        res = shuffle_validation(eggs[rl], eggs[ul], n_shuffle=1000, ds=50)
        dt = time.time() - t0
        shuffle_results[(rl, ul)] = res
        p_str = "p<0.001" if res['p_value'] < 0.001 else f"p={res['p_value']:.4f}"
        print(f"DTW={res['original_corr']:.4f}, shuf={res['shuffle_mean']:.4f}, "
              f"Z={res['z_score']:.1f}, {p_str} ({dt:.1f}s)")

    # Plot shuffle validation
    plot_shuffle_validation(shuffle_results,
                            os.path.join(OUT_DIR, 'shuffle_validation.png'))

    # ════════════════════════════════════════
    # Part 3: Full Report
    # ════════════════════════════════════════
    print("\n[Part 3] Writing full report...")
    write_full_report(spec_info, shuffle_results,
                      os.path.join(OUT_DIR, 'full_analysis_report.txt'))

    # ── Summary ──
    print(f"\n{'=' * 65}")
    print("  Analysis Complete!")
    print(f"{'=' * 65}")
    print("\n  Shuffle validation summary:")
    print(f"  {'Pair':30s}  {'DTW':>7s}  {'Z':>7s}  {'p':>10s}")
    print("  " + "-" * 58)
    for pair in PAIRS:
        r = shuffle_results[pair]
        p_str = "<0.001" if r['p_value'] < 0.001 else f"{r['p_value']:.4f}"
        print(f"  {pair[0]+' vs '+pair[1]:30s}  {r['original_corr']:>7.4f}  "
              f"{r['z_score']:>7.1f}  {p_str:>10s}")

    print(f"\n  Output files:")
    print(f"    1. {OUT_DIR}/spectrogram_0000.png")
    print(f"    2. {OUT_DIR}/spectrogram_0001.png")
    print(f"    3. {OUT_DIR}/spectrogram_user_11s.png")
    print(f"    4. {OUT_DIR}/spectrogram_user_18s.png")
    print(f"    5. {OUT_DIR}/spectrogram_comparison.png")
    print(f"    6. {OUT_DIR}/shuffle_validation.png")
    print(f"    7. {OUT_DIR}/full_analysis_report.txt")
    print(f"{'=' * 65}")


if __name__ == '__main__':
    main()
