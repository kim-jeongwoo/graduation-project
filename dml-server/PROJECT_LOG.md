# PROJECT_LOG.md — 졸업작품 진행 일지
순천향대 IoT학과 | 김정우 | 최종 갱신: 2026-05-04

---

## 0. 현황 요약 (2026-05-04 — 새 채팅방용 빠른 참조)

### 완료된 Phase

| Phase | 내용 | 산출물 |
|-------|------|--------|
| **T1** | 14곡 Demucs 분리 + CREPE F0 + LRC 수집 + MR 정렬 | `data/songs/{audio,lrc,pitch_guide,stems}` |
| **L** | model_server `/analyze` 9항목 + timeline_scores | `services/timeline_analysis.py`, `demo_responses/` |
| **F** | 자체 F0 추출 파이프라인 (외부 MIDI 옥타브 오류 발견 → 전환) | `f0_to_midi_segments.py`, `batch_f0_to_midi_segments.sh` |
| **T2 준비** | `run_t2_pipeline.sh` 3가지 모드 사전 검증 완료 | 5월 10일 데이터 도착 즉시 실행 가능 |
| **진단** | score_mapper per-register vs per-session 매칭 아티팩트 규명 | `results/sidetrack/matching_diagnosis_*.png` |

### 현재 상태 (2026-05-04)

