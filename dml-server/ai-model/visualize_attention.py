#!/usr/bin/env python3
"""
WaveNetEGG의 Self-Attention Weights 시각화
============================================
WaveNetEGG 모델은 nn.MultiheadAttention 레이어를 포함.
실제 학습된 모델에서 Attention Weights를 추출하고 시각화.

생성 이미지:
  1. attention_distribution_sampleN.png - Raw Scores vs Softmax 확률 분포
  2. attention_heatmap_sampleN.png      - 전체 시점 간 Attention Heatmap
  3. attention_on_signal_sampleN.png    - EGG 신호 + Attention 집중 영역
"""
import os
import sys
import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# 한글 폰트
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if os.path.exists(FONT_PATH):
    fprop = fm.FontProperties(fname=FONT_PATH, size=14)
    fprop_s = fm.FontProperties(fname=FONT_PATH, size=10)
    fprop_l = fm.FontProperties(fname=FONT_PATH, size=12)
    fprop_t = fm.FontProperties(fname=FONT_PATH, size=16)
else:
    fprop = fprop_s = fprop_l = fprop_t = None

PROJECT_DIR = os.path.expanduser('~/projects/egg_prediction')
sys.path.insert(0, os.path.join(PROJECT_DIR, 'ai-model'))

from model.wavenet_egg import build_model
from utils.nsp_reader import read_nsp, find_paired_files

# ============================================================
# 설정
# ============================================================
CKPT_PATH = os.path.join(PROJECT_DIR, 'checkpoints/best_model.pt')
SVD_PATH = os.path.join(PROJECT_DIR, 'data/SVD_healthy')
SAVE_DIR = os.path.join(PROJECT_DIR, 'results/attention_analysis')
os.makedirs(SAVE_DIR, exist_ok=True)

# baseline config (체크포인트에서 확인됨)
MODEL_CONFIG = {
    'layers': 8,
    'channels': 32,
    'kernel_size': 3,
    'use_attention': True,
    'dropout': 0.5,
}
WINDOW_LENGTH = 192
TARGET_SR = 16000
SOURCE_SR = 50000


def stitle(ax, text, fp=None, **kw):
    ax.set_title(text, fontproperties=fp, **kw) if fp else ax.set_title(text, **kw)

def slabel(ax, axis, text, fp=None, **kw):
    getattr(ax, f'set_{axis}label')(text, fontproperties=fp, **kw) if fp else getattr(ax, f'set_{axis}label')(text, **kw)


