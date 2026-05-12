import React, { createContext, useState, useContext, useCallback } from 'react';
import type { ReactNode } from 'react';

// ─── Types ───

interface VocalRange {
  low: string;
  high: string;
}

interface ExpansionGoal {
  direction: 'high' | 'low' | 'both';
  targetLow: string;
  targetHigh: string;
}

interface VocalProfileState {
  vocalRange: VocalRange | null;
  voiceType: string;
  expansionGoal: ExpansionGoal | null;
  isTestCompleted: boolean;
  setVocalRange: (range: VocalRange) => void;
  setVoiceType: (type: string) => void;
  setExpansionGoal: (goal: ExpansionGoal | null) => void;
  completeTest: () => void;
  resetTest: () => void;
}

// ─── Context ───

const VocalProfileContext = createContext<VocalProfileState | undefined>(undefined);

export function VocalProfileProvider({ children }: { children: ReactNode }) {
  const [vocalRange, setVocalRangeState] = useState<VocalRange | null>(null);
  const [voiceType, setVoiceTypeState] = useState('');
  const [expansionGoal, setExpansionGoalState] = useState<ExpansionGoal | null>(null);
  const [isTestCompleted, setIsTestCompleted] = useState(false);

  const setVocalRange = useCallback((range: VocalRange) => {
    setVocalRangeState(range);
  }, []);

  const setVoiceType = useCallback((type: string) => {
    setVoiceTypeState(type);
  }, []);

  const setExpansionGoal = useCallback((goal: ExpansionGoal | null) => {
    setExpansionGoalState(goal);
  }, []);

  const completeTest = useCallback(() => {
    setIsTestCompleted(true);
  }, []);

  const resetTest = useCallback(() => {
    setIsTestCompleted(false);
    setVocalRangeState(null);
    setVoiceTypeState('');
    setExpansionGoalState(null);
  }, []);

  return (
    <VocalProfileContext.Provider
      value={{
        vocalRange,
        voiceType,
        expansionGoal,
        isTestCompleted,
        setVocalRange,
        setVoiceType,
        setExpansionGoal,
        completeTest,
        resetTest,
      }}
    >
      {children}
    </VocalProfileContext.Provider>
  );
}

export function useVocalProfile(): VocalProfileState {
  const ctx = useContext(VocalProfileContext);
  if (!ctx) {
    throw new Error('useVocalProfile must be used within VocalProfileProvider');
  }
  return ctx;
}
