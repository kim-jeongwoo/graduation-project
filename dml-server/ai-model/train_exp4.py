#!/usr/bin/env python3
"""
실험 4: Multi-Input (Waveform + Mel Spec) + Augmentation + W=4096
================================================================
핵심 개선:
  1. Dual-path: raw waveform + mel spectrogram features
  2. 30 dilated layers, 3 stacks → RF 6139 > window 4096
  3. Data augmentation: noise injection, gain variation
  4. CosineAnnealing scheduler (안정적)
  5. Alpha=0.3 (MSE 30% + CorrLoss 70%)
"""
import os
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

from model.multi_input_egg import build_multi_input_model
from utils.nsp_reader import read_nsp, find_paired_files


# ============================================================
EXP_NAME = "exp4_multi_input"

CONFIG = {
    'data': {
        'svd_path': os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy'),
        'sample_rate': 16000,
        'window_length': 4096,
        'hop_length': 2048,
    },
    'model': {
        'channels': 96,
        'n_layers': 30,
        'kernel_size': 3,
        'n_stacks': 3,
        'dropout': 0.1,
        'n_mels': 64,
        'spec_channels': 32,
        'spec_hop': 128,
        'sample_rate': 16000,
    },
    'training': {
        'batch_size': 32,
        'max_epochs': 60,
        'learning_rate': 0.0008,
        'weight_decay': 0.0001,
        'early_stopping_patience': 12,
        'loss_alpha': 0.3,
    },
}

RESULTS_DIR = os.path.expanduser(f'~/projects/egg_prediction/results/{EXP_NAME}')
CKPT_DIR = os.path.expanduser(f'~/projects/egg_prediction/checkpoints/{EXP_NAME}')


# ============================================================
# Dataset with augmentation
# ============================================================
def speaker_split(speaker_ids, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42):
    rng = np.random.RandomState(seed)
    unique = sorted(set(speaker_ids))
    rng.shuffle(unique)
    n = len(unique)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train_sp = set(unique[:n_train])
    val_sp = set(unique[n_train:n_train + n_val])
    test_sp = set(unique[n_train + n_val:])
    return train_sp, val_sp, test_sp


class AugmentedSVDDataset(Dataset):
    """Dataset with online data augmentation."""
    
    def __init__(self, pairs, window_length=4096, hop_length=2048,
                 target_sr=16000, source_sr=50000, split_name="",
                 augment=False):
        self.window_length = window_length
        self.hop_length = hop_length
        self.target_sr = target_sr
        self.source_sr = source_sr
        self.augment = augment
        
        self.windows = []
        self.speech_data = []
        self.egg_data = []
        self._load(pairs, split_name)
    
    def _resample(self, sig):
        if self.source_sr == self.target_sr:
            return sig
        import librosa
        return librosa.resample(sig, orig_sr=self.source_sr, target_sr=self.target_sr)
    
    def _load(self, pairs, name):
        skipped = 0
        for nsp_path, egg_path, spk in tqdm(pairs, desc=f"Loading {name}"):
            try:
                speech, sr1 = read_nsp(nsp_path)
                egg, sr2 = read_nsp(egg_path)
            except:
                skipped += 1
                continue
            
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            speech, egg = self._resample(speech), self._resample(egg)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            
            if ml < self.window_length:
                skipped += 1
                continue
            
            # Per-file normalization
            s_std = speech.std()
            e_std = egg.std()
            if s_std > 1e-8:
                speech = (speech - speech.mean()) / s_std
            if e_std > 1e-8:
                egg = (egg - egg.mean()) / e_std
            
            fidx = len(self.speech_data)
            self.speech_data.append(speech)
            self.egg_data.append(egg)
            
            n_win = (ml - self.window_length) // self.hop_length + 1
            for w in range(n_win):
                self.windows.append((fidx, w * self.hop_length))
        
        if skipped > 0:
            print(f"  Skipped {skipped} files")
        print(f"  Loaded {len(self.speech_data)} files, {len(self.windows)} windows")
    
    def __len__(self):
        return len(self.windows)
    
    def __getitem__(self, idx):
        fidx, start = self.windows[idx]
        end = start + self.window_length
        
        x = self.speech_data[fidx][start:end].copy()
        y = self.egg_data[fidx][start:end].copy()
        
        if self.augment:
            # Noise injection to speech only
            if np.random.random() < 0.5:
                noise = np.random.randn(len(x)) * 0.01
                x = x + noise
            
            # Gain variation to speech only
            if np.random.random() < 0.3:
                gain = np.random.uniform(0.8, 1.2)
                x = x * gain
            
            # Random sign flip (both)
            if np.random.random() < 0.3:
                x = -x
                y = -y
        
        x = torch.from_numpy(x).float().unsqueeze(0)
        y = torch.from_numpy(y).float().unsqueeze(0)
        return x, y


