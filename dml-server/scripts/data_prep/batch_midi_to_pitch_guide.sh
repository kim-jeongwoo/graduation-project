#!/usr/bin/env bash
# batch_midi_to_pitch_guide.sh — data/songs/midi/*.mid 전곡 변환
# 사용법: bash batch_midi_to_pitch_guide.sh [--dry-run]
#
# MIDI 파일이 있는 곡만 처리 (없으면 skip).
# inspect_midi 자동 탐지 → 실패 시 --track 으로 재실행.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
MIDI_DIR="$PROJECT_ROOT/data/songs/midi"
PY="$SCRIPT_DIR/midi_to_pitch_guide.py"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=true; fi

echo "========================================================"
echo "batch_midi_to_pitch_guide"
echo "MIDI dir : $MIDI_DIR"
echo "Project  : $PROJECT_ROOT"
echo "========================================================"

ok=0; fail=0; skip=0

for mid in "$MIDI_DIR"/*.mid; do
    [[ -f "$mid" ]] || { echo "[SKIP] MIDI 없음"; ((skip++)); continue; }
    sid=$(basename "$mid" .mid)
    echo ""
    echo "── $sid ──────────────────────────────────────────────"
    if $DRY_RUN; then
        echo "  [DRY-RUN] conda run -n EGGDML python $PY --song $sid"
        ((ok++))
    else
        if conda run -n EGGDML python "$PY" --song "$sid"; then
            ((ok++))
        else
            echo "  [FAIL] $sid — --track 으로 수동 지정 필요"
            ((fail++))
        fi
    fi
done

echo ""
echo "========================================================"
echo "완료: ok=$ok  fail=$fail  skip=$skip"
echo "========================================================"
