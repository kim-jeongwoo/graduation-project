#!/usr/bin/env python3
"""
EGG 예측 모델 자동 최적화 V2 — 목표 Corr >= 0.8
================================================
Base: exp11_multiscale (Corr=0.7484)
  - EfficientEGGNet(channels=128, n_layers=30, kernel_size=5, n_stacks=5, dropout=0.05)
  - window_length=8192, hop_length=4096, target_sr=16000, batch_size=16
  - CombinedLoss(alpha=0.2), AdamW(lr=0.001, wd=1e-4), OneCycleLR, patience=15

이전 실패 반영:
  - wav2vec2 → 사용 안 함
  - Conformer → OOM → 메모리 효율적으로
  - 앙상블 → 효과 없음 → 단일 모델
  - exp11 Epoch 4 과적합 → 더 강한 regularization

Experiments:
  Exp13: 강한 Regularization (dropout 0.3, wd 1e-3, label smoothing)
  Exp14: Data Augmentation (noise, gain — 정렬 유지)
  Exp15: Mixup
  Exp16: Squeeze-and-Excitation blocks
  Exp17: CBAM (Channel + Spatial Attention)
  Exp18: Deeper Multiscale (40 layers, gradient checkpointing)
  Exp19: Cosine Annealing Warm Restarts
  Exp20: Progressive Window Resizing
  Exp21: High-Quality Data Only (raw_corr >= 0.6)
  Exp22: Multi-Scale Loss (MSE + Corr + Spectral)
  Exp23: Perceptual Loss
"""
import os, sys, time, json, traceback, gc, copy, math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import OneCycleLR, CosineAnnealingWarmRestarts
from torch.utils.checkpoint import checkpoint as grad_checkpoint
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# ============================================================
# Paths
# ============================================================
PROJECT_DIR = os.path.expanduser('~/projects/egg_prediction')
sys.path.insert(0, os.path.join(PROJECT_DIR, 'ai-model'))

from model.efficient_egg import build_efficient_model, EfficientEGGNet, DilatedBlock
from utils.dataset import create_dataloaders, SVDEggDataset, speaker_split
from utils.nsp_reader import read_nsp, find_paired_files

SVD_PATH = os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy')
LOG_FILE = os.path.join(PROJECT_DIR, 'results/experiment_log_v2.txt')

# Korean font
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FPROP = fm.FontProperties(fname=FONT_PATH, size=12) if os.path.exists(FONT_PATH) else None
FPROP_S = fm.FontProperties(fname=FONT_PATH, size=10) if os.path.exists(FONT_PATH) else None
FPROP_T = fm.FontProperties(fname=FONT_PATH, size=14) if os.path.exists(FONT_PATH) else None


# ============================================================
# Logging
# ============================================================
def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


# ============================================================
# Loss Functions
# ============================================================
class CombinedLoss(nn.Module):
    """MSE + Correlation loss."""
    def __init__(self, alpha=0.3):
        super().__init__()
        self.alpha = alpha

    def forward(self, pred, target):
        mse = F.mse_loss(pred, target)
        p = pred.squeeze(1)
        t = target.squeeze(1)
        pc = p - p.mean(dim=1, keepdim=True)
        tc = t - t.mean(dim=1, keepdim=True)
        num = (pc * tc).sum(dim=1)
        den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
        corr_loss = 1.0 - (num / den).mean()
        return self.alpha * mse + (1 - self.alpha) * corr_loss


class LabelSmoothingCombinedLoss(nn.Module):
    """CombinedLoss with target smoothing towards zero mean."""
    def __init__(self, alpha=0.3, smoothing=0.1):
        super().__init__()
        self.alpha = alpha
        self.smoothing = smoothing

    def forward(self, pred, target):
        # Smooth target: (1 - eps) * target + eps * 0
        target_smooth = (1 - self.smoothing) * target
        mse = F.mse_loss(pred, target_smooth)
        p = pred.squeeze(1)
        t = target.squeeze(1)
        pc = p - p.mean(dim=1, keepdim=True)
        tc = t - t.mean(dim=1, keepdim=True)
        num = (pc * tc).sum(dim=1)
        den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
        corr_loss = 1.0 - (num / den).mean()
        return self.alpha * mse + (1 - self.alpha) * corr_loss


class MultiScaleLoss(nn.Module):
    """MSE + Correlation + Spectral (multi-resolution STFT) loss."""
    def __init__(self, alpha_mse=0.3, alpha_corr=0.5, alpha_spec=0.2,
                 fft_sizes=(256, 512, 1024)):
        super().__init__()
        self.alpha_mse = alpha_mse
        self.alpha_corr = alpha_corr
        self.alpha_spec = alpha_spec
        self.fft_sizes = fft_sizes

    def _spectral_loss(self, pred, target):
        """Multi-resolution STFT loss."""
        loss = 0
        pred_1d = pred.squeeze(1)
        tgt_1d = target.squeeze(1)
        for fft_size in self.fft_sizes:
            hop = fft_size // 4
            win = torch.hann_window(fft_size, device=pred.device)
            # Ensure enough length
            if pred_1d.shape[-1] < fft_size:
                continue
            pred_stft = torch.stft(pred_1d, fft_size, hop_length=hop,
                                   win_length=fft_size, window=win,
                                   return_complex=True)
            tgt_stft = torch.stft(tgt_1d, fft_size, hop_length=hop,
                                  win_length=fft_size, window=win,
                                  return_complex=True)
            pred_mag = pred_stft.abs()
            tgt_mag = tgt_stft.abs()
            # Spectral convergence + log magnitude
            sc = torch.norm(tgt_mag - pred_mag) / (torch.norm(tgt_mag) + 1e-8)
            log_mag = F.l1_loss(torch.log(pred_mag + 1e-8), torch.log(tgt_mag + 1e-8))
            loss += sc + log_mag
        return loss / max(len(self.fft_sizes), 1)

    def forward(self, pred, target):
        mse = F.mse_loss(pred, target)
        # Correlation loss
        p = pred.squeeze(1)
        t = target.squeeze(1)
        pc = p - p.mean(dim=1, keepdim=True)
        tc = t - t.mean(dim=1, keepdim=True)
        num = (pc * tc).sum(dim=1)
        den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
        corr_loss = 1.0 - (num / den).mean()
        # Spectral loss
        spec_loss = self._spectral_loss(pred, target)
        return self.alpha_mse * mse + self.alpha_corr * corr_loss + self.alpha_spec * spec_loss


