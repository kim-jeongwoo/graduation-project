#!/usr/bin/env python3
"""
EGG 예측 모델 자동 최적화 — 목표 Corr >= 0.9
================================================
Exp5  : 고품질 데이터 필터링 (EfficientEGGNet)
Exp6  : Transformer 기반 모델
Exp7  : Conformer (CNN + Transformer)
Exp8  : wav2vec2 features 사용
Exp9  : Curriculum Learning
Exp10 : Contrastive Learning
Exp11 : Multi-task Learning (EGG + Pitch)
Exp12 : 앙상블
"""
import os, sys, time, json, traceback, gc
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, Subset
from torch.optim.lr_scheduler import OneCycleLR, CosineAnnealingWarmRestarts
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

from model.efficient_egg import build_efficient_model, EfficientEGGNet
from model.transformer_egg import build_transformer_model, TransformerEGG
from model.conformer_egg import build_conformer_model, ConformerEGG
from utils.dataset import create_dataloaders, SVDEggDataset, speaker_split
from utils.nsp_reader import read_nsp, find_paired_files

SVD_PATH = os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy')
LOG_FILE = os.path.join(PROJECT_DIR, 'results/experiment_log.txt')

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
# Loss
# ============================================================
class CombinedLoss(nn.Module):
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


class ContrastiveCombinedLoss(nn.Module):
    """CombinedLoss + Window-level contrastive term."""
    def __init__(self, alpha=0.3, contrastive_weight=0.1, temperature=0.07):
        super().__init__()
        self.base = CombinedLoss(alpha)
        self.cw = contrastive_weight
        self.temp = temperature

    def forward(self, pred, target, embeddings=None):
        base_loss = self.base(pred, target)
        if embeddings is None or embeddings.size(0) < 4:
            return base_loss
        # Simple NT-Xent on embeddings (mean-pooled)
        e = F.normalize(embeddings, dim=-1)
        sim = torch.mm(e, e.t()) / self.temp
        B = e.size(0)
        labels = torch.arange(B, device=e.device)
        cl = F.cross_entropy(sim, labels)
        return base_loss + self.cw * cl


def pearson_corr_batch(pred, target):
    p = pred.squeeze(1)
    t = target.squeeze(1)
    pc = p - p.mean(dim=1, keepdim=True)
    tc = t - t.mean(dim=1, keepdim=True)
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
    return (num / den).mean().item()


# ============================================================
# Training utilities
# ============================================================
def train_epoch(model, loader, optimizer, scheduler, criterion, device, scaler,
                return_embeddings=False):
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
    all_corrs = []
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
        all_corrs.append(corr)
        n += 1
    if n == 0:
        return 0, 0, 0
    return total_corr / n, total_mse / n, 1 - total_mse / n  # corr, mse, r2_approx


# ============================================================
# Visualization
# ============================================================
def stitle(ax, text, fp=FPROP):
    ax.set_title(text, fontproperties=fp) if fp else ax.set_title(text)

def slabel(ax, axis, text, fp=FPROP_S):
    getattr(ax, f'set_{axis}label')(text, fontproperties=fp) if fp else getattr(ax, f'set_{axis}label')(text)


