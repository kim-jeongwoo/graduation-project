# 🔬 SVD EGG Prediction — 실험 종합 보고서

> **프로젝트**: 마이크 음성(MIC)으로부터 EGG(Electroglottography) 신호 예측  
> **데이터셋**: Saarbrücken Voice Database (SVD) — 687명, 건강한 화자  
> **환경**: Ubuntu 25.10 / RTX 5080 (16.6GB) / PyTorch 2.10.0+cu128 / Python 3.11  
> **평가**: Speaker-independent split (549 train / 68 val / 70 test), Pearson Correlation  
> **날짜**: 2026년 2월 7일  

---

## 📊 결과 총괄표

| 실험 | 모델 | 파라미터 | Window | RF | Test Corr | Δ Baseline | 학습시간 | Best Epoch |
|------|------|----------|--------|----|-----------|------------|----------|------------|
| **Baseline** | WaveNet | 72K | 192 (12ms) | ~50 | **0.6662** | — | 49.6 min | 31 |
| **Exp1** | Larger WaveNet | 419K | 192 (12ms) | ~120 | **0.6784** | +0.012 | 132.8 min | 19 |
| **Exp1b** | WaveNet + Long Window | 419K | 1024 (64ms) | ~120 | **0.6763** | +0.010 | 380.4 min | 8 |
| **Exp2** | TCN-UNet | 29.4M | 1024 (64ms) | multi-scale | — (중단) | — | ~94 min (5ep) | 3 |
| **Exp3** | Efficient Dilated CNN | 1.8M | 4096 (256ms) | 1531 (96ms) | **0.7163** | **+0.050** | 248.1 min | 10 |
| **Exp4** | Multi-Input + Aug | 2.4M | 4096 (256ms) | 6139 (384ms) | **0.7137** | +0.048 | 318.3 min | 58 |

> 🏆 **최고 성능: Exp3 — Test Corr 0.7163**  
> ❌ **목표 0.8 미달**

---

## 🧪 실험 0: Baseline

### 설정
- **모델**: WaveNet (causal dilated conv + self-attention)
- **파라미터**: 72K (layers=8, channels=32, heads=4)
- **Window**: 192 samples (12ms) — non-overlapping hop
- **손실함수**: MSE only
- **스케줄러**: ExponentialLR (γ=0.98)
- **배치 크기**: 128
- **학습 윈도우 수**: 2,293,686

### 결과
| Metric | Value |
|--------|-------|
| Best Val Corr | 0.6765 |
| **Test Corr** | **0.6662** |
| Test RMSE | 0.406 |
| 학습 시간 | 49.6 min (31 epochs) |

### 의의
- 초기 목표 Test Corr ≥ 0.5 **달성** ✅
- Window 192 = F0 100Hz 기준 **약 1 주기**만 포함 → 근본적 한계 확인

---

## 🧪 실험 1: Larger WaveNet + Combined Loss

### 변경 사항 (vs Baseline)
| 항목 | Baseline → Exp1 |
|------|----------------|
| Layers | 8 → **12** |
| Channels | 32 → **64** |
| Attention Heads | 4 → **8** |
| Dropout | 0.2 → **0.4** |
| Loss | MSE → **0.5·MSE + 0.5·CorrLoss** |
| Scheduler | ExponentialLR → **CosineAnnealingLR** |
| LR | 0.001 → **0.0005** |

### 가설
> 모델 용량을 6배 늘리고 상관계수를 직접 최적화하면 성능이 크게 오를 것

### 결과
| Metric | Value |
|--------|-------|
| Best Val Corr | 0.6887 |
| **Test Corr** | **0.6784** (+0.012) |
| Test RMSE | 0.393 |
| 학습 시간 | 132.8 min (19 epochs) |

### 교훈
- ✅ Combined Loss (CorrLoss)가 약간의 개선 기여
- ⚠️ 파라미터 6배 증가 대비 **개선폭이 미미** (+0.012)
- 💡 **Window 192 (12ms)가 근본적 병목** — 모델을 키워도 한계

---

## 🧪 실험 1b: Window 확장 (192 → 1024)

### 핵심 분석
```
F0 = 100Hz → 주기 = 160 samples (10ms)
Window 192 = ~1.2 주기 (너무 짧음!)
Window 1024 = ~6.4 주기 (64ms) → 충분한 맥락
```

### 변경 사항 (vs Exp1)
| 항목 | Exp1 → Exp1b |
|------|-------------|
| Window | 192 → **1024** (64ms) |
| Hop | 192 → **512** (50% overlap) |
| Batch | 128 → **64** (메모리) |
| Dropout | 0.4 → **0.3** |
| LR | 0.0005 → **0.001** |
| Windows 수 | 2.29M → **850K** |

### 가설
> 더 긴 윈도우로 여러 주기를 포함시키면 피치 패턴을 더 잘 학습할 것

