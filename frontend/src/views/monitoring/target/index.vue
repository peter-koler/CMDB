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
      :title="modalTitle"
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
                <a-select-option v-for="t in modalTemplates" :key="t.app" :value="t.app">
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

        <a-form-item v-if="requiredParamDefs.length" label="必填参数 (params)">
          <a-row :gutter="12">
            <a-col :span="12" v-for="param in requiredParamDefs" :key="param.field" style="margin-bottom: 12px">
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

        <a-form-item v-if="optionalParamDefs.length" label="非必填参数">
          <a-collapse v-model:activeKey="optionalParamsActiveKeys" ghost>
            <a-collapse-panel key="optional" header="展开配置非必填参数">
              <a-row :gutter="12">
                <a-col :span="12" v-for="param in optionalParamDefs" :key="param.field" style="margin-bottom: 12px">
                  <a-form-item :label="paramLabel(param)" style="margin-bottom: 0">
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
            </a-collapse-panel>
          </a-collapse>
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

        <a-form-item v-if="!editing?.id" label="告警策略">
          <a-space direction="vertical" style="width: 100%" :size="4">
            <a-checkbox v-model:checked="formState.apply_default_alerts">
              创建后自动应用模板默认告警策略
            </a-checkbox>
            <span class="sub-text">当前默认策略优先覆盖 Redis 模板，可在详情页“告警”Tab继续调整。</span>
          </a-space>
        </a-form-item>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
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
  getTemplates,
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
  keyFieldCodes: string[]
  fieldLabelMap: Record<string, string>
}

