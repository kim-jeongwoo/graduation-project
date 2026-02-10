"""
Alignment 유틸리티 모듈
Cross-correlation 기반 mic-egg 신호 정렬
"""
import numpy as np
from scipy import signal as sig


def align_signals(mic, egg, sr, max_lag_ms=50):
    """
    Cross-correlation을 사용하여 mic-egg 신호 정렬 (FFT 기반)
    
    Args:
        mic: 마이크 신호
        egg: EGG/LAR 신호
        sr: 샘플레이트
        max_lag_ms: 최대 lag (ms)
    
    Returns:
        mic_aligned, egg_aligned, best_lag, sign
    """
    max_lag_samples = int(max_lag_ms * sr / 1000)
    
    # Normalize for correlation
    mic_norm = (mic - np.mean(mic)) / (np.std(mic) + 1e-8)
    egg_norm = (egg - np.mean(egg)) / (np.std(egg) + 1e-8)
    
    # FFT 기반 cross-correlation
    corr_pos = sig.correlate(mic_norm, egg_norm, mode='full', method='fft')
    corr_neg = sig.correlate(mic_norm, -egg_norm, mode='full', method='fft')
    
    # 중심 인덱스
    center = len(egg_norm) - 1
    
    # Lag 범위 제한
    start_idx = max(0, center - max_lag_samples)
    end_idx = min(len(corr_pos), center + max_lag_samples + 1)
    
    corr_pos_clipped = corr_pos[start_idx:end_idx]
    corr_neg_clipped = corr_neg[start_idx:end_idx]
    
    # 최적 lag 및 sign 결정
    if corr_pos_clipped.max() >= corr_neg_clipped.max():
        best_idx = np.argmax(corr_pos_clipped)
        best_lag = best_idx - (center - start_idx)
        sign = 1
    else:
        best_idx = np.argmax(corr_neg_clipped)
        best_lag = best_idx - (center - start_idx)
        sign = -1
    
    # 정렬 적용
    egg_aligned = sign * egg
    
    if best_lag > 0:
        mic_aligned = mic[best_lag:]
        egg_aligned = egg_aligned[:-best_lag] if best_lag < len(egg_aligned) else np.array([])
    elif best_lag < 0:
        mic_aligned = mic[:best_lag]
        egg_aligned = egg_aligned[-best_lag:]
    else:
        mic_aligned = mic
    
    # 길이 맞추기
    min_len = min(len(mic_aligned), len(egg_aligned))
    if min_len == 0:
        return mic, sign * egg, 0, sign
    
    return mic_aligned[:min_len], egg_aligned[:min_len], best_lag, sign
