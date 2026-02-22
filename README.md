# 마이크 음성으로부터 EGG 신호 예측 (졸업작품)

## 프로젝트 개요

이 프로젝트는 **마이크로 녹음한 음성 신호(MIC)로부터 성문파(EGG, Electroglottography) 신호를 딥러닝으로 예측**하는 연구입니다.

EGG는 성대의 접촉 면적 변화를 측정하는 신호로, 발성 분석·음성 장애 진단·성악 교육 등에 활용됩니다. 하지만 EGG 측정에는 전용 센서를 목에 부착해야 하므로 일상적인 사용이 어렵습니다. 이 프로젝트의 목표는 **일반 마이크만으로 EGG에 준하는 성대 접촉 정보를 추정**하여, 별도의 센서 없이도 발성 패턴 분석이 가능하게 하는 것입니다.

### 핵심 아이디어

```
마이크 음성 (MIC) ──→ [ 딥러닝 모델 ] ──→ 예측 EGG 신호
                         ↑
              학습: SVD 데이터셋 (MIC + EGG 동시 녹음)
```

MIC 신호와 EGG 신호는 같은 발성에서 동시에 녹음되므로, 같은 시간 위치의 MIC→EGG 매핑을 학습합니다. 학습이 완료되면 마이크 입력만으로 EGG를 추정할 수 있습니다.

---

## 환경

| 항목 | 내용 |
|------|------|
| OS | Ubuntu 25.10 |
| GPU | NVIDIA RTX 5080 (16.6GB VRAM) |
| Framework | PyTorch 2.10.0+cu128 |
| Python | 3.11 |
| 패키지 관리 | Conda (EGGDML 환경) |

---

## 데이터셋

### Saarbrücken Voice Database (SVD)

독일 자를란트 대학교에서 수집한 음성 데이터베이스입니다. 원래는 음성 장애 진단용이지만, 이 프로젝트에서는 **건강한 화자 687명의 데이터만 사용**했습니다.

| 항목 | 내용 |
|------|------|
| 화자 수 | 687명 (건강) |
| 녹음 형태 | MIC(마이크)와 EGG(성문파) **동시 녹음** |
| 원본 샘플레이트 | 50,000 Hz |
| 사용 샘플레이트 | 16,000 Hz (다운샘플링) |
| 파일 형식 | IFF (FORM/DS16) — `.nsp`(음성) / `.egg`(성문파) |
| 발화 종류 | 모음 지속 발성 + 문장 발화 |
| 총 파일 쌍 | 9,565개 (MIC-EGG 페어) |

### 데이터 분할 (Speaker-Independent Split)

모델이 **학습에서 본 적 없는 화자**에 대해서도 작동하는지 평가하기 위해, 화자 단위로 분할했습니다. 같은 화자의 데이터가 학습과 테스트에 동시에 들어가면, 화자의 고유 특성을 암기하는 것만으로도 높은 점수를 받을 수 있기 때문입니다.

| 분할 | 화자 수 | 파일 수 | 비율 |
|------|--------|--------|------|
| Train | 549 | 7,645 | 80% |
| Validation | 68 | 946 | 10% |
| Test | 70 | 974 | 10% |

### NSP/EGG 파일 리더

SVD 데이터셋의 파일 형식은 표준적인 WAV가 아니라 IFF(Interchange File Format) 기반의 독자 포맷입니다. `utils/nsp_reader.py`에서 이 포맷을 파싱합니다.

```
IFF 구조:
  FORM/DS16
  ├── HEDR 청크 → 샘플레이트 (offset 20-24, little-endian uint32)
  └── SDA_ 청크 → 오디오 데이터 (int16 배열)
```

int16 원본 데이터를 32768로 나누어 float32 [-1, 1] 범위로 정규화하고, librosa를 사용하여 50kHz → 16kHz로 리샘플링합니다. 이후 파일별로 z-score 정규화(평균=0, 분산=1)를 적용합니다.

---

## 전처리 파이프라인

```
원본 파일 (.nsp/.egg, 50kHz, int16)
    ↓
float32 변환 + [-1,1] 정규화
    ↓
16kHz 리샘플링 (librosa)
    ↓
파일별 z-score 정규화 (mean=0, std=1)
    ↓
슬라이딩 윈도우로 분할
    ↓
(MIC 윈도우, EGG 윈도우) 쌍 생성
```

윈도우 길이와 hop 길이는 실험마다 다릅니다. 각 윈도우 쌍이 하나의 학습 샘플이 됩니다.

---

## 모델 아키텍처

총 4가지 모델을 설계하고 실험했습니다.

### 1. WaveNet (Baseline / Exp1 / Exp1b)

**파일**: `ai-model/model/wavenet_egg.py`

Google DeepMind의 WaveNet 구조를 기반으로 한 **causal(인과적) dilated convolution** 모델입니다.

