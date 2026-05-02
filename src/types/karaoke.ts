// ─── Server raw types (as returned by API) ───

export interface ServerLrcLine {
  time_start: number;
  time_end: number;
  text: string;
}

export interface ServerPitchPoint {
  time: number;          // seconds, master timeline (was mistakenly assumed 't')
  midi: number | null;
  freq_hz: number | null; // (was mistakenly assumed 'freq')
  voiced: boolean;
  confidence: number;    // CREPE confidence 0~1 (was mistakenly assumed 'conf')
}

export interface ServerPitchGuide {
  song_id: string;
  duration_sec: number;
  frame_hz: number;
  alignment_status: string;
  lrc_offset_sec: number;  // t_mr = t_master - lrc_offset_sec
  review_segments: unknown[];
  points: ServerPitchPoint[];
}

// ─── Domain types (all timestamps in MR playback time) ───

export interface LyricLine {
  timeStart: number;  // seconds, MR-relative
  timeEnd: number;
  text: string;
}

export interface PitchPoint {
  time: number;           // seconds, MR-relative (camelCase matches server 'time')
  midi: number | null;
  freqHz: number | null;  // camelCase of server 'freq_hz'
  voiced: boolean;
  confidence: number;     // camelCase matches server 'confidence'
}

export interface PitchGuide {
  songId: string;
  durationSec: number;
  frameHz: number;
  alignmentStatus: string;
  lrcOffsetSec: number;
  reviewSegments: unknown[];
  points: PitchPoint[];  // all timestamps already converted to MR time
}

// ─── Adapters: master-time → MR-time ───

export function adaptLrc(raw: ServerLrcLine[], lrcOffsetSec: number): LyricLine[] {
  return raw.map((l) => ({
    timeStart: l.time_start - lrcOffsetSec,
    timeEnd:   l.time_end   - lrcOffsetSec,
    text:      l.text,
  }));
}

export function adaptPitchGuide(raw: ServerPitchGuide): PitchGuide {
  const offset = raw.lrc_offset_sec;
  return {
    songId:          raw.song_id,
    durationSec:     raw.duration_sec,
    frameHz:         raw.frame_hz,
    alignmentStatus: raw.alignment_status,
    lrcOffsetSec:    offset,
    reviewSegments:  raw.review_segments,
    points: raw.points.map((p) => ({
      time:       p.time - offset,   // convert master-time → MR-time
      midi:       p.midi,
      freqHz:     p.freq_hz,
      voiced:     p.voiced,
      confidence: p.confidence,
    })),
  };
}

// ─── Pitch utilities ───

export type PitchAccuracy = 'accurate' | 'slight_off' | 'wrong';

export function getPitchAccuracy(userMidi: number, guideMidi: number): PitchAccuracy {
  const diff = Math.abs(userMidi - guideMidi);
  if (diff <= 0.5) return 'accurate';
  if (diff <= 1.0) return 'slight_off';
  return 'wrong';
}

export function midiToNoteName(midi: number): string {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const octave = Math.floor(midi / 12) - 1;
  return `${names[Math.round(midi) % 12]}${octave}`;
}

export function generateFakeUserPitch(guidePoints: PitchPoint[]): PitchPoint[] {
  return guidePoints.map((p) => {
    if (p.midi === null || !p.voiced) return { ...p };
    const r = Math.random();
    let offset: number;
    if (r < 0.7)       offset = (Math.random() - 0.5) * 0.8;
    else if (r < 0.9)  offset = (Math.random() - 0.5) * 1.4;
    else               offset = (Math.random() - 0.5) * 3.0;
    return { ...p, midi: p.midi + offset };
  });
}
