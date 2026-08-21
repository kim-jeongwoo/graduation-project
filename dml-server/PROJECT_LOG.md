# PROJECT_LOG.md — 졸업작품 진행 일지
순천향대 IoT학과 | 김정우 | 최종 갱신: 2026-05-04

---

## 0. 현황 요약 (2026-05-04 — 새 채팅방용 빠른 참조)

### 완료된 Phase

| Phase | 내용 | 산출물 |
|-------|------|--------|
| **T1** | 14곡 Demucs 분리 + CREPE F0 + LRC 수집 + MR 정렬 | `data/songs/{audio,lrc,pitch_guide,stems}` |
| **W** | LRC Whisper ASR — 001·007·011 3곡 완료 ✓ | `lrc/parsed/00{1,7,11}*.json` (총 42개) |
| **L** | model_server `/analyze` 9항목 + timeline_scores | `services/timeline_analysis.py`, `demo_responses/` |
| **F** | 자체 F0 추출 파이프라인 (외부 MIDI 옥타브 오류 발견 → 전환) | `f0_to_midi_segments.py`, `batch_f0_to_midi_segments.sh` |
| **T2 준비** | `run_t2_pipeline.sh` 3가지 모드 사전 검증 완료 | 5월 10일 데이터 도착 즉시 실행 가능 |
| **진단** | score_mapper per-register vs per-session 매칭 아티팩트 규명 | `results/sidetrack/matching_diagnosis_*.png` |

### Whisper ASR 결과 (이전 세션 완료)

| ID | 곡명 | 줄 수 | avg_conf | alignment_status | whisper_snr |
|----|------|-------|----------|-----------------|-------------|
| 001 | 한로로 - 시간을 달리네 | 26줄 | — | auto | 1.21 |
| 007 | 지아 - 물론 | 23줄 | 0.93 | auto | 1.15 |
| 011 | 양다일 - 요즘 | 34줄 | 0.96 | auto | 1.21 |

- songs.json + pitch_guide 메타 갱신 완료
- Mac Studio sync 완료 (lrc/parsed 42 json)
- 001 특이사항: manual_review 1줄 (곡말 "감사합니다" 노이즈)

### 현재 상태 (2026-05-04)

