<template>
  <div class="notification-detail-page">
    <a-card :bordered="false">
      <template #title>
        <div class="page-header">
          <a-button type="link" @click="goBack">
            <ArrowLeftOutlined />
          </a-button>
          <span class="page-title">通知详情</span>
        </div>
      </template>

      <a-spin :spinning="loading">
        <div v-if="notification" class="detail-content">
          <div class="detail-header">
            <h1 class="detail-title">{{ notificationData?.title }}</h1>
            <div class="detail-meta">
              <a-tag :color="notificationData?.type?.color || '#1890ff'">
                <component :is="getIconComponent(notificationData?.type?.icon)" />
                {{ notificationData?.type?.name }}
              </a-tag>
              <span class="meta-item">
                <UserOutlined />
                {{ notificationData?.sender?.username || '系统' }}
              </span>
              <span class="meta-item">
                <ClockCircleOutlined />
                {{ formatTime(notificationData?.created_at) }}
              </span>
              <a-badge
                :status="notification.is_read ? 'default' : 'processing'"
                :text="notification.is_read ? '已读' : '未读'"
              />
            </div>
          </div>

          <a-divider />

          <div class="detail-body">
            <div
              class="content-html"
              v-html="notificationData?.content_html || notificationData?.content"
            />
          </div>

          <div
            v-if="notificationData?.attachments?.length"
            class="detail-attachments"
          >
            <a-divider />
            <h3>
              <PaperClipOutlined />
              附件 ({{ notificationData.attachments.length }})
            </h3>
            <div class="attachment-list">
              <div
                v-for="att in notificationData.attachments"
                :key="att.id"
                class="attachment-item"
                @click="handleDownload(att)"
              >
                <FileOutlined class="file-icon" />
                <div class="file-info">
                  <span class="file-name">{{ att.original_filename }}</span>
                  <span class="file-size">{{ formatFileSize(att.file_size) }}</span>
                </div>
                <DownloadOutlined class="download-icon" />
              </div>
            </div>
          </div>

          <a-divider />

          <div class="detail-actions">
            <a-space>
              <a-button
                v-if="!notification.is_read"
                type="primary"
                @click="handleMarkRead"
              >
                <CheckOutlined />
                标记为已读
              </a-button>
              <a-button
                v-else
                @click="handleMarkUnread"
              >
                标记为未读
              </a-button>
              <a-button @click="goBack">
                返回
              </a-button>
            </a-space>
          </div>
        </div>

        <a-empty v-else-if="!loading" description="通知不存在" />
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useNotificationStore } from '@/stores/notifications'
import { markAsRead, markAsUnread } from '@/api/notifications'
import {
  ArrowLeftOutlined,
  UserOutlined,
  ClockCircleOutlined,
  PaperClipOutlined,
  FileOutlined,
  DownloadOutlined,
  CheckOutlined,
  BellOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  MessageOutlined,
  MailOutlined,
  AlertOutlined,
  StarOutlined,
  FileTextOutlined,
  SettingOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const route = useRoute()
const store = useNotificationStore()

const notification = ref<any>(null)
const loading = ref(true)

const notificationData = computed(() => {
  return notification.value?.notification || notification.value
})

const iconMap: Record<string, any> = {
  bell: BellOutlined,
  info: InfoCircleOutlined,
  success: CheckCircleOutlined,
  warning: WarningOutlined,
  message: MessageOutlined,
  mail: MailOutlined,
  alert: AlertOutlined,
  star: StarOutlined,
  file: FileTextOutlined,
  setting: SettingOutlined
}

const getIconComponent = (iconName?: string) => {
  return iconMap[iconName || 'bell'] || BellOutlined
}

const formatTime = (time: string) => {
  if (!time) return ''
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const loadNotification = async () => {
  const recipientId = route.params.id as string
  if (!recipientId) {
    loading.value = false
    return
  }

  loading.value = true
  try {
    const allNotifications = store.notifications
    const found = allNotifications.find((n: any) => n.id === parseInt(recipientId))
    
    if (found) {
      notification.value = found
    } else {
      await store.fetchNotifications()
      notification.value = store.notifications.find((n: any) => n.id === parseInt(recipientId))
    }
  } catch (error) {
    console.error('加载通知失败:', error)
    message.error('加载通知失败')
  } finally {
    loading.value = false
  }
}

const handleMarkRead = async () => {
  if (!notification.value) return
  
  try {
    const res = await markAsRead(notification.value.id)
    if (res.code === 200) {
      notification.value.is_read = true
      store.decrementUnreadCount()
      message.success('已标记为已读')
    } else {
      message.error(res.message || '操作失败')
    }
  } catch (error) {
    console.error('标记已读失败:', error)
    message.error('操作失败')
  }
}

const handleMarkUnread = async () => {
  if (!notification.value) return
  
  try {
    const res = await markAsUnread(notification.value.id)
    if (res.code === 200) {
      notification.value.is_read = false
      store.incrementUnreadCount()
      message.success('已标记为未读')
    } else {
      message.error(res.message || '操作失败')
    }
  } catch (error) {
    console.error('标记未读失败:', error)
    message.error('操作失败')
  }
}

const handleDownload = (attachment: any) => {
  const token = localStorage.getItem('token')
  const url = `${attachment.download_url}?token=${token}`
  window.open(url, '_blank')
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  loadNotification()
})
</script>

<style scoped>
.notification-detail-page {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.detail-content {
  max-width: 900px;
  margin: 0 auto;
}

.detail-header {
  text-align: center;
  margin-bottom: 16px;
}

.detail-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #262626;
}

.detail-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #8c8c8c;
}

.detail-body {
  padding: 16px 0;
}

.content-html {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}

.content-html :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 8px 0;
}

.content-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
}

.content-html :deep(th),
.content-html :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 8px 12px;
  text-align: left;
}

.content-html :deep(th) {
  background-color: #fafafa;
  font-weight: 600;
}

.content-html :deep(pre) {
  background-color: #f6f8fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.content-html :deep(code) {
  background-color: #f6f8fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.detail-attachments h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attachment-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.attachment-item:hover {
  background-color: #f0f0f0;
  border-color: #1890ff;
}

.file-icon {
  font-size: 24px;
  color: #1890ff;
  margin-right: 12px;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: #262626;
}

.file-size {
  font-size: 12px;
  color: #8c8c8c;
}

.download-icon {
  font-size: 18px;
  color: #1890ff;
}

.detail-actions {
  display: flex;
  justify-content: center;
}
</style>
