import type {
  CreateSessionRequest,
  Session,
  SessionDetail,
  FileUploadResponse,
} from '../types/api';
import { mockSessions, mockFiles, mockAnalysisResults } from '../mock/mockData';

// mock 세션 목록 (런타임에 새 세션 추가 가능)
let runtimeSessions = [...mockSessions];
let mockIdCounter = 100;

export async function createSession(data: CreateSessionRequest): Promise<Session> {
  console.log('[MOCK] createSession:', data);
  const newSession: Session = {
    session_id: `mock-${++mockIdCounter}`,
    song_title: data.song_title,
    song_id: data.song_id,
    status: 'created',
    started_at: undefined,
    created_at: new Date().toISOString(),
  };
  runtimeSessions = [newSession, ...runtimeSessions];
  return newSession;
}

export async function getSessions(): Promise<Session[]> {
  console.log('[MOCK] getSessions');
  return runtimeSessions;
}

export async function getSessionDetail(sessionId: string): Promise<SessionDetail> {
  console.log('[MOCK] getSessionDetail:', sessionId);
  const session = runtimeSessions.find((s) => s.session_id === sessionId);
  if (!session) throw new Error('세션을 찾을 수 없습니다.');

  const files = mockFiles[sessionId] ?? [];
  const analysis = mockAnalysisResults[sessionId]
    ? { run_id: mockAnalysisResults[sessionId].run_id, status: mockAnalysisResults[sessionId].status }
    : null;

  return { ...session, files, analysis };
}

export async function uploadSessionFile(
  sessionId: string,
  fileUri: string,
  fileName: string,
): Promise<FileUploadResponse> {
  console.log('[MOCK] uploadSessionFile:', sessionId, fileName);
  return {
    file_id: `f-mock-${Date.now()}`,
    file_type: 'wav',
    storage_uri: fileUri,
    duration_ms: 180000,
  };
}
