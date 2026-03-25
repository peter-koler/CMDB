<template>
  <div class="app-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <a-tabs v-if="!isMyAlertsView" v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tab-pane key="current" tab="当前告警" />
        <a-tab-pane key="history" tab="告警历史" />
      </a-tabs>
      <a-alert
        v-else
        type="info"
        show-icon
        message="我的告警"
        :description="`默认展示处理人为当前登录用户（${currentUsername || '-'}）的告警，可通过处理人筛选调整。`"
      />

      <a-form layout="inline" :model="filters">
        <a-form-item label="级别">
          <a-select v-model:value="filters.level" allow-clear style="width: 130px" placeholder="全部级别">
            <a-select-option value="critical">critical</a-select-option>
            <a-select-option value="warning">warning</a-select-option>
            <a-select-option value="info">info</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="告警名称">
          <a-input v-model:value="filters.name" placeholder="按告警名称筛选" style="width: 200px" allow-clear />
        </a-form-item>
        <a-form-item label="告警对象">
          <a-input v-model:value="filters.monitor_name" placeholder="按监控对象筛选" style="width: 200px" allow-clear />
        </a-form-item>
        <a-form-item label="处理人">
          <a-input v-model:value="filters.assignee" placeholder="按处理人筛选" style="width: 180px" allow-clear />
        </a-form-item>
        <a-form-item label="告警状态">
          <a-select
            v-model:value="filters.status"
            allow-clear
            style="width: 130px"
            placeholder="全部状态"
            :disabled="isMyAlertsView && myOpenOnly"
          >
            <a-select-option value="open">open</a-select-option>
            <a-select-option value="closed">closed</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="isMyAlertsView" label="仅看未关闭">
          <a-switch v-model:checked="myOpenOnly" />
        </a-form-item>
        <a-form-item label="时间范围">
          <a-range-picker
            v-model:value="timeRange"
            style="width: 280px"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
          />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="loadActiveData" :loading="loading">查询</a-button>
            <a-button @click="resetFilters">重置</a-button>
            <a-button v-if="activeTab === 'history'" @click="exportHistory">导出CSV</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-space>
        <a-button
          v-if="activeTab === 'current'"
          type="primary"
          :disabled="!canClose || !selectedRowKeys.length"
          @click="batchClose"
        >批量关闭</a-button>
        <a-button
          v-if="activeTab === 'current'"
          :disabled="!canClaim || !selectedRowKeys.length"
          @click="batchClaimSelf"
        >批量认领</a-button>
        <a-button
          v-if="activeTab === 'current'"
          :disabled="!canClaim || !selectedRowKeys.length"
          @click="openBatchAssign"
        >批量分派</a-button>
        <a-button
          danger
          :disabled="!canDelete || !selectedRowKeys.length"
          @click="batchDelete"
        >批量删除</a-button>
      </a-space>

      <a-table
        :loading="loading"
        :columns="alertColumns"
        :data-source="alerts"
        :pagination="pagination"
        :row-selection="rowSelection"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a-button type="link" size="small" @click="openAlertDetail(record)">
              {{ record.name || '-' }}
            </a-button>
          </template>
          <template v-if="column.key === 'monitor_name'">
            <a-button type="link" size="small" @click="openMonitorDetail(record)">
              {{ record.monitor_name || '-' }}
            </a-button>
          </template>
          <template v-if="column.key === 'level'">
            <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'open' ? 'red' : 'default'">{{ record.status || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'duration'">
            {{ formatDuration(record.duration_seconds) }}
          </template>
          <template v-if="column.key === 'triggered_at'">
            {{ formatTime(record.triggered_at) }}
          </template>
          <template v-if="column.key === 'recovered_at'">
            {{ formatTime(record.recovered_at) }}
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button
                v-if="activeTab === 'current' && canClaim"
                type="link"
                size="small"
                :disabled="record.status !== 'open' || rowActionLoadingId === record.id"
                @click="handleClaim(record)"
              >认领</a-button>
              <a-button
                v-if="activeTab === 'current' && canClaim"
                type="link"
                size="small"
                :disabled="record.status !== 'open' || rowActionLoadingId === record.id"
                @click="openAssignModal(record)"
              >分派</a-button>
              <a-button
                v-if="activeTab === 'current' && canClose"
                type="link"
                size="small"
                danger
                :disabled="record.status !== 'open' || rowActionLoadingId === record.id"
                @click="handleClose(record)"
              >关闭</a-button>
              <a-button
                v-if="canDelete"
                type="link"
                size="small"
                danger
                @click="handleDelete(record)"
              >删除</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
      </a-space>

      <a-modal
        v-model:open="assignModalOpen"
        title="分派告警"
        :confirm-loading="assigning"
        @ok="submitAssign"
        @cancel="resetAssignModal"
      >
        <a-form layout="vertical">
          <a-form-item label="部门筛选">
            <a-select
              v-model:value="assignForm.department"
              allow-clear
              show-search
              placeholder="全部部门"
              option-filter-prop="label"
              @change="handleAssignDepartmentChange"
            >
              <a-select-option
                v-for="item in assignDepartments"
                :key="item"
                :value="item"
                :label="item"
              >
                {{ item }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="处理人" required>
            <a-select
              v-model:value="assignForm.assignee"
              show-search
              allow-clear
              placeholder="请选择处理人"
              option-filter-prop="label"
            >
              <a-select-option v-for="item in assignUsers" :key="item.username" :value="item.username" :label="item.username">
                {{ item.username }} <span v-if="getUserDepartmentName(item)">({{ getUserDepartmentName(item) }})</span>
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea v-model:value="assignForm.note" :rows="3" placeholder="可选：填写分派说明" />
          </a-form-item>
        </a-form>
      </a-modal>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import dayjs, { Dayjs } from 'dayjs'
import { io, Socket } from 'socket.io-client'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getUsers, type User } from '@/api/user'
import {
  claimAlert,
  closeAlert,
  deleteAlert,
  getAlertHistory,
  getCurrentAlerts,
  type AlertItem
} from '@/api/monitoring'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const activeTab = ref<'current' | 'history'>('current')
const loading = ref(false)
const alerts = ref<AlertItem[]>([])
const timeRange = ref<[Dayjs, Dayjs] | null>(null)
const selectedRowKeys = ref<number[]>([])
const rowActionLoadingId = ref<number | null>(null)
const assignModalOpen = ref(false)
const assigning = ref(false)
const assigningAlertIds = ref<number[]>([])
const assignUsers = ref<User[]>([])
const allAssignableUsers = ref<User[]>([])
const assignDepartments = ref<string[]>([])
const myOpenOnly = ref(true)
const assignForm = reactive({
  department: undefined as string | undefined,
  assignee: '',
  note: ''
})
let socket: Socket | null = null

