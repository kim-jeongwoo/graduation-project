# 저장소 구조 분석 — graduation-project

**대상**: `git@github.com:kim-jeongwoo/graduation-project.git` (private)
**분석 기준 커밋**: `97a6c94` (branch `docs/lessons-learned-migration`, base `276a2ec` on `main`)
**분석일**: 2026-07-26

프로젝트: 순천향대학교 졸업작품 — **딥러닝 EGG(성대전도) 추정 기반 가창 발성 평가 시스템**
마이크 음성만으로 성대 진동 파형(EGG)을 추정하고, 이를 9개 발성 항목 점수로 매핑해 노래방 앱에서 피드백을 제공한다.

> ⚠️ 이 문서는 **git 추적 파일(403개 / 52 MB)** 만을 근거로 한다. dmlserver 로컬에는 34 GB(원본 wav, 체크포인트, 산출 CSV/JSON)가 더 있으나 `.gitignore` 로 제외돼 있다.

---

## 1. 디렉토리 구조 (2단계)

```
graduation-project/
├── README.md                    # 프로젝트 전체 개요 (29 KB)
├── CLAUDE.md / AGENTS.md        # 에이전트 운영 지침
├── environment.yml              # conda 환경 (EGGDML, Python 3.11.14)
├── .gitignore                   # data/, results/, checkpoints/ 제외 규칙
│
├── dml-server/                  # ★ GPU 서버 — AI 모델 + 추론 API (207 파일)
│   ├── ai-model/                #   모델 정의·학습·실험 (59 파일)
│   ├── model_server/            #   FastAPI 추론 서버 (:8001)
│   ├── scripts/                 #   데이터 전처리·분석 스크립트 (약 70개)
│   ├── docs/                    #   API 명세, 검증 리포트, 인계 문서
│   ├── figures/ · images/       #   논문/발표용 그림 (55 PNG)
│   ├── server/ · tests/
│   ├── PROJECT_LOG.md           #   진행 일지 (947행)
│   ├── CLAUDE.md                #   Known Pitfalls 15건
│   └── HANDOVER_TO_GPT.md
│
├── vocal-server/                # ★ Mac Studio — 백엔드 API (53 파일)
│   ├── app/                     #   FastAPI 애플리케이션 (routers/models/services/schemas)
│   ├── alembic/                 #   DB 마이그레이션
│   ├── docs/                    #   api.md, 코드 감사 보고서
│   ├── scripts/
│   ├── main.py · requirements.txt · alembic.ini
│   └── test_integration.py
│
├── vocal-app/                   # ★ Expo/React Native 앱 (96 파일)
│   ├── src/                     #   api·components·screens·services·store·domain 등 14개 모듈
│   ├── assets/ · scripts/ · docs/
│   ├── App.tsx · index.ts
│   ├── package.json · tsconfig.json · app.json · eas.json
│   └── babel.config.js
│
├── docs/                        # 모노레포 공통 문서 (27 파일)
│   ├── LESSONS_LEARNED.md       #   시행착오 정리 (사람용)
│   ├── AI_CONTEXT_FULL.md       #   전체 원문 통합본 (AI용, 559 KB)
│   ├── REPO_STRUCTURE.md        #   ← 이 문서
│   ├── CHANGELOG.md · VOCAL_FIT_PROJECT_OVERVIEW.md
│   ├── VERIFY_vocal-server.md · VOCAL_APP_CURRENT_STATE.md
│   ├── build_docs.py
│   └── research/                #   연구·분석 문서 원문 18건
│
├── app/                         # (레거시) storage 스텁 — 7 파일
└── demo_responses/              # 오프라인 시연용 응답 JSON 5종
```

**규모**

| 디렉터리 | 추적 파일 |
|---|---:|
| `dml-server/` | 207 |
| `vocal-app/` | 96 |
| `vocal-server/` | 53 |
| `docs/` | 27 |
| `demo_responses/`, `app/`, root | 19 |
| **합계** | **403** |

**확장자 분포**: `.py` 158 · `.md` 62 · `.png` 55 · `.tsx` 41 · `.ts` 32 · `.json` 17 · `.sh` 9 · `.yaml` 5

---

## 2. 주요 모듈의 역할

### 2-1. 시스템 전체 흐름

```
[스마트폰 앱 vocal-app]
   │ 녹음 (m4a/wav) + 업로드
   ▼
[vocal-server :8000]  FastAPI · PostgreSQL · SQLAlchemy 2.0
   │ POST /analyze (WAV + song_id)
   ▼
[dml-server/model_server :8001]  FastAPI · PyTorch
   │ EGG 추정 → 음향 지표(CQ/CPP/F0 등) → 9항목 점수 → 피드백
   ▼
[vocal-server DB 저장 → 앱 시각화]

실외/LTE: Cloudflare named tunnel → https://dml.vocal-fit.com
```

