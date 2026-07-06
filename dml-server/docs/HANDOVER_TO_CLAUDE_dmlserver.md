# HANDOVER_TO_CLAUDE.md

작성 기준: 2026-07-06 현재 `/home/dmlserver/projects/egg_prediction` 체크아웃을 직접 읽어 작성했다. 실험 수치는 `results/`, `PROJECT_LOG.md`, `mapping_params_v2.json` 등 저장소 내 로그/결과 파일에 있는 값만 인용했다. `data/`, `results/`, `checkpoints/`는 현재 디스크에는 존재하지만 `.gitignore` 대상이다(`.gitignore:1-45`).

## 1. 저장소 구조와 디렉토리 역할

| 경로 | 역할 | 근거 |
|---|---|---|
| `dml-server/ai-model/` | MIC -> EGG 모델 학습 코드. 모델 정의, 학습 스크립트, SVD loader, 검증/시각화 스크립트가 있다. | `README.md:16-19`, `dml-server/ai-model/README.md:5-34` |
| `dml-server/model_server/` | FastAPI 추론/분석 서버. `/predict`, `/analyze`, `/analyze-chunk`, `/ws/realtime`, `/health`를 제공한다. | `README.md:16-19`, `dml-server/model_server/server.py:1-7`, `dml-server/model_server/server.py:74-84`, `dml-server/model_server/server.py:184-259`, `dml-server/model_server/server.py:397-402` |
| `dml-server/scripts/` | vocal analysis, song data prep, validation, score mapper 관련 스크립트. | `dml-server/PROJECT_LOG.md:330-347`, `dml-server/scripts/data_prep_t2/README.md:52-60` |
| `dml-server/scripts/sidetrack/` | K-9.5/5-10 데이터 분석, score_mapper_v2, F4 검증 스크립트. | `dml-server/HANDOVER_TO_GPT.md:52-60`, `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:21-42` |
| `data/SVD_healthy/` | EGG 학습용 SVD speaker 디렉토리. 현재 디스크 기준 speaker dir 687개, `.nsp`/`.egg` 파일 19,130개. | `dml-server/ai-model/utils/nsp_reader.py:43-76`, `results/validation_exp20_final.txt:7-12` |
| `data/songs/` | 14곡 master/MR/LRC/pitch_guide/stems 작업 데이터. 현재 master 14개, MR 14개, parsed LRC JSON 42개, pitch_guide JSON 29개. | `dml-server/PROJECT_LOG.md:139-146`, `.gitignore:1-5` |
| `data/vocal_academy/` | 평가자 점수, 5/10 데이터, score mapper 결과, singer WAV 데이터. 현재 `singer_01`~`singer_22` 디렉토리 존재. | `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:21-42`, `.gitignore:15-31` |
| `vocal-server/` | 별도 FastAPI 백엔드. 이 문서는 dml-server 코드 상태 중심이며, vocal-server는 dml-server 결과 저장/앱 API 쪽이다. | `README.md:9-15`, `README.md:44-51` |
| `app/` | Expo 앱 placeholder/별도 작업 영역. | `README.md:25-27` |
| `checkpoints/` | 모델 checkpoint 저장 위치. 현재 디스크에 각 실험별 `best_model.pt`가 있다. git ignore 대상. | `.gitignore:33-39` |
| `results/` | 학습/검증 산출물. 현재 Exp별 `metrics.json` 및 validation txt/png가 있다. git ignore 대상. | `.gitignore:44-47` |

## 2. 모델 코드: EfficientEGGNet

EfficientEGGNet 정의 위치는 `dml-server/ai-model/model/efficient_egg.py`이다. 현재 코드 기준 구조는 다음과 같다.

- `DilatedBlock`: non-causal symmetric padding, filter conv + gate conv, 1x1 residual conv, 1x1 skip conv, dropout, GroupNorm을 사용한다. (`dml-server/ai-model/model/efficient_egg.py:13-42`)
- `EfficientEGGNet`: input projection `Conv1d(1, channels, 1) -> GELU -> Conv1d(channels, channels, 3, padding=1)`, dilated block stack, skip sum, output projection `GELU -> Conv1d(channels, channels, 1) -> GELU -> Dropout -> Conv1d(channels, 1, 1)` 구조다. (`dml-server/ai-model/model/efficient_egg.py:45-102`)
- block dilation은 각 stack 안에서 `2 ** layer`로 증가한다. (`dml-server/ai-model/model/efficient_egg.py:75-82`)
- 운영 Exp20 설정은 checkpoint 내부 config가 아니라 코드 상수 `EXP20_CONFIG`로 재기입된다: `channels=128`, `n_layers=30`, `kernel_size=5`, `n_stacks=5`, `dropout=0.05`. (`dml-server/model_server/predictor.py:24-31`, `dml-server/model_server/analysis_pipeline.py:59-62`)
- `receptive_field()` helper는 `kernel_size=3` 전제 주석을 갖고 있어 Exp20 `kernel_size=5` receptive field 산정 근거로 그대로 쓰면 안 된다. (`dml-server/ai-model/model/efficient_egg.py:107-115`)

