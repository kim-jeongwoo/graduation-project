"""
추론 스크립트
Overlap-and-Add 방식으로 연속 파형 생성
"""
import sys
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent))

from model import create_model
from utils.preprocessing import preprocess_mic, frame_signal, overlap_add, TARGET_SR


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def inference(model, audio, sr, window_length=192, hop_length=32, device='cpu'):
    """
    논문 방식: overlap-and-add로 연속 파형 생성
    
    Args:
        model: 학습된 모델
        audio: 입력 마이크 신호
        sr: 샘플레이트
        window_length: 윈도우 길이
        hop_length: 홉 길이
        device: 디바이스
    
    Returns:
        output: 예측된 EGG 신호
    """
    model.eval()
    
    # 전처리
    audio = preprocess_mic(audio, sr)
    
    # 프레이밍
    frames = frame_signal(audio, window_length, hop_length)
    
    if len(frames) == 0:
        return np.zeros(len(audio))
    
    # 배치 추론
    frames_tensor = torch.from_numpy(frames).float().to(device)
    
    with torch.no_grad():
        pred_frames = model(frames_tensor)
    
    pred_frames = pred_frames.cpu().numpy()
    
    # Overlap-and-add
    output = overlap_add(pred_frames, window_length, hop_length)
    
    return output


def main():
    parser = argparse.ArgumentParser(description='EGG prediction from microphone signal')
    parser.add_argument('input', type=str, help='Input audio file (wav)')
    parser.add_argument('output', type=str, help='Output EGG file (wav)')
    parser.add_argument('--checkpoint', type=str, default=None, help='Model checkpoint path')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent
    
    # 체크포인트 경로
    if args.checkpoint:
        checkpoint_path = Path(args.checkpoint)
    else:
        checkpoint_path = base_dir / "checkpoints" / "best_model.pt"
    
    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_path}")
        return
    
    # 모델 로드
    device = get_device()
    print(f"Using device: {device}")
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    config = checkpoint['config']
    
    model = create_model(config['model'])
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    print(f"Model loaded from epoch {checkpoint['epoch']}")
    print(f"Val corr: {checkpoint['val_corr']:.4f}")
    
    # 입력 오디오 로드
    audio, sr = sf.read(args.input)
    
    # Mono로 변환
    if len(audio.shape) > 1:
        audio = audio[:, 0]
    
    print(f"Input: {args.input}")
    print(f"  Duration: {len(audio) / sr:.2f}s")
    print(f"  Sample rate: {sr}")
    
    # 추론
    print("Running inference...")
    output = inference(
        model, audio, sr,
        window_length=config['data']['window_length'],
        hop_length=config['data']['hop_length'],
        device=device
    )
    
    # 저장
    sf.write(args.output, output, TARGET_SR)
    print(f"Output saved: {args.output}")
    print(f"  Duration: {len(output) / TARGET_SR:.2f}s")
    print(f"  Sample rate: {TARGET_SR}")


if __name__ == "__main__":
    main()
