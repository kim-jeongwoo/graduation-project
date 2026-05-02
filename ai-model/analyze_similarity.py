#!/usr/bin/env python3
"""
EGG 예측 및 발성 유사도 비교 스크립트
=====================================
기준 노래 vs 사용자 노래의 EGG 패턴 비교 → 발성 유사도(corr) 계산

Steps:
  1. WAV 파일 정보 확인
  2. 전처리 (16kHz, mono, normalize)
  3. Exp3 모델로 EGG 예측
  4. Pearson correlation 유사도 계산
  5. 시각화 (3개 이미지)
  6. 리포트 저장
"""
import os
import numpy as np
import torch
import librosa
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.signal import resample_poly
from scipy.stats import pearsonr
from math import gcd

from model.efficient_egg import build_efficient_model

# ── 경로 ──
BASE = os.path.expanduser('~/projects/egg_prediction')
REC_DIR = os.path.join(BASE, 'data/rpi_recordings')
CKPT_PATH = os.path.join(BASE, 'checkpoints/exp3_efficient/best_model.pt')
OUT_DIR = os.path.join(BASE, 'results/validation')

# ── 모델 설정 (Exp3) ──
MODEL_CFG = {
    'channels': 96,
    'n_layers': 24,
    'kernel_size': 3,
    'n_stacks': 3,
    'dropout': 0.1,
}
WINDOW = 4096
TARGET_SR = 16000

# ── 파일 정의 ──
REF_FILES = [
    ('0000.wav', '기준 0000'),
    ('0001.wav', '기준 0001'),
]
USER_FILES = [
    ('usb_mic_test1_11s.wav', '사용자 11s'),
    ('usb_mic_test1_18s.wav', '사용자 18s'),
]
ALL_FILES = REF_FILES + USER_FILES


# ============================================================
# 1단계: 파일 정보 확인
# ============================================================
def get_wav_info(filepath):
    """WAV 파일 정보 반환"""
    info = sf.info(filepath)
    return {
        'path': filepath,
        'sample_rate': info.samplerate,
        'channels': info.channels,
        'duration': info.duration,
        'frames': info.frames,
        'format': info.subtype,
    }


# ============================================================
# 2단계: 전처리
# ============================================================
def preprocess_wav(filepath, target_sr=16000):
    """WAV → 16kHz mono normalized numpy array"""
    audio, sr = librosa.load(filepath, sr=None, mono=True)  # load as mono float32

    # Resample to target_sr
    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)

    # Normalize to [-1, 1]
    max_val = np.max(np.abs(audio))
    if max_val > 1e-8:
        audio = audio / max_val

    return audio, target_sr


# ============================================================
# 3단계: EGG 예측
# ============================================================
def load_model(device):
    """Exp3 best model 로드"""
    model = build_efficient_model(MODEL_CFG).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print(f"  모델 로드 완료: epoch {ckpt['epoch']}, val_corr {ckpt['val_corr']:.4f}")
    return model


def predict_egg(model, audio, device, window=WINDOW):
    """
    MIC 오디오 → Pred EGG 생성
    Sliding window로 전체 오디오에 대해 예측, 겹치는 구간은 평균
    """
    hop = window // 2  # 50% overlap
    n = len(audio)

    # Pad to fit windows
    pad_len = 0
    if n < window:
        pad_len = window - n
        audio = np.pad(audio, (0, pad_len), mode='constant')
        n = len(audio)

    # z-normalize (모델 학습 시 z-norm 사용)
    mean, std = audio.mean(), audio.std()
    if std > 1e-8:
        audio_norm = (audio - mean) / std
    else:
        audio_norm = audio.copy()

    # Sliding window prediction
    pred_sum = np.zeros(n, dtype=np.float64)
    pred_cnt = np.zeros(n, dtype=np.float64)

    with torch.no_grad():
        starts = list(range(0, n - window + 1, hop))
        if len(starts) == 0:
            starts = [0]

        # Batch process
        batch_size = 64
        for bi in range(0, len(starts), batch_size):
            batch_starts = starts[bi:bi + batch_size]
            chunks = []
            for s in batch_starts:
                chunk = audio_norm[s:s + window]
                chunks.append(chunk)

            x = torch.from_numpy(np.array(chunks)).float().unsqueeze(1).to(device)  # [B, 1, W]
            pred = model(x)  # [B, 1, W]
            pred_np = pred.cpu().numpy()[:, 0, :]  # [B, W]

            for j, s in enumerate(batch_starts):
                pred_sum[s:s + window] += pred_np[j]
                pred_cnt[s:s + window] += 1.0

    # Average overlapping predictions
    mask = pred_cnt > 0
    pred_egg = np.zeros(n)
    pred_egg[mask] = pred_sum[mask] / pred_cnt[mask]

    # Remove padding
    if pad_len > 0:
        pred_egg = pred_egg[:n - pad_len]

    return pred_egg


