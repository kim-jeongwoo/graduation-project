"""분석 API – 분석 실행 / 결과 조회 / 기준 비교."""

import math
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models.models import AnalysisRun, ReferenceMetric, ReferenceProfile, Session, User
from app.schemas.schemas import (
    AnalysisResultsResponse,
    AnalysisRunDetail,
    AnalyzeResponse,
    ComparisonItem,
    ComparisonResponse,
    MetricItem,
)
from app.services.analysis_service import run_analysis_by_ids

router = APIRouter(tags=["analysis"])


# ──── POST /sessions/{session_id}/analyze ────
@router.post(
    "/sessions/{session_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="AI 분석 요청",
    description="업로드된 오디오의 AI 분석을 비동기로 시작합니다. 즉시 run_id/status를 반환하며 결과는 GET /analysis/{run_id}로 폴링합니다. 세션 status가 'uploaded'여야 합니다.",
)
def analyze_session(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
    if session.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"분석 가능한 상태가 아닙니다. 현재 상태: {session.status}",
        )

    # AnalysisRun 생성
    analysis_run = AnalysisRun(
        session_id=session.session_id,
        model_name="vocal-analysis",
        model_version="0.1.0",
        status="queued",
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)

    background_tasks.add_task(
        run_analysis_by_ids,
        str(analysis_run.run_id),
        str(session.session_id),
    )

    return AnalyzeResponse(run_id=analysis_run.run_id, status=analysis_run.status)


# ──── GET /analysis/{run_id} ────
@router.get(
    "/analysis/{run_id}",
    response_model=AnalysisRunDetail,
    summary="분석 실행 상태 조회",
    description="분석 실행의 status(queued/running/success/failed)를 조회합니다. 비동기 전환 시 폴링 용도.",
)
def get_analysis_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 실행을 찾을 수 없습니다.")

    # 본인 세션의 분석만 조회 가능
    session = db.query(Session).filter(Session.session_id == run.session_id).first()
    if not session or session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    return run


# ──── GET /analysis/{run_id}/results ────
@router.get(
    "/analysis/{run_id}/results",
    response_model=AnalysisResultsResponse,
    summary="분석 결과 조회",
    description="분석 결과 전체를 반환합니다. result_json에 scores 9개, feedback 9개, indicators, audio_info, reliability가 포함됩니다.",
)
def get_analysis_results(
    run_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 실행을 찾을 수 없습니다.")

    session = db.query(Session).filter(Session.session_id == run.session_id).first()
    if not session or session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    if run.status in ("success", "completed", "no_voice"):
        response.headers["Cache-Control"] = "private, max-age=31536000, immutable"
        response.headers["ETag"] = f'"{run_id}"'
    else:
        response.headers["Cache-Control"] = "no-cache"

    metrics = [
        MetricItem(key=r.metric_key, value=r.metric_value, unit=r.unit)
        for r in run.results
    ]
    return AnalysisResultsResponse(
        run_id=run.run_id,
        session_id=run.session_id,
        user_id=session.user_id,
        metrics=metrics,
        result_json=run.result_json,
    )


# ──── GET /analysis/{run_id}/comparison ────
@router.get("/analysis/{run_id}/comparison", response_model=ComparisonResponse)
def get_analysis_comparison(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 실행을 찾을 수 없습니다.")

    session = db.query(Session).filter(Session.session_id == run.session_id).first()
    if not session or session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    # 활성 기준 프로필 조회
    ref_profile = (
        db.query(ReferenceProfile).filter(ReferenceProfile.is_active == True).first()  # noqa: E712
    )
    if not ref_profile:
        return ComparisonResponse(run_id=run.run_id, reference_name=None, comparisons=[])

    # 기준 메트릭을 dict로 변환
    ref_metrics = (
        db.query(ReferenceMetric)
        .filter(ReferenceMetric.reference_id == ref_profile.reference_id)
        .all()
    )
    ref_map = {rm.metric_key: rm for rm in ref_metrics}

    # 비교 계산
    comparisons: list[ComparisonItem] = []
    for result in run.results:
        ref = ref_map.get(result.metric_key)
        if ref and ref.std_value and ref.std_value > 0:
            z = (result.metric_value - ref.mean_value) / ref.std_value
            # 정규분포 CDF 근사 (percentile)
            percentile = _norm_cdf(z) * 100
        else:
            z = None
            percentile = None

        comparisons.append(
            ComparisonItem(
                key=result.metric_key,
                user_value=result.metric_value,
                reference_mean=ref.mean_value if ref else 0.0,
                z_score=round(z, 4) if z is not None else None,
                percentile=round(percentile, 2) if percentile is not None else None,
            )
        )

    return ComparisonResponse(
        run_id=run.run_id,
        reference_name=ref_profile.name,
        comparisons=comparisons,
    )


def _norm_cdf(z: float) -> float:
    """표준정규분포 CDF 근사값을 반환합니다."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
