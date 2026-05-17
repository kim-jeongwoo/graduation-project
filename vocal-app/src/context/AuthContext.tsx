import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type PropsWithChildren,
} from 'react';
import * as SecureStore from 'expo-secure-store';
import * as authApi from '../api/auth';
import { API_BASE_MARKER_KEY, BASE_URL } from '../api/client';
import type { AuthResponse } from '../types/api';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

type UserInfo = Omit<AuthResponse, 'token'> & { isGuest?: boolean };

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, nickname: string) => Promise<void>;
  logout: () => Promise<void>;
  loginAsGuest: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function clearStoredAuth() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(USER_KEY);
  await SecureStore.deleteItemAsync(API_BASE_MARKER_KEY);
}

function logAuthDiag(phase: string, token: string | null, extra: Record<string, unknown> = {}) {
  if (!__DEV__) return;
  console.log('[auth diag]', {
    phase,
    apiUrl: BASE_URL,
    hasToken: Boolean(token),
    tokenLength: token?.length ?? 0,
    ...extra,
  });
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    isLoading: true,
  });

  // 앱 시작 시 저장된 토큰 + 유저 정보 복원
  useEffect(() => {
    (async () => {
      try {
        const storedToken = await SecureStore.getItemAsync(TOKEN_KEY);
        const storedUser = await SecureStore.getItemAsync(USER_KEY);
        const storedApiBase = await SecureStore.getItemAsync(API_BASE_MARKER_KEY);
        if (storedToken) {
          if (storedApiBase !== BASE_URL) {
            await clearStoredAuth();
            logAuthDiag('load-token-cleared-api-base-mismatch', storedToken, {
              storedApiBase,
            });
            setState({ token: null, user: null, isLoading: false });
            return;
          }
          const user = storedUser ? JSON.parse(storedUser) : null;
          logAuthDiag('load-token', storedToken);
          setState({ token: storedToken, user, isLoading: false });
        } else {
          logAuthDiag('load-token', null);
          setState({ token: null, user: null, isLoading: false });
        }
      } catch {
        await clearStoredAuth();
        logAuthDiag('load-token-error', null);
        setState({ token: null, user: null, isLoading: false });
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login({ email, password });
    const userInfo = { user_id: data.user_id, email: data.email, nickname: data.nickname };
    await SecureStore.setItemAsync(TOKEN_KEY, data.token);
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(userInfo));
    await SecureStore.setItemAsync(API_BASE_MARKER_KEY, BASE_URL);
    logAuthDiag('after-login', data.token);
    setState({ token: data.token, user: userInfo, isLoading: false });
  }, []);

  const signup = useCallback(
    async (email: string, password: string, nickname: string) => {
      const data = await authApi.signup({ email, password, nickname });
      const userInfo = { user_id: data.user_id, email: data.email, nickname: data.nickname };
      await SecureStore.setItemAsync(TOKEN_KEY, data.token);
      await SecureStore.setItemAsync(USER_KEY, JSON.stringify(userInfo));
      await SecureStore.setItemAsync(API_BASE_MARKER_KEY, BASE_URL);
      logAuthDiag('after-signup', data.token);
      setState({ token: data.token, user: userInfo, isLoading: false });
    },
    [],
  );

  const logout = useCallback(async () => {
    await clearStoredAuth();
    logAuthDiag('logout', null);
    setState({ token: null, user: null, isLoading: false });
  }, []);

  const loginAsGuest = useCallback(() => {
    const ts = Date.now();
    setState({
      token: `guest_token_${ts}`,
      user: { user_id: `guest_${ts}`, email: 'guest@local', nickname: '게스트', isGuest: true },
      isLoading: false,
    });
    // SecureStore에 저장하지 않음 — 앱 재시작 시 자동 로그아웃
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout, loginAsGuest }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
