"""노래방 곡 API — 목록 / LRC / 음정 가이드 / MR 스트리밍."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path as FPath, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models.models import Song, User
from app.schemas.schemas import SongSummary

router = APIRouter(tags=["songs"])

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage" / "songs"
LRC_DIR = STORAGE_ROOT / "lrc" / "parsed"
PITCH_DIR = STORAGE_ROOT / "pitch_guide"
MR_DIR = STORAGE_ROOT / "audio" / "mr"


def _get_song_or_404(song_id: str, db: DBSession) -> Song:
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 곡입니다.")
    return song


@router.get(
    "/songs",
    response_model=list[SongSummary],
    summary="곡 목록 조회",
    description="노래방 14곡 메타 리스트를 반환합니다.",
)
def list_songs(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return db.query(Song).order_by(Song.id).all()


@router.get(
    "/songs/{song_id}/lrc",
    summary="LRC 가사 조회",
    description="해당 곡의 동기화 가사 데이터를 반환합니다. 시간 + 가사 텍스트 배열.",
)
def get_lrc(
    song_id: Annotated[str, FPath(pattern=r"^\d{3}$")],
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    _get_song_or_404(song_id, db)
    lrc_file = LRC_DIR / f"{song_id}.json"
    if not lrc_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LRC 데이터가 아직 준비되지 않았습니다.",
        )
    with open(lrc_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get(
    "/songs/{song_id}/pitch-guide",
    summary="음정 가이드 조회",
    description="해당 곡의 가수 음정 곡선을 반환합니다. 시간 + MIDI/주파수 + voiced 플래그.",
)
def get_pitch_guide(
    song_id: Annotated[str, FPath(pattern=r"^\d{3}$")],
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    _get_song_or_404(song_id, db)
    pitch_file = PITCH_DIR / f"{song_id}.json"
    if not pitch_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="음정 가이드가 아직 준비되지 않았습니다.",
        )
    with open(pitch_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get(
    "/songs/{song_id}/mr",
    summary="MR 음원 스트리밍",
    description="해당 곡의 MR 음원 파일을 반환합니다 (mp3).",
)
def get_mr(
    song_id: Annotated[str, FPath(pattern=r"^\d{3}$")],
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    # TODO: 앱에서 부분 재생/탐색 필요 시 range request 구현
    song = _get_song_or_404(song_id, db)
    if not song.mr_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MR 파일 정보가 없습니다.",
        )
    mr_file = MR_DIR / song.mr_filename
    if not mr_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MR 파일을 찾을 수 없습니다.",
        )
    return FileResponse(
        path=str(mr_file),
        media_type="audio/mpeg",
        filename=song.mr_filename,
    )
