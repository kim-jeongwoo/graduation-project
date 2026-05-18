import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  useWindowDimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import Pitchy from 'react-native-pitchy';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { AnalyzeStatusError, getSessionDetail, startAnalysis } from '../../api/sessions';
import { AnalysisPollingTimeoutError, pollAnalysisStatus } from '../../api/analysis';
import { isAuthExpiredError } from '../../api/client';
import { getSongLrc, getSongMrUrl, getSongPitchGuideCompat } from '../../api/songs';

// [deprecated] 구형 화면 aliases — P1에서 정리 예정
const requestAnalysis = async (sid: string) => {
  const response = await startAnalysis(sid);
  await pollAnalysisStatus(response.run_id);
  return { run_id: response.run_id, status: response.status };
};
const getSongLyrics = getSongLrc;
const getSongAudioUrl = getSongMrUrl;
const getSongPitch = (songId: string) => getSongPitchGuideCompat(songId).catch(() => null);
import { mockSessions } from '../../mock/mockData';
import StatusBadge from '../../components/StatusBadge';
import PitchVisualizer, { USER_HISTORY_MAX } from '../../components/PitchVisualizer';
import type { UserPitchPoint } from '../../components/PitchVisualizer';
import { formatDate, formatDuration, getStatusLabel } from '../../utils/labels';
import { COLORS } from '../../utils/colors';
import type { SessionDetail, LyricsLine } from '../../types/api';

type Props = NativeStackScreenProps<Record<string, object | undefined>, string>;

