"""
과적합 해결 실험
- 실험 1: 정규화 강화
- 실험 2: 모델 단순화
- 실험 3: 데이터 증강
- 실험 4: 전체 조합
"""
import os
import sys
import yaml
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import ExponentialLR
from pathlib import Path
import numpy as np
import librosa
from collections import defaultdict
import matplotlib.pyplot as plt
import random
import copy

sys.path.insert(0, str(Path(__file__).parent))

from utils.alignment import align_signals
from utils.preprocessing import preprocess_mic, preprocess_egg, frame_signal
from utils.metrics import compute_correlation, compute_mse, compute_r2


# ============================================================
# 단순화된 모델 정의 (실험 2용)
# ============================================================

class SimplifiedWaveNet(nn.Module):
    """단순화된 WaveNet (Attention 제거, 작은 구조)"""
    def __init__(self, input_size=192, n_layers=6, n_channels=16, dropout=0.5):
        super().__init__()
        
        self.input_size = input_size
        self.n_layers = n_layers
        self.n_channels = n_channels
        
        # Input projection
        self.input_conv = nn.Conv1d(1, n_channels, kernel_size=1)
        
        # Dilated convolutions
        self.dilated_convs = nn.ModuleList()
        self.residual_convs = nn.ModuleList()
        self.skip_convs = nn.ModuleList()
        self.dropouts = nn.ModuleList()
        
        for i in range(n_layers):
            dilation = 2 ** i
            self.dilated_convs.append(
                nn.Conv1d(n_channels, n_channels * 2, kernel_size=3,
                         padding=dilation, dilation=dilation)
            )
            self.residual_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.skip_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.dropouts.append(nn.Dropout(dropout))
        
        # Output layers
        self.output_conv1 = nn.Conv1d(n_channels, n_channels, kernel_size=1)
        self.output_conv2 = nn.Conv1d(n_channels, 1, kernel_size=1)
        self.output_dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        # x: (batch, input_size)
        x = x.unsqueeze(1)  # (batch, 1, input_size)
        
        x = self.input_conv(x)
        
        skip_sum = 0
        for i in range(self.n_layers):
            # Gated activation
            out = self.dilated_convs[i](x)
            tanh_out = torch.tanh(out[:, :self.n_channels, :])
            sigmoid_out = torch.sigmoid(out[:, self.n_channels:, :])
            gated = tanh_out * sigmoid_out
            gated = self.dropouts[i](gated)
            
            # Skip connection
            skip = self.skip_convs[i](gated)
            skip_sum = skip_sum + skip
            
            # Residual connection
            residual = self.residual_convs[i](gated)
            x = x + residual
        
        # Output
        out = torch.relu(skip_sum)
        out = self.output_conv1(out)
        out = self.output_dropout(out)
        out = torch.relu(out)
        out = self.output_conv2(out)
        
        # Global average pooling
        out = out.mean(dim=2)
        return out.squeeze(1)
    
    def get_receptive_field(self):
        rf = 1
        for i in range(self.n_layers):
            rf += 2 * (2 ** i)
        return rf


