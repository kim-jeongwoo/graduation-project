import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { mockAnalyze } from '../../api/mock';

type TabParamList = {
  HomeTab: { screen: string };
  RecordTab: undefined;
  HistoryTab: undefined;
  GoalsTab: undefined;
};

export default function RecordScreen() {
  const navigation = useNavigation<BottomTabNavigationProp<TabParamList>>();
  const [loading, setLoading] = useState(false);

  // 임시 버튼 — 실제 녹음 기능은 후속 Step에서 구현
  const handleMockAnalyze = async () => {
    setLoading(true);
    await mockAnalyze({ fileUri: '' });
    setLoading(false);
    navigation.navigate('HomeTab', { screen: 'EvalResult' });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>녹음 화면</Text>
      <Text style={styles.subtitle}>실제 녹음 기능은 준비 중입니다.</Text>

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleMockAnalyze}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color={COLORS.background} />
        ) : (
          <Text style={styles.buttonText}>분석 시작 (Mock)</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACING.md,
    padding: SPACING.base,
  },
  title: {
    ...TYPOGRAPHY.heading,
    color: COLORS.textPrimary,
  },
  subtitle: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  button: {
    marginTop: SPACING.lg,
    backgroundColor: COLORS.primary,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.xl,
    borderRadius: 12,
    minWidth: 180,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    ...TYPOGRAPHY.subheading,
    color: COLORS.background,
  },
});
