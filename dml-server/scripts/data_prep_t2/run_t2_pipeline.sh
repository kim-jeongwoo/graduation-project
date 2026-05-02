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
#   bash dml-server/scripts/data_prep_t2/run_t2_pipeline.sh [--mode validation|all]
#                                                            [--skip-retrain]
#                                                            [--dry-run]

set -e
cd "$(dirname "$0")/../../.."  # egg_prediction root

SCRIPTS="dml-server/scripts/data_prep_t2"
MODE="validation"
SKIP_RETRAIN=0
DRY_RUN=""

for arg in "$@"; do
    case $arg in
        --mode=*)    MODE="${arg#*=}" ;;
        --mode)      shift; MODE="$1" ;;
        --skip-retrain) SKIP_RETRAIN=1 ;;
        --dry-run)   DRY_RUN="--dry-run" ;;
    esac
done

echo "======================================================"
echo " T2 파이프라인 시작: $(date)"
echo " mode=$MODE  skip_retrain=$SKIP_RETRAIN"
echo "======================================================"

# ── Step 1: 평가지 파싱 ───────────────────────────────────
echo ""
echo "[1/5] 평가지 docx 파싱..."
python "$SCRIPTS/parse_new_evals.py" --mode "$MODE" \
  || { echo "[FAIL] Step 1"; exit 1; }

# ── Step 2: ICC 검증 ──────────────────────────────────────
echo ""
echo "[2/5] ICC 신뢰도 검증..."
python "$SCRIPTS/validate_icc.py" \
  || { echo "[FAIL] Step 2"; exit 1; }

# ── Step 3: AI 분석 + 상관계수 ───────────────────────────
echo ""
echo "[3/5] model_server /analyze 호출 + 상관계수 계산..."
python "$SCRIPTS/revalidate.py" --mode "$MODE" \
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
