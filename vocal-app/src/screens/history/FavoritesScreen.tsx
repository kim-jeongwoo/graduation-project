import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { useFavorites, type FavoriteSection } from '../../context/FavoritesContext';
import { INDICATOR_LABELS, ZONE_LABELS, zoneColor, extractWeakSections } from '../../domain/weakSections';
import { getResultsByRunId } from '../../api/analyze';
import type { HistoryStackParamList } from '../../navigation/types';
import type { Zone } from '../../types/analyze';

type Props = NativeStackScreenProps<HistoryStackParamList, 'Favorites'>;

export default function FavoritesScreen({ navigation }: Props) {
  const { favorites, removeFavoriteById } = useFavorites();
  const [loading, setLoading] = useState(false);

  // 옵션 B — 원본 데이터 재조회 후 정확한 scoreInfo/paddedBoundary로 진입
  const onSelect = useCallback(async (fav: FavoriteSection) => {
    if (!fav.runId) {
      Alert.alert('알림', '원본 분석 정보가 없어 진입할 수 없습니다.');
      return;
    }
    setLoading(true);
    try {
      const result = await getResultsByRunId(fav.runId);
      const chunk = result.timelineScores?.[fav.weakSection.chunkIndex];
      if (!chunk) {
        Alert.alert('데이터 없음', '원본 chunk를 찾을 수 없습니다.');
        return;
      }
      const tlKey = fav.indicatorKey === 'breathiness' ? 'breathiness' : 'vocalFoldContact';
      const score = chunk.scores[tlKey];
      if (!score) {
        Alert.alert('데이터 없음', '점수 정보가 없습니다.');
        return;
      }
      const weakSections = extractWeakSections(
        result.timelineScores ?? [],
        fav.indicatorKey,
        result.audio_info?.duration_sec,
      );
      const fullSection = weakSections.find(s => s.chunkIndex === fav.weakSection.chunkIndex);
      const sectionStart = fullSection?.paddedStartSec ?? Math.max(0, chunk.startSec - 4);
      const sectionEnd   = fullSection?.paddedEndSec   ?? chunk.endSec + 3;
      navigation.navigate('Training', {
        indicatorKey:    fav.indicatorKey,
        runId:           fav.runId,
        songId:          fav.songId,
        sessionId:       result.session_id,
        chunkIndex:      fav.weakSection.chunkIndex,
        sectionStartSec: sectionStart,
        sectionEndSec:   sectionEnd,
        chunkInfo:       { startSec: chunk.startSec, endSec: chunk.endSec, lrcText: chunk.lrcText },
        scoreInfo:       { aiScore: score.aiScore, zone: score.zone as Zone },
        feedbackText:    result.feedback[fav.indicatorKey]?.feedback_text ?? '',
      });
    } catch {
      Alert.alert('오류', '원본 데이터를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [navigation]);

  if (favorites.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyIcon}>⭐</Text>
        <Text style={styles.emptyText}>즐겨찾기한 구간이 없습니다</Text>
        <Text style={styles.emptySubtext}>약점 구간 리스트에서 ☆ 버튼을 눌러 추가하세요</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>⭐ 즐겨찾기 구간</Text>
      <FlatList
        data={favorites}
        keyExtractor={(f) => f.id}
        renderItem={({ item }) => {
          const songLabel = item.songTitle
            ? (item.songArtist ? `${item.songTitle} - ${item.songArtist}` : item.songTitle)
            : '';
          return (
            <TouchableOpacity style={styles.row} onPress={() => onSelect(item)} disabled={loading}>
              {songLabel ? <Text style={styles.songLabel}>{songLabel}</Text> : null}
              <View style={styles.rowHeader}>
                <Text style={styles.indicator}>{INDICATOR_LABELS[item.indicatorKey]}</Text>
                <TouchableOpacity
                  onPress={() => removeFavoriteById(item.id)}
                  hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}
                >
                  <Text style={styles.removeText}>★</Text>
                </TouchableOpacity>
              </View>
              <Text style={styles.lrc}>{item.weakSection.lrcText.trim() || '(가사 없음)'}</Text>
              <Text style={styles.time}>
                {item.weakSection.startSec.toFixed(1)}초 ~ {item.weakSection.endSec.toFixed(1)}초
              </Text>
              <Text style={[styles.score, { color: zoneColor(item.weakSection.zone) }]}>
                {item.weakSection.aiScore.toFixed(2)}점 / {ZONE_LABELS[item.weakSection.zone]}
              </Text>
            </TouchableOpacity>
          );
        }}
      />
      {loading && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.overlayText}>원본 데이터 불러오는 중...</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base },
  empty:       { flex: 1, backgroundColor: COLORS.background, justifyContent: 'center', alignItems: 'center', gap: SPACING.sm, padding: SPACING.base },
  emptyIcon:   { fontSize: 48 },
  emptyText:   { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  emptySubtext:{ fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  title:       { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, marginBottom: SPACING.base },
  row:         { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm },
  songLabel:   { fontSize: 14, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 6 },
  rowHeader:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  indicator:   { fontSize: 12, color: COLORS.primaryLight, fontWeight: '600' },
  removeText:  { fontSize: 22, color: '#ffd54f' },
  lrc:         { ...TYPOGRAPHY.body, color: COLORS.textPrimary, marginBottom: 4 },
  time:        { fontSize: 12, color: COLORS.textMuted, marginBottom: 4 },
  score:       { fontSize: 14, fontWeight: '600' },
  overlay:     { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', gap: SPACING.sm },
  overlayText: { ...TYPOGRAPHY.body, color: '#ffffff' },
});
