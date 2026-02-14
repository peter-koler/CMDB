import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login, logout, getCurrentUser, refreshToken } from '@/api/auth'

interface UserInfo {
  id: number
  username: string
  role: string
  email?: string
  phone?: string
  department?: string
  permissions: string[]
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const refreshTokenValue = ref<string | null>(localStorage.getItem('refreshToken'))
  const userInfo = ref<UserInfo | null>(null)

  const setToken = (newToken: string, newRefreshToken: string) => {
    token.value = newToken
    refreshTokenValue.value = newRefreshToken
    localStorage.setItem('token', newToken)
    localStorage.setItem('refreshToken', newRefreshToken)
  }

  const clearToken = () => {
    token.value = null
    refreshTokenValue.value = null
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  const loginAction = async (username: string, password: string) => {
    const res = await login(username, password)
    if (res.code === 200) {
      setToken(res.data.access_token, res.data.refresh_token)
      userInfo.value = res.data.user
      return true
    }
    return false
  }

  const logoutAction = async () => {
    try {
      await logout()
    } catch (e) {
      console.error(e)
    }
    clearToken()
  }

  const getUserInfo = async () => {
    try {
      const res = await getCurrentUser()
      if (res.code === 200) {
        userInfo.value = res.data
        return true
      }
    } catch (e) {
      console.error(e)
    }
    return false
  }

  const refreshTokenAction = async () => {
    try {
      const res = await refreshToken(refreshTokenValue.value!)
      if (res.code === 200) {
        setToken(res.data.access_token, refreshTokenValue.value!)
        return true
      }
    } catch (e) {
      console.error(e)
    }
    clearToken()
    return false
  }

  const hasPermission = (permission: string) => {
    if (!userInfo.value) return false
    if (userInfo.value.role === 'admin') return true
    return userInfo.value.permissions.includes(permission)
  }

  return {
    token,
    userInfo,
    loginAction,
    logoutAction,
    getUserInfo,
    refreshTokenAction,
    hasPermission,
    clearToken
  }
})