# ============================================================
# 1. 모델 로드
# ============================================================
def load_model():
    model = build_model(MODEL_CONFIG)
    ckpt = torch.load(CKPT_PATH, map_location='cpu', weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    print(f"모델 로드 완료: {model.count_params():,} params")
    print(f"  Epoch: {ckpt.get('epoch', '?')}, Val Corr: {ckpt.get('val_corr', '?')}")
    return model


# ============================================================
# 2. 테스트 데이터 로드
# ============================================================
def load_test_samples(n_samples=3):
    import librosa

    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))

    rng = np.random.RandomState(42)
    shuffled = list(all_speakers)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    test_speakers = set(shuffled[n_train + n_val:])
    test_pairs = [(n_, e_, s_) for n_, e_, s_ in pairs if s_ in test_speakers]

    print(f"테스트 화자: {len(test_speakers)}명, 파일: {len(test_pairs)}개")

    samples = []
    for nsp_path, egg_path, speaker_id in test_pairs:
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)

            min_len = min(len(speech), len(egg))
            speech = speech[:min_len]
            egg = egg[:min_len]

            speech = librosa.resample(speech, orig_sr=SOURCE_SR, target_sr=TARGET_SR)
            egg = librosa.resample(egg, orig_sr=SOURCE_SR, target_sr=TARGET_SR)

            min_len = min(len(speech), len(egg))
            speech = speech[:min_len]
            egg = egg[:min_len]

            if min_len < WINDOW_LENGTH:
                continue

            s_std, e_std = speech.std(), egg.std()
            if s_std > 1e-8:
                speech = (speech - speech.mean()) / s_std
            if e_std > 1e-8:
                egg = (egg - egg.mean()) / e_std

            center = min_len // 2
            start = max(0, center - WINDOW_LENGTH // 2)
            end = start + WINDOW_LENGTH

            samples.append({
                'mic': speech[start:end],
                'egg': egg[start:end],
                'speaker': speaker_id,
                'file': os.path.basename(nsp_path),
            })

            if len(samples) >= n_samples:
                break
        except Exception as e:
            continue

    print(f"로드 완료: {len(samples)}개 샘플")
    return samples


# ============================================================
# 3. Attention Weights 추출 (forward hook)
# ============================================================
def extract_attention_weights(model, mic_tensor):
    """
    SelfAttentionBlock 내부의 nn.MultiheadAttention에서
    attention weights를 추출.
    """
    attn_weights = {}

    def attn_hook(module, input, output):
        x = input[0]  # [B, C, T]
        x_t = x.permute(0, 2, 1)  # [B, T, C]
        normed = module.norm(x_t)
        _, weights = module.attn(normed, normed, normed, need_weights=True,
                                 average_attn_weights=False)
        attn_weights['raw'] = weights.detach().cpu()  # [B, num_heads, T, T]

    hook = model.attention.register_forward_hook(attn_hook)

    with torch.no_grad():
        pred = model(mic_tensor)

    hook.remove()

    return attn_weights.get('raw', None), pred.detach().cpu()


# ============================================================
# 시각화 1: Attention 확률 분포 (head별)
# ============================================================
def visualize_attention_distribution(attn_w, mic, egg, pred, sample_info, save_path):
    attn = attn_w[0].numpy()  # [num_heads, T, T]
    n_heads, T, _ = attn.shape
    mid = T // 2
    time_ms = np.linspace(0, WINDOW_LENGTH / TARGET_SR * 1000, T)

    fig, axes = plt.subplots(n_heads + 1, 1, figsize=(14, 3 * (n_heads + 1)))

    for h in range(n_heads):
        ax = axes[h]
        attention_at_mid = attn[h, mid, :]
        colors = plt.cm.Reds(attention_at_mid / (attention_at_mid.max() + 1e-10))
        ax.bar(time_ms, attention_at_mid, color=colors, edgecolor='gray',
               linewidth=0.3, width=time_ms[1] - time_ms[0])
        ax.axvline(x=time_ms[mid], color='blue', linestyle='--', linewidth=1.5, alpha=0.7)
        stitle(ax, f'Head {h}: Attention Weights (시점 {mid}에서 → 다른 시점)', fprop_l)
        slabel(ax, 'y', 'Weight', fprop_s)

        top3 = np.argsort(attention_at_mid)[-3:]
        for idx in top3:
            ax.annotate(f'{attention_at_mid[idx]:.1%}',
                        xy=(time_ms[idx], attention_at_mid[idx]),
                        xytext=(0, 5), textcoords='offset points',
                        ha='center', fontsize=8, color='darkred', fontweight='bold')

    ax = axes[n_heads]
    avg_attn = attn[:, mid, :].mean(axis=0)
    colors = plt.cm.Reds(avg_attn / (avg_attn.max() + 1e-10))
    ax.bar(time_ms, avg_attn, color=colors, edgecolor='gray',
           linewidth=0.3, width=time_ms[1] - time_ms[0])
    ax.axvline(x=time_ms[mid], color='blue', linestyle='--', linewidth=1.5, alpha=0.7)
    stitle(ax, f'평균 Attention (합계={avg_attn.sum():.3f}) — Speaker: {sample_info["speaker"]}', fprop)
    slabel(ax, 'y', 'Weight', fprop_s)
    slabel(ax, 'x', 'Time (ms)', fprop_s)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  저장: {save_path}")


# ============================================================
# 시각화 2: Attention Heatmap (head별 + 평균)
# ============================================================
def visualize_attention_heatmap(attn_w, sample_info, save_path):
    attn = attn_w[0].numpy()  # [num_heads, T, T]
    n_heads = attn.shape[0]
    time_ms_max = WINDOW_LENGTH / TARGET_SR * 1000

    fig, axes = plt.subplots(1, n_heads + 1, figsize=(5 * (n_heads + 1), 5))

    for h in range(n_heads):
        ax = axes[h]
        im = ax.imshow(attn[h], cmap='hot', aspect='auto',
                       extent=[0, time_ms_max, time_ms_max, 0])
        stitle(ax, f'Head {h}', fprop_l)
        slabel(ax, 'x', 'Key (ms)', fprop_s)
        if h == 0:
            slabel(ax, 'y', 'Query (ms)', fprop_s)
        plt.colorbar(im, ax=ax, shrink=0.7)

    ax = axes[n_heads]
    avg = attn.mean(axis=0)
    im = ax.imshow(avg, cmap='hot', aspect='auto',
                   extent=[0, time_ms_max, time_ms_max, 0])
    stitle(ax, '평균 Attention', fprop)
    slabel(ax, 'x', 'Key (ms)', fprop_s)
    plt.colorbar(im, ax=ax, shrink=0.7)

    fig.suptitle(f'Self-Attention Heatmap (밝을수록 높은 attention) — Speaker: {sample_info["speaker"]}',
                 fontproperties=fprop_t if fprop_t else None, y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  저장: {save_path}")


# ============================================================
# 시각화 3: EGG 신호 + Attention 집중 영역
# ============================================================
def visualize_attention_on_signal(attn_w, mic, egg, pred, sample_info, save_path):
    attn = attn_w[0].numpy()  # [num_heads, T, T]
    T = attn.shape[1]
    time_ms = np.linspace(0, WINDOW_LENGTH / TARGET_SR * 1000, WINDOW_LENGTH)
    attn_time_ms = np.linspace(0, WINDOW_LENGTH / TARGET_SR * 1000, T)

    attention_received = attn.mean(axis=(0, 1))  # [T]

    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # (1) MIC + Attention 하이라이트
    ax = axes[0]
    ax.plot(time_ms, mic, 'b-', linewidth=0.8, alpha=0.7)
    high_attn_interp = np.interp(time_ms, attn_time_ms, attention_received)
    threshold = np.percentile(high_attn_interp, 70)
    ax.fill_between(time_ms, mic.min() * 1.1, mic.max() * 1.1,
                    where=high_attn_interp > threshold,
                    alpha=0.3, color='red', label='High Attention (>70th pctl)')
    stitle(ax, f'MIC Input + Attention 집중 영역 (Speaker: {sample_info["speaker"]})', fprop)
    slabel(ax, 'y', 'Amplitude', fprop_l)
    ax.legend(prop=fprop_s if fprop_s else {})
    ax.set_xlim(0, time_ms[-1])

    # (2) EGG: 실제 vs 예측
    ax = axes[1]
    pred_np = pred.squeeze().numpy()
    ax.plot(time_ms, egg, 'g-', linewidth=0.8, alpha=0.7, label='Real EGG')
    ax.plot(time_ms, pred_np, 'r-', linewidth=0.8, alpha=0.7, label='Predicted EGG')
    ax.fill_between(time_ms, egg.min() * 1.1, egg.max() * 1.1,
                    where=high_attn_interp > threshold,
                    alpha=0.2, color='red', label='High Attention')
    stitle(ax, 'EGG 예측 + Attention 하이라이트', fprop)
    slabel(ax, 'y', 'Amplitude', fprop_l)
    ax.legend(prop=fprop_s if fprop_s else {})
    ax.set_xlim(0, time_ms[-1])

    # (3) Attention 분포
    ax = axes[2]
    ax.fill_between(attn_time_ms, 0, attention_received, alpha=0.7, color='coral')
    ax.plot(attn_time_ms, attention_received, 'r-', linewidth=1)
    ax.axhline(y=threshold, color='black', linestyle='--', linewidth=0.8, alpha=0.5,
               label=f'70th pctl = {threshold:.4f}')
    stitle(ax, 'Attention 분포 (각 시점이 얼마나 주목받는가)', fprop)
    slabel(ax, 'y', 'Mean Attention', fprop_l)
    slabel(ax, 'x', 'Time (ms)', fprop_l)
    ax.legend(prop=fprop_s if fprop_s else {})
    ax.set_xlim(0, time_ms[-1])

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  저장: {save_path}")


# ============================================================
# 메인
# ============================================================
def main():
    print("=" * 60)
    print("WaveNetEGG Self-Attention Weights 시각화")
    print("=" * 60)

    model = load_model()
    samples = load_test_samples(n_samples=3)

    if not samples:
        print("테스트 샘플 없음.")
        return

    for i, sample in enumerate(samples):
        print(f"\n--- Sample {i} (Speaker: {sample['speaker']}, File: {sample['file']}) ---")

        mic = sample['mic']
        egg = sample['egg']
        mic_tensor = torch.from_numpy(mic).float().unsqueeze(0).unsqueeze(0)

        print("  Attention weights 추출 중...")
        attn_w, pred = extract_attention_weights(model, mic_tensor)

        if attn_w is None:
            print("  ⚠️ Attention weights를 추출할 수 없습니다.")
            continue

        print(f"  Attention shape: {attn_w.shape}")

        visualize_attention_distribution(
            attn_w, mic, egg, pred, sample,
            os.path.join(SAVE_DIR, f'attention_distribution_sample{i}.png')
        )

        visualize_attention_heatmap(
            attn_w, sample,
            os.path.join(SAVE_DIR, f'attention_heatmap_sample{i}.png')
        )

        visualize_attention_on_signal(
            attn_w, mic, egg, pred, sample,
            os.path.join(SAVE_DIR, f'attention_on_signal_sample{i}.png')
        )

    # 예시 이미지 삭제
    print("\n--- 예시 데이터 이미지 삭제 ---")
    for old_img in ['results/softmax_visualization.png', 'results/attention_focus_visualization.png']:
        full_path = os.path.join(PROJECT_DIR, old_img)
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"  삭제: {full_path}")
        else:
            print(f"  없음 (이미 삭제됨): {old_img}")

    print("\n" + "=" * 60)
    print(f"시각화 완료! 결과: {SAVE_DIR}/")
    print("=" * 60)
    generated = [f for f in os.listdir(SAVE_DIR) if f.endswith('.png')]
    for f in sorted(generated):
        full = os.path.join(SAVE_DIR, f)
        size_kb = os.path.getsize(full) / 1024
        print(f"  {full}  ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
