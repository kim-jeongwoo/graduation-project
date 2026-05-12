import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../utils/colors';

interface Props {
  label: string;
  value: number;
  unit: string;
  type: 'gauge' | 'ratio' | 'text';
  range?: { min: number; max: number; optimalMin?: number; optimalMax?: number };
  leftLabel?: string;
  rightLabel?: string;
}

export default function MetricCard({
  label,
  value,
  unit,
  type,
  range,
  leftLabel,
  rightLabel,
}: Props) {
  const renderGauge = () => {
    const min = range?.min ?? 0;
    const max = range?.max ?? 100;
    const clamped = Math.min(Math.max(value, min), max);
    const pct = ((clamped - min) / (max - min)) * 100;

    // 게이지바 색상: 적정 범위 안이면 초록, 밖이면 주황
    let barColor = '#4CAF50';
    if (range?.optimalMin !== undefined && range?.optimalMax !== undefined) {
      if (value < range.optimalMin || value > range.optimalMax) {
        barColor = '#FF9800';
      }
    }

    return (
      <View>
        <Text style={styles.valueText}>
          {unit === '' ? value.toFixed(2) : `${value}${unit}`}
        </Text>
        <View style={styles.gaugeTrack}>
          {/* 적정 범위 표시 */}
          {range?.optimalMin !== undefined && range?.optimalMax !== undefined && (
            <View
              style={[
                styles.optimalZone,
                {
                  left: `${((range.optimalMin - min) / (max - min)) * 100}%`,
                  width: `${((range.optimalMax - range.optimalMin) / (max - min)) * 100}%`,
                },
              ]}
            />
          )}
          <View style={[styles.gaugeFill, { width: `${pct}%`, backgroundColor: barColor }]} />
        </View>
      </View>
    );
  };

  const renderRatio = () => {
    const pct = Math.min(Math.max(value, 0), 100);
    return (
      <View>
        <Text style={styles.valueText}>{value}{unit}</Text>
        <View style={styles.ratioLabelRow}>
          <Text style={styles.ratioLabel}>{leftLabel ?? ''}</Text>
          <Text style={styles.ratioLabel}>{rightLabel ?? ''}</Text>
        </View>
        <View style={styles.gaugeTrack}>
          <View style={[styles.ratioFillLeft, { width: `${pct}%` }]} />
          <View style={[styles.ratioFillRight, { width: `${100 - pct}%` }]} />
        </View>
      </View>
    );
  };

  const renderText = () => (
    <Text style={styles.valueTextLarge}>
      {value}{unit ? ` ${unit}` : ''}
    </Text>
  );

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      {type === 'gauge' && renderGauge()}
      {type === 'ratio' && renderRatio()}
      {type === 'text' && renderText()}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...CARD_STYLE,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  valueText: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  valueTextLarge: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  gaugeTrack: {
    height: 10,
    backgroundColor: COLORS.surface,
    borderRadius: 5,
    overflow: 'hidden',
    position: 'relative',
  },
  gaugeFill: {
    height: 10,
    borderRadius: 5,
  },
  optimalZone: {
    position: 'absolute',
    top: 0,
    height: 10,
    backgroundColor: 'rgba(76, 175, 80, 0.15)',
  },
  ratioLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  ratioLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  ratioFillLeft: {
    height: 10,
    backgroundColor: '#2196F3',
    borderTopLeftRadius: 5,
    borderBottomLeftRadius: 5,
  },
  ratioFillRight: {
    height: 10,
    backgroundColor: '#FF9800',
    borderTopRightRadius: 5,
    borderBottomRightRadius: 5,
  },
});
