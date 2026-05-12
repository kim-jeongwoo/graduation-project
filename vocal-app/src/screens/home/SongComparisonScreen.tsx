import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import {
  mockSessions,
  mockAnalysisResults,
  mockFeedback,
  mockComparisons,
} from '../../mock/mockData';
import TrendChart from '../../components/TrendChart';
import type { DataPoint } from '../../components/TrendChart';
import { formatDate, getGradeColor, getMetricLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

const METRIC_KEYS = ['contact_rate', 'chest_ratio', 'oral_nasal_ratio'];
const METRIC_UNITS: Record<string, string> = {
  contact_rate: '%',
  chest_ratio: '%',
  oral_nasal_ratio: '%',
};

export default function SongComparisonScreen({ route }: Props) {
  const { songTitle } = (route.params ?? {}) as { songTitle: string };
  const [selectedMetric, setSelectedMetric] = useState(METRIC_KEYS[0]);

  // 같은 곡 completed 세션 (시간순)
  const sameSongSessions = useMemo(
    () =>
      mockSessions
        .filter((s) => s.song_title === songTitle && s.status === 'completed')
        .sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        ),
    [songTitle],
  );

  // 트렌드 데이터
  const { datasets, referenceMeans } = useMemo(() => {
    const ds: Record<string, DataPoint[]> = {};
    const refs: Record<string, number> = {};
    METRIC_KEYS.forEach((key) => {
      ds[key] = [];
    });

    sameSongSessions.forEach((s, idx) => {
      const result = mockAnalysisResults[s.session_id];
      if (!result) return;
      const label = `${idx + 1}회`;
      result.metrics.forEach((m) => {
        if (ds[m.key]) {
          ds[m.key].push({ sessionLabel: label, value: m.value });
        }
      });
    });

    // 첫 세션의 비교 데이터에서 reference_mean
    const firstComp = sameSongSessions[0]
      ? mockComparisons[sameSongSessions[0].session_id]
      : undefined;
    if (firstComp) {
      firstComp.comparisons.forEach((c) => {
        refs[c.key] = c.reference_mean;
      });
    }

    return { datasets: ds, referenceMeans: refs };
  }, [sameSongSessions]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 헤더 */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{songTitle}</Text>
        <Text style={styles.headerSub}>{sameSongSessions.length}회 시도</Text>
      </View>

      {/* 시도별 카드 */}
      {sameSongSessions.map((s, idx) => {
        const fb = mockFeedback[s.session_id];
        const result = mockAnalysisResults[s.session_id];
        const grade = fb?.overall_grade ?? '-';
        const gradeColor = getGradeColor(grade);

        return (
          <View key={s.session_id} style={styles.attemptCard}>
            <View style={styles.attemptHeader}>
              <Text style={styles.attemptLabel}>{idx + 1}회차</Text>
              <View
                style={[
                  styles.gradeBadge,
                  { backgroundColor: gradeColor + '1A' },
                ]}
              >
                <Text style={[styles.gradeText, { color: gradeColor }]}>
                  {grade}
                </Text>
              </View>
            </View>
            <Text style={styles.attemptDate}>{formatDate(s.created_at)}</Text>
            {result && (
              <View style={styles.metricsRow}>
                {METRIC_KEYS.map((key) => {
                  const m = result.metrics.find((met) => met.key === key);
                  if (!m) return null;
                  return (
                    <View key={key} style={styles.miniMetric}>
                      <Text style={styles.miniMetricLabel}>
                        {getMetricLabel(key)}
                      </Text>
                      <Text style={styles.miniMetricValue}>
                        {m.value.toFixed(1)}
                        {m.unit}
                      </Text>
                    </View>
                  );
                })}
              </View>
            )}
          </View>
        );
      })}

      {/* 추이 그래프 */}
      {sameSongSessions.length >= 2 && (
        <View style={styles.chartSection}>
          <Text style={styles.sectionTitle}>시도 간 추이</Text>

          {/* 파라미터 선택 칩 */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.chipScroll}
            contentContainerStyle={styles.chipRow}
          >
            {METRIC_KEYS.map((key) => (
              <TouchableOpacity
                key={key}
                style={[
                  styles.chip,
                  selectedMetric === key && styles.chipActive,
                ]}
                onPress={() => setSelectedMetric(key)}
              >
                <Text
                  style={[
                    styles.chipText,
                    selectedMetric === key && styles.chipTextActive,
                  ]}
                >
                  {getMetricLabel(key)}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <TrendChart
            datasets={{ [selectedMetric]: datasets[selectedMetric] ?? [] }}
            units={{ [selectedMetric]: METRIC_UNITS[selectedMetric] ?? '' }}
            referenceMeans={referenceMeans}
            parameterKeys={[selectedMetric]}
            height={200}
          />
        </View>
      )}

      {sameSongSessions.length === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>같은 곡의 완료된 세션이 없습니다</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },

  header: {
    marginBottom: 16,
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  headerSub: { fontSize: 14, color: COLORS.textSecondary, marginTop: 4 },

  attemptCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  attemptHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  attemptLabel: { fontSize: 15, fontWeight: '700', color: COLORS.textPrimary },
  gradeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    minWidth: 42,
    alignItems: 'center',
  },
  gradeText: { fontSize: 15, fontWeight: '800' },
  attemptDate: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 10 },

  metricsRow: { flexDirection: 'row', gap: 8 },
  miniMetric: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    padding: 8,
    alignItems: 'center',
  },
  miniMetricLabel: { fontSize: 10, color: COLORS.textSecondary, marginBottom: 2 },
  miniMetricValue: { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary },

  chartSection: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginTop: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
  },
  chipScroll: { marginBottom: 12 },
  chipRow: { gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: COLORS.divider,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  chipText: { fontSize: 13, color: COLORS.textSecondary },
  chipTextActive: { color: '#FFF', fontWeight: '600' },

  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 14, color: COLORS.textSecondary },
});
