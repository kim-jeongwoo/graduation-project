"""
화자 단위 분할 검증 실험
기존 모델(corr 0.9571)이 진짜 좋은 건지 검증

핵심: 테스트 화자의 데이터는 학습에 절대 포함되지 않음
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

sys.path.insert(0, str(Path(__file__).parent))

from model import WaveNetEGG, create_model
from utils.alignment import align_signals
from utils.preprocessing import preprocess_mic, preprocess_egg, frame_signal
from utils.metrics import compute_correlation, compute_mse, compute_r2


# ============================================================
# 1. 화자별 데이터 수집
# ============================================================

def get_openglot_speakers(data_dir):
    """OpenGlot 데이터셋에서 화자별 파일 쌍 수집"""
    openglot_dir = Path(data_dir) / "raw" / "OpenGlot"
    
    speaker_files = defaultdict(list)
    
    mic_files = sorted(openglot_dir.glob("*_mic.wav"))
    
    for mic_path in mic_files:
        # F01_breathy_high_mic.wav -> F01
        filename = mic_path.stem  # F01_breathy_high_mic
        speaker_id = filename.split('_')[0]  # F01
        
        # EGG 파일 찾기
        egg_filename = filename.replace('_mic', '_EGG') + '.wav'
        egg_path = openglot_dir / egg_filename
        
        if egg_path.exists():
            speaker_files[speaker_id].append({
                'mic_path': str(mic_path),
                'egg_path': str(egg_path),
                'speaker_id': speaker_id
            })
    
    return dict(speaker_files)


def get_pmc_singvoice_files(data_dir, dataset_name):
    """PMC/Singing-Voice 데이터셋 파일 쌍 수집 (화자 정보 없음 - 파일 단위 분할)"""
    dataset_dir = Path(data_dir) / "raw" / dataset_name / "DATASET"
    
    mic_dir = dataset_dir / "MIC"
    egg_dir = dataset_dir / "EGG"
    
    file_pairs = []
    
    for mic_path in sorted(mic_dir.glob("*.wav")):
        file_id = mic_path.stem
        egg_path = egg_dir / f"{file_id}.wav"
        
        if egg_path.exists():
            file_pairs.append({
                'mic_path': str(mic_path),
                'egg_path': str(egg_path),
                'file_id': file_id
            })
    
    return file_pairs


# ============================================================
# 2. 전처리 함수
# ============================================================

def process_file_pair(mic_path, egg_path, target_sr=16000, window_length=192, hop_length=32):
    """파일 쌍을 전처리하여 프레임 반환"""
    try:
        # 오디오 로드
        mic, sr_mic = librosa.load(mic_path, sr=None)
        egg, sr_egg = librosa.load(egg_path, sr=None)
        
        # 길이 맞추기
        min_len = min(len(mic), len(egg))
        mic = mic[:min_len]
        egg = egg[:min_len]
        
        # 정렬
        mic_aligned, egg_aligned, lag, sign = align_signals(mic, egg, sr_mic)
        
        if len(mic_aligned) < 1000:
            return None, None
        
        # 전처리
        mic_proc = preprocess_mic(mic_aligned, sr_mic)
        egg_proc = preprocess_egg(egg_aligned, sr_egg)
        
        # 길이 맞추기
        min_len = min(len(mic_proc), len(egg_proc))
        mic_proc = mic_proc[:min_len]
        egg_proc = egg_proc[:min_len]
        
        # 프레이밍
        mic_frames = frame_signal(mic_proc, window_length, hop_length)
        egg_frames = frame_signal(egg_proc, window_length, hop_length)
        
        # 길이 맞추기
        min_frames = min(len(mic_frames), len(egg_frames))
        if min_frames == 0:
            return None, None
            
        return mic_frames[:min_frames], egg_frames[:min_frames]
        
    except Exception as e:
        print(f"  Error processing {mic_path}: {e}")
        return None, None


# ============================================================
# 3. 화자 단위 분할
# ============================================================

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
    
    # 최소 1명씩 보장
    if len(test_speakers) == 0 and len(val_speakers) > 1:
        test_speakers = [val_speakers.pop()]
    if len(test_speakers) == 0 and len(train_speakers) > 1:
        test_speakers = [train_speakers.pop()]
    
    return train_speakers, val_speakers, test_speakers


def split_files(file_pairs, train_ratio=0.7, val_ratio=0.2, seed=42):
    """파일 단위로 train/val/test 분할 (화자 정보 없는 경우)"""
    random.seed(seed)
    np.random.seed(seed)
    
    files = list(file_pairs)
    random.shuffle(files)
    
    n_files = len(files)
    n_train = int(n_files * train_ratio)
    n_val = int(n_files * val_ratio)
    
    train_files = files[:n_train]
    val_files = files[n_train:n_train + n_val]
    test_files = files[n_train + n_val:]
    
    return train_files, val_files, test_files


# ============================================================
# 4. 데이터셋 클래스
# ============================================================

class SpeakerSplitDataset(Dataset):
    def __init__(self, mic_frames, egg_frames):
        self.mic_frames = torch.from_numpy(mic_frames).float()
        self.egg_frames = torch.from_numpy(egg_frames).float()
    
    def __len__(self):
        return len(self.mic_frames)
    
    def __getitem__(self, idx):
        return self.mic_frames[idx], self.egg_frames[idx]


# ============================================================
# 5. 학습 및 평가
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


# ============================================================
# 6. 메인 실험
# ============================================================

def main():
    print("=" * 70)
    print("화자 단위 분할 검증 실험")
    print("목표: 기존 모델(corr 0.9571)이 과적합인지 검증")
    print("=" * 70)
    
    device = get_device()
    print(f"Device: {device}")
    
    base_dir = Path(__file__).parent
    data_dir = base_dir.parent / "data"
    
    # ============================================================
    # OpenGlot (화자 단위 분할 가능)
    # ============================================================
    print("\n" + "=" * 70)
    print("[1] OpenGlot 데이터셋 - 화자 단위 분할")
    print("=" * 70)
    
    speaker_files = get_openglot_speakers(data_dir)
    print(f"총 화자 수: {len(speaker_files)}")
    for spk, files in speaker_files.items():
        print(f"  {spk}: {len(files)} files")
    
    # 화자 단위 분할
    train_spk, val_spk, test_spk = split_speakers(speaker_files)
    print(f"\n화자 분할:")
    print(f"  Train: {train_spk} ({len(train_spk)}명)")
    print(f"  Val: {val_spk} ({len(val_spk)}명)")
    print(f"  Test: {test_spk} ({len(test_spk)}명)")
    
    # 데이터 전처리
    print("\n전처리 중...")
    
    def collect_frames(speaker_list):
        all_mic, all_egg = [], []
        for spk in speaker_list:
            for file_info in speaker_files[spk]:
                mic_frames, egg_frames = process_file_pair(
                    file_info['mic_path'], file_info['egg_path']
                )
                if mic_frames is not None:
                    all_mic.append(mic_frames)
                    all_egg.append(egg_frames)
        if all_mic:
            return np.concatenate(all_mic), np.concatenate(all_egg)
        return np.array([]), np.array([])
    
    train_mic, train_egg = collect_frames(train_spk)
    val_mic, val_egg = collect_frames(val_spk)
    test_mic, test_egg = collect_frames(test_spk)
    
    print(f"  Train frames: {len(train_mic)}")
    print(f"  Val frames: {len(val_mic)}")
    print(f"  Test frames: {len(test_mic)}")
    
    if len(train_mic) == 0 or len(val_mic) == 0 or len(test_mic) == 0:
        print("ERROR: 데이터가 부족합니다!")
        return
    
    # 데이터셋 생성
    train_dataset = SpeakerSplitDataset(train_mic, train_egg)
    val_dataset = SpeakerSplitDataset(val_mic, val_egg)
    test_dataset = SpeakerSplitDataset(test_mic, test_egg)
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False)
    
    # 모델 생성
    print("\n모델 생성...")
    config_path = base_dir / "configs" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model = create_model(config['model']).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = ExponentialLR(optimizer, gamma=0.95)
    
    # 학습
    print("\n학습 시작 (50 epochs)...")
    best_val_corr = -1
    history = {'train_loss': [], 'val_corr': [], 'val_mse': []}
    
    for epoch in range(1, 51):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_corr, val_mse, val_r2 = evaluate(model, val_loader, device)
        scheduler.step()
        
        history['train_loss'].append(train_loss)
        history['val_corr'].append(val_corr)
        history['val_mse'].append(val_mse)
        
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            best_model_state = model.state_dict().copy()
        
        if epoch % 10 == 0 or epoch == 1:
            print(f"  Epoch {epoch:2d}: Loss={train_loss:.4f}, Val Corr={val_corr:.4f}, Val MSE={val_mse:.4f}")
    
    # 최고 모델로 테스트
    model.load_state_dict(best_model_state)
    test_corr, test_mse, test_r2 = evaluate(model, test_loader, device)
    
    print(f"\n" + "=" * 70)
    print("OpenGlot 화자 단위 분할 결과")
    print("=" * 70)
    print(f"  Best Val Correlation: {best_val_corr:.4f}")
    print(f"  Test Correlation: {test_corr:.4f}")
    print(f"  Test MSE: {test_mse:.4f}")
    print(f"  Test R²: {test_r2:.4f}")
    
    openglot_result = {
        'val_corr': best_val_corr,
        'test_corr': test_corr,
        'test_mse': test_mse,
        'test_r2': test_r2,
        'train_speakers': train_spk,
        'test_speakers': test_spk
    }
    
    # ============================================================
    # 결과 비교 및 저장
    # ============================================================
    print("\n" + "=" * 70)
    print("최종 결과 비교")
    print("=" * 70)
    
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│                    화자 단위 분할 검증 결과                          │
├─────────────────────────────────────────────────────────────────────┤
│  데이터셋: OpenGlot (화자 10명)                                      │
│  Train 화자: {', '.join(train_spk)} ({len(train_spk)}명)
│  Test 화자: {', '.join(test_spk)} ({len(test_spk)}명)
├─────────────────────────────────────────────────────────────────────┤
│  분할 방식          │ Correlation │ MSE     │ 의미                  │
├─────────────────────────────────────────────────────────────────────┤
│  프레임 단위 (기존) │   0.9571    │ 0.0201  │ 같은 화자 내 일반화   │
│  화자 단위 (검증)   │   {test_corr:.4f}    │ {test_mse:.4f}  │ 새로운 화자 일반화   │
├─────────────────────────────────────────────────────────────────────┤
│  차이: {0.9571 - test_corr:+.4f}                                              │
└─────────────────────────────────────────────────────────────────────┘
""")
    
    # 결론 출력
    if test_corr >= 0.8:
        conclusion = "✅ 모델이 진짜 좋음! 새로운 화자에도 잘 일반화됨"
    elif test_corr >= 0.5:
        conclusion = "⚠️ 논문 수준 성능. 일부 과적합 있지만 사용 가능"
    else:
        conclusion = "❌ 과적합 심각. 모델 수정 필요"
    
    print(f"결론: {conclusion}")
    
    # 결과 저장
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)
    
    # 비교 그래프 생성
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 왼쪽: 학습 곡선
    epochs = range(1, 51)
    axes[0].plot(epochs, history['val_corr'], 'g-', linewidth=2, label='Speaker-Split Val Corr')
    axes[0].axhline(y=0.9571, color='b', linestyle='--', linewidth=2, label='Frame-Split (0.9571)')
    axes[0].axhline(y=0.7, color='r', linestyle='--', linewidth=2, label='Target (0.7)')
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Correlation', fontsize=12)
    axes[0].set_title('Speaker-Split Training Progress', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([0, 1.0])
    
    # 오른쪽: 비교 막대 그래프
    methods = ['Frame-Split\n(기존)', 'Speaker-Split\n(검증)']
    corrs = [0.9571, test_corr]
    colors = ['blue', 'green']
    
    bars = axes[1].bar(methods, corrs, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    axes[1].axhline(y=0.7, color='r', linestyle='--', linewidth=2, label='Target (0.7)')
    axes[1].set_ylabel('Correlation', fontsize=12)
    axes[1].set_title('Correlation Comparison', fontsize=14, fontweight='bold')
    axes[1].set_ylim([0, 1.1])
    axes[1].legend()
    
    for bar, corr in zip(bars, corrs):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                     f'{corr:.4f}', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(results_dir / "speaker_split_comparison.png", dpi=200, bbox_inches='tight')
    plt.close()
    print(f"\n저장됨: {results_dir / 'speaker_split_comparison.png'}")
    
    # 메트릭 저장
    with open(results_dir / "speaker_split_metrics.txt", 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("화자 단위 분할 검증 결과\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"데이터셋: OpenGlot\n")
        f.write(f"총 화자 수: {len(speaker_files)}\n")
        f.write(f"Train 화자: {', '.join(train_spk)} ({len(train_spk)}명)\n")
        f.write(f"Val 화자: {', '.join(val_spk)} ({len(val_spk)}명)\n")
        f.write(f"Test 화자: {', '.join(test_spk)} ({len(test_spk)}명)\n\n")
        f.write(f"Train frames: {len(train_mic)}\n")
        f.write(f"Val frames: {len(val_mic)}\n")
        f.write(f"Test frames: {len(test_mic)}\n\n")
        f.write("-" * 70 + "\n")
        f.write("결과 비교\n")
        f.write("-" * 70 + "\n")
        f.write(f"프레임 단위 (기존): Corr = 0.9571, MSE = 0.0201\n")
        f.write(f"화자 단위 (검증):   Corr = {test_corr:.4f}, MSE = {test_mse:.4f}\n")
        f.write(f"차이: {0.9571 - test_corr:+.4f}\n\n")
        f.write(f"결론: {conclusion}\n")
    
    print(f"저장됨: {results_dir / 'speaker_split_metrics.txt'}")


if __name__ == "__main__":
    main()
