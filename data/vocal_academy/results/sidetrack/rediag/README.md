# rediag — 2026.07 재검증 (진단 2단계) 산출물

배포 중인 score_mapper_v2 / phone_to_oral_mapper_v2의 **성능 추정치가 믿을 수 있는 값인지**를
재검증한 산출물 모음. 배포 파일(`mapping_params_v2.json`, `phone_to_oral_mapper_v2.pkl`)은
건드리지 않으며, 재생성 산출물은 `*_REGENERATED.*` 별도 파일로만 존재한다.

## 목적

배포 성능치 `val_total_corr`은 **같은 검증셋(5/10 코호트)으로 config를 고른 뒤 그 검증셋에서 잰 값**이다.
이 값이 성능 추정치로 유효한지(선택 편향이 얼마나 끼었는지)를 순열 검정·화자 부트스트랩·중첩 CV로 확인했다.

## 9항목 최종 판정

| 항목 | 배포 val_total | 화자 부트스트랩 95% CI (n=17) | 중첩 CV (mean±sd) | 선택 인지 p | 판정 |
|---|---|---|---|---|---|
| 비강사용 | -0.8000 | [-0.930, -0.644] | +0.676±0.182 | tier=academic_only | 학술 참고(academic_only) |
| 흉성두성 | 미배포(deferred) | — | -0.034±0.243 | — | 중첩 CV에서 **붕괴** (≈0) |
| 접촉강도 | +0.7327 | [+0.193, +0.921] | +0.506±0.118 | p=0.0231 | **유의** |
| 호흡식별 | +0.4343 | [-0.054, +0.804] | +0.362±0.282 | p=0.3325 | 미확보 |
| 전방공명 | -0.6797 | [-0.899, -0.348] | +0.395±0.105 | tier=academic_only | 학술 참고(academic_only) |
| 연구개위치 | -0.6236 | [-0.869, -0.242] | +0.603±0.022 | p=0.0536 | 미확보 + **부호 반전** |
| 공명개방 | 미배포(deferred) | — | -0.033±0.231 | — | 중첩 CV에서 **붕괴** (≈0) |
| 혀경직도 | +0.6936 | [+0.366, +0.930] | +0.562±0.081 | p=0.0136 | **유의** |
| 상압하압 | 미배포(deferred) | — | +0.058±0.242 | — | 중첩 CV에서 **붕괴** (≈0) |

- **유의 2항목**: 접촉강도·혀경직도 — 선택 편향을 반영한 검정에서도 유의, 부호 일치.
- **연구개위치**: p=0.0536로 미확보이며, 배포 부호(-0.6236)와 중첩 CV 부호(+0.603)가 **반대** — 부호 반전.
- **호흡식별**: p=0.3325, CI가 0을 포함 — 미확보.
- **deferred 3항목**(흉성두성·공명개방·상압하압): 중첩 CV 평균이 0 부근으로 붕괴 — 배포하지 않은 판단이 옳았음을 재확인.

## 선택 편향 규모 (s1)

n=17 코호트에서 그리드 24개 config 중 유한값 21개를 대상으로,
**라벨 순열 후 "21개 중 최대 |r|"의 우연 분포**를 구했다. 아무 신호가 없어도 최대값 선택만으로 이 정도 |r|이 나온다:

| 항목 | 배포값 | 우연 최대 p50 | p95 | p99 | 선택 인지 p |
|---|---|---|---|---|---|
| 비강사용 | -0.8000 | 0.382 | 0.616 | 0.702 | 0.0011 |
| 접촉강도 | +0.7327 | 0.333 | 0.674 | 0.780 | 0.0231 |
| 호흡식별 | +0.4343 | 0.371 | 0.618 | 0.709 | 0.3325 |
| 전방공명 | -0.6797 | 0.371 | 0.622 | 0.727 | 0.0208 |
| 연구개위치 | -0.6236 | 0.380 | 0.629 | 0.713 | 0.0536 |
| 혀경직도 | +0.6936 | 0.381 | 0.623 | 0.707 | 0.0136 |

→ "config를 고른 뒤의 검증 성능"은 이 분포와 비교해야 하며, 단일 모델 p값은 과대평가다.

## mapper를 직접 산출(direct)로 대체한 근거 (s5b)

1. **성능 동등**: 중첩 CV에서 mapper 경유와 direct의 차이가 미미 (예: 비강사용 Δ=+0.0005).
2. **외삽 붕괴**: mapper의 OOS 재구성 상관이 spectral_centroid_sm -0.008, spectral_tilt_sm +0.586로 붕괴 — direct는 각각 +0.718, +0.998.
3. **분산 축소**: 중첩 CV 표준편차가 direct 쪽이 작음 (비강사용 0.033 vs mapper 0.182).

