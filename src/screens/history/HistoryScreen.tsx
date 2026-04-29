import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  Modal,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { getSessions } from '../../api/sessions';
import {
  mockAnalysisResults,
  mockFeedback,
  mockComparisons,
} from '../../mock/mockData';
import TrendChart from '../../components/TrendChart';
import type { DataPoint } from '../../components/TrendChart';
import { formatDate, getGradeColor, getMetricLabel } from '../../utils/labels';
import type { Session } from '../../types/api';
import { COLORS } from '../../utils/colors';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

// EGG 제거, 종합등급 추가
const PARAM_KEYS = ['contact_rate', 'chest_ratio', 'oral_nasal_ratio', 'grade'];
const PARAM_LABELS: Record<string, string> = {
  contact_rate: '성대접촉률',
  chest_ratio: '흉성/두성',
  oral_nasal_ratio: '구강/비강',
  grade: '종합등급',
};
const PARAM_UNITS: Record<string, string> = {
  contact_rate: '%',
  chest_ratio: '%',
  oral_nasal_ratio: '%',
  grade: '점',
};

type FilterMode = 'all' | 'song';

/** 등급 → 수치 변환 */
function gradeToNumber(grade: string): number {
  const map: Record<string, number> = {
    'A+': 10, 'A': 9, 'A-': 8,
    'B+': 7, 'B': 6, 'B-': 5,
    'C+': 4, 'C': 3, 'C-': 2,
    'D+': 1, 'D': 0.5, 'D-': 0,
  };
  return map[grade] ?? 5;
}

