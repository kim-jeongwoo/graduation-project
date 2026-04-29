import type {
  AnalyzeResponse,
  AnalysisStatus,
  AnalysisResults,
  AnalysisComparison,
  Feedback,
} from '../types/api';
import {
  mockAnalysisResults,
  mockComparisons,
  mockFeedback,
} from '../mock/mockData';

/** 분석 요청 (mock: 2초 딜레이 후 completed 반환) */
export async function requestAnalysis(sessionId: string): Promise<AnalyzeResponse> {
  console.log('[MOCK] requestAnalysis:', sessionId);
  await new Promise((r) => setTimeout(r, 2000));
  const result = mockAnalysisResults[sessionId];
  return {
    run_id: result?.run_id ?? `run-new-${Date.now()}`,
    status: 'completed',
  };
}

/** 분석 상태 조회 */
export async function getAnalysisStatus(runId: string): Promise<AnalysisStatus> {
  console.log('[MOCK] getAnalysisStatus:', runId);
  // runId → sessionId 매핑
  const sessionId = Object.keys(mockAnalysisResults).find(
    (k) => mockAnalysisResults[k].run_id === runId,
  );
  return {
    run_id: runId,
    session_id: sessionId ?? '',
    model_name: 'vocal-analyzer-v2',
    status: 'completed',
    requested_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
  };
}

/** 분석 결과 조회 */
export async function getAnalysisResults(runId: string): Promise<AnalysisResults> {
  console.log('[MOCK] getAnalysisResults:', runId);
  const sessionId = Object.keys(mockAnalysisResults).find(
    (k) => mockAnalysisResults[k].run_id === runId,
  );
  const result = sessionId ? mockAnalysisResults[sessionId] : null;
  return {
    run_id: runId,
    metrics: result?.metrics ?? [],
  };
}

/** 비교 조회 */
export async function getAnalysisComparison(runId: string): Promise<AnalysisComparison> {
  console.log('[MOCK] getAnalysisComparison:', runId);
  const sessionId = Object.keys(mockAnalysisResults).find(
    (k) => mockAnalysisResults[k].run_id === runId,
  );
  const comp = sessionId ? mockComparisons[sessionId] : null;
  return {
    run_id: runId,
    reference_name: comp?.reference_name ?? '',
    comparisons: comp?.comparisons ?? [],
  };
}

/** 피드백 조회 (세션 ID로) */
export async function getAnalysisFeedback(sessionId: string): Promise<Feedback | null> {
  console.log('[MOCK] getAnalysisFeedback:', sessionId);
  return mockFeedback[sessionId] ?? null;
}