class PerceptualLoss(nn.Module):
    """CombinedLoss + feature-matching loss using intermediate representations."""
    def __init__(self, alpha=0.2, perceptual_weight=0.3):
        super().__init__()
        self.base = CombinedLoss(alpha)
        self.pw = perceptual_weight
        # Small 1D feature extractor (frozen after init)
        self.feat_net = nn.Sequential(
            nn.Conv1d(1, 32, 7, stride=2, padding=3),
            nn.GELU(),
            nn.Conv1d(32, 64, 5, stride=2, padding=2),
            nn.GELU(),
            nn.Conv1d(64, 128, 3, stride=2, padding=1),
            nn.GELU(),
        )
        # Freeze perceptual network
        for p in self.feat_net.parameters():
            p.requires_grad = False

    def forward(self, pred, target):
        base_loss = self.base(pred, target)
        with torch.no_grad():
            tgt_feat = self.feat_net(target)
        pred_feat = self.feat_net(pred)
        feat_loss = F.l1_loss(pred_feat, tgt_feat)
        return base_loss + self.pw * feat_loss


def pearson_corr_batch(pred, target):
    p = pred.squeeze(1)
    t = target.squeeze(1)
    pc = p - p.mean(dim=1, keepdim=True)
    tc = t - t.mean(dim=1, keepdim=True)
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
    return (num / den).mean().item()


# ============================================================
# Enhanced Model Architectures
# ============================================================

class SEBlock(nn.Module):
    """Squeeze-and-Excitation block for channel attention."""
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.GELU(),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: [B, C, T]
        b, c, t = x.shape
        se = x.mean(dim=2)  # [B, C]
        se = self.fc(se).unsqueeze(2)  # [B, C, 1]
        return x * se


