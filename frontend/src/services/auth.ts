import apiClient from './apiClient'
import type { LoginPayload, RegisterPayload, JwtLoginResponse, UserPublic } from '../types/auth'

export const registerUser = async (payload: RegisterPayload): Promise<UserPublic> => {
  const { data } = await apiClient.post<UserPublic>('/auth/register', payload)
  return data
}

export const loginUser = async (payload: LoginPayload): Promise<JwtLoginResponse> => {
  const form = new FormData()
  form.set('username', payload.email) // fastapi-users expects 'username' field containing email
  form.set('password', payload.password)
  const { data } = await apiClient.post<JwtLoginResponse>('/auth/jwt/login', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const fetchCurrentUser = async (): Promise<UserPublic> => {
  const { data } = await apiClient.get<UserPublic>('/auth/me')
  return data
}
