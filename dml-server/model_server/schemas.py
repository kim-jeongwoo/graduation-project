"""
schemas.py — Pydantic models for /analyze endpoint response
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# success/completed: 정상 분석 완료 (의미 동등, 호환성 위해 둘 다 허용)
# server.py는 현재 "success" 반환. completed는 alias로 schema에만 정의.
# 향후 표준화 시 server.py 응답을 completed로 변경 가능.
class AnalysisStatus(str, Enum):
    success   = "success"    # server.py 현재 사용 중
    completed = "completed"  # 호환용 alias
    failed    = "failed"
    no_voice  = "no_voice"


class AudioInfo(BaseModel):
    duration_s: float = Field(description="Total wav duration in seconds")
    sample_rate: int = Field(description="Resampled sample rate (always 16000)")
    voiced_ratio: float = Field(description="Fraction of frames detected as voiced (0~1)")
    voiced_duration_s: float = Field(description="Total voiced duration in seconds")
    f0_min: Optional[float] = Field(None, description="Minimum F0 (Hz) of voiced frames")
    f0_max: Optional[float] = Field(None, description="Maximum F0 (Hz) of voiced frames")
    f0_mean: Optional[float] = Field(None, description="Mean F0 (Hz) of voiced frames")


class RegisterBoundaries(BaseModel):
    low_max: float = Field(description="F0 upper bound for low register (Hz)")
    mid_max: float = Field(description="F0 upper bound for mid register (Hz)")


class RegisterMetrics(BaseModel):
    """Metrics computed within one register band."""
    n_frames: int
    cq_mean: Optional[float] = None
    cq_peak: Optional[float] = None
    cpp: Optional[float] = None
    hnr: Optional[float] = None
    spectral_centroid: Optional[float] = None
    spectral_tilt: Optional[float] = None
    h1_h2: Optional[float] = None
    singers_formant_ratio: Optional[float] = None
    a1_p0: Optional[float] = None


class Indicators(BaseModel):
    """Global (all-voiced) acoustic indicators."""
    cq_mean: Optional[float] = None
    cq_peak: Optional[float] = None
    cpp_mean: Optional[float] = None
    hnr_mean: Optional[float] = None
    spectral_centroid_mean: Optional[float] = None
    spectral_tilt_mean: Optional[float] = None
    h1_h2_mean: Optional[float] = None
    singers_formant_ratio_mean: Optional[float] = None
    a1_p0_mean: Optional[float] = None
    nasal_ratio: Optional[float] = Field(
        None, description="Only available if nasal mic channel provided"
    )


class AIIndicator(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None


class ScoreItem(BaseModel):
    ai_score: Optional[float] = Field(None, description="AI-estimated score 0~5")
    rounded_score: Optional[int] = None
    zone: Optional[str] = Field(None, description="insufficient | appropriate | excessive")
    confidence: Optional[str] = Field(
        None, description="high | medium | unavailable"
    )


class FeedbackItem(BaseModel):
    name_ko: str
    ai_score: Optional[float] = None
    score_description: Optional[str] = Field(None, description="Vocalization criteria text from v3 rubric")
    feedback_text: Optional[str] = None
    zone: Optional[str] = None
    zone_label: Optional[str] = None
    ai_indicator: Optional[AIIndicator] = None


class ReliabilityInfo(BaseModel):
    high_reliability: List[str] = Field(
        description="Items with Pearson r > 0.5, p < 0.01 on validation set"
    )
    medium_reliability: List[str] = Field(
        description="Items with learned mapping but below high threshold"
    )
    unavailable: List[str] = Field(
        description="Items with no AI indicator"
    )


class UserF0(BaseModel):
    frame_hz: int = Field(description="F0 샘플링 주파수 (현재 25Hz, 40ms 간격)")
    values: List[Optional[float]] = Field(
        description="voiced 구간 freq_hz(float), unvoiced 구간 None. index × (1/frame_hz) = 시간(초)"
    )


class TimelineScore(BaseModel):
    """분석 점수 — LRC 한 라인(또는 병합/분할된 청크) 단위."""
    start_sec: float
    end_sec: float
    lrc_text: str
    scores: Dict[str, Optional[ScoreItem]] = Field(
        description="Keys: 3_vocal_fold_contact, 4_breathiness"
    )


class TimelineMetadata(BaseModel):
    n_chunks: int = Field(description="총 분석 청크 수")
    n_ok: int = Field(description="분석 성공 청크 수")
    n_skipped: int = Field(description="voiced 부족으로 건너뛴 청크 수")
    processing_time_ms: float
    items: List[str] = Field(description="타임라인에 포함된 항목 키 목록 (backward compat)")
    shown_indicators: Optional[List[str]] = None
    shown_indicators_reason: Optional[str] = None
    deferred_indicators: Optional[List[str]] = None
    deferred_reason: Optional[str] = None
    deferred_revisit_after: Optional[str] = None
    min_chunk_sec: Optional[float] = None
    max_chunk_sec: Optional[float] = None


class AnalysisResponse(BaseModel):
    run_id: str
    status: AnalysisStatus
    reason: Optional[str] = Field(None, description="no_voice / failed 시 사유 메시지")
    processing_time_ms: float
    audio_info: AudioInfo
    register_boundaries: Optional[RegisterBoundaries] = None
    registers: Optional[Dict[str, RegisterMetrics]] = Field(
        None, description="Keys: low | mid | high"
    )
    indicators: Optional[Indicators] = None
    scores: Optional[Dict[str, ScoreItem]] = Field(
        None, description="Keys: 1_nasal_oral_ratio ... 9_pressure_balance"
    )
    feedback: Optional[Dict[str, FeedbackItem]] = Field(
        None, description="Keys: 1_nasal_oral_ratio ... 9_pressure_balance"
    )
    reliability: Optional[ReliabilityInfo] = None
    timeline_scores: Optional[List[TimelineScore]] = Field(
        None, description="song_id 지정 시에만 반환. LRC 라인 단위 분석."
    )
    timeline_metadata: Optional[TimelineMetadata] = Field(
        None, description="song_id 지정 시에만 반환. 타임라인 분석 요약."
    )
    user_f0: Optional[UserF0] = Field(
        None, description="25Hz sparse null 포맷 사용자 F0. no_voice 시 None."
    )


# ── Phase 4: /analyze-chunk 전용 응답 ────────────────────────────────

class ChunkScoreItem(BaseModel):
    """단일 chunk 점수 — high 신뢰 항목(접촉강도/호흡식별)만."""
    ai_score: Optional[float] = Field(None, description="AI 점수 0.0~5.0")
    rounded_score: Optional[int] = Field(None, description="0~5 정수 (UI 표시용)")
    zone: Optional[str] = Field(None, description="insufficient | appropriate | excessive")
    confidence: Optional[str] = Field(
        None, description="high (≥5s) | medium (3~5s) | unavailable"
    )


class ChunkIndicators(BaseModel):
    """단일 chunk acoustic 지표 (참고용)."""
    voiced_ratio: Optional[float] = Field(None, description="0~1 voiced 프레임 비율")
    cpp_mean: Optional[float] = Field(None, description="호흡식별 원본 지표")
    cq_p90: Optional[float] = Field(None, description="접촉강도 원본 지표 (CQ 90백분위)")


class ChunkAnalysisResponse(BaseModel):
    """/analyze-chunk 정상 응답."""
    run_id: str
    status: AnalysisStatus = Field(description="success | no_voice | failed")
    reason: Optional[str] = Field(None, description="no_voice/failed 시 사유")
    duration_sec: float
    scores: Optional[Dict[str, ChunkScoreItem]] = Field(
        None, description="Keys: 3_vocal_fold_contact, 4_breathiness"
    )
    indicators: Optional[ChunkIndicators] = None
    processing_time_ms: float


class ChunkTooShortResponse(BaseModel):
    """duration < 3.0s 시 HTTP 400 응답."""
    error: str = Field("chunk_too_short")
    reason: str = Field(description="사용자 표시 메시지")
    duration_sec: float
    min_required_sec: float = Field(3.0)
