#!/usr/bin/env python3
"""
PTDB-TUG 유성음 구간 분석 및 검증

목표:
1. .f0 Reference pitch 파일로 유성음 구간만 추출
2. 유성음 구간의 MIC-LAR 상관관계 확인
3. corr ≥ 0.3이면 PTDB-TUG로 화자 독립 모델 학습 진행

.f0 파일 형식 (RAPT):
- 4열: pitch, voicing_prob, rms, peak_corr
- pitch > 0: 유성음 (voiced)
- pitch = 0: 무성음 (unvoiced)
- hop size: 10ms @ 48kHz (= 480 samples)
"""

import os
import numpy as np
import librosa
from scipy import signal as sig
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 설정
# ============================================================
BASE_PATH = "/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw/PTDB-TUG"
SR = 48000  # PTDB-TUG 원본 샘플레이트
F0_HOP_MS = 10  # .f0 파일의 hop size (10ms)
F0_HOP_SAMPLES = int(F0_HOP_MS * SR / 1000)  # 480 samples

SAMPLES_PER_SPEAKER = 20  # 화자당 테스트 파일 수


def load_f0_file(f0_path):
    """
    RAPT .f0 파일 로드
    
    형식: pitch, voicing_prob, rms, peak_corr
    - pitch > 0: voiced
    - pitch = 0: unvoiced
    """
    try:
        data = np.loadtxt(f0_path)
        return data
    except Exception as e:
        print(f"Error loading {f0_path}: {e}")
        return None


def find_best_lag(mic, lar, max_lag_samples=1000):
    """
    Cross-correlation으로 최적 시간 지연 찾기
    
    Args:
        mic: 마이크 신호
        lar: 라링고그래프 신호
        max_lag_samples: 최대 검색 범위 (샘플)
    
    Returns:
        best_lag: 최적 지연 (샘플)
    """
    # 신호 정규화
    mic_norm = (mic - np.mean(mic)) / (np.std(mic) + 1e-8)
    lar_norm = (lar - np.mean(lar)) / (np.std(lar) + 1e-8)
    
    # Cross-correlation
    correlation = np.correlate(mic_norm, lar_norm, mode='full')
    
    # 중심 기준 lag 범위 제한
    center = len(correlation) // 2
    search_start = max(0, center - max_lag_samples)
    search_end = min(len(correlation), center + max_lag_samples)
    
    # 최대 correlation 위치 찾기
    best_idx = search_start + np.argmax(np.abs(correlation[search_start:search_end]))
    best_lag = best_idx - center
    
    return best_lag


def get_voiced_segments(mic, lar, f0_data):
    """
    .f0 파일 기반으로 유성음 구간만 추출
    
    Args:
        mic: 마이크 신호 (48kHz)
        lar: 라링고그래프 신호 (48kHz)
        f0_data: .f0 파일 데이터 (N, 4)
    
    Returns:
        mic_voiced, lar_voiced: 유성음 구간만 연결한 신호
    """
    pitch = f0_data[:, 0]
    
    mic_segments = []
    lar_segments = []
    
    for i, p in enumerate(pitch):
        if p > 0:  # voiced frame
            start = i * F0_HOP_SAMPLES
            end = start + F0_HOP_SAMPLES
            
            if end <= len(mic) and end <= len(lar):
                mic_segments.append(mic[start:end])
                lar_segments.append(lar[start:end])
    
    if len(mic_segments) == 0:
        return np.array([]), np.array([])
    
    mic_voiced = np.concatenate(mic_segments)
    lar_voiced = np.concatenate(lar_segments)
    
    return mic_voiced, lar_voiced


def bandpass_filter(signal, lowcut, highcut, sr, order=4):
    """Butterworth bandpass filter"""
    nyq = sr / 2
    low = lowcut / nyq
    high = highcut / nyq
    b, a = sig.butter(order, [low, high], btype='band')
    return sig.filtfilt(b, a, signal)


