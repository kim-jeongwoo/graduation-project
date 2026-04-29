export const COLORS = {
  background: '#121212',        // 전체 배경
  card: '#1E1E2E',             // 카드 배경
  cardBorder: '#2A2A3E',       // 카드 테두리
  surface: '#252538',          // 카드 내부 서브 영역
  primary: '#6C63FF',          // 주요 액센트 (버튼, 강조)
  primaryLight: '#8B83FF',     // 밝은 액센트
  success: '#4CAF50',          // 성공/긍정
  warning: '#FFC107',          // 경고/주의
  danger: '#f44336',           // 실패/위험
  textPrimary: '#EAEAEA',      // 주요 텍스트
  textSecondary: '#9E9E9E',    // 보조 텍스트
  textMuted: '#666666',        // 흐린 텍스트
  divider: '#2A2A3E',          // 구분선
  fab: '#f44336',              // FAB 버튼
};

/** 공통 카드 스타일 */
export const CARD_STYLE = {
  backgroundColor: COLORS.card,
  borderRadius: 16,
  padding: 16,
  marginBottom: 12,
  borderWidth: 1,
  borderColor: COLORS.cardBorder,
} as const;
