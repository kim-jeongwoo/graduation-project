import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Dimensions,
} from 'react-native';
import { Audio } from 'expo-av';
import Svg, { Path, Line } from 'react-native-svg';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { useAuth } from '../../context/AuthContext';
import { isAuthExpiredError } from '../../api/client';
import { clearSongPitchGuideCache, getSongKaraokeData, getSongKaraokeLyricsOnly, getSongMrUrl } from '../../api/songs';
import {
  AnalyzeStatusError,
  createSession,
  uploadSessionFile,
  startAnalysis,
} from '../../api/sessions';
import { AnalysisPollingTimeoutError, pollAnalysisStatus } from '../../api/analysis';
import { requestMicrophonePermission } from '../../services/audio/microphone';
import { VocalRecorder } from '../../services/audio/recorder';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { detectPitch } from '../../services/audio/pitchDetector';
import type { LyricLine, PitchPoint, PitchGuide, MidiSegment, GuideSource } from '../../types/karaoke';
import {
  generateFakeUserPitch,
  getPitchAccuracy,
  midiToNoteName,
} from '../../types/karaoke';

const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === 'true';
const USE_REALTIME_PITCH = true; // false = 가짜 피치 시뮬레이션
const MOCK_RUN_ID = 'c65d43fa-ef3f-4a46-a70e-c102c61eee6c';
const GUIDE_FAILURE_NOTICE_DELAY_SEC = 5;

// ─── Pitch graph constants ───
const SCREEN_W = Dimensions.get('window').width;
const GRAPH_W  = SCREEN_W;
const GRAPH_H  = 200;
const WINDOW_BEFORE_SEC = 3;
const WINDOW_AFTER_SEC  = 5;
const CURSOR_X = GRAPH_W * (WINDOW_BEFORE_SEC / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC));
const MIDI_MIN = 40;
const MIDI_MAX = 88;

function midiToY(midi: number): number {
  return GRAPH_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GRAPH_H;
}
function timeToX(t: number, currentTime: number): number {
  return CURSOR_X + ((t - currentTime) / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC)) * GRAPH_W;
}

// ─── Nav types ───
type AppRootParams = {
  MainTabs: undefined;
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
};
type Props = NativeStackScreenProps<AppRootParams, 'Karaoke'>;

// ─── Analyze step labels ───
const ANALYZE_STEPS = ['녹음 업로드 중...', '분석 요청 접수 중...', 'AI 분석 중...', '결과 정리 중...'];

// ─── Pitch graph component ───
interface PitchGraphProps {
  currentTime: number;
  guideSource: GuideSource;
  midiSegments: MidiSegment[];
  guidePoints: PitchPoint[];
  userPoints: PitchPoint[];
}