Stage 1 / Stage 2 용어 구분:

- EfficientEGGNet 모델 정의 자체에는 `Stage 1`/`Stage 2` 구분이 없다. 모델 학습에서 현재 확인되는 구분은 Exp20의 3개 `phase`이다.
- Exp20은 `run_exp20()`에서 window 4096 -> 8192 -> 16384 progressive training으로 정의되어 있다. (`dml-server/ai-model/auto_experiment_v2.py:1102-1125`)
- 코드 내 `Stage 1`/`Stage 2`는 song data prep에서 LRC 수집 / Demucs+CREPE+MR 정렬 또는 평가 CSV 병합 문맥에 쓰인다. (`dml-server/PROJECT_LOG.md:112-113`, `dml-server/scripts/e4_merge_csv_icc.py:1-15`)

## 3. 체크포인트 현황

저장 경로 규칙:

- 일반 학습 루프는 `PROJECT_DIR/checkpoints/{exp_name}/best_model.pt`에 best checkpoint를 저장한다. (`dml-server/ai-model/auto_experiment_v2.py:713-717`, `dml-server/ai-model/auto_experiment_v2.py:1169-1174`)
- Exp20 최종 운영 checkpoint는 `checkpoints/exp20_progressive/best_model.pt`이고 서버 기본값도 이 경로다. (`dml-server/model_server/server.py:31-36`, `dml-server/model_server/predictor.py:24-31`)
- checkpoint와 `.pt` 파일은 git ignore 대상이다. (`.gitignore:33-39`)

현재 디스크에 있는 `best_model.pt` 목록과 파악 가능한 산출물:

| checkpoint | 산출물/실험 | 확인된 메타/결과 |
|---|---|---|
| `checkpoints/best_model.pt` | 초기 baseline 또는 출처 불명 | checkpoint 내부 `epoch=21`, `val_corr=0.6760882468924102`, config에 `layers=8`, `channels=32`, `use_attention=true`가 있다. 출처 실험명은 checkpoint 경로만으로 불명확. |
| `checkpoints/exp1_larger_model/best_model.pt` | `exp1_larger_model` | `results/exp1_larger_model/metrics.json` test_corr `0.6784170953262242` (`metrics.json` 파일), checkpoint 내부 `epoch=19`, `val_corr=0.6887013181259479`. |
| `checkpoints/exp1b_longer_window/best_model.pt` | `exp1b_longer_window` | `results/exp1b_longer_window/metrics.json` test_corr `0.6763037542275899`; checkpoint 내부 `epoch=8`, `val_corr=0.6847795032148878`. |
| `checkpoints/exp2_tcn_unet/best_model.pt` | `exp2_tcn_unet` | checkpoint 내부 `epoch=3`, `val_corr=0.6918587480150756`; `results/exp2_tcn_unet`에는 `metrics.json` 없음. |
| `checkpoints/exp3_efficient/best_model.pt` | `exp3_efficient` | `results/exp3_efficient/metrics.json` test_corr `0.7162794487029125`; checkpoint 내부 `epoch=10`, `val_corr=0.7229365750990466`. |
| `checkpoints/exp4_multi_input/best_model.pt` | `exp4_multi_input` | `results/exp4_multi_input/metrics.json` test_corr `0.7136946740278122`; checkpoint 내부 `epoch=58`, `val_corr=0.7189312037092406`. |
| `checkpoints/exp5_high_quality_data/best_model.pt` | `exp5_high_quality_data` | `results/exp5_high_quality_data/metrics.json` test_corr `0.6955645073332714`, best_val_corr `0.7682227397130595`. |
| `checkpoints/exp6_transformer/best_model.pt` | `exp6_transformer` | `results/exp6_transformer/metrics.json` test_corr `0.7029876223988406`, best_val_corr `0.7139634341464796`. |
| `checkpoints/exp7_conformer/` | directory only | `best_model.pt` 없음. 출처 불명/중단 가능. |
| `checkpoints/exp8_wav2vec2/best_model.pt` | `exp8_wav2vec2` | `results/exp8_wav2vec2/metrics.json` test_corr `-0.00019703219586240833`, best_val_corr `0.00017953695968843245`. |
| `checkpoints/exp9_curriculum/best_model.pt` | `exp9_curriculum` | `results/exp9_curriculum/metrics.json` test_corr `0.7126064078436152`; checkpoint 내부 `epoch=33`, `phase=2`. |
| `checkpoints/exp10_large_efficient/best_model.pt` | `exp10_large_efficient` | `results/exp10_large_efficient/metrics.json` test_corr `0.7205173860592844`, best_val_corr `0.7242714836189704`. |
| `checkpoints/exp11_multiscale/best_model.pt` | `exp11_multiscale` | `results/exp11_multiscale/metrics.json` test_corr `0.7484286622837446`, best_val_corr `0.7563797699060996`. |
| `checkpoints/exp13_multiscale_regularized/best_model.pt` | `exp13_multiscale_regularized` | `results/exp13_multiscale_regularized/metrics.json` test_corr `0.7494605331008559`, best_val_corr `0.7569620475928123`. |
| `checkpoints/exp14_multiscale_augmented/best_model.pt` | `exp14_multiscale_augmented` | `results/exp14_multiscale_augmented/metrics.json` test_corr `0.7399384050729056`, best_val_corr `0.7527756246574525`. |
| `checkpoints/exp15_multiscale_mixup/best_model.pt` | `exp15_multiscale_mixup` | `results/exp15_multiscale_mixup/metrics.json` test_corr `0.7522326940883698`, best_val_corr `0.7586089069250266`. |
| `checkpoints/exp16_multiscale_se/best_model.pt` | `exp16_multiscale_se` | `results/exp16_multiscale_se/metrics.json` test_corr `0.7497241131454947`, best_val_corr `0.7589636932079983`. |
| `checkpoints/exp17_multiscale_cbam/best_model.pt` | `exp17_multiscale_cbam` | `results/exp17_multiscale_cbam/metrics.json` test_corr `0.7521373566646194`, best_val_corr `0.7601918686433016`. |
| `checkpoints/exp18_deeper_multiscale/best_model.pt` | `exp18_deeper_multiscale` | `results/exp18_deeper_multiscale/metrics.json` test_corr `0.7500210824757213`, best_val_corr `0.7548956012856719`. |
| `checkpoints/exp19_cosine_warmup/best_model.pt` | `exp19_cosine_warmup` | `results/exp19_cosine_warmup/metrics.json` test_corr `0.7490945593986665`, best_val_corr `0.756704491009382`. |
| `checkpoints/exp20_progressive/best_model.pt` | 최종 운영 Exp20 | `results/exp20_progressive/metrics.json` test_corr `0.8248865494888475`, test_mse `0.19214897956556945`, test_r2 `0.8078510204344306`, phases 4096/8192/16384. (`results/exp20_progressive/metrics.json:2-19`) checkpoint 내부 `epoch=61`, `val_corr=0.8217522351357799`, `phase=3`. |