const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const filters = reactive({
  level: undefined as string | undefined,
  name: '',
  monitor_name: '',
  assignee: '',
  status: undefined as string | undefined
})
const currentUsername = computed(() => String(userStore.userInfo?.username || '').trim())
const isMyAlertsView = computed(() => route.path.endsWith('/my'))

const canClaim = computed(() =>
  userStore.hasPermission('monitoring:alert:claim') ||
  userStore.hasPermission('monitoring:alert:my') ||
  userStore.hasPermission('monitoring:alert:current') ||
  userStore.hasPermission('monitoring:alert:center')
)
const canClose = computed(() =>
  userStore.hasPermission('monitoring:alert:close') ||
  userStore.hasPermission('monitoring:alert:my') ||
  userStore.hasPermission('monitoring:alert:current') ||
  userStore.hasPermission('monitoring:alert:center')
)
const canDelete = computed(() =>
  userStore.hasPermission('monitoring:alert:center') ||
  userStore.hasPermission('monitoring:alert:close') ||
  userStore.hasPermission('monitoring:alert:history')
)

const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: (number | string)[]) => {
    selectedRowKeys.value = keys.map((k) => Number(k)).filter((k) => Number.isFinite(k) && k > 0)
  }
}))

const formatTime = (timeStr?: string) => {
  if (!timeStr) return '-'
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss')
}