```
Input [B, 1, T]
    ↓
Input Conv (1→C)
    ↓
WaveNet Block ×N
  ├── Causal Dilated Conv → tanh (filter)
  ├── Causal Dilated Conv → sigmoid (gate)
  ├── filter ⊗ gate (gated activation)
  ├── → Skip Connection (1×1 conv)
  └── → Residual Connection (1×1 conv + BN)
    ↓
Skip Sum
    ↓
Self-Attention (Multi-Head)
    ↓
Output Conv (C→1)
    ↓
Output [B, 1, T]
```

**Causal convolution**: 현재 시점 이전의 데이터만 사용합니다. 오디오 생성(TTS)에서는 미래 정보를 사용할 수 없으므로 필수적이지만, 이 프로젝트처럼 전체 입력이 이미 주어진 경우에는 불필요한 제약입니다. 이 한계는 이후 실험에서 해결합니다.

**Gated activation**: `tanh(filter) ⊗ sigmoid(gate)` 형태로, filter가 특징을 추출하고 gate가 얼마나 통과시킬지 제어합니다. WaveNet 원논문에서 오디오 신호 모델링에 효과적임이 입증된 구조입니다.

**Dilated convolution**: dilation을 1, 2, 4, 8, ... 로 지수적으로 증가시켜 파라미터 수를 크게 늘리지 않으면서 receptive field(수용 영역)를 넓힙니다.

### 2. TCN-UNet (Exp2, 중단)

**파일**: `ai-model/model/tcn_unet.py`

U-Net 인코더-디코더에 TCN(Temporal Convolutional Network) 블록을 결합한 모델입니다.

```
Input [B, 1, T]
    ↓
DownBlock ×4 (인코더, 채널: 64→128→256→512)
  └── TCN Block ×2 + MaxPool1d(2)
    ↓
Bottleneck (Attention)
    ↓
UpBlock ×4 (디코더, skip connection으로 인코더와 연결)
  └── Upsample + Concat(skip) + TCN Block ×2
    ↓
Output Conv (64→1)
    ↓
Output [B, 1, T]
```

Multi-scale feature extraction이 핵심으로, 다양한 해상도에서 특징을 추출합니다. 하지만 29.4M 파라미터로 너무 크고, AMP(Mixed Precision)와의 호환 문제로 중단했습니다. 자세한 시행착오는 아래 실험 섹션에 기술합니다.

### 3. EfficientEGGNet (Exp3, **최고 성능**)

**파일**: `ai-model/model/efficient_egg.py`

Exp2의 교훈을 반영하여 설계한 **non-causal dilated CNN**입니다. WaveNet의 gated activation + skip connection 구조를 유지하되, causal 제약을 제거하고 GroupNorm을 사용합니다.

```
Input [B, 1, T]
    ↓
Input Conv (1→C, GELU, 3×1 conv)
    ↓
DilatedBlock ×24  (3 stacks × 8 layers)
  ├── Symmetric Padding (non-causal)
  ├── Dilated Conv → tanh (filter)
  ├── Dilated Conv → sigmoid (gate)
  ├── filter ⊗ gate
  ├── → Skip (1×1 conv)
  └── → Residual (1×1 conv + GroupNorm)
    ↓
Skip Sum
    ↓
Output Conv (GELU → C→C → GELU → Dropout → C→1)
    ↓
Output [B, 1, T]
```

**Non-causal의 의미**: 양방향 맥락을 모두 사용합니다. `padding = dilation × (kernel_size - 1) / 2`로 symmetric padding을 적용하여, 입력과 출력의 시간 길이가 동일하면서 과거와 미래 정보를 모두 활용합니다. EGG 예측에서는 전체 입력 윈도우가 이미 주어져 있으므로 양방향 정보를 쓰는 것이 자연스럽습니다.

**GroupNorm**: BatchNorm 대신 사용합니다. AMP(float16)에서 InstanceNorm이 수치 불안정을 일으킨 경험(Exp2)을 반영했습니다. GroupNorm은 배치 크기에 독립적이고 AMP에서도 안정적입니다.

**Receptive Field 계산**:
```
3 stacks × 8 layers, dilation = 2^0, 2^1, ..., 2^7 (각 stack)
RF = 1 + Σ(stack) Σ(layer) 2 × 2^layer
   = 1 + 3 × 2 × (2^8 - 1)
   = 1 + 3 × 510 = 1531 samples (96ms)
```

### 4. MultiInputEGGNet (Exp4)

**파일**: `ai-model/model/multi_input_egg.py`

이중 경로 아키텍처로, raw waveform과 mel spectrogram을 동시에 입력받습니다.

```
Input [B, 1, T]
    ├── Path 1: Raw Waveform → Dilated CNN (30 layers, 3 stacks)
    │    └── Skip connections → 1D features
    ├── Path 2: Mel Spectrogram (torchaudio)
    │    └── 2D CNN (3 layers) → 1D projection
    ↓
Fusion (Path1 + Path2 합산)
    ↓
Output Conv → [B, 1, T]
```

