import React, { useState, useCallback, useEffect, useRef } from 'react';
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
import { VocalRecorder } from '../../services/audio/recorder';
import { detectPitch } from '../../services/audio/pitchDetector';
import { requestMicrophonePermission } from '../../services/audio/microphone';

type NavProp = NativeStackNavigationProp<{ Profile: undefined }>;

const PITCH_NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const OCTAVES = [2, 3, 4, 5, 6];
const CALIBRATION_DURATION_MS = 3500;
const CALIBRATION_UI_UPDATE_MS = 120;
const CALIBRATION_NO_INPUT_TIMEOUT_MS = 1800;
const CALIBRATION_MIN_SAMPLE_SEC = 2.5;
const CALIBRATION_MIN_FRAME_COUNT = 3;

function getRmsLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

export default function SettingsScreen() {
  const navigation = useNavigation<NavProp>();
  const { logout } = useAuth();

  const [notificationsOn, setNotificationsOn] = useState(true);
  const [vocalRangeLow, setVocalRangeLow] = useState('C3');
  const [vocalRangeHigh, setVocalRangeHigh] = useState('C5');
  const [calibrationModalVisible, setCalibrationModalVisible] = useState(false);
  const [calibrationRunning, setCalibrationRunning] = useState(false);
  const [calibrationLevel, setCalibrationLevel] = useState(0);
  const [calibrationElapsedSec, setCalibrationElapsedSec] = useState(0);
  const [calibrationMessage, setCalibrationMessage] = useState('');

  // range 피커 모달
  const [rangeModalVisible, setRangeModalVisible] = useState(false);
  const [pickingType, setPickingType] = useState<'low' | 'high'>('low');
  const [tempPick, setTempPick] = useState('C3');

  const calibrationRecorderRef = useRef(new VocalRecorder());
  const calibrationStartedAtRef = useRef<number | null>(null);
  const calibrationUiUpdatedAtRef = useRef(0);
  const calibrationRunIdRef = useRef(0);
  const calibrationElapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const calibrationStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const calibrationNoInputTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const calibrationStatsRef = useRef({
    frameCount: 0,
    voicedFrameCount: 0,
    levelSum: 0,
    peakLevel: 0,
  });

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

  const clearCalibrationTimers = useCallback(() => {
    if (calibrationElapsedTimerRef.current) {
      clearInterval(calibrationElapsedTimerRef.current);
      calibrationElapsedTimerRef.current = null;
    }
    if (calibrationStopTimerRef.current) {
      clearTimeout(calibrationStopTimerRef.current);
      calibrationStopTimerRef.current = null;
    }
    if (calibrationNoInputTimerRef.current) {
      clearTimeout(calibrationNoInputTimerRef.current);
      calibrationNoInputTimerRef.current = null;
    }
  }, []);

  const cleanupCalibrationRecorder = useCallback((_phase: string) => {
    calibrationRecorderRef.current.cancel().catch((e) => {
      void e;
    });
  }, []);

  const resetCalibrationUi = useCallback(() => {
    clearCalibrationTimers();
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    calibrationUiUpdatedAtRef.current = 0;
    setCalibrationRunning(false);
    setCalibrationLevel(0);
    setCalibrationElapsedSec(0);
  }, [clearCalibrationTimers]);

  useEffect(() => () => {
    clearCalibrationTimers();
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    cleanupCalibrationRecorder('unmount');
  }, [cleanupCalibrationRecorder, clearCalibrationTimers]);

  const cancelVoiceCalibration = useCallback((phase = 'cancelled') => {
    resetCalibrationUi();
    cleanupCalibrationRecorder(phase);
    setCalibrationMessage('');
    setCalibrationModalVisible(false);
  }, [cleanupCalibrationRecorder, resetCalibrationUi]);

  const finishVoiceCalibration = useCallback((runId: number) => {
    if (runId !== calibrationRunIdRef.current) return;
    clearCalibrationTimers();
    const startedAt = calibrationStartedAtRef.current;
    calibrationRunIdRef.current += 1;
    calibrationStartedAtRef.current = null;
    setCalibrationRunning(false);
    setCalibrationLevel(0);
    cleanupCalibrationRecorder('finish');

    const stats = calibrationStatsRef.current;
    const sampleDurationSec = startedAt ? Math.max(0, (Date.now() - startedAt) / 1000) : 0;
    const avgInputLevel = stats.frameCount > 0 ? stats.levelSum / stats.frameCount : 0;

    if (
      sampleDurationSec < CALIBRATION_MIN_SAMPLE_SEC
      || stats.frameCount < CALIBRATION_MIN_FRAME_COUNT
      || stats.voicedFrameCount < CALIBRATION_MIN_FRAME_COUNT
      || avgInputLevel <= 0
      || stats.peakLevel <= 0
    ) {
      const message = '마이크 입력이 감지되지 않습니다. 권한과 입력 장치를 확인해 주세요.';
      setCalibrationMessage(message);
      Alert.alert('마이크 입력 없음', message);
      return;
    }

    const message = '마이크 입력이 감지되었습니다.';
    setCalibrationMessage(message);
    Alert.alert('입력 확인됨', message);
  }, [cleanupCalibrationRecorder, clearCalibrationTimers]);

  const startVoiceCalibration = useCallback(async () => {
    if (calibrationRunning) return;
    const granted = await requestMicrophonePermission();
    if (!granted) {
      Alert.alert('마이크 권한 필요', '마이크 입력 테스트를 위해 마이크 권한이 필요합니다.');
      return;
    }

    clearCalibrationTimers();
    calibrationStatsRef.current = {
      frameCount: 0,
      voicedFrameCount: 0,
      levelSum: 0,
      peakLevel: 0,
    };
    const runId = calibrationRunIdRef.current + 1;
    calibrationRunIdRef.current = runId;
    calibrationStartedAtRef.current = Date.now();
    calibrationUiUpdatedAtRef.current = 0;
    setCalibrationElapsedSec(0);
    setCalibrationLevel(0);
    setCalibrationRunning(true);
    setCalibrationMessage('');

    calibrationElapsedTimerRef.current = setInterval(() => {
      if (runId !== calibrationRunIdRef.current) return;
      const startedAt = calibrationStartedAtRef.current;
      setCalibrationElapsedSec(startedAt ? (Date.now() - startedAt) / 1000 : 0);
    }, 250);
    calibrationNoInputTimerRef.current = setTimeout(() => {
      if (runId !== calibrationRunIdRef.current || calibrationStatsRef.current.frameCount > 0) return;
      setCalibrationMessage('마이크 입력이 감지되지 않습니다. 권한과 기기 입력을 확인한 뒤 다시 시도해 주세요.');
      resetCalibrationUi();
      cleanupCalibrationRecorder('no-input-timeout');
      Alert.alert('마이크 입력 없음', '마이크 입력이 감지되지 않습니다. 권한과 기기 입력을 확인한 뒤 다시 시도해 주세요.');
    }, CALIBRATION_NO_INPUT_TIMEOUT_MS);
    calibrationStopTimerRef.current = setTimeout(() => {
      void finishVoiceCalibration(runId);
    }, CALIBRATION_DURATION_MS);

    calibrationRecorderRef.current.start((samples) => {
        if (runId !== calibrationRunIdRef.current) return;
        const now = Date.now();
        const level = Math.min(1, getRmsLevel(samples) * 8);
        const result = detectPitch(samples);
        const stats = calibrationStatsRef.current;
        stats.frameCount += 1;
        stats.levelSum += level;
        stats.peakLevel = Math.max(stats.peakLevel, level);
        if (result.voiced && result.midi !== null) stats.voicedFrameCount += 1;
        if (now - calibrationUiUpdatedAtRef.current >= CALIBRATION_UI_UPDATE_MS) {
          calibrationUiUpdatedAtRef.current = now;
          setCalibrationLevel(level);
        }
      })
      .catch(() => {
        if (runId !== calibrationRunIdRef.current) return;
        resetCalibrationUi();
        cleanupCalibrationRecorder('start-failed');
        setCalibrationMessage('마이크 입력 테스트를 시작하지 못했습니다. 다시 시도해 주세요.');
        Alert.alert('측정 실패', '마이크 입력 테스트를 시작하지 못했습니다. 다시 시도해 주세요.');
      });
  }, [
    calibrationRunning,
    cleanupCalibrationRecorder,
    finishVoiceCalibration,
    resetCalibrationUi,
  ]);

  const handleLogout = () => {
    Alert.alert('로그아웃', '로그아웃 하시겠습니까?', [
      { text: '취소', style: 'cancel' },
      {
        text: '로그아웃',
        style: 'destructive',
        onPress: async () => {
          await SecureStore.deleteItemAsync('token');
          await SecureStore.deleteItemAsync('nickname');
          await logout();
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

  const calibrationProgress = calibrationRunning
    ? Math.min(1, calibrationElapsedSec / (CALIBRATION_DURATION_MS / 1000))
    : 0;

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

      {renderSection(
        '음성 입력',
        renderRow(
          '마이크 입력 테스트',
          '확인',
          () => setCalibrationModalVisible(true),
        ),
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

      <Modal visible={calibrationModalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>마이크 입력 테스트</Text>
            <Text style={styles.calibrationBody}>
              평소 연습할 때의 목소리 크기로 3초 이상 불러 주세요.{'\n'}
              이 기능은 마이크 입력이 감지되는지 확인하는 용도입니다.{'\n'}
              개인별 입력 기준 저장과 음역대 기반 조정은 추후 지원 예정입니다.
            </Text>
            <View style={styles.calibrationMeterTrack}>
              <View
                style={[
                  styles.calibrationMeterFill,
                  { width: `${calibrationProgress * 100}%` },
                ]}
              />
            </View>
            <Text style={styles.calibrationSummary}>
              {calibrationRunning
                ? `${calibrationElapsedSec.toFixed(1)}초 측정 중 / 입력 ${Math.round(calibrationLevel * 100)}%`
                : '아직 테스트를 시작하지 않았습니다.'}
            </Text>
            {calibrationMessage ? (
              <Text style={styles.calibrationMessage}>{calibrationMessage}</Text>
            ) : null}
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => cancelVoiceCalibration(calibrationRunning ? 'user-close-running' : 'user-close')}
              >
                <Text style={styles.cancelBtnText}>닫기</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.confirmBtn, calibrationRunning && styles.disabledBtn]}
                onPress={startVoiceCalibration}
                disabled={calibrationRunning}
              >
                <Text style={styles.confirmBtnText}>
                  {calibrationRunning ? '측정 중' : '측정 시작'}
                </Text>
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
  disabledBtn: { opacity: 0.6 },
  confirmBtnText: { fontSize: 15, color: '#FFF', fontWeight: '600' },
  calibrationBody: {
    fontSize: 14,
    color: COLORS.textSecondary,
    lineHeight: 22,
    marginBottom: 16,
  },
  calibrationMeterTrack: {
    height: 10,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 5,
    overflow: 'hidden',
  },
  calibrationMeterFill: {
    height: '100%',
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  calibrationSummary: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginTop: 10,
    lineHeight: 18,
  },
  calibrationMessage: {
    fontSize: 13,
    color: COLORS.danger,
    marginTop: 8,
    lineHeight: 18,
  },
});