주의: 표의 checkpoint 내부 메타는 2026-07-06에 `torch.load(..., map_location='cpu')`로 binary checkpoint에서 읽은 값이다. 실험 성능 수치(`test_corr`, `best_val_corr`)는 `results/*/metrics.json` 파일에서만 인용했다.

## 4. 추론 서버

엔드포인트:

| endpoint | 코드 위치 | 요청 | 응답 요약 |
|---|---|---|---|
| `GET /health` | `dml-server/model_server/server.py:74-81` | 없음 | `status`, `model_loaded`, `gpu_available`, `device` |
| `POST /predict` | `dml-server/model_server/server.py:84-129` | multipart `file`, optional `run_id` query | `run_id`, `status`, `egg_signal_uri`, `duration_ms`, `processing_time_ms` |
| `POST /analyze` | `dml-server/model_server/server.py:184-255` | multipart `file`, optional `run_id`, optional `song_id` | `StreamingResponse(application/json)`. body status: `success`, `no_voice`, `invalid`, `failed`; includes `audio_info`, `registers`, `indicators`, `scores`, `scores_v2`, `scores_meta`, `academic_analysis_scores`, `score_mapper_version`, `timeline_scores` when `song_id` exists. |
| `POST /analyze-chunk` | `dml-server/model_server/server.py:258-393` | multipart `file`, optional `run_id`, `start_sec`, `end_sec`, `song_id` | chunk duration check, legacy `scores` 2항목, `scores_v2` 4항목, `scores_meta`, `low_confidence_items`, `score_mapper_version`, `indicators` |
| `WebSocket /ws/realtime` | `dml-server/model_server/server.py:397-402`, `dml-server/model_server/services/realtime.py:1-20` | optional meta text frame, then 16kHz mono int16 LE PCM binary frames | per-frame `pitch_match`, 5s마다 `breathiness_chunk`; v2 미적용 |

모델 로딩:

- 서버 startup에서 `EGGPredictor(CHECKPOINT_PATH)`와 `AnalysisPipeline(CHECKPOINT_PATH, CRITERIA_PATH, MAPPINGS_PATH)`를 한 번 생성한다. (`dml-server/model_server/server.py:60-69`)
- 기본 checkpoint는 `~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt`이고 env `CHECKPOINT_PATH`로 override 가능하다. (`dml-server/model_server/server.py:31-36`)
- `EGGPredictor`와 `AnalysisPipeline` 모두 `torch.device("cuda" if torch.cuda.is_available() else "cpu")`를 사용한다. (`dml-server/model_server/predictor.py:41-50`, `dml-server/model_server/analysis_pipeline.py:309-317`)
- `/predict`는 16kHz mono, z-score, `WINDOW_SIZE=16384`, `HOP_SIZE=8192`, overlap-add inference를 수행한다. (`dml-server/model_server/predictor.py:33-35`, `dml-server/model_server/predictor.py:74-107`, `dml-server/model_server/predictor.py:112-146`)
- `/analyze`의 EGG 추론도 동일 window/hop overlap-add helper를 사용한다. (`dml-server/model_server/analysis_pipeline.py:49-57`, `dml-server/model_server/analysis_pipeline.py:165-185`)

