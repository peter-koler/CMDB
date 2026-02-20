import request from '@/utils/request'

export interface UploadResponse {
  code: number
  message: string
  data: {
    filename: string
    path: string
    url: string
  }
}

export const uploadImage = (formData: FormData): Promise<UploadResponse> => {
  return request.post('/api/v1/cmdb/instances/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const uploadFile = (formData: FormData): Promise<UploadResponse> => {
  return request.post('/api/v1/cmdb/instances/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const getFileUrl = (path: string): string => {
  return `/api/v1/cmdb/instances/files/${path}`
}
