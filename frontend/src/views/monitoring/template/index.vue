<template>
  <div class="monitoring-template-page">
    <div class="template-layout">
      <!-- 左侧分类树 -->
      <div class="category-sidebar">
        <div class="sidebar-header">
          <span class="title">{{ t('template.categories') }}</span>
          <a-dropdown>
            <a-button type="primary" size="small">
              <PlusOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="showAddCategoryModal()">
                  <FolderOutlined />
                  {{ t('template.addCategory') }}
                </a-menu-item>
                <a-menu-item @click="showAddSubCategoryModal()" :disabled="!selectedCategoryForActions">
                  <FolderAddOutlined />
                  {{ t('template.addSubCategory') }}
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
        <div class="category-tree">
          <a-tree
            v-model:selectedKeys="selectedCategoryKeys"
            :tree-data="categoryTreeData"
            :field-names="{ title: 'name', key: 'key', children: 'children' }"
            @select="handleCategorySelect"
            @rightClick="handleTreeRightClick"
          >
            <template #title="{ name, key, nodeType, count }">
              <div class="tree-node" @contextmenu.prevent="showContextMenu($event, key, nodeType)">
                <span class="node-name">{{ name }}</span>
                <span class="node-count" v-if="nodeType === 'category' && count > 0">
                  ({{ count }})
                </span>
              </div>
            </template>
          </a-tree>
        </div>
      </div>

      <!-- 右键菜单 -->
      <div
        v-if="contextMenuVisible"
        class="context-menu"
        :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
      >
        <a-menu>
          <a-menu-item @click="handleRenameCategory">
            <EditOutlined />
            {{ t('template.rename') }}
          </a-menu-item>
          <a-menu-item @click="handleAddSubCategory">
            <FolderAddOutlined />
            {{ t('template.addSubCategory') }}
          </a-menu-item>
          <a-menu-divider />
          <a-menu-item danger @click="handleDeleteCategory">
            <DeleteOutlined />
            {{ t('template.delete') }}
          </a-menu-item>
        </a-menu>
      </div>

      <!-- 右侧模板编辑器 -->
      <div class="template-editor">
        <div class="editor-header">
          <div class="header-left">
            <a-breadcrumb>
              <a-breadcrumb-item>{{ t('menu.monitoring') }}</a-breadcrumb-item>
              <a-breadcrumb-item>{{ t('menu.monitoringTemplate') }}</a-breadcrumb-item>
              <a-breadcrumb-item v-if="currentCategory">{{ currentCategory.name }}</a-breadcrumb-item>
            </a-breadcrumb>
          </div>
          <div class="header-actions" v-if="selectedTemplate || isNewTemplate">
            <a-space>
              <a-button @click="handlePreview" v-if="selectedTemplate && activeRightTab === 'content'">
                <EyeOutlined />
                {{ t('template.preview') }}
              </a-button>
              <a-button type="primary" @click="handleSave" :loading="saving">
                <SaveOutlined />
                {{ t('template.saveAndApply') }}
              </a-button>
            </a-space>
          </div>
        </div>

        <div class="editor-content" v-if="selectedTemplate || isNewTemplate">
          <a-tabs v-model:activeKey="activeRightTab">
            <a-tab-pane key="content" tab="模板内容">
              <div class="content-tab-pane">
                <div class="editor-toolbar">
                  <a-space>
                    <a-tag color="blue">{{ isNewTemplate ? currentCategoryKey : selectedTemplate?.category }}</a-tag>
                    <span class="template-name">{{ isNewTemplate ? t('template.addNewType') : getTemplateDisplayName(selectedTemplate) }}</span>
                  </a-space>
                </div>
                <div class="code-editor-wrapper">
                  <textarea
                    v-model="templateYaml"
                    class="code-textarea"
                    :placeholder="isNewTemplate ? '# 请在此粘贴 YAML 模板内容...\n# 例如：\n# category: db\n# app: mysql\n# name:\n#   zh-CN: MySQL数据库\n#   en-US: MySQL Database\n# params:\n#   - name: host\n#     ...' : ''"
                    spellcheck="false"
                  />
                </div>
              </div>
            </a-tab-pane>
            <a-tab-pane key="default-policy" tab="默认监控策略" :disabled="!selectedTemplate">
              <div class="policy-content">
                <a-space style="margin-bottom: 12px">
                  <a-button type="primary" @click="addPolicyRule">新增策略</a-button>
                  <a-button v-if="String(selectedTemplate?.app || '').toLowerCase() === 'redis'" @click="importRedisPolicyRules">
                    导入 Redis 推荐策略
                  </a-button>
                  <a-button danger @click="clearPolicyRules">清空策略</a-button>
                </a-space>
                <a-alert
                  v-if="!defaultPolicyDraft.length"
                  type="info"
                  show-icon
                  message="当前模板未定义默认监控策略"
                  description="可在此可视化维护默认告警策略，保存后会自动同步到模板 YAML 的 alerts 段。"
                />
                <a-table
                  v-else
                  size="small"
                  :pagination="false"
                  :data-source="defaultPolicyDraft"
                  :columns="defaultPolicyColumns"
                  row-key="key"
                  :scroll="{ x: 1180 }"
                >
                  <template #bodyCell="{ column, record, index }">
                    <template v-if="column.key === 'name'">
                      <div class="policy-name-cell">
                        <div>{{ record.name }}</div>
                        <a-tag size="small" :color="record.mode === 'core' ? 'blue' : 'default'">
                          {{ record.mode === 'core' ? '核心' : '扩展' }}
                        </a-tag>
                      </div>
                    </template>
                    <template v-else-if="column.key === 'type'">
                      <a-tag :color="record.type === 'periodic_metric' ? 'green' : 'blue'">
                        {{ record.type === 'periodic_metric' ? '周期' : '实时' }}
                      </a-tag>
                    </template>
                    <template v-else-if="column.key === 'metric'">
                      {{ displayMetricName(record.metric) }}
                    </template>
                    <template v-else-if="column.key === 'level'">
                      <a-tag :color="record.level === 'critical' ? 'red' : record.level === 'warning' ? 'orange' : 'blue'">
                        {{ record.level }}
                      </a-tag>
                    </template>
                    <template v-else-if="column.key === 'rule'">
                      {{ `${record.metric} ${record.operator} ${record.threshold}` }}
                    </template>
                    <template v-else-if="column.key === 'trigger'">
                      {{ `周期 ${record.period}s / 连续 ${record.times} 次` }}
                    </template>
                    <template v-else-if="column.key === 'notice_rule_id'">
                      {{ getNoticeRuleName(record.notice_rule_id) }}
                    </template>
                    <template v-else-if="column.key === 'enabled'">
                      <a-switch :checked="record.enabled" @change="(checked: boolean) => { record.enabled = checked }" />
                    </template>
                    <template v-else-if="column.key === 'actions'">
                      <a-space :size="4">
                        <a-button type="link" size="small" @click="openPolicyRuleEditor(record, index)">编辑</a-button>
                        <a-button type="link" size="small" :disabled="index === 0" @click="movePolicyRule(index, -1)">上移</a-button>
                        <a-button type="link" size="small" :disabled="index === defaultPolicyDraft.length - 1" @click="movePolicyRule(index, 1)">下移</a-button>
                        <a-button danger type="link" size="small" @click="removePolicyRule(index)">删除</a-button>
                      </a-space>
                    </template>
                  </template>
                </a-table>
              </div>
            </a-tab-pane>
          </a-tabs>
        </div>

        <div class="empty-state" v-else>
          <a-empty :description="t('template.selectTemplate')" />
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <a-modal
      v-model:open="previewModalVisible"
      :title="t('template.preview')"
      width="800px"
      :footer="null"
    >
      <template-preview :yaml-content="templateYaml" />
    </a-modal>

    <!-- 分类管理弹窗 -->
    <a-modal
      v-model:open="categoryModalVisible"
      :title="categoryModalTitle"
      @ok="handleSaveCategory"
      width="500px"
    >
      <a-form :model="categoryForm" layout="vertical">
        <a-form-item :label="t('template.categoryName')" required>
          <a-input
            v-model:value="categoryForm.name"
            :placeholder="t('template.categoryNamePlaceholder')"
          />
        </a-form-item>
        <a-form-item :label="t('template.categoryCode')" required>
          <a-input
            v-model:value="categoryForm.code"
            :disabled="isEditMode"
            :placeholder="t('template.categoryCodePlaceholder')"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="policyEditorVisible"
      :title="policyEditIndex === -1 ? '新增默认策略' : '编辑默认策略'"
      width="860px"
      :confirm-loading="policyEditorSaving"
      @ok="savePolicyRuleEditor"
    >
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="规则名称" required>
              <a-input v-model:value="policyForm.name" placeholder="请输入规则名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="规则类型">
              <a-select v-model:value="policyForm.type">
                <a-select-option value="realtime_metric">实时指标</a-select-option>
                <a-select-option value="periodic_metric">周期指标</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="监控指标" required extra="支持派生变量：<app>_server_up（可用性）与 *_ok（字符串状态映射为1/0）">
              <a-select v-model:value="policyForm.metric" show-search option-filter-prop="label" placeholder="请选择模板指标">
                <a-select-option v-for="opt in metricOptions" :key="opt.value" :value="opt.value" :label="opt.label">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="操作符">
              <a-select v-model:value="policyForm.operator">
                <template v-if="policyIsBinaryMetric">
                  <a-select-option value="==">==（推荐）</a-select-option>
                  <a-select-option value="!=">!=</a-select-option>
                </template>
                <template v-else>
                  <a-select-option value=">">&gt;</a-select-option>
                  <a-select-option value=">=">&gt;=</a-select-option>
                  <a-select-option value="<">&lt;</a-select-option>
                  <a-select-option value="<=">&lt;=</a-select-option>
                  <a-select-option value="==">==</a-select-option>
                  <a-select-option value="!=">!=</a-select-option>
                </template>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item :label="policyIsBinaryMetric ? '状态值' : '阈值'" required :extra="policyIsBinaryMetric ? '0=异常，1=正常' : undefined">
              <a-select v-if="policyIsBinaryMetric" v-model:value="policyForm.threshold">
                <a-select-option :value="0">0（异常）</a-select-option>
                <a-select-option :value="1">1（正常）</a-select-option>
              </a-select>
              <a-input-number v-else v-model:value="policyForm.threshold" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="触发级别">
              <a-select v-model:value="policyForm.level">
                <a-select-option value="critical">critical</a-select-option>
                <a-select-option value="warning">warning</a-select-option>
                <a-select-option value="info">info</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="执行周期(秒)">
              <a-input-number v-model:value="policyForm.period" :min="0" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="连续触发次数">
              <a-input-number v-model:value="policyForm.times" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="通知规则">
              <a-select v-model:value="policyForm.notice_rule_id" allow-clear placeholder="请选择通知规则">
                <a-select-option v-for="item in noticeRuleOptions" :key="Number(item.id)" :value="Number(item.id)">
                  {{ item.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="策略分组">
              <a-select v-model:value="policyForm.mode">
                <a-select-option value="core">核心</a-select-option>
                <a-select-option value="extended">扩展</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="默认启用">
              <a-switch v-model:checked="policyForm.enabled" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="自动恢复关闭">
              <a-switch v-model:checked="policyForm.auto_recover" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="恢复次数(N)">
              <a-input-number v-model:value="policyForm.recover_times" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="发送恢复通知">
              <a-switch v-model:checked="policyForm.notify_on_recovered" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="监控标签">
          <a-space direction="vertical" style="width: 100%">
            <a-row v-for="(tag, idx) in policyFormLabelList" :key="idx" :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="tag.key" placeholder="标签名" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="tag.value" placeholder="标签值" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removePolicyLabel(idx)">删除</a-button>
              </a-col>
            </a-row>
            <a-button type="dashed" block @click="addPolicyLabel">添加标签</a-button>
          </a-space>
        </a-form-item>

        <a-form-item label="告警内容模板">
          <a-textarea v-model:value="policyForm.template" :rows="2" placeholder="支持模板变量，如 {{$labels.instance}} {{$value}}" />
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-switch v-model:checked="policyFormUseCustomExpr" />
            <span>高级模式：自定义表达式</span>
          </a-space>
        </a-form-item>
        <a-form-item v-if="policyFormUseCustomExpr" label="表达式">
          <a-textarea v-model:value="policyForm.expr" :rows="3" placeholder="例如：(used_memory / maxmemory) * 100 > 85" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { message, Modal } from 'ant-design-vue'
import * as yaml from 'js-yaml'
import {
  EyeOutlined,
  SaveOutlined,
  PlusOutlined,
  FolderOutlined,
  FolderAddOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'
import TemplatePreview from './components/TemplatePreview.vue'
import {
  getTemplates,
  getCategories,
  createTemplate as createTemplateApi,
  updateTemplate as updateTemplateApi,
  createCategory as createCategoryApi,
  updateCategory as updateCategoryApi,
  deleteCategory as deleteCategoryApi,
  getAlertNotices,
  type AlertNotice
} from '@/api/monitoring'
import {
  REDIS_DEFAULT_POLICY,
  getBuiltinDefaultPolicyByApp,
  type DefaultPolicyItem
} from './default-policies'

const { t, locale } = useI18n()

interface CategoryNode {
  id?: number
  key: string
  name: string
  icon?: string
  parent_id?: number
  children?: CategoryNode[]
}

interface TemplateItem {
  app: string
  category: string
  name: string | Record<string, string>
  content: string
  version?: number
  is_hidden?: boolean
}

interface TreeNode {
  key: string
  name: string
  nodeType: 'category' | 'template'
  children?: TreeNode[]
  count?: number
}

interface MetricOption {
  value: string
  label: string
}

const categories = ref<CategoryNode[]>([])
const templates = ref<TemplateItem[]>([])
const selectedCategoryKeys = ref<string[]>([])
const selectedTemplate = ref<TemplateItem | null>(null)
const templateYaml = ref('')
const saving = ref(false)
const previewModalVisible = ref(false)
const currentCategoryKey = ref('')
const activeRightTab = ref('content')

const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuKey = ref('')

const categoryModalVisible = ref(false)
const categoryModalTitle = ref('')
const categoryForm = ref({ name: '', code: '', key: '', parentKey: '' })
const isEditMode = ref(false)
const isSubCategory = ref(false)
const defaultPolicyDraft = ref<DefaultPolicyItem[]>([])
const mutePolicySync = ref(false)
const metricOptions = ref<MetricOption[]>([])
const noticeRuleOptions = ref<AlertNotice[]>([])
const policyEditorVisible = ref(false)
const policyEditorSaving = ref(false)
const policyEditIndex = ref(-1)
const policyFormUseCustomExpr = ref(false)
const policyForm = ref<DefaultPolicyItem>({
  key: '',
  name: '',
  type: 'realtime_metric',
  metric: 'value',
  operator: '>',
  threshold: 0,
  level: 'warning',
  period: 60,
  times: 1,
  mode: 'extended',
  enabled: false,
  auto_recover: true,
  recover_times: 2,
  notify_on_recovered: true,
  expr: '',
  template: '',
  notice_rule_id: undefined,
  labels: {}
})
const policyFormLabelList = ref<Array<{ key: string; value: string }>>([])

const isNewTemplate = computed(() => Boolean(!selectedTemplate.value && currentCategoryKey.value))
const categoryTreeData = computed<TreeNode[]>(() => buildDisplayTree(categories.value))

const currentCategory = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return null
  if (String(key).startsWith('tpl:')) {
    return selectedTemplate.value ? findCategoryByKey(selectedTemplate.value.category, categories.value) : null
  }
  return findCategoryByKey(key, categories.value)
})

const selectedCategoryForActions = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return null
  if (String(key).startsWith('tpl:')) {
    return selectedTemplate.value ? findCategoryByKey(selectedTemplate.value.category, categories.value) : null
  }
  return findCategoryByKey(key, categories.value)
})

