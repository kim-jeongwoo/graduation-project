import React, { useState, useCallback, useEffect } from 'react';
import {
  Alert,
  View,
  Text,
  FlatList,
  Linking,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { COLORS } from '../../utils/colors';
import { useAuth } from '../../context/AuthContext';
import { getSongs } from '../../api/songs';
import type { Song } from '../../types/api';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import MainTopTabs from '../../components/navigation/MainTopTabs';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

const SPEECH_WEB_URL = 'https://speech.vocal-fit.com';

export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const showSpeechWeb = process.env.EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true';

  const loadSongs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSongs();
      setSongs(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '곡 목록을 불러올 수 없습니다.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  // GET /songs는 14곡 정적 데이터 — 마운트 시 1회만 fetch (focus마다 재호출 X, 학원 학생 부하 회피)
  useEffect(() => { loadSongs(); }, [loadSongs]);

  const openSpeechEvaluation = useCallback(async () => {
    try {
      const canOpen = await Linking.canOpenURL(SPEECH_WEB_URL);
      if (!canOpen) {
        throw new Error('Cannot open speech web URL');
      }
      await Linking.openURL(SPEECH_WEB_URL);
    } catch {
      Alert.alert(
        '스피치 평가를 열 수 없습니다',
        '네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
      );
    }
  }, []);

  const renderSong = ({ item, index }: { item: Song; index: number }) => {
    const ready = item.hasLrc && item.hasPitchGuide;
    return (
      <TouchableOpacity
        style={styles.songCard}
        activeOpacity={0.75}
        onPress={() => navigation.navigate('SongDetail', { song: item })}
      >
        <View style={styles.songLeft}>
          <Text style={styles.songIndex}>{String(index + 1).padStart(2, '0')}</Text>
          <View>
            <Text style={styles.songTitle}>{item.title}</Text>
            <Text style={styles.songArtist}>{item.artist}</Text>
          </View>
        </View>
        <View style={[styles.badge, ready ? styles.badgeReady : styles.badgePending]}>
          <Text style={[styles.badgeText, ready ? styles.badgeTextReady : styles.badgeTextPending]}>
            {ready ? '가능' : '준비 중'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* ─── 헤더 ─── */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>안녕하세요,</Text>
          <Text style={styles.nickname}>
            {user?.nickname ?? (user?.isGuest ? '게스트' : '사용자')}님
          </Text>
        </View>
        <TouchableOpacity onPress={() => navigation.navigate('Settings')}>
          <Text style={styles.settingsIcon}>⚙️</Text>
        </TouchableOpacity>
      </View>

      <MainTopTabs activeTab="HomeTab" />

      {showSpeechWeb ? (
        <View style={styles.speechCard}>
          <View style={styles.speechHeader}>
            <View style={styles.speechTitleRow}>
              <Text style={styles.speechTitle}>스피치 평가</Text>
              <View style={styles.webBadge}>
                <Text style={styles.webBadgeText}>WEB</Text>
              </View>
            </View>
            <Text style={styles.speechDescription}>
              낭독/새도잉 기반 스피치 분석 웹으로 이동합니다.
            </Text>
          </View>
          <TouchableOpacity
            style={styles.speechButton}
            activeOpacity={0.78}
            onPress={openSpeechEvaluation}
          >
            <Text style={styles.speechButtonText}>웹으로 열기</Text>
          </TouchableOpacity>
          <Text style={styles.speechNote}>별도 웹페이지에서 진행됩니다.</Text>
        </View>
      ) : null}

      {/* ─── 곡 목록 ─── */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadSongs}>
            <Text style={styles.retryText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={songs}
          keyExtractor={(item) => item.id}
          renderItem={renderSong}
          ListHeaderComponent={
            <Text style={styles.sectionTitle}>수록곡 {songs.length}</Text>
          }
          contentContainerStyle={styles.listContent}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
  },
  greeting: { fontSize: 14, color: COLORS.textSecondary },
  nickname: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  settingsIcon: { fontSize: 24 },

  speechCard: {
    marginHorizontal: 20,
    marginTop: 14,
    marginBottom: 14,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  speechHeader: {
    gap: 6,
    marginBottom: 14,
  },
  speechTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  speechTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  webBadge: {
    borderRadius: 6,
    borderWidth: 1,
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primary + '22',
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  webBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: COLORS.primaryLight,
  },
  speechDescription: {
    fontSize: 13,
    lineHeight: 19,
    color: COLORS.textSecondary,
  },
  speechButton: {
    alignSelf: 'flex-start',
    backgroundColor: COLORS.primary,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  speechButtonText: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  speechNote: {
    marginTop: 10,
    fontSize: 12,
    color: COLORS.textMuted,
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  listContent: { paddingHorizontal: 20, paddingBottom: 40 },

  songCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: COLORS.card,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  songLeft: { flexDirection: 'row', alignItems: 'center', gap: 14, flex: 1 },
  songIndex: { fontSize: 13, fontWeight: '700', color: COLORS.textMuted, width: 24 },
  songTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },
  songArtist: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2 },

  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
  },
  badgeReady: { borderColor: COLORS.success, backgroundColor: COLORS.success + '22' },
  badgePending: { borderColor: COLORS.textMuted, backgroundColor: 'transparent' },
  badgeText: { fontSize: 11, fontWeight: '600' },
  badgeTextReady: { color: COLORS.success },
  badgeTextPending: { color: COLORS.textMuted },

  errorText: { color: COLORS.danger, fontSize: 14, textAlign: 'center' },
  retryBtn: {
    backgroundColor: COLORS.card,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  retryText: { color: COLORS.textPrimary, fontSize: 14 },
});
