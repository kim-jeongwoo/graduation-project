import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { isAuthExpiredError } from '../../api/client';
import { getSessions } from '../../api/sessions';
import { formatDate } from '../../utils/labels';
import type { Session } from '../../types/api';
import { COLORS } from '../../utils/colors';
import type { HistoryStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<HistoryStackParamList, 'HistoryList'>;

// 곡 제목/아티스트/ID fallback (서버 응답 nested song 우선)
const getSongTitle  = (s: Session) => s.song?.title  ?? s.song_title ?? null;
const getSongArtist = (s: Session) => s.song?.artist ?? null;
const getSongId     = (s: Session) => s.song?.id     ?? s.song_id     ?? null;

// 곡별 폴더 그룹
interface SongFolder {
  songId:     string;
  songTitle:  string;
  songArtist: string | null;
  count:      number;
  lastAt:     Date;
  sessions:   Session[];   // 회차 리스트 (최신 desc)
}

export default function HistoryScreen({ navigation }: Props) {
  const [sessions, setSessions]   = useState<Session[]>([]);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg]   = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setErrorMsg(null);
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) return;
      setErrorMsg('분석 기록을 불러오지 못했습니다.');
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

  // 곡별 그룹화 (song_id 기준, 자유녹음 제외) — 가장 최근 분석 시간 desc
  const folders = useMemo<SongFolder[]>(() => {
    const completed = sessions.filter(s => s.analysis_status === 'completed');
    const map = new Map<string, SongFolder>();
    for (const s of completed) {
      const songId = getSongId(s);
      if (!songId) continue;  // 자유녹음 제외 (옵션 A)
      const created = new Date(s.created_at);
      const existing = map.get(songId);
      if (existing) {
        existing.count += 1;
        existing.sessions.push(s);
        if (created > existing.lastAt) existing.lastAt = created;
      } else {
        map.set(songId, {
          songId,
          songTitle:  getSongTitle(s) ?? '제목 없음',
          songArtist: getSongArtist(s),
          count:      1,
          lastAt:     created,
          sessions:   [s],
        });
      }
    }
    // 각 그룹 sessions 최신 desc
    for (const f of map.values()) {
      f.sessions.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
    return Array.from(map.values()).sort((a, b) => b.lastAt.getTime() - a.lastAt.getTime());
  }, [sessions]);

  const handleFolderPress = (folder: SongFolder) => {
    navigation.navigate('SongHistory', {
      songId:     folder.songId,
      songTitle:  folder.songTitle,
      songArtist: folder.songArtist,
      sessions:   folder.sessions,
    });
  };

  const renderItem = ({ item }: { item: SongFolder }) => {
    const titleLabel = item.songArtist ? `${item.songTitle} - ${item.songArtist}` : item.songTitle;
    return (
      <TouchableOpacity style={styles.card} onPress={() => handleFolderPress(item)}>
        <View style={styles.cardBody}>
          <View style={styles.cardLeft}>
            <Text style={styles.songTitle} numberOfLines={1}>{titleLabel}</Text>
            <Text style={styles.date}>마지막: {formatDate(item.lastAt.toISOString())}</Text>
          </View>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{item.count}회</Text>
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

  const renderHeader = () => (
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📊 히스토리</Text>
        <TouchableOpacity
          style={styles.favBtn}
          onPress={() => navigation.navigate('Favorites')}
        >
          <Text style={styles.favBtnText}>⭐ 즐겨찾기</Text>
        </TouchableOpacity>
      </View>
  );

  if (errorMsg) {
    return (
      <View style={styles.container}>
        {renderHeader()}
        <View style={styles.centered}>
          <Text style={styles.errorText}>{errorMsg}</Text>
          <Text style={styles.errorSubtext}>잠시 후 다시 시도해 주세요.</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => {
              setLoading(true);
              loadSessions();
            }}
          >
            <Text style={styles.retryText}>다시 불러오기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {renderHeader()}

      <FlatList
        data={folders}
        keyExtractor={(f) => f.songId}
        renderItem={renderItem}
        refreshing={refreshing}
        onRefresh={() => {
          setRefreshing(true);
          loadSessions();
        }}
        contentContainerStyle={folders.length === 0 ? styles.emptyContainer : styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>아직 분석 기록이 없습니다.</Text>
            <Text style={styles.emptySubtext}>노래를 녹음하고 분석하면 이곳에서 기록을 확인할 수 있습니다.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.background },
  centered:    { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  header: {
    paddingHorizontal: 20, paddingTop: 60, paddingBottom: 16,
    backgroundColor: COLORS.card,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  favBtn:      { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 14, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.cardBorder },
  favBtnText:  { fontSize: 13, color: COLORS.textPrimary, fontWeight: '600' },
  listContent:    { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 },
  emptyContainer: { flexGrow: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView:      { alignItems: 'center' },
  emptyIcon:      { fontSize: 48, marginBottom: 12 },
  emptyText:      { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext:   { fontSize: 13, color: COLORS.textMuted, marginTop: 4, textAlign: 'center', paddingHorizontal: 24 },
  errorText:      { fontSize: 16, color: COLORS.danger, textAlign: 'center' },
  errorSubtext:   { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  retryBtn:       { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: 8 },
  retryText:      { fontSize: 14, color: '#ffffff', fontWeight: '700' },
  card: {
    backgroundColor: COLORS.card, borderRadius: 12, padding: 16, marginBottom: 10,
    borderWidth: 1, borderColor: COLORS.cardBorder,
  },
  cardBody:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardLeft:    { flex: 1, marginRight: 10 },
  songTitle:   { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  date:        { fontSize: 12, color: COLORS.textMuted },
  countBadge:  { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.cardBorder },
  countText:   { fontSize: 14, fontWeight: '700', color: COLORS.primaryLight },
});
