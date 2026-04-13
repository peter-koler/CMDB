<template>
  <div class="app-page monitoring-target-form-page">
    <div class="app-page__header monitoring-target-form-page__header">
      <div>
        <a-space>
          <a-button @click="goBack">返回</a-button>
          <div>
            <div class="monitoring-target-form-page__title">{{ pageTitle }}</div>
            <div class="monitoring-target-form-page__subtitle">{{ pageSubtitle }}</div>
          </div>
        </a-space>
      </div>
      <div class="app-toolbar">
        <a-space>
          <a-button @click="goBack">取消</a-button>
          <a-button type="primary" :loading="saving" @click="saveTarget">保存</a-button>
        </a-space>
      </div>
    </div>

    <a-card :bordered="false" class="app-surface-card">
      <a-spin :spinning="loading">
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="[16, 0]">
          <a-col :xs="24" :md="12">
            <a-form-item label="任务名称" required>
              <a-input v-model:value="formState.name" placeholder="请输入监控任务名称" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="采集间隔(秒)" required>
              <a-input-number v-model:value="formState.interval" :min="10" :step="10" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="[16, 0]">
          <a-col :xs="24" :md="12">
            <a-form-item label="CI模型" required>
              <a-select
                v-model:value="formState.ci_model_id"
                placeholder="请选择CI模型"
                :loading="modelsLoading"
                show-search
                :filter-option="filterOption"
                @focus="loadModels"
                @change="handleCiModelChange"
              >
                <a-select-option v-for="m in modelOptions" :key="m.id" :value="m.id">
                  {{ m.name }} ({{ m.code }})
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col :xs="24" :md="12">
            <a-form-item label="CI实例" required>
              <div class="monitoring-target-form-page__ci-picker">
                <a-input
                  :value="selectedCiDisplay"
                  :placeholder="formState.ci_model_id ? '请选择 CI 实例' : '请先选择 CI 模型'"
                  readonly
                />
                <a-button :disabled="!formState.ci_model_id" @click="openCiSelector">
                  {{ formState.ci_id ? '更换CI实例' : '选择CI实例' }}
                </a-button>
              </div>
              <div v-if="selectedCiDisplay" class="monitoring-target-form-page__hint">
                已选择 {{ selectedCiDisplay }}
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="[16, 0]">
          <a-col :xs="24" :md="12">
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
                <a-select-option v-for="t in availableTemplates" :key="t.app" :value="t.app">
                  {{ t.name }} ({{ t.app }})
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <a-col v-if="showManualTargetField" :xs="24" :md="12">
            <a-form-item label="目标地址(target)">
              <a-input v-model:value="formState.target" placeholder="可留空，默认由 params host/port 生成" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">必填参数</a-divider>
        <a-row v-if="requiredParamDefs.length" :gutter="[12, 0]">
          <a-col
            v-for="param in requiredParamDefs"
            :key="param.field"
            :xs="24"
            :md="12"
          >
            <a-form-item :label="paramLabel(param)" :required="Boolean(param.required)">
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
              <a-select
                v-else-if="hasParamOptions(param)"
                v-model:value="formState.params[param.field]"
                style="width: 100%"
                :placeholder="paramPlaceholder(param)"
              >
                <a-select-option v-for="opt in paramOptions(param)" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-select-option>
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
        <a-empty v-else description="当前模板无必填参数" />

        <a-divider v-if="optionalParamDefs.length" orientation="left">非必填参数</a-divider>
        <a-collapse v-if="optionalParamDefs.length" v-model:activeKey="optionalParamsActiveKeys" ghost>
          <a-collapse-panel key="optional" header="展开配置非必填参数">
            <a-row :gutter="[12, 0]">
              <a-col
                v-for="param in optionalParamDefs"
                :key="param.field"
                :xs="24"
                :md="12"
              >
                <a-form-item :label="paramLabel(param)">
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
                  <a-select
                    v-else-if="hasParamOptions(param)"
                    v-model:value="formState.params[param.field]"
                    style="width: 100%"
                    :placeholder="paramPlaceholder(param)"
                  >
                    <a-select-option v-for="opt in paramOptions(param)" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </a-select-option>
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
          </a-collapse-panel>
        </a-collapse>

        <a-divider orientation="left">采集与策略</a-divider>
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

        <a-form-item v-if="!isEditMode" label="告警策略">
          <a-space direction="vertical" style="width: 100%" :size="4">
            <a-checkbox v-model:checked="formState.apply_default_alerts">
              创建后自动应用模板默认告警策略
            </a-checkbox>
            <span class="monitoring-target-form-page__hint">当前默认策略可在任务详情页“告警”标签继续调整。</span>
          </a-space>
        </a-form-item>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enabled" />
        </a-form-item>
      </a-form>
      </a-spin>
    </a-card>

    <a-modal
      v-model:open="ciSelectorVisible"
      title="选择 CI 实例"
      width="1120px"
      :mask-closable="false"
      :destroy-on-close="false"
      @cancel="closeCiSelector"
    >
      <a-spin :spinning="ciSelectorLoading">
        <a-form layout="vertical">
          <a-row :gutter="[16, 0]">
            <a-col v-for="fieldCode in selectorSearchFieldCodes" :key="fieldCode" :xs="24" :md="8">
              <a-form-item :label="selectedModel?.fieldLabelMap[fieldCode] || fieldCode">
                <a-input
                  v-model:value="ciSelectorSearch[fieldCode]"
                  :placeholder="`请输入${selectedModel?.fieldLabelMap[fieldCode] || fieldCode}`"
                  @pressEnter="handleCiSelectorSearch"
                />
              </a-form-item>
            </a-col>
          </a-row>

          <div class="monitoring-target-form-page__selector-actions">
            <a-space wrap>
              <a-button type="primary" @click="handleCiSelectorSearch">搜索</a-button>
              <a-button @click="handleCiSelectorReset">重置搜索条件</a-button>
            </a-space>
            <a-button @click="handleCiSelectorListAll">列出全部</a-button>
          </div>
        </a-form>

        <a-alert
          :message="ciSelectorScope === 'all' ? '当前展示该模型全部 CI 实例。' : '当前默认展示未纳入监控的 CI 实例。'"
          type="info"
          show-icon
          class="monitoring-target-form-page__selector-alert"
        />

        <a-table
          row-key="id"
          :columns="ciSelectorColumns"
          :data-source="ciSelectorRows"
          :pagination="ciSelectorPagination"
          :loading="ciSelectorLoading"
          :row-selection="ciSelectorRowSelection"
          :scroll="{ x: 1080 }"
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'index'">
              {{ (ciSelectorPager.page - 1) * ciSelectorPager.perPage + index + 1 }}
            </template>
            <template v-else-if="column.key === 'monitored'">
              <a-tag :color="record.monitored ? 'orange' : 'green'">
                {{ record.monitored ? '已监控' : '未监控' }}
              </a-tag>
            </template>
            <template v-else-if="String(column.key).startsWith('key:')">
              {{ formatCiAttribute(record.attributes, String(column.key).slice(4)) }}
            </template>
            <template v-else-if="String(column.key).startsWith('extra:')">
              {{ formatCiAttribute(record.attributes, String(column.key).slice(6)) }}
            </template>
            <template v-else-if="column.key === 'ciid'">
              {{ record.id }}
            </template>
          </template>
        </a-table>
      </a-spin>

      <template #footer>
        <a-space>
          <a-button @click="closeCiSelector">取消</a-button>
          <a-button type="primary" :disabled="!ciSelectorSelectedRow" @click="confirmCiSelection">确定</a-button>
        </a-space>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import * as yaml from 'js-yaml'
