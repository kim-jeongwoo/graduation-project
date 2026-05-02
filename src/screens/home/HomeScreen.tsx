import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { COLORS } from '../../utils/colors';
import { useAuth } from '../../context/AuthContext';
import { getSongs } from '../../api/songs';
import type { Song } from '../../types/api';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

export default function HomeScreen({ navigation }: Props) {
  const { user } = useAuth();
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSongs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSongs();
      setSongs(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '곡 목록을 불러올 수 없습니다.';
      setError(msg);
      console.log('[HomeScreen] getSongs error:', msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { loadSongs(); }, [loadSongs]));

  const renderSong = ({ item, index }: { item: Song; index: number }) => {
    const ready = item.has_lrc && item.has_pitch_guide;
    return (
      <TouchableOpacity
        style={styles.songCard}
        activeOpacity={ready ? 0.75 : 1}
        disabled={!ready}
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
          keyExtractor={(item) => item.song_id}
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