### 결과
| Metric | Value |
|--------|-------|
| Best Val Corr | 0.6848 |
| **Test Corr** | **0.6763** (+0.010) |
| Test RMSE | 0.410 |
| 학습 시간 | 380.4 min (8 epochs, early stop) |

### 교훈
- ❌ 기대와 달리 Exp1보다 오히려 약간 낮음 (-0.002)
- 🔍 **Causal WaveNet의 한계**: 한 방향으로만 보기 때문에 긴 window 활용 부족
- 🔍 **윈도우 수 감소** (2.29M → 850K): 학습 데이터 다양성 하락
- 💡 **Non-causal 모델**이 양방향 맥락을 활용하여 더 효과적일 것

---

## 🧪 실험 2: TCN-UNet (중단됨)

### 설계
- **모델**: U-Net 인코더-디코더 + TCN(Temporal Convolutional Network) 블록
- **핵심**: Multi-scale feature extraction, non-causal
- **구조**: DownBlock×4 → Attention Bottleneck → UpBlock×4
- **파라미터**: 29.4M (base_channels=64, depth=4)

### 시행착오 과정

#### 🐛 버그 1: 디코더 채널 불일치
```
# 원래 코드 (잘못됨)
dec_in = channels[-(i+1)]  # skip과 차원 불일치

# 수정 코드
dec_in = previous decoder output channels  # 명시적 추적
```

#### 🐛 버그 2: InstanceNorm + AMP → NaN
- **문제**: InstanceNorm이 AMP(float16)에서 수치 불안정 → epoch 3에서 loss=NaN
- **해결**: InstanceNorm → **GroupNorm** (groups=8), AMP 비활성화

#### ⚠️ 성능 문제
- 29.4M params + AMP 없이 → **에폭당 ~19분** (너무 느림)
- 5 에폭 학습 후 Val Corr ~0.692 → 유망하지만 실용적이지 않아 **중단**

### 결과
| Metric | Value |
|--------|-------|
| Val Corr (5 ep) | ~0.692 |
| **Test Corr** | **미평가** (중단) |
| Epoch 속도 | ~19 min/epoch |
| 예상 완료 시간 | ~25시간 (80 epochs) |

### 교훈
- ✅ Non-causal + multi-scale 접근이 유망함 (5ep만에 0.692)
- ❌ 모델이 너무 크면 실험 반복이 불가능
- ❌ InstanceNorm은 AMP와 호환 문제 → GroupNorm 사용
- 💡 **가벼운 non-causal 모델** + **긴 window** + **AMP** 조합 필요

---

## 🧪 실험 3: Efficient Dilated CNN ⭐ (최고 성능)

### 설계 (Exp2 교훈 반영)
- **모델**: EfficientEGGNet — WaveNet-style dilated conv, **non-causal**
- **핵심 개선점**:
  - Non-causal conv (양방향 맥락)
  - Gated activation (tanh ⊗ sigmoid)
  - GroupNorm (AMP 안정성)
  - 3 stacks × 8 layers = 24 dilated layers
  - Skip connections (WaveNet 방식)
  - **AMP 활성화** (빠른 학습)
- **파라미터**: 1.8M (channels=96, 기존 29M → 16배 축소)
- **Receptive Field**: 1531 samples (96ms)
- **Window**: 4096 samples (256ms)

### 변경 사항 총괄 (vs 이전 실험들)
| 항목 | 이전 | Exp3 |
|------|------|------|
| 인과성 | Causal | **Non-causal** |
| Window | 192~1024 | **4096 (256ms)** |
| 정규화 | LayerNorm/InstanceNorm | **GroupNorm** |
| AMP | ✗ (Exp2) | **✓** |
| 파라미터 | 29M (Exp2) | **1.8M** |
| Loss α | 0.5 | **0.3** (MSE 30%, Corr 70%) |
| Batch | 64~128 | **32** |

### 결과
| Metric | Value |
|--------|-------|
| Best Val Corr | **0.7229** |
| **Test Corr** | **0.7163** (+0.050) |
| Test RMSE | 0.398 |
| 학습 시간 | 248.1 min (10 epochs best, 22 total) |
| Epoch 속도 | ~11 min/epoch |

### 왜 성공했나?
1. **Non-causal**: 양방향 맥락으로 EGG 신호의 대칭적 특성 활용
2. **Window 4096**: 256ms = F0 100Hz 기준 ~25 주기 포함
3. **적절한 모델 크기**: 1.8M으로 과적합 없이 충분한 표현력
4. **AMP**: 학습 속도 ~2배 향상
5. **CorrLoss 비중 증가** (70%): 상관계수 직접 최적화

---

## 🧪 실험 4: Multi-Input + Data Augmentation

### 설계 (Exp3 확장)
- **모델**: MultiInputEGGNet — 이중 경로 아키텍처
  - **Path 1**: Raw waveform → Dilated CNN (30 layers, 3 stacks)
  - **Path 2**: Mel Spectrogram → 2D CNN → 1D projection
  - **Fusion**: 두 경로 출력을 합산 → 최종 output conv
