import request from '@/utils/request'

// 角色管理
export const getRoles = (params?: any) => {
  return request({
    url: '/roles',
    method: 'GET',
    params
  })
}

export const createRole = (data: any) => {
  return request({
    url: '/roles',
    method: 'POST',
    data
  })
}

export const updateRole = (id: number, data: any) => {
  return request({
    url: `/roles/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteRole = (id: number) => {
  return request({
    url: `/roles/${id}`,
    method: 'DELETE'
  })
}

// 角色用户管理
export const getRoleUsers = (roleId: number, params?: any) => {
  return request({
    url: `/roles/${roleId}/users`,
    method: 'GET',
    params
  })
}

export const addRoleUsers = (roleId: number, data: any) => {
  return request({
    url: `/roles/${roleId}/users`,
    method: 'POST',
    data
  })
}

export const removeRoleUser = (roleId: number, userId: number) => {
  return request({
    url: `/roles/${roleId}/users/${userId}`,
    method: 'DELETE'
  })
}

// 菜单权限树
export const getMenuTree = () => {
  return request({
    url: '/roles/menus/tree',
    method: 'GET'
  })
}
