#!/usr/bin/env python3
"""
실험 1b: 핵심 개선 — Window 확대 + 큰 모델 + Combined Loss
==========================================================
핵심 발견: window=192 (12ms)는 EGG 주기(5-12ms) 1개도 못 담음.
→ window=1024 (64ms, ~6주기)로 확대하면 상관관계 대폭 개선 예상.

변경 사항 (Baseline 대비):
  - Window: 192 → 1024 (핵심!)
  - Layers: 8 → 12
  - Channels: 32 → 64
  - Attention heads: 4 → 8
  - Loss: MSE → 0.5*MSE + 0.5*CorrLoss
  - LR scheduler: CosineAnnealing
  - Batch: 256 → 64 (window 커져서)
"""
import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from model.wavenet_egg import build_model
from utils.dataset import create_dataloaders


# ============================================================
EXP_NAME = "exp1b_longer_window"

CONFIG = {
    'data': {
        'svd_path': os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy'),
        'sample_rate': 16000,
        'window_length': 1024,   # 핵심: 192 → 1024 (64ms, ~6 F0 cycles)
        'hop_length': 512,       # 50% overlap
    },
    'model': {
        'layers': 12,
        'channels': 64,
        'kernel_size': 3,
        'use_attention': True,
        'num_heads': 8,
        'dropout': 0.3,          # 긴 window에서 더 적은 dropout
    },
    'training': {
        'batch_size': 64,        # window 커져서 줄임
        'max_epochs': 100,
        'learning_rate': 0.001,
        'weight_decay': 0.0001,
        'early_stopping_patience': 15,
        'loss_alpha': 0.5,
    },
}

RESULTS_DIR = os.path.expanduser(f'~/projects/egg_prediction/results/{EXP_NAME}')
CKPT_DIR = os.path.expanduser(f'~/projects/egg_prediction/checkpoints/{EXP_NAME}')


# ============================================================
# Combined Loss
# ============================================================
class CombinedLoss(nn.Module):
    def __init__(self, alpha=0.5):
        super().__init__()
        self.alpha = alpha
        self.mse = nn.MSELoss()
    
    def forward(self, pred, target):
        mse_loss = self.mse(pred, target)
        p = pred.squeeze(1)
        t = target.squeeze(1)
        p_c = p - p.mean(dim=1, keepdim=True)
        t_c = t - t.mean(dim=1, keepdim=True)
        num = (p_c * t_c).sum(dim=1)
        den = torch.sqrt((p_c ** 2).sum(dim=1) * (t_c ** 2).sum(dim=1) + 1e-8)
        corr_loss = 1.0 - (num / den).mean()
        return self.alpha * mse_loss + (1.0 - self.alpha) * corr_loss


# ============================================================
# Metrics
# ============================================================
def pearson_corr(pred, target):
    pred = pred.squeeze(1)
    target = target.squeeze(1)
    p_c = pred - pred.mean(dim=1, keepdim=True)
    t_c = target - target.mean(dim=1, keepdim=True)
    num = (p_c * t_c).sum(dim=1)
    den = torch.sqrt((p_c ** 2).sum(dim=1) * (t_c ** 2).sum(dim=1) + 1e-8)
    return (num / den).mean().item()


def rmse_fn(pred, target):
    return torch.sqrt(F.mse_loss(pred, target)).item()


# ============================================================
# Training / Evaluation
# ============================================================
def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    total_corr = 0
    n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += loss.item()
        total_corr += pearson_corr(pred.detach(), y)
        n += 1
    return total_loss / n, total_corr / n


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    total_corr = 0
    total_rmse = 0
    n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x)
        loss = criterion(pred, y)
        total_loss += loss.item()
        total_corr += pearson_corr(pred, y)
        total_rmse += rmse_fn(pred, y)
        n += 1
    if n == 0:
        return 0, 0, 0
    return total_loss / n, total_corr / n, total_rmse / n


