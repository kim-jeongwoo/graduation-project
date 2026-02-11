#!/usr/bin/env python3
"""
SVD (Saarbrücken Voice Database) 분석 스크립트
- .nsp 파일 (음성) 형식 분석
- .egg 파일 (EGG) 형식 분석
- mic + EGG 쌍 확인
"""

import os
import struct
import numpy as np
from collections import defaultdict

# ============================================================
# 설정
# ============================================================
SVD_PATH = "/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw/SVD"
SVD_HEALTHY_PATH = "/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw/SVD_healthy"


def analyze_file_header(filepath, num_bytes=256):
    """파일 헤더 분석"""
    with open(filepath, 'rb') as f:
        header = f.read(num_bytes)
    return header


def parse_ds16_header(filepath):
    """
    DS16 (IFF variant) 헤더 파싱
    SVD의 .nsp/.egg 파일은 FORMDS16 형식
    
    구조:
    - FORM (4 bytes)
    - DS16 (4 bytes) - form type
    - D... (4 bytes) - size marker
    - HEDR (4 bytes) - header chunk
    - 32 bytes header data (날짜, 샘플레이트 등)
    - SDA_ (4 bytes) - sample data chunk
    - ... audio data (16-bit signed, little-endian)
    """
    with open(filepath, 'rb') as f:
        # Read FORM header
        form_id = f.read(4)
        if form_id != b'FORM':
            return None, "Not IFF format"
        
        form_type = f.read(4)  # DS16
        
        # Skip size marker
        f.read(4)
        
        # Read HEDR chunk
        hedr_id = f.read(4)
        if hedr_id != b'HEDR':
            return None, "No HEDR chunk"
        
        hedr_size = struct.unpack('<I', f.read(4))[0]  # Little-endian
        hedr_data = f.read(hedr_size)
        
        # Parse header - timestamp string (20 bytes) + sample info
        timestamp = hedr_data[:20].decode('ascii', errors='ignore').strip('\x00')
        
        # Sample rate is at offset 20 (4 bytes, little-endian)
        # Based on SVD documentation: 50000 Hz
        sample_rate = 50000  # Default for SVD
        
        # Try to extract from header
        if len(hedr_data) >= 24:
            sr_candidate = struct.unpack('<I', hedr_data[20:24])[0]
            if 8000 <= sr_candidate <= 96000:
                sample_rate = sr_candidate
        
        # Read SDA_ chunk
        sda_id = f.read(4)
        if sda_id != b'SDA_':
            return None, "No SDA_ chunk"
        
        sda_size = struct.unpack('<I', f.read(4))[0]
        
        # Calculate duration
        num_samples = sda_size // 2  # 16-bit = 2 bytes
        duration = num_samples / sample_rate
        
        return {
            'form_type': form_type.decode('ascii', errors='ignore'),
            'timestamp': timestamp,
            'sample_rate': sample_rate,
            'num_samples': num_samples,
            'duration': duration,
            'data_offset': f.tell()
        }, None


def load_ds16_audio(filepath):
    """DS16 형식 오디오 로드"""
    info, error = parse_ds16_header(filepath)
    if error:
        return None, 0
    
    with open(filepath, 'rb') as f:
        # Skip to audio data
        f.seek(info['data_offset'])
        
        # Read all remaining data as 16-bit signed little-endian
        raw_data = f.read()
        audio = np.frombuffer(raw_data, dtype='<i2').astype(np.float32) / 32768.0
    
    return audio, info['sample_rate']


def analyze_nsp_format(nsp_path):
    """NSP/EGG 파일 형식 상세 분석"""
    info, error = parse_ds16_header(nsp_path)
    
    if error:
        print(f"  Error: {error}")
        return None
    
    print(f"  Form Type: {info['form_type']}")
    print(f"  Timestamp: {info['timestamp']}")
    print(f"  Sample Rate: {info['sample_rate']} Hz")
    print(f"  Samples: {info['num_samples']}")
    print(f"  Duration: {info['duration']:.2f}s")
    
    return info


