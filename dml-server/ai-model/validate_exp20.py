#!/usr/bin/env python3
"""exp20 검증 스크립트"""
import sys, os, torch, numpy as np
import torch.nn.functional as F
sys.path.insert(0, os.path.join(os.path.expanduser('~/projects/egg_prediction'), 'ai-model'))
from model.efficient_egg import build_efficient_model
from utils.dataset import create_dataloaders, speaker_split
from utils.nsp_reader import find_paired_files, read_nsp

SVD_PATH = os.path.expanduser('~/projects/egg_prediction/data/SVD_healthy')
device = torch.device('cuda')

def pearson_corr_batch_values(pred, target):
    p = pred.squeeze(1); t = target.squeeze(1)
    pc = p - p.mean(dim=1, keepdim=True)
    tc = t - t.mean(dim=1, keepdim=True)
    num = (pc * tc).sum(dim=1)
    den = torch.sqrt((pc**2).sum(dim=1) * (tc**2).sum(dim=1) + 1e-8)
    return (num / den).cpu().numpy()

# Load models
print("Loading models...")
cfg = {'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05}

model20 = build_efficient_model(cfg)
ckpt20 = torch.load('checkpoints/exp20_progressive/best_model.pt', map_location=device, weights_only=False)
model20.load_state_dict(ckpt20['model_state_dict'])
model20 = model20.to(device).eval()
print(f"  exp20: phase={ckpt20.get('phase','?')}, val_corr={ckpt20.get('val_corr','?'):.4f}")

model11 = build_efficient_model(cfg)
ckpt11 = torch.load('checkpoints/exp11_multiscale/best_model.pt', map_location=device, weights_only=False)
model11.load_state_dict(ckpt11['model_state_dict'])
model11 = model11.to(device).eval()

@torch.no_grad()
def eval_full(model, loader):
    corrs, mses = [], []
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        p = model(x)
        if p.shape != y.shape:
            mt = min(p.shape[-1], y.shape[-1])
            p = p[..., :mt]; y = y[..., :mt]
        c = pearson_corr_batch_values(p, y)
        corrs.extend(c.tolist())
        mses.append(F.mse_loss(p, y).item())
    return np.mean(corrs), np.std(corrs), np.median(corrs), np.mean(mses)

# ===== 1. Data Split =====
print("\n" + "="*60)
print("1. DATA SPLIT VERIFICATION")
print("="*60)
pairs = find_paired_files(SVD_PATH)
all_speakers = sorted(set(p[2] for p in pairs))
train_sp, val_sp, test_sp = speaker_split(all_speakers, seed=42)
print(f"Total files: {len(pairs)}, speakers: {len(all_speakers)}")
print(f"Train: {len(train_sp)} spk, Val: {len(val_sp)} spk, Test: {len(test_sp)} spk")
print(f"Overlaps: T∩V={len(train_sp&val_sp)}, T∩Te={len(train_sp&test_sp)}, V∩Te={len(val_sp&test_sp)}")
print(f"LEAK-FREE: {len(train_sp&val_sp)==0 and len(train_sp&test_sp)==0 and len(val_sp&test_sp)==0}")

# ===== 2. Fair comparison on same 8192 window =====
print("\n" + "="*60)
print("2. FAIR COMPARISON (same test data, window=8192)")
print("="*60)
train_loader, val_loader, test_loader_8k, _ = create_dataloaders(
    SVD_PATH, batch_size=16, window_length=8192, hop_length=4096,
    target_sr=16000, num_workers=4, seed=42
)

print("exp11 on test (8192)...")
e11_mean, e11_std, e11_med, e11_mse = eval_full(model11, test_loader_8k)
print(f"  Mean={e11_mean:.4f}, Med={e11_med:.4f}, Std={e11_std:.4f}, MSE={e11_mse:.4f}")

print("exp20 on test (8192)...")
e20_mean_8k, e20_std_8k, e20_med_8k, e20_mse_8k = eval_full(model20, test_loader_8k)
print(f"  Mean={e20_mean_8k:.4f}, Med={e20_med_8k:.4f}, Std={e20_std_8k:.4f}, MSE={e20_mse_8k:.4f}")

print("exp20 on train (8192)...")
e20_tr, e20_tr_std, _, e20_tr_mse = eval_full(model20, train_loader)
print(f"  Mean={e20_tr:.4f}, Std={e20_tr_std:.4f}")

print("exp20 on val (8192)...")
e20_va, e20_va_std, _, e20_va_mse = eval_full(model20, val_loader)
print(f"  Mean={e20_va:.4f}, Std={e20_va_std:.4f}")

# exp20 on 16384
print("exp20 on test (16384)...")
_, _, test_loader_16k, _ = create_dataloaders(
    SVD_PATH, batch_size=8, window_length=16384, hop_length=8192,
    target_sr=16000, num_workers=4, seed=42
)
e20_mean_16k, e20_std_16k, e20_med_16k, e20_mse_16k = eval_full(model20, test_loader_16k)
print(f"  Mean={e20_mean_16k:.4f}, Med={e20_med_16k:.4f}, Std={e20_std_16k:.4f}, MSE={e20_mse_16k:.4f}")

# exp11 on 16384 too
print("exp11 on test (16384)...")
e11_mean_16k, e11_std_16k, e11_med_16k, e11_mse_16k = eval_full(model11, test_loader_16k)
print(f"  Mean={e11_mean_16k:.4f}, Med={e11_med_16k:.4f}, Std={e11_std_16k:.4f}, MSE={e11_mse_16k:.4f}")

# ===== 3. Per-speaker analysis =====
print("\n" + "="*60)
print("3. PER-SPEAKER TEST CORRELATION (exp20, window=16384)")
print("="*60)
import librosa
test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
speaker_corrs = {}
for nsp_path, egg_path, spk in test_pairs:
    try:
        speech, _ = read_nsp(nsp_path)
        egg, _ = read_nsp(egg_path)
        ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
        speech = librosa.resample(speech, orig_sr=50000, target_sr=16000)
        egg = librosa.resample(egg, orig_sr=50000, target_sr=16000)
        ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
        if ml < 16384: continue
        s_std = speech.std(); e_std = egg.std()
        if s_std > 1e-8: speech = (speech - speech.mean()) / s_std
        if e_std > 1e-8: egg = (egg - egg.mean()) / e_std
        wl = 16384
        for w in range((ml - wl) // 8192 + 1):
            start = w * 8192
            x = torch.from_numpy(speech[start:start+wl]).float().unsqueeze(0).unsqueeze(0).to(device)
            y = torch.from_numpy(egg[start:start+wl]).float().unsqueeze(0).unsqueeze(0).to(device)
            with torch.no_grad():
                p = model20(x)
                if p.shape != y.shape:
                    mt = min(p.shape[-1], y.shape[-1]); p = p[..., :mt]; y = y[..., :mt]
                c = pearson_corr_batch_values(p, y)
                speaker_corrs.setdefault(spk, []).extend(c.tolist())
    except:
        continue

spk_means = {s: np.mean(c) for s, c in speaker_corrs.items()}
sorted_spk = sorted(spk_means.items(), key=lambda x: x[1])
vals = list(spk_means.values())

print(f"Speakers evaluated: {len(vals)}")
print(f"Mean of speaker means: {np.mean(vals):.4f}")
print(f"Std of speaker means:  {np.std(vals):.4f}")
print(f"Min: Speaker {sorted_spk[0][0]} = {sorted_spk[0][1]:.4f}")
print(f"Max: Speaker {sorted_spk[-1][0]} = {sorted_spk[-1][1]:.4f}")
print(f"Median: {np.median(vals):.4f}")

a08 = sum(1 for v in vals if v >= 0.8)
a07 = sum(1 for v in vals if v >= 0.7)
a05 = sum(1 for v in vals if v >= 0.5)
b05 = sum(1 for v in vals if v < 0.5)
b03 = sum(1 for v in vals if v < 0.3)
print(f"\nDistribution:")
print(f"  >= 0.8: {a08}/{len(vals)} ({a08/len(vals)*100:.1f}%)")
print(f"  >= 0.7: {a07}/{len(vals)} ({a07/len(vals)*100:.1f}%)")
print(f"  >= 0.5: {a05}/{len(vals)} ({a05/len(vals)*100:.1f}%)")
print(f"  <  0.5: {b05}/{len(vals)} ({b05/len(vals)*100:.1f}%)")
print(f"  <  0.3: {b03}/{len(vals)} ({b03/len(vals)*100:.1f}%)")

print(f"\nBottom 10:")
for s, c in sorted_spk[:10]:
    print(f"  Spk {s}: {c:.4f} ({len(speaker_corrs[s])} win)")
print(f"\nTop 10:")
for s, c in sorted_spk[-10:]:
    print(f"  Spk {s}: {c:.4f} ({len(speaker_corrs[s])} win)")

# ===== Summary =====
print("\n" + "="*60)
print("SUMMARY TABLE")
print("="*60)
print(f"{'Metric':<40} {'exp11':>10} {'exp20':>10}")
print("-"*60)
print(f"{'Test Corr (window=8192)':<40} {e11_mean:>10.4f} {e20_mean_8k:>10.4f}")
print(f"{'Test Corr (window=16384)':<40} {e11_mean_16k:>10.4f} {e20_mean_16k:>10.4f}")
print(f"{'Test MSE (window=8192)':<40} {e11_mse:>10.4f} {e20_mse_8k:>10.4f}")
print(f"{'Test MSE (window=16384)':<40} {e11_mse_16k:>10.4f} {e20_mse_16k:>10.4f}")
print(f"{'Train Corr (8192, exp20 only)':<40} {'':>10} {e20_tr:>10.4f}")
print(f"{'Val Corr (8192, exp20 only)':<40} {'':>10} {e20_va:>10.4f}")
print(f"{'Train-Test Gap (8192)':<40} {'':>10} {e20_tr - e20_mean_8k:>+10.4f}")
print(f"{'Speaker mean (16384)':<40} {'':>10} {np.mean(vals):>10.4f}")
print(f"{'Speaker std (16384)':<40} {'':>10} {np.std(vals):>10.4f}")
print(f"{'Speakers >= 0.8':<40} {'':>10} {f'{a08}/{len(vals)}':>10}")
print(f"{'Speakers <  0.5':<40} {'':>10} {f'{b05}/{len(vals)}':>10}")
