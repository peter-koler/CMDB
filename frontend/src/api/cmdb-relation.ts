import request from '@/utils/request'

// 关系类型
export function getRelationTypes(params: any) {
  return request.get('/cmdb/relation-types', { params })
}

export function createRelationType(data: any) {
  return request.post('/cmdb/relation-types', data)
}

export function getRelationType(id: number) {
  return request.get(`/cmdb/relation-types/${id}`)
}

export function updateRelationType(id: number, data: any) {
  return request.put(`/cmdb/relation-types/${id}`, data)
}

export function deleteRelationType(id: number) {
  return request.delete(`/cmdb/relation-types/${id}`)
}

// 关系实例
export function getInstanceRelations(id: number, params?: any) {
  return request.get(`/cmdb/instances/${id}/relations`, { params })
}

export function createRelation(data: any) {
  return request.post('/cmdb/relations', data)
}

export function deleteRelation(id: number) {
  return request.delete(`/cmdb/relations/${id}`)
}

// 拓扑图
export function getTopology(params: any) {
  return request.get('/cmdb/topology', { params })
}

export function exportTopology(params: any) {
  return request.get('/cmdb/topology/export', { params, responseType: 'blob' })
}

// 关系触发器
export function getRelationTriggers(params: any) {
  return request.get('/cmdb/relation-triggers', { params })
}

export function createRelationTrigger(data: any) {
  return request.post('/cmdb/relation-triggers', data)
}

export function getRelationTrigger(id: number) {
  return request.get(`/cmdb/relation-triggers/${id}`)
}

export function updateRelationTrigger(id: number, data: any) {
  return request.put(`/cmdb/relation-triggers/${id}`, data)
}

export function deleteRelationTrigger(id: number) {
  return request.delete(`/cmdb/relation-triggers/${id}`)
}

export function toggleRelationTrigger(id: number) {
  return request.put(`/cmdb/relation-triggers/${id}/toggle`)
}
