<template>
  <div class="notification-page">
    <a-card class="page-card" :bordered="false">
      <template #title>
        <div class="page-header">
          <span class="page-title">{{ t('notifications.title') }}</span>
          <a-space>
            <a-button
              type="primary"
              v-if="userInfo?.role === 'admin'"
              @click="goToSend"
            >
              <template #icon><SendOutlined /></template>
              {{ t('notifications.send') }}
            </a-button>
            <a-button
              :disabled="selectedRowKeys.length === 0"
              @click="handleBatchRead"
            >
              <template #icon><CheckOutlined /></template>
              {{ t('notifications.markRead') }}
            </a-button>
          </a-space>
        </div>
      </template>

      <!-- 搜索筛选 -->
      <div class="search-bar">
        <a-form layout="inline">
          <a-form-item :label="t('notifications.search')">
            <a-input-search
              v-model:value="searchQuery"
              :placeholder="t('notifications.searchPlaceholder')"
              @search="handleSearch"
              allowClear
            />
          </a-form-item>
          <a-form-item :label="t('notifications.type')">
            <a-select
              v-model:value="filterType"
              :placeholder="t('common.all')"
              style="width: 150px"
              allowClear
              @change="handleFilterChange"
            >
              <a-select-option
                v-for="type in types"
                :key="type.id"
                :value="type.id"
              >
                {{ type.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item :label="t('notifications.status')">
            <a-select
              v-model:value="filterStatus"
              :placeholder="t('common.all')"
              style="width: 120px"
              allowClear
              @change="handleFilterChange"
            >
              <a-select-option value="unread">
                {{ t('notifications.unread') }}
              </a-select-option>
              <a-select-option value="read">
                {{ t('notifications.read') }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-form>
      </div>

      <!-- 通知列表 -->
      <a-table
        :columns="columns"
        :data-source="notifications"
        :loading="loading"
        :pagination="pagination"
        :row-selection="rowSelection"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 类型 -->
          <template v-if="column.key === 'type'">
            <a-tag :color="record.type?.color || '#1890ff'">
              <component :is="getIconComponent(record.type?.icon)" />
              {{ record.type?.name }}
            </a-tag>
          </template>

          <!-- 标题 -->
          <template v-if="column.key === 'title'">
            <span :class="{ 'unread-text': !record.is_read }">
              {{ record.title }}
            </span>
          </template>

          <!-- 内容 -->
          <template v-if="column.key === 'content'">
            <div class="content-preview" v-html="record.content_html || record.content" />
          </template>

          <!-- 发送者 -->
          <template v-if="column.key === 'sender'">
            {{ record.sender?.username || '-' }}
          </template>

          <!-- 时间 -->
          <template v-if="column.key === 'time'">
            {{ formatTime(record.created_at) }}
          </template>

          <!-- 状态 -->
          <template v-if="column.key === 'status'">
            <a-badge
              :status="record.is_read ? 'default' : 'processing'"
              :text="record.is_read ? t('notifications.read') : t('notifications.unread')"
            />
          </template>

          <!-- 操作 -->
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                v-if="!record.is_read"
                type="link"
                size="small"
                @click="handleMarkRead(record.id)"
              >
                {{ t('notifications.markRead') }}
              </a-button>
              <a-button
                v-else
                type="link"
                size="small"
                @click="handleMarkUnread(record.id)"
              >
                {{ t('notifications.markUnread') }}
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 通知详情弹窗 -->
    <a-modal
      v-model:open="detailVisible"
      :title="selectedNotification?.title"
      :footer="null"
      width="600px"
    >
      <div class="notification-detail">
        <div class="detail-meta">
          <a-tag :color="selectedNotification?.type?.color">
            {{ selectedNotification?.type?.name }}
          </a-tag>
          <span>{{ selectedNotification?.sender?.username }}</span>
          <span>{{ formatTime(selectedNotification?.created_at) }}</span>
        </div>
        <div
          class="detail-content"
          v-html="selectedNotification?.content_html || selectedNotification?.content"
        />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notifications'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  SendOutlined,
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

const { t } = useI18n()
const router = useRouter()
const store = useNotificationStore()
const userStore = useUserStore()

const userInfo = computed(() => userStore.userInfo)
const notifications = computed(() => store.notifications)
const types = computed(() => store.types)
const loading = computed(() => store.loading)

const searchQuery = ref('')
const filterType = ref<number | undefined>(undefined)
const filterStatus = ref<string | undefined>(undefined)
const selectedRowKeys = ref<number[]>([])
const detailVisible = ref(false)
const selectedNotification = ref<any>(null)

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true
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
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const columns = [
  {
    title: t('notifications.type'),
    key: 'type',
    width: 120
  },
  {
    title: t('notifications.title'),
    key: 'title',
    ellipsis: true
  },
  {
    title: t('notifications.content'),
    key: 'content',
    ellipsis: true,
    width: 200
  },
  {
    title: t('notifications.sender'),
    key: 'sender',
    width: 100
  },
  {
    title: t('notifications.time'),
    key: 'time',
    width: 160
  },
  {
    title: t('notifications.status'),
    key: 'status',
    width: 100
  },
  {
    title: t('common.action'),
    key: 'action',
    width: 120
  }
]

const rowSelection = {
  selectedRowKeys: selectedRowKeys,
  onChange: (keys: number[]) => {
    selectedRowKeys.value = keys
  }
}

onMounted(() => {
  loadData()
})

const loadData = async () => {
  const params: any = {
    page: pagination.value.current,
    page_size: pagination.value.pageSize
  }

  if (filterType.value) {
    params.type_id = filterType.value
  }

  if (filterStatus.value) {
    params.is_read = filterStatus.value === 'read'
  }

  const res = await store.fetchNotifications(params)
  if (res) {
    pagination.value.total = res.pagination.total
  }
}

const handleSearch = () => {
  if (searchQuery.value) {
    store.search({
      q: searchQuery.value,
      page: 1,
      page_size: pagination.value.pageSize
    })
  } else {
    loadData()
  }
}

const handleFilterChange = () => {
  pagination.value.current = 1
  loadData()
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  loadData()
}

const handleMarkRead = async (id: number) => {
  const success = await store.markNotificationAsRead(id)
  if (success) {
    message.success(t('notifications.markReadSuccess'))
  }
}

const handleMarkUnread = async (id: number) => {
  const success = await store.markNotificationAsUnread(id)
  if (success) {
    message.success(t('notifications.markUnreadSuccess'))
  }
}

const handleBatchRead = async () => {
  // 批量标记已读
  for (const id of selectedRowKeys.value) {
    await store.markNotificationAsRead(id)
  }
  message.success(t('notifications.batchReadSuccess'))
  selectedRowKeys.value = []
}

const goToSend = () => {
  router.push('/notifications/send')
}
</script>

<style scoped>
.notification-page {
  padding: 16px;
}

.page-card {
  min-height: calc(100vh - 100px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.search-bar {
  margin-bottom: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
}

.unread-text {
  font-weight: 600;
  color: #262626;
}

.content-preview {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-preview :deep(p) {
  margin: 0;
}

.notification-detail {
  padding: 16px 0;
}

.detail-meta {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  color: #8c8c8c;
  font-size: 13px;
}

.detail-content {
  line-height: 1.8;
  color: #262626;
}

.detail-content :deep(p) {
  margin-bottom: 12px;
}

.detail-content :deep(img) {
  max-width: 100%;
  border-radius: 4px;
}
</style>
