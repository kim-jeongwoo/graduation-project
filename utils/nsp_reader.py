"""
NSP/EGG file reader for SVD dataset.
Format: IFF (FORM/DS16) with HEDR and SDA_ chunks.
"""
import struct
import numpy as np


def read_nsp(filepath: str) -> tuple[np.ndarray, int]:
    """
    Read an NSP or EGG file (IFF FORM/DS16 format).
    
    Returns:
        signal: numpy array of float32, normalized to [-1, 1]
        sample_rate: int (typically 50000)
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Find HEDR chunk for sample rate
    hedr_pos = data.find(b'HEDR')
    sample_rate = 50000  # default
    if hedr_pos >= 0:
        hedr_size = struct.unpack('<I', data[hedr_pos + 4:hedr_pos + 8])[0]
        hedr_data = data[hedr_pos + 8:hedr_pos + 8 + hedr_size]
        if len(hedr_data) >= 24:
            sample_rate = struct.unpack('<I', hedr_data[20:24])[0]
    
    # Find SDA_ chunk for audio data
    sda_pos = data.find(b'SDA_')
    if sda_pos < 0:
        raise ValueError(f"No SDA_ chunk found in {filepath}")
    
    sda_size = struct.unpack('<I', data[sda_pos + 4:sda_pos + 8])[0]
    raw = np.frombuffer(data[sda_pos + 8:sda_pos + 8 + sda_size], dtype=np.int16)
    
    # Normalize to float32 [-1, 1]
    signal = raw.astype(np.float32) / 32768.0
    
    return signal, sample_rate


def find_paired_files(base_dir: str) -> list[tuple[str, str, str]]:
    """
    Find all (nsp_path, egg_path, speaker_id) pairs in SVD_healthy.
    Searches both vowels/ and sentences/ subdirectories.
    """
    import os
    
    pairs = []
    speakers = sorted(os.listdir(base_dir))
    
    for speaker_id in speakers:
        speaker_dir = os.path.join(base_dir, speaker_id)
        if not os.path.isdir(speaker_dir):
            continue
        
        for subdir_name in ['vowels', 'sentences']:
            subdir = os.path.join(speaker_dir, subdir_name)
            if not os.path.exists(subdir):
                continue
            
            files = os.listdir(subdir)
            nsp_files = {f for f in files if f.endswith('.nsp')}
            egg_files = {f for f in files if f.endswith('.egg')}
            
            for nsp_file in sorted(nsp_files):
                # Match: X.nsp <-> X-egg.egg
                base_name = nsp_file[:-4]  # remove .nsp
                egg_name = f"{base_name}-egg.egg"
                
                if egg_name in egg_files:
                    nsp_path = os.path.join(subdir, nsp_file)
                    egg_path = os.path.join(subdir, egg_name)
                    pairs.append((nsp_path, egg_path, speaker_id))
    
    return pairs