const alertColumns = computed(() => {
  const base: any[] = [
    { title: '级别', dataIndex: 'level', key: 'level', width: 90 },
    { title: '告警名称', dataIndex: 'name', key: 'name', width: 240 },
    { title: '告警对象', dataIndex: 'monitor_name', key: 'monitor_name', width: 220 },
    { title: '告警状态', dataIndex: 'status', key: 'status', width: 110 },
    { title: '处理人', dataIndex: 'assignee', key: 'assignee', width: 130 },
    { title: '指标值', dataIndex: 'metric_value', key: 'metric_value', width: 120 },
    { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 180 },
    { title: '持续时间', dataIndex: 'duration_seconds', key: 'duration', width: 120 }
  ]
  if (activeTab.value === 'history') {
    base.push({ title: '恢复时间', dataIndex: 'recovered_at', key: 'recovered_at', width: 180 })
  }
  base.push({ title: '操作', key: 'actions', fixed: 'right', width: activeTab.value === 'current' ? 180 : 100 })
  return base
})

const levelColor = (level: string) => {
  if (level === 'critical') return 'red'
  if (level === 'warning') return 'orange'
  return 'blue'
}

const formatDuration = (seconds?: number) => {
  if (!seconds || seconds <= 0) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}h ${m}m ${s}s`
}

const getUserDepartmentName = (user: User | Record<string, any> | null | undefined) => {
  if (!user) return ''
  const fromDirect = String((user as any).department || '').trim()
  if (fromDirect) return fromDirect
  const fromName = String((user as any).department_name || '').trim()
  if (fromName) return fromName
  const list = Array.isArray((user as any).departments) ? (user as any).departments : []
  const first = list.find((item: any) => item && item.name)
  return String(first?.name || '').trim()
}

const normalizeList = (payload: any): { items: any[]; total: number } => {
  if (!payload) return { items: [], total: 0 }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const listPayload = () => ({
  page: pagination.current,
  page_size: pagination.pageSize,
  level: filters.level,
  status: filters.status,
  name: filters.name || undefined,
  monitor_name: filters.monitor_name || undefined,
  assignee: (isMyAlertsView.value ? (filters.assignee || currentUsername.value) : filters.assignee) || undefined,
  q: [filters.name, filters.monitor_name, filters.assignee].filter(Boolean).join(' ') || undefined,
  start_at: timeRange.value?.[0]?.toISOString(),
  end_at: timeRange.value?.[1]?.toISOString()
})

const loadCurrentAlerts = async () => {
  const res = await getCurrentAlerts(listPayload())
  const parsed = normalizeList(res?.data)
  alerts.value = parsed.items
  pagination.total = parsed.total
}

const loadHistoryAlerts = async () => {
  const res = await getAlertHistory(listPayload())
  const parsed = normalizeList(res?.data)
  alerts.value = parsed.items
  pagination.total = parsed.total
}

const loadActiveData = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'current') await loadCurrentAlerts()
    if (activeTab.value === 'history') await loadHistoryAlerts()
    selectedRowKeys.value = []
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadActiveData()
}

const handleTabChange = () => {
  if (activeTab.value === 'current') router.replace('/alert-center/current')
  if (activeTab.value === 'history') router.replace('/alert-center/history')
  pagination.current = 1
  selectedRowKeys.value = []
  loadActiveData()
}

const syncTabByRoute = () => {
  const path = route.path
  if (path.endsWith('/history')) {
    activeTab.value = 'history'
    return
  }
  activeTab.value = 'current'
  if (path.endsWith('/my') && !filters.assignee) {
    filters.assignee = currentUsername.value
  }
  if (path.endsWith('/my') && myOpenOnly.value && !filters.status) {
    filters.status = 'open'
  }
}

const resetFilters = () => {
  filters.level = undefined
  filters.name = ''
  filters.monitor_name = ''
  filters.assignee = isMyAlertsView.value ? currentUsername.value : ''
  filters.status = isMyAlertsView.value && myOpenOnly.value ? 'open' : undefined
  timeRange.value = null
  pagination.current = 1
  selectedRowKeys.value = []
  loadActiveData()
}

const handleClaim = async (record: AlertItem) => {
  if (!record?.id || record.status !== 'open') return
  rowActionLoadingId.value = Number(record.id)
  try {
    await claimAlert(record.id)
    message.success('认领成功')
    await loadActiveData()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '认领失败')
  } finally {
    rowActionLoadingId.value = null
  }
}

const handleClose = async (record: AlertItem) => {
  if (!record?.id || record.status !== 'open') return
  Modal.confirm({
    title: '确认关闭',
    content: `确定要关闭告警 "${record.name}" 吗？`,
    onOk: async () => {
      rowActionLoadingId.value = Number(record.id)
      try {
        await closeAlert(record.id)
        message.success('关闭成功')
        await loadActiveData()
      } catch (error: any) {
        message.error(error?.response?.data?.message || '关闭失败')
      } finally {
        rowActionLoadingId.value = null
      }
    }
  })
}

const handleDelete = async (record: AlertItem) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除告警 "${record.name}" 吗？`,
    onOk: async () => {
      await deleteAlert(record.id, { scope: activeTab.value })
      message.success('删除成功')
      loadActiveData()
    }
  })
}