def highpass_filter(signal, cutoff, sr, order=4):
    """Butterworth highpass filter"""
    nyq = sr / 2
    normalized_cutoff = cutoff / nyq
    b, a = sig.butter(order, normalized_cutoff, btype='high')
    return sig.filtfilt(b, a, signal)


def compute_correlation(mic_path, lar_path, f0_path, apply_filter=True, fix_polarity=True, align=True):
    """
    단일 파일 쌍의 상관관계 계산 (전체 vs 유성음 구간)
    
    Args:
        fix_polarity: True이면 |corr|로 절대값 사용 (극성 반전 보정)
        align: True이면 cross-correlation으로 시간 정렬
    
    Returns:
        dict: full_corr, voiced_corr, voiced_ratio, voiced_frames, total_frames
    """
    # 로드
    mic, _ = librosa.load(mic_path, sr=SR)
    lar, _ = librosa.load(lar_path, sr=SR)
    f0_data = load_f0_file(f0_path)
    
    if f0_data is None:
        return None
    
    # 필터링 (선택적)
    if apply_filter:
        mic = highpass_filter(mic, 30, SR)
        lar = bandpass_filter(lar, 80, 4000, SR)
    
    # 시간 정렬 (선택적)
    if align:
        lag = find_best_lag(mic, lar, max_lag_samples=int(0.05 * SR))  # 최대 50ms
        if lag > 0:
            mic = mic[lag:]
            lar = lar[:len(mic)]
        elif lag < 0:
            lar = lar[-lag:]
            mic = mic[:len(lar)]
    
    # 길이 맞춤
    min_len = min(len(mic), len(lar))
    mic = mic[:min_len]
    lar = lar[:min_len]
    
    # 전체 구간 상관관계
    full_corr_raw = np.corrcoef(mic, lar)[0, 1]
    full_corr = abs(full_corr_raw) if fix_polarity else full_corr_raw
    
    # 유성음 구간 추출
    mic_voiced, lar_voiced = get_voiced_segments(mic, lar, f0_data)
    
    # 유성음 정보
    total_frames = len(f0_data)
    voiced_frames = np.sum(f0_data[:, 0] > 0)
    voiced_ratio = voiced_frames / total_frames if total_frames > 0 else 0
    
    if len(mic_voiced) == 0:
        return {
            'full_corr': full_corr,
            'full_corr_raw': full_corr_raw,
            'voiced_corr': np.nan,
            'voiced_corr_raw': np.nan,
            'voiced_ratio': voiced_ratio,
            'voiced_frames': voiced_frames,
            'total_frames': total_frames
        }
    
    # 유성음 구간 상관관계
    voiced_corr_raw = np.corrcoef(mic_voiced, lar_voiced)[0, 1]
    voiced_corr = abs(voiced_corr_raw) if fix_polarity else voiced_corr_raw
    
    return {
        'full_corr': full_corr,
        'full_corr_raw': full_corr_raw,
        'voiced_corr': voiced_corr,
        'voiced_corr_raw': voiced_corr_raw,
        'voiced_ratio': voiced_ratio,
        'voiced_frames': voiced_frames,
        'total_frames': total_frames,
        'voiced_samples': len(mic_voiced)
    }


