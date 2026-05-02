import type { Session, SessionFile, Metric, Comparison } from '../types/api';
import type { Song, PitchFrame, ComparisonFrame, PitchData, PitchComparison } from '../types/api';

// ─── 곡 목록 mock ───
export const mockSongs: Song[] = [
  { id: '001', title: '주저하는 연인들을 위해', artist: '잔나비', masterDurationSec: 267, mrDurationSec: 267, hasLrc: true, hasPitchGuide: true },
  { id: '002', title: '봄날', artist: 'BTS', masterDurationSec: 274, mrDurationSec: 274, hasLrc: true, hasPitchGuide: true },
  { id: '003', title: '좋은 날', artist: 'IU', masterDurationSec: 228, mrDurationSec: 228, hasLrc: true, hasPitchGuide: true },
  { id: '004', title: '사랑하기 때문에', artist: '유재하', masterDurationSec: 252, mrDurationSec: 252, hasLrc: true, hasPitchGuide: false },
  { id: '005', title: 'Hype Boy', artist: 'NewJeans', masterDurationSec: 179, mrDurationSec: 179, hasLrc: true, hasPitchGuide: true },
];

// ─── 세션 목록 mock ───
export const mockSessions: Session[] = [
  {
    session_id: 'mock-1',
    song_title: '주저하는 연인들을 위해 - 잔나비',
    song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
    status: 'completed',
    started_at: '2026-02-20T14:00:00+09:00',
    created_at: '2026-02-20T13:55:00+09:00',
  },
  {
    session_id: 'mock-2',
    song_title: '사랑하기 때문에 - 유재하',
    status: 'completed',
    started_at: '2026-02-23T10:00:00+09:00',
    created_at: '2026-02-23T09:55:00+09:00',
  },
  {
    session_id: 'mock-3',
    song_title: '나의 사춘기에게 - 볼빨간사춘기',
    status: 'completed',
    started_at: '2026-02-25T16:00:00+09:00',
    created_at: '2026-02-25T15:55:00+09:00',
  },
  {
    session_id: 'mock-4',
    song_title: 'Hype Boy - NewJeans',
    status: 'analyzing',
    started_at: '2026-02-28T11:00:00+09:00',
    created_at: '2026-02-28T10:55:00+09:00',
  },
  {
    session_id: 'mock-5',
    song_title: '좋은 날 - IU',
    status: 'uploaded',
    started_at: undefined,
    created_at: '2026-03-01T09:00:00+09:00',
  },
  {
    session_id: 'mock-6',
    song_title: '봄날 - BTS',
    status: 'completed',
    started_at: '2026-02-27T14:00:00+09:00',
    created_at: '2026-02-27T13:55:00+09:00',
  },
];

// ─── 분석 결과 mock (세션별) ───
export interface MockAnalysis {
  run_id: string;
  status: string;
  metrics: Metric[];
}

export const mockAnalysisResults: Record<string, MockAnalysis> = {
  'mock-1': {
    run_id: 'run-1',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.82, unit: '' },
      { key: 'contact_rate', value: 47.3, unit: '%' },
      { key: 'chest_ratio', value: 65, unit: '%' },
      { key: 'oral_nasal_ratio', value: 78, unit: '%' },
      { key: 'processing_time_ms', value: 1240, unit: 'ms' },
    ],
  },
  'mock-2': {
    run_id: 'run-2',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.79, unit: '' },
      { key: 'contact_rate', value: 52.1, unit: '%' },
      { key: 'chest_ratio', value: 58, unit: '%' },
      { key: 'oral_nasal_ratio', value: 82, unit: '%' },
      { key: 'processing_time_ms', value: 1180, unit: 'ms' },
    ],
  },
  'mock-3': {
    run_id: 'run-3',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.85, unit: '' },
      { key: 'contact_rate', value: 44.8, unit: '%' },
      { key: 'chest_ratio', value: 70, unit: '%' },
      { key: 'oral_nasal_ratio', value: 75, unit: '%' },
      { key: 'processing_time_ms', value: 1320, unit: 'ms' },
    ],
  },
  'mock-6': {
    run_id: 'run-6',
    status: 'completed',
    metrics: [
      { key: 'egg_correlation', value: 0.86, unit: '' },
      { key: 'contact_rate', value: 44.1, unit: '%' },
      { key: 'chest_ratio', value: 62, unit: '%' },
      { key: 'oral_nasal_ratio', value: 81, unit: '%' },
      { key: 'processing_time_ms', value: 1150, unit: 'ms' },
    ],
  },
};

