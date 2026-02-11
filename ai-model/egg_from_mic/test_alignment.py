"""
데이터 정렬(Alignment) 테스트 스크립트
4개 데이터셋에서 정렬 전후 상관관계 비교
"""
import numpy as np
import soundfile as sf
from pathlib import Path
import librosa


def align_signals(mic, egg, sr, max_lag_ms=50):
    """
    Cross-correlation을 사용하여 mic-egg 신호 정렬 (FFT 기반 최적화)
    
    Args:
        mic: 마이크 신호
        egg: EGG/LAR 신호
        sr: 샘플레이트
        max_lag_ms: 최대 lag (ms)
    
    Returns:
        mic_aligned, egg_aligned, best_lag, sign
    """
    from scipy import signal as sig
    
    max_lag_samples = int(max_lag_ms * sr / 1000)
    
    # Normalize for correlation
    mic_norm = (mic - np.mean(mic)) / (np.std(mic) + 1e-8)
    egg_norm = (egg - np.mean(egg)) / (np.std(egg) + 1e-8)
    
    # FFT 기반 cross-correlation (훨씬 빠름)
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


def compute_correlation(a, b):
    """Pearson correlation coefficient"""
    a = a - np.mean(a)
    b = b - np.mean(b)
    denom = np.sqrt(np.sum(a**2)) * np.sqrt(np.sum(b**2))
    if denom < 1e-8:
        return 0.0
    return np.sum(a * b) / denom


def get_ptdb_pairs(base_path, max_pairs=50):
    """PTDB-TUG 데이터셋에서 mic-lar 쌍 가져오기"""
    pairs = []
    mic_files = sorted(list(base_path.rglob("mic_*.wav")))
    
    for mic_path in mic_files:
        lar_path = Path(str(mic_path.parent).replace("/MIC/", "/LAR/")) / mic_path.name.replace("mic_", "lar_")
        if lar_path.exists():
            pairs.append((mic_path, lar_path))
            if len(pairs) >= max_pairs:
                break
    
    return pairs


def get_openglot_pairs(base_path, max_pairs=50):
    """OpenGlot 데이터셋에서 mic-egg 쌍 가져오기"""
    pairs = []
    mic_files = sorted(list(base_path.rglob("*_mic.wav")))
    
    for mic_path in mic_files:
        egg_path = mic_path.parent / mic_path.name.replace("_mic.wav", "_EGG.wav")
        if egg_path.exists():
            pairs.append((mic_path, egg_path))
            if len(pairs) >= max_pairs:
                break
    
    return pairs


def get_singing_voice_pairs(base_path, max_pairs=50):
    """Singing-Voice 데이터셋에서 mic-egg 쌍 가져오기"""
    pairs = []
    mic_dir = base_path / "DATASET" / "MIC"
    egg_dir = base_path / "DATASET" / "EGG"
    
    if not mic_dir.exists():
        return pairs
    
    for mic_path in sorted(mic_dir.glob("*.wav")):
        egg_path = egg_dir / mic_path.name
        if egg_path.exists():
            pairs.append((mic_path, egg_path))
            if len(pairs) >= max_pairs:
                break
    
    return pairs


def get_pmc_pairs(base_path, max_pairs=50):
    """PMC 데이터셋에서 mic-egg 쌍 가져오기"""
    pairs = []
    mic_dir = base_path / "DATASET" / "MIC"
    egg_dir = base_path / "DATASET" / "EGG"
    
    if not mic_dir.exists():
        return pairs
    
    for mic_path in sorted(mic_dir.glob("*.wav")):
        egg_path = egg_dir / mic_path.name
        if egg_path.exists():
            pairs.append((mic_path, egg_path))
            if len(pairs) >= max_pairs:
                break
    
    return pairs


