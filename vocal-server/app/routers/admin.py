"""관리자용 API – 개발 단계 (인증 불필요)."""

from __future__ import annotations

import base64
import binascii
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, not_, or_
from sqlalchemy.orm import Session as DBSession, joinedload

from app.database import get_db
from app.event_store import get_events
from app.models.models import (
    AnalysisRun,
    Session,
    Song,
    TrainingAttempt,
    TrainingFavorite,
    User,
)
from app.routers.sessions import _build_song_field
from app.schemas.schemas import AdminUserResponse, SessionBrief
from app.state import app_state

router = APIRouter(prefix="/admin", tags=["admin"])

# Phase A-3, A-4에서 사용 예정
templates = Jinja2Templates(directory="app/templates")

# Phase A-5-d: 활동 endpoint 한글 매핑
_ACTIVITY_KR: dict[str, str] = {
    "POST /auth/login": "로그인",
    "POST /auth/signup": "회원가입",
    "POST /sessions": "세션 생성",
    "GET /sessions": "세션 목록 조회",
    "GET /sessions/{id}": "세션 상세 조회",
    "POST /sessions/{id}/files": "파일 업로드",
    "POST /sessions/{id}/analyze": "정식 분석 요청",
    "GET /analysis/{id}": "분석 상태 조회",
    "GET /analysis/{id}/results": "분석 결과 조회",
    "GET /analysis/{id}/comparison": "비교 분석 조회",
    "GET /analysis/{id}/user_f0": "F0 데이터 조회",
    "POST /sessions/{id}/training-analyze": "사후 측정 (TrainingScreen)",
    "GET /songs": "곡 목록 조회",
    "GET /songs/{id}/lrc": "가사 조회",
    "GET /songs/{id}/pitch-guide": "음정 가이드 조회",
    "GET /songs/{id}/mr": "MR 음원 조회",
    "GET /users/me/training-attempts": "누적 시도 조회",
    "GET /users/me/favorites": "즐겨찾기 조회",
    "POST /users/me/favorites": "즐겨찾기 추가",
    "DELETE /users/me/favorites/{id}": "즐겨찾기 제거",
}

# Phase A-5-d: 분석 status 라벨 통일 (DB 값은 그대로, 화면만 한글)
_STATUS_KR: dict[str | None, str] = {
    "success": "완료",
    "completed": "완료",
    "no_voice": "무음",
    "failed": "실패",
    "queued": "대기 중",
    "running": "분석 중",
    "uploading": "업로드 중",
    "uploaded": "업로드 완료",
    "analyzing": "분석 중",
    None: "-",
}


def _format_activity(method_path: str | None) -> str:
    if not method_path:
        return "-"
    return _ACTIVITY_KR.get(method_path, method_path)


def _format_status(s: str | None) -> str:
    return _STATUS_KR.get(s, s or "-")


def _status_badge_class(s: str | None) -> str:
    if s in ("success", "completed"):
        return "bg-success"
    if s == "no_voice":
        return "bg-secondary"
    if s == "failed":
        return "bg-danger"
    if s in ("queued", "running", "uploading", "analyzing"):
        return "bg-warning text-dark"
    return "bg-secondary"


def _relative_time(dt: datetime | None) -> str:
    if dt is None:
        return "사용 안 함"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elapsed = (now - dt).total_seconds()
    if elapsed < 60:
        return "방금"
    if elapsed < 3600:
        return f"{int(elapsed // 60)}분 전"
    if elapsed < 86400:
        return f"{int(elapsed // 3600)}시간 전"
    return f"{int(elapsed // 86400)}일 전"


def _activity_status(dt: datetime | None) -> tuple[str, str]:
    """(라벨, badge class) — 사용 안 함 / 접속 중 / 최근 활동 / 미접속."""
    if dt is None:
        return ("사용 안 함", "bg-secondary")
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elapsed = (now - dt).total_seconds()
    if elapsed < 5 * 60:
        return ("접속 중", "bg-success")
    if elapsed < 30 * 60:
        return ("최근 활동", "bg-warning text-dark")
    return ("미접속", "bg-secondary")


