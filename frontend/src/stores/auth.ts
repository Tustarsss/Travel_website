import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { configureAuthInterceptors } from '../services/apiClient'
import {
  registerUser,
  loginUser,
  fetchCurrentUser,
} from '../services/auth'
import type {
  LoginPayload,
  RegisterPayload,
  UserPublic,
} from '../types/auth'

const STORAGE_KEY = 'travel-auth-session'
let interceptorsConfigured = false

interface PersistedSession {
  accessToken: string | null
  user: UserPublic | null
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserPublic | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => {
    return Boolean(accessToken.value && user.value)
  })

  const persistSession = () => {
    const payload: PersistedSession = {
      accessToken: accessToken.value,
      user: user.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  const clearSession = () => {
    accessToken.value = null
    user.value = null
    error.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  const loadFromStorage = () => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return
    try {
      const payload = JSON.parse(stored) as PersistedSession
      accessToken.value = payload.accessToken
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
      const res = await loginUser(credentials)
      accessToken.value = res.access_token
      persistSession()
      // fetch profile separately
      user.value = await fetchCurrentUser()
      persistSession()
      return user.value
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

  const logout = async () => {
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
  }

  initialize()

  if (!interceptorsConfigured) {
    configureAuthInterceptors({
      getAccessToken: () => accessToken.value,
      onUnauthorized: () => {
        clearSession()
      },
    })
    interceptorsConfigured = true
  }

  return {
    accessToken,
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    ensureProfile,
    clearSession,
    initialize,
  }
})
