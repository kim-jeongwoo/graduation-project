#!/usr/bin/env python3
"""
졸업논문 시각화 생성 스크립트
==============================
- 논문 삽입용: 흰 배경, 한글 라벨, 300 DPI, 깔끔한 스타일
- 폰트: Noto Sans CJK KR
- 색상: 파랑(#2E75B6), 주황(#ED7D31), 회색(#AAAAAA)
"""
import sys, os, json, time
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import MaxNLocator
from collections import defaultdict

# ── 경로 설정 ──
PROJECT = os.path.expanduser('~/projects/egg_prediction')
FIGURES = os.path.join(PROJECT, 'figures')
RESULTS = os.path.join(PROJECT, 'results')
CHECKPOINT = os.path.join(PROJECT, 'checkpoints/exp20_progressive/best_model.pt')
SVD_PATH = os.path.join(PROJECT, 'data/SVD_healthy')
os.makedirs(FIGURES, exist_ok=True)

sys.path.insert(0, os.path.join(PROJECT, 'ai-model'))
from model.efficient_egg import build_efficient_model
from utils.dataset import speaker_split
from utils.nsp_reader import find_paired_files, read_nsp
import librosa

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ── 폰트 설정 ──
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_prop = fm.FontProperties(fname=FONT_PATH)
fm.fontManager.addfont(FONT_PATH)
plt.rcParams.update({
    'font.family': font_prop.get_name(),
    'font.size': 11,
    'axes.unicode_minus': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
    'axes.grid': False,
})

# 색상 팔레트
BLUE = '#2E75B6'
ORANGE = '#ED7D31'
GRAY = '#AAAAAA'
GREEN = '#4CAF50'
RED = '#E74C3C'

SR = 16000
WINDOW = 16384
HOP = 8192

EXP20_CFG = {'channels': 128, 'n_layers': 30, 'kernel_size': 5, 'n_stacks': 5, 'dropout': 0.05}