# Phase A-5-c: 9개 평가 항목 한글 매핑 (앱과 동일)
_INDICATOR_KR: dict[str, str] = {
    "1_nasal_oral_ratio": "비강사용",
    "2_chest_head_voice": "흉성두성",
    "3_vocal_fold_contact": "접촉강도",
    "4_breathiness": "호흡식별",
    "5_forward_resonance": "전방공명",
    "6_soft_palate": "연구개위치",
    "7_larynx_tongue_root": "후두설근",
    "8_tongue_tension": "혀경직도",
    "9_pressure_balance": "상압하압",
}

# Phase A-5-b: 테스트 계정 식별 패턴 (이메일 prefix). 운영 계정 추가 시 영향 없음.
# 새 테스트 패턴 생기면 여기에 추가. SQL LIKE 패턴 (% suffix).
_TEST_EMAIL_LIKE_PATTERNS: list[str] = [
    "test_a_%", "test_b_%",          # test_integration.py 사용자A/B
    "hdrtest_%", "tmtest_%",          # test_headers.py, test_timeline.py
    "trtest_%", "trtest2_%",          # test_training.py
    "raw_%",                          # test_training_raw.py
    "p7a_%", "p7b_%",                 # test_phase7.py
    "sigtest_%", "sigtest_back_%",    # signup 토글 단위
    "toggle_test_%", "toggle_status_check%",  # admin 토글 검증
    "signup_check%",                  # signup_toggle.sh 검증
]

_ADMIN_USERS_DEFAULT_LIMIT = 50
_ADMIN_USERS_MAX_LIMIT = 100


def _parse_admin_users_limit(value: str | None) -> int:
    if value is None:
        return _ADMIN_USERS_DEFAULT_LIMIT
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return _ADMIN_USERS_DEFAULT_LIMIT
    if parsed < 1:
        return _ADMIN_USERS_DEFAULT_LIMIT
    return min(parsed, _ADMIN_USERS_MAX_LIMIT)


