"""관리자용 API – 개발 단계 (인증 불필요)."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession
from starlette.responses import StreamingResponse

from sqlalchemy import func

from app.database import get_db
from app.event_store import get_events, subscribe, unsubscribe
from app.models.models import (
    AnalysisRun,
    Session,
    TrainingAttempt,
    TrainingFavorite,
    User,
)
from app.schemas.schemas import AdminUserResponse, SessionBrief
from app.state import app_state

router = APIRouter(prefix="/admin", tags=["admin"])

# Phase A-3, A-4에서 사용 예정
templates = Jinja2Templates(directory="app/templates")


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
def list_all_users_page(request: Request, db: DBSession = Depends(get_db)):
    """사용자 리스트 HTML 페이지 + 토글 카드."""
    # User + 카운트 (N+1 방지: subquery)
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
    rows = (
        db.query(
            User,
            func.coalesce(session_count.c.c, 0).label("sessions"),
            func.coalesce(fav_count.c.c, 0).label("favorites"),
            func.coalesce(att_count.c.c, 0).label("attempts"),
        )
        .outerjoin(session_count, session_count.c.user_id == User.user_id)
        .outerjoin(fav_count, fav_count.c.user_id == User.user_id)
        .outerjoin(att_count, att_count.c.user_id == User.user_id)
        .order_by(User.created_at.desc())
        .all()
    )
    users = [
        {
            "user_id": u.user_id,
            "email": u.email,
            "nickname": u.nickname,
            "created_at": u.created_at,
            "sessions": int(s),
            "favorites": int(f),
            "attempts": int(a),
        }
        for (u, s, f, a) in rows
    ]
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users,
            "total_users": len(users),
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
    return sessions


# ─────────────────────────────────────────────
# 이벤트 API (폴링)
# ─────────────────────────────────────────────
@router.get("/events", dependencies=[Depends(require_admin_auth)])
def list_events():
    """최근 이벤트 리스트를 JSON으로 반환합니다."""
    return get_events()


# ─────────────────────────────────────────────
# SSE 스트림
# ─────────────────────────────────────────────
@router.get("/events/stream", dependencies=[Depends(require_admin_auth)])
async def event_stream(request: Request):
    """SSE 스트림 – 실시간 이벤트를 푸시합니다."""
    queue = subscribe()

    async def _generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(queue)

    return StreamingResponse(_generate(), media_type="text/event-stream")


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