### 2-2. 모델 학습 — `dml-server/ai-model/`

| 파일 | 역할 |
|---|---|
| `model/efficient_egg.py` | **EfficientEGGNet** — 배포 모델. non-causal dilated CNN |
| `model/wavenet_egg.py` | Baseline·Exp1 (causal WaveNet) |
| `model/tcn_unet.py` | Exp2 (중단) |
| `model/transformer_egg.py` · `conformer_egg.py` | Exp6·Exp7 (실패) |
| `model/multi_input_egg.py` | Exp4 (Mel 병합, 실패) |
| `auto_experiment.py` · `auto_experiment_v2.py` | **Exp1~Exp23 자동 실험 러너.** exp20 하이퍼파라미터가 여기 정의됨 |
| `train.py` · `train_exp1~4.py` | 개별 실험 학습 스크립트 |
| `validate_exp20.py` | 최종 모델 검증 (화자 분할 누설 확인 + per-speaker corr) |
| `utils/dataset.py` | `SVDEggDataset` — 화자 독립 분할 + 윈도우 페어 생성 |
| `utils/nsp_reader.py` | SVD 데이터셋 `.nsp`/`.egg` 페어 탐색·읽기 |
| `egg_from_mic/` | 초기 실험 계열 (전처리·정렬·PTDB 실험·시각화) |
| `generate_*_figures.py` · `visualize_attention.py` | 논문/발표용 그림 생성 |

### 2-3. 전처리 — `dml-server/scripts/`

| 그룹 | 파일 | 역할 |
|---|---|---|
| **노래방 T1** | `data_prep/` (15개) | LRC 수집(`fetch_lrc.py`), Whisper ASR(`whisper_lrc.py`), Demucs+CREPE 피치 가이드(`extract_pitch_guide.py`), MIDI 변환(`f0_to_midi_segments.py`, `midi_to_pitch_guide.py`), 일괄 실행(`run_all.py`) |
| **평가 T2** | `data_prep_t2/` (7개) | 평가지 파싱(`parse_new_evals.py`), ICC 검증(`validate_icc.py`), score_mapper 재학습(`retrain_score_mapper.py`) |
| **음향 지표** | `extra_metrics.py`, `spectral_analysis.py`, `nasal_analysis.py`, `vad_preprocess.py` | CPP / spectral centroid·tilt / A1-P0 / nasal ratio / VAD 마스크 |
| **점수 매핑** | `score_mapper.py`, `sidetrack/score_mapper_v2.py`, `sidetrack/indicators_v2.py` | 33개 phone indicator 산출 → 9항목 점수 |
| **분석·검증** | `e1~e4`, `h2`, `i2~i6`, `j1~j6`, `k1~k3` 계열 | 단계별 검증·리포트 생성 |

### 2-4. 서버 API

**`dml-server/model_server/`** — AI 추론 전담

| 파일 | 역할 |
|---|---|
| `server.py` | FastAPI 엔트리. 5개 엔드포인트 |
| `predictor.py` | `EGGPredictor` — 체크포인트 로드, 16384 윈도우 overlap-add 추론 |
| `analysis_pipeline.py` | EGG + 음향 지표 + v1/v2 점수 + 피드백 통합 |
| `schemas.py` | Pydantic 응답 모델 |
| `services/timeline_analysis.py` | LRC 라인 단위 chunk 점수 |
| `services/chunk_analysis.py` | 단구간 통합 점수 |
| `services/realtime.py` | WebSocket 실시간 (음정 200ms + 호흡 5s) |

**`vocal-server/app/`** — 사용자·세션·DB 전담

| 모듈 | 역할 |
|---|---|
| `routers/auth.py` | 회원가입·로그인 (JWT) |
| `routers/sessions.py` | 연습 세션 CRUD, 분석 트리거 |
| `routers/files.py` | 녹음 파일 업로드 |
| `routers/analysis.py` | 분석 실행·결과 조회·비교 |
| `routers/songs.py` | 곡 목록, LRC, 피치 가이드, MR 배포 |
| `routers/training.py` | 연습 이력, 즐겨찾기 |
| `routers/admin.py` | 관리자 대시보드 (HTML + SSE 실시간 로그) |
| `services/analysis_service.py` | dml-server 호출 래퍼 |
| `models/models.py` | ORM: `User`, `Session`, `Song`, `SessionFile`, `AnalysisRun`, `AnalysisResult` |
| `middleware/activity_tracker.py` | 접속·활동 추적 |

