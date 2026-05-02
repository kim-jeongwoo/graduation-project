#!/bin/bash
# dmlserver의 노래방 산출물을 server에 동기화
# 수동 실행: bash scripts/sync_songs.sh
# 자동화는 추후 cron 등으로

set -e  # 에러 시 중단

REMOTE_USER="dmlserver"
REMOTE_HOST="114.71.220.144"
REMOTE_BASE="~/projects/egg_prediction/data/songs"
LOCAL_BASE="app/storage/songs"

echo "[sync] 시작: $(date)"

# 로컬 디렉토리 준비
mkdir -p "$LOCAL_BASE/meta"
mkdir -p "$LOCAL_BASE/audio/mr"
mkdir -p "$LOCAL_BASE/lrc/parsed"
mkdir -p "$LOCAL_BASE/pitch_guide"

# 1. 메타 (songs.json)
echo "[sync] 메타 동기화..."
rsync -avz --progress \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/meta/songs.json" \
  "${LOCAL_BASE}/meta/songs.json"

# 2. MR 음원 (전체)
echo "[sync] MR 음원 동기화..."
rsync -avz --progress \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/audio/mr/" \
  "${LOCAL_BASE}/audio/mr/"

# 3. LRC parsed ({id}.json 만, _aligned 등 변종 제외)
# NOTE: {id}_aligned.json 변종이 존재하나 현재는 {id}.json만 동기화.
#       모델 페이지 산출물 확정 후 패턴 재검토. (CLAUDE.md 참고)
echo "[sync] LRC 동기화..."
rsync -avz --progress \
  --include='[0-9][0-9][0-9].json' \
  --exclude='*' \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/lrc/parsed/" \
  "${LOCAL_BASE}/lrc/parsed/"

# 4. pitch_guide ({id}.json 만, .png 등 제외)
echo "[sync] pitch_guide 동기화..."
rsync -avz --progress \
  --include='[0-9][0-9][0-9].json' \
  --exclude='*' \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/pitch_guide/" \
  "${LOCAL_BASE}/pitch_guide/"

echo "[sync] 완료: $(date)"
echo "[sync] 디스크 사용량:"
du -sh "$LOCAL_BASE"
