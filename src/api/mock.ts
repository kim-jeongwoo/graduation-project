import type { AnalyzeResult } from '../types/analyze';

// 결정적(deterministic) 더미 결과 — 시연 폴백용
export const MOCK_FIXED_RESULT: AnalyzeResult = {
  run_id: 'mock-run-fixed-001',
  status: 'completed',
  processing_time_ms: 1523,
  audio_info: {
    duration_sec: 32.4,
    sample_rate: 44100,
    voiced_ratio: 0.78,
    voiced_duration_s: 25.3,
    f0_min: 196.0,
    f0_max: 523.2,
    f0_mean: 310.5,
  },
  registers: { low: {}, mid: {}, high: {} },
  indicators: {
    cq_mean: 0.42,
    cq_peak: 0.61,
    cpp_mean: 12.3,
    spectral_centroid_mean: 2840.0,
    spectral_tilt_mean: -8.2,
    h1_h2_mean: 2.1,
    hnr_mean: 18.4,
    a1_p0_mean: 3.7,
  },
  scores: {
    breathiness:        { ai_score: 3, zone: 'appropriate',  confidence: 'high' },
    vocal_fold_contact: { ai_score: 2, zone: 'appropriate',  confidence: 'high' },
    nasal_oral_ratio:   { ai_score: 4, zone: 'excessive',    confidence: 'medium' },
    chest_head_voice:   { ai_score: 1, zone: 'insufficient', confidence: 'medium' },
    forward_resonance:  { ai_score: 3, zone: 'appropriate',  confidence: 'medium' },
    soft_palate:        { ai_score: 2, zone: 'appropriate',  confidence: 'medium' },
    pressure_balance:   { ai_score: 4, zone: 'excessive',    confidence: 'medium' },
    larynx_tongue_root: { ai_score: null, zone: null,        confidence: 'unavailable' },
    tongue_tension:     { ai_score: null, zone: null,        confidence: 'unavailable' },
  },
  feedback: {
    breathiness: {
      name_ko: '호흡식별', ai_score: 3, zone: 'appropriate',
      score_description: '호흡 기류가 적절히 조절되고 있음',
      feedback_text: '안정적인 호흡 기류를 유지하고 있습니다.',
      ai_indicator: { name: 'cpp_mean', value: 12.3 },
    },
    vocal_fold_contact: {
      name_ko: '접촉강도', ai_score: 2, zone: 'appropriate',
      score_description: '성대 접촉이 균형적임',
      feedback_text: '성대 접촉 효율이 양호합니다.',
      ai_indicator: { name: 'cq_mean', value: 0.42 },
    },
    nasal_oral_ratio: {
      name_ko: '비강사용', ai_score: 4, zone: 'excessive',
      score_description: '비강 공명 비율이 다소 높음',
      feedback_text: '비강 울림이 과도합니다. 구강 공명 비율을 높여보세요.',
      ai_indicator: { name: 'spectral_tilt_mean', value: -8.2 },
    },
    chest_head_voice: {
      name_ko: '흉성두성', ai_score: 1, zone: 'insufficient',
      score_description: '두성 전환이 불안정함',
      feedback_text: '흉성에서 두성으로의 전환 연습이 필요합니다.',
      ai_indicator: { name: 'spectral_centroid_mean', value: 2840.0 },
    },
    forward_resonance: {
      name_ko: '전방공명', ai_score: 3, zone: 'appropriate',
      score_description: '전방 공명이 적절히 활성화됨',
      feedback_text: '전방 공명 포인트가 잘 유지되고 있습니다.',
      ai_indicator: { name: 'h1_h2_mean', value: 2.1 },
    },
    soft_palate: {
      name_ko: '연구개위치', ai_score: 2, zone: 'appropriate',
      score_description: '연구개가 적절한 위치에 있음',
      feedback_text: '연구개 포지션이 안정적입니다.',
      ai_indicator: { name: 'a1_p0_mean', value: 3.7 },
    },
    pressure_balance: {
      name_ko: '상압하압', ai_score: 4, zone: 'excessive',
      score_description: '성문 상압이 다소 과함',
      feedback_text: '성문 위아래 압력 균형을 낮추는 연습이 필요합니다.',
      ai_indicator: { name: 'hnr_mean', value: 18.4 },
    },
    larynx_tongue_root: {
      name_ko: '공명개방', ai_score: null, zone: null,
      score_description: '분석 데이터 부족',
      feedback_text: '아직 충분한 데이터가 없어 평가하기 어렵습니다.',
      ai_indicator: { name: 'cq_peak', value: 0.61 },
    },
    tongue_tension: {
      name_ko: '혀경직도', ai_score: null, zone: null,
      score_description: '분석 데이터 부족',
      feedback_text: '아직 충분한 데이터가 없어 평가하기 어렵습니다.',
      ai_indicator: { name: 'cpp_mean', value: 12.3 },
    },
  },
  reliability: {
    high_reliability:   ['breathiness', 'vocal_fold_contact'],
    medium_reliability: ['nasal_oral_ratio', 'chest_head_voice', 'forward_resonance', 'soft_palate', 'pressure_balance'],
    unavailable:        ['larynx_tongue_root', 'tongue_tension'],
  },
};

export async function mockAnalyze(_request: { fileUri: string }): Promise<AnalyzeResult> {
  await new Promise<void>((resolve) => setTimeout(resolve, 1500));
  return MOCK_FIXED_RESULT;
}
