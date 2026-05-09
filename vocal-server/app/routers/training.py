"""Phase 7 — TrainingScreen 누적 시도 + 즐겨찾기 API."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models.models import (
    AnalysisRun,
    Session,
    Song,
    TrainingAttempt,
    TrainingFavorite,
    User,
)

router = APIRouter(prefix="/users/me", tags=["training"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class AttemptItem(BaseModel):
    attempt_id: uuid.UUID
    session_id: Optional[uuid.UUID]
    original_run_id: Optional[uuid.UUID]
    chunk_index: int
    chunk_start_sec: float
    chunk_end_sec: float
    indicator_key: str
    before_ai_score: Optional[float]
    before_rounded_score: Optional[int]
    before_zone: Optional[str]
    after_ai_score: float
    after_rounded_score: int
    after_zone: str
    improvement: Optional[float]
    attempted_at: datetime


class AttemptListResponse(BaseModel):
    items: list[AttemptItem]
    next_cursor: Optional[str]
    has_more: bool


class FavoriteItem(BaseModel):
    favorite_id: uuid.UUID
    song_id: str
    song_title: str
    song_artist: str
    original_run_id: Optional[uuid.UUID]
    chunk_index: int
    chunk_start_sec: float
    chunk_end_sec: float
    chunk_lrc_text: Optional[str]
    indicator_key: str
    created_at: datetime


class FavoriteListResponse(BaseModel):
    items: list[FavoriteItem]


class FavoriteCreateRequest(BaseModel):
    original_run_id: uuid.UUID
    chunk_index: int
    indicator_key: str


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _encode_cursor(attempted_at: datetime, attempt_id: uuid.UUID) -> str:
    raw = f"{attempted_at.isoformat()}|{attempt_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
    ts_str, aid_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), uuid.UUID(aid_str)


def _attempt_to_item(a: TrainingAttempt) -> AttemptItem:
    improvement = (
        a.after_ai_score - a.before_ai_score
        if a.before_ai_score is not None
        else None
    )
    return AttemptItem(
        attempt_id=a.attempt_id,
        session_id=a.session_id,
        original_run_id=a.original_run_id,
        chunk_index=a.chunk_index,
        chunk_start_sec=a.chunk_start_sec,
        chunk_end_sec=a.chunk_end_sec,
        indicator_key=a.indicator_key,
        before_ai_score=a.before_ai_score,
        before_rounded_score=a.before_rounded_score,
        before_zone=a.before_zone,
        after_ai_score=a.after_ai_score,
        after_rounded_score=a.after_rounded_score,
        after_zone=a.after_zone,
        improvement=improvement,
        attempted_at=a.attempted_at,
    )


def _favorite_to_item(f: TrainingFavorite, song: Song) -> FavoriteItem:
    return FavoriteItem(
        favorite_id=f.favorite_id,
        song_id=f.song_id,
        song_title=song.title,
        song_artist=song.artist,
        original_run_id=f.original_run_id,
        chunk_index=f.chunk_index,
        chunk_start_sec=f.chunk_start_sec,
        chunk_end_sec=f.chunk_end_sec,
        chunk_lrc_text=f.chunk_lrc_text,
        indicator_key=f.indicator_key,
        created_at=f.created_at,
    )


# ─────────────────────────────────────────────
# GET /users/me/training-attempts
# ─────────────────────────────────────────────
@router.get(
    "/training-attempts",
    response_model=AttemptListResponse,
    summary="누적 시도 기록 조회",
)
def list_training_attempts(
    indicator_key: Optional[str] = Query(None),
    song_id: Optional[str] = Query(None),
    original_run_id: Optional[uuid.UUID] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    q = db.query(TrainingAttempt).filter(TrainingAttempt.user_id == current_user.user_id)

    if indicator_key:
        q = q.filter(TrainingAttempt.indicator_key == indicator_key)
    if original_run_id:
        q = q.filter(TrainingAttempt.original_run_id == original_run_id)
    if song_id:
        # song_id로 필터링 — original_run → session → song_id JOIN
        q = (
            q.join(AnalysisRun, AnalysisRun.run_id == TrainingAttempt.original_run_id)
             .join(Session, Session.session_id == AnalysisRun.session_id)
             .filter(Session.song_id == song_id)
        )

    if cursor:
        try:
            ts, aid = _decode_cursor(cursor)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 cursor")
        # attempted_at DESC, attempt_id DESC 기준 다음 페이지
        q = q.filter(
            (TrainingAttempt.attempted_at < ts)
            | ((TrainingAttempt.attempted_at == ts) & (TrainingAttempt.attempt_id < aid))
        )

    rows = q.order_by(TrainingAttempt.attempted_at.desc(), TrainingAttempt.attempt_id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.attempted_at, last.attempt_id)

    return AttemptListResponse(
        items=[_attempt_to_item(a) for a in rows],
        next_cursor=next_cursor,
        has_more=has_more,
    )


# ─────────────────────────────────────────────
# GET /users/me/favorites
# ─────────────────────────────────────────────
@router.get(
    "/favorites",
    response_model=FavoriteListResponse,
    summary="즐겨찾기 목록 조회",
)
def list_favorites(
    indicator_key: Optional[str] = Query(None),
    song_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    q = db.query(TrainingFavorite).filter(TrainingFavorite.user_id == current_user.user_id)
    if indicator_key:
        q = q.filter(TrainingFavorite.indicator_key == indicator_key)
    if song_id:
        q = q.filter(TrainingFavorite.song_id == song_id)
    favorites = q.order_by(TrainingFavorite.created_at.desc()).all()

    # song join
    song_ids = list({f.song_id for f in favorites})
    songs = {s.id: s for s in db.query(Song).filter(Song.id.in_(song_ids)).all()} if song_ids else {}
    items = [_favorite_to_item(f, songs[f.song_id]) for f in favorites if f.song_id in songs]
    return FavoriteListResponse(items=items)


# ─────────────────────────────────────────────
# POST /users/me/favorites
# ─────────────────────────────────────────────
@router.post(
    "/favorites",
    response_model=FavoriteItem,
    status_code=status.HTTP_201_CREATED,
    summary="즐겨찾기 추가",
)
def create_favorite(
    body: FavoriteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == body.original_run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 실행을 찾을 수 없습니다.")
    session_obj = db.query(Session).filter(Session.session_id == run.session_id).first()
    if not session_obj or session_obj.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
    if not session_obj.song_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="자유녹음 세션은 즐겨찾기 불가")

    timeline_scores = (run.result_json or {}).get("timeline_scores") or []
    if not (0 <= body.chunk_index < len(timeline_scores)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="chunk_index 범위 초과")
    target = timeline_scores[body.chunk_index] or {}
    chunk_start = target.get("start_sec") or target.get("chunk_start_sec") or 0.0
    chunk_end = target.get("end_sec") or target.get("chunk_end_sec") or 0.0
    chunk_lrc = target.get("lrc_text") or target.get("text")

    fav = TrainingFavorite(
        user_id=current_user.user_id,
        song_id=session_obj.song_id,
        original_run_id=run.run_id,
        chunk_index=body.chunk_index,
        chunk_start_sec=float(chunk_start),
        chunk_end_sec=float(chunk_end),
        chunk_lrc_text=chunk_lrc,
        indicator_key=body.indicator_key,
    )
    db.add(fav)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(TrainingFavorite)
            .filter(
                TrainingFavorite.user_id == current_user.user_id,
                TrainingFavorite.song_id == session_obj.song_id,
                TrainingFavorite.chunk_index == body.chunk_index,
                TrainingFavorite.indicator_key == body.indicator_key,
            )
            .first()
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "already_favorited",
                "existing_favorite_id": str(existing.favorite_id) if existing else None,
            },
        )
    db.refresh(fav)
    song = db.query(Song).filter(Song.id == fav.song_id).first()
    return _favorite_to_item(fav, song)


# ─────────────────────────────────────────────
# DELETE /users/me/favorites/{favorite_id}
# ─────────────────────────────────────────────
@router.delete(
    "/favorites/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="즐겨찾기 삭제",
)
def delete_favorite(
    favorite_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    fav = db.query(TrainingFavorite).filter(TrainingFavorite.favorite_id == favorite_id).first()
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="즐겨찾기를 찾을 수 없습니다.")
    if fav.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
    db.delete(fav)
    db.commit()
    return None
