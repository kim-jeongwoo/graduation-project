import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Audio } from 'expo-av';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import { isAuthExpiredError } from '../../api/client';
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
    insufficient: '입 안쪽 공간이 좁아져 소리가 답답하게 느껴질 수 있는 경향이 보입니다. 하품하듯 입천장 뒤쪽을 살짝 들어 올리는 느낌으로 발성해 보세요.',
    appropriate:  '입 안쪽 공간과 연구개 위치가 비교적 안정적인 편입니다. 현재 발성 느낌을 자연스럽게 이어가 보세요.',
    excessive:    '입천장 뒤쪽이나 목 주변에 긴장이 많아지는 경향이 보입니다. 힘을 조금 풀고 소리가 자연스럽게 지나가도록 발성해 보세요.',
  },
  tongue_tension: {
    insufficient: '혀의 움직임이 덜 또렷해 발음이 흐려질 수 있는 경향이 보입니다. 혀를 과하게 누르지 말고 필요한 만큼만 선명하게 사용해 보세요.',
    appropriate:  '혀와 구강 공간의 긴장도가 비교적 안정적인 편입니다. 현재 발음과 발성 느낌을 자연스럽게 이어가 보세요.',
    excessive:    '혀, 턱, 입 안쪽에 힘이 많이 들어간 경향이 보입니다. 혀끝과 턱의 힘을 조금 풀고 자연스럽게 발성해 보세요.',
  },
};

const SERVER_INDICATOR_KEY: Record<IndicatorAppKey, string> = {
  breathiness:         '4_breathiness',
  vocal_fold_contact:  '3_vocal_fold_contact',
  soft_palate:         '6_soft_palate',
  tongue_tension:      '8_tongue_tension',
};

const WS_CONNECT_TIMEOUT_MS = 3000;
const MIN_TRAINING_ANALYZE_SEC = 3;
const VOICE_RECENT_MS = 900;
const MIC_UI_UPDATE_MS = 120;
const INPUT_STATUS_WINDOW_MS = 1200;
const MIC_ANALYSIS_LEVEL_HINT_THRESHOLD = 0.06;
const MIN_ANALYSIS_VOICED_FRAMES = 3;
const INPUT_GUIDANCE = '최소 3초 이상, 조금 더 크게 불러 주세요.';
const SECTION_END_TRIM_SEC = 1;
const RECORDING_PRE_ROLL_SEC = 1;

interface InputFrame {
  at: number;
  voiced: boolean;
  level: number;
}

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

function getNumberDetail(detail: Record<string, unknown> | null, key: string): number | null {
  const value = detail?.[key];
  return typeof value === 'number' ? value : null;
}

function getRmsLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

function formatDuration(sec: number): string {
  return sec.toFixed(1);
}

function getTooShortMessage(durationSec: number | null, minRequiredSec = MIN_TRAINING_ANALYZE_SEC): string {
  const current = durationSec !== null ? `\n현재 녹음: ${formatDuration(durationSec)}초` : '';
  return `분석을 위해 최소 ${minRequiredSec}초 이상 녹음이 필요합니다.${current}\n${INPUT_GUIDANCE}`;
}

function getInputFailureMessage(reason?: string | null): string {
  const trimmed = reason?.trim();
  return trimmed ? `${trimmed}\n${INPUT_GUIDANCE}` : `입력이 부족해 분석이 어렵습니다.\n${INPUT_GUIDANCE}`;
}

function getNoVoiceMessage(reason?: string | null): string {
  const trimmed = reason?.trim();
  return trimmed
    ? `음성이 충분히 감지되지 않았습니다.\n${trimmed}\n${INPUT_GUIDANCE}`
    : `음성이 충분히 감지되지 않았습니다.\n${INPUT_GUIDANCE}`;
}

function isValidZone(value: unknown): value is Zone {
  return value === 'insufficient' || value === 'appropriate' || value === 'excessive';
}

function getInputStatus(
  durationSec: number | null,
  recentVoicedFrames: number,
  level: number,
  levelThreshold = MIC_ANALYSIS_LEVEL_HINT_THRESHOLD,
): VoiceInputStatus {
  if (durationSec === null) return 'waiting';
  if (recentVoicedFrames === 0) return durationSec > VOICE_RECENT_MS / 1000 ? 'noVoice' : 'waiting';
  if (
    durationSec >= MIN_TRAINING_ANALYZE_SEC
    && recentVoicedFrames >= MIN_ANALYSIS_VOICED_FRAMES
    && level >= levelThreshold
  ) {
    return 'ready';
  }
  return 'weak';
}

