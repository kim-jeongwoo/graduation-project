<!-- provenance -->
> **원본**: `dml-server/results/sidetrack/diagnosis_summary.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: score_mapper 매칭 방식 진단 보고서 (per-register vs per-session)
> **원본 수정일**: 2026-05-03 · **크기**: 6,762 bytes · **sha256[:8]**: `c957841a`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# score_mapper 매칭 방식 진단 보고서

**작성일**: 2026-05-03  
**목적**: AI 점수 ↔ 트레이너 점수 상관계수의 매칭 방식 의존성 분석  
**관련 스크립트**: `dml-server/scripts/sidetrack/chest_head_indicators.py`, `visualize_matching_diagnosis.py`

---

## 1. 배경

현재 `score_mapper.py`는 AI 점수와 트레이너 점수를 **per-register** 방식으로 매칭한다.  
각 가수 × 레지스터(low/mid/high) 조합을 독립 행으로 취급하므로, 가수 1명당 최대 3개 행이 생성된다.

**문제 제기**: 흉성두성(EGG CQ) 매핑에서 per-register 상관계수 r = −0.282가 관측되었다.  
AI 모델이 EGG를 정확히 추정하는데 (Test Corr 0.8249) 왜 트레이너 점수와 역상관인가?

---

## 2. 세 가지 매칭 방식

| 방식 | 설명 | 데이터 출처 |
|------|------|------------|
| **per-register** | 가수 × 레지스터 = 한 행 (현재 score_mapper) | ai_scores.json ↔ trainer_scores.csv |
| **per-session** | 가수 전체 발화 평균 = 한 행 | egg_analysis.json (cq_mean) ↔ 항목별 트레이너 평균 |
| **검증 (validation)** | T2 신규 가수 (독립 집합) | analyze_t2.json ↔ trainer_scores_t2.csv |

---

## 3. 전체 진단 결과

| 항목 | AI 지표 | per-register (현재) | per-session | 검증 (T2) |
|------|---------|-------------------|-------------|----------|
| 비강사용 | nasal_ratio | +0.025 (n=69) | +0.089 (n=23) | N/A |
| **흉성두성** | **cq_mean** | **−0.282 (n=57)** | **−0.271 (n=19)** | **+0.554 (n=11)** |
| **접촉강도** | **cq_peak** | **+0.087 (n=57)** | **−0.101 (n=19)** | **+0.627 (n=11)** |
| 호흡식별 | cpp_mean | N/A | +0.664 (n=23) | +0.314 (n=11) |
| 전방공명 | spectral_centroid_mean | N/A | −0.344 (n=23) | −0.456 (n=11) |
| 연구개위치 | nasal_ratio | −0.210 (n=69) | −0.137 (n=23) | N/A |
| 상압하압 | spectral_tilt_mean | +0.556 (n=69) | +0.587 (n=23) | −0.240 (n=11) |

N/A = 해당 방식으로 분석 불가 (지표 없음 또는 데이터 미수집)

---

## 4. 항목별 해석

### 4-1. 흉성두성 — 매칭 방식 아티팩트 확인

- **현재 (per-register)**: r = −0.282  
  → 얼핏 "AI가 흉성두성을 역으로 측정"처럼 보임
- **per-session**: r = −0.271 (거의 동일)  
  → 매칭 방식 자체의 문제가 아님
- **검증 (T2, 독립 집합)**: r = **+0.554**  
  → 실제 방향은 양의 상관. 훈련 데이터의 레이블 품질 또는 분포 문제.

**결론**: 훈련 데이터(가수 2~12)에서 EGG CQ와 트레이너 흉성두성 점수가 역상관인 것은  
트레이닝 데이터 특이성이다. T2 검증 집합(n=11)에서 +0.554로 방향이 반전되므로,  
AI 지표 자체는 흉성두성을 올바르게 반영하고 있다.

### 4-2. 접촉강도 — 훈련/검증 불일치

- per-register: +0.087 (약한 양의 상관)  
- per-session: −0.101 (약한 음의 상관)  
- **검증 (T2)**: **+0.627** (강한 양의 상관)

CQ peak는 접촉 강도의 물리적 지표로 타당하다. 훈련 데이터 분포 편향이 의심된다.  
T2 데이터가 추가되면 더 높은 신뢰도로 재학습 가능.

### 4-3. 호흡식별 — 유망한 지표

- per-session: +0.664 (n=23) — 가장 높은 상관계수  
- **검증 (T2)**: +0.314 (n=11) — 약화되나 방향 유지

CPP(Cepstral Peak Prominence)는 발성의 주기성과 성문 접촉 효율을 측정.  
호흡 조절이 좋을수록 CPP가 높은 경향이 검증된다.

### 4-4. 전방공명 — 일관된 음의 상관

- per-session: −0.344 (n=23)  
- **검증 (T2)**: −0.456 (n=11) — 방향 일치, 강화됨

Spectral centroid와 전방공명 트레이너 점수가 음의 상관인 것은 역설적으로 보인다.  
전방공명이 잘 될수록 배음이 전방으로 집중되어 spectral centroid가 낮아질 수 있음.  
또는 현재 traner 평가 기준과 spectral centroid가 다른 음향 현상을 측정할 가능성 있음.  
T2 데이터 추가 후 재검토 필요.

### 4-5. 상압하압 — 훈련/검증 방향 불일치

- per-register: +0.556 (n=69), per-session: +0.587 (n=23)  
- **검증 (T2)**: −0.240 (n=11) — **방향 반전**

Spectral tilt(고주파 대비 저주파 에너지 비율)와 상압하압의 관계는 복잡하다.  
훈련 집합에서 양의 상관이지만 T2에서 음의 상관 → 과적합 또는 모집단 차이.  
5월 10일 데이터(n=32)로 재검토 예정.

### 4-6. 비강사용, 연구개위치 — 미약한 상관

두 항목 모두 nasal_ratio를 공유하며 전체적으로 낮은 상관계수(|r| < 0.25).  
비강 공명의 주관적 판단(트레이너)과 비강 에너지 비율(AI)이 완전히 대응하지 않을 수 있음.

---

## 5. 핵심 발견 (슬라이드 요약)

### 발견 1: 흉성두성 지표는 타당하다
현재 score_mapper의 r = −0.282는 **훈련 데이터 특이성**이다.  
독립 검증 데이터에서 r = +0.554로 정방향 상관이 확인되었다.

### 발견 2: per-register 매칭의 한계
Pseudoreplication: 비강사용·연구개위치·상압하압은 세션 전체 지표(non-register-specific)인데  
3개 레지스터 행에 동일 값 복사 → 실제 n=23이 n=69로 부풀려짐.

### 발견 3: 5월 10일 데이터가 결정적
T2 검증 집합(n=11)은 방향을 보여주지만 CI가 넓다.  
5월 10일 후 n≈32로 늘어나면 흉성두성/접촉강도/호흡식별에서 유의미한 재학습 가능.

---

## 6. 향후 작업 (5월 10일 이후)

1. **Pseudoreplication 해소**: per-session 매칭으로 score_mapper 재학습  
   - 비강사용, 연구개위치, 상압하압: cq_mean → session-level indicator로 전환  
   - 흉성두성, 접촉강도: 레지스터별 매칭 유지 (의미 있음)

2. **흉성두성 방향 수정**: 현재 선형 매핑의 기울기 부호 검토  
   - T2 포함 재학습 후 positive slope 예상

3. **전방공명 지표 재검토**: spectral centroid 대신 HNR(Harmonics-to-Noise Ratio) 등 시도

4. **가중치 튜닝**: 트레이너 점수 ICC < 0.7인 항목(연구개위치, 비강사용)은 낮은 가중치 부여

---

## 7. 파일 위치

```
dml-server/results/sidetrack/
  matching_diagnosis_bars.png     ← 항목별 상관계수 비교 (grouped bar + CI)
  matching_diagnosis_heatmap.png  ← 7×3 히트맵 (RdYlGn 색상, 금색 테두리: 흉성두성)
  matching_diagnosis_focus.png    ← 흉성두성 집중 분석 + 아티팩트 메커니즘 설명
  diagnosis_summary.md            ← 이 파일
```

```
dml-server/scripts/sidetrack/
  chest_head_indicators.py        ← 상관계수 계산 (per-register/session/validation)
  visualize_matching_diagnosis.py ← 차트 생성
```
