import request from '@/utils/request'

export interface LogParams {
  page?: number
  per_page?: number
  date_from?: string
  date_to?: string
  user_id?: number
  operation_type?: string
  status?: string
}

export const getLogs = (params: LogParams) => {
  return request({
    url: '/logs',
    method: 'GET',
    params
  })
}

export const exportLogs = (params: LogParams) => {
  return request({
    url: '/logs/export',
    method: 'GET',
    params
  })
}
