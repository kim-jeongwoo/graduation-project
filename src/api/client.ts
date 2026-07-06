import axios, { type AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';

// Release fallback is production only. For local/ngrok development, set
// EXPO_PUBLIC_API_URL in a local .env or shell instead of hardcoding it here.

const SERVER_URLS = {
  production: 'https://api.vocal-fit.com',  // 5/10 학원 실험 + 6/15 발표
};

const CURRENT_SERVER: keyof typeof SERVER_URLS = 'production';

const configuredBaseUrl = process.env.EXPO_PUBLIC_API_URL?.trim();

// EXPO_PUBLIC_API_URL 환경변수 우선, 없으면 SERVER_URLS 폴백
export const BASE_URL: string =
  configuredBaseUrl || SERVER_URLS[CURRENT_SERVER];
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';
export const API_BASE_MARKER_KEY = 'auth_api_base_url';

type AuthExpiredHandler = () => void;

let authExpiredHandler: AuthExpiredHandler | null = null;
let authExpiredNotified = false;

export function registerAuthExpiredHandler(handler: AuthExpiredHandler) {
  authExpiredHandler = handler;
  return () => {
    if (authExpiredHandler === handler) {
      authExpiredHandler = null;
    }
  };
}

export function resetAuthExpiredNotification() {
  authExpiredNotified = false;
}

async function clearStoredAuth() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
  await SecureStore.deleteItemAsync(API_BASE_MARKER_KEY);
}

function isAuthRequestPath(path: string) {
  return path.startsWith('/auth/');
}

function hasAuthorizationHeader(headers: unknown) {
  if (!headers || typeof headers !== 'object') return false;
  const maybeHeaders = headers as {
    Authorization?: unknown;
    authorization?: unknown;
    get?: (name: string) => unknown;
  };
  return Boolean(
    maybeHeaders.Authorization
      ?? maybeHeaders.authorization
      ?? maybeHeaders.get?.('Authorization')
      ?? maybeHeaders.get?.('authorization'),
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

export function isAuthExpiredError(error: unknown) {
  return Boolean((error as { authExpired?: boolean } | null)?.authExpired);
}

function attachApiMeta(err: Error, error: AxiosError, authExpired = false): Error {
  const target = err as Error & {
    status?: number;
    code?: string;
    apiMeta?: ReturnType<typeof apiErrorMeta>;
    authExpired?: boolean;
  };
  target.status = error.response?.status;
  target.code = error.code;
  target.apiMeta = apiErrorMeta(error);
  if (authExpired) target.authExpired = true;
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

// Request interceptor: 저장된 토큰을 Authorization 헤더에 자동 추가
apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  const path = config.url ?? '';
  const isAuthRequest = isAuthRequestPath(path);
  if (token && !isAuthRequest) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: 401 시 토큰 삭제 + 에러 메시지 정규화
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    let authExpired = false;
    if (error.response?.status === 401) {
      const path = error.config?.url ?? '';
      const shouldNotifyAuthExpired =
        !isAuthRequestPath(path) && hasAuthorizationHeader(error.config?.headers);
      authExpired = shouldNotifyAuthExpired;

      await clearStoredAuth();

      if (shouldNotifyAuthExpired && !authExpiredNotified) {
        authExpiredNotified = true;
        authExpiredHandler?.();
      }
    }

    if (axios.isAxiosError(error)) {
      if (error.response?.data?.detail) {
        // FastAPI의 {"detail": "메시지"} 형태 에러 — status 보존하여 재발사
        const err = new Error(typeof error.response.data.detail === 'string'
          ? error.response.data.detail
          : JSON.stringify(error.response.data.detail));
        return Promise.reject(attachApiMeta(err, error, authExpired));
      }
      if (error.response?.data) {
        const err = new Error(JSON.stringify(error.response.data));
        return Promise.reject(attachApiMeta(err, error, authExpired));
      }
      if (error.request && !error.response) {
        return Promise.reject(attachApiMeta(
          new Error('서버에 연결할 수 없습니다. 네트워크를 확인하세요.'),
          error,
        ));
      }
    }

    if (authExpired && error && typeof error === 'object') {
      (error as { authExpired?: boolean }).authExpired = true;
    }
    return Promise.reject(error);
  },
);

export default apiClient;