B6 147s 처리 구현:

- `/analyze`는 첫 byte로 whitespace를 즉시 yield하고, 분석은 `asyncio.to_thread(_analyze_sync, ...)`에서 실행하며, 5초 timeout마다 whitespace keepalive를 추가로 yield한다. (`dml-server/model_server/server.py:234-255`)
- 저장소 로그에는 B6 301s 곡 tunnel 검증 결과가 `HTTP 200`, TTFB `6.0s`, read `147.2s`, body.status `success`로 기록되어 있다. (`dml-server/PROJECT_LOG.md:854-858`)
- 같은 로그는 Cloudflare tunnel TTFB 한계 실측을 125.6s, full `/analyze` 비용을 약 150~180s 위험 구간으로 기록한다. (`dml-server/PROJECT_LOG.md:829-833`)

## 5. 학습 파이프라인

데이터 로더:

- `SVDEggDataset`는 `(nsp_path, egg_path, speaker_id)` pair를 받아 speech window와 EGG window를 같은 위치에서 잘라 반환한다. (`dml-server/ai-model/utils/dataset.py:38-55`, `dml-server/ai-model/utils/dataset.py:143-154`)
- NSP/EGG 파일은 `utils/nsp_reader.py`에서 IFF `FORM/DS16`의 `HEDR`와 `SDA_` chunk를 읽고 int16을 float32 `[-1, 1]`로 변환한다. (`dml-server/ai-model/utils/nsp_reader.py:1-40`)
- pair 탐색은 speaker 디렉토리 아래 `vowels/`, `sentences/`에서 `X.nsp`와 `X-egg.egg`를 매칭한다. (`dml-server/ai-model/utils/nsp_reader.py:43-76`)
- split은 speaker 단위 0.8/0.1/0.1, seed 42 `np.random.RandomState`로 수행된다. (`dml-server/ai-model/utils/dataset.py:15-35`, `dml-server/ai-model/utils/dataset.py:157-217`)
- 전처리는 source 50kHz -> target 16kHz resample, speech/EGG 길이 trim, per-file z-score normalize, window/hop index 생성이다. (`dml-server/ai-model/utils/dataset.py:80-138`)

학습 실행:

- Exp20 진입점은 `python dml-server/ai-model/auto_experiment_v2.py`의 `main()`이며 experiment list에 `('exp20_progressive', run_exp20)`가 포함된다. (`dml-server/ai-model/auto_experiment_v2.py:1306-1344`)
- Exp20 단독 함수 `run_exp20(device)`는 `build_efficient_model({'channels':128,'n_layers':30,'kernel_size':5,'n_stacks':5,'dropout':0.05})`를 만들고, 3 phase progressive window로 학습한다. (`dml-server/ai-model/auto_experiment_v2.py:1102-1125`)
- phase 설정: 4096/2048 batch 32 epochs 20 lr 0.001, 8192/4096 batch 16 epochs 40 lr 0.0005, 16384/8192 batch 8 epochs 40 lr 0.0003. (`dml-server/ai-model/auto_experiment_v2.py:1121-1125`)
- loss는 `CombinedLoss(alpha=0.2)`, optimizer는 `AdamW(weight_decay=1e-4)`, scheduler는 `OneCycleLR`, AMP `GradScaler('cuda')`를 사용한다. (`dml-server/ai-model/auto_experiment_v2.py:1127-1148`)
- best checkpoint는 val corr 개선 시 `epoch`, `model_state_dict`, `val_corr`, `phase`를 저장한다. (`dml-server/ai-model/auto_experiment_v2.py:1164-1174`)
- 최종 test는 window 16384/hop 8192 loader로 수행하고 `results/exp20_progressive/metrics.json`, `history.json`을 저장한다. (`dml-server/ai-model/auto_experiment_v2.py:1188-1214`)

주요 설정 파일:

- `dml-server/ai-model/configs/config.yaml`: baseline config.
- `dml-server/ai-model/egg_from_mic/configs/*.yaml`: 초기 `egg_from_mic` 실험 config.
- 현재 Exp20 운영 설정은 YAML이 아니라 `auto_experiment_v2.py`, `model_server/predictor.py`, `model_server/analysis_pipeline.py`의 Python 상수로 확인된다.

검증 수치:

- Exp20 metrics: test_corr `0.8248865494888475`, test_mse `0.19214897956556945`, test_r2 `0.8078510204344306`. (`results/exp20_progressive/metrics.json:2-5`)
- comprehensive validation: total files 9565, speakers 687, train/val/test speakers 549/68/70, overlap 0, leak-free true. (`results/validation_exp20_final.txt:7-12`)
- 같은 validation에서 window 16384 기준 exp20 mean corr `0.8248`, median `0.9515`, std `0.2934`, MSE `0.1921`로 기록되어 있다. (`results/validation_exp20_final.txt:22-28`)

