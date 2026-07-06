import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, CARD_STYLE } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';

export interface ImprovementPriorityItem {
  key: string;
  label: string;
  score: number | null;
  zone: Zone | null;
  priority: number;
  actionText: string;
  weakSectionCount: number;
  isDataMissing?: boolean;
}

interface Props {
  items: ImprovementPriorityItem[];
}

const ZONE_LABEL: Record<Zone, string> = {
  insufficient: '미달',
  appropriate: '적절',
  excessive: '과함',
};

function priorityColor(priority: number): string {
  if (priority >= 70) return '#ffb4ab';
  if (priority >= 40) return '#ffb780';
  return '#59dda5';
}

export default function ImprovementPriorityCard({ items }: Props) {
  return (
    <View style={[CARD_STYLE, styles.card]}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>개선 우선순위</Text>
        <Text style={styles.valueHeader}>개선 필요도</Text>
      </View>
      <Text style={styles.subtitle}>이번 녹음에서 먼저 확인할 발성 항목입니다.</Text>

      {items.length === 0 ? (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyText}>표시할 수 있는 분석 데이터가 부족합니다.</Text>
        </View>
      ) : (
        items.map(item => {
          const hasPriority = !item.isDataMissing && typeof item.score === 'number' && item.zone !== null;
          const priority = hasPriority ? Math.max(0, Math.min(100, item.priority)) : 0;
          const displayWidth = hasPriority ? Math.max(6, priority) : 0;
          const statusText = item.isDataMissing
            ? '데이터 부족'
            : item.zone
              ? ZONE_LABEL[item.zone]
              : '확인';

          return (
            <View key={item.key} style={styles.itemRow}>
              <View style={styles.metricRow}>
                <Text style={styles.itemLabel}>{item.label}</Text>

                <View style={styles.barColumn}>
                  <View style={styles.barTrack}>
                    {hasPriority ? (
                      <View
                        style={[
                          styles.barFill,
                          {
                            width: `${displayWidth}%`,
                            backgroundColor: priorityColor(priority),
                          },
                        ]}
                      />
                    ) : null}
                  </View>
                  <Text style={[
                    styles.statusText,
                    item.zone === 'appropriate' && styles.statusStableText,
                    item.isDataMissing && styles.statusMissingText,
                  ]}>
                    {statusText}
                  </Text>
                </View>

                <View style={styles.valueColumn}>
                  <Text style={[styles.priorityValue, !hasPriority && styles.priorityValueMissing]}>
                    {hasPriority ? Math.round(priority) : '--'}
                  </Text>
                </View>
              </View>

              <Text style={styles.actionText}>{item.actionText}</Text>
              {item.weakSectionCount > 0 ? (
                <Text style={styles.metaText}>취약 구간 {item.weakSectionCount}개 감지</Text>
              ) : null}
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#181824',
    borderRadius: 24,
    marginBottom: SPACING.sm,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: SPACING.sm,
  },
  title: {
    ...TYPOGRAPHY.subheading,
    color: COLORS.textPrimary,
    flex: 1,
  },
  valueHeader: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    fontWeight: '700',
    width: 54,
    textAlign: 'right',
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
  itemRow: {
    marginBottom: SPACING.md,
  },
  metricRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: SPACING.sm,
    marginBottom: SPACING.sm,
  },
  itemLabel: {
    ...TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    flex: 1,
    lineHeight: 21,
  },
  barColumn: {
    flex: 1.35,
    paddingTop: 6,
  },
  barTrack: {
    height: 10,
    borderRadius: 999,
    backgroundColor: '#2b2b3a',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 999,
  },
  statusText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
  },
  statusStableText: {
    color: '#59dda5',
  },
  statusMissingText: {
    color: COLORS.textMuted,
    fontStyle: 'italic',
  },
  valueColumn: {
    width: 54,
    alignItems: 'flex-end',
    paddingTop: 1,
  },
  priorityValue: {
    fontSize: 20,
    lineHeight: 24,
    fontWeight: '800',
    color: COLORS.textSecondary,
  },
  priorityValueMissing: {
    color: COLORS.textMuted,
  },
  actionText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textSecondary,
    lineHeight: 18,
    marginTop: SPACING.sm,
  },
  metaText: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
  },
});
