"""
PTDB-TUG 데이터셋으로 화자 독립 EGG 예측 모델 학습
목표: 화자 분할 corr >= 0.5
"""
import os
import sys
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import ExponentialLR
from pathlib import Path
import numpy as np
import librosa
from scipy import signal
from collections import defaultdict
import matplotlib.pyplot as plt
import random
import copy
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from utils.metrics import compute_correlation, compute_mse, compute_r2


# ============================================================
# 모델 정의
# ============================================================

class WaveNetEGG(nn.Module):
    """WaveNet + Self-Attention for EGG prediction"""
    def __init__(self, input_size=192, n_layers=10, n_channels=32, 
                 n_heads=4, dropout=0.5):
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
        
        # Self-attention
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
# PTDB-TUG 전처리
# ============================================================

def highpass_filter(data, cutoff, sr, order=5):
    """Kaiser window highpass filter"""
    nyq = sr / 2
    normalized_cutoff = cutoff / nyq
    b, a = signal.butter(order, normalized_cutoff, btype='high')
    return signal.filtfilt(b, a, data)


def bandpass_filter(data, low, high, sr, order=5):
    """Bandpass filter"""
    nyq = sr / 2
    low_norm = low / nyq
    high_norm = high / nyq
    b, a = signal.butter(order, [low_norm, high_norm], btype='band')
    return signal.filtfilt(b, a, data)


def preprocess_mic_ptdb(mic, sr):
    """MIC 신호 전처리"""
    # Highpass 30Hz
    mic = highpass_filter(mic, 30, sr)
    # Normalize
    mic = mic / (np.max(np.abs(mic)) + 1e-8)
    return mic


def preprocess_lar_ptdb(lar, sr):
    """LAR(EGG) 신호 전처리 - PTDB 논문 기준"""
    # Bandpass 80-4000Hz
    lar = bandpass_filter(lar, 80, 4000, sr)
    # Normalize
    lar = lar / (np.max(np.abs(lar)) + 1e-8)
    return lar


def frame_signal(signal, window_length=192, hop_length=32):
    """신호를 프레임으로 분할"""
    n_frames = (len(signal) - window_length) // hop_length + 1
    if n_frames <= 0:
        return np.array([])
    
    frames = np.zeros((n_frames, window_length))
    for i in range(n_frames):
        start = i * hop_length
        frames[i] = signal[start:start + window_length]
    return frames


