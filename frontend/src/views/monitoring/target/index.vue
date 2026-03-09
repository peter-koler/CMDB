<template>
  <div class="monitor-target-layout">
    <div class="category-sidebar">
      <a-card :bordered="false" class="category-card">
        <template #title>
          <div class="category-title">
            <span>监控分类</span>
            <a-button type="link" size="small" @click="reloadCategoryMenu">
              <reload-outlined />
            </a-button>
          </div>
        </template>
        <a-tree
          :tree-data="categoryTree"
          :field-names="{ title: 'name', key: 'code', children: 'children' }"
          :selected-keys="selectedCategory ? [selectedCategory] : []"
          @select="handleCategorySelect"
          block-node
          default-expand-all
        >
          <template #title="{ name, count, nodeType }">
            <div class="category-node">
              <span class="category-name">{{ name }}</span>
              <span v-if="nodeType === 'category' && count" class="category-count">({{ count }})</span>
            </div>
          </template>
        </a-tree>
      </a-card>
    </div>

    <div class="target-content">
      <a-card :bordered="false">
        <a-space direction="vertical" style="width: 100%" :size="16">
          <a-form layout="inline">
            <a-form-item label="关键字">
              <a-input v-model:value="keyword" placeholder="名称/CI/地址" style="width: 220px" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="status" allow-clear placeholder="全部状态" style="width: 140px">
                <a-select-option value="enabled">enabled</a-select-option>
                <a-select-option value="disabled">disabled</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item>
              <a-space>
                <a-button type="primary" :loading="loading" @click="loadTargets">查询</a-button>
                <a-button @click="reset">重置</a-button>
                <a-button v-if="canCreate" type="primary" @click="openModal()">新增监控</a-button>
              </a-space>
            </a-form-item>
          </a-form>

          <div v-if="selectedCategoryName" class="current-category">
            <a-tag color="blue">{{ selectedCategoryName }}</a-tag>
            <a-button type="link" size="small" @click="clearCategoryFilter">清除筛选</a-button>
          </div>

          <a-table
            :loading="loading"
            :columns="columns"
            :data-source="targets"
            row-key="id"
            :pagination="pagination"
            :row-selection="rowSelection"
            @change="handleTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'ci'">
                <div class="ci-cell">
                  <div>{{ record.ci_code || '-' }}</div>
                  <div class="sub-text">{{ record.ci_name || '' }}</div>
                </div>
              </template>

              <template v-if="column.key === 'interval'">
                {{ normalizedInterval(record) }}
              </template>

              <template v-if="column.key === 'status'">
                <a-tag :color="record.enabled === false ? 'default' : 'green'">
                  {{ record.enabled === false ? 'disabled' : 'enabled' }}
                </a-tag>
              </template>

              <template v-if="column.key === 'enabled'">
                <a-switch
                  :checked="record.enabled !== false"
                  :disabled="!canEdit"
                  @change="(checked: boolean) => toggleTarget(record, checked)"
                />
              </template>

              <template v-if="column.key === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="openDetail(record)">详情</a-button>
                  <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
                  <a-popconfirm title="确认删除该监控？" @confirm="removeTarget(record)">
                    <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>

          <a-space>
            <a-button :disabled="!selectedRowKeys.length || !canDelete" danger @click="batchDelete">批量删除</a-button>
            <a-input-number v-model:value="batchInterval" :min="10" :step="10" style="width: 160px" />
            <a-button :disabled="!selectedRowKeys.length || !canEdit" @click="batchUpdateInterval">批量修改间隔</a-button>
          </a-space>
        </a-space>
      </a-card>
    </div>

    <a-modal
      v-model:open="modalOpen"
      :title="editing?.id ? '编辑监控' : '新增监控'"
      @ok="saveTarget"
      :confirm-loading="saving"
      width="760px"
    >
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="任务名称" required>
              <a-input v-model:value="formState.name" placeholder="请输入监控任务名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="采集间隔(秒)" required>
              <a-input-number v-model:value="formState.interval" :min="10" :step="10" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="CI模型" required>
              <a-select
                v-model:value="formState.ci_model_id"
                placeholder="请选择CI模型"
                :loading="modelsLoading"
                show-search
                :filter-option="filterOption"
                @focus="loadModels"
              >
                <a-select-option v-for="m in modelOptions" :key="m.id" :value="m.id">
                  {{ m.name }} ({{ m.code }})
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="CI实例" required>
              <a-select
                v-model:value="formState.ci_id"
                placeholder="请先选择模型"
                :loading="ciLoading"
                :disabled="!formState.ci_model_id"
                show-search
                :filter-option="filterOption"
                @focus="() => loadCiOptions(formState.ci_model_id)"
              >
                <a-select-option v-for="ci in ciOptions" :key="ci.id" :value="ci.id">
                  {{ ci.display }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="监控模板" required>
              <a-select
                v-model:value="formState.app"
                placeholder="选择模板(app)"
                style="width: 100%"
                :loading="templatesLoading"
                show-search
                :filter-option="filterOption"
                @focus="loadTemplates"
                @change="handleTemplateChange"
              >
                <a-select-option v-for="t in templates" :key="t.app" :value="t.app">
                  {{ t.name }} ({{ t.app }})
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col :span="12">
            <a-form-item label="目标地址(target)">
              <a-input v-model:value="formState.target" placeholder="可留空，默认由 params host/port 生成" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item v-if="visibleParamDefs.length" label="模板参数 (params)">
          <a-row :gutter="12">
            <a-col :span="12" v-for="param in visibleParamDefs" :key="param.field" style="margin-bottom: 12px">
              <a-form-item :label="paramLabel(param)" :required="Boolean(param.required)" style="margin-bottom: 0">
                <a-input-number
                  v-if="param.type === 'number'"
                  v-model:value="formState.params[param.field]"
                  style="width: 100%"
                />
                <a-select
                  v-else-if="param.type === 'boolean'"
                  v-model:value="formState.params[param.field]"
                  style="width: 100%"
                >
                  <a-select-option value="true">true</a-select-option>
                  <a-select-option value="false">false</a-select-option>
                </a-select>
                <a-input-password
                  v-else-if="param.type === 'password'"
                  v-model:value="formState.params[param.field]"
                  :placeholder="paramPlaceholder(param)"
                />
                <a-textarea
                  v-else-if="param.type === 'textarea'"
                  v-model:value="formState.params[param.field]"
                  :placeholder="paramPlaceholder(param)"
                  :rows="2"
                />
                <a-input
                  v-else
                  v-model:value="formState.params[param.field]"
                  :placeholder="paramPlaceholder(param)"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form-item>

        <a-form-item label="采集器分配">
          <a-space direction="vertical" style="width: 100%">
            <a-select
              v-model:value="formState.collector_id"
              allow-clear
              placeholder="自动分配（推荐）"
              style="width: 100%"
              :loading="collectorsLoading"
              @focus="loadCollectors"
            >
              <a-select-option v-for="c in collectors" :key="c.id" :value="c.id">
                {{ c.name || c.id }} {{ c.host ? `(${c.host})` : '' }}
              </a-select-option>
            </a-select>
            <a-checkbox v-model:checked="formState.pin_collector" :disabled="!formState.collector_id">
              固定分配到该采集器（不随负载均衡变更）
            </a-checkbox>
          </a-space>
        </a-form-item>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer v-model:open="detailOpen" title="监控任务详情" width="980" destroy-on-close @close="closeDetail">
      <template v-if="detailTarget">
        <a-tabs v-model:activeKey="detailTab">
          <a-tab-pane key="basic" tab="基本信息">
            <a-descriptions bordered :column="2" size="small">
              <a-descriptions-item label="任务ID">{{ detailTarget.id }}</a-descriptions-item>
              <a-descriptions-item label="任务标识">{{ detailTarget.job_id || '-' }}</a-descriptions-item>
              <a-descriptions-item label="名称">{{ detailTarget.name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="模板(app)">{{ detailTarget.app || '-' }}</a-descriptions-item>
              <a-descriptions-item label="CI编码">{{ detailTarget.ci_code || '-' }}</a-descriptions-item>
              <a-descriptions-item label="CI名称">{{ detailTarget.ci_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="目标地址">{{ detailTarget.target || '-' }}</a-descriptions-item>
              <a-descriptions-item label="采集间隔">{{ normalizedInterval(detailTarget) }}s</a-descriptions-item>
              <a-descriptions-item label="状态">
                <a-tag :color="detailTarget.enabled === false ? 'default' : 'green'">
                  {{ detailTarget.enabled === false ? 'disabled' : 'enabled' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="创建时间">{{ detailTarget.created_at || '-' }}</a-descriptions-item>
            </a-descriptions>
          </a-tab-pane>

          <a-tab-pane key="metrics" tab="指标">
            <a-space direction="vertical" style="width: 100%" :size="12">
              <a-space wrap>
                <a-segmented
                  v-model:value="metricRangePreset"
                  :options="rangePresetOptions"
                  @change="handleRangePresetChange"
                />
                <a-range-picker
                  v-model:value="metricCustomRange"
                  show-time
                  format="YYYY-MM-DD HH:mm:ss"
                  @change="handleCustomRangeChange"
                />
                <a-select v-model:value="metricStepSeconds" style="width: 120px" @change="refreshMetricData">
                  <a-select-option :value="0">自动步长</a-select-option>
                  <a-select-option :value="15">15s</a-select-option>
                  <a-select-option :value="30">30s</a-select-option>
                  <a-select-option :value="60">60s</a-select-option>
                  <a-select-option :value="300">5m</a-select-option>
                </a-select>
                <a-select
                  v-model:value="selectedMetricNames"
                  mode="multiple"
                  :max-tag-count="3"
                  :options="metricNameSelectOptions"
                  placeholder="选择指标"
                  style="min-width: 320px"
                  @change="refreshMetricData"
                />
                <a-button :loading="metricLoading" @click="refreshMetricData">刷新</a-button>
              </a-space>

              <a-space>
                <a-switch v-model:checked="metricAutoRefresh" />
                <span>自动刷新</span>
                <a-select v-model:value="metricRefreshSeconds" style="width: 110px" :disabled="!metricAutoRefresh">
                  <a-select-option :value="30">30s</a-select-option>
                  <a-select-option :value="60">60s</a-select-option>
                  <a-select-option :value="120">120s</a-select-option>
                </a-select>
                <span class="sub-text">最后更新时间: {{ metricLastLoadedAt || '-' }}</span>
              </a-space>

              <a-spin :spinning="metricLoading">
                <a-empty v-if="!metricChartSeries.length" description="暂无可视化指标数据" />
                <div v-else class="metric-chart-grid">
                  <div v-for="series in metricChartSeries" :key="series.key" class="metric-chart-card">
                    <div class="metric-card-header">
                      <div class="metric-title">{{ series.name }}</div>
                      <div class="metric-stats">
                        <span>最新: {{ formatMetricValue(series.latest) }}</span>
                        <span>最小: {{ formatMetricValue(series.min) }}</span>
                        <span>最大: {{ formatMetricValue(series.max) }}</span>
                      </div>
                    </div>
                    <svg viewBox="0 0 640 220" preserveAspectRatio="none" class="metric-svg">
                      <rect x="0" y="0" width="640" height="220" fill="#fafafa" />
                      <line x1="24" y1="20" x2="24" y2="196" stroke="#d9d9d9" stroke-width="1" />
                      <line x1="24" y1="196" x2="620" y2="196" stroke="#d9d9d9" stroke-width="1" />
                      <polyline :points="series.polyline" fill="none" stroke="#1677ff" stroke-width="2" stroke-linecap="round" />
                    </svg>
                    <div class="metric-axis-text">
                      <span>{{ series.fromText }}</span>
                      <span>{{ series.toText }}</span>
                    </div>
                  </div>
                </div>
              </a-spin>
            </a-space>
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import dayjs, { type Dayjs } from 'dayjs'
import * as yaml from 'js-yaml'
import { useUserStore } from '@/stores/user'
import {
  assignCollectorToMonitor,
  createMonitoringTarget,
  deleteMonitoringTarget,
  disableMonitoringTarget,
  enableMonitoringTarget,
  getCategories,
  getCollectors,
  getMonitoringTargets,
  getTargetMetricSeries,
  getTemplates,
  queryTargetMetricRange,
  type MetricRangePoint,
  type MetricRangeSeries,
  type MonitorCategory,
  type MonitoringTarget,
  type MonitorTemplate,
  unassignCollectorFromMonitor,
  updateMonitoringTarget
} from '@/api/monitoring'
import { getModels } from '@/api/cmdb'
import { getInstances } from '@/api/ci'

interface TemplateParamDef {
  field: string
  name?: Record<string, string> | string
  type?: string
  required?: boolean
  defaultValue?: string | number | boolean
  placeholder?: string
  hide?: boolean
}

interface ParsedTemplate {
  params: TemplateParamDef[]
}

interface ModelOption {
  id: number
  name: string
  code: string
}

interface CiOption {
  id: number
  code: string
  display: string
  attributes: Record<string, any>
}

interface ChartSeriesView {
  key: string
  name: string
  latest: number
  min: number
  max: number
  fromText: string
  toText: string
  polyline: string
}

interface CategoryTreeNode {
  code: string
  name: string
  nodeType: 'category' | 'template'
  count?: number
  app?: string
  children?: CategoryTreeNode[]
}

const userStore = useUserStore()

const categories = ref<MonitorCategory[]>([])
const categoryTree = ref<CategoryTreeNode[]>([])
const selectedCategory = ref<string | null>(null)
const selectedCategoryName = computed(() => {
  if (!selectedCategory.value) return ''
  const findName = (list: any[]): string => {
    for (const item of list) {
      if (item.code === selectedCategory.value) return item.name
      if (item.children) {
        const inner = findName(item.children)
        if (inner) return inner
      }
    }
    return ''
  }
  return findName(categoryTree.value)
})

const templates = ref<MonitorTemplate[]>([])
const templatesLoading = ref(false)
const parsedTemplateMap = computed<Record<string, ParsedTemplate>>(() => {
  const out: Record<string, ParsedTemplate> = {}
  templates.value.forEach((tpl) => {
    out[tpl.app] = parseTemplateContent(tpl.content)
  })
  return out
})

const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const status = ref<string | undefined>(undefined)
const targets = ref<MonitoringTarget[]>([])
const allTargets = ref<MonitoringTarget[]>([])
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const selectedRowKeys = ref<number[]>([])
const batchInterval = ref<number>(60)

const modalOpen = ref(false)
const editing = ref<MonitoringTarget | null>(null)
const formState = reactive({
  name: '',
  app: '',
  target: '',
  interval: 60,
  enabled: true,
  ci_model_id: undefined as number | undefined,
  ci_id: undefined as number | undefined,
  collector_id: undefined as string | undefined,
  pin_collector: false,
  params: {} as Record<string, any>
})

const modelOptions = ref<ModelOption[]>([])
const modelsLoading = ref(false)
const ciOptions = ref<CiOption[]>([])
const ciLoading = ref(false)

const collectors = ref<Array<{ id: string; name?: string; host?: string; status?: string }>>([])
const collectorsLoading = ref(false)

const detailOpen = ref(false)
const detailTab = ref<'basic' | 'metrics'>('basic')
const detailTarget = ref<MonitoringTarget | null>(null)

const metricLoading = ref(false)
const metricRangePreset = ref<'5m' | '1h' | '24h' | '7d' | '30d' | 'custom'>('1h')
const metricCustomRange = ref<[Dayjs, Dayjs] | null>(null)
const metricStepSeconds = ref<number>(0)
const metricAutoRefresh = ref(true)
const metricRefreshSeconds = ref(60)
const metricNameOptions = ref<string[]>([])
const metricLabelMapCache = ref<Record<string, Record<string, string>>>({})
const selectedMetricNames = ref<string[]>([])
const metricSeries = ref<MetricRangeSeries[]>([])
const metricLastLoadedAt = ref('')
const syncingFormFromRecord = ref(false)
let metricTimer: number | undefined

const rangePresetOptions = [
  { label: '5m', value: '5m' },
  { label: '1h', value: '1h' },
  { label: '24h', value: '24h' },
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '自定义', value: 'custom' }
]

const canEdit = computed(() => userStore.hasPermission('monitoring:list:edit') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:update') || userStore.hasPermission('monitoring:target'))
const canCreate = computed(() => userStore.hasPermission('monitoring:list:create') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:create') || userStore.hasPermission('monitoring:target'))
const canDelete = computed(() => userStore.hasPermission('monitoring:list:delete') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:delete') || userStore.hasPermission('monitoring:target'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '任务标识', dataIndex: 'job_id', key: 'job_id', width: 180 },
  { title: 'CI', key: 'ci', width: 220 },
  { title: '类型', dataIndex: 'app', key: 'app', width: 120 },
  { title: '目标地址', dataIndex: 'target', key: 'target' },
  { title: '采集间隔(s)', key: 'interval', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 90 },
  { title: '操作', key: 'actions', width: 190 }
]

const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: (string | number)[]) => {
    selectedRowKeys.value = keys.map((item) => Number(item))
  }
}))

const selectedTemplate = computed(() => templates.value.find((item) => item.app === formState.app))
const visibleParamDefs = computed(() => {
  const parsed = parsedTemplateMap.value[formState.app]
  if (!parsed?.params?.length) return []
  return parsed.params.filter((item) => item && item.field && !item.hide)
})

const metricNameSelectOptions = computed(() => {
  return metricNameOptions.value.map((name) => ({
    value: name,
    label: formatMetricDisplayName(name)
  }))
})

const metricChartSeries = computed<ChartSeriesView[]>(() => {
  const chartList: ChartSeriesView[] = []
  for (const series of metricSeries.value) {
    if (!series?.points?.length) continue
    const sorted = [...series.points].sort((a, b) => a.timestamp - b.timestamp)
    const values = sorted.map((p) => Number(p.value)).filter((v) => Number.isFinite(v))
    if (!values.length) continue
    const latest = values[values.length - 1]
    const min = Math.min(...values)
    const max = Math.max(...values)
    chartList.push({
      key: series.name,
      name: formatMetricDisplayName(series.name),
      latest,
      min,
      max,
      fromText: dayjs(sorted[0].timestamp).format('MM-DD HH:mm:ss'),
      toText: dayjs(sorted[sorted.length - 1].timestamp).format('MM-DD HH:mm:ss'),
      polyline: buildPolyline(sorted)
    })
  }
  return chartList
})

function parseTemplateContent(content: string): ParsedTemplate {
  try {
    const parsed = (yaml.load(content || '') || {}) as any
    const rawParams = Array.isArray(parsed?.params) ? parsed.params : []
    const deduped: TemplateParamDef[] = []
    const seen = new Set<string>()
    for (const item of rawParams) {
      if (!item || typeof item !== 'object') continue
      const field = String(item.field || '').trim()
      if (!field || seen.has(field)) continue
      seen.add(field)
      deduped.push(item)
    }
    return {
      params: deduped
    }
  } catch {
    return { params: [] }
  }
}

const invalidMetricToken = /[^a-zA-Z0-9_]/g

function normalizeMetricToken(raw: string): string {
  let token = String(raw || '').trim()
  if (!token) return 'unknown'
  token = token.replace(invalidMetricToken, '_').replace(/^_+|_+$/g, '')
  if (!token) return 'unknown'
  if (/^[0-9]/.test(token)) {
    token = `m_${token}`
  }
  return token
}

function pickI18nText(value: any): string {
  if (typeof value === 'string') return value.trim()
  if (!value || typeof value !== 'object') return ''

  const obj = value as Record<string, any>
  const candidates = [
    obj['zh-CN'],
    obj['zh_CN'],
    obj['zh'],
    obj['en-US'],
    obj['en_US'],
    obj['en']
  ]
  for (const item of candidates) {
    if (typeof item === 'string' && item.trim()) return item.trim()
  }
  const fallback = Object.values(obj).find((item) => typeof item === 'string' && String(item).trim())
  return typeof fallback === 'string' ? fallback.trim() : ''
}

function buildMetricLabelMapFromTemplate(content: string): Record<string, string> {
  try {
    const parsed = (yaml.load(content || '') || {}) as any
    const groups = Array.isArray(parsed?.metrics) ? parsed.metrics : []
    const labelMap: Record<string, string> = {}
    for (const group of groups) {
      const metricGroupName = String(group?.name || '').trim()
      if (!metricGroupName) continue
      const fields = Array.isArray(group?.fields) ? group.fields : []
      for (const field of fields) {
        const fieldName = String(field?.field || '').trim()
        if (!fieldName) continue
        const metricName = normalizeMetricToken(
          `${normalizeMetricToken(metricGroupName)}_${normalizeMetricToken(fieldName)}`
        )
        const cnName = pickI18nText(field?.i18n || field?.name)
        if (metricName && cnName) {
          labelMap[metricName] = cnName
        }
      }
    }
    return labelMap
  } catch {
    return {}
  }
}

function getMetricLabelMapForApp(app: string): Record<string, string> {
  const appName = String(app || '').trim()
  if (!appName) return {}
  const cached = metricLabelMapCache.value[appName]
  if (cached) return cached

  const tpl = templates.value.find((item) => item.app === appName)
  const labelMap = tpl?.content ? buildMetricLabelMapFromTemplate(tpl.content) : {}
  metricLabelMapCache.value = {
    ...metricLabelMapCache.value,
    [appName]: labelMap
  }
  return labelMap
}

function formatMetricDisplayName(rawMetricName: string): string {
  const metricName = String(rawMetricName || '').trim()
  if (!metricName) return '-'
  const appName = String(detailTarget.value?.app || '').trim()
  if (!appName) return metricName
  const label = getMetricLabelMapForApp(appName)[metricName]
  if (!label || label === metricName) return metricName
  return `${label} (${metricName})`
}

function normalizeList(payload: any): { items: any[]; total: number } {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: Number(payload.total) || payload.items.length }
  return { items: [], total: 0 }
}

function filterOption(input: string, option: any): boolean {
  const text = String(option?.children || '').toLowerCase()
  return text.includes(input.toLowerCase())
}

function normalizedInterval(record: MonitoringTarget): number {
  return Number(record.interval_seconds || record.interval || 0)
}

function paramLabel(param: TemplateParamDef): string {
  if (typeof param.name === 'string') return param.name
  if (param.name && typeof param.name === 'object') return param.name['zh-CN'] || param.name['en-US'] || param.field
  return param.field
}

function paramPlaceholder(param: TemplateParamDef): string {
  if (param.placeholder) return param.placeholder
  if (param.defaultValue !== undefined && param.defaultValue !== null) return `默认值: ${String(param.defaultValue)}`
  return `请输入 ${param.field}`
}

function buildCategoryTree() {
  const byCategoryId = new Map<number, CategoryTreeNode>()
  const byCategoryCode = new Map<string, CategoryTreeNode>()
  const roots: CategoryTreeNode[] = []

  for (const cat of categories.value) {
    const idNum = Number(cat.id)
    const node: CategoryTreeNode = {
      code: String(cat.code),
      name: String(cat.name || cat.code),
      nodeType: 'category',
      count: 0,
      children: []
    }
    byCategoryId.set(idNum, node)
    byCategoryCode.set(node.code, node)
  }

  for (const cat of categories.value) {
    const node = byCategoryId.get(Number(cat.id))
    if (!node) continue
    const parentId = cat.parent_id ? Number(cat.parent_id) : 0
    const parent = parentId ? byCategoryId.get(parentId) : undefined
    if (parent) {
      parent.children = parent.children || []
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  const appCountMap: Record<string, number> = {}
  for (const target of allTargets.value) {
    const app = String(target.app || '').trim()
    if (!app) continue
    appCountMap[app] = (appCountMap[app] || 0) + 1
  }

  const templateAppSeen = new Set<string>()
  for (const tpl of templates.value) {
    const app = String(tpl.app || '').trim()
    const categoryCode = String(tpl.category || '').trim()
    if (!app || templateAppSeen.has(app)) continue
    templateAppSeen.add(app)
    const parentCategory = byCategoryCode.get(categoryCode)
    if (!parentCategory) continue
    const name = typeof tpl.name === 'string'
      ? tpl.name
      : (tpl.name as any)?.['zh-CN'] || (tpl.name as any)?.['en-US'] || app

    parentCategory.children = parentCategory.children || []
    parentCategory.children.push({
      code: `tpl:${app}`,
      name: String(name || app),
      nodeType: 'template',
      app,
      count: appCountMap[app] || 0,
      children: []
    })
  }

  const sortTree = (nodes: CategoryTreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.nodeType !== b.nodeType) return a.nodeType === 'category' ? -1 : 1
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
    })
    for (const item of nodes) {
      if (item.children?.length) sortTree(item.children)
    }
  }

  const fillCount = (node: CategoryTreeNode): number => {
    if (node.nodeType === 'template') {
      node.count = Number(node.count || 0)
      return node.count
    }
    const subtotal = (node.children || []).reduce((sum, child) => sum + fillCount(child), 0)
    node.count = subtotal
    return subtotal
  }

  sortTree(roots)
  roots.forEach(fillCount)
  categoryTree.value = roots
}

function findTreeNodeByCode(nodes: CategoryTreeNode[], code: string): CategoryTreeNode | null {
  for (const node of nodes) {
    if (node.code === code) return node
    if (node.children?.length) {
      const hit = findTreeNodeByCode(node.children, code)
      if (hit) return hit
    }
  }
  return null
}

function collectApps(node: CategoryTreeNode, out: Set<string>) {
  if (node.nodeType === 'template' && node.app) {
    out.add(node.app)
  }
  for (const child of node.children || []) collectApps(child, out)
}

function resolveSelectedApps(categoryKey: string): Set<string> {
  const apps = new Set<string>()
  if (!categoryKey) return apps
  if (categoryKey.startsWith('tpl:')) {
    const app = categoryKey.slice(4)
    if (app) apps.add(app)
    return apps
  }
  const node = findTreeNodeByCode(categoryTree.value, categoryKey)
  if (!node) return apps
  collectApps(node, apps)
  return apps
}

async function loadCategories() {
  try {
    const res = await getCategories()
    categories.value = res?.data || []
    buildCategoryTree()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载分类失败')
  }
}

async function loadTemplates(force = false) {
  if (templates.value.length && !force) return
  templatesLoading.value = true
  try {
    const res = await getTemplates()
    templates.value = Array.isArray(res?.data) ? res.data : []
    metricLabelMapCache.value = {}
  } catch {
    templates.value = []
    metricLabelMapCache.value = {}
  } finally {
    templatesLoading.value = false
    buildCategoryTree()
  }
}

async function reloadCategoryMenu() {
  await Promise.all([loadTemplates(true), loadCategories()])
  buildCategoryTree()
}

async function loadModels() {
  if (modelOptions.value.length) return
  modelsLoading.value = true
  try {
    const res = await getModels({ page: 1, per_page: 1000 })
    const parsed = normalizeList(res?.data)
    modelOptions.value = parsed.items.map((item: any) => ({
      id: Number(item.id),
      name: String(item.name || item.code || item.id),
      code: String(item.code || item.id)
    }))
  } catch {
    modelOptions.value = []
  } finally {
    modelsLoading.value = false
  }
}

async function loadCiOptions(modelId?: number) {
  if (!modelId) {
    ciOptions.value = []
    return
  }
  ciLoading.value = true
  try {
    const res = await getInstances({ model_id: modelId, page: 1, per_page: 500 })
    const parsed = normalizeList(res?.data)
    ciOptions.value = parsed.items.map((item: any) => {
      const attrs = item.attributes && typeof item.attributes === 'object' ? item.attributes : {}
      const short = attrs.ip || attrs.host || attrs.hostname || attrs.name || ''
      return {
        id: Number(item.id),
        code: String(item.code || item.id),
        display: `${item.code || item.id}${short ? ` (${short})` : ''}`,
        attributes: attrs
      }
    })
  } catch {
    ciOptions.value = []
  } finally {
    ciLoading.value = false
  }
}

async function loadCollectors() {
  collectorsLoading.value = true
  try {
    const res = await getCollectors({ status: 'online' })
    const parsed = normalizeList(res?.data)
    collectors.value = parsed.items.map((item: any) => ({
      id: String(item.id),
      name: item.name,
      host: item.host || item.ip,
      status: item.status
    }))
  } catch {
    collectors.value = []
  } finally {
    collectorsLoading.value = false
  }
}

function filterAndPaginateTargets() {
  let filtered = [...allTargets.value]

  if (selectedCategory.value) {
    const apps = resolveSelectedApps(selectedCategory.value)
    filtered = filtered.filter((t) => t.app && apps.has(t.app))
  }

  if (keyword.value) {
    const q = keyword.value.toLowerCase()
    filtered = filtered.filter((t) => {
      const text = [t.name, t.target, t.app, t.ci_code, t.ci_name, t.job_id].join(' ').toLowerCase()
      return text.includes(q)
    })
  }

  if (status.value) {
    const enabled = status.value === 'enabled'
    filtered = filtered.filter((t) => (t.enabled !== false) === enabled)
  }

  pagination.total = filtered.length
  const start = (pagination.current - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  targets.value = filtered.slice(start, end)

  buildCategoryTree()
  selectedRowKeys.value = selectedRowKeys.value.filter((id) => targets.value.some((item) => item.id === id))
}

async function loadTargets() {
  loading.value = true
  try {
    await loadTemplates()
    const res = await getMonitoringTargets({
      q: keyword.value || undefined,
      status: status.value || undefined,
      page: 1,
      page_size: 10000
    })
    const parsed = normalizeList(res?.data)
    allTargets.value = parsed.items
    filterAndPaginateTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载监控目标失败')
  } finally {
    loading.value = false
  }
}

function handleCategorySelect(keys: string[]) {
  selectedCategory.value = keys[0] || null
  pagination.current = 1
  filterAndPaginateTargets()
}

function clearCategoryFilter() {
  selectedCategory.value = null
  pagination.current = 1
  filterAndPaginateTargets()
}

function resetForm() {
  formState.name = ''
  formState.app = ''
  formState.target = ''
  formState.interval = 60
  formState.enabled = true
  formState.ci_model_id = undefined
  formState.ci_id = undefined
  formState.collector_id = undefined
  formState.pin_collector = false
  formState.params = {}
  ciOptions.value = []
}

function applyTemplateDefaults() {
  const params = { ...(formState.params || {}) }
  for (const param of visibleParamDefs.value) {
    if (params[param.field] === undefined || params[param.field] === null || params[param.field] === '') {
      if (param.defaultValue !== undefined && param.defaultValue !== null) {
        params[param.field] = String(param.defaultValue)
      }
    }
  }
  formState.params = params
}

function handleTemplateChange() {
  applyTemplateDefaults()
}

async function openModal(record?: MonitoringTarget) {
  await Promise.all([loadTemplates(), loadCollectors(), loadModels()])
  editing.value = record || null
  resetForm()

  if (record) {
    syncingFormFromRecord.value = true
    formState.name = record.name || ''
    formState.app = record.app || ''
    formState.target = record.target || record.endpoint || ''
    formState.interval = Number(record.interval_seconds || record.interval || 60)
    formState.enabled = record.enabled !== false
    formState.ci_model_id = record.ci_model_id || undefined
    formState.ci_id = record.ci_id || undefined
    formState.params = { ...(record.params || {}) }

    if (formState.ci_model_id) {
      await loadCiOptions(formState.ci_model_id)
    }
    applyTemplateDefaults()
    syncingFormFromRecord.value = false
  }

  modalOpen.value = true
}

async function saveTarget() {
  if (!formState.name.trim()) {
    message.warning('请填写任务名称')
    return
  }
  if (!formState.app) {
    message.warning('请选择监控模板')
    return
  }
  if (!formState.ci_model_id || !formState.ci_id) {
    message.warning('请选择模型和CI实例')
    return
  }
  if (!formState.interval || formState.interval < 10) {
    message.warning('采集间隔最小为10秒')
    return
  }

  const template = selectedTemplate.value
  if (!template?.id) {
    message.warning('模板缺少ID，请检查模板配置')
    return
  }

  const currentCi = ciOptions.value.find((item) => item.id === formState.ci_id)
  const paramsPayload: Record<string, string> = {}
  Object.entries(formState.params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || String(value).trim() === '') return
    paramsPayload[key] = String(value)
  })

  const payload: Partial<MonitoringTarget> & Record<string, any> = {
    name: formState.name.trim(),
    app: formState.app,
    template_id: template.id,
    interval: Number(formState.interval),
    interval_seconds: Number(formState.interval),
    enabled: formState.enabled,
    ci_model_id: formState.ci_model_id,
    ci_id: formState.ci_id,
    ci_code: currentCi?.code || '',
    ci_name: currentCi?.display || '',
    params: paramsPayload
  }
  let resolvedTarget = formState.target.trim()
  if (!resolvedTarget && paramsPayload.host) {
    resolvedTarget = `${paramsPayload.host}:${paramsPayload.port || '6379'}`
  }
  if (!resolvedTarget && editing.value) {
    resolvedTarget = String(editing.value.target || editing.value.endpoint || '').trim()
  }
  if (!resolvedTarget && currentCi?.code) {
    resolvedTarget = `ci:${currentCi.code}`
  }
  payload.target = resolvedTarget

  saving.value = true
  try {
    let monitorId = 0
    if (editing.value?.id) {
      await updateMonitoringTarget(editing.value.id, { ...payload, version: editing.value.version })
      monitorId = editing.value.id
    } else {
      const res = await createMonitoringTarget(payload)
      monitorId = Number(res?.data?.id || res?.data?.monitor_id || 0)
    }

    if (monitorId > 0) {
      if (formState.collector_id && formState.pin_collector) {
        await assignCollectorToMonitor(monitorId, formState.collector_id, true)
      } else if (editing.value?.id) {
        await unassignCollectorFromMonitor(editing.value.id)
      }
    }

    message.success('保存成功')
    modalOpen.value = false
    await loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleTarget(record: MonitoringTarget, checked: boolean) {
  try {
    if (checked) {
      await enableMonitoringTarget(record.id, { version: record.version })
    } else {
      await disableMonitoringTarget(record.id, { version: record.version })
    }
    message.success('操作成功')
    await loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
    await loadTargets()
  }
}

async function removeTarget(record: MonitoringTarget) {
  try {
    await deleteMonitoringTarget(record.id, record.version)
    message.success('删除成功')
    if (targets.value.length === 1 && pagination.current > 1) pagination.current -= 1
    await loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

async function batchDelete() {
  if (!selectedRowKeys.value.length) return
  try {
    for (const id of selectedRowKeys.value) {
      const item = targets.value.find((t) => t.id === id)
      await deleteMonitoringTarget(id, item?.version)
    }
    selectedRowKeys.value = []
    message.success('批量删除成功')
    await loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量删除失败')
  }
}

async function batchUpdateInterval() {
  if (!selectedRowKeys.value.length) return
  if (!batchInterval.value || batchInterval.value < 10) {
    message.warning('采集间隔最小为10秒')
    return
  }
  try {
    for (const id of selectedRowKeys.value) {
      const item = targets.value.find((t) => t.id === id)
      if (!item) continue
      await updateMonitoringTarget(id, {
        name: item.name,
        app: item.app,
        target: item.target || item.endpoint,
        template_id: item.template_id,
        interval: batchInterval.value,
        interval_seconds: batchInterval.value,
        enabled: item.enabled !== false,
        ci_model_id: item.ci_model_id,
        ci_id: item.ci_id,
        ci_code: item.ci_code,
        ci_name: item.ci_name,
        params: item.params || {},
        version: item.version
      })
    }
    message.success('批量修改成功')
    await loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量修改失败')
  }
}

function handleTableChange(pager: any) {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  filterAndPaginateTargets()
}

function reset() {
  keyword.value = ''
  status.value = undefined
  selectedCategory.value = null
  pagination.current = 1
  selectedRowKeys.value = []
  filterAndPaginateTargets()
}

function resolveMetricRange() {
  const now = dayjs()
  if (metricRangePreset.value === 'custom' && metricCustomRange.value) {
    return {
      from: metricCustomRange.value[0].unix(),
      to: metricCustomRange.value[1].unix(),
      seconds: metricCustomRange.value[1].diff(metricCustomRange.value[0], 'second')
    }
  }

  const map: Record<string, number> = {
    '5m': 5 * 60,
    '1h': 60 * 60,
    '24h': 24 * 60 * 60,
    '7d': 7 * 24 * 60 * 60,
    '30d': 30 * 24 * 60 * 60
  }
  const delta = map[metricRangePreset.value] || map['1h']
  return {
    from: now.subtract(delta, 'second').unix(),
    to: now.unix(),
    seconds: delta
  }
}

function resolveQueryStep(rangeSeconds: number): number {
  if (metricStepSeconds.value > 0) return metricStepSeconds.value
  if (rangeSeconds <= 10 * 60) return 10
  if (rangeSeconds <= 60 * 60) return 30
  if (rangeSeconds <= 6 * 60 * 60) return 60
  if (rangeSeconds <= 24 * 60 * 60) return 300
  if (rangeSeconds <= 7 * 24 * 60 * 60) return 900
  return 3600
}

async function loadMetricNameOptions() {
  if (!detailTarget.value?.id) return
  const range = resolveMetricRange()
  const res = await getTargetMetricSeries(detailTarget.value.id, {
    from: range.from,
    to: range.to
  })
  const parsed = normalizeList(res?.data)
  const names = Array.from(new Set(parsed.items.map((item: any) => String(item.__name__ || '')).filter(Boolean))).sort()
  metricNameOptions.value = names
  if (!selectedMetricNames.value.length) {
    selectedMetricNames.value = names.slice(0, Math.min(names.length, 8))
  } else {
    selectedMetricNames.value = selectedMetricNames.value.filter((name) => names.includes(name))
    if (!selectedMetricNames.value.length) selectedMetricNames.value = names.slice(0, Math.min(names.length, 8))
  }
}

async function refreshMetricData() {
  if (!detailTarget.value?.id) return
  if (detailTab.value !== 'metrics') return
  metricLoading.value = true
  try {
    if (!metricNameOptions.value.length) {
      await loadMetricNameOptions()
    }
    if (!selectedMetricNames.value.length) {
      metricSeries.value = []
      return
    }

    const range = resolveMetricRange()
    const step = resolveQueryStep(range.seconds)
    const res = await queryTargetMetricRange(detailTarget.value.id, {
      names: selectedMetricNames.value.join(','),
      from: range.from,
      to: range.to,
      step
    })

    const parsed = normalizeList(res?.data)
    metricSeries.value = parsed.items.map((item: any) => ({
      name: String(item.name || item.labels?.__name__ || 'unknown'),
      labels: item.labels || {},
      points: (Array.isArray(item.points) ? item.points : []).map((pt: any) => ({
        timestamp: Number(pt.timestamp),
        value: Number(pt.value)
      })).filter((pt: MetricRangePoint) => Number.isFinite(pt.timestamp) && Number.isFinite(pt.value))
    }))
    metricLastLoadedAt.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载指标失败')
  } finally {
    metricLoading.value = false
  }
}

function clearMetricTimer() {
  if (metricTimer) {
    window.clearInterval(metricTimer)
    metricTimer = undefined
  }
}

function setupMetricTimer() {
  clearMetricTimer()
  if (!detailOpen.value || detailTab.value !== 'metrics' || !metricAutoRefresh.value) return
  metricTimer = window.setInterval(() => {
    refreshMetricData()
  }, Math.max(metricRefreshSeconds.value, 10) * 1000)
}

function resetMetricState() {
  metricRangePreset.value = '1h'
  metricCustomRange.value = null
  metricStepSeconds.value = 0
  metricAutoRefresh.value = true
  metricRefreshSeconds.value = 60
  metricNameOptions.value = []
  selectedMetricNames.value = []
  metricSeries.value = []
  metricLastLoadedAt.value = ''
}

function openDetail(record: MonitoringTarget) {
  detailTarget.value = record
  detailOpen.value = true
  detailTab.value = 'basic'
  resetMetricState()
}

function closeDetail() {
  clearMetricTimer()
  detailTarget.value = null
}

function handleRangePresetChange(value: string | number) {
  metricRangePreset.value = value as '5m' | '1h' | '24h' | '7d' | '30d' | 'custom'
  if (metricRangePreset.value !== 'custom') {
    metricCustomRange.value = null
  }
  refreshMetricData()
}

function handleCustomRangeChange(value: [Dayjs, Dayjs] | null) {
  metricCustomRange.value = value
  if (value && value[0] && value[1]) {
    metricRangePreset.value = 'custom'
    refreshMetricData()
  }
}

function buildPolyline(points: MetricRangePoint[]): string {
  if (!points.length) return ''
  const width = 640
  const height = 220
  const left = 24
  const right = 20
  const top = 20
  const bottom = 24
  const innerW = width - left - right
  const innerH = height - top - bottom

  const sorted = [...points].sort((a, b) => a.timestamp - b.timestamp)
  const minTs = sorted[0].timestamp
  const maxTs = sorted[sorted.length - 1].timestamp
  const tsRange = Math.max(maxTs - minTs, 1)

  const values = sorted.map((p) => p.value)
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const valRange = Math.max(maxVal - minVal, 1)

  return sorted
    .map((p) => {
      const x = left + ((p.timestamp - minTs) / tsRange) * innerW
      const y = top + (1 - (p.value - minVal) / valRange) * innerH
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

function formatMetricValue(value: number): string {
  if (!Number.isFinite(value)) return '-'
  if (Math.abs(value) >= 1000 || Math.abs(value) < 0.01) return value.toExponential(3)
  return value.toFixed(3)
}

watch(
  () => formState.ci_model_id,
  async (modelId) => {
    if (syncingFormFromRecord.value) return
    formState.ci_id = undefined
    await loadCiOptions(modelId)
  }
)

watch(
  () => detailTab.value,
  async (tab) => {
    if (tab === 'metrics') {
      await refreshMetricData()
      setupMetricTimer()
    } else {
      clearMetricTimer()
    }
  }
)

watch(
  () => [metricAutoRefresh.value, metricRefreshSeconds.value, detailOpen.value, detailTab.value],
  () => {
    setupMetricTimer()
  }
)

onMounted(async () => {
  await reloadCategoryMenu()
  await loadTargets()
})

onUnmounted(() => {
  clearMetricTimer()
})
</script>

<style scoped>
.monitor-target-layout {
  display: flex;
  gap: 16px;
  min-height: calc(100vh - 180px);
}

.category-sidebar {
  width: 260px;
  flex-shrink: 0;
}

.category-card {
  height: 100%;
}

.category-card :deep(.ant-card-body) {
  padding: 12px;
  max-height: calc(100vh - 240px);
  overflow-y: auto;
}

.category-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

.category-name {
  flex: 1;
}

.category-count {
  color: #999;
  font-size: 12px;
}

.target-content {
  flex: 1;
  min-width: 0;
}

.current-category {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.ci-cell .sub-text,
.sub-text {
  color: #8c8c8c;
  font-size: 12px;
}

.metric-chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 12px;
}

.metric-chart-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}

.metric-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.metric-title {
  font-weight: 600;
  color: #1f1f1f;
  max-width: 60%;
  word-break: break-all;
}

.metric-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  color: #595959;
  font-size: 12px;
}

.metric-svg {
  width: 100%;
  height: 180px;
  border-radius: 6px;
  display: block;
}

.metric-axis-text {
  display: flex;
  justify-content: space-between;
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 6px;
}

:deep(.ant-tree-node-content-wrapper) {
  width: calc(100% - 24px);
}

:deep(.ant-tree-title) {
  width: 100%;
}
</style>
