import { create } from 'zustand';

// TODO: Step B에서 실제 상태 정의
interface RecordingState {
  _placeholder: undefined;
}

export const useRecordingStore = create<RecordingState>()(() => ({
  _placeholder: undefined,
}));
