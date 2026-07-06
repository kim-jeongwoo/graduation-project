#!/usr/bin/env bash
# batch_f0_to_midi_segments.sh — 전곡 자체 F0 → MIDI segments 일괄 변환
#
# 사용법:
#   bash batch_f0_to_midi_segments.sh              # 전체 실행
#   bash batch_f0_to_midi_segments.sh --dry-run    # 비교만, JSON 수정 안 함
#   bash batch_f0_to_midi_segments.sh --no-viz     # PNG 생성 안 함
#
# 주의: 외부 MIDI segments 있는 곡은 {id}_external_midi.json 자동 백업.
# 옥타브 검증은 각 곡 dry-run 결과 확인 후 진행 권장.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"
PY="$SCRIPT_DIR/f0_to_midi_segments.py"
PITCH_DIR="$PROJECT_ROOT/data/songs/pitch_guide"

DRY_RUN=""
NO_VIZ=""
for arg in "$@"; do
    [[ "$arg" == "--dry-run" ]] && DRY_RUN="--dry-run"
    [[ "$arg" == "--no-viz"  ]] && NO_VIZ="--no-viz"
done

echo "========================================================"
echo "batch_f0_to_midi_segments"
echo "Project : $PROJECT_ROOT"
[[ -n "$DRY_RUN" ]] && echo "Mode    : dry-run (JSON 수정 안 함)"
echo "========================================================"

ok=0; fail=0; skip=0

for json in "$PITCH_DIR"/[0-9][0-9][0-9].json; do
    sid=$(basename "$json" .json)
    # _mr.json, _external_midi.json 등 제외 (이미 패턴으로 걸러짐)
    echo ""
    echo "── $sid ──────────────────────────────────────────────"

    if conda run -n EGGDML python "$PY" --song "$sid" $DRY_RUN $NO_VIZ; then
        ((ok++))
    else
        echo "  [FAIL] $sid"
        ((fail++))
    fi

    # _mr.json 갱신 (dry-run이 아닐 때)
    if [[ -z "$DRY_RUN" ]]; then
        conda run -n EGGDML python3 - << PYEOF
import json
from pathlib import Path

PITCH_DIR = Path("$PITCH_DIR")
sid = "$sid"

try:
    with open(PITCH_DIR / f"{sid}.json") as f:
        pg = json.load(f)

    if pg.get("guide_source") != "f0":
        exit(0)  # f0가 아니면 _mr.json 갱신 불필요

    lrc_offset = pg.get("lrc_offset_sec", 0.0)
    segs = pg["midi_segments"]
    segs_mr = [
        {**s,
         "start": round(s["start"] + lrc_offset, 3),
         "end":   round(s["end"]   + lrc_offset, 3)}
        for s in segs
    ]
    mr_data = {
        "song_id":        sid,
        "guide_source":   "f0",
        "lrc_offset_sec": lrc_offset,
        "midi_segments":  segs_mr,
    }
    out = PITCH_DIR / f"{sid}_mr.json"
    with open(out, "w") as f:
        json.dump(mr_data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  [MR] {sid}_mr.json 갱신: {len(segs_mr)} segments  offset={lrc_offset:+.3f}s")
except Exception as e:
    print(f"  [MR] 갱신 실패: {e}")
PYEOF
    fi
done

echo ""
echo "========================================================"
echo "완료: ok=$ok  fail=$fail  skip=$skip"
[[ -n "$DRY_RUN" ]] && echo "(dry-run: JSON 수정 없음)"
echo "========================================================"