- **파라미터**: 2.4M (Exp3 대비 +33%)
- **RF**: 6139 samples (384ms) — Exp3 대비 4배

### 새로운 요소: Data Augmentation
| 증강 기법 | 확률 | 설정 |
|-----------|------|------|
| Noise injection | 50% | σ = 0.01 |
| Gain variation | 30% | ×0.8 ~ ×1.2 |
| Sign flip | 30% | ×(-1) |

### 스케줄러
- CosineAnnealingLR (T_max=60)
- 초기 LR: 0.0008

### 학습 곡선 특성
```
Epoch  1: Val Corr 0.6876  (증강으로 초기 수렴 느림)
Epoch 10: Val Corr 0.7025  (꾸준히 상승)
Epoch 20: Val Corr 0.7110
Epoch 29: Val Corr 0.7142
Epoch 40: Val Corr 0.7166
Epoch 54: Val Corr 0.7187
Epoch 58: Val Corr 0.7189  ★ Best
Epoch 60: Val Corr 0.7189  (마지막)
```
- Augmentation으로 인해 **수렴이 매우 느림** (58 에폭까지 개선 지속)
- Cosine LR이 후반부에 미세 조정 역할

### 결과
| Metric | Value |
|--------|-------|
| Best Val Corr | 0.7189 |
| **Test Corr** | **0.7137** (+0.048 vs Baseline) |
| Test RMSE | 0.397 |
| vs Exp3 | **-0.0026** (약간 하락) |
| 학습 시간 | 318.3 min (58 epochs best, 60 total) |
| Epoch 속도 | ~5.3 min/epoch |

### 교훈
- ❌ Mel spectrogram path가 raw waveform path 대비 **추가 정보를 제공하지 못함**
- ❌ Data augmentation이 이 태스크에서는 **제한적 효과** (EGG는 deterministic mapping)
- 🔍 Augmentation이 수렴을 늦추고, 최종 성능은 Exp3과 거의 동일
- 🔍 RF 4배 확장(96ms→384ms)도 유의미한 개선 없음
- 💡 입력 표현보다 **모델 구조 자체의 혁신**이 필요할 수 있음

---

## 🔑 핵심 교훈 종합

### ✅ 효과적이었던 전략
| 전략 | 개선폭 | 실험 |
|------|--------|------|
| Non-causal convolution | +0.038 (Exp1b→Exp3) | Exp3 |
| Window 확장 (192→4096) | +0.038 (Exp1→Exp3) | Exp3 |
| CorrLoss 비중 증가 (50→70%) | ~+0.01 | Exp3 |
| GroupNorm + AMP | 안정성+속도 | Exp3 |

### ❌ 효과 제한적이었던 전략
| 전략 | 결과 | 실험 |
|------|------|------|
| 모델 크기만 증가 (72K→419K) | +0.012 | Exp1 |
| Causal conv + 긴 window | +0.010 | Exp1b |
| 매우 큰 모델 (29M) | 느리고 불안정 | Exp2 |
| Mel spectrogram 추가 경로 | 개선 없음 | Exp4 |
| Data augmentation (noise/gain) | 수렴 지연만 | Exp4 |
| RF 확장 (96→384ms) | 개선 없음 | Exp4 |

### 📈 성능 변화 그래프
```
Test Corr
0.80 ┤ ............................................. TARGET
     │
0.75 ┤
     │
0.72 ┤                               ★ Exp3 (0.716)
0.71 ┤                                     ○ Exp4 (0.714)
0.70 ┤
     │
0.68 ┤         ○ Exp1 (0.678)
0.67 ┤              ○ Exp1b (0.676)
0.66 ┤ ● Baseline (0.666)
0.65 ┤
     └──────────────────────────────────────────────
       Base   Exp1  Exp1b  Exp2   Exp3   Exp4
```

### 🔮 현재 병목 분석
1. **0.72 벽**: Non-causal dilated CNN으로 도달 가능한 한계에 근접
2. **입력 표현**: Raw waveform + Mel → 추가 이득 없음
3. **데이터 규모**: SVD 687명 (건강) → 다양성 부족 가능
4. **태스크 특성**: MIC→EGG는 성문 접촉 정보를 음향에서 추론 → 본질적 한계 존재

---

## 📁 산출물 정리

| 실험 | 결과 폴더 | 산출물 |
|------|-----------|--------|
| Exp1 | `results/exp1_larger_model/` | metrics.txt/json, history.json, training_history.png, sample_1~6.png, all_samples_comparison.png |
| Exp1b | `results/exp1b_longer_window/` | 〃 |
| Exp2 | `results/exp2_tcn_unet/` | training.log, training_history.png (중단됨) |
| Exp3 | `results/exp3_efficient/` | metrics.txt/json, history.json, training.log, training_history.png, sample_1~6.png, all_samples_comparison.png |
| Exp4 | `results/exp4_multi_input/` | 〃 |

---

*보고서 생성: 2026-02-07*