def _encode_admin_users_cursor(created_at: datetime, user_id: uuid.UUID) -> str:
    payload = {
        "created_at": created_at.isoformat(),
        "user_id": str(user_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_admin_users_cursor(value: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not value:
        return None
    try:
        padded = value + ("=" * (-len(value) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        created_at = datetime.fromisoformat(payload["created_at"])
        user_id = uuid.UUID(payload["user_id"])
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ):
        return None
    return created_at, user_id


# ─────────────────────────────────────────────
# Phase A-2: scaffold
# ─────────────────────────────────────────────
@router.get("", include_in_schema=False)
def admin_root():
    """`/admin` 진입 시 로그인 페이지로 redirect (Phase A-3)."""
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)


@router.get("/health", include_in_schema=False)
def admin_health():
    """Phase A-2 검증용 헬스 체크."""
    return {"admin": "ok"}


# ─────────────────────────────────────────────
# Phase A-3: 비밀번호 인증 + IP rate limit
# - 인증: SessionMiddleware 기반 admin_session 쿠키 (24h)
# - rate limit: 메모리 기반 (단일 인스턴스 한정, 재시작 시 초기화)
# ─────────────────────────────────────────────
_FAIL_LIMIT = 5
_BLOCK_DURATION = timedelta(minutes=5)
_FAIL_WINDOW = timedelta(minutes=5)
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)
_rl_lock = Lock()


def get_client_ip(request: Request) -> str:
    """Cloudflare Tunnel 뒤 → X-Forwarded-For 첫 번째 IP 사용."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> tuple[bool, int | None]:
    with _rl_lock:
        now = datetime.utcnow()
        _failed_attempts[ip] = [t for t in _failed_attempts[ip] if now - t < _FAIL_WINDOW]
        failures = _failed_attempts[ip]
        if len(failures) >= _FAIL_LIMIT:
            unblock_at = failures[-_FAIL_LIMIT] + _BLOCK_DURATION
            if now < unblock_at:
                return True, int((unblock_at - now).total_seconds())
        return False, None


def record_failed_attempt(ip: str) -> None:
    with _rl_lock:
        _failed_attempts[ip].append(datetime.utcnow())


def reset_attempts(ip: str) -> None:
    with _rl_lock:
        _failed_attempts.pop(ip, None)


def require_admin_auth(request: Request):
    """세션 쿠키 기반 admin 인증."""
    if not request.session.get("admin_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"Location": "/admin/login"},
        )


# ─────────────────────────────────────────────
# 로그인 페이지 + 폼 처리 + 로그아웃
# ─────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request, error: str | None = None, retry: int | None = None):
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": error, "retry": retry},
    )


@router.post("/login", include_in_schema=False)
def login_submit(request: Request, password: str = Form(...)):
    client_ip = get_client_ip(request)
    blocked, retry_after = check_rate_limit(client_ip)
    if blocked:
        return RedirectResponse(
            url=f"/admin/login?error=rate_limited&retry={retry_after}",
            status_code=status.HTTP_302_FOUND,
        )

    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise HTTPException(status_code=500, detail="ADMIN_PASSWORD not configured")

    if password != admin_password:
        record_failed_attempt(client_ip)
        return RedirectResponse(
            url="/admin/login?error=invalid_password",
            status_code=status.HTTP_302_FOUND,
        )

    reset_attempts(client_ip)
    request.session["admin_authenticated"] = True
    request.session["admin_logged_in_at"] = datetime.utcnow().isoformat()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.post("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)


# ─────────────────────────────────────────────
# 기존 API
# ─────────────────────────────────────────────
@router.get("/api/users", response_model=list[AdminUserResponse], dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def list_all_users_json(db: DBSession = Depends(get_db)):
    """등록된 모든 사용자 목록 (JSON, dashboard JS용)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/users", response_class=HTMLResponse, dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def list_all_users_page(
    request: Request,
    search: str | None = Query(None, alias="q"),
    show_test: bool = False,
    limit: str | None = None,
    cursor: str | None = None,
    db: DBSession = Depends(get_db),
):
    """사용자 리스트 HTML 페이지 + 토글 카드. show_test=true로 테스트 계정 표시."""
    search_q = (search or "").strip()
    page_limit = _parse_admin_users_limit(limit)
    decoded_cursor = _decode_admin_users_cursor(cursor)

    # 카운트 (N+1 방지: subquery)
    session_count = (
        db.query(Session.user_id, func.count(Session.session_id).label("c"))
        .group_by(Session.user_id).subquery()
    )
    fav_count = (
        db.query(TrainingFavorite.user_id, func.count(TrainingFavorite.favorite_id).label("c"))
        .group_by(TrainingFavorite.user_id).subquery()
    )
    att_count = (
        db.query(TrainingAttempt.user_id, func.count(TrainingAttempt.attempt_id).label("c"))
        .group_by(TrainingAttempt.user_id).subquery()
    )

    test_email_filter = or_(*[User.email.like(p) for p in _TEST_EMAIL_LIKE_PATTERNS])

    # 운영/테스트 분리 카운트
    total_all = db.query(func.count(User.user_id)).scalar() or 0
    test_count = db.query(func.count(User.user_id)).filter(test_email_filter).scalar() or 0
    op_count = total_all - test_count

    users_query = (
        db.query(
            User,
            func.coalesce(session_count.c.c, 0).label("sessions"),
            func.coalesce(fav_count.c.c, 0).label("favorites"),
            func.coalesce(att_count.c.c, 0).label("attempts"),
        )
        .outerjoin(session_count, session_count.c.user_id == User.user_id)
        .outerjoin(fav_count, fav_count.c.user_id == User.user_id)
        .outerjoin(att_count, att_count.c.user_id == User.user_id)
    )
    if not show_test:
        users_query = users_query.filter(not_(test_email_filter))
    if search_q:
        search_like = f"%{search_q}%"
        users_query = users_query.filter(or_(User.nickname.ilike(search_like), User.email.ilike(search_like)))
    if decoded_cursor:
        cursor_created_at, cursor_user_id = decoded_cursor
        users_query = users_query.filter(
            or_(
                User.created_at < cursor_created_at,
                (User.created_at == cursor_created_at) & (User.user_id < cursor_user_id),
            )
        )

    rows = users_query.order_by(User.created_at.desc(), User.user_id.desc()).limit(page_limit + 1).all()
    has_next_page = len(rows) > page_limit
    page_rows = rows[:page_limit]
    next_cursor = None
    if has_next_page and page_rows:
        last_user = page_rows[-1][0]
        next_cursor = _encode_admin_users_cursor(last_user.created_at, last_user.user_id)

    users = []
    online_count = 0
    for (u, s, f, a) in page_rows:
        status_label, status_cls = _activity_status(u.last_seen_at)
        if status_label == "접속 중":
            online_count += 1
        users.append({
            "user_id": u.user_id,
            "email": u.email,
            "nickname": u.nickname,
            "created_at": u.created_at,
            "last_seen_at": u.last_seen_at,
            "last_endpoint": u.last_endpoint,
            "activity_label": status_label,
            "activity_cls": status_cls,
            "relative_time": _relative_time(u.last_seen_at),
            "activity_kr": _format_activity(u.last_endpoint),
            "sessions": int(s),
            "favorites": int(f),
            "attempts": int(a),
        })
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users,
            "shown_users": len(users),
            "total_all": total_all,
            "op_count": op_count,
            "test_count": test_count,
            "online_count": online_count,
            "show_test": show_test,
            "q": search_q,
            "limit": page_limit,
            "next_cursor": next_cursor,
            "next_page_url": (
                "/admin/users?"
                + urlencode(
                    {
                        "q": search_q,
                        "show_test": "true" if show_test else "false",
                        "limit": str(page_limit),
                        "cursor": next_cursor,
                    }
                )
                if next_cursor
                else None
            ),
            "signup_enabled": app_state.signup_enabled,
        },
    )


