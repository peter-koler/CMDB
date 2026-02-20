<template>
  <div
    :class="['notification-item', { 'unread': !notification.is_read }]"
    @click="handleClick"
  >
    <div class="notification-icon">
      <component
        :is="getIconComponent(notificationData?.type?.icon)"
        :style="{ color: notificationData?.type?.color || '#1890ff' }"
      />
    </div>
    <div class="notification-content">
      <div class="notification-title">{{ notificationData?.title }}</div>
      <div
        class="notification-body"
        v-html="notificationData?.content_html || notificationData?.content"
      />
      <div class="notification-meta">
        <span class="notification-time">{{ formatTime(notificationData?.created_at) }}</span>
        <span
          v-if="notificationData?.sender"
          class="notification-sender"
        >
          {{ notificationData.sender.username }}
        </span>
      </div>
    </div>
    <div
      v-if="!notification.is_read"
      class="unread-indicator"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
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
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const props = defineProps<{
  notification: any
}>()

const emit = defineEmits<{
  click: [notification: any]
  read: [recipientId: number]
}>()

const notificationData = computed(() => {
  return props.notification?.notification || props.notification
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
  return dayjs(time).fromNow()
}

const handleClick = () => {
  emit('click', props.notification)
  // 如果是未读状态，自动标记为已读
  if (!props.notification.is_read && props.notification.id) {
    emit('read', props.notification.id)
  }
}
</script>

<style scoped>
.notification-item {
  display: flex;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f0f0f0;
  position: relative;
}

.notification-item:hover {
  background-color: #f5f5f5;
}

.notification-item.unread {
  background-color: #e6f7ff;
}

.notification-item.unread:hover {
  background-color: #bae7ff;
}

.notification-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
  font-size: 18px;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 500;
  font-size: 14px;
  color: #262626;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notification-item.unread .notification-title {
  font-weight: 600;
}

.notification-body {
  font-size: 13px;
  color: #595959;
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notification-body :deep(p) {
  margin: 0;
}

.notification-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #8c8c8c;
}

.notification-time {
  color: #bfbfbf;
}

.notification-sender {
  color: #8c8c8c;
}

.unread-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #1890ff;
  position: absolute;
  top: 12px;
  right: 12px;
}
</style>
