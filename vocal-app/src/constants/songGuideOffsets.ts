// Per-song MIDI guide timing offset (seconds to ADD to all segment start/end).
// Negative shifts guide earlier (compensates positionMillis → speaker latency).
// Adjust after device verification.
export const SONG_GUIDE_OFFSETS: Record<string, number> = {
  '004': -0.3, // 김범수: 전 구간 평균 오차 최소값; verified 2026-05-05
};
