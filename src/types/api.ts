// ─── Auth ───
export interface SignupRequest {
  email: string;
  password: string;
  nickname: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  user_id: string;
  email: string;
  nickname: string;
  token: string;
}

// ─── Session ───
export interface CreateSessionRequest {
  song_title?: string;
  song_id?: string;
}

export interface Session {
  session_id: string;
  song_title?: string;
  song_id?: string;
  status: string;
  started_at?: string;
  created_at: string;
}

export interface SessionFile {
  file_id: string;
  file_type: string;
  storage_uri: string;
  duration_ms: number;
}

export interface AnalysisRunSummary {
  run_id: string;
  status: string;
}

export interface SessionDetail extends Session {
  files: SessionFile[];
  analysis: AnalysisRunSummary | null;
}

// ─── File Upload ───
export interface FileUploadResponse {
  file_id: string;
  file_type: string;
  storage_uri: string;
  duration_ms: number;
}

// ─── Analysis ───
export interface AnalyzeResponse {
  run_id: string;
  status: string;
}

export interface AnalysisStatus {
  run_id: string;
  session_id: string;
  model_name: string;
  status: string;
  requested_at: string;
  finished_at: string | null;
}

export interface Metric {
  key: string;
  value: number;
  unit: string;
}

export interface AnalysisResults {
  run_id: string;
  metrics: Metric[];
}

export interface Comparison {
  key: string;
  user_value: number;
  reference_mean: number;
  z_score: number;
  percentile: number;
}

export interface AnalysisComparison {
  run_id: string;
  reference_name: string;
  comparisons: Comparison[];
}

// ─── Feedback ───
export interface Feedback {
  overall_grade: string;
  overall_comment: string;
  strengths: string[];
  improvements: string[];
}

// ─── Vocal (음역대 측정) ───
export interface PitchDetectionResult {
  detected_note: string | null;
  frequency_hz: number;
  confidence: number;
  stable_duration_ms: number;
  all_notes?: string[];
  pitch_range?: {
    low_hz: number;
    high_hz: number;
  };
}

export interface PitchDetectionError {
  error: string;
}

export interface FamousSinger {
  name: string;
  range_low: string;
  range_high: string;
  voice_type: string;
  famous_songs: string[];
  youtube_query: string;
}

// ─── Song ───
export interface Song {
  song_id: string;
  title: string;
  artist: string;
  duration_sec: number;
  has_lrc: boolean;         // 가사 싱크 데이터 준비 여부
  has_pitch_guide: boolean; // 음정 가이드 준비 여부
}

export interface LyricsLine {
  time_ms: number;
  end_ms: number;
  text: string;
  timestamp_source?: string;
}

export interface LyricsData {
  song_id: string;
  lines: LyricsLine[];
}

// ─── Pitch Comparison ───
export interface PitchFrame {
  time_ms: number;
  note: string | null;
  midi: number | null;
  freq_hz?: number;
  freq?: number;  // 서버 실제 응답 필드
}

export interface PitchData {
  song_id: string;
  resolution_ms: number;
  frames: PitchFrame[];
}

export interface ComparisonFrame {
  time_ms: number;
  original_note: string | null;
  original_midi: number | null;
  user_note: string | null;
  user_midi: number | null;
  diff_semitones: number | null;
}

export interface PitchComparisonSection {
  start_ms: number;
  end_ms: number;
  accuracy: number;
  label: string;
}

export interface PitchComparison {
  session_id: string;
  song_id: string;
  comparison: {
    overall_accuracy: number;
    accuracy_lenient: number;
    frames: ComparisonFrame[];
    sections: PitchComparisonSection[];
  };
}