### 2-5. 앱 — `vocal-app/src/`

| 모듈 | 역할 |
|---|---|
| `api/` (10개) | `client.ts`(axios + 토큰 인터셉터), `dmlClient.ts`(WebSocket URL), `analysis`·`sessions`·`songs`·`auth`·`training`, `mock.ts` |
| `services/audio/` | `recorder.ts`, `microphone.ts`, `pitchDetector.ts`, `audioMode.ts` |
| `screens/` | 홈·분석 결과·연습·평가 결과 화면 |
| `components/` | `MetricCard`, `training/ResultCard`, `eval/EvalItemCard` 등 |
| `store/` | Zustand 전역 상태 |
| `domain/` | `evaluationItems.ts` — 9항목 정의 |
| `navigation/` · `theme/` · `constants/` · `utils/` | 라우팅·디자인 토큰·유틸 |

---

## 3. 라이브러리 / 프레임워크

### 3-1. dml-server (AI 추론) — `dml-server/model_server/requirements.txt`

```
fastapi>=0.104          uvicorn[standard]>=0.24    python-multipart>=0.0.6
python-dotenv>=1.0      pydantic>=2.0              numpy
torch>=1.12             scipy                      soundfile
librosa                 praat-parselmouth
```

| 라이브러리 | 용도 |
|---|---|
| **PyTorch** | EfficientEGGNet 학습·추론 |
| **librosa** | 리샘플링, STFT, spectral centroid |
| **praat-parselmouth** | 포먼트, 피치, HNR, jitter/shimmer (Praat 바인딩) |
| **scipy** | Butterworth/FIR 필터 |
| **soundfile** | WAV I/O |
| **FastAPI + uvicorn** | 추론 API |

### 3-2. 학습 환경 — `environment.yml` (conda `EGGDML`)

Python **3.11.14**. pip 의존성에 `absl-py`, `antlr4-python3-runtime`(Hydra 계열), `aiosqlite` 등 포함.
실험 계열은 추가로 **Demucs**(보컬 분리), **CREPE/TensorFlow**(F0 추출), **Whisper**(ASR), **scikit-learn**(score_mapper), **tqdm**, **matplotlib** 사용.

> ⚠️ CREPE는 RTX 5080(Blackwell)을 TF 2.21이 미지원해 **CPU fallback** 으로 동작한다 (곡당 84~98s).

### 3-3. vocal-server (백엔드) — `vocal-server/requirements.txt`

```
fastapi          uvicorn        sqlalchemy       psycopg2-binary
python-dotenv    alembic        bcrypt           python-jose[cryptography]
python-multipart pydantic[email] httpx           itsdangerous      jinja2
```

| 라이브러리 | 용도 |
|---|---|
| **SQLAlchemy 2.0 + psycopg2** | PostgreSQL ORM |
| **Alembic** | DB 마이그레이션 |
| **bcrypt + python-jose** | 비밀번호 해싱 + JWT |
| **httpx** | dml-server 비동기 호출 |
| **Jinja2 + itsdangerous** | 관리자 HTML 대시보드 + 세션 쿠키 |

### 3-4. vocal-app (모바일) — `vocal-app/package.json`

| 패키지 | 버전 | 용도 |
|---|---|---|
| `expo` | ~54.0.33 | 앱 프레임워크 |
| `react` / `react-native` | 19.1.0 / 0.81.5 | UI |
| `typescript` | ~5.9.2 | 타입 |
| `@react-navigation/*` | ^7.x | 라우팅 (native-stack, bottom-tabs) |
| `axios` | ^1.13.6 | HTTP |
| `zustand` | ^5.0.12 | 상태 관리 |
| `expo-av`, `react-native-audio-record` | | 녹음·재생 |
| `pitchfinder`, `react-native-pitchy` | | 온디바이스 피치 검출 |
| `victory-native`, `react-native-svg` | | 차트 |
| `expo-secure-store` | ~15.0.8 | 토큰 보관 |
| `expo-file-system` | ~19.0.22 | 파일 업로드 |
| `react-native-reanimated` | ~4.1.1 | 애니메이션 |

빌드: **EAS** (`eas.json`), 개발: `expo start --dev-client` / tunnel / Cloudflare 스크립트.

---

## 4. 모델 아키텍처

### 4-1. EfficientEGGNet (배포 모델, Exp20)

**근거**: [`dml-server/ai-model/model/efficient_egg.py`](../dml-server/ai-model/model/efficient_egg.py) · [`model_server/predictor.py:24-35`](../dml-server/model_server/predictor.py)

