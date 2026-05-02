import apiClient, { BASE_URL } from './client';
import type { Song, LyricsData, PitchData } from '../types/api';

export async function getSongs(): Promise<Song[]> {
  const res = await apiClient.get<Song[]>('/songs');
  return res.data;
}

export async function getSongLrc(songId: string): Promise<LyricsData> {
  const res = await apiClient.get<LyricsData>(`/songs/${songId}/lrc`);
  return res.data;
}

export async function getSongPitchGuide(songId: string): Promise<PitchData> {
  const res = await apiClient.get<PitchData>(`/songs/${songId}/pitch-guide`);
  return res.data;
}

// MR 스트리밍 URL 반환 (expo-av가 직접 fetch — 헤더 추가 불가)
// ngrok 환경에서는 토큰 인증 우회 가능성 있음. 추후 서명된 URL 방식 검토.
export function getSongMrUrl(songId: string): string {
  return `${BASE_URL}/songs/${songId}/mr`;
}
