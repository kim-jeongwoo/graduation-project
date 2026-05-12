import apiClient from './client';
import {
  AnalyzeStatusError,
  isAnalyzeFailureStatus,
  isAnalyzeSuccessStatus,
} from './sessions';
import type { AnalysisStatus } from '../types/api';
import type { ServerAnalyzeResultsResponse } from '../types/analyze';

export async function getAnalysisStatus(runId: string): Promise<AnalysisStatus> {
  const res = await apiClient.get<AnalysisStatus>(`/analysis/${runId}`);
  return res.data;
}

export async function getAnalysisResults(runId: string): Promise<ServerAnalyzeResultsResponse> {
  const res = await apiClient.get<ServerAnalyzeResultsResponse>(`/analysis/${runId}/results`);
  return res.data;
}

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS  = 120_000;

// status가 성공/실패 terminal 상태가 될 때까지 폴링. 실패 terminal은 throw.
export async function pollAnalysisStatus(runId: string): Promise<AnalysisStatus> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const status = await getAnalysisStatus(runId);
    if (isAnalyzeSuccessStatus(status.status)) {
      return status;
    }
    if (isAnalyzeFailureStatus(status.status)) {
      throw new AnalyzeStatusError(status);
    }
    await new Promise<void>((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error('분석 시간이 초과되었습니다 (120초). 잠시 후 다시 시도해주세요.');
}
