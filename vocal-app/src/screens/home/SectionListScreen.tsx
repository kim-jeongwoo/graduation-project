import React from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import {
  WeakSection,
  IndicatorAppKey,
  INDICATOR_LABELS,
  ZONE_LABELS,
  zoneColor,
} from '../../domain/weakSections';
import { useFavorites } from '../../context/FavoritesContext';

type Props = NativeStackScreenProps<
  {
    SectionList: {
      indicatorKey:   IndicatorAppKey;
      weakSections:   WeakSection[];
      feedbackText:   string;
      runId?:         string;
      songId?:        string;
      sessionId?:     string;
    };
  },
  'SectionList'
>;

export default function SectionListScreen({ route, navigation }: Props) {
  const { indicatorKey, weakSections, feedbackText, runId, songId, sessionId } = route.params;
  const indicatorLabel = INDICATOR_LABELS[indicatorKey];
  const { addFavorite, removeFavoriteByKey, isFavorite } = useFavorites();

  const toggleFavorite = (sec: WeakSection) => {
    if (!songId) return;  // 자유녹음(songId 없음) 즐겨찾기 불가
    if (isFavorite({ songId, chunkIndex: sec.chunkIndex, indicatorKey })) {
      removeFavoriteByKey({ songId, chunkIndex: sec.chunkIndex, indicatorKey });
    } else {
      addFavorite({
        indicatorKey,
        weakSection: sec,
        songId,
        runId,
        sessionId,
        feedbackText,
      });
    }
  };

  const onSelectSection = (sec: WeakSection) => {
    navigation.navigate('Training' as never, {
      indicatorKey,
      runId,
      songId,
      sessionId,
      chunkIndex:      sec.chunkIndex,
      sectionStartSec: sec.paddedStartSec,
      sectionEndSec:   sec.paddedEndSec,
      chunkInfo:       { startSec: sec.startSec, endSec: sec.endSec, lrcText: sec.lrcText },
      scoreInfo:       { aiScore: sec.aiScore, zone: sec.zone },
      lowConfidenceItems: sec.lowConfidenceItems,
      feedbackText,
    } as never);
  };

  if (weakSections.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.title}>{indicatorLabel} 약점 구간</Text>
        <Text style={styles.empty}>약점 구간이 없거나 데이터가 준비되지 않았습니다.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{indicatorLabel} 약점 구간</Text>
      <FlatList
        data={weakSections}
        keyExtractor={(_, i) => `weak-${i}`}
        renderItem={({ item }) => {
          const fav = songId ? isFavorite({ songId, chunkIndex: item.chunkIndex, indicatorKey }) : false;
          return (
            <TouchableOpacity style={styles.row} onPress={() => onSelectSection(item)}>
              <View style={styles.rowHeader}>
                <Text style={styles.lrc}>{item.lrcText.trim() || '(가사 없음)'}</Text>
                {songId && (
                  <TouchableOpacity
                    onPress={(e) => { e.stopPropagation?.(); toggleFavorite(item); }}
                    hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}
                    style={styles.starBtn}
                  >
                    <Text style={[styles.starText, fav && styles.starTextActive]}>
                      {fav ? '★' : '☆'}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
              <Text style={styles.time}>
                {item.startSec.toFixed(1)}초 ~ {item.endSec.toFixed(1)}초
              </Text>
              <Text style={[styles.score, { color: zoneColor(item.zone) }]}>
                {item.aiScore.toFixed(2)}점 / {ZONE_LABELS[item.zone]}
              </Text>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base },
  emptyContainer: { flex: 1, backgroundColor: COLORS.background, padding: SPACING.base, justifyContent: 'center', alignItems: 'center' },
  title:          { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, marginBottom: SPACING.base },
  empty:          { ...TYPOGRAPHY.body, color: COLORS.textMuted, textAlign: 'center' },
  row:            { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm },
  rowHeader:      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  lrc:            { ...TYPOGRAPHY.body, color: COLORS.textPrimary, flex: 1 },
  starBtn:        { paddingHorizontal: 4 },
  starText:       { fontSize: 22, color: COLORS.textMuted },
  starTextActive: { color: '#ffd54f' },
  time:           { fontSize: 12, color: COLORS.textMuted, marginBottom: 4 },
  score:          { fontSize: 14, fontWeight: '600' },
});
