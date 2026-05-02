"""
Dataset and data loading for SVD EGG prediction.
Speaker-independent train/val/test split.
"""
import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Optional
from tqdm import tqdm

from utils.nsp_reader import read_nsp, find_paired_files


def speaker_split(speaker_ids: list[str],
                  train_ratio: float = 0.8,
                  val_ratio: float = 0.1,
                  test_ratio: float = 0.1,
                  seed: int = 42) -> tuple[set, set, set]:
    """Split speakers into train/val/test sets."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6
    
    rng = np.random.RandomState(seed)
    unique = sorted(set(speaker_ids))
    rng.shuffle(unique)
    
    n = len(unique)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    
    train_speakers = set(unique[:n_train])
    val_speakers = set(unique[n_train:n_train + n_val])
    test_speakers = set(unique[n_train + n_val:])
    
    return train_speakers, val_speakers, test_speakers


class SVDEggDataset(Dataset):
    """
    Dataset that creates windowed (speech -> EGG) sample pairs.
    
    Each sample: 
        x = speech window [window_length]
        y = EGG window [window_length]  (aligned, same position)
    """
    
    def __init__(self,
                 pairs: list[tuple[str, str, str]],
                 window_length: int = 192,
                 hop_length: int = 32,
                 target_sr: int = 16000,
                 source_sr: int = 50000,
                 normalize_per_file: bool = True,
                 cache_dir: Optional[str] = None,
                 split_name: str = ""):
        """
        Args:
            pairs: list of (nsp_path, egg_path, speaker_id)
            window_length: samples per window
            hop_length: hop between windows
            target_sr: target sample rate (downsample from source_sr)
            source_sr: original sample rate of NSP/EGG files
            normalize_per_file: z-normalize each file independently
            cache_dir: if set, cache resampled data to disk
            split_name: name for progress bar
        """
        self.window_length = window_length
        self.hop_length = hop_length
        self.target_sr = target_sr
        self.source_sr = source_sr
        self.normalize_per_file = normalize_per_file
        
        # Build all windows
        self.windows = []  # (file_idx, start_sample)
        self.speech_data = []
        self.egg_data = []
        
        self._load_data(pairs, cache_dir, split_name)
    
    def _resample(self, signal: np.ndarray) -> np.ndarray:
        """Resample signal from source_sr to target_sr."""
        if self.source_sr == self.target_sr:
            return signal
        import librosa
        return librosa.resample(signal, orig_sr=self.source_sr, target_sr=self.target_sr)
    
    def _load_data(self, pairs, cache_dir, split_name):
        """Load all files and create window indices."""
        skipped = 0
        
        for nsp_path, egg_path, speaker_id in tqdm(pairs, desc=f"Loading {split_name}"):
            try:
                speech, sr1 = read_nsp(nsp_path)
                egg, sr2 = read_nsp(egg_path)
            except Exception as e:
                skipped += 1
                continue
            
            # Ensure same length
            min_len = min(len(speech), len(egg))
            speech = speech[:min_len]
            egg = egg[:min_len]
            
            # Resample
            speech = self._resample(speech)
            egg = self._resample(egg)
            
            # Ensure same length after resample
            min_len = min(len(speech), len(egg))
            speech = speech[:min_len]
            egg = egg[:min_len]
            
            if min_len < self.window_length:
                skipped += 1
                continue
            
            # Per-file normalization (z-score)
            if self.normalize_per_file:
                s_std = speech.std()
                e_std = egg.std()
                if s_std > 1e-8:
                    speech = (speech - speech.mean()) / s_std
                if e_std > 1e-8:
                    egg = (egg - egg.mean()) / e_std
            
            file_idx = len(self.speech_data)
            self.speech_data.append(speech)
            self.egg_data.append(egg)
            
            # Create windows
            n_windows = (min_len - self.window_length) // self.hop_length + 1
            for w in range(n_windows):
                start = w * self.hop_length
                self.windows.append((file_idx, start))
        
        if skipped > 0:
            print(f"  Skipped {skipped} files (too short or read error)")
        print(f"  Loaded {len(self.speech_data)} files, {len(self.windows)} windows")
    
    def __len__(self):
        return len(self.windows)
    
    def __getitem__(self, idx):
        file_idx, start = self.windows[idx]
        end = start + self.window_length
        
        x = self.speech_data[file_idx][start:end]
        y = self.egg_data[file_idx][start:end]
        
        # [window_length] -> [1, window_length] for Conv1d
        x = torch.from_numpy(x).float().unsqueeze(0)
        y = torch.from_numpy(y).float().unsqueeze(0)
        
        return x, y


def create_dataloaders(svd_path: str,
                       batch_size: int = 256,
                       window_length: int = 192,
                       hop_length: int = 32,
                       target_sr: int = 16000,
                       num_workers: int = 4,
                       seed: int = 42) -> tuple[DataLoader, DataLoader, DataLoader, dict]:
    """
    Create train/val/test DataLoaders with speaker-independent split.
    
    Returns:
        train_loader, val_loader, test_loader, split_info
    """
    print("Finding paired files...")
    pairs = find_paired_files(svd_path)
    print(f"Found {len(pairs)} paired files")
    
    # Get unique speakers
    all_speakers = [p[2] for p in pairs]
    unique_speakers = sorted(set(all_speakers))
    print(f"Unique speakers: {len(unique_speakers)}")
    
    # Speaker split
    train_sp, val_sp, test_sp = speaker_split(unique_speakers, seed=seed)
    print(f"Split: Train={len(train_sp)}, Val={len(val_sp)}, Test={len(test_sp)}")
    
    # Partition pairs
    train_pairs = [(n, e, s) for n, e, s in pairs if s in train_sp]
    val_pairs = [(n, e, s) for n, e, s in pairs if s in val_sp]
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]
    
    print(f"Files: Train={len(train_pairs)}, Val={len(val_pairs)}, Test={len(test_pairs)}")
    
    # Create datasets
    train_ds = SVDEggDataset(train_pairs, window_length, hop_length, target_sr,
                             split_name="train")
    val_ds = SVDEggDataset(val_pairs, window_length, hop_length, target_sr,
                           split_name="val")
    test_ds = SVDEggDataset(test_pairs, window_length, hop_length, target_sr,
                            split_name="test")
    
    # Create loaders
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              num_workers=num_workers, pin_memory=True,
                              drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=True)
    
    split_info = {
        'train_speakers': len(train_sp),
        'val_speakers': len(val_sp),
        'test_speakers': len(test_sp),
        'train_files': len(train_pairs),
        'val_files': len(val_pairs),
        'test_files': len(test_pairs),
        'train_windows': len(train_ds),
        'val_windows': len(val_ds),
        'test_windows': len(test_ds),
    }
    
    return train_loader, val_loader, test_loader, split_info
