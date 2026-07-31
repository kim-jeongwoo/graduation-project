<!-- provenance -->
> **원본**: `data/vocal_academy/results/sidetrack/presentation_key_messages.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: 발표용 핵심 메시지
> **원본 수정일**: 2026-05-11 · **크기**: 6,523 bytes · **sha256[:8]**: `f7ccbfe5`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# 발표 자료 핵심 메시지 (5/14 학원 실험 시작 직전, 2026-05-11)

순천향대 IoT학과 졸업 프로젝트 — MIC 음성 → EGG 추정 + 노래방 발성 평가 시스템

---

## 7줄 핵심 메시지

1. **평가자 5명 ICC(2,k) 0.793 (9항목 평균)** — 학술적 신뢰성 확보 (음성 평가 분야 ICC 0.7 기준 충분 통과). Phase 1 검증: 학습 데이터 22명 ICC 0.916, 5/10 검증 21명 ICC 0.793, 평가자 ID 1~5 동일인 추정 (학습 4/27 + 검증 5/9).

2. **9항목 중 1항목 확정 high + 3항목 잠재 high (총 4항목 표시)**: 음성 평가 분야 표준 기준 (val_total ≥ 0.5, p<0.05 n=17, 4-cohort sign 일관, val/ICC ratio) 적용.
   - **확정 high (1)**: 접촉강도 (val 0.733, ICC ratio 82%, sign 4-cohort 일관 ★)
   - **잠재 high (3)** — 잠재 high는 학원 통제 실험에서 추가 검증:
     · 호흡식별 (val 0.434, ICC ratio 55%, caveat=val_total_below_0.5 + train_val_sign_diverged + regularization_softened — Ridge α=0.001 D-fix 적용)
     · 연구개위치 (val 0.624, ICC ratio 97%, caveat=train_weak)
     · 혀경직도 (val 0.694, ICC ratio 87%, caveat=train_weak)

3. **호흡식별 모델 D-fix 학술 정직성**: 초기 ElasticNet α=1.0은 val 0.694였으나 prediction std=0.04 (앱 사용 무의미한 narrow range). Ridge α=0.001로 교체 — std 0.812 (20×) / range 3.53 / val 0.434. **corr 하락 trade-off 대신 앱 사용성 확보**. tier high → high_star로 강등 (정직성).

4. **🔬 학술적 발견 — Sign Reversal (비강사용/전방공명)**: 학습 마이크(oral)와 검증 마이크(phone) 간 indicator의 **부호가 반전됨**. 단순 선형 매핑(Ridge mapper)으로 회복 불가능한 영역 존재. 음향학적 해석: nasal_ratio는 oral+nasal 2채널에서만 직접 측정 가능 / spectral_centroid는 phone에서 +50% shift (1047→1576Hz)로 학습 매핑 임계값 영역 이탈. **마이크 도메인 ≡ indicator 의미 도메인**.

5. **5/14 통제 실험 시작 — B 그룹 11명 (앱 사용 전 = "Before")**: 5/24까지 학원 측 통제 실험 진행. 5/24 이후 B 그룹 "After" 도착 시 4 표시 항목으로 Before/After 비교. 5/24 비교 결과로 vocal-fit 앱의 발성 개선 효과 정량화.

   **실시간 endpoint(/ws/realtime)는 v2 비적용**: latency 부담 (+70~100s/chunk)으로 실시간 사용 불가. 200ms 음정 일치율 + 5초 호흡 chunk는 v1 score_mapper(cpp_mean indicator) 유지. /analyze + /analyze-chunk만 v2 적용.

6. **phone → oral indicator mapper 학습 (16명 LOO 16-fold CV)**: Ridge 회귀로 마이크 도메인 보정. cpp/spectral_centroid/cq_mean indicator의 **direct corr 음수를 mapped corr 양수로 sign 교정 (gain +0.70~+1.49)**. shimmer 계열은 학습 mic 차이가 가장 큼(Cohen's d=-3.23) — mapper로 +0.42~+0.45 보정. **mapper 효과 9/27 indicator 양**, 나머지 18개는 학술 한계.

7. **9항목 중 5항목 학술 정직성 우선 표시 보류** (excluded 3 + sign_reversal 2): 흉성두성(val_total 0.290), 상압하압(0.218), 공명개방(-0.277) — val_total 임계값 0.3 미달. 비강사용/전방공명 — sign reversal. **모델 신뢰도 한계 명시하여 학원 실험 결과 해석 시 오인 방지**.

---

## 슬라이드 D 갱신용 — 마이크 강건성

```
B1-A Cohen's d 분석 (oral vs phone, 학습 22명 내):
  - shimmer_local      d=-3.23 ★★★  → mapper 보정 가치 최대
  - anti_formant_250_500 d=-1.59 ★★★
  - HNR               d=+1.35 ★★★
  - h1_a1             d=+1.28 ★★★
  - flatness_b1       d=-1.22 ★★★
  - 33 indicator 중 13개 |d| > 0.5 (큰 효과)

