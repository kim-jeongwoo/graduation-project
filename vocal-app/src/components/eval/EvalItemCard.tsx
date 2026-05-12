import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../../utils/colors';
import { SPACING, TYPOGRAPHY, FOCUS_BORDER_COLOR, FOCUS_BORDER_WIDTH } from '../../theme/tokens';
import ScoreGauge from './ScoreGauge';
import ConfidenceBadge from './ConfidenceBadge';
import TierBadge from './TierBadge';
import type { EvaluationItemKey, ConfidenceLevel } from '../../domain/evaluationItems';
import type { Zone, ScoreTier } from '../../types/analyze';

interface EvalItemCardProps {
  itemKey: EvaluationItemKey;
  nameKo: string;
  score: number | null;
  zone: Zone | null;
  confidence: ConfidenceLevel;
  feedbackText: string;
  scoreDescription?: string;
  isFocus?: boolean;
  onTrainPress?: () => void;
  trainDisabled?: boolean;
  // v2 신규
  tier?:    ScoreTier;
  tooltip?: string | null;
  isHighlighted?: boolean;  // 호흡 카드 정적 글로우 (v2)
  isDimmed?: boolean;        // 비활성 항목 카드 전체 어둡게
}

export default function EvalItemCard({
  nameKo,
  score,
  zone,
  confidence,
  feedbackText,
  scoreDescription,
  isFocus = false,
  onTrainPress,
  trainDisabled = false,
  tier,
  tooltip,
  isHighlighted = false,
  isDimmed = false,
}: EvalItemCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={[
      CARD_STYLE,
      styles.card,
      isFocus && styles.focusCard,
      isHighlighted && styles.highlightCard,
      isDimmed && styles.dimmedCard,
    ]}>
      {/* 상단: 항목명 + 뱃지 + (옵션) 훈련 버튼 */}
      <View style={styles.header}>
        <Text style={styles.name}>{nameKo}</Text>
        <View style={styles.headerRight}>
          <TierBadge tier={tier} tooltip={tooltip} nameKo={nameKo} />
          <ConfidenceBadge confidence={confidence} />
          {onTrainPress && (
            <TouchableOpacity
              onPress={onTrainPress}
              activeOpacity={trainDisabled ? 1 : 0.7}
              style={[styles.trainBtn, trainDisabled && styles.trainBtnDisabled]}
            >
              <Text style={[styles.trainBtnText, trainDisabled && styles.trainBtnTextDisabled]}>
                이 부분 연습하기
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* 중단: 게이지 */}
      <View style={styles.gaugeArea}>
        <ScoreGauge score={score} zone={zone} size="md" />
      </View>

      {/* 하단: 피드백 */}
      <Text style={styles.feedback} numberOfLines={3}>
        {feedbackText}
      </Text>

      {/* 평가 기준표 (접기/펼치기) */}
      {scoreDescription ? (
        <>
          <TouchableOpacity onPress={() => setExpanded(v => !v)} style={styles.toggleBtn}>
            <Text style={styles.toggleText}>{expanded ? '접기 ▲' : '평가 기준 보기 ▼'}</Text>
          </TouchableOpacity>
          {expanded && (
            <Text style={styles.description}>{scoreDescription}</Text>
          )}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: SPACING.sm,
  },
  focusCard: {
    borderColor: FOCUS_BORDER_COLOR,
    borderWidth: FOCUS_BORDER_WIDTH,
  },
  // v2 호흡 카드 정적 글로우 (보라 유사색 #8B83FF)
  highlightCard: {
    borderColor:   '#8B83FF',
    borderWidth:   2,
    shadowColor:   '#8B83FF',
    shadowOffset:  { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius:  8,
    elevation:     8,
  },
  // 비활성 항목 (academic_only_v2 + deferred_v2) 카드 전체 어둡게
  dimmedCard: {
    opacity: 0.55,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  trainBtn: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  trainBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#ffffff',
  },
  trainBtnDisabled: {
    backgroundColor: COLORS.cardBorder,
    opacity: 0.5,
  },
  trainBtnTextDisabled: {
    color: COLORS.textMuted,
  },
  name: {
    ...TYPOGRAPHY.subheading,
    color: COLORS.textPrimary,
  },
  gaugeArea: {
    marginBottom: SPACING.sm,
  },
  feedback: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 22,
  },
  toggleBtn: {
    marginTop: SPACING.xs,
    alignSelf: 'flex-start',
  },
  toggleText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.primary,
  },
  description: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
    lineHeight: 18,
  },
});