def test_dataset(dataset_name, pairs, target_sr=16000):
    """데이터셋 정렬 테스트"""
    results = []
    
    for i, (mic_path, egg_path) in enumerate(pairs):
        try:
            print(f"  Processing {i+1}/{len(pairs)}: {mic_path.name[:30]}...", end='\r')
            
            # 오디오 로드
            mic, sr_mic = sf.read(str(mic_path))
            egg, sr_egg = sf.read(str(egg_path))
            
            # Stereo -> Mono
            if len(mic.shape) > 1:
                mic = mic[:, 0]
            if len(egg.shape) > 1:
                egg = egg[:, 0]
            
            # 리샘플링 (필요시)
            if sr_mic != target_sr:
                mic = librosa.resample(mic, orig_sr=sr_mic, target_sr=target_sr)
            if sr_egg != target_sr:
                egg = librosa.resample(egg, orig_sr=sr_egg, target_sr=target_sr)
            
            # 길이 맞추기
            min_len = min(len(mic), len(egg))
            mic = mic[:min_len]
            egg = egg[:min_len]
            
            # 정렬 전 상관관계
            corr_before = compute_correlation(mic, egg)
            
            # 정렬
            mic_aligned, egg_aligned, lag, sign = align_signals(mic, egg, target_sr)
            
            # 정렬 후 상관관계
            corr_after = compute_correlation(mic_aligned, egg_aligned)
            
            lag_ms = lag * 1000 / target_sr
            
            results.append({
                'file': mic_path.name,
                'corr_before': corr_before,
                'corr_after': corr_after,
                'lag_ms': lag_ms,
                'sign': sign
            })
        except Exception as e:
            print(f"  Error processing {mic_path.name}: {e}")
    
    return results


def main():
    base_path = Path("/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw")
    
    datasets = {
        'PTDB-TUG': get_ptdb_pairs(base_path / "PTDB-TUG", max_pairs=20),
        'OpenGlot': get_openglot_pairs(base_path / "OpenGlot", max_pairs=20),
        'Singing-Voice': get_singing_voice_pairs(base_path / "Singing-Voice", max_pairs=20),
        'PMC': get_pmc_pairs(base_path / "PMC", max_pairs=20),
    }
    
    print("=" * 70)
    print("데이터 정렬(Alignment) 테스트 결과")
    print("=" * 70)
    
    summary = []
    
    for name, pairs in datasets.items():
        print(f"\n[{name}] - {len(pairs)} pairs")
        
        if len(pairs) == 0:
            print("  No valid pairs found")
            continue
        
        results = test_dataset(name, pairs)
        
        if len(results) == 0:
            print("  No results")
            continue
        
        avg_before = np.mean([r['corr_before'] for r in results])
        avg_after = np.mean([r['corr_after'] for r in results])
        avg_lag = np.mean([r['lag_ms'] for r in results])
        
        print(f"  정렬 전 평균 corr: {avg_before:.4f}")
        print(f"  정렬 후 평균 corr: {avg_after:.4f}")
        print(f"  평균 lag: {avg_lag:.2f} ms")
        print(f"  개선량: {avg_after - avg_before:.4f}")
        
        summary.append({
            'dataset': name,
            'pairs': len(pairs),
            'corr_before': avg_before,
            'corr_after': avg_after,
            'avg_lag_ms': avg_lag
        })
    
    # 최종 요약 테이블
    print("\n" + "=" * 70)
    print("요약 테이블")
    print("=" * 70)
    print(f"{'데이터셋':<15} {'Pairs':<8} {'정렬 전 corr':<15} {'정렬 후 corr':<15} {'평균 lag(ms)'}")
    print("-" * 70)
    
    for s in summary:
        print(f"{s['dataset']:<15} {s['pairs']:<8} {s['corr_before']:<15.4f} {s['corr_after']:<15.4f} {s['avg_lag_ms']:.2f}")
    
    print("-" * 70)
    
    # 진행 여부 판단
    total_after = np.mean([s['corr_after'] for s in summary]) if summary else 0
    print(f"\n전체 평균 정렬 후 corr: {total_after:.4f}")
    
    if total_after >= 0.5:
        print("✅ 정렬 후 corr >= 0.5 - 모델 학습 진행 가능")
    elif total_after >= 0.3:
        print("⚠️ 정렬 후 corr 0.3~0.5 - 주의하며 진행")
    else:
        print("❌ 정렬 후 corr < 0.3 - 데이터 품질 문제 확인 필요")


if __name__ == "__main__":
    main()
