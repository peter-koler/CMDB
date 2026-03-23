import request from '@/utils/request'

export interface LicenseStatus {
  has_license: boolean
  expired: boolean
  machine_code: string
  expire_time?: string
  max_monitors: number
  enabled_monitors: number
  halted: boolean
  halt_reason?: string
  last_running_time?: string
}

export const getLicenseStatus = () => {
  return request<LicenseStatus>({
    url: '/license/status',
    method: 'get'
  })
}

export const uploadLicense = (license: string) => {
  return request({
    url: '/license/upload',
    method: 'post',
    data: { license }
  })
}
