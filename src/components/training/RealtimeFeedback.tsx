import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';

// ─── 음정 ───
export type PitchVerdict = 'accurate' | 'slight_off' | 'wrong' | 'unknown';

export function pitchVerdictFromScore(score: number | null): PitchVerdict {
  if (score === null) return 'unknown';
  if (score >= 0.92) return 'accurate';
  if (score >= 0.7)  return 'slight_off';
  return 'wrong';
}

const PITCH_COLOR: Record<PitchVerdict, string> = {
  accurate:   '#59dda5',
  slight_off: '#ffb780',
  wrong:      '#ffb4ab',
  unknown:    COLORS.textMuted,
};

const PITCH_TEXT: Record<PitchVerdict, string> = {
  accurate:   '정확해요',
  slight_off: '조금 더 정확하게',
  wrong:      '음정이 어긋났어요',
  unknown:    '측정 중...',
};

interface PitchCardProps {
  verdict: PitchVerdict;
  matchScore: number | null;  // 0~1
}

export function PitchCard({ verdict, matchScore }: PitchCardProps) {
  const color = PITCH_COLOR[verdict];
  const text  = PITCH_TEXT[verdict];
  const fillPct = matchScore !== null ? Math.max(0, Math.min(1, matchScore)) * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 음정 일치율</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.verdictText, { color }]}>{text}</Text>
    </View>
  );
}

// ─── 호흡 ───
const BREATH_COLOR: Record<Zone | 'unknown', string> = {
  appropriate:  '#59dda5',
  excessive:    '#ffb4ab',  // 압축됨 — 빨강
  insufficient: '#ffb4ab',  // 호흡 새는 소리 — 빨강
  unknown:      COLORS.textMuted,
};

const BREATH_TEXT: Record<Zone | 'unknown', string> = {
  appropriate:  '호흡 적절',
  excessive:    '성대를 너무 모으고 있어요',
  insufficient: '호흡이 새는 소리가 많아요',
  unknown:      '측정 중...',
};

interface BreathCardProps {
  zone:    Zone | null;     // null이면 "측정 중"
  aiScore: number | null;
}

export function BreathCard({ zone, aiScore }: BreathCardProps) {
  const key   = (zone ?? 'unknown') as Zone | 'unknown';
  const color = BREATH_COLOR[key];
  const text  = BREATH_TEXT[key];
  // 게이지: ai_score (0~5) 비율로 표시
  const fillPct = aiScore !== null ? Math.max(0, Math.min(5, aiScore)) / 5 * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 호흡</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <View style={styles.row}>
        <Text style={[styles.verdictText, { color }]}>{text}</Text>
        {aiScore !== null && (
          <Text style={styles.scoreText}>{aiScore.toFixed(2)}점</Text>
        )}
      </View>
    </View>
  );
}

// ─── 호흡 안내 (vocal_fold_contact 진입 시 BreathCard 자리에 표시) ───
export function BreathInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>성대 접촉 강도</Text>
      <Text style={styles.infoText}>
        성대 접촉은 녹음 종료 후 측정됩니다.{'\n'}
        노래 끝나면 '이번 시도 점수 보기' 버튼을 눌러주세요.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.base,
    marginHorizontal: SPACING.base,
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  label: {
    fontSize: 11,
    color: COLORS.textSecondary,
  },
  gaugeTrack: {
    height: 10,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 5,
    overflow: 'hidden',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: 5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  verdictText: {
    ...TYPOGRAPHY.body,
    fontWeight: '700',
  },
  scoreText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
  infoText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 20,
  },
});
