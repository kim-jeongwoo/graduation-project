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
import type { LyricLine, PitchPoint, PitchGuide } from '../../types/karaoke';
import {
  generateFakeUserPitch,
  getPitchAccuracy,
  midiToNoteName,
} from '../../types/karaoke';

// ─── Mock run_id for P1-A STOP → EvalResult ───
const MOCK_RUN_ID = 'c65d43fa-ef3f-4a46-a70e-c102c61eee6c';

// ─── Pitch graph constants ───
const SCREEN_W = Dimensions.get('window').width;
const GRAPH_W  = SCREEN_W;
const GRAPH_H  = 200;
const WINDOW_BEFORE_SEC = 3;
const WINDOW_AFTER_SEC  = 5;
const CURSOR_X = GRAPH_W * (WINDOW_BEFORE_SEC / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC));
const MIDI_MIN = 48;  // C3
const MIDI_MAX = 84;  // C6

function midiToY(midi: number): number {
  return GRAPH_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GRAPH_H;
}

function timeToX(t: number, currentTime: number): number {
  const relSec = t - currentTime;
  return CURSOR_X + (relSec / (WINDOW_BEFORE_SEC + WINDOW_AFTER_SEC)) * GRAPH_W;
}

// ─── Nav params ───
// KaraokeScreen lives in AppRootStack (above MainTabNavigator) so bottom tabs are hidden.
type AppRootParams = {
  MainTabs: undefined;
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
};
type Props = NativeStackScreenProps<AppRootParams, 'Karaoke'>;

// ─── Pitch graph component ───
interface PitchGraphProps {
  currentTime: number;
  guidePoints: PitchPoint[];
  userPoints: PitchPoint[];
}