class OriginalWaveNet(nn.Module):
    """원본 WaveNet + Self-Attention (정규화 조절 가능)"""
    def __init__(self, input_size=192, n_layers=10, n_channels=32, 
                 n_heads=4, dropout=0.3, use_attention=True):
        super().__init__()
        
        self.input_size = input_size
        self.n_layers = n_layers
        self.n_channels = n_channels
        self.use_attention = use_attention
        
        # Input projection
        self.input_conv = nn.Conv1d(1, n_channels, kernel_size=1)
        
        # Dilated convolutions
        self.dilated_convs = nn.ModuleList()
        self.residual_convs = nn.ModuleList()
        self.skip_convs = nn.ModuleList()
        self.dropouts = nn.ModuleList()
        
        for i in range(n_layers):
            dilation = 2 ** i
            self.dilated_convs.append(
                nn.Conv1d(n_channels, n_channels * 2, kernel_size=3,
                         padding=dilation, dilation=dilation)
            )
            self.residual_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.skip_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.dropouts.append(nn.Dropout(dropout))
        
        # Self-attention (optional)
        if use_attention:
            self.attention = nn.MultiheadAttention(n_channels, n_heads, dropout=dropout, batch_first=True)
            self.attention_norm = nn.LayerNorm(n_channels)
        
        # Output layers
        self.output_conv1 = nn.Conv1d(n_channels, n_channels, kernel_size=1)
        self.output_conv2 = nn.Conv1d(n_channels, 1, kernel_size=1)
        self.output_dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        # x: (batch, input_size)
        x = x.unsqueeze(1)  # (batch, 1, input_size)
        
        x = self.input_conv(x)
        
        skip_sum = 0
        for i in range(self.n_layers):
            # Gated activation
            out = self.dilated_convs[i](x)
            tanh_out = torch.tanh(out[:, :self.n_channels, :])
            sigmoid_out = torch.sigmoid(out[:, self.n_channels:, :])
            gated = tanh_out * sigmoid_out
            gated = self.dropouts[i](gated)
            
            # Skip connection
            skip = self.skip_convs[i](gated)
            skip_sum = skip_sum + skip
            
            # Residual connection
            residual = self.residual_convs[i](gated)
            x = x + residual
        
        # Self-attention
        if self.use_attention:
            # (batch, channels, time) -> (batch, time, channels)
            attn_in = skip_sum.permute(0, 2, 1)
            attn_out, _ = self.attention(attn_in, attn_in, attn_in)
            attn_out = self.attention_norm(attn_out + attn_in)
            skip_sum = attn_out.permute(0, 2, 1)
        
        # Output
        out = torch.relu(skip_sum)
        out = self.output_conv1(out)
        out = self.output_dropout(out)
        out = torch.relu(out)
        out = self.output_conv2(out)
        
        # Global average pooling
        out = out.mean(dim=2)
        return out.squeeze(1)
    
    def get_receptive_field(self):
        rf = 1
        for i in range(self.n_layers):
            rf += 2 * (2 ** i)
        return rf


# ============================================================
# 데이터 증강
# ============================================================

def augment_audio(mic, egg, sr):
    """데이터 증강 함수"""
    mic = mic.copy()
    egg = egg.copy()
    
    # Pitch shift (±2 semitones)
    if random.random() < 0.5:
        shift = random.uniform(-2, 2)
        mic = librosa.effects.pitch_shift(mic, sr=sr, n_steps=shift)
        egg = librosa.effects.pitch_shift(egg, sr=sr, n_steps=shift)
    
    # Time stretch (0.9x ~ 1.1x)
    if random.random() < 0.5:
        rate = random.uniform(0.9, 1.1)
        mic = librosa.effects.time_stretch(mic, rate=rate)
        egg = librosa.effects.time_stretch(egg, rate=rate)
    
    # Add noise (SNR 20-40dB)
    if random.random() < 0.3:
        snr_db = random.uniform(20, 40)
        signal_power = np.mean(mic ** 2)
        noise_power = signal_power / (10 ** (snr_db / 10))
        noise = np.random.randn(len(mic)) * np.sqrt(noise_power)
        mic = mic + noise
    
    return mic, egg


# ============================================================
# 데이터 수집 및 전처리
# ============================================================

def get_openglot_speakers(data_dir):
    """OpenGlot 데이터셋에서 화자별 파일 쌍 수집"""
    openglot_dir = Path(data_dir) / "raw" / "OpenGlot"
    
    speaker_files = defaultdict(list)
    mic_files = sorted(openglot_dir.glob("*_mic.wav"))
    
    for mic_path in mic_files:
        filename = mic_path.stem
        speaker_id = filename.split('_')[0]
        
        egg_filename = filename.replace('_mic', '_EGG') + '.wav'
        egg_path = openglot_dir / egg_filename
        
        if egg_path.exists():
            speaker_files[speaker_id].append({
                'mic_path': str(mic_path),
                'egg_path': str(egg_path),
                'speaker_id': speaker_id
            })
    
    return dict(speaker_files)