import type { MidiSegment, PitchPoint } from '../../types/karaoke';
import { getSongMidiSegmentsOptional, getSongMrUrl } from '../../api/songs';
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
  VoiceInputCard,
  pitchVerdictFromScore,
  type PitchLiveStatus,
  type PitchVerdict,
  type VoiceInputStatus,
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
    if (!Number.isFinite(legacy.ai_score) || !isValidZone(legacy.zone)) return null;
    return { aiScore: legacy.ai_score, zone: legacy.zone };
  }

  const meta = getKeyedValue(res.scores_meta, indicatorKey, serverIndicatorKey);
  const roundedScore = typeof meta?.rounded_score === 'number'
    ? meta.rounded_score
    : getKeyedValue(res.scores_v2, indicatorKey, serverIndicatorKey);
  if (typeof roundedScore !== 'number') return null;
  return { aiScore: roundedScore, zone: deriveZoneFromRoundedScore(roundedScore) };
}

function normalizeTrainingAnalyzeStatus(res: TrainingAnalyzeResponse): string {
  const raw = (res as TrainingAnalyzeResponse & { bodyStatus?: string | null }).body_status
    ?? (res as TrainingAnalyzeResponse & { bodyStatus?: string | null }).bodyStatus
    ?? res.status;
  return typeof raw === 'string' && raw.trim() ? raw.trim().toLowerCase() : 'unknown';
}

