import apiClient, { BASE_URL } from './client';
import type { Song, LyricsData, PitchData } from '../types/api';
import type { LyricLine, PitchGuide, ServerLrcLine, ServerPitchGuide } from '../types/karaoke';
import { adaptLrc, adaptPitchGuide } from '../types/karaoke';

interface ServerSong {
  id: string;
  title: string;
  artist: string;
  master_duration_sec: number;
  mr_duration_sec: number;
  has_lrc: boolean;
  has_pitch_guide: boolean;
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
  const res = await apiClient.get<ServerPitchGuide>(`/songs/${songId}/pitch-guide`);
  return adaptPitchGuide(res.data);
}

// Fetch both LRC and pitch-guide together so offset is applied consistently
export async function getSongKaraokeData(
  songId: string,
): Promise<{ lyrics: LyricLine[]; pitchGuide: PitchGuide }> {
  const [rawLrc, pitchGuide] = await Promise.all([
    getSongLrcRaw(songId),
    getSongPitchGuide(songId),
  ]);
  const lyrics = adaptLrc(rawLrc, pitchGuide.lrcOffsetSec);
  return { lyrics, pitchGuide };
}

// MR streaming URL — Authorization header must be added by caller (expo-av supports headers in loadAsync)
export function getSongMrUrl(songId: string): string {
  return `${BASE_URL}/songs/${songId}/mr`;
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
      time_ms: Math.round(p.t * 1000),
      midi:    p.midi,
      note:    null,
      freq:    p.freq ?? undefined,
    })),
  };
}
