import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import Svg, { Line, Path } from 'react-native-svg';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import EvalItemCard from '../../components/eval/EvalItemCard';
import { getResultsByRunId } from '../../api/analyze';
import { getSongMidiSegmentsRaw } from '../../api/songs';
import { SONG_GUIDE_OFFSETS } from '../../constants/songGuideOffsets';
import { EVALUATION_ITEMS } from '../../domain/evaluationItems';
import type { AnalyzeResult, TimelineChunkScore, Zone, ScoreMetaEntry } from '../../types/analyze';
import type { EvaluationItemKey, ConfidenceLevel } from '../../domain/evaluationItems';
import { extractWeakSections, type IndicatorAppKey } from '../../domain/weakSections';

type Tab = 'basic' | 'advanced';

// TODO(Step E): 사용자 목표에서 가져오기
const FOCUS_ITEMS_FROM_USER: EvaluationItemKey[] = [];
const BASE_ITEMS: EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact'];

type Props = NativeStackScreenProps<
  { EvalResult: { runId?: string; songId?: string } },
  'EvalResult'
>;

// ─── Timeline constants ───
const PX_PER_SEC = 60;
const GUIDE_H    = 220;
const LRC_H      = 30;
const MIDI_MIN   = 40;
const MIDI_MAX   = 88;

function midiToY(midi: number): number {
  return GUIDE_H - ((midi - MIDI_MIN) / (MIDI_MAX - MIDI_MIN)) * GUIDE_H;
}

function scoreColor(pct: number | null): string {
  if (pct === null) return COLORS.textMuted;
  if (pct >= 80) return '#59dda5';
  if (pct >= 50) return '#ffb780';
  return '#ffb4ab';
}

type VisualizationMode = 'pitch' | 'breathiness' | 'vocalFoldContact' | 'softPalate' | 'tongueTension';
type TimelineIndicatorMode = Exclude<VisualizationMode, 'pitch'>;
type TimelineScoreField = keyof TimelineChunkScore['scores'];
type RawSeg = { start: number; end: number; midi: number };
type UserF0 = { frameHz: number; values: (number | null)[] };

const COLOR_APPROPRIATE = '#59dda5';
const COLOR_WARNING = '#ffb4ab';
const COLOR_DATA_MISSING = '#7ecfff';
const COLOR_LOW_CONFIDENCE = '#9ca3af';

const TIMELINE_MODE_CONFIG = {
  breathiness: {
    appKey: 'breathiness',
    serverKey: '4_breathiness',
    scoreField: 'breathiness',
    label: '호흡 소리 식별',
  },
  vocalFoldContact: {
    appKey: 'vocal_fold_contact',
    serverKey: '3_vocal_fold_contact',
    scoreField: 'vocalFoldContact',
    label: '성대 접촉 강도',
  },
  softPalate: {
    appKey: 'soft_palate',
    serverKey: '6_soft_palate',
    scoreField: 'softPalate',
    label: '연구개 위치',
  },
  tongueTension: {
    appKey: 'tongue_tension',
    serverKey: '8_tongue_tension',
    scoreField: 'tongueTension',
    label: '혀/구강 공간 경직도',
  },
} as const satisfies Record<TimelineIndicatorMode, {
  appKey: IndicatorAppKey;
  serverKey: string;
  scoreField: TimelineScoreField;
  label: string;
}>;
type TimelineModeConfig = typeof TIMELINE_MODE_CONFIG[TimelineIndicatorMode];

function isTimelineIndicatorMode(mode: string): mode is TimelineIndicatorMode {
  return Object.prototype.hasOwnProperty.call(TIMELINE_MODE_CONFIG, mode);
}

function stripServerPrefix(key: string): string {
  return key.replace(/^\d+_/, '');
}

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