## 6. K-9.5 분석 파이프라인 (Steps A~D, F1~F4)

현재 저장소에는 K-9.5 작업의 실행 순서가 `handover_to_new_agent.md`에 “Step A -> B0a -> B1-A -> B1-B -> B2 -> B3 -> D-fix -> D3, Follow-up F1+F2+F3, F4”로 기록되어 있다. (`data/vocal_academy/results/sidetrack/handover_to_new_agent.md:9-15`) 아래 표는 현재 체크아웃에서 확인되는 스크립트와 입출력 기준이다.

| 순서 | 단계 | 스크립트/파일 | 입력 | 출력/역할 | 근거 |
|---|---|---|---|---|---|
| A | 5/10 raw 정리 | `dml-server/scripts/sidetrack/organize_510_data.py` | `data/vocal_academy/_510_raw/평가자료(5:10)/` | A그룹 WAV -> `validation_510/`, B그룹 WAV -> `control_pre_510/`, MIDI -> `midi_510/`, 평가 docx -> `_new_eval_510/` | `organize_510_data.py:1-15`, `organize_510_data.py:24-43` |
| B0a | 평가 docx 파싱 | `dml-server/scripts/sidetrack/parse_510_evals.py` | `_new_eval_510/평가1~5.docx` | `data/vocal_academy/trainer_scores_510.csv` | `parse_510_evals.py:1-12`, `parse_510_evals.py:73-77` |
| B1-A | 33 phone indicator 산출 | `dml-server/scripts/sidetrack/run_indicators_v2.py`, `indicators_v2.py` | training oral/phone WAV + 5/10 phone WAV | `data/vocal_academy/results/sidetrack/indicators_v2_*.csv` 계열 | `run_indicators_v2.py:1-5`, `run_indicators_v2.py:51-90`, `indicators_v2.py:1-24` |
| B1-B/F1 | 차이/누출/매칭 진단 | `matching_comparison_510.py`, `b1_difference_root_cause.md` | `ai_scores.json`, `inference_510/*.json`, `trainer_scores_510.csv` | per-register vs per-session 비교, 분포/클리핑 원인 진단 | `matching_comparison_510.py:1-22`, `matching_comparison_510.py:35-52`, `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:39-42` |
| B2 | single indicator search | 결과 파일 `single_indicator_search_v2.csv` | v2 indicator grid | 1710 indicator grid 결과 | `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:40-42` |
| B3 | multivariate model grid | 결과 파일 `multivariate_models_v3.csv` | B2 후보/indicator | 216 model grid 결과 | `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:40-42` |
| D-fix | 호흡식별 모델 비교 | 결과 파일 `breathiness_model_selection.csv` | 15 후보 모델 | 호흡식별 model selection 결과 | `data/vocal_academy/results/sidetrack/handover_to_new_agent.md:39-40` |
| D3/F2 | endpoint/v2 검증 | `d3_endpoint_validation_full.csv`, `score_mapper_v2_predictions_21.csv` | 21명 WAV, v2 mapper | F2 21명 endpoint 검증 126 cells, 21명 x 6항목 예측 | `dml-server/HANDOVER_TO_GPT.md:65-72` |
| F3 | spec/앱 공유 | `dml-server/docs/vocal_app_score_mapper_v2_spec.md`, `sample_response_analyze.json` | `/analyze` sample | vocal-app/server 응답 schema 문서 | `dml-server/docs/vocal_app_score_mapper_v2_spec.md:1-12`, `dml-server/scripts/sidetrack/f4_sample_response_dump.py:1-27` |
| F4-1/F4-2 | timeline 4항목 확장 | `dml-server/model_server/services/timeline_analysis.py` | audio bytes + LRC segments + pipeline | `timeline_scores`, `timeline_metadata` 4항목 v2 chunk score | `timeline_analysis.py:1-18`, `timeline_analysis.py:153-278` |
| F4-3 | `/analyze-chunk` v2 schema | `dml-server/model_server/server.py`, `f4_chunk_endpoint_test.py` | 3~10s chunk WAV | legacy 2항목 + v2 4항목 + low_confidence | `server.py:258-393`, `f4_chunk_endpoint_test.py:1-68` |
| F4-4 | metadata/low confidence | `timeline_analysis.py` | chunk duration | `shown_indicators`, deferred, low_conf threshold 5.0 | `timeline_analysis.py:29-47`, `timeline_analysis.py:256-278` |
| F4-5 | 21명 validation | `dml-server/scripts/sidetrack/f4_validation_21.py` | `validation_510/`, `control_pre_510/`, `score_mapper_v2_predictions_21.csv` | `timeline_scores_4items_validation.csv`, `timeline_scores_4items_summary.csv` | `f4_validation_21.py:1-12`, `f4_validation_21.py:32-40`, `f4_validation_21.py:150-201` |

F4 검증 로그 수치:

- `PROJECT_LOG.md`에는 F4 검증 완료값으로 `21명 578 chunks`, `out_of_range 0`, full-song ref corr `0.69~0.89`가 기록되어 있다. (`dml-server/PROJECT_LOG.md:790-794`)

