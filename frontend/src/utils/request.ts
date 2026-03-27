import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useUserStore } from '@/stores/user'

interface ApiResponse<T = any> {
  code: number
  message?: string
  data?: T
}

interface RequestInstance {
  <T = any>(config: AxiosRequestConfig): Promise<ApiResponse<T>>
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  head<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  options<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  defaults: AxiosInstance['defaults']
  interceptors: AxiosInstance['interceptors']
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true
}) as unknown as RequestInstance

// 用于存储刷新 token 的 Promise
let refreshPromise: Promise<boolean> | null = null

request.interceptors.request.use(
  (config) => {
    if (config.url === '/auth/refresh') {
      return config
    }
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data as any
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 402) {
      const isLoginRequest = originalRequest?.url === '/auth/login'
      if (window.location.pathname === '/login' && isLoginRequest) {
        return Promise.reject(error)
      }
      if (window.location.pathname !== '/license') {
        window.location.href = '/license'
      }
      return Promise.reject(error)
    }

    // 如果不是 401 错误，直接返回错误
    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    // 如果是登录请求返回 401，直接返回错误（密码错误或账户锁定）
    if (originalRequest.url === '/auth/login') {
      return Promise.reject(error)
    }

    // 如果是刷新 token 的请求返回 401，说明 token 已失效，直接跳转登录
    if (originalRequest.url === '/auth/refresh') {
      const userStore = useUserStore()
      userStore.clearToken()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    const userStore = useUserStore()
    const refreshTokenValue = localStorage.getItem('refreshToken')

    // 如果没有 refresh token，直接跳转登录
    if (!refreshTokenValue) {
      userStore.clearToken()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 如果有正在进行的刷新请求，等待它完成
    if (!refreshPromise) {
      refreshPromise = userStore.refreshTokenAction().finally(() => {
        refreshPromise = null
      })
    }

    const success = await refreshPromise

    if (success) {
      // 刷新成功，重试原请求
      originalRequest.headers.Authorization = `Bearer ${localStorage.getItem('token')}`
      return request(originalRequest)
    } else {
      // 刷新失败，跳转登录
      userStore.clearToken()
      window.location.href = '/login'
      return Promise.reject(error)
    }
  }
)

export const getBaseURL = () => {
  return ''
}

export default request
