import { pollAnalysisStatus, getAnalysisResults } from './analysis';
import { AnalyzeStatusError, isAnalyzeFailureStatus } from './sessions';
import { MOCK_FIXED_RESULT } from './mock';
import type { AnalyzeResult, ServerAnalyzeResult, ServerAnalyzeResultsResponse, ScoreEntry, FeedbackEntry, ScoreMetaEntry, Zone } from '../types/analyze';
import type { EvaluationItemKey } from '../domain/evaluationItems';

const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === 'true';

// ─── prefix 어댑터 ───
// 서버 키 "1_nasal_oral_ratio" → 도메인 키 "nasal_oral_ratio"
function stripPrefix(key: string): EvaluationItemKey {
  return key.replace(/^\d+_/, '') as EvaluationItemKey;
}

// v2 chunk score: zone 필드 없음 → rounded_score로 유도
//  0~1 → insufficient / 2~3 → appropriate / 4~5 → excessive
function deriveZone(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

// chunk.scores raw entry → 내부 표현 (zone derive 포함)
function adaptChunkScore(raw: { ai_score: number; zone?: Zone; rounded_score?: number; tier?: 'high'|'high_star' }) {
  return {
    aiScore:      raw.ai_score,
    zone:         raw.zone ?? (typeof raw.rounded_score === 'number' ? deriveZone(raw.rounded_score) : undefined),
    roundedScore: raw.rounded_score,
    tier:         raw.tier,
  };
}

function adaptServerResult(response: ServerAnalyzeResultsResponse): AnalyzeResult {
  const inner: ServerAnalyzeResult = response.result_json;
  if (isAnalyzeFailureStatus(inner.status)) {
    throw new AnalyzeStatusError({ run_id: inner.run_id, status: inner.status });
  }
  const isV2 = inner.score_mapper_version === 'v2' && !!inner.scores_v2;

  return {
    run_id:              inner.run_id,
    session_id:          response.session_id,
    status:              inner.status,
    processing_time_ms:  inner.processing_time_ms,
    audio_info:          inner.audio_info,
    registers:           inner.registers,
    indicators:          inner.indicators,
    register_boundaries: inner.register_boundaries,
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
      shownV2:        inner.reliability.shown_v2?.map(stripPrefix),
      academicOnlyV2: inner.reliability.academic_only_v2?.map(stripPrefix),
      deferredV2:     inner.reliability.deferred_v2?.map(stripPrefix),
    },
    timelineScores: (inner.timeline_scores ?? []).map((chunk) => ({
      startSec:       chunk.start_sec,
      endSec:         chunk.end_sec,
      lrcText:        chunk.lrc_text,
      chunkDurationS: chunk.chunk_duration_s,
      scores: {
        breathiness:      chunk.scores['4_breathiness']        ? adaptChunkScore(chunk.scores['4_breathiness'])        : undefined,
        vocalFoldContact: chunk.scores['3_vocal_fold_contact'] ? adaptChunkScore(chunk.scores['3_vocal_fold_contact']) : undefined,
        softPalate:       chunk.scores['6_soft_palate']        ? adaptChunkScore(chunk.scores['6_soft_palate'])        : undefined,
        tongueTension:    chunk.scores['8_tongue_tension']     ? adaptChunkScore(chunk.scores['8_tongue_tension'])     : undefined,
      },
      lowConfidenceItems: chunk.low_confidence_items,
    })),
    timelineMetadata: inner.timeline_metadata ? {
      chunkMethod:           inner.timeline_metadata.chunk_method ?? '',
      shownIndicators:       inner.timeline_metadata.shown_indicators,
      shownIndicatorsReason: inner.timeline_metadata.shown_indicators_reason,
    } : undefined,
    userF0: inner.user_f0 ? { frameHz: inner.user_f0.frame_hz, values: inner.user_f0.values } : null,
    // v2 신규 매핑
    scoreMapperVersion: isV2 ? 'v2' : (inner.score_mapper_version ?? 'v1'),
    scoresV2: inner.scores_v2
      ? (Object.fromEntries(
          Object.entries(inner.scores_v2).map(([k, v]) => [stripPrefix(k), v]),
        ) as Partial<Record<EvaluationItemKey, number>>)
      : undefined,
    scoresMeta: inner.scores_meta
      ? (Object.fromEntries(
          Object.entries(inner.scores_meta).map(([k, m]) => [
            stripPrefix(k),
            {
              tier:         m.tier,
              caveats:      m.caveats,
              displayMark:  m.display_mark,
              tooltip:      m.tooltip,
              roundedScore: m.rounded_score,
              icc:          m.icc,
              iccRatio:     m.icc_ratio,
            } as ScoreMetaEntry,
          ]),
        ) as Partial<Record<EvaluationItemKey, ScoreMetaEntry>>)
      : undefined,
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
