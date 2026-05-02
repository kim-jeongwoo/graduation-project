"""
SVD_healthy 기반 화자 독립 EGG 예측 모델 학습
목표: 화자 분할 Test corr >= 0.5

데이터:
  - SVD_healthy: 687명 화자, mic(.nsp) + EGG(.egg) 쌍
  - 파일 형식: FORMDS16 (IFF variant), 50kHz, 16-bit
  - 모음(vowels): a/i/u × high/low/normal/lhl + iau = 최대 13개/화자
  - 문장(sentences): 1개/화자

검증: PTDB-TUG (20명)로 cross-dataset validation
"""
import os
import sys
import struct
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import ExponentialLR
from pathlib import Path
import numpy as np
import librosa
from scipy import signal as sig
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import random
import copy
import time
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))
from utils.metrics import compute_correlation, compute_mse, compute_r2


# ============================================================
# 설정
# ============================================================
SVD_HEALTHY_PATH = "/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw/SVD_healthy"
PTDB_PATH = "/Users/kimjeongwoo/Desktop/졸업작품/workspace/data/raw/PTDB-TUG"

ORIG_SR = 50000      # SVD 원본 샘플레이트
TARGET_SR = 16000     # 학습용 리샘플링
WINDOW_LENGTH = 192   # 프레임 길이
HOP_LENGTH = 32       # 프레임 hop
MIN_CORR = 0.2        # 품질 필터 (낮은 corr 파일 제외)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


# ============================================================
# DS16 파일 로더 (SVD .nsp / .egg)
# ============================================================

def load_ds16_audio(filepath):
    """
    SVD .nsp/.egg 파일 로드 (FORMDS16 형식)
    Returns: audio (float32 numpy), sample_rate
    """
    with open(filepath, 'rb') as f:
        form_id = f.read(4)
        if form_id != b'FORM':
            return None, 0
        
        f.read(4)  # form_type (DS16)
        f.read(4)  # size marker
        
        hedr_id = f.read(4)
        if hedr_id != b'HEDR':
            return None, 0
        
        hedr_size = struct.unpack('<I', f.read(4))[0]
        hedr_data = f.read(hedr_size)
        
        sample_rate = 50000
        if len(hedr_data) >= 24:
            sr_candidate = struct.unpack('<I', hedr_data[20:24])[0]
            if 8000 <= sr_candidate <= 96000:
                sample_rate = sr_candidate
        
        sda_id = f.read(4)
        if sda_id != b'SDA_':
            return None, 0
        
        f.read(4)  # sda_size
        raw_data = f.read()
        audio = np.frombuffer(raw_data, dtype='<i2').astype(np.float32) / 32768.0
    
    return audio, sample_rate


# ============================================================
# 모델 정의 (ptdb_experiment.py와 동일)
# ============================================================

class WaveNetEGG(nn.Module):
    """WaveNet + Self-Attention for EGG prediction"""
    def __init__(self, input_size=192, n_layers=10, n_channels=32,
                 n_heads=4, dropout=0.5):
        super().__init__()
        self.input_size = input_size
        self.n_layers = n_layers
        self.n_channels = n_channels

        self.input_conv = nn.Conv1d(1, n_channels, kernel_size=1)

        self.dilated_convs = nn.ModuleList()
        self.residual_convs = nn.ModuleList()
        self.skip_convs = nn.ModuleList()
        self.dropouts = nn.ModuleList()

        for i in range(n_layers):
            dilation = 2 ** i
            self.dilated_convs.append(
                nn.Conv1d(n_channels, n_channels * 2, kernel_size=3,
                         padding=dilation, dilation=dilation))
            self.residual_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.skip_convs.append(nn.Conv1d(n_channels, n_channels, kernel_size=1))
            self.dropouts.append(nn.Dropout(dropout))

        self.attention = nn.MultiheadAttention(n_channels, n_heads,
                                                dropout=dropout, batch_first=True)
        self.attention_norm = nn.LayerNorm(n_channels)

        self.output_conv1 = nn.Conv1d(n_channels, n_channels, kernel_size=1)
        self.output_conv2 = nn.Conv1d(n_channels, 1, kernel_size=1)
        self.output_dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.input_conv(x)

        skip_sum = 0
        for i in range(self.n_layers):
            out = self.dilated_convs[i](x)
            tanh_out = torch.tanh(out[:, :self.n_channels, :])
            sigmoid_out = torch.sigmoid(out[:, self.n_channels:, :])
            gated = tanh_out * sigmoid_out
            gated = self.dropouts[i](gated)

            skip = self.skip_convs[i](gated)
            skip_sum = skip_sum + skip
            residual = self.residual_convs[i](gated)
            x = x + residual

        attn_in = skip_sum.permute(0, 2, 1)
        attn_out, _ = self.attention(attn_in, attn_in, attn_in)
        attn_out = self.attention_norm(attn_out + attn_in)
        skip_sum = attn_out.permute(0, 2, 1)

        out = torch.relu(skip_sum)
        out = self.output_conv1(out)
        out = self.output_dropout(out)
        out = torch.relu(out)
        out = self.output_conv2(out)

        out = out.mean(dim=2)
        return out.squeeze(1)

    def get_receptive_field(self):
        rf = 1
        for i in range(self.n_layers):
            rf += 2 * (2 ** i)
        return rf