def get_file_triplets(base_path):
    """
    모든 MIC/LAR/REF 파일 쌍 찾기
    
    Returns:
        list of dict: {'speaker', 'file', 'mic', 'lar', 'ref'}
    """
    triplets = []
    
    for gender in ['FEMALE', 'MALE']:
        mic_base = f"{base_path}/{gender}/MIC"
        lar_base = f"{base_path}/{gender}/LAR"
        ref_base = f"{base_path}/{gender}/REF"
        
        if not os.path.exists(mic_base):
            continue
        
        speakers = sorted([d for d in os.listdir(mic_base) 
                          if os.path.isdir(f"{mic_base}/{d}")])
        
        for speaker in speakers:
            mic_dir = f"{mic_base}/{speaker}"
            lar_dir = f"{lar_base}/{speaker}"
            ref_dir = f"{ref_base}/{speaker}"
            
            if not os.path.exists(ref_dir):
                continue
            
            files = sorted([f for f in os.listdir(mic_dir) if f.endswith('.wav')])
            
            for mic_file in files:
                # 파일명 변환
                base_name = mic_file.replace('mic_', '').replace('.wav', '')
                lar_file = f"lar_{base_name}.wav"
                ref_file = f"ref_{base_name}.f0"
                
                mic_path = f"{mic_dir}/{mic_file}"
                lar_path = f"{lar_dir}/{lar_file}"
                ref_path = f"{ref_dir}/{ref_file}"
                
                if os.path.exists(lar_path) and os.path.exists(ref_path):
                    triplets.append({
                        'speaker': speaker,
                        'file': base_name,
                        'mic': mic_path,
                        'lar': lar_path,
                        'ref': ref_path
                    })
    
    return triplets


