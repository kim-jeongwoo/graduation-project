import React, { useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { getSessionDetail, extractRunId } from '../../api/sessions';
import { formatDate } from '../../utils/labels';
import type { Session } from '../../types/api';
import type { HistoryStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<HistoryStackParamList, 'SongHistory'>;

export default function SongHistoryScreen({ route, navigation }: Props) {
  const { songId, songTitle, songArtist, sessions } = route.params;
  const titleLabel = songArtist ? `${songTitle} - ${songArtist}` : songTitle;

  const handleSessionPress = useCallback(async (session: Session) => {
    try {
      const detail = await getSessionDetail(session.session_id);
      const runId = extractRunId(detail);
      if (!runId) {
        Alert.alert('분석 결과 없음', '이 세션은 분석이 완료되지 않았습니다.');
        return;
      }
      navigation.navigate('EvalResult', { runId, songId });
    } catch {
      Alert.alert('오류', '세션 정보를 불러오지 못했습니다.');
    }
  }, [navigation, songId]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={1}>{titleLabel}</Text>
        <Text style={styles.subtitle}>{sessions.length}회 분석</Text>
      </View>
      <FlatList
        data={sessions}
        keyExtractor={(s) => s.session_id}
        contentContainerStyle={styles.list}
        renderItem={({ item, index }) => {
          const attemptNum = sessions.length - index;  // 최신=N회차, 가장 옛=1회차
          return (
            <TouchableOpacity style={styles.row} onPress={() => handleSessionPress(item)}>
              <View style={styles.rowLeft}>
                <View style={styles.attemptBadge}>
                  <Text style={styles.attemptText}>{attemptNum}회차</Text>
                </View>
                <Text style={styles.date}>{formatDate(item.created_at)}</Text>
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: COLORS.background },
  header:       { paddingHorizontal: SPACING.base, paddingTop: SPACING.base, paddingBottom: SPACING.sm, backgroundColor: COLORS.card, borderBottomWidth: 1, borderBottomColor: COLORS.cardBorder },
  title:        { ...TYPOGRAPHY.heading, color: COLORS.textPrimary },
  subtitle:     { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  list:         { padding: SPACING.base },
  row:          { backgroundColor: COLORS.card, borderRadius: 10, padding: SPACING.base, marginBottom: SPACING.sm, borderWidth: 1, borderColor: COLORS.cardBorder },
  rowLeft:      { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  attemptBadge: { backgroundColor: COLORS.surface, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  attemptText:  { fontSize: 12, fontWeight: '700', color: COLORS.primaryLight },
  date:         { fontSize: 13, color: COLORS.textPrimary },
});
