<template>
  <a-space direction="vertical" style="width: 100%" :size="12">
    <a-form layout="inline" :model="filters">
      <a-form-item label="级别">
        <a-select v-model:value="filters.level" allow-clear style="width: 140px" placeholder="全部级别">
          <a-select-option value="critical">critical</a-select-option>
          <a-select-option value="warning">warning</a-select-option>
          <a-select-option value="info">info</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="处理人">
        <a-input v-model:value="filters.assignee" allow-clear style="width: 180px" placeholder="按处理人筛选" />
      </a-form-item>
      <a-form-item>
        <a-space>
          <a-button type="primary" :loading="loading" @click="handleSearch">查询</a-button>
          <a-button @click="handleReset">重置</a-button>
        </a-space>
      </a-form-item>
    </a-form>

    <a-table
      :loading="loading"
      :columns="alertColumns"
      :data-source="pagedAlerts"
      :pagination="pagination"
      size="small"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'index'">
          {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
        </template>
        <template v-else-if="column.key === 'level'">
          <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 'open' ? 'red' : 'default'">{{ record.status || '-' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'name'">
          <a-button type="link" size="small" @click="openAlertDetail(record)">
            {{ record.name || '-' }}
          </a-button>
        </template>
        <template v-else-if="column.key === 'triggered_at'">
          {{ formatTime(record.triggered_at) }}
        </template>
        <template v-else-if="column.key === 'duration'">
          {{ formatDuration(record.duration_seconds) }}
        </template>
      </template>
    </a-table>
  </a-space>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { getCurrentAlerts, getMonitoringTargets, type AlertItem } from '@/api/monitoring'

interface Props {
  ciId: number | null
  active: boolean
  visible: boolean
}

const props = defineProps<Props>()
const router = useRouter()

const loading = ref(false)
const alerts = ref<AlertItem[]>([])
const requestSeq = ref(0)

const filters = reactive({
  level: undefined as string | undefined,
  assignee: ''
})

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50', '100']
})

const alertColumns = [
  { title: '序号', key: 'index', width: 70 },
  { title: '级别', dataIndex: 'level', key: 'level', width: 90 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  { title: '告警名称', dataIndex: 'name', key: 'name' },
  { title: '处理人', dataIndex: 'assignee', key: 'assignee', width: 130 },
  { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 180 },
  { title: '持续时间', dataIndex: 'duration', key: 'duration', width: 120 }
]

const normalizeList = (payload: any): { items: any[]; total: number } => {
  if (!payload) return { items: [], total: 0 }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const isTargetBoundToCi = (target: any, ciId: number) => {
  const normalizedCiId = Number(ciId)
  if (!normalizedCiId || Number.isNaN(normalizedCiId)) return false

  const directCiId = Number(target?.ci_id || target?.ciId || 0)
  if (Number.isFinite(directCiId) && directCiId === normalizedCiId) return true

  const labels = target?.labels && typeof target.labels === 'object' ? target.labels : {}
  const labelCiId = Number(labels['ci.id'] || labels.ci_id || labels.ciId || 0)
  if (Number.isFinite(labelCiId) && labelCiId === normalizedCiId) return true

  const targetText = String(target?.target || target?.endpoint || '').trim()
  if (targetText === `ci:${normalizedCiId}`) return true

  return false
}

const loadAllTargets = async (ciId: number) => {
  const pageSize = 200
  let current = 1
  let total = 0
  const all: any[] = []

  do {
    const res = await getMonitoringTargets({
      page: current,
      page_size: pageSize,
      ci_id: ciId
    })
    const parsed = normalizeList(res?.data)
    if (!parsed.items.length) break
    all.push(...parsed.items)
    total = Number(parsed.total || all.length)
    current += 1
  } while (all.length < total && current <= 100)

  return all
}

const formatTime = (timeStr?: string) => {
  if (!timeStr) return '-'
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss')
}

const formatDuration = (seconds?: number) => {
  if (!seconds || seconds <= 0) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}h ${m}m ${s}s`
}

const levelColor = (level: string) => {
  if (level === 'critical') return 'red'
  if (level === 'warning') return 'orange'
  return 'blue'
}

const openAlertDetail = (record: AlertItem) => {
  if (!record?.id) {
    message.warning('告警ID缺失，无法查看明细')
    return
  }
  router.push(`/alert-center/detail/${record.id}`)
}

const pagedAlerts = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  return alerts.value.slice(start, end)
})

const fetchCurrentAlertsByCi = async () => {
  if (!props.ciId || !props.active || !props.visible) return

  const seq = ++requestSeq.value
  loading.value = true
  try {
    const targetItems = await loadAllTargets(props.ciId)
    const boundTargets = targetItems.filter((item: any) => isTargetBoundToCi(item, Number(props.ciId)))
    const monitorIds = Array.from(new Set(
      boundTargets
        .map((item: any) => Number(item?.id || item?.monitor_id || 0))
        .filter((id: number) => Number.isFinite(id) && id > 0)
    ))

    if (!monitorIds.length) {
      if (seq !== requestSeq.value) return
      alerts.value = []
      pagination.total = 0
      return
    }

    const tasks = monitorIds.map((monitorId) => {
      return getCurrentAlerts({
        page: 1,
        page_size: 1000,
        status: 'open',
        monitor_id: monitorId,
        level: filters.level,
        assignee: String(filters.assignee || '').trim() || undefined
      })
    })

    const responses = await Promise.all(tasks)
    if (seq !== requestSeq.value) return

    const mergedMap = new Map<number, AlertItem>()
    responses.forEach((res) => {
      const items = normalizeList(res?.data).items || []
      items.forEach((item: AlertItem) => {
        if (!item?.id) return
        if (!mergedMap.has(item.id)) {
          mergedMap.set(item.id, item)
        }
      })
    })

    const mergedList = Array.from(mergedMap.values()).sort((a, b) => {
      const ta = dayjs(a.triggered_at || 0).valueOf()
      const tb = dayjs(b.triggered_at || 0).valueOf()
      return tb - ta
    })

    alerts.value = mergedList
    pagination.total = mergedList.length
  } catch (error: any) {
    if (seq !== requestSeq.value) return
    message.error(error?.response?.data?.message || '加载当前告警失败')
  } finally {
    if (seq === requestSeq.value) {
      loading.value = false
    }
  }
}

const handleSearch = () => {
  pagination.current = 1
  void fetchCurrentAlertsByCi()
}

const handleReset = () => {
  filters.level = undefined
  filters.assignee = ''
  pagination.current = 1
  void fetchCurrentAlertsByCi()
}

const handleTableChange = (pager: any) => {
  pagination.current = Number(pager?.current || 1)
  pagination.pageSize = Number(pager?.pageSize || 10)
}

watch(
  () => [props.ciId, props.active, props.visible],
  () => {
    if (!props.active || !props.visible || !props.ciId) return
    pagination.current = 1
    void fetchCurrentAlertsByCi()
  },
  { immediate: true }
)
</script>
