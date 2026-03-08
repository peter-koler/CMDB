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
            <a-tag :color="statusColor(record.status)">{{ formatStatus(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="viewCollector(record)">详情</a-button>
              <a-button type="link" size="small" @click="viewMonitors(record)">查看任务</a-button>
              <a-popconfirm
                title="确认下线该采集器？"
                description="下线后将断开连接并重新平衡任务"
                @confirm="handleOffline(record)"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                  :disabled="!canOffline || isOffline(record.status)"
                >下线</a-button>
              </a-popconfirm>
              <a-popconfirm title="确认删除该采集器？" @confirm="removeCollector(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <!-- 采集器详情抽屉 -->
    <a-drawer v-model:open="drawerOpen" title="采集器详情" width="480">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="Collector ID">{{ currentCollector?.id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="名称">{{ currentCollector?.name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="地址">{{ currentCollector?.ip || '-' }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="statusColor(currentCollector?.status)">{{ formatStatus(currentCollector?.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="版本">{{ currentCollector?.version || '-' }}</a-descriptions-item>
        <a-descriptions-item label="心跳时间">{{ currentCollector?.updated_at || '-' }}</a-descriptions-item>
        <a-descriptions-item label="任务数">{{ currentCollector?.task_count ?? 0 }}</a-descriptions-item>
        <a-descriptions-item label="运行时长">{{ formatRuntime((currentCollector as any)?.uptime_seconds) ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="系统负载">{{ (currentCollector as any)?.system_load ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="内存使用">{{ formatMemory((currentCollector as any)?.memory_usage) ?? '-' }}</a-descriptions-item>
      </a-descriptions>
    </a-drawer>

    <!-- 查看任务抽屉 -->
    <a-drawer v-model:open="monitorsDrawerOpen" title="采集器任务列表" width="640">
      <a-descriptions :column="1" bordered size="small" class="mb-4">
        <a-descriptions-item label="Collector">{{ currentCollector?.name || currentCollector?.id }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="statusColor(currentCollector?.status)">{{ formatStatus(currentCollector?.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="绑定任务数">{{ collectorMonitors.length }}</a-descriptions-item>
      </a-descriptions>

      <a-table
        :loading="monitorsLoading"
        :columns="monitorColumns"
        :data-source="collectorMonitors"
        size="small"
        :pagination="{ pageSize: 10 }"
        row-key="monitor_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 1 ? 'green' : record.status === 2 ? 'red' : 'default'">
              {{ record.status === 1 ? '运行中' : record.status === 2 ? '异常' : '暂停' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'pinned'">
            <a-tag :color="record.pinned ? 'blue' : 'default'">
              {{ record.pinned ? '固定分配' : '自动分配' }}
            </a-tag>
          </template>
        </template>
        <template #empty>
          <a-empty description="暂无绑定的监控任务" />
        </template>
      </a-table>
    </a-drawer>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { deleteCollector, getCollectors, offlineCollector, getCollectorMonitors, type CollectorItem } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const keyword = ref('')
const collectors = ref<CollectorItem[]>([])
const drawerOpen = ref(false)
const currentCollector = ref<CollectorItem | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

// 查看任务相关
const monitorsDrawerOpen = ref(false)
const monitorsLoading = ref(false)
const collectorMonitors = ref<any[]>([])

const canDelete = computed(() => userStore.hasPermission('monitoring:collector:delete') || userStore.hasPermission('monitoring:collector'))
const canOffline = computed(() => userStore.hasPermission('monitoring:collector:offline') || userStore.hasPermission('monitoring:collector:manage'))
const onlineCount = computed(() => collectors.value.filter((item) => statusColor(item.status) === 'green').length)
const offlineCount = computed(() => collectors.value.filter((item) => statusColor(item.status) === 'red').length)

// 判断是否为离线状态
const isOffline = (status?: string | number) => {
  // 支持数字状态：0=在线, 1=离线
  if (typeof status === 'number') {
    return status === 1
  }
  const val = (status || '').toLowerCase()
  return val === 'offline' || val === 'down' || val === 'unhealthy' || val === '1'
}

const columns = [
  { title: 'Collector ID', dataIndex: 'id', key: 'id', width: 180 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: 'IP/地址', dataIndex: 'ip', key: 'ip' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '版本', dataIndex: 'version', key: 'version', width: 120 },
  { title: '心跳时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '任务数', dataIndex: 'task_count', key: 'task_count', width: 100 },
  { title: '操作', key: 'actions', width: 200 }
]

// 监控任务列表列定义
const monitorColumns = [
  { title: '监控ID', dataIndex: 'monitor_id', key: 'monitor_id', width: 100 },
  { title: '监控名称', dataIndex: 'monitor_name', key: 'monitor_name' },
  { title: '应用', dataIndex: 'app', key: 'app', width: 120 },
  { title: '实例', dataIndex: 'instance', key: 'instance' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '分配方式', dataIndex: 'pinned', key: 'pinned', width: 100 }
]

const normalizeList = (payload: any): { items: CollectorItem[]; total: number } => {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const statusColor = (status?: string | number) => {
  // 支持数字状态：0=在线, 1=离线
  if (typeof status === 'number') {
    return status === 0 ? 'green' : 'red'
  }
  const val = (status || '').toLowerCase()
  if (val === 'online' || val === 'up' || val === 'healthy' || val === '0') return 'green'
  if (val === 'offline' || val === 'down' || val === 'unhealthy' || val === '1') return 'red'
  return 'default'
}

const formatStatus = (status?: string | number) => {
  // 支持数字状态：0=在线, 1=离线
  if (typeof status === 'number') {
    return status === 0 ? '在线' : '离线'
  }
  if (status === '0') return '在线'
  if (status === '1') return '离线'
  return status || '-'
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

// 查看采集器绑定的监控任务
const viewMonitors = async (record: CollectorItem) => {
  currentCollector.value = record
  monitorsDrawerOpen.value = true
  monitorsLoading.value = true
  try {
    const res = await getCollectorMonitors(String(record.id))
    const parsed = normalizeList(res?.data)
    collectorMonitors.value = parsed.items
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载任务列表失败')
    collectorMonitors.value = []
  } finally {
    monitorsLoading.value = false
  }
}

// 下线 Collector
const handleOffline = async (record: CollectorItem) => {
  try {
    await offlineCollector(String(record.id))
    message.success('采集器已下线，任务已重新平衡')
    loadCollectors()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '下线失败')
  }
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
