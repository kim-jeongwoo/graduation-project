# CLAUDE.md — dml-server (AI 모델 / 데이터 파이프라인)

## 프로젝트 한 줄 요약
MIC 음성으로 EGG 추정 + 노래방 데이터 파이프라인. 순천향대 IoT학과 졸업 프로젝트.
GitHub: https://github.com/kim-jeongwoo/graduation-project.git (branch: main, 서브폴더: dml-server/)

---

## 환경

- Ubuntu 25.10 / RTX 5080 (16.6GB) / PyTorch 2.10.0+cu128 / Python 3.11 / Conda: **EGGDML**
- 실제 작업 디렉토리: `~/projects/egg_prediction/` (데이터·체크포인트는 여기 disk에 있음)
- 레포 서브폴더: `dml-server/` (git 추적 파일들)
- 서버 IP: 114.71.220.144

```bash
# 환경 활성화
cd ~/projects/egg_prediction && conda activate EGGDML
nvidia-smi

# model_server 실행
conda activate EGGDML
python dml-server/model_server/server.py

# data_prep 스크립트 실행 예시
python dml-server/scripts/data_prep/run_all.py
```

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
| 체크포인트 | `checkpoints/exp20_progressive/best_model.pt` (disk-only, gitignored) |

검증 완료: Data Leak 없음, Train-Test Gap 0.022, 화자 90%가 Corr ≥ 0.7, Median = 0.8532

---

## 폴더 구조 (레포 내)

```
dml-server/
  ai-model/            # EGG 추정 모델 코드
  model_server/        # FastAPI 추론 서버 (port 8001)
    server.py          # /analyze 엔드포인트
    predictor.py       # EfficientEGGNet 추론 래퍼
    schemas.py
  scripts/
    data_prep/         # 노래방 파이프라인 (Stage 0~2 + t_mr 변환)
    sync_songs.sh      # Mac Studio → dmlserver pull (Mac Studio에서 실행)
    *.py               # 분석·평가 스크립트
  docs/                # dml 관련 문서
  figures/, images/    # 논문/보고서용 시각화
  server/              # 레거시 placeholder
  tests/               # test_analyze.py 등
  PROJECT_LOG.md
  CLAUDE.md            # 이 파일
```

disk-only (gitignored):
```
checkpoints/           # best_model.pt 등 (삭제 금지)
data/                  # 학습 데이터 + 노래방 14곡 산출물
results/               # 실험 결과 JSON
.claude/refs/          # 실험 히스토리·데이터셋 레퍼런스
```

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
- 터미널 멀티라인 주의 — Python 코드는 `.py` 파일로 만들어 실행. `-c` 인라인 멀티라인은 쉘 오염.

---

## 절대 규칙

1. `checkpoints/exp20_progressive/best_model.pt` **삭제 금지**.
2. **화자 독립 분할(seed=42) 변경 금지**. 프레임 분할은 Corr 0.95로 보이지만 데이터 누수.
3. **시각화는 중앙값 샘플 사용**. cherry-picking 금지.
4. **model_server 리샘플링 불일치 주의** (scipy vs librosa). 수정 시 양쪽 동기화.
5. 실험 결과는 `results/experiment_log*.txt`에 기록.
6. 시각화 한국어 폰트: `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
7. `data/songs/` 디렉토리 파일 삭제 금지 (원곡 MP3, 보컬 WAV, 피치 JSON).
8. `.env` 파일 내용 출력/로그 금지.

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

- [2026-05-03] [모노레포] dml-server 코드는 `dml-server/` 서브폴더 안.
  스크립트 실행: `cd ~/projects/egg_prediction && python dml-server/scripts/data_prep/run_all.py`
  data_prep 스크립트는 `parents[3]`으로 project root(`egg_prediction/`) 계산. `parents[2]` 아님.

- [2026-04] [import 순서] font 설정 블록(`Path(_NOTO).exists()`)을 `from pathlib import Path` 전에 배치 → ImportError. **`from pathlib import Path`는 항상 최상단.**

- [2026-04] [배치 실행] `fetch_lrc.py --all` 1회 실행 후 바로 Stage 2 배치 돌림 → LRC 누락 상태로 pitch_guide 생성. **Stage 2 전에 `lrc/parsed/` 파일 수 확인 필수.**

- [2026-04] [파일명] macOS 업로드 파일명이 NFD(jamo 분해)로 저장됨 → Linux에서 경로 불일치. **모든 파일명 비교 시 `unicodedata.normalize('NFC', name)` 적용.**

- [2026-04] [LRC 매칭] `007 지아 - 물론`, `011 양다일 - 요즘` LRCLIB 검색 시 전혀 다른 곡 반환 → title similarity 0.4 미달 곡 auto-accept 금지.

- [2026-04] [환경] CREPE GPU: RTX 5080(Blackwell) TF 2.21 미지원 → CPU fallback. 14곡 캐시 완료로 재실행 부담 없음.

---

## 🗓 프로젝트 현황 (2026-05-03)

### AI 모델 — 완료 ✓
Exp20 Progressive Window, Test Corr 0.8249. 체크포인트 보존됨.

### T1 데이터 파이프라인 — 완료 ✓
14/14곡 Stage 0~2. pitch_guide + _mr.json 생성. Mac Studio 동기화 완료.

### 백엔드 서버 — vocal-server 페이지 담당
진행 중. 이 페이지에서는 손대지 않음.

---

## ✅ 다음 작업 큐

- [ ] 5월 10일 평가 데이터 처리 자동화 (score_mapper 재학습 + 검증)
- [ ] 시연용 모범 응답 JSON 준비 (validation/test_01~11 케이스 선별)
- [ ] LRC 3곡 Whisper ASR (001/007/011)