```
입력  [B, 1, T]   16 kHz mono 음성, T = 16384 (1.024초)
   │
   ├─ input_conv:  Conv1d(1→128, k=1) → GELU → Conv1d(128→128, k=3, pad=1)
   │
   ├─ DilatedBlock × 30   (n_stacks=5 × layers_per_stack=6)
   │     stack 내 dilation = 2^0, 2^1, ... 2^5  (1,2,4,8,16,32)
   │     각 블록:
   │        h = Dropout(x)
   │        f = tanh( Conv1d(k=5, dilation=d, padding=d*(k-1)/2) )    ← 대칭 패딩 = non-causal
   │        g = sigmoid( Conv1d(k=5, dilation=d, padding=...) )
   │        h = f * g                                  (gated activation)
   │        skip = Conv1d(h, k=1)
   │        res  = Conv1d(h, k=1) + x                  (residual)
   │        res  = GroupNorm(16, 128)(res)
   │
   ├─ skip_sum = Σ skip   (WaveNet-style skip connection)
   │
   └─ output_conv: GELU → Conv1d(128→128,k=1) → GELU → Dropout → Conv1d(128→1,k=1)

출력  [B, 1, T]   추정 EGG 파형 (입력과 동일 길이)
```

| 항목 | 값 |
|---|---|
| 파라미터 | **5.99 M** |
| channels | 128 |
| n_layers / n_stacks | 30 / 5 (stack당 6층) |
| kernel_size | **5** (기본값 3에서 상향) |
| dropout | 0.05 |
| 정규화 | GroupNorm(groups=16) — *InstanceNorm은 AMP에서 NaN 발생해 교체* |
| 활성화 | gated tanh × sigmoid (내부), GELU (입출력) |
| 인과성 | **non-causal** (대칭 패딩 → 양방향 문맥) |
| 수용 영역 | stack당 Σ2·2^i (i=0..5) = 126 → 5 stack ≈ **631 samples 이상** (k=5 기준 더 큼) |
| 체크포인트 | `checkpoints/exp20_progressive/best_model.pt` — **gitignored, 로컬 전용** |

### 4-2. 학습 하이퍼파라미터 (Exp20 Progressive Window)

**근거**: [`auto_experiment_v2.py:1102-1146`](../dml-server/ai-model/auto_experiment_v2.py)

**Progressive window** — 작은 윈도우로 시작해 3단계로 확장:

| Phase | window | hop | batch | epochs | lr |
|---|---:|---:|---:|---:|---:|
| 1 | 4096 (256 ms) | 2048 | 32 | 20 | 1e-3 |
| 2 | 8192 (512 ms) | 4096 | 16 | 40 | 5e-4 |
| 3 | **16384 (1024 ms)** | 8192 | 8 | 40 | 3e-4 |

| 항목 | 설정 |
|---|---|
| **Loss** | `CombinedLoss(alpha=0.2)` = `0.2·MSE + 0.8·(1 − Pearson corr)` |
| **Optimizer** | AdamW, `weight_decay=1e-4` |
| **Scheduler** | `OneCycleLR` (pct_start=0.1, cos anneal, div_factor=10, final_div_factor=100) |
| **AMP** | `torch.amp.GradScaler('cuda')` 사용 |
| **데이터 분할** | 화자 독립 (`speaker_split`, seed=42), train/val/test = 0.8/0.1/0.1 |
| **샘플레이트** | 16 kHz |
| **num_workers** | 4 |

### 4-3. 추론 설정 (배포)

**근거**: [`model_server/predictor.py`](../dml-server/model_server/predictor.py)

- `TARGET_SR = 16000`, `WINDOW_SIZE = 16384`, `HOP_SIZE = 8192` (50 % overlap)
- 긴 오디오는 윈도우 분할 → 각 윈도우 추론 → **overlap-add + weight 정규화**로 재결합
- 오디오가 윈도우보다 짧으면 zero-padding
- 체크포인트에 config가 없어 하이퍼파라미터를 코드에 명시(`EXP20_CONFIG`)

### 4-4. 실험 계보

| 실험 | 모델 | Params | Window | Test Corr |
|---|---|---:|---|---:|
| Baseline | WaveNet (causal) | 72 K | 192 | 0.6662 |
| Exp1 | Larger WaveNet | 419 K | 192 | 0.6784 |
| Exp1b | WaveNet + long window | 419 K | 1024 | 0.6763 |
| Exp2 | TCN-UNet | 29.4 M | 1024 | 중단 (NaN·속도) |
| Exp3 | **EfficientEGGNet** | 1.8 M | 4096 | 0.7163 |
| Exp10 | Large Efficient | 5.99 M | 4096 | 0.7205 |
| Exp11 | Multiscale | 5.99 M | 8192 | 0.7484 |
| **Exp20** | **Progressive** | **5.99 M** | **16384** | **0.8249** |

