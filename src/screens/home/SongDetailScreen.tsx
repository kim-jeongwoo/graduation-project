import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import type { Song } from '../../types/api';

type HomeStackParams = {
  Home: undefined;
  SongDetail: { song: Song };
  Karaoke: { songId: string };
  EvalResult: { runId?: string };
};

type Props = NativeStackScreenProps<HomeStackParams, 'SongDetail'>;

export default function SongDetailScreen({ navigation, route }: Props) {
  const { song } = route.params;
  const ready = song.hasLrc && song.hasPitchGuide;
  const totalSec = song.mrDurationSec ?? 0;
  const durationMin = Math.floor(totalSec / 60);
  const durationSec = String(Math.round(totalSec % 60)).padStart(2, '0');

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.headerBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>곡 상세</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* 커버 영역 */}
        <View style={styles.coverPlaceholder}>
          <Text style={styles.coverEmoji}>🎵</Text>
        </View>

        {/* 곡 정보 */}
        <Text style={styles.songTitle}>{song.title}</Text>
        <Text style={styles.artistName}>{song.artist}</Text>
        <Text style={styles.duration}>{durationMin}:{durationSec}</Text>

        {/* 준비 상태 뱃지 */}
        <View style={[styles.badge, ready ? styles.badgeReady : styles.badgePending]}>
          <Text style={[styles.badgeText, ready ? styles.badgeTextReady : styles.badgeTextPending]}>
            {ready ? '녹음 가능' : '준비 중'}
          </Text>
        </View>

        {/* 이전 녹음 기록 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>이전 녹음</Text>
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>아직 녹음 기록이 없습니다</Text>
          </View>
        </View>
      </ScrollView>

      {/* 하단 버튼 */}
      <View style={styles.footer}>
        {ready ? (
          <TouchableOpacity
            style={styles.startBtn}
            activeOpacity={0.8}
            onPress={() => navigation.navigate('Karaoke', { songId: song.id })}
          >
            <Text style={styles.startBtnText}>녹음 시작</Text>
          </TouchableOpacity>
        ) : (
          <View style={[styles.startBtn, styles.startBtnDisabled]}>
            <Text style={styles.startBtnTextDisabled}>이 곡은 아직 준비 중입니다</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },

  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 56,
    paddingBottom: 12,
    paddingHorizontal: 16,
    backgroundColor: COLORS.background,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  backIcon: { fontSize: 22, color: COLORS.textPrimary },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 16, fontWeight: '600', color: COLORS.textPrimary },

  content: { paddingHorizontal: 24, paddingBottom: 120, alignItems: 'center' },

  coverPlaceholder: {
    width: 200,
    height: 200,
    borderRadius: 20,
    backgroundColor: COLORS.primary + '33',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 24,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.primary + '55',
  },
  coverEmoji: { fontSize: 64 },

  songTitle: {
    fontSize: 26,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
  },
  artistName: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginTop: 6,
    textAlign: 'center',
  },
  duration: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginTop: 8,
  },

  badge: {
    marginTop: 14,
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
  },
  badgeReady: { borderColor: COLORS.success, backgroundColor: COLORS.success + '22' },
  badgePending: { borderColor: COLORS.textMuted, backgroundColor: 'transparent' },
  badgeText: { fontSize: 13, fontWeight: '600' },
  badgeTextReady: { color: COLORS.success },
  badgeTextPending: { color: COLORS.textMuted },

  section: { width: '100%', marginTop: 36 },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  emptyBox: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  emptyText: { fontSize: 13, color: COLORS.textMuted },

  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    paddingBottom: 36,
    backgroundColor: COLORS.background,
    borderTopWidth: 1,
    borderTopColor: COLORS.cardBorder,
  },
  startBtn: {
    backgroundColor: COLORS.primary,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  startBtnDisabled: {
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  startBtnText: { fontSize: 17, fontWeight: '700', color: '#fff' },
  startBtnTextDisabled: { fontSize: 15, fontWeight: '500', color: COLORS.textMuted },
});
