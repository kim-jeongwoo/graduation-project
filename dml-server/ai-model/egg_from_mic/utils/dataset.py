"""
데이터셋 모듈
PyTorch Dataset 클래스
"""
import numpy as np
import torch
from torch.utils.data import Dataset
import soundfile as sf
from pathlib import Path
from typing import List, Tuple, Optional
import random

from .preprocessing import preprocess_mic, preprocess_egg, frame_signal, TARGET_SR
from .alignment import align_signals


class MicEggDataset(Dataset):
    """
    Mic-EGG 프레임 데이터셋
    """
    def __init__(
        self,
        pairs: List[Tuple[Path, Path]],
        window_length: int = 192,
        hop_length: int = 32,
        align: bool = True,
        max_lag_ms: float = 50,
        cache: bool = True
    ):
        """
        Args:
            pairs: (mic_path, egg_path) 튜플 리스트
            window_length: 프레임 길이
            hop_length: 홉 길이
            align: 정렬 적용 여부
            max_lag_ms: 최대 lag (ms)
            cache: 데이터 캐싱 여부
        """
        self.pairs = pairs
        self.window_length = window_length
        self.hop_length = hop_length
        self.align = align
        self.max_lag_ms = max_lag_ms
        self.cache = cache
        
        # 프레임 인덱싱을 위한 메타데이터
        self.frame_indices = []  # (pair_idx, frame_idx)
        self._cached_data = {} if cache else None
        
        self._build_index()
    
    def _build_index(self):
        """프레임 인덱스 구축"""
        for pair_idx, (mic_path, egg_path) in enumerate(self.pairs):
            try:
                mic, sr = sf.read(str(mic_path))
                
                # Mono로 변환
                if len(mic.shape) > 1:
                    mic = mic[:, 0]
                
                # 리샘플링 후 길이 추정
                num_samples = int(len(mic) * TARGET_SR / sr)
                num_frames = (num_samples - self.window_length) // self.hop_length + 1
                
                if num_frames > 0:
                    for frame_idx in range(num_frames):
                        self.frame_indices.append((pair_idx, frame_idx))
            except Exception as e:
                print(f"Error indexing {mic_path}: {e}")
    
    def _load_and_process(self, pair_idx):
        """파일 로드 및 전처리"""
        if self.cache and pair_idx in self._cached_data:
            return self._cached_data[pair_idx]
        
        mic_path, egg_path = self.pairs[pair_idx]
        
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
        if self.align:
            mic, egg, _, _ = align_signals(mic, egg, TARGET_SR, self.max_lag_ms)
        
        # 프레이밍
        mic_frames = frame_signal(mic, self.window_length, self.hop_length)
        egg_frames = frame_signal(egg, self.window_length, self.hop_length)
        
        # 길이 맞추기
        min_frames = min(len(mic_frames), len(egg_frames))
        mic_frames = mic_frames[:min_frames]
        egg_frames = egg_frames[:min_frames]
        
        if self.cache:
            self._cached_data[pair_idx] = (mic_frames, egg_frames)
        
        return mic_frames, egg_frames
    
    def __len__(self):
        return len(self.frame_indices)
    
    def __getitem__(self, idx):
        pair_idx, frame_idx = self.frame_indices[idx]
        mic_frames, egg_frames = self._load_and_process(pair_idx)
        
        if frame_idx >= len(mic_frames):
            frame_idx = len(mic_frames) - 1
        
        mic_frame = torch.from_numpy(mic_frames[frame_idx]).float()
        egg_frame = torch.from_numpy(egg_frames[frame_idx]).float()
        
        return mic_frame, egg_frame


def get_dataset_pairs(dataset_name: str, base_path: Path) -> List[Tuple[Path, Path]]:
    """
    데이터셋별 mic-egg 쌍 가져오기
    """
    pairs = []
    
    if dataset_name == "PTDB-TUG":
        ds_path = base_path / "PTDB-TUG"
        for mic_path in ds_path.rglob("mic_*.wav"):
            lar_path = Path(str(mic_path.parent).replace("/MIC/", "/LAR/")) / mic_path.name.replace("mic_", "lar_")
            if lar_path.exists():
                pairs.append((mic_path, lar_path))
    
    elif dataset_name == "OpenGlot":
        ds_path = base_path / "OpenGlot"
        for mic_path in ds_path.rglob("*_mic.wav"):
            egg_path = mic_path.parent / mic_path.name.replace("_mic.wav", "_EGG.wav")
            if egg_path.exists():
                pairs.append((mic_path, egg_path))
    
    elif dataset_name == "Singing-Voice":
        mic_dir = base_path / "Singing-Voice" / "DATASET" / "MIC"
        egg_dir = base_path / "Singing-Voice" / "DATASET" / "EGG"
        if mic_dir.exists():
            for mic_path in mic_dir.glob("*.wav"):
                egg_path = egg_dir / mic_path.name
                if egg_path.exists():
                    pairs.append((mic_path, egg_path))
    
    elif dataset_name == "PMC":
        mic_dir = base_path / "PMC" / "DATASET" / "MIC"
        egg_dir = base_path / "PMC" / "DATASET" / "EGG"
        if mic_dir.exists():
            for mic_path in mic_dir.glob("*.wav"):
                egg_path = egg_dir / mic_path.name
                if egg_path.exists():
                    pairs.append((mic_path, egg_path))
    
    return sorted(pairs)


def split_by_speaker(pairs: List[Tuple[Path, Path]], train_ratio=0.7, val_ratio=0.2, seed=42):
    """
    Speaker 단위로 데이터 분할 (data leakage 방지)
    """
    random.seed(seed)
    
    # Speaker 추출
    speaker_to_pairs = {}
    for pair in pairs:
        mic_path = pair[0]
        
        # Speaker ID 추출 (파일명에서)
        name = mic_path.stem
        
        # PTDB-TUG: mic_F01_sa1 -> F01
        if name.startswith("mic_"):
            parts = name.split("_")
            if len(parts) >= 2:
                speaker = parts[1]
            else:
                speaker = "unknown"
        # OpenGlot: F01_breathy_high_mic -> F01
        elif "_mic" in name:
            speaker = name.split("_")[0]
        # Singing-Voice, PMC: 249 -> 파일번호 기반 그룹
        else:
            try:
                file_num = int(mic_path.stem)
                speaker = f"group_{file_num // 50}"
            except:
                speaker = "unknown"
        
        if speaker not in speaker_to_pairs:
            speaker_to_pairs[speaker] = []
        speaker_to_pairs[speaker].append(pair)
    
    # Speaker 셔플
    speakers = list(speaker_to_pairs.keys())
    random.shuffle(speakers)
    
    # 분할
    n_speakers = len(speakers)
    n_train = int(n_speakers * train_ratio)
    n_val = int(n_speakers * val_ratio)
    
    train_speakers = speakers[:n_train]
    val_speakers = speakers[n_train:n_train + n_val]
    test_speakers = speakers[n_train + n_val:]
    
    train_pairs = [p for s in train_speakers for p in speaker_to_pairs[s]]
    val_pairs = [p for s in val_speakers for p in speaker_to_pairs[s]]
    test_pairs = [p for s in test_speakers for p in speaker_to_pairs[s]]
    
    return train_pairs, val_pairs, test_pairs
