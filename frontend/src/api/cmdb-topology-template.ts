import request from '@/utils/request'

export interface TopologyTemplateLayer {
  id: string
  name: string
  modelKeys: string[]
}

export interface TopologyTemplate {
  id: string
  name: string
  description: string
  seedModels: string[]
  traverseDirection: 'up' | 'down' | 'both'
  allowedRelationTypes: string[]
  visibleModelKeys: string[]
  layers: TopologyTemplateLayer[]
  layoutDirection: 'horizontal' | 'vertical'
  groupBy: 'idc' | 'subnet' | 'owner' | string
  aggregateEnabled: boolean
  aggregateThreshold: number
  createdAt?: string
  updatedAt?: string
  createdBy?: number
  updatedBy?: number
}

export const listCmdbTopologyTemplates = (params?: { keyword?: string }) => {
  return request.get('/cmdb/topology-templates', { params })
}

export const getCmdbTopologyTemplate = (id: string) => {
  return request.get(`/cmdb/topology-templates/${id}`)
}

export const createCmdbTopologyTemplate = (data: Partial<TopologyTemplate>) => {
  return request.post('/cmdb/topology-templates', data)
}

export const updateCmdbTopologyTemplate = (id: string, data: Partial<TopologyTemplate>) => {
  return request.put(`/cmdb/topology-templates/${id}`, data)
}

export const deleteCmdbTopologyTemplate = (id: string) => {
  return request.delete(`/cmdb/topology-templates/${id}`)
}

export const cloneCmdbTopologyTemplate = (id: string) => {
  return request.post(`/cmdb/topology-templates/${id}/clone`)
}
