import apiClient, { BASE_URL } from './client';
import type { Song, LyricsData, PitchData } from '../types/api';
import type {
  LyricLine,
  PitchGuide,
  ServerLrcLine,
  ServerMidiSegment,
  ServerPitchGuide,
  ServerPitchPoint,
} from '../types/karaoke';
import { adaptLrc, adaptPitchGuide } from '../types/karaoke';
import { SONG_LRC_OFFSETS } from '../constants/songLrcOffsets';

interface ServerSong {
  id: string;
  title: string;
  artist: string;
  master_duration_sec: number;
  mr_duration_sec: number;
  has_lrc: boolean;
  has_pitch_guide: boolean;
}

const PITCH_GUIDE_TIMEOUT_MS = 45000;
const pitchGuideCache = new Map<string, ServerPitchGuide>();
const pitchGuideRequests = new Map<string, Promise<ServerPitchGuide>>();
const pitchGuideCacheVersions = new Map<string, number>();

function finiteOr(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function optionalFinite(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeServerPitchGuide(payload: unknown): ServerPitchGuide {
  const raw = payload as Record<string, unknown>;
  const pointsRaw = Array.isArray(raw.points) ? raw.points : [];
  const segmentsRaw =
    Array.isArray(raw.midi_segments) ? raw.midi_segments
      : Array.isArray(raw.midiSegments) ? raw.midiSegments
        : [];

  return {
    song_id: String(raw.song_id ?? raw.songId ?? ''),
    duration_sec: finiteOr(raw.duration_sec ?? raw.durationSec, 0),
    frame_hz: finiteOr(raw.frame_hz ?? raw.frameHz, 100),
    alignment_status: String(raw.alignment_status ?? raw.alignmentStatus ?? ''),
    guide_source: typeof (raw.guide_source ?? raw.guideSource) === 'string'
      ? String(raw.guide_source ?? raw.guideSource)
      : undefined,
    lrc_offset_sec: finiteOr(raw.lrc_offset_sec ?? raw.lrcOffsetSec, 0),
    review_segments: Array.isArray(raw.review_segments) ? raw.review_segments
      : Array.isArray(raw.reviewSegments) ? raw.reviewSegments
        : [],
    points: pointsRaw
      .map((item) => {
        const p = item as Record<string, unknown>;
        const time = optionalFinite(p.time ?? p.time_sec ?? p.t);
        if (time === null) return null;
        const midi = optionalFinite(p.midi);
        const freqHz = optionalFinite(p.freq_hz ?? p.freqHz ?? p.freq);
        return {
          time,
          midi,
          freq_hz: freqHz,
          voiced: typeof p.voiced === 'boolean' ? p.voiced : midi !== null,
          confidence: finiteOr(p.confidence ?? p.conf, 1),
        };
      })
      .filter((p): p is ServerPitchPoint => p !== null),
    midi_segments: segmentsRaw
      .map((item) => {
        const s = item as Record<string, unknown>;
        const start = optionalFinite(s.start ?? s.start_sec);
        const end = optionalFinite(s.end ?? s.end_sec);
        const midi = optionalFinite(s.midi);
        if (start === null || end === null || midi === null) return null;
        return {
          start,
          end,
          midi,
          note_name: String(s.note_name ?? s.noteName ?? s.note ?? ''),
        };
      })
      .filter((s): s is ServerMidiSegment => s !== null),
  };
}

export function clearSongPitchGuideCache(songId: string): void {
  const key = String(songId);
  pitchGuideCache.delete(key);
  pitchGuideRequests.delete(key);
  pitchGuideCacheVersions.set(key, (pitchGuideCacheVersions.get(key) ?? 0) + 1);
}

async function getServerPitchGuide(songId: string): Promise<ServerPitchGuide> {
  const key = String(songId);
  const cached = pitchGuideCache.get(key);
  if (cached) return cached;

  const inFlight = pitchGuideRequests.get(key);
  if (inFlight) return inFlight;

  const requestVersion = pitchGuideCacheVersions.get(key) ?? 0;
  const request = apiClient.get<ServerPitchGuide>(`/songs/${key}/pitch-guide`, {
    timeout: PITCH_GUIDE_TIMEOUT_MS,
  })
    .then((res) => {
      const guide = normalizeServerPitchGuide(res.data);
      if ((pitchGuideCacheVersions.get(key) ?? 0) === requestVersion) {
        pitchGuideCache.set(key, guide);
      }
      return guide;
    })
    .finally(() => {
      if (pitchGuideRequests.get(key) === request) {
        pitchGuideRequests.delete(key);
      }
    });
  pitchGuideRequests.set(key, request);
  return request;
}

export async function getSongs(): Promise<Song[]> {
  const res = await apiClient.get<ServerSong[]>('/songs');
  return res.data.map((s) => ({
    id:                s.id,
    title:             s.title,
    artist:            s.artist,
    masterDurationSec: s.master_duration_sec,
    mrDurationSec:     s.mr_duration_sec,
    hasLrc:            s.has_lrc,
    hasPitchGuide:     s.has_pitch_guide,
  }));
}

// LRC: server returns array directly, timestamps in master time
// Adapter converts to MR time using lrcOffsetSec from pitch-guide
export async function getSongLrcRaw(songId: string): Promise<ServerLrcLine[]> {
  const res = await apiClient.get<ServerLrcLine[]>(`/songs/${songId}/lrc`);
  return res.data;
}

function applyClientLrcOffset(songId: string, lyrics: LyricLine[]): LyricLine[] {
  const clientOffset = SONG_LRC_OFFSETS[songId] ?? 0;
  return clientOffset === 0 ? lyrics : lyrics.map((l) => ({
    ...l,
    timeStart: l.timeStart + clientOffset,
    timeEnd:   l.timeEnd   + clientOffset,
  }));
}

// Pitch guide: server returns object with lrc_offset_sec
// Adapter converts all point.t to MR time
export async function getSongPitchGuide(songId: string): Promise<PitchGuide> {
  const raw = await getServerPitchGuide(songId);
  return adaptPitchGuide(raw);
}

// Fetch both LRC and pitch-guide together so offset is applied consistently.
// SONG_LRC_OFFSETS applies an additional per-song client correction to align LRC
// timestamps with the actual vocal onset (midi_segments[0].start).
export async function getSongKaraokeData(
  songId: string,
): Promise<{ lyrics: LyricLine[]; pitchGuide: PitchGuide | null; pitchGuideLoadFailed: boolean }> {
  const rawLrc = await getSongLrcRaw(songId);
  let pitchGuide: PitchGuide | null = null;
  let pitchGuideLoadFailed = false;
  try {
    pitchGuide = await getSongPitchGuide(songId);
  } catch (e) {
    pitchGuideLoadFailed = true;
  }
  const baseLyrics = adaptLrc(rawLrc, pitchGuide?.lrcOffsetSec ?? 0);
  const lyrics = applyClientLrcOffset(songId, baseLyrics);
  return { lyrics, pitchGuide, pitchGuideLoadFailed };
}

export async function getSongKaraokeLyricsOnly(songId: string): Promise<LyricLine[]> {
  const rawLrc = await getSongLrcRaw(songId);
  return applyClientLrcOffset(songId, adaptLrc(rawLrc, 0));
}

// MR streaming URL — Authorization header must be added by caller (expo-av supports headers in loadAsync)
export function getSongMrUrl(songId: string): string {
  return `${BASE_URL}/songs/${songId}/mr`;
}

// EvalResultScreen용: 마스터 기준 raw midi_segments + lrc_offset_sec
// user_f0 시간(MR 기준) → 마스터 시간 변환 시 lrcOffsetSec 사용
export async function getSongMidiSegmentsRaw(
  songId: string,
): Promise<{ segments: Array<{ start: number; end: number; midi: number }>; lrcOffsetSec: number }> {
  const raw = await getServerPitchGuide(songId);
  return {
    segments: (raw.midi_segments ?? []).map((s) => ({ start: s.start, end: s.end, midi: s.midi })),
    lrcOffsetSec: raw.lrc_offset_sec,
  };
}

export async function getSongMidiSegmentsOptional(
  songId: string,
  screen: 'eval' | 'training',
): Promise<{ segments: Array<{ start: number; end: number; midi: number }>; lrcOffsetSec: number } | null> {
  try {
    return await getSongMidiSegmentsRaw(songId);
  } catch {
    return null;
  }
}

// ─── Legacy shims for SessionDetailScreen (deprecated) ───
// Maps new server field names to old LyricsData / PitchData shapes.

/** @deprecated use getSongKaraokeData */
export async function getSongLrc(songId: string): Promise<LyricsData> {
  const raw = await getSongLrcRaw(songId);
  return {
    song_id: songId,
    lines: raw.map((l) => ({
      time_ms: Math.round(l.time_start * 1000),
      end_ms:  Math.round(l.time_end   * 1000),
      text:    l.text,
    })),
  };
}

/** @deprecated use getSongPitchGuide */
export async function getSongPitchGuideCompat(songId: string): Promise<PitchData> {
  const guide = await getSongPitchGuide(songId);
  return {
    song_id: guide.songId,
    resolution_ms: 10,
    frames: guide.points.map((p) => ({
      time_ms: Math.round(p.time * 1000),
      midi:    p.midi,
      note:    null,
      freq:    p.freqHz ?? undefined,
    })),
  };
}
