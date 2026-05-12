import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  LayoutChangeEvent,
} from 'react-native';
import { getMetricLabel } from '../utils/labels';
import { COLORS, CARD_STYLE } from '../utils/colors';

export interface DataPoint {
  sessionLabel: string;
  value: number;
}

interface Props {
  /** key → DataPoint[] 맵 (모든 파라미터 데이터) */
  datasets: Record<string, DataPoint[]>;
  /** key → unit 맵 */
  units: Record<string, string>;
  /** 숙련자 평균 (key → value). 점선 기준선으로 표시 */
  referenceMeans?: Record<string, number>;
  /** 선택 가능한 파라미터 키 목록 */
  parameterKeys: string[];
  /** 그래프 높이 (기본 200) */
  height?: number;
}

const POINT_SIZE = 10;

/**
 * 꺾은선 그래프. View로 직접 구현. 외부 라이브러리 없음.
 */
export default function TrendChart({
  datasets,
  units,
  referenceMeans,
  parameterKeys,
  height = 200,
}: Props) {
  const [selectedKey, setSelectedKey] = useState(parameterKeys[0] ?? '');
  const [tappedIdx, setTappedIdx] = useState<number | null>(null);
  const [graphWidthPx, setGraphWidthPx] = useState<number>(0);

  const data = datasets[selectedKey] ?? [];
  const unit = units[selectedKey] ?? '';
  const refVal = referenceMeans?.[selectedKey];

  const handleGraphLayout = (e: LayoutChangeEvent) => {
    setGraphWidthPx(e.nativeEvent.layout.width);
  };

  if (data.length < 2) {
    return (
      <View style={styles.container}>
        <Text style={styles.emptyText}>
          2회 이상 녹음하면 추이를 확인할 수 있습니다
        </Text>
      </View>
    );
  }

  const values = data.map((d) => d.value);
  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);
  if (refVal !== undefined) {
    minVal = Math.min(minVal, refVal);
    maxVal = Math.max(maxVal, refVal);
  }
  const padding = (maxVal - minVal) * 0.15 || 0.1;
  const yMin = minVal - padding;
  const yMax = maxVal + padding;
  const yRange = yMax - yMin || 1;
  const yMid = (yMax + yMin) / 2;

  const getY = (val: number): number => {
    return height - ((val - yMin) / yRange) * height;
  };

  const getXPx = (i: number, count: number): number => {
    return count > 1 ? (i / (count - 1)) * graphWidthPx : graphWidthPx / 2;
  };

  const count = data.length;

  return (
    <View style={styles.container}>
      {/* 파라미터 선택 칩 */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipScroll}
      >
        {parameterKeys.map((key) => (
          <TouchableOpacity
            key={key}
            style={[styles.chip, selectedKey === key && styles.chipActive]}
            onPress={() => {
              setSelectedKey(key);
              setTappedIdx(null);
            }}
          >
            <Text
              style={[
                styles.chipText,
                selectedKey === key && styles.chipTextActive,
              ]}
            >
              {getMetricLabel(key)}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* 그래프 영역 */}
      <View style={styles.graphArea}>
        {/* Y축 라벨 */}
        <View style={[styles.yAxis, { height }]}>
          <Text style={styles.yLabel}>{formatVal(yMax, unit)}</Text>
          <Text style={styles.yLabel}>{formatVal(yMid, unit)}</Text>
          <Text style={styles.yLabel}>{formatVal(yMin, unit)}</Text>
        </View>

        {/* 그래프 본체 */}
        <View
          style={[styles.graphBody, { height }]}
          onLayout={handleGraphLayout}
        >
          {/* 수평 격자선 */}
          <View style={[styles.guideLine, { top: 0 }]} />
          <View style={[styles.guideLine, { top: height / 2 }]} />
          <View style={[styles.guideLine, { top: height - 1 }]} />

          {/* 숙련자 평균 기준선 */}
          {refVal !== undefined && (
            <View style={[styles.refLine, { top: getY(refVal) }]}>
              <Text style={styles.refLabel}>
                숙련자 평균 {formatVal(refVal, unit)}
              </Text>
            </View>
          )}

          {graphWidthPx > 0 && (
            <>
              {/* 선분 연결 */}
              {data.map((_, i) => {
                if (i === 0) return null;
                const x1Px = getXPx(i - 1, count);
                const x2Px = getXPx(i, count);
                const y1 = getY(data[i - 1].value);
                const y2 = getY(data[i].value);
                const dx = x2Px - x1Px;
                const dy = y2 - y1;
                const length = Math.sqrt(dx * dx + dy * dy);
                const angle = Math.atan2(dy, dx) * (180 / Math.PI);

                return (
                  <View
                    key={`line-${i}`}
                    style={{
                      position: 'absolute',
                      left: x1Px,
                      top: y1,
                      width: length,
                      height: 2,
                      backgroundColor: COLORS.primary,
                      transform: [{ rotate: `${angle}deg` }],
                      transformOrigin: 'left center',
                    }}
                  />
                );
              })}

              {/* 데이터 포인트 + 말풍선 + X축 날짜 */}
              {data.map((d, i) => {
                const xPx = getXPx(i, count);
                const y = getY(d.value);

                return (
                  <React.Fragment key={`pt-${i}`}>
                    <TouchableOpacity
                      style={[
                        styles.point,
                        {
                          left: xPx - POINT_SIZE / 2,
                          top: y - POINT_SIZE / 2,
                        },
                      ]}
                      onPress={() =>
                        setTappedIdx(tappedIdx === i ? null : i)
                      }
                      activeOpacity={0.7}
                    >
                      {tappedIdx === i && (
                        <View style={styles.tooltip}>
                          <Text style={styles.tooltipLabel}>{d.sessionLabel}</Text>
                          <Text style={styles.tooltipValue}>
                            {formatVal(d.value, unit)}
                          </Text>
                        </View>
                      )}
                    </TouchableOpacity>

                    <Text
                      style={[
                        styles.xLabel,
                        {
                          left: xPx - 20,
                          top: height + 4,
                        },
                      ]}
                    >
                      {d.sessionLabel}
                    </Text>
                  </React.Fragment>
                );
              })}
            </>
          )}
        </View>
      </View>

      {/* X축 공간 */}
      <View style={{ height: 24, marginLeft: 45 }} />
    </View>
  );
}

function formatVal(v: number, unit: string): string {
  if (unit === '' || unit === undefined)
    return v < 10 ? v.toFixed(2) : String(Math.round(v));
  return `${v < 10 ? v.toFixed(1) : Math.round(v)}${unit}`;
}

const styles = StyleSheet.create({
  container: {
    ...CARD_STYLE,
  },
  emptyText: {
    fontSize: 14,
    color: COLORS.textMuted,
    textAlign: 'center',
    paddingVertical: 24,
  },

  chipScroll: { marginBottom: 12 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: COLORS.surface,
    marginRight: 8,
  },
  chipActive: {
    backgroundColor: COLORS.primary,
  },
  chipText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  chipTextActive: {
    color: COLORS.textPrimary,
    fontWeight: '600',
  },

  graphArea: {
    flexDirection: 'row',
  },
  yAxis: {
    width: 40,
    justifyContent: 'space-between',
    marginRight: 5,
  },
  yLabel: {
    fontSize: 10,
    color: COLORS.textSecondary,
    textAlign: 'right',
  },

  graphBody: {
    flex: 1,
    position: 'relative',
    overflow: 'visible',
  },
  guideLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.divider,
    opacity: 0.3,
  },
  refLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: COLORS.warning,
    opacity: 0.5,
  },
  refLabel: {
    position: 'absolute',
    right: 0,
    top: -14,
    fontSize: 9,
    color: COLORS.warning,
  },

  point: {
    position: 'absolute',
    width: POINT_SIZE,
    height: POINT_SIZE,
    borderRadius: POINT_SIZE / 2,
    backgroundColor: COLORS.primary,
    borderWidth: 2,
    borderColor: COLORS.primaryLight,
    zIndex: 10,
  },
  tooltip: {
    position: 'absolute',
    bottom: 16,
    left: -36,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    width: 80,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    zIndex: 100,
  },
  tooltipLabel: {
    fontSize: 9,
    color: COLORS.textMuted,
    marginBottom: 2,
  },
  tooltipValue: {
    fontSize: 11,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },

  xLabel: {
    position: 'absolute',
    width: 40,
    textAlign: 'center',
    fontSize: 10,
    color: COLORS.textMuted,
  },
});
