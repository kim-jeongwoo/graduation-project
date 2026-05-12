import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Audio } from 'expo-av';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { IndicatorAppKey, INDICATOR_LABELS, ZONE_LABELS } from '../../domain/weakSections';
import type { Zone } from '../../types/analyze';

// 이슈 3 — 사후 측정 결과 zone별 피드백 텍스트 (클라이언트 hardcode, 5/10 임시)
const FEEDBACK_BY_ZONE: Record<IndicatorAppKey, Record<Zone, string>> = {
  breathiness: {
    insufficient: '호흡 소리 지표가 낮게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
    appropriate:  '호흡 소리 지표가 적절 범위로 측정됐습니다.',
    excessive:    '호흡 소리 지표가 높게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
  },
  vocal_fold_contact: {
    insufficient: '성대 접촉 강도 지표가 낮게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
    appropriate:  '성대 접촉 강도 지표가 적절 범위로 측정됐습니다.',
    excessive:    '성대 접촉 강도 지표가 높게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
  },
  soft_palate: {
    insufficient: '연구개 위치 지표가 낮게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
    appropriate:  '연구개 위치 지표가 적절 범위로 측정됐습니다.',
    excessive:    '연구개 위치 지표가 높게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
  },
  tongue_tension: {
    insufficient: '혀/구강 공간 경직도 지표가 낮게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
    appropriate:  '혀/구강 공간 경직도 지표가 적절 범위로 측정됐습니다.',
    excessive:    '혀/구강 공간 경직도 지표가 높게 측정됐습니다. 같은 구간을 다시 부르며 변화를 확인해보세요.',
  },
};

const SERVER_INDICATOR_KEY: Record<IndicatorAppKey, string> = {
  breathiness:         '4_breathiness',
  vocal_fold_contact:  '3_vocal_fold_contact',
  soft_palate:         '6_soft_palate',
  tongue_tension:      '8_tongue_tension',
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? value as Record<string, unknown> : null;
}

function parseJsonRecord(value: string | undefined): Record<string, unknown> | null {
  if (!value) return null;
  try {
    return asRecord(JSON.parse(value));
  } catch {
    return null;
  }
}

function getApiErrorInfo(error: unknown) {
  const err = asRecord(error);
  const response = asRecord(err?.response);
  const responseData = asRecord(response?.data);
  const parsedMessage = parseJsonRecord(error instanceof Error ? error.message : undefined);
  const parsedDetail = asRecord(parsedMessage?.detail) ?? parsedMessage;
  const detail = asRecord(responseData?.detail) ?? parsedDetail;
  const responseStatus = response?.status;
  const errorStatus = err?.status;
  const code = typeof responseStatus === 'number'
    ? responseStatus
    : (typeof errorStatus === 'number' ? errorStatus : undefined);
  return {
    code,
    detail,
    message: error instanceof Error ? error.message : undefined,
  };
}

