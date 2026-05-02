# CLAUDE.md — EGG Prediction (ai-model)

## 프로젝트 한 줄 요약
MIC 음성만으로 EGG(성대접촉파형)를 추정하는 딥러닝 모델. 순천향대 IoT학과 졸업 프로젝트.
GitHub: https://github.com/kim-jeongwoo/graduation-project.git (branch: main)

---

## 환경
- Ubuntu 25.10 / RTX 5080 (16.6GB) / PyTorch 2.10.0+cu128 / Python 3.11 / Conda: **EGGDML**
- 활성화: `cd ~/projects/egg_prediction && conda activate EGGDML`
- GPU 확인: `nvidia-smi`
- 서버 IP: 114.71.220.144

---

## 현재 상태 (Best: Exp20 Progressive Window)

| 항목 | 값 |
|------|------|
| 모델 | EfficientEGGNet (non-causal dilated CNN) |
| 구조 | channels=128, n_layers=30, kernel_size=5, n_stacks=5, dropout=0.05 |
| 파라미터 | 5.99M |
| Window | 16384 samples (1024ms @16kHz) |
| Loss | 0.2·MSE + 0.8·CorrLoss |
| **Test Corr** | **0.8249** |
| Val Corr | 0.8218 |
| 체크포인트 | `checkpoints/exp20_progressive/best_model.pt` |

검증 완료: Data Leak 없음, Train-Test Gap 0.022, 화자 90%가 Corr ≥ 0.7, Median = 0.8532

---

## 상세 레퍼런스 (필요할 때만 읽을 것)

- 실험 히스토리 & 실패 원인: `.claude/refs/experiments.md`
- 데이터셋 & 전처리 파이프라인: `.claude/refs/dataset.md`
- 폴더 구조: `.claude/refs/folder-structure.md`
- 자주 쓰는 명령어: `.claude/refs/commands.md`

---

## 에이전트 행동 규칙

### 토큰 효율
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.

### 실수 방지
- 파일 수정 전 뭘 바꿀 건지 먼저 설명.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.
- 되돌릴 수 있는 작업은 물어보지 말고 바로 진행. 삭제·전송 같은 비가역 작업만 확인.
- 추측 금지. 불명확하면 궁금한 것들을 한 번에 묶어 질문.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.

---

## 절대 규칙 (주의사항)

