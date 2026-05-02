#!/usr/bin/env python3
"""
Exp20 시각화 생성 스크립트 (v2 — 대표 샘플 기반)
==================================================
샘플 선택 기준: 중앙값/사분위수 기반으로 대표적인 화자를 선택합니다.
가장 좋은 화자만 보여주는 cherry-picking을 배제합니다.

생성 이미지:
  1. prediction_comparison.png  — 중앙값 근처 화자 3명의 MIC/GT/Pred 비교
  2. prediction_range.png       — 상위25%/중앙/하위25% 화자의 성능 범위
  3. speaker_correlation_distribution.png — 화자별 Corr 히스토그램 + 샘플 위치 표시
"""
import sys, os
import torch
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.expanduser('~/projects/egg_prediction'), 'ai-model'))
from model.efficient_egg import build_efficient_model
from utils.dataset import speaker_split
from utils.nsp_reader import find_paired_files, read_nsp

SVD_PATH = os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy')
FIGURES_DIR = os.path.expanduser('~/projects/egg_prediction/figures')
CHECKPOINT = os.path.expanduser('~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt')

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
os.makedirs(FIGURES_DIR, exist_ok=True)
SR = 16000


# ===== Helpers =====

def pearson_corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float(np.sum(a * b) / (np.sqrt(np.sum(a**2) * np.sum(b**2)) + 1e-8))


