"""세션 API – 생성 / 목록 / 상세 조회 / 피치 비교 / 훈련 청크 분석."""

import json as _json
import logging
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession, selectinload

from app.config import MODEL_SERVER_URL
from app.database import get_db
from app.deps import get_current_user
from app.models.models import AnalysisRun, Session, SessionFile, Song, User
from app.schemas.schemas import (
    FileInfo,
    LatestAnalysis,
    MetricItem,
    SessionBrief,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetail,
    SongInSession,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/sessions", tags=["sessions"])

_TRAINING_TIMEOUT = 10.0


def _build_song_field(session_obj) -> SongInSession | None:
    if session_obj.song is not None:
        s = session_obj.song
        return SongInSession(id=s.id, artist=s.artist, title=s.title)
    if session_obj.song_title is not None:
        return SongInSession(id=None, artist=None, title=session_obj.song_title)
    return None


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="세션 생성",
    description="분석 세션을 생성합니다. 파일 업로드 전에 먼저 호출하세요.",
)
def create_session(
    body: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if body.song_id is not None:
        song = db.query(Song).filter(Song.id == body.song_id).first()
        if not song:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="존재하지 않는 곡입니다.")

    session = Session(
        user_id=current_user.user_id,
        song_id=body.song_id,
        song_title=body.song_title,
        status="uploading",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
    )


@router.get(
    "",
    response_model=list[SessionBrief],
    summary="내 세션 목록 조회",
    description="로그인한 사용자의 세션 목록을 최신순으로 반환합니다. 각 세션에 analysis_status가 포함됩니다. result_json은 포함되지 않으므로 상세 결과는 GET /sessions/{id}를 사용하세요.",
)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    sessions = (
        db.query(Session)
        .filter(Session.user_id == current_user.user_id)
        .options(selectinload(Session.song))
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


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="세션 상세 조회",
    description="세션 정보, 업로드된 파일 목록, 가장 최근 분석 결과(latest_analysis)를 반환합니다. latest_analysis.result_json에 scores 9개, feedback 9개가 포함됩니다.",
)
def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    files = [FileInfo.model_validate(f) for f in session.files]

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.session_id == session.session_id)
        .order_by(AnalysisRun.requested_at.desc())
        .first()
    )
    latest_analysis: LatestAnalysis | None = None
    if latest_run is not None:
        metrics = [
            MetricItem(key=r.metric_key, value=r.metric_value, unit=r.unit)
            for r in latest_run.results
        ]
        latest_analysis = LatestAnalysis(
            run_id=latest_run.run_id,
            status=latest_run.status,
            requested_at=latest_run.requested_at,
            finished_at=latest_run.finished_at,
            result_json=latest_run.result_json,
            metrics=metrics,
        )

    return SessionDetail(
        session_id=session.session_id,
        user_id=session.user_id,
        song_title=session.song_title,
        song=_build_song_field(session),
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        created_at=session.created_at,
        files=files,
        latest_analysis=latest_analysis,
    )


@router.post(
    "/{session_id}/training-analyze",
    summary="훈련 청크 사후 측정 (휘발)",
    description="TrainingScreen 사후 측정용 chunk 분석. DB 저장 없이 dml-server /analyze-chunk 호출 결과를 그대로 전달합니다.",
)
def training_analyze(
    session_id: uuid.UUID,
    audio: UploadFile = File(...),
    chunk_meta: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    # chunk_meta echo용 파싱 (실패 시 None)
    parsed_meta: dict | None = None
    if chunk_meta:
        try:
            parsed_meta = _json.loads(chunk_meta)
        except Exception:
            parsed_meta = None

    audio_bytes = audio.file.read()
    # dml-server /analyze-chunk는 필드명 'file' 기대 (vocal-server는 클라이언트와의 일관성을 위해 'audio')
    files_payload = {"file": (audio.filename or "chunk.wav", audio_bytes, "audio/wav")}
    data_payload: dict = {}
    if chunk_meta:
        data_payload["chunk_meta"] = chunk_meta

    try:
        r = httpx.post(
            f"{MODEL_SERVER_URL}/analyze-chunk",
            files=files_payload,
            data=data_payload,
            timeout=_TRAINING_TIMEOUT,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="분석 서버 응답 시간 초과")
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="분석 서버에 연결할 수 없음")

    if r.status_code == 400:
        try:
            err = r.json()
            detail = err.get("detail", err)
        except Exception:
            detail = r.text[:500]
        raise HTTPException(status_code=400, detail=detail)

    if r.status_code >= 500:
        raise HTTPException(status_code=502, detail="분석 서버 오류")

    if not r.is_success:
        raise HTTPException(status_code=502, detail=f"분석 서버 비정상 응답: HTTP {r.status_code}")

    try:
        body = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="분석 서버 응답 파싱 실패")

    logger.info(f"[training-analyze] session_id={session_id}, status={body.get('status')}")

    return {
        "session_id": str(session_id),
        "status": body.get("status"),
        "scores": body.get("scores"),
        "chunk_meta": parsed_meta,
    }
