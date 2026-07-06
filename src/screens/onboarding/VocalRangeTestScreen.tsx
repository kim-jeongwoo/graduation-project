import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  ScrollView,
  Linking,
  Alert,
  Dimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useVocalProfile } from '../../context/VocalProfileContext';
import { getVoiceType, getExpansionTarget, noteToIndex } from '../../utils/noteUtils';
import { COLORS } from '../../utils/colors';
import { detectPitch, getFamousSingers } from '../../api/vocal';
import type { PitchDetectionResult, FamousSinger } from '../../types/api';

type NavProp = NativeStackNavigationProp<{
  VocalRangeTest: undefined;
  MainTabs: undefined;
  Home: undefined;
}>;

type Step = 'intro' | 'low' | 'high' | 'result' | 'expansion';
type RecordState = 'idle' | 'countdown' | 'recording' | 'analyzing' | 'success' | 'error';

const RECORD_DURATION_SEC = 5;

// ─── 음역대 시각화 상수 ───
const FULL_LOW = noteToIndex('C2');
const FULL_HIGH = noteToIndex('C6');
const FULL_RANGE = FULL_HIGH - FULL_LOW;

// ─── confidence → 메시지 ───
function getConfidenceMessage(confidence: number): string {
  if (confidence >= 0.7) return '안정적으로 감지했어요! 🎯';
  if (confidence >= 0.4) return '감지했어요! 음이 조금 흔들렸지만 괜찮아요 👍';
  return '감지했어요! 다시 측정하면 더 정확할 수 있어요';
}