def process_file_pair(mic_path, egg_path, target_sr=16000, window_length=192, 
                      hop_length=32, augment=False):
    """파일 쌍을 전처리하여 프레임 반환"""
    try:
        # 오디오 로드
        mic, sr_mic = librosa.load(mic_path, sr=target_sr)
        egg, sr_egg = librosa.load(egg_path, sr=target_sr)
        
        # 길이 맞추기
        min_len = min(len(mic), len(egg))
        mic = mic[:min_len]
        egg = egg[:min_len]
        
        # 데이터 증강 (학습 시에만)
        if augment:
            mic, egg = augment_audio(mic, egg, target_sr)
        
        # 정렬
        mic_aligned, egg_aligned, lag, sign = align_signals(mic, egg, target_sr)
        
        if len(mic_aligned) < 1000:
            return None, None
        
        # 전처리
        mic_proc = preprocess_mic(mic_aligned, target_sr)
        egg_proc = preprocess_egg(egg_aligned, target_sr)
        
        # 길이 맞추기
        min_len = min(len(mic_proc), len(egg_proc))
        mic_proc = mic_proc[:min_len]
        egg_proc = egg_proc[:min_len]
        
        # 프레이밍
        mic_frames = frame_signal(mic_proc, window_length, hop_length)
        egg_frames = frame_signal(egg_proc, window_length, hop_length)
        
        # EGG는 중심값만 사용 (스칼라 타겟)
        egg_center = egg_frames[:, window_length // 2]  # (N,)
        
        # 길이 맞추기
        min_frames = min(len(mic_frames), len(egg_center))
        if min_frames == 0:
            return None, None
            
        return mic_frames[:min_frames], egg_center[:min_frames]
        
    except Exception as e:
        print(f"  Error processing {mic_path}: {e}")
        return None, None


def split_speakers(speaker_files, train_ratio=0.7, val_ratio=0.2, seed=42):
    """화자 단위로 train/val/test 분할"""
    random.seed(seed)
    np.random.seed(seed)
    
    speakers = list(speaker_files.keys())
    random.shuffle(speakers)
    
    n_speakers = len(speakers)
    n_train = max(1, int(n_speakers * train_ratio))
    n_val = max(1, int(n_speakers * val_ratio))
    
    train_speakers = speakers[:n_train]
    val_speakers = speakers[n_train:n_train + n_val]
    test_speakers = speakers[n_train + n_val:]
    
    if len(test_speakers) == 0 and len(val_speakers) > 1:
        test_speakers = [val_speakers.pop()]
    if len(test_speakers) == 0 and len(train_speakers) > 1:
        test_speakers = [train_speakers.pop()]
    
    return train_speakers, val_speakers, test_speakers


def collect_frames(speaker_files, speaker_list, augment=False, n_augment=1):
    """화자 리스트의 모든 프레임 수집"""
    all_mic, all_egg = [], []
    
    for spk in speaker_list:
        for file_info in speaker_files[spk]:
            # 원본 데이터
            mic_frames, egg_frames = process_file_pair(
                file_info['mic_path'], file_info['egg_path'], augment=False
            )
            if mic_frames is not None:
                all_mic.append(mic_frames)
                all_egg.append(egg_frames)
            
            # 증강 데이터 (학습 시에만)
            if augment:
                for _ in range(n_augment):
                    mic_frames, egg_frames = process_file_pair(
                        file_info['mic_path'], file_info['egg_path'], augment=True
                    )
                    if mic_frames is not None:
                        all_mic.append(mic_frames)
                        all_egg.append(egg_frames)
    
    if all_mic:
        return np.concatenate(all_mic), np.concatenate(all_egg)
    return np.array([]), np.array([])


# ============================================================
# 데이터셋 클래스
# ============================================================

class EGGDataset(Dataset):
    def __init__(self, mic_frames, egg_frames):
        self.mic_frames = torch.from_numpy(mic_frames).float()
        self.egg_frames = torch.from_numpy(egg_frames).float()
    
    def __len__(self):
        return len(self.mic_frames)
    
    def __getitem__(self, idx):
        return self.mic_frames[idx], self.egg_frames[idx]


# ============================================================
# 학습 및 평가
# ============================================================

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    
    for mic, egg in dataloader:
        mic, egg = mic.to(device), egg.to(device)
        
        optimizer.zero_grad()
        pred = model(mic)
        loss = criterion(pred, egg)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(dataloader)


def evaluate(model, dataloader, device):
    model.eval()
    all_preds, all_gts = [], []
    
    with torch.no_grad():
        for mic, egg in dataloader:
            mic, egg = mic.to(device), egg.to(device)
            pred = model(mic)
            all_preds.append(pred.cpu().numpy())
            all_gts.append(egg.cpu().numpy())
    
    all_preds = np.concatenate(all_preds).flatten()
    all_gts = np.concatenate(all_gts).flatten()
    
    corr = compute_correlation(all_preds, all_gts)
    mse = compute_mse(all_preds, all_gts)
    r2 = compute_r2(all_preds, all_gts)
    
    return corr, mse, r2


def train_model(model, train_loader, val_loader, device, config):
    """모델 학습 (early stopping 포함)"""
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config['lr'], 
                                  weight_decay=config.get('weight_decay', 0))
    scheduler = ExponentialLR(optimizer, gamma=0.95)
    
    best_val_corr = -1
    best_model_state = None
    patience_counter = 0
    patience = config.get('early_stopping_patience', 5)
    
    history = {'train_loss': [], 'val_corr': [], 'val_mse': []}
    
    for epoch in range(1, config['epochs'] + 1):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_corr, val_mse, val_r2 = evaluate(model, val_loader, device)
        scheduler.step()
        
        history['train_loss'].append(train_loss)
        history['val_corr'].append(val_corr)
        history['val_mse'].append(val_mse)
        
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            best_model_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1
        
        if epoch % 10 == 0 or epoch == 1:
            print(f"    Epoch {epoch:2d}: Loss={train_loss:.4f}, Val Corr={val_corr:.4f}")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"    Early stopping at epoch {epoch}")
            break
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    return model, history, best_val_corr


