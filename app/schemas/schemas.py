"""Pydantic 요청/응답 스키마 정의."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    nickname: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: str
    token: str


class AdminUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────
class SessionCreateRequest(BaseModel):
    song_title: Optional[str] = None


class FileInfo(BaseModel):
    file_id: uuid.UUID
    file_type: str
    storage_uri: str
    format: Optional[str]
    sample_rate_hz: Optional[int]
    duration_ms: Optional[int]
    file_size_bytes: Optional[int]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class MetricItem(BaseModel):
    key: str
    value: float
    unit: Optional[str]


class AnalysisRunBrief(BaseModel):
    run_id: uuid.UUID
    model_name: str
    model_version: str
    status: str
    requested_at: datetime
    finished_at: Optional[datetime]
    metrics: list[MetricItem] = []

    model_config = {"from_attributes": True}


class LatestAnalysis(BaseModel):
    run_id: uuid.UUID
    status: str
    requested_at: datetime
    finished_at: Optional[datetime]
    result_json: Optional[dict] = None
    metrics: list[MetricItem] = []


class SessionBrief(BaseModel):
    session_id: uuid.UUID
    song_title: Optional[str]
    status: str
    analysis_status: str
    started_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetail(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    song_title: Optional[str]
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    files: list[FileInfo] = []
    latest_analysis: Optional[LatestAnalysis] = None

    model_config = {"from_attributes": True}


class SessionCreateResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────
class FileUploadResponse(BaseModel):
    file_id: uuid.UUID
    file_type: str
    storage_uri: str
    duration_ms: Optional[int]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────
class AnalyzeResponse(BaseModel):
    run_id: uuid.UUID
    status: str


class AnalysisRunDetail(BaseModel):
    run_id: uuid.UUID
    session_id: uuid.UUID
    model_name: str
    model_version: str
    status: str
    requested_at: datetime
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AnalysisResultsResponse(BaseModel):
    run_id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    metrics: list[MetricItem]
    result_json: Optional[dict] = None


class ComparisonItem(BaseModel):
    key: str
    user_value: float
    reference_mean: float
    z_score: Optional[float]
    percentile: Optional[float]


class ComparisonResponse(BaseModel):
    run_id: uuid.UUID
    reference_name: Optional[str]
    comparisons: list[ComparisonItem]


# ─────────────────────────────────────────────
# Songs
# ─────────────────────────────────────────────
class SongSummary(BaseModel):
    id: str
    artist: str
    title: str
    master_duration_sec: Optional[float] = None
    mr_duration_sec: Optional[float] = None
    has_lrc: bool
    has_pitch_guide: bool

    model_config = {"from_attributes": True}