def create_augmented_dataloaders(svd_path, batch_size=32, window_length=4096,
                                  hop_length=2048, target_sr=16000,
                                  num_workers=4, seed=42):
    print("Finding paired files...")
    pairs = find_paired_files(svd_path)
    print(f"Found {len(pairs)} paired files")
    
    all_sp = [p[2] for p in pairs]
    train_sp, val_sp, test_sp = speaker_split(all_sp, seed=seed)
    print(f"Split: Train={len(train_sp)}, Val={len(val_sp)}, Test={len(test_sp)}")
    
    train_pairs = [(n, e, s) for n, e, s in pairs if s in train_sp]
    val_pairs = [(n, e, s) for n, e, s in pairs if s in val_sp]
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
    print(f"Files: Train={len(train_pairs)}, Val={len(val_pairs)}, Test={len(test_pairs)}")
    
    train_ds = AugmentedSVDDataset(train_pairs, window_length, hop_length, target_sr,
                                    split_name="train", augment=True)
    val_ds = AugmentedSVDDataset(val_pairs, window_length, hop_length, target_sr,
                                  split_name="val", augment=False)
    test_ds = AugmentedSVDDataset(test_pairs, window_length, hop_length, target_sr,
                                   split_name="test", augment=False)
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=num_workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=True)
    
    info = {
        'train_speakers': len(train_sp), 'val_speakers': len(val_sp), 'test_speakers': len(test_sp),
        'train_files': len(train_pairs), 'val_files': len(val_pairs), 'test_files': len(test_pairs),
        'train_windows': len(train_ds), 'val_windows': len(val_ds), 'test_windows': len(test_ds),
    }
    return train_loader, val_loader, test_loader, info


# ============================================================
class CombinedLoss(nn.Module):
    def __init__(self, alpha=0.3):
        super().__init__()
        self.alpha = alpha
        self.mse = nn.MSELoss()
    
    def forward(self, pred, target):
        mse_loss = self.mse(pred, target)
        p = pred.squeeze(1); t = target.squeeze(1)
        pc = p - p.mean(dim=1, keepdim=True)
        tc = t - t.mean(dim=1, keepdim=True)
        num = (pc * tc).sum(dim=1)
        den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
        corr_loss = 1.0 - (num / den).mean()
        return self.alpha * mse_loss + (1-self.alpha) * corr_loss


def pearson_corr(pred, target):
    p = pred.squeeze(1); t = target.squeeze(1)
    pc = p - p.mean(dim=1, keepdim=True)
    tc = t - t.mean(dim=1, keepdim=True)
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
    return (num / den).mean().item()


def rmse_fn(pred, target):
    return torch.sqrt(F.mse_loss(pred, target)).item()


# ============================================================
def train_epoch(model, loader, optimizer, criterion, device, scaler):
    model.train()
    total_loss = 0; total_corr = 0; n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        
        with torch.amp.autocast('cuda'):
            pred = model(x)
            loss = criterion(pred, y)
        
        if torch.isnan(loss) or torch.isinf(loss):
            continue
        
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        
        total_loss += loss.item()
        total_corr += pearson_corr(pred.detach().float(), y)
        n += 1
    if n == 0:
        return float('nan'), float('nan')
    return total_loss / n, total_corr / n


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0; total_corr = 0; total_rmse = 0; n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x)
        total_loss += criterion(pred, y).item()
        total_corr += pearson_corr(pred, y)
        total_rmse += rmse_fn(pred, y)
        n += 1
    if n == 0: return 0, 0, 0
    return total_loss / n, total_corr / n, total_rmse / n