# ============================================================
# 실험 실행
# ============================================================

def run_experiment(exp_name, exp_config, speaker_files, train_spk, val_spk, test_spk, 
                   device, results_dir):
    """단일 실험 실행"""
    print(f"\n{'='*70}")
    print(f"실험: {exp_name}")
    print(f"{'='*70}")
    print(f"설정: {exp_config}")
    
    # 데이터 수집
    print("\n데이터 전처리 중...")
    augment = exp_config.get('augment', False)
    n_augment = exp_config.get('n_augment', 2)
    
    train_mic, train_egg = collect_frames(speaker_files, train_spk, 
                                           augment=augment, n_augment=n_augment)
    val_mic, val_egg = collect_frames(speaker_files, val_spk, augment=False)
    test_mic, test_egg = collect_frames(speaker_files, test_spk, augment=False)
    
    print(f"  Train frames: {len(train_mic)}")
    print(f"  Val frames: {len(val_mic)}")
    print(f"  Test frames: {len(test_mic)}")
    
    if len(train_mic) == 0 or len(val_mic) == 0 or len(test_mic) == 0:
        print("ERROR: 데이터 부족!")
        return None
    
    # 데이터 로더
    train_dataset = EGGDataset(train_mic, train_egg)
    val_dataset = EGGDataset(val_mic, val_egg)
    test_dataset = EGGDataset(test_mic, test_egg)
    
    train_loader = DataLoader(train_dataset, batch_size=exp_config['batch_size'], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=exp_config['batch_size'], shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=exp_config['batch_size'], shuffle=False)
    
    # 모델 생성
    print("\n모델 생성...")
    if exp_config.get('simplified', False):
        model = SimplifiedWaveNet(
            n_layers=exp_config.get('n_layers', 6),
            n_channels=exp_config.get('n_channels', 16),
            dropout=exp_config.get('dropout', 0.5)
        )
    else:
        model = OriginalWaveNet(
            n_layers=exp_config.get('n_layers', 10),
            n_channels=exp_config.get('n_channels', 32),
            dropout=exp_config.get('dropout', 0.3),
            use_attention=exp_config.get('use_attention', True)
        )
    
    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {n_params:,}")
    print(f"  Receptive field: {model.get_receptive_field()} samples")
    
    # 학습
    print("\n학습 시작...")
    model, history, best_val_corr = train_model(model, train_loader, val_loader, device, exp_config)
    
    # 테스트
    test_corr, test_mse, test_r2 = evaluate(model, test_loader, device)
    
    results = {
        'exp_name': exp_name,
        'config': exp_config,
        'best_val_corr': best_val_corr,
        'test_corr': test_corr,
        'test_mse': test_mse,
        'test_r2': test_r2,
        'n_params': n_params,
        'history': history,
        'train_frames': len(train_mic),
        'test_frames': len(test_mic)
    }
    
    print(f"\n결과:")
    print(f"  Best Val Corr: {best_val_corr:.4f}")
    print(f"  Test Corr: {test_corr:.4f}")
    print(f"  Test MSE: {test_mse:.4f}")
    print(f"  Test R²: {test_r2:.4f}")
    
    # 결과 저장
    save_experiment_results(results, results_dir)
    
    return results