Mel spectrogram은 torchaudio의 `MelSpectrogram`으로 실시간 추출합니다. 주파수 영역의 구조적 정보(포먼트, 배음 구조 등)를 활용하려는 시도였습니다.

---

## 손실 함수

### MSE (Mean Squared Error)

```python
MSE = (1/N) Σ (pred_i - target_i)²
```

기본적인 회귀 손실입니다. 신호의 절대적 크기 차이를 줄이는 데 효과적이지만, 파형의 "모양"이 비슷한지(상관관계)를 직접 최적화하지는 않습니다.

### Correlation Loss

```python
CorrLoss = 1 - PearsonCorrelation(pred, target)
```

Pearson 상관계수를 직접 최적화합니다. 신호의 크기보다 패턴(모양)의 유사성에 집중합니다. 미분 가능하도록 구현:

```python
p_centered = pred - pred.mean()
t_centered = target - target.mean()
numerator = (p_centered * t_centered).sum()
denominator = sqrt(sum(p_centered²) * sum(t_centered²) + ε)
corr = numerator / denominator
loss = 1 - corr
```

### Combined Loss

```python
Loss = α × MSE + (1 - α) × CorrLoss
```

두 손실의 가중합입니다. α 값은 실험에 따라 조정했습니다.

| 실험 | α (MSE 비중) | Corr 비중 |
|------|-------------|-----------|
| Baseline | 1.0 (MSE only) | 0.0 |
| Exp1, Exp1b | 0.5 | 0.5 |
| Exp3, Exp4 | 0.3 | 0.7 |

**α=0.3으로 Corr 비중을 높인 이유**: 평가 지표가 Pearson Correlation이므로, 손실 함수도 이에 맞춰 최적화하는 것이 효과적이었습니다. 다만 MSE를 완전히 제거하면 신호의 스케일이 불안정해지므로 30% 비중을 유지했습니다.

---

## 실험 과정과 시행착오

### 실험 0: Baseline — WaveNet + MSE

**목표**: 기본 구조로 MIC→EGG 예측이 가능한지 확인

| 설정 | 값 |
|------|------|
| 모델 | WaveNet (causal, 72K params) |
| Window | 192 samples (12ms) |
| Hop | 192 (overlap 없음) |
| Loss | MSE only |
| LR | 0.001, ExponentialLR (γ=0.98) |
| Batch | 128 |
| 학습 윈도우 수 | 2,293,686 |

**결과**: Test Corr = **0.6662**

초기 목표였던 0.5를 크게 상회하여, MIC→EGG 예측이 딥러닝으로 실현 가능함을 확인했습니다. 하지만 Window 192(12ms)는 F0=100Hz 기준으로 약 1.2 주기에 불과하여, 피치의 주기적 패턴을 충분히 학습하기 어려운 근본적 한계가 있었습니다.

---

### 실험 1: Larger WaveNet + Combined Loss

**가설**: 모델을 키우고 Correlation Loss를 추가하면 크게 개선될 것

| 변경 | Baseline → Exp1 |
|------|-----------------|
| Layers | 8 → 12 |
| Channels | 32 → 64 |
| Attention Heads | 4 → 8 |
| Dropout | 0.2 → 0.4 |
| Loss | MSE → 0.5·MSE + 0.5·CorrLoss |
| LR | 0.001 → 0.0005, CosineAnnealingLR |
| 파라미터 | 72K → 419K (5.8배) |

**결과**: Test Corr = **0.6784** (+0.012)

**실패 분석**: 파라미터를 거의 6배로 늘렸는데 개선폭이 +0.012에 불과했습니다. CorrLoss가 약간의 기여를 했지만, 근본적인 문제는 모델 크기가 아니라 **Window 길이**였습니다. 12ms 안에는 음성의 피치 주기가 1~2개밖에 없어, 모델이 아무리 커도 "지금 이 순간의 발성이 어떤 상태인지" 파악할 맥락이 부족했습니다.

**교훈**: 모델 크기를 늘리는 것보다 **입력 윈도우를 늘려 더 많은 맥락을 제공**하는 것이 중요합니다.

---

### 실험 1b: Window 확장 (192 → 1024)

**가설**: 더 긴 윈도우(64ms, ~6.4 주기)로 피치 패턴을 더 잘 학습할 것

```
F0 = 100Hz → 주기 = 160 samples (10ms)
Window 192  = ~1.2 주기 (너무 짧음)
Window 1024 = ~6.4 주기 (여러 주기 포함)
```

| 변경 | Exp1 → Exp1b |
|------|-------------|
| Window | 192 → 1024 |
| Hop | 192 → 512 (50% overlap) |
| Batch | 128 → 64 (메모리) |
| 학습 윈도우 수 | 2.29M → 850K |

**결과**: Test Corr = **0.6763** (+0.010, Exp1보다 오히려 -0.002)

**실패 분석**: 두 가지 문제가 있었습니다.

