import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TextInput,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { COLORS } from '../../utils/colors';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useAuth } from '../../context/AuthContext';
import { useVocalProfile } from '../../context/VocalProfileContext';
import { getSessions, createSession } from '../../api/sessions';
import { getSongs } from '../../api/songs';
import { mockFeedback, mockSessions as allMockSessions } from '../../mock/mockData';
import StatusBadge from '../../components/StatusBadge';
import { formatDate, getGradeColor } from '../../utils/labels';
import type { Session, Song } from '../../types/api';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;
type TabNav = { navigate: (screen: string, params?: Record<string, unknown>) => void };

const MAX_RECENT = 5;

export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const { vocalRange, voiceType, isTestCompleted } = useVocalProfile();
  const tabNav = useNavigation();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // FAB 모달 (새 세션)
  const [songSelectModal, setSongSelectModal] = useState(false);
  const [manualInputModal, setManualInputModal] = useState(false);
  const [songTitle, setSongTitle] = useState('');
  const [songList, setSongList] = useState<Song[]>([]);
  const [songsLoading, setSongsLoading] = useState(false);

  // 같은 곡 비교 모달
  const [songPickerModal, setSongPickerModal] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (e: unknown) {
      console.log('[HomeScreen] loadSessions error:', e);
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

  const handleRefresh = () => {
    setRefreshing(true);
    loadSessions();
  };

  // 곡 목록 로드
  const loadSongList = useCallback(async () => {
    setSongsLoading(true);
    try {
      const data = await getSongs();
      setSongList(data);
    } catch (e: unknown) {
      console.log('[HomeScreen] loadSongs error:', e);
    } finally {
      setSongsLoading(false);
    }
  }, []);

  const handleFabPress = () => {
    setSongSelectModal(true);
    loadSongList();
  };

  const handleSelectSong = async (song: Song) => {
    setSongSelectModal(false);
    try {
      const newSession = await createSession({
        song_title: `${song.title} - ${song.artist}`,
        song_id: song.song_id,
      });
      navigation.navigate('SessionDetail', {
        sessionId: newSession.session_id,
        songId: song.song_id,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '세션 생성 실패';
      Alert.alert('오류', msg);
    }
  };

  const handleManualCreate = async () => {
    if (!songTitle.trim()) {
      Alert.alert('오류', '곡 제목을 입력하세요.');
      return;
    }
    try {
      const newSession = await createSession({ song_title: songTitle.trim() });
      setSongTitle('');
      setManualInputModal(false);
      navigation.navigate('SessionDetail', { sessionId: newSession.session_id });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '세션 생성 실패';
      Alert.alert('오류', msg);
    }
  };

  // ─── 요약 통계 ───
  const completedSessions = sessions.filter((s) => s.status === 'completed');
  const totalCompleted = completedSessions.length;

  let latestGrade = '-';
  if (completedSessions.length > 0) {
    const latest = completedSessions[0];
    const fb = mockFeedback[latest.session_id];
    if (fb) latestGrade = fb.overall_grade;
  }

  const streakDays = '3일';

  // 최근 5개
  const recentSessions = sessions.slice(0, MAX_RECENT);

  // 같은 곡 비교용 곡 목록 (completed만)
  const songTitles = useMemo(() => {
    const titles = new Set<string>();
    allMockSessions
      .filter((s) => s.status === 'completed' && s.song_title)
      .forEach((s) => titles.add(s.song_title as string));
    return Array.from(titles);
  }, []);

  // ─── 렌더링 ───
  const renderSessionItem = ({ item }: { item: Session }) => {
    const fb = mockFeedback[item.session_id];
    const grade = fb?.overall_grade;
    const gradeColor = grade ? getGradeColor(grade) : '#AAA';

    return (
      <TouchableOpacity
        style={styles.sessionCard}
        onPress={() => navigation.navigate('SessionDetail', { sessionId: item.session_id, songId: item.song_id })}
      >
        <View style={styles.sessionRow}>
          <View style={styles.sessionLeft}>
            <Text style={styles.songTitle} numberOfLines={1}>
              {item.song_title ?? '제목 없음'}
            </Text>
            <Text style={styles.sessionDate}>{formatDate(item.created_at)}</Text>
          </View>
          <View style={styles.sessionRight}>
            {grade ? (
              <View style={[styles.miniGrade, { backgroundColor: gradeColor + '1A' }]}>
                <Text style={[styles.miniGradeText, { color: gradeColor }]}>{grade}</Text>
              </View>
            ) : (
              <StatusBadge status={item.status} />
            )}
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
      <FlatList
        data={recentSessions}
        keyExtractor={(item) => item.session_id}
        renderItem={renderSessionItem}
        refreshing={refreshing}
        onRefresh={handleRefresh}
        contentContainerStyle={
          recentSessions.length === 0 ? styles.emptyContainer : styles.listContent
        }
        ListHeaderComponent={
          <>
            {/* ─── 헤더 ─── */}
            <View style={styles.header}>
              <Text style={styles.greeting}>안녕하세요, {user?.nickname ?? '사용자'}님</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Settings')}>
                <Text style={styles.settingsIcon}>⚙️</Text>
              </TouchableOpacity>
            </View>

            {/* ─── 요약 카드 ─── */}
            <View style={styles.summaryRow}>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{totalCompleted}</Text>
                <Text style={styles.summaryLabel}>총 녹음</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{latestGrade}</Text>
                <Text style={styles.summaryLabel}>최근 등급</Text>
              </View>
              <View style={styles.summaryCard}>
                <Text style={styles.summaryValue}>{streakDays}</Text>
                <Text style={styles.summaryLabel}>연속 연습</Text>
              </View>
            </View>

            {/* ─── 음역대 섹션 ─── */}
            {!isTestCompleted && (
              <TouchableOpacity
                style={styles.rangeBanner}
                onPress={() => navigation.navigate('VocalRangeTest')}
              >
                <Text style={styles.rangeBannerEmoji}>🎤</Text>
                <View style={styles.rangeBannerTextWrap}>
                  <Text style={styles.rangeBannerTitle}>
                    음역대를 측정하고 맞춤 피드백을 받아보세요
                  </Text>
                </View>
                <View style={styles.rangeBannerBtn}>
                  <Text style={styles.rangeBannerBtnText}>측정하기</Text>
                </View>
              </TouchableOpacity>
            )}

            {isTestCompleted && vocalRange && (
              <View style={styles.rangeInfoCard}>
                <View style={styles.rangeInfoRow}>
                  <View>
                    <Text style={styles.rangeInfoLabel}>내 음역대</Text>
                    <Text style={styles.rangeInfoValue}>
                      {vocalRange.low} ~ {vocalRange.high}
                      {voiceType ? ` (${voiceType.replace(' 범위', '')})` : ''}
                    </Text>
                  </View>
                  <TouchableOpacity
                    style={styles.retestBtn}
                    onPress={() => navigation.navigate('VocalRangeTest')}
                  >
                    <Text style={styles.retestBtnText}>다시 측정</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* ─── 기능 바로가기 ─── */}
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.shortcutScroll}
              contentContainerStyle={styles.shortcutScrollInner}
            >
              <TouchableOpacity
                style={styles.shortcutCard}
                onPress={() => (tabNav as unknown as TabNav).navigate('HistoryTab')}
              >
                <Text style={styles.shortcutEmoji}>📊</Text>
                <Text style={styles.shortcutLabel}>분석 히스토리</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.shortcutCard}
                onPress={() => (tabNav as unknown as TabNav).navigate('GoalsTab')}
              >
                <Text style={styles.shortcutEmoji}>🎯</Text>
                <Text style={styles.shortcutLabel}>목표 관리</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.shortcutCard}
                onPress={() => {
                  if (songTitles.length === 0) {
                    Alert.alert('알림', '비교할 수 있는 곡이 없습니다.');
                    return;
                  }
                  setSongPickerModal(true);
                }}
              >
                <Text style={styles.shortcutEmoji}>🎵</Text>
                <Text style={styles.shortcutLabel}>같은 곡 비교</Text>
              </TouchableOpacity>
            </ScrollView>

            {/* ─── 세션 목록 헤더 ─── */}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>최근 녹음</Text>
              {sessions.length > MAX_RECENT && (
                <TouchableOpacity
                  onPress={() => (tabNav as unknown as TabNav).navigate('HistoryTab')}
                >
                  <Text style={styles.seeMoreText}>더 보기 →</Text>
                </TouchableOpacity>
              )}
            </View>
          </>
        }
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>🎵</Text>
            <Text style={styles.emptyText}>아직 녹음 세션이 없습니다</Text>
            <Text style={styles.emptySubtext}>
              우측 하단 녹음 버튼을 눌러 시작하세요
            </Text>
          </View>
        }
      />

      {/* ─── FAB (플로팅 녹음 버튼) ─── */}
      <TouchableOpacity
        style={styles.fab}
        onPress={handleFabPress}
        activeOpacity={0.85}
      >
        <Text style={styles.fabText}>🎤</Text>
      </TouchableOpacity>

      {/* ─── 곡 선택 모달 ─── */}
      <Modal visible={songSelectModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>곡 선택</Text>
            {songsLoading ? (
              <View style={{ alignItems: 'center', paddingVertical: 20 }}>
                <ActivityIndicator size="small" color={COLORS.primary} />
              </View>
            ) : (
              <ScrollView style={styles.songPickerList}>
                {songList.map((song) => (
                  <TouchableOpacity
                    key={song.song_id}
                    style={styles.songPickerItem}
                    onPress={() => handleSelectSong(song)}
                  >
                    <Text style={styles.songPickerText}>
                      🎵 {song.title} - {song.artist}
                    </Text>
                    <Text style={styles.songPickerArrow}>→</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancel}
                onPress={() => setSongSelectModal(false)}
              >
                <Text style={styles.modalCancelText}>닫기</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalConfirm}
                onPress={() => {
                  setSongSelectModal(false);
                  setManualInputModal(true);
                }}
              >
                <Text style={styles.modalConfirmText}>직접 입력</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ─── 직접 입력 모달 ─── */}
      <Modal visible={manualInputModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>새 녹음 세션</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="곡 제목 (예: 봄날 - BTS)"
              placeholderTextColor={COLORS.textMuted}
              value={songTitle}
              onChangeText={setSongTitle}
              autoFocus
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancel}
                onPress={() => {
                  setSongTitle('');
                  setManualInputModal(false);
                }}
              >
                <Text style={styles.modalCancelText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalConfirm} onPress={handleManualCreate}>
                <Text style={styles.modalConfirmText}>생성</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ─── 곡 선택 모달 (같은 곡 비교) ─── */}
      <Modal visible={songPickerModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>비교할 곡 선택</Text>
            <ScrollView style={styles.songPickerList}>
              {songTitles.map((title) => (
                <TouchableOpacity
                  key={title}
                  style={styles.songPickerItem}
                  onPress={() => {
                    setSongPickerModal(false);
                    navigation.navigate('SongComparison', { songTitle: title });
                  }}
                >
                  <Text style={styles.songPickerText}>{title}</Text>
                  <Text style={styles.songPickerArrow}>→</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => setSongPickerModal(false)}
            >
              <Text style={styles.modalCancelText}>닫기</Text>
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
  listContent: { paddingHorizontal: 16, paddingBottom: 90 },
  emptyContainer: { flexGrow: 1, justifyContent: 'center', alignItems: 'center' },

  // ─── 헤더 ───
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 4,
    paddingTop: 60,
    paddingBottom: 12,
    backgroundColor: 'transparent',
  },
  greeting: { fontSize: 20, fontWeight: '700', color: COLORS.textPrimary },
  settingsIcon: { fontSize: 24 },

  // ─── 요약 카드 ───
  summaryRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  summaryValue: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  summaryLabel: { fontSize: 12, color: COLORS.textSecondary, marginTop: 4 },

  // ─── 음역대 배너 ───
  rangeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.primary + '1A',
    padding: 16,
    borderRadius: 14,
    gap: 12,
    marginBottom: 14,
  },
  rangeBannerEmoji: { fontSize: 28 },
  rangeBannerTextWrap: { flex: 1 },
  rangeBannerTitle: { fontSize: 14, fontWeight: '600', color: COLORS.primaryLight, lineHeight: 20 },
  rangeBannerBtn: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  rangeBannerBtnText: { color: '#FFF', fontSize: 13, fontWeight: '600' },

  rangeInfoCard: {
    backgroundColor: COLORS.card,
    padding: 16,
    borderRadius: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  rangeInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rangeInfoLabel: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 2 },
  rangeInfoValue: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary },
  retestBtn: {
    backgroundColor: COLORS.surface,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  retestBtnText: { fontSize: 12, color: COLORS.textSecondary, fontWeight: '600' },

  // ─── 바로가기 ───
  shortcutScroll: { marginBottom: 18 },
  shortcutScrollInner: { gap: 10, paddingRight: 4 },
  shortcutCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    paddingVertical: 16,
    paddingHorizontal: 22,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    minWidth: 100,
  },
  shortcutEmoji: { fontSize: 26, marginBottom: 6 },
  shortcutLabel: { fontSize: 12, fontWeight: '600', color: COLORS.textSecondary },

  // ─── 세션 섹션 ───
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary },
  seeMoreText: { fontSize: 13, color: COLORS.primaryLight, fontWeight: '600' },

  sessionCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  sessionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sessionLeft: { flex: 1, marginRight: 10 },
  sessionRight: {},
  songTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },
  sessionDate: { fontSize: 12, color: COLORS.textMuted, marginTop: 4 },
  miniGrade: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignItems: 'center',
  },
  miniGradeText: { fontSize: 14, fontWeight: '800' },

  emptyView: { alignItems: 'center' },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext: { fontSize: 13, color: COLORS.textMuted, marginTop: 4 },

  // ─── FAB ───
  fab: {
    position: 'absolute',
    bottom: 30,
    right: 20,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: COLORS.fab,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    elevation: 6,
    zIndex: 999,
  },
  fabText: { fontSize: 28 },

  // ─── 모달 ───
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    padding: 24,
  },
  modalContent: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 24,
    maxHeight: 400,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', marginBottom: 16, color: COLORS.textPrimary },
  modalInput: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    marginBottom: 16,
    backgroundColor: COLORS.surface,
    color: COLORS.textPrimary,
  },
  modalButtons: { flexDirection: 'row', gap: 10 },
  modalCancel: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  modalCancelText: { fontSize: 15, color: COLORS.textSecondary },
  modalConfirm: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  modalConfirmText: { fontSize: 15, color: '#FFF', fontWeight: '600' },

  // ─── 곡 선택 모달 ───
  songPickerList: { maxHeight: 260, marginBottom: 12 },
  songPickerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 10,
    marginBottom: 4,
  },
  songPickerText: { fontSize: 15, color: COLORS.textPrimary, flex: 1 },
  songPickerArrow: { fontSize: 16, color: COLORS.primary },
});