def save_experiment_results(results, results_dir):
    """실험 결과 저장"""
    exp_name = results['exp_name']
    
    # 메트릭 저장
    metrics_path = results_dir / f"{exp_name}_metrics.txt"
    with open(metrics_path, 'w') as f:
        f.write(f"{'='*70}\n")
        f.write(f"실험: {results['exp_name']}\n")
        f.write(f"{'='*70}\n\n")
        f.write(f"설정:\n")
        for k, v in results['config'].items():
            f.write(f"  {k}: {v}\n")
        f.write(f"\n모델 파라미터: {results['n_params']:,}\n")
        f.write(f"Train frames: {results['train_frames']}\n")
        f.write(f"Test frames: {results['test_frames']}\n")
        f.write(f"\n{'-'*70}\n")
        f.write(f"결과:\n")
        f.write(f"  Best Val Correlation: {results['best_val_corr']:.4f}\n")
        f.write(f"  Test Correlation: {results['test_corr']:.4f}\n")
        f.write(f"  Test MSE: {results['test_mse']:.4f}\n")
        f.write(f"  Test R²: {results['test_r2']:.4f}\n")
    
    print(f"  저장: {metrics_path}")
    
    # 학습 곡선 저장
    fig, ax = plt.subplots(figsize=(10, 5))
    epochs = range(1, len(results['history']['val_corr']) + 1)
    ax.plot(epochs, results['history']['val_corr'], 'b-', linewidth=2, label='Val Corr')
    ax.axhline(y=0.5, color='g', linestyle='--', label='Target (0.5)')
    ax.axhline(y=0.3, color='orange', linestyle='--', label='Min Target (0.3)')
    ax.axhline(y=-0.0416, color='r', linestyle='--', label='Baseline (-0.04)')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Correlation')
    ax.set_title(f'{exp_name}: Training Progress')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim([-0.2, 0.8])
    
    fig_path = results_dir / f"{exp_name}_training.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  저장: {fig_path}")


