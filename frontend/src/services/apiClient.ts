import axios, { type AxiosRequestHeaders, type InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
})

type AccessTokenGetter = () => string | null
type RefreshHandler = () => Promise<string | null>
type UnauthorizedHandler = () => void

let getAccessToken: AccessTokenGetter | null = null
let refreshTokens: RefreshHandler | null = null
let onUnauthorized: UnauthorizedHandler | null = null
let refreshPromise: Promise<string | null> | null = null

export interface AuthInterceptorOptions {
  getAccessToken?: AccessTokenGetter
  refreshTokens?: RefreshHandler
  onUnauthorized?: UnauthorizedHandler
}

export const configureAuthInterceptors = (options: AuthInterceptorOptions) => {
  getAccessToken = options.getAccessToken ?? getAccessToken
  refreshTokens = options.refreshTokens ?? refreshTokens
  onUnauthorized = options.onUnauthorized ?? onUnauthorized
}

const ensureHeaders = (config: InternalAxiosRequestConfig): AxiosRequestHeaders => {
  const headers = (config.headers ?? {}) as AxiosRequestHeaders
  headers['Accept'] = headers['Accept'] ?? 'application/json'
  headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
  return headers
}

const resolveAccessToken = (): string | null => {
  if (typeof getAccessToken === 'function') {
    return getAccessToken() ?? null
  }
  return null
}

const scheduleRefresh = async (): Promise<string | null> => {
  if (!refreshTokens) {
    return null
  }

  if (!refreshPromise) {
    refreshPromise = refreshTokens()
      .catch((error) => {
        refreshPromise = null
        throw error
      })
      .then((token) => {
        refreshPromise = null
        return token
      })
  }

  return refreshPromise
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const headers = ensureHeaders(config)
  const token = resolveAccessToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  config.headers = headers
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error
    if (!response || !config) {
      return Promise.reject(error)
    }

    if (response.status !== 401) {
      return Promise.reject(error)
    }

    if (!refreshTokens) {
      onUnauthorized?.()
      return Promise.reject(error)
    }

    const originalRequest = config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (originalRequest._retry) {
      onUnauthorized?.()
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const newToken = await scheduleRefresh()
      if (!newToken) {
        onUnauthorized?.()
        return Promise.reject(error)
      }

      originalRequest.headers = ensureHeaders(originalRequest)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      onUnauthorized?.()
      return Promise.reject(refreshError)
    }
  }
)

export default apiClient
