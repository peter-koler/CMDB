import request from '@/utils/request'

export const getCustomViews = (params?: any) => {
  return request({
    url: '/custom-views',
    method: 'GET',
    params
  })
}

export const getCustomView = (id: number) => {
  return request({
    url: `/custom-views/${id}`,
    method: 'GET'
  })
}

export const createCustomView = (data: any) => {
  return request({
    url: '/custom-views',
    method: 'POST',
    data
  })
}

export const updateCustomView = (id: number, data: any) => {
  return request({
    url: `/custom-views/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteCustomView = (id: number) => {
  return request({
    url: `/custom-views/${id}`,
    method: 'DELETE'
  })
}

export const getViewNodes = (viewId: number) => {
  return request({
    url: `/custom-views/${viewId}/nodes`,
    method: 'GET'
  })
}

export const createNode = (data: any) => {
  return request({
    url: '/custom-view-nodes',
    method: 'POST',
    data
  })
}

export const updateNode = (id: number, data: any) => {
  return request({
    url: `/custom-view-nodes/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteNode = (id: number) => {
  return request({
    url: `/custom-view-nodes/${id}`,
    method: 'DELETE'
  })
}

export const moveNode = (id: number, data: any) => {
  return request({
    url: `/custom-view-nodes/${id}/move`,
    method: 'PUT',
    data
  })
}

export const getNodeCis = (nodeId: number, params?: any) => {
  return request({
    url: `/custom-view-nodes/${nodeId}/cis`,
    method: 'GET',
    params
  })
}

export const getViewNodesTree = (viewId: number) => {
  return request({
    url: `/custom-views/${viewId}/nodes/tree`,
    method: 'GET'
  })
}

export const getNodePermissions = (nodeId: number) => {
  return request({
    url: `/custom-view-nodes/${nodeId}/permissions`,
    method: 'GET'
  })
}

export const grantNodePermission = (nodeId: number, data: any) => {
  return request({
    url: `/custom-view-nodes/${nodeId}/permissions`,
    method: 'POST',
    data
  })
}

export const revokeNodePermission = (nodeId: number, roleId: number) => {
  return request({
    url: `/custom-view-nodes/${nodeId}/permissions/${roleId}`,
    method: 'DELETE'
  })
}

export const registerViewPermission = (data: any) => {
  return request({
    url: '/custom-views/permissions/register',
    method: 'POST',
    data
  })
}

export const unregisterViewPermission = (data: any) => {
  return request({
    url: '/custom-views/permissions/unregister',
    method: 'POST',
    data
  })
}

export const getCustomViewPermissionsTree = () => {
  return request({
    url: '/custom-views/permissions/tree',
    method: 'GET'
  })
}

export const getMyViews = () => {
  return request({
    url: '/custom-views/my',
    method: 'GET'
  })
}
