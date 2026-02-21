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

export const getProfile = () => {
  return request({
    url: '/auth/profile',
    method: 'GET'
  })
}

export const updateProfile = (data: { email?: string; phone?: string }) => {
  return request({
    url: '/auth/profile',
    method: 'PUT',
    data
  })
}

export const uploadAvatar = (file: File) => {
  const formData = new FormData()
  formData.append('avatar', file)
  return request({
    url: '/auth/avatar',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