import {
  assignCollectorToMonitor,
  createMonitoringTarget,
  getCategories,
  getCollectors,
  getMonitoringTarget,
  getTemplates,
  unassignCollectorFromMonitor,
  updateMonitoringTarget,
  type MonitorCategory,
  type MonitoringTarget,
  type MonitorTemplate
} from '@/api/monitoring'
import { getModels } from '@/api/cmdb'
import { getMonitoringTargetCiOptions } from '@/api/ci'
import {
  buildCiSelectionValue,
  createModelOption,
  getMonitoringTargetDraftKey,
  readMonitoringTargetDraft,
  removeMonitoringTargetDraft,
  writeMonitoringTargetDraft,
  type ModelOption
} from './form-helpers'

interface TemplateParamDef {
  field: string
  name?: Record<string, string> | string
  type?: string
  options?: Array<{ label?: string; value?: string | number | boolean }>
  required?: boolean
  defaultValue?: string | number | boolean
  placeholder?: string
  hide?: boolean
  persist?: boolean | string
}

interface ParsedTemplate {
  params: TemplateParamDef[]
  protocols: string[]
}

interface CategoryTreeNode {
  code: string
  name: string
  nodeType: 'category' | 'template'
  app?: string
  children?: CategoryTreeNode[]
}

interface CiSelectorRow {
  id: number
  code: string
  attributes: Record<string, any>
  monitored: boolean
  monitor_count: number
  monitor_names: string[]
}

