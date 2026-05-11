import React from 'react';
import { Text, TouchableOpacity, Alert, StyleSheet } from 'react-native';
import type { ScoreTier } from '../../types/analyze';

interface Props {
  tier?:    ScoreTier;
  tooltip?: string | null;
  nameKo?:  string;
}

// v2 score_mapper_v2 — high_star tier 항목에 별표(*) 표시. tap 시 tooltip Alert.
export default function TierBadge({ tier, tooltip, nameKo }: Props) {
  if (tier !== 'high_star') return null;
  return (
    <TouchableOpacity
      onPress={() => {
        if (tooltip) {
          Alert.alert(`${nameKo ?? '항목'} 신뢰도`, tooltip);
        }
      }}
      hitSlop={{ top: 6, right: 6, bottom: 6, left: 6 }}
      activeOpacity={0.6}
    >
      <Text style={styles.star}>*</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  star: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFD54F',  // 골드 — ⭐ 즐겨찾기와 같은 신뢰/강조 톤
    paddingHorizontal: 2,
  },
});