# ============================================================
# Enhanced Plotting
# ============================================================
def plot_training_history(history, save_path):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    epochs = range(1, len(history['train_loss']) + 1)
    
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train', linewidth=1.5)
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val', linewidth=1.5)
    axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
    axes[0].set_title('Combined Loss'); axes[0].legend(); axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(epochs, history['train_corr'], 'b-', label='Train', linewidth=1.5)
    axes[1].plot(epochs, history['val_corr'], 'r-', label='Val', linewidth=1.5)
    axes[1].axhline(y=0.8, color='g', linestyle='--', alpha=0.7, label='Target (0.8)')
    axes[1].axhline(y=0.6662, color='orange', linestyle=':', alpha=0.7, label='Baseline (0.67)')
    axes[1].set_xlabel('Epoch'); axes[1].set_ylabel('Pearson Corr')
    axes[1].set_title('Correlation'); axes[1].legend(); axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(epochs, history['lr'], 'g-', linewidth=1.5)
    axes[2].set_xlabel('Epoch'); axes[2].set_ylabel('LR')
    axes[2].set_title('Learning Rate'); axes[2].grid(True, alpha=0.3)
    
    plt.suptitle(f'Exp1b: Window=1024 + Larger Model', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_detailed_comparison(model, test_loader, device, save_dir, n_examples=6):
    """MIC 입력, GT vs Pred EGG 겹침, Zoomed view"""
    model.eval()
    os.makedirs(save_dir, exist_ok=True)
    
    with torch.no_grad():
        all_x, all_y, all_pred = [], [], []
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            all_x.append(x.cpu()); all_y.append(y.cpu()); all_pred.append(pred.cpu())
            if sum(a.size(0) for a in all_x) >= n_examples:
                break
        all_x = torch.cat(all_x, 0)
        all_y = torch.cat(all_y, 0)
        all_pred = torch.cat(all_pred, 0)
    
    # 개별 3-panel 비교
    for i in range(min(n_examples, all_x.size(0))):
        mic = all_x[i, 0].numpy()
        gt = all_y[i, 0].numpy()
        pr = all_pred[i, 0].numpy()
        corr = np.corrcoef(gt, pr)[0, 1]
        T = len(mic)
        t = np.arange(T)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        
        axes[0].plot(t, mic, 'b-', linewidth=0.7)
        axes[0].set_title('MIC Input Signal', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Amplitude'); axes[0].set_xlim(0, T)
        axes[0].grid(True, alpha=0.3)
        
        axes[1].plot(t, gt, 'b-', label='Ground Truth EGG', linewidth=1.2)
        axes[1].plot(t, pr, color='orange', label='Predicted EGG', linewidth=1.2, alpha=0.85)
        axes[1].set_title(f'EGG Comparison  |  Pearson Corr: {corr:.4f}',
                          fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Amplitude'); axes[1].set_xlim(0, T)
        axes[1].legend(loc='upper right', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        z_len = min(200, T // 3)
        z_start = T // 3
        z_end = z_start + z_len
        axes[2].plot(range(z_start, z_end), gt[z_start:z_end], 'b-', label='GT', linewidth=2)
        axes[2].plot(range(z_start, z_end), pr[z_start:z_end], color='orange',
                     label='Pred', linewidth=2, alpha=0.85)
        axes[2].set_title(f'Zoomed View ({z_len} samples)', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('Sample'); axes[2].set_ylabel('Amplitude')
        axes[2].legend(fontsize=10); axes[2].grid(True, alpha=0.3)
        
        plt.suptitle(f'Test Sample {i+1}  |  Correlation: {corr:.4f}',
                     fontsize=14, fontweight='bold', y=1.01)
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f'sample_{i+1}.png'), dpi=150, bbox_inches='tight')
        plt.close()
    
    # 종합 비교
    fig, axes = plt.subplots(n_examples, 2, figsize=(16, 3 * n_examples))
    for i in range(min(n_examples, all_x.size(0))):
        mic = all_x[i, 0].numpy()
        gt = all_y[i, 0].numpy()
        pr = all_pred[i, 0].numpy()
        corr = np.corrcoef(gt, pr)[0, 1]
        T = len(mic)
        
        axes[i, 0].plot(np.arange(T), mic, 'b-', linewidth=0.7)
        if i == 0: axes[i, 0].set_title('MIC Input', fontsize=12, fontweight='bold')
        axes[i, 0].set_ylabel(f'#{i+1}', fontsize=10, fontweight='bold')
        axes[i, 0].set_xlim(0, T); axes[i, 0].grid(True, alpha=0.3)
        
        axes[i, 1].plot(np.arange(T), gt, 'b-', label='GT', linewidth=1)
        axes[i, 1].plot(np.arange(T), pr, color='orange', label='Pred', linewidth=1, alpha=0.85)
        if i == 0: axes[i, 1].set_title('GT vs Pred EGG', fontsize=12, fontweight='bold')
        axes[i, 1].set_xlim(0, T)
        axes[i, 1].legend(loc='upper right', fontsize=8)
        axes[i, 1].text(0.02, 0.88, f'r={corr:.4f}', transform=axes[i, 1].transAxes,
                        fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[i, 1].grid(True, alpha=0.3)
    
    axes[-1, 0].set_xlabel('Sample'); axes[-1, 1].set_xlabel('Sample')
    plt.suptitle('Exp1b: Window=1024 — Test Set Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'all_samples_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved comparison images to {save_dir}")


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print(f"  실험 1b: Window 1024 + Larger Model + Combined Loss")
    print(f"  핵심 변경: window 192→1024 (12ms→64ms, ~6 F0 cycles)")
    print("=" * 70)
    
    cfg = CONFIG
    data_cfg = cfg['data']
    model_cfg = cfg['model']
    train_cfg = cfg['training']
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(CKPT_DIR, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # Data
    print(f"\nWindow: {data_cfg['window_length']} ({data_cfg['window_length']/data_cfg['sample_rate']*1000:.0f}ms)")
    print(f"Hop: {data_cfg['hop_length']}")
    
    train_loader, val_loader, test_loader, split_info = create_dataloaders(
        svd_path=data_cfg['svd_path'],
        batch_size=train_cfg['batch_size'],
        window_length=data_cfg['window_length'],
        hop_length=data_cfg['hop_length'],
        target_sr=data_cfg['sample_rate'],
        num_workers=4,
        seed=42,
    )
    
    print(f"\nSplit: Train={split_info['train_speakers']} spk, "
          f"Val={split_info['val_speakers']} spk, Test={split_info['test_speakers']} spk")
    print(f"Windows: Train={split_info['train_windows']:,}, "
          f"Val={split_info['val_windows']:,}, Test={split_info['test_windows']:,}")
    
    # Model
    model = build_model(model_cfg).to(device)
    n_params = model.count_params()
    print(f"\nModel: {n_params:,} params")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=train_cfg['learning_rate'],
                                  weight_decay=train_cfg['weight_decay'])
    scheduler = CosineAnnealingWarmRestarts(optimizer, T_0=20, T_mult=2, eta_min=1e-6)
    criterion = CombinedLoss(alpha=train_cfg['loss_alpha'])
    mse_criterion = nn.MSELoss()
    
    history = {'train_loss': [], 'train_corr': [], 'val_loss': [], 'val_corr': [],
               'val_rmse': [], 'lr': []}
    
    best_val_corr = -1
    patience_counter = 0
    patience = train_cfg['early_stopping_patience']
    
    print(f"\n{'='*70}")
    print(f"  Training | Epochs: {train_cfg['max_epochs']} | Batch: {train_cfg['batch_size']} | LR: {train_cfg['learning_rate']}")
    print(f"  Patience: {patience} | Loss: α={train_cfg['loss_alpha']}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    for epoch in range(1, train_cfg['max_epochs'] + 1):
        t0 = time.time()
        train_loss, train_corr = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_corr, val_rmse = evaluate(model, val_loader, criterion, device)
        lr = optimizer.param_groups[0]['lr']
        
        history['train_loss'].append(train_loss)
        history['train_corr'].append(train_corr)
        history['val_loss'].append(val_loss)
        history['val_corr'].append(val_corr)
        history['val_rmse'].append(val_rmse)
        history['lr'].append(lr)
        
        scheduler.step()
        dt = time.time() - t0
        
        print(f"Epoch {epoch:3d}/{train_cfg['max_epochs']} | "
              f"Train Loss: {train_loss:.6f} Corr: {train_corr:.4f} | "
              f"Val Loss: {val_loss:.6f} Corr: {val_corr:.4f} RMSE: {val_rmse:.4f} | "
              f"LR: {lr:.6f} | {dt:.1f}s", end="")
        
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_corr': val_corr, 'val_loss': val_loss,
                'config': cfg,
            }, os.path.join(CKPT_DIR, 'best_model.pt'))
            print(f" ★ Best")
        else:
            patience_counter += 1
            print(f" (p: {patience_counter}/{patience})")
        
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch}")
            break
        
        if epoch % 10 == 0:
            plot_training_history(history, os.path.join(RESULTS_DIR, 'training_history.png'))
    
    total_time = time.time() - start_time
    print(f"\nTraining: {total_time / 60:.1f} min")
    
    # ── Final Evaluation ──
    print(f"\n{'='*70}")
    print("  Test Set Evaluation")
    print(f"{'='*70}")
    
    ckpt = torch.load(os.path.join(CKPT_DIR, 'best_model.pt'),
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    print(f"Best: epoch {ckpt['epoch']} (val_corr: {ckpt['val_corr']:.4f})")
    
    test_loss, test_corr, test_rmse = evaluate(model, test_loader, mse_criterion, device)
    
    print(f"\n  Test MSE Loss: {test_loss:.6f}")
    print(f"  Test Corr:     {test_corr:.4f}")
    print(f"  Test RMSE:     {test_rmse:.4f}")
    print(f"  Baseline:      0.6662 → {test_corr:.4f} ({'↑' if test_corr > 0.6662 else '↓'}{abs(test_corr - 0.6662):.4f})")
    print(f"  Target 0.8:    {'✅ 달성!' if test_corr >= 0.8 else '❌ 미달'}")
    
    # Plots
    plot_training_history(history, os.path.join(RESULTS_DIR, 'training_history.png'))
    plot_detailed_comparison(model, test_loader, device, RESULTS_DIR, n_examples=6)
    
    # Save metrics
    metrics = {
        'experiment': EXP_NAME,
        'model_params': n_params,
        'training_time_min': total_time / 60,
        'best_epoch': ckpt['epoch'],
        'best_val_corr': ckpt['val_corr'],
        'test_loss': test_loss, 'test_corr': test_corr, 'test_rmse': test_rmse,
        'baseline_test_corr': 0.6662,
        'improvement': test_corr - 0.6662,
        'config': cfg, 'split_info': split_info,
    }
    
    with open(os.path.join(RESULTS_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(RESULTS_DIR, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)
    
    with open(os.path.join(RESULTS_DIR, 'metrics.txt'), 'w') as f:
        f.write("=" * 60 + "\n")
        f.write(f"실험 1b: Window 1024 + Larger Model + Combined Loss\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"핵심: window 192→1024 (12ms→64ms)\n")
        f.write(f"Model: WaveNet (L=12, C=64, H=8), {n_params:,} params\n")
        f.write(f"Loss: 0.5*MSE + 0.5*CorrLoss\n")
        f.write(f"Training: {total_time/60:.1f} min, best epoch {ckpt['epoch']}\n\n")
        f.write(f"Best Val Corr: {ckpt['val_corr']:.4f}\n\n")
        f.write(f"Test:\n")
        f.write(f"  Loss: {test_loss:.6f}\n")
        f.write(f"  Corr: {test_corr:.4f}\n")
        f.write(f"  RMSE: {test_rmse:.4f}\n\n")
        f.write(f"Baseline: 0.6662\n")
        f.write(f"Improvement: {test_corr - 0.6662:+.4f}\n")
        f.write(f"Target (0.8): {'PASS' if test_corr >= 0.8 else 'FAIL'}\n")
    
    print(f"\n  Results: {RESULTS_DIR}")
    print(f"\n{'='*70}")
    print(f"  실험 1b 완료!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