const route = useRoute()
const router = useRouter()

const templates = ref<MonitorTemplate[]>([])
const templatesLoading = ref(false)
const categories = ref<MonitorCategory[]>([])
const saving = ref(false)
const loading = ref(false)
const modelsLoading = ref(false)
const collectorsLoading = ref(false)
const modelOptions = ref<ModelOption[]>([])
const collectors = ref<Array<{ id: string; name?: string; host?: string; status?: string }>>([])
const optionalParamsActiveKeys = ref<string[]>([])
const syncingFormFromRecord = ref(false)
const editing = ref<MonitoringTarget | null>(null)
const ciSelectorVisible = ref(false)
const ciSelectorLoading = ref(false)
const ciSelectorRows = ref<CiSelectorRow[]>([])
const ciSelectorSelectedRow = ref<CiSelectorRow | null>(null)
const ciSelectorSelectedKeys = ref<number[]>([])
const ciSelectorScope = ref<'unmonitored' | 'all'>('unmonitored')
const ciSelectorPager = reactive({
  page: 1,
  perPage: 10,
  total: 0
})
const ciSelectorSearch = reactive<Record<string, string>>({})

const formState = reactive({
  name: '',
  app: '',
  target: '',
  interval: 60,
  enabled: true,
  ci_model_id: undefined as number | undefined,
  ci_id: undefined as number | undefined,
  ci_code: '',
  ci_display: '',
  ci_attributes: {} as Record<string, any>,
  collector_id: undefined as string | undefined,
  pin_collector: false,
  apply_default_alerts: true,
  params: {} as Record<string, any>
})

const monitorId = computed(() => Number(route.params.id || 0))
const isEditMode = computed(() => monitorId.value > 0)
const categoryContext = computed(() => String(route.query.category || '').trim())
const draftKey = computed(() => getMonitoringTargetDraftKey(isEditMode.value ? 'edit' : 'create', monitorId.value, categoryContext.value))

const parsedTemplateMap = computed<Record<string, ParsedTemplate>>(() => {
  const out: Record<string, ParsedTemplate> = {}
  templates.value.forEach((tpl) => {
    out[tpl.app] = parseTemplateContent(tpl.content)
  })
  return out
})

const categoryTree = computed<CategoryTreeNode[]>(() => {
  const byCode = new Map<string, CategoryTreeNode>()
  const roots: CategoryTreeNode[] = []
  for (const cat of categories.value) {
    const node: CategoryTreeNode = { code: String(cat.code), name: String(cat.name || cat.code), nodeType: 'category', children: [] }
    byCode.set(node.code, node)
  }
  for (const cat of categories.value) {
    const node = byCode.get(String(cat.code))
    if (!node) continue
    const parentCode = categories.value.find((item) => Number(item.id) === Number(cat.parent_id))?.code
    const parent = parentCode ? byCode.get(String(parentCode)) : undefined
    if (parent) {
      parent.children?.push(node)
    } else {
      roots.push(node)
    }
  }
  for (const tpl of templates.value) {
    const parent = byCode.get(String(tpl.category || ''))
    if (!parent || !tpl.app) continue
    parent.children?.push({
      code: `tpl:${tpl.app}`,
      name: String(tpl.name || tpl.app),
      nodeType: 'template',
      app: tpl.app
    })
  }
  return roots
})

