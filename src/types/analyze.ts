import type { EvaluationItemKey, ConfidenceLevel } from '../domain/evaluationItems';

export type Zone = 'insufficient' | 'appropriate' | 'excessive';

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
  };
  run_id: string;
  status: string;
  processing_time_ms: number;
  register_boundaries?: { low_max: number; mid_max: number };
}

// ─── 서버 raw 응답 타입 ───
// GET /analysis/{run_id}/results 응답의 result_json 필드 구조
// 키에 숫자 prefix 포함: "1_nasal_oral_ratio" 등
export interface ServerAnalyzeResult
  extends Omit<AnalyzeResult, 'scores' | 'feedback' | 'reliability'> {
  scores: Record<string, ScoreEntry>;
  feedback: Record<string, FeedbackEntry>;
  reliability: {
    high_reliability: string[];
    medium_reliability: string[];
    unavailable: string[];
  };
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
