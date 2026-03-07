<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-row :gutter="[16, 16]">
        <a-col :xs="24" :sm="8">
          <a-card size="small"><a-statistic title="总采集器" :value="collectors.length" /></a-card>
        </a-col>
        <a-col :xs="24" :sm="8">
          <a-card size="small"><a-statistic title="在线" :value="onlineCount" :value-style="{ color: '#52c41a' }" /></a-card>
        </a-col>
        <a-col :xs="24" :sm="8">
          <a-card size="small"><a-statistic title="离线" :value="offlineCount" :value-style="{ color: '#f5222d' }" /></a-card>
        </a-col>
      </a-row>

      <a-form layout="inline">
        <a-form-item label="关键字">
          <a-input v-model:value="keyword" placeholder="采集器名称/地址" style="width: 240px" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="loading" @click="loadCollectors">查询</a-button>
            <a-button @click="reset">重置</a-button>
            <a-button @click="loadCollectors">刷新</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="collectors"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ record.status || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="viewCollector(record)">详情</a-button>
              <a-popconfirm title="确认删除该采集器？" @confirm="removeCollector(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <a-drawer v-model:open="drawerOpen" title="采集器详情" width="480">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="Collector ID">{{ currentCollector?.id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="名称">{{ currentCollector?.name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="地址">{{ currentCollector?.host || '-' }}</a-descriptions-item>
        <a-descriptions-item label="状态">{{ currentCollector?.status || '-' }}</a-descriptions-item>
        <a-descriptions-item label="版本">{{ currentCollector?.version || '-' }}</a-descriptions-item>
        <a-descriptions-item label="心跳时间">{{ currentCollector?.heartbeat_at || '-' }}</a-descriptions-item>
        <a-descriptions-item label="任务数">{{ currentCollector?.task_count ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="运行时长">{{ formatRuntime((currentCollector as any)?.uptime_seconds) }}</a-descriptions-item>
        <a-descriptions-item label="系统负载">{{ (currentCollector as any)?.system_load ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="内存使用">{{ formatMemory((currentCollector as any)?.memory_usage) }}</a-descriptions-item>
      </a-descriptions>
      <a-divider>任务列表</a-divider>
      <a-table
        :columns="taskColumns"
        :data-source="collectorTasks"
        size="small"
        :pagination="false"
        row-key="id"
      />
    </a-drawer>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { deleteCollector, getCollectors, type CollectorItem } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const keyword = ref('')
const collectors = ref<CollectorItem[]>([])
const drawerOpen = ref(false)
const currentCollector = ref<CollectorItem | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const canDelete = computed(() => userStore.hasPermission('monitoring:collector:delete') || userStore.hasPermission('monitoring:collector'))
const onlineCount = computed(() => collectors.value.filter((item) => statusColor(item.status) === 'green').length)
const offlineCount = computed(() => collectors.value.filter((item) => statusColor(item.status) === 'red').length)

const columns = [
  { title: 'Collector ID', dataIndex: 'id', key: 'id', width: 180 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: 'IP/地址', dataIndex: 'host', key: 'host' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '版本', dataIndex: 'version', key: 'version', width: 120 },
  { title: '心跳时间', dataIndex: 'heartbeat_at', key: 'heartbeat_at', width: 180 },
  { title: '任务数', dataIndex: 'task_count', key: 'task_count', width: 100 },
  { title: '操作', key: 'actions', width: 90 }
]
const taskColumns = [
  { title: '任务ID', dataIndex: 'id', key: 'id', width: 120 },
  { title: '监控名称', dataIndex: 'name', key: 'name' },
  { title: '采集间隔(s)', dataIndex: 'interval', key: 'interval', width: 120 }
]
const collectorTasks = computed(() => {
  const tasks = (currentCollector.value as any)?.tasks
  return Array.isArray(tasks) ? tasks : []
})

const normalizeList = (payload: any): { items: CollectorItem[]; total: number } => {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const statusColor = (status?: string) => {
  const val = (status || '').toLowerCase()
  if (val === 'online' || val === 'up' || val === 'healthy') return 'green'
  if (val === 'offline' || val === 'down' || val === 'unhealthy') return 'red'
  return 'default'
}

const formatRuntime = (seconds?: number) => {
  if (!seconds || seconds < 0) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

const formatMemory = (value?: string | number) => {
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return `${value}%`
  return String(value)
}

const loadCollectors = async () => {
  loading.value = true
  try {
    const res = await getCollectors({ q: keyword.value || undefined, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalizeList(res?.data)
    collectors.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载采集器失败')
  } finally {
    loading.value = false
  }
}

const removeCollector = async (record: CollectorItem) => {
  try {
    await deleteCollector(String(record.id))
    message.success('删除成功')
    if (collectors.value.length === 1 && pagination.current > 1) {
      pagination.current -= 1
    }
    loadCollectors()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const viewCollector = (record: CollectorItem) => {
  currentCollector.value = record
  drawerOpen.value = true
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadCollectors()
}

const reset = () => {
  keyword.value = ''
  pagination.current = 1
  loadCollectors()
}

onMounted(() => {
  loadCollectors()
})
</script>