1. **Causal convolution의 한계**: WaveNet은 causal(인과적) 구조라서 현재 시점 이전의 데이터만 봅니다. 윈도우를 1024로 늘려도, 출력의 각 시점은 그 앞쪽만 참조할 수 있어 양방향 맥락을 활용하지 못합니다.

2. **학습 데이터 다양성 감소**: 윈도우가 길어지면서 hop도 늘어나, 전체 윈도우 수가 2.29M → 850K로 줄었습니다. 모델이 볼 수 있는 다양한 패턴이 줄어든 것입니다.

**교훈**: 긴 윈도우의 이점을 살리려면 **non-causal(양방향) 모델**이 필요합니다.

---

### 실험 2: TCN-UNet (중단됨)

**가설**: U-Net의 multi-scale 구조 + non-causal TCN으로 양방향 맥락 활용

**설계**:
- U-Net 인코더(4단계 다운샘플링) → Attention Bottleneck → 디코더(4단계 업샘플링)
- 각 단계에 TCN 블록 사용 (non-causal)
- 29.4M 파라미터

**시행착오 1 — 디코더 채널 불일치 버그**:

U-Net의 skip connection에서 인코더와 디코더의 채널 수가 맞지 않는 버그가 있었습니다. 인코더의 출력 채널을 디코더에서 concat할 때 차원 계산이 틀려 RuntimeError가 발생했습니다. 채널 수를 명시적으로 추적하도록 수정했습니다.

**시행착오 2 — InstanceNorm + AMP → NaN**:

원래 TCN 블록에 InstanceNorm을 사용했는데, AMP(Automatic Mixed Precision, float16)와 함께 사용하면 epoch 3에서 loss가 NaN이 되었습니다. InstanceNorm이 float16의 좁은 수치 범위에서 정규화 계산 중 오버플로우를 일으킨 것입니다.

해결: InstanceNorm → **GroupNorm** (groups=8)으로 교체하고, AMP를 비활성화했습니다.

**시행착오 3 — 학습 속도 문제**:

AMP 없이 29.4M 파라미터 모델을 학습하니 **에폭당 ~19분**이 소요되었습니다. 80 에폭이면 ~25시간이고, 하이퍼파라미터 튜닝까지 고려하면 실험 반복이 불가능한 수준이었습니다.

5 에폭만 학습한 시점에서 Val Corr ~0.692로 유망한 신호를 보였지만, 실용적이지 않아 **중단**하고 더 가벼운 모델을 설계하기로 했습니다.

**교훈**:
- Non-causal + multi-scale은 유망하다 (5 에폭만에 0.692)
- 하지만 모델이 너무 크면 실험 반복이 불가능
- InstanceNorm은 AMP와 호환 문제 → GroupNorm 사용
- **가벼운 non-causal 모델 + 긴 window + AMP** 조합이 필요

---

### 실험 3: EfficientEGGNet ⭐ (최고 성능)

**핵심 전략**: Exp2에서 얻은 교훈을 모두 반영

| 전략 | 이전 실험의 문제 | Exp3의 해결 |
|------|----------------|------------|
| Non-causal conv | Exp1b: causal이라 긴 window 활용 부족 | 양방향 symmetric padding |
| 가벼운 모델 | Exp2: 29M params, 너무 느림 | 1.8M params (16배 축소) |
| AMP 활성화 | Exp2: InstanceNorm이 AMP와 충돌 | GroupNorm으로 안정적 AMP |
| 긴 Window | Baseline/Exp1: 192(12ms), 1~2주기만 | 4096(256ms), ~25주기 포함 |
| CorrLoss 비중 ↑ | Exp1: 50% corr loss | 70% corr loss |

| 설정 | 값 |
|------|------|
| 모델 | EfficientEGGNet (non-causal, 1.8M params) |
| 구조 | 3 stacks × 8 layers = 24 dilated blocks |
| Channels | 96 |
| Window | 4096 samples (256ms) |
| Hop | 2048 (50% overlap) |
| RF | 1531 samples (96ms) |
| Loss | 0.3·MSE + 0.7·CorrLoss |
| LR | 0.001, OneCycleLR |
| AMP | 활성화 |
| Batch | 32 |

**결과**: Test Corr = **0.7163** (+0.050 vs Baseline)

| Metric | 값 |
|--------|------|
| Best Val Corr | 0.7229 |
| **Test Corr** | **0.7163** |
| Test MSE | 0.1893 |
| Test RMSE | 0.3982 |
| R² | 0.5131 |
| 학습 시간 | 248분 (best epoch 10) |

**왜 성공했나**:

1. **Non-causal**: 양방향 맥락으로 EGG 신호의 대칭적 특성 활용. 성대 접촉은 열리는 순간과 닫히는 순간 모두의 정보가 필요합니다.
2. **Window 4096 (256ms)**: F0 100Hz 기준 약 25주기를 포함하여, 피치 패턴의 반복 구조를 충분히 학습 가능.
3. **적절한 모델 크기**: 1.8M으로 과적합 없이 충분한 표현력 확보. RTX 5080에서 AMP로 빠르게 학습.
4. **OneCycleLR**: 초반에 LR을 빠르게 올려 좋은 방향을 찾고, 후반에 세밀하게 조정.
5. **CorrLoss 70%**: 평가 지표(Pearson Corr)를 직접 최적화.

