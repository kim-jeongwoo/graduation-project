import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';
import { ZONE_LABELS, zoneColor } from '../../domain/weakSections';

export interface BeforeAfterScore {
  aiScore: number;
  zone:    Zone;
}

interface Props {
  before: BeforeAfterScore;
  after:  BeforeAfterScore;
  beforeLowConfidence?: boolean;
  afterLowConfidence?:  boolean;
}

/**
 * 개선도 판정 — zone 기준 (단순 점수 차이는 부정확)
 *  - appropriate으로 진입 = 개선
 *  - appropriate에서 벗어남 = 악화
 *  - zone 동일 + 점수도 거의 같음 = 변화 없음
 *  - zone 동일 + appropriate 방향으로 점수 이동 = 개선
 *  - zone 동일 + appropriate에서 멀어짐 = 악화
 */
function judgeImprovement(before: BeforeAfterScore, after: BeforeAfterScore): {
  label: string;
  color: string;
} {
  const diff = after.aiScore - before.aiScore;
  const diffStr = (diff >= 0 ? '+' : '') + diff.toFixed(1);

  // zone 변화
  if (before.zone !== after.zone) {
    if (after.zone === 'appropriate') return { label: `${diffStr} 개선`, color: '#59dda5' };
    if (before.zone === 'appropriate') return { label: `${diffStr} 악화`, color: '#ffb4ab' };
    // 둘 다 비-적절 (insufficient ↔ excessive 전환)
    return { label: `${diffStr} 변화`, color: COLORS.textSecondary };
  }

  // zone 동일
  if (Math.abs(diff) < 0.2) return { label: '변화 없음', color: COLORS.textSecondary };

  // appropriate 영역(중심 3 가정)에서 벗어난 정도
  const TARGET = 3;
  const beforeDist = Math.abs(before.aiScore - TARGET);
  const afterDist  = Math.abs(after.aiScore  - TARGET);
  if (afterDist < beforeDist) return { label: `${diffStr} 개선`, color: '#59dda5' };
  return { label: `${diffStr} 악화`, color: '#ffb4ab' };
}

export default function ResultCard({ before, after, beforeLowConfidence, afterLowConfidence }: Props) {
  const verdict = judgeImprovement(before, after);
  return (
    <View style={styles.card}>
      <Text style={styles.title}>이번 시도 결과</Text>
      <View style={styles.row}>
        <ScoreCol label="원본 점수" score={before} lowConfidence={beforeLowConfidence} />
        <Text style={styles.arrow}>→</Text>
        <ScoreCol label="이번 시도" score={after} lowConfidence={afterLowConfidence} />
      </View>
      <Text style={[styles.verdict, { color: verdict.color }]}>{verdict.label}</Text>
    </View>
  );
}

function ScoreCol({ label, score, lowConfidence }: { label: string; score: BeforeAfterScore; lowConfidence?: boolean }) {
  return (
    <View style={styles.col}>
      <Text style={styles.colLabel}>{label}</Text>
      <Text style={[styles.colScore, { color: zoneColor(score.zone) }]}>
        {score.aiScore.toFixed(2)}
      </Text>
      <Text style={styles.colZone}>{ZONE_LABELS[score.zone]}</Text>
      {lowConfidence && <Text style={styles.lowConfidence}>신뢰도 낮음</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.base,
    marginHorizontal: SPACING.base,
    marginTop: SPACING.base,
    gap: SPACING.sm,
  },
  title:    { ...TYPOGRAPHY.subheading, color: COLORS.textPrimary },
  row:      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', paddingVertical: SPACING.sm },
  col:      { alignItems: 'center', gap: 4 },
  colLabel: { fontSize: 11, color: COLORS.textSecondary },
  colScore: { fontSize: 24, fontWeight: '800' },
  colZone:  { fontSize: 12, color: COLORS.textPrimary },
  lowConfidence: { fontSize: 11, color: COLORS.textMuted },
  arrow:    { fontSize: 20, color: COLORS.textMuted, paddingHorizontal: 8 },
  verdict:  { ...TYPOGRAPHY.body, fontWeight: '700', textAlign: 'center' },
});
