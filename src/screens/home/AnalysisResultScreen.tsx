import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { COLORS } from '../../utils/colors';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackScreenProps, NativeStackNavigationProp } from '@react-navigation/native-stack';
import { getAnalysisResults } from '../../api/analysis';

// [deprecated] 구형 화면 - 아래 함수들은 폐기됨. null 반환 stub으로 유지.
const getAnalysisComparison = (_runId: string) => Promise.resolve(null);
const getAnalysisFeedback = (_sessionId: string) => Promise.resolve(null);
const comparePitch = (_sessionId: string, _songId: string) => Promise.resolve(null);
import { useGoals } from '../../context/GoalsContext';
import MetricCard from '../../components/MetricCard';
import ComparisonBar from '../../components/ComparisonBar';
import FeedbackCard from '../../components/FeedbackCard';
import PitchComparisonChart from '../../components/PitchComparisonChart';
import { getMetricLabel } from '../../utils/labels';
import type { Metric, Comparison, Feedback, PitchComparison, PitchFrame, ComparisonFrame } from '../../types/api';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;
type Tab = 'focus' | 'full';

/** 메트릭 key별 MetricCard 설정 */
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

/** 정확도를 색상으로 */
function getAccuracyColor(accuracy: number): string {
  if (accuracy >= 80) return COLORS.success;
  if (accuracy >= 60) return COLORS.warning;
  return COLORS.danger;
}

