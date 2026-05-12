import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CONFIDENCE_COLORS } from '../../theme/tokens';
import type { ConfidenceLevel } from '../../domain/evaluationItems';

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === 'high') return null;

  const label = confidence === 'medium' ? '베타' : '측정 불가';
  const color = CONFIDENCE_COLORS[confidence];

  return (
    <View style={[styles.badge, { borderColor: color }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  text: {
    fontSize: 10,
    fontWeight: '600',
  },
});
