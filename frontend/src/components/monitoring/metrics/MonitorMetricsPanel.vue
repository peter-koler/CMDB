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
            <a-button v-if="!currentIsRowMode" type="primary" @click="openAddModal">添加</a-button>
            <a-button v-if="!currentIsRowMode" danger :disabled="!currentSelectedRowKeys.length" @click="removeSelectedMetrics">删除</a-button>
            <a-button :loading="refreshing" @click="refreshCurrentGroup">刷新</a-button>
            <a-input-search
              v-model:value="currentSearchKeyword"
              allow-clear
              :placeholder="currentIsRowMode ? '按任意列搜索' : '按中文名/指标名搜索'"
              style="width: 260px"
            />
            <span class="sub-text">最后刷新：{{ lastRefreshByGroup[group.key] || '-' }}</span>
          </a-space>

          <a-table
            v-if="!currentIsRowMode"
            size="small"
            :pagination="currentPaginationConfig"
            :loading="refreshing"
            :data-source="pagedRows"
            row-key="field"
            :row-selection="currentRowSelection"
            @change="handleTableChange"
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

          <a-table
            v-else
            size="small"
            :pagination="currentPaginationConfig"
            :loading="refreshing"
            :data-source="pagedRowRows"
            row-key="__row_key__"
            @change="handleTableChange"
          >
            <a-table-column title="序号" key="__row_index__" width="80">
              <template #default="{ record }">{{ record.__row_index__ }}</template>
            </a-table-column>
            <a-table-column
              v-for="field in currentVisibleFields"
              :key="field.field"
              :title="field.title"
              :data-index="field.field"
            >
              <template #default="{ record }">{{ record[field.field] ?? '-' }}</template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="320">
              <template #default="{ record }">
                <a-space :size="[4, 0]" wrap>
                  <a-button
                    v-for="field in rowTrendFields"
                    :key="`${record.__row_key__}-${field.field}`"
                    type="link"
                    size="small"
                    :disabled="!canOpenRowTrend(record, field)"
                    @click="openRowTrend(record, field)"
                  >
                    查看{{ field.title }}趋势
                  </a-button>
                </a-space>
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
      :metric-type="trendMetricType"
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