# ============================================================
def plot_training_history(history, save_path):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    epochs = range(1, len(history['train_loss']) + 1)
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train', lw=1.5)
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val', lw=1.5)
    axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
    axes[0].set_title('Loss'); axes[0].legend(); axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(epochs, history['train_corr'], 'b-', label='Train', lw=1.5)
    axes[1].plot(epochs, history['val_corr'], 'r-', label='Val', lw=1.5)
    axes[1].axhline(y=0.8, color='g', ls='--', alpha=0.7, label='Target')
    axes[1].axhline(y=0.7163, color='purple', ls=':', alpha=0.7, label='Exp3 (0.716)')
    axes[1].axhline(y=0.6662, color='orange', ls=':', alpha=0.7, label='Baseline (0.67)')
    axes[1].set_xlabel('Epoch'); axes[1].set_ylabel('Corr')
    axes[1].set_title('Correlation'); axes[1].legend(); axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(epochs, history['lr'], 'g-', lw=1.5)
    axes[2].set_xlabel('Epoch'); axes[2].set_ylabel('LR')
    axes[2].set_title('LR'); axes[2].grid(True, alpha=0.3)
    
    plt.suptitle('Exp4: Multi-Input CNN', fontsize=14, fontweight='bold')
    plt.tight_layout(); plt.savefig(save_path, dpi=150, bbox_inches='tight'); plt.close()