T2 보조 파이프라인:

- `dml-server/scripts/data_prep_t2/run_t2_pipeline.sh`는 별도 T2 5단계 pipeline이다: 평가지 파싱, ICC 검증, `/analyze` 호출+상관계수, score_mapper 재학습, 신뢰도 재분류. (`dml-server/scripts/data_prep_t2/README.md:52-60`, `dml-server/scripts/data_prep_t2/run_t2_pipeline.sh:68-105`)

## 7. score_mapper_v2

위치:

- 코드: `dml-server/scripts/sidetrack/score_mapper_v2.py`
- indicator 함수: `dml-server/scripts/sidetrack/indicators_v2.py`
- params: `data/vocal_academy/results/sidetrack/mapping_params_v2.json`
- phone->oral mapper: `dml-server/scripts/sidetrack/models/phone_to_oral_mapper_v2.pkl`
- tongue tension tree: `dml-server/scripts/sidetrack/models/score_mapper_v2_혀경직도_tree.pkl`

처리 로직:

- `ScoreMapperV2`는 params JSON과 phone-to-oral pickle을 load하고, mapper feature order를 pickle에서 가져온다. (`score_mapper_v2.py:35-50`)
- WAV/audio를 16kHz mono로 만들고 `indicators_v2.compute_all()`로 33 phone indicator를 산출한다. (`score_mapper_v2.py:52-69`, `indicators_v2.py:1-24`)
- phone indicators를 ridge mapper로 oral indicator mapped feature로 변환한다. (`score_mapper_v2.py:71-80`)
- params의 `feature_order`와 `feature_translation`에 따라 학습 feature vector를 만든다. (`score_mapper_v2.py:82-97`, `mapping_params_v2.json:3-51`)
- 각 item model은 scaler mean/scale로 표준화한 뒤 linear coefficient/intercept 또는 lazy-loaded tree model로 raw prediction을 만들고, 0~5 clip 후 `ai_score`, `rounded_score`, `raw_pred`, `tier`, `caveats`, `icc`, `icc_ratio`를 반환한다. (`score_mapper_v2.py:113-139`)

9개 항목 매핑:

| app key | 한국어 | v2 상태 | 근거 |
|---|---|---|---|
| `1_nasal_oral_ratio` | 비강사용 | `academic_only`, 앱 표시 X | `analysis_pipeline.py:618-656`, `mapping_params_v2.json:803-901` |
| `2_chest_head_voice` | 흉성두성 | deferred | `mapping_params_v2.json:52-56`, `analysis_pipeline.py:699-701` |
| `3_vocal_fold_contact` | 접촉강도 | 표시 4항목, `high` | `mapping_params_v2.json:58-153`, `analysis_pipeline.py:638-649` |
| `4_breathiness` | 호흡식별 | 표시 4항목, `high_star` | `mapping_params_v2.json:248-426`, `analysis_pipeline.py:638-649` |
| `5_forward_resonance` | 전방공명 | `academic_only`, 앱 표시 X | `mapping_params_v2.json:998-1095`, `analysis_pipeline.py:650-655` |
| `6_soft_palate` | 연구개위치 | 표시 4항목, `high_star` | `mapping_params_v2.json:443-541`, `analysis_pipeline.py:638-649` |
| `7_larynx_tongue_root` | 공명개방 | deferred | `mapping_params_v2.json:52-56`, `analysis_pipeline.py:699-701` |
| `8_tongue_tension` | 혀경직도 | 표시 4항목, `high_star`, GB tree | `mapping_params_v2.json:638-756`, `analysis_pipeline.py:638-649` |
| `9_pressure_balance` | 상압하압 | deferred | `mapping_params_v2.json:52-56`, `analysis_pipeline.py:699-701` |

표시 4항목 선정:

- 서버 응답의 `reliability.shown_v2`는 `3_vocal_fold_contact`, `4_breathiness`, `6_soft_palate`, `8_tongue_tension`이고, tiers는 contact만 `high`, 나머지 3개는 `high_star`다. (`analysis_pipeline.py:686-701`)
- vocal-app spec도 통제 실험 기간 표시 항목을 위 4개로 정의한다. (`dml-server/docs/vocal_app_score_mapper_v2_spec.md:126-138`)
- `academic_only_v2`는 `1_nasal_oral_ratio`, `5_forward_resonance`; `deferred_v2`는 `2_chest_head_voice`, `7_larynx_tongue_root`, `9_pressure_balance`이다. (`analysis_pipeline.py:699-701`)

low_confidence 기준:

- timeline에서는 `LOW_CONF_THRESHOLD_S = 5.0`이고, chunk duration이 5초 미만이면 `4_breathiness`, `6_soft_palate`, `8_tongue_tension`을 `low_confidence_items`에 넣는다. (`timeline_analysis.py:43-47`, `timeline_analysis.py:231-244`)
- `/analyze-chunk`도 `duration < 5.0`이면 같은 3항목을 `low_confidence_items`로 반환한다. (`server.py:368-371`)
- chunk 전처리 자체는 3초 미만이면 `ChunkTooShortError`, 3초 이상 5초 미만은 `confidence="medium"`, 5초 이상은 `confidence="high"`다. (`chunk_analysis.py:24-27`, `chunk_analysis.py:65-73`)

