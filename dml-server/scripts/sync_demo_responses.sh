#!/bin/bash
# sync_demo_responses.sh — dml-server/results/demo_responses → 모노레포 루트 demo_responses/
#
# 앱 페이지가 git clone만으로 mock 데이터 접근 가능하도록 루트에 동기화.
# select_demo_cases.py 재실행 후 이 스크립트로 갱신.
#
# 실행:
#   cd ~/projects/egg_prediction
#   bash dml-server/scripts/sync_demo_responses.sh

set -e
cd "$(dirname "$0")/../.."  # egg_prediction root

SOURCE="$HOME/projects/egg_prediction/dml-server/results/demo_responses"
DEST="$HOME/projects/egg_prediction/demo_responses"

echo "[demo-sync] 시작: $(date)"
mkdir -p "$DEST"

rsync -av --delete \
  --include="*.json" \
  --exclude="*" \
  "$SOURCE/" "$DEST/"

echo "[demo-sync] 완료: $(date)"
echo "[demo-sync] 파일 수: $(ls "$DEST"/*.json 2>/dev/null | wc -l) json"
echo "[demo-sync] 디스크: $(du -sh "$DEST" | cut -f1)"
