// 분석 결과 탭 진입 시 자동으로 최신 완료 세션의 EvalResult로 이동
// 이전 [P0 검증용] run_id 직접 입력 화면을 대체
import React, { useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { CommonActions } from '@react-navigation/native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { isAuthExpiredError } from '../../api/client';
import { getSessions, getSessionDetail, extractRunId } from '../../api/sessions';
import type { Session } from '../../types/api';
import type { MainTabParamList, ResultStackParamList } from '../../navigation/types';
import MainTopTabs from '../../components/navigation/MainTopTabs';

type Props = NativeStackScreenProps<ResultStackParamList, 'LatestAnalysis'>;

export default function LatestAnalysisScreen({ navigation }: Props) {
  const [loading, setLoading]   = useState(true);
  const [empty, setEmpty]       = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadAndRedirect = useCallback(async () => {
    setLoading(true);
    setEmpty(false);
    setErrorMsg(null);
    try {
      const sessions = await getSessions();
      const completed = sessions
        .filter((s: Session) => s.analysis_status === 'completed')
        .sort((a: Session, b: Session) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
      if (completed.length === 0) {
        setEmpty(true);
        return;
      }
      const latest = completed[0];
      const detail = await getSessionDetail(latest.session_id);
      const runId  = extractRunId(detail);
      if (!runId) {
        setEmpty(true);
        return;
      }
      const songId = latest.song?.id ?? latest.song_id;
      // reset으로 이동 — 백 버튼 시 빈 LatestAnalysis로 돌아가지 않음
      navigation.dispatch(
        CommonActions.reset({
          index: 0,
          routes: [{ name: 'EvalResult', params: { runId, songId } }],
        }),
      );
    } catch (e: any) {
      if (isAuthExpiredError(e)) return;
      setErrorMsg('분석 결과를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [navigation]);

  // 탭 포커스 시마다 최신 세션 fetch + 이동
  useFocusEffect(
    useCallback(() => {
      loadAndRedirect();
    }, [loadAndRedirect]),
  );

  if (loading) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.loadingText}>최신 분석 결과를 불러오는 중입니다.</Text>
        </View>
      </View>
    );
  }

  if (errorMsg) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <Text style={styles.errorText}>{errorMsg}</Text>
          <Text style={styles.errorSubtext}>네트워크 상태를 확인한 뒤 다시 시도해 주세요.</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={loadAndRedirect}>
            <Text style={styles.retryText}>다시 불러오기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (empty) {
    return (
      <View style={styles.container}>
        <MainTopTabs activeTab="RecordTab" style={styles.topTabs} />
        <View style={styles.center}>
          <Text style={styles.emptyIcon}>📈</Text>
          <Text style={styles.emptyTitle}>아직 분석 기록이 없습니다.</Text>
          <Text style={styles.emptySubtitle}>홈에서 노래를 선택해 녹음하고 분석하면 결과가 표시됩니다.</Text>
          <TouchableOpacity
            style={styles.homeBtn}
            onPress={() => navigation.getParent<BottomTabNavigationProp<MainTabParamList>>()?.navigate('HomeTab', { screen: 'Home' })}
          >
            <Text style={styles.homeBtnText}>홈에서 곡 선택하기</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // redirect 진행 중 — 빈 화면 (보통 잠깐만 보임)
  return <View style={styles.center} />;
}

const styles = StyleSheet.create({
  container:     { flex: 1, backgroundColor: COLORS.background },
  topTabs:       { paddingTop: 60 },
  center:        { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background, gap: SPACING.sm, padding: SPACING.base },
  loadingText:   { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:     { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center' },
  errorSubtext:  { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  retryBtn:      { paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: SPACING.sm },
  retryText:     { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '600' },
  emptyIcon:     { fontSize: 56 },
  emptyTitle:    { ...TYPOGRAPHY.subheading, color: COLORS.textPrimary },
  emptySubtitle: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },
  homeBtn:       { paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, borderRadius: 10, backgroundColor: COLORS.primary, marginTop: SPACING.base },
  homeBtnText:   { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '600' },
});
