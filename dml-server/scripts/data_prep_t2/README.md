# data_prep_t2 — T2 데이터 파이프라인

5월 10일 수집 데이터(신규 평가지 docx + 신규 가수 WAV)를 처리하여 score_mapper를 재학습하는 5단계 파이프라인.

## 전제 조건

```bash
conda activate EGGDML
cd ~/projects/egg_prediction
# model_server 실행 중 확인
python3 -c "import requests; print(requests.get('http://localhost:8001/health').json())"
```

## 실행 방법

```bash
# 기본 사용 (T2 validation 데이터만)
bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh \
  --mode validation \
  --eval-dir data/vocal_academy/_new_eval_t2

# 신규 가수 포함 (training 모드, 가수 번호 23~32 → singer-offset=22)
bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh \
  --mode training \
  --eval-dir data/vocal_academy/_new_eval_t2 \
  --singer-offset 22 \
  --wav-dir data/vocal_academy/control_pre

# 전체 (mixed): validation_t2/ + control_pre/ 자동 스캔
bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh \
  --mode mixed \
  --eval-dir data/vocal_academy/_new_eval_t2

# score_mapper 재학습 건너뛰기 (검증만)
bash ... --skip-retrain

# 재학습 dry-run (모델 저장 안 함)
bash ... --dry-run
```

## 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--mode` | `validation` | `validation` / `training` / `mixed` |
| `--eval-dir` | `data/vocal_academy/_new_eval_t2` | 평가지 docx 폴더 |
| `--singer-offset` | `22` | training 모드: 가수 번호 오프셋 (docx item N → singer_{offset+N}) |
| `--wav-dir` | 모드별 기본 경로 | wav 폴더 직접 지정 (기본: validation_t2/ 또는 control_pre/) |
| `--skip-retrain` | — | Step 4 score_mapper 재학습 건너뜀 |
| `--dry-run` | — | Step 4 재학습 실행하되 파일 저장 안 함 |

## 5단계 파이프라인

| 단계 | 스크립트 | 출력 |
|------|----------|------|
| 1. 평가지 파싱 | `parse_new_evals.py` | `data/vocal_academy/trainer_scores_t2.csv` |
| 2. ICC 검증 | `validate_icc.py` | `data/vocal_academy/results/icc_t2.json` |
| 3. AI 분석 + 상관계수 | `revalidate.py` | `data/vocal_academy/results/analyze_t2.json` |
| 4. score_mapper 재학습 | `retrain_score_mapper.py` | `data/vocal_academy/results/ai_scores.json` 갱신 |
| 5. 신뢰도 재분류 | `generate_summary.py` | `data/vocal_academy/results/reliability_t2.json` |

## mode별 wav 경로 (기본값)

| pipeline mode | revalidate mode | 기본 wav 폴더 |
|---------------|-----------------|---------------|
| `validation` | `validation` | `data/vocal_academy/validation_t2/test_*.wav` |
| `training` | `control_pre` | `data/vocal_academy/control_pre/singer_*.wav` |
| `mixed` | `all` | validation_t2/ + control_pre/ 모두 |

## 5월 10일 데이터 준비

```
data/vocal_academy/
  _new_eval_t2/           ← 평가지1~5.docx 여기에
  validation_t2/          ← test_01~10.wav (신규 validation 가수)
  control_pre/            ← singer_23~32.wav (대조군 사전)
  control_post/           ← singer_23~32.wav (대조군 사후, 선택)
```

## 사전 검증 (더미 데이터 테스트)

`test_dummy/` 폴더로 파이프라인 동작 검증 완료 (2026-05-03):
- validation 모드: test_01~11 11곡, 11/11 OK, ICC ≥ 0.7, 전 단계 exit 0
- training 모드: singer_23~32 10곡, 10/10 OK, ICC ≥ 0.7, 전 단계 exit 0
- mixed 모드: 11/11 OK, 전 단계 exit 0
- 버그 수정: health check timeout 5s → 30s + 3회 재시도

`test_dummy/`는 `.gitignore`에 포함됨 (평가지 사본 포함, 개인정보).
