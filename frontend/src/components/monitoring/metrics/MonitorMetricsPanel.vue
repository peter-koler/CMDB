<template>
  <div class="monitor-metrics-panel">
    <a-alert
      v-if="!groups.length"
      type="info"
      show-icon
      message="当前模板未定义指标分类(metrics)，无法渲染分类视图。"
    />

    <a-tabs v-else v-model:activeKey="activeGroupKey" @change="handleGroupChange">
      <a-tab-pane v-for="group in groups" :key="group.key" :tab="group.title">
        <a-space direction="vertical" style="width: 100%" :size="12">
          <a-space wrap>
            <a-button type="primary" @click="openAddModal">添加</a-button>
            <a-button danger :disabled="!currentSelectedRowKeys.length" @click="removeSelectedMetrics">删除</a-button>
            <a-button :loading="refreshing" @click="refreshCurrentGroup">刷新</a-button>
            <span class="sub-text">最后刷新：{{ lastRefreshByGroup[group.key] || '-' }}</span>
          </a-space>

          <a-table
            size="small"
            :pagination="false"
            :loading="refreshing"
            :data-source="currentRows"
            row-key="field"
            :row-selection="currentRowSelection"
          >
            <a-table-column title="名称" key="title" width="260">
              <template #default="{ record }">
                <div class="metric-name-cell">
                  <div>{{ record.title }}</div>
                  <div class="field-name">{{ record.field }}</div>
                </div>
              </template>
            </a-table-column>
            <a-table-column title="状态" key="status" width="100">
              <template #default="{ record }">
                <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="最新值" key="latest" width="160">
              <template #default="{ record }">{{ record.latestValueText }}</template>
            </a-table-column>
            <a-table-column title="间隔" key="interval" width="100">
              <template #default>
                {{ intervalSeconds }}s
              </template>
            </a-table-column>
            <a-table-column title="时间" key="time" width="190">
              <template #default="{ record }">{{ record.latestTimeText }}</template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="140">
              <template #default="{ record }">
                <a-button type="link" size="small" @click="openTrend(record)">查看趋势明细</a-button>
              </template>
            </a-table-column>
          </a-table>
        </a-space>
      </a-tab-pane>
    </a-tabs>

    <a-modal
      v-model:open="addModalOpen"
      title="添加指标"
      width="560px"
      @ok="confirmAddMetrics"
    >
      <a-checkbox-group v-model:value="addSelectedFields" style="width: 100%">
        <a-space direction="vertical" style="width: 100%">
          <a-checkbox v-for="item in addCandidates" :key="item.field" :value="item.field">
            {{ item.title }}
            <span class="field-name">({{ item.field }})</span>
          </a-checkbox>
        </a-space>
      </a-checkbox-group>
      <a-empty v-if="!addCandidates.length" description="当前分类已全部添加" />
    </a-modal>

    <MetricTrendDialog
      v-model:open="trendOpen"
      :monitor-id="monitorId"
      :interval-seconds="intervalSeconds"
      :metric-name="trendMetricName"
      :metric-title="trendMetricTitle"
      :monitor-name="monitorName"
      :target="target"
      :app="app"
      :ci-code="ciCode"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import MetricTrendDialog from './MetricTrendDialog.vue'
import {
  computeMetricStatus,
  fetchLatestByNames,
  fetchSeriesNames,
  formatMetricValue,
  normalizeMetricToken,
  parseTemplateMetricGroups,
  resolveMetricName,
  type MetricFieldType,
  type MetricLatestPoint,
  type TemplateMetricField,
  type TemplateMetricGroup
} from '@/composables/useMonitorMetrics'
import {
  getCurrentAlerts,
  getTargetMetricsView,
  saveTargetMetricsView
} from '@/api/monitoring'

type RowStatus = 'normal' | 'abnormal' | 'unknown'

interface MetricTableRow {
  field: string
  title: string
  type: MetricFieldType
  metricName: string
  latest?: MetricLatestPoint
  latestValueText: string
  latestTimeText: string
  status: RowStatus
}

