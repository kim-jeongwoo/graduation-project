"""
학습 스크립트
논문 기준 구현
"""
import os
import sys
import yaml
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import ExponentialLR
from pathlib import Path
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from model import WaveNetEGG, create_model
from utils.dataset import MicEggDataset, get_dataset_pairs, split_by_speaker
from utils.metrics import compute_correlation, compute_mse, compute_r2


def get_device(config_device: str = "auto"):
    """Device 설정"""
    if config_device == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        elif torch.cuda.is_available():
            return torch.device("cuda")
        else:
            return torch.device("cpu")
    return torch.device(config_device)


def save_comparison_plot(pred, gt, filepath, corr, mse, epoch):
    """예측 vs 실제 비교 플롯 저장"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))
    
    # 샘플 수 제한
    n_samples = min(1000, len(pred))
    pred = pred[:n_samples]
    gt = gt[:n_samples]
    
    # 상단: GT
    axes[0].plot(gt, 'b-', linewidth=0.5, label='Ground Truth')
    axes[0].set_title('Ground Truth EGG')
    axes[0].set_ylabel('Amplitude')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 중간: Prediction
    axes[1].plot(pred, 'r-', linewidth=0.5, label='Prediction')
    axes[1].set_title('Predicted EGG')
    axes[1].set_ylabel('Amplitude')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # 하단: 차이
    residual = gt - pred
    axes[2].plot(residual, 'g-', linewidth=0.5, label='Residual')
    axes[2].set_title(f'Residual (GT - Pred)')
    axes[2].set_xlabel('Sample')
    axes[2].set_ylabel('Amplitude')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.suptitle(f'Epoch {epoch} | Corr: {corr:.4f} | MSE: {mse:.4f}', fontsize=14)
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()


def save_training_history(history, filepath):
    """학습 이력 플롯 저장"""
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    # Loss
    axes[0].plot(epochs, history['train_loss'], 'b-', label='Train Loss')
    axes[0].plot(epochs, history['val_loss'], 'r-', label='Val Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training and Validation Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Correlation
    axes[1].plot(epochs, history['val_corr'], 'g-', label='Val Correlation')
    axes[1].axhline(y=0.7, color='r', linestyle='--', label='Target (0.7)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Correlation')
    axes[1].set_title('Validation Correlation')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()


def train_epoch(model, dataloader, criterion, optimizer, device):
    """한 에폭 학습"""
    model.train()
    total_loss = 0
    num_batches = 0
    
    for batch_idx, (mic, egg) in enumerate(dataloader):
        mic = mic.to(device)
        egg = egg.to(device)
        
        optimizer.zero_grad()
        pred = model(mic)
        loss = criterion(pred, egg)
        
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        total_loss += loss.item()
        num_batches += 1
        
        if batch_idx % 100 == 0:
            print(f"  Batch {batch_idx}/{len(dataloader)}, Loss: {loss.item():.4f}")
    
    return total_loss / max(num_batches, 1)


def evaluate(model, dataloader, criterion, device):
    """평가"""
    model.eval()
    total_loss = 0
    all_preds = []
    all_gts = []
    num_batches = 0
    
    with torch.no_grad():
        for mic, egg in dataloader:
            mic = mic.to(device)
            egg = egg.to(device)
            
            pred = model(mic)
            loss = criterion(pred, egg)
            
            total_loss += loss.item()
            num_batches += 1
            
            all_preds.append(pred.cpu().numpy())
            all_gts.append(egg.cpu().numpy())
    
    avg_loss = total_loss / max(num_batches, 1)
    
    # 전체 결과 concatenate
    all_preds = np.concatenate(all_preds, axis=0).flatten()
    all_gts = np.concatenate(all_gts, axis=0).flatten()
    
    # 메트릭 계산
    corr = compute_correlation(all_preds, all_gts)
    mse = compute_mse(all_preds, all_gts)
    r2 = compute_r2(all_preds, all_gts)
    
    return avg_loss, corr, mse, r2, all_preds, all_gts


def main():
    # 설정 로드
    config_path = Path(__file__).parent / "configs" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("=" * 60)
    print("WaveNet EGG 예측 모델 학습")
    print("=" * 60)
    
    # Device 설정
    device = get_device(config.get('device', 'auto'))
    print(f"Using device: {device}")
    
    # 디렉토리 생성
    base_dir = Path(__file__).parent
    checkpoint_dir = base_dir / config['output']['checkpoint_dir']
    results_dir = base_dir / config['output']['results_dir']
    checkpoint_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    
    # 데이터 로드
    print("\n[1/4] Loading datasets...")
    data_base_path = base_dir.parent / "data" / "raw"
    
    all_pairs = []
    for dataset_name in config['data']['datasets']:
        pairs = get_dataset_pairs(dataset_name, data_base_path)
        print(f"  {dataset_name}: {len(pairs)} pairs")
        all_pairs.extend(pairs)
    
    print(f"  Total: {len(all_pairs)} pairs")
    
    # 데이터 분할
    train_pairs, val_pairs, test_pairs = split_by_speaker(
        all_pairs,
        train_ratio=config['data']['train_ratio'],
        val_ratio=config['data']['val_ratio']
    )
    
    print(f"  Train: {len(train_pairs)}, Val: {len(val_pairs)}, Test: {len(test_pairs)}")
    
    # Dataset 생성
    print("\n[2/4] Creating datasets...")
    train_dataset = MicEggDataset(
        train_pairs,
        window_length=config['data']['window_length'],
        hop_length=config['data']['hop_length'],
        align=config['data']['align'],
        max_lag_ms=config['data']['max_lag_ms'],
        cache=True
    )
    
    val_dataset = MicEggDataset(
        val_pairs,
        window_length=config['data']['window_length'],
        hop_length=config['data']['hop_length'],
        align=config['data']['align'],
        max_lag_ms=config['data']['max_lag_ms'],
        cache=True
    )
    
    print(f"  Train frames: {len(train_dataset)}")
    print(f"  Val frames: {len(val_dataset)}")
    
    # DataLoader 생성
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
        num_workers=0,  # macOS에서 안정적
        pin_memory=False
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=0
    )
    
    # 모델 생성
    print("\n[3/4] Creating model...")
    model = create_model(config['model'])
    model = model.to(device)
    
    num_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {num_params:,}")
    print(f"  Receptive field: {model.get_receptive_field()} samples")
    
    # Loss, Optimizer, Scheduler
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config['training']['learning_rate'],
        weight_decay=config['training'].get('weight_decay', 0)
    )
    scheduler = ExponentialLR(optimizer, gamma=config['training']['lr_gamma'])
    
    # 학습
    print("\n[4/4] Training...")
    history = {
        'train_loss': [],
        'val_loss': [],
        'val_corr': [],
        'val_mse': [],
        'val_r2': []
    }
    
    best_corr = -1
    
    for epoch in range(1, config['training']['epochs'] + 1):
        print(f"\nEpoch {epoch}/{config['training']['epochs']}")
        print(f"  LR: {scheduler.get_last_lr()[0]:.6f}")
        
        # Train
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_loss, val_corr, val_mse, val_r2, preds, gts = evaluate(
            model, val_loader, criterion, device
        )
        
        # 기록
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_corr'].append(val_corr)
        history['val_mse'].append(val_mse)
        history['val_r2'].append(val_r2)
        
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_loss:.4f}, Corr: {val_corr:.4f}, MSE: {val_mse:.4f}, R²: {val_r2:.4f}")
        
        # 이미지 저장
        if config['output'].get('save_every_epoch', True):
            plot_path = results_dir / f"epoch_{epoch:02d}_corr_{val_corr:.3f}.png"
            save_comparison_plot(preds, gts, plot_path, val_corr, val_mse, epoch)
        
        # Best 모델 저장
        if val_corr > best_corr:
            best_corr = val_corr
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_corr': val_corr,
                'val_mse': val_mse,
                'config': config
            }, checkpoint_dir / "best_model.pt")
            print(f"  ✅ Best model saved! (corr: {val_corr:.4f})")
        
        # Scheduler step
        scheduler.step()
    
    # 최종 결과 저장
    print("\n" + "=" * 60)
    print("Training completed!")
    print(f"Best correlation: {best_corr:.4f}")
    
    # 학습 이력 저장
    save_training_history(history, results_dir / "training_history.png")
    
    # 메트릭 CSV 저장
    import csv
    with open(results_dir / "metrics_summary.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['epoch', 'train_loss', 'val_loss', 'val_corr', 'val_mse', 'val_r2'])
        for i in range(len(history['train_loss'])):
            writer.writerow([
                i + 1,
                history['train_loss'][i],
                history['val_loss'][i],
                history['val_corr'][i],
                history['val_mse'][i],
                history['val_r2'][i]
            ])
    
    print(f"\nResults saved to: {results_dir}")
    print(f"Checkpoint saved to: {checkpoint_dir}")
    
    # 목표 달성 여부
    if best_corr >= 0.7:
        print("\n🎉 목표 달성! (corr >= 0.7)")
    else:
        print(f"\n⚠️ 목표 미달성 (corr: {best_corr:.4f} < 0.7)")


if __name__ == "__main__":
    main()
