<template>
  <div class="notification-center">
    <!-- 头部 -->
    <div class="notification-header">
      <div class="header-title">
        <span>通知中心</span>
        <a-badge
          v-if="unreadCount > 0"
          :count="unreadCount"
          :overflow-count="99"
          class="unread-badge"
        />
      </div>
      <a-button
        v-if="unreadCount > 0"
        type="link"
        size="small"
        @click="handleMarkAllRead"
      >
        全部已读
      </a-button>
    </div>

    <!-- 标签页 -->
    <a-tabs
      v-model:activeKey="activeTab"
      class="notification-tabs"
      @change="handleTabChange"
    >
      <a-tab-pane
        key="all"
        tab="全部"
      >
        <NotificationList
          :notifications="notifications"
          :loading="loading"
          :has-more="hasMore"
          empty-text="暂无通知"
          @click="handleNotificationClick"
          @read="handleMarkRead"
          @load-more="handleLoadMore"
        />
      </a-tab-pane>
      <a-tab-pane
        key="unread"
        tab="未读"
      >
        <NotificationList
          :notifications="unreadNotifications"
          :loading="loading"
          :has-more="hasMoreUnread"
          empty-text="暂无未读通知"
          @click="handleNotificationClick"
          @read="handleMarkRead"
          @load-more="handleLoadMoreUnread"
        />
      </a-tab-pane>
    </a-tabs>

    <!-- 底部 -->
    <div class="notification-footer">
      <a-button
        type="link"
        @click="goToNotificationPage"
      >
        查看全部
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notifications'
import NotificationList from './NotificationList.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'click': [notification: any]
}>()

const router = useRouter()
const store = useNotificationStore()

const activeTab = ref('all')
const page = ref(1)
const pageSize = ref(10)
const unreadPage = ref(1)

const notifications = computed(() => store.notifications)
const unreadNotifications = computed(() => store.unreadNotifications)
const unreadCount = computed(() => store.unreadCount)
const loading = computed(() => store.loading)

const hasMore = computed(() => notifications.value.length >= page.value * pageSize.value)
const hasMoreUnread = computed(() => unreadNotifications.value.length >= unreadPage.value * pageSize.value)

onMounted(() => {
  loadNotifications()
})

const loadNotifications = async () => {
  await store.fetchNotifications({
    page: page.value,
    page_size: pageSize.value
  })
}

const loadUnreadNotifications = async () => {
  await store.fetchNotifications({
    is_read: false,
    page: unreadPage.value,
    page_size: pageSize.value
  })
}

const handleTabChange = (key: string) => {
  if (key === 'unread') {
    unreadPage.value = 1
    loadUnreadNotifications()
  } else {
    page.value = 1
    loadNotifications()
  }
}

const handleMarkRead = async (recipientId: number) => {
  await store.markNotificationAsRead(recipientId)
}

const handleMarkAllRead = async () => {
  await store.markAllNotificationsAsRead()
}

const handleNotificationClick = (notification: any) => {
  emit('click', notification)
  emit('update:visible', false)
}

const handleLoadMore = () => {
  page.value++
  loadNotifications()
}

const handleLoadMoreUnread = () => {
  unreadPage.value++
  loadUnreadNotifications()
}

const goToNotificationPage = () => {
  router.push('/notifications')
  emit('update:visible', false)
}
</script>

<style scoped>
.notification-center {
  width: 360px;
  max-height: 500px;
  display: flex;
  flex-direction: column;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.header-title {
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.unread-badge {
  margin-left: 4px;
}

.notification-tabs {
  flex: 1;
  overflow: hidden;
}

.notification-tabs :deep(.ant-tabs-content) {
  height: calc(100% - 46px);
  overflow-y: auto;
}

.notification-footer {
  padding: 8px 16px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}
</style>
