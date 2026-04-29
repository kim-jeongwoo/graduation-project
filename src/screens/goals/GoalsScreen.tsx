import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TextInput,
  Alert,
} from 'react-native';
import { mockAnalysisResults, mockSessions } from '../../mock/mockData';
import { useGoals } from '../../context/GoalsContext';
import type { Goal } from '../../context/GoalsContext';
import { getMetricLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';

const PARAM_OPTIONS: { key: string; label: string; unit: string }[] = [
  { key: 'contact_rate', label: '성대접촉률', unit: '%' },
  { key: 'chest_ratio', label: '흉성/두성 비율', unit: '%' },
  { key: 'oral_nasal_ratio', label: '구강/비강 비율', unit: '%' },
  { key: 'egg_correlation', label: 'EGG 상관계수', unit: '' },
];

const DIRECTION_OPTIONS: { key: 'above' | 'below'; label: string }[] = [
  { key: 'above', label: '이상 (≥)' },
  { key: 'below', label: '이하 (≤)' },
];

export default function GoalsScreen() {
  const { goals, addGoal, removeGoal } = useGoals();
  const [modalVisible, setModalVisible] = useState(false);

  // 모달 폼 상태
  const [selectedParam, setSelectedParam] = useState(PARAM_OPTIONS[0].key);
  const [targetValueStr, setTargetValueStr] = useState('');
  const [direction, setDirection] = useState<'above' | 'below'>('above');
  const [goalName, setGoalName] = useState('');

  // 최신 completed 세션의 metric 값
  const getLatestValue = useCallback((paramKey: string): number | null => {
    const completedSessions = mockSessions
      .filter((s) => s.status === 'completed')
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

    for (const s of completedSessions) {
      const result = mockAnalysisResults[s.session_id];
      if (!result) continue;
      const m = result.metrics.find((metric) => metric.key === paramKey);
      if (m) return m.value;
    }
    return null;
  }, []);

  const isGoalAchieved = (goal: Goal): boolean | null => {
    const val = getLatestValue(goal.parameter);
    if (val === null) return null;
    return goal.direction === 'above' ? val >= goal.target : val <= goal.target;
  };

  const handleAddGoal = () => {
    const targetNum = parseFloat(targetValueStr);
    if (isNaN(targetNum)) {
      Alert.alert('오류', '목표값을 올바르게 입력해주세요.');
      return;
    }
    if (!goalName.trim()) {
      Alert.alert('오류', '목표 이름을 입력해주세요.');
      return;
    }

    const newGoal: Goal = {
      id: `goal-${Date.now()}`,
      parameter: selectedParam,
      target: targetNum,
      direction,
      name: goalName.trim(),
      createdAt: new Date().toISOString().slice(0, 10),
    };

    addGoal(newGoal);
    resetModal();
  };

  const handleDeleteGoal = (goalId: string) => {
    Alert.alert('목표 삭제', '이 목표를 삭제하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제',
        style: 'destructive',
        onPress: () => removeGoal(goalId),
      },
    ]);
  };

  const resetModal = () => {
    setModalVisible(false);
    setSelectedParam(PARAM_OPTIONS[0].key);
    setTargetValueStr('');
    setDirection('above');
    setGoalName('');
  };

  const renderGoal = ({ item }: { item: Goal }) => {
    const achieved = isGoalAchieved(item);
    const latestVal = getLatestValue(item.parameter);
    const paramOption = PARAM_OPTIONS.find((p) => p.key === item.parameter);
    const unit = paramOption?.unit ?? '';
    const dirLabel = item.direction === 'above' ? '이상' : '이하';

    let statusEmoji = '⏳';
    let statusColor = COLORS.textSecondary;
    if (achieved === true) {
      statusEmoji = '✅';
      statusColor = COLORS.success;
    } else if (achieved === false) {
      statusEmoji = '❌';
      statusColor = COLORS.danger;
    }

    return (
      <View style={styles.goalCard}>
        <View style={styles.goalHeader}>
          <View style={styles.goalTitleRow}>
            <Text style={styles.goalEmoji}>{statusEmoji}</Text>
            <Text style={styles.goalName}>{item.name}</Text>
          </View>
          <TouchableOpacity onPress={() => handleDeleteGoal(item.id)}>
            <Text style={styles.deleteBtn}>🗑</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.goalBody}>
          <Text style={styles.goalMetric}>{getMetricLabel(item.parameter)}</Text>
          <Text style={styles.goalTarget}>
            {'목표: ' + item.target + unit + ' ' + dirLabel}
          </Text>
        </View>

        <View style={styles.goalFooter}>
          <Text style={styles.goalCurrent}>
            {'현재: ' +
              (latestVal !== null
                ? (item.parameter === 'egg_correlation'
                    ? latestVal.toFixed(2)
                    : latestVal.toFixed(1)) + unit
                : '데이터 없음')}
          </Text>
          <Text style={[styles.goalStatus, { color: statusColor }]}>
            {achieved === true
              ? '달성!'
              : achieved === false
                ? '미달성'
                : '측정 필요'}
          </Text>
        </View>

        {/* 달성도 프로그레스 바 */}
        {latestVal !== null && (
          <View style={styles.progressOuter}>
            <View
              style={[
                styles.progressInner,
                {
                  width: `${Math.min(100, (latestVal / item.target) * 100)}%`,
                  backgroundColor: achieved ? COLORS.success : COLORS.warning,
                },
              ]}
            />
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🎯 목표 관리</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Text style={styles.addButtonText}>+ 추가</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={goals}
        keyExtractor={(item) => item.id}
        renderItem={renderGoal}
        contentContainerStyle={
          goals.length === 0 ? styles.emptyContainer : styles.listContent
        }
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>🎯</Text>
            <Text style={styles.emptyText}>설정된 목표가 없습니다</Text>
            <Text style={styles.emptySubtext}>
              + 추가 버튼을 눌러 목표를 설정하세요
            </Text>
          </View>
        }
      />

      {/* 목표 추가 모달 */}
      <Modal visible={modalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>새 목표 추가</Text>

            {/* 목표 이름 */}
            <Text style={styles.fieldLabel}>목표 이름</Text>
            <TextInput
              style={styles.textInput}
              placeholder="예: 성대접촉률 최적화"
              placeholderTextColor={COLORS.textMuted}
              value={goalName}
              onChangeText={setGoalName}
            />

            {/* 파라미터 선택 */}
            <Text style={styles.fieldLabel}>분석 항목</Text>
            <View style={styles.chipRow}>
              {PARAM_OPTIONS.map((p) => (
                <TouchableOpacity
                  key={p.key}
                  style={[
                    styles.chip,
                    selectedParam === p.key && styles.chipSelected,
                  ]}
                  onPress={() => setSelectedParam(p.key)}
                >
                  <Text
                    style={[
                      styles.chipText,
                      selectedParam === p.key && styles.chipTextSelected,
                    ]}
                  >
                    {p.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* 방향 선택 */}
            <Text style={styles.fieldLabel}>조건</Text>
            <View style={styles.chipRow}>
              {DIRECTION_OPTIONS.map((d) => (
                <TouchableOpacity
                  key={d.key}
                  style={[
                    styles.chip,
                    direction === d.key && styles.chipSelected,
                  ]}
                  onPress={() => setDirection(d.key)}
                >
                  <Text
                    style={[
                      styles.chipText,
                      direction === d.key && styles.chipTextSelected,
                    ]}
                  >
                    {d.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* 목표값 */}
            <Text style={styles.fieldLabel}>목표값</Text>
            <TextInput
              style={styles.textInput}
              placeholder="예: 45"
              placeholderTextColor={COLORS.textMuted}
              keyboardType="numeric"
              value={targetValueStr}
              onChangeText={setTargetValueStr}
            />

            {/* 버튼 */}
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={resetModal}>
                <Text style={styles.cancelBtnText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={handleAddGoal}>
                <Text style={styles.confirmBtnText}>추가</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: COLORS.card,
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textPrimary },
  addButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  addButtonText: { color: '#FFF', fontSize: 14, fontWeight: '600' },

  listContent: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyView: { alignItems: 'center' },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, color: COLORS.textSecondary },
  emptySubtext: { fontSize: 13, color: COLORS.textMuted, marginTop: 4 },

  goalCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  goalTitleRow: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  goalEmoji: { fontSize: 20, marginRight: 8 },
  goalName: { fontSize: 16, fontWeight: '700', color: COLORS.textPrimary, flex: 1 },
  deleteBtn: { fontSize: 18, padding: 4 },

  goalBody: { marginBottom: 8 },
  goalMetric: { fontSize: 13, color: COLORS.textSecondary },
  goalTarget: { fontSize: 14, color: COLORS.textSecondary, marginTop: 2 },

  goalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  goalCurrent: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '500' },
  goalStatus: { fontSize: 14, fontWeight: '600' },

  progressOuter: {
    height: 6,
    backgroundColor: COLORS.surface,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressInner: { height: 6, borderRadius: 3 },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 20 },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
    marginTop: 12,
  },
  textInput: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    color: COLORS.textPrimary,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: COLORS.surface,
  },
  chipSelected: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  chipText: { fontSize: 13, color: COLORS.textSecondary },
  chipTextSelected: { color: '#FFF', fontWeight: '600' },

  modalActions: { flexDirection: 'row', gap: 10, marginTop: 20 },
  cancelBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  cancelBtnText: { fontSize: 15, color: COLORS.textMuted },
  confirmBtn: {
    flex: 1,
    padding: 14,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  confirmBtnText: { fontSize: 15, color: '#FFF', fontWeight: '600' },
});