def analyze_voiced_correlation(samples_per_speaker=SAMPLES_PER_SPEAKER):
    """유성음 구간 상관관계 분석"""
    
    print("=" * 70)
    print("PTDB-TUG 유성음 구간 분석")
    print("=" * 70)
    
    # 1. 데이터 구조 확인
    print("\n[1] 데이터 구조 확인...")
    triplets = get_file_triplets(BASE_PATH)
    
    speakers = sorted(set(t['speaker'] for t in triplets))
    print(f"  화자 수: {len(speakers)}명")
    print(f"  총 파일 수: {len(triplets)}개")
    
    # 화자별 파일 수
    speaker_counts = defaultdict(int)
    for t in triplets:
        speaker_counts[t['speaker']] += 1
    
    print("\n  화자별 파일 수:")
    for sp in speakers:
        print(f"    {sp}: {speaker_counts[sp]} files")
    
    # 2. .f0 파일 형식 확인
    print("\n[2] .f0 파일 형식 확인...")
    sample_f0_path = triplets[0]['ref']
    sample_f0 = load_f0_file(sample_f0_path)
    print(f"  샘플 파일: {os.path.basename(sample_f0_path)}")
    print(f"  Shape: {sample_f0.shape}")
    print(f"  Columns: pitch, voicing_prob, rms, peak_corr")
    print(f"  Voiced frames: {np.sum(sample_f0[:, 0] > 0)} / {len(sample_f0)}")
    
    # 3. 화자별 샘플 분석
    print(f"\n[3] 상관관계 분석 (화자당 {samples_per_speaker}개)...")
    
    results = []
    speaker_samples = defaultdict(list)
    
    for t in triplets:
        speaker_samples[t['speaker']].append(t)
    
    total_samples = len(speakers) * samples_per_speaker
    processed = 0
    
    for speaker in speakers:
        samples = speaker_samples[speaker][:samples_per_speaker]
        
        for t in samples:
            result = compute_correlation(t['mic'], t['lar'], t['ref'])
            
            if result is not None:
                result['speaker'] = t['speaker']
                result['file'] = t['file']
                results.append(result)
            
            processed += 1
            if processed % 20 == 0 or processed == total_samples:
                print(f"\r  처리 중: {processed}/{total_samples} ({100*processed/total_samples:.1f}%)", end='', flush=True)
    
    print()
    
    # 4. 결과 요약
    print("\n" + "=" * 70)
    print("분석 결과")
    print("=" * 70)
    
    # 전체 통계
    full_corrs = [r['full_corr'] for r in results if not np.isnan(r['full_corr'])]
    voiced_corrs = [r['voiced_corr'] for r in results if not np.isnan(r['voiced_corr'])]
    voiced_corrs_raw = [r['voiced_corr_raw'] for r in results if not np.isnan(r.get('voiced_corr_raw', np.nan))]
    full_corrs_raw = [r['full_corr_raw'] for r in results if not np.isnan(r.get('full_corr_raw', np.nan))]
    voiced_ratios = [r['voiced_ratio'] for r in results]
    
    print(f"\n샘플 수: {len(results)}개")
    print(f"\n⚠️ 참고: 극성 반전 보정(|corr|) 적용됨")
    print(f"\n상관관계 비교:")
    print("┌" + "─" * 15 + "┬" + "─" * 15 + "┬" + "─" * 15 + "┬" + "─" * 15 + "┐")
    print(f"│ {'구간':<13} │ {'Mean |Corr|':<13} │ {'Mean Raw':<13} │ {'Std':<13} │")
    print("├" + "─" * 15 + "┼" + "─" * 15 + "┼" + "─" * 15 + "┼" + "─" * 15 + "┤")
    print(f"│ {'전체':<13} │ {np.mean(full_corrs):>13.4f} │ {np.mean(full_corrs_raw):>13.4f} │ {np.std(full_corrs):>13.4f} │")
    print(f"│ {'유성음만':<12} │ {np.mean(voiced_corrs):>13.4f} │ {np.mean(voiced_corrs_raw):>13.4f} │ {np.std(voiced_corrs):>13.4f} │")
    print("└" + "─" * 15 + "┴" + "─" * 15 + "┴" + "─" * 15 + "┴" + "─" * 15 + "┘")
    
    print(f"\n평균 유성음 비율: {np.mean(voiced_ratios):.1%}")
    
    # 화자별 유성음 corr
    print("\n화자별 유성음 corr (극성 보정 |corr|):")
    print("┌" + "─" * 10 + "┬" + "─" * 15 + "┬" + "─" * 15 + "┬" + "─" * 15 + "┐")
    print(f"│ {'Speaker':<8} │ {'|Voiced Corr|':<13} │ {'|Full Corr|':<13} │ {'Raw Corr':<13} │")
    print("├" + "─" * 10 + "┼" + "─" * 15 + "┼" + "─" * 15 + "┼" + "─" * 15 + "┤")
    
    speaker_stats = defaultdict(list)
    for r in results:
        speaker_stats[r['speaker']].append(r)
    
    speaker_voiced_means = {}
    for sp in sorted(speaker_stats.keys()):
        sp_results = speaker_stats[sp]
        sp_voiced = [r['voiced_corr'] for r in sp_results if not np.isnan(r['voiced_corr'])]
        sp_full = [r['full_corr'] for r in sp_results if not np.isnan(r['full_corr'])]
        sp_voiced_raw = [r['voiced_corr_raw'] for r in sp_results if not np.isnan(r.get('voiced_corr_raw', np.nan))]
        
        voiced_mean = np.mean(sp_voiced) if sp_voiced else np.nan
        full_mean = np.mean(sp_full) if sp_full else np.nan
        raw_mean = np.mean(sp_voiced_raw) if sp_voiced_raw else np.nan
        
        # 극성 확인 (raw가 대부분 음수면 극성 반전된 화자)
        polarity = "🔄" if raw_mean < 0 else "  "
        
        speaker_voiced_means[sp] = voiced_mean
        print(f"│ {sp:<8} │ {voiced_mean:>13.4f} │ {full_mean:>13.4f} │ {raw_mean:>+10.4f} {polarity}│")
    
    print("└" + "─" * 10 + "┴" + "─" * 15 + "┴" + "─" * 15 + "┴" + "─" * 15 + "┘")
    print("  🔄 = 극성 반전 (Raw corr < 0)")
    
    # 극성 반전 화자 수 확인
    inverted_speakers = []
    normal_speakers = []
    for sp in speaker_stats.keys():
        sp_results = speaker_stats[sp]
        sp_voiced_raw = [r['voiced_corr_raw'] for r in sp_results if not np.isnan(r.get('voiced_corr_raw', np.nan))]
        raw_mean = np.mean(sp_voiced_raw) if sp_voiced_raw else 0
        if raw_mean < 0:
            inverted_speakers.append(sp)
        else:
            normal_speakers.append(sp)
    
    print(f"\n  정상 극성 화자 ({len(normal_speakers)}명): {sorted(normal_speakers)}")
    print(f"  반전 극성 화자 ({len(inverted_speakers)}명): {sorted(inverted_speakers)}")
    
    # corr 분포
    print("\n유성음 corr 분포:")
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
    hist, _ = np.histogram(voiced_corrs, bins=bins)
    for i in range(len(bins) - 1):
        bar = "█" * int(hist[i] / max(hist) * 30) if max(hist) > 0 else ""
        print(f"  {bins[i]:.1f}-{bins[i+1]:.1f}: {hist[i]:3d} {bar}")
    
    # 5. 판단
    mean_voiced_corr = np.mean(voiced_corrs)
    mean_full_corr = np.mean(full_corrs)
    improvement = mean_voiced_corr - mean_full_corr
    
    print("\n" + "=" * 70)
    print("판단 결과")
    print("=" * 70)
    
    print(f"\n전체 구간 corr: {mean_full_corr:.4f}")
    print(f"유성음 구간 corr: {mean_voiced_corr:.4f}")
    print(f"개선: +{improvement:.4f} ({improvement/mean_full_corr*100:.1f}% 향상)" if mean_full_corr > 0 else "")
    
    if mean_voiced_corr >= 0.3:
        print(f"\n✅ 유성음 구간 corr = {mean_voiced_corr:.4f} (≥ 0.3)")
        print("→ PTDB-TUG 사용 가능!")
        print("→ 다음 단계: 유성음 구간으로 화자 독립 모델 학습")
        decision = "USE_PTDB"
    elif mean_voiced_corr >= 0.1:
        print(f"\n⚠️ 유성음 구간 corr = {mean_voiced_corr:.4f} (0.1 ~ 0.3)")
        print("→ 추가 분석 필요")
        print("→ 정렬 최적화 또는 필터링 조정 시도")
        decision = "NEED_OPTIMIZATION"
    else:
        print(f"\n❌ 유성음 구간 corr = {mean_voiced_corr:.4f} (< 0.1)")
        print("→ PTDB-TUG 데이터 자체 문제 가능성")
        print("→ 다른 데이터셋(OpenGlot, Singing-Voice)만 사용 권장")
        decision = "SKIP_PTDB"
    
    return {
        'mean_full_corr': mean_full_corr,
        'mean_voiced_corr': mean_voiced_corr,
        'voiced_ratio': np.mean(voiced_ratios),
        'speaker_stats': speaker_voiced_means,
        'decision': decision,
        'all_results': results
    }


