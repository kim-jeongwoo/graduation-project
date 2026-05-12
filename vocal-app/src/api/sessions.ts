import apiClient from './client';
import type {
  CreateSessionRequest,
  Session,
  SessionDetail,
  FileUploadResponse,
} from '../types/api';
import type { ServerScoreMeta } from '../types/analyze';

const ANALYZE_SUCCESS_STATUSES = new Set(['success', 'completed', 'complete', 'done']);
const ANALYZE_FAILURE_STATUSES = new Set(['failed', 'invalid', 'no_voice', 'error']);

export interface StartAnalysisResponse {
  run_id: string;
  status?: string | null;
  reason?: string | null;
  message?: string | null;
  detail?: unknown;
}

interface AnalyzeStatusPayload {
  run_id?: string;
  status?: string | null;
  reason?: string | null;
  message?: string | null;
  detail?: unknown;
}

function normalizeAnalyzeStatus(status: string | null | undefined): string | undefined {
  const normalized = status?.trim().toLowerCase();
  return normalized || undefined;
}

function getStringField(value: unknown, key: string): string | null {
  if (!value || typeof value !== 'object' || !(key in value)) return null;
  const field = (value as Record<string, unknown>)[key];
  return typeof field === 'string' && field.trim() ? field : null;
}

function extractAnalyzeMessage(payload: AnalyzeStatusPayload): string | null {
  const detail = payload.detail;
  return payload.reason
    ?? payload.message
    ?? (typeof detail === 'string' ? detail : null)
    ?? getStringField(detail, 'reason')
    ?? getStringField(detail, 'message')
    ?? getStringField(detail, 'detail')
    ?? getStringField(detail, 'error');
}

function buildAnalyzeStatusMessage(payload: AnalyzeStatusPayload): string {
  const status = normalizeAnalyzeStatus(payload.status);
  const detailMessage = extractAnalyzeMessage(payload);
  if (detailMessage) return detailMessage;
  if (status === 'no_voice') {
    return '음성이 감지되지 않았습니다. 마이크가 정상 동작하는지, 노래를 부르셨는지 확인해 주세요.';
  }
  if (status === 'invalid') {
    return '분석할 수 없는 녹음입니다. 다시 녹음해 주세요.';
  }
  return 'AI 분석에 실패했습니다. 다시 시도해 주세요.';
}

export function isAnalyzeSuccessStatus(status: string | null | undefined): boolean {
  const normalized = normalizeAnalyzeStatus(status);
  return normalized !== undefined && ANALYZE_SUCCESS_STATUSES.has(normalized);
}

export function isAnalyzeFailureStatus(status: string | null | undefined): boolean {
  const normalized = normalizeAnalyzeStatus(status);
  return normalized !== undefined && ANALYZE_FAILURE_STATUSES.has(normalized);
}

export class AnalyzeStatusError extends Error {
  status?: string;
  reason?: string | null;
  detail?: unknown;
  runId?: string;

  constructor(payload: AnalyzeStatusPayload) {
    super(buildAnalyzeStatusMessage(payload));
    this.name = 'AnalyzeStatusError';
    this.status = normalizeAnalyzeStatus(payload.status);
    this.reason = payload.reason ?? null;
    this.detail = payload.detail;
    this.runId = payload.run_id;
  }
}

export function assertAnalyzeBodyStatus<T extends StartAnalysisResponse>(response: T): T {
  const normalized = normalizeAnalyzeStatus(response.status);
  if (normalized === undefined || isAnalyzeSuccessStatus(normalized)) return response;
  throw new AnalyzeStatusError(response);
}

export async function createSession(data: CreateSessionRequest): Promise<Session> {
  const res = await apiClient.post<Session>('/sessions', data);
  return res.data;
}

export async function getSessions(): Promise<Session[]> {
  const res = await apiClient.get<Session[]>('/sessions');
  return res.data;
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  const res = await apiClient.get<SessionDetail>(`/sessions/${sessionId}`);
  return res.data;
}

// SessionDetail 응답에서 run_id 추출 (서버 위치: detail.latest_analysis.run_id)
export function extractRunId(detail: unknown): string | null {
  return (detail as { latest_analysis?: { run_id?: string } })?.latest_analysis?.run_id ?? null;
}

export async function uploadSessionFile(
  sessionId: string,
  fileUri: string,
  fileName: string,
  mimeType: string = 'audio/wav',
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append('file', { uri: fileUri, name: fileName, type: mimeType } as unknown as Blob);
  const res = await apiClient.post<FileUploadResponse>(
    `/sessions/${sessionId}/files`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 },
  );
  return res.data;
}

// ─── 사후 측정 (training-analyze) ───
// 사용자가 훈련 구간 부른 후 그 구간만 재분석 (DB 저장 X, 휘발성)
export interface TrainingAnalyzeChunkMeta {
  chunk_index?: number;
  start_sec?: number;
  end_sec?: number;
  original_run_id?: string;
}

export interface TrainingAnalyzeScore {
  ai_score:      number;
  rounded_score: number;
  zone:          'insufficient' | 'appropriate' | 'excessive';
  confidence:    string;
}

export interface TrainingAnalyzeResponse {
  session_id:           string;
  status:               'success' | 'no_voice' | string;
  scores:               Record<string, TrainingAnalyzeScore> | null;
  reason:               string | null;
  duration_sec:         number;
  indicators:           Record<string, number> | null;
  scores_v2?:           Record<string, number> | null;
  scores_meta?:         Record<string, ServerScoreMeta> | null;
  low_confidence_items?: string[] | null;
  processing_time_ms:   number;
  chunk_meta:           TrainingAnalyzeChunkMeta | null;
}

export async function trainingAnalyze(
  sessionId: string,
  fileUri: string,
  chunkMeta?: TrainingAnalyzeChunkMeta,
  fileName: string = 'training.wav',
  mimeType: string = 'audio/wav',
): Promise<TrainingAnalyzeResponse> {
  const formData = new FormData();
  formData.append('audio', { uri: fileUri, name: fileName, type: mimeType } as unknown as Blob);
  if (chunkMeta) formData.append('chunk_meta', JSON.stringify(chunkMeta));
  const res = await apiClient.post<TrainingAnalyzeResponse>(
    `/sessions/${sessionId}/training-analyze`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 30000 },
  );
  console.log('[V2 진단 chunk] training-analyze response:', JSON.stringify(res.data).slice(0, 1500));
  return res.data;
}

export async function startAnalysis(sessionId: string): Promise<StartAnalysisResponse> {
  // Full-song duration varies by song length and timeline chunk cost.
  const res = await apiClient.post<StartAnalysisResponse>(
    `/sessions/${sessionId}/analyze`,
    {},
    { timeout: 200000 },  // v2: dml-server v2 chunk 처리 + Cloudflare Tunnel streaming 여유
  );
  return assertAnalyzeBodyStatus(res.data);
}
