import request from '@/utils/request'

export interface MonitorTemplate {
  id: number
  app: string
  name: string
  category: string
  content: string
  version: number
  is_hidden: boolean
  created_at: string
  updated_at: string
}

export interface MonitorCategory {
  id: number
  name: string
  code: string
  icon?: string
  sort_order: number
  parent_id?: number
}

export const getTemplates = (params?: { category?: string }) => {
  return request({
    url: '/monitoring/templates',
    method: 'GET',
    params
  })
}

export const getTemplate = (app: string) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'GET'
  })
}

export const createTemplate = (data: Partial<MonitorTemplate>) => {
  return request({
    url: '/monitoring/templates',
    method: 'POST',
    data
  })
}

export const updateTemplate = (app: string, data: Partial<MonitorTemplate>) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'PUT',
    data
  })
}

export const deleteTemplate = (app: string) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'DELETE'
  })
}

export const getCategories = () => {
  return request({
    url: '/monitoring/templates/categories',
    method: 'GET'
  })
}

export const createCategory = (data: Partial<MonitorCategory>) => {
  return request({
    url: '/monitoring/templates/categories',
    method: 'POST',
    data
  })
}

export const updateCategory = (code: string, data: Partial<MonitorCategory>) => {
  return request({
    url: `/monitoring/templates/categories/${code}`,
    method: 'PUT',
    data
  })
}

export const deleteCategory = (code: string) => {
  return request({
    url: `/monitoring/templates/categories/${code}`,
    method: 'DELETE'
  })
}

export const getTemplateHierarchy = (lang: string = 'zh-CN') => {
  return request({
    url: '/monitoring/templates/hierarchy',
    method: 'GET',
    params: { lang }
  })
}
