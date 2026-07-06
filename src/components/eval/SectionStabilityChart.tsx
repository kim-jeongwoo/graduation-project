import React, { useMemo } from 'react';
import { View, Text, StyleSheet, useWindowDimensions } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText } from 'react-native-svg';
import { COLORS, CARD_STYLE } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { TimelineChunkScore } from '../../types/analyze';

export type StabilityIndicatorKey = 'breathiness' | 'vocal_fold_contact' | 'soft_palate' | 'tongue_tension';

interface Props {
  timelineScores: TimelineChunkScore[];
  activeIndicatorKeys: StabilityIndicatorKey[];
}

const CHART_H = 150;
const PAD_X = 28;
const PAD_TOP = 18;
const PAD_BOTTOM = 28;
const LINE_COLOR = '#8B83FF';
const WEAK_COLOR = '#ffb4ab';

const FIELD_BY_KEY: Record<StabilityIndicatorKey, keyof TimelineChunkScore['scores']> = {
  breathiness: 'breathiness',
  vocal_fold_contact: 'vocalFoldContact',
  soft_palate: 'softPalate',
  tongue_tension: 'tongueTension',
};

const SERVER_KEY_BY_KEY: Record<StabilityIndicatorKey, string> = {
  breathiness: '4_breathiness',
  vocal_fold_contact: '3_vocal_fold_contact',
  soft_palate: '6_soft_palate',
  tongue_tension: '8_tongue_tension',
};

function formatTime(sec: number): string {
  const safeSec = Math.max(0, Math.round(sec));
  const min = Math.floor(safeSec / 60);
  const rest = safeSec % 60;
  return `${min}:${rest.toString().padStart(2, '0')}`;
}

function isLowConfidence(chunk: TimelineChunkScore, key: StabilityIndicatorKey): boolean {
  const field = FIELD_BY_KEY[key];
  const serverKey = SERVER_KEY_BY_KEY[key];
  return chunk.lowConfidenceItems?.some(item => {
    const stripped = item.replace(/^\d+_/, '');
    return item === key || item === field || item === serverKey || stripped === key;
  }) ?? false;
}

function roundedScoreToStability(score: number): number {
  const distance = score < 2 ? 2 - score : score > 3 ? score - 3 : 0;
  return Math.max(0, Math.round(100 - distance * 50));
}

export default function SectionStabilityChart({ timelineScores, activeIndicatorKeys }: Props) {
  const { width: windowWidth } = useWindowDimensions();
  const chartW = Math.max(280, Math.min(windowWidth - SPACING.base * 4, 440));
  const plotW = chartW - PAD_X * 2;
  const plotH = CHART_H - PAD_TOP - PAD_BOTTOM;

  const points = useMemo(() => {
    return timelineScores.map((chunk) => {
      const values = activeIndicatorKeys.flatMap(key => {
        if (isLowConfidence(chunk, key)) return [];
        const field = FIELD_BY_KEY[key];
        const roundedScore = chunk.scores[field]?.roundedScore;
        return typeof roundedScore === 'number' ? [roundedScoreToStability(roundedScore)] : [];
      });
      if (!values.length) return null;
      const stability = Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
      return {
        startSec: chunk.startSec,
        endSec: chunk.endSec,
        label: chunk.lrcText.trim(),
        stability,
      };
    }).filter((point): point is NonNullable<typeof point> => point !== null);
  }, [activeIndicatorKeys, timelineScores]);

  const maxEndSec = points.length ? Math.max(...points.map(point => point.endSec)) : 0;
  const minPoint = points.length
    ? points.reduce((lowest, point) => point.stability < lowest.stability ? point : lowest, points[0])
    : null;

  const path = points.map((point, index) => {
    const centerSec = (point.startSec + point.endSec) / 2;
    const x = PAD_X + (maxEndSec > 0 ? centerSec / maxEndSec : 0) * plotW;
    const y = PAD_TOP + (1 - point.stability / 100) * plotH;
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');

  const marker = minPoint && maxEndSec > 0 ? {
    x: PAD_X + (((minPoint.startSec + minPoint.endSec) / 2) / maxEndSec) * plotW,
    y: PAD_TOP + (1 - minPoint.stability / 100) * plotH,
  } : null;

  return (
    <View style={[CARD_STYLE, styles.card]}>
      <Text style={styles.title}>구간별 안정도</Text>
      <Text style={styles.subtitle}>노래 진행 중 발성 점수 흐름과 취약 구간을 확인합니다.</Text>

      {points.length < 2 ? (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyText}>구간별 점수 데이터가 부족합니다.</Text>
        </View>
      ) : (
        <>
          <Svg width={chartW} height={CHART_H}>
            {[0, 50, 100].map(value => {
              const y = PAD_TOP + (1 - value / 100) * plotH;
              return (
                <React.Fragment key={value}>
                  <Line
                    x1={PAD_X}
                    y1={y}
                    x2={chartW - PAD_X}
                    y2={y}
                    stroke={COLORS.divider}
                    strokeWidth={1}
                  />
                  <SvgText
                    x={6}
                    y={y + 4}
                    fill={COLORS.textMuted}
                    fontSize={10}
                  >
                    {value}
                  </SvgText>
                </React.Fragment>
              );
            })}

            <Path d={path} stroke={LINE_COLOR} strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />

            {marker ? (
              <>
                <Circle cx={marker.x} cy={marker.y} r={5} fill={WEAK_COLOR} />
                <SvgText
                  x={Math.min(chartW - 76, Math.max(PAD_X, marker.x + 8))}
                  y={Math.max(14, marker.y - 8)}
                  fill={WEAK_COLOR}
                  fontSize={11}
                  fontWeight="700"
                >
                  취약 구간
                </SvgText>
              </>
            ) : null}

            <SvgText x={PAD_X} y={CHART_H - 8} fill={COLORS.textMuted} fontSize={10}>
              0:00
            </SvgText>
            <SvgText x={chartW / 2 - 14} y={CHART_H - 8} fill={COLORS.textMuted} fontSize={10}>
              {formatTime(maxEndSec / 2)}
            </SvgText>
            <SvgText x={chartW - PAD_X - 28} y={CHART_H - 8} fill={COLORS.textMuted} fontSize={10}>
              {formatTime(maxEndSec)}
            </SvgText>
          </Svg>

          {minPoint ? (
            <Text style={styles.markerText} numberOfLines={2}>
              가장 흔들린 구간: {formatTime(minPoint.startSec)}~{formatTime(minPoint.endSec)}
              {minPoint.label ? ` · ${minPoint.label}` : ''}
            </Text>
          ) : null}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: SPACING.sm,
    overflow: 'hidden',
  },
  title: {
    ...TYPOGRAPHY.subheading,
    color: COLORS.textPrimary,
  },
  subtitle: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    lineHeight: 18,
    marginTop: SPACING.xs,
    marginBottom: SPACING.md,
  },
  emptyBox: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.md,
  },
  emptyText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 22,
  },
  markerText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textSecondary,
    lineHeight: 18,
    marginTop: SPACING.xs,
  },
});
