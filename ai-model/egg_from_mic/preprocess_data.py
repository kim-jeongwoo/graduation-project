"""
데이터 전처리 스크립트
모든 데이터를 미리 처리하여 numpy 파일로 저장
"""
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from tqdm import tqdm
import pickle

sys.path.insert(0, str(Path(__file__).parent))

from utils.preprocessing import preprocess_mic, preprocess_egg, frame_signal, TARGET_SR
from utils.alignment import align_signals
from utils.dataset import get_dataset_pairs


def process_and_save(pairs, output_path, window_length=192, hop_length=32, max_lag_ms=50):
    """
    파일들을 처리하고 프레임으로 저장
    """
    all_mic_frames = []
    all_egg_frames = []
    metadata = []
    
    for i, (mic_path, egg_path) in enumerate(tqdm(pairs, desc="Processing")):
        try:
            # 로드
            mic, sr_mic = sf.read(str(mic_path))
            egg, sr_egg = sf.read(str(egg_path))
            
            # Mono로 변환
            if len(mic.shape) > 1:
                mic = mic[:, 0]
            if len(egg.shape) > 1:
                egg = egg[:, 0]
            
            # 전처리
            mic = preprocess_mic(mic, sr_mic)
            egg = preprocess_egg(egg, sr_egg)
            
            # 길이 맞추기
            min_len = min(len(mic), len(egg))
            mic = mic[:min_len]
            egg = egg[:min_len]
            
            # 정렬
            mic, egg, lag, sign = align_signals(mic, egg, TARGET_SR, max_lag_ms)
            
            # 프레이밍
            mic_frames = frame_signal(mic, window_length, hop_length)
            egg_frames = frame_signal(egg, window_length, hop_length)
            
            # 길이 맞추기
            min_frames = min(len(mic_frames), len(egg_frames))
            if min_frames == 0:
                continue
            
            mic_frames = mic_frames[:min_frames]
            egg_frames = egg_frames[:min_frames]
            
            all_mic_frames.append(mic_frames)
            all_egg_frames.append(egg_frames)
            
            metadata.append({
                'mic_path': str(mic_path),
                'egg_path': str(egg_path),
                'num_frames': min_frames,
                'lag': lag,
                'sign': sign
            })
            
        except Exception as e:
            print(f"Error processing {mic_path}: {e}")
    
    # Concatenate
    all_mic_frames = np.concatenate(all_mic_frames, axis=0).astype(np.float32)
    all_egg_frames = np.concatenate(all_egg_frames, axis=0).astype(np.float32)
    
    # 저장
    output_path.mkdir(parents=True, exist_ok=True)
    np.save(output_path / "mic_frames.npy", all_mic_frames)
    np.save(output_path / "egg_frames.npy", all_egg_frames)
    
    with open(output_path / "metadata.pkl", 'wb') as f:
        pickle.dump(metadata, f)
    
    print(f"Saved {len(all_mic_frames)} frames to {output_path}")
    return len(all_mic_frames)


def main():
    base_dir = Path(__file__).parent
    data_base_path = base_dir.parent / "data" / "raw"
    output_base = base_dir / "processed_data"
    
    datasets = ["OpenGlot", "Singing-Voice", "PMC"]
    
    print("=" * 60)
    print("데이터 전처리")
    print("=" * 60)
    
    total_frames = 0
    
    for dataset_name in datasets:
        print(f"\n[{dataset_name}]")
        pairs = get_dataset_pairs(dataset_name, data_base_path)
        print(f"  Pairs: {len(pairs)}")
        
        if len(pairs) == 0:
            continue
        
        output_path = output_base / dataset_name
        n_frames = process_and_save(pairs, output_path)
        total_frames += n_frames
    
    print(f"\n총 프레임: {total_frames}")
    print("전처리 완료!")


if __name__ == "__main__":
    main()