interface MetricGroupRow {
  __row_key__: string
  __row_index__: number
  __metric_name_by_field__?: Record<string, string>
  [field: string]: string | number | Record<string, string> | undefined
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
const rowRowsByGroup = ref<Record<string, MetricGroupRow[]>>({})
const rowModeByGroup = ref<Record<string, boolean>>({})
const visibleFieldKeysByGroup = ref<Record<string, string[]>>({})
const selectedRowKeysByGroup = ref<Record<string, string[]>>({})
const searchKeywordByGroup = ref<Record<string, string>>({})
const lastRefreshByGroup = ref<Record<string, string>>({})
const paginationByGroup = ref<Record<string, { current: number; pageSize: number }>>({})
const activeAlertMetricSet = ref<Set<string>>(new Set())
let persistTimer: ReturnType<typeof setTimeout> | null = null

const DEFAULT_PAGE_SIZE = 10
const PAGE_SIZE_OPTIONS = ['10', '20', '50', '100']
const ROW_MODE_PROBE_LIMIT = 50

const addModalOpen = ref(false)
const addSelectedFields = ref<string[]>([])

const trendOpen = ref(false)
const trendMetricName = ref('')
const trendMetricTitle = ref('')
const trendMetricType = ref<MetricFieldType>('number')

const currentGroup = computed(() => groups.value.find((group) => group.key === activeGroupKey.value) || null)
const currentIsRowMode = computed(() => !!rowModeByGroup.value[activeGroupKey.value])
const osApps = new Set([
  'linux',
  'windows',
  'ubuntu',
  'debian',
  'centos',
  'almalinux',
  'opensuse',
  'freebsd',
  'redhat',
  'rockylinux',
  'euleros',
  'fedora',
  'darwin',
  'macos'
])
const isOsApp = computed(() => osApps.has(normalizeMetricToken(props.app || '')))
const currentRows = computed(() => rowsByGroup.value[activeGroupKey.value] || [])
const currentRowRows = computed(() => rowRowsByGroup.value[activeGroupKey.value] || [])
const currentVisibleFields = computed<TemplateMetricField[]>(() => {
  const group = currentGroup.value
  if (!group) return []
  const visible = new Set(visibleFieldKeysByGroup.value[group.key] || [])
  return group.fields.filter((field) => visible.has(field.field))
})
const rowTrendFields = computed<TemplateMetricField[]>(() => {
  if (!currentIsRowMode.value) return []
  return currentVisibleFields.value.filter((field) => field.type === 'number')
})
const currentSearchKeyword = computed({
  get: () => searchKeywordByGroup.value[activeGroupKey.value] || '',
  set: (value: string) => {
    const key = activeGroupKey.value
    if (!key) return
    searchKeywordByGroup.value = {
      ...searchKeywordByGroup.value,
      [key]: String(value || '')
    }
    const pag = paginationByGroup.value[key] || { current: 1, pageSize: DEFAULT_PAGE_SIZE }
    paginationByGroup.value = {
      ...paginationByGroup.value,
      [key]: { ...pag, current: 1 }
    }
  }
})
const filteredRows = computed(() => {
  const keyword = String(currentSearchKeyword.value || '').trim().toLowerCase()
  if (!keyword) return currentRows.value
  return currentRows.value.filter((row) => {
    const title = String(row.title || '').toLowerCase()
    const field = String(row.field || '').toLowerCase()
    return title.includes(keyword) || field.includes(keyword)
  })
})
const filteredRowRows = computed(() => {
  const keyword = String(currentSearchKeyword.value || '').trim().toLowerCase()
  if (!keyword) return currentRowRows.value
  return currentRowRows.value.filter((row) => {
    for (const field of currentVisibleFields.value) {
      const val = String(row[field.field] ?? '').toLowerCase()
      if (val.includes(keyword)) return true
    }
    return String(row.__row_index__).includes(keyword)
  })
})
const currentSelectedRowKeys = computed(() => selectedRowKeysByGroup.value[activeGroupKey.value] || [])
const currentPagination = computed(() => paginationByGroup.value[activeGroupKey.value] || { current: 1, pageSize: DEFAULT_PAGE_SIZE })
const pagedRows = computed(() => {
  const { current, pageSize } = currentPagination.value
  const start = (current - 1) * pageSize
  return filteredRows.value.slice(start, start + pageSize)
})
const pagedRowRows = computed(() => {
  const { current, pageSize } = currentPagination.value
  const start = (current - 1) * pageSize
  return filteredRowRows.value.slice(start, start + pageSize)
})
const currentPaginationConfig = computed(() => ({
  current: currentPagination.value.current,
  pageSize: currentPagination.value.pageSize,
  total: currentIsRowMode.value ? filteredRowRows.value.length : filteredRows.value.length,
  showSizeChanger: true,
  pageSizeOptions: PAGE_SIZE_OPTIONS,
  showTotal: (total: number) => `共 ${total} 条`
}))

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

function isOsPercentUsageField(groupKey: string, fieldKey: string): boolean {
  if (!isOsApp.value) return false
  const group = normalizeMetricToken(groupKey)
  const field = normalizeMetricToken(fieldKey)
  if (field !== 'usage') return false
  return group === 'memory' || group === 'disk_free'
}

function formatPercentTwo(raw: unknown): string {
  const num = parseNumericCellValue(raw)
  if (num === undefined) return '-'
  return `${num.toFixed(2)}%`
}

function formatLatestValueText(
  _fieldType: MetricFieldType,
  metricName: string,
  latest?: MetricLatestPoint,
  groupKey = '',
  fieldKey = ''
): string {
  if (!latest) return '-'
  const key = String(metricName || '').trim().toLowerCase()
  const text = String(latest.text || '').trim()
  const forcePercent = isOsPercentUsageField(groupKey, fieldKey)
  if (key.endsWith('_ok') || key.endsWith('_up')) {
    if (latest.value !== undefined && Number.isFinite(latest.value)) {
      return latest.value >= 0.5 ? 'OK' : 'FAIL'
    }
    if (text) return text
    return '-'
  }
  if (text) {
    if (forcePercent) {
      const percentText = formatPercentTwo(text)
      return percentText === '-' ? text : percentText
    }
    return text
  }
  if (latest.value !== undefined && Number.isFinite(latest.value)) {
    if (forcePercent) return `${latest.value.toFixed(2)}%`
    return formatMetricValue(latest.value)
  }
  return '-'
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
  const nextSearchKeyword: Record<string, string> = {}
  const nextPagination: Record<string, { current: number; pageSize: number }> = {}
  for (const group of groups.value) {
    nextVisible[group.key] = group.fields.map((field) => field.field)
    nextSelected[group.key] = []
    nextSearchKeyword[group.key] = searchKeywordByGroup.value[group.key] || ''
    nextPagination[group.key] = {
      current: 1,
      pageSize: paginationByGroup.value[group.key]?.pageSize || DEFAULT_PAGE_SIZE
    }
  }
  visibleFieldKeysByGroup.value = nextVisible
  selectedRowKeysByGroup.value = nextSelected
  searchKeywordByGroup.value = nextSearchKeyword
  paginationByGroup.value = nextPagination
  rowsByGroup.value = {}
  rowRowsByGroup.value = {}
  rowModeByGroup.value = {}
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

function escapeRegex(raw: string): string {
  return String(raw || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function detectRowIndices(group: TemplateMetricGroup, visibleFields: TemplateMetricField[]): number[] {
  const out = new Set<number>()
  if (!visibleFields.length || !seriesNames.value.length) return []
  const groupNorm = normalizeMetricToken(group.key)
  const fieldSet = new Set(visibleFields.map((field) => normalizeMetricToken(field.field)))
  const withGroup = new RegExp(`^${escapeRegex(groupNorm)}_row(\\d+)_([a-z0-9_]+)$`)
  const plain = /^row(\d+)_([a-z0-9_]+)$/
  for (const rawName of seriesNames.value) {
    const name = String(rawName || '').trim().toLowerCase()
    if (!name) continue
    let matched = withGroup.exec(name)
    if (!matched) matched = plain.exec(name)
    if (!matched) continue
    const idx = Number(matched[1])
    const field = String(matched[2] || '').trim()
    if (!Number.isFinite(idx) || idx <= 0) continue
    if (!fieldSet.has(field)) continue
    out.add(idx)
  }
  return Array.from(out).sort((a, b) => a - b)
}

function hasLatestMetricData(latest?: MetricLatestPoint): boolean {
  if (!latest) return false
  if (latest.value !== undefined && Number.isFinite(latest.value)) return true
  if (String(latest.text || '').trim()) return true
  return Number.isFinite(latest.timestamp) && Number(latest.timestamp) > 0
}

function buildRowMetricNameCandidates(
  group: TemplateMetricGroup,
  field: TemplateMetricField,
  baseMetricName: string,
  rowIndex: number
): string[] {
  const out: string[] = []
  const push = (value: string) => {
    const key = String(value || '').trim()
    if (!key || out.includes(key)) return
    out.push(key)
  }

  const groupRaw = String(group.key || '').trim()
  const groupNorm = normalizeMetricToken(group.key)
  const fieldRaw = String(field.field || '').trim()
  const fieldNorm = normalizeMetricToken(field.field)
  const rowRaw = `row${rowIndex}_${fieldRaw}`
  const rowNorm = `row${rowIndex}_${fieldNorm}`
  const groupRowRaw = `${groupRaw}_row${rowIndex}_${fieldRaw}`
  const groupRowNorm = `${groupNorm}_row${rowIndex}_${fieldNorm}`

  if (field.type === 'string') {
    push(groupRowRaw)
    push(groupRowNorm)
    push(rowRaw)
    push(rowNorm)
  } else {
    push(groupRowRaw)
    push(groupRowNorm)
    push(rowRaw)
    push(rowNorm)
  }

  const base = String(baseMetricName || '').trim()
  if (base) {
    if (fieldRaw) {
      if (base.endsWith(`_${fieldRaw}_ok`)) {
        push(base.replace(`_${fieldRaw}_ok`, `_row${rowIndex}_${fieldRaw}_ok`))
        push(`row${rowIndex}_${fieldRaw}_ok`)
      }
      if (base.endsWith(`_${fieldRaw}`)) {
        push(base.replace(`_${fieldRaw}`, `_row${rowIndex}_${fieldRaw}`))
      }
    }
    if (fieldNorm && fieldNorm !== fieldRaw) {
      if (base.endsWith(`_${fieldNorm}_ok`)) {
        push(base.replace(`_${fieldNorm}_ok`, `_row${rowIndex}_${fieldNorm}_ok`))
        push(`row${rowIndex}_${fieldNorm}_ok`)
      }
      if (base.endsWith(`_${fieldNorm}`)) {
        push(base.replace(`_${fieldNorm}`, `_row${rowIndex}_${fieldNorm}`))
      }
    }
    if (groupRaw && fieldRaw) {
      push(`${groupRaw}_row${rowIndex}_${fieldRaw}`)
    }
    if (groupNorm && fieldNorm) {
      push(`${groupNorm}_row${rowIndex}_${fieldNorm}`)
    }
  }

  return out
}

function resolveRowMetricName(
  candidates: string[],
  seriesNameSet: Set<string>,
  seriesNameMapLower: Map<string, string>
): string {
  for (const candidate of candidates) {
    if (seriesNameSet.has(candidate)) return candidate
    const matched = seriesNameMapLower.get(String(candidate || '').toLowerCase())
    if (matched) return matched
  }
  return candidates[0] || ''
}

function detectExplicitRowIndices(
  group: TemplateMetricGroup,
  visibleFields: TemplateMetricField[],
  baseMetricByField: Record<string, string>,
  latestMap: Record<string, MetricLatestPoint>
): number[] {
  const out: number[] = []
  for (let rowIndex = 1; rowIndex <= ROW_MODE_PROBE_LIMIT; rowIndex += 1) {
    let hasAny = false
    for (const field of visibleFields) {
      const candidates = buildRowMetricNameCandidates(group, field, baseMetricByField[field.field], rowIndex)
      for (const candidate of candidates) {
        if (hasLatestMetricData(latestMap[candidate])) {
          hasAny = true
          break
        }
      }
      if (hasAny) break
    }
    if (!hasAny) {
      if (out.length > 0) break
      continue
    }
    out.push(rowIndex)
  }
  return out
}

function buildExplicitRowMetricNameByKey(
  group: TemplateMetricGroup,
  visibleFields: TemplateMetricField[],
  rowIndices: number[],
  baseMetricByField: Record<string, string>,
  latestMap: Record<string, MetricLatestPoint>
): Record<string, string> {
  const out: Record<string, string> = {}
  for (const rowIndex of rowIndices) {
    for (const field of visibleFields) {
      const candidates = buildRowMetricNameCandidates(group, field, baseMetricByField[field.field], rowIndex)
      const matched = candidates.find((candidate) => hasLatestMetricData(latestMap[candidate]))
      if (matched) out[`${rowIndex}:${field.field}`] = matched
    }
  }
  return out
}

function parseNumericCellValue(raw: unknown): number | undefined {
  const text = String(raw ?? '').trim()
  if (!text || text === '-') return undefined
  const normalized = text.replace(/,/g, '').replace(/%/g, '').trim()
  if (!normalized) return undefined
  const value = Number(normalized)
  if (!Number.isFinite(value)) return undefined
  return value
}

function applyOsComputedRowFields(group: TemplateMetricGroup, row: MetricGroupRow) {
  if (!isOsApp.value) return
  const groupKey = normalizeMetricToken(group.key)
  if (groupKey !== 'disk_free') return
  const usageText = String(row.usage ?? '').trim()
  if (usageText && usageText !== '-') return

  const used = parseNumericCellValue(row.used)
  const available = parseNumericCellValue(row.available ?? row.free)
  const total = parseNumericCellValue(row.size ?? row.total)

  let usage: number | undefined
  if (used !== undefined && available !== undefined && used + available > 0) {
    usage = (used / (used + available)) * 100
  } else if (used !== undefined && total !== undefined && total > 0) {
    usage = (used / total) * 100
  }
  if (usage === undefined) return
  row.usage = formatPercentTwo(usage)
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
      latestValueText: formatLatestValueText(field.type, metricName, latest, group.key, field.field),
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
    const visibleFields = group.fields.filter((field) => visibleSet.has(field.field))
    const baseMetricByField: Record<string, string> = {}
    const metricNames: string[] = []
    for (const field of visibleFields) {
      const metricName = resolveMetricName(props.app || '', group.key, field.field, field.type, seriesNames.value)
      baseMetricByField[field.field] = metricName
      if (metricName) metricNames.push(metricName)
    }

    const explicitRowMode = group.viewMode === 'row'
    let explicitRowLatestMap: Record<string, MetricLatestPoint> = {}
    let rowIndices = explicitRowMode ? [] : detectRowIndices(group, visibleFields)
    const seriesNamesClean = seriesNames.value.map((item) => String(item || '').trim()).filter(Boolean)
    const seriesNameSet = new Set(seriesNamesClean)
    const seriesNameMapLower = new Map<string, string>()
    for (const name of seriesNamesClean) {
      const lower = name.toLowerCase()
      if (!seriesNameMapLower.has(lower)) {
        seriesNameMapLower.set(lower, name)
      }
    }
    if (explicitRowMode) {
      const explicitMetricNames: string[] = [...metricNames]
      for (let rowIndex = 1; rowIndex <= ROW_MODE_PROBE_LIMIT; rowIndex += 1) {
        for (const field of visibleFields) {
          explicitMetricNames.push(...buildRowMetricNameCandidates(group, field, baseMetricByField[field.field], rowIndex))
        }
      }
      explicitRowLatestMap = explicitMetricNames.length
        ? await fetchLatestByNames(props.monitorId, explicitMetricNames, props.intervalSeconds)
        : {}
      rowIndices = detectExplicitRowIndices(group, visibleFields, baseMetricByField, explicitRowLatestMap)
    }
    if (rowIndices.length) {
      const rowMetricNameByKey: Record<string, string> = explicitRowMode
        ? buildExplicitRowMetricNameByKey(group, visibleFields, rowIndices, baseMetricByField, explicitRowLatestMap)
        : {}
      if (!explicitRowMode) {
        for (const rowIndex of rowIndices) {
          for (const field of visibleFields) {
            const rowMetricName = resolveRowMetricName(
              buildRowMetricNameCandidates(group, field, baseMetricByField[field.field], rowIndex),
              seriesNameSet,
              seriesNameMapLower
            )
            if (!rowMetricName) continue
            rowMetricNameByKey[`${rowIndex}:${field.field}`] = rowMetricName
            metricNames.push(rowMetricName)
          }
        }
      }
      const latestMap = explicitRowMode
        ? explicitRowLatestMap
        : metricNames.length
          ? await fetchLatestByNames(props.monitorId, metricNames, props.intervalSeconds)
          : {}
      const nextRows: MetricGroupRow[] = []
      for (const rowIndex of rowIndices) {
        const row: MetricGroupRow = {
          __row_key__: `row-${rowIndex}`,
          __row_index__: rowIndex,
          __metric_name_by_field__: {}
        }
        let hasAny = false
        for (const field of visibleFields) {
          const key = `${rowIndex}:${field.field}`
          const rowMetricName = rowMetricNameByKey[key]
          const latest = rowMetricName ? latestMap[rowMetricName] : undefined
          const fallbackName = rowIndex === 1 ? baseMetricByField[field.field] : ''
          const fallback = fallbackName ? latestMap[fallbackName] : undefined
          const metricNameForCell = rowMetricName || (latest ? '' : fallbackName)
          const text = formatLatestValueText(field.type, metricNameForCell, latest || fallback, group.key, field.field)
          if (metricNameForCell && row.__metric_name_by_field__) {
            row.__metric_name_by_field__[field.field] = metricNameForCell
          }
          row[field.field] = text
          if (text !== '-') hasAny = true
        }
        applyOsComputedRowFields(group, row)
        if (String(row.usage ?? '').trim() && String(row.usage ?? '').trim() !== '-') {
          hasAny = true
        }
        if (hasAny) nextRows.push(row)
      }
      await refreshActiveAlertMetrics()
      rowRowsByGroup.value = {
        ...rowRowsByGroup.value,
        [group.key]: nextRows
      }
      rowModeByGroup.value = {
        ...rowModeByGroup.value,
        [group.key]: true
      }
      rowsByGroup.value = {
        ...rowsByGroup.value,
        [group.key]: []
      }
      lastRefreshByGroup.value = {
        ...lastRefreshByGroup.value,
        [group.key]: dayjs().format('YYYY-MM-DD HH:mm:ss')
      }
      return
    }
    if (explicitRowMode) {
      await refreshActiveAlertMetrics()
      rowRowsByGroup.value = {
        ...rowRowsByGroup.value,
        [group.key]: []
      }
      rowModeByGroup.value = {
        ...rowModeByGroup.value,
        [group.key]: true
      }
      rowsByGroup.value = {
        ...rowsByGroup.value,
        [group.key]: []
      }
      lastRefreshByGroup.value = {
        ...lastRefreshByGroup.value,
        [group.key]: dayjs().format('YYYY-MM-DD HH:mm:ss')
      }
      return
    }

    const latestMap = metricNames.length
      ? await fetchLatestByNames(props.monitorId, metricNames, props.intervalSeconds)
      : {}
    await refreshActiveAlertMetrics()

    rowRowsByGroup.value = {
      ...rowRowsByGroup.value,
      [group.key]: []
    }
    rowModeByGroup.value = {
      ...rowModeByGroup.value,
      [group.key]: false
    }
    rowsByGroup.value = {
      ...rowsByGroup.value,
      [group.key]: mapRows(group, latestMap)
    }
    lastRefreshByGroup.value = {
      ...lastRefreshByGroup.value,
      [group.key]: dayjs().format('YYYY-MM-DD HH:mm:ss')
    }
  } catch {
    rowRowsByGroup.value = {
      ...rowRowsByGroup.value,
      [group.key]: []
    }
    rowModeByGroup.value = {
      ...rowModeByGroup.value,
      [group.key]: false
    }
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

function handleTableChange(pagination: { current?: number; pageSize?: number }) {
  if (!activeGroupKey.value) return
  const current = pagination.current ?? 1
  const pageSize = pagination.pageSize ?? DEFAULT_PAGE_SIZE
  paginationByGroup.value = {
    ...paginationByGroup.value,
    [activeGroupKey.value]: { current, pageSize }
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
  trendMetricType.value = row.type
  trendOpen.value = true
}

function resolveRowMetricNameFromRecord(record: MetricGroupRow, fieldKey: string): string {
  const map = record.__metric_name_by_field__
  if (!map || typeof map !== 'object') return ''
  return String(map[fieldKey] || '').trim()
}

function canOpenRowTrend(record: MetricGroupRow, field: TemplateMetricField): boolean {
  if (field.type !== 'number') return false
  const metricName = resolveRowMetricNameFromRecord(record, field.field)
  return !!metricName
}

function openRowTrend(record: MetricGroupRow, field: TemplateMetricField) {
  if (field.type !== 'number') {
    message.warning('行模式仅支持数值指标趋势')
    return
  }
  const metricName = resolveRowMetricNameFromRecord(record, field.field)
  if (!metricName) {
    message.warning('当前指标暂无可用时序数据')
    return
  }
  const group = currentGroup.value
  const rowIndex = Number(record.__row_index__) || 0
  trendMetricName.value = metricName
  trendMetricTitle.value = group
    ? `${group.title}-${field.title}(序号${rowIndex})`
    : `${field.title}(序号${rowIndex})`
  trendMetricType.value = field.type
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

watch(
  () => [activeGroupKey.value, filteredRows.value.length, filteredRowRows.value.length, currentIsRowMode.value],
  () => {
    const key = activeGroupKey.value
    if (!key) return
    const pag = paginationByGroup.value[key]
    if (!pag) return
    const total = currentIsRowMode.value ? filteredRowRows.value.length : filteredRows.value.length
    const maxPage = Math.max(1, Math.ceil(total / pag.pageSize))
    if (pag.current > maxPage) {
      paginationByGroup.value = {
        ...paginationByGroup.value,
        [key]: { ...pag, current: maxPage }
      }
    }
  }
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
  color: var(--app-text-muted);
  font-size: 12px;
}

.metric-name-cell {
  display: flex;
  flex-direction: column;
}

.field-name {
  color: var(--app-text-muted);
  font-size: 12px;
}
</style>
