<!-- provenance -->
> **원본**: `data/vocal_academy/results/sidetrack/sign_reversal_analysis.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: 부호 반전 학술 분석 (비강사용·전방공명)
> **원본 수정일**: 2026-05-11 · **크기**: 6,917 bytes · **sha256[:8]**: `468dcfca`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# Sign Reversal 학술 분석 (2026-05-11)

**대상 항목**: 비강사용 (1_nasal_oral_ratio), 전방공명 (5_forward_resonance)

**발견 요약**: 학습 데이터(학원 oral mic)에서 학습한 indicator-점수 관계가 검증 데이터(5/10 phone mic)에서 **부호가 반전**된다. 단순 선형 매핑(Ridge phone→oral mapper)으로 회복되지 않음.

---

## 1. 발견 정량화

### 1-1. 비강사용

| Cohort | best indicator/model | corr | sign |
|---|---|---:|:-:|
| 학습 5-fold CV (n=24) | ElasticNet (anti_formant_250_500 + F2_F1_distance + ...) | **+0.639** | **양(+)** |
| 5/10 val_A 외부 (n=9) | 동일 모델 | -0.880 | 음(-) |
| 5/10 val_B 외부 (n=8) | 동일 | -0.726 | 음(-) |
| 5/10 val_total (n=17) | 동일 | **-0.800** | **음(-)** |
| 5/10 paired 누설 (n=4) | 동일 | +0.600 | 양(+) |

→ **학습 양(+) ↔ 5/10 외부 음(-)** 완전 반전. paired만 학습 부호 유지.

### 1-2. 전방공명

| Cohort | corr | sign |
|---|---:|:-:|
| 학습 5-fold CV | **+0.535** | 양(+) |
| 5/10 val_A | -0.700 | 음(-) |
| 5/10 val_B | -0.752 | 음(-) |
| 5/10 val_total | **-0.680** | **음(-)** |
| 5/10 paired | -0.807 | 음(-) |

→ **학습 양(+) ↔ 5/10 음(-)** 일관 반전.

---

## 2. 음향학적 해석

### 2-1. 비강사용 — nasal_ratio indicator의 본질적 의미 변화

**학습 데이터 (4월, 학원)**:
- 구강(oral) + 비강(nasal) 2채널 동시 녹음
- `nasal_ratio = nasal_mic 에너지 / oral_mic 에너지`
- 의미: 발성 시 비강 공명 비율 (해부학적 직접 측정)
- 분포: mean 0.325, std 0.078 (학습 데이터)
- 평가자 비강사용 점수와의 corr: weak (학습 r=+0.025, score_mapper 자체 약함)

**5/10 데이터 (5/9, 스마트폰)**:
- 단일 채널 phone mic만
- `nasal_ratio` 직접 측정 불가
- score_mapper_v2는 phone→oral mapper로 추정된 nasal_ratio 사용
- mapper 학습 시: 16명 paired oral nasal_ratio + phone indicator 33개 → Ridge
- 추정 nasal_ratio는 실제 nasal mic 측정과 의미 다름

**결론**: 학습 nasal_ratio (직접 측정)와 5/10 mapped nasal_ratio (phone에서 회귀 추정)는 **동일 indicator 이름이지만 측정 메커니즘 자체가 다른 신호**. 부호 반전은 mapper의 한계가 아니라 indicator 의미의 영역 의존성.

### 2-2. 전방공명 — spectral_centroid mic 응답 차이

**학습 데이터 (oral mic)**:
- spectral_centroid mean **1047 Hz** (std 165)
- score_mapper 학습 매핑 임계값: 점수 0 → 5에 대응 (1095 → 801) — **decreasing**
- 평가자 전방공명 점수와의 학습 corr: -0.317 (낮은 centroid → 높은 전방공명 점수)
- 해석: 학습 마이크에서는 centroid가 낮을수록 "전방공명 강함" 평가

**5/10 데이터 (phone mic)**:
- spectral_centroid mean **1576 Hz** (std 250) — **+50% shift**
- 학습 매핑 max 1095를 5/10 mean 1576이 넘음 → 매핑 함수에서 모두 점수 0 클리핑 (Phase 2 §12-4 확인)
- score_mapper_v2 Lasso 다변량 모델 corr: -0.680 (val_total)
- 부호: 음(-) (학습 -0.317과 동일 부호이지만 5/10 분포 자체가 학습 범위 밖)

**Cohen's d 정량**:
- d(oral vs train_phone) = -1.58 (★★★ 큰 효과, B1-A rank 4)
- d(train_phone vs val_phone) = -0.34 (⚠ 작은~중간)

→ **마이크 응답 차이**로 centroid 분포가 +50% 이동. score_mapper 임계값과 일치하지 않음. mapper(Ridge)로도 회복 안 됨.

---

## 3. mapper 한계

### 3-1. 단순 선형 매핑의 회복 불가능

phone→oral indicator mapper (B1-B, 16명 LOO CV):

| target | direct corr (phone↔oral raw) | mapped corr (Ridge) | gain |
|---|---:|---:|---:|
| cpp_score_mapper | -0.795 | +0.695 | **+1.490** ★ (sign 회복 성공) |
| spectral_centroid_score_mapper | -0.668 | +0.043 | +0.711 (sign 거의 회복) |
| spectral_tilt_score_mapper | +0.708 | -0.086 | **-0.794** (악화) |

→ Ridge는 일부 indicator의 sign을 교정하나, **선형 결합 가설이 깨지는 영역에서는 회복 불가**. Sign reversal 영역.

### 3-2. n=25 paired sample의 통계적 한계

mapper 학습 데이터: 16명 가수 × 평균 1.5 곡 = 25 paired samples. 33 feature × 27 target → high dimensional, low sample. 정규화로 과적합 방지하나 학술적 한계 명확.

---

## 4. 학술적 시사점

1. **마이크 도메인 ≡ indicator 의미 도메인**: 음성 평가 시스템에서 학습 마이크와 검증 마이크가 다르면 indicator의 측정값뿐 아니라 **의미 자체가 변할 수 있음**. spectral feature의 mic 응답 의존성이 단순 보정 한계를 넘음.

2. **score_mapper 학습 단계 마이크 = 검증 단계 마이크 일치 권장**: 본 연구의 score_mapper 학습 oral mic = 4월 학원 마이크 / 검증 5/10 phone = 스마트폰. **두 환경 일관 시 sign reversal 없음** (학습 corr이 weak해도 그 weak한 관계는 유지됨). 마이크 변경 = 매핑 함수 재학습 필수.

3. **도메인별 별도 indicator 설계 필요**: phone 환경 전용 indicator (예: phone band-pass 특성 보정한 spectral measure) 별도 개발 필요. 일반 oral mic indicator를 mapper로 재현하는 것보다 phone 신호에서 직접 의미 있는 feature 산출이 더 robust.

4. **score_mapper 학습 시점의 통계적 신뢰성 한계 인지**: 본 sign reversal 발견은 score_mapper 학습 corr 자체가 약함(비강사용 +0.025, 전방공명 -0.317)에서 시작됨. **학습 corr 약한 indicator는 검증 환경 변경 시 sign reversal 위험 ↑**. 학습 단계에서 corr ≥ 0.5 이상의 강한 indicator만 신뢰 가능.

5. **본 발견의 일반화**: 음성 평가 분야의 마이크 도메인 변경 (학원/병원/연구실 → 스마트폰/스마트워치/IoT 마이크) 시 동일 위험. score_mapper 학습 시 의도된 검증 환경의 마이크로 학습하거나, 도메인 적응(domain adaptation) 기법 (CORAL, ADDA 등) 적용 필요.

---

## 5. 운영 결정

본 분석 결과 기반:

- **비강사용 / 전방공명 앱 표시 X** — tier="academic_only", caveat="sign_reversed"
- **mapping_params_v2.json에 명시**: `"deferred_indicators": ["1_nasal", "5_forward_resonance"]` (sign_reversal 별도 필드)
- **vocal-app 표시 제외 + dml-server 학술 분석용 데이터 보존**

5/10 ~ 5/24 통제 실험 기간 모니터링:
- 표시 4항목 (접촉강도, 호흡식별, 연구개위치, 혀경직도)에 sign reversal 증상 발생 여부 모니터링
- 만약 학원 실험에서 점수 분포가 갑자기 한쪽으로 치우치면 sign reversal 확장 가능성 → 즉시 사용 중단 + 재분석

---

**산출물 참조**: 
- `data/vocal_academy/results/sidetrack/multivariate_models_v3.csv` (B3 결과)
- `data/vocal_academy/results/sidetrack/score_mapper_v2_validation.csv` (D6 검증)
- `data/vocal_academy/results/sidetrack/mapping_params_v2.json` (배포 spec)
