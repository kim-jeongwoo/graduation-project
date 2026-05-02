"""
schemas.py — Pydantic models for /analyze endpoint response
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


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


class AnalysisResponse(BaseModel):
    run_id: str
    status: str
    processing_time_ms: float
    audio_info: AudioInfo
    register_boundaries: RegisterBoundaries
    registers: Dict[str, RegisterMetrics] = Field(
        description="Keys: low | mid | high"
    )
    indicators: Indicators
    scores: Dict[str, ScoreItem] = Field(
        description="Keys: 1_nasal_oral_ratio ... 9_pressure_balance"
    )
    feedback: Dict[str, FeedbackItem] = Field(
        description="Keys: 1_nasal_oral_ratio ... 9_pressure_balance"
    )
    reliability: ReliabilityInfo
