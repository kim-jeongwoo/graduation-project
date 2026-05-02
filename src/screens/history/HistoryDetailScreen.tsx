import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { getSessionDetail } from '../../api/sessions';
// [deprecated] 구형 화면 - 모든 분석 API stub으로 유지. P1에서 EvalResultScreen으로 대체.
const getAnalysisResults = (_runId: string) => Promise.resolve({ metrics: [] as never[] });
const getAnalysisComparison = (_runId: string) => Promise.resolve(null as { comparisons: never[]; reference_name: string } | null);
const getAnalysisFeedback = (_sessionId: string) => Promise.resolve(null);
import { TouchableOpacity } from 'react-native';
import MetricCard from '../../components/MetricCard';
import ComparisonBar from '../../components/ComparisonBar';
import FeedbackCard from '../../components/FeedbackCard';
import StatusBadge from '../../components/StatusBadge';
import { getMetricLabel, formatDate, formatDuration } from '../../utils/labels';
import { mockAnalysisResults, mockSessions } from '../../mock/mockData';
import type { Metric, Comparison, Feedback, SessionDetail } from '../../types/api';
import { COLORS } from '../../utils/colors';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

type NavProp = { navigate: (screen: string, params?: Record<string, unknown>) => void };

interface PrevDelta {
  key: string;
  current: number;
  previous: number;
  diff: number;
  unit: string;
}

function getMetricConfig(key: string) {
  switch (key) {
    case 'egg_correlation':
      return { type: 'gauge' as const, range: { min: 0, max: 1 } };
    case 'contact_rate':
      return {
        type: 'gauge' as const,
        range: { min: 0, max: 100, optimalMin: 40, optimalMax: 50 },
      };
    case 'chest_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '흉성',
        rightLabel: '두성',
      };
    case 'oral_nasal_ratio':
      return {
        type: 'ratio' as const,
        range: { min: 0, max: 100 },
        leftLabel: '구강',
        rightLabel: '비강',
      };
    case 'processing_time_ms':
      return { type: 'text' as const };
    default:
      return { type: 'gauge' as const, range: { min: 0, max: 100 } };
  }
}

