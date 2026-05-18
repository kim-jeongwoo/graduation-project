import type { TimelineChunkScore, Zone } from '../types/analyze';

// 앱 내부 키 (EvaluationItemKey와 동일 형식, prefix 제거 snake_case)
export type IndicatorAppKey = 'breathiness' | 'vocal_fold_contact' | 'soft_palate' | 'tongue_tension';

// timeline_scores 내부 키 (camelCase) 매핑 — v2 4항목
const APP_TO_TIMELINE: Record<IndicatorAppKey, 'breathiness' | 'vocalFoldContact' | 'softPalate' | 'tongueTension'> = {
  breathiness:         'breathiness',
  vocal_fold_contact:  'vocalFoldContact',
  soft_palate:         'softPalate',
  tongue_tension:      'tongueTension',
};

export const INDICATOR_LABELS: Record<IndicatorAppKey, string> = {
  breathiness:         '호흡소리식별',
  vocal_fold_contact:  '성대접촉강도',
  soft_palate:         '연구개위치',
  tongue_tension:      '혀경직도',
};

export const ZONE_LABELS: Record<Zone, string> = {
  excessive:    '과함',
  insufficient: '미달',
  appropriate:  '적절',
};

export const SECTION_FEEDBACK_BY_ZONE: Record<IndicatorAppKey, Record<Zone, string>> = {
  breathiness: {
    insufficient: '숨소리가 많이 섞이고 발성 밀도가 약한 경향이 보입니다. 소리가 지나치게 새지 않는지 확인해 볼 수 있습니다.',
    appropriate:  '호흡감과 발성 밀도가 자연스럽게 섞인 상태로 보입니다. 현재의 균형감을 유지하는 데 도움이 될 수 있습니다.',
    excessive:    '숨소리가 거의 없거나 소리가 지나치게 눌리고 압축된 경향이 보입니다. 소리가 답답하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  vocal_fold_contact: {
    insufficient: '성대 접촉이 약해 소리가 가볍거나 힘이 덜 실릴 수 있는 경향이 보입니다. 소리의 중심이 안정적으로 모이는지 확인해 볼 수 있습니다.',
    appropriate:  '성대 접촉이 비교적 안정적이고 소리가 자연스럽게 유지되는 경향이 보입니다. 현재의 접촉감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '성대 접촉이 강하거나 눌린 느낌이 생길 수 있는 경향이 보입니다. 힘이 과하게 모이지 않는지 확인해 볼 수 있습니다.',
  },
  soft_palate: {
    insufficient: '입 안쪽 공간이 좁아지거나 소리가 답답하게 느껴질 수 있는 경향이 보입니다. 공간이 자연스럽게 열리는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '입 안쪽 공간과 연구개 위치가 비교적 안정적인 경향이 보입니다. 현재의 편안한 공명감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '입천장 뒤쪽이나 목 주변에 힘이 과하게 들어갈 수 있는 경향이 보입니다. 과하게 들어 올리려 하기보다 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
  tongue_tension: {
    insufficient: '발음 지지가 약해 소리가 흐리거나 덜 또렷하게 느껴질 수 있는 경향이 보입니다. 필요한 만큼만 또렷하게 사용하는 느낌을 확인해 볼 수 있습니다.',
    appropriate:  '혀와 구강 공간의 긴장도가 비교적 자연스럽고 발음이 안정적인 경향이 보입니다. 현재의 유연한 발음감을 이어가는 데 도움이 될 수 있습니다.',
    excessive:    '혀, 턱, 입 안쪽에 힘이 많이 들어가 소리가 뭉개지거나 경직될 수 있는 경향이 보입니다. 혀끝과 턱 주변의 힘을 덜어내는 방향을 확인해 볼 수 있습니다.',
  },
};

export interface WeakSection {
  chunkIndex:     number;  // timeline_scores 원본 인덱스 (chunk_meta echo용)
  paddedStartSec: number;  // 패딩 적용된 연습 시작 시간 (앞 패딩)
  paddedEndSec:   number;  // 패딩 적용된 연습 끝 시간 (뒤 패딩)
  startSec:       number;  // 원본 chunk 시작
  endSec:         number;  // 원본 chunk 끝
  lrcText:        string;
  aiScore:        number;
  zone:           Zone;
  lowConfidenceItems?: string[];
}

const PAD_START_SEC = 4;
const PAD_END_SEC   = 3;

function deriveZoneFromRoundedScore(roundedScore: number): Zone {
  if (roundedScore <= 1) return 'insufficient';
  if (roundedScore >= 4) return 'excessive';
  return 'appropriate';
}

/**
 * 약점 구간 추출 — zone !== 'appropriate' 필터 + 앞 패딩 4초 / 뒤 패딩 3초
 *  - 앞 패딩: max(0, c.startSec - 4)  (이전 chunk 클램프 제거)
 *  - 뒤 패딩: min(totalDurationSec ?? Infinity, c.endSec + 3)  (다음 chunk 클램프 제거)
 *  - 사용자가 그 구간만 연습하므로 시간 침범 무관
 */
export function extractWeakSections(
  timelineScores: TimelineChunkScore[],
  key: IndicatorAppKey,
  totalDurationSec?: number,
): WeakSection[] {
  const tlKey = APP_TO_TIMELINE[key];
  const out: WeakSection[] = [];
  for (let i = 0; i < timelineScores.length; i++) {
    const c = timelineScores[i];
    const entry = c.scores[tlKey];
    if (!entry || typeof entry.roundedScore !== 'number') continue;
    const zone = deriveZoneFromRoundedScore(entry.roundedScore);
    if (zone === 'appropriate') continue;
    const paddedStart = Math.max(0, c.startSec - PAD_START_SEC);
    const paddedEnd   = Math.min(totalDurationSec ?? Infinity, c.endSec + PAD_END_SEC);
    out.push({
      chunkIndex:     i,
      paddedStartSec: paddedStart,
      paddedEndSec:   paddedEnd,
      startSec:       c.startSec,
      endSec:         c.endSec,
      lrcText:        c.lrcText,
      aiScore:        entry.aiScore,
      zone,
      lowConfidenceItems: c.lowConfidenceItems,
    });
  }
  return sortWeakSections(out);
}

/**
 * 정렬 헬퍼 — excessive 먼저 (aiScore 큰 순), insufficient 그다음 (aiScore 작은 순).
 * 5/10 학원 데이터 기준으로 재조정 가능 — 이 함수만 수정하면 됨.
 */
export function sortWeakSections(sections: WeakSection[]): WeakSection[] {
  return [...sections].sort((a, b) => {
    if (a.zone !== b.zone) {
      if (a.zone === 'excessive')    return -1;
      if (b.zone === 'excessive')    return  1;
    }
    if (a.zone === 'excessive')      return b.aiScore - a.aiScore;
    return a.aiScore - b.aiScore;  // insufficient: 작은 점수가 더 약점
  });
}

export function zoneColor(zone: Zone): string {
  if (zone === 'excessive')    return '#ffb4ab';
  if (zone === 'insufficient') return '#ffb780';
  return '#59dda5';
}
