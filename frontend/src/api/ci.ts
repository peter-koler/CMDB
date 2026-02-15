import request from '@/utils/request'

// CI实例管理
export const getInstances = (params?: any) => {
  return request({
    url: '/cmdb/instances',
    method: 'GET',
    params
  })
}

export const getInstance = (id: number) => {
  return request({
    url: `/cmdb/instances/${id}`,
    method: 'GET'
  })
}

export const createInstance = (data: any) => {
  return request({
    url: '/cmdb/instances',
    method: 'POST',
    data
  })
}

export const updateInstance = (id: number, data: any) => {
  return request({
    url: `/cmdb/instances/${id}`,
    method: 'PUT',
    data
  })
}

export const deleteInstance = (id: number) => {
  return request({
    url: `/cmdb/instances/${id}`,
    method: 'DELETE'
  })
}

// 批量操作
export const batchUpdateInstances = (data: any) => {
  return request({
    url: '/cmdb/instances/batch-update',
    method: 'POST',
    data
  })
}

export const batchDeleteInstances = (data: any) => {
  return request({
    url: '/cmdb/instances/batch-delete',
    method: 'POST',
    data
  })
}

// 变更历史
export const getInstanceHistory = (ciId: number, params?: any) => {
  return request({
    url: `/cmdb/instances/${ciId}/history`,
    method: 'GET',
    params
  })
}

// 获取CI详情（含模型信息）
export const getInstanceDetail = (id: number) => {
  return request({
    url: `/cmdb/instances/${id}`,
    method: 'GET'
  })
}

// 获取CI变更历史
export const getCiHistory = (ciId: number) => {
  return request({
    url: `/cmdb/instances/${ciId}/history`,
    method: 'GET'
  })
}

// 获取所有CI变更历史（支持筛选）
export const getAllCiHistory = (params?: any) => {
  return request({
    url: '/cmdb/instances/history',
    method: 'GET',
    params
  })
}

// 全文搜索
export const searchInstances = (data: any) => {
  return request({
    url: '/cmdb/instances/search',
    method: 'POST',
    data
  })
}

// 文件上传
export const uploadFile = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/cmdb/instances/upload',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 生成编码
export const generateCICode = () => {
  return request({
    url: '/cmdb/instances/generate-code',
    method: 'GET'
  })
}

// 获取CI关联关系数量
export const getInstanceRelationsCount = (id: number) => {
  return request({
    url: `/cmdb/instances/${id}/relations-count`,
    method: 'GET'
  })
}

// 批量导出
export const exportInstances = (data: any) => {
  return request({
    url: '/cmdb/instances/export',
    method: 'POST',
    data,
    responseType: 'blob'
  })
}

// 批量导入
export const importInstances = (file: File, modelId: number) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('model_id', String(modelId))
  return request({
    url: '/cmdb/instances/import',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
