"""세션 API – 생성 / 목록 / 상세 조회 / 피치 비교."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models.models import AnalysisRun, Session, SessionFile, User
from app.schemas.schemas import (
    FileInfo,
    LatestAnalysis,
    MetricItem,
    SessionBrief,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetail,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


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
    session = Session(
        user_id=current_user.user_id,
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
        .order_by(Session.created_at.desc())
        .all()
    )

    # TODO: 사용자 증가 시 N+1 쿼리 최적화 필요
    # subquery 또는 join으로 한 번에 가져오는 방식으로 리팩토링
    # 현재는 시연 단계 단순 구현 (세션 수 적음)
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
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        created_at=session.created_at,
        files=files,
        latest_analysis=latest_analysis,
    )