실패·중단 14건의 상세는 [`docs/research/01-model-experiments-full.md`](research/01-model-experiments-full.md).

---

## 5. 데이터 전처리 파이프라인

두 개의 독립 파이프라인이 있다.

### 5-1. EGG 모델 학습 파이프라인 (SVD 데이터셋 → 학습 텐서)

**근거**: [`egg_from_mic/utils/preprocessing.py`](../dml-server/ai-model/egg_from_mic/utils/preprocessing.py) · [`ai-model/utils/dataset.py`](../dml-server/ai-model/utils/dataset.py) · [`utils/nsp_reader.py`](../dml-server/ai-model/utils/nsp_reader.py)

```
[1] 원본 수집
    data/SVD_healthy/{speaker_id}/{vowels,sentences}/
      X.nsp      (마이크 음성)
      X-egg.egg  (동시 녹음 EGG)
    → nsp_reader.py 가 두 하위 디렉터리를 훑어 (nsp, egg, speaker_id) 페어 생성

[2] 채널별 전처리                     preprocessing.py
    ├ MIC:  resample 16 kHz
    │       → Butterworth highpass 30 Hz (order=2, filtfilt)
    │       → peak normalization [-1, 1]
    └ EGG:  resample 16 kHz
            → FIR bandpass 80–4000 Hz (numtaps=1024, firwin + lfilter)
            → peak normalization [-1, 1]

[3] 화자 독립 분할                    dataset.py: speaker_split(seed=42)
    train 0.8 / val 0.1 / test 0.1
    → 화자 ID 기준 분할. 교집합 0 검증(validate_exp20.py 의 LEAK-FREE 체크)

[4] 윈도우 페어 생성                  SVDEggDataset
    파일별 z-normalize (normalize_per_file=True)
    두 신호를 같은 길이로 절단
    window_length 간격으로 슬라이딩 (hop_length)
    x = speech[start : start+W]   y = egg[start : start+W]   (동일 위치 정렬)
    → 캐시 디렉터리에 리샘플 결과 저장 가능

[5] DataLoader                        create_dataloaders(...)
    Exp20은 phase마다 window/hop/batch 를 바꿔 재생성
    (4096/2048/32 → 8192/4096/16 → 16384/8192/8)
```

**출력 shape**: `x, y : [B, 1, W]` — W는 phase에 따라 4096 / 8192 / 16384

### 5-2. 노래방 곡 파이프라인 (원곡 → 피치 가이드)

**근거**: [`dml-server/scripts/data_prep/`](../dml-server/scripts/data_prep/) · [`PROJECT_LOG.md §2-B`](../dml-server/PROJECT_LOG.md)

```
Stage 0  파일 분류               classify_uploads.py
         업로드 파일 → master(원곡) / MR 식별                     14/14 ✓

Stage 1  가사 수집               fetch_lrc.py (LRCLIB API)
         → lrc/raw/{id}.lrc, lrc/parsed/{id}.json                11/14 ✓
         미확보 3곡(001·007·011)은 whisper_lrc.py 로 ASR 생성     → 14/14

Stage 2  보컬 분리 + F0 + 정렬   extract_pitch_guide.py
         ├ Demucs      → stems/{id}/vocals.wav, no_vocals.wav
         ├ CREPE       → F0 곡선 (crepe_cache.npz 로 캐시)
         ├ MR 정렬     → lrc_offset_sec 측정
         └ 산출        → pitch_guide/{id}_pitch_guide.json + .png

Stage 2b MIDI 경로 (선택)        f0_to_midi_segments.py → midi_to_pitch_guide.py
         외부 MIDI는 --dry-run 으로 자체 F0 와 옥타브 비교 후 채택 판단
         (외부 MIDI가 +12 semitone 인 사례 발견 → 자체 F0 추출로 전환)

Stage 3  일괄 실행 + 검증        run_all.py
         14곡 배치 처리 + 4×4 그리드 PNG + 종합 보고
```

**주의 사항 (코드에 규칙으로 명시됨)**
- macOS 업로드 파일명은 NFD로 저장되므로 비교 전 `unicodedata.normalize('NFC', name)` 필수
- LRC title similarity 0.4 미만은 auto-accept 금지 (전혀 다른 곡이 매칭된 사례)
- Stage 2 전에 `lrc/parsed/` 파일 수 확인 (LRC 없이 pitch_guide 생성된 사고)

