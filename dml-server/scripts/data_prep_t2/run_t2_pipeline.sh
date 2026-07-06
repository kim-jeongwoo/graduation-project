#!/bin/bash
# run_t2_pipeline.sh — T2 데이터 일괄 처리 파이프라인
#
# 전제:
#   - conda activate EGGDML
#   - cd ~/projects/egg_prediction
#   - model_server 실행 중 (revalidate 단계에서 필요)
#   - 평가지 docx: data/vocal_academy/_new_eval_t2/평가지{1~5}.docx
#   - 신규 wav:    data/vocal_academy/validation_t2/test_*.wav
#                  data/vocal_academy/control_pre/singer_*.wav  (선택)
#                  data/vocal_academy/control_post/singer_*.wav (선택)
#
# 사용:
#   bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh \
#        [--mode validation|training|mixed] \
#        [--eval-dir data/vocal_academy/_new_eval_t2] \
#        [--singer-offset 22] \
#        [--wav-dir data/vocal_academy/validation_t2] \
#        [--skip-retrain] [--dry-run]
#
# mode별 revalidate.py 모드 매핑:
#   validation → validation  (test_*.wav)
#   training   → control_pre (singer_*.wav)
#   mixed      → all         (test_*.wav + singer_*.wav)

set -e
cd "$(dirname "$0")/../../.."  # egg_prediction root

SCRIPTS="dml-server/scripts/data_prep_t2"
MODE="validation"
SKIP_RETRAIN=0
DRY_RUN=""
EVAL_DIR_ARG=""
SINGER_OFFSET=22
WAV_DIR_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)          MODE="$2";          shift 2 ;;
        --mode=*)        MODE="${1#*=}";     shift ;;
        --eval-dir)      EVAL_DIR_ARG="$2";  shift 2 ;;
        --eval-dir=*)    EVAL_DIR_ARG="${1#*=}"; shift ;;
        --singer-offset) SINGER_OFFSET="$2"; shift 2 ;;
        --singer-offset=*) SINGER_OFFSET="${1#*=}"; shift ;;
        --wav-dir)       WAV_DIR_ARG="$2";   shift 2 ;;
        --wav-dir=*)     WAV_DIR_ARG="${1#*=}"; shift ;;
        --skip-retrain)  SKIP_RETRAIN=1;     shift ;;
        --dry-run)       DRY_RUN="--dry-run"; shift ;;
        *) echo "[경고] 알 수 없는 인자: $1" >&2; shift ;;
    esac
done

# revalidate.py 모드 매핑
case "$MODE" in
    validation) REVAL_MODE="validation" ;;
    training)   REVAL_MODE="control_pre" ;;
    mixed)      REVAL_MODE="all" ;;
    *)          REVAL_MODE="$MODE" ;;
esac

echo "======================================================"
echo " T2 파이프라인 시작: $(date)"
echo " mode=$MODE  reval_mode=$REVAL_MODE  skip_retrain=$SKIP_RETRAIN"
[ -n "$EVAL_DIR_ARG" ] && echo " eval_dir=$EVAL_DIR_ARG"
[ -n "$WAV_DIR_ARG"  ] && echo " wav_dir=$WAV_DIR_ARG"
echo "======================================================"

# ── Step 1: 평가지 파싱 ───────────────────────────────────
echo ""
echo "[1/5] 평가지 docx 파싱..."
PARSE_ARGS=(--mode "$MODE" --singer-offset "$SINGER_OFFSET")
[ -n "$EVAL_DIR_ARG" ] && PARSE_ARGS+=(--eval-dir "$EVAL_DIR_ARG")
python "$SCRIPTS/parse_new_evals.py" "${PARSE_ARGS[@]}" \
  || { echo "[FAIL] Step 1"; exit 1; }

# ── Step 2: ICC 검증 ──────────────────────────────────────
echo ""
echo "[2/5] ICC 신뢰도 검증..."
python "$SCRIPTS/validate_icc.py" \
  || { echo "[FAIL] Step 2"; exit 1; }

# ── Step 3: AI 분석 + 상관계수 ───────────────────────────
echo ""
echo "[3/5] model_server /analyze 호출 + 상관계수 계산..."
REVAL_ARGS=(--mode "$REVAL_MODE")
[ -n "$WAV_DIR_ARG" ] && REVAL_ARGS+=(--wav-dir "$WAV_DIR_ARG")
python "$SCRIPTS/revalidate.py" "${REVAL_ARGS[@]}" \
  || { echo "[FAIL] Step 3"; exit 1; }

# ── Step 4: score_mapper 재학습 ──────────────────────────
if [ "$SKIP_RETRAIN" -eq 0 ]; then
    echo ""
    echo "[4/5] score_mapper 재학습..."
    python "$SCRIPTS/retrain_score_mapper.py" $DRY_RUN \
      || { echo "[FAIL] Step 4"; exit 1; }
else
    echo ""
    echo "[4/5] score_mapper 재학습 skip (--skip-retrain)"
fi

# ── Step 5: 신뢰도 분류 + 알림 ──────────────────────────
echo ""
echo "[5/5] 신뢰도 재분류 + 앱 갱신 알림..."
python "$SCRIPTS/generate_summary.py" \
  || { echo "[FAIL] Step 5"; exit 1; }

echo ""
echo "======================================================"
echo " T2 파이프라인 완료: $(date)"
echo " 출력 확인: data/vocal_academy/results/"
echo "======================================================"
