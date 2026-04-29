import { COLORS } from '../utils/colors';
import type { Zone } from '../types/analyze';
import type { ConfidenceLevel } from '../domain/evaluationItems';

// 발성 구간 색상: insufficient 0~1점(미달), appropriate 2~3점(적절), excessive 4~5점(과함)
export const ZONE_COLORS: Record<Zone, string> = {
  insufficient: COLORS.danger,    // '#f44336'
  appropriate:  COLORS.success,   // '#4CAF50'
  excessive:    COLORS.warning,   // '#FFC107'
};

// 모델 신뢰도 색상
export const CONFIDENCE_COLORS: Record<ConfidenceLevel, string> = {
  high:        COLORS.success,    // '#4CAF50'
  medium:      COLORS.warning,    // '#FFC107'
  unavailable: COLORS.textMuted,  // '#666666'
};

// 타이포그래피 (한글 가독성 — 시스템 기본 폰트 우선)
export const TYPOGRAPHY = {
  heading:    { fontSize: 20, fontWeight: '700' as const },
  subheading: { fontSize: 17, fontWeight: '600' as const },
  body:       { fontSize: 15, fontWeight: '400' as const },
  caption:    { fontSize: 12, fontWeight: '400' as const },
} as const;

// 포커스 항목 강조 테두리 (사용자 목표 연동 항목)
export const FOCUS_BORDER_COLOR = COLORS.primary;
export const FOCUS_BORDER_WIDTH = 2;

// 스페이싱 (4px 배수)
export const SPACING = {
  xs:   4,
  sm:   8,
  md:   12,
  base: 16,
  lg:   24,
  xl:   32,
} as const;
