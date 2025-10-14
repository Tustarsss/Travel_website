import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { configureAuthInterceptors } from '../services/apiClient'
import {
  registerUser,
  loginUser,
  refreshTokenPair,
  logoutUser,
  fetchCurrentUser,
} from '../services/auth'
import type {
  LoginPayload,
  RegisterPayload,
  TokenPair,
  UserPublic,
} from '../types/auth'

const STORAGE_KEY = 'travel-auth-session'
let interceptorsConfigured = false

interface PersistedSession {
  accessToken: string | null
  refreshToken: string | null
  tokenExpiresAt: number | null
  refreshExpiresAt: number | null
  user: UserPublic | null
}

const toTimestamp = (isoString: string): number => new Date(isoString).getTime()

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const tokenExpiresAt = ref<number | null>(null)
  const refreshExpiresAt = ref<number | null>(null)
  const user = ref<UserPublic | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => {
    if (!accessToken.value || !user.value) return false
    if (tokenExpiresAt.value && tokenExpiresAt.value <= Date.now()) return false
    return true
  })

  const persistSession = () => {
    const payload: PersistedSession = {
      accessToken: accessToken.value,
      refreshToken: refreshToken.value,
      tokenExpiresAt: tokenExpiresAt.value,
      refreshExpiresAt: refreshExpiresAt.value,
      user: user.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  const clearSession = () => {
    accessToken.value = null
    refreshToken.value = null
    tokenExpiresAt.value = null
    refreshExpiresAt.value = null
    user.value = null
    error.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  const applyTokenPair = (tokens: TokenPair) => {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    const issuedAt = toTimestamp(tokens.issued_at)
    tokenExpiresAt.value = issuedAt + tokens.expires_in * 1000
    refreshExpiresAt.value = issuedAt + tokens.refresh_expires_in * 1000
    user.value = tokens.user
    persistSession()
  }

  const loadFromStorage = () => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return
    try {
      const payload = JSON.parse(stored) as PersistedSession
      accessToken.value = payload.accessToken
      refreshToken.value = payload.refreshToken
      tokenExpiresAt.value = payload.tokenExpiresAt
      refreshExpiresAt.value = payload.refreshExpiresAt
      user.value = payload.user
    } catch (err) {
      console.warn('Failed to parse auth session', err)
      clearSession()
    }
  }

  const login = async (credentials: LoginPayload) => {
    loading.value = true
    error.value = null
    try {
      const tokens = await loginUser(credentials)
      applyTokenPair(tokens)
      return tokens.user
    } catch (err: any) {
      error.value = err?.response?.data?.detail ?? '登录失败，请稍后重试'
      throw err
    } finally {
      loading.value = false
    }
  }

  const register = async (payload: RegisterPayload) => {
    loading.value = true
    error.value = null
    try {
      const profile = await registerUser(payload)
      return profile
    } catch (err: any) {
      error.value = err?.response?.data?.detail ?? '注册失败，请稍后重试'
      throw err
    } finally {
      loading.value = false
    }
  }

  const refreshTokens = async (): Promise<string | null> => {
    if (!refreshToken.value) {
      return null
    }

    if (refreshExpiresAt.value && refreshExpiresAt.value <= Date.now()) {
      clearSession()
      return null
    }

    try {
      const tokens = await refreshTokenPair({ refresh_token: refreshToken.value })
      applyTokenPair(tokens)
      return tokens.access_token
    } catch (err) {
      clearSession()
      return null
    }
  }

  const logout = async () => {
    if (refreshToken.value) {
      try {
        await logoutUser({ refresh_token: refreshToken.value })
      } catch (err) {
        console.warn('Failed to notify backend logout', err)
      }
    }
    clearSession()
  }

  const ensureProfile = async () => {
    if (!accessToken.value) return null
    if (!user.value) {
      try {
        user.value = await fetchCurrentUser()
        persistSession()
      } catch (err) {
        console.warn('Failed to fetch current user profile', err)
      }
    }
    return user.value
  }

  const initialize = () => {
    loadFromStorage()
    if (
      accessToken.value &&
      tokenExpiresAt.value &&
      tokenExpiresAt.value <= Date.now() &&
      refreshToken.value
    ) {
      void refreshTokens()
    }
  }

  initialize()

  if (!interceptorsConfigured) {
    configureAuthInterceptors({
      getAccessToken: () => accessToken.value,
      refreshTokens,
      onUnauthorized: () => {
        clearSession()
      },
    })
    interceptorsConfigured = true
  }

  return {
    accessToken,
    refreshToken,
    tokenExpiresAt,
    refreshExpiresAt,
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    refreshTokens,
    logout,
    ensureProfile,
    clearSession,
    initialize,
  }
})
