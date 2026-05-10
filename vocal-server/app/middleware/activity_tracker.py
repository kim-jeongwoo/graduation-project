"""Phase A-5-d 사용자 활동 추적 미들웨어.

- 인증된 일반 사용자 요청만 추적 (admin/health/docs/openapi/static 제외)
- 5분 throttle: 같은 user + 같은 endpoint면 DB UPDATE 스킵 (메모리 캐시)
- best-effort: 모든 추적 로직 try/except, 실패해도 응답에 영향 없음
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import ALGORITHM, SECRET_KEY
from app.database import SessionLocal
from app.models.models import User

logger = logging.getLogger("uvicorn.error")

_THROTTLE_WINDOW = timedelta(minutes=5)
_EXCLUDE_PREFIXES = ("/admin", "/health", "/docs", "/openapi.json", "/redoc", "/static")

# UUID + 16자리 hex (run_id) 정규화 → "{id}"
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_HEX_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
# /songs/{song_id} 같은 3자리 숫자도 정규화 (LRC, pitch-guide, mr 경로)
_SONG_ID_RE = re.compile(r"/songs/\d{3}")

# 활동 캐시 (단일 인스턴스 한정, 재시작 시 초기화)
_last_activity: dict[str, tuple[datetime, str]] = {}
_cache_lock = Lock()


def _normalize_path(path: str) -> str:
    """경로의 가변 부분(UUID, hex id, song id)을 {id}로 통일."""
    p = _UUID_RE.sub("{id}", path)
    p = _HEX_RE.sub("{id}", p)
    p = _SONG_ID_RE.sub("/songs/{id}", p)
    return p


def _should_track(path: str) -> bool:
    return not any(path.startswith(prefix) for prefix in _EXCLUDE_PREFIXES)


def _extract_user_id(auth_header: str | None) -> uuid.UUID | None:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return uuid.UUID(sub) if sub else None
    except (JWTError, ValueError, TypeError):
        return None


class ActivityTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        try:
            self._track(request)
        except Exception as exc:
            logger.warning(f"[activity_tracker] failed: {exc}")
        return response

    def _track(self, request: Request) -> None:
        path = request.url.path
        if not _should_track(path):
            return
        user_id = _extract_user_id(request.headers.get("authorization"))
        if user_id is None:
            return
        normalized = f"{request.method} {_normalize_path(path)}"
        now = datetime.now(timezone.utc)

        # throttle: 같은 user + 같은 endpoint, 5분 이내면 skip
        cache_key = str(user_id)
        with _cache_lock:
            last = _last_activity.get(cache_key)
            if last and last[1] == normalized and now - last[0] < _THROTTLE_WINDOW:
                return
            _last_activity[cache_key] = (now, normalized)

        # DB UPDATE (별도 세션, try/finally close)
        db = SessionLocal()
        try:
            db.query(User).filter(User.user_id == user_id).update(
                {"last_seen_at": now, "last_endpoint": normalized},
                synchronize_session=False,
            )
            db.commit()
        finally:
            db.close()