function PitchGraph({ currentTime, guidePoints, userPoints }: PitchGraphProps) {
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

  // Build SVG <Path> elements, breaking the line at unvoiced gaps.
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
        result.push(
          <Path key={segKey++} d={d} stroke={segColor} strokeWidth={3}
                fill="none" strokeLinecap="round" strokeLinejoin="round" />,
        );
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

  const guidePaths = useMemo(
    () => buildPaths(visibleGuide, () => '#938ea1aa'),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [visibleGuide, currentTime],
  );

  const userPaths = useMemo(() => {
    if (visibleGuide.length === 0) return [];
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

  const latestUserMidi = useMemo(
    () => [...visibleUser].reverse().find((p) => p.midi !== null && p.voiced)?.midi ?? null,
    [visibleUser],
  );
  const nearestGuideMidi = useMemo(
    () => visibleGuide.find((p) => p.voiced && p.midi !== null && p.time >= currentTime)?.midi ?? null,
    [visibleGuide, currentTime],
  );

  const accuracy = latestUserMidi !== null && nearestGuideMidi !== null
    ? getPitchAccuracy(latestUserMidi, nearestGuideMidi)
    : null;
  const noteColor = accuracy === 'accurate' ? '#59dda5'
    : accuracy === 'slight_off' ? '#ffb780'
    : accuracy === 'wrong'      ? '#ffb4ab'
    : COLORS.textMuted;

  return (
    <View style={graphStyles.container}>
      <Svg width={GRAPH_W} height={GRAPH_H}>
        {guidePaths}
        {userPaths}
        <Line
          x1={CURSOR_X} y1={0} x2={CURSOR_X} y2={GRAPH_H}
          stroke={COLORS.primary} strokeWidth={1.5} strokeDasharray="4,3"
        />
      </Svg>
      {latestUserMidi !== null && (
        <View style={[graphStyles.noteBox, { borderColor: noteColor }]}>
          <Text style={[graphStyles.noteText, { color: noteColor }]}>
            {midiToNoteName(latestUserMidi)}
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

  const [loading, setLoading]         = useState(true);
  const [countdown, setCountdown]     = useState<number | null>(null);
  const [lyrics, setLyrics]           = useState<LyricLine[]>([]);
  const [pitchGuide, setPitchGuide]   = useState<PitchGuide | null>(null);
  const [userPitch, setUserPitch]     = useState<PitchPoint[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying]         = useState(false);

  const soundRef = useRef<Audio.Sound | null>(null);

  // ─── Load data ───
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { lyrics: lrc, pitchGuide: guide } = await getSongKaraokeData(songId);
        if (cancelled) return;
        // ─── [진단] pitch_guide 로드 확인 ───
        console.log('[KaraokeScreen] pitchGuide.points.length:', guide.points.length);
        console.log('[KaraokeScreen] durationSec:', guide.durationSec, 'frameHz:', guide.frameHz);
        console.log('[KaraokeScreen] first 3 points:', JSON.stringify(guide.points.slice(0, 3)));
        console.log('[KaraokeScreen] last  3 points:', JSON.stringify(guide.points.slice(-3)));
        const voicedCount = guide.points.filter((p) => p.voiced).length;
        const validTimeCount = guide.points.filter((p) => p.time !== null && p.time !== undefined).length;
        console.log('[KaraokeScreen] voiced:', voicedCount, '/ valid_time:', validTimeCount, '/ total:', guide.points.length);
        console.log('[KaraokeScreen] lrcOffsetSec:', guide.lrcOffsetSec);
        const fake = generateFakeUserPitch(guide.points);
        setLyrics(lrc);
        setPitchGuide(guide);
        setUserPitch(fake);
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
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  // ─── 진단: 현재 시간 및 윈도우 내 포인트 수 1초마다 로그 ───
  useEffect(() => {
    if (!pitchGuide) return;
    const iv = setInterval(() => {
      const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
      const hi = currentTime + WINDOW_AFTER_SEC  + 0.5;
      const visible = pitchGuide.points.filter((p) => p.time >= lo && p.time <= hi && p.voiced);
      console.log(`[KaraokeScreen] t=${currentTime.toFixed(2)}s  window=[${lo.toFixed(1)},${hi.toFixed(1)}]  voiced_visible=${visible.length}`);
    }, 1000);
    return () => clearInterval(iv);
  }, [pitchGuide, currentTime]);

  // ─── Countdown + auto-play ───
  const startCountdown = useCallback(() => {
    let n = 3;
    setCountdown(n);
    const iv = setInterval(() => {
      n -= 1;
      if (n <= 0) { clearInterval(iv); setCountdown(null); startMr(); }
      else setCountdown(n);
    }, 1000);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startMr = useCallback(async () => {
    try {
      await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
      const sound = new Audio.Sound();
      await sound.loadAsync(
        {
          uri: getSongMrUrl(songId),
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        },
        { shouldPlay: true, progressUpdateIntervalMillis: 80 },
      );
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded) {
          setCurrentTime(status.positionMillis / 1000);
          setPlaying(status.isPlaying);
        }
      });
      soundRef.current = sound;
      setPlaying(true);
    } catch (e) {
      console.error('[KaraokeScreen] MR load error:', e);
      Alert.alert('오류', 'MR 음원을 재생할 수 없습니다.');
    }
  }, [songId, token]);

  // ─── Controls ───
  const handlePause = useCallback(async () => {
    const s = soundRef.current;
    if (!s) return;
    const st = await s.getStatusAsync();
    if (st.isLoaded) { st.isPlaying ? await s.pauseAsync() : await s.playAsync(); }
  }, []);

  const handleRestart = useCallback(() => {
    Alert.alert('처음부터 다시 시작', '녹음이 초기화됩니다.', [
      { text: '취소', style: 'cancel' },
      {
        text: '확인',
        onPress: async () => {
          const s = soundRef.current;
          if (s) { await s.stopAsync(); await s.setPositionAsync(0); }
          setCurrentTime(0);
          if (pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
          startCountdown();
        },
      },
    ]);
  }, [pitchGuide, startCountdown]);

  // ─── Lyrics sync ───
  const currentLine = useMemo(
    () => lyrics.find((l) => l.timeStart <= currentTime && currentTime < l.timeEnd) ?? null,
    [lyrics, currentTime],
  );
  const nextLine = useMemo(
    () => lyrics.find((l) => l.timeStart > currentTime) ?? null,
    [lyrics, currentTime],
  );

  // ─── Progress ───
  // mrDurationSec from params is authoritative; fall back to last pitch point
  const totalSec = mrDurationSec > 0
    ? mrDurationSec
    : (pitchGuide?.points[pitchGuide.points.length - 1]?.time ?? 0);
  const progress = totalSec > 0 ? Math.min(currentTime / totalSec, 1) : 0;
  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // ─── EvalResult navigation helper (bubbles up through HomeStack) ───
  const goToEvalResult = useCallback((runId: string) => {
    // KaraokeScreen is in AppRootStack; navigate to HomeStack's EvalResult via nested params
    (navigation as any).navigate('MainTabs', {
      screen: 'HomeTab',
      params: { screen: 'EvalResult', params: { runId } },
    });
  }, [navigation]);

  const handleStopWithEval = useCallback(async () => {
    const s = soundRef.current;
    if (s) await s.stopAsync();
    goToEvalResult(MOCK_RUN_ID);
  }, [goToEvalResult]);

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
        <TouchableOpacity onPress={() => { soundRef.current?.stopAsync(); navigation.goBack(); }}>
          <Text style={styles.closeBtn}>✕</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{artist} - {title}</Text>
        <View style={{ width: 32 }} />
      </View>

      {/* 피치 그래프 */}
      {pitchGuide ? (
        <PitchGraph
          currentTime={currentTime}
          guidePoints={pitchGuide.points}
          userPoints={userPitch}
        />
      ) : (
        <View style={graphStyles.container} />
      )}

      {/* 가사 영역 — 고정 높이 */}
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

      {/* 컨트롤 */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.ctrlBtn} onPress={handleRestart}>
          <Text style={styles.ctrlIcon}>↻</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.stopBtn} onPress={handleStopWithEval}>
          <Text style={styles.stopIcon}>■</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.ctrlBtn} onPress={handlePause}>
          <Text style={styles.ctrlIcon}>{playing ? '⏸' : '▶'}</Text>
        </TouchableOpacity>
      </View>

      {/* 카운트다운 오버레이 */}
      {countdown !== null && (
        <View style={styles.countdownOverlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 52,
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  closeBtn: { fontSize: 20, color: COLORS.textSecondary, padding: 4 },
  headerTitle: {
    flex: 1, textAlign: 'center',
    fontSize: 15, fontWeight: '600', color: COLORS.textPrimary,
  },

  // Fixed-height lyrics block so it doesn't take up all remaining space
  lyricsArea: {
    height: 96,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    gap: 8,
    backgroundColor: COLORS.background,
  },
  currentLyric: {
    fontSize: 22,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
    lineHeight: 30,
  },
  nextLyric: {
    fontSize: 14,
    color: COLORS.textMuted,
    textAlign: 'center',
  },

  progressArea: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
    gap: 10,
  },
  timeText: { fontSize: 12, color: COLORS.textMuted, width: 36, textAlign: 'center' },
  progressTrack: {
    flex: 1, height: 4,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 2, overflow: 'hidden',
  },
  progressFill: {
    height: '100%', backgroundColor: COLORS.primary, borderRadius: 2,
  },

  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 48,
    paddingTop: 8,
    gap: 32,
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

  countdownOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.78)',
    justifyContent: 'center', alignItems: 'center',
  },
  countdownNum: { fontSize: 96, fontWeight: '800', color: '#fff' },
});
