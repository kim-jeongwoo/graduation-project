// Per-song LRC timestamp correction (seconds to ADD to all LRC timeStart/timeEnd).
// Use when LRC timing doesn't align with the actual vocal onset in midi_segments.
// Positive value shifts lyrics later; negative shifts earlier.
// Add entries after manual verification per song.
export const SONG_LRC_OFFSETS: Record<string, number> = {};
