<template>
  <a-badge
    :count="unreadCount"
    :overflow-count="99"
    class="notification-badge"
  >
    <a-button
      type="text"
      class="notification-btn"
      @click="$emit('click')"
    >
      <BellOutlined />
    </a-button>
  </a-badge>
</template>

<script setup lang="ts">
import { BellOutlined } from '@ant-design/icons-vue'

defineProps<{
  unreadCount: number
}>()

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.notification-badge {
  cursor: pointer;
}

.notification-btn {
  font-size: 18px;
  color: #666;
  padding: 4px 8px;
}

.notification-btn:hover {
  color: #1890ff;
}
</style>
