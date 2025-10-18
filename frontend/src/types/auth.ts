export interface UserPublic {
  id: string
  email: string
  username: string
  interests: string[]
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
  last_login_at?: string | null
  created_at: string
  updated_at: string
}

export interface JwtLoginResponse {
  access_token: string
  token_type: 'bearer'
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  username: string
  password: string
  interests?: string[]
}
