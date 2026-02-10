#!/usr/bin/env python3
"""
결과 시각화 이미지 생성 스크립트
Best 모델(Exp3, EfficientEGGNet)로 3가지 비교 이미지 생성
"""
import os
import sys
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from model.efficient_egg import build_efficient_model
from utils.dataset import create_dataloaders

# ── 경로 설정 ──
BASE = os.path.expanduser('~/projects/egg_prediction')
CKPT_PATH = os.path.join(BASE, 'checkpoints/exp3_efficient/best_model.pt')
RESULTS_DIR = os.path.join(BASE, 'results')
SVD_PATH = os.path.join(BASE, 'data/SVD_healthy')

# ── Exp3 설정 (train_exp3.py와 동일) ──
DATA_CFG = {
    'svd_path': SVD_PATH,
    'sample_rate': 16000,
    'window_length': 4096,
    'hop_length': 2048,
}
MODEL_CFG = {
    'channels': 96,
    'n_layers': 24,
    'kernel_size': 3,
    'n_stacks': 3,
    'dropout': 0.1,
}


def load_model(device):
    """Exp3 best model 로드"""
    model = build_efficient_model(MODEL_CFG).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print(f"모델 로드: epoch {ckpt['epoch']}, val_corr {ckpt['val_corr']:.4f}")
    return model


def get_test_samples(model, test_loader, device, n=10):
    """테스트 데이터에서 예측 수행, 가장 corr 높은 샘플 반환"""
    samples = []
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            for i in range(x.size(0)):
                mic = x[i, 0].cpu().numpy()
                gt = y[i, 0].cpu().numpy()
                pr = pred[i, 0].cpu().numpy()
                if np.std(gt) > 1e-8 and np.std(pr) > 1e-8:
                    corr = np.corrcoef(gt, pr)[0, 1]
                else:
                    corr = 0.0
                samples.append((mic, gt, pr, corr))
            if len(samples) >= 200:
                break
    # corr 높은 순 정렬
    samples.sort(key=lambda s: s[3], reverse=True)
    return samples


