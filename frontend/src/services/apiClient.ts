import axios, { type AxiosRequestHeaders, type InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const headers = (config.headers ?? {}) as AxiosRequestHeaders
  headers['Accept'] = headers['Accept'] ?? 'application/json'
  headers['Content-Type'] = headers['Content-Type'] ?? 'application/json'
  config.headers = headers
  return config
})

export default apiClient