// ─── 숙련자 비교 mock ───
export interface MockComparison {
  reference_name: string;
  comparisons: Comparison[];
}

export const mockComparisons: Record<string, MockComparison> = {
  'mock-1': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 47.3, reference_mean: 45.0, z_score: 0.46, percentile: 68 },
      { key: 'chest_ratio', user_value: 65, reference_mean: 60, z_score: 0.71, percentile: 76 },
      { key: 'oral_nasal_ratio', user_value: 78, reference_mean: 80, z_score: -0.33, percentile: 37 },
      { key: 'egg_correlation', user_value: 0.82, reference_mean: 0.78, z_score: 0.57, percentile: 72 },
    ],
  },
  'mock-2': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 52.1, reference_mean: 45.0, z_score: 1.42, percentile: 92 },
      { key: 'chest_ratio', user_value: 58, reference_mean: 60, z_score: -0.29, percentile: 39 },
      { key: 'oral_nasal_ratio', user_value: 82, reference_mean: 80, z_score: 0.33, percentile: 63 },
      { key: 'egg_correlation', user_value: 0.79, reference_mean: 0.78, z_score: 0.14, percentile: 56 },
    ],
  },
  'mock-3': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 44.8, reference_mean: 45.0, z_score: -0.04, percentile: 48 },
      { key: 'chest_ratio', user_value: 70, reference_mean: 60, z_score: 1.43, percentile: 92 },
      { key: 'oral_nasal_ratio', user_value: 75, reference_mean: 80, z_score: -0.83, percentile: 20 },
      { key: 'egg_correlation', user_value: 0.85, reference_mean: 0.78, z_score: 1.0, percentile: 84 },
    ],
  },
  'mock-6': {
    reference_name: '데벨로 아카데미 숙련자 평균',
    comparisons: [
      { key: 'contact_rate', user_value: 44.1, reference_mean: 45.0, z_score: -0.18, percentile: 43 },
      { key: 'chest_ratio', user_value: 62, reference_mean: 60, z_score: 0.29, percentile: 61 },
      { key: 'oral_nasal_ratio', user_value: 81, reference_mean: 80, z_score: 0.17, percentile: 57 },
      { key: 'egg_correlation', user_value: 0.86, reference_mean: 0.78, z_score: 1.14, percentile: 87 },
    ],
  },
};

// ─── 피드백 mock ───
export interface MockFeedback {
  overall_grade: string;
  overall_comment: string;
  strengths: string[];
  improvements: string[];
}

export const mockFeedback: Record<string, MockFeedback> = {
  'mock-1': {
    overall_grade: 'B+',
    overall_comment:
      '안정적인 발성 기반을 갖추고 있습니다. 흉성 활용이 좋으며, 비강 공명 조절에 조금 더 신경 쓰면 한 단계 도약할 수 있습니다.',
    strengths: [
      '흉성 발성이 안정적으로 유지됩니다',
      '성대 접촉 효율이 숙련자 평균 이상입니다',
    ],
    improvements: [
      '비강 공명이 다소 부족합니다. 허밍 연습을 통해 비강 울림을 키워보세요',
      '고음부에서 두성 전환을 더 부드럽게 연습해보세요',
    ],
  },
  'mock-2': {
    overall_grade: 'B',
    overall_comment:
      '발성 효율이 높은 편이나 다소 강한 성대 접촉이 관찰됩니다. 장시간 발성 시 피로 관리에 주의하세요.',
    strengths: [
      '구강/비강 공명 밸런스가 양호합니다',
      '흉성-두성 전환이 자연스럽습니다',
    ],
    improvements: [
      '성대 접촉률이 높은 편입니다. 발성 시 과도한 힘을 빼는 연습을 권장합니다',
      '브레이크 구간(파사지오) 부근에서 안정성을 높여보세요',
    ],
  },
  'mock-3': {
    overall_grade: 'A-',
    overall_comment:
      '전반적으로 우수한 발성 품질입니다. EGG 추정 상관도가 높아 발성 패턴이 일관적입니다.',
    strengths: [
      'EGG 상관계수가 매우 높아 발성 일관성이 뛰어납니다',
      '흉성 활용도가 높고 발성에 힘이 있습니다',
    ],
    improvements: [
      '비강 공명이 숙련자 대비 다소 낮습니다. 공명 포인트를 높이는 연습을 추천합니다',
      '두성 비율을 늘려 고음부 표현력을 키워보세요',
    ],
  },
  'mock-6': {
    overall_grade: 'A',
    overall_comment:
      '이전 시도 대비 전반적으로 향상되었습니다. 성대접촉률이 최적 범위에 진입했고, 비강 공명도 개선되었습니다.',
    strengths: [
      '성대접촉률이 최적 범위(40~50%)에 들어왔습니다',
      'EGG 상관계수가 0.86으로 매우 높은 발성 일관성을 보여줍니다',
      '비강 공명이 이전 대비 개선되었습니다',
    ],
    improvements: [
      '흉성 비율을 조금 낮추고 두성 활용을 늘려보세요',
      '파사지오 구간에서의 전환을 더 연습해보세요',
    ],
  },
};

