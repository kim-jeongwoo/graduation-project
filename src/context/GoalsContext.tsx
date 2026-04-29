import React, { createContext, useState, useContext, useCallback } from 'react';
import type { ReactNode } from 'react';

// ─── Types ───

export interface Goal {
  id: string;
  name: string;
  parameter: string;
  target: number;
  direction: 'above' | 'below';
  createdAt: string;
}

interface GoalsState {
  goals: Goal[];
  addGoal: (goal: Goal) => void;
  removeGoal: (goalId: string) => void;
  getActiveGoals: () => Goal[];
}

// ─── Default Goals ───

const DEFAULT_GOALS: Goal[] = [
  {
    id: 'goal-1',
    name: '성대접촉률 최적화',
    parameter: 'contact_rate',
    target: 45,
    direction: 'below',
    createdAt: '2026-02-20',
  },
  {
    id: 'goal-2',
    name: '비강 공명 강화',
    parameter: 'oral_nasal_ratio',
    target: 80,
    direction: 'above',
    createdAt: '2026-02-22',
  },
];

// ─── Context ───

const GoalsContext = createContext<GoalsState | undefined>(undefined);

export function GoalsProvider({ children }: { children: ReactNode }) {
  const [goals, setGoals] = useState<Goal[]>(DEFAULT_GOALS);

  const addGoal = useCallback((goal: Goal) => {
    setGoals((prev) => [...prev, goal]);
  }, []);

  const removeGoal = useCallback((goalId: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== goalId));
  }, []);

  const getActiveGoals = useCallback(() => {
    return goals;
  }, [goals]);

  return (
    <GoalsContext.Provider value={{ goals, addGoal, removeGoal, getActiveGoals }}>
      {children}
    </GoalsContext.Provider>
  );
}

export function useGoals(): GoalsState {
  const ctx = useContext(GoalsContext);
  if (!ctx) {
    throw new Error('useGoals must be used within GoalsProvider');
  }
  return ctx;
}