const props = defineProps<{
  monitorId: number
  app: string
  intervalSeconds: number
  templateContent: string
  monitorName?: string
  target?: string
  ciCode?: string
}>()

const groups = computed<TemplateMetricGroup[]>(() => parseTemplateMetricGroups(props.templateContent || ''))
const activeGroupKey = ref('')
const seriesNames = ref<string[]>([])
const refreshing = ref(false)
const rowsByGroup = ref<Record<string, MetricTableRow[]>>({})
const visibleFieldKeysByGroup = ref<Record<string, string[]>>({})
const selectedRowKeysByGroup = ref<Record<string, string[]>>({})
const lastRefreshByGroup = ref<Record<string, string>>({})
const activeAlertMetricSet = ref<Set<string>>(new Set())
let persistTimer: ReturnType<typeof setTimeout> | null = null

const addModalOpen = ref(false)
const addSelectedFields = ref<string[]>([])

const trendOpen = ref(false)
const trendMetricName = ref('')
const trendMetricTitle = ref('')

const currentGroup = computed(() => groups.value.find((group) => group.key === activeGroupKey.value) || null)
const currentRows = computed(() => rowsByGroup.value[activeGroupKey.value] || [])
const currentSelectedRowKeys = computed(() => selectedRowKeysByGroup.value[activeGroupKey.value] || [])

const currentRowSelection = computed(() => ({
  selectedRowKeys: currentSelectedRowKeys.value,
  onChange: (keys: (string | number)[]) => {
    selectedRowKeysByGroup.value = {
      ...selectedRowKeysByGroup.value,
      [activeGroupKey.value]: keys.map((item) => String(item))
    }
  }
}))

const addCandidates = computed<TemplateMetricField[]>(() => {
  const group = currentGroup.value
  if (!group) return []
  const visible = new Set(visibleFieldKeysByGroup.value[group.key] || [])
  return group.fields.filter((field) => !visible.has(field.field))
})

function statusText(status: RowStatus) {
  if (status === 'normal') return '正常'
  if (status === 'abnormal') return '异常'
  return '未知'
}

function statusColor(status: RowStatus) {
  if (status === 'normal') return 'green'
  if (status === 'abnormal') return 'red'
  return 'default'
}

function formatLatestValueText(fieldType: MetricFieldType, metricName: string, latest?: MetricLatestPoint): string {
  if (!latest) return '-'
  if (latest.text && String(latest.text).trim()) return String(latest.text).trim()
  if (latest.value === undefined || !Number.isFinite(latest.value)) return '-'
  const key = String(metricName || '').trim().toLowerCase()
  if (fieldType === 'string' || key.endsWith('_ok') || key.endsWith('_up')) {
    return latest.value >= 0.5 ? 'OK' : 'FAIL'
  }
  return formatMetricValue(latest.value)
}

function normalizeList(payload: any): { items: any[]; total: number } {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: Number(payload.total) || payload.items.length }
  return { items: [], total: 0 }
}

function ensureActiveGroup() {
  if (!groups.value.length) {
    activeGroupKey.value = ''
    return
  }
  if (!activeGroupKey.value || !groups.value.some((group) => group.key === activeGroupKey.value)) {
    activeGroupKey.value = groups.value[0].key
  }
}

function initVisibleFields() {
  const nextVisible: Record<string, string[]> = {}
  const nextSelected: Record<string, string[]> = {}
  for (const group of groups.value) {
    nextVisible[group.key] = group.fields.map((field) => field.field)
    nextSelected[group.key] = []
  }
  visibleFieldKeysByGroup.value = nextVisible
  selectedRowKeysByGroup.value = nextSelected
  rowsByGroup.value = {}
  lastRefreshByGroup.value = {}
}

