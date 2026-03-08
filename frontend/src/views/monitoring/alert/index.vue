<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tab-pane key="current" tab="当前告警" />
        <a-tab-pane key="history" tab="告警历史" />
        <a-tab-pane key="rules" tab="告警配置" />
      </a-tabs>

      <a-form layout="inline" :model="filters">
        <a-form-item label="级别">
          <a-select v-model:value="filters.level" allow-clear style="width: 140px" placeholder="全部级别">
            <a-select-option value="critical">critical</a-select-option>
            <a-select-option value="warning">warning</a-select-option>
            <a-select-option value="info">info</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="关键字">
          <a-input v-model:value="filters.keyword" placeholder="告警名称/对象" style="width: 220px" />
        </a-form-item>
        <a-form-item v-if="activeTab === 'history'" label="时间范围">
          <a-range-picker v-model:value="historyRange" style="width: 280px" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" @click="loadActiveData" :loading="loading">查询</a-button>
            <a-button @click="resetFilters">重置</a-button>
            <a-button v-if="activeTab === 'history'" @click="exportHistory">导出CSV</a-button>
            <a-button v-if="activeTab === 'rules' && canEditRule" type="primary" @click="openRuleModal()">新增配置</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        v-if="activeTab !== 'rules'"
        :loading="loading"
        :columns="alertColumns"
        :data-source="alerts"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'level'">
            <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'open' ? 'red' : 'default'">{{ record.status || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'duration'">
            {{ formatDuration(record.duration_seconds) }}
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button
                v-if="activeTab === 'current' && canClaim"
                type="link"
                size="small"
                @click="handleClaim(record)"
              >认领</a-button>
              <a-button
                v-if="activeTab === 'current' && canClose"
                type="link"
                size="small"
                danger
                @click="handleClose(record)"
              >关闭</a-button>
            </a-space>
          </template>
        </template>
      </a-table>

      <a-table
        v-else
        :loading="loading"
        :columns="ruleColumns"
        :data-source="rules"
        :pagination="false"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'enabled'">
            <a-switch :checked="!!record.enabled" :disabled="!canEditRule" @change="(checked: boolean) => toggleRule(record, checked)" />
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEditRule" @click="openRuleModal(record)">编辑</a-button>
              <a-popconfirm title="确认删除该规则？" @confirm="handleDeleteRule(record)">
                <a-button type="link" size="small" danger :disabled="!canEditRule">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <a-modal v-model:open="ruleModalOpen" :title="editingRule?.id ? '编辑规则' : '新增规则'" @ok="saveRule" :confirm-loading="ruleSaving">
      <a-form layout="vertical" :model="ruleForm">
        <a-form-item label="规则名称" required><a-input v-model:value="ruleForm.name" /></a-form-item>
        <a-form-item label="指标" required><a-input v-model:value="ruleForm.metric" /></a-form-item>
        <a-form-item label="阈值" required><a-input-number v-model:value="ruleForm.threshold" style="width: 100%" /></a-form-item>
        <a-form-item label="级别" required>
          <a-select v-model:value="ruleForm.level">
            <a-select-option value="critical">critical</a-select-option>
            <a-select-option value="warning">warning</a-select-option>
            <a-select-option value="info">info</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import dayjs, { Dayjs } from 'dayjs'
import { io, Socket } from 'socket.io-client'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  claimAlert,
  closeAlert,
  createAlertRule,
  deleteAlertRule,
  disableAlertRule,
  enableAlertRule,
  getAlertHistory,
  getAlertRules,
  getCurrentAlerts,
  updateAlertRule,
  type AlertItem,
  type AlertRule
} from '@/api/monitoring'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const activeTab = ref<'current' | 'history' | 'rules'>('current')
const loading = ref(false)
const alerts = ref<AlertItem[]>([])
const rules = ref<AlertRule[]>([])
const historyRange = ref<[Dayjs, Dayjs] | null>(null)
let socket: Socket | null = null

const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const filters = reactive({ level: undefined as string | undefined, keyword: '' })

const canClaim = computed(() => userStore.hasPermission('monitoring:alert:claim') || userStore.hasPermission('monitoring:alert:center'))
const canClose = computed(() => userStore.hasPermission('monitoring:alert:close') || userStore.hasPermission('monitoring:alert:center'))
const canEditRule = computed(() => userStore.hasPermission('monitoring:alert:rule') || userStore.hasPermission('monitoring:alert:setting'))

const alertColumns = computed(() => {
  const base = [
    { title: '级别', dataIndex: 'level', key: 'level', width: 90 },
    { title: '告警名称', dataIndex: 'name', key: 'name' },
    { title: '监控对象', dataIndex: 'monitor_name', key: 'monitor_name' },
    { title: '指标值', dataIndex: 'metric_value', key: 'metric_value', width: 110 },
    { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 180 },
    { title: '持续时间', dataIndex: 'duration_seconds', key: 'duration', width: 120 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 }
  ]
  if (activeTab.value === 'history') {
    base.push({ title: '恢复时间', dataIndex: 'recovered_at', key: 'recovered_at', width: 180 })
    base.push({ title: '处理人', dataIndex: 'assignee', key: 'assignee', width: 120 })
  }
  if (activeTab.value === 'current') {
    base.push({ title: '操作', key: 'actions', fixed: 'right', width: 140 })
  }
  return base
})

