import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAsUnread,
  markAllAsRead,
  searchNotifications,
  getNotificationTypes
} from '@/api/notifications'
import { message } from 'ant-design-vue'
import { io, Socket } from 'socket.io-client'

// Socket.IO连接
let socket: Socket | null = null

export const useNotificationStore = defineStore('notifications', () => {
  // ==================== State ====================
  const notifications = ref<any[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const types = ref<any[]>([])
  const connected = ref(false)

  // ==================== Getters ====================
  const unreadNotifications = computed(() => {
    return notifications.value.filter(n => !n.is_read)
  })

  const readNotifications = computed(() => {
    return notifications.value.filter(n => n.is_read)
  })

  // ==================== Actions ====================

  /**
   * 获取通知列表
   */
  const fetchNotifications = async (params?: {
    is_read?: boolean
    type_id?: number
    page?: number
    page_size?: number
  }) => {
    loading.value = true
    try {
      const res = await getNotifications(params)
      if (res.code === 200) {
        notifications.value = res.data.items || []
        return res.data
      }
      return null
    } catch (error) {
      console.error('获取通知列表失败:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取未读数量
   */
  const fetchUnreadCount = async () => {
    try {
      const res = await getUnreadCount()
      if (res.code === 200) {
        unreadCount.value = res.data.count || 0
      }
    } catch (error) {
      console.error('获取未读数量失败:', error)
    }
  }

  /**
   * 标记为已读
   */
  const markNotificationAsRead = async (recipientId: number) => {
    try {
      const res = await markAsRead(recipientId)
      if (res.code === 200) {
        // 更新本地状态
        const index = notifications.value.findIndex(n => n.id === recipientId)
        if (index !== -1) {
          notifications.value[index].is_read = true
          notifications.value[index].read_at = new Date().toISOString()
        }
        unreadCount.value = Math.max(0, unreadCount.value - 1)
        return true
      }
      return false
    } catch (error) {
      console.error('标记已读失败:', error)
      return false
    }
  }

  /**
   * 标记为未读
   */
  const markNotificationAsUnread = async (recipientId: number) => {
    try {
      const res = await markAsUnread(recipientId)
      if (res.code === 200) {
        // 更新本地状态
        const index = notifications.value.findIndex(n => n.id === recipientId)
        if (index !== -1) {
          notifications.value[index].is_read = false
          notifications.value[index].read_at = null
        }
        unreadCount.value++
        return true
      }
      return false
    } catch (error) {
      console.error('标记未读失败:', error)
      return false
    }
  }

  /**
   * 标记全部已读
   */
  const markAllNotificationsAsRead = async () => {
    try {
      const res = await markAllAsRead()
      if (res.code === 200) {
        // 更新本地状态
        notifications.value.forEach(n => {
          n.is_read = true
          n.read_at = new Date().toISOString()
        })
        unreadCount.value = 0
        message.success(`已标记 ${res.data.marked_count} 条通知为已读`)
        return true
      }
      return false
    } catch (error) {
      console.error('标记全部已读失败:', error)
      return false
    }
  }

  /**
   * 搜索通知
   */
  const search = async (params: {
    q?: string
    date_from?: string
    date_to?: string
    type_id?: number
    is_read?: boolean
    page?: number
    page_size?: number
  }) => {
    loading.value = true
    try {
      const res = await searchNotifications(params)
      if (res.code === 200) {
        notifications.value = res.data.items || []
        return res.data
      }
      return null
    } catch (error) {
      console.error('搜索通知失败:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取通知类型
   */
  const fetchTypes = async () => {
    try {
      const res = await getNotificationTypes()
      if (res.code === 200) {
        types.value = res.data.items || []
      }
    } catch (error) {
      console.error('获取通知类型失败:', error)
    }
  }

  /**
   * 处理新通知（WebSocket）
   */
  const handleNewNotification = (notification: any) => {
    // 添加到列表开头
    notifications.value.unshift(notification)
    // 增加未读数
    unreadCount.value++
    // 显示消息提示
    message.info(`新通知: ${notification.title}`, 3)
  }

  /**
   * 连接Socket.IO
   */
  const connectWebSocket = (token: string) => {
    if (socket?.connected) {
      return
    }

    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'http://localhost:5000'

    try {
      socket = io(wsUrl, {
        path: '/socket.io',
        transports: ['websocket', 'polling'],
        query: { token }
      })

      socket.on('connect', () => {
        console.log('Socket.IO连接成功')
        connected.value = true
      })

      socket.on('authenticated', (data) => {
        console.log('认证成功:', data)
      })

      socket.on('notification:new', (data) => {
        handleNewNotification(data)
      })

      socket.on('disconnect', () => {
        console.log('Socket.IO连接关闭')
        connected.value = false
      })

      socket.on('connect_error', (error) => {
        console.error('Socket.IO连接错误:', error)
      })
    } catch (error) {
      console.error('创建Socket.IO连接失败:', error)
    }
  }

  /**
   * 断开Socket.IO
   */
  const disconnectWebSocket = () => {
    if (socket) {
      socket.disconnect()
      socket = null
    }
    connected.value = false
  }

  /**
   * 初始化（获取基础数据）
   */
  const initialize = async () => {
    await Promise.all([
      fetchUnreadCount(),
      fetchTypes()
    ])
  }

  return {
    // State
    notifications,
    unreadCount,
    loading,
    types,
    connected,
    // Getters
    unreadNotifications,
    readNotifications,
    // Actions
    fetchNotifications,
    fetchUnreadCount,
    markNotificationAsRead,
    markNotificationAsUnread,
    markAllNotificationsAsRead,
    search,
    fetchTypes,
    handleNewNotification,
    connectWebSocket,
    disconnectWebSocket,
    initialize
  }
})
