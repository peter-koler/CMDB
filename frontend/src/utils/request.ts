import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useUserStore } from '@/stores/user'

interface ApiResponse<T = any> {
  code: number
  message?: string
  data?: T
}

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

let isRefreshing = false
let refreshingPromise: Promise<boolean> | null = null

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
    const userStore = useUserStore()
    
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refreshToken')
      
      if (refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true
          refreshingPromise = userStore.refreshTokenAction().then(success => {
            isRefreshing = false
            return success
          })
        }
        
        const success = await refreshingPromise
        if (success) {
          error.config.headers.Authorization = `Bearer ${localStorage.getItem('token')}`
          return request(error.config)
        }
      }
      
      userStore.clearToken()
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

export default request as {
  <T = any>(config: AxiosRequestConfig): Promise<ApiResponse<T>>
}
