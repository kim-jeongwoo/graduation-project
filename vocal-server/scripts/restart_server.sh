#!/bin/bash
# vocal-server 안전 재시작 (graceful shutdown + 기동 대기)
# 실행: bash scripts/restart_server.sh
# 위치: vocal-server/vocal-server/

set -e

PROJECT_DIR="/Users/kimjeongwoo/vocal-server/vocal-server"
VENV_BIN="/Users/kimjeongwoo/vocal-server/vocalserver/bin"
LOG_FILE="/tmp/uvicorn_new.log"

cd "$PROJECT_DIR"

echo "[restart] graceful shutdown (SIGTERM)..."
pkill -TERM -f "uvicorn app.main" 2>/dev/null || true

# 최대 10초까지 종료 대기
for i in $(seq 1 10); do
  if ! pgrep -f "uvicorn app.main" > /dev/null; then
    echo "[restart] 종료 완료 (${i}s)"
    break
  fi
  sleep 1
done

# 안 죽으면 강제 종료
pkill -9 -f "uvicorn app.main" 2>/dev/null || true
sleep 1

echo "[restart] 새 프로세스 시작..."
nohup "$VENV_BIN/uvicorn" app.main:app --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "[restart] PID: $NEW_PID"

echo "[restart] 기동 대기..."
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/health -m 2 || echo "000")
  if [ "$code" = "200" ]; then
    echo "[restart] 기동 완료 (${i}s, /admin/health 200)"
    exit 0
  fi
  sleep 1
done

echo "[restart] ERROR: 30초 안에 기동 실패. 로그 확인:"
tail -20 "$LOG_FILE"
exit 1