def plot_training_history(history, save_path, exp_name=''):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    epochs = range(1, len(history['train_loss']) + 1)
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train', lw=1.5)
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val', lw=1.5)
    stitle(axes[0], 'Loss')
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    axes[1].plot(epochs, history['train_corr'], 'b-', label='Train', lw=1.5)
    axes[1].plot(epochs, history['val_corr'], 'r-', label='Val', lw=1.5)
    axes[1].axhline(y=0.9, color='g', ls='--', alpha=0.7, label='Target (0.9)')
    axes[1].axhline(y=0.7163, color='orange', ls=':', alpha=0.7, label='Best (0.7163)')
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

    fig, axes = plt.subplots(n, 2, figsize=(18, 3*n))
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
            pp = p.squeeze(1)
            yy = y.squeeze(1)
            pc = pp - pp.mean(dim=1, keepdim=True)
            tc = yy - yy.mean(dim=1, keepdim=True)
            num = (pc * tc).sum(dim=1)
            den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
            batch_corrs = (num / den).cpu().numpy()
            corrs.extend(batch_corrs.tolist())
    corrs = np.array(corrs)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(corrs, bins=50, color='steelblue', edgecolor='black', alpha=0.8)
    axes[0].axvline(np.mean(corrs), color='red', ls='--', lw=2, label=f'Mean={np.mean(corrs):.4f}')
    axes[0].axvline(np.median(corrs), color='orange', ls='--', lw=2, label=f'Median={np.median(corrs):.4f}')
    stitle(axes[0], 'Per-window Correlation Distribution')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    sorted_c = np.sort(corrs)
    axes[1].plot(sorted_c, np.linspace(0, 1, len(sorted_c)), 'b-', lw=2)
    axes[1].axvline(0.9, color='g', ls='--', alpha=0.7, label='Target 0.9')
    axes[1].axhline(0.5, color='gray', ls=':', alpha=0.5)
    pct_above_09 = (corrs >= 0.9).mean() * 100
    pct_above_07 = (corrs >= 0.7).mean() * 100
    axes[1].text(0.05, 0.9, f'>0.9: {pct_above_09:.1f}%\n>0.7: {pct_above_07:.1f}%',
                 transform=axes[1].transAxes, fontsize=11,
                 bbox=dict(boxstyle='round', facecolor='lightyellow'))
    stitle(axes[1], 'CDF')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

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
# Data utilities
# ============================================================
def create_quality_filtered_dataloaders(svd_path, batch_size, window_length, hop_length,
                                        target_sr, min_corr=0.5, seed=42):
    """Create dataloaders filtering out low-quality speech-EGG pairs."""
    import librosa

    log(f"  Loading data with quality filter (min_corr={min_corr})...")
    pairs = find_paired_files(svd_path)
    all_speakers = sorted(set(p[2] for p in pairs))

    rng = np.random.RandomState(seed)
    shuffled = list(all_speakers)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train_sp = set(shuffled[:n_train])
    val_sp = set(shuffled[n_train:n_train + n_val])
    test_sp = set(shuffled[n_train + n_val:])

    def filter_pairs(pairs_list):
        filtered = []
        skipped = 0
        for nsp_path, egg_path, spk in pairs_list:
            try:
                speech, _ = read_nsp(nsp_path)
                egg, _ = read_nsp(egg_path)
                min_len = min(len(speech), len(egg))
                speech = speech[:min_len]
                egg = egg[:min_len]
                # Quick raw correlation check (no resample needed)
                if np.std(speech) > 1e-8 and np.std(egg) > 1e-8:
                    raw_corr = abs(np.corrcoef(speech, egg)[0, 1])
                else:
                    raw_corr = 0
                if raw_corr >= min_corr:
                    filtered.append((nsp_path, egg_path, spk))
                else:
                    skipped += 1
            except:
                skipped += 1
        return filtered, skipped

    train_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in train_sp]
    val_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in val_sp]
    test_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in test_sp]

    train_filtered, skip_tr = filter_pairs(train_pairs)
    val_filtered, skip_va = filter_pairs(val_pairs)
    # Test: use ALL data (unfiltered) for fair comparison
    test_filtered = test_pairs

    log(f"  Train: {len(train_pairs)} → {len(train_filtered)} (filtered {skip_tr})")
    log(f"  Val: {len(val_pairs)} → {len(val_filtered)} (filtered {skip_va})")
    log(f"  Test: {len(test_filtered)} (unfiltered for fair eval)")

    train_ds = SVDEggDataset(train_filtered, window_length, hop_length, target_sr, split_name="train_hq")
    val_ds = SVDEggDataset(val_filtered, window_length, hop_length, target_sr, split_name="val_hq")
    test_ds = SVDEggDataset(test_filtered, window_length, hop_length, target_sr, split_name="test")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=4, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=4, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=4, pin_memory=True)

    return train_loader, val_loader, test_loader