interface CiOption {
  id: number
  code: string
  display: string
  attributes: Record<string, any>
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
const router = useRouter()

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
const modalTitle = computed(() => {
  if (editing.value?.id) return '编辑监控'
  if (!createContextCategoryName.value) return '新增监控'
  return `新增监控（${createContextCategoryName.value}）`
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
const createContextCategory = ref<string | null>(null)
const createContextCategoryName = computed(() => resolveCategoryContextName(createContextCategory.value))
const optionalParamsActiveKeys = ref<string[]>([])
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
  apply_default_alerts: true,
  params: {} as Record<string, any>
})

const modelOptions = ref<ModelOption[]>([])
const modelsLoading = ref(false)
const ciOptions = ref<CiOption[]>([])
const ciLoading = ref(false)

const collectors = ref<Array<{ id: string; name?: string; host?: string; status?: string }>>([])
const collectorsLoading = ref(false)

const syncingFormFromRecord = ref(false)

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
const modalTemplates = computed(() => {
  if (editing.value?.id) return templates.value
  const categoryKey = createContextCategory.value
  if (!categoryKey) return templates.value
  const apps = resolveSelectedApps(categoryKey)
  if (!apps.size) return templates.value
  return templates.value.filter((item) => item.app && apps.has(item.app))
})
const allParamDefs = computed(() => {
  const parsed = parsedTemplateMap.value[formState.app]
  if (!parsed?.params?.length) return []
  return parsed.params.filter((item) => item && item.field)
})
const requiredParamDefs = computed(() => allParamDefs.value.filter((item) => isParamRequired(item)))
const optionalParamDefs = computed(() => allParamDefs.value.filter((item) => !isParamRequired(item)))

function isParamRequired(param: TemplateParamDef): boolean {
  const raw = param?.required
  if (typeof raw === 'boolean') return raw
  const text = String(raw ?? '').trim().toLowerCase()
  return text === 'true' || text === '1' || text === 'yes' || text === 'on'
}

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
    return {
      params: deduped
    }
  } catch {
    return { params: [] }
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

function resolveCategoryContextName(code: string | null): string {
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
  } catch {
    templates.value = []
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
    const extractFieldLabelMap = (formConfig: any): Record<string, string> => {
      const out: Record<string, string> = {}
      const walk = (nodes: any[]) => {
        if (!Array.isArray(nodes)) return
        for (const node of nodes) {
          if (!node || typeof node !== 'object') continue
          const props = node.props && typeof node.props === 'object' ? node.props : {}
          const code = String(props.code || '').trim()
          const label = String(props.label || code).trim()
          if (code) out[code] = label || code
          if (Array.isArray(node.children) && node.children.length) walk(node.children)
        }
      }
      walk(formConfig)
      return out
    }
    modelOptions.value = parsed.items.map((item: any) => ({
      id: Number(item.id),
      name: String(item.name || item.code || item.id),
      code: String(item.code || item.id),
      keyFieldCodes: Array.isArray(item.key_field_codes)
        ? item.key_field_codes.map((x: any) => String(x || '').trim()).filter(Boolean)
        : [],
      fieldLabelMap: extractFieldLabelMap(Array.isArray(item.form_config) ? item.form_config : [])
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
    const modelMeta = modelOptions.value.find((item) => item.id === Number(modelId))
    ciOptions.value = parsed.items.map((item: any) => {
      const attrs = item.attributes && typeof item.attributes === 'object' ? item.attributes : {}
      const keyPairs: string[] = []
      if (modelMeta?.keyFieldCodes?.length) {
        for (const keyCode of modelMeta.keyFieldCodes) {
          const raw = attrs[keyCode]
          if (raw === undefined || raw === null || String(raw).trim() === '') continue
          const label = modelMeta.fieldLabelMap[keyCode] || keyCode
          keyPairs.push(`${label}: ${String(raw)}`)
        }
      }
      if (!keyPairs.length) {
        const fallbackKeys = ['name', 'hostname', 'host', 'ip']
        for (const key of fallbackKeys) {
          const raw = attrs[key]
          if (raw === undefined || raw === null || String(raw).trim() === '') continue
          keyPairs.push(`${key}: ${String(raw)}`)
        }
      }
      const codeText = String(item.code || item.id)
      const idText = `CIID:${item.id}`
      const keyText = keyPairs.length ? ` | ${keyPairs.join(' | ')}` : ''
      return {
        id: Number(item.id),
        code: codeText,
        display: `${idText} | 编码:${codeText}${keyText}`,
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
  formState.apply_default_alerts = true
  formState.params = {}
  optionalParamsActiveKeys.value = []
  ciOptions.value = []
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
  applyTemplateDefaults()
}

function applyDefaultTemplateByCategory(categoryKey: string | null) {
  if (!categoryKey) return
  if (categoryKey.startsWith('tpl:')) {
    const app = categoryKey.slice(4)
    if (app && templates.value.some((tpl) => tpl.app === app)) {
      formState.app = app
      applyTemplateDefaults()
    }
    return
  }
  const apps = resolveSelectedApps(categoryKey)
  if (!apps.size) return
  const hit = templates.value.find((tpl) => tpl.app && apps.has(tpl.app))
  if (hit?.app) {
    formState.app = hit.app
    applyTemplateDefaults()
  }
}

async function openModal(record?: MonitoringTarget) {
  await Promise.all([loadTemplates(), loadCollectors(), loadModels()])
  editing.value = record || null
  createContextCategory.value = record ? null : selectedCategory.value
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
    const hasOptionalValues = optionalParamDefs.value.some((param) => {
      const val = formState.params[param.field]
      return val !== undefined && val !== null && String(val).trim() !== ''
    })
    optionalParamsActiveKeys.value = hasOptionalValues ? ['optional'] : []
    syncingFormFromRecord.value = false
  } else {
    applyDefaultTemplateByCategory(createContextCategory.value)
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
  if (!editing.value?.id) {
    payload.apply_default_alerts = Boolean(formState.apply_default_alerts)
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

function openDetail(record: MonitoringTarget) {
  if (!record?.id) return
  router.push(`/monitoring/target/${record.id}`)
}

watch(
  () => formState.ci_model_id,
  async (modelId) => {
    if (syncingFormFromRecord.value) return
    formState.ci_id = undefined
    await loadCiOptions(modelId)
  }
)

onMounted(async () => {
  await reloadCategoryMenu()
  await loadTargets()
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
}

.current-category {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ci-cell {
  display: flex;
  flex-direction: column;
}

.sub-text {
  color: #8c8c8c;
  font-size: 12px;
}
</style>
