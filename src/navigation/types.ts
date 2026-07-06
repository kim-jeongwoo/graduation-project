import type { NavigatorScreenParams } from '@react-navigation/native';
import type { IndicatorAppKey, WeakSection } from '../domain/weakSections';
import type { Zone } from '../types/analyze';
import type { Session, Song } from '../types/api';

export type EvalResultParams = {
  runId?: string;
  songId?: string;
};

export type SectionListParams = {
  indicatorKey: IndicatorAppKey;
  weakSections: WeakSection[];
  feedbackText: string;
  runId?: string;
  songId?: string;
  sessionId?: string;
};

export type TrainingParams = {
  indicatorKey: IndicatorAppKey;
  runId?: string;
  songId?: string;
  sessionId?: string;
  chunkIndex: number;
  sectionStartSec: number;
  sectionEndSec: number;
  chunkInfo: { startSec: number; endSec: number; lrcText: string };
  scoreInfo: { aiScore: number; zone: Zone };
  lowConfidenceItems?: string[];
  feedbackText: string;
};

export type HomeStackParamList = {
  Home: undefined;
  SessionDetail: { sessionId: string; songId?: string };
  AnalysisResult: { sessionId: string; runId: string; songId?: string };
  Settings: undefined;
  Profile: undefined;
  VocalRangeTest: undefined;
  SongComparison: { songTitle: string };
  SongDetail: { song: Song };
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  Training: TrainingParams;
};

export type HistoryStackParamList = {
  HistoryList: undefined;
  HistoryDetail: { sessionId: string };
  SongHistory: {
    songId: string;
    songTitle: string;
    songArtist: string | null;
    sessions: Session[];
  };
  Favorites: undefined;
  Training: TrainingParams;
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  SongComparison: { songTitle: string };
};

export type ResultStackParamList = {
  LatestAnalysis: undefined;
  EvalResult: EvalResultParams;
  SectionList: SectionListParams;
  Training: TrainingParams;
};

export type MainTabParamList = {
  HomeTab: NavigatorScreenParams<HomeStackParamList>;
  RecordTab: NavigatorScreenParams<ResultStackParamList>;
  HistoryTab: NavigatorScreenParams<HistoryStackParamList>;
};

export type AppRootStackParamList = {
  MainTabs: NavigatorScreenParams<MainTabParamList>;
  Karaoke: { songId: string; title: string; artist: string; mrDurationSec: number };
};