@router.post("/signup-toggle", dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def toggle_signup(request: Request):
    """admin 페이지에서 호출. 메모리 상태 토글 (재시작 시 .env 값으로 reset)."""
    app_state.signup_enabled = not app_state.signup_enabled
    new_state = app_state.signup_enabled
    logger = __import__("logging").getLogger("uvicorn.error")
    logger.info(f"[admin] signup_enabled toggled to {new_state} by ip={get_client_ip(request)}")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.get("/users/{user_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def get_user_detail(
    user_id: uuid.UUID,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """사용자 상세 페이지 — 분석 세션, 즐겨찾기, 누적 시도 통합 표시."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    session_count = db.query(func.count(Session.session_id)).filter(Session.user_id == user_id).scalar() or 0
    favorite_count = db.query(func.count(TrainingFavorite.favorite_id)).filter(TrainingFavorite.user_id == user_id).scalar() or 0
    attempt_count = db.query(func.count(TrainingAttempt.attempt_id)).filter(TrainingAttempt.user_id == user_id).scalar() or 0

    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .options(joinedload(Session.song))
        .order_by(Session.created_at.desc())
        .limit(50).all()
    )
    favorites = (
        db.query(TrainingFavorite)
        .filter(TrainingFavorite.user_id == user_id)
        .order_by(TrainingFavorite.created_at.desc())
        .all()
    )
    # TrainingFavorite.song relationship 없음 → song_id로 dict 매핑
    fav_song_ids = list({f.song_id for f in favorites})
    fav_songs = {s.id: s for s in db.query(Song).filter(Song.id.in_(fav_song_ids)).all()} if fav_song_ids else {}

    attempts_raw = (
        db.query(TrainingAttempt)
        .filter(TrainingAttempt.user_id == user_id)
        .order_by(TrainingAttempt.attempted_at.desc())
        .limit(100).all()
    )
    attempts = []
    for a in attempts_raw:
        improvement = (
            a.after_ai_score - a.before_ai_score
            if a.before_ai_score is not None and a.after_ai_score is not None
            else None
        )
        attempts.append({
            "attempted_at": a.attempted_at,
            "chunk_start_sec": a.chunk_start_sec,
            "chunk_end_sec": a.chunk_end_sec,
            "indicator_key": a.indicator_key,
            "before_ai_score": a.before_ai_score,
            "after_ai_score": a.after_ai_score,
            "improvement": improvement,
        })

    activity_label, activity_cls = _activity_status(user.last_seen_at)

    # 세션 status 한글 + badge class를 미리 계산해서 템플릿에 전달
    sessions_view = [
        {
            "session_id": s.session_id,
            "created_at": s.created_at,
            "song": s.song,
            "song_title": s.song_title,
            "status_raw": s.status,
            "status_label": _format_status(s.status),
            "status_cls": _status_badge_class(s.status),
        }
        for s in sessions
    ]

    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "user": user,
            "session_count": session_count,
            "favorite_count": favorite_count,
            "attempt_count": attempt_count,
            "sessions": sessions_view,
            "favorites": favorites,
            "fav_songs": fav_songs,
            "attempts": attempts,
            "indicator_kr": _INDICATOR_KR,
            "activity_label": activity_label,
            "activity_cls": activity_cls,
            "relative_time": _relative_time(user.last_seen_at),
            "activity_kr": _format_activity(user.last_endpoint),
        },
    )


@router.get("/users/{user_id}/sessions", response_model=list[SessionBrief], dependencies=[Depends(require_admin_auth)])
def list_user_sessions(user_id: uuid.UUID, db: DBSession = Depends(get_db)):
    """특정 사용자의 모든 세션 목록을 최신순으로 반환합니다."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        latest_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.session_id == s.session_id)
            .order_by(AnalysisRun.requested_at.desc())
            .first()
        )
        if latest_run is None:
            analysis_status = "no_analysis"
        elif latest_run.status in ("queued", "running"):
            analysis_status = latest_run.status
        elif latest_run.status in ("completed", "success"):
            analysis_status = "completed"
        else:
            analysis_status = "failed"

        result.append(SessionBrief(
            session_id=s.session_id,
            song_title=s.song_title,
            song=_build_song_field(s),
            status=s.status,
            analysis_status=analysis_status,
            started_at=s.started_at,
            created_at=s.created_at,
        ))
    return result


# ─────────────────────────────────────────────
# 이벤트 API (폴링)
# ─────────────────────────────────────────────
@router.get("/events", dependencies=[Depends(require_admin_auth)])
def list_events():
    """최근 이벤트 리스트를 JSON으로 반환합니다 (기존 호환성)."""
    return get_events()


# ─────────────────────────────────────────────
# Phase A-5-e: 폴링 기반 실시간 로그 (SSE 폐기)
# ─────────────────────────────────────────────
@router.get("/logs", response_class=HTMLResponse, dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def logs_page(request: Request):
    """실시간 로그 페이지 (5초 폴링)."""
    return templates.TemplateResponse("admin/logs.html", {"request": request})


@router.get("/api/events", dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def api_events(limit: int = 100, since: str | None = None):
    """이벤트 리스트. since(ISO datetime) 이후만 + limit 제한."""
    limit = max(1, min(limit, 500))
    events = get_events()  # 이미 최신순 (deque appendleft)
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            events = [e for e in events if datetime.fromisoformat(e["timestamp"]) > since_dt]
        except (ValueError, TypeError):
            pass  # 잘못된 since는 무시
    return {
        "events": events[:limit],
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/online-users", dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def api_online_users(db: DBSession = Depends(get_db)):
    """5분 이내 활동한 사용자 목록 (현재 접속 중)."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    users = (
        db.query(User)
        .filter(User.last_seen_at >= threshold)
        .order_by(User.last_seen_at.desc())
        .all()
    )
    return {
        "users": [
            {
                "user_id": str(u.user_id),
                "nickname": u.nickname,
                "email": u.email,
                "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
                "last_endpoint": u.last_endpoint,
                "activity_kr": _format_activity(u.last_endpoint),
                "relative_time": _relative_time(u.last_seen_at),
            }
            for u in users
        ],
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────
# SSE 스트림
# ─────────────────────────────────────────────
@router.get("/events/stream", dependencies=[Depends(require_admin_auth)], include_in_schema=False)
def event_stream_deprecated():
    """SSE 폐기 (Phase A-5-e). Cloudflare Tunnel(QUIC)에서 long-lived connection 끊김.
    `/admin/logs` 페이지(5초 폴링)로 대체."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="SSE deprecated. Use /admin/logs (polling) instead.",
    )


# ─────────────────────────────────────────────
# 대시보드 HTML
# ─────────────────────────────────────────────
_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vocal Server – Admin Dashboard</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:20px}
  h1{text-align:center;margin-bottom:24px;font-size:1.5rem;color:#a0c4ff}
  .summary{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}
  .card{flex:1;min-width:180px;background:#16213e;border-radius:12px;padding:20px;text-align:center}
  .card .value{font-size:2rem;font-weight:700;color:#fff}
  .card .label{font-size:.85rem;color:#8899aa;margin-top:4px}
  .section{background:#16213e;border-radius:12px;padding:20px;margin-bottom:24px;overflow:hidden}
  .section h2{font-size:1.1rem;color:#a0c4ff;margin-bottom:12px}
  #log-list{list-style:none;max-height:320px;overflow-y:auto}
  #log-list li{padding:8px 12px;border-bottom:1px solid #1a1a2e;font-size:.9rem;display:flex;gap:10px;align-items:center}
  #log-list li:last-child{border-bottom:none}
  .badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:600;white-space:nowrap}
  .badge.signup{background:#064e3b;color:#6ee7b7}
  .badge.login{background:#1e3a5f;color:#93c5fd}
  .time{color:#6b7b8d;font-size:.8rem;min-width:70px}
  .empty{color:#6b7b8d;font-style:italic;padding:16px 0}
  table{width:100%;border-collapse:collapse}
  th,td{text-align:left;padding:10px 12px;font-size:.9rem}
  th{color:#8899aa;font-weight:600;border-bottom:2px solid #1a1a2e}
  td{border-bottom:1px solid #1a1a2e}
  tr:hover td{background:#1a1a2e}
  ::-webkit-scrollbar{width:6px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}
  .status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
  .status-dot.connected{background:#6ee7b7}
  .status-dot.disconnected{background:#f87171}
  #sse-status{font-size:.8rem;color:#6b7b8d;text-align:right;margin-bottom:8px}
  @media(max-width:640px){body{padding:12px}.summary{flex-direction:column}.card .value{font-size:1.5rem}}
</style>
</head>
<body>
<h1>Vocal Server Dashboard</h1>
<div class="summary">
  <div class="card"><div class="value" id="total-users">-</div><div class="label">총 가입자</div></div>
  <div class="card"><div class="value" id="today-logins">-</div><div class="label">오늘 로그인</div></div>
  <div class="card"><div class="value" id="last-login" style="font-size:1rem">-</div><div class="label">최근 로그인</div></div>
</div>
<div class="section">
  <div id="sse-status"><span class="status-dot disconnected" id="sse-dot"></span>연결 중…</div>
  <h2>실시간 활동 로그</h2>
  <ul id="log-list"><li class="empty">이벤트 대기 중…</li></ul>
</div>
<div class="section">
  <h2>등록된 사용자</h2>
  <table>
    <thead><tr><th>닉네임</th><th>이메일</th><th>가입일시</th></tr></thead>
    <tbody id="user-tbody"><tr><td colspan="3" class="empty">로딩 중…</td></tr></tbody>
  </table>
</div>
<script>
const logList=document.getElementById('log-list'),userTbody=document.getElementById('user-tbody');
const totalEl=document.getElementById('total-users'),todayEl=document.getElementById('today-logins');
const lastEl=document.getElementById('last-login'),sseDot=document.getElementById('sse-dot');
const sseStatus=document.getElementById('sse-status'),MAX_LOG=50;
function fmtTime(i){return new Date(i).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})}
function fmtDate(i){return new Date(i).toLocaleDateString('ko-KR')+' '+fmtTime(i)}
function isToday(i){const d=new Date(i),n=new Date();return d.getFullYear()===n.getFullYear()&&d.getMonth()===n.getMonth()&&d.getDate()===n.getDate()}
function renderLogItem(ev){
  const li=document.createElement('li');
  const icon=ev.event_type==='signup'?'🆕':'🔑';
  const label=ev.event_type==='signup'?'회원가입':'로그인';
  li.innerHTML='<span class="time">'+fmtTime(ev.timestamp)+'</span><span class="badge '+ev.event_type+'">'+icon+' '+label+'</span><span>'+ev.nickname+' ('+ev.email+')</span>';
  return li;
}
async function loadInitialEvents(){
  try{const r=await fetch('/admin/events'),events=await r.json();if(!events.length)return;
  logList.innerHTML='';events.forEach(ev=>logList.appendChild(renderLogItem(ev)));updateStats(events)}catch(e){console.error(e)}
}
function updateStats(events){
  todayEl.textContent=events.filter(e=>e.event_type==='login'&&isToday(e.timestamp)).length;
  const ll=events.find(e=>e.event_type==='login');lastEl.textContent=ll?ll.nickname:'-';
}
function connectSSE(){
  const es=new EventSource('/admin/events/stream');
  es.onopen=()=>{sseDot.className='status-dot connected';sseStatus.innerHTML='<span class="status-dot connected"></span>실시간 연결됨'};
  es.onmessage=(msg)=>{
    const ev=JSON.parse(msg.data);
    if(logList.querySelector('.empty'))logList.innerHTML='';
    logList.prepend(renderLogItem(ev));
    while(logList.children.length>MAX_LOG)logList.lastChild.remove();
    fetch('/admin/events').then(r=>r.json()).then(updateStats).catch(()=>{});
    if(ev.event_type==='signup')loadUsers();
  };
  es.onerror=()=>{sseDot.className='status-dot disconnected';sseStatus.innerHTML='<span class="status-dot disconnected"></span>연결 끊김 – 재연결 중…'};
}
async function loadUsers(){
  try{const r=await fetch('/admin/api/users'),users=await r.json();totalEl.textContent=users.length;
  if(!users.length){userTbody.innerHTML='<tr><td colspan="3" class="empty">등록된 사용자 없음</td></tr>';return}
  userTbody.innerHTML=users.map(u=>'<tr><td>'+u.nickname+'</td><td>'+u.email+'</td><td>'+fmtDate(u.created_at)+'</td></tr>').join('')}catch(e){console.error(e)}
}
loadUsers();loadInitialEvents();connectSSE();
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_admin_auth)])
def dashboard():
    """관리자 대시보드 HTML 페이지를 반환합니다."""
    return HTMLResponse(content=_DASHBOARD_HTML)