async function restoreVisibleFieldsFromServer() {
  if (!props.monitorId || !groups.value.length) return
  try {
    const res = await getTargetMetricsView(props.monitorId)
    const payload = ((res as any)?.data || res) as any
    const raw = payload?.visible_fields_by_group
    if (!raw || typeof raw !== 'object') return
    const nextVisible: Record<string, string[]> = { ...visibleFieldKeysByGroup.value }
    for (const group of groups.value) {
      if (!Object.prototype.hasOwnProperty.call(raw, group.key)) continue
      const selectedRaw = Array.isArray(raw[group.key]) ? raw[group.key] : []
      const allowSet = new Set(group.fields.map((item) => item.field))
      const selected: string[] = []
      for (const one of selectedRaw) {
        const field = String(one || '').trim()
        if (!field || !allowSet.has(field) || selected.includes(field)) continue
        selected.push(field)
      }
      nextVisible[group.key] = selected
    }
    visibleFieldKeysByGroup.value = nextVisible
  } catch {
    // keep defaults when no persisted view exists
  }
}

async function persistVisibleFields() {
  if (!props.monitorId) return
  try {
    await saveTargetMetricsView(props.monitorId, {
      visible_fields_by_group: visibleFieldKeysByGroup.value
    })
  } catch {
    message.warning('指标展示配置保存失败，刷新后将回到默认显示')
  }
}

function schedulePersistVisibleFields() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    persistVisibleFields()
  }, 400)
}

function rowAlertCandidates(group: TemplateMetricGroup, field: TemplateMetricField, metricName: string): string[] {
  const out: string[] = []
  const push = (value: string) => {
    const key = String(value || '').trim().toLowerCase()
    if (!key || out.includes(key)) return
    out.push(key)
  }
  const groupNorm = normalizeMetricToken(group.key)
  const fieldNorm = normalizeMetricToken(field.field)
  push(metricName)
  push(field.field)
  push(`${groupNorm}_${fieldNorm}`)
  if (field.type === 'string') {
    push(`${field.field}_ok`)
    push(`${groupNorm}_${fieldNorm}_ok`)
  }
  if (field.field === 'success') {
    const appNorm = normalizeMetricToken(props.app || '')
    if (appNorm) push(`${appNorm}_server_up`)
    push('server_up')
  }
  return out
}

function isAlertingMetric(group: TemplateMetricGroup, field: TemplateMetricField, metricName: string): boolean {
  const set = activeAlertMetricSet.value
  if (!set.size) return false
  for (const candidate of rowAlertCandidates(group, field, metricName)) {
    if (set.has(candidate)) return true
  }
  return false
}

async function refreshActiveAlertMetrics() {
  if (!props.monitorId) {
    activeAlertMetricSet.value = new Set()
    return
  }
  try {
    const res = await getCurrentAlerts({
      monitor_id: props.monitorId,
      page: 1,
      page_size: 500
    })
    const parsed = normalizeList((res as any)?.data || res)
    const next = new Set<string>()
    for (const item of parsed.items || []) {
      const metric = String((item as any)?.metric || (item as any)?.labels?.metric || '').trim().toLowerCase()
      if (metric) next.add(metric)
    }
    activeAlertMetricSet.value = next
  } catch {
    activeAlertMetricSet.value = new Set()
  }
}

function mapRows(group: TemplateMetricGroup, latestMap: Record<string, MetricLatestPoint>): MetricTableRow[] {
  const visibleSet = new Set(visibleFieldKeysByGroup.value[group.key] || [])
  const rows: MetricTableRow[] = []

  for (const field of group.fields) {
    if (!visibleSet.has(field.field)) continue
    const metricName = resolveMetricName(props.app || '', group.key, field.field, field.type, seriesNames.value)
    const latest = metricName ? latestMap[metricName] : undefined
    let status = metricName
      ? computeMetricStatus(metricName, latest, props.intervalSeconds)
      : 'unknown'
    if (isAlertingMetric(group, field, metricName)) status = 'abnormal'

    rows.push({
      field: field.field,
      title: field.title,
      type: field.type,
      metricName,
      latest,
      latestValueText: formatLatestValueText(field.type, metricName, latest),
      latestTimeText: latest?.timestamp ? dayjs(latest.timestamp).format('YYYY-MM-DD HH:mm:ss') : '-',
      status
    })
  }

  return rows
}

