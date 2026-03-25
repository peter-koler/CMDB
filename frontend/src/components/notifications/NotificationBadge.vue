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
  color: var(--arco-text-secondary);
  padding: 4px 8px;
  border-radius: 10px;
}

.notification-btn:hover {
  color: var(--arco-primary);
  background: var(--arco-primary-soft);
}
</style>