function getTrainingAnalyzeReason(res: TrainingAnalyzeResponse): string | null {
  if (typeof res.reason === 'string' && res.reason.trim()) return res.reason;
  if (typeof res.message === 'string' && res.message.trim()) return res.message;
  if (typeof res.error === 'string' && res.error.trim()) return res.error;
  if (typeof res.detail === 'string' && res.detail.trim()) return res.detail;
  if (res.detail && typeof res.detail === 'object') {
    const detail = res.detail as Record<string, unknown>;
    for (const key of ['reason', 'message', 'detail', 'error']) {
      const value = detail[key];
      if (typeof value === 'string' && value.trim()) return value;
    }
  }
  return null;
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
  const trainingSectionEndSec = Math.max(sectionStartSec, sectionEndSec - SECTION_END_TRIM_SEC);
  const trainingChunkStartSec = chunkInfo.startSec;
  const trainingChunkEndSec = Math.max(chunkInfo.startSec, chunkInfo.endSec - SECTION_END_TRIM_SEC);
  const recordingStartSec = Math.max(sectionStartSec, trainingChunkStartSec - RECORDING_PRE_ROLL_SEC);
  const recordingEndSec = trainingChunkEndSec;

  const [loading,      setLoading]      = useState(true);
  const [errorMsg,     setErrorMsg]     = useState<string | null>(null);
  const [guideUnavailable, setGuideUnavailable] = useState(false);
  const [midiSegments, setMidiSegments] = useState<MidiSegment[]>([]);
  const [lrcOffsetSec, setLrcOffsetSec] = useState(0);
  const [currentTime,  setCurrentTime]  = useState(sectionStartSec);  // master time
  const [playing,      setPlaying]      = useState(false);
  const [countdown,    setCountdown]    = useState<number | null>(null);
  const [userPitch,    setUserPitch]    = useState<PitchPoint[]>([]);

  // 실시간 피드백 state (Phase 3)
  const [pitchMatchScore, setPitchMatchScore] = useState<number | null>(null);
  const [pitchVerdict,    setPitchVerdict]    = useState<PitchVerdict>('unknown');
  const [pitchLiveStatus, setPitchLiveStatus] = useState<PitchLiveStatus>('idle');
  const [voiceInputStatus, setVoiceInputStatus] = useState<VoiceInputStatus>('idle');
  const [micLevel, setMicLevel] = useState(0);
  const [voicedFrameCount, setVoicedFrameCount] = useState(0);
  const [analysisInputLevel, setAnalysisInputLevel] = useState(0);
  const [breathZone,      setBreathZone]      = useState<Zone | null>(null);
  const [breathScore,     setBreathScore]     = useState<number | null>(null);

  // 사후 측정 state (Phase 4-2)
  type Status = 'idle' | 'countdown' | 'preparing' | 'recording' | 'stopped' | 'analyzing' | 'result';
  const [status,         setStatus]        = useState<Status>('idle');
  const [recordedUri,    setRecordedUri]   = useState<string | null>(null);
  const [recordedDurationSec, setRecordedDurationSec] = useState<number | null>(null);
  const [afterScore,     setAfterScore]    = useState<BeforeAfterScore | null>(null);
  const [afterLowConfidence, setAfterLowConfidence] = useState(false);

  const serverIndicatorKey = SERVER_INDICATOR_KEY[indicatorKey];
  const beforeLowConfidence = lowConfidenceItems?.includes(serverIndicatorKey) ?? false;
  const canAnalyze = !!sessionId && !!recordedUri;

  const soundRef       = useRef<Audio.Sound | null>(null);
  const recorderRef    = useRef(new VocalRecorder());
  const currentTimeRef = useRef(sectionStartSec);  // master time
  const stoppedRef     = useRef(false);
  const recordingStartedRef = useRef(false);
  const recordingStartedAtRef = useRef<number | null>(null);
  const lastVoiceAtRef = useRef<number | null>(null);
  const lastMicUiAtRef = useRef(0);
  const voicedFrameCountRef = useRef(0);
  const recentInputFramesRef = useRef<InputFrame[]>([]);
  const analysisLevelSumRef = useRef(0);
  const analysisFrameCountRef = useRef(0);
  const maxInputLevelRef = useRef(0);
  const attemptIdRef = useRef(0);
  const startingRef = useRef(false);
  const recordingStartPendingRef = useRef(false);
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket + PCM buffering refs (Phase 3)
  const wsRef          = useRef<WebSocket | null>(null);
  const wsReadyRef     = useRef(false);
  const pcmBufferRef   = useRef<number[]>([]);
  const pitchHistRef   = useRef<PitchVerdict[]>([]);  // 최근 5프레임 다수결

  const getCurrentRecordingDurationSec = useCallback((): number | null => {
    if (recordingStartedAtRef.current === null) return null;
    return Math.max(0, (Date.now() - recordingStartedAtRef.current) / 1000);
  }, []);

  const getAnalysisInputLevel = useCallback((): number => {
    if (analysisFrameCountRef.current === 0) return 0;
    return analysisLevelSumRef.current / analysisFrameCountRef.current;
  }, []);

  const disposeSound = useCallback(async (sound?: Audio.Sound | null, phase = 'cleanup') => {
    const s = sound ?? soundRef.current;
    if (!s) return;
    try { s.setOnPlaybackStatusUpdate(null); } catch {}
    try { await s.stopAsync(); } catch {}
    try { await s.unloadAsync(); } catch {}
    if (soundRef.current === s) soundRef.current = null;
  }, []);

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
        setGuideUnavailable(false);
        const granted = await requestMicrophonePermission();
        if (!granted) {
          Alert.alert('마이크 권한 필요', '훈련하려면 마이크 권한이 필요합니다.');
        }
        const guideData = await getSongMidiSegmentsOptional(songId, 'training');
        if (cancelled) return;
        if (!guideData) {
          setMidiSegments([]);
          setLrcOffsetSec(0);
          setGuideUnavailable(true);
          setLoading(false);
          return;
        }
        const { segments, lrcOffsetSec: off } = guideData;
        const guideOffset = SONG_GUIDE_OFFSETS[songId] ?? 0;
        const adjusted: MidiSegment[] = segments.map(s => ({
          start:    s.start + guideOffset,
          end:      s.end   + guideOffset,
          midi:     s.midi,
          noteName: '',
        }));
        setMidiSegments(adjusted);
        setLrcOffsetSec(off);
        setGuideUnavailable(false);
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
  }, [songId, sectionStartSec, sectionEndSec, trainingSectionEndSec, trainingChunkStartSec, trainingChunkEndSec, chunkInfo]);

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
    await disposeSound(undefined, 'cleanup');
    try { await recorderRef.current.cancel(); } catch {}
    recordingStartedRef.current = false;
    recordingStartedAtRef.current = null;
    lastVoiceAtRef.current = null;
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    startingRef.current = false;
    recordingStartPendingRef.current = false;
  }, [closeWs, disposeSound]);

  // ─── WebSocket 연결 (1회 재시도) ───
  const openWs = useCallback((startTimestampSec: number, retried = false): Promise<WebSocket | null> => {
    return new Promise((resolve) => {
      if (!songId) { resolve(null); return; }
      const url = buildRealtimeWsUrl(songId);
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.binaryType = 'arraybuffer';
      let resolved = false;
      let timeout: ReturnType<typeof setTimeout> | null = null;
      const clearConnectTimeout = () => {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
      };
      const settle = (value: WebSocket | null) => {
        if (resolved) return;
        resolved = true;
        clearConnectTimeout();
        resolve(value);
      };
      timeout = setTimeout(() => {
        wsReadyRef.current = false;
        if (wsRef.current === ws) wsRef.current = null;
        try { ws.close(); } catch {}
        settle(null);
      }, WS_CONNECT_TIMEOUT_MS);
      ws.onopen = () => {
        if (resolved) {
          try { ws.close(); } catch {}
          return;
        }
        wsReadyRef.current = true;
        if (stoppedRef.current) {
          try { ws.close(); } catch {}
          settle(null);
          return;
        }
        // meta 송신
        try {
          ws.send(JSON.stringify({
            type: 'meta',
            sample_rate: 16000,
            start_timestamp: startTimestampSec,
          }));
        } catch {}
        settle(ws);
      };
      ws.onmessage = (ev) => {
        if (stoppedRef.current) return;
        if (typeof ev.data !== 'string') return;
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'pitch_match') {
            // 사용자 음성 없음 (user_midi=null) → 게이지 리셋, history 비움
            if (msg.user_midi === null || msg.user_midi === undefined) {
              setPitchMatchScore(null);
              setPitchVerdict('unknown');
              setPitchLiveStatus('noVoice');
              pitchHistRef.current = [];
              return;
            }
            const score: number | null = msg.match_score ?? null;
            const voiceRecent = lastVoiceAtRef.current !== null
              && Date.now() - lastVoiceAtRef.current <= VOICE_RECENT_MS;
            if (!voiceRecent) {
              setPitchMatchScore(null);
              setPitchVerdict('unknown');
              setPitchLiveStatus('noVoice');
              pitchHistRef.current = [];
              return;
            }
            setPitchMatchScore(score);
            setPitchLiveStatus('active');
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
        } catch {}
      };
      ws.onerror = () => {};
      ws.onclose = () => {
        wsReadyRef.current = false;
        if (wsRef.current === ws) wsRef.current = null;
        if (!resolved) {
          clearConnectTimeout();
          if (!retried) {
            openWs(startTimestampSec, true).then(settle);
          } else {
            settle(null);
          }
        } else if (!stoppedRef.current) {
          setPitchLiveStatus('serverUnavailable');
        }
      };
    });
  }, [songId]);

  // ─── MR + recorder 시작 ───
  const startMrAndRecord = useCallback(async () => {
    if (!songId) return;
    const granted = await requestMicrophonePermission();
    if (!granted) {
      Alert.alert('마이크 권한 필요', '마이크 권한이 필요합니다. 설정에서 마이크 권한을 허용해 주세요.');
      setStatus('idle');
      setPitchLiveStatus('idle');
      return;
    }
    const mrStart = Math.max(0, sectionStartSec - lrcOffsetSec);  // MR time
    const recordingStartMaster = recordingStartSec;
    const recordingEndMaster = recordingEndSec;
    const recordingStartMr = Math.max(0, recordingStartMaster - lrcOffsetSec);
    const mrEnd = Math.max(recordingStartMr, recordingEndMaster - lrcOffsetSec);
    const attemptId = attemptIdRef.current + 1;
    attemptIdRef.current = attemptId;
    stoppedRef.current = false;
    setStatus('preparing');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('leadIn');
    setMicLevel(0);
    try {
      await disposeSound(undefined, 'start-replace');
      if (stoppedRef.current || attemptIdRef.current !== attemptId) return;

      // MR sound
      const sound = new Audio.Sound();
      soundRef.current = sound;
      const stopTargetRecording = async (phase = 'auto-stop') => {
        if (stoppedRef.current || attemptIdRef.current !== attemptId || soundRef.current !== sound) return;
        stoppedRef.current = true;
        recordingStartPendingRef.current = false;
        const hadRecording = recordingStartedRef.current;
        try {
          if (hadRecording) {
            const durationSec = getCurrentRecordingDurationSec();
            const result = await recorderRef.current.stop();
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
            setRecordedDurationSec(durationSec);
            setRecordedUri(result.uri);
            const analysisLevel = getAnalysisInputLevel();
            setVoiceInputStatus(getInputStatus(durationSec, 0, 0));
            setVoicedFrameCount(voicedFrameCountRef.current);
            setAnalysisInputLevel(analysisLevel);
          } else {
            try { await recorderRef.current.cancel(); } catch {}
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
          }
        } catch (e) {
          console.error('[TrainingScreen] recorder.stop (auto) error:', e);
          recordingStartedRef.current = false;
          recordingStartedAtRef.current = null;
        }
        closeWs();
        await disposeSound(sound, phase);
        setPitchLiveStatus('idle');
        setPlaying(false);
        setStatus(hadRecording ? 'stopped' : 'idle');
      };

      const startTargetRecording = async () => {
        if (
          stoppedRef.current
          || attemptIdRef.current !== attemptId
          || recordingStartedRef.current
          || recordingStartPendingRef.current
        ) {
          return;
        }
        recordingStartPendingRef.current = true;
        setPitchLiveStatus('serverConnecting');
        setVoiceInputStatus('waiting');
        openWs(recordingStartSec).then((ws) => {
          if (stoppedRef.current || attemptIdRef.current !== attemptId) {
            if (ws && ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
              try { ws.close(); } catch {}
            }
            return;
          }
          setPitchLiveStatus(ws ? 'micWaiting' : 'serverUnavailable');
        });
        try {
          await recorderRef.current.start((samples) => {
            if (stoppedRef.current || attemptIdRef.current !== attemptId || !recordingStartedRef.current) return;
            // ── 로컬 피치 (기존) ──
            const result = detectPitch(samples);
            const now = Date.now();
            const level = Math.min(1, getRmsLevel(samples) * 8);
            maxInputLevelRef.current = Math.max(maxInputLevelRef.current, level);
            const hasVoice = result.voiced && result.midi !== null;
            if (hasVoice) {
              lastVoiceAtRef.current = now;
              voicedFrameCountRef.current += 1;
            }
            recentInputFramesRef.current = [
              ...recentInputFramesRef.current.filter((frame) => now - frame.at <= INPUT_STATUS_WINDOW_MS),
              { at: now, voiced: hasVoice, level },
            ];
            analysisLevelSumRef.current += level;
            analysisFrameCountRef.current += 1;
            if (now - lastMicUiAtRef.current >= MIC_UI_UPDATE_MS) {
              const durationSec = getCurrentRecordingDurationSec();
              const recentFrames = recentInputFramesRef.current;
              const recentVoicedFrames = recentFrames.filter((frame) => frame.voiced).length;
              const recentLevel = recentFrames.length
                ? recentFrames.reduce((sum, frame) => sum + frame.level, 0) / recentFrames.length
                : level;
              const analysisLevel = getAnalysisInputLevel();
              setMicLevel(level);
              setVoiceInputStatus(getInputStatus(durationSec, recentVoicedFrames, recentLevel));
              setVoicedFrameCount(voicedFrameCountRef.current);
              setAnalysisInputLevel(analysisLevel);
              setRecordedDurationSec(durationSec);
              lastMicUiAtRef.current = now;
            }
            const t = currentTimeRef.current;
            if (hasVoice) {
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
                try { wsRef.current.send(int16.buffer); } catch {}
              }
            }
          });
          recordingStartPendingRef.current = false;
          if (stoppedRef.current || attemptIdRef.current !== attemptId) {
            try { await recorderRef.current.cancel(); } catch {}
            recordingStartedRef.current = false;
            recordingStartedAtRef.current = null;
            setPitchLiveStatus('idle');
            return;
          }
          recordingStartedRef.current = true;
          recordingStartedAtRef.current = Date.now();
          lastVoiceAtRef.current = null;
          setRecordedDurationSec(0);
          setStatus('recording');
        } catch (e) {
          recordingStartPendingRef.current = false;
          console.error('[TrainingScreen] recorder.start error:', e);
          Alert.alert('훈련 시작 실패', '녹음을 시작할 수 없습니다. 마이크 상태를 확인해 주세요.');
          await stopTargetRecording('recording-start-failure');
        }
      };

      sound.setOnPlaybackStatusUpdate((status) => {
        if (attemptIdRef.current !== attemptId || soundRef.current !== sound) return;
        if (!status.isLoaded) return;
        const mrPos = status.positionMillis / 1000;
        const masterPos = mrPos + lrcOffsetSec;
        currentTimeRef.current = masterPos;
        setCurrentTime(masterPos);
        setPlaying(status.isPlaying);
        if (!stoppedRef.current && masterPos >= recordingStartMaster) {
          void startTargetRecording();
        }
        // 자동 정지: target chunk 끝 도달
        if (!stoppedRef.current && mrPos >= mrEnd) {
          void stopTargetRecording('auto-stop');
        }
      });
      await sound.loadAsync(
        { uri: getSongMrUrl(songId), headers: token ? { Authorization: `Bearer ${token}` } : {} },
        { shouldPlay: false, progressUpdateIntervalMillis: 50 },
      );
      if (stoppedRef.current || attemptIdRef.current !== attemptId) {
        await disposeSound(sound, 'load-cancel');
        try { await recorderRef.current.cancel(); } catch {}
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        recordingStartPendingRef.current = false;
        setPitchLiveStatus('idle');
        return;
      }
      await sound.playFromPositionAsync(mrStart * 1000);
      if (stoppedRef.current || attemptIdRef.current !== attemptId) {
        await disposeSound(sound, 'play-cancel');
        try { await recorderRef.current.cancel(); } catch {}
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        recordingStartPendingRef.current = false;
        setPitchLiveStatus('idle');
        return;
      }
    } catch (e) {
      console.error('[TrainingScreen] startMrAndRecord error:', e);
      Alert.alert('훈련 시작 실패', '반주 또는 녹음을 시작할 수 없습니다. 마이크 상태를 확인해 주세요.');
      stoppedRef.current = true;
      try { await recorderRef.current.cancel(); } catch {}
      recordingStartedRef.current = false;
      recordingStartedAtRef.current = null;
      recordingStartPendingRef.current = false;
      await disposeSound(undefined, 'start-failure');
      closeWs();
      setPitchLiveStatus('idle');
      setPlaying(false);
      setStatus('idle');
    }
  }, [
    songId,
    sectionStartSec,
    sectionEndSec,
    trainingSectionEndSec,
    trainingChunkStartSec,
    trainingChunkEndSec,
    recordingStartSec,
    recordingEndSec,
    lrcOffsetSec,
    token,
    openWs,
    closeWs,
    getCurrentRecordingDurationSec,
    getAnalysisInputLevel,
    disposeSound,
    midiSegments,
    chunkInfo,
  ]);

  const performTrainingAnalyze = useCallback(async () => {
    if (!sessionId || !recordedUri) {
      Alert.alert('알림', '녹음 데이터 또는 세션 정보가 없습니다.');
      return;
    }
    setStatus('analyzing');
    setAfterScore(null);
    setAfterLowConfidence(false);
    const chunkMeta = {
      chunk_index: chunkIndex,
      start_sec: recordingStartSec,
      end_sec: recordingEndSec,
      original_run_id: runId,
    };
    try {
      const res = await trainingAnalyze(sessionId, recordedUri, chunkMeta);
      const bodyStatus = normalizeTrainingAnalyzeStatus(res);
      const responseReason = getTrainingAnalyzeReason(res);
      if (bodyStatus === 'no_voice') {
        setVoiceInputStatus('noVoice');
        Alert.alert('음성 미감지', getNoVoiceMessage(responseReason));
        setStatus('stopped');
        return;
      }
      if (bodyStatus === 'invalid') {
        setVoiceInputStatus('weak');
        Alert.alert('입력 확인', getInputFailureMessage(responseReason ?? '분석할 수 없는 입력입니다.'));
        setStatus('stopped');
        return;
      }
      if (bodyStatus !== 'success') {
        setVoiceInputStatus('weak');
        Alert.alert('분석 실패', getInputFailureMessage(responseReason ?? '분석에 실패했습니다.'));
        setStatus('stopped');
        return;
      }
      const after = getTrainingAnalyzeScore(res, indicatorKey, serverIndicatorKey);
      if (!after) {
        setVoiceInputStatus('weak');
        Alert.alert('분석 결과 없음', getInputFailureMessage('진입 항목 점수가 응답에 없습니다.'));
        setStatus('stopped');
        return;
      }
      setAfterScore(after);
      setAfterLowConfidence(hasLowConfidenceItem(res.low_confidence_items, indicatorKey, serverIndicatorKey));
      setStatus('result');
    } catch (e: unknown) {
      if (isAuthExpiredError(e)) {
        setStatus('stopped');
        return;
      }
      const { code, detail, message } = getApiErrorInfo(e);
      const detailError = getStringDetail(detail, 'error');
      const detailReason = getStringDetail(detail, 'reason');
      const serverDurationSec = getNumberDetail(detail, 'duration_sec') ?? recordedDurationSec;
      const minRequiredSec = getNumberDetail(detail, 'min_required_sec') ?? MIN_TRAINING_ANALYZE_SEC;
      if (code === 400 && (detailError === 'chunk_too_short' || detailReason?.includes('최소 3초'))) {
        setVoiceInputStatus('weak');
        Alert.alert('녹음 너무 짧음', detailReason ?? getTooShortMessage(serverDurationSec, minRequiredSec));
      } else if (code === 401) {
        Alert.alert('인증 만료', '다시 로그인해주세요.');
      } else if (code === 403) {
        Alert.alert('권한 없음', '다른 사용자의 세션입니다.');
      } else if (code === 404) {
        Alert.alert('세션 없음', '세션이 만료되었습니다.');
      } else if (code === 504) {
        setVoiceInputStatus('weak');
        Alert.alert('사후 측정 지연', '사후 측정 분석 응답이 지연되었습니다. 잠시 후 다시 시도해주세요.');
      } else if (code) {
        setVoiceInputStatus('weak');
        Alert.alert('분석 실패', getInputFailureMessage(detailReason ?? message ?? '분석에 실패했습니다.'));
      } else {
        Alert.alert('네트워크 오류', '네트워크를 확인하고 다시 시도해주세요.');
      }
      setStatus('stopped');
    }
  }, [
    sessionId,
    recordedUri,
    recordedDurationSec,
    chunkIndex,
    chunkInfo,
    trainingChunkEndSec,
    trainingSectionEndSec,
    recordingStartSec,
    recordingEndSec,
    runId,
    songId,
    indicatorKey,
    serverIndicatorKey,
    sectionStartSec,
    sectionEndSec,
    trainingChunkStartSec,
    status,
  ]);

  // ─── 사후 측정 ───
  const handleAnalyze = useCallback(async () => {
    if (!sessionId || !recordedUri) {
      Alert.alert('알림', '녹음 데이터 또는 세션 정보가 없습니다.');
      return;
    }
    if (recordedDurationSec !== null && recordedDurationSec < MIN_TRAINING_ANALYZE_SEC) {
      setVoiceInputStatus('weak');
      Alert.alert('녹음 너무 짧음', getTooShortMessage(recordedDurationSec));
      return;
    }
    const analysisReady = recordedDurationSec !== null
      && recordedDurationSec >= MIN_TRAINING_ANALYZE_SEC
      && voicedFrameCount >= MIN_ANALYSIS_VOICED_FRAMES
      && analysisInputLevel >= MIC_ANALYSIS_LEVEL_HINT_THRESHOLD;
    if (!analysisReady) {
      if (voicedFrameCount === 0) {
        setVoiceInputStatus('noVoice');
        Alert.alert(
          '입력 부족',
          getInputFailureMessage(),
        );
        return;
      }
      setVoiceInputStatus('weak');
      Alert.alert(
        '입력 확인',
        `음성은 감지됐지만 분석에는 부족할 수 있습니다. 음정 선이 보여도 서버 분석은 실패할 수 있습니다.\n${INPUT_GUIDANCE}`,
        [
          { text: '다시 부르기', style: 'cancel' },
          { text: '그래도 분석', onPress: () => { void performTrainingAnalyze(); } },
        ],
      );
      return;
    }
    await performTrainingAnalyze();
  }, [
    sessionId,
    recordedUri,
    recordedDurationSec,
    voicedFrameCount,
    analysisInputLevel,
    pitchMatchScore,
    performTrainingAnalyze,
  ]);

  const handleRetry = useCallback(() => {
    setStatus('idle');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('idle');
    setMicLevel(0);
    setVoicedFrameCount(0);
    setAnalysisInputLevel(0);
    setAfterScore(null);
    setAfterLowConfidence(false);
    setRecordedUri(null);
    setRecordedDurationSec(null);
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    maxInputLevelRef.current = 0;
  }, []);

  const resetAttemptState = useCallback(() => {
    setUserPitch([]);
    setCurrentTime(sectionStartSec);
    currentTimeRef.current = sectionStartSec;
    setPitchMatchScore(null);
    setPitchVerdict('unknown');
    setPitchLiveStatus('idle');
    setVoiceInputStatus('idle');
    setMicLevel(0);
    setVoicedFrameCount(0);
    setAnalysisInputLevel(0);
    setBreathZone(null);
    setBreathScore(null);
    pitchHistRef.current = [];
    pcmBufferRef.current = [];
    setRecordedUri(null);
    setRecordedDurationSec(null);
    setAfterScore(null);
    setAfterLowConfidence(false);
    recordingStartedAtRef.current = null;
    recordingStartPendingRef.current = false;
    lastVoiceAtRef.current = null;
    lastMicUiAtRef.current = 0;
    voicedFrameCountRef.current = 0;
    recentInputFramesRef.current = [];
    analysisLevelSumRef.current = 0;
    analysisFrameCountRef.current = 0;
    maxInputLevelRef.current = 0;
  }, [sectionStartSec]);

  const startPractice = useCallback(() => {
    if (startingRef.current || countdownTimer.current) return;
    startingRef.current = true;
    resetAttemptState();
    startingRef.current = false;
    startMrAndRecord();
  }, [resetAttemptState, startMrAndRecord]);

  // ─── 카운트다운 → 시작 ───
  const startCountdown = useCallback(() => {
    if (startingRef.current || countdownTimer.current) return;
    startingRef.current = true;
    resetAttemptState();
    setStatus('countdown');
    let n = 3;
    setCountdown(n);
    countdownTimer.current = setInterval(() => {
      n -= 1;
      if (n <= 0) {
        if (countdownTimer.current) clearInterval(countdownTimer.current);
        countdownTimer.current = null;
        startingRef.current = false;
        setCountdown(null);
        startMrAndRecord();
      } else {
        setCountdown(n);
      }
    }, 1000);
  }, [resetAttemptState, startMrAndRecord]);

  // ─── 사용자 액션 ───
  const handleStart = useCallback(async () => {
    if (startingRef.current || countdown !== null || playing || status === 'preparing' || status === 'recording') return;
    startingRef.current = true;
    try {
      const granted = await requestMicrophonePermission();
      if (!granted) {
        Alert.alert('마이크 권한 필요', '마이크 권한이 필요합니다. 설정에서 마이크 권한을 허용해 주세요.');
        setPitchLiveStatus('idle');
        startingRef.current = false;
        return;
      }
    } catch (e) {
      console.error('[TrainingScreen] microphone permission error:', e);
      Alert.alert('마이크 권한 확인 실패', '마이크 권한을 확인할 수 없습니다. 다시 시도해 주세요.');
      setPitchLiveStatus('idle');
      startingRef.current = false;
      return;
    }
    startingRef.current = false;
    startCountdown();
  }, [countdown, playing, status, startCountdown]);

  const handleStop = useCallback(async () => {
    const wasRecording = !stoppedRef.current && recordingStartedRef.current;
    attemptIdRef.current += 1;
    stoppedRef.current = true;
    recordingStartPendingRef.current = false;
    startingRef.current = false;
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
      setCountdown(null);
    }
    const s = soundRef.current;
    if (s) await disposeSound(s, 'manual-stop');
    if (wasRecording) {
      try {
        const durationSec = getCurrentRecordingDurationSec();
        const result = await recorderRef.current.stop();
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
        setRecordedDurationSec(durationSec);
        setRecordedUri(result.uri);
        const analysisLevel = getAnalysisInputLevel();
        setVoiceInputStatus(getInputStatus(
          durationSec,
          0,
          0,
        ));
        setVoicedFrameCount(voicedFrameCountRef.current);
        setAnalysisInputLevel(analysisLevel);
      } catch (e) {
        console.error('[TrainingScreen] recorder.stop (manual) error:', e);
        recordingStartedRef.current = false;
        recordingStartedAtRef.current = null;
      }
    } else {
      try { await recorderRef.current.cancel(); } catch {}
      recordingStartedRef.current = false;
      recordingStartedAtRef.current = null;
    }
    closeWs();
    setPitchLiveStatus('idle');
    setPlaying(false);
    setStatus(wasRecording ? 'stopped' : 'idle');
  }, [closeWs, getCurrentRecordingDurationSec, getAnalysisInputLevel, disposeSound]);

  const handleRestart = useCallback(async () => {
    if (status === 'countdown' || status === 'preparing' || status === 'recording') {
      await handleStop();
    }
    startPractice();
  }, [handleStop, startPractice, status]);

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

  const isActive    = status === 'countdown' || status === 'preparing' || status === 'recording';
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
          <Text style={styles.label}>불러야 하는 구간</Text>
          <Text style={styles.value}>
            {chunkInfo.startSec.toFixed(1)}초 ~ {trainingChunkEndSec.toFixed(1)}초
          </Text>

          <Text style={styles.label}>MR 재생 범위</Text>
          <Text style={styles.value}>
            {sectionStartSec.toFixed(1)}초 ~ {trainingSectionEndSec.toFixed(1)}초
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
          endSec={trainingSectionEndSec}
          originalStartSec={chunkInfo.startSec}
          originalEndSec={trainingChunkEndSec}
          currentTimeSec={currentTime}
          userPitch={userPitch}
        />
        {guideUnavailable && (
          <View style={styles.guideNotice}>
            <Text style={styles.guideNoticeText}>
              피치 가이드를 불러오지 못했습니다. 구간훈련은 계속할 수 있습니다.
            </Text>
          </View>
        )}

        {/* 실시간 피드백 (Phase 3) */}
        <View style={{ marginTop: SPACING.base }}>
          <VoiceInputCard status={voiceInputStatus} level={micLevel} durationSec={recordedDurationSec} />
          <PitchCard verdict={pitchVerdict} matchScore={pitchMatchScore} liveStatus={pitchLiveStatus} />
          {indicatorFeedbackCard}
        </View>

        <View style={styles.feedbackBox}>
          <Text style={styles.label}>피드백</Text>
          <Text style={styles.feedbackText}>
            {showResult && afterScore
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
              <TouchableOpacity style={[styles.bigBtn, styles.startBtn]} onPress={handleRestart}>
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
  guideNotice:      { backgroundColor: COLORS.surface, borderRadius: 10, padding: SPACING.sm, marginHorizontal: SPACING.base, marginTop: SPACING.sm },
  guideNoticeText:  { ...TYPOGRAPHY.caption, color: COLORS.textSecondary, textAlign: 'center' },
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