function hasLowConfidence(
  lowConfidenceItems: string[] | undefined,
  config: TimelineModeConfig,
): boolean {
  return lowConfidenceItems?.some((item) => {
    const stripped = stripServerPrefix(item);
    return item === config.serverKey
      || item === config.appKey
      || item === config.scoreField
      || stripped === config.appKey;
  }) ?? false;
}

function getTimelineModeForAppKey(key: EvaluationItemKey): TimelineIndicatorMode | null {
  if (key === 'breathiness') return 'breathiness';
  if (key === 'vocal_fold_contact') return 'vocalFoldContact';
  if (key === 'soft_palate') return 'softPalate';
  if (key === 'tongue_tension') return 'tongueTension';
  return null;
}

function getMappedScoreMeta(
  record: Partial<Record<EvaluationItemKey, ScoreMetaEntry>> | undefined,
  key: EvaluationItemKey,
  config: TimelineModeConfig | null,
): ScoreMetaEntry | undefined {
  const raw = record as Record<string, ScoreMetaEntry | undefined> | undefined;
  if (!raw) return undefined;
  const candidates = config ? [key, config.serverKey, config.scoreField] : [key];
  return candidates.map(candidate => raw[candidate]).find(Boolean);
}

function getMappedNumber(
  record: Partial<Record<EvaluationItemKey, number>> | undefined,
  key: EvaluationItemKey,
  config: TimelineModeConfig | null,
): number | undefined {
  const raw = record as Record<string, number | undefined> | undefined;
  if (!raw) return undefined;
  const candidates = config ? [key, config.serverKey, config.scoreField] : [key];
  return candidates.map(candidate => raw[candidate]).find(value => typeof value === 'number');
}

const MODE_BUTTONS: { id: string; label: string; active: boolean; v2Only?: boolean }[] = [
  { id: 'pitch',            label: '음정',          active: true  },
  { id: 'breathiness',      label: '호흡소리식별',   active: true  },
  { id: 'vocalFoldContact', label: '성대접촉강도',   active: true  },
  { id: 'softPalate',       label: '연구개위치',     active: true, v2Only: true },
  { id: 'tongueTension',    label: '혀경직도',       active: true, v2Only: true },
  { id: 'nasal',            label: '비강구강공명비율', active: false },
  { id: 'register',         label: '흉성두성경향',   active: false },
  { id: 'resonance',        label: '전방공명정도',   active: false },
  { id: 'larynx',           label: '후두혀뿌리위치', active: false },
  { id: 'pressure',         label: '상압하압비율',   active: false },
];

interface TimelineSectionProps {
  timelineScores: TimelineChunkScore[];
  midiSegments:   RawSeg[];
  userF0:         UserF0 | null;
  activeMode:     VisualizationMode;
  lrcOffsetSec:   number;
  guideOffset:    number;
}