### 5-3. 발성 평가 파이프라인 (녹음 → 9항목 점수)

**근거**: [`scripts/sidetrack/indicators_v2.py`](../dml-server/scripts/sidetrack/indicators_v2.py) · [`score_mapper_v2.py`](../dml-server/scripts/sidetrack/score_mapper_v2.py) · [`model_server/analysis_pipeline.py`](../dml-server/model_server/analysis_pipeline.py)

```
phone WAV
  → resample 16 kHz (mono)
  → VAD 마스크 (RMS p90×0.10 ∧ parselmouth F0 > 0)
  → indicators_v2.compute_all()  →  33개 phone indicator
       HNR, H1-H2, H1-A1, H1-A3, F1~F3 + bandwidth,
       jitter(local/rap), shimmer(local/apq3),
       spectral flatness 5밴드, band ratio 2종,
       anti-formant 250-500 / 500-800, F2/F1 비·차·안정도,
       formant transition speed, spectral entropy,
       spectral centroid variability, f0 std/range,
       A1-P0, singer's formant ratio
  → phone_to_oral_mapper_v2.pkl (27 target Ridge) 로 oral 도메인 추정
  → feature_order 38차원 구성 (mapped 25 + raw phone 13)
  → StandardScaler → score_mapper_v2 (Ridge/ElasticNet/Lasso/GB)
  → 9항목 중 6항목 점수 (표시 4 + 학술 2), 0~5 clip
```

> ⚠️ 이 매핑 단계의 통계적 타당성은 [`docs/research/40-rediag-selection-bias-2026-07.md`](research/40-rediag-selection-bias-2026-07.md) 에서 재검증됐다. 표시 4항목 중 2개만 유의성이 확인됐다.

---

## 6. 서버 엔드포인트 + 앱-서버 통신

### 6-1. dml-server (`:8001`) — AI 추론

**근거**: [`model_server/server.py`](../dml-server/model_server/server.py)

| Method | Path | 역할 |
|---|---|---|
| `GET` | `/health` | 헬스 체크 (모델 로드 상태) |
| `POST` | `/predict` | WAV → 추정 EGG WAV 반환 |
| `POST` | `/analyze` | 전곡 종합 분석. **StreamingResponse** — Cloudflare 125s edge timeout 우회를 위해 5초 간격 공백 keepalive 송신. HTTP 200 고정, 오류도 body `status` 필드(`invalid`/`failed`)로 반환 |
| `POST` | `/analyze-chunk` | 3~10초 단구간 → 호흡/접촉 통합 점수. `duration<3s`→400, `voiced_s < dur×0.4`→`no_voice` |
| `WS` | `/ws/realtime` | 실시간. 음정 일치율 200 ms 주기 + 호흡 5초 chunk. 실측 pitch latency p95 = 2.9 ms |

**`/analyze` 응답 주요 필드** (`schemas.py`)

```json
{
  "status": "success",
  "audio_info": { "duration_s", "sample_rate", "voiced_ratio", "f0_min/max/mean" },
  "indicators": { "cq_mean","cq_peak","cpp_mean","hnr_mean",
                  "spectral_centroid_mean","spectral_tilt_mean",
                  "h1_h2_mean","singers_formant_ratio_mean","a1_p0_mean","nasal_ratio" },
  "register_metrics": { "low": {...}, "mid": {...}, "high": {...} },
  "scores": { ...9항목 v1 legacy... },
  "scores_v2": { "3_vocal_fold_contact", "4_breathiness",
                 "6_soft_palate", "8_tongue_tension" },
  "scores_meta": { "<key>": { "tier","caveats","display_mark","icc","icc_ratio" } },
  "academic_analysis_scores": { "1_nasal_oral_ratio", "5_forward_resonance" },
  "timeline_scores": [ { "start_sec","end_sec","lrc_text",
                         "chunk_duration_s","scores","low_confidence_items" } ],
  "user_f0": { "frame_hz": 25, "values": [ ...null 포함... ] },
  "reliability": { "shown_v2","academic_only_v2","deferred_v2" },
  "score_mapper_version": "v2"
}
```

### 6-2. vocal-server (`:8000`) — 사용자·세션·DB

**근거**: `vocal-server/app/routers/*.py`

