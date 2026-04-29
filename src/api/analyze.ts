import apiClient from './client';
import type { AnalyzeResult, UploadRecordingRequest } from '../types/analyze';
import { mockAnalyze, MOCK_FIXED_RESULT } from './mock';

// TODO: 백엔드 명세 확정 시 false로 전환 후 realAnalyze 구현
const USE_MOCK = true;

async function realAnalyze(_request: UploadRecordingRequest): Promise<AnalyzeResult> {
  // TODO: 엔드포인트 및 요청 형식은 server 명세 확정 후 구현
  const response = await apiClient.post<AnalyzeResult>('/analyze', _request);
  return response.data;
}

export const analyzeApi = {
  analyze: USE_MOCK
    ? (request: UploadRecordingRequest) => mockAnalyze({ fileUri: request.fileUri })
    : realAnalyze,
};

export { MOCK_FIXED_RESULT };
