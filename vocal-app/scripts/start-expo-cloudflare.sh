#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

for p in 8081 8082 19000 19001 19002; do
  PIDS="$(lsof -tiTCP:$p -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null || true
  fi
done

pkill -f "expo" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true

EXPO_PACKAGER_PROXY_URL="https://expo-dev.vocal-fit.com" \
npx expo start --dev-client --clear --port 8081
