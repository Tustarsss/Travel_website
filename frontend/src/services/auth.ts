import apiClient from './apiClient'
import type {
  LoginPayload,
  RegisterPayload,
  TokenPair,
  RefreshPayload,
  LogoutPayload,
  UserPublic,
} from '../types/auth'

export const registerUser = async (payload: RegisterPayload): Promise<UserPublic> => {
  const { data } = await apiClient.post<UserPublic>('/auth/register', payload)
  return data
}

export const loginUser = async (payload: LoginPayload): Promise<TokenPair> => {
  const { data } = await apiClient.post<TokenPair>('/auth/login', payload)
  return data
}

export const refreshTokenPair = async (payload: RefreshPayload): Promise<TokenPair> => {
  const { data } = await apiClient.post<TokenPair>('/auth/refresh', payload)
  return data
}

export const logoutUser = async (payload: LogoutPayload): Promise<void> => {
  await apiClient.post('/auth/logout', payload)
}

export const fetchCurrentUser = async (): Promise<UserPublic> => {
  const { data } = await apiClient.get<UserPublic>('/auth/me')
  return data
}
