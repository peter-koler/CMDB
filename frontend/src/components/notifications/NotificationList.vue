<template>
  <div class="notification-list">
    <div
      v-if="notifications.length === 0"
      class="empty-state"
    >
      <a-empty
        :description="emptyText"
        :image="Empty.PRESENTED_IMAGE_SIMPLE"
      />
    </div>
    <div
      v-else
      class="list-container"
    >
      <NotificationItem
        v-for="notification in notifications"
        :key="notification.id"
        :notification="notification"
        @click="$emit('click', $event)"
        @read="$emit('read', $event)"
      />
      <div
        v-if="hasMore"
        class="load-more"
      >
        <a-button
          type="link"
          :loading="loading"
          @click="$emit('loadMore')"
        >
          加载更多
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Empty } from 'ant-design-vue'
import NotificationItem from './NotificationItem.vue'

defineProps<{
  notifications: any[]
  loading?: boolean
  hasMore?: boolean
  emptyText?: string
}>()

defineEmits<{
  click: [notification: any]
  read: [recipientId: number]
  loadMore: []
}>()
</script>

<style scoped>
.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.empty-state {
  padding: 40px 0;
}

.list-container {
  min-height: 100px;
}

.load-more {
  text-align: center;
  padding: 12px;
}
</style>
