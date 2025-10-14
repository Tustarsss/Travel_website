export interface UserPublic {
  id: number
  username: string
  display_name: string
  email?: string | null
  interests: string[]
  is_active: boolean
  last_login_at?: string | null
  created_at: string
  updated_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  refresh_expires_in: number
  issued_at: string
  user: UserPublic
}

export interface LoginPayload {
  identifier: string
  password: string
}

export interface RegisterPayload {
  username: string
  display_name: string
  email?: string
  password: string
  interests?: string[]
}

export interface RefreshPayload {
  refresh_token: string
}

export interface LogoutPayload {
  refresh_token: string
}
