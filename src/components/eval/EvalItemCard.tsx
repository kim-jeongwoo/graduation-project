import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../../utils/colors';
import { SPACING, TYPOGRAPHY, FOCUS_BORDER_COLOR, FOCUS_BORDER_WIDTH } from '../../theme/tokens';
import ScoreGauge from './ScoreGauge';
import ConfidenceBadge from './ConfidenceBadge';
import type { EvaluationItemKey, ConfidenceLevel } from '../../domain/evaluationItems';
import type { Zone } from '../../types/analyze';

interface EvalItemCardProps {
  itemKey: EvaluationItemKey;
  nameKo: string;
  score: number | null;
  zone: Zone | null;
  confidence: ConfidenceLevel;
  feedbackText: string;
  scoreDescription?: string;
  isFocus?: boolean;
}

export default function EvalItemCard({
  nameKo,
  score,
  zone,
  confidence,
  feedbackText,
  scoreDescription,
  isFocus = false,
}: EvalItemCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={[
      CARD_STYLE,
      styles.card,
      isFocus && styles.focusCard,
    ]}>
      {/* 상단: 항목명 + 뱃지 */}
      <View style={styles.header}>
        <Text style={styles.name}>{nameKo}</Text>
        <ConfidenceBadge confidence={confidence} />
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
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