- **dml-server**: 대기 모드. 5월 10일 학원 데이터 도착 전까지 score_mapper 변경 금지.
- **pitch_guide**: 002(F#3~A#5), 004(B2~A5) `guide_source=f0` 처리 완료. 나머지 12곡은 5월 10일 이후 일괄 처리.
- **Mac Studio sync**: `cd /Users/kimjeongwoo/vocal-server && bash dml-server/scripts/sync_songs.sh`
- **vocal-app**: 갤럭시 재검증 진행 중.

### 다음 액션

1. **5월 10일**: `run_t2_pipeline.sh` + 13곡 `batch_f0_to_midi_segments.sh`
2. **5월 10~24일**: 학원 통제 실험 데이터 수집
3. **5월 24일 이후**: 사전/사후 분석 + score_mapper 재학습
4. **6월 초**: PPT 발표 자료 작성
5. **6월 15일**: 발표

### 발표 자료 후보 (기 생성)

- `results/sidetrack/matching_diagnosis_bars/heatmap/focus.png` + `diagnosis_slides.md` (5종 슬라이드)
- `results/sidetrack/004_midi_vs_f0_comparison.png` (외부 MIDI 옥타브 오류 시각화)
- `results/timeline_validation_test_11.json` (타임라인 검증 데이터)

### 미해결 의문점

- score_mapper per-session 채택 시 9개 항목 영향 (5월 10일 데이터 후 결정)
- 상압하압 마이크 차이 영향 정량화 (학원 스마트폰 환경으로 재검증 예정)
- vocal-app 002/004 가이드라인 피치 일치 여부 (갤럭시 재검증 대기)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 주제 | MIC 음성으로 EGG(성대접촉파형) 추정 + 노래방 앱 |
| 구성 | ① EGG 추정 AI 모델 ② 노래방 데이터 파이프라인 ③ 서버/앱 |
| 목표 | 발성 피드백이 없는 노래방 환경에서 실시간 음정·발성 분석 제공 |
| 개발환경 | Ubuntu 25.10 / RTX 5080 / PyTorch 2.10.0+cu128 / Python 3.11 |

---

## 2. 페이지별 진행 현황

### 2-A. AI 모델 (EGG 추정)

**상태: 완료 ✓**

| 실험 | 모델 | Test Corr | 비고 |
|------|------|-----------|------|
| Exp01~10 | 초기 CNN 변형 | 0.60~0.71 | 구조 탐색 |
| Exp11~15 | Window 크기 실험 | 0.71~0.78 | 512→4096→8192 |
| Exp16~19 | Loss 조합 실험 | 0.78~0.82 | MSE+CorrLoss 비율 조정 |
| **Exp20** | **EfficientEGGNet** | **0.8249** | **Best. 고정.** |

**Exp20 최종 구성**
- 모델: non-causal dilated CNN, channels=128, n_layers=30, kernel_size=5, n_stacks=5, dropout=0.05
- 파라미터: 5.99M
- 윈도우: 16384 samples (1024ms @16kHz)
- Loss: 0.2·MSE + 0.8·CorrLoss

**검증 결과**
- Data Leak 없음 (화자 독립 분할, seed=42)
- Train-Test Gap: 0.022 (과적합 없음)
- 화자 분포: 90%가 Corr ≥ 0.7, Median = 0.8532
- 체크포인트: `checkpoints/exp20_progressive/best_model.pt`

---

### 2-B. 노래방 데이터 파이프라인 (T1)

**상태: 완료 ✓ (2026-04-30)**

14곡 선정 기준: 발성 난이도 분포, 장르 다양성, 공개 LRC 가용성

| Stage | 내용 | 결과 |
|-------|------|------|
| Stage 0 | 파일 분류 (master/MR 식별) | 14/14 ✓ |
| Stage 1 | LRC 수집 (LRCLIB API) | 11/14 ✓ · 3곡 manual_required |
| Stage 2 | Demucs 보컬 분리 + CREPE F0 추출 + MR 정렬 | 14/14 ✓ |
| Stage 3 | 배치 실행 + 검증 | ✓ |

**14곡 처리 결과**

| ID | 아티스트 - 곡명 | LRC | offset_sec | 특이사항 |
|----|----------------|-----|-----------|---------|
| 001 | 한로로 - 시간을 달리네 | ✗ | — | LRCLIB 없음 |
| 002 | 윤하 - 기다리다 | ✓ (35줄) | 측정 | — |
| 003 | 보보 - 늦은 후회 | ✓ (7줄) | 측정 | — |
| 004 | 김범수 - 보고싶다 | ✓ (14줄) | 측정 | 파이프라인 시범 검증곡 |
| 005 | 이적 - 다행이다 | ✓ (5줄) | 측정 | — |
| 006 | 폴킴 - 모든 날 모든 순간 | ✓ (2줄) | 측정 | — |
| 007 | 지아 - 물론 | ✗ | +2.854s | LRCLIB 없음. pitch curve 정상 |
| 008 | Lee Hi - Breathe (한숨) | ✓ (3줄) | 측정 | 마지막 7.7s review_segment = 페이드아웃 정상 |
| 009 | 거미 - 친구라도 될걸 그랬어 | ✓ | 측정 | — |
| 010 | 나윤권 - 나였으면 | ✓ (4줄) | 측정 | — |
| 011 | 양다일 - 요즘 | ✗ | — | LRCLIB 없음 |
| 012 | 조성모 - 슬픈 영혼식 | ✓ (1줄) | +2.249s | 0~20s Demucs leakage = 정상 |
| 013 | 케이윌 - Love Blossom | ✓ (5줄) | 측정 | — |
| 014 | 성시경 - 너의 모든 순간 | ✓ (14줄) | 측정 | — |

**산출물 위치**
```
data/songs/
  meta/songs.json               # 14곡 메타데이터
  meta/results_summary.json     # Stage 2 통계 (전곡)
  meta/manual_required.txt      # 001, 007, 011
  lrc/raw/{id}.lrc              # 원본 LRC (11개)
  lrc/parsed/{id}.json          # 파싱된 LRC (11개)
  lrc/parsed/{id}_aligned.json  # offset 적용 LRC (11개)
  pitch_guide/{id}_pitch_guide.json  # F0 curve JSON (14개)
  pitch_guide/{id}_pitch_guide.png   # 시각화 PNG (14개)
  pitch_guide/00_grid_all_songs.png  # 전체 4×4 그리드
stems/{id}/
  vocals.wav, no_vocals.wav     # Demucs 분리 결과
  crepe_cache.npz               # CREPE 캐시 (재실행 ~1s)
```

---

### 2-C. 서버 / 앱

**상태: 미시작 (다음 단계)**

계획:
- songs DB 테이블 (id, artist, title, master_path, mr_path, lrc_offset_sec, ...)
- API 엔드포인트: 곡 목록 · pitch_guide JSON · lrc_aligned JSON
- 앱: MR 재생 + 가사 표시 + 실시간 음정 곡선 오버레이
- rsync: `data/songs/` → 114.71.220.144 동기화 (미실행)

---

## 3. 대표님 협의 결과 / 학원 일정

<!-- 협의 내용 추가 필요 -->

| 날짜 | 협의 내용 | 결정/액션 |
|------|----------|---------|
| — | — | — |

> 학원 일정, 발표 시연 조건, 데이터 활용 범위 등 협의 결과를 여기에 기록.

---

## 4. 검증 결과 + 한계 분석

### 검증된 것

| 항목 | 결과 | 방법 |
|------|------|------|
| Data Leak 없음 | ✓ | 화자 독립 분할 검증 |
| 오프셋 정확도 (012) | ✓ | LRC 첫 라인 [21.25s] ↔ CREPE 고신뢰 개시 일치 |
| review_segment 신뢰도 (008) | ✓ | 마지막 7.7s = 페이드아웃, conf 0.142 = 무발성 정상 |
| 007 pitch quality | ✓ | F#3~B4 여성 보컬 범위, 130~155s 공백 = 간주 구간 |
| Demucs leakage | ✓ 정상 범위 | 도입 악기음 bleed → conf 0.67~0.75 (보컬 0.87+와 구분) |

### 한계 / 미해결

| 항목 | 내용 | 영향도 |
|------|------|--------|
| CREPE GPU 미지원 | RTX 5080(Blackwell) TF 2.21 미지원. CPU 84~98s/곡 | 낮음 (캐시로 보완) |
| LRC 3곡 미확보 | 001·007·011 LRCLIB 없음. 가사 표시 불가 | 중간 (앱 완성도) |
| pitch_guide 타임라인 | JSON 내 시간 = master 기준. 앱에서 `t_mr = t - lrc_offset_sec` 변환 필요 | 중간 (앱 구현 시 주의) |
| EGG 실시간 추론 지연 | 모델 윈도우 1024ms → 실시간 피드백 최소 1s 딜레이 | 중간 (UX) |
| 데이터셋 크기 | 실험 데이터 규모 제한적. 일반화 성능 추가 검증 필요 | 높음 (학술적) |

---

## 5. 발표용 핵심 메시지

### 한 줄 요약
> "마이크 소리만으로 성대 진동 파형을 추정하는 AI — 노래방에서 발성 피드백을 가능하게 한다"

### 핵심 수치 (슬라이드용)
- **Test Corr 0.8249** — 실제 EGG 파형과 AI 추정값의 상관계수
- **화자 독립 검증** — 학습에 없던 화자에 대해 90%가 Corr ≥ 0.7
- **5.99M 파라미터** — 경량 모델, 실시간 처리 가능
- **14곡 파이프라인 완성** — 자동 MR 정렬 + 음정 곡선 생성

### 차별점
1. EGG 센서 없이 MIC만으로 성대 접촉 패턴 추정
2. 음정 정확도 + 발성 품질을 동시에 피드백 가능
3. 기존 노래방 장비 교체 없이 소프트웨어만으로 구현 가능

### 예상 질문 & 답변
| 질문 | 답변 요지 |
|------|---------|
| 실제 EGG와 얼마나 같냐? | Corr 0.8249. 절대적 수치보다 패턴 유사성이 발성 피드백에 중요. |
| 실시간으로 되냐? | 1024ms 윈도우로 ~1s 딜레이. 노래 피드백 용도로 허용 범위. |
| 데이터는 어디서? | 연구용 공개 EGG+MIC 동시 녹음 데이터셋 활용. |
| 노래방에서 쓰려면? | 기존 MIC 신호만 있으면 됨. MR 파일과 pitch guide JSON으로 앱 연동. |

---

## 6. 미해결 의문점

<!-- 답 나오면 해당 항목 삭제하고 결정 사항 누적에 기록 -->

- [ ] **앱 아키텍처**: 실시간 EGG 추론을 클라이언트(앱)에서 할지 서버에서 할지 미결정.
- [ ] **LRC 3곡**: 001·007·011 Whisper ASR 자동 생성 vs 수동 작성 — 품질 vs 공수 트레이드오프 미결정.
- [ ] **pitch_guide 앱 연동 타임라인**: `t_mr = t_master - lrc_offset_sec` 변환을 JSON에 미리 적용할지, 앱에서 런타임 계산할지.
- [ ] **모델 경량화**: 앱 온디바이스 추론 가능 여부 미검토 (현재 5.99M 파라미터, ONNX 변환 미시도).
- [ ] **발표 시연 방식**: 실시간 녹음 vs 미리 녹음한 시연 파일 재생 — 네트워크/하드웨어 리스크 고려 필요.
- [ ] **대표님 협의 사항**: 학원 데이터 활용 범위, 시연 조건, 이후 상용화 계획 미기록.

---

## 7. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-03 | PROJECT_LOG.md 최초 작성. T1 파이프라인 완료 기준 현황 기록. |
| 2026-05-03 | score_mapper per-register vs per-session 매칭 방식 진단. 아래 섹션 참조. |
| 2026-05-04 | MIDI 파이프라인 + /analyze timeline 확장 + 자체 F0 추출 전환. 섹션 9·10 참조. |

---

## 8. Per-register vs Per-session 매칭 진단 (2026-05-03)

`dml-server/scripts/sidetrack/chest_head_indicators.py` 실행 결과 기록.

### 8-1. 발단

흉성두성 검증 r=-0.215 (현재 AI 점수 기준) 문제 해결 시도.
4가지 신규 CQ 지표 후보(cq_high-cq_low, cq_high/cq_low, cq_variance, cq_high_normalized) 탐색.

**결론: 4종 모두 실패.** 음역대 간 CQ 변동은 흉성두성과 무관.

### 8-2. 부수 발견: 매칭 방식 아티팩트

흉성두성의 학습-검증 r 불일치 원인 규명.

| 항목 | 학습 per-register (mapper 현행) | 학습 per-session | 검증 per-session (n=11) |
|---|---|---|---|
| 비강사용 | +0.025 (n=69) | +0.089 (n=23) | N/A |
| **흉성두성** | **-0.282 (n=57)** | **+0.139 (n=28)** | **+0.554 (n=11)** |
| **접촉강도** | **+0.087 (n=57)** | **-0.101 (n=19)** | **+0.627 (n=11)** |
| 호흡식별 * | +0.569 (n=69) | +0.664 (n=23) | +0.314 (n=11) |
| 전방공명 * | -0.317 (n=69) | -0.344 (n=23) | -0.456 (n=11) |
| 연구개위치 | -0.210 (n=69) | -0.137 (n=23) | N/A |
| 상압하압 | +0.556 (n=69) | +0.587 (n=23) | -0.240 (n=11) |

\* 호흡식별(cpp)·전방공명(spectral_centroid)은 global-only 지표 → per-register n=69가 의사반복(pseudoreplication).  
실제 독립 관측 수는 각 23회 (session 수).

**흉성두성 원인 분석:**
- per-register: 같은 가수 내 "저→고로 갈수록 CQ 변동"이 가수 간 차이로 오인됨
- per-session: 가수당 1값 → 음역대 변동 평균화 → 이론적 양의 상관 (+0.139) 회복
- 검증에서 +0.554로 더 강한 양의 상관 → 이론 방향 확인

**추가 주목 항목:**
- **상압하압**: 학습 +0.556/+0.587 → 강하고 일관. 검증 -0.240 → 방향 역전. n=11 과소 표본 가능성.
- **접촉강도**: 학습 per-session -0.101이지만 검증 +0.627 → 불일치. 학습 데이터 singers 2-12(n=19)에서 per-session이 노이즈 발생.
- **호흡식별**: 학습/검증 모두 양의 상관으로 가장 안정적인 항목.
- **전방공명**: 모든 방식에서 음의 상관 → spectral_centroid 지표 방향 자체가 반대일 가능성.

### 8-3. 결정 (2026-05-03)

**5월 10일 데이터 수령 전 score_mapper 매칭 방식 변경 안 함.**

근거:
- 학습 per-session 흉성두성 r=+0.139는 통계적으로 약함 (95% CI: [-0.247, +0.486])
- 검증 n=11에서 r=+0.554가 우연일 가능성 배제 불가
- 접촉강도처럼 per-session이 오히려 악화되는 항목도 존재
- 9개 항목에 일관 적용하려면 더 많은 데이터 필요

### 8-4. 5월 10일 데이터 도착 시 후속 작업

1. **per-session 재검증**: T2 데이터(10명 신규 가수) 추가 후 per-session r 재계산
2. **일관 적용 여부 결정**: 흉성두성·접촉강도·상압하압 모두 방향 일치하면 per-session으로 전환
3. **pseudoreplication 수정**: 호흡식별·전방공명을 per-session으로 통일
4. **검증 n 확보**: 현재 n=11 → T2 추가로 n=21~22 → 통계 신뢰도 향상

스크립트 위치: `dml-server/scripts/sidetrack/chest_head_indicators.py`

### 8-5. 발표 자료 시각화 (2026-05-03 완료)

---

## 9. MIDI 파이프라인 + 타임라인 분석 (2026-05-04 완료)

### 9-1. 구현 요약

**MIDI → pitch_guide 변환**
- `dml-server/scripts/data_prep/inspect_midi.py` — MIDI 트랙 구조 분석 + 멜로디 트랙 자동 추정
  - 휴리스틱: poly_pct < 5%(+25점), 이름 키워드(+50점), 보컬 음역 [48,84](+20/10점), 평균 음표 길이 0.25~3.0s(+10점), 음표 수 > 400(-10점)
  - 004.mid 결과: instrument #0 "Split Chan 1", score=65.0 → C4~C6, 265음표, onset=31.47s ✓
- `dml-server/scripts/data_prep/midi_to_pitch_guide.py` — MIDI → `midi_segments` JSON 변환
  - 화음 처리: 겹치는 음표에서 최고음 선택
  - MIDI 범위 [36,96] 필터
  - `{id}.json` 업데이트 (`guide_source:"midi"`, `midi_segments` 추가) + `{id}_mr.json` 생성
- `dml-server/scripts/data_prep/batch_midi_to_pitch_guide.sh` — 전곡 일괄 변환

**004.mid 검증 결과**
- 265 segments, MIDI 60~84 (C4~C6), intro 공백 확인(31.469s 시작), poly=0%
- `004_mr.json` 생성 완료 (lrc_offset_sec=0.0s)

**타임라인 분석 (`/analyze` 확장)**
- `dml-server/model_server/services/timeline_analysis.py` (신규)
  - `build_chunks()`: LRC 세그먼트 병합(<2s) + 분할(>15s)
  - `analyze_with_timeline()`: 청크별 파이프라인 호출, voiced 부족 시 null 처리
- `schemas.py`: `TimelineScore`, `TimelineMetadata` 추가 (Optional, 하위 호환)
- `server.py`: `song_id` 쿼리 파라미터 추가 → LRC 자동 로드 → 타임라인 분석 통합

### 9-2. 타임라인 검증 결과 (test_11, 2026-05-04)

**입력**: `data/vocal_academy/validation_t2/test_11.wav` (223.6s, excellent_high 케이스)
**LRC**: `data/songs/lrc/parsed/004_aligned.json` (25 lines → 28 chunks 병합/분할)

| 검증 항목 | 결과 | 판정 |
|-----------|------|------|
| Audio 내 skip 비율 | 4/22 = **18.2%** | ✓ (< 20%) |
| 접촉강도 전곡↔chunk 일관성 | \|0.00 − 0.20\| = **0.20점** | ✓ (< 1.0점) |
| 호흡식별 전곡↔chunk 일관성 | \|3.36 − 3.17\| = **0.19점** | ✓ (< 1.0점) |
| 호흡식별 chunk별 변동 | 0.00~5.00 (음절/구문 단위 포착) | ✓ 음악적 합리적 |

**처리 시간**: 전곡 17.3s + 타임라인 10.9s = **총 28.2s** (162~224s 오디오 기준)

**한계 (예상됨)**: 접촉강도 대부분 0.00 클리핑 → per-register 아티팩트 잔존.
5월 10일 score_mapper 재학습 후 재검증 필요.

**산출물**: `dml-server/results/timeline_validation_test_11.json`

### 9-3. 5월 10일 후속 작업 큐

1. `bash dml-server/scripts/data_prep/batch_midi_to_pitch_guide.sh` — 나머지 13곡 MIDI 변환
2. `bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh` — T2 데이터 처리
3. per-session score_mapper 재학습 (흉성두성·접촉강도·호흡식별 우선)
4. demo_responses 5종 재생성 (song_id 파라미터 포함)
5. timeline 검증 재실행 — 접촉강도 클리핑 개선 확인

**생성 파일**: `dml-server/results/sidetrack/`
- `matching_diagnosis_bars.png` — 항목별 Pearson r 비교 (grouped bar + 95% CI, 흉성두성 금색 강조)
- `matching_diagnosis_heatmap.png` — 7×3 히트맵 (RdYlGn, 흉성두성 행 금색 테두리)
- `matching_diagnosis_focus.png` — 흉성두성 집중 분석 + 아티팩트 메커니즘 설명 패널
- `diagnosis_summary.md` — 전체 진단 보고서 (항목별 해석 + 향후 작업)

**슬라이드 활용 포인트**:
1. heatmap → "AI 지표와 트레이너 점수의 상관계수 전체 조망" (한 장에 21개 데이터 포인트)
2. focus → "흉성두성 음의 상관의 실체: 훈련 데이터 특이성, 독립 검증에서 +0.554로 반전"
3. bars → "매칭 방식에 따른 r 변화: 5월 10일 데이터로 재학습 방향 결정"

**학술적 가치 진술**:
> "EGG 기반 AI 지표의 생리적 타당도는 독립 검증 데이터(n=11)에서 확인되었으나,
> 기존 훈련 데이터(n=19~23)에서의 역상관은 매칭 방식의 방법론적 제약과 데이터 분포 특이성에서 기인한다.
> 5월 10일 데이터(n≈10 추가) 수집 후 per-session 재학습으로 이 한계를 해소할 예정이다."

---

## 10. 외부 MIDI 옥타브 차이 발견 + 자체 F0 추출 전환 (2026-05-04)

### 10-1. 발견

앱 검증 중 외부 MIDI(midiex.net 등) 기반 pitch guide가 가수 실제 음역과 1옥타브 어긋나는 문제 발견.

| 항목 | 외부 MIDI (Steinway) | 자체 F0 (vocals.wav) |
|------|---------------------|---------------------|
| segments 수 | 265 | 214 |
| 음역대 min | C4 (MIDI 60) | B2 (MIDI 47) |
| 음역대 max | C6 (MIDI 84) | A5 (MIDI 81) |
| 평균 MIDI | 73.3 | 61.1 |
| 차이 중앙값 | — | +12.0 (정확히 1옥타브) |

**진단**: 외부 MIDI Steinway 트랙이 보컬 옥타브 위에 작성된 데이터.  
자체 F0 음역 B2~A5 (MIDI 47~81)이 김범수 테너 음역과 일치.

### 10-2. 결론 및 방향

- **외부 카라오케 MIDI** (midiex.net 등)는 트랙 구조 표준화 부족 → 직접 사용 시 옥타브 transpose 검증 필수
- **자체 vocals.wav F0 추출**이 가창 가이드라인으로 더 안전하고 정확
- `guide_source` 필드: `"midi"` (외부) / `"f0"` (자체 추출) / `"crepe"` (raw)로 구분

### 10-3. 구현

**신규 스크립트**: `dml-server/scripts/data_prep/f0_to_midi_segments.py`
- 입력: `pitch_guide/{id}.json`의 `points[]` (CREPE 재실행 불필요)
- 알고리즘: voiced 프레임 추출 → 임계값 기반 경계 탐지 → 평균 MIDI 반올림 → 짧은 구간 제거 → 인접 동일음 병합
- CLI: `--midi-threshold` (0.5), `--min-segment-ms` (100), `--voiced-gap-ms` (100), `--smoothing` (median 옵션), `--dry-run`
- `--dry-run` 모드: JSON 수정 없이 비교 테이블 + PNG만 출력

**일괄 처리**: `dml-server/scripts/data_prep/batch_f0_to_midi_segments.sh`

### 10-4. 처리 결과 (2026-05-04)

| 곡 | guide_source | segments | 음역 (MIDI) | lrc_offset |
|----|-------------|----------|------------|-----------|
| 004 김범수 보고싶다 | f0 | 214 | 47~81 (B2~A5) | 0.000s |
| 002 윤하 기다리다 | f0 | 334 | 54~82 (F#3~A#5) | −0.069s |

백업: `data/songs/pitch_guide/004_external_midi.json` (외부 MIDI 원본 보존)

### 10-5. 발표 자료 활용

- "외부 데이터 신뢰성 검증" 슬라이드 후보
- 자체 F0 추출 파이프라인의 가치: "공개 MIDI 데이터의 옥타브 오류를 검출하고 보컬에서 직접 추출"
- 졸업작품 분석 깊이 강조 포인트

### 10-6. 5월 10일 학원 MIDI 도착 시 처리 방침

외부 MIDI 받더라도 **옥타브 검증 필수**:
```bash
# 1. 외부 MIDI 비교 (dry-run)
python dml-server/scripts/data_prep/f0_to_midi_segments.py --song NNN --dry-run

# 2. 옥타브 차이 확인 후 자체 F0 채택
bash dml-server/scripts/data_prep/batch_f0_to_midi_segments.sh
```
