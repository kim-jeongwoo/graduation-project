import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import type { WeakSection, IndicatorAppKey } from '../domain/weakSections';
import { useAuth } from './AuthContext';
import {
  isAuthExpiredError,
} from '../api/client';
import {
  getFavoritesList,
  postFavorite,
  deleteFavorite,
  serverToAppKey,
  type FavoriteServerItem,
} from '../api/training';

// Phase 7 — vocal-server endpoint 통합
// 서버 GET 응답엔 paddedStart/EndSec, aiScore, zone 없음 → 단순 패딩 + placeholder
// scoreInfo placeholder는 ResultCard "원본 점수"가 의미 없음 (즐겨찾기 진입 시 한정)

const PAD_START = 4;
const PAD_END   = 3;

export interface FavoriteSection {
  id:           string;            // 서버 favorite_id (or tmp-/local- 접두 임시 ID)
  indicatorKey: IndicatorAppKey;
  weakSection:  WeakSection;
  songId:       string;
  songTitle?:   string;
  songArtist?:  string;
  runId?:       string;
  sessionId?:   string;
  feedbackText: string;
  addedAt:      number;
}

function fromServer(item: FavoriteServerItem): FavoriteSection | null {
  const indicatorKey = serverToAppKey(item.indicator_key);
  if (!indicatorKey) return null;
  return {
    id:           item.favorite_id,
    indicatorKey,
    weakSection: {
      chunkIndex:     item.chunk_index,
      paddedStartSec: Math.max(0, item.chunk_start_sec - PAD_START),
      paddedEndSec:   item.chunk_end_sec + PAD_END,
      startSec:       item.chunk_start_sec,
      endSec:         item.chunk_end_sec,
      lrcText:        item.chunk_lrc_text,
      aiScore:        0,                 // 서버 미반환 placeholder
      zone:           'appropriate',      // placeholder
    },
    songId:       item.song_id,
    songTitle:    item.song_title,
    songArtist:   item.song_artist,
    runId:        item.original_run_id,
    sessionId:    undefined,              // 서버 미반환
    feedbackText: '',
    addedAt:      new Date(item.created_at).getTime(),
  };
}

interface FavoritesContextValue {
  favorites:           FavoriteSection[];
  favoritesLoading:    boolean;
  favoritesError:      string | null;
  reloadFavorites:     () => Promise<void>;
  addFavorite:         (fav: Omit<FavoriteSection, 'id' | 'addedAt'>) => Promise<void>;
  removeFavoriteById:  (id: string) => Promise<void>;
  removeFavoriteByKey: (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => Promise<void>;
  isFavorite:          (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => boolean;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [favorites, setFavorites] = useState<FavoriteSection[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoritesError, setFavoritesError] = useState<string | null>(null);

  const loadFavorites = useCallback(async (shouldIgnore?: () => boolean) => {
    if (!token) {
      setFavorites([]);
      setFavoritesLoading(false);
      setFavoritesError(null);
      return;
    }
    setFavoritesLoading(true);
    setFavoritesError(null);
    try {
      const res = await getFavoritesList();
      if (shouldIgnore?.()) return;
      const items = res.items
        .map(fromServer)
        .filter((x): x is FavoriteSection => x !== null);
      setFavorites(items);
    } catch (e: unknown) {
      if (shouldIgnore?.()) return;
      if (!isAuthExpiredError(e)) {
        setFavoritesError('즐겨찾기를 불러오지 못했습니다.');
      }
    } finally {
      if (!shouldIgnore?.()) {
        setFavoritesLoading(false);
      }
    }
  }, [token]);

  // 토큰 변화 시 서버에서 즐겨찾기 로드 (로그아웃/만료 시 비움)
  useEffect(() => {
    if (!token) {
      setFavorites([]);
      setFavoritesLoading(false);
      setFavoritesError(null);
      return;
    }
    let cancelled = false;
    void loadFavorites(() => cancelled);
    return () => { cancelled = true; };
  }, [token, loadFavorites]);

  const addFavorite = useCallback(async (fav: Omit<FavoriteSection, 'id' | 'addedAt'>) => {
    // runId 없으면 서버 호출 불가 (mock 등) → 로컬에만
    if (!fav.runId) {
      const localId = `local-${Date.now()}`;
      setFavorites(prev => [...prev, { ...fav, id: localId, addedAt: Date.now() }]);
      return;
    }
    // optimistic UI
    const tempId = `tmp-${Date.now()}`;
    setFavorites(prev => [...prev, { ...fav, id: tempId, addedAt: Date.now() }]);
    try {
      const serverItem = await postFavorite(fav.runId, fav.weakSection.chunkIndex, fav.indicatorKey);
      // 임시 → 서버 응답 ID로 교체
      setFavorites(prev =>
        prev.map(f => f.id === tempId
          ? {
              ...f,
              id: serverItem.favorite_id,
              songTitle:  serverItem.song_title  ?? f.songTitle,
              songArtist: serverItem.song_artist ?? f.songArtist,
            }
          : f
        ),
      );
    } catch (e: any) {
      const code = e?.response?.status;
      if (code === 409) {
        // 중복 — 서버 측 existing_favorite_id 활용 (있으면 매핑, 없으면 임시 그대로)
        const existingId = e?.response?.data?.detail?.existing_favorite_id;
        if (existingId) {
          setFavorites(prev =>
            prev.map(f => f.id === tempId ? { ...f, id: existingId } : f),
          );
        }
        // silent
      } else {
        // rollback
        setFavorites(prev => prev.filter(f => f.id !== tempId));
      }
    }
  }, []);

  const removeFavoriteById = useCallback(async (id: string) => {
    let target: FavoriteSection | undefined;
    setFavorites(prev => {
      target = prev.find(f => f.id === id);
      return prev.filter(f => f.id !== id);
    });
    if (!target) return;
    if (id.startsWith('tmp-') || id.startsWith('local-')) return;
    try {
      await deleteFavorite(id);
    } catch {
      // rollback
      const saved = target;
      setFavorites(prev => saved ? [...prev, saved] : prev);
    }
  }, []);

  const removeFavoriteByKey = useCallback(async (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => {
    const target = favorites.find(f =>
      f.songId === params.songId &&
      f.weakSection.chunkIndex === params.chunkIndex &&
      f.indicatorKey === params.indicatorKey,
    );
    if (!target) return;
    return removeFavoriteById(target.id);
  }, [favorites, removeFavoriteById]);

  const isFavorite = useCallback(
    (params: { songId: string; chunkIndex: number; indicatorKey: IndicatorAppKey }) => {
      return favorites.some(f =>
        f.songId === params.songId &&
        f.weakSection.chunkIndex === params.chunkIndex &&
        f.indicatorKey === params.indicatorKey,
      );
    },
    [favorites],
  );

  return (
    <FavoritesContext.Provider value={{
      favorites,
      favoritesLoading,
      favoritesError,
      reloadFavorites: loadFavorites,
      addFavorite,
      removeFavoriteById,
      removeFavoriteByKey,
      isFavorite,
    }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error('useFavorites must be used within FavoritesProvider');
  return ctx;
}
