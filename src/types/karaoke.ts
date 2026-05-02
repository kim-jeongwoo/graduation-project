// ─── Server raw types (as returned by API) ───

export interface ServerLrcLine {
  time_start: number;
  time_end: number;
  text: string;
}

export interface ServerPitchPoint {
  t: number;      // seconds, master timeline
  freq: number | null;
  midi: number | null;
  voiced: boolean;
  conf: number;   // CREPE confidence 0~1
}

export interface ServerPitchGuide {
  song_id: string;
  lrc_offset_sec: number;  // t_mr = t_master - lrc_offset_sec
  points: ServerPitchPoint[];
}

// ─── Domain types (all timestamps in MR playback time) ───

export interface LyricLine {
  timeStart: number;  // seconds, MR-relative
  timeEnd: number;
  text: string;
}

export interface PitchPoint {
  t: number;           // seconds, MR-relative
  freq: number | null;
  midi: number | null;
  voiced: boolean;
  conf: number;
}

export interface PitchGuide {
  songId: string;
  lrcOffsetSec: number;
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
    songId:        raw.song_id,
    lrcOffsetSec:  offset,
    points: raw.points.map((p) => ({
      t:      p.t - offset,
      freq:   p.freq,
      midi:   p.midi,
      voiced: p.voiced,
      conf:   p.conf,
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