# ============================================================
# 전처리
# ============================================================

def highpass_filter(data, cutoff, sr, order=5):
    nyq = sr / 2
    b, a = sig.butter(order, cutoff / nyq, btype='high')
    return sig.filtfilt(b, a, data)


def bandpass_filter(data, low, high, sr, order=5):
    nyq = sr / 2
    b, a = sig.butter(order, [low / nyq, high / nyq], btype='band')
    return sig.filtfilt(b, a, data)


def align_signals(mic, egg, max_lag_samples=800):
    """Cross-correlation 기반 시간 정렬 + 극성 보정"""
    mic_norm = (mic - np.mean(mic)) / (np.std(mic) + 1e-8)
    egg_norm = (egg - np.mean(egg)) / (np.std(egg) + 1e-8)

    # 앞부분 사용해서 lag 추정 (빠르게)
    seg_len = min(20000, len(mic_norm))
    xcorr = np.correlate(mic_norm[:seg_len], egg_norm[:seg_len], mode='full')
    center = len(xcorr) // 2
    s = max(0, center - max_lag_samples)
    e = min(len(xcorr), center + max_lag_samples)

    best_idx = s + np.argmax(np.abs(xcorr[s:e]))
    best_lag = best_idx - center
    polarity = 1 if xcorr[best_idx] >= 0 else -1

    if best_lag > 0:
        mic = mic[best_lag:]
        egg = egg[:len(mic)]
    elif best_lag < 0:
        egg = egg[-best_lag:]
        mic = mic[:len(egg)]

    min_len = min(len(mic), len(egg))
    return mic[:min_len], egg[:min_len] * polarity, best_lag, polarity


def frame_signal(signal_data, window_length=192, hop_length=32):
    n_frames = (len(signal_data) - window_length) // hop_length + 1
    if n_frames <= 0:
        return np.array([])
    frames = np.zeros((n_frames, window_length))
    for i in range(n_frames):
        start = i * hop_length
        frames[i] = signal_data[start:start + window_length]
    return frames


# ============================================================
# SVD 데이터 로드
# ============================================================

def get_svd_speakers(base_path):
    """SVD_healthy 화자 목록"""
    speakers = []
    for d in os.listdir(base_path):
        full = os.path.join(base_path, d)
        if os.path.isdir(full) and d.isdigit():
            speakers.append(d)
    return sorted(speakers, key=int)


def get_svd_pairs(base_path, speaker):
    """한 화자의 mic-egg 파일 쌍 (vowels + sentences)"""
    pairs = []
    for subdir in ['vowels', 'sentences']:
        folder = os.path.join(base_path, speaker, subdir)
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if f.endswith('.nsp') and '-egg' not in f:
                base_name = f.replace('.nsp', '')
                egg_name = f"{base_name}-egg.egg"
                egg_path = os.path.join(folder, egg_name)
                if os.path.exists(egg_path):
                    pairs.append({
                        'mic': os.path.join(folder, f),
                        'egg': egg_path,
                        'speaker': speaker,
                        'file': base_name,
                        'type': subdir
                    })
    return pairs


