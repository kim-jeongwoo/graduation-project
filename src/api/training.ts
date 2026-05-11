import apiClient from './client';
import type { IndicatorAppKey } from '../domain/weakSections';
import type { Zone } from '../types/analyze';

// ─── indicator_key 매핑 (앱 ↔ 서버 prefix 형식) ───
const APP_TO_SERVER: Record<IndicatorAppKey, string> = {
  breathiness:        '4_breathiness',
  vocal_fold_contact: '3_vocal_fold_contact',
};

export function appToServerKey(k: IndicatorAppKey): string {
  return APP_TO_SERVER[k];
}

export function serverToAppKey(s: string): IndicatorAppKey | null {
  const stripped = s.replace(/^\d+_/, '');
  if (stripped === 'breathiness' || stripped === 'vocal_fold_contact') return stripped;
  return null;
}

// ─── 누적 시도 (GET /users/me/training-attempts) ───
export interface TrainingAttemptItem {
  attempt_id:           string;
  session_id:           string;
  original_run_id:      string;
  chunk_index:          number;
  chunk_start_sec:      number;
  chunk_end_sec:        number;
  indicator_key:        string;
  before_ai_score:      number;
  before_rounded_score: number;
  before_zone:          Zone;
  after_ai_score:       number;
  after_rounded_score:  number;
  after_zone:           Zone;
  improvement:          number;
  attempted_at:         string;
}

export interface TrainingAttemptsResponse {
  items:        TrainingAttemptItem[];
  next_cursor?: string;
  has_more:     boolean;
}

export interface AttemptsFilters {
  indicatorKey?:  IndicatorAppKey;
  songId?:        string;
  originalRunId?: string;
  cursor?:        string;
  limit?:         number;
}

export async function getTrainingAttempts(filters: AttemptsFilters = {}): Promise<TrainingAttemptsResponse> {
  const params: Record<string, string | number> = {};
  if (filters.indicatorKey)  params.indicator_key   = appToServerKey(filters.indicatorKey);
  if (filters.songId)        params.song_id         = filters.songId;
  if (filters.originalRunId) params.original_run_id = filters.originalRunId;
  if (filters.cursor)        params.cursor          = filters.cursor;
  if (filters.limit)         params.limit           = filters.limit;
  const res = await apiClient.get<TrainingAttemptsResponse>('/users/me/training-attempts', { params });
  return res.data;
}

// ─── 즐겨찾기 (GET/POST/DELETE /users/me/favorites) ───
export interface FavoriteServerItem {
  favorite_id:     string;
  song_id:         string;
  song_title?:     string;
  song_artist?:    string;
  original_run_id: string;
  chunk_index:     number;
  chunk_start_sec: number;
  chunk_end_sec:   number;
  chunk_lrc_text:  string;
  indicator_key:   string;
  created_at:      string;
}

export interface FavoritesResponse {
  items: FavoriteServerItem[];
}

export async function getFavoritesList(filters: { indicatorKey?: IndicatorAppKey; songId?: string } = {}): Promise<FavoritesResponse> {
  const params: Record<string, string> = {};
  if (filters.indicatorKey) params.indicator_key = appToServerKey(filters.indicatorKey);
  if (filters.songId)       params.song_id       = filters.songId;
  const res = await apiClient.get<FavoritesResponse>('/users/me/favorites', { params });
  return res.data;
}

export async function postFavorite(
  originalRunId: string,
  chunkIndex: number,
  indicatorKey: IndicatorAppKey,
): Promise<FavoriteServerItem> {
  const res = await apiClient.post<FavoriteServerItem>('/users/me/favorites', {
    original_run_id: originalRunId,
    chunk_index:     chunkIndex,
    indicator_key:   appToServerKey(indicatorKey),
  });
  return res.data;
}

export async function deleteFavorite(favoriteId: string): Promise<void> {
  await apiClient.delete(`/users/me/favorites/${favoriteId}`);
}