| Method | Path | 역할 |
|---|---|---|
| `POST` | `/auth/signup` | 회원가입 |
| `POST` | `/auth/login` | 로그인 (JWT 발급) |
| `POST` | `/sessions` | 세션 생성 |
| `GET` | `/sessions` | 세션 목록 |
| `GET` | `/sessions/{session_id}` | 세션 상세 |
| `POST` | `/sessions/{session_id}/files` | 녹음 파일 업로드 |
| `POST` | `/sessions/{session_id}/analyze` | 분석 실행 (→ dml-server 호출) |
| `POST` | `/sessions/{session_id}/training-analyze` | 연습 모드 분석 |
| `GET` | `/analysis/{run_id}` | 분석 실행 상태 |
| `GET` | `/analysis/{run_id}/results` | 분석 결과 |
| `GET` | `/analysis/{run_id}/comparison` | 이전 세션과 비교 |
| `GET` | `/songs` | 곡 목록 |
| `GET` | `/songs/{song_id}/lrc` | 가사 |
| `GET` | `/songs/{song_id}/pitch-guide` | 음정 가이드 JSON |
| `GET` | `/songs/{song_id}/mr` | MR 음원 |
| `GET` | `/users/me/training-attempts` | 연습 이력 |
| `GET/POST/DELETE` | `/users/me/favorites[/{id}]` | 즐겨찾기 |
| `GET/POST` | `/admin/*` | 관리자 대시보드 (로그인, 사용자, 세션, 이벤트 SSE, 로그) |

> ⚠️ 코드 감사([`vocal_server_code_audit_2026-06-16.md`](../vocal-server/docs/vocal_server_code_audit_2026-06-16.md))에서 `/songs/*` 는 인증은 요구하나 **user_id 검증이 없다**는 점이 지적됐다.

### 6-3. 앱 ↔ 서버 통신 구조

**근거**: `vocal-app/src/api/client.ts`, `dmlClient.ts`, `.env.example`

```
                         ┌──────────────────────────────┐
   vocal-app             │  api/client.ts (axios)       │
   (Expo / RN)           │   baseURL = EXPO_PUBLIC_API_URL
                         │           ?? https://api.vocal-fit.com
                         │   request interceptor:
                         │     SecureStore 토큰 → Authorization 헤더
                         └───────────────┬──────────────┘
                                         │ HTTPS (REST)
                                         ▼
                              vocal-server :8000
                                         │ httpx
                                         ▼
                              dml-server :8001  (POST /analyze)

   ┌─────────────────────────────────────────────────────┐
   │  실시간 경로는 서버를 거치지 않고 직결                │
   │  api/dmlClient.ts                                    │
   │    DML_WS_URL = EXPO_PUBLIC_DML_WS_URL               │
   │                 ?? wss://dml.vocal-fit.com           │
   │    buildRealtimeWsUrl(songId)                        │
   │      → wss://dml.vocal-fit.com/ws/realtime?song_id=… │
   └─────────────────────────────────────────────────────┘
```

| 특징 | 내용 |
|---|---|
| 인증 | JWT. `expo-secure-store` 에 보관, axios 인터셉터가 자동 첨부 |
| 두 경로 | 분석/세션은 **vocal-server 경유**, 실시간 WebSocket은 **dml-server 직결** |
| 터널링 | LTE에서 8001 비표준 포트가 통신사에 차단돼 Cloudflare named tunnel(`dml.vocal-fit.com`) 사용 |
| 오프라인 모드 | `EXPO_PUBLIC_USE_MOCK=true` → `api/mock.ts` + `demo_responses/*.json` 5종으로 시연 |
| 온디바이스 처리 | 피치 검출은 `pitchfinder` / `react-native-pitchy` 로 앱에서 직접 수행 |

---

## 7. 최종 성능 지표

### 7-1. EGG 추정 모델

**기록 위치**: [`dml-server/CLAUDE.md` §현재 상태](../dml-server/CLAUDE.md) · [`ai-model/EXPERIMENT_REPORT.md`](../dml-server/ai-model/EXPERIMENT_REPORT.md) · [`ai-model/validate_exp20.py`](../dml-server/ai-model/validate_exp20.py)

| 지표 | 값 |
|---|---|
| **Test Corr** | **0.8249** |
| Val Corr | 0.8218 |
| Train–Test Gap | 0.022 |
| Median (per-speaker) | 0.8532 |
| 화자 90 % 가 | Corr ≥ 0.7 |
| Data Leak | 없음 (화자 독립 분할 검증) |
| 파라미터 | 5.99 M |

`validate_exp20.py` 는 exp11 대비 비교, 8192/16384 두 윈도우 평가, per-speaker corr 분포, LEAK-FREE 검증을 출력한다.

### 7-2. 평가자 신뢰도 (ICC)

