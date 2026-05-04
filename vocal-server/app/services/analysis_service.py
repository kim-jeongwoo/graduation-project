"""분석 서비스 – AI 모델서버 호출 및 결과 저장."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session as DBSession

from app.config import MODEL_SERVER_URL
from app.models.models import AnalysisResult, AnalysisRun, Session, SessionFile

logger = logging.getLogger("uvicorn.error")

_ANALYZE_TIMEOUT = 120.0


def run_analysis(run: AnalysisRun, session: Session, db: DBSession, song_id: str | None = None) -> AnalysisRun:
    """세션의 오디오 파일을 모델서버에 전송하고 결과를 저장합니다."""

    # ── 1. 상태 → running ──
    run.status = "running"
    session.status = "analyzing"
    db.commit()

    try:
        # ── 2. 오디오 파일 경로 조회 ──
        audio_file: SessionFile | None = (
            db.query(SessionFile)
            .filter(
                SessionFile.session_id == session.session_id,
                SessionFile.file_type == "audio",
            )
            .first()
        )
        if not audio_file:
            raise FileNotFoundError("세션에 업로드된 오디오 파일이 없습니다.")

        file_path = Path(audio_file.storage_uri)
        if not file_path.exists():
            raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")

        # ── 3. 모델서버 호출 ──
        analyze_url = f"{MODEL_SERVER_URL}/analyze"
        params: dict = {"run_id": str(run.run_id)}
        if song_id:
            params["song_id"] = song_id
        with open(file_path, "rb") as f:
            response = httpx.post(
                analyze_url,
                params=params,
                files={"file": (file_path.name, f, "audio/wav")},
                timeout=_ANALYZE_TIMEOUT,
            )

        # ── 4. 응답 파싱 ──
        http_status = response.status_code
        data: dict | None = None
        parse_error: str | None = None

        try:
            data = response.json()
        except Exception as e:
            parse_error = str(e)

        # HTTP 비-200이거나 JSON 파싱 실패 시 에러 형식으로 result_json 저장
        if not response.is_success or data is None:
            run.result_json = {
                "error": True,
                "http_status": http_status,
                "raw_response": response.text[:5000],
                **({"exception": parse_error} if parse_error else {}),
            }
            run.status = "failed"
            run.error_message = f"HTTP {http_status}: {response.text[:500]}"
            run.finished_at = datetime.now(timezone.utc)
            session.status = "failed"
            db.commit()
            db.refresh(run)
            return run

        logger.info(f"모델서버 응답 status={data.get('status')} run_id={run.run_id}")

        # ── 5. 응답 JSON 전체 저장 ──
        run.result_json = data

        # ── 6. 핵심 메트릭 3개 AnalysisResult에 저장 ──
        audio_info = data.get("audio_info") or {}  # no_voice 등 audio_info=None 방어
        metric_rows = [
            ("voiced_ratio", audio_info.get("voiced_ratio"), "ratio"),
            ("processing_time_ms", data.get("processing_time_ms"), "ms"),
            # 모델서버가 duration_s 키로 반환 (스펙 duration_sec와 다름)
            ("duration_sec", audio_info.get("duration_s") or audio_info.get("duration_sec"), "sec"),
        ]
        for key, value, unit in metric_rows:
            if value is not None:
                db.add(AnalysisResult(
                    run_id=run.run_id,
                    metric_key=key,
                    metric_value=float(value),
                    unit=unit,
                ))

        # ── 7. 완료/실패/no_voice 처리 ──
        server_status = data.get("status", "completed")
        run.status = server_status
        run.finished_at = datetime.now(timezone.utc)

        if server_status == "no_voice":
            logger.info(f"[analyze] no_voice detected: run_id={run.run_id}, reason={data.get('reason')}")
            session.status = "completed"
        elif server_status == "failed":
            run.error_message = data.get("error_message", "모델서버가 failed 상태 반환")
            session.status = "failed"
        else:
            session.status = server_status

        db.commit()
        db.refresh(run)

    except Exception as exc:
        # ── 예외 실패 처리 ──
        logger.error(f"분석 실패 (run_id={run.run_id}): {exc}")
        run.result_json = {
            "error": True,
            "http_status": None,
            "raw_response": None,
            "exception": str(exc),
        }
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.now(timezone.utc)
        session.status = "failed"
        db.commit()
        db.refresh(run)

    return run
