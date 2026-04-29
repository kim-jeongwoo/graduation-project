import { create } from 'zustand';

// TODO: Step B에서 실제 상태 정의
interface HistoryState {
  _placeholder: undefined;
}

export const useHistoryStore = create<HistoryState>()(() => ({
  _placeholder: undefined,
}));