---

### 실험 4: Multi-Input + Data Augmentation

**가설**: Mel spectrogram의 주파수 정보를 추가하고, Data Augmentation으로 일반화 성능을 높이면 Exp3을 넘길 수 있을 것

| 추가 요소 | 설정 |
|-----------|------|
| Mel Spectrogram 경로 | 2D CNN (n_mels=64, n_fft=512) |
| Noise Injection | 50% 확률, σ=0.01 |
| Gain Variation | 30% 확률, ×0.8~1.2 |
| Sign Flip | 30% 확률 |
| 파라미터 | 2.4M (+33%) |
| RF | 6139 samples (384ms, 4배) |

**결과**: Test Corr = **0.7137** (Exp3보다 -0.0026)

**실패 분석**:

1. **Mel spectrogram이 추가 정보를 제공하지 못함**: Raw waveform에서 이미 주파수 정보를 학습하고 있었습니다. Mel spectrogram은 중복 정보에 가까웠고, 추가 파라미터(+33%)의 오버헤드만 발생했습니다.

2. **Data augmentation의 제한적 효과**: MIC→EGG는 deterministic한 물리적 매핑입니다. 같은 MIC 신호에는 항상 같은 EGG가 대응되므로, noise injection이나 gain variation이 학습에 도움이 되기보다 수렴을 방해했습니다. 실제로 58 에폭까지 아주 느리게 개선되었습니다.

3. **RF 확장(96ms→384ms)의 한계**: 4배 더 넓은 receptive field를 가졌지만 성능 개선은 없었습니다. 96ms(1531 samples)면 이미 충분한 맥락이었던 것으로 보입니다.

**교훈**: 이 태스크에서 더 나아가려면 입력 표현의 변화가 아니라 근본적으로 다른 접근이 필요합니다.

---

## 자동화 실험 Phase 1 (Exp5 ~ Exp12)

Exp3(EfficientEGGNet)을 기반으로, 다양한 아키텍처와 하이퍼파라미터를 자동 탐색했습니다. `auto_experiment.py` 스크립트로 8개 실험을 순차 실행했습니다.

### 공통 설정 (Exp3 기반)

| 항목 | 값 |
|------|------|
| Base Model | EfficientEGGNet |
| Loss | 0.2·MSE + 0.8·CorrLoss |
| Optimizer | AdamW (weight_decay=1e-4) |
| Scheduler | OneCycleLR |
| AMP | 활성화 |
| Early Stopping | patience=15 |

### 실험별 결과

| 실험 | 핵심 변경 | Test Corr | 비고 |
|------|-----------|-----------|------|
| Exp5 | 고품질 데이터 필터링 | 0.6956 | 데이터 줄어 오히려 하락 |
| Exp6 | Transformer | 0.7030 | Positional encoding 추가 |
| **Exp7** | **Conformer** | **CUDA OOM** | **4GB 할당 시도 → 실패** |
| Exp9 | Curriculum Learning | 0.7126 | 쉬운→어려운 순서 학습 |
| Exp10 | Large Efficient (5.99M) | 0.7205 | channels=128, layers=30 |
| **Exp11** | **Multiscale (5.99M)** | **0.7484** | **window=8192, hop=4096** |
| **Exp8** | **wav2vec2 Fine-tune** | **-0.0002** | **90M params, 학습 완전 실패** |
| Exp12 | Ensemble (Exp10+11) | 0.7191 | 단일 모델보다 낮음 |

### 핵심 교훈

- **Exp11 (Multiscale)**: Window=8192(512ms)로 확장하고 모델을 키운 것이 결정적. Exp3(0.7163) 대비 +0.032 향상
- **Exp7 (Conformer)**: Self-attention의 O(N²) 메모리로 16GB VRAM에서 OOM. 긴 시퀀스에는 attention 없는 CNN이 유리
- **Exp8 (wav2vec2)**: 90M params의 사전학습 모델이 16kHz EGG 예측에는 전혀 작동하지 않음 (Corr ≈ 0)
- **Exp12 (Ensemble)**: 두 모델을 합쳐도 개선 없음. 이 태스크에서는 단일 모델 최적화가 효과적

---

## 자동화 실험 Phase 2 (Exp13 ~ Exp20): 목표 Corr ≥ 0.8

Exp11(0.7484)을 베이스라인으로, **Corr ≥ 0.8 달성**을 목표로 `auto_experiment_v2.py`로 체계적 탐색을 진행했습니다.

### 시도한 전략과 결과