def align_signals_simple(mic, lar, max_lag=1000):
    """간단한 cross-correlation 정렬 (PTDB는 동시 녹음이라 약간의 지연만)"""
    # 중앙 부분만 사용하여 빠르게 정렬
    center = len(mic) // 2
    window = min(10000, len(mic) // 4)
    
    mic_seg = mic[center - window:center + window]
    lar_seg = lar[center - window:center + window]
    
    corr = signal.correlate(mic_seg, lar_seg, mode='full')
    lags = signal.correlation_lags(len(mic_seg), len(lar_seg), mode='full')
    
    # max_lag 범위 내에서 최대 상관 찾기
    valid_idx = np.abs(lags) <= max_lag
    corr_valid = corr[valid_idx]
    lags_valid = lags[valid_idx]
    
    best_idx = np.argmax(np.abs(corr_valid))
    best_lag = lags_valid[best_idx]
    
    # 정렬
    if best_lag > 0:
        mic_aligned = mic[best_lag:]
        lar_aligned = lar[:len(mic_aligned)]
    elif best_lag < 0:
        lar_aligned = lar[-best_lag:]
        mic_aligned = mic[:len(lar_aligned)]
    else:
        mic_aligned = mic
        lar_aligned = lar
    
    # 길이 맞추기
    min_len = min(len(mic_aligned), len(lar_aligned))
    return mic_aligned[:min_len], lar_aligned[:min_len], best_lag


# ============================================================
# PTDB-TUG 데이터 로더
# ============================================================

def load_ptdb_data(base_path):
    """PTDB-TUG 데이터 로드"""
    pairs = []
    base_path = Path(base_path)
    
    for gender in ['FEMALE', 'MALE']:
        mic_dir = base_path / gender / 'MIC'
        lar_dir = base_path / gender / 'LAR'
        
        if not mic_dir.exists():
            continue
            
        for speaker in sorted(os.listdir(mic_dir)):
            if speaker.startswith('.'):
                continue
                
            speaker_mic_dir = mic_dir / speaker
            speaker_lar_dir = lar_dir / speaker
            
            if not speaker_mic_dir.is_dir():
                continue
                
            for mic_file in sorted(os.listdir(speaker_mic_dir)):
                if not mic_file.endswith('.wav'):
                    continue
                    
                # mic_F01_sa1.wav → lar_F01_sa1.wav
                lar_file = mic_file.replace('mic_', 'lar_')
                
                mic_path = speaker_mic_dir / mic_file
                lar_path = speaker_lar_dir / lar_file
                
                if lar_path.exists():
                    pairs.append({
                        'mic': str(mic_path),
                        'lar': str(lar_path),
                        'speaker': speaker,
                        'gender': gender
                    })
    
    return pairs


def process_ptdb_pair(mic_path, lar_path, target_sr=16000, window_length=192, hop_length=32):
    """PTDB 파일 쌍 전처리"""
    try:
        # 오디오 로드 (원본 48kHz → 16kHz 리샘플링)
        mic, sr = librosa.load(mic_path, sr=target_sr)
        lar, _ = librosa.load(lar_path, sr=target_sr)
        
        # 길이 맞추기
        min_len = min(len(mic), len(lar))
        mic = mic[:min_len]
        lar = lar[:min_len]
        
        if len(mic) < 2000:
            return None, None
        
        # 정렬 (동시 녹음이라 작은 지연만)
        mic_aligned, lar_aligned, lag = align_signals_simple(mic, lar, max_lag=500)
        
        if len(mic_aligned) < 1000:
            return None, None
        
        # 전처리
        mic_proc = preprocess_mic_ptdb(mic_aligned, target_sr)
        lar_proc = preprocess_lar_ptdb(lar_aligned, target_sr)
        
        # 프레이밍
        mic_frames = frame_signal(mic_proc, window_length, hop_length)
        lar_frames = frame_signal(lar_proc, window_length, hop_length)
        
        if len(mic_frames) == 0 or len(lar_frames) == 0:
            return None, None
        
        # LAR은 중심값만 사용 (스칼라 타겟)
        lar_center = lar_frames[:, window_length // 2]
        
        # 길이 맞추기
        min_frames = min(len(mic_frames), len(lar_center))
        
        return mic_frames[:min_frames], lar_center[:min_frames]
        
    except Exception as e:
        print(f"  Error: {mic_path}: {e}")
        return None, None


# ============================================================
# 데이터셋
# ============================================================

class PTDBDataset(Dataset):
    def __init__(self, mic_frames, lar_frames):
        self.mic_frames = torch.from_numpy(mic_frames).float()
        self.lar_frames = torch.from_numpy(lar_frames).float()
    
    def __len__(self):
        return len(self.mic_frames)
    
    def __getitem__(self, idx):
        return self.mic_frames[idx], self.lar_frames[idx]


# ============================================================
# 학습
# ============================================================

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train_epoch(model, dataloader, criterion, optimizer, device, epoch=0, total_epochs=0):
    model.train()
    total_loss = 0
    n_batches = len(dataloader)
    
    for batch_idx, (mic, lar) in enumerate(dataloader, 1):
        mic, lar = mic.to(device), lar.to(device)
        
        optimizer.zero_grad()
        pred = model(mic)
        loss = criterion(pred, lar)
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
        
        # 진행률 계산 (10% 단위로만 출력)
        progress = batch_idx / n_batches * 100
        if batch_idx == 1 or batch_idx == n_batches or batch_idx % max(1, n_batches // 10) == 0:
            avg_loss = total_loss / batch_idx
            print(f"\r  Epoch {epoch:3d}/{total_epochs} | Batch {batch_idx:4d}/{n_batches} | {progress:5.1f}% | Loss: {avg_loss:.4f}", end='', flush=True)
    
    print()  # 줄바꿈
    return total_loss / n_batches


def evaluate(model, dataloader, device):
    model.eval()
    all_preds, all_gts = [], []
    
    with torch.no_grad():
        for mic, lar in dataloader:
            mic, lar = mic.to(device), lar.to(device)
            pred = model(mic)
            all_preds.append(pred.cpu().numpy())
            all_gts.append(lar.cpu().numpy())
    
    all_preds = np.concatenate(all_preds).flatten()
    all_gts = np.concatenate(all_gts).flatten()
    
    corr = compute_correlation(all_preds, all_gts)
    mse = compute_mse(all_preds, all_gts)
    r2 = compute_r2(all_preds, all_gts)
    
    return corr, mse, r2, all_preds, all_gts


# ============================================================
# 메인 실험
# ============================================================

def main():
    print("=" * 70)
    print("PTDB-TUG 화자 독립 EGG 예측 실험")
    print("목표: 화자 분할 corr >= 0.5")
    print("=" * 70)
    
    device = get_device()
    print(f"Device: {device}")
    
    base_dir = Path(__file__).parent
    ptdb_path = base_dir.parent / "data" / "raw" / "PTDB-TUG"
    results_dir = base_dir / "results" / "ptdb_experiment"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # ============================================================
    # 1. 데이터 로드
    # ============================================================
    print("\n[1] 데이터 로드...")
    all_pairs = load_ptdb_data(ptdb_path)
    print(f"  총 파일 쌍: {len(all_pairs)}")
    
    # 화자별 통계
    speaker_counts = defaultdict(int)
    for pair in all_pairs:
        speaker_counts[pair['speaker']] += 1
    
    print(f"  화자 수: {len(speaker_counts)}")
    for spk, count in sorted(speaker_counts.items()):
        print(f"    {spk}: {count} files")
    
    # ============================================================
    # 2. 화자 분할 (Train 16명, Test 4명)
    # ============================================================
    print("\n[2] 화자 분할...")
    
    all_speakers = sorted(speaker_counts.keys())
    
    # 고정 분할: F09, F10, M09, M10을 테스트로
    test_speakers = ['F09', 'F10', 'M09', 'M10']
    train_speakers = [s for s in all_speakers if s not in test_speakers]
    
    # Validation을 위해 train에서 2명 분리
    val_speakers = ['F08', 'M08']
    train_speakers = [s for s in train_speakers if s not in val_speakers]
    
    print(f"  Train 화자 ({len(train_speakers)}명): {train_speakers}")
    print(f"  Val 화자 ({len(val_speakers)}명): {val_speakers}")
    print(f"  Test 화자 ({len(test_speakers)}명): {test_speakers}")
    
    # 화자별 데이터 분류
    train_pairs = [p for p in all_pairs if p['speaker'] in train_speakers]
    val_pairs = [p for p in all_pairs if p['speaker'] in val_speakers]
    test_pairs = [p for p in all_pairs if p['speaker'] in test_speakers]
    
    print(f"  Train 파일: {len(train_pairs)}")
    print(f"  Val 파일: {len(val_pairs)}")
    print(f"  Test 파일: {len(test_pairs)}")
    
    # ============================================================
    # 3. 전처리
    # ============================================================
    print("\n[3] 전처리 중...")
    
    def collect_frames(pairs, desc=""):
        all_mic, all_lar = [], []
        n_pairs = len(pairs)
        
        for i, pair in enumerate(pairs, 1):
            mic_frames, lar_frames = process_ptdb_pair(pair['mic'], pair['lar'])
            if mic_frames is not None:
                all_mic.append(mic_frames)
                all_lar.append(lar_frames)
            
            # 10% 단위로 진행률 출력
            progress = i / n_pairs * 100
            if i == 1 or i == n_pairs or i % max(1, n_pairs // 10) == 0:
                print(f"\r  {desc}: {i:4d}/{n_pairs} ({progress:5.1f}%)", end='', flush=True)
        
        print()  # 줄바꿈
        
        if all_mic:
            return np.concatenate(all_mic), np.concatenate(all_lar)
        return np.array([]), np.array([])
    
    train_mic, train_lar = collect_frames(train_pairs, "Train")
    val_mic, val_lar = collect_frames(val_pairs, "Val")
    test_mic, test_lar = collect_frames(test_pairs, "Test")
    
    print(f"\n  Train frames: {len(train_mic)}")
    print(f"  Val frames: {len(val_mic)}")
    print(f"  Test frames: {len(test_mic)}")
    
    if len(train_mic) == 0 or len(val_mic) == 0 or len(test_mic) == 0:
        print("ERROR: 데이터 부족!")
        return
    
    # ============================================================
    # 4. 데이터 로더 생성
    # ============================================================
    print("\n[4] 데이터 로더 생성...")
    
    train_dataset = PTDBDataset(train_mic, train_lar)
    val_dataset = PTDBDataset(val_mic, val_lar)
    test_dataset = PTDBDataset(test_mic, test_lar)
    
    train_loader = DataLoader(train_dataset, batch_size=512, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=512, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=512, shuffle=False, num_workers=0)
    
    # ============================================================
    # 5. 모델 생성
    # ============================================================
    print("\n[5] 모델 생성...")
    
    model = WaveNetEGG(
        input_size=192,
        n_layers=10,
        n_channels=32,
        n_heads=4,
        dropout=0.5
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {n_params:,}")
    print(f"  Receptive field: {model.get_receptive_field()} samples")
    
    # ============================================================
    # 6. 학습
    # ============================================================
    print("\n[6] 학습 시작...")
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = ExponentialLR(optimizer, gamma=0.95)
    
    best_val_corr = -1
    best_model_state = None
    patience_counter = 0
    patience = 10
    
    history = {'train_loss': [], 'val_corr': [], 'val_mse': [], 'val_r2': []}
    
    epochs = 100
    import time
    start_time = time.time()
    
    print(f"\n  {'='*70}")
    print(f"  학습 시작 (총 {epochs} epochs, Early Stopping patience={patience})")
    print(f"  {'='*70}")
    
    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device, epoch, epochs)
        val_corr, val_mse, val_r2, val_preds, val_gts = evaluate(model, val_loader, device)
        scheduler.step()
        
        epoch_time = time.time() - epoch_start
        total_elapsed = time.time() - start_time
        avg_epoch_time = total_elapsed / epoch
        remaining_epochs = epochs - epoch
        eta = avg_epoch_time * remaining_epochs
        
        history['train_loss'].append(train_loss)
        history['val_corr'].append(val_corr)
        history['val_mse'].append(val_mse)
        history['val_r2'].append(val_r2)
        
        # 추가 메트릭 계산
        val_std = np.std(val_preds - val_gts)
        
        improved = ""
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            best_model_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
            improved = " ★ NEW BEST"
        else:
            patience_counter += 1
        
        # 상세 Epoch 결과 출력
        print(f"  {'─'*70}")
        print(f"  Epoch {epoch:3d}/{epochs} 완료 ({epoch_time:.1f}s) | ETA: {eta/60:.1f}분")
        print(f"    Loss: {train_loss:.6f}")
        print(f"    Val Corr: {val_corr:.4f} | MSE: {val_mse:.6f} | R²: {val_r2:.4f} | Std: {val_std:.4f}")
        print(f"    Best Corr: {best_val_corr:.4f} | Patience: {patience_counter}/{patience}{improved}")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\n  ⚠️ Early stopping at epoch {epoch}")
            break
    
    total_time = time.time() - start_time
    print(f"\n  {'='*70}")
    print(f"  학습 완료! 총 시간: {total_time/60:.1f}분")
    print(f"  {'='*70}")
    
    # ============================================================
    # 7. 테스트
    # ============================================================
    print("\n[7] 테스트...")
    
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    test_corr, test_mse, test_r2, test_preds, test_gts = evaluate(model, test_loader, device)
    
    print(f"\n{'='*70}")
    print("PTDB-TUG 화자 독립 실험 결과")
    print(f"{'='*70}")
    print(f"  Train 화자: {len(train_speakers)}명")
    print(f"  Test 화자: {test_speakers} ({len(test_speakers)}명)")
    print(f"\n  Best Val Correlation: {best_val_corr:.4f}")
    print(f"  Test Correlation: {test_corr:.4f}")
    print(f"  Test MSE: {test_mse:.4f}")
    print(f"  Test R²: {test_r2:.4f}")
    
    # 목표 달성 여부
    if test_corr >= 0.5:
        status = "✅ 목표 달성!"
    elif test_corr >= 0.3:
        status = "⚠️ 최소 목표 달성"
    else:
        status = "❌ 목표 미달"
    
    print(f"\n  결론: {status}")
    
    # ============================================================
    # 8. 결과 저장
    # ============================================================
    print("\n[8] 결과 저장...")
    
    # 메트릭 저장
    with open(results_dir / "metrics.txt", 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("PTDB-TUG 화자 독립 EGG 예측 실험 결과\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"데이터셋: PTDB-TUG\n")
        f.write(f"총 화자: 20명 (F01-F10, M01-M10)\n")
        f.write(f"총 파일 쌍: {len(all_pairs)}\n\n")
        f.write("-" * 70 + "\n")
        f.write("화자 분할\n")
        f.write("-" * 70 + "\n")
        f.write(f"Train 화자 ({len(train_speakers)}명): {', '.join(train_speakers)}\n")
        f.write(f"Val 화자 ({len(val_speakers)}명): {', '.join(val_speakers)}\n")
        f.write(f"Test 화자 ({len(test_speakers)}명): {', '.join(test_speakers)}\n\n")
        f.write(f"Train frames: {len(train_mic)}\n")
        f.write(f"Val frames: {len(val_mic)}\n")
        f.write(f"Test frames: {len(test_mic)}\n\n")
        f.write("-" * 70 + "\n")
        f.write("모델\n")
        f.write("-" * 70 + "\n")
        f.write(f"Architecture: WaveNet + Self-Attention\n")
        f.write(f"Parameters: {n_params:,}\n")
        f.write(f"Receptive field: {model.get_receptive_field()} samples\n")
        f.write(f"Dropout: 0.5\n")
        f.write(f"Weight decay: 1e-4\n\n")
        f.write("-" * 70 + "\n")
        f.write("결과\n")
        f.write("-" * 70 + "\n")
        f.write(f"Best Val Correlation: {best_val_corr:.4f}\n")
        f.write(f"Test Correlation: {test_corr:.4f}\n")
        f.write(f"Test MSE: {test_mse:.4f}\n")
        f.write(f"Test R²: {test_r2:.4f}\n\n")
        f.write(f"결론: {status}\n")
    
    print(f"  저장: {results_dir / 'metrics.txt'}")
    
    # 학습 곡선
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    epochs_range = range(1, len(history['val_corr']) + 1)
    
    # 왼쪽: Correlation
    axes[0].plot(epochs_range, history['val_corr'], 'b-', linewidth=2, label='Val Corr')
    axes[0].axhline(y=0.5, color='g', linestyle='--', linewidth=2, label='Target (0.5)')
    axes[0].axhline(y=0.3, color='orange', linestyle='--', linewidth=2, label='Min Target (0.3)')
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Correlation', fontsize=12)
    axes[0].set_title('PTDB-TUG Speaker-Independent Training', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([-0.2, 1.0])
    
    # 오른쪽: 비교
    methods = ['OpenGlot\nBaseline', 'OpenGlot\nBest', 'PTDB-TUG\n(Current)']
    corrs = [-0.0416, 0.0709, test_corr]
    colors = ['gray', 'blue', 'green' if test_corr >= 0.3 else 'red']
    
    bars = axes[1].bar(methods, corrs, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    axes[1].axhline(y=0.5, color='g', linestyle='--', linewidth=2, label='Target (0.5)')
    axes[1].axhline(y=0.3, color='orange', linestyle='--', linewidth=2, label='Min (0.3)')
    axes[1].axhline(y=0, color='gray', linestyle='-', linewidth=1)
    axes[1].set_ylabel('Test Correlation', fontsize=12)
    axes[1].set_title('Comparison with OpenGlot', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].set_ylim([-0.2, 0.8])
    
    for bar, corr in zip(bars, corrs):
        y_pos = max(corr + 0.02, 0.02) if corr >= 0 else corr - 0.05
        axes[1].text(bar.get_x() + bar.get_width()/2, y_pos, 
                     f'{corr:.3f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(results_dir / "comparison.png", dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"  저장: {results_dir / 'comparison.png'}")
    
    # 예측 시각화
    fig, ax = plt.subplots(figsize=(14, 4))
    
    # 일부만 시각화
    n_show = min(2000, len(test_preds))
    ax.plot(test_gts[:n_show], 'b-', alpha=0.7, linewidth=1, label='Ground Truth (LAR)')
    ax.plot(test_preds[:n_show], 'r-', alpha=0.7, linewidth=1, label='Predicted')
    ax.set_xlabel('Frame', fontsize=12)
    ax.set_ylabel('Amplitude', fontsize=12)
    ax.set_title(f'PTDB-TUG Test Prediction (corr={test_corr:.4f})', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(results_dir / "prediction.png", dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"  저장: {results_dir / 'prediction.png'}")
    
    print("\n완료!")


if __name__ == "__main__":
    main()