export default function HistoryScreen({ navigation }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 필터
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [selectedSong, setSelectedSong] = useState<string | null>(null);
  const [songPickerVisible, setSongPickerVisible] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      const sorted = [...data].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setSessions(sorted);
    } catch (e: unknown) {
      console.log('[HistoryScreen] error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      loadSessions();
    }, [loadSessions]),
  );

  // completed 세션만 (오래된 순 for trend)
  const allCompletedSessions = useMemo(
    () =>
      sessions
        .filter((s) => s.status === 'completed')
        .sort(
          (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        ),
    [sessions],
  );

  // 중복 제거한 곡 목록
  const songTitles = useMemo(() => {
    const titles = new Set<string>();
    allCompletedSessions.forEach((s) => {
      if (s.song_title) titles.add(s.song_title);
    });
    return Array.from(titles);
  }, [allCompletedSessions]);

  // 필터 적용된 세션
  const filteredSessions = useMemo(() => {
    if (filterMode === 'song' && selectedSong) {
      return allCompletedSessions.filter((s) => s.song_title === selectedSong);
    }
    return allCompletedSessions;
  }, [allCompletedSessions, filterMode, selectedSong]);

  // 같은 곡 시도 횟수 맵
  const songAttemptCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    allCompletedSessions.forEach((s) => {
      const title = s.song_title ?? '';
      counts[title] = (counts[title] ?? 0) + 1;
    });
    return counts;
  }, [allCompletedSessions]);

  // 같은 곡 내에서 회차 계산
  const getAttemptNumber = useCallback(
    (session: Session): number | null => {
      const title = session.song_title ?? '';
      if ((songAttemptCounts[title] ?? 0) <= 1) return null;
      const sameSong = allCompletedSessions.filter((s) => s.song_title === title);
      const idx = sameSong.findIndex((s) => s.session_id === session.session_id);
      return idx >= 0 ? idx + 1 : null;
    },
    [allCompletedSessions, songAttemptCounts],
  );

  // 트렌드 데이터
  const { datasets, referenceMeans } = useMemo(() => {
    const ds: Record<string, DataPoint[]> = {};
    const refs: Record<string, number> = {};
    PARAM_KEYS.forEach((key) => {
      ds[key] = [];
    });

    filteredSessions.forEach((s) => {
      const result = mockAnalysisResults[s.session_id];
      const fb = mockFeedback[s.session_id];
      if (!result) return;
      const label = s.song_title?.substring(0, 6) ?? s.session_id.substring(0, 6);

      result.metrics.forEach((m) => {
        if (ds[m.key]) {
          ds[m.key].push({ sessionLabel: label, value: m.value });
        }
      });

      // 종합등급
      if (fb) {
        ds['grade'].push({ sessionLabel: label, value: gradeToNumber(fb.overall_grade) });
      }
    });

    // reference means from first session's comparisons
    const first = filteredSessions[0];
    if (first) {
      const comp = mockComparisons[first.session_id];
      if (comp) {
        comp.comparisons.forEach((c) => {
          refs[c.key] = c.reference_mean;
        });
      }
    }
    return { datasets: ds, referenceMeans: refs };
  }, [filteredSessions]);

  // 화면 목록 (최신 순)
  const displaySessions = useMemo(
    () => [...filteredSessions].reverse(),
    [filteredSessions],
  );

  const renderItem = ({ item }: { item: Session }) => {
    const fb = mockFeedback[item.session_id];
    const grade = fb?.overall_grade ?? '-';
    const gradeColor = getGradeColor(grade);
    const attemptNum = getAttemptNumber(item);

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('HistoryDetail', { sessionId: item.session_id })}
      >
        <View style={styles.cardBody}>
          <View style={styles.cardLeft}>
            <View style={styles.cardTitleRow}>
              <Text style={styles.songTitle} numberOfLines={1}>
                {item.song_title ?? '제목 없음'}
              </Text>
              {attemptNum !== null && (
                <View style={styles.attemptBadge}>
                  <Text style={styles.attemptBadgeText}>{attemptNum}회차</Text>
                </View>
              )}
            </View>
            <Text style={styles.date}>{formatDate(item.created_at)}</Text>
          </View>
          <View style={[styles.gradeBadge, { backgroundColor: gradeColor + '1A' }]}>
            <Text style={[styles.gradeText, { color: gradeColor }]}>{grade}</Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📊 히스토리</Text>
      </View>

      <FlatList
        data={displaySessions}
        keyExtractor={(item) => item.session_id}
        renderItem={renderItem}
        refreshing={refreshing}
        onRefresh={() => {
          setRefreshing(true);
          loadSessions();
        }}
        contentContainerStyle={
          displaySessions.length === 0 ? styles.emptyContainer : styles.listContent
        }
        ListHeaderComponent={
          <>
            {/* 트렌드 그래프 */}
            {filteredSessions.length >= 2 && (
              <View style={styles.chartWrapper}>
                <Text style={styles.chartTitle}>발성 추이</Text>
                <TrendChart
                  datasets={datasets}
                  units={PARAM_UNITS}
                  referenceMeans={referenceMeans}
                  parameterKeys={PARAM_KEYS}
                  height={200}
                />
              </View>
            )}

            {/* 필터 */}
            <View style={styles.filterRow}>
              <TouchableOpacity
                style={[styles.filterChip, filterMode === 'all' && styles.filterChipActive]}
                onPress={() => {
                  setFilterMode('all');
                  setSelectedSong(null);
                }}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    filterMode === 'all' && styles.filterChipTextActive,
                  ]}
                >
                  전체
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.filterChip,
                  filterMode === 'song' && styles.filterChipActive,
                ]}
                onPress={() => {
                  if (songTitles.length > 0) {
                    setFilterMode('song');
                    if (!selectedSong) setSongPickerVisible(true);
                  }
                }}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    filterMode === 'song' && styles.filterChipTextActive,
                  ]}
                >
                  {filterMode === 'song' && selectedSong
                    ? selectedSong.length > 10
                      ? selectedSong.substring(0, 10) + '...'
                      : selectedSong
                    : '같은 곡만 ▼'}
                </Text>
              </TouchableOpacity>
              {filterMode === 'song' && selectedSong && (
                <TouchableOpacity onPress={() => setSongPickerVisible(true)}>
                  <Text style={styles.changeSongBtn}>변경</Text>
                </TouchableOpacity>
              )}
            </View>
          </>
        }
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>완료된 분석이 없습니다</Text>
            <Text style={styles.emptySubtext}>녹음을 완료하면 여기에 표시됩니다</Text>
          </View>
        }
      />

      {/* 곡 선택 모달 */}
      <Modal visible={songPickerVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>곡 선택</Text>
            <ScrollView style={styles.songList}>
              {songTitles.map((title) => (
                <TouchableOpacity
                  key={title}
                  style={[
                    styles.songItem,
                    selectedSong === title && styles.songItemActive,
                  ]}
                  onPress={() => {
                    setSelectedSong(title);
                    setFilterMode('song');
                    setSongPickerVisible(false);
                  }}
                >
                  <Text
                    style={[
                      styles.songItemText,
                      selectedSong === title && styles.songItemTextActive,
                    ]}
                  >
                    {title}
                  </Text>
                  <Text style={styles.songItemCount}>
                    {songAttemptCounts[title] ?? 0}회
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity
              style={styles.modalCloseBtn}
              onPress={() => {
                setSongPickerVisible(false);
                if (!selectedSong) setFilterMode('all');
              }}
            >
              <Text style={styles.modalCloseBtnText}>닫기</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  header: {
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: COLORS.card,
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  listContent: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 },
  emptyContainer: { flexGrow: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView: { alignItems: 'center' },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext: { fontSize: 13, color: COLORS.textMuted, marginTop: 4 },

  chartWrapper: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  chartTitle: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 8 },

  // Filter
  filterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  filterChip: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: COLORS.surface,
  },
  filterChipActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  filterChipText: { fontSize: 13, color: COLORS.textSecondary },
  filterChipTextActive: { color: '#FFF', fontWeight: '600' },
  changeSongBtn: { fontSize: 13, color: COLORS.primary, fontWeight: '600' },

  card: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  cardBody: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardLeft: { flex: 1, marginRight: 10 },
  cardTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  songTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary, flexShrink: 1 },
  attemptBadge: {
    backgroundColor: COLORS.surface,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  attemptBadgeText: { fontSize: 11, color: COLORS.primaryLight, fontWeight: '600' },
  date: { fontSize: 12, color: COLORS.textMuted, marginTop: 4 },

  gradeBadge: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    minWidth: 48,
    alignItems: 'center',
  },
  gradeText: { fontSize: 16, fontWeight: '800' },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 24,
  },
  modalContent: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 24,
    maxHeight: 400,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 16 },
  songList: { maxHeight: 260 },
  songItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 10,
    marginBottom: 4,
  },
  songItemActive: { backgroundColor: COLORS.surface },
  songItemText: { fontSize: 15, color: COLORS.textPrimary, flex: 1 },
  songItemTextActive: { color: COLORS.primaryLight, fontWeight: '600' },
  songItemCount: { fontSize: 13, color: COLORS.textSecondary },
  modalCloseBtn: {
    marginTop: 12,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  modalCloseBtnText: { fontSize: 15, color: COLORS.textMuted },
});