function getStringDetail(detail: Record<string, unknown> | null, key: string): string | null {
  const value = detail?.[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

import type { MidiSegment, PitchPoint } from '../../types/karaoke';
import { getSongMidiSegmentsRaw, getSongMrUrl } from '../../api/songs';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { VocalRecorder } from '../../services/audio/recorder';
import { detectPitch } from '../../services/audio/pitchDetector';
import { requestMicrophonePermission } from '../../services/audio/microphone';
import { useAuth } from '../../context/AuthContext';
import SectionPitchGraph from '../../components/training/SectionPitchGraph';
import {
  PitchCard,
  BreathCard,
  BreathInfoCard,
  SoftPalateInfoCard,
  TongueTensionInfoCard,
  pitchVerdictFromScore,
  type PitchVerdict,
} from '../../components/training/RealtimeFeedback';
import { buildRealtimeWsUrl } from '../../api/dmlClient';
import { trainingAnalyze, type TrainingAnalyzeResponse } from '../../api/sessions';
import ResultCard, { type BeforeAfterScore } from '../../components/training/ResultCard';

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

function getKeyedValue<T>(
  record: Record<string, T> | null | undefined,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): T | undefined {
  return record?.[serverIndicatorKey] ?? record?.[indicatorKey];
}

function getTrainingAnalyzeScore(
  res: TrainingAnalyzeResponse,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): BeforeAfterScore | null {
  const legacy = getKeyedValue(res.scores, indicatorKey, serverIndicatorKey);
  if (legacy) {
    return { aiScore: legacy.ai_score, zone: legacy.zone as Zone };
  }

  const meta = getKeyedValue(res.scores_meta, indicatorKey, serverIndicatorKey);
  const roundedScore = typeof meta?.rounded_score === 'number'
    ? meta.rounded_score
    : getKeyedValue(res.scores_v2, indicatorKey, serverIndicatorKey);
  if (typeof roundedScore !== 'number') return null;
  return { aiScore: roundedScore, zone: deriveZoneFromRoundedScore(roundedScore) };
}

function hasLowConfidenceItem(
  items: string[] | null | undefined,
  indicatorKey: IndicatorAppKey,
  serverIndicatorKey: string,
): boolean {
  return items?.some((item) => {
    const stripped = item.replace(/^\d+_/, '');
    return item === serverIndicatorKey || item === indicatorKey || stripped === indicatorKey;
  }) ?? false;
}

type Props = NativeStackScreenProps<
  {
    Training: {
      indicatorKey:    IndicatorAppKey;
      runId?:          string;
      songId?:         string;
      sessionId?:      string;
      chunkIndex?:     number;
      sectionStartSec: number;  // master time, padded
      sectionEndSec:   number;  // master time
      chunkInfo:       { startSec: number; endSec: number; lrcText: string };
      scoreInfo:       { aiScore: number; zone: Zone };
      lowConfidenceItems?: string[];
      feedbackText:    string;
    };
  },
  'Training'
>;

export default function TrainingScreen({ route }: Props) {
  const {
    indicatorKey, runId, songId, sessionId, chunkIndex,
    sectionStartSec, sectionEndSec,
    chunkInfo, scoreInfo, lowConfidenceItems, feedbackText,
  } = route.params;
  const indicatorLabel = INDICATOR_LABELS[indicatorKey];
  const { token } = useAuth();

  const [loading,      setLoading]      = useState(true);
  const [errorMsg,     setErrorMsg]     = useState<string | null>(null);
  const [midiSegments, setMidiSegments] = useState<MidiSegment[]>([]);
  const [lrcOffsetSec, setLrcOffsetSec] = useState(0);
  const [currentTime,  setCurrentTime]  = useState(sectionStartSec);  // master time
  const [playing,      setPlaying]      = useState(false);
  const [countdown,    setCountdown]    = useState<number | null>(null);
  const [userPitch,    setUserPitch]    = useState<PitchPoint[]>([]);

  // 실시간 피드백 state (Phase 3)
  const [pitchMatchScore, setPitchMatchScore] = useState<number | null>(null);
  const [pitchVerdict,    setPitchVerdict]    = useState<PitchVerdict>('unknown');
  const [breathZone,      setBreathZone]      = useState<Zone | null>(null);
  const [breathScore,     setBreathScore]     = useState<number | null>(null);

  // 사후 측정 state (Phase 4-2)
  type Status = 'idle' | 'countdown' | 'recording' | 'stopped' | 'analyzing' | 'result';
  const [status,         setStatus]        = useState<Status>('idle');
  const [recordedUri,    setRecordedUri]   = useState<string | null>(null);
  const [afterScore,     setAfterScore]    = useState<BeforeAfterScore | null>(null);
  const [afterLowConfidence, setAfterLowConfidence] = useState(false);

  const serverIndicatorKey = SERVER_INDICATOR_KEY[indicatorKey];
  const beforeLowConfidence = lowConfidenceItems?.includes(serverIndicatorKey) ?? false;
  const canAnalyze = !!sessionId && !!recordedUri;

  const soundRef       = useRef<Audio.Sound | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const currentTimeRef = useRef(sectionStartSec);  // master time
  const stoppedRef     = useRef(false);
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket + PCM buffering refs (Phase 3)
  const wsRef          = useRef<WebSocket | null>(null);
  const wsReadyRef     = useRef(false);
  const pcmBufferRef   = useRef<number[]>([]);
  const pitchHistRef   = useRef<PitchVerdict[]>([]);  // 최근 5프레임 다수결

  // ─── songId 기반 midi/offset 로드 ───
  useEffect(() => {
    let cancelled = false;
    if (!songId) {
      setErrorMsg('songId가 없어 가이드라인을 표시할 수 없습니다.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const granted = await requestMicrophonePermission();
        if (!granted) {
          Alert.alert('마이크 권한 필요', '훈련하려면 마이크 권한이 필요합니다.');
        }
        const { segments, lrcOffsetSec: off } = await getSongMidiSegmentsRaw(songId);
        if (cancelled) return;
        const guideOffset = SONG_GUIDE_OFFSETS[songId] ?? 0;
        const adjusted: MidiSegment[] = segments.map(s => ({
          start:    s.start + guideOffset,
          end:      s.end   + guideOffset,
          midi:     s.midi,
          noteName: '',
        }));
        setMidiSegments(adjusted);
        setLrcOffsetSec(off);
        setLoading(false);
      } catch (e) {
        console.error('[TrainingScreen] load error:', e);
        if (!cancelled) {
          setErrorMsg('곡 데이터를 불러오지 못했습니다.');
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      cleanup();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  // ─── WebSocket 종료 ───
  const closeWs = useCallback(() => {
    const ws = wsRef.current;
    wsReadyRef.current = false;
    pcmBufferRef.current = [];
    if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
      try { ws.close(); } catch {}
    }
    wsRef.current = null;
  }, []);

  // ─── 정리 (언마운트/정지) ───
  const cleanup = useCallback(async () => {
    stoppedRef.current = true;
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
    }
    closeWs();
    const s = soundRef.current;
    if (s) {
      try { await s.unloadAsync(); } catch {}
      soundRef.current = null;
    }
    try { await recorderRef.current.cancel(); } catch {}
  }, [closeWs]);

  // ─── WebSocket 연결 (1회 재시도) ───
  const openWs = useCallback((retried = false): Promise<WebSocket | null> => {
    return new Promise((resolve) => {
      if (!songId) { resolve(null); return; }
      const url = buildRealtimeWsUrl(songId);
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';
      let resolved = false;
      ws.onopen = () => {
        wsReadyRef.current = true;
        // meta 송신
        try {
          ws.send(JSON.stringify({
            type: 'meta',
            sample_rate: 16000,
            start_timestamp: sectionStartSec,
          }));
        } catch (e) {
          console.error('[TrainingScreen] meta send error:', e);
        }
        if (!resolved) { resolved = true; resolve(ws); }
      };
      ws.onmessage = (ev) => {
        if (typeof ev.data !== 'string') return;
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'pitch_match') {
            // 사용자 음성 없음 (user_midi=null) → 게이지 리셋, history 비움
            if (msg.user_midi === null || msg.user_midi === undefined) {
              setPitchMatchScore(null);
              setPitchVerdict('unknown');
              pitchHistRef.current = [];
              return;
            }
            const score: number | null = msg.match_score ?? null;
            setPitchMatchScore(score);
            const v = pitchVerdictFromScore(score);
            const hist = pitchHistRef.current;
            hist.push(v);
            if (hist.length > 5) hist.shift();
            // 다수결
            const counts: Record<string, number> = {};
            for (const x of hist) counts[x] = (counts[x] ?? 0) + 1;
            let majority: PitchVerdict = 'unknown', best = 0;
            for (const k of Object.keys(counts)) {
              if (counts[k] > best) { best = counts[k]; majority = k as PitchVerdict; }
            }
            setPitchVerdict(majority);
          } else if (msg.type === 'breathiness_chunk') {
            setBreathZone((msg.zone ?? null) as Zone | null);
            setBreathScore(msg.ai_score ?? null);
          }
        } catch (e) {
          console.error('[TrainingScreen] ws message parse error:', e);
        }
      };
      ws.onerror = (e) => {
        console.error('[TrainingScreen] ws error:', e);
      };
      ws.onclose = () => {
        wsReadyRef.current = false;
        if (!resolved) {
          resolved = true;
          if (!retried) {
            console.log('[TrainingScreen] ws first connect failed, retrying...');
            openWs(true).then(resolve);
          } else {
            Alert.alert('연결 실패', '실시간 분석 서버에 연결할 수 없습니다.');
            resolve(null);
          }
        }
      };
    });
  }, [songId, sectionStartSec]);

  // ─── MR + recorder 시작 ───
  const startMrAndRecord = useCallback(async () => {
    if (!songId) return;
    const mrStart = Math.max(0, sectionStartSec - lrcOffsetSec);  // MR time
    const mrEnd   = Math.max(0, sectionEndSec   - lrcOffsetSec);
    stoppedRef.current = false;
    setStatus('recording');

    // WebSocket 연결 (실패 시 음성 분석 없이 진행)
    const ws = await openWs();
    wsRef.current = ws;

    try {
      // recorder
      await recorderRef.current.start((samples) => {
        // ── 로컬 피치 (기존) ──
        const result = detectPitch(samples);
        const t = currentTimeRef.current;
        if (result.voiced && result.midi !== null) {
          setUserPitch(prev => [...prev, {
            time: t, midi: result.midi, voiced: true,
            freqHz: result.freq, confidence: 1,
          }]);
        }
        // ── PCM buffering → 200ms(3200 samples) 단위로 WS 송신 ──
        const buf = pcmBufferRef.current;
        for (let i = 0; i < samples.length; i++) buf.push(samples[i]);
        while (buf.length >= 3200) {
          const chunk = buf.splice(0, 3200);
          if (wsReadyRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
            const int16 = new Int16Array(3200);
            for (let i = 0; i < 3200; i++) {
              const v = Math.round(chunk[i] * 32768);
              int16[i] = v < -32768 ? -32768 : v > 32767 ? 32767 : v;
            }
            try { wsRef.current.send(int16.buffer); } catch (e) {
              console.error('[TrainingScreen] ws send error:', e);
            }
          }
        }
      });

      // MR sound
      const sound = new Audio.Sound();
      sound.setOnPlaybackStatusUpdate((status) => {
        if (!status.isLoaded) return;
        const mrPos = status.positionMillis / 1000;
        const masterPos = mrPos + lrcOffsetSec;
        currentTimeRef.current = masterPos;
        setCurrentTime(masterPos);
        setPlaying(status.isPlaying);
        // 자동 정지: 구간 끝 도달
        if (!stoppedRef.current && mrPos >= mrEnd) {
          stoppedRef.current = true;
          (async () => {
            try { await sound.pauseAsync(); } catch {}
            try {
              const result = await recorderRef.current.stop();
              setRecordedUri(result.uri);
            } catch (e) {
              console.error('[TrainingScreen] recorder.stop (auto) error:', e);
            }
            closeWs();
            setPlaying(false);
            setStatus('stopped');
          })();
        }
      });
      await sound.loadAsync(
        { uri: getSongMrUrl(songId), headers: token ? { Authorization: `Bearer ${token}` } : {} },
        { shouldPlay: false, progressUpdateIntervalMillis: 50 },
      );
      await sound.playFromPositionAsync(mrStart * 1000);
      soundRef.current = sound;
    } catch (e) {
      console.error('[TrainingScreen] startMrAndRecord error:', e);
      Alert.alert('오류', 'MR 또는 녹음을 시작할 수 없습니다.');
      stoppedRef.current = true;
      closeWs();
      setStatus('idle');
    }
  }, [songId, sectionStartSec, sectionEndSec, lrcOffsetSec, token, openWs, closeWs]);

  // ─── 사후 측정 ───
  const handleAnalyze = useCallback(async () => {
    if (!sessionId || !recordedUri) {
      Alert.alert('알림', '녹음 데이터 또는 세션 정보가 없습니다.');
      return;
    }
    setStatus('analyzing');
    setAfterLowConfidence(false);
    const chunkMeta = {
      chunk_index: chunkIndex,
      start_sec: chunkInfo.startSec,
      end_sec: chunkInfo.endSec,
      original_run_id: runId,
    };
    try {
      const res = await trainingAnalyze(sessionId, recordedUri, chunkMeta);
      if (res.status === 'no_voice') {
        Alert.alert('음성 미감지', res.reason ?? '음성이 감지되지 않았습니다.');
        setStatus('stopped');
        return;
      }
      if (res.status !== 'success') {
        Alert.alert('분석 실패', res.reason ?? '분석에 실패했습니다.');
        setStatus('stopped');
        return;
      }
      const after = getTrainingAnalyzeScore(res, indicatorKey, serverIndicatorKey);
      if (!after) {
        Alert.alert('분석 결과 없음', '진입 항목 점수가 응답에 없습니다.');
        setStatus('stopped');
        return;
      }
      setAfterScore(after);
      setAfterLowConfidence(hasLowConfidenceItem(res.low_confidence_items, indicatorKey, serverIndicatorKey));
      setStatus('result');
    } catch (e: unknown) {
      const { code, detail, message } = getApiErrorInfo(e);
      const detailError = getStringDetail(detail, 'error');
      const detailReason = getStringDetail(detail, 'reason');
      if (code === 400 && detailError === 'chunk_too_short') {
        Alert.alert('녹음 너무 짧음', detailReason ?? '최소 3초 이상 녹음이 필요합니다.');
      } else if (code === 401) {
        Alert.alert('인증 만료', '다시 로그인해주세요.');
      } else if (code === 403) {
        Alert.alert('권한 없음', '다른 사용자의 세션입니다.');
      } else if (code === 404) {
        Alert.alert('세션 없음', '세션이 만료되었습니다.');
      } else if (code === 504) {
        Alert.alert('서버 응답 지연', '잠시 후 다시 시도해주세요.');
      } else if (code) {
        Alert.alert('분석 실패', message ?? '분석에 실패했습니다.');
        console.error('[TrainingScreen] trainingAnalyze error:', e);
      } else {
        Alert.alert('네트워크 오류', '네트워크를 확인하고 다시 시도해주세요.');
        console.error('[TrainingScreen] trainingAnalyze error:', e);
      }
      setStatus('stopped');
    }
  }, [sessionId, recordedUri, chunkIndex, chunkInfo, runId, serverIndicatorKey]);

  const handleRetry = useCallback(() => {
    setStatus('idle');
    setAfterScore(null);
    setAfterLowConfidence(false);
    setRecordedUri(null);
  }, []);

  // ─── 카운트다운 → 시작 ───
  const startCountdown = useCallback(() => {
    setUserPitch([]);
    setCurrentTime(sectionStartSec);
    currentTimeRef.current = sectionStartSec;
    // 실시간 피드백 리셋
    setPitchMatchScore(null);
    setPitchVerdict('unknown');
    setBreathZone(null);
    setBreathScore(null);
    pitchHistRef.current = [];
    pcmBufferRef.current = [];
    // 사후 측정 리셋
    setRecordedUri(null);
    setAfterScore(null);
    setAfterLowConfidence(false);
    setStatus('countdown');
    let n = 3;
    setCountdown(n);
    countdownTimer.current = setInterval(() => {
      n -= 1;
      if (n <= 0) {
        if (countdownTimer.current) clearInterval(countdownTimer.current);
        countdownTimer.current = null;
        setCountdown(null);
        startMrAndRecord();
      } else {
        setCountdown(n);
      }
    }, 1000);
  }, [sectionStartSec, startMrAndRecord]);

  // ─── 사용자 액션 ───
  const handleStart = useCallback(() => {
    if (countdown !== null || playing) return;
    startCountdown();
  }, [countdown, playing, startCountdown]);

  const handleStop = useCallback(async () => {
    const wasRecording = !stoppedRef.current && playing;
    stoppedRef.current = true;
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
      setCountdown(null);
    }
    const s = soundRef.current;
    if (s) {
      try { await s.pauseAsync(); } catch {}
    }
    if (wasRecording) {
      try {
        const result = await recorderRef.current.stop();
        setRecordedUri(result.uri);
      } catch (e) {
        console.error('[TrainingScreen] recorder.stop (manual) error:', e);
      }
    } else {
      try { await recorderRef.current.cancel(); } catch {}
    }
    closeWs();
    setPlaying(false);
    setStatus(wasRecording ? 'stopped' : 'idle');
  }, [closeWs, playing]);

  const handleRestart = useCallback(async () => {
    await handleStop();
    const s = soundRef.current;
    if (s) {
      try { await s.unloadAsync(); } catch {}
      soundRef.current = null;
    }
    startCountdown();
  }, [handleStop, startCountdown]);

  // ─── Loading / Error ───
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>곡 데이터 로딩 중...</Text>
      </View>
    );
  }
  if (errorMsg) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{errorMsg}</Text>
      </View>
    );
  }

  const isActive    = status === 'countdown' || status === 'recording';
  const isAnalyzing = status === 'analyzing';
  const showResult  = status === 'result' && afterScore !== null;
  const indicatorFeedbackCard =
    indicatorKey === 'breathiness' ? (
      <BreathCard zone={breathZone} aiScore={breathScore} />
    ) : indicatorKey === 'vocal_fold_contact' ? (
      <BreathInfoCard />
    ) : indicatorKey === 'soft_palate' ? (
      <SoftPalateInfoCard />
    ) : (
      <TongueTensionInfoCard />
    );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: SPACING.xl }}>
        <Text style={styles.title}>{indicatorLabel} 훈련</Text>

        <View style={styles.infoBox}>
          <Text style={styles.label}>구간</Text>
          <Text style={styles.value}>
            {chunkInfo.startSec.toFixed(1)}초 ~ {chunkInfo.endSec.toFixed(1)}초
            {'  '}(연습: {sectionStartSec.toFixed(1)}초 ~ {sectionEndSec.toFixed(1)}초)
          </Text>

          <Text style={styles.label}>가사</Text>
          <Text style={styles.value}>{chunkInfo.lrcText.trim() || '(가사 없음)'}</Text>

          <Text style={styles.label}>현재 점수</Text>
          <Text style={styles.value}>
            {scoreInfo.aiScore.toFixed(2)}점 / {ZONE_LABELS[scoreInfo.zone]}
          </Text>
        </View>

        <SectionPitchGraph
          midiSegments={midiSegments}
          startSec={sectionStartSec}
          endSec={sectionEndSec}
          originalStartSec={chunkInfo.startSec}
          originalEndSec={chunkInfo.endSec}
          currentTimeSec={currentTime}
          userPitch={userPitch}
        />

        {/* 실시간 피드백 (Phase 3) */}
        <View style={{ marginTop: SPACING.base }}>
          <PitchCard verdict={pitchVerdict} matchScore={pitchMatchScore} />
          {indicatorFeedbackCard}
        </View>

        <View style={styles.feedbackBox}>
          <Text style={styles.label}>피드백</Text>
          <Text style={styles.feedbackText}>
            {afterScore
              ? FEEDBACK_BY_ZONE[indicatorKey][afterScore.zone]
              : (feedbackText || '(피드백 없음)')}
          </Text>
        </View>

        {/* 사후 측정 결과 카드 */}
        {showResult && afterScore && (
          <ResultCard
            before={{ aiScore: scoreInfo.aiScore, zone: scoreInfo.zone }}
            after={afterScore}
            beforeLowConfidence={beforeLowConfidence}
            afterLowConfidence={afterLowConfidence}
          />
        )}

        <View style={styles.btnArea}>
          {isActive ? (
            <TouchableOpacity style={[styles.bigBtn, styles.stopBtn]} onPress={handleStop}>
              <Text style={styles.bigBtnText}>정지</Text>
            </TouchableOpacity>
          ) : isAnalyzing ? (
            <View style={[styles.bigBtn, styles.analyzingBtn]}>
              <ActivityIndicator color="#ffffff" />
              <Text style={[styles.bigBtnText, { marginTop: 4 }]}>점수 계산 중...</Text>
            </View>
          ) : status === 'stopped' ? (
            <View style={{ gap: SPACING.sm }}>
              {canAnalyze && (
                <TouchableOpacity style={[styles.bigBtn, styles.analyzeBtn]} onPress={handleAnalyze}>
                  <Text style={styles.bigBtnText}>이번 시도 점수 보기</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleStart}>
                <Text style={styles.bigBtnText}>구간 재시작</Text>
              </TouchableOpacity>
            </View>
          ) : showResult ? (
            <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleRetry}>
              <Text style={styles.bigBtnText}>다시 시도</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleStart}>
              <Text style={styles.bigBtnText}>구간 재시작</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>

      {countdown !== null && (
        <View style={styles.overlay}>
          <Text style={styles.countdownNum}>{countdown}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:        { flex: 1, backgroundColor: COLORS.background },
  center:           { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background, gap: SPACING.sm },
  loadingText:      { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:        { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center', paddingHorizontal: 24 },
  title:            { ...TYPOGRAPHY.heading, color: COLORS.textPrimary, padding: SPACING.base },
  infoBox:          { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginHorizontal: SPACING.base, marginBottom: SPACING.base },
  label:            { fontSize: 11, color: COLORS.textSecondary, marginTop: SPACING.sm, marginBottom: 2 },
  value:            { ...TYPOGRAPHY.body, color: COLORS.textPrimary },
  feedbackBox:      { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.base, marginHorizontal: SPACING.base, marginTop: SPACING.base, marginBottom: SPACING.base },
  feedbackText:     { ...TYPOGRAPHY.body, color: COLORS.textSecondary, lineHeight: 22 },
  btnArea:          { paddingHorizontal: SPACING.base, marginTop: SPACING.sm },
  bigBtn:           { padding: SPACING.base, borderRadius: 10, alignItems: 'center' },
  startBtn:         { backgroundColor: COLORS.primary },
  stopBtn:          { backgroundColor: '#c62828' },
  analyzeBtn:       { backgroundColor: '#2e7d32' },
  analyzingBtn:     { backgroundColor: COLORS.surface, flexDirection: 'column' },
  bigBtnText:       { ...TYPOGRAPHY.body, color: '#ffffff', fontWeight: '700', fontSize: 16 },
  overlay:          { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.82)', justifyContent: 'center', alignItems: 'center' },
  countdownNum:     { fontSize: 96, fontWeight: '800', color: '#ffffff' },
});
