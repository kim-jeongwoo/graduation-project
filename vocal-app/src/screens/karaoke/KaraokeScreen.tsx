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
import { getSongKaraokeData, getSongMrUrl } from '../../api/songs';
import { AnalyzeStatusError, createSession, uploadSessionFile, startAnalysis } from '../../api/sessions';
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
const ANALYZE_STEPS = ['녹음 업로드 중...', 'AI 분석 중...', '결과 정리 중...'];

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

  const userPaths = useMemo(() => {
    if (!visibleGuide.length) return [];
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
        {guideSource === 'midi' ? midiLines : guidePaths}
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
  const [userPitch, setUserPitch]         = useState<PitchPoint[]>([]);
  const [currentTime, setCurrentTime]     = useState(0);
  const [playing, setPlaying]             = useState(false);
  const [isAnalyzing, setIsAnalyzing]     = useState(false);
  const [analyzeStep, setAnalyzeStep]     = useState(0);

  const soundRef       = useRef<Audio.Sound | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const currentTimeRef = useRef(0);

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
          [{ text: '확인', onPress: () => navigation.goBack() }],
        );
        return;
      }

      // 2. Karaoke data
      try {
        const { lyrics: lrc, pitchGuide: guide } = await getSongKaraokeData(songId);
        if (cancelled) return;
        console.log('[KaraokeScreen] pitchGuide.points:', guide.points.length, 'voiced:', guide.points.filter(p => p.voiced).length);
        setLyrics(lrc);
        setPitchGuide(guide);
        if (!USE_REALTIME_PITCH) setUserPitch(generateFakeUserPitch(guide.points));
        setLoading(false);
        startCountdown();
      } catch (e) {
        console.error('[KaraokeScreen] load error:', e);
        Alert.alert('오류', '곡 데이터를 불러오지 못했습니다.', [
          { text: '닫기', onPress: () => navigation.goBack() },
        ]);
      }
    })();
    return () => {
      cancelled = true;
      soundRef.current?.unloadAsync();
      recorderRef.current.cancel();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  // ─── Countdown → MR + recording start ───
  const startCountdown = useCallback(() => {
    let n = 3;
    setCountdown(n);
    const iv = setInterval(() => {
      n -= 1;
      if (n <= 0) { clearInterval(iv); setCountdown(null); startMrAndRecord(); }
      else setCountdown(n);
    }, 1000);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startMrAndRecord = useCallback(async () => {
    try {
      if (!USE_MOCK) {
        await recorderRef.current.start(USE_REALTIME_PITCH ? (samples) => {
          const result = detectPitch(samples);
          const t = currentTimeRef.current;
          if (t < 0.1) return;
          setUserPitch((prev) => {
            const cutoff = t - 10;
            const trimmed = cutoff > 0 ? prev.filter((p) => p.time >= cutoff) : prev;
            if (!result.voiced || result.midi === null) return trimmed;
            return [...trimmed, { time: t, midi: result.midi, voiced: true, freqHz: result.freq, confidence: 1 }];
          });
        } : undefined);
      }
      const sound = new Audio.Sound();
      // ① 콜백 먼저 등록 (shouldPlay:true + loadAsync 완료 후 등록 시 초기 update 누락 방지)
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded) {
          currentTimeRef.current = status.positionMillis / 1000;
          setCurrentTime(status.positionMillis / 1000);
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
      soundRef.current = sound;
    } catch (e) {
      console.error('[KaraokeScreen] startMrAndRecord error:', e);
      Alert.alert('오류', 'MR 또는 녹음을 시작할 수 없습니다.');
    }
  }, [songId, token]);

  // ─── Restart ───
  const handleRestart = useCallback(() => {
    Alert.alert('처음부터 다시 시작', '녹음이 초기화됩니다.', [
      { text: '취소', style: 'cancel' },
      {
        text: '확인',
        onPress: async () => {
          const s = soundRef.current;
          if (s) { await s.stopAsync(); await s.setPositionAsync(0); }
          await recorderRef.current.cancel();
          setCurrentTime(0);
          currentTimeRef.current = 0;
          if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
          else setUserPitch([]);
          startCountdown();
        },
      },
    ]);
  }, [pitchGuide, startCountdown]);

  // ─── Close (X) — cancel without analysis ───
  const handleClose = useCallback(async () => {
    const s = soundRef.current;
    if (s) await s.stopAsync();
    await recorderRef.current.cancel();
    navigation.goBack();
  }, [navigation]);

  // ─── STOP → analyze → EvalResult ───
  const handleStop = useCallback(async () => {
    if (USE_MOCK) {
      const s = soundRef.current;
      if (s) await s.stopAsync();
      goToEvalResult(MOCK_RUN_ID);
      return;
    }

    const s = soundRef.current;
    if (s) await s.stopAsync();

    setIsAnalyzing(true);
    setAnalyzeStep(0);

    try {
      // Stop recording
      const { uri, fileName, mimeType } = await recorderRef.current.stop();
      console.log('[KaraokeScreen] recording uri:', uri, 'type:', mimeType);

      // Step 0: upload
      setAnalyzeStep(0);
      if (__DEV__) console.log('[handleStop] createSession...');
      const session = await createSession({ song_id: songId });
      if (__DEV__) console.log('[handleStop] session:', session.session_id);

      if (__DEV__) console.log('[handleStop] uploading:', fileName, mimeType, uri.slice(0, 60));
      await uploadSessionFile(session.session_id, uri, fileName, mimeType);
      if (__DEV__) console.log('[handleStop] upload done');

      // Step 1: analyze (full-song duration varies by song length and timeline chunks)
      setAnalyzeStep(1);
      if (__DEV__) console.log('[handleStop] startAnalysis...');
      const { run_id, status, reason } = await startAnalysis(session.session_id);
      if (__DEV__) console.log('[handleStop] analyze result:', { run_id, status, reason });

      if (status === 'no_voice') {
        Alert.alert(
          '음성이 감지되지 않았어요',
          '마이크가 정상 동작하는지, 노래를 부르셨는지 확인해주세요.',
          [
            {
              text: '다시 녹음',
              onPress: async () => {
                const snd = soundRef.current;
                if (snd) { try { await snd.unloadAsync(); } catch {} soundRef.current = null; }
                await recorderRef.current.cancel();
                setCurrentTime(0);
                currentTimeRef.current = 0;
                if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
                else setUserPitch([]);
                startCountdown();
              },
            },
            { text: '닫기', style: 'cancel', onPress: () => navigation.goBack() },
          ],
        );
        return;
      }

      if (status === 'failed' || status === 'invalid' || status === 'error') {
        throw new Error(`AI 분석에 실패했습니다. ${reason ?? '다시 시도해주세요.'}`);
      }

      // Step 2: brief done state
      setAnalyzeStep(2);
      await new Promise<void>((r) => setTimeout(r, 600));

      goToEvalResult(run_id);
    } catch (err: unknown) {
      if (err instanceof AnalyzeStatusError && err.status === 'no_voice') {
        Alert.alert(
          '음성이 감지되지 않았어요',
          err.message,
          [
            {
              text: '다시 녹음',
              onPress: async () => {
                const snd = soundRef.current;
                if (snd) { try { await snd.unloadAsync(); } catch {} soundRef.current = null; }
                await recorderRef.current.cancel();
                setCurrentTime(0);
                currentTimeRef.current = 0;
                if (!USE_REALTIME_PITCH && pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
                else setUserPitch([]);
                startCountdown();
              },
            },
            { text: '닫기', style: 'cancel', onPress: () => navigation.goBack() },
          ],
        );
        return;
      }
      if (err instanceof AnalyzeStatusError && __DEV__) {
        console.warn('[KaraokeScreen] analyze status failure:', {
          status: err.status,
          reason: err.reason,
          detail: err.detail,
        });
      }
      const msg = err instanceof Error ? err.message : '다시 시도해주세요.';
      Alert.alert('분석 실패', msg, [
        { text: '다시 시도', onPress: handleStop },
        { text: '닫기', onPress: () => navigation.goBack() },
      ]);
    } finally {
      setIsAnalyzing(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId, navigation]);

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

  // ─── Progress ───
  const totalSec = mrDurationSec > 0
    ? mrDurationSec
    : (pitchGuide?.points[pitchGuide.points.length - 1]?.time ?? 0);
  const progress = totalSec > 0 ? Math.min(currentTime / totalSec, 1) : 0;
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
          guidePoints={pitchGuide.points}
          userPoints={userPitch}
        />
      ) : (
        <View style={graphStyles.container} />
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

      {/* 컨트롤: ↻ 다시시작 | ■ STOP (일시정지는 P1-C에서 추가) */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.ctrlBtn} onPress={handleRestart}>
          <Text style={styles.ctrlIcon}>↻</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.stopBtn} onPress={handleStop}>
          <Text style={styles.stopIcon}>■</Text>
        </TouchableOpacity>
      </View>

      {/* 카운트다운 오버레이 */}
      {countdown !== null && (
        <View style={styles.overlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
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
    paddingBottom: 48, paddingTop: 8, gap: 32,
  },
  ctrlBtn: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: COLORS.card,
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.cardBorder,
  },
  ctrlIcon: { fontSize: 22, color: COLORS.textPrimary },
  stopBtn: {
    width: 68, height: 68, borderRadius: 34,
    backgroundColor: '#c62828',
    justifyContent: 'center', alignItems: 'center',
  },
  stopIcon: { fontSize: 26, color: '#fff' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.82)',
    justifyContent: 'center', alignItems: 'center', gap: 20,
  },
  countdownNum: { fontSize: 96, fontWeight: '800', color: '#fff' },

  analyzeStepText: {
    fontSize: 20, fontWeight: '700', color: '#fff', marginTop: 8,
  },
  stepIndicators: { flexDirection: 'row', gap: 10 },
  stepDot: { width: 10, height: 10, borderRadius: 5 },
  stepDotActive:   { backgroundColor: COLORS.primary },
  stepDotInactive: { backgroundColor: COLORS.textMuted },
  analyzeHint: { fontSize: 13, color: COLORS.textSecondary },
});
