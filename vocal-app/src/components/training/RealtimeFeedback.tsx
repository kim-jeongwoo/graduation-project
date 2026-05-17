import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../../utils/colors';
import { SPACING, TYPOGRAPHY } from '../../theme/tokens';
import type { Zone } from '../../types/analyze';

// ─── 음정 ───
export type PitchVerdict = 'accurate' | 'slight_off' | 'wrong' | 'unknown';
export type PitchLiveStatus =
  | 'idle'
  | 'serverConnecting'
  | 'serverUnavailable'
  | 'micWaiting'
  | 'noVoice'
  | 'active';
export type VoiceInputStatus = 'idle' | 'leadIn' | 'waiting' | 'weak' | 'ready' | 'noVoice';

export function pitchVerdictFromScore(score: number | null): PitchVerdict {
  if (score === null) return 'unknown';
  if (score >= 0.92) return 'accurate';
  if (score >= 0.7)  return 'slight_off';
  return 'wrong';
}

const PITCH_COLOR: Record<PitchVerdict, string> = {
  accurate:   '#59dda5',
  slight_off: '#ffb780',
  wrong:      '#ffb4ab',
  unknown:    COLORS.textMuted,
};

const PITCH_TEXT: Record<PitchVerdict, string> = {
  accurate:   '정확해요',
  slight_off: '조금 더 정확하게',
  wrong:      '음정이 어긋났어요',
  unknown:    '측정 중...',
};

const PITCH_STATUS_TEXT: Record<PitchLiveStatus, string> = {
  idle:              '시작하면 실시간 음정이 표시됩니다.',
  serverConnecting:  '실시간 분석 연결 중...',
  serverUnavailable: '실시간 분석 연결이 불안정합니다. 사후 측정은 계속 진행할 수 있습니다.',
  micWaiting:        '마이크 입력을 기다리는 중입니다.',
  noVoice:           '음성이 감지되지 않습니다. 조금 더 크게 불러보세요.',
  active:            '',
};

const VOICE_INPUT_TEXT: Record<VoiceInputStatus, string> = {
  idle:    '시작하면 입력 상태가 표시됩니다.',
  leadIn:  '곧 녹음이 시작됩니다.',
  waiting: '입력 대기 중',
  weak:    '음성은 감지되지만 분석에는 부족할 수 있습니다.',
  ready:   '입력이 충분한 것으로 추정됩니다.',
  noVoice: '입력이 부족합니다. 조금 더 크게 불러보세요.',
};

const VOICE_INPUT_COLOR: Record<VoiceInputStatus, string> = {
  idle:    COLORS.textMuted,
  leadIn:  COLORS.textMuted,
  waiting: COLORS.textMuted,
  weak:    '#ffb780',
  ready:   '#59dda5',
  noVoice: '#ffb4ab',
};

interface PitchCardProps {
  verdict: PitchVerdict;
  matchScore: number | null;  // 0~1
  liveStatus?: PitchLiveStatus;
}

export function PitchCard({ verdict, matchScore, liveStatus = 'active' }: PitchCardProps) {
  const color = PITCH_COLOR[verdict];
  const statusText = PITCH_STATUS_TEXT[liveStatus];
  const text  = liveStatus === 'active' ? PITCH_TEXT[verdict] : statusText;
  const fillPct = matchScore !== null ? Math.max(0, Math.min(1, matchScore)) * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 음정 일치율</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.verdictText, { color }]}>{text}</Text>
    </View>
  );
}

interface VoiceInputCardProps {
  status: VoiceInputStatus;
  level: number;  // 0~1
  durationSec: number | null;
}

export function VoiceInputCard({ status, level, durationSec }: VoiceInputCardProps) {
  const color = VOICE_INPUT_COLOR[status];
  const fillPct = Math.max(0, Math.min(1, level)) * 100;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>입력 상태</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <View style={styles.row}>
        <Text style={[styles.verdictText, { color }]}>{VOICE_INPUT_TEXT[status]}</Text>
        {durationSec !== null && (
          <Text style={styles.scoreText}>{durationSec.toFixed(1)}초</Text>
        )}
      </View>
      <Text style={styles.helpText}>입력 상태는 최근 음량/음성 여부, 음정 일치율은 피치 정확도를 나타냅니다.</Text>
    </View>
  );
}

// ─── 호흡 ───
const BREATH_COLOR: Record<Zone | 'unknown', string> = {
  appropriate:  '#59dda5',
  excessive:    '#ffb4ab',  // 압축됨 — 빨강
  insufficient: '#ffb4ab',  // 호흡 새는 소리 — 빨강
  unknown:      COLORS.textMuted,
};

const BREATH_TEXT: Record<Zone | 'unknown', string> = {
  appropriate:  '호흡 지표 적절',
  excessive:    '호흡 지표가 높아요',
  insufficient: '호흡 지표가 낮아요',
  unknown:      '측정 중...',
};

interface BreathCardProps {
  zone:    Zone | null;     // null이면 "측정 중"
  aiScore: number | null;
}

export function BreathCard({ zone, aiScore }: BreathCardProps) {
  const key   = (zone ?? 'unknown') as Zone | 'unknown';
  const color = BREATH_COLOR[key];
  const text  = BREATH_TEXT[key];
  // 게이지: ai_score (0~5) 비율로 표시
  const fillPct = aiScore !== null ? Math.max(0, Math.min(5, aiScore)) / 5 * 100 : 0;
  return (
    <View style={styles.card}>
      <Text style={styles.label}>실시간 호흡</Text>
      <View style={styles.gaugeTrack}>
        <View style={[styles.gaugeFill, { width: `${fillPct}%`, backgroundColor: color }]} />
      </View>
      <View style={styles.row}>
        <Text style={[styles.verdictText, { color }]}>{text}</Text>
        {aiScore !== null && (
          <Text style={styles.scoreText}>{aiScore.toFixed(2)}점</Text>
        )}
      </View>
    </View>
  );
}

// ─── 호흡 안내 (vocal_fold_contact 진입 시 BreathCard 자리에 표시) ───
export function BreathInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>성대 접촉 강도</Text>
      <Text style={styles.infoText}>
        성대 접촉은 녹음 종료 후 측정됩니다.{'\n'}
        노래 끝나면 '이번 시도 점수 보기' 버튼을 눌러주세요.
      </Text>
    </View>
  );
}

export function SoftPalateInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>연구개 위치</Text>
      <Text style={styles.infoText}>
        연구개 위치 지표는 녹음 종료 후 측정됩니다. 같은 구간을 다시 부르며 결과 변화를 확인해보세요.
      </Text>
    </View>
  );
}

export function TongueTensionInfoCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>혀경직도</Text>
      <Text style={styles.infoText}>
        혀/구강 공간 경직도 지표는 녹음 종료 후 측정됩니다. 같은 구간을 다시 부르며 결과 변화를 확인해보세요.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 10,
    padding: SPACING.base,
    marginHorizontal: SPACING.base,
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  label: {
    fontSize: 11,
    color: COLORS.textSecondary,
  },
  gaugeTrack: {
    height: 10,
    backgroundColor: COLORS.cardBorder,
    borderRadius: 5,
    overflow: 'hidden',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: 5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  verdictText: {
    ...TYPOGRAPHY.body,
    fontWeight: '700',
  },
  scoreText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    fontWeight: '600',
  },
  infoText: {
    ...TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 20,
  },
  helpText: {
    fontSize: 11,
    color: COLORS.textMuted,
    lineHeight: 16,
  },
});