def save_comparison(all_results, results_dir):
    """전체 실험 비교 저장"""
    # 비교 그래프
    fig, ax = plt.subplots(figsize=(12, 6))
    
    exp_names = ['Baseline'] + [r['exp_name'] for r in all_results]
    test_corrs = [-0.0416] + [r['test_corr'] for r in all_results]
    
    colors = ['gray'] + ['blue', 'green', 'orange', 'red'][:len(all_results)]
    bars = ax.bar(exp_names, test_corrs, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    
    ax.axhline(y=0.5, color='green', linestyle='--', linewidth=2, label='Good (0.5)')
    ax.axhline(y=0.3, color='orange', linestyle='--', linewidth=2, label='Min (0.3)')
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=1)
    
    ax.set_ylabel('Test Correlation', fontsize=12)
    ax.set_title('Overfitting Fix Experiments Comparison', fontsize=14, fontweight='bold')
    ax.legend()
    ax.set_ylim([-0.2, 0.8])
    
    for bar, corr in zip(bars, test_corrs):
        y_pos = max(corr + 0.02, 0.02) if corr >= 0 else corr - 0.05
        ax.text(bar.get_x() + bar.get_width()/2, y_pos, 
                f'{corr:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    plt.savefig(results_dir / "comparison.png", dpi=200, bbox_inches='tight')
    plt.close()
    
    # 비교 표
    with open(results_dir / "comparison.txt", 'w') as f:
        f.write("="*80 + "\n")
        f.write("과적합 해결 실험 결과 비교\n")
        f.write("="*80 + "\n\n")
        f.write(f"{'실험':<20} {'Test Corr':>12} {'Test MSE':>12} {'개선':>12} {'상태':>10}\n")
        f.write("-"*70 + "\n")
        
        baseline_corr = -0.0416
        f.write(f"{'Baseline':<20} {baseline_corr:>12.4f} {'0.4132':>12} {'-':>12} {'❌':>10}\n")
        
        for r in all_results:
            improvement = r['test_corr'] - baseline_corr
            if r['test_corr'] >= 0.5:
                status = "✅ Good"
            elif r['test_corr'] >= 0.3:
                status = "⚠️ OK"
            else:
                status = "❌ Bad"
            
            f.write(f"{r['exp_name']:<20} {r['test_corr']:>12.4f} {r['test_mse']:>12.4f} {improvement:>+12.4f} {status:>10}\n")
        
        f.write("-"*70 + "\n")
        
        best_exp = max(all_results, key=lambda x: x['test_corr'])
        f.write(f"\n최고 성능: {best_exp['exp_name']} (Corr = {best_exp['test_corr']:.4f})\n")
        
        if best_exp['test_corr'] >= 0.5:
            f.write("결론: ✅ 목표 달성! 논문 수준 성능\n")
        elif best_exp['test_corr'] >= 0.3:
            f.write("결론: ⚠️ 최소 목표 달성. 추가 개선 필요\n")
        else:
            f.write("결론: ❌ 목표 미달. 다른 접근법 필요\n")
    
    print(f"\n저장: {results_dir / 'comparison.png'}")
    print(f"저장: {results_dir / 'comparison.txt'}")


# ============================================================
# 메인
# ============================================================

def main():
    print("="*70)
    print("과적합 해결 실험")
    print("목표: 화자 단위 분할에서 corr >= 0.5")
    print("="*70)
    
    device = get_device()
    print(f"Device: {device}")
    
    base_dir = Path(__file__).parent
    data_dir = base_dir.parent / "data"
    results_dir = base_dir / "results" / "overfitting_fix"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # 데이터 수집
    print("\n데이터셋 로드...")
    speaker_files = get_openglot_speakers(data_dir)
    print(f"총 화자 수: {len(speaker_files)}")
    
    # 화자 분할 (고정)
    train_spk, val_spk, test_spk = split_speakers(speaker_files)
    print(f"Train: {train_spk}")
    print(f"Val: {val_spk}")
    print(f"Test: {test_spk}")
    
    # 실험 설정
    experiments = {
        'exp1_regularization': {
            'dropout': 0.5,
            'weight_decay': 1e-4,
            'early_stopping_patience': 5,
            'epochs': 50,
            'lr': 0.001,
            'batch_size': 256,
            'n_layers': 10,
            'n_channels': 32,
            'use_attention': True,
            'simplified': False,
            'augment': False
        },
        'exp2_simplified': {
            'dropout': 0.5,
            'weight_decay': 1e-4,
            'early_stopping_patience': 5,
            'epochs': 50,
            'lr': 0.001,
            'batch_size': 256,
            'n_layers': 6,
            'n_channels': 16,
            'use_attention': False,
            'simplified': True,
            'augment': False
        },
        'exp3_augmentation': {
            'dropout': 0.5,
            'weight_decay': 1e-4,
            'early_stopping_patience': 5,
            'epochs': 50,
            'lr': 0.001,
            'batch_size': 256,
            'n_layers': 6,
            'n_channels': 16,
            'use_attention': False,
            'simplified': True,
            'augment': True,
            'n_augment': 3
        },
        'exp4_full_combination': {
            'dropout': 0.6,
            'weight_decay': 5e-4,
            'early_stopping_patience': 10,
            'epochs': 100,
            'lr': 0.0005,
            'batch_size': 128,
            'n_layers': 6,
            'n_channels': 16,
            'use_attention': False,
            'simplified': True,
            'augment': True,
            'n_augment': 5
        }
    }
    
    # 실험 실행
    all_results = []
    
    for exp_name, exp_config in experiments.items():
        results = run_experiment(
            exp_name, exp_config, speaker_files, 
            train_spk, val_spk, test_spk, device, results_dir
        )
        if results:
            all_results.append(results)
        
        # 중간 결과 확인
        if results and results['test_corr'] >= 0.5:
            print(f"\n🎉 목표 달성! {exp_name}: corr = {results['test_corr']:.4f}")
    
    # 전체 비교
    print("\n" + "="*70)
    print("전체 실험 비교")
    print("="*70)
    
    save_comparison(all_results, results_dir)
    
    # 최종 결과 출력
    print("\n" + "="*70)
    print("최종 결과")
    print("="*70)
    
    print(f"\n{'실험':<25} {'Test Corr':>12} {'개선':>12}")
    print("-"*50)
    print(f"{'Baseline':<25} {-0.0416:>12.4f} {'-':>12}")
    
    for r in all_results:
        improvement = r['test_corr'] - (-0.0416)
        print(f"{r['exp_name']:<25} {r['test_corr']:>12.4f} {improvement:>+12.4f}")
    
    best = max(all_results, key=lambda x: x['test_corr'])
    print(f"\n최고 성능: {best['exp_name']} (corr = {best['test_corr']:.4f})")


if __name__ == "__main__":
    main()