| 실험 | 전략 | Test Corr | Δ Exp11 |
|------|------|-----------|---------|
| Exp13 | 정규화 강화 (dropout=0.1, wd=5e-4) | 0.7495 | +0.001 |
| Exp14 | Data Augmentation (noise/gain/shift) | 0.7399 | -0.009 |
| Exp15 | Mixup (α=0.2) | 0.7522 | +0.004 |
| Exp16 | SE Block (channel attention) | 0.7497 | +0.001 |
| Exp17 | CBAM (spatial + channel attention) | 0.7521 | +0.004 |
| Exp18 | Deeper Model (40 layers, 6.57M) | 0.7500 | +0.002 |
| Exp19 | Cosine Annealing + Warmup | 0.7491 | +0.001 |
| **Exp20** | **Progressive Window Resizing** | **0.8249** | **+0.077** |

### Exp20: Progressive Window Resizing ⭐

0.75 부근에서 정체되던 성능을 **Corr=0.8249**로 끌어올린 핵심 전략입니다.

**아이디어**: 작은 window에서 기본 패턴을 학습한 뒤, 점진적으로 window를 키워 더 넓은 맥락을 학습합니다.

```
Phase 1: window=4096  (256ms)  → batch=32, 20 epochs, lr=0.001
Phase 2: window=8192  (512ms)  → batch=16, 40 epochs, lr=0.0005
Phase 3: window=16384 (1024ms) → batch=8,  40 epochs, lr=0.0003
```

| Phase | Window | Epochs | Best Val Corr |
|-------|--------|--------|---------------|
| 1 | 4096 | 20 | 0.7123 |
| 2 | 8192 | 40 | 0.7564 |
| 3 | 16384 | 16 (early stop) | **0.8218** |

**총 76 epochs**, Phase 3에서 16 epoch 만에 목표 달성.

### 검증 후 밝혀진 사실 — 진짜 원인은 Window 크기

공정 비교를 위해 **동일 window에서 Exp11과 Exp20을 재평가**한 결과:

| Window | Exp11 | Exp20 | 차이 |
|--------|-------|-------|------|
| 8192 | 0.7484 | 0.7501 | +0.002 |
| **16384** | **0.8240** | **0.8248** | **+0.001** |

같은 window=16384에서 **Exp11도 0.824 달성**. 즉, Progressive Training 자체의 기여는 미미하고 (+0.001), **긴 Context Window (16384 = 1초)**가 성능 향상의 핵심 원인이었습니다.

---

## 실험 결과 총괄

### 모델 발전 과정

| 실험 | 모델 | 파라미터 | Window | Test Corr | 핵심 변경 |
|------|------|----------|--------|-----------|-----------|
| Baseline | WaveNet (causal) | 72K | 192 (12ms) | 0.6662 | 초기 모델 |
| Exp1 | Larger WaveNet | 419K | 192 (12ms) | 0.6784 | 모델 크기 증가 |
| Exp1b | WaveNet + Long Window | 419K | 1024 (64ms) | 0.6763 | window 확장 |
| Exp2 | TCN-UNet | 29.4M | 1024 (64ms) | 중단 | 너무 큰 모델 |
| Exp3 | EfficientEGGNet | 1.8M | 4096 (256ms) | 0.7163 | Non-causal CNN |
| Exp4 | Multi-Input | 2.4M | 4096 (256ms) | 0.7137 | Mel spectrogram 추가 |
| Exp5 | High Quality Data | 1.8M | 4096 (256ms) | 0.6956 | 데이터 필터링 |
| Exp6 | Transformer | — | 4096 (256ms) | 0.7030 | Self-attention |
| Exp7 | Conformer | — | 8192 (512ms) | OOM | CUDA 메모리 초과 |
| Exp8 | wav2vec2 | 90M | 8192 (512ms) | ≈ 0 | 학습 실패 |
| Exp9 | Curriculum | 1.8M | 4096 (256ms) | 0.7126 | 난이도 순 학습 |
| Exp10 | Large Efficient | 5.99M | 4096 (256ms) | 0.7205 | channels/layers 증가 |
| **Exp11** | **Multiscale** | **5.99M** | **8192 (512ms)** | **0.7484** | **Window 확장** |
| Exp13–19 | 다양한 정규화/attention | 5.99M | 8192 (512ms) | 0.74~0.75 | 정체 |
| **Exp20** | **Progressive Window** | **5.99M** | **16384 (1024ms)** | **0.8249** | **🏆 목표 달성** |

### 성능 변화 그래프

```
Corr
0.83 │                                                          ★ Exp20 (0.8249)
     │
0.80 │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ 목표선 (0.8)
     │
0.75 │                              ● Exp11 (0.7484)
     │    
0.72 │                  ● Exp3 (0.7163)
     │
0.68 │  ● Exp1 (0.6784)
0.67 │ ● Base (0.6662)
     └────────────────────────────────────────────────────────────→ 실험
      Base  Exp1  Exp3   Exp5~10   Exp11  Exp13~19  Exp20
```

### 효과적이었던 전략