export default function HistoryDetailScreen({ route, navigation }: Props) {
  const { sessionId } = (route.params ?? {}) as { sessionId: string };
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [referenceName, setReferenceName] = useState('');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      const load = async () => {
        try {
          const sessionData = await getSessionDetail(sessionId);
          if (cancelled) return;
          setDetail(sessionData);

          if (sessionData.analysis) {
            const runId = sessionData.analysis.run_id;
            const [resultsData, compData, fbData] = await Promise.all([
              getAnalysisResults(runId),
              getAnalysisComparison(runId).catch(() => null),
              getAnalysisFeedback(sessionId),
            ]);
            if (cancelled) return;
            setMetrics(resultsData.metrics);
            if (compData) {
              setComparisons(compData.comparisons);
              setReferenceName(compData.reference_name);
            }
            setFeedback(fbData);
          }
        } catch (e: unknown) {
          console.log('[HistoryDetail] error:', e);
        } finally {
          if (!cancelled) setLoading(false);
        }
      };
      load();
      return () => {
        cancelled = true;
      };
    }, [sessionId]),
  );

  // 같은 곡 시도 존재 여부
  const hasSameSongAttempts = useMemo(() => {
    if (!detail?.song_title) return false;
    return (
      mockSessions.filter(
        (s) =>
          s.status === 'completed' &&
          s.song_title === detail.song_title &&
          s.session_id !== sessionId,
      ).length > 0
    );
  }, [detail, sessionId]);

  // 이전 세션 대비 변화 계산
  const prevDeltas: PrevDelta[] = useMemo(() => {
    const completedSorted = mockSessions
      .filter((s) => s.status === 'completed')
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    const currentIdx = completedSorted.findIndex((s) => s.session_id === sessionId);
    if (currentIdx <= 0) return [];

    const prevSession = completedSorted[currentIdx - 1];
    const currentResult = mockAnalysisResults[sessionId];
    const prevResult = mockAnalysisResults[prevSession.session_id];
    if (!currentResult || !prevResult) return [];

    const deltas: PrevDelta[] = [];
    const skipKeys = new Set(['processing_time_ms', 'egg_estimation_status']);

    currentResult.metrics.forEach((cm) => {
      if (skipKeys.has(cm.key)) return;
      const pm = prevResult.metrics.find((m) => m.key === cm.key);
      if (!pm) return;
      deltas.push({
        key: cm.key,
        current: cm.value,
        previous: pm.value,
        diff: cm.value - pm.value,
        unit: cm.unit,
      });
    });
    return deltas;
  }, [sessionId]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (!detail) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>세션 정보를 불러올 수 없습니다</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 세션 정보 */}
      <View style={styles.titleRow}>
        <Text style={styles.songTitle}>{detail.song_title ?? '제목 없음'}</Text>
        <StatusBadge status={detail.status} />
      </View>

      <View style={styles.infoCard}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>생성일</Text>
          <Text style={styles.infoValue}>{formatDate(detail.created_at)}</Text>
        </View>
        {detail.files.length > 0 && (
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>재생시간</Text>
            <Text style={styles.infoValue}>{formatDuration(detail.files[0].duration_ms)}</Text>
          </View>
        )}
      </View>

      {/* 피드백 */}
      {feedback && (
        <>
          <Text style={styles.sectionTitle}>종합 평가</Text>
          <FeedbackCard
            grade={feedback.overall_grade}
            comment={feedback.overall_comment}
            strengths={feedback.strengths}
            improvements={feedback.improvements}
          />
        </>
      )}

      {/* 이전 세션 대비 변화 */}
      {prevDeltas.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>이전 세션 대비 변화</Text>
          <View style={styles.deltaCard}>
            {prevDeltas.map((d) => {
              const isUp = d.diff > 0;
              const isZero = d.diff === 0;
              const arrow = isZero ? '→' : isUp ? '↑' : '↓';
              const diffColor = isZero ? COLORS.textSecondary : isUp ? COLORS.success : COLORS.danger;
              const diffAbs = Math.abs(d.diff);
              const formatted =
                d.key === 'egg_correlation' ? diffAbs.toFixed(2) : diffAbs.toFixed(1);

              return (
                <View key={d.key} style={styles.deltaRow}>
                  <Text style={styles.deltaLabel}>{getMetricLabel(d.key)}</Text>
                  <View style={styles.deltaRight}>
                    <Text style={styles.deltaPrev}>
                      {d.key === 'egg_correlation'
                        ? d.previous.toFixed(2)
                        : d.previous.toFixed(1)}
                      {d.unit}
                    </Text>
                    <Text style={[styles.deltaArrow, { color: diffColor }]}>{arrow}</Text>
                    <Text style={[styles.deltaCurr, { color: diffColor }]}>
                      {d.key === 'egg_correlation'
                        ? d.current.toFixed(2)
                        : d.current.toFixed(1)}
                      {d.unit}
                    </Text>
                    <View style={[styles.deltaBadge, { backgroundColor: diffColor + '1A' }]}>
                      <Text style={[styles.deltaBadgeText, { color: diffColor }]}>
                        {arrow} {formatted}
                        {d.unit}
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        </>
      )}

      {/* 메트릭 */}
      {metrics.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>발성 분석 수치</Text>
          {metrics.map((m) => {
            const config = getMetricConfig(m.key);
            return (
              <MetricCard
                key={m.key}
                label={getMetricLabel(m.key)}
                value={m.value}
                unit={m.unit}
                type={config.type}
                range={'range' in config ? config.range : undefined}
                leftLabel={'leftLabel' in config ? config.leftLabel : undefined}
                rightLabel={'rightLabel' in config ? config.rightLabel : undefined}
              />
            );
          })}
        </>
      )}

      {/* 숙련자 비교 */}
      {comparisons.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>
            {'숙련자 비교' + (referenceName ? ` — ${referenceName}` : '')}
          </Text>
          {comparisons.map((c) => (
            <ComparisonBar
              key={c.key}
              label={getMetricLabel(c.key)}
              userValue={c.user_value}
              referenceMean={c.reference_mean}
              zScore={c.z_score}
              percentile={c.percentile}
            />
          ))}
        </>
      )}

      {/* 같은 곡 시도 비교 */}
      {hasSameSongAttempts && detail?.song_title && (
        <TouchableOpacity
          style={styles.songCompareButton}
          onPress={() =>
            (navigation as unknown as NavProp).navigate('SongComparison', {
              songTitle: detail.song_title,
            })
          }
        >
          <Text style={styles.songCompareButtonText}>🎵 같은 곡 시도 비교</Text>
        </TouchableOpacity>
      )}

      {/* 분석 결과 없는 경우 */}
      {metrics.length === 0 && !feedback && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>이 세션에는 분석 결과가 없습니다</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },

  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  songTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    flex: 1,
    marginRight: 8,
  },

  infoCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  infoLabel: { fontSize: 14, color: COLORS.textSecondary },
  infoValue: { fontSize: 14, fontWeight: '500', color: COLORS.textPrimary },

  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    marginTop: 8,
  },

  // 이전 세션 대비 변화
  deltaCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  deltaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.divider,
  },
  deltaLabel: { fontSize: 14, color: COLORS.textSecondary, flex: 1 },
  deltaRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  deltaPrev: { fontSize: 13, color: COLORS.textMuted },
  deltaArrow: { fontSize: 16, fontWeight: '700' },
  deltaCurr: { fontSize: 14, fontWeight: '600' },
  deltaBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginLeft: 4,
  },
  deltaBadgeText: { fontSize: 11, fontWeight: '600' },

  songCompareButton: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 16,
    marginTop: 8,
  },
  songCompareButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.primaryLight,
  },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textMuted },
});
