#!/usr/bin/env python3
"""
SVD EGG Prediction - Training Script
=====================================
Speaker-independent model: Speech -> EGG prediction
WaveNet + Self-Attention architecture

Usage:
    conda activate EGGDML
    cd ~/projects/egg_prediction
    python train.py
"""
import os
import sys
import time
import json
import yaml
import numpy as np
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ExponentialLR
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from model.wavenet_egg import build_model
from utils.dataset import create_dataloaders


# ============================================================
# Configuration
# ============================================================
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'configs', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    # Default config
    return {
        'data': {
            'svd_path': os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy'),
            'sample_rate': 16000,
            'window_length': 192,
            'hop_length': 32,
        },
        'model': {
            'layers': 8,
            'channels': 32,
            'kernel_size': 3,
            'use_attention': True,
            'dropout': 0.5,
        },
        'training': {
            'batch_size': 256,
            'max_epochs': 100,
            'learning_rate': 0.001,
            'lr_decay': 0.95,
            'weight_decay': 0.0001,
            'early_stopping_patience': 10,
        },
        'split': {
            'train_ratio': 0.8,
            'val_ratio': 0.1,
            'test_ratio': 0.1,
        },
        'paths': {
            'results': os.path.expanduser('~/projects/egg_prediction/results'),
            'checkpoints': os.path.expanduser('~/projects/egg_prediction/checkpoints'),
        }
    }


# ============================================================
# Metrics
# ============================================================
def pearson_corr(pred, target):
    """Batch-wise Pearson correlation (average over batch)."""
    # pred, target: [B, 1, T]
    pred = pred.squeeze(1)     # [B, T]
    target = target.squeeze(1) # [B, T]
    
    pred_mean = pred.mean(dim=1, keepdim=True)
    target_mean = target.mean(dim=1, keepdim=True)
    
    pred_centered = pred - pred_mean
    target_centered = target - target_mean
    
    num = (pred_centered * target_centered).sum(dim=1)
    den = torch.sqrt((pred_centered ** 2).sum(dim=1) * (target_centered ** 2).sum(dim=1) + 1e-8)
    
    corr = num / den
    return corr.mean().item()


def rmse(pred, target):
    """Root mean squared error."""
    return torch.sqrt(nn.functional.mse_loss(pred, target)).item()


# ============================================================
# Training / Evaluation
# ============================================================
def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    total_corr = 0
    n_batches = 0
    
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        
        optimizer.zero_grad()
        pred = model(x)
        loss = criterion(pred, y)
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        
        optimizer.step()
        
        total_loss += loss.item()
        total_corr += pearson_corr(pred.detach(), y)
        n_batches += 1
    
    return total_loss / n_batches, total_corr / n_batches


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    total_corr = 0
    total_rmse = 0
    n_batches = 0
    
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x)
        loss = criterion(pred, y)
        
        total_loss += loss.item()
        total_corr += pearson_corr(pred, y)
        total_rmse += rmse(pred, y)
        n_batches += 1
    
    if n_batches == 0:
        return 0, 0, 0
    
    return total_loss / n_batches, total_corr / n_batches, total_rmse / n_batches