| 전략 | 개선폭 | 실험 |
|------|--------|------|
| Causal → Non-causal 전환 | +0.038 | Exp1b → Exp3 |
| Window 확장 (192 → 4096) | +0.038 | Baseline → Exp3 |
| Window 확장 (4096 → 8192) | +0.028 | Exp3 → Exp11 |
| **Window 확장 (8192 → 16384)** | **+0.077** | **Exp11 → Exp20** |
| CorrLoss 비중 증가 | ~+0.01 | Exp1 → Exp3 |
| 모델 스케일업 (1.8M → 6M) | +0.004 | Exp3 → Exp10 |

### 효과 제한적이었던 전략

| 전략 | 결과 | 실험 |
|------|------|------|
| 모델 크기만 증가 (72K→419K) | +0.012 | Exp1 |
| 매우 큰 모델 (29M, 90M) | 불안정/실패 | Exp2, Exp8 |
| Mel spectrogram 추가 경로 | 개선 없음 | Exp4 |
| Data augmentation (noise/gain) | 수렴 지연 | Exp4, Exp14 |
| Attention 모듈 (SE, CBAM) | +0.001~0.004 | Exp16, Exp17 |
| 정규화 강화 (dropout/wd) | +0.001 | Exp13 |
| Ensemble | 오히려 하락 | Exp12 |

### 핵심 발견 요약

1. **Window 크기가 가장 중요한 요소**: 192 → 4096 → 8192 → 16384로 확장할 때마다 가장 큰 성능 향상이 발생. 모델이 더 긴 시간 맥락을 볼수록 성대 접촉 패턴을 더 잘 예측
2. **화자독립 분할의 영향**: 화자 겹침이 있으면 Corr ≈ 0.95로 측정되지만, 화자독립 분할 시 0.66으로 하락. 정직한 평가가 필수
3. **Non-causal > Causal**: EGG 예측은 전체 입력이 주어진 태스크이므로, 양방향 맥락을 활용하는 것이 자연스럽고 효과적
4. **큰 모델 ≠ 좋은 성능**: 5.99M params면 충분. 그 이상(29M, 90M)은 오히려 불안정하거나 실패
5. **Data Augmentation 비효과적**: MIC→EGG는 deterministic 물리적 매핑이므로, noise injection은 수렴만 방해

---

## 검증 결과

Exp20(Corr=0.8249)의 신뢰성을 검증했습니다.

### 1. 데이터 분할 검증

| 항목 | 값 |
|------|------|
| 분할 방식 | Speaker-Independent (seed=42) |
| Train / Val / Test 화자 | 549 / 68 / 70 |
| 화자 겹침 (T∩V, T∩Te, V∩Te) | 모두 0 |
| **Data Leak** | **없음** |

### 2. 과적합 점검 (Exp20, window=8192)

| Split | Corr | MSE |
|-------|------|-----|
| Train | 0.7721 | 0.1508 |
| Val | 0.7583 | 0.1934 |
| Test | 0.7501 | 0.1906 |
| Train-Test Gap | **+0.022** | — |

Train-Test gap 0.022로 **과적합 징후 없음**. 건전한 일반화 확인.

### 3. 화자별 성능 분포 (Exp20, window=16384)

| 구간 | 화자 수 | 비율 |
|------|---------|------|
| Corr ≥ 0.9 | 15/70 | 21.4% |
| Corr ≥ 0.8 | 50/70 | **71.4%** |
| Corr ≥ 0.7 | 63/70 | **90.0%** |
| Corr ≥ 0.5 | 69/70 | 98.6% |
| Corr < 0.5 | 1/70 | 1.4% |

- Median speaker Corr = **0.8532**
- 70명 중 1명만 0.5 미만 (Spk 838 = 0.4566)
- 상위 10명: 0.92 ~ 0.95

---

## 발성 유사도 분석 (응용 실험)

학습된 모델을 실제 녹음에 적용하여, 기준 노래와 사용자 노래의 **발성 유사도**를 비교하는 실험도 수행했습니다.

### 데이터
- 기준 파일: 라즈베리파이 녹음 2개 (0000.wav, 0001.wav)
- 사용자 파일: USB 마이크 녹음 2개 (usb_mic_test1_11s.wav, usb_mic_test1_18s.wav)
- 같은 노래를 다른 환경에서 녹음

### DTW (Dynamic Time Warping)로 시간 정렬 후 비교

| 비교 쌍 | Raw Corr | DTW Corr |
|---------|----------|----------|
| Ref 0000 vs User 11s | -0.004 | **0.722** |
| Ref 0000 vs User 18s | 0.004 | **0.643** |
| Ref 0001 vs User 11s | 0.004 | **0.688** |
| Ref 0001 vs User 18s | 0.003 | **0.727** |

### 통계적 검증 (1000회 Shuffle Test)