**기록 위치**: [`docs/research/20-icc-510-report.md`](research/20-icc-510-report.md)

ICC(2,k), 5 raters × 21 singers × 3 registers = 315행

| 항목 | 5/10 통합 | 항목 | 5/10 통합 |
|---|---:|---|---:|
| 상압하압 | **0.910** | 흉성두성 | 0.805 |
| 접촉강도 | **0.898** | 비강사용 | 0.796 |
| 혀경직도 | 0.802 | 호흡식별 | 0.796 |
| 전방공명 | 0.762 | 공명개방 | 0.728 |
| 연구개위치 | 0.643 | **9항목 평균** | **0.793** |

### 7-3. 9항목 점수 매핑 성능

**기록 위치**: `data/vocal_academy/results/sidetrack/mapping_params_v2.json` (**gitignored, 로컬 전용**) → 수치는 [`docs/research/40-rediag-selection-bias-2026-07.md`](research/40-rediag-selection-bias-2026-07.md) 에 이관됨

| 항목 | tier | 배포 val corr | 선택보정 p | 중첩 CV \|r\| | 판정 |
|---|---|---:|---:|---:|---|
| 접촉강도 | high | +0.7327 | 0.023 | 0.506 | ✅ 유의 |
| 혀경직도 | high_star | +0.6936 | 0.014 | 0.562 | ✅ 유의 |
| 연구개위치 | high_star | −0.6236 | 0.054 | 0.603 | ❌ 미확보 + 부호 반전 |
| 호흡식별 | high_star | +0.4343 | 0.333 | 0.362 | ❌ 미확보 |
| 비강사용 | academic_only | −0.8000 | 0.001 | 0.676 | 부호 반전 (앱 미표시) |
| 전방공명 | academic_only | −0.6797 | 0.021 | 0.395 | 부호 반전 (앱 미표시) |
| 흉성두성·공명개방·상압하압 | deferred | — | — | 0.03~0.06 | 모델 미배포 |

> **주의**: `배포 val corr` 은 24개 모델 중 검증셋 상관이 최대인 것을 고른 값이라 **선택 편향이 포함**돼 있다. n=17에서 우연만으로 |r| ≈ 0.62(95분위)가 나오므로, 인용 시에는 `선택보정 p` 와 `중첩 CV` 열을 함께 봐야 한다.

### 7-4. 성능 기록 파일 목록

| 파일 | 담긴 지표 | 저장소 |
|---|---|:-:|
| `dml-server/ai-model/EXPERIMENT_REPORT.md` | Exp0~4 총괄표 (Test Corr, 학습시간, best epoch) | ✅ |
| `dml-server/CLAUDE.md` §현재 상태 | Exp20 최종 지표 | ✅ |
| `dml-server/PROJECT_LOG.md` §4 | 검증된 것 / 한계 표 | ✅ |
| `docs/research/01-model-experiments-full.md` | Exp1b~Exp20 전체 (실패 14건 포함) | ✅ |
| `docs/research/20-icc-510-report.md` | 9항목 ICC (코호트별) | ✅ |
| `docs/research/31-final-validation-report.md` | 항목별 AI 지표 매핑 + 검증 결과 | ✅ |
| `docs/research/32-graduation-final-summary.md` | 졸업작품 최종 요약 | ✅ |
| `docs/research/40-rediag-selection-bias-2026-07.md` | 선택 편향 보정 후 성능 (**최신·최정확**) | ✅ |
| `data/vocal_academy/results/sidetrack/mapping_params_v2.json` | 6모델 계수·scaler·validation_corr 원본 | ❌ 로컬 |
| `checkpoints/exp20_progressive/best_model.pt` | 모델 가중치 | ❌ 로컬 |

---

## 부록: 저장소에 없는 것

`.gitignore` 규칙(`data/`, `results/`, `checkpoints/`, `.claude/`)으로 제외된 항목.

| 경로 | 내용 | 용량 |
|---|---|---:|
| `data/vocal_academy/singer_01..22/` | 가수 녹음 원본 (oral/nasal/phone wav) | — |
| `data/songs/`, `song/`, `songs/` | 곡 음원, MR, Demucs stem | — |
| `data/SVD_healthy/` | 외부 EGG 데이터셋 | — |
| `checkpoints/` | 모델 가중치 22종 | 1 GB |
| `results/`, `data/vocal_academy/results/` | 지표·모델 산출 CSV/JSON | 69 MB |
| `data/vocal_academy/results/sidetrack/rediag/` | 2단계 진단 스크립트 19개 + JSON | — |
| **합계** | | **약 34 GB** |
