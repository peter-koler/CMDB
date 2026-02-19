import request from '@/utils/request'

// ==================== 用户通知 ====================

/**
 * 获取我的通知列表
 * @param params 查询参数
 */
export const getNotifications = (params?: {
  is_read?: boolean
  type_id?: number
  page?: number
  page_size?: number
}) => {
  return request({
    url: '/notifications/my',
    method: 'GET',
    params
  })
}

/**
 * 获取未读通知数量
 */
export const getUnreadCount = () => {
  return request({
    url: '/notifications/my/unread-count',
    method: 'GET'
  })
}

/**
 * 标记通知为已读
 * @param recipientId 接收者记录ID
 */
export const markAsRead = (recipientId: number) => {
  return request({
    url: `/notifications/my/${recipientId}/read`,
    method: 'PATCH'
  })
}

/**
 * 标记通知为未读
 * @param recipientId 接收者记录ID
 */
export const markAsUnread = (recipientId: number) => {
  return request({
    url: `/notifications/my/${recipientId}/unread`,
    method: 'PATCH'
  })
}

/**
 * 标记所有通知为已读
 */
export const markAllAsRead = () => {
  return request({
    url: '/notifications/my/read-all',
    method: 'PATCH'
  })
}

/**
 * 搜索通知
 * @param params 搜索参数
 */
export const searchNotifications = (params?: {
  q?: string
  date_from?: string
  date_to?: string
  type_id?: number
  is_read?: boolean
  page?: number
  page_size?: number
}) => {
  return request({
    url: '/notifications/my/search',
    method: 'GET',
    params
  })
}

// ==================== 通知发送（管理员） ====================

/**
 * 发送通知
 * @param data 通知数据
 */
export const sendNotification = (data: {
  recipient_type: 'users' | 'department'
  user_ids?: number[]
  department_id?: number
  type_id: number
  title: string
  content: string
  template_id?: number
  variables?: Record<string, any>
}) => {
  return request({
    url: '/notifications',
    method: 'POST',
    data
  })
}

/**
 * 发送广播通知（全员）
 * @param data 通知数据
 */
export const sendBroadcast = (data: {
  type_id: number
  title: string
  content: string
  template_id?: number
  variables?: Record<string, any>
}) => {
  return request({
    url: '/notifications/broadcast',
    method: 'POST',
    data
  })
}

// ==================== 通知类型管理 ====================

/**
 * 获取通知类型列表
 */
export const getNotificationTypes = () => {
  return request({
    url: '/notifications/types',
    method: 'GET'
  })
}

/**
 * 创建通知类型
 * @param data 类型数据
 */
export const createNotificationType = (data: {
  name: string
  description?: string
  icon?: string
  color?: string
}) => {
  return request({
    url: '/notifications/types',
    method: 'POST',
    data
  })
}

/**
 * 更新通知类型
 * @param typeId 类型ID
 * @param data 类型数据
 */
export const updateNotificationType = (typeId: number, data: {
  name?: string
  description?: string
  icon?: string
  color?: string
}) => {
  return request({
    url: `/notifications/types/${typeId}`,
    method: 'PATCH',
    data
  })
}

/**
 * 删除通知类型
 * @param typeId 类型ID
 */
export const deleteNotificationType = (typeId: number) => {
  return request({
    url: `/notifications/types/${typeId}`,
    method: 'DELETE'
  })
}

// ==================== 通知模板管理 ====================

/**
 * 获取模板列表
 */
export const getTemplates = () => {
  return request({
    url: '/notifications/templates',
    method: 'GET'
  })
}

/**
 * 创建模板
 * @param data 模板数据
 */
export const createTemplate = (data: {
  name: string
  title_template: string
  content_template: string
  type_id: number
  description?: string
}) => {
  return request({
    url: '/notifications/templates',
    method: 'POST',
    data
  })
}

/**
 * 更新模板
 * @param templateId 模板ID
 * @param data 模板数据
 */
export const updateTemplate = (templateId: number, data: {
  name?: string
  title_template?: string
  content_template?: string
  type_id?: number
  description?: string
}) => {
  return request({
    url: `/notifications/templates/${templateId}`,
    method: 'PATCH',
    data
  })
}

/**
 * 删除模板
 * @param templateId 模板ID
 */
export const deleteTemplate = (templateId: number) => {
  return request({
    url: `/notifications/templates/${templateId}`,
    method: 'DELETE'
  })
}