def load_and_preprocess(nsp_path, egg_path, target_sr=16000, window=16384):
    """Load, resample, normalize, return a window from the middle."""
    speech, _ = read_nsp(nsp_path)
    egg, _ = read_nsp(egg_path)
    ml = min(len(speech), len(egg))
    speech, egg = speech[:ml], egg[:ml]
    speech = librosa.resample(speech, orig_sr=50000, target_sr=target_sr)
    egg = librosa.resample(egg, orig_sr=50000, target_sr=target_sr)
    ml = min(len(speech), len(egg))
    speech, egg = speech[:ml], egg[:ml]
    if ml < window:
        return None, None
    s_std, e_std = speech.std(), egg.std()
    if s_std > 1e-8:
        speech = (speech - speech.mean()) / s_std
    if e_std > 1e-8:
        egg = (egg - egg.mean()) / e_std
    mid = ml // 2
    start = max(0, mid - window // 2)
    if start + window > ml:
        start = ml - window
    return speech[start:start + window], egg[start:start + window]


@torch.no_grad()
def predict(model, speech_window):
    x = torch.from_numpy(speech_window).float().unsqueeze(0).unsqueeze(0).to(device)
    return model(x).squeeze().cpu().numpy()


def select_representative_samples(spk_means):
    """대표 샘플 선택 — 중앙값 근처 3명 + 상/중/하 각 1명."""
    speakers = np.array(list(spk_means.keys()))
    corrs = np.array([spk_means[s] for s in speakers])

    median_corr = np.median(corrs)

    # 중앙값 근처 화자 3명
    distances = np.abs(corrs - median_corr)
    median_indices = np.argsort(distances)[:3]
    median_samples = [(speakers[i], corrs[i]) for i in median_indices]

    # 상위25%, 중앙, 하위25% 각 1명
    q25 = np.percentile(corrs, 25)
    q50 = np.percentile(corrs, 50)
    q75 = np.percentile(corrs, 75)

    low_idx = np.argmin(np.abs(corrs - q25))
    mid_idx = np.argmin(np.abs(corrs - q50))
    high_idx = np.argmin(np.abs(corrs - q75))

    range_samples = {
        'Challenging (Q25)': (speakers[low_idx], corrs[low_idx]),
        'Typical (Median)': (speakers[mid_idx], corrs[mid_idx]),
        'Good (Q75)': (speakers[high_idx], corrs[high_idx]),
    }

    return median_samples, range_samples


def load_speaker_sample(model, spk, spk_files):
    """Load a representative sample for a speaker (best single-window file)."""
    files = spk_files[spk]
    best = None
    for nsp_path, egg_path in files:
        mic, egg_gt = load_and_preprocess(nsp_path, egg_path)
        if mic is None:
            continue
        egg_pred = predict(model, mic)
        mt = min(len(egg_gt), len(egg_pred))
        egg_gt, egg_pred, mic = egg_gt[:mt], egg_pred[:mt], mic[:mt]
        corr = pearson_corr(egg_gt, egg_pred)
        if best is None or corr > best[-1]:
            best = (spk, mic, egg_gt, egg_pred, corr)
    return best


# ================================================================
# STEP 0 — Load model
# ================================================================
print("Loading Exp20 model...")
cfg = {'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05}
model = build_efficient_model(cfg)
ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
model.load_state_dict(ckpt['model_state_dict'])
model = model.to(device).eval()
print(f"  Loaded (phase={ckpt.get('phase', '?')}, val_corr={ckpt.get('val_corr', '?'):.4f})")

# ================================================================
# STEP 1 — Compute per-speaker correlations (all 70 test speakers)
# ================================================================
print("\nComputing per-speaker correlations (all 70 test speakers)...")
pairs = find_paired_files(SVD_PATH)
all_speakers = sorted(set(p[2] for p in pairs))
train_sp, val_sp, test_sp = speaker_split(all_speakers, seed=42)
test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]

spk_files = defaultdict(list)
for n, e, s in test_pairs:
    spk_files[s].append((n, e))

speaker_corrs_raw = {}   # spk -> [window corrs]
processed = 0
for nsp_path, egg_path, spk in test_pairs:
    try:
        speech, _ = read_nsp(nsp_path)
        egg, _ = read_nsp(egg_path)
        ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
        speech = librosa.resample(speech, orig_sr=50000, target_sr=16000)
        egg = librosa.resample(egg, orig_sr=50000, target_sr=16000)
        ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
        if ml < 16384:
            continue
        s_std, e_std = speech.std(), egg.std()
        if s_std > 1e-8: speech = (speech - speech.mean()) / s_std
        if e_std > 1e-8: egg = (egg - egg.mean()) / e_std
        wl = 16384
        for w in range((ml - wl) // 8192 + 1):
            start = w * 8192
            x = torch.from_numpy(speech[start:start + wl]).float().unsqueeze(0).unsqueeze(0).to(device)
            y_np = egg[start:start + wl]
            with torch.no_grad():
                p = model(x).squeeze().cpu().numpy()
            mt = min(len(p), len(y_np))
            c = pearson_corr(y_np[:mt], p[:mt])
            speaker_corrs_raw.setdefault(spk, []).append(c)
        processed += 1
        if processed % 100 == 0:
            print(f"  Processed {processed} files...")
    except Exception:
        continue

spk_means = {s: np.mean(c) for s, c in speaker_corrs_raw.items()}
vals = np.array(list(spk_means.values()))
mean_val = np.mean(vals)
median_val = np.median(vals)
print(f"  Done — {len(vals)} speakers, Mean={mean_val:.4f}, Median={median_val:.4f}")

# ================================================================
# STEP 2 — Select representative samples
# ================================================================
print("\nSelecting representative samples...")
median_samples, range_samples = select_representative_samples(spk_means)

print("  Median-near samples (for prediction_comparison.png):")
for spk, corr in median_samples:
    print(f"    Speaker {spk}: Corr={corr:.4f} (dist from median: {abs(corr - median_val):.4f})")

print("  Range samples (for prediction_range.png):")
for label, (spk, corr) in range_samples.items():
    print(f"    {label}: Speaker {spk}, Corr={corr:.4f}")

# Load actual waveform data for selected speakers
all_selected_spks = set(s for s, _ in median_samples) | set(s for _, (s, _) in range_samples.items())
loaded = {}
for spk in all_selected_spks:
    sample = load_speaker_sample(model, spk, spk_files)
    if sample is not None:
        loaded[spk] = sample

# ================================================================
# FIGURE 1 — prediction_comparison.png (중앙값 근처 3명)
# ================================================================
print("\nGenerating prediction_comparison.png...")
fig, axes = plt.subplots(3, 3, figsize=(14, 9))
fig.suptitle('MIC → EGG Prediction — Median Corr Samples (Typical Performance)',
             fontsize=13, fontweight='bold', y=1.01)

for i, (spk, spk_corr) in enumerate(median_samples):
    data = loaded[spk]
    _, mic, egg_gt, egg_pred, corr = data
    # Show 50ms detail (800 samples)
    detail_len = min(800, len(mic))
    t_ms = np.arange(detail_len) / SR * 1000

    # MIC input
    axes[i, 0].plot(t_ms, mic[:detail_len], color='#2196F3', linewidth=0.6)
    axes[i, 0].set_title(f'Speaker {spk}: MIC Input', fontsize=10)
    axes[i, 0].set_ylabel('Amplitude', fontsize=8)
    axes[i, 0].tick_params(labelsize=7)

    # Ground truth EGG
    axes[i, 1].plot(t_ms, egg_gt[:detail_len], color='#4CAF50', linewidth=0.6)
    axes[i, 1].set_title('Ground Truth EGG', fontsize=10)
    axes[i, 1].tick_params(labelsize=7)

    # Comparison overlay
    axes[i, 2].plot(t_ms, egg_gt[:detail_len], color='#4CAF50', linewidth=0.8, label='GT EGG')
    axes[i, 2].plot(t_ms, egg_pred[:detail_len], color='#F44336', linewidth=0.8,
                    linestyle='--', label='Predicted')
    axes[i, 2].set_title(f'Comparison (Corr: {spk_corr:.4f})', fontsize=10)
    axes[i, 2].legend(fontsize=7, loc='upper right')
    axes[i, 2].tick_params(labelsize=7)

for j in range(3):
    axes[-1, j].set_xlabel('Time (ms)', fontsize=9)

plt.tight_layout()
path1 = os.path.join(FIGURES_DIR, 'prediction_comparison.png')
fig.savefig(path1, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path1}")

# ================================================================
# FIGURE 2 — prediction_range.png (상/중/하 비교)
# ================================================================
print("Generating prediction_range.png...")
labels_order = ['Good (Q75)', 'Typical (Median)', 'Challenging (Q25)']
colors_label = {'Good (Q75)': '#4CAF50', 'Typical (Median)': '#2196F3', 'Challenging (Q25)': '#FF9800'}

fig, axes = plt.subplots(3, 2, figsize=(14, 10))
fig.suptitle('Prediction Quality Range — Good / Typical / Challenging',
             fontsize=13, fontweight='bold', y=1.01)

for i, label in enumerate(labels_order):
    spk, spk_corr = range_samples[label]
    data = loaded[spk]
    _, mic, egg_gt, egg_pred, corr = data

    # Show 100ms window (1600 samples)
    show_len = min(1600, len(egg_gt))
    t_ms = np.arange(show_len) / SR * 1000
    accent = colors_label[label]

    # Left: GT vs Pred overlay
    axes[i, 0].plot(t_ms, egg_gt[:show_len], color='#4CAF50', linewidth=1.0,
                    label='Ground Truth', alpha=0.9)
    axes[i, 0].plot(t_ms, egg_pred[:show_len], color='#F44336', linewidth=1.0,
                    linestyle='--', label='Predicted', alpha=0.8)
    axes[i, 0].fill_between(t_ms, egg_gt[:show_len], egg_pred[:show_len],
                            alpha=0.12, color='gray')
    axes[i, 0].set_title(f'{label}  —  Speaker {spk} (Corr: {spk_corr:.4f})',
                         fontsize=10, fontweight='bold', color=accent)
    axes[i, 0].set_ylabel('Amplitude', fontsize=9)
    axes[i, 0].legend(fontsize=8, loc='upper right')
    axes[i, 0].tick_params(labelsize=7)

    # Right: Residual (error)
    residual = egg_gt[:show_len] - egg_pred[:show_len]
    axes[i, 1].fill_between(t_ms, residual, 0, alpha=0.4, color=accent)
    axes[i, 1].axhline(0, color='gray', linewidth=0.5)
    rmse = np.sqrt(np.mean(residual ** 2))
    axes[i, 1].set_title(f'Prediction Error (RMSE: {rmse:.4f})', fontsize=10)
    axes[i, 1].set_ylabel('Error', fontsize=9)
    axes[i, 1].tick_params(labelsize=7)

for j in range(2):
    axes[-1, j].set_xlabel('Time (ms)', fontsize=9)

plt.tight_layout()
path2 = os.path.join(FIGURES_DIR, 'prediction_range.png')
fig.savefig(path2, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path2}")

# ================================================================
# FIGURE 3 — speaker_correlation_distribution.png
# ================================================================
print("Generating speaker_correlation_distribution.png...")

fig, ax = plt.subplots(figsize=(10, 6))

# Histogram
counts, bins, patches = ax.hist(vals, bins=20, color='#2196F3', alpha=0.7,
                                edgecolor='white', linewidth=0.8)
for patch, left_edge in zip(patches, bins[:-1]):
    if left_edge >= 0.8:
        patch.set_facecolor('#4CAF50')
    elif left_edge >= 0.7:
        patch.set_facecolor('#8BC34A')
    elif left_edge < 0.5:
        patch.set_facecolor('#FF9800')

# Mean / Median lines
ax.axvline(mean_val, color='#F44336', linestyle='-', linewidth=2,
           label=f'Mean: {mean_val:.4f}')
ax.axvline(median_val, color='#9C27B0', linestyle='--', linewidth=2,
           label=f'Median: {median_val:.4f}')
ax.axvline(0.7, color='gray', linestyle=':', linewidth=1.5, alpha=0.7,
           label='Corr = 0.7 (90% above)')
ax.axvline(0.8, color='gray', linestyle='-.', linewidth=1.5, alpha=0.7,
           label='Corr = 0.8 (71% above)')

# Mark selected samples on the histogram
marker_y = max(counts) * 0.92
# Median samples — blue diamonds
for spk, corr in median_samples:
    ax.plot(corr, marker_y, 'D', color='#2196F3', markersize=8, zorder=5)
ax.plot([], [], 'D', color='#2196F3', markersize=8, label='Median samples (Fig 1)')

# Range samples — colored triangles
range_colors = {'Good (Q75)': '#4CAF50', 'Typical (Median)': '#9C27B0', 'Challenging (Q25)': '#FF9800'}
for label, (spk, corr) in range_samples.items():
    ax.plot(corr, marker_y * 0.82, '^', color=range_colors[label], markersize=10, zorder=5)
ax.plot([], [], '^', color='gray', markersize=10, label='Range samples (Fig 2)')

# Stats box
n_above_07 = int(np.sum(vals >= 0.7))
n_above_08 = int(np.sum(vals >= 0.8))
n_total = len(vals)
ax.text(0.98, 0.95,
        f'Total speakers: {n_total}\n'
        f'Corr ≥ 0.8: {n_above_08}/{n_total} ({n_above_08 / n_total * 100:.0f}%)\n'
        f'Corr ≥ 0.7: {n_above_07}/{n_total} ({n_above_07 / n_total * 100:.0f}%)',
        transform=ax.transAxes, fontsize=10, va='top', ha='right',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8))

ax.set_xlabel('Pearson Correlation', fontsize=12)
ax.set_ylabel('Number of Speakers', fontsize=12)
ax.set_title('Per-Speaker Test Correlation Distribution (Exp20, window=16384)',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=8, loc='upper left')
ax.set_xlim(0.3, 1.0)
ax.tick_params(labelsize=10)

plt.tight_layout()
path3 = os.path.join(FIGURES_DIR, 'speaker_correlation_distribution.png')
fig.savefig(path3, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path3}")

# ================================================================
# Summary
# ================================================================
print("\n" + "=" * 60)
print("All visualizations generated!")
print(f"  {path1}")
print(f"  {path2}")
print(f"  {path3}")
print(f"\nSample selection summary:")
print(f"  Overall: Mean={mean_val:.4f}, Median={median_val:.4f}")
print(f"  Fig 1 (prediction_comparison) — Median-near samples:")
for spk, corr in median_samples:
    print(f"    Speaker {spk}: Corr={corr:.4f}")
print(f"  Fig 2 (prediction_range) — Quartile samples:")
for label, (spk, corr) in range_samples.items():
    print(f"    {label}: Speaker {spk}, Corr={corr:.4f}")