const ruleColumns = [
  { title: '规则名称', dataIndex: 'name', key: 'name' },
  { title: '指标', dataIndex: 'metric', key: 'metric' },
  { title: '阈值', dataIndex: 'threshold', key: 'threshold', width: 120 },
  { title: '级别', dataIndex: 'level', key: 'level', width: 100 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', width: 120 }
]

const ruleModalOpen = ref(false)
const ruleSaving = ref(false)
const editingRule = ref<AlertRule | null>(null)
const ruleForm = reactive({ name: '', metric: '', threshold: 0, level: 'warning' })

const listPayload = () => ({
  page: pagination.current,
  page_size: pagination.pageSize,
  level: filters.level,
  q: filters.keyword || undefined,
  start_at: historyRange.value?.[0]?.toISOString(),
  end_at: historyRange.value?.[1]?.toISOString()
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

const normalizeList = (payload: any): { items: any[]; total: number } => {
  if (!payload) return { items: [], total: 0 }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

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

const loadRules = async () => {
  const res = await getAlertRules({ q: filters.keyword || undefined })
  const parsed = normalizeList(res?.data)
  rules.value = parsed.items
}

const loadActiveData = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'current') await loadCurrentAlerts()
    if (activeTab.value === 'history') await loadHistoryAlerts()
    if (activeTab.value === 'rules') await loadRules()
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
  if (activeTab.value === 'current') router.replace('/monitoring/alert/current')
  if (activeTab.value === 'history') router.replace('/monitoring/alert/history')
  if (activeTab.value === 'rules') router.replace('/monitoring/alert/rule')
  pagination.current = 1
  loadActiveData()
}

const syncTabByRoute = () => {
  const path = route.path
  if (path.endsWith('/history')) activeTab.value = 'history'
  else if (path.endsWith('/rule')) activeTab.value = 'rules'
  else activeTab.value = 'current'
}

const resetFilters = () => {
  filters.level = undefined
  filters.keyword = ''
  historyRange.value = null
  pagination.current = 1
  loadActiveData()
}

const handleClaim = async (record: AlertItem) => {
  await claimAlert(record.id)
  message.success('认领成功')
  loadActiveData()
}

const handleClose = async (record: AlertItem) => {
  Modal.confirm({
    title: '确认关闭告警？',
    onOk: async () => {
      await closeAlert(record.id)
      message.success('关闭成功')
      loadActiveData()
    }
  })
}

const openRuleModal = (record?: AlertRule) => {
  editingRule.value = record || null
  ruleForm.name = record?.name || ''
  ruleForm.metric = record?.metric || ''
  ruleForm.threshold = Number(record?.threshold || 0)
  ruleForm.level = record?.level || 'warning'
  ruleModalOpen.value = true
}

const saveRule = async () => {
  if (!ruleForm.name || !ruleForm.metric) {
    message.warning('请填写完整规则信息')
    return
  }
  ruleSaving.value = true
  try {
    const payload = {
      name: ruleForm.name,
      metric: ruleForm.metric,
      threshold: ruleForm.threshold,
      level: ruleForm.level,
      enabled: true
    }
    if (editingRule.value?.id) {
      await updateAlertRule(editingRule.value.id, payload)
    } else {
      await createAlertRule(payload)
    }
    message.success('保存成功')
    ruleModalOpen.value = false
    loadRules()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    ruleSaving.value = false
  }
}

const toggleRule = async (record: AlertRule, checked: boolean) => {
  try {
    if (checked) {
      await enableAlertRule(record.id)
    } else {
      await disableAlertRule(record.id)
    }
    message.success('状态更新成功')
    loadRules()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '状态更新失败')
  }
}

const handleDeleteRule = async (record: AlertRule) => {
  try {
    await deleteAlertRule(record.id)
    message.success('删除成功')
    loadRules()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const exportHistory = () => {
  const rows = alerts.value.map((item) => [
    item.level || '',
    item.name || '',
    item.monitor_name || '',
    item.metric_value ?? '',
    item.triggered_at || '',
    item.recovered_at || '',
    item.assignee || '',
    item.note || ''
  ])
  const header = ['级别', '告警名称', '监控对象', '指标值', '触发时间', '恢复时间', '处理人', '备注']
  const csv = [header, ...rows].map((line) => line.map((v) => `"${String(v).split('"').join('""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `alerts-history-${dayjs().format('YYYYMMDDHHmmss')}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const connectAlertSocket = () => {
  const token = localStorage.getItem('token')
  if (!token) return
  const wsUrl = (import.meta as any).env?.VITE_WS_URL || window.location.origin
  socket = io(`${wsUrl}/notifications`, {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    query: { token }
  })
  socket.on('monitoring:alert:new', () => {
    if (activeTab.value !== 'rules') loadActiveData()
  })
  socket.on('monitoring:alert:update', () => {
    if (activeTab.value !== 'rules') loadActiveData()
  })
}

onMounted(() => {
  syncTabByRoute()
  loadActiveData()
  connectAlertSocket()
})

watch(
  () => route.path,
  () => {
    syncTabByRoute()
    pagination.current = 1
    loadActiveData()
  }
)

onUnmounted(() => {
  if (socket) {
    socket.disconnect()
    socket = null
  }
})
</script>
