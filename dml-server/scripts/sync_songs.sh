#!/bin/bash
# dmlserver의 노래방 산출물을 Mac Studio 서버에 동기화 (Mac Studio에서 실행)
# 수동 실행: cd /Users/kimjeongwoo/vocal-server && bash scripts/sync_songs.sh
# 전제: ssh dmlserver@114.71.220.144 키 기반 인증 설정 완료

set -e

REMOTE_USER="dmlserver"
REMOTE_HOST="114.71.220.144"
REMOTE_BASE="/home/dmlserver/projects/egg_prediction/data/songs"
REMOTE_DEMO="/home/dmlserver/projects/egg_prediction/dml-server/results/demo_responses"
LOCAL_BASE="app/storage/songs"
LOCAL_DEMO="app/storage/demo_responses"

echo "[sync] 시작: $(date)"

mkdir -p "$LOCAL_BASE/meta"
mkdir -p "$LOCAL_BASE/audio/master"
mkdir -p "$LOCAL_BASE/audio/mr"
mkdir -p "$LOCAL_BASE/lrc/parsed"
mkdir -p "$LOCAL_BASE/pitch_guide"
mkdir -p "$LOCAL_DEMO"

# 1. 메타
echo "[sync] 1/5 메타 동기화..."
rsync -avz --delete \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/meta/songs.json" \
  "${LOCAL_BASE}/meta/songs.json"

# 2. Master 음원
echo "[sync] 2/5 master 음원 동기화..."
rsync -avz --delete \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/audio/master/" \
  "${LOCAL_BASE}/audio/master/"

# 3. MR 음원
echo "[sync] 3/5 MR 음원 동기화..."
rsync -avz --delete \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/audio/mr/" \
  "${LOCAL_BASE}/audio/mr/"

# 4. LRC parsed ({id}.json, {id}_aligned.json, {id}_mr.json)
echo "[sync] 4/5 LRC 동기화..."
rsync -avz --delete \
  --include='[0-9][0-9][0-9].json' \
  --include='[0-9][0-9][0-9]_aligned.json' \
  --include='[0-9][0-9][0-9]_mr.json' \
  --exclude='*' \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/lrc/parsed/" \
  "${LOCAL_BASE}/lrc/parsed/"

# 5. pitch_guide ({id}.json + {id}_mr.json, .png 제외)
echo "[sync] 5/5 pitch_guide 동기화..."
rsync -avz --delete \
  --include='[0-9][0-9][0-9].json' \
  --include='[0-9][0-9][0-9]_mr.json' \
  --exclude='*' \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_BASE}/pitch_guide/" \
  "${LOCAL_BASE}/pitch_guide/"

# 6. demo_responses (mock JSON — dml-server/results/demo_responses/)
echo "[sync] 6/6 demo_responses 동기화..."
rsync -avz --delete \
  --include='*.json' \
  --exclude='*' \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DEMO}/" \
  "${LOCAL_DEMO}/"

echo ""
echo "[sync] 완료: $(date)"
echo "[sync] 파일 수:"
echo "  meta:          $(ls $LOCAL_BASE/meta/*.json 2>/dev/null | wc -l) json"
echo "  audio/master:  $(ls $LOCAL_BASE/audio/master/*.mp3 2>/dev/null | wc -l) mp3"
echo "  audio/mr:      $(ls $LOCAL_BASE/audio/mr/*.mp3 2>/dev/null | wc -l) mp3"
echo "  lrc/parsed:    $(ls $LOCAL_BASE/lrc/parsed/*.json 2>/dev/null | wc -l) json"
echo "  pitch_guide:   $(ls $LOCAL_BASE/pitch_guide/*.json 2>/dev/null | wc -l) json"
echo "  (pitch_guide *_mr: $(ls $LOCAL_BASE/pitch_guide/*_mr.json 2>/dev/null | wc -l), lrc *_mr: $(ls $LOCAL_BASE/lrc/parsed/*_mr.json 2>/dev/null | wc -l))"
echo "  demo_responses: $(ls $LOCAL_DEMO/*.json 2>/dev/null | wc -l) json"
echo "[sync] 디스크 사용량: songs=$(du -sh $LOCAL_BASE | cut -f1), demo=$(du -sh $LOCAL_DEMO | cut -f1)"
