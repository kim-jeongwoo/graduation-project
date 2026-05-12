import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ZONE_COLORS } from '../../theme/tokens';
import { COLORS } from '../../utils/colors';
import type { Zone } from '../../types/analyze';

interface ScoreGaugeProps {
  score: number | null;
  zone: Zone | null;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const CELL_HEIGHTS = { sm: 10, md: 14, lg: 18 } as const;
const LABEL_SIZES  = { sm: 11, md: 13, lg: 15 } as const;
const TOTAL_CELLS  = 6; // 0~5

export default function ScoreGauge({ score, zone, size = 'md', label }: ScoreGaugeProps) {
  const cellHeight = CELL_HEIGHTS[size];
  const labelSize  = LABEL_SIZES[size];
  const isUnavailable = score === null;

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={[styles.label, { fontSize: labelSize }]}>{label}</Text> : null}
      <View style={styles.barRow}>
        {Array.from({ length: TOTAL_CELLS }, (_, i) => {
          const isActive = !isUnavailable && i === score;
          const bgColor  = isActive && zone ? ZONE_COLORS[zone] : COLORS.surface;
          return (
            <View
              key={i}
              style={[
                styles.cell,
                { height: cellHeight, backgroundColor: bgColor },
                isActive && styles.cellActive,
              ]}
            />
          );
        })}
      </View>
      <View style={styles.scoreRow}>
        {isUnavailable ? (
          <Text style={[styles.unavailableText, { fontSize: labelSize }]}>AI 측정 불가</Text>
        ) : (
          <>
            <Text style={[styles.scoreText, { fontSize: labelSize, color: zone ? ZONE_COLORS[zone] : COLORS.textPrimary }]}>
              {score}점
            </Text>
            <Text style={[styles.zoneText, { fontSize: labelSize - 1 }]}>
              {zone === 'insufficient' ? '미달' : zone === 'appropriate' ? '적절' : '과함'}
            </Text>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
  },
  label: {
    color: COLORS.textSecondary,
    marginBottom: 6,
  },
  barRow: {
    flexDirection: 'row',
    gap: 3,
  },
  cell: {
    flex: 1,
    borderRadius: 3,
    opacity: 0.5,
  },
  cellActive: {
    opacity: 1,
    transform: [{ scaleY: 1.25 }],
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 5,
  },
  scoreText: {
    fontWeight: '700',
  },
  zoneText: {
    color: COLORS.textSecondary,
  },
  unavailableText: {
    color: COLORS.textMuted,
    fontStyle: 'italic',
  },
});