const openMonitorDetail = (record: AlertItem) => {
  const monitorId = Number(record.monitor_id)
  if (!Number.isFinite(monitorId) || monitorId <= 0) {
    message.warning('未找到监控任务ID，无法跳转')
    return
  }
  router.push(`/monitoring/target/${monitorId}`)
}

const openAlertDetail = (record: AlertItem) => {
  if (!record?.id) {
    message.warning('告警ID缺失，无法查看明细')
    return
  }
  router.push(`/alert-center/detail/${record.id}`)
}

const batchClose = async () => {
  if (!selectedRowKeys.value.length) return
  Modal.confirm({
    title: '批量关闭确认',
    content: `确定批量关闭 ${selectedRowKeys.value.length} 条告警吗？`,
    onOk: async () => {
      const tasks = selectedRowKeys.value.map((id) => closeAlert(id))
      const results = await Promise.allSettled(tasks)
      const okCount = results.filter((r) => r.status === 'fulfilled').length
      const failCount = results.length - okCount
      if (okCount > 0) message.success(`批量关闭完成，成功 ${okCount} 条${failCount ? `，失败 ${failCount} 条` : ''}`)
      if (failCount > 0 && okCount === 0) message.error('批量关闭失败')
      loadActiveData()
    }
  })
}

const loadAssignableUsers = async () => {
  try {
    const res = await getUsers({ page: 1, per_page: 500, status: 'active' })
    const payload = (res as any)?.data
    const items = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : []
    allAssignableUsers.value = items as User[]
    assignDepartments.value = Array.from(
      new Set(
        allAssignableUsers.value
          .map((u) => getUserDepartmentName(u))
          .filter(Boolean)
      )
    ).sort((a, b) => a.localeCompare(b))
    applyAssignUserFilter()
  } catch {
    allAssignableUsers.value = []
    assignDepartments.value = []
    assignUsers.value = []
  }
}

const applyAssignUserFilter = () => {
  const department = String(assignForm.department || '').trim()
  if (!department) {
    assignUsers.value = [...allAssignableUsers.value]
    return
  }
  assignUsers.value = allAssignableUsers.value.filter(
    (u) => getUserDepartmentName(u) === department
  )
}

const handleAssignDepartmentChange = () => {
  assignForm.assignee = ''
  applyAssignUserFilter()
}

const openAssignModal = async (record: AlertItem) => {
  if (!record?.id || record.status !== 'open') return
  assigningAlertIds.value = [Number(record.id)]
  assignForm.department = undefined
  assignForm.assignee = ''
  assignForm.note = ''
  await loadAssignableUsers()
  assignModalOpen.value = true
}

const openBatchAssign = async () => {
  if (!selectedRowKeys.value.length) return
  assigningAlertIds.value = [...selectedRowKeys.value]
  assignForm.department = undefined
  assignForm.assignee = ''
  assignForm.note = ''
  await loadAssignableUsers()
  assignModalOpen.value = true
}