async function refreshGroup(groupKey: string) {
  const group = groups.value.find((item) => item.key === groupKey)
  if (!group || !props.monitorId) return

  refreshing.value = true
  try {
    if (!seriesNames.value.length) {
      seriesNames.value = await fetchSeriesNames(props.monitorId)
    }

    const visibleSet = new Set(visibleFieldKeysByGroup.value[group.key] || [])
    const metricNames: string[] = []
    for (const field of group.fields) {
      if (!visibleSet.has(field.field)) continue
      const metricName = resolveMetricName(props.app || '', group.key, field.field, field.type, seriesNames.value)
      if (metricName) metricNames.push(metricName)
    }

    const latestMap = metricNames.length
      ? await fetchLatestByNames(props.monitorId, metricNames, props.intervalSeconds)
      : {}
    await refreshActiveAlertMetrics()

    rowsByGroup.value = {
      ...rowsByGroup.value,
      [group.key]: mapRows(group, latestMap)
    }
    lastRefreshByGroup.value = {
      ...lastRefreshByGroup.value,
      [group.key]: dayjs().format('YYYY-MM-DD HH:mm:ss')
    }
  } catch {
    rowsByGroup.value = {
      ...rowsByGroup.value,
      [group.key]: mapRows(group, {})
    }
    message.error('指标刷新失败')
  } finally {
    refreshing.value = false
  }
}

async function refreshCurrentGroup() {
  if (!activeGroupKey.value) return
  await refreshGroup(activeGroupKey.value)
}

function handleGroupChange(key: string) {
  activeGroupKey.value = key
  if (!rowsByGroup.value[key]) {
    refreshGroup(key)
  }
}

function openAddModal() {
  addSelectedFields.value = []
  addModalOpen.value = true
}

function confirmAddMetrics() {
  const group = currentGroup.value
  if (!group) {
    addModalOpen.value = false
    return
  }
  const visible = new Set(visibleFieldKeysByGroup.value[group.key] || [])
  for (const field of addSelectedFields.value) {
    visible.add(String(field))
  }
  visibleFieldKeysByGroup.value = {
    ...visibleFieldKeysByGroup.value,
    [group.key]: group.fields.map((item) => item.field).filter((field) => visible.has(field))
  }
  schedulePersistVisibleFields()
  addModalOpen.value = false
  refreshGroup(group.key)
}

function removeSelectedMetrics() {
  const group = currentGroup.value
  if (!group) return
  const toDelete = new Set(currentSelectedRowKeys.value)
  if (!toDelete.size) return

  const nextVisible = (visibleFieldKeysByGroup.value[group.key] || []).filter((field) => !toDelete.has(field))
  visibleFieldKeysByGroup.value = {
    ...visibleFieldKeysByGroup.value,
    [group.key]: nextVisible
  }
  schedulePersistVisibleFields()
  selectedRowKeysByGroup.value = {
    ...selectedRowKeysByGroup.value,
    [group.key]: []
  }
  refreshGroup(group.key)
}

function openTrend(row: MetricTableRow) {
  if (!row.metricName) {
    message.warning('当前指标暂无可用时序数据')
    return
  }
  trendMetricName.value = row.metricName
  trendMetricTitle.value = row.title
  trendOpen.value = true
}

async function initialize() {
  ensureActiveGroup()
  initVisibleFields()
  seriesNames.value = []
  await restoreVisibleFieldsFromServer()
  if (activeGroupKey.value) {
    await refreshGroup(activeGroupKey.value)
  }
}

watch(
  () => [props.monitorId, props.app, props.templateContent],
  () => {
    initialize()
  },
  { immediate: true }
)

onUnmounted(() => {
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = null
  }
})
</script>

<style scoped>
.sub-text {
  color: #8c8c8c;
  font-size: 12px;
}

.metric-name-cell {
  display: flex;
  flex-direction: column;
}

.field-name {
  color: #8c8c8c;
  font-size: 12px;
}
</style>
