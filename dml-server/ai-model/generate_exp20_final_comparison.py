#!/usr/bin/env python3
"""
Exp20 최종 비교 이미지 생성 스크립트
final_comparison.png 형식으로 생성
3개 subplot: MIC Input | EGG Comparison | Zoomed View
"""
import os
import sys
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa
from collections import defaultdict

# ── 경로 설정 ──
BASE = os.path.expanduser('~/projects/egg_prediction')
CKPT_PATH = os.path.join(BASE, 'checkpoints/exp20_progressive/best_model.pt')
RESULTS_DIR = os.path.join(BASE, 'results')
SVD_PATH = os.path.join(BASE, 'data/SVD_healthy')

# ── 경로 추가 ──
sys.path.insert(0, os.path.join(BASE, 'dml-server/ai-model'))
from model.efficient_egg import build_efficient_model
from utils.nsp_reader import find_paired_files, read_nsp
from utils.dataset import speaker_split

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
SR = 16000


def pearson_corr(a, b):
    """Pearson correlation coefficient"""
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
    """Predict EGG from speech"""
    x = torch.from_numpy(speech_window).float().unsqueeze(0).unsqueeze(0).to(device)
    return model(x).squeeze().cpu().numpy()


def find_best_samples(model, n_samples=5):
    """Find best correlation samples from test set"""
    print(f"Finding best {n_samples} samples...")
    
    # Load test pairs
    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))
    train_sp, val_sp, test_sp = speaker_split(all_speakers, seed=42)
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
    
    samples = []
    processed = 0
    
    for nsp_path, egg_path, spk in test_pairs[:200]:  # limit to speed up
        try:
            mic, egg_gt = load_and_preprocess(nsp_path, egg_path)
            if mic is None:
                continue
            
            egg_pred = predict(model, mic)
            mt = min(len(egg_gt), len(egg_pred))
            egg_gt, egg_pred, mic = egg_gt[:mt], egg_pred[:mt], mic[:mt]
            
            corr = pearson_corr(egg_gt, egg_pred)
            samples.append((mic, egg_gt, egg_pred, corr, spk))
            
            processed += 1
            if processed % 50 == 0:
                print(f"  Processed {processed} files...")
            
            if len(samples) >= n_samples * 3:
                break
        except Exception as e:
            continue
    
    # Sort by correlation and get top samples
    samples.sort(key=lambda x: x[3], reverse=True)
    return samples[:n_samples]


def plot_final_comparison(samples, save_path):
    """Create final_comparison.png style image"""
    mic, gt, pr, corr, spk = samples[0]  # best corr sample
    T = len(mic)
    t = np.arange(T)
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [1, 1.2, 1.2]})
    fig.patch.set_facecolor('white')
    
    # ── 상단: MIC Input ──
    axes[0].plot(t, mic, color='#1f77b4', lw=0.6)
    axes[0].set_title('MIC Input Signal', fontsize=13, fontweight='bold', pad=8)
    axes[0].set_ylabel('Amplitude', fontsize=11)
    axes[0].set_xlim(0, T)
    axes[0].grid(True, alpha=0.25, linewidth=0.5)
    axes[0].tick_params(labelsize=9)
    
    # ── 중단: GT + Pred 오버레이 ──
    axes[1].plot(t, gt, color='#1f77b4', lw=0.8, label='Ground Truth EGG', zorder=2)
    axes[1].plot(t, pr, color='#ff7f0e', lw=0.8, alpha=0.85, label='Predicted EGG', zorder=3)
    axes[1].set_title(f'EGG Comparison  (Pearson r = {corr:.4f})', fontsize=13, fontweight='bold', pad=8)
    axes[1].set_ylabel('Amplitude', fontsize=11)
    axes[1].set_xlim(0, T)
    axes[1].legend(loc='upper right', fontsize=10, framealpha=0.9)
    axes[1].grid(True, alpha=0.25, linewidth=0.5)
    axes[1].tick_params(labelsize=9)
    
    # ── 하단: Zoomed View (200 samples) ──
    zoom_len = 200
    # 에너지 높은 구간 찾기
    energy = np.convolve(gt**2, np.ones(zoom_len), mode='valid')
    start = np.argmax(energy)
    end = start + zoom_len
    t_zoom = np.arange(start, end)
    
    axes[2].plot(t_zoom, gt[start:end], color='#1f77b4', lw=2.0, label='Ground Truth EGG', zorder=2)
    axes[2].plot(t_zoom, pr[start:end], color='#ff7f0e', lw=2.0, alpha=0.85, label='Predicted EGG', zorder=3)
    axes[2].set_title(f'Zoomed View ({zoom_len} samples, idx {start}–{end})', fontsize=13, fontweight='bold', pad=8)
    axes[2].set_xlabel('Sample Index', fontsize=11)
    axes[2].set_ylabel('Amplitude', fontsize=11)
    axes[2].legend(loc='upper right', fontsize=10, framealpha=0.9)
    axes[2].grid(True, alpha=0.25, linewidth=0.5)
    axes[2].tick_params(labelsize=9)
    
    plt.suptitle(f'EGG Prediction — Best Model (Exp20, Test Corr: 0.8249)',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ 이미지 저장: {save_path}")


def main():
    print("="*60)
    print("Exp20 Final Comparison Image Generation")
    print("="*60)
    
    # Load model
    print("\n1️⃣  Loading Exp20 model...")
    cfg = {'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05}
    model = build_efficient_model(cfg)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model = model.to(device).eval()
    print(f"   ✓ Loaded (val_corr={ckpt.get('val_corr', '?'):.4f})")
    
    # Find best samples
    print("\n2️⃣  Finding best samples from test set...")
    best_samples = find_best_samples(model, n_samples=5)
    print(f"   Found {len(best_samples)} samples")
    for i, (_, _, _, corr, spk) in enumerate(best_samples):
        print(f"     {i+1}. Speaker {spk}: corr={corr:.4f}")
    
    # Generate final_comparison.png
    print("\n3️⃣  Generating final_comparison.png...")
    output_path = os.path.join(RESULTS_DIR, 'exp20_final_comparison.png')
    plot_final_comparison(best_samples, output_path)
    
    print("\n" + "="*60)
    print(f"✅ Done! Image saved to: {output_path}")
    print("="*60)


if __name__ == '__main__':
    main()
