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
    if (!entry || entry.zone === 'appropriate') continue;
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
      zone:           entry.zone,
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
