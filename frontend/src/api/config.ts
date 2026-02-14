import request from '@/utils/request'

export const getConfigs = () => {
  return request({
    url: '/configs',
    method: 'GET'
  })
}

export const updateConfigs = (data: any) => {
  return request({
    url: '/configs',
    method: 'PUT',
    data
  })
}