// ─── 파일 목록 mock ───
export const mockFiles: Record<string, SessionFile[]> = {
  'mock-1': [
    { file_id: 'f1', file_type: 'm4a', storage_uri: '/recordings/mock-1.m4a', duration_ms: 185000 },
  ],
  'mock-2': [
    { file_id: 'f2', file_type: 'm4a', storage_uri: '/recordings/mock-2.m4a', duration_ms: 210000 },
  ],
  'mock-3': [
    { file_id: 'f3', file_type: 'm4a', storage_uri: '/recordings/mock-3.m4a', duration_ms: 195000 },
  ],
  'mock-6': [
    { file_id: 'f6', file_type: 'm4a', storage_uri: '/recordings/mock-6.m4a', duration_ms: 190000 },
  ],
};

// ─── 목표 mock ───
export interface MockGoal {
  id: string;
  parameter: string;
  target: number;
  direction: 'above' | 'below';
  name: string;
}

export const mockGoals: MockGoal[] = [
  { id: 'goal-1', parameter: 'contact_rate', target: 45, direction: 'below', name: '성대접촉률 최적화' },
  { id: 'goal-2', parameter: 'egg_correlation', target: 0.85, direction: 'above', name: '발성 일관성 향상' },
  { id: 'goal-3', parameter: 'oral_nasal_ratio', target: 80, direction: 'above', name: '비강 공명 강화' },
];

// ─── 피치 비교 mock ───
function midiToNote(midi: number): string {
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  return `${notes[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

function generateMockPitchFrames(): { original: PitchFrame[]; comparison: ComparisonFrame[] } {
  const melody = [60, 60, 62, 64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 67, 69, 67, 65, 64];
  const originalFrames: PitchFrame[] = [];
  const compFrames: ComparisonFrame[] = [];

  // 고정 시드 의사 난수 (매번 같은 결과)
  let seed = 42;
  const rand = () => {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let t = 0; t < 180000; t += 50) {
    const idx = Math.floor((t / 400) % melody.length);
    const origMidi = melody[idx];
    const isVoiced = rand() > 0.15;
    let userOffset = 0;
    if (isVoiced) {
      if (rand() < 0.65) {
        userOffset = 0;
      } else if (rand() < 0.8) {
        userOffset = rand() < 0.5 ? 1 : -1;
      } else {
        userOffset = Math.floor(rand() * 5) - 2;
      }
    }

    originalFrames.push({
      time_ms: t,
      note: midiToNote(origMidi),
      midi: origMidi,
    });

    compFrames.push({
      time_ms: t,
      original_note: midiToNote(origMidi),
      original_midi: origMidi,
      user_note: isVoiced ? midiToNote(origMidi + userOffset) : null,
      user_midi: isVoiced ? origMidi + userOffset : null,
      diff_semitones: isVoiced ? userOffset : null,
    });
  }
  return { original: originalFrames, comparison: compFrames };
}

const mockPitchData = generateMockPitchFrames();

export const mockSongPitch: PitchData = {
  song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
  resolution_ms: 50,
  frames: mockPitchData.original,
};

export const mockPitchComparison: PitchComparison = {
  session_id: 'mock-1',
  song_id: 'efe04b77-532d-458a-8713-5f3b70c83465',
  comparison: {
    overall_accuracy: 65.2,
    accuracy_lenient: 82.7,
    frames: mockPitchData.comparison,
    sections: [
      { start_ms: 0, end_ms: 60000, accuracy: 68.5, label: '1절' },
      { start_ms: 60000, end_ms: 120000, accuracy: 61.3, label: '2절' },
      { start_ms: 120000, end_ms: 180000, accuracy: 66.0, label: '후반부' },
    ],
  },
};
