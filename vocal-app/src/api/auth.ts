import apiClient, { BASE_URL } from './client';
import type { SignupRequest, LoginRequest, AuthResponse } from '../types/api';

export async function signup(data: SignupRequest): Promise<AuthResponse> {
  console.log('[auth diag]', {
    phase: 'signup-request',
    apiUrl: BASE_URL,
    hasEmail: Boolean(data.email),
    hasPassword: Boolean(data.password),
    hasNickname: Boolean(data.nickname),
  });
  try {
    const res = await apiClient.post<AuthResponse>('/auth/signup', data);
    console.log('[auth diag]', {
      phase: 'after-signup',
      apiUrl: BASE_URL,
      hasToken: Boolean(res.data.token),
      tokenLength: res.data.token?.length ?? 0,
      hasUserId: Boolean(res.data.user_id),
    });
    return res.data;
  } catch (error: any) {
    console.log('[auth diag]', {
      phase: 'signup-error',
      apiUrl: BASE_URL,
      status: error.status ?? error.response?.status,
      code: error.code,
      message: error.message,
    });
    throw error;
  }
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  console.log('[auth diag]', {
    phase: 'login-request',
    apiUrl: BASE_URL,
    hasEmail: Boolean(data.email),
    hasPassword: Boolean(data.password),
  });
  try {
    const res = await apiClient.post<AuthResponse>('/auth/login', data);
    console.log('[auth diag]', {
      phase: 'after-login-response',
      apiUrl: BASE_URL,
      hasToken: Boolean(res.data.token),
      tokenLength: res.data.token?.length ?? 0,
      hasUserId: Boolean(res.data.user_id),
    });
    return res.data;
  } catch (error: any) {
    console.log('[auth diag]', {
      phase: 'login-error',
      apiUrl: BASE_URL,
      status: error.status ?? error.response?.status,
      code: error.code,
      message: error.message,
    });
    throw error;
  }
}
