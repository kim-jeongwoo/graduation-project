import apiClient, { BASE_URL } from './client';
import type { Song, LyricsData, PitchData } from '../types/api';
import type { LyricLine, PitchGuide, ServerLrcLine, ServerPitchGuide } from '../types/karaoke';
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

const pitchGuideCache = new Map<string, ServerPitchGuide>();
const pitchGuideRequests = new Map<string, Promise<ServerPitchGuide>>();

async function getServerPitchGuide(songId: string): Promise<ServerPitchGuide> {
  const key = String(songId);
  const cached = pitchGuideCache.get(key);
  if (cached) return cached;

  const inFlight = pitchGuideRequests.get(key);
  if (inFlight) return inFlight;

  const request = apiClient.get<ServerPitchGuide>(`/songs/${key}/pitch-guide`)
    .then((res) => {
      pitchGuideCache.set(key, res.data);
      return res.data;
    })
    .finally(() => {
      pitchGuideRequests.delete(key);
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
): Promise<{ lyrics: LyricLine[]; pitchGuide: PitchGuide }> {
  const [rawLrc, pitchGuide] = await Promise.all([
    getSongLrcRaw(songId),
    getSongPitchGuide(songId),
  ]);
  const clientOffset = SONG_LRC_OFFSETS[songId] ?? 0;
  const baseLyrics = adaptLrc(rawLrc, pitchGuide.lrcOffsetSec);
  const lyrics = clientOffset === 0 ? baseLyrics : baseLyrics.map((l) => ({
    ...l,
    timeStart: l.timeStart + clientOffset,
    timeEnd:   l.timeEnd   + clientOffset,
  }));
  return { lyrics, pitchGuide };
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