1. `exp20_progressive/best_model.pt` **삭제 금지**.
2. **화자 독립 분할(seed=42) 변경 금지**. 프레임 분할은 Corr 0.95로 보이지만 데이터 누수.
3. **시각화는 중앙값 샘플 사용**. cherry-picking 금지.
4. **model_server 리샘플링 불일치 주의** (scipy vs librosa). 수정 시 양쪽 동기화.
5. 실험 결과는 `results/experiment_log*.txt`에 기록.
6. 시각화 한국어 폰트: `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

<!-- 형식: [날짜] [카테고리] 실수 / 원인 / 대신 어떻게 -->
<!-- 최신이 위. 기존 항목은 절대 지우지 말고 누적만. -->
<!-- 에이전트가 실수했을 때 즉시 추가 -->

- [2026-04] [import 순서] font 설정 블록(`Path(_NOTO).exists()`)을 `from pathlib import Path` 전에 배치 → ImportError. **`from pathlib import Path`는 항상 최상단.**
- [2026-04] [배치 실행] `fetch_lrc.py --all` 1회 실행 후 바로 Stage 2 배치 돌림 → LRC 누락 상태로 pitch_guide 생성. **Stage 2 전에 `lrc/parsed/` 파일 수 확인 필수.**
- [2026-04] [파일명] macOS 업로드 파일명이 NFD(jamo 분해)로 저장됨 → Linux에서 경로 불일치. **모든 파일명 비교 시 `unicodedata.normalize('NFC', name)` 적용.**
- [2026-04] [LRC 매칭] `007 지아 - 물론`, `011 양다일 - 요즘` LRCLIB 검색 시 전혀 다른 곡 반환 → title similarity 0.4 미달 곡 auto-accept 금지. **similarity < 0.4이면 MANUAL_SONGS 처리.**

---

## 🗓 프로젝트 현황 (2026-05-03)

### AI 모델 (EGG 추정)
- **완료.** Exp20 Progressive Window = Best. Test Corr **0.8249**.
- 체크포인트: `checkpoints/exp20_progressive/best_model.pt` (보존됨)
- 검증: Data Leak 없음, 화자 독립 분할(seed=42), Train-Test Gap 0.022, 화자 90% ≥ Corr 0.7

### T1 데이터 준비 (노래방 파이프라인)
- **완료.** 14/14곡 Stage 0~2 처리 완료 (2026-04-30).
- LRC: 11/14 확보. 3곡(001·007·011) manual_required.
- 산출물: `data/songs/pitch_guide/` (JSON 14개 · PNG 14개 · 그리드 1개), `data/songs/lrc/parsed/` (11개 + aligned 11개).
- CREPE 캐시: `stems/{id}/crepe_cache.npz` 14개 완료.

### 서버 / 앱
- **미시작.** songs 테이블 + API 엔드포인트 설계 단계.
- rsync 동기화(data/songs/ → 114.71.220.144) 아직 미실행.

---

## 📌 결정 사항 누적

<!-- 형식: [날짜] 결정 내용 / 근거 -->

- [2026-04] **화자 독립 분할 seed=42 고정** — 프레임 분할 시 Corr 0.95는 데이터 누수 허수. 변경 금지.
- [2026-04] **CREPE CPU 실행 유지** — RTX 5080(Blackwell) + CUDA 13.1에서 TF 2.21 GPU 미지원. 캐시로 보완.
- [2026-04] **MR 정렬: cross-correlation 첫 30s** — 도입부 기기적 특성이 전체 구간 평균보다 안정적.
- [2026-04] **review_segment 기준: 연속 unvoiced ≥5s** — 1s 이하 갭은 동일 세그먼트로 병합.
- [2026-04] **012 조성모 offset +2.249s → auto 유지** — LRC 첫 라인 [21.25s]가 CREPE 고신뢰 보컬 개시와 정확히 일치. 0~20s Demucs leakage(conf 0.67~0.75)는 정상 범위.
- [2026-04] **008 이하이 review_segment → needs_review 아님** — 281.8~289.6s (마지막 7.7s), voiced=0, conf 0.142 = 곡 종료 페이드아웃.
- [2026-04] **pitch_guide JSON 타임라인 = master 기준** — 앱에서 MR 재생 시간으로 변환 필요: `t_mr = t_master - lrc_offset_sec`.

---

## ✅ 다음 작업 큐

<!-- 완료 시 [x] 표시 + 날짜 -->

- [ ] rsync 동기화: `data/songs/` 전체 → 114.71.220.144 프로덕션 서버
- [ ] songs DB 테이블 스키마 설계 (id, artist, title, master_path, mr_path, lrc_offset_sec, ...)
- [ ] API 엔드포인트 구현 (곡 목록 · pitch_guide · lrc_aligned 조회)
- [ ] LRC 3곡 확보 (001 한로로 / 007 지아 / 011 양다일) — Whisper ASR 또는 수동 작성
- [ ] 앱 pitch_guide 연동 (MR 재생 타임라인 → t_mr 변환 적용)

---

## 🔁 시행착오 기록

<!-- 형식: [날짜] [단계] 현상 → 원인 → 해결 -->

- [2026-04] [Stage 1] `002 윤하` LRCLIB API timeout → 네트워크 간헐적 불안정 → `--song 002` 단독 재시도 성공.
- [2026-04] [환경] `pip install crepe` 실패 (`pkg_resources not found`) → build 격리 환경에 setuptools 없음 → `pip install "setuptools<70"` 후 `--no-build-isolation` 플래그로 설치.
- [2026-04] [환경] RTX 5080 CREPE GPU 미인식 → TF 2.21이 Blackwell 아키텍처 미지원 → CPU fallback 수용, 14곡 캐시 완료로 재실행 부담 없음.
- [2026-04] [Stage 2] 007 지아 pitch 품질 의심 → 130~155s 구간 피치 공백 → 악기 간주 구간으로 확인 (여성 보컬 F#3~B4 범위 정상).
- [2026-04] [Stage 2] 012 조성모 0~20s 저신뢰 프레임 의심 → Demucs vocal stem에 MR 악기음 bleed → conf 0.67~0.75 = leakage 정상 수치, 실제 보컬 구간은 0.87+.

---

## 📋 향후 개선 (노래방 데이터 파이프라인)

### LRC 미확보 3곡
**001 한로로 - 시간을 달리네 / 007 지아 - 물론 / 011 양다일 - 요즘**
LRCLIB에 데이터 없음. `data/songs/meta/manual_required.txt`에 기록됨.
Stage 2 음정 곡선 추출은 정상 진행 (LRC 없어도 Demucs+CREPE 동작).
노래방 가사 표시는 동작 안 함. 졸업작품 발표 후 아래 옵션 중 선택:
- 옵션 1: 벅스/멜론 평문 가사 + ASR(Whisper)로 시간 정렬 자동 생성
- 옵션 2: 사용자 수동 LRC 작성 (Aegisub 등 활용)
- 옵션 3: LRCLIB 커뮤니티에 직접 LRC 기여
