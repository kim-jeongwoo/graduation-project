/**
 * 음표/음역 관련 유틸리티
 */

export const NOTE_LIST = [
  'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B',
] as const;

export type NoteName = (typeof NOTE_LIST)[number];

/** 음표 문자열 → 절대 인덱스 (C0 = 0, C#0 = 1, ..., C1 = 12, ...) */
export function noteToIndex(note: string): number {
  const match = note.match(/^([A-Ga-g]#?)(\d)$/);
  if (!match) return 0;
  const name = match[1].toUpperCase();
  const octave = parseInt(match[2], 10);
  const semitone = NOTE_LIST.indexOf(name as NoteName);
  if (semitone === -1) return 0;
  return octave * 12 + semitone;
}

/** 절대 인덱스 → 음표 문자열 */
export function indexToNote(index: number): string {
  const octave = Math.floor(index / 12);
  const semitone = index % 12;
  return `${NOTE_LIST[semitone]}${octave}`;
}

/** 주어진 범위의 모든 음표 생성 */
export function generateNoteRange(start: string, end: string): string[] {
  const startIdx = noteToIndex(start);
  const endIdx = noteToIndex(end);
  const notes: string[] = [];
  for (let i = startIdx; i <= endIdx; i++) {
    notes.push(indexToNote(i));
  }
  return notes;
}

/** 음표가 검은 건반(#)인지 */
export function isBlackKey(note: string): boolean {
  return note.includes('#');
}

/** 음표에서 이름만 추출 (옥타브 제거) */
export function getNoteName(note: string): string {
  const match = note.match(/^([A-Ga-g]#?)/);
  return match ? match[1].toUpperCase() : note;
}

// ─── 성부(Voice Type) 분류 ───

interface VoiceRange {
  label: string;
  low: number; // noteToIndex 기준
  high: number;
  midpoint: number;
}

const VOICE_TYPES: VoiceRange[] = [
  // 남성
  { label: '베이스', low: noteToIndex('E2'), high: noteToIndex('E4'), midpoint: 0 },
  { label: '바리톤', low: noteToIndex('A2'), high: noteToIndex('A4'), midpoint: 0 },
  { label: '테너', low: noteToIndex('C3'), high: noteToIndex('C5'), midpoint: 0 },
  // 여성
  { label: '알토', low: noteToIndex('F3'), high: noteToIndex('F5'), midpoint: 0 },
  { label: '메조소프라노', low: noteToIndex('A3'), high: noteToIndex('A5'), midpoint: 0 },
  { label: '소프라노', low: noteToIndex('C4'), high: noteToIndex('C6'), midpoint: 0 },
].map((v) => ({ ...v, midpoint: Math.round((v.low + v.high) / 2) }));

/**
 * 최저음~최고음 기준 성부 분류.
 * 중간값에 가장 가까운 성부를 최대 2개 반환.
 */
export function getVoiceType(low: string, high: string): string {
  const lowIdx = noteToIndex(low);
  const highIdx = noteToIndex(high);
  const userMid = Math.round((lowIdx + highIdx) / 2);

  const sorted = [...VOICE_TYPES].sort(
    (a, b) => Math.abs(a.midpoint - userMid) - Math.abs(b.midpoint - userMid),
  );

  // 가장 가까운 것 + 그 다음 (차이가 3반음 이내면)
  const closest = sorted[0];
  const second = sorted[1];

  if (
    second &&
    Math.abs(second.midpoint - userMid) - Math.abs(closest.midpoint - userMid) <= 3
  ) {
    return `${closest.label} / ${second.label} 범위`;
  }
  return `${closest.label} 범위`;
}

/**
 * 확장 목표 계산
 * direction: "high" → 최고음 +3반음
 *            "low"  → 최저음 -3반음
 *            "both" → 최저음 -2반음, 최고음 +2반음
 */
export function getExpansionTarget(
  low: string,
  high: string,
  direction: 'high' | 'low' | 'both',
): { targetLow: string; targetHigh: string } {
  const lowIdx = noteToIndex(low);
  const highIdx = noteToIndex(high);

  switch (direction) {
    case 'high':
      return { targetLow: low, targetHigh: indexToNote(highIdx + 3) };
    case 'low':
      return { targetLow: indexToNote(lowIdx - 3), targetHigh: high };
    case 'both':
      return {
        targetLow: indexToNote(lowIdx - 2),
        targetHigh: indexToNote(highIdx + 2),
      };
  }
}