def pearson_corr(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float(np.sum(a * b) / (np.sqrt(np.sum(a**2) * np.sum(b**2)) + 1e-8))


# ================================================================
# 1-1. Ablation 구성요소별 성능 비교 막대그래프
# ================================================================
def fig_ablation_bar():
    print("[1-1] Ablation 비교 막대그래프 생성...")
    labels = [
        'Baseline\n(Causal WaveNet)',
        '+Non-causal\n+EfficientEGGNet',
        '+모델 확장\n+Window 8192',
        '+Mixup\n정규화',
        '+Progressive\nWindow (최종)',
    ]
    values = [0.6662, 0.7163, 0.7484, 0.7522, 0.8249]
    exps = ['Baseline', 'Exp3', 'Exp11', 'Exp15', 'Exp20']
    colors = [GRAY, GRAY, GRAY, GRAY, BLUE]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(values)), values, color=colors, width=0.6,
                  edgecolor='white', linewidth=1.5)
    bars[-1].set_color(BLUE)

    for i, (v, exp) in enumerate(zip(values, exps)):
        ax.text(i, v + 0.008, f'{v:.4f}', ha='center', va='bottom', fontsize=11,
                fontweight='bold', fontproperties=font_prop)
        ax.text(i, v - 0.015, f'({exp})', ha='center', va='top', fontsize=8,
                color='white', fontproperties=font_prop)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontproperties=font_prop, fontsize=9)
    ax.set_ylabel('테스트 상관계수 (Pearson r)', fontproperties=font_prop, fontsize=12)
    ax.set_title('Ablation Study: 구성요소별 성능 비교', fontproperties=font_prop,
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_ylim(0.6, 0.88)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=8))

    # 개선폭 화살표
    for i in range(1, len(values)):
        delta = values[i] - values[i-1]
        ax.annotate(f'+{delta:.3f}', xy=(i - 0.5, max(values[i], values[i-1]) + 0.025),
                    fontsize=8, ha='center', color=ORANGE, fontweight='bold',
                    fontproperties=font_prop)

    plt.tight_layout()
    path = os.path.join(FIGURES, 'ablation_comparison_bar.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ================================================================
# 1-2. Context Window 크기별 성능 변화 꺾은선 그래프
# ================================================================
def fig_context_window():
    print("[1-2] Context Window 성능 변화 그래프 생성...")
    # 데이터: window_ms → (test_corr, label)
    windows =      [12,       64,       256,      512,      1024]
    window_labels = ['192\n(12ms)', '1024\n(64ms)', '4096\n(256ms)', '8192\n(512ms)', '16384\n(1024ms)']
    corrs =        [0.6662,   0.6763,   0.7163,   0.7484,   0.8249]
    exps =         ['Baseline', 'Exp1b', 'Exp3',  'Exp11',  'Exp20']

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(len(corrs)), corrs, 'o-', color=BLUE, linewidth=2.5,
            markersize=10, markerfacecolor='white', markeredgewidth=2.5,
            markeredgecolor=BLUE, zorder=5)

    for i, (c, exp) in enumerate(zip(corrs, exps)):
        ax.text(i, c + 0.012, f'{c:.4f}\n({exp})', ha='center', va='bottom',
                fontsize=9, fontweight='bold', fontproperties=font_prop)

    ax.set_xticks(range(len(window_labels)))
    ax.set_xticklabels(window_labels, fontproperties=font_prop, fontsize=10)
    ax.set_xlabel('Context Window 크기 (샘플 수 / 시간)', fontproperties=font_prop, fontsize=12)
    ax.set_ylabel('테스트 상관계수 (Pearson r)', fontproperties=font_prop, fontsize=12)
    ax.set_title('Context Window 크기에 따른 EGG 추정 성능', fontproperties=font_prop,
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_ylim(0.62, 0.88)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Progressive 구간 음영
    ax.axvspan(3.5, 4.5, alpha=0.08, color=BLUE)
    ax.text(4, 0.63, 'Progressive\nWindow', ha='center', fontsize=8,
            color=BLUE, fontstyle='italic', fontproperties=font_prop)

    plt.tight_layout()
    path = os.path.join(FIGURES, 'context_window_performance.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ================================================================
# 1-3. Speaker별 상관계수 분포 (히스토그램 + 박스플롯)
# ================================================================
def fig_speaker_distribution(spk_means):
    print("[1-3] Speaker별 상관계수 분포 생성...")
    vals = np.array(list(spk_means.values()))
    mean_v = np.mean(vals)
    median_v = np.median(vals)
    q25, q75 = np.percentile(vals, [25, 75])

    fig, (ax_box, ax_hist) = plt.subplots(2, 1, figsize=(9, 6),
                                           gridspec_kw={'height_ratios': [1, 3]},
                                           sharex=True)

    # 박스플롯 (상단)
    bp = ax_box.boxplot(vals, vert=False, widths=0.6,
                        patch_artist=True,
                        boxprops=dict(facecolor=BLUE, alpha=0.3, edgecolor=BLUE),
                        medianprops=dict(color=ORANGE, linewidth=2),
                        whiskerprops=dict(color=BLUE),
                        capprops=dict(color=BLUE),
                        flierprops=dict(marker='o', markerfacecolor=GRAY, markersize=5))
    ax_box.set_yticks([])
    ax_box.spines['top'].set_visible(False)
    ax_box.spines['right'].set_visible(False)
    ax_box.spines['left'].set_visible(False)
    ax_box.set_title('화자별 테스트 상관계수 분포 (70명, Speaker-Independent)',
                     fontproperties=font_prop, fontsize=13, fontweight='bold', pad=10)

    # 히스토그램 (하단)
    n_bins = 15
    counts, bins, patches = ax_hist.hist(vals, bins=n_bins, color=BLUE, alpha=0.7,
                                         edgecolor='white', linewidth=1.2)
    for patch, left in zip(patches, bins[:-1]):
        if left >= 0.8:
            patch.set_facecolor(GREEN)
        elif left < 0.6:
            patch.set_facecolor(ORANGE)

    ax_hist.axvline(mean_v, color=RED, linestyle='-', linewidth=2,
                    label=f'평균: {mean_v:.4f}')
    ax_hist.axvline(median_v, color=ORANGE, linestyle='--', linewidth=2,
                    label=f'중앙값: {median_v:.4f}')
    ax_hist.axvline(0.7, color=GRAY, linestyle=':', linewidth=1.5,
                    label=f'r = 0.7 ({int(np.sum(vals >= 0.7))}/{len(vals)}, {np.sum(vals >= 0.7)/len(vals)*100:.0f}%)')

    # 통계 박스
    n_07 = int(np.sum(vals >= 0.7))
    n_08 = int(np.sum(vals >= 0.8))
    stat_text = (f'화자 수: {len(vals)}명\n'
                 f'평균: {mean_v:.4f}\n'
                 f'중앙값: {median_v:.4f}\n'
                 f'Q25/Q75: {q25:.4f} / {q75:.4f}\n'
                 f'r ≥ 0.7: {n_07}명 ({n_07/len(vals)*100:.0f}%)\n'
                 f'r ≥ 0.8: {n_08}명 ({n_08/len(vals)*100:.0f}%)')
    ax_hist.text(0.02, 0.97, stat_text, transform=ax_hist.transAxes,
                 fontsize=9, va='top', fontproperties=font_prop,
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#F5F5F5', alpha=0.9,
                           edgecolor=GRAY))

    ax_hist.set_xlabel('Pearson 상관계수 (r)', fontproperties=font_prop, fontsize=12)
    ax_hist.set_ylabel('화자 수', fontproperties=font_prop, fontsize=12)
    ax_hist.legend(fontsize=9, loc='upper right', prop=font_prop)
    ax_hist.spines['top'].set_visible(False)
    ax_hist.spines['right'].set_visible(False)

    plt.tight_layout()
    path = os.path.join(FIGURES, 'speaker_correlation_distribution.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")
    return vals, median_v


# ================================================================
# 2-1. 파형 비교 그래프 (2행 1열: 마이크 + EGG 오버레이)
# ================================================================
def fig_waveform_comparison(model, spk_means, spk_files):
    print("[2-1] 파형 비교 그래프 (중앙값 샘플) 생성...")
    vals = np.array(list(spk_means.values()))
    speakers = np.array(list(spk_means.keys()))
    median_v = np.median(vals)

    # 전체 테스트 상관계수 0.8249에 가장 가까운 화자 선택
    TARGET_CORR = 0.8249
    idx = np.argmin(np.abs(vals - TARGET_CORR))
    target_spk = speakers[idx]
    target_corr = vals[idx]
    print(f"  선택: Speaker {target_spk}, Corr={target_corr:.4f} (target={TARGET_CORR})")

    # 해당 화자의 데이터 로드
    mic_sig, egg_gt, egg_pred, corr = _load_best_sample(model, target_spk, spk_files)

    # 0.5초 구간 (8000 samples)
    show_len = min(8000, len(mic_sig))
    t = np.arange(show_len) / SR

    MIC_COLOR = '#4A90D9'
    EST_COLOR = '#FF9500'
    GT_COLOR = '#4CAF50'

    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    fig.subplots_adjust(hspace=0.3)
    fig.suptitle(f'마이크 음성 → EGG 추정 결과 (Speaker {target_spk}, r = {target_corr:.4f})',
                 fontproperties=font_prop, fontsize=14, fontweight='bold', y=0.98)

    # (상) 마이크 음성 단독
    axes[0].plot(t, mic_sig[:show_len], color=MIC_COLOR, linewidth=0.6)
    axes[0].set_ylabel('마이크 음성', fontproperties=font_prop, fontsize=12)
    axes[0].set_xlim(0, t[-1])
    axes[0].tick_params(labelbottom=False)  # x축 라벨은 아래만

    # (하) 추정 EGG + 정답 EGG 오버레이
    axes[1].plot(t, egg_gt[:show_len], color=GT_COLOR, linewidth=0.7,
                 label='정답 EGG', alpha=0.9)
    axes[1].plot(t, egg_pred[:show_len], color=EST_COLOR, linewidth=0.7,
                 label='추정 EGG', alpha=0.85, linestyle='-')
    axes[1].set_ylabel('EGG', fontproperties=font_prop, fontsize=12)
    axes[1].set_xlabel('시간 (초)', fontproperties=font_prop, fontsize=12)
    axes[1].legend(fontsize=10, loc='upper right', prop=font_prop,
                   framealpha=0.9, edgecolor=GRAY)

    for ax in axes:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(labelsize=9)
        ax.set_facecolor('white')

    plt.tight_layout()
    path = os.path.join(FIGURES, 'waveform_comparison_median.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ================================================================
# 2-2. EGG 산점도
# ================================================================
def fig_scatter(model, spk_means, spk_files):
    print("[2-2] EGG 산점도 생성...")
    vals = np.array(list(spk_means.values()))
    speakers = np.array(list(spk_means.keys()))
    median_v = np.median(vals)

    # 중앙값 근처 3명
    dists = np.abs(vals - median_v)
    idxs = np.argsort(dists)[:3]

    all_gt = []
    all_pred = []
    for i in idxs:
        spk = speakers[i]
        mic, gt, pred, c = _load_best_sample(model, spk, spk_files)
        # 서브샘플 (점이 너무 많으면 느림)
        step = max(1, len(gt) // 3000)
        all_gt.append(gt[::step])
        all_pred.append(pred[::step])

    gt_arr = np.concatenate(all_gt)
    pred_arr = np.concatenate(all_pred)
    overall_corr = pearson_corr(gt_arr, pred_arr)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(gt_arr, pred_arr, s=1, alpha=0.15, color=BLUE, rasterized=True)

    lim_min = min(gt_arr.min(), pred_arr.min()) * 1.05
    lim_max = max(gt_arr.max(), pred_arr.max()) * 1.05
    ax.plot([lim_min, lim_max], [lim_min, lim_max], '--', color=GRAY, linewidth=1.5,
            label='y = x (이상적 예측)')
    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_min, lim_max)

    ax.text(0.05, 0.95, f'Pearson r = {overall_corr:.4f}\n(중앙값 근처 화자 3명)',
            transform=ax.transAxes, fontsize=11, va='top',
            fontproperties=font_prop,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#F5F5F5', alpha=0.9,
                      edgecolor=GRAY))

    ax.set_xlabel('정답 EGG', fontproperties=font_prop, fontsize=12)
    ax.set_ylabel('추정 EGG', fontproperties=font_prop, fontsize=12)
    ax.set_title('정답 vs 추정 EGG 산점도', fontproperties=font_prop,
                 fontsize=13, fontweight='bold', pad=10)
    ax.legend(fontsize=9, loc='lower right', prop=font_prop)
    ax.set_aspect('equal')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    path = os.path.join(FIGURES, 'egg_scatter_plot.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ================================================================
# 3-1. 학습 곡선
# ================================================================
def fig_training_curve():
    print("[3-1] 학습 곡선 생성...")
    with open(os.path.join(RESULTS, 'exp20_progressive/history.json')) as f:
        h = json.load(f)

    epochs = np.arange(1, len(h['train_loss']) + 1)
    train_loss = h['train_loss']
    val_loss = h['val_loss']
    train_corr = h['train_corr']
    val_corr = h['val_corr']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 좌: Loss
    ax1.plot(epochs, train_loss, color=BLUE, linewidth=1.5, label='Train Loss')
    ax1.plot(epochs, val_loss, color=ORANGE, linewidth=1.5, label='Validation Loss')
    ax1.axvline(20.5, color=GRAY, linestyle=':', linewidth=1.5, alpha=0.7)
    ax1.axvline(60.5, color=GRAY, linestyle=':', linewidth=1.5, alpha=0.7)
    ax1.text(10, max(train_loss) * 0.98, 'Phase 1\nwin=4096', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax1.text(40, max(train_loss) * 0.98, 'Phase 2\nwin=8192', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax1.text(68, max(train_loss) * 0.98, 'Phase 3\nwin=16384', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax1.set_xlabel('Epoch', fontproperties=font_prop, fontsize=12)
    ax1.set_ylabel('Loss', fontproperties=font_prop, fontsize=12)
    ax1.set_title('학습/검증 손실 (Loss)', fontproperties=font_prop, fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9, prop=font_prop)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # 우: Correlation
    ax2.plot(epochs, train_corr, color=BLUE, linewidth=1.5, label='Train Corr')
    ax2.plot(epochs, val_corr, color=ORANGE, linewidth=1.5, label='Validation Corr')
    ax2.axvline(20.5, color=GRAY, linestyle=':', linewidth=1.5, alpha=0.7)
    ax2.axvline(60.5, color=GRAY, linestyle=':', linewidth=1.5, alpha=0.7)
    ax2.text(10, min(train_corr) + 0.005, 'Phase 1\nwin=4096', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax2.text(40, min(train_corr) + 0.005, 'Phase 2\nwin=8192', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax2.text(68, min(train_corr) + 0.005, 'Phase 3\nwin=16384', ha='center', fontsize=8,
             color=GRAY, fontproperties=font_prop)
    ax2.set_xlabel('Epoch', fontproperties=font_prop, fontsize=12)
    ax2.set_ylabel('Pearson 상관계수', fontproperties=font_prop, fontsize=12)
    ax2.set_title('학습/검증 상관계수', fontproperties=font_prop, fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9, prop=font_prop, loc='lower right')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    path = os.path.join(FIGURES, 'training_curve.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ================================================================
# Helper: 화자의 대표 샘플 로드
# ================================================================
def _load_best_sample(model, spk, spk_files):
    files = spk_files[spk]
    best = None
    for nsp_path, egg_path in files:
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            speech = librosa.resample(speech, orig_sr=50000, target_sr=SR)
            egg = librosa.resample(egg, orig_sr=50000, target_sr=SR)
            ml = min(len(speech), len(egg))
            speech, egg = speech[:ml], egg[:ml]
            if ml < WINDOW:
                continue
            s_std, e_std = speech.std(), egg.std()
            if s_std > 1e-8: speech = (speech - speech.mean()) / s_std
            if e_std > 1e-8: egg = (egg - egg.mean()) / e_std
            # 중앙 윈도우
            mid = ml // 2
            start = max(0, mid - WINDOW // 2)
            if start + WINDOW > ml: start = ml - WINDOW
            sw = speech[start:start+WINDOW]
            ew = egg[start:start+WINDOW]
            x = torch.from_numpy(sw).float().unsqueeze(0).unsqueeze(0).to(device)
            with torch.no_grad():
                pw = model(x).squeeze().cpu().numpy()
            mt = min(len(ew), len(pw))
            c = pearson_corr(ew[:mt], pw[:mt])
            if best is None or c > best[-1]:
                best = (speech[start:start+WINDOW], ew[:mt], pw[:mt], c)
        except Exception:
            continue
    return best


# ================================================================
# Helper: 전 화자 상관계수 계산
# ================================================================
def compute_speaker_corrs(model):
    print("전체 테스트 화자 상관계수 계산 중...")
    pairs = find_paired_files(SVD_PATH)
    all_speakers = sorted(set(p[2] for p in pairs))
    _, _, test_sp = speaker_split(all_speakers, seed=42)
    test_pairs = [(n, e, s) for n, e, s in pairs if s in test_sp]

    spk_files = defaultdict(list)
    for n, e, s in test_pairs:
        spk_files[s].append((n, e))

    spk_corrs_raw = {}
    cnt = 0
    for nsp_path, egg_path, spk in test_pairs:
        try:
            speech, _ = read_nsp(nsp_path)
            egg, _ = read_nsp(egg_path)
            ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
            speech = librosa.resample(speech, orig_sr=50000, target_sr=SR)
            egg = librosa.resample(egg, orig_sr=50000, target_sr=SR)
            ml = min(len(speech), len(egg)); speech = speech[:ml]; egg = egg[:ml]
            if ml < WINDOW: continue
            s_std, e_std = speech.std(), egg.std()
            if s_std > 1e-8: speech = (speech - speech.mean()) / s_std
            if e_std > 1e-8: egg = (egg - egg.mean()) / e_std
            for w in range((ml - WINDOW) // HOP + 1):
                start = w * HOP
                x = torch.from_numpy(speech[start:start+WINDOW]).float().unsqueeze(0).unsqueeze(0).to(device)
                y_np = egg[start:start+WINDOW]
                with torch.no_grad():
                    p = model(x).squeeze().cpu().numpy()
                mt = min(len(p), len(y_np))
                c = pearson_corr(y_np[:mt], p[:mt])
                spk_corrs_raw.setdefault(spk, []).append(c)
            cnt += 1
            if cnt % 100 == 0: print(f"  {cnt} 파일 처리 완료...")
        except Exception:
            continue

    spk_means = {s: np.mean(c) for s, c in spk_corrs_raw.items()}
    print(f"  완료: {len(spk_means)}명, Mean={np.mean(list(spk_means.values())):.4f}, "
          f"Median={np.median(list(spk_means.values())):.4f}")
    return spk_means, spk_files


# ================================================================
# Main
# ================================================================
if __name__ == '__main__':
    t0 = time.time()

    # 모델 불필요한 그래프 먼저
    fig_ablation_bar()
    fig_context_window()
    fig_training_curve()

    # 모델 로드
    print("\n모델 로드 중...")
    model = build_efficient_model(EXP20_CFG)
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.to(device).eval()
    print(f"  로드 완료 (val_corr={ckpt.get('val_corr', 'N/A'):.4f})")

    # 화자별 상관계수
    spk_means, spk_files = compute_speaker_corrs(model)

    # 모델 필요한 그래프
    fig_speaker_distribution(spk_means)
    fig_waveform_comparison(model, spk_means, spk_files)
    fig_scatter(model, spk_means, spk_files)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"전체 완료! (소요 시간: {elapsed:.0f}초)")
    print(f"생성된 파일:")
    for f in sorted(os.listdir(FIGURES)):
        if f.endswith('.png'):
            size = os.path.getsize(os.path.join(FIGURES, f)) / 1024
            print(f"  figures/{f} ({size:.0f} KB)")