export default function AnalysisResultScreen({ route }: Props) {
  const { sessionId, runId, songId } = route.params as {
    sessionId: string;
    runId: string;
    songId?: string;
  };
  const navigation = useNavigation<NativeStackNavigationProp<Record<string, object | undefined>>>();
  const { goals } = useGoals();

  const [tab, setTab] = useState<Tab>('focus');
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [referenceName, setReferenceName] = useState('');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [pitchData, setPitchData] = useState<PitchComparison | null>(null);
  const [loading, setLoading] = useState(true);

  // Sequential reveal animation
  const [showGrade, setShowGrade] = useState(false);
  const [showPitch, setShowPitch] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const fadeGrade = useRef(new Animated.Value(0)).current;
  const fadePitch = useRef(new Animated.Value(0)).current;
  const fadeMetrics = useRef(new Animated.Value(0)).current;
  const fadeFeedback = useRef(new Animated.Value(0)).current;

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;

      const load = async () => {
        try {
          const promises: Promise<unknown>[] = [
            getAnalysisResults(runId),
            getAnalysisComparison(runId).catch(() => null),
            getAnalysisFeedback(sessionId),
          ];

          // 가사 비교 데이터 (songId가 있을 때)
          if (songId) {
            promises.push(comparePitch(sessionId, songId).catch(() => null));
          }

          const results = await Promise.all(promises);

          if (cancelled) return;

          const resultsData = results[0] as { metrics: Metric[] };
          const compData = results[1] as { reference_name: string; comparisons: Comparison[] } | null;
          const fbData = results[2] as Feedback;
          const pitchComp = songId ? (results[3] as PitchComparison | null) : null;

          setMetrics(resultsData.metrics);
          if (compData) {
            setComparisons(compData.comparisons);
            setReferenceName(compData.reference_name);
          }
          setFeedback(fbData);
          if (pitchComp) setPitchData(pitchComp);
        } catch {} finally {
          if (!cancelled) setLoading(false);
        }
      };

      load();
      return () => { cancelled = true; };
    }, [runId, sessionId, songId]),
  );

  // Sequential reveal animation after loading
  useEffect(() => {
    if (loading) return;

    const t1 = setTimeout(() => {
      setShowGrade(true);
      Animated.timing(fadeGrade, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 300);

    const t2 = setTimeout(() => {
      setShowPitch(true);
      Animated.timing(fadePitch, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 1200);

    const t3 = setTimeout(() => {
      setShowMetrics(true);
      Animated.timing(fadeMetrics, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 2000);

    const t4 = setTimeout(() => {
      setShowFeedback(true);
      Animated.timing(fadeFeedback, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    }, 2800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [loading, fadeGrade, fadePitch, fadeMetrics, fadeFeedback]);

  // 목표 관련 파라미터 키
  const goalParamKeys = useMemo(
    () => [...new Set(goals.map((g) => g.parameter))],
    [goals],
  );

  // 목표 관련 메트릭
  const goalMetrics = useMemo(
    () => metrics.filter((m) => goalParamKeys.includes(m.key)),
    [metrics, goalParamKeys],
  );

  // 목표 관련 비교 데이터
  const goalComparisons = useMemo(
    () => comparisons.filter((c) => goalParamKeys.includes(c.key)),
    [comparisons, goalParamKeys],
  );

  // 피드백 정렬: 목표 관련 개선점 최상단
  const sortedImprovements = useMemo(() => {
    if (!feedback) return [];
    const goalRelated: string[] = [];
    const others: string[] = [];
    const goalKeywords = goals.map((g) => getMetricLabel(g.parameter).toLowerCase());

    feedback.improvements.forEach((imp) => {
      const impLower = imp.toLowerCase();
      const isRelated = goalKeywords.some((kw) => impLower.includes(kw));
      if (isRelated) goalRelated.push(imp);
      else others.push(imp);
    });
    return [...goalRelated, ...others];
  }, [feedback, goals]);

  // Build original/user frames for PitchComparisonChart
  const originalFrames = useMemo(() => {
    if (!pitchData) return [];
    return pitchData.comparison.frames.map((f) => ({
      time_ms: f.time_ms,
      note: f.original_note,
      midi: f.original_midi,
    }));
  }, [pitchData]);

  const userFrames = useMemo(() => {
    if (!pitchData) return [];
    return pitchData.comparison.frames.map((f) => ({
      time_ms: f.time_ms,
      user_note: f.user_note,
      user_midi: f.user_midi,
      diff_semitones: f.diff_semitones,
    }));
  }, [pitchData]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>분석 결과를 불러오는 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 탭 바 */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tabItem, tab === 'focus' && styles.tabItemActive]}
          onPress={() => setTab('focus')}
        >
          <Text style={[styles.tabText, tab === 'focus' && styles.tabTextActive]}>
            📌 포커스 피드백
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tabItem, tab === 'full' && styles.tabItemActive]}
          onPress={() => setTab('full')}
        >
          <Text style={[styles.tabText, tab === 'full' && styles.tabTextActive]}>
            📊 전체 분석
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === 'focus' ? (
          <>
            {/* 1. 종합 평가 (with sequential reveal) */}
            {showGrade && feedback && (
              <Animated.View style={{ opacity: fadeGrade }}>
                <Text style={styles.sectionTitle}>종합 평가</Text>
                <FeedbackCard
                  grade={feedback.overall_grade}
                  comment={feedback.overall_comment}
                  strengths={feedback.strengths}
                  improvements={sortedImprovements}
                />
              </Animated.View>
            )}

            {/* 2. 음정 정확도 카드 (songId가 있을 때) */}
            {showPitch && pitchData && (
              <Animated.View style={{ opacity: fadePitch }}>
                <Text style={styles.sectionTitle}>🎵 음정 분석</Text>

                {/* 정확도 요약 카드 */}
                <View style={styles.pitchAccuracyCard}>
                  <View style={styles.pitchAccuracyHeader}>
                    <Text style={styles.pitchAccuracyTitle}>음정 정확도</Text>
                  </View>
                  <View style={styles.pitchAccuracyRow}>
                    <View style={styles.pitchAccuracyMain}>
                      <Text
                        style={[
                          styles.pitchAccuracyValue,
                          { color: getAccuracyColor(pitchData.comparison.overall_accuracy) },
                        ]}
                      >
                        {pitchData.comparison.overall_accuracy.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>정확 일치</Text>
                    </View>
                    <View style={styles.pitchAccuracySub}>
                      <Text
                        style={[
                          styles.pitchLenientValue,
                          { color: getAccuracyColor(pitchData.comparison.accuracy_lenient) },
                        ]}
                      >
                        {pitchData.comparison.accuracy_lenient.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>±1반음 허용</Text>
                    </View>
                  </View>

                  {/* 정확도 프로그레스 바 */}
                  <View style={styles.pitchProgressBg}>
                    <View
                      style={[
                        styles.pitchProgressFill,
                        {
                          width: `${Math.min(100, pitchData.comparison.overall_accuracy)}%`,
                          backgroundColor: getAccuracyColor(pitchData.comparison.overall_accuracy),
                        },
                      ]}
                    />
                  </View>

                  {/* 구간별 정확도 */}
                  {pitchData.comparison.sections.length > 0 && (
                    <View style={styles.pitchSectionsContainer}>
                      <Text style={styles.pitchSectionsTitle}>구간별 정확도</Text>
                      {pitchData.comparison.sections.map((sec, idx) => (
                        <View key={idx} style={styles.pitchSectionRow}>
                          <Text style={styles.pitchSectionLabel}>{sec.label}</Text>
                          <View style={styles.pitchSectionBarBg}>
                            <View
                              style={[
                                styles.pitchSectionBarFill,
                                {
                                  width: `${Math.min(100, sec.accuracy)}%`,
                                  backgroundColor: getAccuracyColor(sec.accuracy),
                                },
                              ]}
                            />
                          </View>
                          <Text
                            style={[
                              styles.pitchSectionValue,
                              { color: getAccuracyColor(sec.accuracy) },
                            ]}
                          >
                            {sec.accuracy.toFixed(0)}%
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>

                {/* 피치 비교 차트 */}
                <PitchComparisonChart
                  originalFrames={originalFrames}
                  userFrames={userFrames}
                  duration_ms={
                    pitchData.comparison.frames.length > 0
                      ? pitchData.comparison.frames[pitchData.comparison.frames.length - 1].time_ms
                      : 0
                  }
                />
              </Animated.View>
            )}

            {/* 3. 목표 연관 메트릭 */}
            {showMetrics && goals.length > 0 && (
              <Animated.View style={{ opacity: fadeMetrics }}>
                <Text style={styles.sectionTitle}>🎯 목표 관련 분석</Text>
                {goals.map((goal) => {
                  const metric = goalMetrics.find((m) => m.key === goal.parameter);
                  const comp = goalComparisons.find((c) => c.key === goal.parameter);
                  if (!metric) return null;

                  const diff = goal.direction === 'above'
                    ? goal.target - metric.value
                    : metric.value - goal.target;
                  const isAchieved = diff <= 0;
                  const diffAbs = Math.abs(diff);
                  const unit = metric.unit;

                  return (
                    <View key={goal.id} style={styles.goalMetricCard}>
                      <View style={styles.goalMetricHeader}>
                        <Text style={styles.goalMetricEmoji}>
                          {isAchieved ? '🎉' : '🎯'}
                        </Text>
                        <Text style={styles.goalMetricName}>{goal.name}</Text>
                      </View>

                      <View style={styles.goalMetricBody}>
                        <View style={styles.goalMetricRow}>
                          <Text style={styles.goalMetricLabel}>현재 값</Text>
                          <Text style={styles.goalMetricValue}>
                            {metric.key === 'egg_correlation'
                              ? metric.value.toFixed(2)
                              : metric.value.toFixed(1)}
                            {unit}
                          </Text>
                        </View>
                        <View style={styles.goalMetricRow}>
                          <Text style={styles.goalMetricLabel}>목표 값</Text>
                          <Text style={styles.goalMetricValue}>
                            {goal.target}{unit} {goal.direction === 'above' ? '이상' : '이하'}
                          </Text>
                        </View>
                      </View>

                      <View style={[
                        styles.goalStatusBadge,
                        { backgroundColor: isAchieved ? 'rgba(76,175,80,0.15)' : 'rgba(255,193,7,0.15)' },
                      ]}>
                        <Text style={[
                          styles.goalStatusText,
                          { color: isAchieved ? COLORS.success : COLORS.warning },
                        ]}>
                          {isAchieved
                            ? '🎉 목표 달성!'
                            : `목표까지 ${diffAbs.toFixed(1)}${unit ? unit.replace('%', '%p') : ''} 남았습니다`}
                        </Text>
                      </View>

                      {comp && (
                        <View style={styles.goalCompWrapper}>
                          <ComparisonBar
                            label={getMetricLabel(comp.key)}
                            userValue={comp.user_value}
                            referenceMean={comp.reference_mean}
                            zScore={comp.z_score}
                            percentile={comp.percentile}
                          />
                        </View>
                      )}
                    </View>
                  );
                })}
              </Animated.View>
            )}

            {/* 4. 추가 피드백 (full tab에 있던 것) */}
            {showFeedback && feedback && (
              <Animated.View style={{ opacity: fadeFeedback }}>
                <Text style={styles.sectionTitle}>💡 상세 피드백</Text>
                {feedback.improvements.length > 0 && (
                  <View style={styles.detailFeedbackCard}>
                    {feedback.improvements.map((item, idx) => (
                      <View key={idx} style={styles.detailFeedbackRow}>
                        <Text style={styles.detailFeedbackIcon}>📝</Text>
                        <Text style={styles.detailFeedbackText}>{item}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </Animated.View>
            )}
          </>
        ) : (
          /* ─── 전체 분석 탭 ─── */
          <>
            {/* 종합 평가 */}
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

            {/* 음정 정확도 (songId가 있을 때) */}
            {pitchData && (
              <>
                <Text style={styles.sectionTitle}>🎵 음정 분석</Text>
                <View style={styles.pitchAccuracyCard}>
                  <View style={styles.pitchAccuracyRow}>
                    <View style={styles.pitchAccuracyMain}>
                      <Text
                        style={[
                          styles.pitchAccuracyValue,
                          { color: getAccuracyColor(pitchData.comparison.overall_accuracy) },
                        ]}
                      >
                        {pitchData.comparison.overall_accuracy.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>정확 일치</Text>
                    </View>
                    <View style={styles.pitchAccuracySub}>
                      <Text
                        style={[
                          styles.pitchLenientValue,
                          { color: getAccuracyColor(pitchData.comparison.accuracy_lenient) },
                        ]}
                      >
                        {pitchData.comparison.accuracy_lenient.toFixed(1)}%
                      </Text>
                      <Text style={styles.pitchAccuracySubLabel}>±1반음 허용</Text>
                    </View>
                  </View>
                </View>
                <PitchComparisonChart
                  originalFrames={originalFrames}
                  userFrames={userFrames}
                  duration_ms={
                    pitchData.comparison.frames.length > 0
                      ? pitchData.comparison.frames[pitchData.comparison.frames.length - 1].time_ms
                      : 0
                  }
                />
              </>
            )}

            {/* 모든 메트릭 */}
            <Text style={styles.sectionTitle}>발성 분석 수치</Text>
            {metrics.length === 0 ? (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyText}>분석 결과가 아직 없습니다</Text>
              </View>
            ) : (
              metrics.map((m) => {
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
              })
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
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  loadingText: { marginTop: 12, fontSize: 14, color: COLORS.textSecondary },

  // Tabs
  tabBar: {
    flexDirection: 'row',
    backgroundColor: COLORS.card,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.divider,
  },
  tabItem: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabItemActive: {
    borderBottomColor: COLORS.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textMuted,
  },
  tabTextActive: {
    color: COLORS.primary,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    marginTop: 8,
  },

  // ─── Pitch accuracy card ───
  pitchAccuracyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  pitchAccuracyHeader: {
    marginBottom: 12,
  },
  pitchAccuracyTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.textSecondary,
  },
  pitchAccuracyRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    marginBottom: 16,
  },
  pitchAccuracyMain: {
    alignItems: 'center',
  },
  pitchAccuracyValue: {
    fontSize: 36,
    fontWeight: '800',
  },
  pitchAccuracySubLabel: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 4,
  },
  pitchAccuracySub: {
    alignItems: 'center',
  },
  pitchLenientValue: {
    fontSize: 28,
    fontWeight: '700',
  },
  pitchProgressBg: {
    height: 8,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 16,
  },
  pitchProgressFill: {
    height: '100%',
    borderRadius: 4,
  },
  pitchSectionsContainer: {
    marginTop: 4,
  },
  pitchSectionsTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  pitchSectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  pitchSectionLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    width: 80,
  },
  pitchSectionBarBg: {
    flex: 1,
    height: 6,
    backgroundColor: COLORS.surface,
    borderRadius: 3,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  pitchSectionBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  pitchSectionValue: {
    fontSize: 12,
    fontWeight: '600',
    width: 38,
    textAlign: 'right',
  },

  // ─── Detail feedback ───
  detailFeedbackCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  detailFeedbackRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  detailFeedbackIcon: {
    fontSize: 16,
    marginRight: 8,
    marginTop: 1,
  },
  detailFeedbackText: {
    flex: 1,
    fontSize: 14,
    color: COLORS.textPrimary,
    lineHeight: 20,
  },

  // Goal metric cards
  goalMetricCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  goalMetricHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  goalMetricEmoji: { fontSize: 22, marginRight: 8 },
  goalMetricName: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, flex: 1 },
  goalMetricBody: { marginBottom: 10 },
  goalMetricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  goalMetricLabel: { fontSize: 14, color: COLORS.textSecondary },
  goalMetricValue: { fontSize: 14, fontWeight: '600', color: COLORS.textPrimary },
  goalStatusBadge: {
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 8,
  },
  goalStatusText: { fontSize: 14, fontWeight: '600' },
  goalCompWrapper: { marginTop: 4 },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textSecondary },
});