const isBinaryMetric = (metric: string) => {
  const key = String(metric || '').trim().toLowerCase()
  return key.endsWith('_ok') || key.endsWith('_up')
}

const normalizeBinaryRule = (metric: string, operator: string, threshold: number) => {
  if (!isBinaryMetric(metric)) {
    return { operator: String(operator || '>').trim() || '>', threshold: Number(threshold ?? 0) || 0 }
  }
  const op = String(operator || '==').trim() || '=='
  if (op === '<' || op === '<=') {
    return { operator: '==', threshold: 0 }
  }
  if (op === '>' || op === '>=') {
    return { operator: '==', threshold: 1 }
  }
  if (op === '!=') {
    return { operator: '!=', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
  }
  return { operator: '==', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
}

const policyIsBinaryMetric = computed(() => isBinaryMetric(policyForm.value.metric))

const toBool = (value: any, defaultValue = false) => {
  if (value === undefined || value === null) return defaultValue
  if (typeof value === 'boolean') return value
  const text = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(text)) return true
  if (['0', 'false', 'no', 'off'].includes(text)) return false
  return defaultValue
}

const normalizePolicyItem = (item: any, index: number): DefaultPolicyItem | null => {
  if (!item || typeof item !== 'object') return null
  const name = String(item.name || '').trim()
  if (!name) return null
  const typeRaw = String(item.type || item.monitor_type || '').trim().toLowerCase()
  const type = typeRaw.includes('periodic') ? 'periodic_metric' : 'realtime_metric'
  const mode = String(item.mode || '').trim().toLowerCase() === 'core' ? 'core' : 'extended'
  const labelsObj = item.labels && typeof item.labels === 'object' ? item.labels : {}
  const metric = String(item.metric || 'value').trim() || 'value'
  const binary = normalizeBinaryRule(metric, String(item.operator || '>').trim() || '>', Number(item.threshold ?? 0) || 0)
  return {
    key: String(item.key || item.id || `alert_${index + 1}`),
    name,
    type,
    metric,
    operator: binary.operator,
    threshold: binary.threshold,
    level: (String(item.level || item.severity || 'warning').trim().toLowerCase() as any) || 'warning',
    period: Math.max(Number(item.period ?? (type === 'periodic_metric' ? 300 : 60)) || 0, 0),
    times: Math.max(Number(item.times ?? 1) || 1, 1),
    mode,
    enabled: toBool(item.enabled ?? item.default_enabled, mode === 'core'),
    auto_recover: toBool(item.auto_recover, true),
    recover_times: Math.max(Number(item.recover_times ?? 2) || 2, 1),
    notify_on_recovered: toBool(item.notify_on_recovered, true),
    expr: String(item.expr || '').trim() || undefined,
    template: String(item.template || '').trim() || undefined,
    notice_rule_id: item.notice_rule_id !== undefined && item.notice_rule_id !== null ? Number(item.notice_rule_id) : undefined,
    labels: labelsObj
  }
}

const parseDefaultPoliciesFromYaml = (content: string): DefaultPolicyItem[] => {
  try {
    const doc = yaml.load(content || '') as any
    if (!doc || typeof doc !== 'object' || !Array.isArray((doc as any).alerts)) return []
    const rows: DefaultPolicyItem[] = []
    ;(doc as any).alerts.forEach((item: any, index: number) => {
      const normalized = normalizePolicyItem(item, index)
      if (normalized) rows.push(normalized)
    })
    return rows
  } catch {
    return []
  }
}

const parseTemplateMetricOptions = (content: string): MetricOption[] => {
  try {
    const doc = yaml.load(content || '') as any
    if (!doc || typeof doc !== 'object') return []
    const options = new Map<string, MetricOption>()
    const appName = String((doc as any).app || '').trim()
    const metricsList = Array.isArray((doc as any).metrics) ? (doc as any).metrics : []
    const localeKey = String(locale.value || 'zh-CN')
    const pickI18nText = (node: any, fallback = '') => {
      if (!node) return fallback
      if (typeof node === 'string') return node
      if (typeof node === 'object') {
        const i18n = node.i18n && typeof node.i18n === 'object' ? node.i18n : node
        return String(i18n[localeKey] || i18n['zh-CN'] || i18n['en-US'] || fallback)
      }
      return String(fallback || '')
    }
    for (const m of metricsList) {
      const metricName = String(m?.field || m?.metric || m?.name || '').trim()
      const metricTitle = pickI18nText(m?.i18n || m?.name, metricName)
      if (metricName) {
        options.set(metricName, { value: metricName, label: `${metricTitle} (${metricName})` })
      }
      const fields = Array.isArray(m?.fields) ? m.fields : []
      for (const f of fields) {
        const field = String(f?.field || '').trim()
        if (!field) continue
        const fieldTitle = pickI18nText(f?.i18n || f?.name, field)
        const groupTitle = metricTitle || metricName
        const label = groupTitle ? `${groupTitle} / ${fieldTitle} (${field})` : `${fieldTitle} (${field})`
        options.set(field, { value: field, label })
        const fieldType = Number(f?.type)
        if (fieldType === 1) {
          const okField = `${field}_ok`
          const okLabel = groupTitle
            ? `${groupTitle} / ${fieldTitle} 状态OK (${okField})`
            : `${fieldTitle} 状态OK (${okField})`
          options.set(okField, { value: okField, label: okLabel })
        }
      }
    }
    if (appName) {
      const appUp = `${appName}_server_up`
      options.set(appUp, { value: appUp, label: `实例可用性 (${appUp})` })
    }
    if (!options.size) {
      options.set('value', { value: 'value', label: 'value' })
    }
    return Array.from(options.values())
  } catch {
    return [{ value: 'value', label: 'value' }]
  }
}

const displayMetricName = (metric: string) => {
  const key = String(metric || '').trim()
  const found = metricOptions.value.find((item) => item.value === key)
  return found?.label || key || 'value'
}

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const loadNoticeRuleOptions = async () => {
  try {
    const res = await getAlertNotices({ page_size: 1000 })
    const parsed = normalizeList((res as any)?.data ?? res)
    noticeRuleOptions.value = (parsed.items || []) as AlertNotice[]
  } catch {
    noticeRuleOptions.value = []
  }
}

const loadDefaultPolicyDraft = () => {
  mutePolicySync.value = true
  metricOptions.value = parseTemplateMetricOptions(templateYaml.value || selectedTemplate.value?.content || '')
  const fromTemplate = parseDefaultPoliciesFromYaml(templateYaml.value || selectedTemplate.value?.content || '')
  if (fromTemplate.length) {
    defaultPolicyDraft.value = fromTemplate
  } else {
    defaultPolicyDraft.value = getBuiltinDefaultPolicyByApp(String(selectedTemplate.value?.app || ''))
  }
  mutePolicySync.value = false
}

const syncPolicyDraftToYaml = () => {
  if (mutePolicySync.value) return
  if (!selectedTemplate.value) return
  try {
    const baseContent = templateYaml.value || selectedTemplate.value.content || ''
    const doc = parseYamlObject(baseContent)
    const alerts = defaultPolicyDraft.value
      .filter((item) => String(item.name || '').trim())
      .map((item) => {
        const out: any = {
          name: item.name.trim(),
          type: item.type,
          metric: item.metric || 'value',
          operator: item.operator || '>',
          threshold: Number(item.threshold || 0),
          level: item.level || 'warning',
          period: Math.max(Number(item.period || 0), 0),
          times: Math.max(Number(item.times || 1), 1),
          mode: item.mode || 'extended',
          enabled: Boolean(item.enabled),
          auto_recover: item.auto_recover !== false,
          recover_times: Math.max(Number(item.recover_times ?? 2), 1),
          notify_on_recovered: item.notify_on_recovered !== false
        }
        if (item.notice_rule_id !== undefined && item.notice_rule_id !== null) out.notice_rule_id = Number(item.notice_rule_id)
        if (item.labels && Object.keys(item.labels).length) out.labels = item.labels
        if (item.expr && item.expr.trim()) out.expr = item.expr.trim()
        if (item.template && item.template.trim()) out.template = item.template.trim()
        return out
      })
    if (alerts.length) {
      doc.alerts = alerts
    } else {
      delete doc.alerts
    }
    templateYaml.value = yaml.dump(doc, { noRefs: true, sortKeys: false, lineWidth: -1 })
  } catch (error) {
    console.error('sync policy to yaml failed', error)
  }
}

const buildPolicyExpr = (item: Pick<DefaultPolicyItem, 'metric' | 'operator' | 'threshold'>) => {
  const metric = String(item.metric || 'value').trim() || 'value'
  const binary = normalizeBinaryRule(metric, String(item.operator || '>').trim() || '>', Number(item.threshold ?? 0))
  const op = binary.operator
  const threshold = binary.threshold
  return `${metric} ${op} ${Number.isFinite(threshold) ? threshold : 0}`
}

const resetPolicyForm = () => {
  const defaultMetric = metricOptions.value[0]?.value || 'value'
  const defaultOperator = isBinaryMetric(defaultMetric) ? '==' : '>'
  const binary = normalizeBinaryRule(defaultMetric, defaultOperator, 0)
  policyForm.value = {
    key: `alert_${Date.now()}`,
    name: '',
    type: 'realtime_metric',
    metric: defaultMetric,
    operator: binary.operator,
    threshold: binary.threshold,
    level: 'warning',
    period: 60,
    times: 1,
    mode: 'extended',
    enabled: false,
    auto_recover: true,
    recover_times: 2,
    notify_on_recovered: true,
    expr: '',
    template: '',
    notice_rule_id: undefined,
    labels: {}
  }
  policyFormLabelList.value = []
  policyFormUseCustomExpr.value = false
}

const addPolicyRule = async () => {
  await loadNoticeRuleOptions()
  policyEditIndex.value = -1
  resetPolicyForm()
  policyEditorVisible.value = true
}

const openPolicyRuleEditor = async (record: DefaultPolicyItem, index: number) => {
  await loadNoticeRuleOptions()
  policyEditIndex.value = index
  const binary = normalizeBinaryRule(record.metric, record.operator, record.threshold)
  policyForm.value = {
    ...record,
    operator: binary.operator,
    threshold: binary.threshold,
    labels: { ...(record.labels || {}) }
  }
  policyFormLabelList.value = Object.entries(record.labels || {}).map(([key, value]) => ({ key, value }))
  policyFormUseCustomExpr.value = Boolean(String(record.expr || '').trim())
  policyEditorVisible.value = true
}

const addPolicyLabel = () => {
  policyFormLabelList.value.push({ key: '', value: '' })
}

const removePolicyLabel = (index: number) => {
  if (index < 0 || index >= policyFormLabelList.value.length) return
  policyFormLabelList.value.splice(index, 1)
}

const savePolicyRuleEditor = () => {
  policyEditorSaving.value = true
  try {
    const name = String(policyForm.value.name || '').trim()
    if (!name) {
      message.error('规则名称不能为空')
      return
    }
    const metric = String(policyForm.value.metric || '').trim()
    if (!metric) {
      message.error('请选择监控指标')
      return
    }
    const labels: Record<string, string> = {}
    policyFormLabelList.value.forEach((item) => {
      const key = String(item.key || '').trim()
      const value = String(item.value || '').trim()
      if (key && value) labels[key] = value
    })
    const row: DefaultPolicyItem = {
      key: String(policyForm.value.key || `alert_${Date.now()}`),
      name,
      type: policyForm.value.type === 'periodic_metric' ? 'periodic_metric' : 'realtime_metric',
      metric,
      operator: String(policyForm.value.operator || '>'),
      threshold: Number(policyForm.value.threshold ?? 0),
      level: (String(policyForm.value.level || 'warning') as any),
      period: Math.max(Number(policyForm.value.period ?? 60), 0),
      times: Math.max(Number(policyForm.value.times ?? 1), 1),
      mode: policyForm.value.mode === 'core' ? 'core' : 'extended',
      enabled: Boolean(policyForm.value.enabled),
      auto_recover: policyForm.value.auto_recover !== false,
      recover_times: Math.max(Number(policyForm.value.recover_times ?? 2), 1),
      notify_on_recovered: policyForm.value.notify_on_recovered !== false,
      template: String(policyForm.value.template || '').trim() || undefined,
      notice_rule_id: policyForm.value.notice_rule_id !== undefined && policyForm.value.notice_rule_id !== null
        ? Number(policyForm.value.notice_rule_id)
        : undefined,
      labels
    }
    const normalized = normalizeBinaryRule(row.metric, row.operator, row.threshold)
    row.operator = normalized.operator
    row.threshold = normalized.threshold
    if (policyFormUseCustomExpr.value) {
      row.expr = String(policyForm.value.expr || '').trim() || buildPolicyExpr(row)
    } else {
      row.expr = buildPolicyExpr(row)
    }
    if (policyEditIndex.value >= 0 && policyEditIndex.value < defaultPolicyDraft.value.length) {
      defaultPolicyDraft.value.splice(policyEditIndex.value, 1, row)
    } else {
      defaultPolicyDraft.value.push(row)
    }
    policyEditorVisible.value = false
  } finally {
    policyEditorSaving.value = false
  }
}

const getNoticeRuleName = (noticeRuleId?: number) => {
  if (!noticeRuleId) return '-'
  const found = noticeRuleOptions.value.find((item) => Number(item.id) === Number(noticeRuleId))
  return found?.name || `#${noticeRuleId}`
}

const removePolicyRule = (index: number) => {
  if (index < 0 || index >= defaultPolicyDraft.value.length) return
  defaultPolicyDraft.value.splice(index, 1)
}

const movePolicyRule = (index: number, step: number) => {
  const target = index + step
  if (index < 0 || index >= defaultPolicyDraft.value.length) return
  if (target < 0 || target >= defaultPolicyDraft.value.length) return
  const rows = [...defaultPolicyDraft.value]
  const [row] = rows.splice(index, 1)
  rows.splice(target, 0, row)
  defaultPolicyDraft.value = rows
}

const clearPolicyRules = () => {
  defaultPolicyDraft.value = []
}

const importRedisPolicyRules = () => {
  defaultPolicyDraft.value = [...REDIS_DEFAULT_POLICY]
}

const defaultPolicyColumns = [
  { title: '规则名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 90 },
  { title: '监控指标', dataIndex: 'metric', key: 'metric', width: 220 },
  { title: '判断', key: 'rule', width: 220 },
  { title: '级别', dataIndex: 'level', key: 'level', width: 100 },
  { title: '触发配置', key: 'trigger', width: 170 },
  { title: '通知规则', key: 'notice_rule_id', width: 180 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 90 },
  { title: '操作', key: 'actions', width: 190, fixed: 'right' as const }
]

const normalizeCode = (name: string) => {
  const normalized = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  return normalized || `cat_${Date.now()}`
}

const isValidCategoryCode = (code: string) => /^[a-z0-9][a-z0-9_-]*$/.test(code)

const findCategoryByKey = (key: string, list: CategoryNode[]): CategoryNode | null => {
  for (const item of list) {
    if (item.key === key) return item
    if (item.children?.length) {
      const found = findCategoryByKey(key, item.children)
      if (found) return found
    }
  }
  return null
}

const getTemplateByTreeKey = (key: string) => {
  if (!key.startsWith('tpl:')) return null
  const app = key.slice(4)
  return templates.value.find((item) => item.app === app) || null
}

const collectCategoryCodes = (nodes: CategoryNode[]): Set<string> => {
  const out = new Set<string>()
  const walk = (list: CategoryNode[]) => {
    for (const item of list) {
      out.add(item.key)
      if (item.children?.length) walk(item.children)
    }
  }
  walk(nodes)
  return out
}

const buildDisplayTree = (categoryNodes: CategoryNode[], includeUncategorized = true): TreeNode[] => {
  const treeNodes = categoryNodes.map((cat) => {
    const categoryChildren = buildDisplayTree(cat.children || [], false)
    const templateChildren = templates.value
      .filter((t) => t.category === cat.key)
      .sort((a, b) => getTemplateDisplayName(a).localeCompare(getTemplateDisplayName(b)))
      .map<TreeNode>((tpl) => ({
        key: `tpl:${tpl.app}`,
        name: getTemplateDisplayName(tpl),
        nodeType: 'template'
      }))

    const subtreeCount = categoryChildren.reduce((sum, node) => sum + (node.count || 0), 0)
    const count = templateChildren.length + subtreeCount

    return {
      key: cat.key,
      name: cat.name,
      nodeType: 'category',
      count,
      children: [...categoryChildren, ...templateChildren]
    }
  })
  if (includeUncategorized) {
    const categoryCodes = collectCategoryCodes(categoryNodes)
    const uncategorizedTemplates = templates.value
      .filter((t) => !categoryCodes.has(t.category))
      .sort((a, b) => getTemplateDisplayName(a).localeCompare(getTemplateDisplayName(b)))
      .map<TreeNode>((tpl) => ({
        key: `tpl:${tpl.app}`,
        name: getTemplateDisplayName(tpl),
        nodeType: 'template'
      }))
    if (uncategorizedTemplates.length) {
      treeNodes.push({
        key: '__uncategorized__',
        name: '未分类',
        nodeType: 'category',
        count: uncategorizedTemplates.length,
        children: uncategorizedTemplates
      })
    }
  }
  return treeNodes
}

const findFirstTemplateKey = (nodes: TreeNode[]): string | null => {
  for (const node of nodes) {
    if (node.nodeType === 'template') return node.key
    if (node.children?.length) {
      const nested = findFirstTemplateKey(node.children)
      if (nested) return nested
    }
  }
  return null
}

const getTemplateDisplayName = (tpl: TemplateItem | null) => {
  if (!tpl) return ''
  if (typeof tpl.name === 'string') return tpl.name || tpl.app
  return tpl.name?.[String(locale.value)] || tpl.name?.['zh-CN'] || tpl.name?.['en-US'] || tpl.app
}

const parseYamlObject = (content: string): any => {
  const doc = yaml.load(content || '')
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    throw new Error('YAML 顶层必须是对象')
  }
  return doc
}

const normalizeTemplateYaml = (content: string, fallbackCategory = '') => {
  const doc = parseYamlObject(content)
  const app = String(doc.app || '').trim()
  const category = String(doc.category || fallbackCategory || '').trim()
  const nameNode = doc.name
  const name = typeof nameNode === 'string'
    ? nameNode.trim()
    : String(nameNode?.['zh-CN'] || nameNode?.['en-US'] || app).trim()

  if (!app) {
    throw new Error('模板缺少 app 字段')
  }
  if (!category) {
    throw new Error('模板缺少 category 字段')
  }

  const params = Array.isArray(doc.params) ? doc.params : []
  const seen = new Set<string>()
  const duplicates: string[] = []
  const deduped: any[] = []
  for (const item of params) {
    if (!item || typeof item !== 'object') continue
    const field = String((item as any).field || '').trim()
    if (!field) continue
    if (seen.has(field)) {
      duplicates.push(field)
      continue
    }
    seen.add(field)
    deduped.push(item)
  }
  doc.params = deduped

  return {
    app,
    category,
    name: name || app,
    content: yaml.dump(doc, { noRefs: true, sortKeys: false, lineWidth: -1 }),
    duplicates
  }
}

const buildCategoryTree = (rows: any[]): CategoryNode[] => {
  const byId = new Map<number, CategoryNode>()
  const roots: CategoryNode[] = []

  rows.forEach((row) => {
    const node: CategoryNode = {
      id: Number(row.id),
      key: String(row.code),
      name: String(row.name || row.code),
      icon: row.icon,
      parent_id: row.parent_id ? Number(row.parent_id) : undefined,
      children: []
    }
    byId.set(node.id as number, node)
  })

  rows.forEach((row) => {
    const node = byId.get(Number(row.id))
    if (!node) return
    const parentId = row.parent_id ? Number(row.parent_id) : undefined
    if (parentId && byId.has(parentId)) {
      byId.get(parentId)?.children?.push(node)
    } else {
      roots.push(node)
    }
  })

  return roots
}

const dedupeTemplatesByApp = (rows: any[]): TemplateItem[] => {
  const byApp = new Map<string, TemplateItem>()
  for (const row of rows || []) {
    const app = String(row?.app || '').trim()
    if (!app) continue
    byApp.set(app, {
      app,
      category: String(row?.category || '').trim(),
      name: row?.name || app,
      content: String(row?.content || ''),
      version: Number(row?.version || 0),
      is_hidden: Boolean(row?.is_hidden)
    })
  }
  return Array.from(byApp.values()).sort((a, b) => a.app.localeCompare(b.app))
}

const loadTemplates = async () => {
  try {
    const [tplResp, catResp] = await Promise.all([getTemplates(), getCategories()])

    templates.value = dedupeTemplatesByApp(tplResp?.data || [])
    categories.value = buildCategoryTree(catResp?.data || [])
    const selectedKey = selectedCategoryKeys.value[0]
    if (selectedKey?.startsWith('tpl:')) {
      const selectedTpl = getTemplateByTreeKey(selectedKey)
      if (selectedTpl) {
        selectTemplate(selectedTpl)
      } else {
        selectedCategoryKeys.value = []
        selectedTemplate.value = null
        templateYaml.value = ''
      }
      return
    }

    if (selectedKey && findCategoryByKey(selectedKey, categories.value)) {
      currentCategoryKey.value = selectedKey
      selectedTemplate.value = null
      templateYaml.value = ''
      return
    }

    const firstTplKey = findFirstTemplateKey(categoryTreeData.value)
    if (firstTplKey) {
      selectedCategoryKeys.value = [firstTplKey]
      const firstTpl = getTemplateByTreeKey(firstTplKey)
      if (firstTpl) {
        selectTemplate(firstTpl)
      }
      return
    }

    if (categories.value.length) {
      selectedCategoryKeys.value = [categories.value[0].key]
      currentCategoryKey.value = categories.value[0].key
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
    message.error(t('template.loadFailed'))
  }
}

const showContextMenu = (e: MouseEvent, key: string, nodeType: 'category' | 'template') => {
  if (nodeType !== 'category') return
  e.preventDefault()
  contextMenuKey.value = key
  contextMenuPosition.value = { x: e.clientX, y: e.clientY }
  contextMenuVisible.value = true
}

const hideContextMenu = () => {
  contextMenuVisible.value = false
}

const handleTreeRightClick = ({ event, node }: any) => {
  if (node?.nodeType !== 'category') return
  showContextMenu(event, String(node.key), 'category')
}

const showAddCategoryModal = () => {
  isEditMode.value = false
  isSubCategory.value = false
  categoryModalTitle.value = t('template.addCategory')
  categoryForm.value = { name: '', code: '', key: '', parentKey: '' }
  categoryModalVisible.value = true
}

const showAddSubCategoryModal = () => {
  const parentKey = selectedCategoryForActions.value?.key
  if (!parentKey) return
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', code: '', key: '', parentKey }
  categoryModalVisible.value = true
}

const handleRenameCategory = () => {
  hideContextMenu()
  const category = findCategoryByKey(contextMenuKey.value, categories.value)
  if (!category) return
  isEditMode.value = true
  isSubCategory.value = Boolean(category.parent_id)
  categoryModalTitle.value = t('template.renameCategory')
  categoryForm.value = { name: category.name, code: category.key, key: category.key, parentKey: '' }
  categoryModalVisible.value = true
}

const handleAddSubCategory = () => {
  hideContextMenu()
  if (!contextMenuKey.value) return
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', code: '', key: '', parentKey: contextMenuKey.value }
  categoryModalVisible.value = true
}

const handleDeleteCategory = () => {
  hideContextMenu()
  const key = contextMenuKey.value
  if (!key) return
  Modal.confirm({
    title: t('template.confirmDeleteCategory'),
    content: t('template.confirmDeleteCategoryContent'),
    okText: t('common.confirm'),
    cancelText: t('common.cancel'),
    onOk: async () => {
      try {
        await deleteCategoryApi(key)
        if (selectedCategoryKeys.value[0] === key) {
          selectedCategoryKeys.value = []
          selectedTemplate.value = null
          templateYaml.value = ''
        }
        await loadTemplates()
        message.success(t('template.deleteSuccess'))
      } catch (error: any) {
        message.error(error?.response?.data?.message || t('template.saveFailed'))
      }
    }
  })
}

const handleSaveCategory = async () => {
  const name = categoryForm.value.name.trim()
  const codeInput = categoryForm.value.code.trim().toLowerCase()
  if (!name) {
    message.error(t('template.categoryNameRequired'))
    return
  }
  if (!codeInput) {
    message.error(t('template.categoryCodeRequired'))
    return
  }
  if (!isValidCategoryCode(codeInput)) {
    message.error(t('template.categoryCodeInvalid'))
    return
  }
  if (!isEditMode.value && findCategoryByKey(codeInput, categories.value)) {
    message.error(t('template.categoryCodeDuplicate'))
    return
  }

  try {
    if (isEditMode.value) {
      await updateCategoryApi(categoryForm.value.key, { name })
      message.success(t('template.saveSuccess'))
    } else {
      const parent = isSubCategory.value
        ? findCategoryByKey(categoryForm.value.parentKey, categories.value)
        : null
      const code = codeInput || normalizeCode(name)
      await createCategoryApi({
        name,
        code,
        parent_id: parent?.id
      })
      message.success(t('template.addSuccess'))
    }
    categoryModalVisible.value = false
    await loadTemplates()
  } catch (error: any) {
    message.error(error?.response?.data?.message || t('template.saveFailed'))
  }
}

const handleCategorySelect = (keys: string[]) => {
  selectedCategoryKeys.value = keys
  hideContextMenu()
  activeRightTab.value = 'content'

  const key = keys[0]
  if (!key) {
    selectedTemplate.value = null
    templateYaml.value = ''
    currentCategoryKey.value = ''
    defaultPolicyDraft.value = []
    return
  }

  if (key.startsWith('tpl:')) {
    const template = getTemplateByTreeKey(key)
    if (template) {
      selectTemplate(template)
      return
    }
    selectedTemplate.value = null
    templateYaml.value = ''
    defaultPolicyDraft.value = []
    return
  }

  currentCategoryKey.value = key
  selectedTemplate.value = null
  templateYaml.value = ''
  defaultPolicyDraft.value = []
}

const selectTemplate = (template: TemplateItem) => {
  selectedTemplate.value = template
  currentCategoryKey.value = template.category
  templateYaml.value = template.content || ''
  activeRightTab.value = 'content'
  loadDefaultPolicyDraft()
  loadNoticeRuleOptions()
}

const handleSave = async () => {
  const validatePolicyDraft = (): string[] => {
    const errs: string[] = []
    const names = new Set<string>()
    defaultPolicyDraft.value.forEach((item, idx) => {
      const row = idx + 1
      const name = String(item.name || '').trim()
      if (!name) errs.push(`第${row}条规则名称不能为空`)
      if (name) {
        if (names.has(name)) errs.push(`第${row}条规则名称重复: ${name}`)
        names.add(name)
      }
      if (!String(item.metric || '').trim()) errs.push(`第${row}条规则指标不能为空`)
      if (!['realtime_metric', 'periodic_metric'].includes(String(item.type))) errs.push(`第${row}条规则类型非法`)
      if (!['>', '>=', '<', '<=', '==', '!='].includes(String(item.operator || '').trim())) errs.push(`第${row}条规则操作符非法`)
      if (!Number.isFinite(Number(item.threshold))) errs.push(`第${row}条规则阈值必须是数字`)
      if (!['critical', 'warning', 'info'].includes(String(item.level || '').trim())) errs.push(`第${row}条规则级别非法`)
      if (Number(item.period) < 0) errs.push(`第${row}条规则周期不能小于0`)
      if (Number(item.times) < 1) errs.push(`第${row}条规则触发次数不能小于1`)
      if (!['core', 'extended'].includes(String(item.mode || '').trim())) errs.push(`第${row}条规则分组非法`)
    })
    return errs
  }
  const policyErrors = validatePolicyDraft()
  if (policyErrors.length) {
    message.error(policyErrors[0])
    return
  }
  syncPolicyDraftToYaml()

  const raw = templateYaml.value.trim()
  if (!raw) {
    message.warning('请输入模板内容')
    return
  }

  saving.value = true
  try {
    const normalized = normalizeTemplateYaml(raw, selectedTemplate.value?.category || currentCategoryKey.value)
    if (normalized.duplicates.length) {
      message.warning(`检测到重复 params 字段并自动去重: ${Array.from(new Set(normalized.duplicates)).join(', ')}`)
    }
    const savingFromPolicyTab = activeRightTab.value === 'default-policy' && Boolean(selectedTemplate.value)
    let finalApp = normalized.app
    let finalCategory = normalized.category
    let finalName = normalized.name
    let finalContent = normalized.content
    if (savingFromPolicyTab && selectedTemplate.value) {
      const doc = parseYamlObject(normalized.content)
      doc.app = selectedTemplate.value.app
      doc.category = selectedTemplate.value.category
      finalApp = selectedTemplate.value.app
      finalCategory = selectedTemplate.value.category
      finalName = getTemplateDisplayName(selectedTemplate.value) || normalized.name
      finalContent = yaml.dump(doc, { noRefs: true, sortKeys: false, lineWidth: -1 })
    }
    templateYaml.value = finalContent

    if (isNewTemplate.value) {
      const resp = await createTemplateApi({
        app: finalApp,
        name: finalName,
        category: finalCategory,
        content: finalContent
      })
      if (resp.code != 200) {
        message.error(resp.message || t('template.saveFailed'))
        return
      }
      message.success(t('template.addSuccess') || '添加成功')
      await loadTemplates()
      selectedCategoryKeys.value = [`tpl:${finalApp}`]
      const created = templates.value.find((t) => t.app === finalApp)
      if (created) selectTemplate(created)
      return
    }

    if (!selectedTemplate.value) return
    const resp = await updateTemplateApi(selectedTemplate.value.app, {
      name: finalName,
      category: finalCategory,
      content: finalContent
    })
    if (resp.code != 200) {
      message.error(resp.message || t('template.saveFailed'))
      return
    }
    message.success(t('template.saveSuccess'))
    await loadTemplates()
    selectedCategoryKeys.value = [`tpl:${selectedTemplate.value.app}`]
    const updated = templates.value.find((t) => t.app === selectedTemplate.value?.app)
    if (updated) selectTemplate(updated)
  } catch (error: any) {
    console.error('Save template error:', error)
    message.error(error?.message || t('template.saveFailed'))
  } finally {
    saving.value = false
  }
}

const handlePreview = () => {
  previewModalVisible.value = true
}

watch(
  () => defaultPolicyDraft.value,
  () => syncPolicyDraftToYaml(),
  { deep: true }
)

watch(
  () => templateYaml.value,
  (value) => {
    if (!selectedTemplate.value) return
    metricOptions.value = parseTemplateMetricOptions(value || selectedTemplate.value.content || '')
  }
)

watch(
  () => policyForm.value.metric,
  (metric, prevMetric) => {
    if (isBinaryMetric(metric) && !isBinaryMetric(String(prevMetric || ''))) {
      policyForm.value.operator = '=='
      policyForm.value.threshold = 0
      return
    }
    const normalized = normalizeBinaryRule(policyForm.value.metric, policyForm.value.operator, policyForm.value.threshold)
    policyForm.value.operator = normalized.operator
    policyForm.value.threshold = normalized.threshold
  }
)

onMounted(() => {
  loadTemplates()
  loadNoticeRuleOptions()
})
</script>

<style scoped lang="scss">
.monitoring-template-page {
  height: 100%;
  padding: 16px;
  background: var(--arco-app-bg);

  .template-layout {
    display: flex;
    height: calc(100vh - 120px);
    background: var(--app-surface-card);
    border-radius: 8px;
    box-shadow: var(--app-shadow-sm);
    overflow: hidden;

    .category-sidebar {
      width: 240px;
      border-right: 1px solid var(--app-border);
      background: var(--app-surface-subtle);
      display: flex;
      flex-direction: column;

      .sidebar-header {
        padding: 16px;
        border-bottom: 1px solid var(--app-border);
        display: flex;
        justify-content: space-between;
        align-items: center;

        .title {
          font-weight: 600;
          font-size: 16px;
          color: var(--app-text-primary);
        }
      }

      .category-tree {
        flex: 1;
        overflow-y: auto;
        padding: 8px;

        .tree-node {
          display: flex;
          align-items: center;
          gap: 8px;

          .node-name {
            flex: 1;
          }

          .node-count {
            color: var(--app-text-muted);
            font-size: 12px;
          }
        }
      }
    }

    .template-editor {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;

      .editor-header {
        padding: 16px;
        border-bottom: 1px solid var(--app-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: var(--app-surface-card);

        .header-left {
          display: flex;
          flex-direction: column;
          gap: 12px;

          .template-tabs {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;

            .template-tab {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 6px 12px;
              background: var(--app-surface-subtle);
              border-radius: 4px;
              cursor: pointer;
              transition: all 0.3s;
              color: var(--app-text-secondary);

              &:hover {
                background: color-mix(in srgb, var(--app-accent) 10%, var(--app-surface-card));
              }

              &.active {
                background: var(--app-accent);
                color: #fff;
              }

              .tab-name {
                font-size: 13px;
              }
            }
          }
        }

        .header-actions {
          display: flex;
          gap: 8px;
        }
      }

      .editor-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 16px;
        overflow: hidden;

        :deep(.ant-tabs) {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        :deep(.ant-tabs-content-holder) {
          flex: 1;
          overflow: hidden;
        }

        :deep(.ant-tabs-content) {
          height: 100%;
        }

        :deep(.ant-tabs-tabpane) {
          height: 100%;
        }

        .content-tab-pane {
          height: 100%;
          display: flex;
          flex-direction: column;
          min-height: 0;
        }

        .editor-toolbar {
          background: var(--app-surface-card);
          padding: 12px 16px;
          border-bottom: 1px solid var(--app-border);
          border-radius: 4px 4px 0 0;

          .template-name {
            font-weight: 500;
            margin-left: 8px;
            color: var(--app-text-primary);
          }
        }

        .code-editor-wrapper {
          flex: 1;
          min-height: 0;
          background: #1e1e1e;
          border-radius: 0 0 4px 4px;
          overflow: hidden;

          .code-textarea {
            width: 100%;
            height: 100%;
            padding: 16px;
            border: none;
            outline: none;
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: none;
            white-space: pre;
            overflow-wrap: normal;
            overflow: auto;
          }
        }

        .policy-content {
          height: 100%;
          overflow: auto;
          background: var(--app-surface-card);
          padding: 8px 4px;

          .policy-name-cell {
            display: flex;
            align-items: center;
            gap: 8px;
          }
        }
      }

      .empty-state {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
      }
    }
  }
}

// 右键菜单样式
.context-menu {
  position: fixed;
  z-index: 1000;
  background: var(--app-surface-card);
  border-radius: 4px;
  box-shadow: var(--app-shadow-sm);
  min-width: 160px;

  :deep(.ant-menu) {
    border: none;
    border-radius: 4px;
  }
}
</style>
