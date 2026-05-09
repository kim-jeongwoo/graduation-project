"""관리자용 API – 개발 단계 (인증 불필요)."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession
from starlette.responses import StreamingResponse

from app.database import get_db
from app.event_store import get_events, subscribe, unsubscribe
from app.models.models import Session, User
from app.schemas.schemas import AdminUserResponse, SessionBrief

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
# 기존 API
# ─────────────────────────────────────────────
@router.get("/users", response_model=list[AdminUserResponse])
def list_all_users(db: DBSession = Depends(get_db)):
    """등록된 모든 사용자 목록을 최신순으로 반환합니다."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/users/{user_id}/sessions", response_model=list[SessionBrief])
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
@router.get("/events")
def list_events():
    """최근 이벤트 리스트를 JSON으로 반환합니다."""
    return get_events()


# ─────────────────────────────────────────────
# SSE 스트림
# ─────────────────────────────────────────────
@router.get("/events/stream")
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
  try{const r=await fetch('/admin/users'),users=await r.json();totalEl.textContent=users.length;
  if(!users.length){userTbody.innerHTML='<tr><td colspan="3" class="empty">등록된 사용자 없음</td></tr>';return}
  userTbody.innerHTML=users.map(u=>'<tr><td>'+u.nickname+'</td><td>'+u.email+'</td><td>'+fmtDate(u.created_at)+'</td></tr>').join('')}catch(e){console.error(e)}
}
loadUsers();loadInitialEvents();connectSSE();
</script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """관리자 대시보드 HTML 페이지를 반환합니다."""
    return HTMLResponse(content=_DASHBOARD_HTML)