# ============================================================
# 이미지 1: 전체 비교 (3개 subplot)
# ============================================================
def plot_final_comparison(samples, save_path):
    mic, gt, pr, corr = samples[0]  # best corr sample
    T = len(mic)
    t = np.arange(T)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [1, 1.2, 1.2]})
    fig.patch.set_facecolor('white')

    # 상단: MIC Input
    axes[0].plot(t, mic, color='#1f77b4', lw=0.6)
    axes[0].set_title('MIC Input Signal', fontsize=13, fontweight='bold', pad=8)
    axes[0].set_ylabel('Amplitude', fontsize=11)
    axes[0].set_xlim(0, T)
    axes[0].grid(True, alpha=0.25, linewidth=0.5)
    axes[0].tick_params(labelsize=9)

    # 중단: GT + Pred 겹쳐서
    axes[1].plot(t, gt, color='#1f77b4', lw=0.8, label='Ground Truth EGG')
    axes[1].plot(t, pr, color='#ff7f0e', lw=0.8, alpha=0.85, label='Predicted EGG')
    axes[1].set_title(f'EGG Comparison  (Pearson r = {corr:.4f})', fontsize=13, fontweight='bold', pad=8)
    axes[1].set_ylabel('Amplitude', fontsize=11)
    axes[1].set_xlim(0, T)
    axes[1].legend(loc='upper right', fontsize=10, framealpha=0.9)
    axes[1].grid(True, alpha=0.25, linewidth=0.5)
    axes[1].tick_params(labelsize=9)

    # 하단: Zoomed View (200 samples)
    zoom_len = 200
    # 에너지 높은 구간 찾기
    energy = np.convolve(gt**2, np.ones(zoom_len), mode='valid')
    start = np.argmax(energy)
    end = start + zoom_len
    t_zoom = np.arange(start, end)

    axes[2].plot(t_zoom, gt[start:end], color='#1f77b4', lw=2.0, label='Ground Truth EGG')
    axes[2].plot(t_zoom, pr[start:end], color='#ff7f0e', lw=2.0, alpha=0.85, label='Predicted EGG',
                 linestyle='-')
    axes[2].set_title(f'Zoomed View ({zoom_len} samples, idx {start}–{end})', fontsize=13, fontweight='bold', pad=8)
    axes[2].set_xlabel('Sample Index', fontsize=11)
    axes[2].set_ylabel('Amplitude', fontsize=11)
    axes[2].legend(loc='upper right', fontsize=10, framealpha=0.9)
    axes[2].grid(True, alpha=0.25, linewidth=0.5)
    axes[2].tick_params(labelsize=9)

    plt.suptitle(f'EGG Prediction — Best Model (Exp3, Test Corr: 0.7163)',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ 이미지 1 저장: {save_path}")


# ============================================================
# 이미지 2: GT vs Pred 오버레이 (단일 그래프)
# ============================================================
def plot_overlay_comparison(samples, save_path):
    mic, gt, pr, corr = samples[0]
    T = len(gt)

    # 에너지 높은 구간에서 250 samples
    zoom_len = 250
    energy = np.convolve(gt**2, np.ones(zoom_len), mode='valid')
    start = np.argmax(energy)
    end = start + zoom_len
    t_zoom = np.arange(start, end)

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor('white')

    ax.plot(t_zoom, gt[start:end], color='#1f77b4', lw=2.0, label='Ground Truth EGG', zorder=2)
    ax.plot(t_zoom, pr[start:end], color='#ff7f0e', lw=2.0, alpha=0.85, label='Predicted EGG',
            linestyle='-', zorder=3)

    ax.set_title('EGG Prediction (Test Corr: 0.7163)', fontsize=15, fontweight='bold', pad=10)
    ax.set_xlabel('Sample Index', fontsize=12)
    ax.set_ylabel('Amplitude', fontsize=12)
    ax.legend(loc='upper right', fontsize=12, framealpha=0.9, edgecolor='gray')
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.tick_params(labelsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ 이미지 2 저장: {save_path}")


# ============================================================
# 이미지 3: 실험별 성능 비교 Bar Chart
# ============================================================
def plot_experiment_comparison(save_path):
    experiments = ['Baseline', 'Exp1\n(Larger)', 'Exp3\n(Efficient)', 'Exp4\n(Multi-Input)']
    test_corrs = [0.6662, 0.6784, 0.7163, 0.7137]
    colors = ['#95a5a6', '#3498db', '#e74c3c', '#2ecc71']

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')

    bars = ax.bar(experiments, test_corrs, color=colors, width=0.55, edgecolor='white', linewidth=1.5,
                  zorder=3)

    # 목표선 (0.8)
    ax.axhline(y=0.8, color='#e74c3c', linestyle='--', linewidth=2, alpha=0.7, zorder=2,
               label='Target (0.8)')

    # 바 위에 값 표시
    for bar, val in zip(bars, test_corrs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f'{val:.4f}', ha='center', va='bottom', fontsize=13, fontweight='bold')

    # Best 표시
    best_idx = np.argmax(test_corrs)
    bars[best_idx].set_edgecolor('#c0392b')
    bars[best_idx].set_linewidth(3)
    ax.text(bars[best_idx].get_x() + bars[best_idx].get_width() / 2,
            test_corrs[best_idx] + 0.018, '* Best *', ha='center', va='bottom',
            fontsize=12, fontweight='bold', color='#c0392b')

    ax.set_title('Experiment Comparison — Test Pearson Correlation', fontsize=15, fontweight='bold', pad=12)
    ax.set_ylabel('Test Correlation', fontsize=12)
    ax.set_ylim(0.60, 0.85)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.02))
    ax.grid(axis='y', alpha=0.25, linewidth=0.5, zorder=0)
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)
    ax.tick_params(labelsize=11)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ 이미지 3 저장: {save_path}")


# ============================================================
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # ── 이미지 3: 바 차트 (모델 불필요) ──
    plot_experiment_comparison(os.path.join(RESULTS_DIR, 'experiment_comparison.png'))

    # ── 모델 + 데이터 로드 ──
    print("\n모델 로딩...")
    model = load_model(device)

    print("테스트 데이터 로딩...")
    _, _, test_loader, split_info = create_dataloaders(
        svd_path=DATA_CFG['svd_path'],
        batch_size=32,
        window_length=DATA_CFG['window_length'],
        hop_length=DATA_CFG['hop_length'],
        target_sr=DATA_CFG['sample_rate'],
        num_workers=4, seed=42,
    )
    print(f"Test: {split_info['test_speakers']} speakers, {split_info['test_windows']:,} windows")

    print("\n예측 수행 중...")
    samples = get_test_samples(model, test_loader, device)
    print(f"Top-5 sample corr: {[f'{s[3]:.4f}' for s in samples[:5]]}")

    # ── 이미지 1, 2 ──
    plot_final_comparison(samples, os.path.join(RESULTS_DIR, 'final_comparison.png'))
    plot_overlay_comparison(samples, os.path.join(RESULTS_DIR, 'overlay_comparison.png'))

    print(f"\n{'='*50}")
    print("  모든 이미지 생성 완료!")
    print(f"  1. {RESULTS_DIR}/final_comparison.png")
    print(f"  2. {RESULTS_DIR}/overlay_comparison.png")
    print(f"  3. {RESULTS_DIR}/experiment_comparison.png")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
