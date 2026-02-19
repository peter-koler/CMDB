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

export const uploadLogo = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/configs/logo',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const deleteLogo = () => {
  return request({
    url: '/configs/logo',
    method: 'DELETE'
  })
}