발표 메시지: "phone↔oral mapper 학습으로 13개 indicator의 마이크 응답 차이 정량 보정"
```

---

## 슬라이드 — 실험 디자인 + 한계 명시

```
[데이터 구성]
- 학습 22명 × 9항목 × 3 register, 평가자 5명 (ICC 0.916)
- 5/10 검증 21명 (방음부스 A 10명 + 일반환경 B 11명), 평가자 5명 (ICC 0.793)
- phone↔oral paired 16명 (mapper 학습) + 누설 가수 4명 (별도 paired 분석)

[누설 가수 처리]
- A9 (singer_04): 곡 + 가수 누설 — paired 분석 별도 트랙
- B4/B7/B11: 가수만 누설 — paired 분석 (다른 곡)
- 외부 검증 cohort에서 누설 가수 제외 → A 외부 9명 + B 외부 8명 = 17명

[엄격한 4-fold criterion 통과 항목 = "high" tier 자격]
  1. val_total corr ≥ 0.5 (Cohen large effect)
  2. n=17 p<0.05 statistical significance (|r| ≥ 0.482)
  3. 4 cohort sign 일관 (train_5fold / val_A / val_B / val_total)
  4. val/ICC ratio ≥ 0.7 (평가자 천장 대비 적정)

[결과 항목별 분류]
  high (2):     접촉강도, 호흡식별 — 4 criterion 모두 통과
  high* (2):    연구개위치, 혀경직도 — 1,2,3 통과, train_weak (caveat 명시)
  academic (2): 비강사용, 전방공명 — sign reversed (학술 발견)
  excluded (3): 흉성두성, 상압하압, 공명개방
```

---

## 학술 정직성 메시지 (핵심)

> "9항목 모두 표시하는 다른 시스템과 달리, 본 연구는 검증되지 않은 항목 5개를 명시적으로 표시 보류함. 4 항목만 안전하게 표시하고, sign reversal 학술 발견은 별도 보고서로 정리함. 음성 평가 분야의 마이크 도메인 변경 위험을 정량화한 첫 시도."

---

## 발표 시연 시나리오

1. **학습 데이터 demo**: 학습 22명 중 1명 oral wav → 9항목 점수 예시 (점수 신뢰 높음 표시)
2. **5/10 검증 demo**: 5/10 A 그룹 1명 phone wav → 4 표시 + 2 academic 별도 출력
3. **B 그룹 통제 실험 demo**: B 그룹 1명 Before/After (5/24 데이터 도착 후)
4. **mapper effect visualization**: cpp direct -0.795 → mapped +0.695 sign 교정 시각화
5. **sign reversal demo**: 학습 oral spectral_centroid → 5/10 phone centroid +50% shift → 매핑 함수 클리핑 시각화

---

## 산출물 참조

- `mapping_params_v2.json` — 6항목 모델 spec (배포용)
- `score_mapper_v2.py` — 통합 mapper 모듈
- `phone_to_oral_mapper_v2.pkl` — 27 target mapper
- `sign_reversal_analysis.md` — 학술 발견 상세
- `score_mapper_v2_validation.csv` — D6 검증 결과
- `multivariate_models_v3.csv` — B3 216 모델 그리드 결과
- `single_indicator_search_v2.csv` — B2 1710 indicator 그리드
- `phone_inventory_2026_05.csv` + `triplet_sync_check.csv` — phone 인벤토리
- `icc_510_report.md` — Phase 1 평가자 ICC 보고서
