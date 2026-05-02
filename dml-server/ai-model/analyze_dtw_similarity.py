#!/usr/bin/env python3
"""
DTW 시간 정렬 후 발성 유사도 재계산
====================================
같은 노래를 부른 기준/사용자 파일을 DTW로 시간 정렬하여
EGG 패턴 유사도를 정확하게 비교
"""
import os
import sys
import time
import numpy as np
import torch
import librosa
import soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from model.efficient_egg import build_efficient_model

# ── 경로 ──
BASE = os.path.expanduser('~/projects/egg_prediction')
REC_DIR = os.path.join(BASE, 'data/rpi_recordings')
CKPT_PATH = os.path.join(BASE, 'checkpoints/exp3_efficient/best_model.pt')
OUT_DIR = os.path.join(BASE, 'results/validation')

# ── 모델 설정 (Exp3) ──
MODEL_CFG = {
    'channels': 96, 'n_layers': 24, 'kernel_size': 3,
    'n_stacks': 3, 'dropout': 0.1,
}
WINDOW = 4096
TARGET_SR = 16000

# ── 파일 정의 ──
REF_FILES = [
    ('0000.wav', 'Ref 0000'),
    ('0001.wav', 'Ref 0001'),
]
USER_FILES = [
    ('usb_mic_test1_11s.wav', 'User 11s'),
    ('usb_mic_test1_18s.wav', 'User 18s'),
]
ALL_FILES = REF_FILES + USER_FILES

# 기존 Raw correlation 결과 (이전 분석에서)
RAW_CORRS = {
    ('Ref 0000', 'User 11s'): -0.0039,
    ('Ref 0000', 'User 18s'):  0.0036,
    ('Ref 0001', 'User 11s'):  0.0037,
    ('Ref 0001', 'User 18s'):  0.0028,
}


# ============================================================
# 전처리 & 모델
# ============================================================
def preprocess_wav(filepath, target_sr=16000):
    audio, sr = librosa.load(filepath, sr=None, mono=True)
    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    max_val = np.max(np.abs(audio))
    if max_val > 1e-8:
        audio = audio / max_val
    return audio, target_sr


def load_model(device):
    model = build_efficient_model(MODEL_CFG).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print(f"  Model loaded: epoch {ckpt['epoch']}, val_corr {ckpt['val_corr']:.4f}")
    return model


def predict_egg(model, audio, device, window=WINDOW):
    hop = window // 2
    n = len(audio)
    if n < window:
        audio = np.pad(audio, (0, window - n), mode='constant')
        n = len(audio)
    mean, std = audio.mean(), audio.std()
    audio_norm = (audio - mean) / std if std > 1e-8 else audio.copy()

    pred_sum = np.zeros(n, dtype=np.float64)
    pred_cnt = np.zeros(n, dtype=np.float64)

    with torch.no_grad():
        starts = list(range(0, n - window + 1, hop))
        if not starts:
            starts = [0]
        batch_size = 64
        for bi in range(0, len(starts), batch_size):
            batch_starts = starts[bi:bi + batch_size]
            chunks = [audio_norm[s:s + window] for s in batch_starts]
            x = torch.from_numpy(np.array(chunks)).float().unsqueeze(1).to(device)
            pred = model(x).cpu().numpy()[:, 0, :]
            for j, s in enumerate(batch_starts):
                pred_sum[s:s + window] += pred[j]
                pred_cnt[s:s + window] += 1.0

    mask = pred_cnt > 0
    pred_egg = np.zeros(n)
    pred_egg[mask] = pred_sum[mask] / pred_cnt[mask]
    return pred_egg


# ============================================================
# DTW 정렬
# ============================================================
def extract_envelope(egg, frame_len=160, hop_len=80):
    """EGG에서 에너지 엔벨로프 추출 (DTW 입력용)"""
    n_frames = (len(egg) - frame_len) // hop_len + 1
    envelope = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop_len
        frame = egg[start:start + frame_len]
        envelope[i] = np.sqrt(np.mean(frame ** 2))
    return envelope


