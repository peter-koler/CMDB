import { useUserStore } from '@/stores/user'

interface JwtPayload {
  exp: number
  iat?: number
  sub?: string
  [key: string]: any
}

let checkInterval: number | null = null

const parseJwt = (token: string): JwtPayload | null => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Token parse error:', error)
    return null
  }
}

const CHECK_INTERVAL_MS = 60000

export const startTokenExpirationCheck = () => {
  stopTokenExpirationCheck()

  checkInterval = window.setInterval(() => {
    checkTokenExpiration()
  }, CHECK_INTERVAL_MS)
}

export const stopTokenExpirationCheck = () => {
  if (checkInterval) {
    clearInterval(checkInterval)
    checkInterval = null
  }
}

export const checkTokenExpiration = () => {
  const token = localStorage.getItem('token')
  const refreshTokenValue = localStorage.getItem('refreshToken')

  if (!token && !refreshTokenValue) {
    return
  }

  const currentTime = Math.floor(Date.now() / 1000)

  if (token) {
    const decoded = parseJwt(token)
    if (!decoded || decoded.exp < currentTime) {
      handleTokenExpired()
      return
    }
  }

  if (refreshTokenValue) {
    const decodedRefresh = parseJwt(refreshTokenValue)
    if (!decodedRefresh || decodedRefresh.exp < currentTime) {
      handleTokenExpired()
    }
  }
}

const handleTokenExpired = () => {
  const userStore = useUserStore()
  userStore.clearToken()
  window.location.href = '/login'
}

export const getTokenRemainingTime = (): number | null => {
  const token = localStorage.getItem('token')
  if (!token) return null

  const decoded = parseJwt(token)
  if (!decoded) return null

  const currentTime = Math.floor(Date.now() / 1000)
  return decoded.exp - currentTime
}
