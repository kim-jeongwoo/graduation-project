import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Modal,
  Alert,
} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '../../context/AuthContext';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { testStreamEndpoint } from '../../utils/testStream';

type NavProp = NativeStackNavigationProp<{ Profile: undefined }>;

const PITCH_NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const OCTAVES = [2, 3, 4, 5, 6];

export default function SettingsScreen() {
  const navigation = useNavigation<NavProp>();
  const { logout } = useAuth();

  const [notificationsOn, setNotificationsOn] = useState(true);
  const [vocalRangeLow, setVocalRangeLow] = useState('C3');
  const [vocalRangeHigh, setVocalRangeHigh] = useState('C5');

  // range 피커 모달
  const [rangeModalVisible, setRangeModalVisible] = useState(false);
  const [pickingType, setPickingType] = useState<'low' | 'high'>('low');
  const [tempPick, setTempPick] = useState('C3');

  const openRangePicker = (type: 'low' | 'high') => {
    setPickingType(type);
    setTempPick(type === 'low' ? vocalRangeLow : vocalRangeHigh);
    setRangeModalVisible(true);
  };

  const confirmRange = useCallback(() => {
    if (pickingType === 'low') {
      setVocalRangeLow(tempPick);
    } else {
      setVocalRangeHigh(tempPick);
    }
    setRangeModalVisible(false);
  }, [pickingType, tempPick]);

  const handleLogout = () => {
    Alert.alert('로그아웃', '로그아웃 하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '로그아웃',
        style: 'destructive',
        onPress: async () => {
          await SecureStore.deleteItemAsync('token');
          await SecureStore.deleteItemAsync('nickname');
          logout();
        },
      },
    ]);
  };

  const renderSection = (title: string, children: React.ReactNode) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );

  const renderRow = (
    label: string,
    value: string,
    onPress?: () => void,
    rightNode?: React.ReactNode,
  ) => (
    <TouchableOpacity
      style={styles.row}
      onPress={onPress}
      disabled={!onPress && !rightNode}
    >
      <Text style={styles.rowLabel}>{label}</Text>
      {rightNode ?? <Text style={styles.rowValue}>{value}</Text>}
    </TouchableOpacity>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>⚙️ 설정</Text>

      {/* 프로필 */}
      {renderSection(
        '사용자',
        renderRow('프로필 보기 / 수정', '→', () =>
          navigation.navigate('Profile'),
        ),
      )}

      {/* 음역대 */}
      {renderSection(
        '음역대 설정',
        <>
          {renderRow('최저 음역', vocalRangeLow, () => openRangePicker('low'))}
          {renderRow('최고 음역', vocalRangeHigh, () =>
            openRangePicker('high'),
          )}
        </>,
      )}

      {/* 알림 */}
      {renderSection(
        '알림',
        renderRow(
          '연습 리마인더',
          '',
          undefined,
          <Switch
            value={notificationsOn}
            onValueChange={(v) => {
              setNotificationsOn(v);
              if (v) Alert.alert('알림', '연습 리마인더 기능은 추후 업데이트 예정입니다.');
            }}
          />,
        ),
      )}

      {/* 앱 정보 */}
      {renderSection(
        '앱 정보',
        <>
          {renderRow('버전', '1.0.0 (개발 중)')}
          {renderRow('언어', '한국어')}
          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              AI 기반 보컬 발성 분석 서비스{'\n'}순천향대학교 사물인터넷학과
              {'\n'}음성 분석 연구팀
            </Text>
          </View>
        </>,
      )}

      {/* (Dev) P1-3 streaming 사전 점검 — __DEV__에서만 보임. 점검 완료 후 제거 예정. */}
      {__DEV__ && (
        <TouchableOpacity
          style={[styles.logoutBtn, { backgroundColor: COLORS.surface, marginBottom: 12 }]}
          onPress={testStreamEndpoint}
        >
          <Text style={styles.logoutBtnText}>(Dev) _test_stream 호출 (130s)</Text>
        </TouchableOpacity>
      )}

      {/* 로그아웃 */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutBtnText}>로그아웃</Text>
      </TouchableOpacity>

      {/* 음역 선택 모달 */}
      <Modal visible={rangeModalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {pickingType === 'low' ? '최저 음역 선택' : '최고 음역 선택'}
            </Text>

            <View style={styles.pitchGrid}>
              {OCTAVES.map((oct) =>
                PITCH_NOTES.map((note) => {
                  const key = `${note}${oct}`;
                  const isSelected = tempPick === key;
                  return (
                    <TouchableOpacity
                      key={key}
                      style={[
                        styles.pitchCell,
                        isSelected && styles.pitchCellSelected,
                      ]}
                      onPress={() => setTempPick(key)}
                    >
                      <Text
                        style={[
                          styles.pitchCellText,
                          isSelected && styles.pitchCellTextSelected,
                        ]}
                      >
                        {key}
                      </Text>
                    </TouchableOpacity>
                  );
                }),
              )}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setRangeModalVisible(false)}
              >
                <Text style={styles.cancelBtnText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.confirmBtn}
                onPress={confirmRange}
              >
                <Text style={styles.confirmBtnText}>확인</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingBottom: 40 },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: COLORS.card,
  },

  section: { marginTop: 20, paddingHorizontal: 16 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 8,
    marginLeft: 4,
    textTransform: 'uppercase',
  },
  sectionContent: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },

  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: COLORS.divider,
  },
  rowLabel: { fontSize: 15, color: COLORS.textPrimary },
  rowValue: { fontSize: 15, color: COLORS.textSecondary },

  infoBox: {
    backgroundColor: COLORS.surface,
    padding: 16,
  },
  infoText: { fontSize: 13, color: COLORS.textSecondary, lineHeight: 20, textAlign: 'center' },

  logoutBtn: {
    marginHorizontal: 16,
    marginTop: 32,
    padding: 16,
    borderRadius: 14,
    backgroundColor: COLORS.card,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  logoutBtnText: { fontSize: 16, fontWeight: '600', color: COLORS.danger },

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

  pitchGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
  },
  pitchCell: {
    width: 48,
    height: 40,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pitchCellSelected: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  pitchCellText: { fontSize: 13, color: COLORS.textSecondary },
  pitchCellTextSelected: { color: '#FFF', fontWeight: '700' },

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
