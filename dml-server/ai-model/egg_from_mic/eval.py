"""
평가 스크립트
"""
import sys
import torch
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from model import WaveNetEGG, create_model
from utils.dataset import MicEggDataset, get_dataset_pairs, split_by_speaker
from utils.metrics import compute_correlation, compute_mse, compute_r2, compute_rmse
from torch.utils.data import DataLoader


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def main():
    base_dir = Path(__file__).parent
    checkpoint_path = base_dir / "checkpoints" / "best_model.pt"
    results_dir = base_dir / "results"
    
    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_path}")
        return
    
    # 체크포인트 로드
    device = get_device()
    print(f"Using device: {device}")
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    config = checkpoint['config']
    
    print(f"Loaded model from epoch {checkpoint['epoch']}")
    print(f"Val corr: {checkpoint['val_corr']:.4f}")
    
    # 모델 생성 및 가중치 로드
    model = create_model(config['model'])
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    # 테스트 데이터 로드
    data_base_path = base_dir.parent / "data" / "raw"
    
    all_pairs = []
    for dataset_name in config['data']['datasets']:
        pairs = get_dataset_pairs(dataset_name, data_base_path)
        all_pairs.extend(pairs)
    
    _, _, test_pairs = split_by_speaker(
        all_pairs,
        train_ratio=config['data']['train_ratio'],
        val_ratio=config['data']['val_ratio']
    )
    
    print(f"Test pairs: {len(test_pairs)}")
    
    # Dataset
    test_dataset = MicEggDataset(
        test_pairs,
        window_length=config['data']['window_length'],
        hop_length=config['data']['hop_length'],
        align=config['data']['align'],
        max_lag_ms=config['data']['max_lag_ms'],
        cache=True
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=0
    )
    
    print(f"Test frames: {len(test_dataset)}")
    
    # 평가
    all_preds = []
    all_gts = []
    
    with torch.no_grad():
        for mic, egg in test_loader:
            mic = mic.to(device)
            pred = model(mic)
            
            all_preds.append(pred.cpu().numpy())
            all_gts.append(egg.numpy())
    
    all_preds = np.concatenate(all_preds, axis=0).flatten()
    all_gts = np.concatenate(all_gts, axis=0).flatten()
    
    # 메트릭 계산
    corr = compute_correlation(all_preds, all_gts)
    mse = compute_mse(all_preds, all_gts)
    rmse = compute_rmse(all_preds, all_gts)
    r2 = compute_r2(all_preds, all_gts)
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Correlation: {corr:.4f}")
    print(f"MSE: {mse:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²: {r2:.4f}")
    
    # 최종 비교 플롯
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    
    n_samples = min(2000, len(all_preds))
    
    axes[0].plot(all_gts[:n_samples], 'b-', linewidth=0.5, label='Ground Truth')
    axes[0].set_title('Ground Truth EGG')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(all_preds[:n_samples], 'r-', linewidth=0.5, label='Prediction')
    axes[1].set_title('Predicted EGG')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(all_gts[:n_samples], 'b-', linewidth=0.5, alpha=0.7, label='Ground Truth')
    axes[2].plot(all_preds[:n_samples], 'r-', linewidth=0.5, alpha=0.7, label='Prediction')
    axes[2].set_title('Overlay')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    
    plt.suptitle(f'Test Results | Corr: {corr:.4f} | MSE: {mse:.4f} | R²: {r2:.4f}', fontsize=14)
    plt.tight_layout()
    plt.savefig(results_dir / "final_comparison.png", dpi=150)
    plt.close()
    
    print(f"\nFinal comparison saved to: {results_dir / 'final_comparison.png'}")


if __name__ == "__main__":
    main()
