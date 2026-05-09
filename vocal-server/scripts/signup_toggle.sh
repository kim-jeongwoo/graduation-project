#!/bin/bash
# SIGNUP_ENABLED 토글 (.env 수정 + 서버 재시작 + 검증)
# 실행: bash scripts/signup_toggle.sh on|off
# 위치: vocal-server/vocal-server/

set -e

ACTION="${1:-}"
if [ "$ACTION" != "on" ] && [ "$ACTION" != "off" ]; then
  echo "사용법: bash scripts/signup_toggle.sh on|off"
  exit 1
fi

ENV_FILE="/Users/kimjeongwoo/vocal-server/.env"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$ACTION" = "on" ]; then
  NEW_VALUE="true"
  EXPECTED_CODES="201 400"  # 201 신규 또는 400 이미 존재
else
  NEW_VALUE="false"
  EXPECTED_CODES="403"
fi

echo "[toggle] SIGNUP_ENABLED=$NEW_VALUE 적용..."
if grep -q "^SIGNUP_ENABLED=" "$ENV_FILE"; then
  sed -i.bak "s|^SIGNUP_ENABLED=.*|SIGNUP_ENABLED=$NEW_VALUE|" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
else
  echo "SIGNUP_ENABLED=$NEW_VALUE" >> "$ENV_FILE"
fi

echo "[toggle] 서버 재시작..."
bash "$SCRIPT_DIR/restart_server.sh"

# 검증 이메일: test.com 도메인 사용 (EmailValidator가 .local TLD 거부)
# 가입 후 admin에서 정리 가능. 비밀번호 짧아 422 안 뜨도록 8자 이상.
echo "[toggle] 검증 (POST /auth/signup, signup_check@test.com 사용)..."
CODE=$(curl -s -o /tmp/signup_check.json -w "%{http_code}" \
  -X POST https://api.vocal-fit.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"signup_check@test.com","password":"check1234","nickname":"check"}')

echo "  HTTP: $CODE"
echo "  body: $(cat /tmp/signup_check.json)"

case " $EXPECTED_CODES " in
  *" $CODE "*)
    echo "[toggle] OK — SIGNUP_ENABLED=$NEW_VALUE 정상 적용"
    exit 0
    ;;
  *)
    echo "[toggle] FAIL — 기대: $EXPECTED_CODES, 실제: $CODE"
    exit 1
    ;;
esac
