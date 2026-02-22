#!/usr/bin/env python3
"""
Exp20 시각화 생성 스크립트
- prediction_comparison.png: MIC / GT EGG / Predicted EGG 파형 비교
- egg_overlay.png: GT vs Predicted 오버레이
- speaker_correlation_distribution.png: 화자별 Correlation 분포
"""
import sys, os
import torch
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa

sys.path.insert(0, os.path.join(os.path.expanduser('~/projects/egg_prediction'), 'ai-model'))
from model.efficient_egg import build_efficient_model
from utils.dataset import speaker_split
from utils.nsp_reader import find_paired_files, read_nsp

SVD_PATH = os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy')
FIGURES_DIR = os.path.expanduser('~/projects/egg_prediction/figures')
CHECKPOINT = os.path.expanduser('~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt')

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
os.makedirs(FIGURES_DIR, exist_ok=True)

# ===== Helpers =====
def pearson_corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float(np.sum(a * b) / (np.sqrt(np.sum(a**2) * np.sum(b**2)) + 1e-8))

def load_and_preprocess(nsp_path, egg_path, target_sr=16000, window=16384):
    """Load, resample, normalize, and return windowed samples."""
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
    # Take a window from the middle of the file (more interesting content)
    mid = ml // 2
    start = max(0, mid - window // 2)
    if start + window > ml:
        start = ml - window
    return speech[start:start+window], egg[start:start+window]

@torch.no_grad()
def predict(model, speech_window):
    """Run model inference on a single window."""
    x = torch.from_numpy(speech_window).float().unsqueeze(0).unsqueeze(0).to(device)
    pred = model(x)
    return pred.squeeze().cpu().numpy()


# ===== Load model =====
print("Loading Exp20 model...")
cfg = {'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05}
model = build_efficient_model(cfg)
ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
model.load_state_dict(ckpt['model_state_dict'])
model = model.to(device).eval()
print(f"  Loaded (phase={ckpt.get('phase','?')}, val_corr={ckpt.get('val_corr','?'):.4f})")

# ===== Get test speakers & files =====
print("Finding test files...")
pairs = find_paired_files(SVD_PATH)
all_speakers = sorted(set(p[2] for p in pairs))
train_sp, val_sp, test_sp = speaker_split(all_speakers, seed=42)
test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]

# Group by speaker
from collections import defaultdict
spk_files = defaultdict(list)
for n, e, s in test_pairs:
    spk_files[s].append((n, e))

# Pick 5 diverse speakers (spread across sorted list for variety)
test_spk_sorted = sorted(test_sp)
step = max(1, len(test_spk_sorted) // 5)
selected_speakers = [test_spk_sorted[i * step] for i in range(5)]
print(f"  Selected speakers: {selected_speakers}")

# Load samples for selected speakers
samples = []  # (speaker_id, mic, egg_gt, egg_pred, corr)
for spk in selected_speakers:
    files = spk_files[spk]
    # Try to find a good file (long enough)
    for nsp_path, egg_path in files:
        mic, egg_gt = load_and_preprocess(nsp_path, egg_path)
        if mic is not None:
            egg_pred = predict(model, mic)
            # Trim to same length
            mt = min(len(egg_gt), len(egg_pred))
            egg_gt, egg_pred = egg_gt[:mt], egg_pred[:mt]
            mic = mic[:mt]
            corr = pearson_corr(egg_gt, egg_pred)
            samples.append((spk, mic, egg_gt, egg_pred, corr))
            break

print(f"  Loaded {len(samples)} samples")
for spk, _, _, _, corr in samples:
    print(f"    Speaker {spk}: Corr={corr:.4f}")


# ===== Figure 1: Prediction Comparison =====
print("\nGenerating prediction_comparison.png...")
n = len(samples)
fig, axes = plt.subplots(n, 3, figsize=(14, 3 * n))
fig.suptitle('MIC → EGG Prediction (Exp20, Test Corr: 0.8249)', fontsize=14, fontweight='bold', y=1.01)

# Time axis in ms
sr = 16000
for i, (spk, mic, egg_gt, egg_pred, corr) in enumerate(samples):
    t_ms = np.arange(len(mic)) / sr * 1000
    # Show a 50ms window for detail (800 samples at 16kHz)
    detail_len = min(800, len(mic))
    t_detail = t_ms[:detail_len]

    # MIC
    axes[i, 0].plot(t_detail, mic[:detail_len], color='#2196F3', linewidth=0.6)
    axes[i, 0].set_title(f'Speaker {spk}: MIC Input', fontsize=10)
    axes[i, 0].set_ylabel('Amplitude', fontsize=8)
    axes[i, 0].tick_params(labelsize=7)

    # GT EGG
    axes[i, 1].plot(t_detail, egg_gt[:detail_len], color='#4CAF50', linewidth=0.6)
    axes[i, 1].set_title(f'Ground Truth EGG', fontsize=10)
    axes[i, 1].tick_params(labelsize=7)

    # Comparison
    axes[i, 2].plot(t_detail, egg_gt[:detail_len], color='#4CAF50', linewidth=0.8, label='GT EGG')
    axes[i, 2].plot(t_detail, egg_pred[:detail_len], color='#F44336', linewidth=0.8, linestyle='--', label='Predicted')
    axes[i, 2].set_title(f'Comparison (Corr: {corr:.4f})', fontsize=10)
    axes[i, 2].legend(fontsize=7, loc='upper right')
    axes[i, 2].tick_params(labelsize=7)

# X labels on bottom row only
for j in range(3):
    axes[-1, j].set_xlabel('Time (ms)', fontsize=9)

plt.tight_layout()
path1 = os.path.join(FIGURES_DIR, 'prediction_comparison.png')
fig.savefig(path1, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path1}")


# ===== Figure 2: EGG Overlay =====
print("Generating egg_overlay.png...")
n_overlay = min(3, len(samples))
fig, axes = plt.subplots(n_overlay, 1, figsize=(14, 3.5 * n_overlay))
if n_overlay == 1:
    axes = [axes]
fig.suptitle('Ground Truth vs Predicted EGG Overlay', fontsize=14, fontweight='bold')

for i in range(n_overlay):
    spk, mic, egg_gt, egg_pred, corr = samples[i]
    # Show 100ms window (1600 samples)
    show_len = min(1600, len(egg_gt))
    t_ms = np.arange(show_len) / sr * 1000

    axes[i].plot(t_ms, egg_gt[:show_len], color='#4CAF50', linewidth=1.0,
                 label='Ground Truth', alpha=0.9)
    axes[i].plot(t_ms, egg_pred[:show_len], color='#F44336', linewidth=1.0,
                 linestyle='--', label='Predicted', alpha=0.8)
    axes[i].fill_between(t_ms, egg_gt[:show_len], egg_pred[:show_len],
                         alpha=0.1, color='gray')
    axes[i].set_title(f'Speaker {spk} (Corr: {corr:.4f})', fontsize=11)
    axes[i].set_ylabel('Amplitude', fontsize=9)
    axes[i].legend(fontsize=9, loc='upper right')
    axes[i].tick_params(labelsize=8)

axes[-1].set_xlabel('Time (ms)', fontsize=10)
plt.tight_layout()
path2 = os.path.join(FIGURES_DIR, 'egg_overlay.png')
fig.savefig(path2, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path2}")


# ===== Figure 3: Speaker Correlation Distribution =====
print("Generating speaker_correlation_distribution.png...")
print("  Computing per-speaker correlations (all 70 test speakers)...")
speaker_corrs = {}
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
            x = torch.from_numpy(speech[start:start+wl]).float().unsqueeze(0).unsqueeze(0).to(device)
            y_np = egg[start:start+wl]
            with torch.no_grad():
                p = model(x).squeeze().cpu().numpy()
            mt = min(len(p), len(y_np))
            c = pearson_corr(y_np[:mt], p[:mt])
            speaker_corrs.setdefault(spk, []).append(c)
        processed += 1
        if processed % 100 == 0:
            print(f"    Processed {processed} files...")
    except:
        continue

spk_means = {s: np.mean(c) for s, c in speaker_corrs.items()}
vals = np.array(list(spk_means.values()))
mean_val = np.mean(vals)
median_val = np.median(vals)

print(f"  Speakers: {len(vals)}, Mean={mean_val:.4f}, Median={median_val:.4f}")

fig, ax = plt.subplots(figsize=(10, 6))

# Histogram
counts, bins, patches = ax.hist(vals, bins=20, color='#2196F3', alpha=0.7,
                                 edgecolor='white', linewidth=0.8)
# Color bars by threshold
for patch, left_edge in zip(patches, bins[:-1]):
    if left_edge >= 0.8:
        patch.set_facecolor('#4CAF50')
    elif left_edge >= 0.7:
        patch.set_facecolor('#8BC34A')
    elif left_edge < 0.5:
        patch.set_facecolor('#FF9800')

# Vertical lines
ax.axvline(mean_val, color='#F44336', linestyle='-', linewidth=2,
           label=f'Mean: {mean_val:.4f}')
ax.axvline(median_val, color='#9C27B0', linestyle='--', linewidth=2,
           label=f'Median: {median_val:.4f}')
ax.axvline(0.7, color='gray', linestyle=':', linewidth=1.5, alpha=0.7,
           label='Corr = 0.7 (90% above)')
ax.axvline(0.8, color='gray', linestyle='-.', linewidth=1.5, alpha=0.7,
           label='Corr = 0.8 (71% above)')

# Annotations
n_above_07 = np.sum(vals >= 0.7)
n_above_08 = np.sum(vals >= 0.8)
n_total = len(vals)
ax.text(0.98, 0.95,
        f'Total speakers: {n_total}\n'
        f'Corr ≥ 0.8: {n_above_08}/{n_total} ({n_above_08/n_total*100:.0f}%)\n'
        f'Corr ≥ 0.7: {n_above_07}/{n_total} ({n_above_07/n_total*100:.0f}%)',
        transform=ax.transAxes, fontsize=10, verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8))

ax.set_xlabel('Pearson Correlation', fontsize=12)
ax.set_ylabel('Number of Speakers', fontsize=12)
ax.set_title('Per-Speaker Test Correlation Distribution (Exp20, window=16384)',
             fontsize=13, fontweight='bold')
ax.legend(fontsize=9, loc='upper left')
ax.set_xlim(0.3, 1.0)
ax.tick_params(labelsize=10)

plt.tight_layout()
path3 = os.path.join(FIGURES_DIR, 'speaker_correlation_distribution.png')
fig.savefig(path3, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  Saved: {path3}")


print("\n✅ All visualizations generated!")
print(f"  {path1}")
print(f"  {path2}")
print(f"  {path3}")