export default function SessionDetailScreen({ route, navigation }: Props) {
  const { width: screenWidth } = useWindowDimensions();
  const { sessionId, songId } = (route.params ?? {}) as {
    sessionId: string;
    songId?: string;
  };
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const analysisTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 녹음 상태
  const recordingRef = useRef<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [recordingDurationMs, setRecordingDurationMs] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [volumeLevel, setVolumeLevel] = useState(0);

  // 재생 상태 (미리 듣기)
  const soundRef = useRef<Audio.Sound | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // 원곡 재생 (녹음 중 배경 재생)
  const bgSoundRef = useRef<Audio.Sound | null>(null);

  // 실시간 피치 감지
  const pitchSubRef = useRef<ReturnType<typeof Pitchy.addListener> | null>(null);
  const [currentPitch, setCurrentPitch] = useState(0);

  // 피치 시각화 데이터
  const [referencePitchFrames, setReferencePitchFrames] = useState<import('../../types/api').PitchFrame[]>([]);
  const [referencePitchResolution, setReferencePitchResolution] = useState(50);
  const userPitchHistoryRef = useRef<UserPitchPoint[]>([]);
  const [userPitchHistory, setUserPitchHistory] = useState<UserPitchPoint[]>([]);
  const lastPitchFlushRef = useRef(0);

  // 키 시프트 (-4 ~ +4 반음)
  const [keyShift, setKeyShift] = useState(0);

  // 가사
  const [lyrics, setLyrics] = useState<LyricsLine[]>([]);
  const [currentLineIdx, setCurrentLineIdx] = useState(-1);
  const startTimeRef = useRef<number>(0);

  // 가사 로드 (songId 파라미터 또는 detail.song_id 사용)
  useEffect(() => {
    const sid = songId ?? detail?.song_id;
    if (!sid) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getSongLyrics(sid);
        if (!cancelled) {
          setLyrics(data.lines);
        }
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, [songId, detail?.song_id]);

  // 원곡 피치 데이터 로드
  useEffect(() => {
    const sid = songId ?? detail?.song_id;
    if (!sid) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getSongPitch(sid);
        if (!cancelled && data) {
          setReferencePitchFrames(data.frames);
          setReferencePitchResolution(data.resolution_ms);
        }
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [songId, detail?.song_id]);

  const loadDetail = useCallback(async () => {
    try {
      const data = await getSessionDetail(sessionId);
      setDetail(data);
    } catch {} finally {
      setLoading(false);
    }
  }, [sessionId]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      loadDetail();
    }, [loadDetail]),
  );

  // 타이머 & 녹음 & 사운드 정리
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync().catch(() => {});
        recordingRef.current = null;
      }
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
        soundRef.current = null;
      }
      if (bgSoundRef.current) {
        bgSoundRef.current.unloadAsync().catch(() => {});
        bgSoundRef.current = null;
      }
      // 피치 감지 정리
      Pitchy.stop().catch(() => {});
      if (pitchSubRef.current) {
        pitchSubRef.current.remove();
        pitchSubRef.current = null;
      }
    };
  }, []);

  // 가사 싱크: elapsedMs가 바뀔 때마다 현재 라인 계산
  useEffect(() => {
    if (lyrics.length === 0 || !isRecording) return;
    const idx = lyrics.findIndex((l) => l.time_ms > elapsedMs) - 1;
    const newIdx = idx >= 0 ? idx : lyrics.length - 1;
    setCurrentLineIdx(newIdx);
  }, [elapsedMs, lyrics, isRecording, currentLineIdx]);

  const startRecording = async () => {
    const activeSongId = effectiveSongId;
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('권한 필요', '녹음을 위해 마이크 권한이 필요합니다.');
        return;
      }

      // 1) 오디오 모드: 녹음 + 재생 동시 허용
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        playThroughEarpieceAndroid: false,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
      });

      // 2) 원곡 오디오 미리 로드 (재생은 녹음 시작 후)
      let preloadedSound: Audio.Sound | null = null;
      if (activeSongId) {
        try {
          const audioUrl = getSongAudioUrl(activeSongId);
          const { sound } = await Audio.Sound.createAsync(
            {
              uri: audioUrl,
              overrideFileExtensionAndroid: '.mp3',
            },
            { shouldPlay: false, volume: 0.7 },
          );
          preloadedSound = sound;
        } catch {}
      }

      // 3) 녹음 시작
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
      setIsRecording(true);
      setRecordingUri(null);
      setRecordingDurationMs(0);
      setElapsedSec(0);
      setElapsedMs(0);
      setCurrentLineIdx(-1);
      startTimeRef.current = Date.now();

      // 4) 녹음 시작 직후 원곡 재생 (이미 버퍼링 완료)
      if (preloadedSound) {
        try {
          await preloadedSound.playAsync();
          bgSoundRef.current = preloadedSound;
          // 원곡 재생 완료 시 녹음 자동 중지
          preloadedSound.setOnPlaybackStatusUpdate((status) => {
            if (status.isLoaded && status.didJustFinish && recordingRef.current) {
              stopRecording();
            }
          });
        } catch {
          preloadedSound.unloadAsync().catch(() => {});
          Alert.alert('알림', '원곡 재생에 실패했습니다. 녹음은 계속됩니다.');
        }
      } else if (activeSongId) {
        Alert.alert('알림', '원곡을 불러올 수 없습니다. 녹음은 계속됩니다.');
      }

      // 5) 실시간 피치 감지 시작
      try {
        await Pitchy.init({ bufferSize: 4096, minVolume: -40 });
        pitchSubRef.current = Pitchy.addListener(({ pitch }) => {
          if (pitch > 0) {
            setCurrentPitch(pitch);
            // 피치 히스토리 축적 (ref에 저장, 80ms 간격으로 state 반영)
            const now = Date.now() - startTimeRef.current;
            const entry: UserPitchPoint = { timeMs: now, freq: pitch };
            const hist = userPitchHistoryRef.current;
            hist.push(entry);
            if (hist.length > USER_HISTORY_MAX) hist.splice(0, hist.length - USER_HISTORY_MAX);
            // throttle: 80ms마다 state 반영
            if (now - lastPitchFlushRef.current > 80) {
              lastPitchFlushRef.current = now;
              setUserPitchHistory([...hist]);
            }
          }
        });
        await Pitchy.start();
      } catch {
        // 피치 감지 실패해도 녹음은 계속
      }

      // 타이머: 200ms 간격으로 경과 시간 + 볼륨
      timerRef.current = setInterval(async () => {
        const now = Date.now();
        const ms = now - startTimeRef.current;
        setElapsedMs(ms);
        setElapsedSec(Math.floor(ms / 1000));

        // 볼륨 미터링
        if (recordingRef.current) {
          try {
            const status = await recordingRef.current.getStatusAsync();
            if (status.isRecording && status.metering !== undefined) {
              // metering: -160 ~ 0 dB → 0 ~ 1 linear
              const db = status.metering;
              const normalized = Math.max(0, Math.min(1, (db + 60) / 60));
              setVolumeLevel(normalized);
            }
          } catch {
            // ignore
          }
        }
      }, 200);
    } catch {
      Alert.alert('녹음 실패', '녹음을 시작할 수 없습니다.');
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    try {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      // 피치 감지 중지
      try {
        await Pitchy.stop();
      } catch {}
      if (pitchSubRef.current) {
        pitchSubRef.current.remove();
        pitchSubRef.current = null;
      }
      setCurrentPitch(0);
      userPitchHistoryRef.current = [];
      setUserPitchHistory([]);

      // 원곡 재생 중지
      if (bgSoundRef.current) {
        await bgSoundRef.current.stopAsync().catch(() => {});
        await bgSoundRef.current.unloadAsync().catch(() => {});
        bgSoundRef.current = null;
      }

      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      const status = await recordingRef.current.getStatusAsync();
      const durationMs = status.durationMillis ?? elapsedSec * 1000;
      recordingRef.current = null;
      setIsRecording(false);
      setRecordingUri(uri);
      setRecordingDurationMs(durationMs);
      setVolumeLevel(0);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
    } catch {
      setIsRecording(false);
    }
  };

  const handleReRecord = () => {
    if (soundRef.current) {
      soundRef.current.unloadAsync().catch(() => {});
      soundRef.current = null;
      setIsPlaying(false);
    }
    setRecordingUri(null);
    setRecordingDurationMs(0);
    setElapsedSec(0);
    setElapsedMs(0);
    setVolumeLevel(0);
    setCurrentLineIdx(-1);
  };

  const handlePlayback = async () => {
    if (!recordingUri) return;
    try {
      if (isPlaying && soundRef.current) {
        await soundRef.current.stopAsync();
        await soundRef.current.unloadAsync();
        soundRef.current = null;
        setIsPlaying(false);
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const { sound } = await Audio.Sound.createAsync(
        { uri: recordingUri },
        { shouldPlay: true },
        (status) => {
          if (status.isLoaded && status.didJustFinish) {
            setIsPlaying(false);
            sound.unloadAsync().catch(() => {});
            soundRef.current = null;
          }
        },
      );
      soundRef.current = sound;
      setIsPlaying(true);
    } catch {
      Alert.alert('재생 실패', '녹음 파일을 재생할 수 없습니다.');
    }
  };

  const formatTimer = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // 볼륨 바 색상 결정
  const getVolumeColor = (level: number): string => {
    if (level > 0.8) return COLORS.danger;
    if (level > 0.5) return COLORS.warning;
    return COLORS.success;
  };

  // Hook은 early return 이전에 호출해야 함 (Rules of Hooks)
  const hasSongId = !!songId || !!detail?.song_id;
  const effectiveSongId = songId ?? detail?.song_id;

  // 분석 단계 정의
  const analysisSteps = useMemo(() => {
    const steps = [
      { emoji: '📤', label: '음성 파일 분석 준비' },
      { emoji: '🧠', label: 'EGG 신호 추정 중' },
      { emoji: '📊', label: '발성 패턴 분석 중' },
    ];
    if (hasSongId) {
      steps.push({ emoji: '🎵', label: '음정 비교 분석 중' });
    }
    steps.push({ emoji: '💬', label: '피드백 생성 중' });
    return steps;
  }, [hasSongId]);

  if (loading || !detail) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  const files = detail.files;
  const hasFiles = files.length > 0;
  const isCompleted = detail.status === 'completed';
  const isAnalyzingStatus = detail.status === 'analyzing';
  const hasAnalysis = detail.analysis !== null;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisStep(0);

    // 단계별 진행 (0.8초 간격)
    let step = 0;
    analysisTimerRef.current = setInterval(() => {
      step = Math.min(step + 1, analysisSteps.length - 1);
      setAnalysisStep(step);
    }, 800);

    try {
      const resp = await requestAnalysis(sessionId);

      // 모든 단계가 완료될 때까지 대기
      const totalSteps = analysisSteps.length;
      const elapsed = step;
      const remaining = totalSteps - 1 - elapsed;
      if (remaining > 0) {
        await new Promise((resolve) => setTimeout(resolve, remaining * 800));
      }

      // 마지막 단계 표시 후 1초 대기
      if (analysisTimerRef.current) {
        clearInterval(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
      setAnalysisStep(totalSteps);
      await new Promise((resolve) => setTimeout(resolve, 1000));

      navigation.navigate('AnalysisResult', {
        sessionId,
        runId: resp.run_id,
        songId: effectiveSongId,
      });
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) {
        return;
      }
      if (e instanceof AnalyzeStatusError) {
        Alert.alert(
          e.status === 'no_voice' ? '음성이 감지되지 않았습니다' : '분석 실패',
          e.message,
        );
      } else if (e instanceof AnalysisPollingTimeoutError) {
        Alert.alert(
          '분석 진행 중',
          '분석이 계속 진행 중입니다. 잠시 후 히스토리에서 결과를 확인해주세요.',
        );
      } else {
        Alert.alert('오류', e instanceof Error ? e.message : '분석 요청에 실패했습니다.');
      }
    } finally {
      if (analysisTimerRef.current) {
        clearInterval(analysisTimerRef.current);
        analysisTimerRef.current = null;
      }
      setAnalyzing(false);
      setAnalysisStep(0);
    }
  };

  // 같은 곡 제목의 다른 completed 세션이 있는지
  const hasSameSongAttempts = detail.song_title
    ? mockSessions.filter(
        (s) =>
          s.song_title === detail.song_title &&
          s.status === 'completed' &&
          s.session_id !== sessionId,
      ).length > 0
    : false;

  // 현재/다음 가사 라인
  const currentLyric = currentLineIdx >= 0 && currentLineIdx < lyrics.length
    ? lyrics[currentLineIdx].text
    : '';
  const nextLyric = currentLineIdx + 1 < lyrics.length
    ? lyrics[currentLineIdx + 1].text
    : '';

  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* 곡 제목 + 상태 */}
        <View style={styles.titleRow}>
          <Text style={styles.songTitle}>{detail.song_title ?? '제목 없음'}</Text>
          <StatusBadge status={detail.status} />
        </View>

      {/* 세션 정보 카드 */}
      <View style={styles.infoCard}>
        <InfoRow label="생성일" value={formatDate(detail.created_at)} />
        <InfoRow
          label="시작일"
          value={detail.started_at ? formatDate(detail.started_at) : '-'}
        />
        <InfoRow label="상태" value={getStatusLabel(detail.status)} />
        {hasSongId && <InfoRow label="원곡" value="🎵 연결됨" />}
      </View>

      {/* 기존 파일 */}
      {hasFiles && (
        <>
          <Text style={styles.sectionTitle}>녹음 파일</Text>
          {files.map((f) => (
            <View key={f.file_id} style={styles.fileCard}>
              <Text style={styles.fileName}>🎵 {f.file_type.toUpperCase()} 파일</Text>
              <Text style={styles.fileDuration}>{formatDuration(f.duration_ms)}</Text>
            </View>
          ))}
        </>
      )}

      {/* ─── 녹음 섹션 ─── */}
      <Text style={styles.sectionTitle}>녹음</Text>

      {/* 대기 상태: 녹음 전 */}
      {!recordingUri && !isRecording && (
        <View style={styles.recordSection}>
          {hasSongId && lyrics.length > 0 && (
            <View style={styles.lyricsPreviewCard}>
              <Text style={styles.lyricsPreviewIcon}>🎵</Text>
              <Text style={styles.lyricsPreviewText}>
                녹음을 시작하면 원곡이 재생됩니다
              </Text>
              <Text style={styles.lyricsPreviewSub}>
                가사에 맞춰 따라 불러주세요
              </Text>
            </View>
          )}
          {/* 키 조절 UI */}
          {hasSongId && (
            <View style={styles.keyShiftRow}>
              <TouchableOpacity
                style={[styles.keyShiftBtn, keyShift <= -4 && styles.keyShiftBtnDisabled]}
                onPress={() => setKeyShift((k) => Math.max(-4, k - 1))}
                disabled={isRecording || keyShift <= -4}
              >
                <Text style={styles.keyShiftBtnText}>▼</Text>
              </TouchableOpacity>
              <Text style={styles.keyShiftLabel}>
                {keyShift === 0 ? '원키' : `${keyShift > 0 ? '+' : ''}${keyShift}`}
              </Text>
              <TouchableOpacity
                style={[styles.keyShiftBtn, keyShift >= 4 && styles.keyShiftBtnDisabled]}
                onPress={() => setKeyShift((k) => Math.min(4, k + 1))}
                disabled={isRecording || keyShift >= 4}
              >
                <Text style={styles.keyShiftBtnText}>▲</Text>
              </TouchableOpacity>
            </View>
          )}
          <TouchableOpacity style={styles.recordButton} onPress={startRecording}>
            <Text style={styles.recordButtonEmoji}>🎤</Text>
          </TouchableOpacity>
          <Text style={styles.recordHint}>
            {hasSongId ? '터치하면 원곡 재생과 함께 녹음 시작' : '터치하여 녹음 시작'}
          </Text>
        </View>
      )}

      {/* ─── 녹음 중 ─── */}
      {isRecording && (
        <View style={styles.recordingCard}>
          {/* 피치 시각화 (songId 있고 원곡 피치 데이터 있을 때) */}
          {hasSongId && referencePitchFrames.length > 0 && (
            <PitchVisualizer
              referenceFrames={referencePitchFrames}
              resolutionMs={referencePitchResolution}
              userPitchHistory={userPitchHistory}
              currentUserPitch={currentPitch}
              currentTimeMs={elapsedMs}
              width={screenWidth - 64}
              keyShift={keyShift}
            />
          )}

          {/* 가사 표시 (songId 있을 때만) */}
          {hasSongId && lyrics.length > 0 && (
            <View style={styles.lyricsSection}>
              <Text style={styles.lyricsLabel}>🎵 가사</Text>
              <Text style={styles.currentLyric} numberOfLines={2}>
                {currentLyric || '♪ ...'}
              </Text>
              {nextLyric ? (
                <Text style={styles.nextLyric} numberOfLines={1}>
                  {nextLyric}
                </Text>
              ) : null}
            </View>
          )}

          {/* 볼륨 바 */}
          <View style={styles.volumeBarContainer}>
            <View style={styles.volumeBarBg}>
              <View
                style={[
                  styles.volumeBarFill,
                  {
                    width: `${Math.round(volumeLevel * 100)}%`,
                    backgroundColor: getVolumeColor(volumeLevel),
                  },
                ]}
              />
            </View>
          </View>

          {/* 경과 시간 */}
          <Text style={styles.timerText}>{formatTimer(elapsedSec)}</Text>

          {/* 녹음 중 인디케이터 + 정지 버튼 */}
          <View style={styles.recordingControls}>
            <View style={styles.recordingDot} />
            <Text style={styles.recordingLabel}>녹음 중</Text>
          </View>

          <TouchableOpacity style={styles.stopButton} onPress={stopRecording}>
            <Text style={styles.stopButtonEmoji}>⏹</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* 녹음 완료 */}
      {recordingUri && !isRecording && (
        <View style={styles.recordedSection}>
          <View style={styles.recordedInfo}>
            <Text style={styles.recordedIcon}>🎵</Text>
            <View style={styles.recordedDetails}>
              <Text style={styles.recordedTitle}>녹음 완료</Text>
              <Text style={styles.recordedDuration}>
                {formatDuration(recordingDurationMs)}
              </Text>
            </View>
          </View>
          <TouchableOpacity style={styles.playbackButton} onPress={handlePlayback}>
            <Text style={styles.playbackButtonText}>
              {isPlaying ? '⏹ 재생 중지' : '▶️ 미리 듣기'}
            </Text>
          </TouchableOpacity>
          <View style={styles.recordedActions}>
            <TouchableOpacity style={styles.reRecordButton} onPress={handleReRecord}>
              <Text style={styles.reRecordText}>다시 녹음</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.analyzeRecordingButton}
              onPress={handleAnalyze}
              disabled={analyzing}
            >
              {analyzing ? (
                <ActivityIndicator color="#FFF" size="small" />
              ) : (
                <Text style={styles.analyzeRecordingText}>이 녹음으로 분석</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* 분석 섹션 */}
      <Text style={styles.sectionTitle}>발성 분석</Text>
      {isAnalyzingStatus && (
        <View style={styles.analyzingCard}>
          <ActivityIndicator size="small" color={COLORS.warning} />
          <Text style={styles.analyzingText}>AI가 발성을 분석하고 있습니다...</Text>
        </View>
      )}

      {isCompleted && hasAnalysis && (
        <TouchableOpacity
          style={styles.resultButton}
          onPress={() =>
            navigation.navigate('AnalysisResult', {
              sessionId,
              runId: detail.analysis!.run_id,
              songId: effectiveSongId,
            })
          }
        >
          <Text style={styles.resultButtonText}>분석 결과 보기</Text>
        </TouchableOpacity>
      )}

      {hasSameSongAttempts && (
        <TouchableOpacity
          style={styles.songCompareButton}
          onPress={() =>
            navigation.navigate('SongComparison', { songTitle: detail.song_title })
          }
        >
          <Text style={styles.songCompareButtonText}>이전 시도와 비교</Text>
        </TouchableOpacity>
      )}

      {!isAnalyzingStatus && !hasAnalysis && hasFiles && !recordingUri && (
        <TouchableOpacity
          style={styles.analyzeButton}
          onPress={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.analyzeButtonText}>분석 시작</Text>
          )}
        </TouchableOpacity>
      )}

      {!isAnalyzingStatus && !hasAnalysis && !hasFiles && !recordingUri && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            녹음을 완료한 후 분석을 시작할 수 있습니다
          </Text>
        </View>
      )}
      </ScrollView>

      {/* 분석 중 오버레이 */}
      {analyzing && (
        <View style={styles.analysisOverlay}>
          <View style={styles.analysisOverlayCard}>
            <Text style={styles.analysisOverlayTitle}>🎙️ AI가 분석하고 있어요</Text>
            <Text style={styles.analysisOverlaySubtitle}>잠시만 기다려 주세요</Text>

            <View style={styles.analysisStepsList}>
              {analysisSteps.map((s, idx) => {
                const isDone = analysisStep > idx;
                const isCurrent = analysisStep === idx;
                return (
                  <View key={idx} style={styles.analysisStepRow}>
                    <Text style={styles.analysisStepEmoji}>
                      {isDone ? '✅' : s.emoji}
                    </Text>
                    <Text
                      style={[
                        styles.analysisStepLabel,
                        isDone && styles.analysisStepLabelDone,
                        isCurrent && styles.analysisStepLabelCurrent,
                      ]}
                    >
                      {s.label}
                    </Text>
                    {isCurrent && (
                      <ActivityIndicator
                        size="small"
                        color={COLORS.primary}
                        style={{ marginLeft: 8 }}
                      />
                    )}
                  </View>
                );
              })}
            </View>
          </View>
        </View>
      )}
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: 16, paddingBottom: 40 },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  songTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    flex: 1,
    marginRight: 8,
  },
  infoCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  infoLabel: { fontSize: 14, color: COLORS.textSecondary },
  infoValue: { fontSize: 14, fontWeight: '500', color: COLORS.textPrimary },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
    marginTop: 8,
  },
  fileCard: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 14,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  fileName: { fontSize: 14, color: COLORS.textPrimary },
  fileDuration: { fontSize: 13, color: COLORS.textSecondary },

  // ─── 녹음 대기 ───
  recordSection: { alignItems: 'center', paddingVertical: 24 },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.danger,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: COLORS.danger,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  recordButtonEmoji: { fontSize: 36 },
  recordHint: { marginTop: 12, fontSize: 14, color: COLORS.textSecondary, textAlign: 'center' },

  // ─── 키 조절 ───
  keyShiftRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    gap: 12,
  },
  keyShiftBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: COLORS.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  keyShiftBtnDisabled: {
    opacity: 0.3,
  },
  keyShiftBtnText: {
    fontSize: 16,
    color: COLORS.textPrimary,
  },
  keyShiftLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: COLORS.textPrimary,
    minWidth: 40,
    textAlign: 'center',
  },

  // ─── 녹음 전 가사 안내 ───
  lyricsPreviewCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    alignItems: 'center',
    width: '100%',
  },
  lyricsPreviewIcon: { fontSize: 28, marginBottom: 8 },
  lyricsPreviewText: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary, textAlign: 'center' },
  lyricsPreviewSub: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center', marginTop: 4 },

  // ─── 녹음 중 카드 ───
  recordingCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    alignItems: 'center',
  },
  lyricsSection: {
    width: '100%',
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    alignItems: 'center',
    minHeight: 80,
    justifyContent: 'center',
  },
  lyricsLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginBottom: 8,
    alignSelf: 'flex-start',
  },
  currentLyric: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
    lineHeight: 28,
  },
  nextLyric: {
    fontSize: 14,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: 6,
  },
  volumeBarContainer: {
    width: '100%',
    marginBottom: 12,
  },
  volumeBarBg: {
    height: 8,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
    overflow: 'hidden',
  },
  volumeBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  timerText: {
    fontSize: 32,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  recordingControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 16,
  },
  recordingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.danger,
  },
  recordingLabel: { fontSize: 14, color: COLORS.danger },
  stopButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: COLORS.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stopButtonEmoji: { fontSize: 32 },

  // ─── 녹음 완료 ───
  recordedSection: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  recordedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  recordedIcon: { fontSize: 32, marginRight: 12 },
  recordedDetails: { flex: 1 },
  recordedTitle: { fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },
  recordedDuration: { fontSize: 13, color: COLORS.textSecondary, marginTop: 2 },
  recordedActions: { flexDirection: 'row', gap: 10 },
  playbackButton: {
    backgroundColor: COLORS.surface,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 10,
  },
  playbackButtonText: { fontSize: 14, color: COLORS.textPrimary, fontWeight: '600' },
  reRecordButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
  },
  reRecordText: { fontSize: 14, color: COLORS.textSecondary, fontWeight: '500' },
  analyzeRecordingButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
  },
  analyzeRecordingText: { fontSize: 14, color: '#FFF', fontWeight: '600' },

  // ─── 분석 ───
  analyzingCard: {
    backgroundColor: COLORS.warning + '1A',
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  analyzingText: { fontSize: 14, color: COLORS.warning },
  analyzeButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  analyzeButtonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  resultButton: {
    backgroundColor: COLORS.success,
    borderRadius: 10,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  resultButtonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  songCompareButton: {
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  songCompareButtonText: { color: COLORS.primary, fontSize: 15, fontWeight: '600' },
  emptyCard: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 20,
    marginBottom: 12,
    alignItems: 'center',
  },
  emptyText: { fontSize: 13, color: COLORS.textMuted, textAlign: 'center' },

  // ─── 분석 오버레이 ───
  analysisOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  analysisOverlayCard: {
    backgroundColor: COLORS.card,
    borderRadius: 20,
    padding: 32,
    width: '85%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  analysisOverlayTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 6,
  },
  analysisOverlaySubtitle: {
    fontSize: 14,
    color: COLORS.textMuted,
    marginBottom: 28,
  },
  analysisStepsList: {
    width: '100%',
  },
  analysisStepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
  },
  analysisStepEmoji: {
    fontSize: 20,
    width: 32,
    textAlign: 'center',
  },
  analysisStepLabel: {
    fontSize: 15,
    color: COLORS.textMuted,
    flex: 1,
  },
  analysisStepLabelDone: {
    color: COLORS.success,
  },
  analysisStepLabelCurrent: {
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
});