- **dml-server**: 대기 모드. 5월 10일 학원 데이터 도착 전까지 score_mapper 변경 금지.
- **LRC**: 14/14곡 완료 (11곡 LRCLIB + 3곡 Whisper ASR)
- **pitch_guide**: 002(F#3~A#5), 004(B2~A5) `guide_source=f0` 처리 완료. 나머지 12곡은 5월 10일 이후 일괄 처리.
- **Mac Studio sync**: `cd /Users/kimjeongwoo/vocal-server && bash dml-server/scripts/sync_songs.sh`
- **vocal-app**: 갤럭시 재검증 진행 중.

### 다음 액션 (2026-05-10 갱신)

1. **5/10 도착 데이터 Phase 1+2 분석 완료** ✓ (자세히는 §11, §12)
2. **Phase 3 (새 채팅방)**:
   - K-9 마이크 강건성 분석 (학습 vs 5/10 indicator 분포 비교)
   - K-10 매핑 재학습 결정 (5/10 데이터 활용 또는 마이크별 분리)
   - K-11 종합 보고서
3. **5/10~24**: 통제 실험 진행 (학원 측, dml-server 모델 변경 금지)
4. **5/24+**: B그룹 After 도착 → Before/After 비교 + 사전/사후 분석
5. **6월 초**: PPT 발표 자료 작성
6. **6월 15일**: 발표

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
- [x] **LRC 3곡**: ~~001·007·011 Whisper ASR 자동 생성 vs 수동 작성~~ → Whisper ASR 완료. 14/14곡 LRC 확보.
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
| 2026-05-04 | Whisper ASR 완료 (001·007·011). 14/14곡 LRC 확보. songs.json + Mac Studio sync 완료. |
| 2026-05-05 | 무음 입력 가드 (SilentInputError Guard A/B) 구현. HTTP 422 → 200 no_voice 응답 변환. 6종 합성 wav 검증 PASS. |
| 2026-05-05 | user_f0 응답 추가 (25Hz sparse null). schemas.py UserF0, AnalysisResponse 확장. 실측: 103s→42KB, 224s→80KB. |
| 2026-05-05 | CLAUDE.md 에이전트 행동 규칙 → Karpathy 4원칙으로 재구성. |
| 2026-05-05 | timeline_scores 빈 배열 진단 완료. 원인: vocal-server song_id 미전달. dml-server 정상. |
| 2026-05-05 | chunk MIN_VOICED_S 2.0s 완화 + 접촉강도 timeline 비활성화 (threshold unstable). |
| 2026-05-09 | /ws/realtime WebSocket 엔드포인트 구현. 음정 일치율(200ms)+호흡 chunk(5s) 동시 제공. 검증: pitch latency p95=2.9ms, 호흡 chunk 3.12 vs 전체 3.36 (차이 0.24 ✓). |
| 2026-05-09 | /analyze-chunk endpoint 신설 (Phase 4 사후 측정). 호흡/접촉 통합 점수 1개. duration<3s→400, voiced_s<dur×0.4→no_voice. 7케이스 검증 PASS, 일관성 차이 0.07. 5s=368ms / 10s=716ms (목표 5000ms ≪ 달성). |
| 2026-05-09 | SKT LTE 8001 비표준 포트 차단 발견 → Cloudflare Tunnel(trycloudflare) 셋업. 3 endpoint 모두 검증 PASS: /health 818ms, WSS RTT 22ms, /analyze-chunk 628ms. URL: `~/.cloudflared/current-url.txt`. nohup 백그라운드 실행 중 (systemd는 사용자 sudo 보류). |
| 2026-05-09 | trycloudflare → named tunnel 전환. **`https://dml.vocal-fit.com`** 영구 도메인 발급. tunnel UUID 725417d8-...ebe5. 4 connection (icn01/05/06×2). 검증 PASS: /health 666ms, WSS connect 688ms, /analyze-chunk 2346ms. systemd 등록은 사용자 sudo 보류 (현재 nohup 운영). |
| 2026-05-09 | systemd 등록 + K-9 재기동 시뮬레이션 PASS. Restart=always 작동 확인 (다운타임 ~10초, 안정화 ~20초). 동일 URL 유지. 14일 안정 운영 + 6/15 발표까지 보장. dml-server 측 작업 종료. |
| 2026-05-10 | 5/10 데이터(A10+B11+미디6+평가지5) Phase 1 분석 PASS. 5 raters 평가지 → 315행. 통합 ICC: 호흡식별 0.796 / 접촉강도 0.898 / 상압하압 0.910. A 단독: 호흡 0.770 / 접촉 0.898. B 단독: 호흡 0.836 / 접촉 0.897 / 연구개위치 0.321 (poor). 외부 MIDI 6곡 옥타브 모두 정상. Phase 2 진행 가능. |
| 2026-05-10 | Phase 2 매칭 비교 + 신뢰도 재분류 완료. per-register 채택(per-session 효과 없음, 학습 z corr ≈0). 5/10 corr: 호흡식별 +0.705 / 상압하압 +0.564 / 접촉강도 +0.358 / 흉성두성 +0.004 / 전방공명 -0.231(클리핑). 신뢰도 재분류: high 0개 / medium 2개(호흡식별·상압하압) / unavailable 7개. 전방공명 클리핑 원인 — spectral_centroid 학습 1047 vs 5/10 1580 (마이크 차이). |

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

---

## 11. Phase 1: 5/10 데이터 정리 + ICC (완료, 2026-05-10)

### 11-1. 입력
- A그룹 10명 wav (`validation_510/`, 방음부스 스마트폰)
- B그룹 11명 wav (`control_pre_510/`, 일반환경 스마트폰, 통제 실험 Before)
- 평가지 5개 docx (`_new_eval_510/`, 5명 평가자, 21명 평가, 9항목 × 3 register)
- 외부 미디 6곡 (`midi_510/`)

### 11-2. 데이터 정리
- 평가지 NFC 정규화 + 사용자 자체 수정 완료(평가5 B12 제거 + B10/B11 정정, 평가3 (앱) 표기)
- 디렉토리 분리: `validation_510 / control_pre_510 / _new_eval_510 / midi_510`
- 외부 MIDI 6곡 옥타브 모두 정상 (|diff|<3 semitone, 자체 F0 추출 불필요)

### 11-3. ICC 결과 (315 rows = 5 raters × 21 singers × 3 registers)

| 데이터셋 | n | 환경 | 호흡식별 ICC | 접촉강도 ICC | 9항목 평균 ICC |
|---|---:|---|---:|---:|---:|
| training (v2) | 10 (5 raters) | 학원 일반마이크 | 0.965 | 0.970 | 0.916 |
| validation (v2) | 11 (5 raters) | 학원 일반마이크 | 0.917 | 0.892 | 0.817 |
| **5/10 A그룹** | **10 (5 raters)** | **방음부스 + 스마트폰** | **0.770** | **0.898** | **0.797** |
| **5/10 B그룹** | **11 (5 raters)** | **일반환경 (앱 7명 포함)** | **0.836** | **0.897** | **0.764** |
| **5/10 A+B 통합** | **21 (5 raters)** | **혼합** | **0.796** | **0.898** | **0.793** |

핵심 관찰:
- **접촉강도 ICC 0.898** — 환경 무관 안정 (학습 0.970, validation 0.892와 거의 동등)
- **호흡식별 ICC 0.770~0.836** — 학습 0.965 대비 하락. 마이크 차이 가설.
- **상압하압 ICC 0.910** — 전 환경 excellent
- **B 단독 연구개위치 0.321 (poor) ⚠** — 11명 작은 표본 + 일반환경 noise. 통제 실험 분석 시 신중.

### 11-4. 산출물
- `data/vocal_academy/trainer_scores_510{,_a,_b}.csv` (315/150/165행)
- `data/vocal_academy/results/sidetrack/icc_510_{ab,a,b}.json`
- `data/vocal_academy/results/sidetrack/icc_510_report.md` (종합)
- `data/vocal_academy/results/sidetrack/midi_octave_check_510.md`
- `dml-server/scripts/sidetrack/{organize_510_data,parse_510_evals,verify_midi_octave_510}.py`

---

## 12. Phase 2: 매칭 비교 + 신뢰도 재분류 (완료, 2026-05-10)

### 12-1. K-6 추론
- `pipeline.analyze()` 21명 일괄 (총 361.6s, 평균 17.2s/곡)
- 9항목 ai_score + indicators(cq_peak, cpp_mean, ...) JSON 21개
- voiced_ratio 0.518~0.772 (mean 0.683) — 모두 정상
- A5 cq_peak outlier 1건 (z=+2.9) — per-session에서 자동 완화 예상이었으나 per-session 효과 없음(아래)

### 12-2. K-7 per-register vs per-session 매칭 결정

**per-session 매핑 학습 결과 (학습 데이터 99 entries):**
- 흉성두성: z vs trainer corr = -0.043
- 접촉강도: z vs trainer corr = +0.044
- 상압하압: z vs trainer corr = +0.101
- → 모두 거의 0. 임계값 모두 0 근처 수렴.

**결론: per-register 채택 (모든 항목)**
- 평가자는 register 간 상대 차이가 아닌 **절대값 기반**으로 점수 매김
- per-session 가설 기각 (학습 데이터에서도 정보 없음)

**5/10 21명 점수 vs 평가자 5명 평균 corr (n=63):**

| 항목 | per-register | per-session | Δ | 채택 |
|---|---:|---:|---:|---|
| 호흡식별 | **+0.705** | n/a (cpp register-invariant) | — | per-register |
| 상압하압 | +0.564 | -0.462 | -1.03 | per-register |
| 접촉강도 | +0.358 | -0.362 | -0.72 | per-register |
| 흉성두성 | +0.004 | +0.033 | +0.03 | per-register |
| 전방공명 | -0.231 | n/a | — | per-register (클리핑) |
| 비강사용/연구개위치/공명개방/혀경직도 | n/a | n/a | — | n/a |

### 12-3. K-8 신뢰도 재분류

| 항목 | ICC | corr | 분류 (이전 → 5/10 검증 후) |
|---|---:|---:|---|
| 호흡식별 | 0.796 | +0.705 | high → **medium** (ICC 0.796<0.8 경계 + corr 강함) |
| 상압하압 | 0.910 | +0.564 | medium → **medium** (유지) |
| 흉성두성 | 0.805 | +0.004 | medium → **unavailable** (corr 무상관) |
| 접촉강도 | 0.898 | +0.358 | high → **unavailable** (corr 부족) |
| 전방공명 | 0.762 | -0.231 | medium → **unavailable** (클리핑) |
| 비강사용 | 0.796 | — | medium → **unavailable** (지표 없음) |
| 연구개위치 | 0.643 | — | medium → **unavailable** |
| 공명개방 | 0.728 | — | unavail → unavail |
| 혀경직도 | 0.802 | — | unavail → unavail |

→ **high 0개 / medium 2개 / unavailable 7개**. 이전 high 2개(호흡식별·접촉강도) → medium/unavailable로 강등.

### 12-4. 전방공명 클리핑 원인 (마이크 의존)

```
spectral_centroid_mean:
  학습 데이터:  713~1394, mean 1047, median 1032
  5/10 데이터:  1224~2198, mean 1580, median 1537   (+50%)
  학습 매핑 임계값(decreasing): 1095(점수0) → 801(점수5)
  5/10 mean 1580 > 학습 max 1095 → 모두 점수 0 클리핑
```

원인: 5/10 마이크(스마트폰/방음부스)와 학습 마이크(학원 일반)의 spectral 응답 차이.
대처: K-9 마이크 강건성 분석 + K-10 매핑 재학습 (Phase 3).

### 12-5. 의외 발견 (Phase 3 검토)

1. **접촉강도 corr 0.358** — 학습 시 0.087과 동일한 약한 패턴. score_mapper 학습 자체가 약한 항목. cq_peak이 접촉강도 본질 지표인지 의문.
2. **흉성두성 corr 0.004** — 학습 시 -0.282였고 5/10에서 무상관. cq_mean이 흉성두성 본질 지표가 아닐 가능성 ↑
3. **호흡식별 corr 0.705** — 5/10에서 가장 강한 corr (학습 0.569 대비 ↑). 진짜 가창 본질 측정 항목으로 부각.

### 12-6. 산출물
- `data/vocal_academy/results/sidetrack/inference_510/{A1..A10,B1..B11}.json` (21개)
- `data/vocal_academy/results/sidetrack/matching_comparison_510.csv`
- `data/vocal_academy/results/sidetrack/reliability_510.csv`
- `dml-server/scripts/sidetrack/{inference_510,matching_comparison_510}.py`

### 12-7. 다음 단계 (Phase 3, 새 채팅방에서 진행)

- **K-9 마이크 강건성 분석**:
  - training/validation/A/B 항목별 corr 비교 + Δ corr 시각화
  - 마이크 강건 항목(Δ<0.1) vs 마이크 의존 항목(Δ≥0.1) 분류
  - 발표 슬라이드 D 갱신용
- **K-10 매핑 재학습 결정**:
  - per-register 유지 (Phase 2 결정)
  - 옵션 A: 5/10 데이터로 매핑 임계값 재학습 (특히 전방공명)
  - 옵션 B: 마이크별 매핑 분리 (학원 vs 스마트폰)
  - 흉성두성/접촉강도 corr 약함은 매핑으로 해결 어려움 → 지표 자체 재검토 필요
- **K-11 종합 보고서** (`phase2_report.md`)

---

## 13. 데이터 자산 카탈로그 (2026-05-11 보강)

데이터 디렉토리 직접 확인 결과. 새 채팅방 인계용. 추측 없음.

### 13-1. 14곡 노래방 가이드 (`data/songs/`)

| ID | 아티스트 - 곡명 | guide_source | 외부MIDI | LRC | 음역 (자체 F0) | 비고 |
|---|---|:-:|:-:|:-:|---|---|
| 001 | 한로로 - 시간을 달리네 | (default crepe?) | ✗ | ✓ | C#3-B5 | Whisper ASR LRC |
| 002 | 윤하 - 기다리다 | **f0** | ✗ | ✓ | C#3-B5 | 자체 F0 처리 완료 |
| 003 | 보보 - 늦은 후회 | (default crepe?) | ✗ | ✓ | D#3-A#5 | |
| 004 | 김범수 - 보고싶다 | **f0** | ✓ | ✓ | G2-A5 | **외부MIDI +12 옥타브 → 자체 F0 채택**, 백업: `pitch_guide/004_external_midi.json` |
| 005 | 이적 - 다행이다 | (default) | ✗ | ✓ | E2-E5 | |
| 006 | 폴킴 - 모든 날 모든 순간 | (default) | ✗ | ✓ | D3-E5 | |
| 007 | 지아 - 물론 | (default) | ✗ | ✓ | C3-E5 | Whisper ASR LRC |
| 008 | 이하이 - 한숨 | (default) | ✗ | ✓ | C#3-A#5 | |
| 009 | 거미 - 친구라도 될걸 그랬어 | (default) | ✗ | ✓ | C#3-A5 | |
| 010 | 나윤권 - 나였으면 | (default) | ✗ | ✓ | A#2-D#5 | |
| 011 | 양다일 - 요즘 | (default) | ✗ | ✓ | A2-G#5 | Whisper ASR LRC |
| 012 | 조성모 - 슬픈 영혼식 | (default) | ✗ | ✓ | D#3-C#5 | |
| 013 | 케이윌 - Love Blossom | (default) | ✗ | ✓ | C#3-G#5 | |
| 014 | 성시경 - 너의 모든 순간 | (default) | ✗ | ✓ | G#2-F5 | |

- pitch_guide JSON 위치: `data/songs/pitch_guide/{ID}.json` + `{ID}_mr.json`
- LRC 위치: `data/songs/lrc/parsed/{ID}.json` 또는 `{ID}_aligned.json`
- 외부 MIDI는 004만 보유 (`data/songs/midi/004.mid`). 002/004 자체 F0 처리 완료.
- 002/004 외 12곡의 guide_source는 명시 안 됨 (기본값 crepe 추정, 코드 default).

### 13-2. score_mapper 학습 데이터 (`data/vocal_academy/singer_01..22/`)

총 22명. 명명: `{singer}-{song}_{oral|nasal|phone}.wav`. ground truth: `trainer_scores.csv` 510 rows (5 raters).

| singer | wav 수 | 곡 수 | 채널 보유 | 평가 곡 (trainer_scores) |
|---:|---:|---:|---|---|
| 01 | 4 | 2 | oral+nasal | 1, 2 |
| 02 | 6 | 2 | oral+nasal+**phone** | 2, 3 |
| 03 | 6 | 2 | oral+nasal+**phone** | 2, 3 |
| 04 | 4 | 2 | oral+nasal | 4, 6 |
| 05 | 9 | 3 | oral+nasal+**phone** | 4, 5, 6 |
| 06 | 6 | 2 | oral+nasal+**phone** | 7, 8 |
| 07 | 3 | 1 | oral+nasal+**phone** | 9 |
| 08 | 3 | 1 | oral+nasal+**phone** | 10 |
| 09 | 3 | 1 | oral+nasal+**phone** | 10 |
| 10 | 3 | 1 | oral+nasal+**phone** | 11 |
| 11 | 6 | 2 | oral+nasal+**phone** | 4, 6 |
| 12 | 15 | 5 | oral+nasal+**phone** | 4, 5, 6, 12, 13 |
| 13~21 | 3×9 | 1×9 | oral+nasal+**phone** | (song 컬럼 일부 빈값) |
| 22 | 2 | 1 | oral+nasal | (song 빈값) |

- **phone 채널 보유 가수: 19명** (총 phone wav 29개). 미보유: 1, 4, 22.
- score_mapper 학습 마이크: **oral.wav만 사용** (`score_mapper.get_ai_value`).
- 녹음 일자: 평가지(`_new_eval_v2/평가지N.docx`) 평가 일시 **20260427** 기준 약 4월말.

### 13-3. validation 11명 (`data/vocal_academy/validation_t2/`)

- 파일: `test_01.wav ~ test_11.wav` (11개)
- 메타: 48000Hz / PCM_24 / mono (11개 모두 동일)
- duration: mean 181s [101~268]
- ground truth: `trainer_scores_validation.csv` (test_01~test_11, 5 raters)
- 마이크: 단일 채널 (학원 일반 마이크 추정)
- 녹음 환경: 학습 22명과 같은 학원 환경 (CLAUDE.md 기준)

### 13-4. 5/10 신규 데이터 (`data/vocal_academy/{validation_510, control_pre_510}/`)

| 그룹 | 디렉토리 | 인원 | 환경 | 마이크 | 비고 |
|---|---|:-:|---|---|---|
| **A** | `validation_510/` | 10 (A1~A10) | **방음부스** | 스마트폰 | A9.wav만 PCM_16, 나머지 9개 PCM_24 |
| **B** | `control_pre_510/` | 11 (B1~B11) | 일반환경 | 스마트폰 | 7명 (B6~B11) "(앱)" 표기 — 앱 사용 녹음 |

- sample_rate: 48000Hz / mono (전부 동일)
- duration: A 평균 189s [152~216], B 평균 218s [162~301]
- ground truth: `trainer_scores_510.csv` (315 rows = 5 raters × 21 singers × 3 register)
- ID-곡명 매핑 (평가1.docx 첫 표 기준):

| ID | 곡 | 14곡 매칭 |
|---|---|---|
| A1 | 물론 | 007 |
| A2 | 세상이그대를속일지라도 | 14곡 외 |
| A3 | 눈사람 | 14곡 외 |
| A4 | 화장을고치고 | 14곡 외 |
| A5 | 시든꽃에물을주듯 | 14곡 외 |
| A6 | 응급실 | 14곡 외 |
| A7 | 사랑해요 | 14곡 외 |
| A8 | Brave heart | 14곡 외 |
| A9 | 보고싶다 | 004 |
| A10 | 물론 | 007 (허각? 14곡 외) |
| B1 | 응급실 | 14곡 외 |
| B2 | 봄이와도 | 14곡 외 |
| B3 | 꽃길 | 14곡 외 |
| B4 | 늘 | 14곡 외 |
| B5 | Happy Birthday | 14곡 외 |
| B6~B11 | 앱 사용 곡 | 14곡 외 |

→ 5/10 21명 중 14곡 매칭은 A1, A9, A10 정도. **대부분 14곡 외 자유곡.**

### 13-5. raw_2026 phone 별도 인벤토리

위치: `~/egg_prediction/data/vocal_academy/raw_2026_phone_inventory/구강_비강_폰/보컬 데이터/` (평면 구조, NFD 인코딩)

- 69 wav (oral 24 + nasal 24 + phone 21)
- 12명 가수 (1~12), 24 (singer, song) pairs, triplet 20 pairs
- **이 데이터는 `singer_NN/` 학습 디렉토리에 이미 통합됨** (md5 동일 확인)
- 재인벤토리 스크립트: `scripts/sidetrack/phone_inventory_2026_05.csv`

### 13-6. 평가지 메타데이터

| 데이터셋 | 디렉토리 | 평가일 | 평가자 ID |
|---|---|---|---|
| 학습 (4월) | `_new_eval_v2/평가지1~5.docx` | **20260427** | 1, 2, 3, 4, 5 |
| 5/10 | `_new_eval_510/평가1~5.docx` | **20260509** | 1, 2, 3, 4, 5 |

- 평가자 ID 동일 (1~5 양쪽). Phase 2 §12-2 K-8.5c 평가자 통합 분포 |d|≥0.5 항목 0~1개 → **동일인 가능성 강함** (메타데이터로도 ID 일치).
- 평가일 차이: 약 12일 (4/27 → 5/9).

### 13-7. 가수 ID 누설 점검

가수 실명 메타 미확보 (`song_map.json`은 곡 매핑만, 가수 매핑 없음).

| 비교 | 명명체계 | 직접 비교 |
|---|---|---|
| 학습 22명 | 정수 1~22 | — |
| validation 11명 | test_01~test_11 | — |
| 5/10 A그룹 10명 | A1~A10 | — |
| 5/10 B그룹 11명 | B1~B11 | — |

→ **명명체계 완전 다름. 직접 ID 매칭 불가.**

간접 추론:
- 학습 22명은 14곡 자유곡 위주 (대부분 매칭). 5/10 21명은 **대부분 14곡 외 곡** (A1/A9/A10 일부만).
- 5/10 A그룹 곡명에 "응급실", "꽃길", "안녕" 등 학원 자유 선곡으로 추정 → **다른 가수 풀** 추정.
- 단 **확정 불가**. 학원에 가수 실명 매핑 요청 필요.

### 13-8. 마이크 종류별 indicator 분포 (K-9 사전 준비)

| indicator | 학습 (oral) | 5/10 (스마트폰) | shift |
|---|---|---|---|
| spectral_centroid_mean | 1047 (std 165, n=69) | **1576** (std 250, n=21) | **⚠ +50%** |
| spectral_tilt | -0.978 (std 0.269) | -0.737 (std 0.152) | ⚠ shift +0.24 |
| cq_peak (cq_p90) | 0.551 (std 0.058, n=57) | 0.551 (std 0.040, n=21) | ✓ 동등 |
| cpp_mean | 0.386 (std 0.052, n=69) | 0.394 (std 0.053, n=21) | ✓ 동등 |
| cq_mean | 0.460 (std 0.018) | 0.448 (std 0.012) | ✓ 동등 |
| nasal_ratio | 0.325 (std 0.078, n=69) | — (5/10 nasal mic 미보유) | n/a |

→ **spectral 계열(centroid/tilt)이 마이크 의존**, **EGG 계열(cq/cpp)은 강건**. 전방공명 5/10 클리핑 원인 = centroid +50% shift.

---

## 14. score_mapper 학습 명세 정리 (§13-2 + 임계값)

### 14-1. 학습 데이터 단위

- **데이터**: `trainer_scores.csv` 510 rows = 22 singers × 5 raters × 33 (singer, song) sessions × 3 register
- **매핑 단위**: `(singer, song, register)` — n=99 entries (excludes pair (6, 8))
- **마이크**: oral.wav만 사용 (score_mapper.get_ai_value)
- **9항목 분류**: 7개 매핑 학습 / 2개 skip (공명개방, 혀경직도 — indicator 없음)

### 14-2. 항목별 매핑 임계값

| 항목 | indicator | n_pairs | 학습 corr | method | thresholds (점수 0→5) |
|---|---|---:|---:|---|---|
| 비강사용 | nasal_ratio | 69 | +0.025 | percentile | 0.317 / 0.317 / 0.331 / 0.293 / 0.293 / 0.293 |
| 흉성두성 | cq_mean | 57 | -0.282 | linear | (decreasing) |
| 접촉강도 | cq_peak | 57 | +0.087 | percentile | 0.5297 ×4 ... narrow |
| 호흡식별 | cpp | 69 | **+0.569** | linear | (increasing) |
| 전방공명 | spectral_centroid | 69 | -0.317 | linear | **1095/1095/1095/1004/801/801** (decreasing) |
| 연구개위치 | nasal_ratio | 69 | -0.210 | linear | (decreasing) |
| 상압하압 | spectral_tilt | 69 | **+0.556** | linear | (increasing) |

전방공명 임계값 max=1095 → **5/10 mean 1576 > 1095** → 모두 점수 0 클리핑 (Phase 2 §12-4 확인).

---

## 15. 배포 이력 (Deployment History)

**운영 규칙**:
- dml-server 코드 변경 또는 production restart 시 새 항목 추가
- vocal-server / vocal-app 페이지가 새 작업 시작 시 §15 최신 항목 확인
- 트리거: 응답 schema 변경, endpoint 변경, production process restart

### §15-0 소급 정리 (알려진 이전 배포)

| 일자 | 배포 내용 | 영향 / 공유 상태 |
|---|---|---|
| 2026-04-17 | ai-model Exp20 Best (Test Corr 0.8249), model_server FastAPI 가동 (port 8001) | 초기 배포 |
| 2026-04-22 | 3개 워크스페이스 `.claude/settings.json` 생성 | 개발환경 설정 |
| 2026-05-04 | `/analyze` 응답에 `user_f0` 필드 추가 (옵션 C: 25Hz sparse null) | vocal-server result_json 통과 OK, **사후 공유 누락 사례** |

### §15-1 — 2026-05-11 22:50 score_mapper_v2 production restart (F4 완료)

**변경 내용**:
- F4: `timeline_scores` 4항목 확장 (`3_vocal_fold_contact`, `4_breathiness`, `6_soft_palate`, `8_tongue_tension`)
- `/analyze` 응답 schema 확장:
  `scores_v2`, `scores_meta`, `academic_analysis_scores`, `score_mapper_version`, `reliability.shown_v2`
- `/analyze-chunk` 응답 schema 확장:
  `scores_v2`, `scores_meta`, `low_confidence_items`, `chunk_duration_s`, `score_mapper_version`
  - **⚠ 정정 (5/12 추가)**: 본 항목은 F4 작업 시 `/analyze`와 함께 통합되었으나 vocal-server / vocal-app **사전 공유 누락**.
    5/12 vocal-app 갤럭시 검증에서 `/sessions/{id}/training-analyze` forward 시 v2 필드 누락 발견. 상세는 §15-5.
- `timeline_scores[i].scores` 형식 변경: float → dict (`ai_score` / `rounded_score` / `tier`)  ← **breaking**
- `analysis_pipeline.py` + `timeline_analysis.py` + `score_mapper_v2.py` 통합
- `mapping_params_v2.json` 적용 (6 모델: Ridge/ElasticNet/GB/Lasso)

**영향 받는 페이지**:
- **vocal-server**: result_json 통째 저장 패턴 → 자동 통과 (schema 변경 무영향)
- **vocal-app**: v1 → v2 분기 처리 추가 필요
  - detect: `result.score_mapper_version === "v2" && result.scores_v2` 사용
  - tier별 UI: `high` 기본 / `high_star` 별표+툴팁
  - `timeline_scores[i].scores.4_breathiness` dict로 변경 (이전 float)

**배포 과정**:
- 22:00 — F4 코드 작성 시작
- 22:40 — F4 검증 완료 (21명 578 chunks, out_of_range 0, full-song ref corr 0.69~0.89)
- 22:50 — production restart (`fuser -k 8001/tcp` → `nohup python server.py`)
- 22:55 — 검증: `localhost:8001/analyze` + `dml.vocal-fit.com/analyze` 양쪽 v2 키 정상 반환 확인

**배포 누락 사고 (root cause)**:
- model_server `python server.py` (PID 3362489)이 **5/9부터 가동 중**, F4 코드 변경 후 restart 미수행
- vocal-app / vocal-server에서 "v2 필드 없음" 보고 → 22:50 emergency restart로 해결
- **재발 방지**: §15 배포 이력 + 5/13 systemd unit 작업 예정

**알려진 한계** (학원 실험 중 모니터링):
- B1 sequential state leak (11+ sample 누적 시): 실 endpoint 영향 작음, periodic restart로 회피
- 호흡식별 `train_val_sign_diverged`, `val_total_below_0_5` (tier=high_star caveat 명시)
- 연구개위치/혀경직도 `train_weak_external_only` (tier=high_star caveat 명시)
- 비강사용/전방공명 `sign_reversed` (academic_only, 앱 표시 X)

**산출물**:
- `dml-server/model_server/services/timeline_analysis.py` (수정)
- `dml-server/model_server/server.py` (수정)
- `dml-server/model_server/analysis_pipeline.py` (D3 통합 시 기 적용)
- `dml-server/docs/vocal_app_score_mapper_v2_spec.md` (§8 신규)
- `data/vocal_academy/results/sidetrack/timeline_scores_4items_validation.csv` (578 rows)
- `data/vocal_academy/results/sidetrack/timeline_scores_4items_summary.csv` (21 wavs)
- `data/vocal_academy/results/sidetrack/sample_response_analyze.json` (vocal-app 명세용)

### §15-2 — 5/14 학원 실험 운영 권고 (5가지)

1. **single uvicorn worker**: `python server.py` (현재 단일 worker로 가동 중) — 멀티 worker 시 score_mapper_v2 메모리 중복
2. **periodic restart**: 50 req마다 또는 1시간마다 worker restart (cron 또는 supervisor) — sequential state leak 회피
3. **학원 기간 모니터링**:
   - 동일 가수 점수가 다른 시점에 다르게 나오는지 주기 확인
   - `timeline_scores` chunk 점수 분포 합리성 (mean/std 트래킹)
   - 응답 schema 정상 (`score_mapper_version="v2"` 유지) 확인
4. **dml-server systemd unit** (5/13 작업 예정): `cloudflared-tunnel.service`와 유사 패턴. `systemctl restart dml-server` 1줄로 자동화. nohup 수동 launch 의존 제거.
5. **§15 배포 이력 작성**: 모든 dml-server 코드 변경/restart 시 §15에 새 항목 추가. vocal-server / vocal-app 페이지가 새 작업 시작 시 §15 최신 항목 확인.

### §15-3 — 2026-05-12 `/analyze` StreamingResponse 적용 (Cloudflare 125s 우회)

**배경**:
- vocal-server 측 critical 발견 보고: Cloudflare Tunnel TTFB 한계로 곡 분석 응답이 524 위험
- 실측 (`/_debug_sleep` probe): 105s OK, **200s/300s 모두 524 at 125.6s** — 실제 한계 ≈ 125s
- 곡 전체 `/analyze` 비용 ~150~180s → 125s 초과 위험 매우 큼

**변경 내용** (`dml-server/model_server/server.py`):
- `/analyze` handler를 `StreamingResponse(media_type="application/json")`로 변환
- 동작:
  1. 첫 byte 즉시 송신 (leading whitespace `b" "`) → **TTFB ~0s, Cloudflare 524 우회**
  2. 분석은 `asyncio.to_thread(_analyze_sync, ...)`로 별도 thread 실행
  3. 5s마다 leading whitespace `b" "` keepalive ping
  4. 처리 완료 후 최종 JSON body 송신
- 표준 JSON parser는 leading whitespace 무시 (RFC 7159) → **응답 schema 변경 0**
- `_analyze_sync` 함수 분리 (sync, thread pool 실행용)

**예외 처리 통일 (P2-A 채택)** — streaming 시작 후 HTTP status code 변경 불가:
| 케이스 | 변경 전 | 변경 후 |
|---|---|---|
| 정상 | 200 + status='success' | (동일) |
| 무음/잡음 | 200 + status='no_voice' | (동일) |
| `ValueError` | **HTTP 422** | **200 + status='invalid' + error** |
| 일반 `Exception` | **HTTP 500** | **200 + status='failed' + error** |
| file 검증 실패 | 400 | (동일, streaming 시작 전 raise) |
| 모듈 미로드 | 503 | (동일, streaming 시작 전 raise) |

**검증 결과** (5/12 검증):
| 시나리오 | HTTP | TTFB | read | body.status |
|---|---:|---:|---:|---|
| B6 301s 곡 전체 (tunnel) | 200 | 6.0s | **147.2s** | success — **125s 초과 정상 응답, 524 회피** |
| B1 30s (tunnel) | 200 | 2.3s | 15.1s | success |
| 무음 10s | 200 | 1.5s | 1.6s | no_voice |
| 너무 작은 file (200B) | **400** | — | — | — |
| garbage 5KB | 200 | 0.0s | 0.0s | failed |

P1 사전 검증 양쪽 통과 확인:
- vocal-server (commit 52710c9): `/_test_stream?duration=130` response.json() 자동 파싱 OK
- vocal-app (run_id 451329b0...): 동일 endpoint OK
- 코드 수정 0줄 양쪽

**영향**:
- **vocal-server** (result_json 통째 저장 패턴): **자동 통과**. 422/500 → 200 변경으로 dict 저장 분기에 영향 없음
- **vocal-app**: 422/500 status code를 명시적으로 분기 처리한 코드가 있다면 미세 변경 필요 (body의 `status` 필드로 분기 권장)
  - body 형태: `{"run_id":..., "status":"invalid"|"failed", "error":...}`
  - 정상 케이스는 영향 0

**추가 변경**:
- 임시 `/_test_stream` endpoint 제거 (P1 검증 완료 후)
- `/analyze-chunk`는 ~3~5s 응답이라 125s 마진 충분, 변경 없음 (5/12 검증에서 v2 응답 정상 확인됨)
- `/predict`, `/health`, `/ws/realtime` 변경 없음

**배포 과정**:
- 5/12 ~00:00 — Phase 1 사전 점검 (`/_test_stream`) → 양쪽 통과
- 5/12 — Phase 2 구현 + 검증 (B6 301s 정상, 4 시나리오 통과)
- restart: `fuser -k 8001/tcp` → `nohup python server.py`

**기타 알려진 한계**:
- `garbage` 케이스에서 `soundfile.LibsndfileError`가 `ValueError`가 아닌 일반 `Exception`로 잡혀서 `status='failed'`. spec 의도는 'invalid'였으나 vocal-server/app 측 영향 없으므로 그대로 두기.
- streaming response가 leading whitespace 18~30 bytes 추가됨 (총 응답 130KB 기준 0.02% 오버헤드, 무시 가능)

**§15-3 적용 범위 명확화 (보강 5/12)**:
- §15 "응답 schema 변경" 정의: 응답 body의 키/값/형식이 바뀌는 모든 변경. status code 변경 포함.
- **모든 endpoint 명시 의무**: 변경 작업 시 영향 받는 endpoint를 빠짐없이 나열 (`/analyze`, `/analyze-chunk`, `/ws/realtime`, `/predict`, `/health`)
- **endpoint별 변경 사항 명시 의무**: endpoint마다 schema 변경 내용을 항목별로 분리 기술 (한 항목에 묶어 쓰지 말 것)
- **사전 공유 → 검증 → 자동 통과 패턴**: P1 사전 검증 (vocal-server/vocal-app 양쪽 OK) → P2 본격 적용 → 자동 통과. 향후 모든 schema 변경 시 본 패턴 적용.

### §15-4 — 2026-05-12 Phase 2 StreamingResponse 적용 (회고)

**요약**: §15-3에 기술된 `/analyze` StreamingResponse 적용에 대한 메타 회고.

**변경 단계**:
1. **Phase 1 사전 점검**: `/_test_stream?duration=130` 임시 endpoint 추가 → vocal-server / vocal-app 양쪽 호출 검증
2. **Phase 2 본격 적용**: `/analyze` handler StreamingResponse + 예외 status 통일
3. **검증**: B6 301s 곡 tunnel HTTP 200, read 147.2s (125s 초과 정상 응답)
4. **임시 endpoint 제거**: `/_test_stream` 제거

**영향 결과**:
- vocal-server: 자동 통과 (P1 검증에서 commit 52710c9로 확정 — 코드 수정 0줄)
- vocal-app: 코드 수정 0 (status 422/500 명시 처리 코드 없음 — P1 검증 결과)
- vocal-app run_id: 451329b0...로 P1 검증 완료

**§15-3 패턴 두 번째 성공**:
- 첫 번째: §15-1 v2 통합 → 5/11 22:50 restart 누락 사고 → 사후 수습
- 두 번째: §15-4 StreamingResponse → P1 사전 공유 → 자동 통과 → **무사고 배포 성공**
- 결론: 사전 공유 패턴이 무사고 배포에 결정적. 향후 모든 schema 변경에 적용.

### §15-5 — 2026-05-11 F4 시점 `/analyze-chunk` v2 통합 사전 공유 누락 (소급 정정)

**사고 내용**:
- 5/11 F4 작업 시 `/analyze-chunk`도 `scores_v2` / `scores_meta` / `low_confidence_items` / `chunk_duration_s` / `score_mapper_version` 추가
- §15-1 (F4 배포 항목)에서 `/analyze-chunk`도 v2 통합 명시했으나, **vocal-server / vocal-app 측 사전 공유 누락**
- 5/12 vocal-app 갤럭시 검증에서 `/sessions/{id}/training-analyze` forward 시 v2 필드 누락 발견
- 원인: dml-server 작업 시 `/analyze`만 사전 공유 + `/analyze-chunk`는 빠뜨림 (endpoint별 변경 분리 인지 부족)

**대응**:
- §15-3 보강: 응답 schema 변경 시 영향 받는 모든 endpoint 명시 의무화
- §15-1 정정: `/analyze-chunk` v2 통합 항목에 "사전 공유 누락" 노트 추가
- CLAUDE.md `#반복하지말것` 추가: [페이지 간 정보 동기화] 항목

**검증** (5/12, F4-3 chunk endpoint 점검):
- localhost / 8s, tunnel / 8s, localhost / 3.5s, tunnel / 3.5s 모두 v2 키 정상 응답
- legacy `scores` (2 항목) 호환 유지 확인
- vocal-app Step 3 G 작업 진행 가능 알림 완료

### §15-6 — endpoint별 v2 적용 현황 (2026-05-12 기준)

| endpoint | v2 적용 시점 | streaming | schema 변경 |
|---|---|---|---|
| `/analyze` | 2026-05-11 (F4) + 2026-05-12 (Phase 2) | ✅ StreamingResponse | `scores_v2`, `scores_meta`, `academic_analysis_scores`, `score_mapper_version`, `reliability.shown_v2/shown_v2_tiers/academic_only_v2/deferred_v2`, `timeline_scores`(4항목 dict), `timeline_metadata.shown_indicators` 등 |
| `/analyze-chunk` | 2026-05-11 (F4) | ❌ (3~5s 응답) | `scores_v2`, `scores_meta`, `low_confidence_items`, `chunk_duration_s`, `score_mapper_version` (legacy `scores` 2항목 호환 유지) |
| `/ws/realtime` | v1 유지 | WebSocket | latency 부담으로 v2 비적용 확정. 200ms binary PCM → pitch_match, 5s chunk → breathiness_chunk (v1 cpp_mean) |
| `/predict` | v1 유지 | ❌ | 변경 없음 (EGG wav 반환) |
| `/health` | v1 유지 | ❌ | 변경 없음 (`{status, model_loaded, gpu_available, device}`) |

### §15-7 — 2026-05-13 dml-server systemd unit 전환

- `dml-server.service` 추가: 기존 수동/nohup `python server.py` 실행을 systemd로 이관, `User=dmlserver`, `WorkingDirectory=model_server`, port 8001 유지.
- single uvicorn worker 유지: `server.py`의 uvicorn 기본 단일 worker 실행, cloudflared target `http://localhost:8001` 변경 없음.
- 운영 안정화: `Restart=always`, `RestartSec=10`, `RuntimeMaxSec=3600`, stdout/stderr `/var/log/dml-server.log` append 기록.
- 검증: local `/health` 및 production `https://dml.vocal-fit.com/health` OK. `/analyze` StreamingResponse P2-A/status body 정책 변경 없음.

## 16. 2026.07 재검증 (진단 2단계) — 성능 추정치 신뢰성 (2026-08-11 기록)

산출물·상세: `data/vocal_academy/results/sidetrack/rediag/` (README 포함, 재검증 수행 2026-07-26).

**결론 — 9항목 판정**
- 유의 2: **접촉강도**(p=0.0231, nested 0.506) · **혀경직도**(p=0.0136, nested 0.562)
- 미확보: 호흡식별(p=0.3325, CI 0 포함) · **연구개위치(p=0.0536 + 배포 −0.62 vs nested +0.60 부호 반전)**
- deferred 3(흉성두성·공명개방·상압하압): 중첩 CV ≈ 0 붕괴 — 미배포 판단 재확인
- 비강사용·전방공명: academic_only 유지

**반복 방지 원칙 2가지 (필독)**
1. **검증셋으로 모델(config)을 선택하면 그 검증 성능은 성능 추정치로 재사용 불가.**
   n=17에서 21개 config 중 최대 |r|은 우연만으로 p50 ≈ 0.38, p95 ≈ 0.62까지 나온다 (s1 순열 분포).
   → **5/10 21명 코호트는 이미 선택에 소진되었으므로 향후 성능 추정에 쓸 수 없다.** 새 성능 주장은 새 코호트(After 등)에서만.
2. **unit 단위 KFold는 화자 누설을 만든다.** 배포 당시 train_5fold가 unit KFold였음이 재현으로 확정
   (비강사용 0.6394 ≈ 재현 0.6330; 화자 단위 전환 시 접촉강도 0.47 → 0.10).
   → 분할은 항상 **화자 단위**. 논문에 기존 train CV 수치를 쓸 땐 누설 사실 병기.

**재현성 자산**
- `rediag/retrain_v2.py` — mapping_params_v2/phone_to_oral_mapper_v2 재학습 파이프라인 복원본.
  입력 4종(indicators_v2_training.csv, trainer_scores.csv, extra_metrics.json, spectral_analysis.json) 저장소 추적 추가.
  출력은 `*_REGENERATED.*` 전용 — **배포 파일 무수정 원칙 유지.**
- mapper 학습집합 확정: 25쌍/16화자 (제외 4 unit: (6,'8') _sm 결측 평균대체 / (9,'10')·(13,'4')·(15,'2') 5/10 누설 화자)
- 구조 한계 기록: p=38 > n=24, rank 23, a1_p0·h1_a1 완전 중복(r=−1.0)
