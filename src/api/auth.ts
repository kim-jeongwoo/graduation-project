import apiClient, { BASE_URL } from './client';
import type { SignupRequest, LoginRequest, AuthResponse } from '../types/api';

export async function signup(data: SignupRequest): Promise<AuthResponse> {
  console.log('[AUTH] signup 요청 URL:', BASE_URL + '/auth/signup');
  console.log('[AUTH] signup 요청 데이터:', JSON.stringify(data));
  try {
    const res = await apiClient.post<AuthResponse>('/auth/signup', data);
    console.log('[AUTH] signup 응답:', JSON.stringify(res.data));
    return res.data;
  } catch (error: any) {
    console.log('[AUTH] signup 에러:', error.message);
    console.log('[AUTH] signup 에러 상세:', error.response?.status, JSON.stringify(error.response?.data));
    throw error;
  }
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  console.log('[AUTH] login 요청 URL:', BASE_URL + '/auth/login');
  console.log('[AUTH] login 요청 데이터:', JSON.stringify(data));
  try {
    const res = await apiClient.post<AuthResponse>('/auth/login', data);
    console.log('[AUTH] login 응답:', JSON.stringify(res.data));
    return res.data;
  } catch (error: any) {
    console.log('[AUTH] login 에러:', error.message);
    console.log('[AUTH] login 에러 상세:', error.response?.status, JSON.stringify(error.response?.data));
    throw error;
  }
}