# ============================================================
# Plotting
# ============================================================
def plot_training_history(history, save_path):
    """Plot training curves."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    # Loss
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train')
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss (MSE)')
    axes[0].set_title('Loss')
    axes[0].legend()
    axes[0].grid(True)
    
    # Correlation
    axes[1].plot(epochs, history['train_corr'], 'b-', label='Train')
    axes[1].plot(epochs, history['val_corr'], 'r-', label='Val')
    axes[1].axhline(y=0.5, color='g', linestyle='--', alpha=0.5, label='Target (0.5)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Pearson Correlation')
    axes[1].set_title('Correlation')
    axes[1].legend()
    axes[1].grid(True)
    
    # Learning rate
    axes[2].plot(epochs, history['lr'], 'g-')
    axes[2].set_xlabel('Epoch')
    axes[2].set_ylabel('Learning Rate')
    axes[2].set_title('Learning Rate')
    axes[2].grid(True)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path}")


def plot_comparison(model, test_loader, device, save_path, n_examples=4):
    """Plot predicted vs actual EGG for test samples."""
    model.eval()
    
    fig, axes = plt.subplots(n_examples, 1, figsize=(14, 3 * n_examples))
    if n_examples == 1:
        axes = [axes]
    
    with torch.no_grad():
        x, y = next(iter(test_loader))
        x, y = x.to(device), y.to(device)
        pred = model(x)
        
        for i in range(min(n_examples, x.size(0))):
            ax = axes[i]
            t = np.arange(x.size(-1))
            
            actual = y[i, 0].cpu().numpy()
            predicted = pred[i, 0].cpu().numpy()
            corr = np.corrcoef(actual, predicted)[0, 1]
            
            ax.plot(t, actual, 'b-', alpha=0.7, label='Actual EGG', linewidth=0.8)
            ax.plot(t, predicted, 'r-', alpha=0.7, label='Predicted EGG', linewidth=0.8)
            ax.set_title(f'Sample {i+1} | Corr: {corr:.4f}')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
    
    plt.suptitle('Test Set: Predicted vs Actual EGG', fontsize=14)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {save_path}")


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 70)
    print("  SVD EGG Prediction - Speaker-Independent Training")
    print("  WaveNet + Self-Attention")
    print("=" * 70)
    
    # Load config
    cfg = load_config()
    data_cfg = cfg['data']
    model_cfg = cfg['model']
    train_cfg = cfg['training']
    paths_cfg = cfg['paths']
    
    # Expand paths
    svd_path = os.path.expanduser(data_cfg['svd_path'])
    results_dir = os.path.expanduser(paths_cfg['results'])
    ckpt_dir = os.path.expanduser(paths_cfg['checkpoints'])
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Data
    print(f"\nData path: {svd_path}")
    print(f"Window: {data_cfg['window_length']}, Hop: {data_cfg['hop_length']}")
    print(f"Target SR: {data_cfg['sample_rate']} Hz")
    
    train_loader, val_loader, test_loader, split_info = create_dataloaders(
        svd_path=svd_path,
        batch_size=train_cfg['batch_size'],
        window_length=data_cfg['window_length'],
        hop_length=data_cfg['hop_length'],
        target_sr=data_cfg['sample_rate'],
        num_workers=4,
        seed=42,
    )
    
    print(f"\nSplit info:")
    for k, v in split_info.items():
        print(f"  {k}: {v}")
    
    # Model
    model = build_model(model_cfg).to(device)
    print(f"\nModel parameters: {model.count_params():,}")
    print(model)
    
    # Optimizer, scheduler, criterion
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_cfg['learning_rate'],
        weight_decay=train_cfg['weight_decay'],
    )
    scheduler = ExponentialLR(optimizer, gamma=train_cfg['lr_decay'])
    criterion = nn.MSELoss()
    
    # Training history
    history = {
        'train_loss': [], 'train_corr': [],
        'val_loss': [], 'val_corr': [], 'val_rmse': [],
        'lr': [],
    }
    
    best_val_corr = -1
    patience_counter = 0
    patience = train_cfg['early_stopping_patience']
    
    print(f"\n{'='*70}")
    print(f"  Training Start | Epochs: {train_cfg['max_epochs']} | "
          f"Batch: {train_cfg['batch_size']} | LR: {train_cfg['learning_rate']}")
    print(f"  Early stopping patience: {patience}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    for epoch in range(1, train_cfg['max_epochs'] + 1):
        epoch_start = time.time()
        
        # Train
        train_loss, train_corr = train_epoch(model, train_loader, optimizer,
                                             criterion, device)
        
        # Validate
        val_loss, val_corr, val_rmse = evaluate(model, val_loader, criterion, device)
        
        # Get LR
        current_lr = optimizer.param_groups[0]['lr']
        
        # Record
        history['train_loss'].append(train_loss)
        history['train_corr'].append(train_corr)
        history['val_loss'].append(val_loss)
        history['val_corr'].append(val_corr)
        history['val_rmse'].append(val_rmse)
        history['lr'].append(current_lr)
        
        # Scheduler step
        scheduler.step()
        
        epoch_time = time.time() - epoch_start
        
        # Print progress
        print(f"Epoch {epoch:3d}/{train_cfg['max_epochs']} | "
              f"Train Loss: {train_loss:.6f} Corr: {train_corr:.4f} | "
              f"Val Loss: {val_loss:.6f} Corr: {val_corr:.4f} RMSE: {val_rmse:.4f} | "
              f"LR: {current_lr:.6f} | {epoch_time:.1f}s", end="")
        
        # Best model check
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            patience_counter = 0
            ckpt_path = os.path.join(ckpt_dir, 'best_model.pt')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_corr': val_corr,
                'val_loss': val_loss,
                'config': cfg,
            }, ckpt_path)
            print(f" ★ Best (saved)")
        else:
            patience_counter += 1
            print(f" (patience: {patience_counter}/{patience})")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch}")
            break
        
        # Save plots every 10 epochs
        if epoch % 10 == 0:
            plot_training_history(history, os.path.join(results_dir, 'training_history.png'))
    
    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time / 60:.1f} minutes")
    
    # ── Final Evaluation ──
    print(f"\n{'='*70}")
    print("  Final Evaluation on Test Set")
    print(f"{'='*70}")
    
    # Load best model
    ckpt = torch.load(os.path.join(ckpt_dir, 'best_model.pt'), map_location=device,
                      weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    print(f"Loaded best model from epoch {ckpt['epoch']} (val_corr: {ckpt['val_corr']:.4f})")
    
    test_loss, test_corr, test_rmse = evaluate(model, test_loader, criterion, device)
    
    print(f"\n  Test Loss:  {test_loss:.6f}")
    print(f"  Test Corr:  {test_corr:.4f}")
    print(f"  Test RMSE:  {test_rmse:.4f}")
    print(f"  Target:     corr >= 0.5 → {'✅ 달성!' if test_corr >= 0.5 else '❌ 미달'}")
    
    # ── Save Results ──
    # Final plots
    plot_training_history(history, os.path.join(results_dir, 'training_history.png'))
    plot_comparison(model, test_loader, device,
                    os.path.join(results_dir, 'comparison.png'))
    
    # Metrics text
    metrics_path = os.path.join(results_dir, 'metrics.txt')
    with open(metrics_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("SVD EGG Prediction - Training Results\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Model: WaveNet + Self-Attention\n")
        f.write(f"Parameters: {model.count_params():,}\n")
        f.write(f"Training time: {total_time / 60:.1f} minutes\n")
        f.write(f"Best epoch: {ckpt['epoch']}\n\n")
        
        f.write(f"Split:\n")
        for k, v in split_info.items():
            f.write(f"  {k}: {v}\n")
        
        f.write(f"\nBest Validation:\n")
        f.write(f"  Corr: {ckpt['val_corr']:.4f}\n")
        f.write(f"  Loss: {ckpt['val_loss']:.6f}\n")
        
        f.write(f"\nTest Set:\n")
        f.write(f"  Loss: {test_loss:.6f}\n")
        f.write(f"  Corr: {test_corr:.4f}\n")
        f.write(f"  RMSE: {test_rmse:.4f}\n")
        f.write(f"  Target (corr>=0.5): {'PASS' if test_corr >= 0.5 else 'FAIL'}\n")
    
    print(f"  Saved: {metrics_path}")
    
    # Save history JSON
    history_path = os.path.join(results_dir, 'history.json')
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"  Saved: {history_path}")
    
    print(f"\n{'='*70}")
    print(f"  완료! 결과: {results_dir}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