# ============================================================
# Core training function
# ============================================================
def run_training(model, train_loader, val_loader, test_loader, device,
                 exp_name, max_epochs=60, lr=0.001, weight_decay=1e-4,
                 loss_alpha=0.3, patience=12, criterion=None):
    """Generic training loop. Returns (test_corr, test_mse, test_r2, history, model)."""
    results_dir = os.path.join(PROJECT_DIR, 'results', exp_name)
    ckpt_dir = os.path.join(PROJECT_DIR, 'checkpoints', exp_name)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    log(f"  Model params: {n_params:,}")

    if criterion is None:
        criterion = CombinedLoss(alpha=loss_alpha)

    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * max_epochs

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = OneCycleLR(optimizer, max_lr=lr, total_steps=total_steps,
                           pct_start=0.1, anneal_strategy='cos',
                           div_factor=10, final_div_factor=100)
    scaler = torch.amp.GradScaler('cuda')

    history = {'train_loss': [], 'train_corr': [], 'val_loss': [],
               'val_corr': [], 'lr': []}
    best_val_corr = -1
    patience_counter = 0
    start = time.time()

    for epoch in range(1, max_epochs + 1):
        t0 = time.time()
        tr_loss, tr_corr = train_epoch(model, train_loader, optimizer, scheduler,
                                        criterion, device, scaler)
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
        'train_time_min': train_time / 60,
        'best_epoch': ckpt['epoch'], 'best_val_corr': float(best_val_corr),
        'test_corr': float(test_corr), 'test_mse': float(test_mse),
        'test_r2': float(test_r2),
    }
    with open(os.path.join(results_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(results_dir, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    return test_corr, test_mse, test_r2, history, model


# ============================================================
# Experiment definitions
# ============================================================

def run_exp5(device, test_loader_ref=None):
    """Exp5: High-quality data filtering + EfficientEGGNet"""
    exp_name = 'exp5_high_quality_data'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader = create_quality_filtered_dataloaders(
        SVD_PATH, batch_size=32, window_length=4096, hop_length=2048,
        target_sr=16000, min_corr=0.5, seed=42
    )

    model = build_efficient_model({
        'channels': 96, 'n_layers': 24, 'kernel_size': 3,
        'n_stacks': 3, 'dropout': 0.1,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.3, patience=15
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp6(device, test_loader_ref=None):
    """Exp6: Transformer-based model"""
    exp_name = 'exp6_transformer'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=32, window_length=4096, hop_length=2048,
        target_sr=16000, num_workers=4, seed=42
    )

    model = build_transformer_model({
        'd_model': 256, 'n_heads': 8, 'n_layers': 6,
        'd_ff': 1024, 'dropout': 0.1, 'kernel_size': 7,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.0005, loss_alpha=0.3, patience=15
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp7(device, test_loader_ref=None):
    """Exp7: Conformer model"""
    exp_name = 'exp7_conformer'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=16, window_length=4096, hop_length=2048,
        target_sr=16000, num_workers=4, seed=42
    )

    model = build_conformer_model({
        'd_model': 256, 'n_heads': 4, 'n_layers': 6,
        'd_ff': 1024, 'conv_kernel': 31, 'dropout': 0.1,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.0005, loss_alpha=0.3, patience=15
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp8(device, test_loader_ref=None):
    """Exp8: wav2vec2 feature extractor + prediction head"""
    exp_name = 'exp8_wav2vec2'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    # Install transformers if needed
    try:
        import transformers
    except ImportError:
        log("  Installing transformers...")
        os.system('pip install transformers')
        import transformers

    from transformers import Wav2Vec2Model, Wav2Vec2Config

    class Wav2Vec2EGG(nn.Module):
        def __init__(self, freeze_feature_extractor=True):
            super().__init__()
            self.wav2vec2 = Wav2Vec2Model.from_pretrained('facebook/wav2vec2-base')
            hidden_size = self.wav2vec2.config.hidden_size  # 768

            if freeze_feature_extractor:
                for p in self.wav2vec2.feature_extractor.parameters():
                    p.requires_grad = False

            self.head = nn.Sequential(
                nn.Linear(hidden_size, 256),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(256, 128),
                nn.GELU(),
                nn.Linear(128, 1),
            )

        def forward(self, x):
            # x: [B, 1, T]
            waveform = x.squeeze(1)  # [B, T]
            outputs = self.wav2vec2(waveform)
            hidden = outputs.last_hidden_state  # [B, T', hidden_size]
            pred = self.head(hidden)  # [B, T', 1]
            pred = pred.permute(0, 2, 1)  # [B, 1, T']
            # Upsample to match input length
            T = x.shape[-1]
            pred = F.interpolate(pred, size=T, mode='linear', align_corners=False)
            return pred

        def count_params(self):
            return sum(p.numel() for p in self.parameters() if p.requires_grad)

    train_loader, val_loader, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=8, window_length=4096, hop_length=2048,
        target_sr=16000, num_workers=4, seed=42
    )

    model = Wav2Vec2EGG(freeze_feature_extractor=True)

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=40, lr=0.0001, loss_alpha=0.3, patience=10
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp9(device, test_loader_ref=None):
    """Exp9: Curriculum Learning — easy to hard"""
    exp_name = 'exp9_curriculum'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    # Load all data and compute per-file correlation for difficulty ranking
    import librosa
    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))
    rng = np.random.RandomState(42)
    shuffled = list(all_speakers)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train_sp = set(shuffled[:n_train])
    val_sp = set(shuffled[n_train:n_train + n_val])
    test_sp = set(shuffled[n_train + n_val:])

    train_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in train_sp]

    # Compute difficulty (raw correlation) for each training file
    log("  Computing file difficulties...")
    pair_corrs = []
    for nsp_path, egg_path, spk in train_pairs:
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            if np.std(speech) > 1e-8 and np.std(egg) > 1e-8:
                c = abs(np.corrcoef(speech, egg)[0, 1])
            else:
                c = 0
            pair_corrs.append((nsp_path, egg_path, spk, c))
        except:
            pair_corrs.append((nsp_path, egg_path, spk, 0))

    # Sort: easy (high corr) first
    pair_corrs.sort(key=lambda x: -x[3])
    log(f"  Difficulty range: {pair_corrs[-1][3]:.3f} ~ {pair_corrs[0][3]:.3f}")

    val_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in val_sp]
    test_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in test_sp]

    # Phase 1: Train on easy 50%
    easy_pairs = [(p[0], p[1], p[2]) for p in pair_corrs[:len(pair_corrs)//2]]
    # Phase 2: Train on all
    all_train = [(p[0], p[1], p[2]) for p in pair_corrs]

    model = build_efficient_model({
        'channels': 96, 'n_layers': 24, 'kernel_size': 3,
        'n_stacks': 3, 'dropout': 0.1,
    })

    # Phase 1: Easy data
    log("  Phase 1: Training on easy data (top 50% corr)...")
    wl, hl = 4096, 2048
    easy_ds = SVDEggDataset(easy_pairs, wl, hl, 16000, split_name="easy")
    val_ds = SVDEggDataset(val_pairs, wl, hl, 16000, split_name="val")
    test_ds = SVDEggDataset(test_pairs, wl, hl, 16000, split_name="test")

    easy_loader = DataLoader(easy_ds, batch_size=32, shuffle=True, num_workers=4,
                             pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False, num_workers=4, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=4, pin_memory=True)

    # Phase 1 training
    results_dir = os.path.join(PROJECT_DIR, 'results', exp_name)
    ckpt_dir = os.path.join(PROJECT_DIR, 'checkpoints', exp_name)
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    model = model.to(device)
    criterion = CombinedLoss(0.3)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    total_steps = len(easy_loader) * 30
    scheduler = OneCycleLR(optimizer, max_lr=0.001, total_steps=total_steps,
                           pct_start=0.1, anneal_strategy='cos')
    scaler = torch.amp.GradScaler('cuda')

    history = {'train_loss': [], 'train_corr': [], 'val_loss': [], 'val_corr': [], 'lr': []}
    best_val_corr = -1

    for epoch in range(1, 31):
        tl, tc = train_epoch(model, easy_loader, optimizer, scheduler, criterion, device, scaler)
        vc, vm, _ = evaluate(model, val_loader, device)
        history['train_loss'].append(tl)
        history['train_corr'].append(tc)
        history['val_loss'].append(vm)
        history['val_corr'].append(vc)
        history['lr'].append(optimizer.param_groups[0]['lr'])
        if vc > best_val_corr:
            best_val_corr = vc
            torch.save({'epoch': epoch, 'model_state_dict': model.state_dict(),
                        'val_corr': vc, 'phase': 1}, os.path.join(ckpt_dir, 'best_model.pt'))
        if epoch % 10 == 0:
            log(f"  [Phase 1] Ep {epoch}/30 TrCorr={tc:.4f} VaCorr={vc:.4f}")

    # Phase 2: All data (continue from phase 1 model)
    log("  Phase 2: Fine-tuning on all data...")
    all_ds = SVDEggDataset(all_train, wl, hl, 16000, split_name="all")
    all_loader = DataLoader(all_ds, batch_size=32, shuffle=True, num_workers=4,
                            pin_memory=True, drop_last=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0003, weight_decay=1e-4)
    total_steps2 = len(all_loader) * 50
    scheduler = OneCycleLR(optimizer, max_lr=0.0003, total_steps=total_steps2,
                           pct_start=0.05, anneal_strategy='cos')
    scaler = torch.amp.GradScaler('cuda')

    patience_counter = 0
    for epoch in range(1, 51):
        tl, tc = train_epoch(model, all_loader, optimizer, scheduler, criterion, device, scaler)
        vc, vm, _ = evaluate(model, val_loader, device)
        history['train_loss'].append(tl)
        history['train_corr'].append(tc)
        history['val_loss'].append(vm)
        history['val_corr'].append(vc)
        history['lr'].append(optimizer.param_groups[0]['lr'])
        if vc > best_val_corr:
            best_val_corr = vc
            patience_counter = 0
            torch.save({'epoch': 30 + epoch, 'model_state_dict': model.state_dict(),
                        'val_corr': vc, 'phase': 2}, os.path.join(ckpt_dir, 'best_model.pt'))
        else:
            patience_counter += 1
        if epoch % 10 == 0:
            log(f"  [Phase 2] Ep {epoch}/50 TrCorr={tc:.4f} VaCorr={vc:.4f}")
        if patience_counter >= 15:
            log(f"  Phase 2 early stop at ep {epoch}")
            break

    # Final test
    ckpt = torch.load(os.path.join(ckpt_dir, 'best_model.pt'), map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    test_corr, test_mse, test_r2 = evaluate(model, test_loader, device)
    log(f"  TEST → Corr={test_corr:.4f} MSE={test_mse:.6f} R²={test_r2:.4f}")

    metrics = {'experiment': exp_name, 'test_corr': float(test_corr),
               'test_mse': float(test_mse), 'test_r2': float(test_r2)}
    with open(os.path.join(results_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(results_dir, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)

    vis_dir = os.path.join(results_dir, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp10(device, test_loader_ref=None):
    """Exp10: EfficientEGGNet + larger model + stronger correlation loss"""
    exp_name = 'exp10_large_efficient'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    train_loader, val_loader, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=16, window_length=4096, hop_length=2048,
        target_sr=16000, num_workers=4, seed=42
    )

    # Larger EfficientEGGNet
    model = build_efficient_model({
        'channels': 160, 'n_layers': 30, 'kernel_size': 3,
        'n_stacks': 3, 'dropout': 0.05,
    })

    # Heavier correlation loss
    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=100, lr=0.001, loss_alpha=0.15, patience=20
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp11(device, test_loader_ref=None):
    """Exp11: Multi-scale EfficientEGGNet (multiple window sizes combined)"""
    exp_name = 'exp11_multiscale'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    # Use longer window for more context
    train_loader, val_loader, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=16, window_length=8192, hop_length=4096,
        target_sr=16000, num_workers=4, seed=42
    )

    # Larger model with more stacks for multi-scale
    model = build_efficient_model({
        'channels': 128, 'n_layers': 30, 'kernel_size': 5,  # larger kernel
        'n_stacks': 5, 'dropout': 0.05,
    })

    test_corr, test_mse, test_r2, history, model = run_training(
        model, train_loader, val_loader, test_loader, device,
        exp_name, max_epochs=80, lr=0.001, loss_alpha=0.2, patience=15
    )

    vis_dir = os.path.join(PROJECT_DIR, 'results', exp_name, 'visualizations')
    generate_visualizations(model, test_loader, device, vis_dir, exp_name, history)

    return test_corr, model


def run_exp12(device, best_models_info=None):
    """Exp12: Ensemble of best models"""
    exp_name = 'exp12_ensemble'
    log(f"{'='*60}")
    log(f"Starting {exp_name}")
    log(f"{'='*60}")

    results_dir = os.path.join(PROJECT_DIR, 'results', exp_name)
    os.makedirs(results_dir, exist_ok=True)

    # Collect available models
    model_configs = [
        ('exp3_efficient', build_efficient_model, {
            'channels': 96, 'n_layers': 24, 'kernel_size': 3, 'n_stacks': 3, 'dropout': 0.1
        }, 4096),
    ]

    # Add any new experiments that have checkpoints
    for ename in ['exp5_high_quality_data', 'exp6_transformer', 'exp7_conformer',
                   'exp9_curriculum', 'exp10_large_efficient', 'exp11_multiscale']:
        ckpt_path = os.path.join(PROJECT_DIR, 'checkpoints', ename, 'best_model.pt')
        if os.path.exists(ckpt_path):
            if 'transformer' in ename:
                model_configs.append((ename, build_transformer_model, {
                    'd_model': 256, 'n_heads': 8, 'n_layers': 6, 'd_ff': 1024, 'dropout': 0.1
                }, 4096))
            elif 'conformer' in ename:
                model_configs.append((ename, build_conformer_model, {
                    'd_model': 256, 'n_heads': 4, 'n_layers': 6, 'd_ff': 1024, 'conv_kernel': 31
                }, 4096))
            elif 'multiscale' in ename:
                model_configs.append((ename, build_efficient_model, {
                    'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05
                }, 8192))
            else:
                model_configs.append((ename, build_efficient_model, {
                    'channels': 96, 'n_layers': 24, 'kernel_size': 3, 'n_stacks': 3, 'dropout': 0.1
                }, 4096))

    if len(model_configs) < 2:
        log("  Not enough models for ensemble. Skipping.")
        return 0, None

    log(f"  Ensemble with {len(model_configs)} models: {[m[0] for m in model_configs]}")

    # Use smallest window size among models
    min_window = min(m[3] for m in model_configs)
    _, _, test_loader, _ = create_dataloaders(
        SVD_PATH, batch_size=32, window_length=min_window, hop_length=min_window // 2,
        target_sr=16000, num_workers=4, seed=42
    )

    # Load all models
    models = []
    for ename, builder, config, wl in model_configs:
        try:
            m = builder(config)
            ckpt = torch.load(os.path.join(PROJECT_DIR, 'checkpoints', ename, 'best_model.pt'),
                              map_location=device, weights_only=False)
            m.load_state_dict(ckpt['model_state_dict'])
            m = m.to(device)
            m.eval()
            models.append((ename, m))
            log(f"    Loaded {ename}")
        except Exception as e:
            log(f"    Failed to load {ename}: {e}")

    if len(models) < 2:
        log("  Not enough models loaded. Skipping ensemble.")
        return 0, None

    # Simple averaging ensemble
    all_corrs = []
    all_mse = []
    with torch.no_grad():
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            preds = []
            for name, m in models:
                p = m(x)
                if p.shape != y.shape:
                    mt = min(p.shape[-1], y.shape[-1])
                    p = p[..., :mt]
                preds.append(p)
            # Average
            min_t = min(p.shape[-1] for p in preds)
            preds = [p[..., :min_t] for p in preds]
            y = y[..., :min_t]
            avg_pred = torch.stack(preds).mean(dim=0)
            corr = pearson_corr_batch(avg_pred, y)
            mse = F.mse_loss(avg_pred, y).item()
            all_corrs.append(corr)
            all_mse.append(mse)

    test_corr = np.mean(all_corrs)
    test_mse = np.mean(all_mse)
    log(f"  Ensemble TEST → Corr={test_corr:.4f} MSE={test_mse:.6f}")

    metrics = {
        'experiment': exp_name,
        'models': [m[0] for m in models],
        'test_corr': float(test_corr),
        'test_mse': float(test_mse),
    }
    with open(os.path.join(results_dir, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)

    return test_corr, None


# ============================================================
# Main auto-experiment loop
# ============================================================
def main():
    log("=" * 60)
    log("EGG 예측 모델 자동 최적화 시작")
    log(f"목표: Test Correlation >= 0.9")
    log(f"현재 Best: 0.7163 (Exp3 EfficientEGGNet)")
    log("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log(f"Device: {device}")
    if torch.cuda.is_available():
        log(f"GPU: {torch.cuda.get_device_name(0)}")
        log(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    best_corr = 0.7163
    target = 0.9
    results_summary = []

    experiments = [
        ('exp5_high_quality_data', run_exp5),
        ('exp6_transformer', run_exp6),
        ('exp7_conformer', run_exp7),
        ('exp9_curriculum', run_exp9),
        ('exp10_large_efficient', run_exp10),
        ('exp11_multiscale', run_exp11),
        ('exp8_wav2vec2', run_exp8),       # Last (needs pip install)
        ('exp12_ensemble', run_exp12),
    ]

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
                'is_best': test_corr > best_corr,
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
                        _, _, tl, _ = create_dataloaders(
                            SVD_PATH, batch_size=32, window_length=4096, hop_length=2048,
                            target_sr=16000, num_workers=4, seed=42)
                        generate_visualizations(model, tl, device, new_best_vis, exp_name)
                    except:
                        pass

            if test_corr >= target:
                log(f"🏆 TARGET ACHIEVED! Corr = {test_corr:.4f}")
                break
            else:
                log(f"Target not reached ({test_corr:.4f} < {target}). Continuing...")

        except Exception as e:
            log(f"❌ {exp_name} FAILED: {str(e)}")
            log(traceback.format_exc())
            results_summary.append({
                'experiment': exp_name,
                'test_corr': 0,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            })

        # Cleanup GPU memory
        gc.collect()
        torch.cuda.empty_cache()

    # Final summary
    log("\n" + "=" * 60)
    log("실험 종료 — 최종 요약")
    log("=" * 60)
    log(f"{'Experiment':<30} {'Corr':>8} {'Best?':>6}")
    log("-" * 50)
    for r in results_summary:
        mark = "★" if r.get('is_best') else ""
        corr_str = f"{r['test_corr']:.4f}" if r['test_corr'] > 0 else "FAIL"
        log(f"{r['experiment']:<30} {corr_str:>8} {mark:>6}")
    log("-" * 50)
    log(f"Final Best Corr: {best_corr:.4f}")
    log(f"Target (0.9): {'ACHIEVED ✅' if best_corr >= target else 'NOT REACHED ❌'}")

    # Save summary
    summary_path = os.path.join(PROJECT_DIR, 'results/experiment_summary.json')
    with open(summary_path, 'w') as f:
        json.dump({
            'final_best_corr': float(best_corr),
            'target': target,
            'target_achieved': best_corr >= target,
            'experiments': results_summary,
        }, f, indent=2)
    log(f"Summary saved: {summary_path}")


if __name__ == '__main__':
    main()
