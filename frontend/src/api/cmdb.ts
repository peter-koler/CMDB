import request from '@/utils/request'

// 模型目录
export function getCategories() {
  return request({
    url: '/cmdb/categories',
    method: 'get'
  })
}

export function createCategory(data: any) {
  return request({
    url: '/cmdb/categories',
    method: 'post',
    data
  })
}

export function updateCategory(id: number, data: any) {
  return request({
    url: `/cmdb/categories/${id}`,
    method: 'put',
    data
  })
}

export function deleteCategory(id: number) {
  return request({
    url: `/cmdb/categories/${id}`,
    method: 'delete'
  })
}

// 模型类型
export function getModelTypes() {
  return request({
    url: '/cmdb/types',
    method: 'get'
  })
}

export function createModelType(data: any) {
  return request({
    url: '/cmdb/types',
    method: 'post',
    data
  })
}

export function updateModelType(id: number, data: any) {
  return request({
    url: `/cmdb/types/${id}`,
    method: 'put',
    data
  })
}

export function deleteModelType(id: number) {
  return request({
    url: `/cmdb/types/${id}`,
    method: 'delete'
  })
}

// 模型
export function getModels(params: any) {
  return request({
    url: '/cmdb/models',
    method: 'get',
    params
  })
}

export function getModelsTree() {
  return request({
    url: '/cmdb/models/tree',
    method: 'get'
  })
}

export function getModelDetail(id: number) {
  return request({
    url: `/cmdb/models/${id}`,
    method: 'get'
  })
}

export function createModel(data: any) {
  return request({
    url: '/cmdb/models',
    method: 'post',
    data
  })
}

export function updateModel(id: number, data: any) {
  return request({
    url: `/cmdb/models/${id}`,
    method: 'put',
    data
  })
}

export function deleteModel(id: number) {
  return request({
    url: `/cmdb/models/${id}`,
    method: 'delete'
  })
}

export function uploadModelIcon(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/cmdb/models/icon-upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 模型区域
export function createRegion(modelId: number, data: any) {
  return request({
    url: `/cmdb/models/${modelId}/regions`,
    method: 'post',
    data
  })
}

export function updateRegion(id: number, data: any) {
  return request({
    url: `/cmdb/regions/${id}`,
    method: 'put',
    data
  })
}

export function deleteRegion(id: number) {
  return request({
    url: `/cmdb/regions/${id}`,
    method: 'delete'
  })
}

// 模型字段
export function createField(modelId: number, data: any) {
  return request({
    url: `/cmdb/models/${modelId}/fields`,
    method: 'post',
    data
  })
}

export function updateField(id: number, data: any) {
  return request({
    url: `/cmdb/fields/${id}`,
    method: 'put',
    data
  })
}

export function deleteField(id: number) {
  return request({
    url: `/cmdb/fields/${id}`,
    method: 'delete'
  })
}

export function sortFields(data: { field_orders: { id: number; sort_order: number }[] }) {
  return request({
    url: '/cmdb/fields/sort',
    method: 'post',
    data
  })
}

// 导入导出
export function exportModel(id: number) {
  return request({
    url: `/cmdb/models/${id}/export`,
    method: 'get'
  })
}

export function importModel(data: any) {
  return request({
    url: '/cmdb/models/import',
    method: 'post',
    data
  })
}

// 字典类型
export function getDictTypes(params?: any) {
  return request({
    url: '/cmdb/dict/types',
    method: 'get',
    params
  })
}

export function createDictType(data: any) {
  return request({
    url: '/cmdb/dict/types',
    method: 'post',
    data
  })
}

export function updateDictType(id: number, data: any) {
  return request({
    url: `/cmdb/dict/types/${id}`,
    method: 'put',
    data
  })
}

export function deleteDictType(id: number) {
  return request({
    url: `/cmdb/dict/types/${id}`,
    method: 'delete'
  })
}

// 字典项
export function getDictItems(typeId: number, params?: any) {
  return request({
    url: `/cmdb/dict/types/${typeId}/items`,
    method: 'get',
    params
  })
}

export function createDictItem(typeId: number, data: any) {
  return request({
    url: `/cmdb/dict/types/${typeId}/items`,
    method: 'post',
    data
  })
}

export function updateDictItem(id: number, data: any) {
  return request({
    url: `/cmdb/dict/items/${id}`,
    method: 'put',
    data
  })
}

export function deleteDictItem(id: number) {
  return request({
    url: `/cmdb/dict/items/${id}`,
    method: 'delete'
  })
}

export function getDictItemsByTypeCode(typeCode: string, params?: any) {
  return request({
    url: `/cmdb/dict/items/by-type-code/${typeCode}`,
    method: 'get',
    params
  })
}
