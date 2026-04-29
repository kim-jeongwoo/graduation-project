import apiClient from './client';
import { BASE_URL, DEFAULT_FETCH_HEADERS } from './client';
import { mockSongs, mockPitchComparison } from '../mock/mockData';
import type { Song, LyricsData, PitchData, PitchComparison } from '../types/api';

/**
 * 서버에서 곡 목록을 가져옵니다.
 * 서버 접속 실패 시 mock 데이터를 반환합니다.
 */
export async function getSongs(): Promise<Song[]> {
  try {
    console.log('[songs] getSongs 서버 요청:', `${BASE_URL}/songs`);
    const res = await fetch(`${BASE_URL}/songs`, {
      method: 'GET',
      headers: DEFAULT_FETCH_HEADERS,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: Song[] = await res.json();
    console.log('[songs] 서버에서 곡 목록 로드:', data.length, '곡');
    if (data.length > 0) {
      console.log('[songs] 첫 번째 곡 song_id:', data[0].song_id);
    }
    return data;
  } catch (e: unknown) {
    console.log('[songs] 서버 실패, mock 사용:', e);
    return mockSongs;
  }
}

/**
 * 곡의 가사(싱크) 데이터를 가져옵니다.
 */
export async function getSongLyrics(songId: string): Promise<LyricsData> {
  try {
    const res = await apiClient.get<LyricsData>(`/songs/${songId}/lyrics`);
    console.log('[songs] 서버에서 가사 로드 성공:', res.data.lines?.length, '라인');
    return res.data;
  } catch (e: unknown) {
    console.log('[songs] getSongLyrics 서버 실패:', e);
    return { song_id: songId, lines: [] };
  }
}

/**
 * 곡의 원곡 오디오 URL을 반환합니다.
 */
/**
 * 곡의 원곡 오디오 URL을 반환합니다.
 * ngrok 터널 사용 시에도 expo-av가 직접 스트리밍할 수 있도록
 * 헤더 없이 URL만 반환. (expo-av는 자체적으로 fetch함)
 */
export function getSongAudioUrl(songId: string): string {
  const url = `${BASE_URL}/songs/${songId}/audio`;
  console.log('[songs] getSongAudioUrl:', url);
  return url;
}

/**
 * 곡의 피치(음정) 데이터를 가져옵니다.
 */
export async function getSongPitch(songId: string): Promise<PitchData | null> {
  try {
    const res = await apiClient.get<PitchData>(`/songs/${songId}/pitch`);
    const data = res.data;
    console.log('[PITCH-DATA] 프레임 수:', data.frames?.length);
    console.log('[PITCH-DATA] resolution_ms:', data.resolution_ms);
    if (data.frames?.length > 0) {
      console.log('[PITCH-DATA] 첫 프레임:', JSON.stringify(data.frames[0]));
      console.log('[PITCH-DATA] 마지막 프레임:', JSON.stringify(data.frames[data.frames.length - 1]));
    }
    return data;
  } catch (e: unknown) {
    console.log('[PITCH-DATA] getSongPitch 서버 실패:', e);
    return null;
  }
}

/**
 * 세션의 피치 비교 결과를 가져옵니다.
 */
export async function comparePitch(sessionId: string, songId: string): Promise<PitchComparison | null> {
  try {
    console.log('[songs] comparePitch 서버 요청:', sessionId, songId);
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/compare-pitch`, {
      method: 'POST',
      headers: { ...DEFAULT_FETCH_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ song_id: songId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: PitchComparison = await res.json();
    console.log('[songs] 피치 비교 성공, 정확도:', data.comparison?.overall_accuracy);
    return data;
  } catch (e: unknown) {
    console.log('[songs] comparePitch 서버 실패, mock 폴백:', e);
    if (sessionId === mockPitchComparison.session_id && songId === mockPitchComparison.song_id) {
      return mockPitchComparison;
    }
    return {
      ...mockPitchComparison,
      session_id: sessionId,
      song_id: songId,
    };
  }
}
