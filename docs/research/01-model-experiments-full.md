<!-- provenance -->
> **원본**: `.claude/refs/experiments.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: EGG 추정 모델 실험 전체 이력 (성공 6 / 실패·중단 14)
> **원본 수정일**: 2026-04-17 · **크기**: 2,878 bytes · **sha256[:8]**: `02ce3795`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# 실험 히스토리

## 성공한 실험 (성능 향상 순)

| 실험 | 모델 | Params | Window | Test Corr | 핵심 변경 |
|------|------|--------|--------|-----------|-----------|
| Baseline | WaveNet (causal) | 72K | 192 (12ms) | 0.6662 | 초기 모델 |
| Exp1 | Larger WaveNet | 419K | 192 | 0.6784 | 크기 증가 |
| Exp3 | EfficientEGGNet | 1.8M | 4096 (256ms) | 0.7163 | **Non-causal 전환** |
| Exp10 | Large Efficient | 5.99M | 4096 | 0.7205 | 스케일업 |
| Exp11 | Multiscale | 5.99M | 8192 (512ms) | 0.7484 | **Window 확장** |
| **Exp20** | **Progressive** | **5.99M** | **16384 (1024ms)** | **0.8249** | **Window 1024ms ★** |

## 실패/중단된 실험

| 실험 | Test Corr | 사유 |
|------|-----------|------|
| Exp1b | 0.6763 | Window 1024 늘렸으나 causal이라 효과 없음 |
| Exp2 (TCN-UNet) | 중단 | 29.4M params, AMP + InstanceNorm → NaN, 너무 느림 |
| Exp4 (Multi-Input) | 0.7137 | Mel spectrogram 중복 정보, augmentation 비효과 |
| Exp5 (고품질 필터) | 0.6956 | 데이터 절반 삭제 → 오히려 하락 |
| Exp6 (Transformer) | 0.7030 | 에폭당 ~32분, 수렴 느림 |
| Exp7 (Conformer) | OOM | Self-attention O(N²) → CUDA OOM |
| Exp8 (wav2vec2) | ≈ 0 | 90M params 사전학습 모델, 학습 완전 실패 |
| Exp9 (Curriculum) | 0.7126 | 난이도 순 학습 효과 없음 |
| Exp12 (Ensemble) | 0.7191 | 단일 모델보다 낮음 |
| Exp13~19 | 0.74~0.75 | 정규화/attention/augmentation — 모두 정체 |

## Exp20 Progressive Window 상세

### 학습 설정
```
Phase 1: window=4096,  batch=32, 20 epochs, lr=0.001,  hop=2048
Phase 2: window=8192,  batch=16, 40 epochs, lr=0.0005, hop=4096
Phase 3: window=16384, batch=8,  40 epochs, lr=0.0003, hop=8192 → epoch 16 early stop
```
- Optimizer: AdamW (weight_decay=1e-4)
- Scheduler: OneCycleLR (pct_start=0.1, anneal_strategy='cos')
- AMP: GradScaler 활성화
- Loss: `CombinedLoss(alpha=0.2)` → 0.2·MSE + 0.8·CorrLoss
- 총 76 epochs

### 검증 결과
- Data Leak: 없음 (화자 겹침 0, seed=42)
- Train-Test Gap: 0.022 (과적합 없음)
- 화자별 분포: 90% Corr ≥ 0.7, 71% Corr ≥ 0.8, Median = 0.8532
- 체크포인트: epoch=61, val_corr=0.8218, phase=3

### 핵심 발견 (반복 실수 방지)
1. **Window 크기가 가장 중요** — 192→4096→8192→16384 확장마다 최대 폭 향상. Progressive training 자체보다 16384 window가 핵심.
2. **Non-causal > Causal** — 양방향 맥락 필수. Exp1b에서 window만 늘리고 causal 유지 → 효과 없었음.
3. **큰 모델 ≠ 좋은 성능** — 5.99M이면 충분. 29M(Exp2)/90M(Exp8) 실패.
4. **Data Augmentation 비효과** — MIC→EGG는 deterministic 물리 매핑. noise/gain 추가가 수렴만 방해.
5. **화자독립 분할 필수** — 프레임 분할 시 Corr 0.95 나오지만 데이터 누수. seed=42 speaker split 유지.