const selectedTemplate = computed(() => templates.value.find((item) => item.app === formState.app))
const selectedTemplateProtocols = computed(() => parsedTemplateMap.value[formState.app]?.protocols || [])
const allParamDefs = computed(() => parsedTemplateMap.value[formState.app]?.params.filter((item) => item && item.field) || [])
const requiredParamDefs = computed(() => allParamDefs.value.filter((item) => isParamRequired(item)))
const optionalParamDefs = computed(() => allParamDefs.value.filter((item) => !isParamRequired(item)))
const showManualTargetField = computed(() => selectedTemplateProtocols.value.includes('http'))
const availableTemplates = computed(() => {
  if (isEditMode.value || !categoryContext.value) return templates.value
  const apps = resolveSelectedApps(categoryContext.value)
  if (!apps.size) return templates.value
  return templates.value.filter((item) => item.app && apps.has(item.app))
})
const categoryContextName = computed(() => resolveCategoryContextName(categoryContext.value))
const selectedModel = computed(() => modelOptions.value.find((item) => item.id === Number(formState.ci_model_id)))
const selectedCiDisplay = computed(() => formState.ci_display || '')
const selectorSearchFieldCodes = computed(() => selectedModel.value?.keyFieldCodes?.length ? selectedModel.value.keyFieldCodes : ['name', 'ip'])
const selectorExtraFieldCodes = computed(() => {
  const model = selectedModel.value
  if (!model) return []
  return model.orderedFieldCodes.filter((code) => !model.keyFieldCodes.includes(code)).slice(0, 2)
})
const ciSelectorColumns = computed(() => {
  const columns: Array<Record<string, any>> = [
    { title: '序号', key: 'index', width: 72, fixed: 'left' }
  ]
  selectorSearchFieldCodes.value.forEach((fieldCode) => {
    columns.push({
      title: selectedModel.value?.fieldLabelMap[fieldCode] || fieldCode,
      key: `key:${fieldCode}`,
      width: 180
    })
  })
  columns.push({ title: '是否监控', key: 'monitored', width: 120 })
  selectorExtraFieldCodes.value.forEach((fieldCode) => {
    columns.push({
      title: selectedModel.value?.fieldLabelMap[fieldCode] || fieldCode,
      key: `extra:${fieldCode}`,
      width: 180
    })
  })
  columns.push({ title: 'CIID', key: 'ciid', width: 120 })
  return columns
})
const ciSelectorRowSelection = computed(() => ({
  type: 'radio' as const,
  selectedRowKeys: ciSelectorSelectedKeys.value,
  onChange: (keys: Array<string | number>, rows: CiSelectorRow[]) => {
    ciSelectorSelectedKeys.value = keys.map((item) => Number(item))
    ciSelectorSelectedRow.value = rows[0] || null
  }
}))
const ciSelectorPagination = computed(() => ({
  current: ciSelectorPager.page,
  pageSize: ciSelectorPager.perPage,
  total: ciSelectorPager.total,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (total: number) => `共 ${total} 条`,
  onChange: (page: number, pageSize: number) => {
    ciSelectorPager.page = page
    ciSelectorPager.perPage = pageSize
    void fetchCiSelectorRows()
  },
  onShowSizeChange: (page: number, pageSize: number) => {
    ciSelectorPager.page = page
    ciSelectorPager.perPage = pageSize
    void fetchCiSelectorRows()
  }
}))
const pageTitle = computed(() => {
  if (isEditMode.value) return '编辑监控任务'
  if (categoryContextName.value) return `新增监控任务 · ${categoryContextName.value}`
  return '新增监控任务'
})
const pageSubtitle = computed(() => (isEditMode.value ? '在当前壳层内完成任务配置与参数调整。' : '使用统一表单页面创建监控任务，并保留当前导航上下文。'))

