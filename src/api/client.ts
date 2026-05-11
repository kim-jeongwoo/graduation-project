import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// ─── 서버 주소 설정 ───
// 같은 네트워크(집/연구실): CURRENT_SERVER = "local"
// 외부 접속 시:
//   1. 서버 PC에서 ngrok http 8000 실행
//   2. 나온 https://xxxx.ngrok-free.app 주소를 tunnel에 입력
//   3. CURRENT_SERVER = "tunnel" 로 변경
// ngrok 무료 플랜은 주소가 매번 바뀌므로 재시작 시 tunnel 주소 갱신 필요

const SERVER_URLS = {
  local: 'http://192.168.0.16:8000',
  tunnel: 'https://0a10-114-71-220-101.ngrok-free.app',
  production: 'https://api.vocal-fit.com',  // 5/10 학원 실험 + 6/15 발표
};

const CURRENT_SERVER: keyof typeof SERVER_URLS = 'production';

// EXPO_PUBLIC_API_URL 환경변수 우선, 없으면 SERVER_URLS 폴백
export const BASE_URL: string =
  process.env.EXPO_PUBLIC_API_URL ?? SERVER_URLS[CURRENT_SERVER];
const TOKEN_KEY = 'auth_token';

/**
 * ngrok 터널 사용 시 필요한 기본 헤더.
 * ngrok 무료 플랜은 브라우저 경고 페이지를 반환하는데,
 * 이 헤더가 없으면 fetch()가 HTML을 받아 JSON 파싱 실패함.
 */
export const DEFAULT_FETCH_HEADERS: Record<string, string> = {
  'ngrok-skip-browser-warning': 'true',
  'Accept': 'application/json',
};

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
});

// Request interceptor: 저장된 토큰을 Authorization 헤더에 자동 추가 + 디버깅 로그
apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  return config;
});

// Response interceptor: 401 시 토큰 삭제 + 에러 메시지 정규화
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (__DEV__ && axios.isAxiosError(error)) {
      console.error('[API] error', {
        req: `${error.config?.method?.toUpperCase()} ${error.config?.url}`,
        status: error.response?.status,
        data: JSON.stringify(error.response?.data ?? null).slice(0, 400),
        code: error.code, // ECONNABORTED = timeout
      });
    }
    if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    }

    if (axios.isAxiosError(error)) {
      if (error.response?.data?.detail) {
        // FastAPI의 {"detail": "메시지"} 형태 에러 — status 보존하여 재발사
        const err = new Error(typeof error.response.data.detail === 'string'
          ? error.response.data.detail
          : JSON.stringify(error.response.data.detail));
        (err as Error & { status?: number }).status = error.response.status;
        return Promise.reject(err);
      }
      if (error.response?.data) {
        const err = new Error(JSON.stringify(error.response.data));
        (err as Error & { status?: number }).status = error.response.status;
        return Promise.reject(err);
      }
      if (error.request && !error.response) {
        return Promise.reject(
          new Error('서버에 연결할 수 없습니다. 네트워크를 확인하세요.'),
        );
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
