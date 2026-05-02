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
import Svg, { Path, Line, Text as SvgText } from 'react-native-svg';
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
const GRAPH_W = SCREEN_W;
const GRAPH_H = 160;
const WINDOW_BEFORE_SEC = 3;   // seconds of history shown left of cursor
const WINDOW_AFTER_SEC  = 5;   // seconds of guide shown right of cursor
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
type HomeStackParams = {
  Home: undefined;
  SongDetail: { song: import('../../types/api').Song };
  Karaoke: { songId: string };
  EvalResult: { runId?: string };
};
type Props = NativeStackScreenProps<HomeStackParams, 'Karaoke'>;

// ─── Pitch graph component ───
interface PitchGraphProps {
  currentTime: number;
  guidePoints: PitchPoint[];
  userPoints: PitchPoint[];
}

function PitchGraph({ currentTime, guidePoints, userPoints }: PitchGraphProps) {
  // Filter visible guide points
  const visibleGuide = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    const hi = currentTime + WINDOW_AFTER_SEC + 0.5;
    return guidePoints.filter((p) => p.t >= lo && p.t <= hi);
  }, [guidePoints, currentTime]);

  // Filter visible user points (past only)
  const visibleUser = useMemo(() => {
    const lo = currentTime - WINDOW_BEFORE_SEC - 0.5;
    return userPoints.filter((p) => p.t >= lo && p.t <= currentTime && p.midi !== null && p.voiced);
  }, [userPoints, currentTime]);

  // Build SVG path string from points, breaking on unvoiced gaps
  function buildPath(points: PitchPoint[], color: (p: PitchPoint, prev: PitchPoint | null) => string): React.ReactNode[] {
    const paths: React.ReactNode[] = [];
    let segment: PitchPoint[] = [];
    let segmentColor = color(points[0] ?? { t: 0, midi: null, voiced: false, freq: null, conf: 0 }, null);

    const flush = (idx: number) => {
      if (segment.length < 2) { segment = []; return; }
      const d = segment.map((p, i) => {
        const x = timeToX(p.t, currentTime);
        const y = midiToY(p.midi!);
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(' ');
      paths.push(<Path key={`path-${idx}`} d={d} stroke={segmentColor} strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      segment = [];
    };

    points.forEach((p, i) => {
      if (!p.voiced || p.midi === null) {
        flush(i);
        return;
      }
      const c = color(p, segment[segment.length - 1] ?? null);
      if (segment.length > 0 && c !== segmentColor) {
        flush(i);
        segmentColor = c;
      } else {
        segmentColor = c;
      }
      segment.push(p);
    });
    flush(points.length);
    return paths;
  }

  // Guide path (single gray color)
  const guidePaths = useMemo(() => {
    if (visibleGuide.length === 0) return null;
    return buildPath(visibleGuide, () => '#938ea199');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleGuide]);

  // User path (color per accuracy vs nearest guide)
  const userPaths = useMemo(() => {
    if (visibleUser.length === 0 || visibleGuide.length === 0) return null;
    return buildPath(visibleUser, (p) => {
      const nearby = visibleGuide.reduce<PitchPoint | null>((best, g) => {
        if (!g.voiced || g.midi === null) return best;
        if (!best) return g;
        return Math.abs(g.t - p.t) < Math.abs(best.t - p.t) ? g : best;
      }, null);
      if (!nearby || nearby.midi === null || p.midi === null) return COLORS.textMuted;
      const acc = getPitchAccuracy(p.midi, nearby.midi);
      if (acc === 'accurate')   return '#59dda5';
      if (acc === 'slight_off') return '#ffb780';
      return '#ffb4ab';
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleUser, visibleGuide]);

  // Current user midi for note display
  const latestUserMidi = useMemo(() => {
    const last = [...visibleUser].reverse().find((p) => p.midi !== null && p.voiced);
    return last?.midi ?? null;
  }, [visibleUser]);

  // Nearest guide midi
  const nearestGuideMidi = useMemo(() => {
    const g = visibleGuide.find((p) => p.voiced && p.midi !== null && p.t >= currentTime);
    return g?.midi ?? null;
  }, [visibleGuide, currentTime]);

  const accuracy = latestUserMidi !== null && nearestGuideMidi !== null
    ? getPitchAccuracy(latestUserMidi, nearestGuideMidi)
    : null;
  const accuracyColor = accuracy === 'accurate' ? '#59dda5' : accuracy === 'slight_off' ? '#ffb780' : accuracy === 'wrong' ? '#ffb4ab' : COLORS.textMuted;

  return (
    <View style={graphStyles.container}>
      <Svg width={GRAPH_W} height={GRAPH_H}>
        {/* Guide paths */}
        {guidePaths}
        {/* User paths */}
        {userPaths}
        {/* Cursor line */}
        <Line
          x1={CURSOR_X} y1={0}
          x2={CURSOR_X} y2={GRAPH_H}
          stroke={COLORS.primary}
          strokeWidth={2}
          strokeDasharray="4,3"
        />
      </Svg>
      {/* Current note display */}
      {latestUserMidi !== null && (
        <View style={[graphStyles.noteBox, { borderColor: accuracyColor }]}>
          <Text style={[graphStyles.noteText, { color: accuracyColor }]}>
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
    position: 'absolute',
    top: 8,
    right: 12,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1.5,
    backgroundColor: COLORS.card,
  },
  noteText: { fontSize: 13, fontWeight: '700' },
});

// ─── Main screen ───
export default function KaraokeScreen({ navigation, route }: Props) {
  const { songId } = route.params;
  const { token } = useAuth();

  const [loading, setLoading]       = useState(true);
  const [countdown, setCountdown]   = useState<number | null>(null);
  const [lyrics, setLyrics]         = useState<LyricLine[]>([]);
  const [pitchGuide, setPitchGuide] = useState<PitchGuide | null>(null);
  const [userPitch, setUserPitch]   = useState<PitchPoint[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying]       = useState(false);

  const soundRef = useRef<Audio.Sound | null>(null);

  // ─── Load data ───
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { lyrics: lrc, pitchGuide: guide } = await getSongKaraokeData(songId);
        if (cancelled) return;
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

  // ─── Countdown + auto-play ───
  const startCountdown = useCallback(() => {
    let n = 3;
    setCountdown(n);
    const iv = setInterval(() => {
      n -= 1;
      if (n <= 0) {
        clearInterval(iv);
        setCountdown(null);
        startMr();
      } else {
        setCountdown(n);
      }
    }, 1000);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const startMr = useCallback(async () => {
    try {
      await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
      const sound = new Audio.Sound();
      const mrUrl = getSongMrUrl(songId);
      await sound.loadAsync(
        { uri: mrUrl, headers: token ? { Authorization: `Bearer ${token}` } : {} },
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
    const status = await s.getStatusAsync();
    if (status.isLoaded) {
      if (status.isPlaying) await s.pauseAsync();
      else await s.playAsync();
    }
  }, []);

  const handleRestart = useCallback(() => {
    Alert.alert('처음부터 다시 시작', '녹음이 초기화됩니다.', [
      { text: '취소', style: 'cancel' },
      {
        text: '확인',
        onPress: async () => {
          const s = soundRef.current;
          if (s) {
            await s.stopAsync();
            await s.setPositionAsync(0);
          }
          setCurrentTime(0);
          if (pitchGuide) setUserPitch(generateFakeUserPitch(pitchGuide.points));
          startCountdown();
        },
      },
    ]);
  }, [pitchGuide, startCountdown]);

  const handleStop = useCallback(async () => {
    const s = soundRef.current;
    if (s) await s.stopAsync();
    navigation.replace('EvalResult', { runId: MOCK_RUN_ID });
  }, [navigation]);

  // ─── Lyrics sync ───
  const currentLine = useMemo(
    () => lyrics.find((l) => l.timeStart <= currentTime && currentTime < l.timeEnd) ?? null,
    [lyrics, currentTime],
  );
  const nextLine = useMemo(
    () => lyrics.find((l) => l.timeStart > currentTime) ?? null,
    [lyrics, currentTime],
  );

  // ─── Progress bar ───
  const totalSec = pitchGuide ? (pitchGuide.points[pitchGuide.points.length - 1]?.t ?? 0) : 0;
  const progress = totalSec > 0 ? Math.min(currentTime / totalSec, 1) : 0;
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

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
        <Text style={styles.headerTitle} numberOfLines={1}>김범수 - 보고싶다</Text>
        <View style={{ width: 32 }} />
      </View>

      {/* 피치 그래프 */}
      {pitchGuide && (
        <PitchGraph
          currentTime={currentTime}
          guidePoints={pitchGuide.points}
          userPoints={userPitch}
        />
      )}

      {/* 가사 영역 */}
      <View style={styles.lyricsArea}>
        <Text style={styles.currentLyric}>{currentLine?.text ?? ''}</Text>
        <Text style={styles.nextLyric}>{nextLine?.text ?? ''}</Text>
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
        <TouchableOpacity style={styles.stopBtn} onPress={handleStop}>
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
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background, gap: 16 },
  loadingText: { color: COLORS.textSecondary, fontSize: 14 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 56,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  closeBtn: { fontSize: 20, color: COLORS.textSecondary, padding: 4 },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 15, fontWeight: '600', color: COLORS.textPrimary },

  lyricsArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    gap: 10,
  },
  currentLyric: {
    fontSize: 24,
    fontWeight: '700',
    color: COLORS.textPrimary,
    textAlign: 'center',
    lineHeight: 34,
  },
  nextLyric: {
    fontSize: 16,
    color: COLORS.textMuted,
    textAlign: 'center',
  },

  progressArea: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 12,
    gap: 10,
  },
  timeText: { fontSize: 12, color: COLORS.textMuted, width: 36, textAlign: 'center' },
  progressTrack: {
    flex: 1,
    height: 4,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 2,
  },

  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 44,
    gap: 32,
  },
  ctrlBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.card,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
  },
  ctrlIcon: { fontSize: 22, color: COLORS.textPrimary },
  stopBtn: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: '#c62828',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stopIcon: { fontSize: 26, color: '#fff' },

  countdownOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.72)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  countdownNum: {
    fontSize: 96,
    fontWeight: '800',
    color: '#fff',
  },
});
