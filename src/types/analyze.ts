import type { EvaluationItemKey, ConfidenceLevel } from '../domain/evaluationItems';

export type Zone = 'insufficient' | 'appropriate' | 'excessive';

export interface AudioInfo {
  duration_sec: number;
  sample_rate: number;
  voiced_ratio: number;
  f0_range: { min: number; max: number; mean: number };
}

export interface AcousticIndicators {
  cq_mean: number;
  cq_peak: number;
  cpp: number;
  spectral_centroid: number;
  spectral_tilt: number;
  h1_h2: number;
  hnr: number;
  a1_p0: number;
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
}

// ─── 서버 raw 응답 타입 (키에 숫자 prefix 포함: "1_nasal_oral_ratio" 등) ───
// 앱 내부에서는 이 타입을 직접 사용하지 않음 — analyze.ts 어댑터에서 AnalyzeResult로 변환
export interface ServerAnalyzeResult
  extends Omit<AnalyzeResult, 'scores' | 'feedback' | 'reliability'> {
  scores: Record<string, ScoreEntry>;     // key: "3_vocal_fold_contact" 등
  feedback: Record<string, FeedbackEntry>;
  reliability: {
    high_reliability: string[];           // value: "3_vocal_fold_contact" 등
    medium_reliability: string[];
    unavailable: string[];
  };
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
