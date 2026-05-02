import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# 1. User
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nickname = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # user / trainer / admin
    # TODO: 상용화 시 default=False로 변경, 가입 승인 흐름 추가
    is_approved = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# 2. Session
# ─────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    # song_id 있으면 14곡 자유곡, 없고 song_title만 있으면 사용자 자유 입력곡
    song_id = Column(String(8), ForeignKey("songs.id"), nullable=True)
    song_title = Column(String, nullable=True)
    status = Column(
        String, default="uploading", nullable=False
    )  # uploading / uploaded / analyzing / completed / failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # relationships
    user = relationship("User", back_populates="sessions")
    song = relationship("Song", back_populates="sessions")
    files = relationship("SessionFile", back_populates="session", cascade="all, delete-orphan")
    analysis_runs = relationship(
        "AnalysisRun", back_populates="session", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# 3. SessionFile
# ─────────────────────────────────────────────
class SessionFile(Base):
    __tablename__ = "session_files"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_type = Column(String, nullable=False)  # audio / piezo / accelerometer
    storage_uri = Column(String, nullable=False)
    format = Column(String, nullable=True)  # wav, csv 등
    sample_rate_hz = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # relationships
    session = relationship("Session", back_populates="files")


# ─────────────────────────────────────────────
# 4. AnalysisRun
# ─────────────────────────────────────────────
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    status = Column(
        String, default="queued", nullable=False
    )  # queued / running / completed / failed
    requested_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    output_uri = Column(String, nullable=True)
    result_json = Column(JSONB, nullable=True)  # model_server /analyze 응답 JSON 전체 저장

    # relationships
    session = relationship("Session", back_populates="analysis_runs")
    results = relationship(
        "AnalysisResult", back_populates="analysis_run", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# 5. AnalysisResult
# ─────────────────────────────────────────────
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_key = Column(
        String, nullable=False
    )  # contact_rate, chest_ratio, oral_nasal_ratio, egg_correlation 등
    metric_value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)  # ratio, percent, dB 등

    # relationships
    analysis_run = relationship("AnalysisRun", back_populates="results")


# ─────────────────────────────────────────────
# 6. ReferenceProfile
# ─────────────────────────────────────────────
class ReferenceProfile(Base):
    __tablename__ = "reference_profiles"

    reference_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # relationships
    metrics = relationship(
        "ReferenceMetric", back_populates="profile", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# 7. ReferenceMetric (복합 PK)
# ─────────────────────────────────────────────
class ReferenceMetric(Base):
    __tablename__ = "reference_metrics"

    reference_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reference_profiles.reference_id", ondelete="CASCADE"),
        primary_key=True,
    )
    metric_key = Column(String, primary_key=True)
    mean_value = Column(Float, nullable=False)
    std_value = Column(Float, nullable=False)

    # relationships
    profile = relationship("ReferenceProfile", back_populates="metrics")


# ─────────────────────────────────────────────
# 8. Song (노래방 자유곡 메타)
# 14곡 자유곡 메타. id는 dmlserver의 songs.json과 1:1 매핑 ('001'~'014')
# ─────────────────────────────────────────────
class Song(Base):
    __tablename__ = "songs"

    id = Column(String(8), primary_key=True)  # "001" ~ "014"
    artist = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    master_filename = Column(String(255), nullable=True)
    mr_filename = Column(String(255), nullable=True)
    master_duration_sec = Column(Float, nullable=True)
    mr_duration_sec = Column(Float, nullable=True)
    lrc_offset_sec = Column(Float, nullable=True)
    alignment_status = Column(String(20), nullable=True)
    has_lrc = Column(Boolean, default=False, nullable=False, server_default="false")
    has_pitch_guide = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    sessions = relationship("Session", back_populates="song")