function TimelineSection({ timelineScores, midiSegments, userF0, activeMode, lrcOffsetSec, guideOffset }: TimelineSectionProps) {
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    if (!midiSegments.length) return;
    const x = Math.max(0, midiSegments[0].start * PX_PER_SEC - 20);
    scrollRef.current?.scrollTo({ x, animated: false });
  }, [midiSegments]);

  const midiLastSec   = midiSegments.length ? midiSegments[midiSegments.length - 1].end : 0;
  const f0DurationSec = userF0 ? (userF0.values.length / userF0.frameHz) + lrcOffsetSec : 0;
  const totalSec = Math.max(midiLastSec, f0DurationSec, 60);
  const totalW   = Math.ceil(totalSec * PX_PER_SEC);


  // ─── 사용자 F0 경로 (모드별 색상 분기) ───
  const f0Paths = useMemo(() => {
    if (!userF0?.values?.length) return [];
    const { frameHz, values } = userF0;
    const stride = values.length > 4000 ? 2 : 1;

    const getColor = (i: number, freq: number): string => {
      const tMaster = i / frameHz + lrcOffsetSec;
      const midi    = 12 * Math.log2(freq / 440) + 69;

      if (activeMode === 'pitch') {
        let nearest: RawSeg | null = null, minDist = Infinity;
        for (const s of midiSegments) {
          const sA = s.start + guideOffset, eA = s.end + guideOffset;
          const d  = tMaster >= sA && tMaster <= eA ? 0
            : Math.min(Math.abs(tMaster - sA), Math.abs(tMaster - eA));
          if (d < minDist) { minDist = d; nearest = s; }
        }
        if (!nearest || minDist > 1.5) return COLOR_DATA_MISSING;
        const diff = Math.abs(midi - nearest.midi);
        return diff < 0.5 ? COLOR_APPROPRIATE : diff < 1.0 ? '#ffb780' : COLOR_WARNING;
      }
      // dml-server v2 timeline_scores 기준: rounded_score가 source of truth, low_confidence 우선.
      if (!isTimelineIndicatorMode(activeMode)) return COLOR_DATA_MISSING;
      const config = TIMELINE_MODE_CONFIG[activeMode];
      const chunk = timelineScores.find(c => tMaster >= c.startSec && tMaster <= c.endSec);
      if (!chunk) return COLOR_DATA_MISSING;
      if (hasLowConfidence(chunk.lowConfidenceItems, config)) return COLOR_LOW_CONFIDENCE;
      const entry = chunk.scores[config.scoreField];
      if (!entry) return COLOR_DATA_MISSING;
      const zone = typeof entry.roundedScore === 'number'
        ? deriveZoneFromRoundedScore(entry.roundedScore)
        : entry.zone;
      if (!zone) return COLOR_DATA_MISSING;
      return zone === 'appropriate' ? COLOR_APPROPRIATE : COLOR_WARNING;
    };

    const nodes: React.ReactNode[] = [];
    let d = '', curColor = '', key = 0;

    const flush = () => {
      if (!d) return;
      nodes.push(<Path key={key++} d={d} stroke={curColor} strokeWidth={2.5}
        fill="none" strokeLinecap="round" strokeLinejoin="round" />);
      d = '';
    };

    for (let i = 0; i < values.length; i++) {
      const freq = values[i];
      if (freq === null || freq <= 60 || freq >= 1500) { flush(); continue; }
      const midi = 12 * Math.log2(freq / 440) + 69;
      if (midi < MIDI_MIN || midi > MIDI_MAX) { flush(); continue; }

      const color = getColor(i, freq);
      if (color !== curColor && d) flush();
      curColor = color;

      const nextFreq = values[i + 1];
      const isSegEnd = nextFreq === null || nextFreq <= 60;
      if (!d || isSegEnd || i % stride === 0) {
        const x = (i / frameHz + lrcOffsetSec) * PX_PER_SEC;
        const y = midiToY(midi);
        d += d ? ` L${x.toFixed(1)} ${y.toFixed(1)}` : `M${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    }
    flush();
    return nodes;
  }, [userF0, activeMode, midiSegments, timelineScores, lrcOffsetSec, guideOffset]);

  const nearestSegStart = (tSec: number): number => {
    if (!midiSegments.length) return tSec;
    let best = midiSegments[0], bestDist = Math.abs(midiSegments[0].start - tSec);
    for (const s of midiSegments) {
      const d = Math.abs(s.start - tSec);
      if (d < bestDist) { bestDist = d; best = s; }
    }
    return best.start;
  };

  const scrollH = timelineScores.length > 0 ? GUIDE_H + LRC_H : GUIDE_H;
  return (
    <ScrollView ref={scrollRef} horizontal showsHorizontalScrollIndicator={false}
      style={[tlStyles.scroll, { height: scrollH, maxHeight: scrollH }]}
    >
      <View style={{ width: totalW, height: scrollH }}>
        <Svg width={totalW} height={GUIDE_H} style={{ backgroundColor: COLORS.surface, height: GUIDE_H }}>
          {midiSegments.map((s, i) => (
            <Line key={i}
              x1={s.start * PX_PER_SEC} y1={midiToY(s.midi)}
              x2={s.end   * PX_PER_SEC} y2={midiToY(s.midi)}
              stroke="#938ea1" strokeWidth={6} strokeLinecap="round"
            />
          ))}
          {f0Paths}
        </Svg>
        {timelineScores.length > 0 && (
          <View style={{ width: totalW, height: LRC_H, backgroundColor: '#1a1a2e', position: 'relative' }}>
            {timelineScores.map((chunk, i) => chunk.lrcText.trim() ? (
              <View key={i} style={{
                position: 'absolute',
                left: nearestSegStart(chunk.startSec) * PX_PER_SEC,
                top: 10,
                backgroundColor: '#2a2a3e',
                borderRadius: 8,
                paddingHorizontal: 8,
                paddingVertical: 4,
              }}>
                <Text style={{ fontSize: 11, color: '#ffffff' }}>
                  {chunk.lrcText.trim()}
                </Text>
              </View>
            ) : null)}
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const tlStyles = StyleSheet.create({
  scroll: { borderTopWidth: 1, borderTopColor: COLORS.divider, flexGrow: 0 },
});

// ─── Color legend ───
const ZONE_LEGEND = [
  { color: COLOR_APPROPRIATE, label: '적절 (2~3)' },
  { color: COLOR_WARNING, label: '미달/과함 (0~1, 4~5)' },
  { color: COLOR_LOW_CONFIDENCE, label: '신뢰도 낮음' },
  { color: COLOR_DATA_MISSING, label: '데이터 없음' },
];
const LEGEND_ITEMS: Record<VisualizationMode, Array<{ color: string; label: string }>> = {
  pitch: [
    { color: COLOR_APPROPRIATE, label: '정확 (≤0.5반음)' },
    { color: '#ffb780', label: '살짝 어긋남 (≤1.0)' },
    { color: COLOR_WARNING, label: '틀림 (>1.0반음)' },
    { color: COLOR_DATA_MISSING, label: '가이드 없음' },
  ],
  breathiness:      ZONE_LEGEND,
  vocalFoldContact: ZONE_LEGEND,
  softPalate:       ZONE_LEGEND,
  tongueTension:    ZONE_LEGEND,
};

function LegendRow({ activeMode }: { activeMode: VisualizationMode }) {
  const items = LEGEND_ITEMS[activeMode] ?? [];
  return (
    <View style={lgStyles.row}>
      {items.map((item, i) => (
        <View key={i} style={lgStyles.item}>
          <View style={[lgStyles.dot, { backgroundColor: item.color }]} />
          <Text style={lgStyles.label}>{item.label}</Text>
        </View>
      ))}
    </View>
  );
}

const lgStyles = StyleSheet.create({
  row:   { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: SPACING.base, paddingVertical: 6, gap: SPACING.sm, backgroundColor: COLORS.background, borderBottomWidth: 1, borderBottomColor: COLORS.divider },
  item:  { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot:   { width: 8, height: 8, borderRadius: 4 },
  label: { fontSize: 10, color: COLORS.textSecondary },
});

// ─── Main screen ───
export default function EvalResultScreen({ route, navigation }: Props) {
  const { runId, songId } = route.params ?? {};
  const [result, setResult]     = useState<AnalyzeResult | null>(null);
  const [midiSegs, setMidiSegs] = useState<RawSeg[]>([]);
  const [loading, setLoading]   = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [tab, setTab]               = useState<Tab>('basic');
  const [activeMode, setActiveMode] = useState<VisualizationMode>('pitch');
  const [lrcOffsetSec, setLrcOffsetSec] = useState(0);

  useEffect(() => {
    getResultsByRunId(runId)
      .then(data => {
        setResult(data);
        setLoading(false);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : '결과를 불러올 수 없습니다.';
        setErrorMsg(msg);
        setLoading(false);
      });
  }, [runId]);

  useEffect(() => {
    if (!songId || !result) return;
    getSongMidiSegmentsRaw(songId)
      .then(({ segments, lrcOffsetSec: offset }) => {
        setMidiSegs(segments);
        setLrcOffsetSec(offset);
      })
      .catch((e) => { if (__DEV__) console.warn('[EvalResult] midiSegs fetch failed:', e); });
  }, [songId, result]);

  const guideOffset = SONG_GUIDE_OFFSETS[songId ?? ''] ?? 0;

  const { pitchPct, rhythmPct } = useMemo(() => {
    const f0 = result?.userF0;
    if (!f0?.values?.length || !midiSegs.length) return { pitchPct: null, rhythmPct: null };
    const { frameHz, values } = f0;

    // 음정 정확도: voiced 프레임 중 1.0반음 이내 비율
    let inPitch = 0, voicedTotal = 0;
    for (let i = 0; i < values.length; i++) {
      const freq = values[i];
      if (freq === null || freq <= 60 || freq >= 1500) continue;
      voicedTotal++;
      const tMaster = i / frameHz + lrcOffsetSec;
      const midi    = 12 * Math.log2(freq / 440) + 69;
      let minDist = Infinity, nearestMidi = 0;
      for (const s of midiSegs) {
        const sA = s.start + guideOffset, eA = s.end + guideOffset;
        const d  = tMaster >= sA && tMaster <= eA ? 0
          : Math.min(Math.abs(tMaster - sA), Math.abs(tMaster - eA));
        if (d < minDist) { minDist = d; nearestMidi = s.midi; }
      }
      if (minDist <= 1.5 && Math.abs(midi - nearestMidi) < 1.0) inPitch++;
    }
    const pitchPct = voicedTotal > 0 ? Math.round(inPitch / voicedTotal * 100) : null;

    // 박자 정확도 (옵션 B): 각 segment 시작점 ±0.3s 내 voiced 여부
    const ONSET_WIN = 0.3;
    let onTime = 0;
    for (const s of midiSegs) {
      const tMr    = (s.start + guideOffset) - lrcOffsetSec;
      const iStart = Math.max(0, Math.floor((tMr - ONSET_WIN) * frameHz));
      const iEnd   = Math.min(values.length - 1, Math.ceil((tMr + ONSET_WIN) * frameHz));
      for (let i = iStart; i <= iEnd; i++) {
        const freq = values[i];
        if (freq !== null && freq > 60 && freq < 1500) { onTime++; break; }
      }
    }
    const rhythmPct = midiSegs.length > 0 ? Math.round(onTime / midiSegs.length * 100) : null;

    return { pitchPct, rhythmPct };
  }, [result, midiSegs, lrcOffsetSec, guideOffset]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>
          {runId ? '분석 결과 조회 중...' : '분석 중...'}
        </Text>
      </View>
    );
  }

  if (errorMsg || !result) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{errorMsg ?? '결과를 불러올 수 없습니다.'}</Text>
      </View>
    );
  }

  // v2 카드 순서 (정우 신규 spec):
  //   기본 탭 (4 active):  breathiness / vocal_fold_contact / soft_palate / tongue_tension
  //   고급 탭 (5 inactive): nasal_oral_ratio / chest_head_voice / forward_resonance / pressure_balance / larynx_tongue_root
  const BASIC_V2:    EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact', 'soft_palate', 'tongue_tension'];
  const ADVANCED_V2: EvaluationItemKey[] = ['nasal_oral_ratio', 'chest_head_voice', 'forward_resonance', 'pressure_balance', 'larynx_tongue_root'];

  const isV2 = result.scoreMapperVersion === 'v2';
  const basicItems: EvaluationItemKey[] = isV2
    ? BASIC_V2
    : [...BASE_ITEMS, ...FOCUS_ITEMS_FROM_USER.filter(k => !BASE_ITEMS.includes(k))];
  const advancedItems: EvaluationItemKey[] = isV2
    ? ADVANCED_V2
    : [
        ...result.reliability.high_reliability,
        ...result.reliability.medium_reliability,
        ...result.reliability.unavailable,
      ];
  const shownStripped: EvaluationItemKey[] = result.scoreMapperVersion === 'v2' && result.reliability.shownV2
    ? result.reliability.shownV2
    : (result.timelineMetadata?.shownIndicators ?? [])
        .map(s => s.replace(/^\d+_/, '') as EvaluationItemKey);
  const activeTimelineMode: VisualizationMode =
    activeMode === 'pitch'
    || result.scoreMapperVersion !== 'v2'
    || (isTimelineIndicatorMode(activeMode) && shownStripped.includes(TIMELINE_MODE_CONFIG[activeMode].appKey))
      ? activeMode
      : 'pitch';

  const renderCard = (key: EvaluationItemKey) => {
    const meta       = EVALUATION_ITEMS.find(m => m.key === key)!;
    const scoreEntry = result.scores[key];
    const fb         = result.feedback[key];
    const nameKo     = fb?.name_ko ?? meta.nameKo;
    const timelineMode = getTimelineModeForAppKey(key);
    const timelineConfig = timelineMode ? TIMELINE_MODE_CONFIG[timelineMode] : null;
    const scoreMeta = getMappedScoreMeta(result.scoresMeta, key, timelineConfig);
    const v2Score = typeof scoreMeta?.roundedScore === 'number'
      ? scoreMeta.roundedScore
      : getMappedNumber(result.scoresV2, key, timelineConfig);
    const hasV2Score = result.scoreMapperVersion === 'v2' && typeof v2Score === 'number';
    const score = hasV2Score ? v2Score : (scoreEntry?.ai_score ?? null);
    const zone = hasV2Score ? deriveZoneFromRoundedScore(v2Score) : (scoreEntry?.zone ?? null);
    const confidence: ConfidenceLevel = hasV2Score ? 'high' : (scoreEntry?.confidence ?? meta.defaultConfidence);

    // 9항목 모두 동적 분기 — v2 분기: reliability.shownV2 우선, fallback: timelineMetadata.shownIndicators
    // SectionList/Training 코어는 v2 4항목 지원
    const SUPPORTED: EvaluationItemKey[] = ['breathiness', 'vocal_fold_contact', 'soft_palate', 'tongue_tension'];
    const isShown = shownStripped.includes(key);
    const trainDisabled = !isShown;
    const onTrainPress = () => {
      if (trainDisabled) {
        Alert.alert('곧 출시', '데이터 수집 후 활성화 예정입니다.');
        return;
      }
      if (!SUPPORTED.includes(key)) {
        Alert.alert('준비 중', '이 항목은 훈련 화면이 아직 준비되지 않았습니다.');
        return;
      }
      const indicatorKey = key as IndicatorAppKey;
      if (!songId) {
        Alert.alert('곡 정보 없음', '이 결과는 구간 훈련에 필요한 곡 정보가 없습니다.');
        return;
      }
      const weakSections = extractWeakSections(
        result.timelineScores ?? [],
        indicatorKey,
        result.audio_info?.duration_sec,
      );
      if (weakSections.length === 0) {
        Alert.alert('연습 구간 없음', '이 항목에서 바로 연습할 약점 구간이 없습니다.');
        return;
      }
      navigation.navigate('SectionList' as never, {
        indicatorKey,
        weakSections,
        feedbackText: fb?.feedback_text ?? '',
        runId,
        songId,
        sessionId: result.session_id,
      } as never);
    };

    return (
      <EvalItemCard
        key={key}
        itemKey={key}
        nameKo={nameKo}
        score={score}
        zone={zone}
        confidence={confidence}
        feedbackText={fb?.feedback_text ?? ''}
        scoreDescription={fb?.score_description}
        isFocus={FOCUS_ITEMS_FROM_USER.includes(key)}
        onTrainPress={onTrainPress}
        trainDisabled={trainDisabled}
        tier={scoreMeta?.tier}
        tooltip={scoreMeta?.tooltip}
        isHighlighted={key === 'breathiness' && result.scoreMapperVersion === 'v2'}
        isDimmed={result.scoreMapperVersion === 'v2' && trainDisabled}
      />
    );
  };

  const showTimeline = !!songId; // songId 있으면 guide lines 항상 표시 (timeline_scores 길이 무관)

  return (
    <View style={styles.container}>
      {/* 헤더 */}
      <View style={styles.headerBar}>
        <Text style={styles.headerTitle}>평가 결과</Text>
        <Text style={styles.headerMeta}>
          처리 시간 {result.processing_time_ms}ms · {result.audio_info?.duration_sec?.toFixed(1) ?? '-'}초
          {runId ? ` · ${runId.slice(0, 8)}…` : ' · mock'}
        </Text>
      </View>

      {/* 타임라인 시각화 */}
      {showTimeline && (
        <TimelineSection
          timelineScores={result.timelineScores ?? []}
          midiSegments={midiSegs}
          userF0={result.userF0 ?? null}
          activeMode={activeTimelineMode}
          lrcOffsetSec={lrcOffsetSec}
          guideOffset={guideOffset}
        />
      )}

      {/* 모드 버튼 */}
      {showTimeline && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}
          style={[styles.modeBtnRow, { maxHeight: 36 }]}
          contentContainerStyle={{ paddingHorizontal: SPACING.base, alignItems: 'center', paddingVertical: 4 }}
        >
          {MODE_BUTTONS.map(btn => {
            const mode = btn.id as VisualizationMode;
            const isShownMode = mode === 'pitch'
              || result.scoreMapperVersion !== 'v2'
              || (isTimelineIndicatorMode(mode) && shownStripped.includes(TIMELINE_MODE_CONFIG[mode].appKey));
            const effectiveActive = btn.active
              && (!btn.v2Only || result.scoreMapperVersion === 'v2')
              && isShownMode;
            return (
              <TouchableOpacity
                key={btn.id}
                activeOpacity={effectiveActive ? 0.7 : 1}
                style={[
                  styles.modeBtn,
                  effectiveActive && mode === activeTimelineMode && styles.modeBtnActive,
                  !effectiveActive && styles.modeBtnDisabled,
                ]}
                onPress={() => { if (effectiveActive) setActiveMode(mode); }}
              >
                <Text style={[
                  styles.modeBtnLabel,
                  effectiveActive && mode === activeTimelineMode && styles.modeBtnLabelActive,
                  !effectiveActive && styles.modeBtnLabelDisabled,
                ]}>
                  {btn.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {/* 색상 범례 */}
      {showTimeline && <LegendRow activeMode={activeTimelineMode} />}

      <ScrollView style={{ flex: 1 }}>
      {/* 음정·박자 점수 */}
      {showTimeline && (pitchPct !== null || rhythmPct !== null) && (
        <View style={styles.scoreCardsRow}>
          {pitchPct !== null && (
            <View style={styles.scoreCard}>
              <Text style={[styles.scoreCardPct, { color: scoreColor(pitchPct) }]}>{pitchPct}%</Text>
              <Text style={styles.scoreCardLabel}>음정 정확도</Text>
            </View>
          )}
          {rhythmPct !== null && (
            <View style={styles.scoreCard}>
              <Text style={[styles.scoreCardPct, { color: scoreColor(rhythmPct) }]}>{rhythmPct}%</Text>
              <Text style={styles.scoreCardLabel}>박자 정확도</Text>
            </View>
          )}
        </View>
      )}

      {/* 안내 문구 (v2 분기로 4항목 안내) */}
      {showTimeline && (
        <Text style={styles.timelineInfo}>
          {result.scoreMapperVersion === 'v2'
            ? '이 시각화는 호흡 소리 + 성대 접촉 강도 + 연구개 위치 + 혀 경직도 4가지 기준입니다.'
            : '이 시각화는 호흡 소리 + 성대 접촉 강도 2가지 기준입니다.'}{'\n'}
          (다른 항목은 신뢰도가 충분히 높지 않아 시간 구간 표시 X)
        </Text>
      )}

      {/* 탭 */}
      <View style={styles.tabRow}>
        {(['basic', 'advanced'] as Tab[]).map(t => (
          <TouchableOpacity
            key={t}
            style={[styles.tabBtn, tab === t && styles.tabBtnActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabLabel, tab === t && styles.tabLabelActive]}>
              {t === 'basic' ? '기본' : '고급'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

        <View style={styles.scroll}>
          {tab === 'basic'
            ? basicItems.map(renderCard)
            : advancedItems.map(renderCard)
          }
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  center: {
    flex: 1, backgroundColor: COLORS.background,
    justifyContent: 'center', alignItems: 'center', gap: SPACING.sm,
  },
  loadingText:  { ...TYPOGRAPHY.body, color: COLORS.textSecondary },
  errorText:    { ...TYPOGRAPHY.body, color: COLORS.danger, textAlign: 'center', paddingHorizontal: 24 },
  headerBar:    { paddingHorizontal: SPACING.base, paddingTop: SPACING.base, paddingBottom: SPACING.sm },
  headerTitle:  { ...TYPOGRAPHY.heading, color: COLORS.textPrimary },
  headerMeta:   { ...TYPOGRAPHY.caption, color: COLORS.textMuted, marginTop: 2 },
  timelineInfo: {
    paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm,
    fontSize: 11, color: COLORS.textMuted, lineHeight: 17,
    borderBottomWidth: 1, borderBottomColor: COLORS.divider,
  },
  tabRow: {
    flexDirection: 'row',
    borderBottomWidth: 1, borderBottomColor: COLORS.divider,
    marginHorizontal: SPACING.base,
  },
  tabBtn:         { paddingVertical: SPACING.sm, paddingHorizontal: SPACING.base, marginRight: SPACING.sm },
  tabBtnActive:   { borderBottomWidth: 2, borderBottomColor: COLORS.primary },
  tabLabel:       { ...TYPOGRAPHY.body, color: COLORS.textMuted },
  tabLabelActive: { color: COLORS.primary, fontWeight: '600' },
  scroll:               { padding: SPACING.base, paddingBottom: SPACING.xl },
  modeBtnRow:           { height: 36, borderBottomWidth: 1, borderBottomColor: COLORS.divider, flexGrow: 0 },
  modeBtn:              { flexShrink: 0, height: 28, paddingHorizontal: 9, borderRadius: 14, marginRight: 8, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.divider, justifyContent: 'center', alignItems: 'center' },
  modeBtnActive:        { backgroundColor: '#6C63FF33', borderColor: '#6C63FF' },
  modeBtnDisabled:      { opacity: 0.35 },
  modeBtnLabel:         { fontSize: 12, color: '#D0D0D0' },
  modeBtnLabelActive:   { color: '#a78bfa', fontWeight: '600' },
  modeBtnLabelDisabled: { color: '#888888' },
  scoreCardsRow:        { flexDirection: 'row', paddingHorizontal: SPACING.base, paddingVertical: SPACING.sm, gap: SPACING.base },
  scoreCard:            { flex: 1, alignItems: 'center', backgroundColor: COLORS.surface, borderRadius: 10, paddingVertical: SPACING.sm },
  scoreCardPct:         { fontSize: 22, fontWeight: '700' },
  scoreCardLabel:       { fontSize: 11, color: COLORS.textMuted, marginTop: 2 },
});
