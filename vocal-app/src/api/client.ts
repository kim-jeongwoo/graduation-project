import axios, { type AxiosError } from 'axios';
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
const USER_KEY = 'auth_user';
export const API_BASE_MARKER_KEY = 'auth_api_base_url';

if (__DEV__) {
  console.log('[api boot]', {
    baseURL: BASE_URL,
    currentServer: CURRENT_SERVER,
    hasEnvApiUrl: Boolean(process.env.EXPO_PUBLIC_API_URL),
  });
}

function isExpectedTrainingAnalyzeValidationError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  const detail = error.response?.data?.detail;
  const detailRecord = detail && typeof detail === 'object'
    ? detail as Record<string, unknown>
    : null;
  const detailError = detailRecord?.error;
  return error.config?.url?.includes('/training-analyze') === true
    && error.response?.status === 400
    && (
      detailError === 'chunk_too_short'
      || detailError === 'no_voice'
      || detailError === 'invalid'
      || detailError === 'failed'
      || (typeof detail === 'string' && (detail.includes('최소 3초') || detail.includes('음성')))
    );
}

function isExpectedTrainingAnalyzeRecoverableError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  return isExpectedTrainingAnalyzeValidationError(error)
    || (
      error.config?.url?.includes('/training-analyze') === true
      && (error.response?.status === 504 || error.code === 'ECONNABORTED')
    );
}

function apiErrorMeta(error: AxiosError) {
  return {
    method: error.config?.method?.toUpperCase(),
    path: error.config?.url,
    baseURL: error.config?.baseURL ?? BASE_URL,
    status: error.response?.status,
    code: error.code,
    hasResponse: Boolean(error.response),
    hasRequest: Boolean(error.request),
    message: error.message,
    timeout: error.config?.timeout,
  };
}

function attachApiMeta(err: Error, error: AxiosError): Error {
  const target = err as Error & {
    status?: number;
    code?: string;
    apiMeta?: ReturnType<typeof apiErrorMeta>;
  };
  target.status = error.response?.status;
  target.code = error.code;
  target.apiMeta = apiErrorMeta(error);
  return target;
}

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
  const path = config.url ?? '';
  const isAuthRequest = path.startsWith('/auth/');
  if (token && !isAuthRequest) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (__DEV__) {
    console.log('[api diag]', {
      method: config.method?.toUpperCase(),
      path,
      baseURL: config.baseURL ?? BASE_URL,
      hasToken: Boolean(token),
      tokenLength: token?.length ?? 0,
      hasAuthHeader: Boolean((config.headers as Record<string, unknown>)?.Authorization),
      timeout: config.timeout,
    });
  }
  return config;
});

// Response interceptor: 401 시 토큰 삭제 + 에러 메시지 정규화
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (__DEV__ && axios.isAxiosError(error)) {
      const payload = apiErrorMeta(error);
      if (isExpectedTrainingAnalyzeRecoverableError(error)) {
        console.warn('[API] expected training-analyze error', payload);
      } else if (error.config?.url?.includes('/pitch-guide')) {
        console.warn('[api error diag]', payload);
      } else {
        console.error('[api error diag]', payload);
      }
    }
    if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      await SecureStore.deleteItemAsync(USER_KEY);
      await SecureStore.deleteItemAsync(API_BASE_MARKER_KEY);
    }

    if (axios.isAxiosError(error)) {
      if (error.response?.data?.detail) {
        // FastAPI의 {"detail": "메시지"} 형태 에러 — status 보존하여 재발사
        const err = new Error(typeof error.response.data.detail === 'string'
          ? error.response.data.detail
          : JSON.stringify(error.response.data.detail));
        return Promise.reject(attachApiMeta(err, error));
      }
      if (error.response?.data) {
        const err = new Error(JSON.stringify(error.response.data));
        return Promise.reject(attachApiMeta(err, error));
      }
      if (error.request && !error.response) {
        return Promise.reject(attachApiMeta(
          new Error('서버에 연결할 수 없습니다. 네트워크를 확인하세요.'),
          error,
        ));
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
