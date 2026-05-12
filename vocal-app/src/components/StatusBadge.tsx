import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getStatusLabel, getStatusColor } from '../utils/labels';

interface Props {
  status: string;
}

export default function StatusBadge({ status }: Props) {
  const color = getStatusColor(status);
  return (
    <View style={[styles.badge, { backgroundColor: color.bg }]}>
      <Text style={[styles.text, { color: color.text }]}>
        {getStatusLabel(status)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
  },
});