function parseTemplateContent(content: string): ParsedTemplate {
  try {
    const sanitizedContent = String(content || '').replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
    const parsed = (yaml.load(sanitizedContent) || {}) as any
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
    const protocols = Array.isArray(parsed?.metrics)
      ? parsed.metrics.map((item: any) => String(item?.protocol || '').trim().toLowerCase()).filter(Boolean)
      : []
    return { params: deduped, protocols: Array.from(new Set(protocols)) }
  } catch {
    return { params: [], protocols: [] }
  }
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

function isParamRequired(param: TemplateParamDef): boolean {
  const raw = param?.required
  if (typeof raw === 'boolean') return raw
  const text = String(raw ?? '').trim().toLowerCase()
  return text === 'true' || text === '1' || text === 'yes' || text === 'on'
}

function isParamPersistable(param: TemplateParamDef): boolean {
  const raw = param?.persist
  if (typeof raw === 'boolean') return raw
  const text = String(raw ?? '').trim().toLowerCase()
  if (!text) return true
  return !(text === 'false' || text === '0' || text === 'no' || text === 'off')
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

function hasParamOptions(param: TemplateParamDef): boolean {
  return Array.isArray(param?.options) && param.options.length > 0
}

function paramOptions(param: TemplateParamDef): Array<{ label: string; value: string }> {
  if (!Array.isArray(param?.options)) return []
  return param.options
    .map((item) => {
      const value = String(item?.value ?? '').trim()
      if (!value) return null
      const label = String(item?.label ?? value).trim() || value
      return { label, value }
    })
    .filter((item): item is { label: string; value: string } => Boolean(item))
}

function formatCiAttribute(attributes: Record<string, any>, fieldCode: string) {
  const value = attributes?.[fieldCode]
  if (value === undefined || value === null || String(value).trim() === '') return '-'
  return String(value)
}

function resetForm() {
  formState.name = ''
  formState.app = ''
  formState.target = ''
  formState.interval = 60
  formState.enabled = true
  formState.ci_model_id = undefined
  formState.ci_id = undefined
  formState.ci_code = ''
  formState.ci_display = ''
  formState.ci_attributes = {}
  formState.collector_id = undefined
  formState.pin_collector = false
  formState.apply_default_alerts = true
  formState.params = {}
  optionalParamsActiveKeys.value = []
}

function applyTemplateDefaults() {
  const params = { ...(formState.params || {}) }
  for (const param of allParamDefs.value) {
    if (params[param.field] === undefined || params[param.field] === null || params[param.field] === '') {
      if (param.defaultValue !== undefined && param.defaultValue !== null) {
        params[param.field] = String(param.defaultValue)
      }
    }
  }
  formState.params = params
}

function handleTemplateChange() {
  optionalParamsActiveKeys.value = []
  if (!showManualTargetField.value) formState.target = ''
  applyTemplateDefaults()
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
  if (node.nodeType === 'template' && node.app) out.add(node.app)
  for (const child of node.children || []) collectApps(child, out)
}

function resolveSelectedApps(code: string): Set<string> {
  const apps = new Set<string>()
  if (!code) return apps
  if (code.startsWith('tpl:')) {
    const app = code.slice(4)
    if (app) apps.add(app)
    return apps
  }
  const node = findTreeNodeByCode(categoryTree.value, code)
  if (!node) return apps
  collectApps(node, apps)
  return apps
}

function resolveCategoryContextName(code: string): string {
  if (!code) return ''
  const walk = (nodes: CategoryTreeNode[], parentCategoryName = ''): string => {
    for (const node of nodes) {
      const currentCategory = node.nodeType === 'category' ? node.name : parentCategoryName
      if (node.code === code) {
        return node.nodeType === 'category' ? node.name : parentCategoryName
      }
      if (node.children?.length) {
        const hit = walk(node.children, currentCategory)
        if (hit) return hit
      }
    }
    return ''
  }
  return walk(categoryTree.value)
}

function applyDefaultTemplateByCategory(code: string) {
  if (!code) return
  if (code.startsWith('tpl:')) {
    const app = code.slice(4)
    if (app && templates.value.some((tpl) => tpl.app === app)) {
      formState.app = app
      applyTemplateDefaults()
    }
    return
  }
  const apps = resolveSelectedApps(code)
  const hit = templates.value.find((tpl) => tpl.app && apps.has(tpl.app))
  if (hit?.app) {
    formState.app = hit.app
    applyTemplateDefaults()
  }
}

async function loadTemplates(force = false) {
  if (templates.value.length && !force) return
  templatesLoading.value = true
  try {
    const res = await getTemplates()
    templates.value = Array.isArray(res?.data) ? res.data : []
  } catch {
    templates.value = []
  } finally {
    templatesLoading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await getCategories()
    categories.value = res?.data || []
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载分类失败')
  }
}

async function loadModels() {
  if (modelOptions.value.length) return
  modelsLoading.value = true
  try {
    const res = await getModels({ page: 1, per_page: 1000 })
    const parsed = normalizeList(res?.data)
    modelOptions.value = parsed.items.map((item: any) => createModelOption(item))
  } catch {
    modelOptions.value = []
  } finally {
    modelsLoading.value = false
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

async function loadEditingTarget() {
  if (!isEditMode.value) return
  loading.value = true
  try {
    const res = await getMonitoringTarget(monitorId.value)
    const record = (res as any)?.data as MonitoringTarget | null
    if (!record) {
      message.warning('监控任务不存在')
      goBack()
      return
    }
    editing.value = record
    syncingFormFromRecord.value = true
    resetForm()
    formState.name = record.name || ''
    formState.app = record.app || ''
    formState.target = record.target || record.endpoint || ''
    formState.interval = Number(record.interval_seconds || record.interval || 60)
    formState.enabled = record.enabled !== false
    formState.ci_model_id = record.ci_model_id || undefined
    formState.ci_id = record.ci_id || undefined
    formState.ci_code = record.ci_code || ''
    formState.ci_display = record.ci_name || ''
    formState.ci_attributes = {}
    formState.params = { ...(record.params || {}) }
    applyTemplateDefaults()
    applyDraftToForm(readMonitoringTargetDraft(draftKey.value))
    const hasOptionalValues = optionalParamDefs.value.some((param) => {
      const val = formState.params[param.field]
      return val !== undefined && val !== null && String(val).trim() !== ''
    })
    optionalParamsActiveKeys.value = hasOptionalValues ? ['optional'] : []
    syncingFormFromRecord.value = false
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载任务详情失败')
  } finally {
    loading.value = false
  }
}

async function initializePage() {
  await Promise.all([loadTemplates(), loadCollectors(), loadModels(), loadCategories()])
  if (isEditMode.value) {
    await loadEditingTarget()
    return
  }
  editing.value = null
  resetForm()
  applyDefaultTemplateByCategory(categoryContext.value)
  applyDraftToForm(readMonitoringTargetDraft(draftKey.value))
}

function applyDraftToForm(draft?: Partial<Record<string, any>> | null) {
  if (!draft || typeof draft !== 'object') return
  if (draft.name !== undefined) formState.name = String(draft.name || '')
  if (draft.app !== undefined) formState.app = String(draft.app || '')
  if (draft.target !== undefined) formState.target = String(draft.target || '')
  if (draft.interval !== undefined) formState.interval = Number(draft.interval || 60)
  if (draft.enabled !== undefined) formState.enabled = Boolean(draft.enabled)
  if (draft.ci_model_id !== undefined) formState.ci_model_id = draft.ci_model_id ? Number(draft.ci_model_id) : undefined
  if (draft.ci_id !== undefined) formState.ci_id = draft.ci_id ? Number(draft.ci_id) : undefined
  if (draft.ci_code !== undefined) formState.ci_code = String(draft.ci_code || '')
  if (draft.ci_display !== undefined) formState.ci_display = String(draft.ci_display || '')
  if (draft.ci_attributes && typeof draft.ci_attributes === 'object') formState.ci_attributes = { ...draft.ci_attributes }
  if (draft.collector_id !== undefined) formState.collector_id = draft.collector_id ? String(draft.collector_id) : undefined
  if (draft.pin_collector !== undefined) formState.pin_collector = Boolean(draft.pin_collector)
  if (draft.apply_default_alerts !== undefined) formState.apply_default_alerts = Boolean(draft.apply_default_alerts)
  if (draft.params && typeof draft.params === 'object') formState.params = { ...draft.params }
}

function persistDraft() {
  writeMonitoringTargetDraft(draftKey.value, {
    name: formState.name,
    app: formState.app,
    target: formState.target,
    interval: formState.interval,
    enabled: formState.enabled,
    ci_model_id: formState.ci_model_id,
    ci_id: formState.ci_id,
    ci_code: formState.ci_code,
    ci_display: formState.ci_display,
    ci_attributes: formState.ci_attributes,
    collector_id: formState.collector_id,
    pin_collector: formState.pin_collector,
    apply_default_alerts: formState.apply_default_alerts,
    params: formState.params
  })
}

function resetCiSelectorState() {
  selectorSearchFieldCodes.value.forEach((fieldCode) => {
    ciSelectorSearch[fieldCode] = ''
  })
  ciSelectorScope.value = 'unmonitored'
  ciSelectorPager.page = 1
  ciSelectorPager.perPage = 10
  ciSelectorPager.total = 0
  ciSelectorRows.value = []
  ciSelectorSelectedRow.value = null
  ciSelectorSelectedKeys.value = formState.ci_id ? [formState.ci_id] : []
}

async function fetchCiSelectorRows() {
  if (!formState.ci_model_id) return
  ciSelectorLoading.value = true
  try {
    const params: Record<string, any> = {
      model_id: formState.ci_model_id,
      page: ciSelectorPager.page,
      per_page: ciSelectorPager.perPage,
      scope: ciSelectorScope.value
    }
    selectorSearchFieldCodes.value.forEach((fieldCode) => {
      const value = String(ciSelectorSearch[fieldCode] || '').trim()
      if (value) params[`attr_${fieldCode}`] = value
    })
    const res = await getMonitoringTargetCiOptions(params)
    const data = res?.data || {}
    ciSelectorRows.value = Array.isArray(data.items) ? data.items : []
    ciSelectorPager.total = Number(data.total) || 0
    if (formState.ci_id) {
      const current = ciSelectorRows.value.find((item) => item.id === formState.ci_id) || null
      ciSelectorSelectedRow.value = current
      ciSelectorSelectedKeys.value = current ? [current.id] : []
    }
  } catch (error: any) {
    ciSelectorRows.value = []
    ciSelectorPager.total = 0
    message.error(error?.response?.data?.message || '加载 CI 实例失败')
  } finally {
    ciSelectorLoading.value = false
  }
}

async function openCiSelector() {
  if (!formState.ci_model_id) {
    message.warning('请先选择 CI 模型')
    return
  }
  resetCiSelectorState()
  ciSelectorVisible.value = true
  await fetchCiSelectorRows()
}

function closeCiSelector() {
  ciSelectorVisible.value = false
}

function handleCiSelectorSearch() {
  ciSelectorScope.value = 'unmonitored'
  ciSelectorPager.page = 1
  void fetchCiSelectorRows()
}

function handleCiSelectorReset() {
  selectorSearchFieldCodes.value.forEach((fieldCode) => {
    ciSelectorSearch[fieldCode] = ''
  })
  ciSelectorScope.value = 'unmonitored'
  ciSelectorPager.page = 1
  void fetchCiSelectorRows()
}

function handleCiSelectorListAll() {
  ciSelectorScope.value = 'all'
  ciSelectorPager.page = 1
  void fetchCiSelectorRows()
}

function confirmCiSelection() {
  if (!ciSelectorSelectedRow.value || !selectedModel.value) {
    message.warning('请选择一个 CI 实例')
    return
  }
  const selectedValue = buildCiSelectionValue(ciSelectorSelectedRow.value, selectedModel.value)
  formState.ci_id = selectedValue.id
  formState.ci_code = selectedValue.code
  formState.ci_display = selectedValue.display
  formState.ci_attributes = { ...selectedValue.attributes }
  persistDraft()
  closeCiSelector()
}

function handleCiModelChange(value?: number) {
  const nextModelId = value ? Number(value) : undefined
  if (!nextModelId) {
    formState.ci_model_id = undefined
    formState.ci_id = undefined
    formState.ci_code = ''
    formState.ci_display = ''
    formState.ci_attributes = {}
    persistDraft()
    return
  }
  formState.ci_model_id = nextModelId
  formState.ci_id = undefined
  formState.ci_code = ''
  formState.ci_display = ''
  formState.ci_attributes = {}
  persistDraft()
  void openCiSelector()
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

  const paramsPayload: Record<string, string> = {}
  const paramDefMap = new Map(allParamDefs.value.map((item) => [item.field, item] as const))
  Object.entries(formState.params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || String(value).trim() === '') return
    const def = paramDefMap.get(key)
    if (def && !isParamPersistable(def)) return
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
    ci_code: formState.ci_code || '',
    ci_name: formState.ci_display || '',
    params: paramsPayload
  }
  if (!isEditMode.value) payload.apply_default_alerts = Boolean(formState.apply_default_alerts)
  let resolvedTarget = showManualTargetField.value ? formState.target.trim() : ''
  if (!resolvedTarget && paramsPayload.host) resolvedTarget = `${paramsPayload.host}:${paramsPayload.port || '6379'}`
  if (!resolvedTarget && editing.value) resolvedTarget = String(editing.value.target || editing.value.endpoint || '').trim()
  if (!resolvedTarget && formState.ci_code) resolvedTarget = `ci:${formState.ci_code}`
  payload.target = resolvedTarget

  saving.value = true
  try {
    let savedMonitorId = 0
    if (editing.value?.id) {
      await updateMonitoringTarget(editing.value.id, { ...payload, version: editing.value.version })
      savedMonitorId = editing.value.id
    } else {
      const res = await createMonitoringTarget(payload)
      savedMonitorId = Number(res?.data?.id || res?.data?.monitor_id || 0)
    }

    if (savedMonitorId > 0) {
      if (formState.collector_id && formState.pin_collector) {
        await assignCollectorToMonitor(savedMonitorId, formState.collector_id, true)
      } else if (editing.value?.id) {
        await unassignCollectorFromMonitor(editing.value.id)
      }
    }

    message.success('保存成功')
    removeMonitoringTargetDraft(draftKey.value)
    router.push('/monitoring/list')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/monitoring/list')
}

watch(
  () => route.fullPath,
  async () => {
    await initializePage()
  }
)

watch(
  () => ({
    name: formState.name,
    app: formState.app,
    target: formState.target,
    interval: formState.interval,
    enabled: formState.enabled,
    ci_model_id: formState.ci_model_id,
    ci_id: formState.ci_id,
    ci_code: formState.ci_code,
    ci_display: formState.ci_display,
    collector_id: formState.collector_id,
    pin_collector: formState.pin_collector,
    apply_default_alerts: formState.apply_default_alerts,
    params: formState.params
  }),
  () => {
    if (syncingFormFromRecord.value) return
    persistDraft()
  },
  { deep: true }
)

onMounted(async () => {
  await initializePage()
})
</script>

<style scoped>
.monitoring-target-form-page {
  min-height: 100%;
}

.monitoring-target-form-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.monitoring-target-form-page__title {
  color: var(--app-text-primary);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.monitoring-target-form-page__subtitle {
  margin-top: 4px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.monitoring-target-form-page__hint {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.monitoring-target-form-page__ci-picker {
  display: flex;
  align-items: center;
  gap: 12px;
}

.monitoring-target-form-page__selector-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.monitoring-target-form-page__selector-alert {
  margin-bottom: 16px;
}

.monitoring-target-form-page__ci-picker :deep(.ant-input-affix-wrapper),
.monitoring-target-form-page__ci-picker :deep(.ant-input) {
  flex: 1;
}

@media (max-width: 960px) {
  .monitoring-target-form-page__header {
    flex-direction: column;
    align-items: stretch;
  }

  .monitoring-target-form-page__header :deep(.app-toolbar) {
    width: 100%;
  }

  .monitoring-target-form-page__ci-picker {
    flex-direction: column;
    align-items: stretch;
  }

  .monitoring-target-form-page__selector-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