# ============================================================
# 4단계: 유사도 계산
# ============================================================
def compute_similarity(egg1, egg2):
    """두 EGG 신호 간 Pearson correlation (짧은 쪽 기준)"""
    min_len = min(len(egg1), len(egg2))
    e1 = egg1[:min_len]
    e2 = egg2[:min_len]

    if np.std(e1) < 1e-8 or np.std(e2) < 1e-8:
        return 0.0

    corr, _ = pearsonr(e1, e2)
    return corr


def compute_windowed_similarity(egg1, egg2, window_sec=1.0, sr=16000):
    """
    윈도우 단위로 corr 계산 후 평균 (전체 길이 차이에 강건)
    """
    min_len = min(len(egg1), len(egg2))
    e1 = egg1[:min_len]
    e2 = egg2[:min_len]

    win = int(window_sec * sr)
    hop = win // 2
    corrs = []

    for s in range(0, min_len - win + 1, hop):
        seg1 = e1[s:s + win]
        seg2 = e2[s:s + win]
        if np.std(seg1) > 1e-8 and np.std(seg2) > 1e-8:
            c, _ = pearsonr(seg1, seg2)
            corrs.append(c)

    if len(corrs) == 0:
        return 0.0
    return float(np.mean(corrs))


# ============================================================
# 5단계: 시각화
# ============================================================
def plot_individual_predictions(file_data, save_path):
    """이미지 1: 각 파일별 MIC + Pred EGG"""
    n_files = len(file_data)
    fig, axes = plt.subplots(n_files, 2, figsize=(18, 3.5 * n_files))
    fig.patch.set_facecolor('white')

    for i, (name, audio, pred_egg, info) in enumerate(file_data):
        sr = TARGET_SR
        t_audio = np.arange(len(audio)) / sr
        t_egg = np.arange(len(pred_egg)) / sr

        # MIC
        axes[i, 0].plot(t_audio, audio, color='#1f77b4', lw=0.4)
        axes[i, 0].set_title(f'{name} — MIC Input', fontsize=11, fontweight='bold')
        axes[i, 0].set_ylabel('Amplitude', fontsize=9)
        axes[i, 0].set_xlim(0, t_audio[-1])
        axes[i, 0].grid(True, alpha=0.25)
        axes[i, 0].tick_params(labelsize=8)

        # Pred EGG
        axes[i, 1].plot(t_egg, pred_egg, color='#e74c3c', lw=0.4)
        axes[i, 1].set_title(f'{name} — Predicted EGG', fontsize=11, fontweight='bold')
        axes[i, 1].set_ylabel('Amplitude', fontsize=9)
        axes[i, 1].set_xlim(0, t_egg[-1])
        axes[i, 1].grid(True, alpha=0.25)
        axes[i, 1].tick_params(labelsize=8)

    axes[-1, 0].set_xlabel('Time (s)', fontsize=10)
    axes[-1, 1].set_xlabel('Time (s)', fontsize=10)

    plt.suptitle('Individual EGG Predictions (Exp3 Model)', fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✅ 이미지 1 저장: {save_path}")


def plot_best_comparison(ref_name, ref_egg, user_name, user_egg, corr_val, save_path):
    """이미지 2: 가장 유사도 높은 쌍 비교"""
    min_len = min(len(ref_egg), len(user_egg))
    ref_e = ref_egg[:min_len]
    user_e = user_egg[:min_len]
    t = np.arange(min_len) / TARGET_SR

    # 줌인 구간: 에너지 높은 1초 구간
    zoom_samples = TARGET_SR  # 1초
    if min_len > zoom_samples:
        energy = np.convolve(ref_e ** 2 + user_e ** 2, np.ones(zoom_samples), mode='valid')
        zoom_start = np.argmax(energy)
    else:
        zoom_start = 0
    zoom_end = min(zoom_start + zoom_samples, min_len)
    t_zoom = np.arange(zoom_start, zoom_end) / TARGET_SR

    fig, axes = plt.subplots(3, 1, figsize=(16, 11), gridspec_kw={'height_ratios': [1, 1, 1.3]})
    fig.patch.set_facecolor('white')

    # 상단: 기준 Pred EGG
    axes[0].plot(t, ref_e, color='#1f77b4', lw=0.5)
    axes[0].set_title(f'{ref_name} — Predicted EGG', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Amplitude', fontsize=10)
    axes[0].set_xlim(t[0], t[-1])
    axes[0].grid(True, alpha=0.25)
    axes[0].axvspan(t_zoom[0], t_zoom[-1], alpha=0.1, color='red', label='Zoom region')
    axes[0].legend(loc='upper right', fontsize=9)

    # 중단: 사용자 Pred EGG
    axes[1].plot(t, user_e, color='#ff7f0e', lw=0.5)
    axes[1].set_title(f'{user_name} — Predicted EGG', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Amplitude', fontsize=10)
    axes[1].set_xlim(t[0], t[-1])
    axes[1].grid(True, alpha=0.25)
    axes[1].axvspan(t_zoom[0], t_zoom[-1], alpha=0.1, color='red', label='Zoom region')
    axes[1].legend(loc='upper right', fontsize=9)

    # 하단: 겹친 그래프 (줌인 1초)
    axes[2].plot(t_zoom, ref_e[zoom_start:zoom_end], color='#1f77b4', lw=1.5,
                 label=f'{ref_name}')
    axes[2].plot(t_zoom, user_e[zoom_start:zoom_end], color='#ff7f0e', lw=1.5, alpha=0.85,
                 label=f'{user_name}')
    axes[2].set_title(f'Zoomed Overlay (1s) — Correlation: {corr_val:.4f}',
                      fontsize=12, fontweight='bold')
    axes[2].set_xlabel('Time (s)', fontsize=11)
    axes[2].set_ylabel('Amplitude', fontsize=10)
    axes[2].legend(loc='upper right', fontsize=10, framealpha=0.9)
    axes[2].grid(True, alpha=0.25)

    plt.suptitle(f'Best Match — Vocal Similarity (Corr: {corr_val:.4f})',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✅ 이미지 2 저장: {save_path}")


def plot_similarity_matrix(corr_matrix, ref_labels, user_labels, save_path):
    """이미지 3: 유사도 히트맵"""
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')

    im = ax.imshow(corr_matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Pearson Correlation', fontsize=11)

    ax.set_xticks(range(len(user_labels)))
    ax.set_xticklabels(user_labels, fontsize=11, fontweight='bold')
    ax.set_yticks(range(len(ref_labels)))
    ax.set_yticklabels(ref_labels, fontsize=11, fontweight='bold')

    # 값 표시
    for i in range(len(ref_labels)):
        for j in range(len(user_labels)):
            val = corr_matrix[i, j]
            color = 'white' if val > 0.5 else 'black'
            ax.text(j, i, f'{val:.4f}', ha='center', va='center',
                    fontsize=14, fontweight='bold', color=color)

    ax.set_title('Vocal Similarity Matrix (EGG Correlation)', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('User Files', fontsize=12)
    ax.set_ylabel('Reference Files', fontsize=12)

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✅ 이미지 3 저장: {save_path}")


# ============================================================
# 6단계: 리포트
# ============================================================
def write_report(file_infos, corr_matrix, windowed_matrix, ref_labels, user_labels, save_path):
    """결과 리포트 텍스트 파일 저장"""
    best_idx = np.unravel_index(np.argmax(corr_matrix), corr_matrix.shape)
    best_corr = corr_matrix[best_idx]
    best_pair = f"{ref_labels[best_idx[0]]} vs {user_labels[best_idx[1]]}"

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  발성 유사도 분석 결과\n")
        f.write("  모델: Exp3 (EfficientEGGNet, Test Corr: 0.7163)\n")
        f.write("=" * 60 + "\n\n")

        f.write("파일 정보:\n")
        f.write("-" * 60 + "\n")
        for name, info in file_infos:
            f.write(f"  {name}:\n")
            f.write(f"    길이: {info['duration']:.2f}초 ({info['frames']:,} samples)\n")
            f.write(f"    샘플레이트: {info['sample_rate']}Hz\n")
            f.write(f"    채널: {info['channels']}ch\n")
            f.write(f"    포맷: {info['format']}\n")
        f.write("\n")

        f.write("유사도 매트릭스 (Global Pearson Correlation):\n")
        f.write("-" * 60 + "\n")
        header = f"{'':20s}"
        for ul in user_labels:
            header += f" | {ul:>15s}"
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")
        for i, rl in enumerate(ref_labels):
            row = f"{rl:20s}"
            for j in range(len(user_labels)):
                row += f" | {corr_matrix[i, j]:>15.4f}"
            f.write(row + "\n")
        f.write("\n")

        f.write("유사도 매트릭스 (Windowed Mean Correlation, 1s window):\n")
        f.write("-" * 60 + "\n")
        header = f"{'':20s}"
        for ul in user_labels:
            header += f" | {ul:>15s}"
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")
        for i, rl in enumerate(ref_labels):
            row = f"{rl:20s}"
            for j in range(len(user_labels)):
                row += f" | {windowed_matrix[i, j]:>15.4f}"
            f.write(row + "\n")
        f.write("\n")

        f.write(f"최고 유사도: {best_corr:.4f} ({best_pair})\n\n")

        f.write("해석 기준:\n")
        f.write("-" * 60 + "\n")
        f.write("  0.8 이상  : 매우 유사한 발성\n")
        f.write("  0.6 ~ 0.8 : 유사한 발성\n")
        f.write("  0.4 ~ 0.6 : 보통\n")
        f.write("  0.4 미만  : 다른 발성 패턴\n")
        f.write("\n")

        # 해석
        if best_corr >= 0.8:
            interpretation = "매우 유사한 발성 패턴"
        elif best_corr >= 0.6:
            interpretation = "유사한 발성 패턴"
        elif best_corr >= 0.4:
            interpretation = "보통 수준의 유사성"
        else:
            interpretation = "다른 발성 패턴"
        f.write(f"결론: {best_pair} → {interpretation} ({best_corr:.4f})\n")
        f.write("=" * 60 + "\n")

    print(f"  ✅ 리포트 저장: {save_path}")


# ============================================================
# 메인
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print("=" * 60)
    print("  EGG 예측 및 발성 유사도 비교")
    print("=" * 60)

    # ── 1단계: 파일 정보 ──
    print("\n[1단계] 파일 정보 확인")
    file_infos = []
    for fname, label in ALL_FILES:
        path = os.path.join(REC_DIR, fname)
        info = get_wav_info(path)
        file_infos.append((label, info))
        print(f"  {label:15s}: {info['duration']:.2f}s, {info['sample_rate']}Hz, "
              f"{info['channels']}ch, {info['format']}")

    # ── 2단계: 전처리 ──
    print("\n[2단계] 전처리 (16kHz mono normalize)")
    audio_data = {}
    for fname, label in ALL_FILES:
        path = os.path.join(REC_DIR, fname)
        audio, sr = preprocess_wav(path, TARGET_SR)
        audio_data[label] = audio
        print(f"  {label:15s}: {len(audio):,} samples ({len(audio)/sr:.2f}s)")

    # ── 3단계: EGG 예측 ──
    print("\n[3단계] EGG 예측 (Exp3 모델)")
    model = load_model(device)
    egg_data = {}
    for label, audio in audio_data.items():
        print(f"  예측 중: {label} ({len(audio):,} samples)...", end=" ")
        pred_egg = predict_egg(model, audio, device)
        egg_data[label] = pred_egg
        print(f"→ EGG {len(pred_egg):,} samples")

    # ── 4단계: 유사도 계산 ──
    print("\n[4단계] 유사도 계산")
    ref_labels = [label for _, label in REF_FILES]
    user_labels = [label for _, label in USER_FILES]

    corr_matrix = np.zeros((len(ref_labels), len(user_labels)))
    windowed_matrix = np.zeros((len(ref_labels), len(user_labels)))

    for i, rl in enumerate(ref_labels):
        for j, ul in enumerate(user_labels):
            # Global correlation
            corr_val = compute_similarity(egg_data[rl], egg_data[ul])
            corr_matrix[i, j] = corr_val
            # Windowed correlation
            win_corr = compute_windowed_similarity(egg_data[rl], egg_data[ul],
                                                    window_sec=1.0, sr=TARGET_SR)
            windowed_matrix[i, j] = win_corr
            print(f"  {rl:10s} vs {ul:12s}: global={corr_val:.4f}, windowed={win_corr:.4f}")

    best_idx = np.unravel_index(np.argmax(corr_matrix), corr_matrix.shape)
    best_corr = corr_matrix[best_idx]
    print(f"\n  최고 유사도: {best_corr:.4f} "
          f"({ref_labels[best_idx[0]]} vs {user_labels[best_idx[1]]})")

    # ── 5단계: 시각화 ──
    print("\n[5단계] 시각화")
    # 이미지 1: 개별 예측 결과
    file_data_for_plot = []
    for fname, label in ALL_FILES:
        file_data_for_plot.append((label, audio_data[label], egg_data[label],
                                   dict(file_infos)[label] if label in dict(file_infos) else {}))
    # fix: file_infos를 dict로 변환
    info_dict = {name: info for name, info in file_infos}
    file_data_for_plot = []
    for fname, label in ALL_FILES:
        file_data_for_plot.append((label, audio_data[label], egg_data[label], info_dict[label]))

    plot_individual_predictions(file_data_for_plot,
                                os.path.join(OUT_DIR, 'individual_predictions.png'))

    # 이미지 2: 최고 유사도 쌍 비교
    best_ref = ref_labels[best_idx[0]]
    best_user = user_labels[best_idx[1]]
    plot_best_comparison(best_ref, egg_data[best_ref],
                         best_user, egg_data[best_user],
                         best_corr,
                         os.path.join(OUT_DIR, 'best_comparison.png'))

    # 이미지 3: 유사도 매트릭스
    plot_similarity_matrix(corr_matrix, ref_labels, user_labels,
                           os.path.join(OUT_DIR, 'similarity_matrix.png'))

    # ── 6단계: 리포트 ──
    print("\n[6단계] 리포트 저장")
    write_report(file_infos, corr_matrix, windowed_matrix, ref_labels, user_labels,
                 os.path.join(OUT_DIR, 'similarity_report.txt'))

    # ── 결과 요약 ──
    print(f"\n{'=' * 60}")
    print("  분석 완료!")
    print(f"{'=' * 60}")
    print(f"\n  유사도 매트릭스 (Global Corr):")
    print(f"  {'':15s}  {'사용자 11s':>12s}  {'사용자 18s':>12s}")
    for i, rl in enumerate(ref_labels):
        print(f"  {rl:15s}  {corr_matrix[i,0]:>12.4f}  {corr_matrix[i,1]:>12.4f}")
    print(f"\n  최고: {best_corr:.4f} ({best_ref} vs {best_user})")

    if best_corr >= 0.8:
        print("  → 매우 유사한 발성 패턴")
    elif best_corr >= 0.6:
        print("  → 유사한 발성 패턴")
    elif best_corr >= 0.4:
        print("  → 보통 수준의 유사성")
    else:
        print("  → 다른 발성 패턴")

    print(f"\n  출력 파일:")
    print(f"    1. {OUT_DIR}/individual_predictions.png")
    print(f"    2. {OUT_DIR}/best_comparison.png")
    print(f"    3. {OUT_DIR}/similarity_matrix.png")
    print(f"    4. {OUT_DIR}/similarity_report.txt")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
