import request from '@/utils/request'

// 部门管理
export const getDepartments = () => {
  return request({
    url: '/departments',
    method: 'GET'
  })
}

export const createDepartment = (data: any) => {
  return request({
    url: '/departments',
    method: 'POST',
    data
  })
}

export const updateDepartment = (id: number, data: any) => {
  return request({
    url: `/departments/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteDepartment = (id: number) => {
  return request({
    url: `/departments/${id}`,
    method: 'DELETE'
  })
}

// 部门用户管理
export const getDepartmentUsers = (deptId: number, params?: any) => {
  return request({
    url: `/departments/${deptId}/users`,
    method: 'GET',
    params
  })
}

export const addDepartmentUsers = (deptId: number, data: any) => {
  return request({
    url: `/departments/${deptId}/users`,
    method: 'POST',
    data
  })
}

export const removeDepartmentUser = (deptId: number, userId: number) => {
  return request({
    url: `/departments/${deptId}/users/${userId}`,
    method: 'DELETE'
  })
}

export const updateDepartmentUser = (deptId: number, userId: number, data: any) => {
  return request({
    url: `/departments/${deptId}/users/${userId}`,
    method: 'PUT',
    data
  })
}

export const updateDepartmentSort = (updates: { id: number; sort_order: number }[]) => {
  return request({
    url: '/departments/sort',
    method: 'PUT',
    data: { updates }
  })
}
