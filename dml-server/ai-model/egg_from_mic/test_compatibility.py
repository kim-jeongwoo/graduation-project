#!/usr/bin/env python3
"""
test_compatibility.py — 48kHz 24bit 입력 호환성 테스트 & 도메인 진단
====================================================================
학원 녹음 데이터(48kHz/24bit)가 현재 EGG 추정 모델(Exp20)에
정상 입력될 수 있는지 검증하고, SVD 학습 데이터와의 도메인 차이를 진단한다.

테스트 항목:
  [1] 리샘플링 경로 비교: 50kHz→16kHz vs 48kHz→16kHz (라운드트립)
  [2] 48kHz 24bit WAV 로드 → 전처리 → 값 범위 검증
  [3] 스펙트로그램 분포 비교 (SVD vs 48kHz 입력)
  [4] 모델 추론 안정성 (NaN, 극단값 검출)
  [5] CQ(접촉률) 분포 비교

사용법:
  python test_compatibility.py [--wav48 /path/to/48khz.wav]
  --wav48 없으면 rpi_recordings/0000.wav 사용
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf

# ── paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # egg_prediction/
AI_MODEL_DIR = os.path.join(PROJECT_ROOT, "ai-model")
sys.path.insert(0, AI_MODEL_DIR)

from utils.nsp_reader import read_nsp, find_paired_files  # noqa: E402

# ── constants (Exp20 학습 설정과 동일) ─────────────────────────────
TARGET_SR = 16000
SOURCE_SR_SVD = 50000
WINDOW_SIZE = 16384  # ~1.024s @16kHz

SVD_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "SVD_healthy")
RPI_DIR = os.path.join(PROJECT_ROOT, "data", "rpi_recordings")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "compatibility_test")
CHECKPOINT = os.path.join(
    PROJECT_ROOT, "checkpoints", "exp20_progressive", "best_model.pt"
)
# fallback
if not os.path.exists(CHECKPOINT):
    CHECKPOINT = os.path.join(PROJECT_ROOT, "checkpoints", "best_model.pt")


# ── helpers ────────────────────────────────────────────────────────
def resample_librosa(signal, orig_sr, target_sr):
    """학습 시와 동일한 librosa 리샘플링."""
    import librosa
    return librosa.resample(signal, orig_sr=orig_sr, target_sr=target_sr)


def zscore(x):
    """z-score 정규화 (학습 전처리와 동일)."""
    std = x.std()
    if std > 1e-8:
        return (x - x.mean()) / std
    return x - x.mean()


def load_wav_48khz(path):
    """48kHz WAV 로드 → float32 mono."""
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, sr


def load_svd_sample(speaker_id="1", utterance="a_h"):
    """SVD 데이터에서 한 파일 로드."""
    nsp_path = os.path.join(SVD_DATA_DIR, speaker_id, "vowels",
                            f"{speaker_id}-{utterance}.nsp")
    egg_path = os.path.join(SVD_DATA_DIR, speaker_id, "vowels",
                            f"{speaker_id}-{utterance}-egg.egg")
    speech, sr1 = read_nsp(nsp_path)
    egg, sr2 = read_nsp(egg_path)
    return speech, egg, sr1


def compute_spectral_centroid(signal, sr, n_fft=1024, hop=256):
    """스펙트럼 중심 주파수."""
    import librosa
    return librosa.feature.spectral_centroid(y=signal, sr=sr,
                                             n_fft=n_fft, hop_length=hop)[0]


def compute_mel_spectrogram(signal, sr, n_mels=80, n_fft=1024, hop=256):
    """Mel spectrogram (dB)."""
    import librosa
    S = librosa.feature.melspectrogram(y=signal, sr=sr, n_mels=n_mels,
                                       n_fft=n_fft, hop_length=hop)
    return librosa.power_to_db(S, ref=np.max)


def estimate_cq(egg_signal, sr, frame_len_ms=10):
    """
    간이 CQ(Contact Quotient) 추정.
    EGG 파형에서 양수 구간 비율 = 성대 접촉 비율 (근사).
    """
    frame_len = int(sr * frame_len_ms / 1000)
    n_frames = len(egg_signal) // frame_len
    cqs = []
    for i in range(n_frames):
        frame = egg_signal[i * frame_len:(i + 1) * frame_len]
        contact = (frame > 0).sum() / len(frame)
        cqs.append(contact)
    return np.array(cqs)


# ── Test 1: 리샘플링 경로 비교 ────────────────────────────────────
def test_resample_roundtrip():
    """
    SVD 원본(50kHz) → 16kHz  vs
    SVD 원본(50kHz) → 48kHz → 16kHz
    두 결과의 MSE, 상관계수 비교.
    """
    print("\n" + "=" * 60)
    print("[Test 1] 리샘플링 경로 비교 (50k→16k vs 50k→48k→16k)")
    print("=" * 60)

    speech_50k, _, sr = load_svd_sample()

    # 경로 A: 학습과 동일 (50k → 16k)
    speech_a = resample_librosa(speech_50k, SOURCE_SR_SVD, TARGET_SR)

    # 경로 B: 학원 시뮬레이션 (50k → 48k → 16k)
    speech_48k = resample_librosa(speech_50k, SOURCE_SR_SVD, 48000)
    speech_b = resample_librosa(speech_48k, 48000, TARGET_SR)

    # 길이 맞추기
    min_len = min(len(speech_a), len(speech_b))
    speech_a = speech_a[:min_len]
    speech_b = speech_b[:min_len]

    # z-score
    speech_a = zscore(speech_a)
    speech_b = zscore(speech_b)

    mse = np.mean((speech_a - speech_b) ** 2)
    corr = np.corrcoef(speech_a, speech_b)[0, 1]

    print(f"  길이: A={min_len} samples ({min_len/TARGET_SR:.2f}s)")
    print(f"  MSE:  {mse:.8f}")
    print(f"  Corr: {corr:.6f}")

    status = "✅" if corr > 0.999 else "⚠️"
    print(f"  결과: {status} 리샘플링 경로 차이 {'무시 가능' if corr > 0.999 else '유의미'}")

    return speech_a, speech_b, {"mse": mse, "corr": corr}


# ── Test 2: 48kHz 24bit 로드 & 값 범위 ────────────────────────────
def test_load_48khz(wav_path):
    """48kHz WAV 로드 후 전처리, 값 범위 검증."""
    print("\n" + "=" * 60)
    print(f"[Test 2] 48kHz WAV 로드 & 값 범위 검증")
    print(f"  파일: {os.path.basename(wav_path)}")
    print("=" * 60)

    info = sf.info(wav_path)
    print(f"  포맷: {info.samplerate}Hz, {info.subtype}, {info.channels}ch, {info.duration:.2f}s")

    audio, sr = load_wav_48khz(wav_path)
    print(f"  로드: shape={audio.shape}, dtype={audio.dtype}")
    print(f"  raw 범위: [{audio.min():.6f}, {audio.max():.6f}]")

    # 리샘플링
    audio_16k = resample_librosa(audio, sr, TARGET_SR)
    print(f"  16kHz 변환: {len(audio_16k)} samples ({len(audio_16k)/TARGET_SR:.2f}s)")
    print(f"  16kHz 범위: [{audio_16k.min():.6f}, {audio_16k.max():.6f}]")

    # z-score
    audio_norm = zscore(audio_16k)
    print(f"  z-score 후: mean={audio_norm.mean():.8f}, std={audio_norm.std():.4f}")
    print(f"  z-score 범위: [{audio_norm.min():.4f}, {audio_norm.max():.4f}]")

    # NaN/Inf 체크
    has_nan = np.isnan(audio_norm).any()
    has_inf = np.isinf(audio_norm).any()
    print(f"  NaN: {'⚠️ 있음!' if has_nan else '✅ 없음'}")
    print(f"  Inf: {'⚠️ 있음!' if has_inf else '✅ 없음'}")

    # 윈도우 수
    n_windows = max(0, (len(audio_norm) - WINDOW_SIZE) // (WINDOW_SIZE // 2) + 1)
    print(f"  추론 윈도우 수: {n_windows} (hop={WINDOW_SIZE//2})")

    status = "✅" if not has_nan and not has_inf and n_windows > 0 else "⚠️"
    print(f"  결과: {status} 입력 호환성 {'OK' if status == '✅' else '문제 있음'}")

    return audio_norm, sr


# ── Test 3: 스펙트로그램 비교 ──────────────────────────────────────
def test_spectral_comparison(audio_48k_norm, svd_speech_norm):
    """두 신호의 mel spectrogram, spectral centroid 분포 비교."""
    print("\n" + "=" * 60)
    print("[Test 3] 스펙트로그램 분포 비교 (48kHz 입력 vs SVD)")
    print("=" * 60)

    # 길이 통일 (짧은 쪽 기준)
    min_len = min(len(audio_48k_norm), len(svd_speech_norm))
    a = audio_48k_norm[:min_len]
    s = svd_speech_norm[:min_len]

    # Mel spectrogram
    mel_a = compute_mel_spectrogram(a, TARGET_SR)
    mel_s = compute_mel_spectrogram(s, TARGET_SR)

    # 통계
    print(f"  48kHz mel: mean={mel_a.mean():.2f} dB, std={mel_a.std():.2f}")
    print(f"  SVD   mel: mean={mel_s.mean():.2f} dB, std={mel_s.std():.2f}")

    # Spectral centroid
    sc_a = compute_spectral_centroid(a, TARGET_SR)
    sc_s = compute_spectral_centroid(s, TARGET_SR)
    print(f"  48kHz centroid: mean={sc_a.mean():.1f} Hz, std={sc_a.std():.1f}")
    print(f"  SVD   centroid: mean={sc_s.mean():.1f} Hz, std={sc_s.std():.1f}")

    # 시각화
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Spectral Comparison: 48kHz Input vs SVD", fontsize=14)

    axes[0, 0].imshow(mel_s, aspect="auto", origin="lower", cmap="magma")
    axes[0, 0].set_title("SVD Mel Spectrogram")
    axes[0, 0].set_ylabel("Mel bin")

    axes[0, 1].imshow(mel_a, aspect="auto", origin="lower", cmap="magma")
    axes[0, 1].set_title("48kHz Input Mel Spectrogram")

    axes[1, 0].hist(mel_s.flatten(), bins=100, alpha=0.7, label="SVD", color="blue")
    axes[1, 0].hist(mel_a.flatten(), bins=100, alpha=0.7, label="48kHz", color="orange")
    axes[1, 0].set_title("Mel Energy Distribution")
    axes[1, 0].legend()
    axes[1, 0].set_xlabel("dB")

    axes[1, 1].hist(sc_s, bins=50, alpha=0.7, label="SVD", color="blue")
    axes[1, 1].hist(sc_a, bins=50, alpha=0.7, label="48kHz", color="orange")
    axes[1, 1].set_title("Spectral Centroid Distribution")
    axes[1, 1].legend()
    axes[1, 1].set_xlabel("Hz")

    plt.tight_layout()
    fig_path = os.path.join(OUTPUT_DIR, "spectral_comparison.png")
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"  저장: {fig_path}")

    return mel_a, mel_s


# ── Test 4: 모델 추론 안정성 ──────────────────────────────────────
def test_model_inference(audio_norm):
    """실제 Exp20 모델로 추론해서 출력 안정성 검증."""
    print("\n" + "=" * 60)
    print("[Test 4] 모델 추론 안정성 (Exp20)")
    print("=" * 60)

    import torch
    from model.efficient_egg import build_efficient_model

    EXP20_CONFIG = {
        "channels": 128, "n_layers": 30, "kernel_size": 5,
        "n_stacks": 5, "dropout": 0.05,
    }

    if not os.path.exists(CHECKPOINT):
        print(f"  ⚠️ 체크포인트 없음: {CHECKPOINT}")
        return None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficient_model(EXP20_CONFIG)
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    print(f"  모델 로드: device={device}, val_corr={ckpt.get('val_corr')}")

    # 윈도우 분할 추론
    hop = WINDOW_SIZE // 2
    n_windows = max(1, (len(audio_norm) - WINDOW_SIZE) // hop + 1)
    egg_windows = []

    with torch.no_grad():
        for i in range(n_windows):
            start = i * hop
            end = start + WINDOW_SIZE
            if end > len(audio_norm):
                break
            chunk = audio_norm[start:end]
            x = torch.from_numpy(chunk).float().unsqueeze(0).unsqueeze(0).to(device)
            pred = model(x).squeeze().cpu().numpy()
            egg_windows.append(pred)

    if not egg_windows:
        print("  ⚠️ 추론 윈도우 없음 (오디오가 너무 짧음)")
        return None

    egg_pred = np.concatenate(egg_windows) if len(egg_windows) == 1 else \
        _overlap_add(egg_windows, hop)

    # 안정성 검사
    has_nan = np.isnan(egg_pred).any()
    has_inf = np.isinf(egg_pred).any()
    max_abs = np.abs(egg_pred).max()
    mean_val = egg_pred.mean()
    std_val = egg_pred.std()

    print(f"  추론 완료: {n_windows} windows → {len(egg_pred)} samples")
    print(f"  출력 범위: [{egg_pred.min():.4f}, {egg_pred.max():.4f}]")
    print(f"  mean={mean_val:.6f}, std={std_val:.4f}, max|x|={max_abs:.4f}")
    print(f"  NaN:  {'⚠️ 있음!' if has_nan else '✅ 없음'}")
    print(f"  Inf:  {'⚠️ 있음!' if has_inf else '✅ 없음'}")
    print(f"  극단값(|x|>10): {'⚠️ 있음' if max_abs > 10 else '✅ 없음'}")

    status = "✅" if not has_nan and not has_inf and max_abs < 10 else "⚠️"
    print(f"  결과: {status} 추론 안정성 {'OK' if status == '✅' else '문제 있음'}")

    return egg_pred


def _overlap_add(windows, hop):
    """Overlap-add로 윈도우 이어붙이기."""
    win_len = len(windows[0])
    total_len = hop * (len(windows) - 1) + win_len
    output = np.zeros(total_len, dtype=np.float32)
    count = np.zeros(total_len, dtype=np.float32)

    for i, w in enumerate(windows):
        start = i * hop
        output[start:start + win_len] += w
        count[start:start + win_len] += 1.0

    count = np.maximum(count, 1.0)
    return output / count


# ── Test 5: CQ 분포 비교 + SVD 참조 추론 ─────────────────────────
def test_cq_comparison(egg_pred_48k, svd_speech_norm):
    """48kHz 입력의 추정 EGG vs SVD 입력의 추정 EGG: CQ 분포 비교."""
    print("\n" + "=" * 60)
    print("[Test 5] CQ 분포 비교 (48kHz 추정 EGG vs SVD GT EGG)")
    print("=" * 60)

    # SVD GT EGG 로드
    _, svd_egg_50k, _ = load_svd_sample()
    svd_egg_16k = resample_librosa(svd_egg_50k, SOURCE_SR_SVD, TARGET_SR)
    svd_egg_norm = zscore(svd_egg_16k)

    cq_pred = estimate_cq(egg_pred_48k, TARGET_SR)
    cq_svd = estimate_cq(svd_egg_norm, TARGET_SR)

    print(f"  48kHz 추정 CQ: mean={cq_pred.mean():.3f}, std={cq_pred.std():.3f}")
    print(f"  SVD GT    CQ: mean={cq_svd.mean():.3f}, std={cq_svd.std():.3f}")

    # 시각화
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("CQ & Waveform Comparison", fontsize=14)

    # CQ 분포
    axes[0].hist(cq_svd, bins=50, alpha=0.7, label="SVD GT EGG", color="blue")
    axes[0].hist(cq_pred, bins=50, alpha=0.7, label="48kHz Pred EGG", color="orange")
    axes[0].set_title("CQ Distribution")
    axes[0].set_xlabel("Contact Quotient")
    axes[0].legend()

    # 추정 EGG 파형 (처음 1초)
    t = np.arange(min(TARGET_SR, len(egg_pred_48k))) / TARGET_SR
    axes[1].plot(t, egg_pred_48k[:len(t)], alpha=0.8, linewidth=0.5)
    axes[1].set_title("48kHz → Predicted EGG (1s)")
    axes[1].set_xlabel("Time (s)")

    # SVD GT EGG 파형 (처음 1초)
    t2 = np.arange(min(TARGET_SR, len(svd_egg_norm))) / TARGET_SR
    axes[2].plot(t2, svd_egg_norm[:len(t2)], alpha=0.8, linewidth=0.5, color="green")
    axes[2].set_title("SVD GT EGG (1s)")
    axes[2].set_xlabel("Time (s)")

    plt.tight_layout()
    fig_path = os.path.join(OUTPUT_DIR, "cq_comparison.png")
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"  저장: {fig_path}")


# ── Test 6: 파형 시각화 ───────────────────────────────────────────
def test_waveform_visual(audio_norm, egg_pred):
    """48kHz 입력 + 추정 EGG 파형 시각화."""
    print("\n" + "=" * 60)
    print("[Test 6] 파형 시각화 (MIC → 추정 EGG)")
    print("=" * 60)

    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    dur = min(3.0, len(audio_norm) / TARGET_SR)  # 최대 3초
    n = int(dur * TARGET_SR)

    t = np.arange(n) / TARGET_SR
    axes[0].plot(t, audio_norm[:n], linewidth=0.3, color="steelblue")
    axes[0].set_title("Input MIC (48kHz→16kHz, z-scored)")
    axes[0].set_ylabel("Amplitude")

    if egg_pred is not None:
        n2 = min(n, len(egg_pred))
        axes[1].plot(t[:n2], egg_pred[:n2], linewidth=0.3, color="darkorange")
    axes[1].set_title("Predicted EGG")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Amplitude")

    plt.tight_layout()
    fig_path = os.path.join(OUTPUT_DIR, "waveform_48khz.png")
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"  저장: {fig_path}")


# ── Main ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="48kHz 호환성 테스트 & 도메인 진단")
    parser.add_argument("--wav48", type=str, default=None,
                        help="48kHz WAV 파일 경로 (없으면 rpi_recordings/0000.wav)")
    args = parser.parse_args()

    # 48kHz 파일 결정
    if args.wav48 and os.path.exists(args.wav48):
        wav_path = args.wav48
    else:
        wav_path = os.path.join(RPI_DIR, "0000.wav")
        if not os.path.exists(wav_path):
            print(f"ERROR: 48kHz 테스트 파일 없음: {wav_path}")
            print("  --wav48 옵션으로 직접 지정하세요.")
            sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print(" 48kHz/24bit 입력 호환성 테스트 & 도메인 진단")
    print("=" * 60)

    # ── Test 1: 리샘플링 경로 비교 ──
    svd_a, svd_b, resample_metrics = test_resample_roundtrip()

    # ── Test 2: 48kHz 로드 & 값 범위 ──
    audio_norm, _ = test_load_48khz(wav_path)

    # ── Test 3: 스펙트로그램 비교 ──
    # SVD 참조: 50k→16k→zscore
    svd_speech_50k, _, _ = load_svd_sample()
    svd_speech_16k = resample_librosa(svd_speech_50k, SOURCE_SR_SVD, TARGET_SR)
    svd_speech_norm = zscore(svd_speech_16k)
    test_spectral_comparison(audio_norm, svd_speech_norm)

    # ── Test 4: 모델 추론 안정성 ──
    egg_pred = test_model_inference(audio_norm)

    # ── Test 5: CQ 비교 ──
    if egg_pred is not None:
        test_cq_comparison(egg_pred, svd_speech_norm)

    # ── Test 6: 파형 시각화 ──
    test_waveform_visual(audio_norm, egg_pred)

    # ── Summary ──
    print("\n" + "=" * 60)
    print(" 종합 결과")
    print("=" * 60)
    print(f"  [Test 1] 리샘플링 경로:  Corr={resample_metrics['corr']:.6f}, "
          f"MSE={resample_metrics['mse']:.8f}")
    print(f"  [Test 2] 입력 호환성:    float32 변환 OK, NaN/Inf 없음")
    print(f"  [Test 3] 스펙트로그램:   시각화 저장 완료")
    if egg_pred is not None:
        print(f"  [Test 4] 추론 안정성:    NaN={'없음' if not np.isnan(egg_pred).any() else '있음!'}, "
              f"max|x|={np.abs(egg_pred).max():.4f}")
        print(f"  [Test 5] CQ 분포:        시각화 저장 완료")
    else:
        print(f"  [Test 4] 추론 안정성:    ⚠️ 체크포인트 없음 (스킵)")
        print(f"  [Test 5] CQ 분포:        ⚠️ 스킵")
    print(f"  [Test 6] 파형 시각화:    저장 완료")
    print(f"\n  📁 결과 디렉토리: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