function PitchGraph({ currentTime, guideSource, midiSegments, guidePoints, userPoints }: PitchGraphProps) {
  // MIDI 직선 모드: window 내 segments 필터
  const visibleMidi = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    const hi = currentTime + WINDOW_AFTER_SEC  + 0.5;
    return midiSegments.filter((s) => s.end >= lo && s.start <= hi);
  }, [midiSegments, currentTime]);

  const visibleGuide = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    const hi = currentTime + WINDOW_AFTER_SEC  + 0.5;
    return guidePoints.filter((p) => p.time >= lo && p.time <= hi);
  }, [guidePoints, currentTime]);

  const visibleUser = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    return userPoints.filter(
      (p) => p.time >= lo && p.time <= currentTime && p.midi !== null && p.voiced,
    );
  }, [userPoints, currentTime]);

  function buildPaths(
    points: PitchPoint[],
    colorFn: (p: PitchPoint) => string,
  ): React.ReactNode[] {
    const result: React.ReactNode[] = [];
    let seg: { x: number; y: number }[] = [];
    let segColor = '';
    let segKey = 0;
    const flush = () => {
      if (seg.length >= 2) {
        const d = seg.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(' ');
        result.push(<Path key={segKey++} d={d} stroke={segColor} strokeWidth={3}
          fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      }
      seg = [];
    };
    for (const p of points) {
      if (!p.voiced || p.midi === null) { flush(); continue; }
      const c = colorFn(p);
      if (seg.length > 0 && c !== segColor) flush();
      segColor = c;
      seg.push({ x: timeToX(p.time, currentTime), y: midiToY(p.midi) });
    }
    flush();
    return result;
  }

  // MIDI 직선 세그먼트 (guide_source === 'midi' 전용)
  const midiLines = useMemo(() => {
    if (guideSource !== 'midi') return null;
    return visibleMidi.map((s, i) => {
      const x1 = timeToX(s.start, currentTime);
      const x2 = timeToX(s.end,   currentTime);
      const y  = midiToY(s.midi);
      return (
        <Line
          key={i}
          x1={x1} y1={y} x2={x2} y2={y}
          stroke="#938ea1"
          strokeWidth={6}
          strokeLinecap="round"
        />
      );
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleMidi, currentTime, guideSource]);

  const guidePaths = useMemo(
    () => buildPaths(visibleGuide, () => '#938ea1aa'),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [visibleGuide, currentTime],
  );
  const shouldRenderMidiGuide = guideSource === 'midi' && visibleMidi.length > 0;

  const userPaths = useMemo(() => {
    return buildPaths(visibleUser, (p) => {
      const nearby = visibleGuide.reduce<PitchPoint | null>((best, g) => {
        if (!g.voiced || g.midi === null) return best;
        if (!best) return g;
        return Math.abs(g.time - p.time) < Math.abs(best.time - p.time) ? g : best;
      }, null);
      if (!nearby?.midi || p.midi === null) return COLORS.textMuted;
      const acc = getPitchAccuracy(p.midi, nearby.midi);
      return acc === 'accurate' ? '#59dda5' : acc === 'slight_off' ? '#ffb780' : '#ffb4ab';
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleUser, visibleGuide, currentTime]);

  const latestMidi = useMemo(
    () => [...visibleUser].reverse().find((p) => p.midi !== null && p.voiced)?.midi ?? null,
    [visibleUser],
  );
  const nearestGuideMidi = useMemo(
    () => visibleGuide.find((p) => p.voiced && p.midi !== null && p.time >= currentTime)?.midi ?? null,
    [visibleGuide, currentTime],
  );
  const accuracy = latestMidi !== null && nearestGuideMidi !== null
    ? getPitchAccuracy(latestMidi, nearestGuideMidi)
    : null;
  const noteColor = accuracy === 'accurate' ? '#59dda5'
    : accuracy === 'slight_off' ? '#ffb780'
    : accuracy === 'wrong' ? '#ffb4ab'
    : COLORS.textMuted;

  return (
    <View style={graphStyles.container}>
      <Svg width={GRAPH_W} height={GRAPH_H}>
        {/* 가이드라인: MIDI 직선 or CREPE 곡선 */}
        {shouldRenderMidiGuide ? midiLines : guidePaths}
        {userPaths}
        <Line x1={CURSOR_X} y1={0} x2={CURSOR_X} y2={GRAPH_H}
          stroke={COLORS.primary} strokeWidth={1.5} strokeDasharray="4,3" />
      </Svg>
      {latestMidi !== null && (
        <View style={[graphStyles.noteBox, { borderColor: noteColor }]}>
          <Text style={[graphStyles.noteText, { color: noteColor }]}>
            {midiToNoteName(latestMidi)}
          </Text>
        </View>
      )}
    </View>
  );
}
const graphStyles = StyleSheet.create({
  container: { width: GRAPH_W, height: GRAPH_H, backgroundColor: COLORS.surface },
  noteBox: {
    position: 'absolute', top: 8, right: 12,
    paddingHorizontal: 8, paddingVertical: 3,
    borderRadius: 6, borderWidth: 1.5, backgroundColor: COLORS.card,
  },
  noteText: { fontSize: 13, fontWeight: '700' },
});

// ─── Main screen ───
export default function KaraokeScreen({ navigation, route }: Props) {
  const { songId, title, artist, mrDurationSec } = route.params;
  const { token } = useAuth();

  const [loading, setLoading]             = useState(true);
  const [countdown, setCountdown]         = useState<number | null>(null);
  const [lyrics, setLyrics]               = useState<LyricLine[]>([]);
  const [pitchGuide, setPitchGuide]       = useState<PitchGuide | null>(null);
  const [pitchGuideStatus, setPitchGuideStatus] = useState<'loading' | 'success' | 'failed' | null>(null);
  const [userPitch, setUserPitch]         = useState<PitchPoint[]>([]);
  const [currentTime, setCurrentTime]     = useState(0);
  const [playing, setPlaying]             = useState(false);
  const [isAnalyzing, setIsAnalyzing]     = useState(false);
  const [analyzeStep, setAnalyzeStep]     = useState(0);
  const [paused, setPaused]               = useState(false);
  const [resumeCountdown, setResumeCountdown] = useState<number | null>(null);

  const soundRef       = useRef<Audio.Sound | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const currentTimeRef = useRef(0);
  const startMrAndRecordRef = useRef<(() => void) | null>(null);
  const resumeAfterCountdownRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(false);
  const focusedRef = useRef(false);
  const playingRef = useRef(false);
  const pausedRef = useRef(false);
  const resumeCountingRef = useRef(false);
  const isAnalyzingRef = useRef(false);
  const attemptSeqRef = useRef(0);
  const activeAnalyzeAttemptRef = useRef<number | null>(null);
  const leaveConfirmedRef = useRef(false);
  const leaveAlertVisibleRef = useRef(false);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resumeCountdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearCountdownTimer = useCallback(() => {
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }
  }, []);

  const clearResumeCountdownTimer = useCallback(() => {
    if (resumeCountdownTimerRef.current) {
      clearInterval(resumeCountdownTimerRef.current);
      resumeCountdownTimerRef.current = null;
    }
    resumeCountingRef.current = false;
  }, []);

  const invalidateAnalyzeAttempt = useCallback(() => {
    attemptSeqRef.current += 1;
    activeAnalyzeAttemptRef.current = null;
  }, []);

  const beginAnalyzeAttempt = useCallback(() => {
    const attemptId = attemptSeqRef.current + 1;
    attemptSeqRef.current = attemptId;
    activeAnalyzeAttemptRef.current = attemptId;
    leaveConfirmedRef.current = false;
    return attemptId;
  }, []);

  const isActiveAnalyzeAttempt = useCallback((attemptId: number) => {
    return mountedRef.current
      && focusedRef.current
      && !leaveConfirmedRef.current
      && activeAnalyzeAttemptRef.current === attemptId
      && !playingRef.current
      && !recorderRef.current.active;
  }, []);

  const safeGoBack = useCallback(() => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    }
  }, [navigation]);

  const cleanupStartFailure = useCallback(async (sound?: Audio.Sound | null, recorderStarted = false) => {
    const s = sound ?? soundRef.current;
    if (s) {
      try { s.setOnPlaybackStatusUpdate(null); } catch {}
      try { await s.stopAsync(); } catch {}
      try { await s.unloadAsync(); } catch {}
      if (soundRef.current === s) soundRef.current = null;
    }
    if (recorderStarted || recorderRef.current.active) {
      try { await recorderRef.current.cancel(); } catch {}
    }
    if (!mountedRef.current) return;
    currentTimeRef.current = 0;
    setCurrentTime(0);
    playingRef.current = false;
    pausedRef.current = false;
    setPlaying(false);
    setPaused(false);
    setCountdown(null);
    setResumeCountdown(null);
    setLoading(false);
    setUserPitch([]);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    focusedRef.current = navigation.isFocused();
    const unsubscribeFocus = navigation.addListener('focus', () => {
      focusedRef.current = true;
    });
    const unsubscribeBlur = navigation.addListener('blur', () => {
      focusedRef.current = false;
    });
    return () => {
      mountedRef.current = false;
      focusedRef.current = false;
      clearCountdownTimer();
      clearResumeCountdownTimer();
      invalidateAnalyzeAttempt();
      unsubscribeFocus();
      unsubscribeBlur();
    };
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, navigation]);

  useEffect(() => {
    isAnalyzingRef.current = isAnalyzing;
  }, [isAnalyzing]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('beforeRemove', (e) => {
      if (!isAnalyzingRef.current || leaveConfirmedRef.current) return;

      e.preventDefault();
      if (leaveAlertVisibleRef.current) return;

      leaveAlertVisibleRef.current = true;
      Alert.alert(
        '분석이 진행 중입니다',
        '지금 나가도 분석은 계속 진행될 수 있습니다. 완료된 결과는 히스토리에서 확인할 수 있습니다.',
        [
          {
            text: '계속 기다리기',
            style: 'cancel',
            onPress: () => {
              leaveAlertVisibleRef.current = false;
            },
          },
          {
            text: '나가기',
            style: 'destructive',
            onPress: () => {
              leaveAlertVisibleRef.current = false;
              leaveConfirmedRef.current = true;
              invalidateAnalyzeAttempt();
              clearCountdownTimer();
              clearResumeCountdownTimer();
              void cleanupStartFailure(soundRef.current, recorderRef.current.active);
              navigation.dispatch(e.data.action);
            },
          },
        ],
      );
    });

    return unsubscribe;
  }, [clearCountdownTimer, clearResumeCountdownTimer, cleanupStartFailure, invalidateAnalyzeAttempt, navigation]);

  // ─── Permission check + data load ───
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 1. Microphone permission
      const granted = await requestMicrophonePermission();
      if (!granted) {
        Alert.alert(
          '마이크 권한 필요',
          '녹음하려면 마이크 권한이 필요합니다.\n설정 > 앱 > 마이크 권한을 허용해주세요.',
          [{ text: '확인', onPress: safeGoBack }],
        );
        return;
      }

      // 2. Required karaoke data: lyrics first, pitch-guide in background.
      try {
        if (songId === '004') {
          clearSongPitchGuideCache(songId);
        }
        const lrc = await getSongKaraokeLyricsOnly(songId);
        if (cancelled) return;
        setLyrics(lrc);
        setPitchGuide(null);
        setPitchGuideStatus('loading');
        setUserPitch([]);
        setLoading(false);
        startCountdown();

        getSongKaraokeData(songId)
          .then(({ lyrics: guideAdjustedLrc, pitchGuide: guide, pitchGuideLoadFailed }) => {
            if (cancelled) return;
            if (guide) {
              setLyrics(guideAdjustedLrc);
              setPitchGuide(guide);
              setPitchGuideStatus('success');
              if (!USE_REALTIME_PITCH) setUserPitch(generateFakeUserPitch(guide.points));
              return;
            }
            if (pitchGuideLoadFailed) {
              setPitchGuideStatus('failed');
            }
          })
          .catch(() => {
            if (cancelled) return;
            setPitchGuideStatus('failed');
          });
      } catch (e) {
        if (isAuthExpiredError(e)) return;
        console.error('[KaraokeScreen] load error:', e);
        Alert.alert('오류', '곡 데이터를 불러오지 못했습니다.', [
          { text: '닫기', onPress: safeGoBack },
        ]);
      }
    })();
    return () => {
      cancelled = true;
      clearCountdownTimer();
      clearResumeCountdownTimer();
      invalidateAnalyzeAttempt();
      soundRef.current?.unloadAsync();
      recorderRef.current.cancel();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  // ─── Countdown → MR + recording start ───
  const handlePitchSamples = useCallback((samples: Float32Array) => {
    if (pausedRef.current || resumeCountingRef.current) return;
    const result = detectPitch(samples);
    const t = currentTimeRef.current;
    if (t < 0.1) return;
    setUserPitch((prev) => {
      const cutoff = t - 10;
      const trimmed = cutoff > 0 ? prev.filter((p) => p.time >= cutoff) : prev;
      if (!result.voiced || result.midi === null) return trimmed;
      return [...trimmed, { time: t, midi: result.midi, voiced: true, freqHz: result.freq, confidence: 1 }];
    });
  }, []);

  const startCountdown = useCallback(() => {
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    pausedRef.current = false;
    setPaused(false);
    let n = 3;
    setCountdown(n);
    const iv = setInterval(() => {
      if (!mountedRef.current || !focusedRef.current) {
        clearInterval(iv);
        countdownTimerRef.current = null;
        return;
      }
      n -= 1;
      if (n <= 0) {
        clearInterval(iv);
        countdownTimerRef.current = null;
        setCountdown(null);
        void startMrAndRecordRef.current?.();
      }
      else setCountdown(n);
    }, 1000);
    countdownTimerRef.current = iv;
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt]);

  const startMrAndRecord = useCallback(async () => {
    let sound: Audio.Sound | null = null;
    let recorderStarted = false;
    try {
      if (!USE_MOCK) {
        await recorderRef.current.start(
          USE_REALTIME_PITCH ? handlePitchSamples : undefined,
          { capturePcm: true },
        );
        recorderStarted = true;
      }
      sound = new Audio.Sound();
      soundRef.current = sound;
      // ① 콜백 먼저 등록 (shouldPlay:true + loadAsync 완료 후 등록 시 초기 update 누락 방지)
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded) {
          currentTimeRef.current = status.positionMillis / 1000;
          if (!mountedRef.current) return;
          setCurrentTime(status.positionMillis / 1000);
          playingRef.current = status.isPlaying;
          setPlaying(status.isPlaying);
        }
      });
      // ② shouldPlay:false 로딩만
      await sound.loadAsync(
        { uri: getSongMrUrl(songId), headers: token ? { Authorization: `Bearer ${token}` } : {} },
        { shouldPlay: false, progressUpdateIntervalMillis: 16 },
      );
      // ③ position 0에서 명시적 재생 시작
      await sound.playFromPositionAsync(0);
    } catch (e) {
      console.error('[KaraokeScreen] startMrAndRecord error:', e);
      await cleanupStartFailure(sound, recorderStarted);
      Alert.alert('재생 시작 실패', 'MR 재생을 시작하지 못했습니다. 다시 시도해 주세요.', [
        { text: '닫기', style: 'cancel', onPress: safeGoBack },
        { text: '다시 시도', onPress: startCountdown },
      ]);
    }
  }, [cleanupStartFailure, handlePitchSamples, safeGoBack, songId, startCountdown, token]);

  useEffect(() => {
    startMrAndRecordRef.current = startMrAndRecord;
  }, [startMrAndRecord]);

  const resumeAfterCountdown = useCallback(async () => {
    try {
      if (!USE_MOCK) {
        await recorderRef.current.resumeRecording(USE_REALTIME_PITCH ? handlePitchSamples : undefined);
      }
      const s = soundRef.current;
      if (s) await s.playAsync();
      pausedRef.current = false;
      playingRef.current = true;
      if (!mountedRef.current) return;
      setPaused(false);
      setPlaying(true);
    } catch (e) {
      console.error('[KaraokeScreen] resume error:', e);
      try { await recorderRef.current.pause(); } catch {}
      pausedRef.current = true;
      playingRef.current = false;
      if (mountedRef.current) {
        setPaused(true);
        setPlaying(false);
      }
      Alert.alert('재개 실패', '녹음 재개를 시작하지 못했습니다. 다시 시도해 주세요.');
    }
  }, [handlePitchSamples]);

  useEffect(() => {
    resumeAfterCountdownRef.current = resumeAfterCountdown;
  }, [resumeAfterCountdown]);

  const startResumeCountdown = useCallback(() => {
    if (!pausedRef.current || isAnalyzingRef.current) return;
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    let n = 3;
    resumeCountingRef.current = true;
    setResumeCountdown(n);
    const iv = setInterval(() => {
      if (!mountedRef.current || !focusedRef.current || !pausedRef.current) {
        clearInterval(iv);
        resumeCountdownTimerRef.current = null;
        resumeCountingRef.current = false;
        return;
      }
      n -= 1;
      if (n <= 0) {
        clearInterval(iv);
        resumeCountdownTimerRef.current = null;
        resumeCountingRef.current = false;
        setResumeCountdown(null);
        void resumeAfterCountdownRef.current?.();
      } else {
        setResumeCountdown(n);
      }
    }, 1000);
    resumeCountdownTimerRef.current = iv;
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt]);

  const handlePauseResume = useCallback(async () => {
    if (isAnalyzingRef.current || countdown !== null || resumeCountdown !== null) return;

    if (pausedRef.current) {
      startResumeCountdown();
      return;
    }

    const s = soundRef.current;
    if (!s || !recorderRef.current.active) return;

    clearResumeCountdownTimer();
    try {
      await s.pauseAsync();
      await recorderRef.current.pause();
      pausedRef.current = true;
      playingRef.current = false;
      setPaused(true);
      setPlaying(false);
    } catch (e) {
      console.error('[KaraokeScreen] pause error:', e);
      Alert.alert('일시정지 실패', '녹음을 일시정지하지 못했습니다. 다시 시도해 주세요.');
    }
  }, [clearResumeCountdownTimer, countdown, resumeCountdown, startResumeCountdown]);

  // ─── Restart ───
  const handleRestart = useCallback(() => {
    Alert.alert('처음부터 다시 시작', '녹음이 초기화됩니다.', [
      { text: '취소', style: 'cancel' },
      {
        text: '확인',
        onPress: async () => {
          invalidateAnalyzeAttempt();
          clearCountdownTimer();
          clearResumeCountdownTimer();
          try {
            const s = soundRef.current;
            if (s) {
              try { await s.stopAsync(); } catch {}
              try { await s.unloadAsync(); } catch {}
              soundRef.current = null;
            }
            await recorderRef.current.cancel();
          } catch (e) {
            console.error('[KaraokeScreen] restart cleanup error:', e);
          }
          setCurrentTime(0);
          currentTimeRef.current = 0;
          playingRef.current = false;
          pausedRef.current = false;
          setPlaying(false);
          setPaused(false);
          setResumeCountdown(null);
          if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
          else setUserPitch([]);
          startCountdown();
        },
      },
    ]);
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, pitchGuide, startCountdown]);

  // ─── Close (X) — cancel without analysis ───
  const handleClose = useCallback(async () => {
    if (isAnalyzingRef.current) {
      safeGoBack();
      return;
    }
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    const s = soundRef.current;
    if (s) await s.stopAsync();
    await recorderRef.current.cancel();
    safeGoBack();
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, safeGoBack]);

  const handleRetryRecording = useCallback(async () => {
    invalidateAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    const snd = soundRef.current;
    if (snd) {
      try { snd.setOnPlaybackStatusUpdate(null); } catch {}
      try { await snd.stopAsync(); } catch {}
      try { await snd.unloadAsync(); } catch {}
      soundRef.current = null;
    }
    if (recorderRef.current.active) {
      try { await recorderRef.current.cancel(); } catch {}
    }
    setIsAnalyzing(false);
    setAnalyzeStep(0);
    setCountdown(null);
    setResumeCountdown(null);
    setCurrentTime(0);
    currentTimeRef.current = 0;
    playingRef.current = false;
    pausedRef.current = false;
    setPlaying(false);
    setPaused(false);
    if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
    else setUserPitch([]);
    setTimeout(startCountdown, 0);
  }, [clearCountdownTimer, clearResumeCountdownTimer, invalidateAnalyzeAttempt, pitchGuide, startCountdown]);

  const showRetryRecordingAlert = useCallback((title: string, message: string) => {
    Alert.alert(title, message, [
      {
        text: '다시 녹음',
        onPress: () => { void handleRetryRecording(); },
      },
      { text: '닫기', style: 'cancel', onPress: safeGoBack },
    ]);
  }, [handleRetryRecording, safeGoBack]);

  // ─── STOP → analyze → EvalResult ───
  const handleStop = useCallback(async () => {
    const attemptId = beginAnalyzeAttempt();
    clearCountdownTimer();
    clearResumeCountdownTimer();
    if (USE_MOCK) {
      const s = soundRef.current;
      if (s) await s.stopAsync();
      playingRef.current = false;
      pausedRef.current = false;
      setPlaying(false);
      setPaused(false);
      setResumeCountdown(null);
      if (isActiveAnalyzeAttempt(attemptId)) goToEvalResult(MOCK_RUN_ID);
      if (activeAnalyzeAttemptRef.current === attemptId) activeAnalyzeAttemptRef.current = null;
      return;
    }

    const s = soundRef.current;
    if (s) await s.stopAsync();
    playingRef.current = false;
    pausedRef.current = false;
    setPlaying(false);
    setPaused(false);
    setResumeCountdown(null);

    isAnalyzingRef.current = true;
    setIsAnalyzing(true);
    setAnalyzeStep(0);

    try {
      // Stop recording
      const { uri, fileName, mimeType } = await recorderRef.current.stop();
      if (!isActiveAnalyzeAttempt(attemptId)) return;
      if (!uri) {
        throw new Error('녹음 파일을 만들지 못했습니다. 다시 녹음해 주세요.');
      }

      // Step 0: upload
      setAnalyzeStep(0);
      const session = await createSession({ song_id: songId });
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      try {
        await uploadSessionFile(session.session_id, uri, fileName, mimeType);
      } catch (err: unknown) {
        if (!isActiveAnalyzeAttempt(attemptId)) return;
        if (isAuthExpiredError(err)) return;
        Alert.alert(
          '녹음 파일 업로드 실패',
          '녹음 파일 업로드에 실패했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요.',
        );
        return;
      }

      // Step 1: request server-side async analysis
      setAnalyzeStep(1);
      const { run_id, status, reason } = await startAnalysis(session.session_id);
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      if (status === 'no_voice' || status === 'invalid') {
        showRetryRecordingAlert(
          status === 'no_voice' ? '음성이 감지되지 않았어요' : '다시 녹음이 필요해요',
          status === 'no_voice'
            ? '마이크가 정상 동작하는지, 노래를 부르셨는지 확인해주세요.'
            : '분석할 수 없는 녹음입니다. 다시 녹음해 주세요.',
        );
        return;
      }

      if (status === 'failed' || status === 'error') {
        throw new Error(`AI 분석에 실패했습니다. ${reason ?? '다시 시도해주세요.'}`);
      }

      // Step 2: wait until queued async analysis reaches a terminal result
      setAnalyzeStep(2);
      await pollAnalysisStatus(run_id);
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      // Step 3: brief done state
      setAnalyzeStep(3);
      await new Promise<void>((r) => setTimeout(r, 600));
      if (!isActiveAnalyzeAttempt(attemptId)) return;

      goToEvalResult(run_id);
    } catch (err: unknown) {
      if (!isActiveAnalyzeAttempt(attemptId)) return;
      if (isAuthExpiredError(err)) return;
      if (err instanceof AnalyzeStatusError && (err.status === 'no_voice' || err.status === 'invalid')) {
        showRetryRecordingAlert(
          err.status === 'no_voice' ? '음성이 감지되지 않았어요' : '다시 녹음이 필요해요',
          err.message,
        );
        return;
      }
      if (err instanceof AnalysisPollingTimeoutError) {
        Alert.alert(
          '분석 진행 중',
          '분석이 계속 진행 중입니다. 잠시 후 히스토리에서 결과를 확인해주세요.',
          [{ text: '확인', onPress: safeGoBack }],
        );
        return;
      }
      const msg = err instanceof Error ? err.message : '다시 시도해주세요.';
      if (msg.includes('녹음 파일')) {
        Alert.alert('녹음 파일 생성 실패', msg);
        return;
      }
      Alert.alert('분석 실패', msg, [
        { text: '다시 시도', onPress: handleStop },
        { text: '닫기', onPress: safeGoBack },
      ]);
    } finally {
      if (activeAnalyzeAttemptRef.current === attemptId) {
        activeAnalyzeAttemptRef.current = null;
        isAnalyzingRef.current = false;
        if (mountedRef.current) setIsAnalyzing(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beginAnalyzeAttempt, clearCountdownTimer, clearResumeCountdownTimer, isActiveAnalyzeAttempt, songId, navigation, safeGoBack, showRetryRecordingAlert]);

  // Navigate to EvalResult (KaraokeScreen is in AppRootStack, EvalResult is in HomeStack)
  const goToEvalResult = useCallback((runId: string) => {
    (navigation as any).navigate('MainTabs', {
      screen: 'HomeTab',
      params: { screen: 'EvalResult', params: { runId, songId } },
    });
  }, [navigation, songId]);

  // ─── Lyrics sync ───
  const currentLine = useMemo(
    () => lyrics.find((l) => l.timeStart <= currentTime && currentTime < l.timeEnd) ?? null,
    [lyrics, currentTime],
  );
  const nextLine = useMemo(
    () => lyrics.find((l) => l.timeStart > currentTime) ?? null,
    [lyrics, currentTime],
  );

  // ─── Guide offset ───
  const guideOffset = SONG_GUIDE_OFFSETS[songId] ?? 0;
  const adjustedMidiSegments = useMemo(
    () => guideOffset === 0
      ? pitchGuide?.midiSegments ?? []
      : (pitchGuide?.midiSegments ?? []).map((s) => ({
          ...s,
          start: s.start + guideOffset,
          end:   s.end   + guideOffset,
        })),
    [pitchGuide, guideOffset],
  );
  const adjustedGuidePoints = useMemo(
    () => guideOffset === 0
      ? pitchGuide?.points ?? []
      : (pitchGuide?.points ?? []).map((p) => ({
          ...p,
          time: p.time + guideOffset,
        })),
    [pitchGuide, guideOffset],
  );

  // ─── Progress ───
  const totalSec = mrDurationSec > 0
    ? mrDurationSec
    : (pitchGuide?.points[pitchGuide.points.length - 1]?.time ?? 0);
  const progress = totalSec > 0 ? Math.min(currentTime / totalSec, 1) : 0;
  const showGuideFailureNotice = pitchGuideStatus === 'failed' && currentTime >= GUIDE_FAILURE_NOTICE_DELAY_SEC;
  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // ─── Loading ───
  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>곡 데이터 로딩 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleClose}>
          <Text style={styles.closeBtn}>✕</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{artist} - {title}</Text>
        <View style={{ width: 32 }} />
      </View>

      {/* 피치 그래프 */}
      {pitchGuide ? (
        <PitchGraph
          currentTime={currentTime}
          guideSource={pitchGuide.guideSource}
          midiSegments={adjustedMidiSegments}
          guidePoints={adjustedGuidePoints}
          userPoints={userPitch}
        />
      ) : (
        <View style={graphStyles.container} />
      )}

      {showGuideFailureNotice && (
        <View style={styles.guideWarning}>
          <Text style={styles.guideWarningText}>
            피치 가이드를 불러오지 못했습니다. MR과 녹음은 계속할 수 있습니다.
          </Text>
        </View>
      )}

      {/* 가사 영역 */}
      <View style={styles.lyricsArea}>
        <Text style={styles.currentLyric} numberOfLines={2}>
          {currentLine?.text ?? ''}
        </Text>
        <Text style={styles.nextLyric} numberOfLines={1}>
          {nextLine?.text ?? ''}
        </Text>
      </View>

      {/* 프로그레스 바 */}
      <View style={styles.progressArea}>
        <Text style={styles.timeText}>{fmt(currentTime)}</Text>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.timeText}>{fmt(totalSec)}</Text>
      </View>

      {/* 컨트롤: 다시시작 | 일시정지/재개 | 종료 후 분석 */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.ctrlBtn} onPress={handleRestart}>
          <Text style={styles.ctrlIcon}>↻</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.pauseBtn, paused && styles.resumeBtn]}
          onPress={handlePauseResume}
        >
          <Text style={styles.pauseIcon}>{paused ? '▶' : '||'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.finishBtn} onPress={() => { void handleStop(); }}>
          <Text style={styles.finishText}>종료 후 분석</Text>
        </TouchableOpacity>
      </View>

      {/* 카운트다운 오버레이 */}
      {countdown !== null && (
        <View style={styles.overlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
        </View>
      )}

      {resumeCountdown !== null && (
        <View pointerEvents="none" style={styles.resumeCountdownOverlay}>
          <Text style={styles.resumeCountdownNum}>{resumeCountdown}</Text>
        </View>
      )}

      {/* 분석 중 오버레이 */}
      {isAnalyzing && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.analyzeStepText}>{ANALYZE_STEPS[analyzeStep]}</Text>
          <View style={styles.stepIndicators}>
            {ANALYZE_STEPS.map((_, i) => (
              <View
                key={i}
                style={[
                  styles.stepDot,
                  i <= analyzeStep ? styles.stepDotActive : styles.stepDotInactive,
                ]}
              />
            ))}
          </View>
          <Text style={styles.analyzeHint}>
            곡 길이와 분석 구간 수에 따라 시간이 걸릴 수 있습니다.
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  centered: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
    backgroundColor: COLORS.background, gap: 16,
  },
  loadingText: { color: COLORS.textSecondary, fontSize: 14 },

  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 52, paddingHorizontal: 16, paddingBottom: 10,
  },
  closeBtn: { fontSize: 20, color: COLORS.textSecondary, padding: 4 },
  headerTitle: {
    flex: 1, textAlign: 'center',
    fontSize: 15, fontWeight: '600', color: COLORS.textPrimary,
  },

  lyricsArea: {
    height: 96, justifyContent: 'center', alignItems: 'center',
    paddingHorizontal: 24, gap: 8, backgroundColor: COLORS.background,
  },
  guideWarning: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: COLORS.card,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  guideWarningText: {
    fontSize: 12,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  currentLyric: {
    fontSize: 22, fontWeight: '700', color: COLORS.textPrimary,
    textAlign: 'center', lineHeight: 30,
  },
  nextLyric: { fontSize: 14, color: COLORS.textMuted, textAlign: 'center' },

  progressArea: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 10, gap: 10,
  },
  timeText: { fontSize: 12, color: COLORS.textMuted, width: 36, textAlign: 'center' },
  progressTrack: {
    flex: 1, height: 4, backgroundColor: COLORS.cardBorder, borderRadius: 2, overflow: 'hidden',
  },
  progressFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: 2 },

  controls: {
    flexDirection: 'row', justifyContent: 'center', alignItems: 'center',
    paddingBottom: 48, paddingTop: 8, gap: 16,
  },
  ctrlBtn: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: COLORS.card,
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.cardBorder,
  },
  ctrlIcon: { fontSize: 22, color: COLORS.textPrimary },
  pauseBtn: {
    width: 68, height: 68, borderRadius: 34,
    backgroundColor: COLORS.primary,
    justifyContent: 'center', alignItems: 'center',
  },
  resumeBtn: {
    backgroundColor: '#2e7d32',
  },
  pauseIcon: { fontSize: 25, color: '#fff', fontWeight: '800' },
  finishBtn: {
    height: 48,
    minWidth: 104,
    borderRadius: 8,
    paddingHorizontal: 14,
    backgroundColor: '#c62828',
    justifyContent: 'center',
    alignItems: 'center',
  },
  finishText: { fontSize: 13, color: '#fff', fontWeight: '800' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.82)',
    justifyContent: 'center', alignItems: 'center', gap: 20,
  },
  countdownNum: { fontSize: 96, fontWeight: '800', color: '#fff' },
  resumeCountdownOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  resumeCountdownNum: {
    fontSize: 88,
    fontWeight: '800',
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.65)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },

  analyzeStepText: {
    fontSize: 20, fontWeight: '700', color: '#fff', marginTop: 8,
  },
  stepIndicators: { flexDirection: 'row', gap: 10 },
  stepDot: { width: 10, height: 10, borderRadius: 5 },
  stepDotActive:   { backgroundColor: COLORS.primary },
  stepDotInactive: { backgroundColor: COLORS.textMuted },
  analyzeHint: { fontSize: 13, color: COLORS.textSecondary },
});