v2 수치 출처:

- `mapping_params_v2.json` version은 `v2`다. (`mapping_params_v2.json:1-2`)
- 접촉강도: tier `high`, ICC `0.898`, ICC ratio `0.816`, validation `val_total=0.7327`, `val_full21=0.7593`, `paired_leaked=0.9522`. (`mapping_params_v2.json:150-162`)
- 호흡식별: tier `high_star`, ICC `0.796`, ICC ratio `0.546`, caveats `regularization_softened_for_range_v2_fix`, `train_val_sign_diverged`, `val_total_below_0_5`, validation `val_total=0.4343`, `val_full21=0.4676`, `paired_leaked=0.9113`. (`mapping_params_v2.json:423-438`)
- 연구개위치: tier `high_star`, ICC `0.643`, ICC ratio `0.97`, caveat `train_weak_external_only`, validation `val_total=-0.6236`, `val_full21=-0.5759`. (`mapping_params_v2.json:538-552`)
- 혀경직도: tier `high_star`, ICC `0.802`, ICC ratio `0.865`, caveat `train_weak_external_only`, tree model pickle path. (`mapping_params_v2.json:743-756`)
- 비강사용/전방공명: `academic_only`, caveat `sign_reversed`. (`mapping_params_v2.json:898-905`, `mapping_params_v2.json:1092-1099`)

## 8. 데이터셋 구성과 누출 격리

EGG 학습 데이터:

- `data/SVD_healthy/{speaker_id}/{vowels,sentences}` 구조에서 `.nsp`와 `-egg.egg` pair를 찾는다. (`nsp_reader.py:43-76`)
- 현재 디스크 기준 SVD speaker directory는 687개이며, comprehensive validation도 speakers 687로 기록한다. (`results/validation_exp20_final.txt:7-12`)
- speaker-independent split은 speaker id set을 train/val/test로 나누고, 파일 pair는 speaker membership으로 분리한다. (`dataset.py:15-35`, `dataset.py:174-188`)
- validation 로그는 train/val/test speakers 549/68/70, overlap 0, leak-free true를 기록한다. (`results/validation_exp20_final.txt:7-12`)

score_mapper / vocal academy 데이터:

- `data/vocal_academy/singer_01`~`singer_22`: 학습/평가 WAV.
- `data/vocal_academy/validation_510`: 5/10 A group 10명.
- `data/vocal_academy/control_pre_510`: 5/10 B group 11명.
- `data/vocal_academy/results/sidetrack/`: K-9.5/F4 산출물과 mapper params.
- `run_indicators_v2.py`는 `LEAKED`와 `LEAKED_TRAINING_SINGERS`를 명시하고 각 job meta에 `is_leaked`, `leakage_type`을 넣는다. (`run_indicators_v2.py:16-23`, `run_indicators_v2.py:56-90`)

데이터/git 주의:

- `.gitignore`가 음원, 사용자 음성, SVD, trainer score CSV, checkpoints, results, data 전체를 ignore한다. (`.gitignore:1-47`)
- 따라서 코드 저장소만 clone하면 학습/검증 재현에 필요한 `data/`, `checkpoints/`, `results/`는 따라오지 않을 수 있다.

## 9. 환경

`environment.yml`은 2026-07-06에 다음 명령으로 export했다.

```bash
/home/dmlserver/miniconda3/bin/conda env export -n EGGDML --no-builds > /tmp/egg_prediction_environment.yml
```

현재 세션에서 확인한 런타임:

- Conda env: `EGGDML` (`/home/dmlserver/miniconda3/envs/EGGDML`)
- Python: `3.11.14`
- PyTorch: `2.10.0+cu128`
- `torch.version.cuda`: `12.8`
- cuDNN: `91002`
- 현재 세션에서는 `torch.cuda.is_available()`가 `False`, `torch.cuda.device_count()`가 `0`이었다. `nvidia-smi`는 driver communication 실패를 반환했다. 이는 서버 코드가 CUDA 가능 시 GPU를 쓰도록 되어 있다는 사실과 별개로, 2026-07-06 현재 이 shell 세션의 GPU 접근은 실패했다는 뜻이다.
- 서버 코드의 GPU 선택은 `torch.cuda.is_available()` 기준이다. (`predictor.py:41-50`, `analysis_pipeline.py:309-317`)

운영 로그/문서상 과거 production baseline:

- `HANDOVER_TO_GPT.md`는 model_server가 `dml-server.service -> python server.py`, port 8001, CUDA, ScoreMapperV2 6 models로 가동된다고 기록한다. (`dml-server/HANDOVER_TO_GPT.md:26-29`)
- systemd 전환 기록은 `WorkingDirectory=model_server`, port 8001, `RuntimeMaxSec=3600`을 기록한다. (`dml-server/PROJECT_LOG.md:942-947`)

