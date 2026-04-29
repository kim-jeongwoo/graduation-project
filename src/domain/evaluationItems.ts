export type EvaluationItemKey =
  | 'breathiness'
  | 'vocal_fold_contact'
  | 'nasal_oral_ratio'
  | 'chest_head_voice'
  | 'forward_resonance'
  | 'velar_opening'
  | 'pressure_balance'
  | 'resonance_open'
  | 'tongue_tension';

export type ConfidenceLevel = 'high' | 'medium' | 'unavailable';

export interface EvaluationItemMeta {
  key: EvaluationItemKey;
  nameKo: string;
  /** 시연 시점 기본값. 실제 화면에서는 서버 응답의 confidence 필드를 우선 사용. */
  defaultConfidence: ConfidenceLevel;
  description?: string;
}

export const EVALUATION_ITEMS: EvaluationItemMeta[] = [
  { key: 'breathiness',        nameKo: '호흡식별',   defaultConfidence: 'high' },
  { key: 'vocal_fold_contact', nameKo: '접촉강도',   defaultConfidence: 'high' },
  { key: 'nasal_oral_ratio',   nameKo: '비강사용',   defaultConfidence: 'medium' },
  { key: 'chest_head_voice',   nameKo: '흉성두성',   defaultConfidence: 'medium' },
  { key: 'forward_resonance',  nameKo: '전방공명',   defaultConfidence: 'medium' },
  { key: 'velar_opening',      nameKo: '연구개위치', defaultConfidence: 'medium' },
  { key: 'pressure_balance',   nameKo: '상압하압',   defaultConfidence: 'medium' },
  { key: 'resonance_open',     nameKo: '공명개방',   defaultConfidence: 'unavailable' },
  { key: 'tongue_tension',     nameKo: '혀경직도',   defaultConfidence: 'unavailable' },
];