def main():
    results = analyze_voiced_correlation(samples_per_speaker=10)
    
    # 추가 분석: corr이 높은 화자 확인
    print("\n" + "=" * 70)
    print("추가 분석: 화자별 상세")
    print("=" * 70)
    
    # corr 높은 순 정렬
    sorted_speakers = sorted(results['speaker_stats'].items(), 
                             key=lambda x: x[1] if not np.isnan(x[1]) else -1, 
                             reverse=True)
    
    print("\n화자별 유성음 corr (높은 순):")
    for i, (sp, corr) in enumerate(sorted_speakers):
        marker = "🔥" if corr >= 0.3 else "✓" if corr >= 0.1 else "✗"
        print(f"  {i+1:2d}. {sp}: {corr:.4f} {marker}")
    
    # corr >= 0.3인 화자
    high_corr_speakers = [sp for sp, c in sorted_speakers if c >= 0.3]
    mid_corr_speakers = [sp for sp, c in sorted_speakers if 0.1 <= c < 0.3]
    
    print(f"\n고 corr 화자 (≥0.3): {len(high_corr_speakers)}명")
    print(f"중 corr 화자 (0.1-0.3): {len(mid_corr_speakers)}명")
    
    if len(high_corr_speakers) >= 10:
        print("\n→ 고 corr 화자만으로 학습 가능!")
    elif len(high_corr_speakers) + len(mid_corr_speakers) >= 10:
        print("\n→ 중/고 corr 화자 결합 시 학습 가능")


if __name__ == "__main__":
    main()
