import apiClient from './client';
import type {
  CreateSessionRequest,
  Session,
  SessionDetail,
  FileUploadResponse,
} from '../types/api';

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
    { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 10000 },
  );
  return res.data;
}

export async function startAnalysis(sessionId: string): Promise<{ run_id: string; status: string; reason?: string }> {
  // Synchronous processing: server takes 10~30s. Timeout set to 90s (server 60s + network buffer).
  const res = await apiClient.post<{ run_id: string; status: string; reason?: string }>(
    `/sessions/${sessionId}/analyze`,
    {},
    { timeout: 90000 },
  );
  return res.data;
}
