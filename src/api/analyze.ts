import { BASE_URL } from './client';
import { pollAnalysisStatus, getAnalysisResults } from './analysis';
import { MOCK_FIXED_RESULT } from './mock';
import type { AnalyzeResult, ServerAnalyzeResult, ServerAnalyzeResultsResponse, ScoreEntry, FeedbackEntry } from '../types/analyze';
import type { EvaluationItemKey } from '../domain/evaluationItems';

const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === 'true';

// 부팅 시 환경 확인용 로그
console.log('[boot] USE_MOCK=', USE_MOCK, 'API_URL=', BASE_URL);

// ─── prefix 어댑터 ───
// 서버 키 "1_nasal_oral_ratio" → 도메인 키 "nasal_oral_ratio"
function stripPrefix(key: string): EvaluationItemKey {
  return key.replace(/^\d+_/, '') as EvaluationItemKey;
}

function adaptServerResult(response: ServerAnalyzeResultsResponse): AnalyzeResult {
  const inner: ServerAnalyzeResult = response.result_json;
  return {
    ...inner,
    scores: Object.fromEntries(
      Object.entries(inner.scores).map(([k, v]) => [stripPrefix(k), v]),
    ) as Record<EvaluationItemKey, ScoreEntry>,
    feedback: Object.fromEntries(
      Object.entries(inner.feedback).map(([k, v]) => [stripPrefix(k), v]),
    ) as Record<EvaluationItemKey, FeedbackEntry>,
    reliability: {
      high_reliability:   inner.reliability.high_reliability.map(stripPrefix),
      medium_reliability: inner.reliability.medium_reliability.map(stripPrefix),
      unavailable:        inner.reliability.unavailable.map(stripPrefix),
    },
  };
}

// ─── P0 검증용: run_id로 직접 결과 조회 ───
// USE_MOCK=true 이거나 runId 없으면 mock 반환
export async function getResultsByRunId(runId?: string): Promise<AnalyzeResult> {
  if (USE_MOCK || !runId) {
    await new Promise<void>((resolve) => setTimeout(resolve, 800));
    return MOCK_FIXED_RESULT;
  }
  await pollAnalysisStatus(runId);
  const raw = await getAnalysisResults(runId);
  return adaptServerResult(raw);
}

// ─── P1에서 호출자 연결 예정: WAV 업로드 → 분석 시작 → 결과 조회 ───
export interface AnalyzeRequest {
  sessionId: string;
  fileUri: string;
  fileName: string;
}

export async function analyzeRecording(request: AnalyzeRequest): Promise<AnalyzeResult> {
  if (USE_MOCK) {
    await new Promise<void>((resolve) => setTimeout(resolve, 1500));
    return MOCK_FIXED_RESULT;
  }
  // P1에서 구현: uploadSessionFile → startAnalysis → getResultsByRunId
  throw new Error('analyzeRecording: P1에서 구현 예정');
}

export { MOCK_FIXED_RESULT };
