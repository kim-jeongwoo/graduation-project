// dml-server (실시간 분석 WebSocket) 연결 정보
// 5/9: named tunnel (Cloudflare) 적용. 학교 서버 재부팅에도 영구 유지.
// 6/15 시연까지 사용. 향후 환경 분리 시 EXPO_PUBLIC_DML_WS_URL env override.
const DEFAULT_DML_WS_URL = 'wss://dml.vocal-fit.com';

export const DML_WS_URL: string =
  process.env.EXPO_PUBLIC_DML_WS_URL ?? DEFAULT_DML_WS_URL;

export function buildRealtimeWsUrl(songId: string): string {
  return `${DML_WS_URL}/ws/realtime?song_id=${encodeURIComponent(songId)}`;
}
