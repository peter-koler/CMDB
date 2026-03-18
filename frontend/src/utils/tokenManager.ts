import { useUserStore } from '@/stores/user'

interface JwtPayload {
  exp: number
  iat?: number
  sub?: string
  [key: string]: any
}

let checkInterval: number | null = null
let idleTimer: number | null = null
let idleDeadlineTs: number | null = null
let idleListenersBound = false

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
const DEFAULT_IDLE_LOGOUT_MINUTES = 30
const IDLE_LOGOUT_MINUTES_KEY = 'idleLogoutMinutes'
const IDLE_ACTIVITY_EVENTS: Array<keyof WindowEventMap> = [
  'mousemove',
  'keydown',
  'click',
  'scroll',
  'touchstart'
]

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

const resolveIdleLogoutMinutes = (minutes?: number) => {
  if (typeof minutes === 'number' && Number.isFinite(minutes) && minutes > 0) {
    return Math.floor(minutes)
  }
  const stored = Number.parseInt(localStorage.getItem(IDLE_LOGOUT_MINUTES_KEY) || '', 10)
  if (Number.isFinite(stored) && stored > 0) {
    return stored
  }
  return DEFAULT_IDLE_LOGOUT_MINUTES
}

const bindIdleListeners = () => {
  if (idleListenersBound) return
  IDLE_ACTIVITY_EVENTS.forEach((eventName) => {
    window.addEventListener(eventName, handleUserActivity)
  })
  document.addEventListener('visibilitychange', handleVisibilityChange)
  idleListenersBound = true
}

const unbindIdleListeners = () => {
  if (!idleListenersBound) return
  IDLE_ACTIVITY_EVENTS.forEach((eventName) => {
    window.removeEventListener(eventName, handleUserActivity)
  })
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  idleListenersBound = false
}

const scheduleIdleTimer = (delayMs: number) => {
  if (idleTimer) {
    clearTimeout(idleTimer)
  }
  idleTimer = window.setTimeout(() => {
    handleIdleExpired()
  }, Math.max(0, delayMs))
}

const resetIdleTimer = (minutes?: number) => {
  const effectiveMinutes = resolveIdleLogoutMinutes(minutes)
  const timeoutMs = effectiveMinutes * 60 * 1000
  idleDeadlineTs = Date.now() + timeoutMs
  scheduleIdleTimer(timeoutMs)
}

const handleUserActivity = () => {
  if (!localStorage.getItem('token')) return
  resetIdleTimer()
}

const handleVisibilityChange = () => {
  if (!localStorage.getItem('token') || idleDeadlineTs === null) return
  const remainingMs = idleDeadlineTs - Date.now()
  if (remainingMs <= 0) {
    handleIdleExpired()
    return
  }
  if (document.visibilityState === 'visible') {
    scheduleIdleTimer(remainingMs)
  }
}

const handleIdleExpired = () => {
  const userStore = useUserStore()
  userStore.clearToken()
  window.location.href = '/login'
}

export const startIdleLogoutCheck = (minutes?: number) => {
  const effectiveMinutes = resolveIdleLogoutMinutes(minutes)
  localStorage.setItem(IDLE_LOGOUT_MINUTES_KEY, String(effectiveMinutes))
  bindIdleListeners()
  resetIdleTimer(effectiveMinutes)
}

export const stopIdleLogoutCheck = () => {
  if (idleTimer) {
    clearTimeout(idleTimer)
    idleTimer = null
  }
  idleDeadlineTs = null
  unbindIdleListeners()
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