## 10. git 이력

문서 작성 중 확인한 git 상태:

- branch: `main`
- 선행 snapshot commit: `acb71d0 chore: capture pre-handover state`
- tag: `v2.x-gpt-final`은 `acb71d0`에 로컬 생성됨.
- `origin/main`은 `b95ddc1`에 있었다. `acb71d0` push는 정책상 보류됨.
- 이 문서와 `environment.yml`은 `acb71d0` 이후 별도 handover commit으로 추가된다. 자기 자신을 포함한 최종 commit hash는 `git log --oneline -1`로 확인한다.

최근 커밋:

```text
acb71d0 (tag: v2.x-gpt-final) chore: capture pre-handover state
b95ddc1 (origin/main, origin/HEAD) docs: update CLAUDE.md and PROJECT_LOG.md with 2026-05-04 session summary
42a1345 feat: song_id 쿼리 파라미터 -> dml-server 전달 (timeline_scores 지원)
1002974 feat: Add demo_responses mock data (5 cases) for app development
483932d feat: Whisper cross-corr diagnostic, demo case selector, stability probe
3acffbf feat: T2 pipeline scripts + Whisper ASR LRC generation
4d17503 Merge branch 'main' of github.com:kim-jeongwoo/graduation-project
16bd8c4 Reorganize: move dml-server code into dml-server/ subfolder for monorepo structure
```

## 11. TODO/FIXME/HACK 주석 전수 수집

검색 범위: `/home/dmlserver/projects/egg_prediction`, 제외: `.git`, `.venv`, 검색어: `TODO|FIXME|HACK` 대소문자 무시.

| 파일 | 줄 | 내용 |
|---|---:|---|
| `vocal-server/app/models/models.py` | 36 | `# TODO: 상용화 시 default=False로 변경, 가입 승인 흐름 추가` |
| `vocal-server/app/routers/songs.py` | 98 | `# TODO: 앱에서 부분 재생/탐색 필요 시 range request 구현` |

`FIXME`, `HACK`는 검색 결과 없음.

## 12. 위험 지점

하드코딩 경로:

- `PROJECT_DIR = os.path.expanduser('~/projects/egg_prediction')`, `SVD_PATH = ~/projects/egg_prediction/data/SVD_healthy`: 학습 스크립트는 절대/홈 경로 의존이다. (`auto_experiment_v2.py:47-55`)
- `ScoreMapperV2`는 `ROOT = Path("/home/dmlserver/projects/egg_prediction")`를 하드코딩한다. (`score_mapper_v2.py:35-38`)
- `server.py` 기본 checkpoint도 `~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt`다. (`server.py:31-36`)
- `analysis_pipeline.py`는 sidetrack dir을 현재 dml-server 기준으로 sys.path에 넣는다. (`analysis_pipeline.py:28-47`)

재현성:

- speaker split seed는 42로 고정되어 있으나, training DataLoader shuffle, augmentation, mixup, AMP, CUDA kernel까지 완전 deterministic 설정은 확인되지 않는다. (`dataset.py:15-35`, `auto_experiment_v2.py:432-510`, `auto_experiment_v2.py:515-542`)
- Exp20 학습은 `torch.amp.autocast('cuda')`와 `GradScaler('cuda')`를 사용한다. CUDA/GPU 접근 상태가 달라지면 재현성/실행 가능성이 달라질 수 있다. (`auto_experiment_v2.py:515-542`, `auto_experiment_v2.py:1148`)
- 현재 shell에서는 GPU 접근이 실패했다. inference server는 CPU fallback이 가능하지만 성능/latency가 달라질 수 있다. (`predictor.py:41-50`, `analysis_pipeline.py:309-317`)

데이터/산출물:

- `data/`, `results/`, `checkpoints/`는 git ignore 대상이라 clone만으로 재현되지 않는다. (`.gitignore:33-47`)
- `ai-model/README.md`는 "Exp3 최고 성능 0.7163"이라고 쓰지만, root README와 결과 파일은 Exp20 `0.8248865494888475`를 최종 성능으로 둔다. 오래된 문서 혼재에 주의해야 한다. (`dml-server/ai-model/README.md:36-43`, `README.md:30-36`, `results/exp20_progressive/metrics.json:2-5`)
- `revalidate.py`의 HTTP timeout은 120초로 되어 있어 현재 full-song `/analyze` 총 소요 `~160-190s` 또는 B6 read `147.2s`와 맞지 않을 수 있다. (`revalidate.py:94-104`, `dml-server/docs/vocal_app_score_mapper_v2_spec.md:270-279`, `dml-server/PROJECT_LOG.md:854-858`)
- `/analyze` StreamingResponse는 HTTP status를 streaming 시작 후 바꿀 수 없어 body `status`를 읽어야 한다. (`server.py:143-162`, `server.py:211-217`, `server.py:234-255`)
- `/ws/realtime`은 v2 score_mapper를 적용하지 않고 v1 schema를 유지한다. (`realtime.py:1-20`, `dml-server/PROJECT_LOG.md:932-940`)