export default function VocalRangeTestScreen() {
  const navigation = useNavigation<NavProp>();
  const {
    setVocalRange,
    setVoiceType,
    setExpansionGoal,
    completeTest,
  } = useVocalProfile();

  const [step, setStep] = useState<Step>('intro');

  // 측정 상태
  const [recordState, setRecordState] = useState<RecordState>('idle');
  const [detectedNote, setDetectedNote] = useState<string | null>(null);
  const [pitchResult, setPitchResult] = useState<PitchDetectionResult | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  // 카운트다운
  const [countdownNum, setCountdownNum] = useState(3);

  // 볼륨 미터링
  const [meterLevel, setMeterLevel] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);

  // 결과
  const [selectedLow, setSelectedLow] = useState<string | null>(null);
  const [selectedHigh, setSelectedHigh] = useState<string | null>(null);

  // 가수 데이터
  const [singers, setSingers] = useState<FamousSinger[]>([]);
  const [singersLoading, setSingersLoading] = useState(false);

  // 확장 단계
  const [expansionSingers, setExpansionSingers] = useState<Record<string, FamousSinger[]>>({});
  const [selectedExpansion, setSelectedExpansion] = useState<'high' | 'low' | 'both' | null>(null);

  // refs
  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 계산값
  const voiceTypeLabel =
    selectedLow && selectedHigh ? getVoiceType(selectedLow, selectedHigh) : '';
  const rangeLabel =
    selectedLow && selectedHigh ? `${selectedLow} ~ ${selectedHigh}` : '';

  // ─── 가수 정보 로딩 (결과 단계) ───
  useEffect(() => {
    if (step === 'result' && selectedLow && selectedHigh) {
      setSingersLoading(true);
      getFamousSingers(selectedLow, selectedHigh)
        .then((data) => setSingers(data))
        .catch(() => setSingers([]))
        .finally(() => setSingersLoading(false));
    }
  }, [step, selectedLow, selectedHigh]);

  // ─── 확장 단계 가수 정보 로딩 ───
  useEffect(() => {
    if (step === 'expansion' && selectedLow && selectedHigh) {
      const loadExpansionSingers = async () => {
        const highTarget = getExpansionTarget(selectedLow, selectedHigh, 'high');
        const lowTarget = getExpansionTarget(selectedLow, selectedHigh, 'low');
        const bothTarget = getExpansionTarget(selectedLow, selectedHigh, 'both');

        const results: Record<string, FamousSinger[]> = {};
        try {
          const [highS, lowS, bothS] = await Promise.all([
            getFamousSingers(selectedLow, highTarget.targetHigh).catch(() => []),
            getFamousSingers(lowTarget.targetLow, selectedHigh).catch(() => []),
            getFamousSingers(bothTarget.targetLow, bothTarget.targetHigh).catch(() => []),
          ]);
          results['high'] = highS;
          results['low'] = lowS;
          results['both'] = bothS;
        } catch {
          // ignore
        }
        setExpansionSingers(results);
      };
      loadExpansionSingers();
    }
  }, [step, selectedLow, selectedHigh]);

  const navigateHome = () => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.replace('MainTabs');
    }
  };

  const handleSkip = () => {
    completeTest();
    navigateHome();
  };

  // ─── 카운트다운 → 녹음 ───
  const startMeasurement = async () => {
    setDetectedNote(null);
    setPitchResult(null);
    setErrorMessage('');
    setMeterLevel(0);
    setElapsedSec(0);

    // 마이크 권한
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('권한 필요', '음역대 측정을 위해 마이크 권한이 필요합니다.');
        return;
      }
    } catch {
      Alert.alert('오류', '마이크 권한을 확인할 수 없습니다.');
      return;
    }

    // 카운트다운 시작
    setRecordState('countdown');
    setCountdownNum(3);

    let count = 3;
    const cdInterval = setInterval(() => {
      count -= 1;
      if (count > 0) {
        setCountdownNum(count);
      } else {
        clearInterval(cdInterval);
        beginRecording();
      }
    }, 1000);
  };

  const beginRecording = async () => {
    setRecordState('recording');
    setElapsedSec(0);

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        {
          android: {
            extension: '.m4a',
            outputFormat: Audio.AndroidOutputFormat.MPEG_4,
            audioEncoder: Audio.AndroidAudioEncoder.AAC,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          ios: {
            extension: '.m4a',
            outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
            audioQuality: Audio.IOSAudioQuality.MAX,
            sampleRate: 44100,
            numberOfChannels: 1,
            bitRate: 128000,
          },
          web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
          isMeteringEnabled: true,
        },
      );

      recordingRef.current = recording;

      // 미터링 콜백
      recording.setOnRecordingStatusUpdate((status) => {
        if (status.isRecording && status.metering !== undefined) {
          const normalized = Math.max(0, (status.metering + 60) / 60);
          setMeterLevel(Math.min(1, normalized));
        }
      });

      // 경과 시간 타이머
      let sec = 0;
      timerRef.current = setInterval(() => {
        sec += 1;
        setElapsedSec(sec);
      }, 1000);

      // 5초 후 자동 중지
      setTimeout(async () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        try {
          if (!recordingRef.current) return;
          await recordingRef.current.stopAndUnloadAsync();
          const uri = recordingRef.current.getURI();
          recordingRef.current = null;
          setMeterLevel(0);

          if (!uri) {
            setErrorMessage('녹음 파일을 생성할 수 없습니다.');
            setRecordState('error');
            return;
          }

          setRecordState('analyzing');

          const result = await detectPitch(uri);
          if ('error' in result) {
            setErrorMessage(String(result.error));
            setRecordState('error');
          } else if (result.detected_note === null) {
            setErrorMessage('음을 감지하지 못했어요.\n더 크고 안정적인 소리로 다시 시도해주세요.');
            setRecordState('error');
          } else {
            setPitchResult(result);
            setDetectedNote(result.detected_note);
            setRecordState('success');
          }
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : '음높이 감지에 실패했습니다.';
          setErrorMessage(msg);
          setRecordState('error');
        }
      }, RECORD_DURATION_SEC * 1000);
    } catch {
      setRecordState('error');
      setErrorMessage('녹음을 시작할 수 없습니다.');
    }
  };

  const handleConfirmNote = () => {
    if (!detectedNote) return;
    if (step === 'low') {
      setSelectedLow(detectedNote);
      setRecordState('idle');
      setDetectedNote(null);
      setPitchResult(null);
      setStep('high');
    } else if (step === 'high') {
      setSelectedHigh(detectedNote);
      setRecordState('idle');
      setDetectedNote(null);
      setPitchResult(null);
      setStep('result');
    }
  };

  const handleRetry = () => {
    setRecordState('idle');
    setDetectedNote(null);
    setPitchResult(null);
    setErrorMessage('');
    setMeterLevel(0);
    setElapsedSec(0);
  };

  const handleUseCurrent = () => {
    if (!selectedLow || !selectedHigh) return;
    setVocalRange({ low: selectedLow, high: selectedHigh });
    setVoiceType(voiceTypeLabel);
    setExpansionGoal(null);
    completeTest();
    navigateHome();
  };

  const handleExpansionChoice = () => {
    if (!selectedLow || !selectedHigh || !selectedExpansion) return;
    const target = getExpansionTarget(selectedLow, selectedHigh, selectedExpansion);
    setVocalRange({ low: selectedLow, high: selectedHigh });
    setVoiceType(voiceTypeLabel);
    setExpansionGoal({
      direction: selectedExpansion,
      targetLow: target.targetLow,
      targetHigh: target.targetHigh,
    });
    completeTest();
    navigateHome();
  };

  // ─── all_notes 피치 추이 그래프 ───
  const renderPitchChart = () => {
    if (!pitchResult?.all_notes || pitchResult.all_notes.length === 0) return null;
    const allNotes = pitchResult.all_notes;

    // 고유 음 정렬 (낮→높)
    const uniqueNotes = [...new Set(allNotes)].sort(
      (a, b) => noteToIndex(a) - noteToIndex(b),
    );
    const screenWidth = Dimensions.get('window').width;
    const yAxisWidth = 40;
    const graphWidth = screenWidth - 80 - yAxisWidth;
    const graphHeight = 200;
    const stepX =
      allNotes.length > 1 ? graphWidth / (allNotes.length - 1) : graphWidth;
    const stepY =
      uniqueNotes.length > 1 ? graphHeight / (uniqueNotes.length - 1) : graphHeight;

    const resultNoteIdx = pitchResult.detected_note
      ? uniqueNotes.indexOf(pitchResult.detected_note)
      : -1;

    return (
      <View style={styles.chartContainer}>
        <Text style={styles.chartTitle}>당신의 발성 추이</Text>
        <View style={styles.chartWrapper}>
          {/* Y축 라벨 */}
          <View style={[styles.chartYAxis, { height: graphHeight }]}>
            {[...uniqueNotes].reverse().map((note, i) => (
              <Text key={`y-${i}`} style={styles.chartYLabel}>
                {note}
              </Text>
            ))}
          </View>
          {/* 그래프 영역 */}
          <View style={[styles.chartArea, { width: graphWidth, height: graphHeight }]}>
            {/* 격자 가로선 */}
            {uniqueNotes.map((_, i) => (
              <View
                key={`grid-${i}`}
                style={[styles.chartGridLine, { bottom: i * stepY }]}
              />
            ))}
            {/* 기준선 (감지된 음 — 빨간 선) */}
            {resultNoteIdx >= 0 && (
              <View
                style={[styles.chartRefLine, { bottom: resultNoteIdx * stepY - 1 }]}
              />
            )}
            {/* 데이터 점 */}
            {allNotes.map((note, i) => {
              const noteIdx = uniqueNotes.indexOf(note);
              return (
                <View
                  key={`dot-${i}`}
                  style={[
                    styles.chartDot,
                    { left: i * stepX - 2, bottom: noteIdx * stepY - 2 },
                  ]}
                />
              );
            })}
          </View>
        </View>
        <Text style={styles.chartDesc}>
          파란 점은 순간 감지된 음 높이, 빨간 선은 최종 판정 음
        </Text>
      </View>
    );
  };

  // ─── 음역대 시각화 바 ───
  const renderRangeBar = (lowNote: string, highNote: string) => {
    const lowIdx = noteToIndex(lowNote);
    const highIdx = noteToIndex(highNote);
    const leftPct = ((lowIdx - FULL_LOW) / FULL_RANGE) * 100;
    const widthPct = ((highIdx - lowIdx) / FULL_RANGE) * 100;

    return (
      <View style={styles.rangeBarContainer}>
        <View style={styles.rangeBarTrack}>
          <View
            style={[
              styles.rangeBarFill,
              { left: `${Math.max(0, leftPct)}%`, width: `${Math.min(100, widthPct)}%` },
            ]}
          />
        </View>
        <View style={styles.rangeBarLabels}>
          <Text style={styles.rangeBarLabel}>C2</Text>
          <Text style={styles.rangeBarLabel}>C4</Text>
          <Text style={styles.rangeBarLabel}>C6</Text>
        </View>
      </View>
    );
  };

  // ───────────────────────────────────────
  // 2단계/3단계 측정 UI
  // ───────────────────────────────────────
  const renderMeasurementUI = (config: {
    title: string;
    description: string;
    tip: string;
    stepLabel: string;
    stepEmoji: string;
  }) => (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => {
            if (timerRef.current) {
              clearInterval(timerRef.current);
              timerRef.current = null;
            }
            if (recordingRef.current) {
              recordingRef.current.stopAndUnloadAsync().catch(() => {});
              recordingRef.current = null;
            }
            setRecordState('idle');
            setDetectedNote(null);
            setPitchResult(null);
            setErrorMessage('');
            setMeterLevel(0);
            setStep(step === 'low' ? 'intro' : 'low');
          }}
        >
          <Text style={styles.backText}>← 이전</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleSkip}>
          <Text style={styles.skipText}>건너뛰기</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.measureScrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.stepLabel}>{config.stepLabel}</Text>
        <Text style={styles.stepEmoji}>{config.stepEmoji}</Text>

        {/* ─── idle: 대기 ─── */}
        {recordState === 'idle' && (
          <>
            <Text style={styles.measureTitle}>{config.title}</Text>
            <Text style={styles.measureInstruction}>{config.description}</Text>
            <Text style={styles.measureTip}>{config.tip}</Text>
            <TouchableOpacity style={styles.micButton} onPress={startMeasurement}>
              <Text style={styles.micButtonEmoji}>🎤</Text>
            </TouchableOpacity>
            <Text style={styles.micHint}>탭하여 측정 시작</Text>
          </>
        )}

        {/* ─── countdown: 카운트다운 ─── */}
        {recordState === 'countdown' && (
          <>
            <Text style={styles.countdownLabel}>준비하세요!</Text>
            <Text style={styles.countdownNum}>{countdownNum}</Text>
            <Text style={styles.countdownHint}>곧 녹음이 시작됩니다</Text>
          </>
        )}

        {/* ─── recording: 녹음 중 + 볼륨 바 ─── */}
        {recordState === 'recording' && (
          <>
            <Text style={styles.measureTitle}>{config.title}를 내주세요</Text>

            {/* 볼륨 바 영역 */}
            <View style={styles.volumeBarSection}>
              <View style={styles.volumeBarLabels}>
                <Text style={styles.volumeBarLabelText}>큼</Text>
                <Text style={styles.volumeBarLabelText}>작음</Text>
              </View>
              <View style={styles.volumeBarTrack}>
                <View
                  style={[
                    styles.volumeBarFill,
                    {
                      height: meterLevel * 200,
                      backgroundColor:
                        meterLevel < 0.4
                          ? COLORS.success
                          : meterLevel < 0.7
                            ? COLORS.warning
                            : COLORS.danger,
                    },
                  ]}
                />
              </View>
              <Text style={styles.volumeBarHint}>
                {meterLevel < 0.15
                  ? '🔇 소리가 안 들려요'
                  : meterLevel < 0.7
                    ? '👍 좋아요!'
                    : '📢 조금 작게 해도 돼요'}
              </Text>
            </View>

            {/* 마이크 + 타이머 */}
            <View style={[styles.micButton, styles.micButtonRecording]}>
              <Text style={styles.micButtonEmoji}>🎤</Text>
            </View>
            <Text style={styles.recordingTimer}>
              녹음 중... {elapsedSec}/{RECORD_DURATION_SEC}초
            </Text>
          </>
        )}

        {/* ─── analyzing: 분석 중 ─── */}
        {recordState === 'analyzing' && (
          <>
            <ActivityIndicator size="large" color={COLORS.primary} style={{ marginVertical: 30 }} />
            <Text style={styles.analyzingText}>분석 중...</Text>
          </>
        )}

        {/* ─── success: 결과 ─── */}
        {recordState === 'success' && detectedNote && (
          <>
            <Text style={styles.detectedNote}>감지된 음: {detectedNote}</Text>
            {pitchResult && (
              <Text style={styles.detectedFreq}>
                {Math.round(pitchResult.frequency_hz)} Hz
              </Text>
            )}

            {/* confidence 메시지 */}
            {pitchResult && (
              <Text style={styles.confidenceText}>
                {getConfidenceMessage(pitchResult.confidence)}
              </Text>
            )}

            {/* all_notes 피치 추이 그래프 */}
            {renderPitchChart()}

            {/* pitch range */}
            {pitchResult?.pitch_range && (
              <Text style={styles.pitchRangeText}>
                발성 범위: {Math.round(pitchResult.pitch_range.low_hz)}Hz ~{' '}
                {Math.round(pitchResult.pitch_range.high_hz)}Hz
              </Text>
            )}

            <View style={styles.confirmRow}>
              <TouchableOpacity style={styles.confirmBtn} onPress={handleConfirmNote}>
                <Text style={styles.confirmBtnText}>✅ 이 음이 맞아요</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.retryBtn} onPress={handleRetry}>
                <Text style={styles.retryBtnText}>🔄 다시 측정</Text>
              </TouchableOpacity>
            </View>
          </>
        )}

        {/* ─── error ─── */}
        {recordState === 'error' && (
          <>
            <Text style={styles.errorText}>{errorMessage || '측정에 실패했습니다'}</Text>
            <TouchableOpacity style={styles.retryBtn} onPress={handleRetry}>
              <Text style={styles.retryBtnText}>🔄 다시 측정</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );

  // ══════════════════════════════════════
  // 1단계: 안내
  // ══════════════════════════════════════
  if (step === 'intro') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <View />
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.centerContent}>
          <Text style={styles.introEmoji}>🎵</Text>
          <Text style={styles.introTitle}>목소리로 음역대를{'\n'}측정해볼게요</Text>
          <Text style={styles.introDesc}>
            조용한 곳에서 진행해주세요.{'\n'}
            가장 낮은 음과 높은 음을 차례로 측정합니다.{'\n'}
            각 측정 전 3초 카운트다운이 있어요.
          </Text>
        </View>

        <TouchableOpacity style={[styles.primaryButton, { marginBottom: 48 }]} onPress={() => setStep('low')}>
          <Text style={styles.primaryButtonText}>시작하기</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // ══════════════════════════════════════
  // 2단계: 최저음 측정
  // ══════════════════════════════════════
  if (step === 'low') {
    return renderMeasurementUI({
      title: '가장 낮은 목소리',
      description:
        "목소리를 최대한 낮춰서 '아~' 하고 길게 내주세요\n편안하게 낼 수 있는 가장 낮은 소리면 돼요\n억지로 쥐어짤 필요 없어요!",
      tip: '💡 팁: 하품할 때처럼 목을 편하게 열고 소리를 내보세요',
      stepLabel: '1/2 단계 — 최저음',
      stepEmoji: '🔽',
    });
  }

  // ══════════════════════════════════════
  // 3단계: 최고음 측정
  // ══════════════════════════════════════
  if (step === 'high') {
    return renderMeasurementUI({
      title: '가장 높은 목소리',
      description:
        "이번에는 최대한 높은 소리로 '아~' 하고 길게 내주세요\n가성(얇은 소리)도 괜찮아요!\n무리하지 마세요",
      tip: '💡 팁: 사이렌 소리를 흉내내듯 올려보세요',
      stepLabel: '2/2 단계 — 최고음',
      stepEmoji: '🔼',
    });
  }

  // ══════════════════════════════════════
  // 4단계: 결과 + 유명 가수
  // ══════════════════════════════════════
  if (step === 'result') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity
            onPress={() => {
              setSelectedHigh(null);
              setRecordState('idle');
              setDetectedNote(null);
              setPitchResult(null);
              setStep('high');
            }}
          >
            <Text style={styles.backText}>← 이전</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollInner}>
          <Text style={styles.resultTitleBig}>당신의 음역대</Text>
          <Text style={styles.resultRange}>{rangeLabel}</Text>
          <View style={styles.voiceTypeBadge}>
            <Text style={styles.voiceTypeText}>{voiceTypeLabel}</Text>
          </View>

          {selectedLow && selectedHigh && renderRangeBar(selectedLow, selectedHigh)}

          <Text style={styles.singerSectionTitle}>🎤 나와 비슷한 가수들</Text>

          {singersLoading && (
            <ActivityIndicator size="small" color={COLORS.primary} style={{ marginVertical: 16 }} />
          )}

          {!singersLoading && singers.length === 0 && (
            <View style={styles.noSingersCard}>
              <Text style={styles.noSingersText}>
                비슷한 음역대의 가수 정보를 준비 중입니다
              </Text>
            </View>
          )}

          {!singersLoading && singers.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.singerScroll}
              contentContainerStyle={styles.singerScrollInner}
            >
              {singers.map((singer) => (
                <View key={singer.name} style={styles.singerCard}>
                  <Text style={styles.singerName}>{singer.name}</Text>
                  <Text style={styles.singerType}>
                    {singer.voice_type} • {singer.range_low} ~ {singer.range_high}
                  </Text>
                  {singer.famous_songs.length > 0 && (
                    <View style={styles.singerSongs}>
                      {singer.famous_songs.slice(0, 3).map((song) => (
                        <Text key={song} style={styles.singerSong}>
                          ♪ {song}
                        </Text>
                      ))}
                    </View>
                  )}
                  <TouchableOpacity
                    style={styles.youtubeBtn}
                    onPress={() => {
                      const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(singer.youtube_query)}`;
                      Linking.openURL(url);
                    }}
                  >
                    <Text style={styles.youtubeBtnText}>🎵 노래 찾아보기</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </ScrollView>
          )}

          <Text style={styles.motivationText}>
            같은 음역대의 가수들이 이미 훌륭한 활동을 하고 있어요.{'\n'}
            음역을 확장하면 더 다양한 곡에 도전할 수 있습니다!
          </Text>
        </ScrollView>

        <View style={styles.resultActions}>
          <TouchableOpacity style={styles.primaryButton} onPress={handleUseCurrent}>
            <Text style={styles.primaryButtonText}>현재 음역대로 시작하기</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => setStep('expansion')}
          >
            <Text style={styles.secondaryButtonText}>음역 확장 목표 설정하기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ══════════════════════════════════════
  // 5단계: 확장 방향 선택
  // ══════════════════════════════════════
  if (step === 'expansion') {
    const lowStr = selectedLow ?? 'C3';
    const highStr = selectedHigh ?? 'C5';

    const highTarget = getExpansionTarget(lowStr, highStr, 'high');
    const lowTarget = getExpansionTarget(lowStr, highStr, 'low');
    const bothTarget = getExpansionTarget(lowStr, highStr, 'both');

    const getSingerHint = (dir: string): string => {
      const list = expansionSingers[dir] ?? [];
      if (list.length === 0) return '';
      if (list.length === 1) return `${list[0].name} 등이 이 음역대에 해당해요`;
      return `${list[0].name}, ${list[1].name} 등이 이 음역대에 해당해요`;
    };

    const cards: {
      dir: 'high' | 'low' | 'both';
      emoji: string;
      label: string;
      desc: string;
      targetRange: string;
    }[] = [
      {
        dir: 'high',
        emoji: '🔼',
        label: '고음 확장',
        desc: '더 높은 음역을 개발합니다',
        targetRange: `${lowStr} ~ ${highTarget.targetHigh}`,
      },
      {
        dir: 'low',
        emoji: '🔽',
        label: '저음 확장',
        desc: '더 깊고 풍부한 저음을 만듭니다',
        targetRange: `${lowTarget.targetLow} ~ ${highStr}`,
      },
      {
        dir: 'both',
        emoji: '↕️',
        label: '양쪽 확장',
        desc: '전체 음역을 넓힙니다',
        targetRange: `${bothTarget.targetLow} ~ ${bothTarget.targetHigh}`,
      },
    ];

    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => setStep('result')}>
            <Text style={styles.backText}>← 이전</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleSkip}>
            <Text style={styles.skipText}>건너뛰기</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.expansionInner}>
          <Text style={styles.expansionTitle}>어떤 방향으로 확장할까요?</Text>

          {cards.map((card) => {
            const isSelected = selectedExpansion === card.dir;
            const singerHint = getSingerHint(card.dir);
            return (
              <TouchableOpacity
                key={card.dir}
                style={[styles.expansionCard, isSelected && styles.expansionCardSelected]}
                onPress={() => setSelectedExpansion(card.dir)}
              >
                <Text style={styles.expansionEmoji}>{card.emoji}</Text>
                <Text style={styles.expansionLabel}>{card.label}</Text>
                <Text style={styles.expansionDesc}>{card.desc}</Text>
                <Text style={styles.expansionTarget}>목표: {card.targetRange}</Text>
                {singerHint.length > 0 && (
                  <Text style={styles.expansionSingerHint}>{singerHint}</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        <View style={styles.resultActions}>
          <TouchableOpacity
            style={[styles.primaryButton, !selectedExpansion && styles.disabledButton]}
            onPress={handleExpansionChoice}
            disabled={!selectedExpansion}
          >
            <Text style={styles.primaryButtonText}>이 목표로 시작하기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return null;
}

// ═══════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
    paddingHorizontal: 20,
  },

  // ─── 상단 바 ───
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
    paddingTop: 12,
    paddingBottom: 8,
  },
  backText: { fontSize: 15, color: COLORS.primaryLight, fontWeight: '600' },
  skipText: { fontSize: 15, color: COLORS.textMuted },

  // ─── 1단계: 안내 ───
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  introEmoji: { fontSize: 64, marginBottom: 24 },
  introTitle: {
    fontSize: 26,
    fontWeight: '800',
    color: COLORS.textPrimary,
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 36,
  },
  introDesc: {
    fontSize: 15,
    color: COLORS.textMuted,
    textAlign: 'center',
    lineHeight: 24,
  },

  // ─── 2/3단계: 측정 ───
  measureScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 20,
  },
  stepLabel: { fontSize: 13, color: COLORS.textSecondary, marginBottom: 8 },
  stepEmoji: { fontSize: 36, marginBottom: 16 },
  measureTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
    textAlign: 'center',
  },
  measureInstruction: {
    fontSize: 15,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 16,
    paddingHorizontal: 10,
  },
  measureTip: {
    fontSize: 13,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginBottom: 28,
  },

  micButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: COLORS.card,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
    zIndex: 2,
  },
  micButtonRecording: {
    backgroundColor: COLORS.danger + '33',
  },
  micButtonEmoji: { fontSize: 48 },
  micHint: { fontSize: 13, color: COLORS.textMuted },

  // ─── 카운트다운 ───
  countdownLabel: {
    fontSize: 18,
    color: COLORS.textSecondary,
    marginBottom: 16,
  },
  countdownNum: {
    fontSize: 80,
    fontWeight: '800',
    color: COLORS.primary,
    marginBottom: 16,
  },
  countdownHint: {
    fontSize: 14,
    color: COLORS.textMuted,
  },

  // ─── 볼륨 바 ───
  volumeBarSection: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    marginVertical: 20,
    gap: 12,
  },
  volumeBarLabels: {
    height: 200,
    justifyContent: 'space-between' as const,
    alignItems: 'flex-end' as const,
  },
  volumeBarLabelText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  volumeBarTrack: {
    height: 200,
    width: 40,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
    overflow: 'hidden' as const,
    justifyContent: 'flex-end' as const,
  },
  volumeBarFill: {
    width: 40,
    borderRadius: 8,
  },
  volumeBarHint: {
    fontSize: 14,
    color: COLORS.textSecondary,
    width: 120,
    textAlign: 'center' as const,
  },
  recordingTimer: {
    fontSize: 15,
    color: COLORS.primary,
    fontWeight: '600' as const,
  },

  // ─── 분석 중 ───
  analyzingText: { fontSize: 16, color: COLORS.primary, fontWeight: '600' },

  // ─── 결과 (성공) ───
  detectedNote: {
    fontSize: 36,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 4,
    marginTop: 12,
  },
  detectedFreq: {
    fontSize: 15,
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  pitchRangeText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  confidenceText: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '600',
    marginBottom: 16,
  },
  confirmQuestion: { fontSize: 16, color: COLORS.textSecondary, marginBottom: 20, marginTop: 12 },
  confirmRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  confirmBtn: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
  },
  confirmBtnText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  retryBtn: {
    backgroundColor: COLORS.card,
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  retryBtnText: { color: COLORS.textSecondary, fontSize: 16, fontWeight: '600' },

  errorText: {
    fontSize: 15,
    color: COLORS.danger,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 22,
  },

  // ─── 피치 추이 그래프 ───
  chartContainer: {
    width: '100%',
    alignItems: 'center',
    marginVertical: 16,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: 12,
  },
  chartWrapper: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
  },
  chartYAxis: {
    width: 40,
    justifyContent: 'space-between' as const,
    alignItems: 'flex-end' as const,
    paddingRight: 6,
  },
  chartYLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
  chartArea: {
    backgroundColor: COLORS.card,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    position: 'relative' as const,
    overflow: 'hidden' as const,
  },
  chartGridLine: {
    position: 'absolute' as const,
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.divider,
  },
  chartRefLine: {
    position: 'absolute' as const,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: COLORS.danger,
    opacity: 0.6,
  },
  chartDot: {
    position: 'absolute' as const,
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: COLORS.primary,
  },
  chartDesc: {
    fontSize: 12,
    color: COLORS.textMuted,
    textAlign: 'center' as const,
    marginTop: 8,
    lineHeight: 18,
  },

  // ─── 4단계: 결과 ───
  scrollContent: { flex: 1 },
  scrollInner: {
    paddingTop: 20,
    paddingBottom: 20,
    alignItems: 'center',
  },

  resultTitleBig: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  resultRange: {
    fontSize: 36,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  voiceTypeBadge: {
    backgroundColor: COLORS.primary + '1A',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    marginBottom: 24,
  },
  voiceTypeText: { fontSize: 15, fontWeight: '600', color: COLORS.primaryLight },

  // 음역대 바
  rangeBarContainer: { width: '100%', marginBottom: 28 },
  rangeBarTrack: {
    height: 12,
    backgroundColor: COLORS.surface,
    borderRadius: 6,
    overflow: 'hidden',
  },
  rangeBarFill: {
    position: 'absolute',
    top: 0,
    height: 12,
    backgroundColor: COLORS.primary,
    borderRadius: 6,
  },
  rangeBarLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  rangeBarLabel: { fontSize: 11, color: COLORS.textMuted },

  // 가수 섹션
  singerSectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.textPrimary,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  singerScroll: { maxHeight: 250, marginBottom: 16 },
  singerScrollInner: { gap: 12, paddingRight: 8 },
  singerCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    width: 200,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  singerName: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  singerType: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 8 },
  singerSongs: { marginBottom: 10 },
  singerSong: { fontSize: 13, color: COLORS.textSecondary, lineHeight: 20 },
  youtubeBtn: {
    backgroundColor: COLORS.danger + '1A',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  youtubeBtnText: { fontSize: 13, color: COLORS.danger, fontWeight: '600' },

  noSingersCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
    width: '100%',
  },
  noSingersText: { fontSize: 14, color: COLORS.textMuted, textAlign: 'center' },

  motivationText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginTop: 8,
    marginBottom: 8,
  },

  resultActions: {
    gap: 10,
    paddingBottom: 20,
  },

  // ─── 5단계: 확장 ───
  expansionInner: {
    paddingTop: 20,
    paddingBottom: 20,
    gap: 14,
  },
  expansionTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  expansionCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
    borderWidth: 2,
    borderColor: COLORS.cardBorder,
  },
  expansionCardSelected: {
    borderColor: COLORS.primary,
    backgroundColor: COLORS.primary + '0D',
  },
  expansionEmoji: { fontSize: 32, marginBottom: 8 },
  expansionLabel: { fontSize: 17, fontWeight: '700', color: COLORS.textPrimary, marginBottom: 4 },
  expansionDesc: { fontSize: 13, color: COLORS.textMuted, marginBottom: 6 },
  expansionTarget: { fontSize: 14, color: COLORS.primary, fontWeight: '600', marginBottom: 4 },
  expansionSingerHint: { fontSize: 12, color: COLORS.textSecondary, textAlign: 'center', marginTop: 4 },

  // ─── 공통 버튼 ───
  primaryButton: {
    backgroundColor: COLORS.primary,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  disabledButton: { backgroundColor: COLORS.surface },
  secondaryButton: {
    backgroundColor: COLORS.card,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  secondaryButtonText: { color: COLORS.textSecondary, fontSize: 16, fontWeight: '600' },
});