def align_with_dtw(egg_ref, egg_user, downsample_factor=50):
    """
    DTW로 두 EGG 신호 시간 정렬

    전략: 원본 신호를 다운샘플링하여 DTW 계산 후,
          경로를 원본 해상도로 매핑

    Args:
        egg_ref: 기준 EGG (full resolution)
        egg_user: 사용자 EGG (full resolution)
        downsample_factor: 다운샘플링 비율

    Returns:
        aligned_ref, aligned_user: 정렬된 신호 (다운샘플 해상도)
        distance: DTW 거리
        path: DTW 경로
    """
    # 다운샘플링
    ref_down = egg_ref[::downsample_factor]
    user_down = egg_user[::downsample_factor]

    # DTW 계산
    distance, path = fastdtw(
        ref_down.reshape(-1, 1),
        user_down.reshape(-1, 1),
        dist=euclidean,
        radius=50
    )

    # 경로에서 정렬된 신호 생성
    path_ref = np.array([p[0] for p in path])
    path_user = np.array([p[1] for p in path])

    aligned_ref = ref_down[path_ref]
    aligned_user = user_down[path_user]

    return aligned_ref, aligned_user, distance, path


def compute_dtw_correlation(egg_ref, egg_user, downsample_factor=50):
    """DTW 정렬 후 correlation 계산"""
    t0 = time.time()
    aligned_ref, aligned_user, dtw_dist, path = align_with_dtw(
        egg_ref, egg_user, downsample_factor
    )
    dt = time.time() - t0

    # 전체 correlation
    if np.std(aligned_ref) > 1e-8 and np.std(aligned_user) > 1e-8:
        corr, _ = pearsonr(aligned_ref, aligned_user)
    else:
        corr = 0.0

    # 윈도우별 correlation (안정성)
    win = max(len(aligned_ref) // 10, 100)
    hop = win // 2
    local_corrs = []
    for s in range(0, len(aligned_ref) - win + 1, hop):
        seg_r = aligned_ref[s:s + win]
        seg_u = aligned_user[s:s + win]
        if np.std(seg_r) > 1e-8 and np.std(seg_u) > 1e-8:
            c, _ = pearsonr(seg_r, seg_u)
            local_corrs.append(c)
    windowed_corr = float(np.mean(local_corrs)) if local_corrs else 0.0

    return {
        'corr': corr,
        'windowed_corr': windowed_corr,
        'dtw_dist': dtw_dist,
        'dtw_time': dt,
        'aligned_ref': aligned_ref,
        'aligned_user': aligned_user,
        'path': path,
        'n_aligned': len(aligned_ref),
    }


# ============================================================
# 시각화
# ============================================================
def plot_alignment_comparison(results, ref_eggs, user_eggs, save_path):
    """
    Image 1: DTW alignment before/after for best pair
    4 subplots: before overlay, after overlay, for top 2 pairs
    """
    # 상위 2개 쌍 정렬
    sorted_pairs = sorted(results.items(), key=lambda x: x[1]['corr'], reverse=True)
    n_show = min(2, len(sorted_pairs))

    fig, axes = plt.subplots(n_show * 2, 1, figsize=(16, 5 * n_show * 2))
    if n_show * 2 == 1:
        axes = [axes]
    fig.patch.set_facecolor('white')

    for pi in range(n_show):
        (ref_label, user_label), res = sorted_pairs[pi]
        raw_corr = RAW_CORRS.get((ref_label, user_label), 0.0)
        dtw_corr = res['corr']

        egg_ref = ref_eggs[ref_label]
        egg_user = user_eggs[user_label]
        aligned_ref = res['aligned_ref']
        aligned_user = res['aligned_user']

        ax_before = axes[pi * 2]
        ax_after = axes[pi * 2 + 1]

        # ── Before (Raw, 다운샘플) ──
        ds = 50
        ref_d = egg_ref[::ds]
        user_d = egg_user[::ds]
        min_len = min(len(ref_d), len(user_d))
        t_raw = np.arange(min_len)

        ax_before.plot(t_raw, ref_d[:min_len], color='#1f77b4', lw=0.8,
                       label=f'{ref_label}', alpha=0.9)
        ax_before.plot(t_raw, user_d[:min_len], color='#ff7f0e', lw=0.8,
                       label=f'{user_label}', alpha=0.75)
        ax_before.set_title(f'BEFORE DTW — {ref_label} vs {user_label}  |  '
                            f'Raw Corr = {raw_corr:.4f}',
                            fontsize=12, fontweight='bold', pad=8)
        ax_before.set_ylabel('Amplitude', fontsize=10)
        ax_before.legend(loc='upper right', fontsize=10, framealpha=0.9)
        ax_before.grid(True, alpha=0.2)
        ax_before.tick_params(labelsize=9)

        # ── After (DTW aligned) ──
        t_aligned = np.arange(len(aligned_ref))
        ax_after.plot(t_aligned, aligned_ref, color='#1f77b4', lw=0.8,
                      label=f'{ref_label} (aligned)', alpha=0.9)
        ax_after.plot(t_aligned, aligned_user, color='#ff7f0e', lw=0.8,
                      label=f'{user_label} (aligned)', alpha=0.75)
        ax_after.set_title(f'AFTER DTW — {ref_label} vs {user_label}  |  '
                           f'DTW Corr = {dtw_corr:.4f}',
                           fontsize=12, fontweight='bold', pad=8)
        ax_after.set_ylabel('Amplitude', fontsize=10)
        ax_after.set_xlabel('Aligned Sample Index', fontsize=10)
        ax_after.legend(loc='upper right', fontsize=10, framealpha=0.9)
        ax_after.grid(True, alpha=0.2)
        ax_after.tick_params(labelsize=9)

        # 배경 색으로 개선 정도 표시
        if dtw_corr > raw_corr + 0.05:
            ax_after.set_facecolor('#f0fff0')  # light green

    plt.suptitle('DTW Time Alignment — Before vs After',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  [OK] Image 1: {save_path}")


def plot_dtw_best_match(results, save_path):
    """
    Image 2: Best DTW match detailed view
    3 subplots: ref EGG, user EGG (aligned), overlay zoom
    """
    sorted_pairs = sorted(results.items(), key=lambda x: x[1]['corr'], reverse=True)
    (ref_label, user_label), res = sorted_pairs[0]

    aligned_ref = res['aligned_ref']
    aligned_user = res['aligned_user']
    dtw_corr = res['corr']
    n = len(aligned_ref)
    t = np.arange(n)

    # Zoom: energy-rich 1-sec region (at downsampled rate ~320 samples = 1s)
    zoom_len = min(320, n // 3)
    energy = np.convolve(aligned_ref ** 2 + aligned_user ** 2,
                         np.ones(zoom_len), mode='valid')
    zoom_start = np.argmax(energy)
    zoom_end = zoom_start + zoom_len
    t_zoom = np.arange(zoom_start, zoom_end)

    fig, axes = plt.subplots(3, 1, figsize=(16, 12),
                             gridspec_kw={'height_ratios': [1, 1, 1.3]})
    fig.patch.set_facecolor('white')

    # Ref EGG
    axes[0].plot(t, aligned_ref, color='#1f77b4', lw=0.6)
    axes[0].set_title(f'{ref_label} — Predicted EGG (DTW aligned)',
                      fontsize=12, fontweight='bold', pad=8)
    axes[0].set_ylabel('Amplitude', fontsize=10)
    axes[0].axvspan(zoom_start, zoom_end, alpha=0.12, color='red', label='Zoom region')
    axes[0].legend(loc='upper right', fontsize=9)
    axes[0].grid(True, alpha=0.2)

    # User EGG
    axes[1].plot(t, aligned_user, color='#ff7f0e', lw=0.6)
    axes[1].set_title(f'{user_label} — Predicted EGG (DTW aligned)',
                      fontsize=12, fontweight='bold', pad=8)
    axes[1].set_ylabel('Amplitude', fontsize=10)
    axes[1].axvspan(zoom_start, zoom_end, alpha=0.12, color='red', label='Zoom region')
    axes[1].legend(loc='upper right', fontsize=9)
    axes[1].grid(True, alpha=0.2)

    # Overlay Zoom
    axes[2].plot(t_zoom, aligned_ref[zoom_start:zoom_end], color='#1f77b4',
                 lw=2.0, label=f'{ref_label}')
    axes[2].plot(t_zoom, aligned_user[zoom_start:zoom_end], color='#ff7f0e',
                 lw=2.0, alpha=0.85, label=f'{user_label}')

    # 줌 구간 local corr
    seg_r = aligned_ref[zoom_start:zoom_end]
    seg_u = aligned_user[zoom_start:zoom_end]
    if np.std(seg_r) > 1e-8 and np.std(seg_u) > 1e-8:
        local_corr, _ = pearsonr(seg_r, seg_u)
    else:
        local_corr = 0.0

    axes[2].set_title(f'Zoomed Overlay — Global Corr: {dtw_corr:.4f}, '
                      f'Local Corr: {local_corr:.4f}',
                      fontsize=12, fontweight='bold', pad=8)
    axes[2].set_xlabel('Aligned Sample Index', fontsize=11)
    axes[2].set_ylabel('Amplitude', fontsize=10)
    axes[2].legend(loc='upper right', fontsize=11, framealpha=0.9)
    axes[2].grid(True, alpha=0.2)

    plt.suptitle(f'Best DTW Match: {ref_label} vs {user_label} (Corr: {dtw_corr:.4f})',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  [OK] Image 2: {save_path}")


# ============================================================
# 리포트
# ============================================================
def write_dtw_report(results, save_path):
    sorted_pairs = sorted(results.items(), key=lambda x: x[1]['corr'], reverse=True)
    best_pair, best_res = sorted_pairs[0]
    best_corr = best_res['corr']

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write("=" * 65 + "\n")
        f.write("  DTW Time-Aligned Vocal Similarity Analysis\n")
        f.write("  Model: Exp3 (EfficientEGGNet, Test Corr: 0.7163)\n")
        f.write("=" * 65 + "\n\n")

        # 비교 표
        f.write("Comparison Results:\n")
        f.write("-" * 65 + "\n")
        f.write(f"{'Pair':30s} | {'Raw Corr':>9s} | {'DTW Corr':>9s} | "
                f"{'DTW Dist':>10s} | {'Time':>6s}\n")
        f.write("-" * 65 + "\n")

        for (rl, ul), res in sorted(results.items()):
            raw = RAW_CORRS.get((rl, ul), 0.0)
            f.write(f"{rl + ' vs ' + ul:30s} | {raw:>9.4f} | "
                    f"{res['corr']:>9.4f} | {res['dtw_dist']:>10.1f} | "
                    f"{res['dtw_time']:>5.1f}s\n")

        f.write("-" * 65 + "\n\n")

        # Windowed correlation
        f.write("Windowed Correlation (segment-wise stability):\n")
        f.write("-" * 65 + "\n")
        f.write(f"{'Pair':30s} | {'Global':>9s} | {'Windowed':>9s}\n")
        f.write("-" * 65 + "\n")
        for (rl, ul), res in sorted(results.items()):
            f.write(f"{rl + ' vs ' + ul:30s} | {res['corr']:>9.4f} | "
                    f"{res['windowed_corr']:>9.4f}\n")
        f.write("-" * 65 + "\n\n")

        f.write(f"Best match: {best_pair[0]} vs {best_pair[1]}\n")
        f.write(f"  DTW Correlation: {best_corr:.4f}\n")
        f.write(f"  Windowed Corr:   {best_res['windowed_corr']:.4f}\n")
        f.write(f"  DTW Distance:    {best_res['dtw_dist']:.1f}\n")
        f.write(f"  Aligned length:  {best_res['n_aligned']:,} samples\n\n")

        f.write("Interpretation:\n")
        f.write("-" * 65 + "\n")
        f.write("  >= 0.7  : Very similar vocal pattern\n")
        f.write("  0.5~0.7 : Similar vocal pattern\n")
        f.write("  0.3~0.5 : Moderately similar\n")
        f.write("  < 0.3   : Different vocal pattern\n\n")

        if best_corr >= 0.7:
            interp = "Very similar vocal pattern"
        elif best_corr >= 0.5:
            interp = "Similar vocal pattern"
        elif best_corr >= 0.3:
            interp = "Moderately similar"
        else:
            interp = "Different vocal pattern"

        f.write(f"Conclusion: {best_pair[0]} vs {best_pair[1]}\n")
        f.write(f"  => {interp} (corr={best_corr:.4f})\n")
        f.write("=" * 65 + "\n")

    print(f"  [OK] Report: {save_path}")


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print("=" * 65)
    print("  DTW Time-Aligned Vocal Similarity Analysis")
    print("=" * 65)

    # ── 1. Load model & predict EGG ──
    print("\n[1] Loading model & predicting EGG...")
    model = load_model(device)

    ref_eggs = {}
    user_eggs = {}
    for fname, label in REF_FILES:
        audio, _ = preprocess_wav(os.path.join(REC_DIR, fname), TARGET_SR)
        egg = predict_egg(model, audio, device)
        ref_eggs[label] = egg
        print(f"  {label}: {len(audio):,} -> EGG {len(egg):,}")

    for fname, label in USER_FILES:
        audio, _ = preprocess_wav(os.path.join(REC_DIR, fname), TARGET_SR)
        egg = predict_egg(model, audio, device)
        user_eggs[label] = egg
        print(f"  {label}: {len(audio):,} -> EGG {len(egg):,}")

    # ── 2. DTW alignment & correlation ──
    print("\n[2] DTW alignment & correlation...")
    results = {}
    for _, rl in REF_FILES:
        for _, ul in USER_FILES:
            print(f"  {rl} vs {ul}...", end=" ", flush=True)
            res = compute_dtw_correlation(ref_eggs[rl], user_eggs[ul],
                                          downsample_factor=50)
            results[(rl, ul)] = res
            raw = RAW_CORRS.get((rl, ul), 0.0)
            print(f"Raw={raw:.4f} -> DTW={res['corr']:.4f} "
                  f"(dist={res['dtw_dist']:.0f}, {res['dtw_time']:.1f}s)")

    # ── 3. Summary ──
    print("\n[3] Results Summary:")
    print(f"  {'Pair':30s}  {'Raw':>8s}  {'DTW':>8s}  {'Delta':>8s}")
    print("  " + "-" * 60)
    for (rl, ul), res in sorted(results.items()):
        raw = RAW_CORRS.get((rl, ul), 0.0)
        delta = res['corr'] - raw
        marker = " ***" if res['corr'] == max(r['corr'] for r in results.values()) else ""
        print(f"  {rl + ' vs ' + ul:30s}  {raw:>8.4f}  {res['corr']:>8.4f}  "
              f"{delta:>+8.4f}{marker}")

    best_pair = max(results, key=lambda k: results[k]['corr'])
    best = results[best_pair]
    print(f"\n  Best: {best_pair[0]} vs {best_pair[1]} = {best['corr']:.4f}")

    # ── 4. Visualization ──
    print("\n[4] Generating visualizations...")
    plot_alignment_comparison(results, ref_eggs, user_eggs,
                              os.path.join(OUT_DIR, 'dtw_alignment_comparison.png'))
    plot_dtw_best_match(results,
                        os.path.join(OUT_DIR, 'dtw_best_match.png'))

    # ── 5. Report ──
    print("\n[5] Writing report...")
    write_dtw_report(results, os.path.join(OUT_DIR, 'dtw_similarity_report.txt'))

    # ── Done ──
    print(f"\n{'=' * 65}")
    print("  Analysis complete!")
    print(f"{'=' * 65}")
    print(f"\n  Output files:")
    print(f"    1. {OUT_DIR}/dtw_alignment_comparison.png")
    print(f"    2. {OUT_DIR}/dtw_best_match.png")
    print(f"    3. {OUT_DIR}/dtw_similarity_report.txt")
    print(f"{'=' * 65}")


if __name__ == '__main__':
    main()