def plot_comparison(model, loader, device, save_dir, n_ex=6):
    model.eval()
    os.makedirs(save_dir, exist_ok=True)
    with torch.no_grad():
        ax, ay, ap = [], [], []
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            p = model(x)
            ax.append(x.cpu()); ay.append(y.cpu()); ap.append(p.cpu())
            if sum(a.size(0) for a in ax) >= n_ex: break
        ax = torch.cat(ax); ay = torch.cat(ay); ap = torch.cat(ap)
    
    for i in range(min(n_ex, ax.size(0))):
        mic = ax[i,0].numpy(); gt = ay[i,0].numpy(); pr = ap[i,0].numpy()
        c = np.corrcoef(gt, pr)[0,1] if np.std(gt) > 1e-8 and np.std(pr) > 1e-8 else 0
        T = len(mic); t = np.arange(T)
        
        fig, axes = plt.subplots(3, 1, figsize=(16, 10))
        axes[0].plot(t, mic, 'b-', lw=0.5); axes[0].set_title('MIC', fontweight='bold')
        axes[0].set_xlim(0, T); axes[0].grid(True, alpha=0.3)
        
        axes[1].plot(t, gt, 'b-', label='GT', lw=1)
        axes[1].plot(t, pr, color='orange', label='Pred', lw=1, alpha=0.85)
        axes[1].set_title(f'EGG | r={c:.4f}', fontweight='bold')
        axes[1].set_xlim(0, T); axes[1].legend(); axes[1].grid(True, alpha=0.3)
        
        z = min(400, T//3); s = T//3
        axes[2].plot(range(s,s+z), gt[s:s+z], 'b-', label='GT', lw=2)
        axes[2].plot(range(s,s+z), pr[s:s+z], color='orange', label='Pred', lw=2, alpha=0.85)
        axes[2].set_title(f'Zoomed', fontweight='bold')
        axes[2].legend(); axes[2].grid(True, alpha=0.3)
        
        plt.suptitle(f'Sample {i+1} | r={c:.4f}', fontsize=14, fontweight='bold', y=1.01)
        plt.tight_layout(); plt.savefig(os.path.join(save_dir, f'sample_{i+1}.png'), dpi=150, bbox_inches='tight')
        plt.close()
    
    # Combined
    fig, axes = plt.subplots(n_ex, 2, figsize=(18, 3*n_ex))
    for i in range(min(n_ex, ax.size(0))):
        mic = ax[i,0].numpy(); gt = ay[i,0].numpy(); pr = ap[i,0].numpy()
        c = np.corrcoef(gt, pr)[0,1] if np.std(gt) > 1e-8 and np.std(pr) > 1e-8 else 0
        T = len(mic)
        axes[i,0].plot(np.arange(T), mic, 'b-', lw=0.5)
        if i==0: axes[i,0].set_title('MIC', fontweight='bold')
        axes[i,0].set_ylabel(f'#{i+1}', fontweight='bold')
        axes[i,0].set_xlim(0,T); axes[i,0].grid(True, alpha=0.3)
        axes[i,1].plot(np.arange(T), gt, 'b-', label='GT', lw=0.8)
        axes[i,1].plot(np.arange(T), pr, color='orange', label='Pred', lw=0.8, alpha=0.85)
        if i==0: axes[i,1].set_title('GT vs Pred', fontweight='bold')
        axes[i,1].set_xlim(0,T); axes[i,1].legend(fontsize=7)
        axes[i,1].text(0.02, 0.85, f'r={c:.4f}', transform=axes[i,1].transAxes,
                       fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        axes[i,1].grid(True, alpha=0.3)
    axes[-1,0].set_xlabel('Sample'); axes[-1,1].set_xlabel('Sample')
    plt.suptitle('Exp4: Multi-Input — Test Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout(); plt.savefig(os.path.join(save_dir, 'all_samples_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved images to {save_dir}")


# ============================================================
def main():
    print("=" * 70)
    print("  실험 4: Multi-Input (Waveform + Mel) + Augmentation")
    print("=" * 70)
    
    cfg = CONFIG; d = cfg['data']; m = cfg['model']; t = cfg['training']
    os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(CKPT_DIR, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}, GPU: {torch.cuda.get_device_name(0)}")
    print(f"Window: {d['window_length']} ({d['window_length']/d['sample_rate']*1000:.0f}ms)")
    
    train_loader, val_loader, test_loader, info = create_augmented_dataloaders(
        d['svd_path'], t['batch_size'], d['window_length'], d['hop_length'],
        d['sample_rate'], num_workers=4, seed=42)
    
    print(f"\nSplit: Train={info['train_speakers']} spk, Val={info['val_speakers']} spk, Test={info['test_speakers']} spk")
    print(f"Windows: Train={info['train_windows']:,}, Val={info['val_windows']:,}, Test={info['test_windows']:,}")
    
    model = build_multi_input_model(m).to(device)
    n_params = model.count_params()
    rf = model.receptive_field()
    print(f"\nModel: {n_params:,} params, RF={rf} ({rf/d['sample_rate']*1000:.0f}ms)")
    
    with torch.no_grad():
        dummy = torch.randn(2, 1, d['window_length']).to(device)
        out = model(dummy)
        print(f"Shape: {dummy.shape} → {out.shape}")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=t['learning_rate'],
                                  weight_decay=t['weight_decay'])
    scheduler = CosineAnnealingLR(optimizer, T_max=t['max_epochs'], eta_min=1e-6)
    criterion = CombinedLoss(alpha=t['loss_alpha'])
    mse_criterion = nn.MSELoss()
    scaler = torch.amp.GradScaler('cuda')
    
    history = {'train_loss':[], 'train_corr':[], 'val_loss':[], 'val_corr':[], 'val_rmse':[], 'lr':[]}
    best_val_corr = -1; patience_counter = 0; patience = t['early_stopping_patience']
    
    print(f"\n{'='*70}")
    print(f"  Training | Epochs: {t['max_epochs']} | Batch: {t['batch_size']} | AMP")
    print(f"  LR: {t['learning_rate']} (CosineAnnealing) | Loss: α={t['loss_alpha']}")
    print(f"  Augmentation: noise(0.5), gain(0.3), flip(0.3)")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    for epoch in range(1, t['max_epochs']+1):
        t0 = time.time()
        train_loss, train_corr = train_epoch(model, train_loader, optimizer, criterion, device, scaler)
        val_loss, val_corr, val_rmse = evaluate(model, val_loader, criterion, device)
        lr = optimizer.param_groups[0]['lr']
        scheduler.step()
        
        history['train_loss'].append(train_loss); history['train_corr'].append(train_corr)
        history['val_loss'].append(val_loss); history['val_corr'].append(val_corr)
        history['val_rmse'].append(val_rmse); history['lr'].append(lr)
        
        dt = time.time() - t0
        print(f"Epoch {epoch:3d}/{t['max_epochs']} | "
              f"Train Loss: {train_loss:.6f} Corr: {train_corr:.4f} | "
              f"Val Loss: {val_loss:.6f} Corr: {val_corr:.4f} RMSE: {val_rmse:.4f} | "
              f"LR: {lr:.6f} | {dt:.1f}s", end="")
        
        if val_corr > best_val_corr:
            best_val_corr = val_corr; patience_counter = 0
            torch.save({'epoch': epoch, 'model_state_dict': model.state_dict(),
                       'val_corr': val_corr, 'config': cfg},
                      os.path.join(CKPT_DIR, 'best_model.pt'))
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
    print(f"\nTraining: {total_time/60:.1f} min")
    
    # Test
    print(f"\n{'='*70}\n  Test Set Evaluation\n{'='*70}")
    ckpt = torch.load(os.path.join(CKPT_DIR, 'best_model.pt'), map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    print(f"Best: epoch {ckpt['epoch']} (val_corr: {ckpt['val_corr']:.4f})")
    
    test_loss, test_corr, test_rmse = evaluate(model, test_loader, mse_criterion, device)
    
    print(f"\n  Test MSE:  {test_loss:.6f}")
    print(f"  Test Corr: {test_corr:.4f}")
    print(f"  Test RMSE: {test_rmse:.4f}")
    print(f"  Baseline:  0.6662 → Δ={test_corr-0.6662:+.4f}")
    print(f"  Exp3:      0.7163 → Δ={test_corr-0.7163:+.4f}")
    print(f"  Target 0.8: {'✅ 달성!' if test_corr >= 0.8 else '❌ 미달'}")
    
    plot_training_history(history, os.path.join(RESULTS_DIR, 'training_history.png'))
    plot_comparison(model, test_loader, device, RESULTS_DIR, n_ex=6)
    
    metrics = {'experiment': EXP_NAME, 'model_params': n_params, 'rf': rf,
               'training_time_min': total_time/60, 'best_epoch': ckpt['epoch'],
               'best_val_corr': float(ckpt['val_corr']),
               'test_loss': test_loss, 'test_corr': test_corr, 'test_rmse': test_rmse,
               'baseline': 0.6662, 'exp3': 0.7163,
               'improvement': test_corr - 0.6662, 'config': cfg, 'split_info': info}
    
    with open(os.path.join(RESULTS_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(RESULTS_DIR, 'history.json'), 'w') as f:
        json.dump(history, f, indent=2)
    
    with open(os.path.join(RESULTS_DIR, 'metrics.txt'), 'w') as f:
        f.write("=" * 60 + "\n실험 4: Multi-Input + Augmentation\n" + "=" * 60 + "\n\n")
        f.write(f"Model: MultiInputEGGNet, {n_params:,} params, RF={rf}\n")
        f.write(f"Window: {d['window_length']} ({d['window_length']/d['sample_rate']*1000:.0f}ms)\n")
        f.write(f"Loss: {t['loss_alpha']}*MSE + {1-t['loss_alpha']}*CorrLoss\n")
        f.write(f"Augmentation: noise, gain, flip\n")
        f.write(f"Training: {total_time/60:.1f} min, best epoch {ckpt['epoch']}\n\n")
        f.write(f"Best Val Corr: {ckpt['val_corr']:.4f}\n\n")
        f.write(f"Test:\n  Loss: {test_loss:.6f}\n  Corr: {test_corr:.4f}\n  RMSE: {test_rmse:.4f}\n\n")
        f.write(f"Baseline: 0.6662 (Δ={test_corr-0.6662:+.4f})\nExp3: 0.7163 (Δ={test_corr-0.7163:+.4f})\n")
        f.write(f"Target (0.8): {'PASS' if test_corr >= 0.8 else 'FAIL'}\n")
    
    print(f"\n  Results: {RESULTS_DIR}")
    print(f"\n{'='*70}\n  실험 4 완료!\n{'='*70}")


if __name__ == '__main__':
    main()
