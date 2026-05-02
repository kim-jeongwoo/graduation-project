import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';

type TabParamList = {
  HomeTab: { screen: string; params?: Record<string, unknown> };
  RecordTab: undefined;
  HistoryTab: undefined;
  GoalsTab: undefined;
};

// [P0 검증용] run_id 직접 입력 → EvalResultScreen 진입
// P1에서 실제 녹음 화면으로 교체 예정
export default function RecordScreen() {
  const navigation = useNavigation<BottomTabNavigationProp<TabParamList>>();
  const [runId, setRunId] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFetch = async () => {
    const trimmed = runId.trim();
    if (!trimmed) return;
    setLoading(true);
    navigation.navigate('HomeTab', {
      screen: 'EvalResult',
      params: { runId: trimmed },
    });
    setLoading(false);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>분석 결과 조회</Text>
      <Text style={styles.subtitle}>서버에서 받은 run_id를 입력하세요 (P0 검증용)</Text>

      <TextInput
        style={styles.input}
        placeholder="run_id (예: abc12345-...)"
        placeholderTextColor={COLORS.textMuted}
        autoCapitalize="none"
        autoCorrect={false}
        value={runId}
        onChangeText={setRunId}
      />

      <TouchableOpacity
        style={[styles.button, (!runId.trim() || loading) && styles.buttonDisabled]}
        onPress={handleFetch}
        disabled={!runId.trim() || loading}
      >
        {loading
          ? <ActivityIndicator color={COLORS.background} />
          : <Text style={styles.buttonText}>결과 조회</Text>
        }
      </TouchableOpacity>

      <Text style={styles.hint}>
        USE_MOCK=true 시 run_id 무관하게 mock 결과 표시
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    padding: SPACING.base,
    justifyContent: 'center',
    gap: SPACING.md,
  },
  title: { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, textAlign: 'center' },
  subtitle: { ...TYPOGRAPHY.body, color: COLORS.textSecondary, textAlign: 'center' },
  input: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 14,
    fontSize: 14,
    backgroundColor: COLORS.card,
    color: COLORS.textPrimary,
    marginTop: SPACING.sm,
  },
  button: {
    backgroundColor: COLORS.primary,
    paddingVertical: SPACING.md,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.45 },
  buttonText: { ...TYPOGRAPHY.subheading, color: COLORS.background },
  hint: {
    ...TYPOGRAPHY.caption,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: SPACING.sm,
  },
});
