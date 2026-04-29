/** 메트릭 key → 한글 라벨 */
export const METRIC_LABELS: Record<string, string> = {
  egg_estimation_status: 'EGG 추정 상태',
  processing_time_ms: '처리 시간',
  contact_rate: '성대접촉률',
  chest_ratio: '흉성/두성 비율',
  oral_nasal_ratio: '구강/비강 비율',
  egg_correlation: 'EGG 상관계수',
};

export function getMetricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key;
}

/** 세션 status → 한글 */
const STATUS_LABELS: Record<string, string> = {
  created: '생성됨',
  recording: '녹음 중',
  uploaded: '업로드 완료',
  analyzing: '분석 중',
  completed: '완료',
  failed: '실패',
};

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

/** 세션 status → 색상 */
const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  created: { bg: '#E3F2FD', text: '#1565C0' },
  recording: { bg: '#FFF3E0', text: '#E65100' },
  uploaded: { bg: '#E8F5E9', text: '#2E7D32' },
  analyzing: { bg: '#FFF8E1', text: '#F57F17' },
  completed: { bg: '#E8F5E9', text: '#2E7D32' },
  failed: { bg: '#FFEBEE', text: '#C62828' },
};

const DEFAULT_COLOR = { bg: '#F5F5F5', text: '#666' };

export function getStatusColor(status: string): { bg: string; text: string } {
  return STATUS_COLORS[status] ?? DEFAULT_COLOR;
}

/** 등급 → 색상 (A=초록, B=파랑, C=노랑, D=빨강) */
export function getGradeColor(grade: string): string {
  const first = grade.charAt(0).toUpperCase();
  switch (first) {
    case 'A': return '#4CAF50';
    case 'B': return '#2196F3';
    case 'C': return '#FFC107';
    case 'D': return '#F44336';
    default: return '#9E9E9E';
  }
}

/** duration_ms → "3분 05초" 형식 */
export function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}분 ${sec.toString().padStart(2, '0')}초`;
}

/** ISO 날짜 → "2026.02.20 14:00" */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const yyyy = d.getFullYear();
  const mm = (d.getMonth() + 1).toString().padStart(2, '0');
  const dd = d.getDate().toString().padStart(2, '0');
  const hh = d.getHours().toString().padStart(2, '0');
  const mi = d.getMinutes().toString().padStart(2, '0');
  return `${yyyy}.${mm}.${dd} ${hh}:${mi}`;
}