def process_svd_pair(mic_path, egg_path):
    """
    SVD 파일 쌍 전처리: 로드 → 리샘플 → 정렬 → 필터 → 프레이밍
    Returns: mic_frames, egg_center, corr
    """
    try:
        mic, mic_sr = load_ds16_audio(mic_path)
        egg, egg_sr = load_ds16_audio(egg_path)

        if mic is None or egg is None:
            return None, None, 0.0

        if len(mic) < 5000 or len(egg) < 5000:
            return None, None, 0.0

        # 리샘플링 50kHz → 16kHz
        mic = librosa.resample(mic, orig_sr=ORIG_SR, target_sr=TARGET_SR)
        egg = librosa.resample(egg, orig_sr=ORIG_SR, target_sr=TARGET_SR)

        # 정렬 + 극성 보정
        mic, egg, lag, polarity = align_signals(mic, egg,
                                                 max_lag_samples=int(0.05 * TARGET_SR))

        if len(mic) < 1000:
            return None, None, 0.0

        # 필터링
        mic = highpass_filter(mic, 30, TARGET_SR)
        egg = bandpass_filter(egg, 80, 4000, TARGET_SR)

        # 정규화
        mic = mic / (np.max(np.abs(mic)) + 1e-8)
        egg = egg / (np.max(np.abs(egg)) + 1e-8)

        # 상관관계 확인
        corr = abs(np.corrcoef(mic, egg)[0, 1])

        # 프레이밍
        mic_frames = frame_signal(mic, WINDOW_LENGTH, HOP_LENGTH)
        egg_frames = frame_signal(egg, WINDOW_LENGTH, HOP_LENGTH)

        if len(mic_frames) == 0 or len(egg_frames) == 0:
            return None, None, corr

        # EGG는 중심값만 사용 (스칼라 타겟)
        egg_center = egg_frames[:, WINDOW_LENGTH // 2]

        min_frames = min(len(mic_frames), len(egg_center))
        return mic_frames[:min_frames], egg_center[:min_frames], corr

    except Exception:
        return None, None, 0.0


# ============================================================
# 데이터셋
# ============================================================

class FrameDataset(Dataset):
    def __init__(self, mic_frames, egg_frames):
        self.mic = torch.from_numpy(mic_frames).float()
        self.egg = torch.from_numpy(egg_frames).float()

    def __len__(self):
        return len(self.mic)

    def __getitem__(self, idx):
        return self.mic[idx], self.egg[idx]


# ============================================================
# 학습 / 평가
# ============================================================

def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train_epoch(model, loader, criterion, optimizer, device, epoch, total):
    model.train()
    total_loss = 0
    n = len(loader)
    for i, (mic, egg) in enumerate(loader, 1):
        mic, egg = mic.to(device), egg.to(device)
        optimizer.zero_grad()
        pred = model(mic)
        loss = criterion(pred, egg)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item()
        if i == 1 or i == n or i % max(1, n // 10) == 0:
            print(f"\r  Epoch {epoch:3d}/{total} | Batch {i:4d}/{n} | "
                  f"{100*i/n:5.1f}% | Loss: {total_loss/i:.4f}", end='', flush=True)
    print()
    return total_loss / n


def evaluate(model, loader, device):
    model.eval()
    preds_list, gts_list = [], []
    with torch.no_grad():
        for mic, egg in loader:
            mic, egg = mic.to(device), egg.to(device)
            pred = model(mic)
            preds_list.append(pred.cpu().numpy())
            gts_list.append(egg.cpu().numpy())
    preds = np.concatenate(preds_list).flatten()
    gts = np.concatenate(gts_list).flatten()
    corr = compute_correlation(preds, gts)
    mse = compute_mse(preds, gts)
    r2 = compute_r2(preds, gts)
    return corr, mse, r2, preds, gts


# ============================================================
# 메인
# ============================================================

def main():
    print("=" * 70)
    print("SVD 화자 독립 EGG 예측 실험")
    print("목표: 화자 분할 Test corr >= 0.5")
    print("=" * 70)

    device = get_device()
    print(f"Device: {device}")

    base_dir = Path(__file__).parent
    results_dir = base_dir / "results" / "svd_experiment"
    results_dir.mkdir(parents=True, exist_ok=True)

    # ==================================================================
    # 1. 화자 목록 및 분할
    # ==================================================================
    print("\n[1] 화자 목록 로드...")
    all_speakers = get_svd_speakers(SVD_HEALTHY_PATH)
    print(f"  SVD_healthy 총 화자: {len(all_speakers)}명")

    random.shuffle(all_speakers)
    n = len(all_speakers)
    n_train = int(n * 0.80)
    n_val = int(n * 0.10)

    train_speakers = all_speakers[:n_train]
    val_speakers = all_speakers[n_train:n_train + n_val]
    test_speakers = all_speakers[n_train + n_val:]

    print(f"\n[2] 화자 분할:")
    print(f"  Train: {len(train_speakers)}명 (80%)")
    print(f"  Val:   {len(val_speakers)}명 (10%)")
    print(f"  Test:  {len(test_speakers)}명 (10%) ← 완전히 새로운 화자")

    # ==================================================================
    # 2. 데이터 전처리
    # ==================================================================
    print("\n[3] 데이터 전처리 중...")

    def collect_frames(speakers, label):
        all_mic, all_egg = [], []
        total_pairs = 0
        skipped = 0
        n_spk = len(speakers)

        for si, spk in enumerate(speakers, 1):
            pairs = get_svd_pairs(SVD_HEALTHY_PATH, spk)
            for p in pairs:
                mic_frames, egg_center, corr = process_svd_pair(p['mic'], p['egg'])
                total_pairs += 1
                if mic_frames is not None and corr >= MIN_CORR:
                    all_mic.append(mic_frames)
                    all_egg.append(egg_center)
                else:
                    skipped += 1

            if si % max(1, n_spk // 20) == 0 or si == n_spk:
                print(f"\r  {label}: {si:4d}/{n_spk} 화자 ({100*si/n_spk:.0f}%)"
                      f" | pairs: {total_pairs}, skipped: {skipped}",
                      end='', flush=True)
        print()

        if all_mic:
            return np.concatenate(all_mic), np.concatenate(all_egg), total_pairs, skipped
        return np.array([]), np.array([]), total_pairs, skipped

    t0 = time.time()
    train_mic, train_egg, train_total, train_skip = collect_frames(train_speakers, "Train")
    val_mic, val_egg, val_total, val_skip = collect_frames(val_speakers, "Val")
    test_mic, test_egg, test_total, test_skip = collect_frames(test_speakers, "Test")
    preproc_time = time.time() - t0

    print(f"\n  전처리 완료 ({preproc_time/60:.1f}분)")
    print(f"  Train: {len(train_mic):,} frames ({train_total} pairs, {train_skip} skipped)")
    print(f"  Val:   {len(val_mic):,} frames ({val_total} pairs, {val_skip} skipped)")
    print(f"  Test:  {len(test_mic):,} frames ({test_total} pairs, {test_skip} skipped)")

    if len(train_mic) == 0 or len(val_mic) == 0 or len(test_mic) == 0:
        print("ERROR: 데이터 부족!")
        return

    # ==================================================================
    # 3. 데이터 로더
    # ==================================================================
    print("\n[4] 데이터 로더 생성...")

    train_ds = FrameDataset(train_mic, train_egg)
    val_ds = FrameDataset(val_mic, val_egg)
    test_ds = FrameDataset(test_mic, test_egg)

    BS = 512
    train_loader = DataLoader(train_ds, batch_size=BS, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BS, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BS, shuffle=False, num_workers=0)

    print(f"  Train batches: {len(train_loader)}")
    print(f"  Val batches:   {len(val_loader)}")
    print(f"  Test batches:  {len(test_loader)}")

    # ==================================================================
    # 4. 모델
    # ==================================================================
    print("\n[5] 모델 생성...")

    model = WaveNetEGG(input_size=WINDOW_LENGTH, n_layers=10,
                       n_channels=32, n_heads=4, dropout=0.5).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {n_params:,}")
    print(f"  Receptive field: {model.get_receptive_field()} samples")

    # ==================================================================
    # 5. 학습
    # ==================================================================
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = ExponentialLR(optimizer, gamma=0.95)

    EPOCHS = 100
    PATIENCE = 10
    best_val_corr = -1
    best_state = None
    patience_cnt = 0
    history = {'loss': [], 'val_corr': [], 'val_mse': [], 'val_r2': []}

    print(f"\n{'='*70}")
    print(f"  학습 시작 (총 {EPOCHS} epochs, Early Stopping patience={PATIENCE})")
    print(f"{'='*70}")

    t_start = time.time()

    for epoch in range(1, EPOCHS + 1):
        ep_start = time.time()

        loss = train_epoch(model, train_loader, criterion, optimizer, device, epoch, EPOCHS)
        val_corr, val_mse, val_r2, _, _ = evaluate(model, val_loader, device)
        scheduler.step()

        ep_time = time.time() - ep_start
        elapsed = time.time() - t_start
        eta = (elapsed / epoch) * (EPOCHS - epoch)

        history['loss'].append(loss)
        history['val_corr'].append(val_corr)
        history['val_mse'].append(val_mse)
        history['val_r2'].append(val_r2)

        improved = ""
        if val_corr > best_val_corr:
            best_val_corr = val_corr
            best_state = copy.deepcopy(model.state_dict())
            patience_cnt = 0
            improved = " ★ NEW BEST"
        else:
            patience_cnt += 1

        print(f"  {'─'*66}")
        print(f"  Epoch {epoch:3d}/{EPOCHS} ({ep_time:.1f}s) | ETA: {eta/60:.1f}분")
        print(f"    Loss: {loss:.6f}  |  Val Corr: {val_corr:.4f}  |  "
              f"MSE: {val_mse:.6f}  |  R²: {val_r2:.4f}")
        print(f"    Best: {best_val_corr:.4f}  |  Patience: {patience_cnt}/{PATIENCE}{improved}")

        if patience_cnt >= PATIENCE:
            print(f"\n  ⚠️ Early stopping at epoch {epoch}")
            break

    total_time = time.time() - t_start
    print(f"\n{'='*70}")
    print(f"  학습 완료! 총 {total_time/60:.1f}분")
    print(f"{'='*70}")

    # ==================================================================
    # 6. 테스트
    # ==================================================================
    print("\n[6] 화자 독립 테스트...")
    if best_state is not None:
        model.load_state_dict(best_state)

    test_corr, test_mse, test_r2, test_preds, test_gts = evaluate(model, test_loader, device)

    # 화자별 corr (테스트 화자 10명 샘플)
    print("\n  화자별 테스트 (샘플 10명)...")
    speaker_corrs = {}
    sample_test_spk = test_speakers[:min(10, len(test_speakers))]
    for spk in sample_test_spk:
        pairs = get_svd_pairs(SVD_HEALTHY_PATH, spk)
        spk_mic, spk_egg = [], []
        for p in pairs:
            mf, ec, c = process_svd_pair(p['mic'], p['egg'])
            if mf is not None and c >= MIN_CORR:
                spk_mic.append(mf)
                spk_egg.append(ec)
        if spk_mic:
            spk_ds = FrameDataset(np.concatenate(spk_mic), np.concatenate(spk_egg))
            spk_loader = DataLoader(spk_ds, batch_size=512, shuffle=False)
            sc, _, _, _, _ = evaluate(model, spk_loader, device)
            speaker_corrs[spk] = sc

    # ==================================================================
    # 7. Cross-dataset validation (PTDB-TUG)
    # ==================================================================
    ptdb_corr = None
    if os.path.exists(PTDB_PATH):
        print("\n[7] Cross-dataset validation (PTDB-TUG)...")
        try:
            ptdb_mic_all, ptdb_egg_all = [], []
            ptdb_count = 0
            for gender in ['FEMALE', 'MALE']:
                mic_dir = os.path.join(PTDB_PATH, gender, 'MIC')
                lar_dir = os.path.join(PTDB_PATH, gender, 'LAR')
                if not os.path.exists(mic_dir):
                    continue
                for spk in sorted(os.listdir(mic_dir)):
                    spk_mic_dir = os.path.join(mic_dir, spk)
                    spk_lar_dir = os.path.join(lar_dir, spk)
                    if not os.path.isdir(spk_mic_dir):
                        continue
                    files = sorted([f for f in os.listdir(spk_mic_dir) if f.endswith('.wav')])
                    for mic_f in files[:5]:  # 화자당 5개
                        lar_f = mic_f.replace('mic_', 'lar_')
                        mic_p = os.path.join(spk_mic_dir, mic_f)
                        lar_p = os.path.join(spk_lar_dir, lar_f)
                        if not os.path.exists(lar_p):
                            continue
                        try:
                            m, _ = librosa.load(mic_p, sr=TARGET_SR)
                            e, _ = librosa.load(lar_p, sr=TARGET_SR)
                            m, e, _, _ = align_signals(m, e, max_lag_samples=int(0.05*TARGET_SR))
                            if len(m) < 1000:
                                continue
                            m = highpass_filter(m, 30, TARGET_SR)
                            e = bandpass_filter(e, 80, 4000, TARGET_SR)
                            m = m / (np.max(np.abs(m)) + 1e-8)
                            e = e / (np.max(np.abs(e)) + 1e-8)
                            mf = frame_signal(m, WINDOW_LENGTH, HOP_LENGTH)
                            ef = frame_signal(e, WINDOW_LENGTH, HOP_LENGTH)
                            if len(mf) == 0:
                                continue
                            ec = ef[:, WINDOW_LENGTH // 2]
                            n = min(len(mf), len(ec))
                            ptdb_mic_all.append(mf[:n])
                            ptdb_egg_all.append(ec[:n])
                            ptdb_count += 1
                        except Exception:
                            pass

            if ptdb_mic_all:
                ptdb_ds = FrameDataset(np.concatenate(ptdb_mic_all), np.concatenate(ptdb_egg_all))
                ptdb_loader = DataLoader(ptdb_ds, batch_size=512, shuffle=False)
                ptdb_corr, ptdb_mse, ptdb_r2, _, _ = evaluate(model, ptdb_loader, device)
                print(f"  PTDB-TUG: {ptdb_count} files | corr={ptdb_corr:.4f} | mse={ptdb_mse:.6f}")
        except Exception as ex:
            print(f"  PTDB-TUG 검증 실패: {ex}")

    # ==================================================================
    # 8. 결과 출력
    # ==================================================================
    print(f"\n{'='*70}")
    print("SVD 화자 독립 모델 결과")
    print(f"{'='*70}")
    print(f"  데이터: SVD_healthy ({len(all_speakers)}명)")
    print(f"  Train: {len(train_speakers)}명, {len(train_mic):,} frames")
    print(f"  Val:   {len(val_speakers)}명, {len(val_mic):,} frames")
    print(f"  Test:  {len(test_speakers)}명, {len(test_mic):,} frames")
    print(f"\n  Best Val Corr: {best_val_corr:.4f}")
    print(f"\n  🎯 화자 독립 Test:")
    print(f"     Corr: {test_corr:.4f}")
    print(f"     MSE:  {test_mse:.6f}")
    print(f"     R²:   {test_r2:.4f}")

    if test_corr >= 0.5:
        status = "✅ 목표 달성! (corr ≥ 0.5)"
    elif test_corr >= 0.3:
        status = "⚠️ 최소 목표 달성 (corr ≥ 0.3)"
    else:
        status = "❌ 목표 미달"
    print(f"\n  결론: {status}")

    if speaker_corrs:
        print(f"\n  화자별 Test corr (샘플 {len(speaker_corrs)}명):")
        print(f"  ┌{'─'*10}┬{'─'*10}┐")
        print(f"  │ {'Speaker':<8} │ {'Corr':<8} │")
        print(f"  ├{'─'*10}┼{'─'*10}┤")
        for spk in sorted(speaker_corrs, key=lambda s: speaker_corrs[s], reverse=True):
            print(f"  │ {spk:<8} │ {speaker_corrs[spk]:>8.4f} │")
        print(f"  └{'─'*10}┴{'─'*10}┘")

    if ptdb_corr is not None:
        print(f"\n  Cross-Dataset Validation (PTDB-TUG): corr={ptdb_corr:.4f}")
        if ptdb_corr >= 0.3:
            print(f"  ✅ 일반화 성공!")
        else:
            print(f"  ⚠️ 일반화 부족 – SVD 특화 모델")

    # ==================================================================
    # 9. 저장
    # ==================================================================
    print(f"\n[8] 결과 저장...")

    # 모델 저장
    if best_state is not None:
        torch.save(best_state, results_dir / "best_model.pt")
        print(f"  모델: {results_dir / 'best_model.pt'}")

    # 메트릭 텍스트
    with open(results_dir / "metrics.txt", 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("SVD 화자 독립 EGG 예측 실험 결과\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"데이터셋: SVD_healthy\n")
        f.write(f"총 화자: {len(all_speakers)}명\n\n")
        f.write(f"Train: {len(train_speakers)}명, {len(train_mic):,} frames\n")
        f.write(f"Val:   {len(val_speakers)}명, {len(val_mic):,} frames\n")
        f.write(f"Test:  {len(test_speakers)}명, {len(test_mic):,} frames\n\n")
        f.write(f"모델: WaveNet + Self-Attention\n")
        f.write(f"Parameters: {n_params:,}\n")
        f.write(f"Dropout: 0.5, Weight decay: 1e-4\n\n")
        f.write(f"Best Val Corr: {best_val_corr:.4f}\n")
        f.write(f"Test Corr: {test_corr:.4f}\n")
        f.write(f"Test MSE:  {test_mse:.6f}\n")
        f.write(f"Test R²:   {test_r2:.4f}\n\n")
        f.write(f"결론: {status}\n")
        if ptdb_corr is not None:
            f.write(f"\nCross-Dataset (PTDB-TUG): corr={ptdb_corr:.4f}\n")
    print(f"  메트릭: {results_dir / 'metrics.txt'}")

    # 학습 곡선
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    ep_range = range(1, len(history['val_corr']) + 1)

    axes[0].plot(ep_range, history['loss'], 'r-', label='Train Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(ep_range, history['val_corr'], 'b-', linewidth=2, label='Val Corr')
    axes[1].axhline(y=0.5, color='g', linestyle='--', label='Target (0.5)')
    axes[1].axhline(y=0.3, color='orange', linestyle='--', label='Min (0.3)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Correlation')
    axes[1].set_title('Validation Correlation')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([-0.2, 1.0])

    # 비교 bar chart
    methods = ['OpenGlot', 'PTDB-TUG\n(prev)', 'SVD\n(this)']
    corrs_bar = [0.07, 0.03, test_corr]
    colors = ['gray', 'gray', 'green' if test_corr >= 0.3 else 'red']
    axes[2].bar(methods, corrs_bar, color=colors, alpha=0.7, edgecolor='black')
    axes[2].axhline(y=0.5, color='g', linestyle='--', label='Target')
    axes[2].set_ylabel('Test Correlation')
    axes[2].set_title('Method Comparison')
    axes[2].legend()
    for i, v in enumerate(corrs_bar):
        axes[2].text(i, v + 0.02, f'{v:.3f}', ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(results_dir / "training_curves.png", dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  그래프: {results_dir / 'training_curves.png'}")

    # 예측 시각화
    fig, ax = plt.subplots(figsize=(14, 4))
    n_show = min(2000, len(test_preds))
    ax.plot(test_gts[:n_show], 'b-', alpha=0.7, linewidth=1, label='Ground Truth')
    ax.plot(test_preds[:n_show], 'r-', alpha=0.7, linewidth=1, label='Predicted')
    ax.set_xlabel('Frame')
    ax.set_ylabel('Amplitude')
    ax.set_title(f'SVD Test Prediction (corr={test_corr:.4f})')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(results_dir / "prediction.png", dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  예측: {results_dir / 'prediction.png'}")

    print("\n완료!")


if __name__ == "__main__":
    main()