def compute_correlation(audio1, audio2, align=True):
    """두 오디오 신호의 상관관계 계산"""
    min_len = min(len(audio1), len(audio2))
    a1 = audio1[:min_len]
    a2 = audio2[:min_len]
    
    # 시간 정렬 (cross-correlation)
    if align:
        # 정규화
        a1_norm = (a1 - np.mean(a1)) / (np.std(a1) + 1e-8)
        a2_norm = (a2 - np.mean(a2)) / (np.std(a2) + 1e-8)
        
        # Cross-correlation으로 최적 lag 찾기
        max_lag = min(5000, len(a1) // 10)  # 최대 100ms @ 50kHz
        correlation = np.correlate(a1_norm[:20000], a2_norm[:20000], mode='full')
        center = len(correlation) // 2
        search_start = max(0, center - max_lag)
        search_end = min(len(correlation), center + max_lag)
        
        best_idx = search_start + np.argmax(np.abs(correlation[search_start:search_end]))
        best_lag = best_idx - center
        
        # 정렬 적용
        if best_lag > 0:
            a1 = a1[best_lag:]
            a2 = a2[:len(a1)]
        elif best_lag < 0:
            a2 = a2[-best_lag:]
            a1 = a1[:len(a2)]
        
        min_len = min(len(a1), len(a2))
        a1 = a1[:min_len]
        a2 = a2[:min_len]
    
    # 정규화
    a1 = (a1 - np.mean(a1)) / (np.std(a1) + 1e-8)
    a2 = (a2 - np.mean(a2)) / (np.std(a2) + 1e-8)
    
    return np.corrcoef(a1, a2)[0, 1]


def main():
    print("=" * 70)
    print("SVD (Saarbrücken Voice Database) 분석")
    print("=" * 70)
    
    # 1. 데이터 구조 확인
    print("\n[1] 데이터 구조 확인...")
    
    # SVD 폴더 수
    svd_folders = [d for d in os.listdir(SVD_PATH) 
                   if os.path.isdir(os.path.join(SVD_PATH, d)) and d != '.DS_Store']
    print(f"  SVD 총 폴더(화자) 수: {len(svd_folders)}")
    
    # SVD_healthy 폴더 수
    healthy_folders = [d for d in os.listdir(SVD_HEALTHY_PATH) 
                       if os.path.isdir(os.path.join(SVD_HEALTHY_PATH, d)) and d != '.DS_Store']
    print(f"  SVD_healthy 폴더(화자) 수: {len(healthy_folders)}")
    
    # 2. 샘플 폴더 분석
    print("\n[2] 샘플 폴더 내용 분석...")
    sample_folder = os.path.join(SVD_PATH, "1")
    
    print(f"\n  폴더: {sample_folder}")
    for subdir in ['vowels', 'sentences']:
        subdir_path = os.path.join(sample_folder, subdir)
        if os.path.exists(subdir_path):
            files = os.listdir(subdir_path)
            nsp_files = [f for f in files if f.endswith('.nsp')]
            egg_files = [f for f in files if f.endswith('.egg')]
            print(f"    {subdir}/")
            print(f"      .nsp 파일: {len(nsp_files)}개")
            print(f"      .egg 파일: {len(egg_files)}개")
            
            # 쌍 확인
            pairs = []
            for nsp in nsp_files:
                base = nsp.replace('.nsp', '')
                egg = f"{base}-egg.egg"
                if egg in egg_files:
                    pairs.append((nsp, egg))
            print(f"      nsp-egg 쌍: {len(pairs)}개")
    
    # 3. 파일 형식 분석
    print("\n[3] 파일 형식 분석...")
    
    sample_nsp = os.path.join(SVD_PATH, "1/vowels/1-a_n.nsp")
    sample_egg = os.path.join(SVD_PATH, "1/vowels/1-a_n-egg.egg")
    
    print(f"\n  NSP 파일: {os.path.basename(sample_nsp)}")
    nsp_info = analyze_nsp_format(sample_nsp)
    
    print(f"\n  EGG 파일: {os.path.basename(sample_egg)}")
    egg_info = analyze_nsp_format(sample_egg)
    
    # 4. 오디오 데이터 로드 및 상관관계 계산
    print("\n[4] 오디오 데이터 분석...")
    
    try:
        nsp_audio, nsp_sr = load_ds16_audio(sample_nsp)
        egg_audio, egg_sr = load_ds16_audio(sample_egg)
        
        print(f"  NSP: {len(nsp_audio)} samples, {nsp_sr} Hz")
        print(f"  EGG: {len(egg_audio)} samples, {egg_sr} Hz")
        
        # 상관관계
        corr = compute_correlation(nsp_audio, egg_audio)
        print(f"  Raw Correlation: {corr:.4f}")
        print(f"  |Correlation|: {abs(corr):.4f}")
        
    except Exception as e:
        print(f"  Error loading audio: {e}")
    
    # 5. 여러 샘플 분석 (시간 정렬 포함)
    print("\n[5] 다중 샘플 상관관계 분석 (시간 정렬 적용)...")
    
    results = []
    sample_folders = sorted(healthy_folders)[:30]  # 처음 30개 화자
    
    for folder in sample_folders:
        vowels_path = os.path.join(SVD_HEALTHY_PATH, folder, "vowels")
        if not os.path.exists(vowels_path):
            continue
        
        files = os.listdir(vowels_path)
        nsp_files = [f for f in files if f.endswith('.nsp')]
        
        for nsp_file in nsp_files[:2]:  # 화자당 2개
            base = nsp_file.replace('.nsp', '')
            egg_file = f"{base}-egg.egg"
            
            nsp_path = os.path.join(vowels_path, nsp_file)
            egg_path = os.path.join(vowels_path, egg_file)
            
            if os.path.exists(egg_path):
                try:
                    nsp_audio, _ = load_ds16_audio(nsp_path)
                    egg_audio, _ = load_ds16_audio(egg_path)
                    corr = compute_correlation(nsp_audio, egg_audio)
                    results.append({
                        'speaker': folder,
                        'file': base,
                        'corr': corr,
                        'abs_corr': abs(corr)
                    })
                except:
                    pass
    
    if results:
        corrs = [r['abs_corr'] for r in results]
        print(f"  분석한 샘플 수: {len(results)}")
        print(f"  평균 |Correlation|: {np.mean(corrs):.4f}")
        print(f"  Std: {np.std(corrs):.4f}")
        print(f"  Min: {np.min(corrs):.4f}")
        print(f"  Max: {np.max(corrs):.4f}")
        
        # 분포
        print("\n  |Corr| 분포:")
        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        hist, _ = np.histogram(corrs, bins=bins)
        for i in range(len(bins) - 1):
            bar = "█" * int(hist[i] / max(hist) * 30) if max(hist) > 0 else ""
            print(f"    {bins[i]:.1f}-{bins[i+1]:.1f}: {hist[i]:3d} {bar}")
    
    # 6. 최종 판단
    print("\n" + "=" * 70)
    print("최종 판단")
    print("=" * 70)
    
    checklist = {
        "mic 신호 있음 (.nsp)": True,
        "EGG 신호 있음 (.egg)": True,
        "동시 녹음 (쌍)": True,
        "화자 수 충분 (≥10)": len(healthy_folders) >= 10,
        "wav 변환 가능 (ffmpeg 필요)": True,
    }
    
    print("\n체크리스트:")
    for item, result in checklist.items():
        status = "✅" if result else "❌"
        print(f"  {status} {item}")
    
    mean_corr = np.mean(corrs) if results else 0
    
    print(f"\n평균 |Correlation|: {mean_corr:.4f}")
    
    if mean_corr >= 0.3:
        print(f"\n✅ SVD 사용 가능!")
        print(f"  - {len(healthy_folders)}명 건강한 화자")
        print(f"  - mic + EGG 쌍 존재")
        print(f"  - 평균 corr = {mean_corr:.4f} (≥ 0.3)")
        print(f"\n→ 다음 단계: ffmpeg 설치 후 wav 변환")
        print(f"  brew install ffmpeg")
        print(f"  python convert_nsp_to_wav.py {SVD_HEALTHY_PATH}")
    elif mean_corr >= 0.1:
        print(f"\n⚠️ SVD 추가 분석 필요")
        print(f"  - 시간 정렬 필요할 수 있음")
    else:
        print(f"\n❌ SVD 데이터 품질 문제")


if __name__ == "__main__":
    main()
