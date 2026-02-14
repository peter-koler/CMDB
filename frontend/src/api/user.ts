import request from '@/utils/request'

export interface UserParams {
  page?: number
  per_page?: number
  keyword?: string
  role?: string
  status?: string
  sort_by?: string
  sort_order?: string
}

export interface User {
  id: number
  username: string
  email?: string
  phone?: string
  department?: string
  role: string
  status: string
  created_at: string
  last_password_change?: string
}

export const getUsers = (params: UserParams) => {
  return request({
    url: '/users',
    method: 'GET',
    params
  })
}

export const getUser = (id: number) => {
  return request({
    url: `/users/${id}`,
    method: 'GET'
  })
}

export const createUser = (data: any) => {
  return request({
    url: '/users',
    method: 'POST',
    data
  })
}

export const updateUser = (id: number, data: any) => {
  return request({
    url: `/users/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteUser = (id: number) => {
  return request({
    url: `/users/${id}`,
    method: 'DELETE'
  })
}

export const resetPassword = (id: number, newPassword: string) => {
  return request({
    url: `/users/${id}/reset-password`,
    method: 'POST',
    data: { new_password: newPassword }
  })
}

export const unlockUser = (id: number) => {
  return request({
    url: `/users/${id}/unlock`,
    method: 'POST'
  })
}
