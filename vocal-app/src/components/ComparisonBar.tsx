import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getMetricLabel } from '../utils/labels';
import { COLORS, CARD_STYLE } from '../utils/colors';

interface Props {
  label: string;
  userValue: number;
  referenceMean: number;
  zScore: number;
  percentile: number;
}

export default function ComparisonBar({
  label,
  userValue,
  referenceMean,
  zScore,
  percentile,
}: Props) {
  // 바 범위 계산: 숙련자 평균을 중앙에 놓기 위한 스케일
  const spread = Math.max(Math.abs(userValue - referenceMean) * 2, referenceMean * 0.4);
  const barMin = referenceMean - spread;
  const barMax = referenceMean + spread;
  const range = barMax - barMin;

  const refPct = ((referenceMean - barMin) / range) * 100;
  const userPct = Math.min(Math.max(((userValue - barMin) / range) * 100, 2), 98);

  // z_score 기반 색상
  const absZ = Math.abs(zScore);
  let markerColor = '#4CAF50'; // 기본 초록
  if (absZ >= 2) markerColor = '#F44336'; // 빨강
  else if (absZ >= 1) markerColor = '#FFC107'; // 노랑

  // ±1σ 영역
  const sigma = range > 0 ? (spread / 2) : 10;
  const sigmaMinPct = Math.max(((referenceMean - sigma * 0.5 - barMin) / range) * 100, 0);
  const sigmaWidthPct = Math.min((sigma / range) * 100, 100 - sigmaMinPct);

  const percentileText = percentile >= 50
    ? `상위 ${100 - percentile}%`
    : `하위 ${percentile}%`;

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.barContainer}>
        {/* ±1σ 구간 */}
        <View
          style={[
            styles.sigmaZone,
            { left: `${sigmaMinPct}%`, width: `${sigmaWidthPct}%` },
          ]}
        />
        {/* 숙련자 평균 기준선 */}
        <View style={[styles.refLine, { left: `${refPct}%` }]} />
        {/* 내 수치 마커 */}
        <View style={[styles.userMarker, { left: `${userPct}%`, backgroundColor: markerColor }]} />
      </View>
      <View style={styles.infoRow}>
        <Text style={styles.infoText}>내 수치: {userValue}</Text>
        <Text style={styles.infoText}>평균: {referenceMean}</Text>
        <Text style={[styles.percentileText, { color: markerColor }]}>{percentileText}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...CARD_STYLE,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 10,
  },
  barContainer: {
    height: 20,
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    position: 'relative',
    overflow: 'hidden',
  },
  sigmaZone: {
    position: 'absolute',
    top: 0,
    height: 20,
    backgroundColor: 'rgba(76, 175, 80, 0.15)',
  },
  refLine: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 20,
    backgroundColor: COLORS.textMuted,
    marginLeft: -1,
  },
  userMarker: {
    position: 'absolute',
    top: 2,
    width: 16,
    height: 16,
    borderRadius: 8,
    marginLeft: -8,
    borderWidth: 2,
    borderColor: COLORS.card,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  infoText: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  percentileText: {
    fontSize: 12,
    fontWeight: '600',
  },
});
