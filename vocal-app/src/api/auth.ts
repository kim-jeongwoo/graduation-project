import apiClient from './client';
import type { SignupRequest, LoginRequest, AuthResponse } from '../types/api';

export async function signup(data: SignupRequest): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/auth/signup', data);
  return res.data;
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const res = await apiClient.post<AuthResponse>('/auth/login', data);
  return res.data;
}