| 비교 쌍 | DTW Corr | 셔플 평균 | Z-score | p-value |
|---------|----------|----------|---------|---------|
| Ref 0000 vs User 11s | 0.722 | -0.003 | 40.6 | <0.001 |
| Ref 0001 vs User 18s | 0.727 | 0.003 | 48.8 | <0.001 |

모든 쌍에서 Z-score > 40, p < 0.001으로, **유사도가 통계적으로 매우 유의미**함을 확인했습니다.

---

## 프로젝트 구조

```
egg_prediction/
├── ai-model/                       # AI 모델 관련 코드
│   ├── model/                      # 모델 아키텍처 정의
│   │   ├── wavenet_egg.py          # WaveNet (Baseline/Exp1/Exp1b)
│   │   ├── tcn_unet.py            # TCN-UNet (Exp2, 중단)
│   │   ├── efficient_egg.py       # EfficientEGGNet (Exp3~Exp20, 최고 성능)
│   │   ├── multi_input_egg.py     # Multi-Input (Exp4)
│   │   ├── transformer_egg.py     # Transformer (Exp6)
│   │   └── conformer_egg.py       # Conformer (Exp7, OOM)
│   ├── utils/                      # 유틸리티
│   │   ├── dataset.py             # SVD 데이터셋 로더 + speaker split
│   │   └── nsp_reader.py          # SVD NSP/EGG 파일 파서
│   ├── configs/                    # 학습 설정 파일
│   ├── train.py                    # Baseline 학습
│   ├── train_exp1.py ~ exp4.py    # 수동 실험 학습 스크립트
│   ├── auto_experiment.py         # 자동 실험 v1 (Exp5~Exp12)
│   ├── auto_experiment_v2.py      # 자동 실험 v2 (Exp13~Exp20)
│   ├── validate_exp20.py          # Exp20 검증 스크립트
│   ├── analyze_*.py               # 분석 스크립트
│   ├── generate_figures.py        # 결과 시각화
│   ├── EXPERIMENT_REPORT.md       # 실험 상세 보고서
│   └── egg_from_mic/              # 초기 실험 코드 (PTDB 등)
│
├── docs/                           # 프로젝트 문서 및 참고자료
│   └── useful-info.md             # 유용한 도구/정보 모음
│
├── images/                         # 프로젝트 관련 이미지
│
├── server/                         # 서버 코드 (추후 추가 예정)
│
├── app/                            # 앱 코드 (추후 추가 예정)
│
├── data/                           # 데이터 (gitignore)
│   ├── SVD_healthy/               # SVD 건강 화자 데이터
│   └── rpi_recordings/            # 라즈베리파이 녹음
│
├── checkpoints/                    # 모델 체크포인트 (gitignore)
│
└── results/                        # 실험 결과 로그 (gitignore)
```

---

## 실행 방법

### 환경 설정

```bash
conda create -n EGGDML python=3.11
conda activate EGGDML
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install numpy scipy librosa soundfile matplotlib tqdm pyyaml
pip install dtw-python fastdtw  # 유사도 분석용
```

### 데이터 준비

SVD 데이터셋의 건강 화자 데이터를 `data/SVD_healthy/`에 배치합니다. 각 화자 폴더에 `vowels/`과 `sentences/` 하위 디렉토리가 있고, `.nsp`(음성)와 `.egg`(성문파) 파일 쌍이 포함되어야 합니다.

```
data/SVD_healthy/
├── 1/
│   ├── vowels/
│   │   ├── a1.nsp
│   │   ├── a1-egg.egg
│   │   └── ...
│   └── sentences/
│       ├── s1.nsp
│       ├── s1-egg.egg
│       └── ...
├── 10/
└── ...
```

### 학습

```bash
cd ai-model/

# Baseline
python train.py

# 수동 실험 (Exp1~Exp4)
python train_exp3.py

# 자동 실험 v1 (Exp5~Exp12)
python auto_experiment.py

# 자동 실험 v2 (Exp13~Exp20, 목표 Corr ≥ 0.8)
python auto_experiment_v2.py
```

### 검증

```bash
cd ai-model/

# Exp20 모델 검증 (data leak, 과적합, 화자별 분석)
python validate_exp20.py
```

### 유사도 분석

```bash
cd ai-model/

# DTW 기반 유사도 분석
python analyze_dtw_similarity.py

# 스펙트로그램 + 통계 검증
python analyze_spectrogram_validation.py
```

---

## 향후 과제

1. **Corr 0.9 목표**: 현재 0.8249 달성. Window를 더 늘리거나 (32768), multi-resolution 접근으로 추가 개선 가능성 탐색
2. **실시간 추론**: Streaming 방식으로 전환하여 실시간 발성 피드백 시스템에 적용
3. **라즈베리파이 배포**: ONNX 변환 후 Edge 디바이스에서 구동
4. **음성 장애 환자 데이터**: 현재는 건강 화자만 사용. 장애 화자에 대한 성능 검증 필요
5. **다른 데이터셋 일반화**: SVD 외 PTDB-TUG, OpenGlot 등으로 교차 검증
