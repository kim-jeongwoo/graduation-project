import apiClient from './client';
import type { AnalysisStatus } from '../types/api';
import type { ServerAnalyzeResult } from '../types/analyze';

export async function getAnalysisStatus(runId: string): Promise<AnalysisStatus> {
  const res = await apiClient.get<AnalysisStatus>(`/analysis/${runId}`);
  return res.data;
}

export async function getAnalysisResults(runId: string): Promise<ServerAnalyzeResult> {
  const res = await apiClient.get<ServerAnalyzeResult>(`/analysis/${runId}/results`);
  return res.data;
}

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS  = 120_000;

// status가 completed/failed 될 때까지 폴링. 타임아웃 시 throw.
export async function pollAnalysisStatus(runId: string): Promise<AnalysisStatus> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const status = await getAnalysisStatus(runId);
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error('분석 시간이 초과되었습니다 (120초). 잠시 후 다시 시도해주세요.');
}