const resetAssignModal = () => {
  assignModalOpen.value = false
  assigningAlertIds.value = []
  assignForm.department = undefined
  assignForm.assignee = ''
  assignForm.note = ''
}

const submitAssign = async () => {
  const assignee = String(assignForm.assignee || '').trim()
  if (!assignee) {
    message.warning('请选择处理人')
    return
  }
  if (!assigningAlertIds.value.length) {
    resetAssignModal()
    return
  }
  assigning.value = true
  try {
    const note = String(assignForm.note || '').trim()
    const tasks = assigningAlertIds.value.map((id) =>
      claimAlert(id, { assignee, note: note || undefined })
    )
    const results = await Promise.allSettled(tasks)
    const okCount = results.filter((r) => r.status === 'fulfilled').length
    const failCount = results.length - okCount
    if (okCount > 0) {
      message.success(`分派完成，成功 ${okCount} 条${failCount ? `，失败 ${failCount} 条` : ''}`)
    } else {
      message.error('分派失败')
    }
    resetAssignModal()
    await loadActiveData()
  } finally {
    assigning.value = false
  }
}

const batchClaimSelf = async () => {
  if (!selectedRowKeys.value.length) return
  const assignee = String(userStore.userInfo?.username || '').trim() || undefined
  const tasks = selectedRowKeys.value.map((id) => claimAlert(id, assignee ? { assignee } : undefined))
  const results = await Promise.allSettled(tasks)
  const okCount = results.filter((r) => r.status === 'fulfilled').length
  const failCount = results.length - okCount
  if (okCount > 0) message.success(`批量认领完成，成功 ${okCount} 条${failCount ? `，失败 ${failCount} 条` : ''}`)
  if (okCount === 0) message.error('批量认领失败')
  await loadActiveData()
}

const batchDelete = async () => {
  if (!selectedRowKeys.value.length) return
  Modal.confirm({
    title: '批量删除确认',
    content: `确定批量删除 ${selectedRowKeys.value.length} 条告警吗？删除后不可恢复。`,
    onOk: async () => {
      const tasks = selectedRowKeys.value.map((id) => deleteAlert(id, { scope: activeTab.value }))
      const results = await Promise.allSettled(tasks)
      const okCount = results.filter((r) => r.status === 'fulfilled').length
      const failCount = results.length - okCount
      if (okCount > 0) message.success(`批量删除完成，成功 ${okCount} 条${failCount ? `，失败 ${failCount} 条` : ''}`)
      if (failCount > 0 && okCount === 0) message.error('批量删除失败')
      loadActiveData()
    }
  })
}

const exportHistory = () => {
  message.info('导出功能开发中')
}

onMounted(() => {
  syncTabByRoute()
  loadActiveData()
  socket = io('/alert', { transports: ['websocket'] })
  socket.on('alert', () => {
    loadActiveData()
  })
})

onUnmounted(() => {
  socket?.disconnect()
})

watch(
  () => route.path,
  (newPath, oldPath) => {
    syncTabByRoute()
    if (!oldPath || newPath === oldPath) return
    const isAlertCenterRoute = (p: string) => p.includes('/alert-center/')
    if (!isAlertCenterRoute(newPath) || !isAlertCenterRoute(oldPath)) return
    const leavingMyAlerts = oldPath.endsWith('/my') && !newPath.endsWith('/my')
    if (leavingMyAlerts) {
      // 避免“我的告警”的处理人/状态条件串到“当前告警”
      filters.assignee = ''
      if (myOpenOnly.value && filters.status === 'open') {
        filters.status = undefined
      }
    }
    pagination.current = 1
    selectedRowKeys.value = []
    loadActiveData()
  }
)

watch(
  () => currentUsername.value,
  (username) => {
    if (!isMyAlertsView.value) return
    if (!filters.assignee) {
      filters.assignee = username
    }
  }
)

watch(
  () => myOpenOnly.value,
  (checked) => {
    if (!isMyAlertsView.value) return
    filters.status = checked ? 'open' : undefined
    pagination.current = 1
    loadActiveData()
  }
)
</script>
