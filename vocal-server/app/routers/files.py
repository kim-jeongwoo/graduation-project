"""파일 업로드 API."""

import os
import uuid
import wave
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models.models import Session, SessionFile, User
from app.schemas.schemas import FileUploadResponse

router = APIRouter(prefix="/sessions/{session_id}/files", tags=["files"])

# 업로드 파일 저장 경로
STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"


@router.post(
    "",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="오디오 파일 업로드",
    description="세션에 오디오 파일(WAV/MP3/M4A)을 업로드합니다. 업로드 후 세션 status가 'uploaded'로 변경되며, 이후 분석 요청이 가능합니다.",
)
def upload_file(
    session_id: uuid.UUID,
    file: UploadFile = File(...),    
    file_type: str = Query(default="audio"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    # 세션 확인 + 권한 체크
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")

    # WAV 파일은 영구 보관 (학습 데이터 활용 가능성 검증 후 정책 결정)
    save_dir = STORAGE_ROOT / "users" / str(current_user.user_id) / "sessions" / str(session_id)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 파일 저장
    filename = file.filename or "upload"
    save_path = save_dir / filename
    contents = file.file.read()
    save_path.write_bytes(contents)

    file_size = len(contents)
    file_ext = os.path.splitext(filename)[1].lstrip(".").lower() or None

    # WAV 파일이면 sample_rate, duration 자동 추출
    sample_rate: int | None = None
    duration_ms: int | None = None
    if file_ext == "wav":
        try:
            with wave.open(str(save_path), "rb") as wf:
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                duration_ms = int(n_frames / sample_rate * 1000) if sample_rate else None
        except Exception:
            pass  # WAV 파싱 실패해도 업로드는 진행

    # DB 레코드 생성
    session_file = SessionFile(
        session_id=session.session_id,
        file_type=file_type,
        storage_uri=str(save_path),
        format=file_ext,
        sample_rate_hz=sample_rate,
        duration_ms=duration_ms,
        file_size_bytes=file_size,
    )
    db.add(session_file)

    # 세션 상태를 "uploaded"로 변경
    session.status = "uploaded"

    db.commit()
    db.refresh(session_file)

    return FileUploadResponse(
        file_id=session_file.file_id,
        file_type=session_file.file_type,
        storage_uri=session_file.storage_uri,
        duration_ms=session_file.duration_ms,
    )
