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

export async function uploadSessionFile(
  sessionId: string,
  fileUri: string,
  fileName: string,
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append('file', { uri: fileUri, name: fileName, type: 'audio/wav' } as unknown as Blob);
  const res = await apiClient.post<FileUploadResponse>(
    `/sessions/${sessionId}/files`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data;
}

export async function startAnalysis(sessionId: string): Promise<{ run_id: string; status: string }> {
  const res = await apiClient.post<{ run_id: string; status: string }>(
    `/sessions/${sessionId}/analyze`,
  );
  return res.data;
}
