import type { EvaluationItemKey, ConfidenceLevel } from '../domain/evaluationItems';

export type Zone = 'insufficient' | 'appropriate' | 'excessive';

// v2 — score_mapper_v2 tier (5/11)
export type ScoreTier = 'high' | 'high_star';

export interface ScoreMetaEntry {
  tier:         ScoreTier;
  caveats:      string[];
  displayMark:  'asterisk' | null;
  tooltip:      string | null;
  roundedScore: number;
  icc:          number;
  iccRatio:     number;
}

// timeline chunk score: v1 호환 + v2 4항목 + low_confidence_items
export interface TimelineChunkScore {
  startSec:         number;
  endSec:           number;
  lrcText:          string;
  chunkDurationS?:  number;
  scores: {
    breathiness?:      { aiScore: number; zone: Zone; roundedScore: number; tier?: ScoreTier };
    vocalFoldContact?: { aiScore: number; zone: Zone; roundedScore: number; tier?: ScoreTier };
    softPalate?:       { aiScore: number; zone: Zone; roundedScore: number; tier?: ScoreTier };
    tongueTension?:    { aiScore: number; zone: Zone; roundedScore: number; tier?: ScoreTier };
  };
  lowConfidenceItems?: EvaluationItemKey[];
}

export interface TimelineMetadata {
  chunkMethod:           string;
  shownIndicators:       string[];
  shownIndicatorsReason: string;
}

export interface AudioInfo {
  duration_sec: number;
  sample_rate: number;
  voiced_ratio: number;
  voiced_duration_s?: number;
  f0_min?: number;
  f0_max?: number;
  f0_mean?: number;
  /** @deprecated server now uses f0_min/f0_max/f0_mean */
  f0_range?: { min: number; max: number; mean: number };
}

export interface AcousticIndicators {
  cq_mean: number;
  cq_peak: number;
  cpp_mean: number;
  spectral_centroid_mean: number;
  spectral_tilt_mean: number;
  h1_h2_mean: number;
  hnr_mean: number;
  a1_p0_mean: number;
  nasal_ratio?: number;
  singers_formant_ratio_mean?: number;
}

export interface ScoreEntry {
  ai_score: number | null;  // 0~5 정수, unavailable 항목은 null
  zone: Zone | null;
  confidence: ConfidenceLevel;
}

export interface FeedbackEntry {
  name_ko: string;
  ai_score: number | null;
  score_description: string;  // 평가 기준표 원문
  feedback_text: string;
  zone: Zone | null;
  ai_indicator: { name: string; value: number };
}

export interface AnalyzeResult {
  audio_info: AudioInfo;
  registers: {
    low: Record<string, unknown>;
    mid: Record<string, unknown>;
    high: Record<string, unknown>;
  };
  indicators: AcousticIndicators;
  scores: Record<EvaluationItemKey, ScoreEntry>;
  feedback: Record<EvaluationItemKey, FeedbackEntry>;
  reliability: {
    high_reliability: EvaluationItemKey[];
    medium_reliability: EvaluationItemKey[];
    unavailable: EvaluationItemKey[];
    // v2 신규 (선택, v1 응답엔 없음)
    shownV2?:        EvaluationItemKey[];
    academicOnlyV2?: EvaluationItemKey[];
    deferredV2?:     EvaluationItemKey[];
  };
  run_id: string;
  session_id?: string;
  status: string;
  processing_time_ms: number;
  register_boundaries?: { low_max: number; mid_max: number };
  timelineScores?:      TimelineChunkScore[];
  timelineMetadata?:    TimelineMetadata;
  userF0?:              { frameHz: number; values: (number | null)[] } | null;
  // v2 신규 (5/11 score_mapper_v2)
  scoreMapperVersion?:  'v1' | 'v2' | string;
  scoresV2?:            Partial<Record<EvaluationItemKey, number>>;
  scoresMeta?:          Partial<Record<EvaluationItemKey, ScoreMetaEntry>>;
}

// ─── 서버 raw 응답 타입 ───
// GET /analysis/{run_id}/results 응답의 result_json 필드 구조
// 키에 숫자 prefix 포함: "1_nasal_oral_ratio" 등
// v2 server score_meta raw (snake_case)
export interface ServerScoreMeta {
  tier:          ScoreTier;
  caveats:       string[];
  display_mark:  'asterisk' | null;
  tooltip:       string | null;
  rounded_score: number;
  icc:           number;
  icc_ratio:     number;
}

export interface ServerAnalyzeResult
  extends Omit<AnalyzeResult, 'scores' | 'feedback' | 'reliability' | 'timelineScores' | 'timelineMetadata' | 'scoresV2' | 'scoresMeta'> {
  scores: Record<string, ScoreEntry>;
  feedback: Record<string, FeedbackEntry>;
  reliability: {
    high_reliability: string[];
    medium_reliability: string[];
    unavailable: string[];
    // v2 신규
    shown_v2?:         string[];
    shown_v2_tiers?:   Record<string, ScoreTier>;
    academic_only_v2?: string[];
    deferred_v2?:      string[];
  };
  // v2 신규 top-level
  score_mapper_version?: string;
  scores_v2?:            Record<string, number>;
  scores_meta?:          Record<string, ServerScoreMeta>;
  academic_analysis_scores?: Record<string, unknown>;  // 학술 전용, 앱 표시 X
  timeline_scores?: Array<{
    start_sec: number;
    end_sec:   number;
    lrc_text:  string;
    chunk_duration_s?: number;
    scores: Record<string, { ai_score: number; zone?: Zone; rounded_score: number; tier?: ScoreTier }>;
    low_confidence_items?: string[];
  }>;
  timeline_metadata?: {
    chunk_method?:            string;
    shown_indicators:         string[];
    shown_indicators_reason:  string;
    score_mapper_version?:    string;
    // 그 외 v2 필드는 인지하지만 클라이언트에서 사용 X
  };
  user_f0?: { frame_hz: number; values: (number | null)[] } | null;
}

// GET /analysis/{run_id}/results 응답 최상위 래퍼
export interface ServerAnalyzeResultsResponse {
  run_id: string;
  session_id: string;
  user_id: string;
  metrics: Array<{ key: string; value: number; unit: string }>;
  result_json: ServerAnalyzeResult;   // 실제 분석 데이터
}

// server 래핑 시 추가 예상 메타 (명세 확정 전, 선택적 필드)
export interface AnalyzeResultWithMeta extends AnalyzeResult {
  recordingId?: string;
  userId?: string;
  timestamp?: string;  // ISO 8601
  songId?: string;
}

export interface UploadRecordingRequest {
  fileUri: string;
  songId: string;
  userId: string;
}
