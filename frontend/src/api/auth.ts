import request from '@/utils/request'

export const login = (username: string, password: string) => {
  return request({
    url: '/auth/login',
    method: 'POST',
    data: { username, password }
  })
}

export const logout = () => {
  return request({
    url: '/auth/logout',
    method: 'POST'
  })
}

export const getCurrentUser = () => {
  return request({
    url: '/auth/me',
    method: 'GET'
  })
}

export const refreshToken = (refreshToken: string) => {
  return request({
    url: '/auth/refresh',
    method: 'POST',
    headers: {
      Authorization: `Bearer ${refreshToken}`
    }
  })
}

export const changePassword = (oldPassword: string, newPassword: string) => {
  return request({
    url: '/auth/change-password',
    method: 'POST',
    data: { old_password: oldPassword, new_password: newPassword }
  })
}