## 구조적 한계 (s4a + docs/research/40-*)

- **p=38 feature > n=24 표본**, 설계행렬 **rank 23** — 어떤 정칙화를 써도 해가 유일하지 않은 영역.
- **`a1_p0`와 `h1_a1`은 완전 중복** (부호만 반대, r=−1.0) — 실질 독립 feature는 37개.

## 기존 train_5fold는 화자 누설 (s3-B)

배포 당시 train_5fold는 **unit 단위 KFold**였음이 재현으로 확정 (예: 비강사용 0.6394 ≈ unit KFold 재현 0.6330).
화자 단위로 바꾸면 값이 크게 변한다 (접촉강도 0.47 → 0.103).
**논문에 train CV 수치를 쓸 때는 화자 누설 사실을 반드시 병기할 것.**

## mapper 학습집합 확정 (s4e)

oral/phone 동시녹음 **25쌍 / 16화자**. 전체 29쌍에서 4 unit 제외:

| 제외 unit | 사유 |
|---|---|
| (6, '8') | v1 extra_metrics/spectral JSON에서 빠져 있어 _sm 5열 평균 대체 대상 |
| (9, '10') | 5/10 검증 코호트 누설 화자 |
| (13, '4') | 5/10 검증 코호트 누설 화자 |
| (15, '2') | 5/10 검증 코호트 누설 화자 |

## 스크립트 역할

- `common.py` — rediag 공용 데이터 로더 (진단 2단계)
- `grid.py` — multivariate_models_v3.csv 의 24 config 복원본 (s1a 로 확정).
- `rebuild.py` — 배포 X_train / X_val 을 원자료에서 재구성 (진단 2단계 공용 모듈).
- `retrain_v2.py` — 복원된 재학습 파이프라인 (작업 4 산출물).
- `s0_validate_pipeline.py` — 재구성 파이프라인이 배포 JSON의 validation_corr 을 재현하는지 검증.
- `s1_selection_bias.py` — 작업 1: 선택 편향 정량화.
- `s1a_grid_recover.py` — multivariate_models_v3.csv 의 24개 모델 config 를 정확히 복원.
- `s2_speaker_bootstrap.py` — 작업 2: 화자 단위 재집계 + 화자 클러스터 부트스트랩 95% CI.
- `s3_nested_cv.py` — 작업 3: 선택 절차를 포함한 정직한 추정 (중첩 CV).
- `s4a_scaler_forensics.py` — 배포 JSON의 scaler_mean/scale 이 어떤 데이터에서 나왔는지 역추적.
- `s4b_subset_search.py` — scaler_mean 을 정확히 재현하는 학습 subset 탐색.
- `s4c_refit.py` — 재구성한 X_train/y 로 배포 계수(coefficients) 재현 시도.
- `s4d_mapper_refit.py` — phone_to_oral_mapper_v2.pkl 재현 시도 + 학습 규모 판정(작업 7).
- `s4e_mapper_subset.py` — mapper scaler_mean 을 정확히 재현하는 pair subset 전수 탐색.
- `s5a_direct_phone.py` — 작업 5 전반부: phone 오디오에서 CPP / spectral_centroid /
- `s5b_mapper_necessity.py` — 작업 5 후반부: mapper 경유가 실제로 이득인가.
- `s6_oral_vs_phone.py` — 작업 6: 도메인 갭 손실량 정량화 (학습 코호트 paired).
- `s6b_oral_vs_phone_nested_mapper.py` — s6b — 작업 6 정정판: 도메인 갭 손실량을 **누설 없이** 산출.
- `s6c_linear_variant.py` — s6b — 작업 6 정정판: 도메인 갭 손실량을 **누설 없이** 산출.
- `s8_summary.py` — 1~7 결과 통합표 + 표시 4항목 유의성 최종 판정.

## 재학습 방법 (재현 절차)

```bash
cd data/vocal_academy/results/sidetrack/rediag
python retrain_v2.py
```

입력 (모두 저장소에 추적됨):
- `../indicators_v2_training.csv` — oral/phone 채널별 33개 지표
- `../../../trainer_scores.csv` — 5 rater × 3 register 평가 점수 (라벨)
- `../../extra_metrics.json`, `../../spectral_analysis.json` — _sm 5개 지표 원천

출력은 `mapping_params_v2_REGENERATED.json` / `phone_to_oral_mapper_v2_REGENERATED.pkl` 등
**`*_REGENERATED.*` 파일로만** 생성되며 배포 파일을 덮어쓰지 않는다.
재현 검증: s4c(score_mapper 6모델)·s4e(mapper 27 target) 모두 계수 일치 확인 완료.

---
*재검증 수행 2026-07-26 · 이 README의 수치는 rediag JSON 산출물에서 직접 추출 (2026-08-11)*
