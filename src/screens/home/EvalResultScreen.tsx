import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import EvalItemCard from '../../components/eval/EvalItemCard';
import { analyzeApi } from '../../api/analyze';
import { EVALUATION_ITEMS } from '../../domain/evaluationItems';
import type { AnalyzeResult } from '../../types/analyze';
import type { EvaluationItemKey } from '../../domain/evaluationItems';

type Tab = 'basic' | 'advanced';

// TODO(Step E): 사용자 목표에서 가져오기
const FOCUS_ITEMS_FROM_USER: EvaluationItemKey[] = [];

const BASE_ITEMS: EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact'];

export default function EvalResultScreen() {
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading]  = useState(true);
  const [tab, setTab] = useState<Tab>('basic');

  useEffect(() => {
    analyzeApi.analyze({ fileUri: '', songId: '', userId: '' })
      .then(data => { setResult(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>분석 중...</Text>
      </View>
    );
  }

  if (!result) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>분석 결과를 불러올 수 없습니다.</Text>
      </View>
    );
  }

  const basicItems: EvaluationItemKey[] = [
    ...BASE_ITEMS,
    ...FOCUS_ITEMS_FROM_USER.filter(k => !BASE_ITEMS.includes(k)),
  ];

  // 고급 탭: high → medium → unavailable 순
  const advancedItems: EvaluationItemKey[] = [
    ...result.reliability.high_reliability,
    ...result.reliability.medium_reliability,
    ...result.reliability.unavailable,
  ];

  const renderCard = (key: EvaluationItemKey) => {
    const meta     = EVALUATION_ITEMS.find(m => m.key === key)!;
    const scoreEntry = result.scores[key];
    const fb       = result.feedback[key];
    // 응답 confidence 우선, 없으면 defaultConfidence 폴백
    const confidence = scoreEntry?.confidence ?? meta.defaultConfidence;

    return (
      <EvalItemCard
        key={key}
        itemKey={key}
        nameKo={meta.nameKo}
        score={scoreEntry?.ai_score ?? null}
        zone={scoreEntry?.zone ?? null}
        confidence={confidence}
        feedbackText={fb?.feedback_text ?? ''}
        scoreDescription={fb?.score_description}
        isFocus={FOCUS_ITEMS_FROM_USER.includes(key)}
      />
    );
  };

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.headerBar}>
        <Text style={styles.headerTitle}>평가 결과</Text>
        <Text style={styles.headerMeta}>
          처리 시간 {result.processing_time_ms}ms · {result.audio_info.duration_sec.toFixed(1)}초
        </Text>
      </View>

      {/* 탭 */}
      <View style={styles.tabRow}>
        {(['basic', 'advanced'] as Tab[]).map(t => (
          <TouchableOpacity
            key={t}
            style={[styles.tabBtn, tab === t && styles.tabBtnActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabLabel, tab === t && styles.tabLabelActive]}>
              {t === 'basic' ? '기본' : '고급'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {tab === 'basic'
          ? basicItems.map(renderCard)
          : advancedItems.map(renderCard)
        }
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  center: {
    flex: 1,
    backgroundColor: COLORS.background,
    justifyContent: 'center',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  loadingText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  errorText: {
    ...TYPOGRAPHY.body,
    color: COLORS.danger,
  },
  headerBar: {
    paddingHorizontal: SPACING.base,
    paddingTop: SPACING.base,
    paddingBottom: SPACING.sm,
  },
  headerTitle: {
    ...TYPOGRAPHY.heading,
    color: COLORS.textPrimary,
  },
  headerMeta: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  tabRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: COLORS.divider,
    marginHorizontal: SPACING.base,
  },
  tabBtn: {
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.base,
    marginRight: SPACING.sm,
  },
  tabBtnActive: {
    borderBottomWidth: 2,
    borderBottomColor: COLORS.primary,
  },
  tabLabel: {
    ...TYPOGRAPHY.body,
    color: COLORS.textMuted,
  },
  tabLabelActive: {
    color: COLORS.primary,
    fontWeight: '600',
  },
  scroll: {
    padding: SPACING.base,
    paddingBottom: SPACING.xl,
  },
});
