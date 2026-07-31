<!-- provenance -->
> **원본**: `.claude/refs/folder-structure.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: 저장소 폴더 구조 상세
> **원본 수정일**: 2026-04-17 · **크기**: 4,576 bytes · **sha256[:8]**: `5dfe9cbf`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# 폴더 구조

```
egg_prediction/
├── CLAUDE.md                        # 에이전트 컨텍스트 (이 파일)
├── README.md                        # 프로젝트 전체 문서 (상세)
│
├── ai-model/                        # 모델 학습/실험 코드
│   ├── model/
│   │   ├── efficient_egg.py         #   ★ EfficientEGGNet (Exp3~Exp20, Best)
│   │   ├── wavenet_egg.py           #   WaveNet (Baseline/Exp1/Exp1b) — causal
│   │   ├── tcn_unet.py             #   TCN-UNet (Exp2, 중단) — 29.4M
│   │   ├── multi_input_egg.py      #   Multi-Input (Exp4)
│   │   ├── transformer_egg.py      #   Transformer (Exp6)
│   │   └── conformer_egg.py        #   Conformer (Exp7, OOM)
│   ├── utils/
│   │   ├── dataset.py              #   SVDEggDataset + speaker-independent split
│   │   └── nsp_reader.py           #   SVD NSP/EGG 파서 (IFF FORM/DS16)
│   ├── configs/config.yaml          #   Baseline 학습 설정
│   ├── train.py                     #   Baseline 학습
│   ├── train_exp{1,1b,2,3,4}.py    #   수동 실험
│   ├── auto_experiment.py           #   자동 실험 v1 (Exp5~12)
│   ├── auto_experiment_v2.py        #   자동 실험 v2 (Exp13~20) ★
│   ├── validate_exp20.py            #   Exp20 검증 (data leak, overfit)
│   ├── generate_figures.py          #   예측 결과 시각화
│   ├── generate_thesis_figures.py   #   논문용 6개 도표
│   ├── analyze_similarity.py        #   발성 유사도 분석
│   ├── analyze_dtw_similarity.py    #   DTW 기반 유사도
│   └── egg_from_mic/                #   초기 실험 (PTDB, SVD)
│       └── test_compatibility.py   #     48kHz 호환성 테스트
│
├── model_server/                    # FastAPI 추론 서버 (현재 유일한 서빙 구현체)
│   ├── server.py                    #   GET /health, POST /predict (port 8001)
│   ├── predictor.py                 #   EGGPredictor — windowed inference
│   ├── .env                         #   CHECKPOINT_PATH, HOST, PORT
│   ├── requirements.txt
│   └── outputs/                     #   추론 결과 WAV 저장 ({run_id}/egg_estimated.wav)
│
├── scripts/                         # 보컬 학원 분석 파이프라인
│   ├── vad_preprocess.py            #   VAD 마스크 생성 (RMS+F0)
│   ├── batch_analyze.py             #   EGG 추정 + CQ 분석
│   ├── nasal_analysis.py            #   비강/구강 비율
│   ├── spectral_analysis.py         #   Singer's formant / tilt / H1-H2 / HNR
│   ├── score_mapper.py              #   AI 지표 → 0~5점 매핑
│   ├── feedback_generator.py        #   피드백 텍스트 생성
│   ├── compare_scores.py            #   AI vs 트레이너 비교
│   └── check_recordings.py          #   녹음 품질 전수 검사
│
├── song/                            # 노래 타임스탬프 처리 (잔나비 곡 완료)
│   ├── convert_timestamps.py        #   Whisper → timestamps JSON
│   ├── merge_lyrics.py              #   가사 + 타임스탬프 병합
│   └── separated/htdemucs/input/    #   demucs 분리 결과
│
├── data/
│   ├── SVD_healthy/                 #   SVD 건강화자 687명 (50kHz, .nsp/.egg)
│   ├── rpi_recordings/              #   라즈베리파이 녹음 (48kHz/24bit)
│   └── vocal_academy/               #   보컬학원 데이터 (singer_01~12)
│
├── checkpoints/                     # 모델 체크포인트 (exp1~exp20, 21개)
│   ├── best_model.pt               #   Baseline
│   └── exp20_progressive/best_model.pt  # ★ Best (삭제 금지)
│
├── results/                         # 실험 결과 로그
│   ├── experiment_log.txt           #   자동 실험 v1 로그
│   ├── experiment_log_v2.txt        #   자동 실험 v2 로그
│   ├── validation_exp20_final.txt   #   Exp20 검증 결과
│   └── compatibility_test/          #   48kHz 호환성 테스트
│
├── figures/                         # 시각화 PNG (11개, 300 DPI)
├── app/                             # 🚧 클라이언트 앱 예정 (빈 폴더)
├── server/                          # 🚧 백엔드 예정 (빈 폴더)
└── .claude/refs/                    # 에이전트 참조 문서
```