class CBAMBlock(nn.Module):
    """Convolutional Block Attention Module — channel + spatial."""
    def __init__(self, channels, reduction=8, spatial_kernel=7):
        super().__init__()
        # Channel attention
        self.channel_fc = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.GELU(),
            nn.Linear(channels // reduction, channels),
        )
        # Spatial attention
        self.spatial_conv = nn.Conv1d(2, 1, spatial_kernel,
                                      padding=spatial_kernel // 2)

    def forward(self, x):
        # Channel attention
        b, c, t = x.shape
        avg_pool = x.mean(dim=2)  # [B, C]
        max_pool = x.max(dim=2)[0]  # [B, C]
        ch_att = torch.sigmoid(self.channel_fc(avg_pool) + self.channel_fc(max_pool))
        x = x * ch_att.unsqueeze(2)
        # Spatial attention
        avg_sp = x.mean(dim=1, keepdim=True)   # [B, 1, T]
        max_sp = x.max(dim=1, keepdim=True)[0]  # [B, 1, T]
        sp_att = torch.sigmoid(self.spatial_conv(torch.cat([avg_sp, max_sp], dim=1)))
        x = x * sp_att
        return x


class DilatedBlockSE(nn.Module):
    """DilatedBlock + SE attention."""
    def __init__(self, channels, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = dilation * (kernel_size - 1) // 2
        self.filter_conv = nn.Conv1d(channels, channels, kernel_size,
                                      dilation=dilation, padding=pad)
        self.gate_conv = nn.Conv1d(channels, channels, kernel_size,
                                    dilation=dilation, padding=pad)
        self.res_conv = nn.Conv1d(channels, channels, 1)
        self.skip_conv = nn.Conv1d(channels, channels, 1)
        self.dropout = nn.Dropout(dropout)
        self.se = SEBlock(channels)
        n_groups = min(16, channels)
        while channels % n_groups != 0:
            n_groups -= 1
        self.norm = nn.GroupNorm(n_groups, channels)

    def forward(self, x):
        h = self.dropout(x)
        f = torch.tanh(self.filter_conv(h))
        g = torch.sigmoid(self.gate_conv(h))
        h = f * g
        h = self.se(h)
        skip = self.skip_conv(h)
        res = self.res_conv(h) + x
        res = self.norm(res)
        return res, skip


class DilatedBlockCBAM(nn.Module):
    """DilatedBlock + CBAM attention."""
    def __init__(self, channels, kernel_size=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = dilation * (kernel_size - 1) // 2
        self.filter_conv = nn.Conv1d(channels, channels, kernel_size,
                                      dilation=dilation, padding=pad)
        self.gate_conv = nn.Conv1d(channels, channels, kernel_size,
                                    dilation=dilation, padding=pad)
        self.res_conv = nn.Conv1d(channels, channels, 1)
        self.skip_conv = nn.Conv1d(channels, channels, 1)
        self.dropout = nn.Dropout(dropout)
        self.cbam = CBAMBlock(channels)
        n_groups = min(16, channels)
        while channels % n_groups != 0:
            n_groups -= 1
        self.norm = nn.GroupNorm(n_groups, channels)

    def forward(self, x):
        h = self.dropout(x)
        f = torch.tanh(self.filter_conv(h))
        g = torch.sigmoid(self.gate_conv(h))
        h = f * g
        h = self.cbam(h)
        skip = self.skip_conv(h)
        res = self.res_conv(h) + x
        res = self.norm(res)
        return res, skip


class EfficientEGGNetSE(nn.Module):
    """EfficientEGGNet with Squeeze-and-Excitation blocks."""
    def __init__(self, channels=128, n_layers=30, kernel_size=5,
                 n_stacks=5, dropout=0.05):
        super().__init__()
        self.n_layers = n_layers
        self.n_stacks = n_stacks
        layers_per_stack = n_layers // n_stacks

        self.input_conv = nn.Sequential(
            nn.Conv1d(1, channels, 1), nn.GELU(),
            nn.Conv1d(channels, channels, 3, padding=1),
        )
        self.blocks = nn.ModuleList()
        for stack in range(n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                self.blocks.append(DilatedBlockSE(channels, kernel_size, dilation, dropout))

        self.output_conv = nn.Sequential(
            nn.GELU(), nn.Conv1d(channels, channels, 1),
            nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )

    def forward(self, x):
        h = self.input_conv(x)
        skip_sum = 0
        for block in self.blocks:
            h, skip = block(h)
            skip_sum = skip_sum + skip
        return self.output_conv(skip_sum)


class EfficientEGGNetCBAM(nn.Module):
    """EfficientEGGNet with CBAM blocks."""
    def __init__(self, channels=128, n_layers=30, kernel_size=5,
                 n_stacks=5, dropout=0.05):
        super().__init__()
        self.n_layers = n_layers
        self.n_stacks = n_stacks
        layers_per_stack = n_layers // n_stacks

        self.input_conv = nn.Sequential(
            nn.Conv1d(1, channels, 1), nn.GELU(),
            nn.Conv1d(channels, channels, 3, padding=1),
        )
        self.blocks = nn.ModuleList()
        for stack in range(n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                self.blocks.append(DilatedBlockCBAM(channels, kernel_size, dilation, dropout))

        self.output_conv = nn.Sequential(
            nn.GELU(), nn.Conv1d(channels, channels, 1),
            nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )

    def forward(self, x):
        h = self.input_conv(x)
        skip_sum = 0
        for block in self.blocks:
            h, skip = block(h)
            skip_sum = skip_sum + skip
        return self.output_conv(skip_sum)


class EfficientEGGNetDeep(nn.Module):
    """Deeper EfficientEGGNet with gradient checkpointing."""
    def __init__(self, channels=128, n_layers=40, kernel_size=5,
                 n_stacks=5, dropout=0.05, use_checkpointing=True):
        super().__init__()
        self.n_layers = n_layers
        self.n_stacks = n_stacks
        self.use_checkpointing = use_checkpointing
        layers_per_stack = n_layers // n_stacks

        self.input_conv = nn.Sequential(
            nn.Conv1d(1, channels, 1), nn.GELU(),
            nn.Conv1d(channels, channels, 3, padding=1),
        )
        self.blocks = nn.ModuleList()
        for stack in range(n_stacks):
            for layer in range(layers_per_stack):
                dilation = 2 ** layer
                self.blocks.append(DilatedBlock(channels, kernel_size, dilation, dropout))

        self.output_conv = nn.Sequential(
            nn.GELU(), nn.Conv1d(channels, channels, 1),
            nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(channels, 1, 1),
        )

    def _block_forward(self, block, x):
        return block(x)

    def forward(self, x):
        h = self.input_conv(x)
        skip_sum = torch.zeros_like(h)
        for block in self.blocks:
            if self.use_checkpointing and self.training:
                # Gradient checkpointing to save memory
                h, skip = grad_checkpoint(self._block_forward, block, h,
                                          use_reentrant=False)
            else:
                h, skip = block(h)
            skip_sum = skip_sum + skip
        return self.output_conv(skip_sum)


# ============================================================
# Data Augmentation (alignment-preserving)
# ============================================================
class AugmentedSVDDataset(Dataset):
    """Wraps SVDEggDataset with alignment-preserving augmentations.
    
    Only augmentations that apply identically to both MIC and EGG
    (preserving temporal alignment) OR only to MIC:
      - Additive noise (MIC only — EGG is clean target)
      - Gain variation (both — scale jitter) 
      - Polarity flip (both — random sign flip)
    """
    def __init__(self, base_dataset, noise_std=0.01, gain_range=0.1,
                 polarity_flip=True):
        self.base = base_dataset
        self.noise_std = noise_std
        self.gain_range = gain_range
        self.polarity_flip = polarity_flip

    def __len__(self):
        return len(self.base)

    def __getitem__(self, idx):
        x, y = self.base[idx]  # [1, T] each

        if self.training_mode:
            # 1. Additive noise on MIC only
            if self.noise_std > 0:
                noise = torch.randn_like(x) * self.noise_std
                x = x + noise

            # 2. Gain variation (both)
            if self.gain_range > 0:
                gain = 1.0 + (torch.rand(1).item() * 2 - 1) * self.gain_range
                x = x * gain
                y = y * gain

            # 3. Polarity flip (both)
            if self.polarity_flip and torch.rand(1).item() > 0.5:
                x = -x
                y = -y

        return x, y

    @property
    def training_mode(self):
        return getattr(self, '_training', True)

    def train(self):
        self._training = True

    def eval(self):
        self._training = False


class MixupDataset(Dataset):
    """Wraps SVDEggDataset with Mixup augmentation."""
    def __init__(self, base_dataset, alpha=0.2):
        self.base = base_dataset
        self.alpha = alpha

    def __len__(self):
        return len(self.base)

    def __getitem__(self, idx):
        x1, y1 = self.base[idx]

        if self.alpha > 0 and getattr(self, '_training', True):
            idx2 = np.random.randint(0, len(self.base))
            x2, y2 = self.base[idx2]
            lam = np.random.beta(self.alpha, self.alpha)
            x = lam * x1 + (1 - lam) * x2
            y = lam * y1 + (1 - lam) * y2
            return x, y
        return x1, y1

    def train(self):
        self._training = True

    def eval(self):
        self._training = False


# ============================================================
# Training utilities
# ============================================================
def train_epoch(model, loader, optimizer, scheduler, criterion, device, scaler):
    model.train()
    total_loss, total_corr, n = 0, 0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast('cuda'):
            pred = model(x)
            if pred.shape != y.shape:
                min_t = min(pred.shape[-1], y.shape[-1])
                pred = pred[..., :min_t]
                y = y[..., :min_t]
            loss = criterion(pred, y)
        if torch.isnan(loss) or torch.isinf(loss):
            continue
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        if scheduler is not None:
            scheduler.step()
        total_loss += loss.item()
        total_corr += pearson_corr_batch(pred.detach().float(), y)
        n += 1
    if n == 0:
        return float('nan'), float('nan')
    return total_loss / n, total_corr / n


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    total_corr, total_mse, n = 0, 0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x)
        if pred.shape != y.shape:
            min_t = min(pred.shape[-1], y.shape[-1])
            pred = pred[..., :min_t]
            y = y[..., :min_t]
        mse = F.mse_loss(pred, y).item()
        corr = pearson_corr_batch(pred, y)
        total_mse += mse
        total_corr += corr
        n += 1
    if n == 0:
        return 0, 0, 0
    return total_corr / n, total_mse / n, 1 - total_mse / n


# ============================================================
# Visualization
# ============================================================
def stitle(ax, text, fp=FPROP):
    ax.set_title(text, fontproperties=fp) if fp else ax.set_title(text)


def plot_training_history(history, save_path, exp_name=''):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    epochs = range(1, len(history['train_loss']) + 1)
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train', lw=1.5)
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val', lw=1.5)
    stitle(axes[0], 'Loss')
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    axes[1].plot(epochs, history['train_corr'], 'b-', label='Train', lw=1.5)
    axes[1].plot(epochs, history['val_corr'], 'r-', label='Val', lw=1.5)
    axes[1].axhline(y=0.8, color='g', ls='--', alpha=0.7, label='Target (0.8)')
    axes[1].axhline(y=0.7484, color='orange', ls=':', alpha=0.7, label='Best (0.7484)')
    stitle(axes[1], 'Correlation')
    axes[1].legend(); axes[1].grid(True, alpha=0.3)

    if 'lr' in history:
        axes[2].plot(epochs, history['lr'], 'g-', lw=1.5)
        stitle(axes[2], 'Learning Rate')
        axes[2].grid(True, alpha=0.3)

    plt.suptitle(exp_name, fontproperties=FPROP_T if FPROP_T else None, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_predictions(model, test_loader, device, save_path, n=5, exp_name=''):
    model.eval()
    all_x, all_y, all_p = [], [], []
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            p = model(x)
            if p.shape != y.shape:
                mt = min(p.shape[-1], y.shape[-1])
                p = p[..., :mt]; y = y[..., :mt]; x = x[..., :mt]
            all_x.append(x.cpu()); all_y.append(y.cpu()); all_p.append(p.cpu())
            if sum(a.size(0) for a in all_x) >= n:
                break
    all_x = torch.cat(all_x)[:n]
    all_y = torch.cat(all_y)[:n]
    all_p = torch.cat(all_p)[:n]

    fig, axes = plt.subplots(n, 2, figsize=(18, 3 * n))
    if n == 1:
        axes = axes.reshape(1, 2)
    for i in range(n):
        mic = all_x[i, 0].numpy()
        gt = all_y[i, 0].numpy()
        pr = all_p[i, 0].numpy()
        c = np.corrcoef(gt, pr)[0, 1] if np.std(gt) > 1e-8 and np.std(pr) > 1e-8 else 0
        axes[i, 0].plot(mic, 'b-', lw=0.5)
        if i == 0:
            stitle(axes[i, 0], 'MIC')
        axes[i, 0].set_ylabel(f'#{i+1}', fontweight='bold')
        axes[i, 0].grid(True, alpha=0.3)
        axes[i, 1].plot(gt, 'b-', label='GT', lw=0.8)
        axes[i, 1].plot(pr, 'orange', label='Pred', lw=0.8, alpha=0.85)
        if i == 0:
            stitle(axes[i, 1], 'GT vs Pred EGG')
        axes[i, 1].text(0.02, 0.85, f'r={c:.4f}', transform=axes[i, 1].transAxes,
                         fontsize=10, fontweight='bold',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[i, 1].legend(loc='upper right', fontsize=7)
        axes[i, 1].grid(True, alpha=0.3)
    plt.suptitle(exp_name, fontproperties=FPROP_T if FPROP_T else None, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_error_analysis(model, test_loader, device, save_path, exp_name=''):
    model.eval()
    corrs = []
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            p = model(x)
            if p.shape != y.shape:
                mt = min(p.shape[-1], y.shape[-1])
                p = p[..., :mt]; y = y[..., :mt]
            pp = p.squeeze(1); yy = y.squeeze(1)
            pc = pp - pp.mean(dim=1, keepdim=True)
            tc = yy - yy.mean(dim=1, keepdim=True)
            num = (pc * tc).sum(dim=1)
            den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
            batch_corrs = (num / den).cpu().numpy()
            corrs.extend(batch_corrs.tolist())
    corrs = np.array(corrs)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(corrs, bins=50, color='steelblue', edgecolor='black', alpha=0.8)
    axes[0].axvline(np.mean(corrs), color='red', ls='--', lw=2,
                     label=f'Mean={np.mean(corrs):.4f}')
    axes[0].axvline(np.median(corrs), color='orange', ls='--', lw=2,
                     label=f'Median={np.median(corrs):.4f}')
    stitle(axes[0], 'Per-window Correlation Distribution')
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    sorted_c = np.sort(corrs)
    axes[1].plot(sorted_c, np.linspace(0, 1, len(sorted_c)), 'b-', lw=2)
    axes[1].axvline(0.8, color='g', ls='--', alpha=0.7, label='Target 0.8')
    axes[1].axhline(0.5, color='gray', ls=':', alpha=0.5)
    pct_above_08 = (corrs >= 0.8).mean() * 100
    pct_above_07 = (corrs >= 0.7).mean() * 100
    axes[1].text(0.05, 0.9, f'>0.8: {pct_above_08:.1f}%\n>0.7: {pct_above_07:.1f}%',
                 transform=axes[1].transAxes, fontsize=11,
                 bbox=dict(boxstyle='round', facecolor='lightyellow'))
    stitle(axes[1], 'CDF')
    axes[1].legend(); axes[1].grid(True, alpha=0.3)

    plt.suptitle(f'{exp_name} Error Analysis', fontproperties=FPROP_T if FPROP_T else None)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_visualizations(model, test_loader, device, save_dir, exp_name, history=None):
    os.makedirs(save_dir, exist_ok=True)
    try:
        if history:
            plot_training_history(history, os.path.join(save_dir, 'training_history.png'), exp_name)
        plot_predictions(model, test_loader, device,
                         os.path.join(save_dir, 'prediction_comparison.png'), n=5, exp_name=exp_name)
        plot_error_analysis(model, test_loader, device,
                            os.path.join(save_dir, 'error_analysis.png'), exp_name)
        log(f"  Visualizations saved: {save_dir}")
    except Exception as e:
        log(f"  Visualization error: {e}")


# ============================================================
# Core training function (enhanced)
# ============================================================
def run_training(model, train_loader, val_loader, test_loader, device,
                 exp_name, max_epochs=80, lr=0.001, weight_decay=1e-4,
                 loss_alpha=0.2, patience=15, criterion=None,
                 scheduler_type='onecycle', scheduler_kwargs=None,
                 warmup_from_checkpoint=None):
    """Generic training loop. Returns (test_corr, test_mse, test_r2, history, model)."""
    results_dir = os.path.join(PROJECT_DIR, 'results', exp_name)
    ckpt_dir = os.path.join(PROJECT_DIR, 'checkpoints', exp_name)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    log(f"  Model params: {n_params:,}")

    # Optionally load pretrained weights
    if warmup_from_checkpoint is not None:
        try:
            ckpt = torch.load(warmup_from_checkpoint, map_location=device, weights_only=False)
            model.load_state_dict(ckpt['model_state_dict'], strict=False)
            log(f"  Loaded pretrained weights from {warmup_from_checkpoint}")
        except Exception as e:
            log(f"  Could not load pretrained weights: {e}")

    if criterion is None:
        criterion = CombinedLoss(alpha=loss_alpha)

    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * max_epochs

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    if scheduler_type == 'cosine_warm_restarts':
        sk = scheduler_kwargs or {}
        scheduler = CosineAnnealingWarmRestarts(
            optimizer, T_0=sk.get('T_0', 10), T_mult=sk.get('T_mult', 2),
            eta_min=sk.get('eta_min', 1e-6)
        )
        step_scheduler_per_batch = False
    else:
        scheduler = OneCycleLR(optimizer, max_lr=lr, total_steps=total_steps,
                               pct_start=0.1, anneal_strategy='cos',
                               div_factor=10, final_div_factor=100)
        step_scheduler_per_batch = True

    scaler = torch.amp.GradScaler('cuda')

    history = {'train_loss': [], 'train_corr': [], 'val_loss': [],
               'val_corr': [], 'lr': []}
    best_val_corr = -1
    patience_counter = 0
    start = time.time()

    for epoch in range(1, max_epochs + 1):
        t0 = time.time()

        if step_scheduler_per_batch:
            tr_loss, tr_corr = train_epoch(model, train_loader, optimizer,
                                            scheduler, criterion, device, scaler)
        else:
            tr_loss, tr_corr = train_epoch(model, train_loader, optimizer,
                                            None, criterion, device, scaler)
            scheduler.step()

        va_corr, va_mse, _ = evaluate(model, val_loader, device)

        lr_now = optimizer.param_groups[0]['lr']
        history['train_loss'].append(tr_loss)
        history['train_corr'].append(tr_corr)
        history['val_loss'].append(va_mse)
        history['val_corr'].append(va_corr)
        history['lr'].append(lr_now)

        dt = time.time() - t0
        improved = ''
        if va_corr > best_val_corr:
            best_val_corr = va_corr
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_corr': va_corr,
                'config': exp_name,
            }, os.path.join(ckpt_dir, 'best_model.pt'))
            improved = ' ★'
        else:
            patience_counter += 1

        if epoch % 5 == 0 or improved:
            log(f"  [{exp_name}] Ep {epoch:3d}/{max_epochs} | "
                f"TrCorr={tr_corr:.4f} VaCorr={va_corr:.4f} | "
                f"LR={lr_now:.6f} | {dt:.1f}s{improved}")

        if patience_counter >= patience:
            log(f"  Early stopping at epoch {epoch}")
            break

    train_time = time.time() - start
    log(f"  Training time: {train_time/60:.1f} min")

    # Load best and test
    ckpt = torch.load(os.path.join(ckpt_dir, 'best_model.pt'),
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    test_corr, test_mse, test_r2 = evaluate(model, test_loader, device)

    log(f"  TEST → Corr={test_corr:.4f} MSE={test_mse:.6f} R²={test_r2:.4f}")

    # Save metrics
    metrics = {
        'experiment': exp_name, 'params': n_params,
        'train_time_min': round(train_time / 60, 1),
        'best_epoch': int(ckpt['epoch']), 'best_val_corr': float(best_val_corr),
        'test_corr': float(test_corr), 'test_mse': float(test_mse),
        'test_r2': float(test_r2),
    }
    with open(os.path.join(results_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(results_dir, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    return test_corr, test_mse, test_r2, history, model


# ============================================================
# Data loading utilities
# ============================================================
def load_standard_data(window_length=8192, hop_length=4096, batch_size=16):
    """Load data matching exp11 config."""
    return create_dataloaders(
        SVD_PATH, batch_size=batch_size, window_length=window_length,
        hop_length=hop_length, target_sr=16000, num_workers=4, seed=42
    )


def load_quality_filtered_data(window_length=8192, hop_length=4096,
                               batch_size=16, min_corr=0.6):
    """Load data with quality filtering on training set."""
    log(f"  Loading quality-filtered data (min_corr={min_corr})...")
    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))

    rng = np.random.RandomState(42)
    shuffled = list(all_speakers); rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.8); n_val = int(n * 0.1)
    train_sp = set(shuffled[:n_train])
    val_sp = set(shuffled[n_train:n_train + n_val])
    test_sp = set(shuffled[n_train + n_val:])

    train_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in train_sp]
    val_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in val_sp]
    test_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in test_sp]

    # Filter training pairs by raw correlation
    filtered_train = []
    skipped = 0
    for nsp_path, egg_path, spk in train_pairs:
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            if np.std(speech) > 1e-8 and np.std(egg) > 1e-8:
                raw_corr = abs(np.corrcoef(speech, egg)[0, 1])
            else:
                raw_corr = 0
            if raw_corr >= min_corr:
                filtered_train.append((nsp_path, egg_path, spk))
            else:
                skipped += 1
        except:
            skipped += 1

    log(f"  Train: {len(train_pairs)} → {len(filtered_train)} (filtered {skipped})")

    train_ds = SVDEggDataset(filtered_train, window_length, hop_length, 16000, split_name="train_hq")
    val_ds = SVDEggDataset(val_pairs, window_length, hop_length, 16000, split_name="val")
    test_ds = SVDEggDataset(test_pairs, window_length, hop_length, 16000, split_name="test")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=4, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=4, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=4, pin_memory=True)

    split_info = {'train_files': len(filtered_train), 'val_files': len(val_pairs),
                  'test_files': len(test_pairs)}
    return train_loader, val_loader, test_loader, split_info


# ============================================================
# Experiment definitions
# ============================================================

def run_exp13(device):
    """Exp13: exp11 + strong regularization (dropout 0.3, wd 1e-3, label smoothing)."""
    exp_name = 'exp13_multiscale_regularized'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 base + dropout 0.3, weight_decay 1e-3, label_smoothing 0.1")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.3,  # 0.05 → 0.3
    })

    criterion = LabelSmoothingCombinedLoss(alpha=0.2, smoothing=0.1)

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=100, lr=0.001, weight_decay=1e-3,  # 1e-4 → 1e-3
        patience=20, criterion=criterion,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp14(device):
    """Exp14: exp11 + data augmentation (noise, gain, polarity flip)."""
    exp_name = 'exp14_multiscale_augmented'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 base + noise(0.01), gain(0.1), polarity flip")
    log(f"{'='*60}")

    train_loader_raw, val_loader, test_loader, _ = load_standard_data()

    # Wrap training dataset with augmentation
    aug_ds = AugmentedSVDDataset(train_loader_raw.dataset,
                                  noise_std=0.01, gain_range=0.1, polarity_flip=True)
    aug_ds.train()
    train_loader = DataLoader(aug_ds, batch_size=16, shuffle=True,
                              num_workers=4, pin_memory=True, drop_last=True)

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.1,  # slightly higher
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=100, lr=0.001, loss_alpha=0.2, patience=20,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp15(device):
    """Exp15: exp11 + Mixup augmentation."""
    exp_name = 'exp15_multiscale_mixup'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 base + Mixup(alpha=0.2)")
    log(f"{'='*60}")

    train_loader_raw, val_loader, test_loader, _ = load_standard_data()

    mixup_ds = MixupDataset(train_loader_raw.dataset, alpha=0.2)
    mixup_ds.train()
    train_loader = DataLoader(mixup_ds, batch_size=16, shuffle=True,
                              num_workers=4, pin_memory=True, drop_last=True)

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=100, lr=0.001, loss_alpha=0.2, patience=20,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp16(device):
    """Exp16: exp11 + Squeeze-and-Excitation blocks."""
    exp_name = 'exp16_multiscale_se'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 architecture + SE block on each dilated layer")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = EfficientEGGNetSE(
        channels=128, n_layers=30, kernel_size=5,
        n_stacks=5, dropout=0.05,
    )

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.2, patience=15,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp17(device):
    """Exp17: exp11 + CBAM (Channel + Spatial Attention) blocks."""
    exp_name = 'exp17_multiscale_cbam'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 architecture + CBAM on each dilated layer")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = EfficientEGGNetCBAM(
        channels=128, n_layers=30, kernel_size=5,
        n_stacks=5, dropout=0.05,
    )

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.2, patience=15,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp18(device):
    """Exp18: Deeper multiscale (40 layers, gradient checkpointing)."""
    exp_name = 'exp18_deeper_multiscale'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: 40 layers (vs 30), 8 stacks, gradient checkpointing for memory")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = EfficientEGGNetDeep(
        channels=128, n_layers=40, kernel_size=5,
        n_stacks=8, dropout=0.05, use_checkpointing=True,
    )

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.2, patience=15,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp19(device):
    """Exp19: Cosine Annealing with Warm Restarts."""
    exp_name = 'exp19_cosine_warmup'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 + CosineAnnealingWarmRestarts(T_0=10, T_mult=2)")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=100, lr=0.001, loss_alpha=0.2, patience=25,
        scheduler_type='cosine_warm_restarts',
        scheduler_kwargs={'T_0': 10, 'T_mult': 2, 'eta_min': 1e-6},
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp20(device):
    """Exp20: Progressive window resizing (smaller → larger)."""
    exp_name = 'exp20_progressive'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: Train with window 4096 → 8192 → 16384 progressively")
    log(f"{'='*60}")

    results_dir = os.path.join(PROJECT_DIR, 'results', exp_name)
    ckpt_dir = os.path.join(PROJECT_DIR, 'checkpoints', exp_name)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })
    model = model.to(device)

    phases = [
        {'window': 4096, 'hop': 2048, 'batch': 32, 'epochs': 20, 'lr': 0.001},
        {'window': 8192, 'hop': 4096, 'batch': 16, 'epochs': 40, 'lr': 0.0005},
        {'window': 16384, 'hop': 8192, 'batch': 8, 'epochs': 40, 'lr': 0.0003},
    ]

    history = {'train_loss': [], 'train_corr': [], 'val_loss': [], 'val_corr': [], 'lr': []}
    best_val_corr = -1
    criterion = CombinedLoss(alpha=0.2)

    for phase_idx, phase in enumerate(phases):
        log(f"  Phase {phase_idx+1}/3: window={phase['window']}, batch={phase['batch']}, lr={phase['lr']}")

        try:
            train_loader, val_loader, test_loader, _ = create_dataloaders(
                SVD_PATH, batch_size=phase['batch'], window_length=phase['window'],
                hop_length=phase['hop'], target_sr=16000, num_workers=4, seed=42
            )
        except Exception as e:
            log(f"  Phase {phase_idx+1} data load failed: {e}")
            continue

        optimizer = torch.optim.AdamW(model.parameters(), lr=phase['lr'], weight_decay=1e-4)
        total_steps = len(train_loader) * phase['epochs']
        scheduler = OneCycleLR(optimizer, max_lr=phase['lr'], total_steps=total_steps,
                               pct_start=0.1, anneal_strategy='cos',
                               div_factor=10, final_div_factor=100)
        scaler = torch.amp.GradScaler('cuda')
        patience_counter = 0

        for epoch in range(1, phase['epochs'] + 1):
            t0 = time.time()
            tr_loss, tr_corr = train_epoch(model, train_loader, optimizer,
                                            scheduler, criterion, device, scaler)
            va_corr, va_mse, _ = evaluate(model, val_loader, device)

            lr_now = optimizer.param_groups[0]['lr']
            history['train_loss'].append(tr_loss)
            history['train_corr'].append(tr_corr)
            history['val_loss'].append(va_mse)
            history['val_corr'].append(va_corr)
            history['lr'].append(lr_now)

            dt = time.time() - t0
            improved = ''
            if va_corr > best_val_corr:
                best_val_corr = va_corr
                patience_counter = 0
                torch.save({
                    'epoch': sum(p['epochs'] for p in phases[:phase_idx]) + epoch,
                    'model_state_dict': model.state_dict(),
                    'val_corr': va_corr,
                    'phase': phase_idx + 1,
                }, os.path.join(ckpt_dir, 'best_model.pt'))
                improved = ' ★'
            else:
                patience_counter += 1

            if epoch % 5 == 0 or improved:
                log(f"  [Phase {phase_idx+1}] Ep {epoch:3d}/{phase['epochs']} | "
                    f"TrCorr={tr_corr:.4f} VaCorr={va_corr:.4f} | "
                    f"LR={lr_now:.6f} | {dt:.1f}s{improved}")

            if patience_counter >= 15:
                log(f"  Phase {phase_idx+1} early stop at epoch {epoch}")
                break

    # Load best and final test
    ckpt = torch.load(os.path.join(ckpt_dir, 'best_model.pt'),
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])

    # Test with largest window
    _, _, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=8, window_length=16384, hop_length=8192,
        target_sr=16000, num_workers=4, seed=42
    )
    test_corr, test_mse, test_r2 = evaluate(model, test_loader, device)
    log(f"  TEST → Corr={test_corr:.4f} MSE={test_mse:.6f} R²={test_r2:.4f}")

    metrics = {
        'experiment': exp_name, 'test_corr': float(test_corr),
        'test_mse': float(test_mse), 'test_r2': float(test_r2),
        'phases': [{'window': p['window'], 'epochs': p['epochs']} for p in phases],
    }
    with open(os.path.join(results_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(results_dir, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    vis_dir = os.path.join(results_dir, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp21(device):
    """Exp21: High-quality data only (raw_corr >= 0.6)."""
    exp_name = 'exp21_high_quality_only'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 base + train only on data with raw speech-EGG corr >= 0.6")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_quality_filtered_data(
        window_length=8192, hop_length=4096, batch_size=16, min_corr=0.6
    )

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.2, patience=15,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp22(device):
    """Exp22: Multi-Scale Loss (MSE + Corr + Spectral)."""
    exp_name = 'exp22_multiscale_loss'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 + spectral convergence loss (multi-resolution STFT)")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })

    criterion = MultiScaleLoss(alpha_mse=0.3, alpha_corr=0.5, alpha_spec=0.2,
                                fft_sizes=(256, 512, 1024))

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, patience=15, criterion=criterion,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp23(device):
    """Exp23: Perceptual Loss (feature-matching)."""
    exp_name = 'exp23_perceptual_loss'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log("Strategy: exp11 + perceptual loss on learned intermediate features")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = load_standard_data()

    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,
        'n_stacks': 5, 'dropout': 0.05,
    })

    criterion = PerceptualLoss(alpha=0.2, perceptual_weight=0.3)
    criterion = criterion.to(device)

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, patience=15, criterion=criterion,
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


# ============================================================
# Main auto-experiment loop
# ============================================================
def main():
    log("=" * 60)
    log("AUTO EXPERIMENT V2 — EGG 예측 모델 자동 최적화")
    log(f"목표: Test Correlation >= 0.8")
    log(f"현재 Best: 0.7484 (exp11_multiscale)")
    log(f"Base: EfficientEGGNet(ch=128, layers=30, k=5, stacks=5)")
    log("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log(f"Device: {device}")
    if torch.cuda.is_available():
        log(f"GPU: {torch.cuda.get_device_name(0)}")
        mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        log(f"Memory: {mem_gb:.1f} GB")

    best_corr = 0.7484
    target = 0.8
    results_summary = []

    experiments = [
        # Phase 1: 과적합 방지
        ('exp13_multiscale_regularized', run_exp13),
        ('exp14_multiscale_augmented', run_exp14),
        ('exp15_multiscale_mixup', run_exp15),
        # Phase 2: 모델 구조 개선
        ('exp16_multiscale_se', run_exp16),
        ('exp17_multiscale_cbam', run_exp17),
        ('exp18_deeper_multiscale', run_exp18),
        # Phase 3: 학습 방법 개선
        ('exp19_cosine_warmup', run_exp19),
        ('exp20_progressive', run_exp20),
        ('exp21_high_quality_only', run_exp21),
        # Phase 4: Loss 개선
        ('exp22_multiscale_loss', run_exp22),
        ('exp23_perceptual_loss', run_exp23),
    ]

    log(f"Total experiments: {len(experiments)}")
    log(f"Experiments: {[e[0] for e in experiments]}")
    log("")

    for exp_name, exp_fn in experiments:
        log(f"\n{'='*60}")
        log(f">>> Experiment: {exp_name}")
        log(f">>> Current Best: {best_corr:.4f}")
        log(f"{'='*60}")

        try:
            test_corr, model = exp_fn(device)

            results_summary.append({
                'experiment': exp_name,
                'test_corr': float(test_corr),
                'is_best': bool(test_corr > best_corr),
                'timestamp': datetime.now().isoformat(),
            })

            if test_corr > best_corr:
                log(f"🎉 NEW BEST! {best_corr:.4f} → {test_corr:.4f} ({exp_name})")
                best_corr = test_corr

                # Extra visualization for new best
                if model is not None:
                    new_best_vis = os.path.join(PROJECT_DIR, 'results', exp_name,
                                                'visualizations', 'new_best')
                    try:
                        _, _, tl, _ = load_standard_data()
                        generate_visualizations(model, tl, device, new_best_vis, exp_name)
                    except Exception as ve:
                        log(f"  New best visualization error: {ve}")

            if test_corr >= target:
                log(f"🏆 TARGET ACHIEVED! Corr = {test_corr:.4f} >= {target}")
                break
            else:
                log(f"Target not reached ({test_corr:.4f} < {target}). Continuing...")

        except Exception as e:
            log(f"❌ {exp_name} FAILED: {str(e)}")
            log(traceback.format_exc())
            results_summary.append({
                'experiment': exp_name,
                'test_corr': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            })

        # Cleanup GPU memory
        gc.collect()
        torch.cuda.empty_cache()

    # Final summary
    log("\n" + "=" * 60)
    log("실험 종료 — 최종 요약 (V2)")
    log("=" * 60)
    log(f"{'Experiment':<35} {'Corr':>8} {'Best?':>6}")
    log("-" * 55)
    for r in results_summary:
        mark = "★" if r.get('is_best') else ""
        corr_str = f"{r['test_corr']:.4f}" if r['test_corr'] > 0 else "FAIL"
        log(f"{r['experiment']:<35} {corr_str:>8} {mark:>6}")
    log("-" * 55)
    log(f"Final Best Corr: {best_corr:.4f}")
    log(f"Target ({target}): {'ACHIEVED ✅' if best_corr >= target else 'NOT REACHED ❌'}")

    # Save summary
    summary_path = os.path.join(PROJECT_DIR, 'results/experiment_summary_v2.json')
    with open(summary_path, 'w') as f:
        json.dump({
            'final_best_corr': float(best_corr),
            'target': float(target),
            'target_achieved': bool(best_corr >= target),
            'experiments': results_summary,
        }, f, indent=2, default=str)
    log(f"Summary saved: {summary_path}")


if __name__ == '__main__':
    main()
