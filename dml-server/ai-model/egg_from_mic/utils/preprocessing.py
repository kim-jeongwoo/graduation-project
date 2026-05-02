"""
전처리 모듈 - 논문 기준
"""
import numpy as np
from scipy import signal
import librosa


# 논문 기준 설정
TARGET_SR = 16000
WINDOW_LENGTH = 192  # 12ms @ 16kHz
HOP_LENGTH = 32      # 2ms @ 16kHz


def highpass_filter(audio, sr, cutoff_hz=30, order=2):
    """
    Butterworth highpass filter for mic signal
    논문: 30Hz highpass (2nd order)
    """
    nyquist = sr / 2
    normalized_cutoff = cutoff_hz / nyquist
    
    # 안전하게 cutoff 제한
    if normalized_cutoff >= 1.0:
        normalized_cutoff = 0.99
    
    b, a = signal.butter(order, normalized_cutoff, btype='high')
    filtered = signal.filtfilt(b, a, audio)
    return filtered


def bandpass_filter(audio, sr, low_hz=80, high_hz=4000, numtaps=101):
    """
    FIR bandpass filter for EGG signal
    논문: 80Hz ~ 4000Hz (FIR, Hamming window)
    탭 수 줄임 (1024 -> 101) for speed
    """
    nyquist = sr / 2
    low_normalized = low_hz / nyquist
    high_normalized = high_hz / nyquist
    
    # 안전하게 제한
    if high_normalized >= 1.0:
        high_normalized = 0.99
    if low_normalized <= 0:
        low_normalized = 0.01
    
    taps = signal.firwin(numtaps, [low_normalized, high_normalized], 
                         pass_zero=False, window='hamming')
    filtered = signal.lfilter(taps, [1.0], audio)  # lfilter 사용 (더 빠름)
    return filtered


def resample(audio, orig_sr, target_sr=TARGET_SR):
    """
    리샘플링
    """
    if orig_sr == target_sr:
        return audio
    return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)


def normalize(audio):
    """
    Peak normalization to [-1, 1]
    논문 기준
    """
    max_val = np.max(np.abs(audio))
    if max_val > 1e-8:
        return audio / max_val
    return audio


def preprocess_mic(audio, sr):
    """
    마이크 신호 전처리
    1. 리샘플링 (16kHz)
    2. Highpass filter (30Hz)
    3. Peak normalization
    """
    # 리샘플링
    audio = resample(audio, sr, TARGET_SR)
    
    # Highpass filter
    audio = highpass_filter(audio, TARGET_SR, cutoff_hz=30, order=2)
    
    # Normalization
    audio = normalize(audio)
    
    return audio


def preprocess_egg(audio, sr):
    """
    EGG 신호 전처리
    1. 리샘플링 (16kHz)
    2. Bandpass filter (80Hz - 4000Hz)
    3. Peak normalization
    """
    # 리샘플링
    audio = resample(audio, sr, TARGET_SR)
    
    # Bandpass filter
    audio = bandpass_filter(audio, TARGET_SR, low_hz=80, high_hz=4000, numtaps=1024)
    
    # Normalization
    audio = normalize(audio)
    
    return audio


def frame_signal(audio, window_length=WINDOW_LENGTH, hop_length=HOP_LENGTH):
    """
    신호를 프레임으로 분할
    
    Args:
        audio: 입력 신호
        window_length: 윈도우 길이 (samples)
        hop_length: 홉 길이 (samples)
    
    Returns:
        frames: (num_frames, window_length) 형태의 배열
    """
    num_samples = len(audio)
    num_frames = (num_samples - window_length) // hop_length + 1
    
    if num_frames <= 0:
        return np.array([])
    
    frames = np.zeros((num_frames, window_length), dtype=np.float32)
    
    for i in range(num_frames):
        start = i * hop_length
        frames[i] = audio[start:start + window_length]
    
    return frames


def overlap_add(frames, window_length=WINDOW_LENGTH, hop_length=HOP_LENGTH):
    """
    Overlap-and-add 방식으로 프레임 결합
    
    Args:
        frames: (num_frames, window_length) 형태의 배열
        window_length: 윈도우 길이
        hop_length: 홉 길이
    
    Returns:
        reconstructed: 복원된 신호
    """
    num_frames = len(frames)
    if num_frames == 0:
        return np.array([])
    
    output_length = (num_frames - 1) * hop_length + window_length
    output = np.zeros(output_length, dtype=np.float32)
    counts = np.zeros(output_length, dtype=np.float32)
    
    for i, frame in enumerate(frames):
        start = i * hop_length
        output[start:start + window_length] += frame
        counts[start:start + window_length] += 1
    
    # 평균화 (overlap 구간)
    counts = np.maximum(counts, 1)
    output = output / counts
    
    return output
