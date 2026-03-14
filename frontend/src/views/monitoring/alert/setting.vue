<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 工具栏 -->
      <a-row justify="space-between" align="middle">
        <a-space>
          <a-button @click="loadData" :loading="loading">
            <ReloadOutlined />
            刷新
          </a-button>
          <a-button type="primary" @click="openCreateRule">
            <PlusOutlined />
            新增配置
          </a-button>
          <a-dropdown>
            <a-button>
              <EllipsisOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="handleBatchDelete" :disabled="!selectedRowKeys.length">
                  <DeleteOutlined />
                  批量删除
                </a-menu-item>
                <a-menu-item @click="handleExport">
                  <ExportOutlined />
                  导出配置
                </a-menu-item>
                <a-menu-item>
                  <a-upload
                    :action="uploadAction"
                    :show-upload-list="false"
                    :before-upload="beforeUpload"
                    @change="handleUploadChange"
                  >
                    <ImportOutlined />
                    导入配置
                  </a-upload>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-space>
        <a-space>
          <a-select v-model:value="ruleScope" style="width: 160px" @change="handleScopeChange">
            <a-select-option value="global">全局规则</a-select-option>
            <a-select-option value="bound">实例规则</a-select-option>
            <a-select-option value="all">全部规则</a-select-option>
          </a-select>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索规则名称/表达式"
            style="width: 250px"
            @search="loadData"
            allow-clear
          />
        </a-space>
      </a-row>

      <!-- 数据表格 -->
      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="rules"
        :pagination="pagination"
        row-key="id"
        :row-selection="{ selectedRowKeys, onChange: onSelectChange }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 规则名称 -->
          <template v-if="column.key === 'name'">
            <a-space direction="vertical" size="small">
              <span style="font-weight: 500">{{ record.name }}</span>
              <a-tag v-if="record.level" :color="severityColor(record.level)">
                {{ record.level }}
              </a-tag>
            </a-space>
          </template>

          <!-- 规则类型 -->
          <template v-if="column.key === 'type'">
            <a-tag :color="typeColor(record.type || record.monitor_type)">
              {{ typeText(record.type || record.monitor_type) }}
            </a-tag>
          </template>

          <!-- 表达式 -->
          <template v-if="column.key === 'expr'">
            <a-typography-text ellipsis style="max-width: 200px" :title="record.expr || `${record.metric || 'value'} ${record.operator || '>'} ${record.threshold ?? 0}`">
              {{ record.expr || `${record.metric || 'value'} ${record.operator || '>'} ${record.threshold ?? 0}` }}
            </a-typography-text>
          </template>

          <!-- 通知规则 -->
          <template v-if="column.key === 'notice_rule'">
            <a-space v-if="(record.notice_rule_ids || []).length" wrap>
              <a-tag
                v-for="ruleId in record.notice_rule_ids"
                :key="ruleId"
                size="small"
                color="blue"
              >
                {{ getNoticeRuleName(ruleId) }}
              </a-tag>
            </a-space>
            <a-space v-else-if="record.notice_rule" direction="vertical" size="small">
              <span style="font-weight: 500">{{ record.notice_rule.name }}</span>
              <a-tag v-if="record.notice_rule.receiver_name" size="small" color="blue">
                {{ record.notice_rule.receiver_name }}
              </a-tag>
            </a-space>
            <a-tag v-else color="default">未配置</a-tag>
          </template>

          <!-- 标签 -->
          <template v-if="column.key === 'labels'">
            <a-space wrap>
              <a-tag v-for="(value, key) in record.labels" :key="key" size="small">
                {{ key }}: {{ value }}
              </a-tag>
            </a-space>
          </template>

          <!-- 触发配置 -->
          <template v-if="column.key === 'trigger'">
            <a-space direction="vertical" size="small">
              <span>连续 {{ record.times }} 次触发</span>
              <span v-if="record.period">周期: {{ record.period }}s</span>
            </a-space>
          </template>

          <!-- 启用状态 -->
          <template v-if="column.key === 'enabled'">
            <a-switch
              :checked="record.enabled"
              @change="(checked: boolean) => toggleEnabled(record, checked)"
            />
          </template>

          <!-- 操作 -->
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)">
                <EditOutlined />
                编辑
              </a-button>
              <a-popconfirm
                title="确认删除该规则？"
                @confirm="handleDelete(record)"
                ok-text="确认"
                cancel-text="取消"
              >
                <a-button type="link" size="small" danger>
                  <DeleteOutlined />
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <!-- 规则编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingRule?.id ? '编辑告警规则' : '新增告警规则'"
      width="800px"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="handleCancel"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        layout="vertical"
      >
        <!-- 基本信息 -->
        <a-divider orientation="left">基本信息</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="规则名称" name="name">
              <a-input v-model:value="formState.name" placeholder="请输入规则名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="规则类型">
              <a-select v-model:value="formState.type">
                <a-select-option value="realtime_metric">实时指标</a-select-option>
                <a-select-option value="periodic_metric">周期指标</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">规则条件</a-divider>
        <a-row :gutter="12">
          <a-col :span="10">
            <a-form-item label="监控指标" extra="支持派生变量：<app>_server_up（可用性）与 *_ok（字符串状态映射为1/0）">
              <a-select v-model:value="formState.metric" show-search option-filter-prop="label" placeholder="请选择模板指标">
                <a-select-option v-for="opt in metricOptions" :key="opt.value" :value="opt.value" :label="opt.label">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="操作符">
              <a-select v-model:value="formState.operator">
                <template v-if="isBinaryMetricSelected">
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
          <a-col :span="8">
            <a-form-item :label="isBinaryMetricSelected ? '状态值' : '阈值'" :extra="isBinaryMetricSelected ? '0=异常，1=正常' : undefined">
              <a-select v-if="isBinaryMetricSelected" v-model:value="formState.threshold">
                <a-select-option :value="0">0（异常）</a-select-option>
                <a-select-option :value="1">1（正常）</a-select-option>
              </a-select>
              <a-input-number v-else v-model:value="formState.threshold" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 触发配置 -->
        <a-divider orientation="left">触发配置</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="连续触发次数" name="times" extra="连续多少次满足条件才触发告警">
              <a-input-number v-model:value="formState.times" :min="1" :max="10" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="告警级别" name="severity">
              <a-select v-model:value="formState.level">
                <a-select-option value="critical">紧急 (Critical)</a-select-option>
                <a-select-option value="warning">警告 (Warning)</a-select-option>
                <a-select-option value="info">信息 (Info)</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">高级表达式</a-divider>
        <a-form-item>
          <a-space>
            <a-switch v-model:checked="formUseCustomExpr" />
            <span>高级模式：自定义表达式</span>
          </a-space>
        </a-form-item>
        <a-form-item v-if="formUseCustomExpr" label="表达式" name="expr">
          <a-textarea v-model:value="formState.expr" :rows="3" placeholder="例如：(used_memory / maxmemory) * 100 > 85" />
        </a-form-item>

        <a-divider orientation="left">监控标签</a-divider>
        <a-form-item label="标签" extra="用于告警分组和路由">
          <a-space direction="vertical" style="width: 100%">
            <a-row v-for="(tag, index) in tagList" :key="index" :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="tag.key" placeholder="标签名" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="tag.value" placeholder="标签值" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeTag(index)">
                  <DeleteOutlined />
                </a-button>
              </a-col>
            </a-row>
            <a-button type="dashed" block @click="addTag">
              <PlusOutlined />
              添加标签
            </a-button>
          </a-space>
        </a-form-item>

        <!-- 通知配置 -->
        <a-divider orientation="left">通知配置</a-divider>
        <a-form-item label="通知规则" extra="选择告警触发时使用的通知规则（可多选）">
          <a-select
            v-model:value="formState.notice_rule_ids"
            mode="multiple"
            placeholder="请选择通知规则"
            allow-clear
            style="width: 100%"
            show-search
            option-filter-prop="label"
          >
            <a-select-option v-for="rule in noticeRules" :key="rule.id" :value="rule.id" :label="rule.name">
              <a-space>
                <span>{{ rule.name }}</span>
                <a-tag v-if="rule.receiver_name" size="small" color="blue">
                  {{ rule.receiver_name }}
                </a-tag>
              </a-space>
            </a-select-option>
          </a-select>
          <div class="form-help">
            没有合适的规则？<a @click="goToNoticeConfig">去配置通知规则</a>
          </div>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="自动恢复关闭">
              <a-switch v-model:checked="formState.auto_recover" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="恢复次数(N)">
              <a-input-number v-model:value="formState.recover_times" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="发送恢复通知">
              <a-switch v-model:checked="formState.notify_on_recovered" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">告警升级</a-divider>
        <a-form-item label="启用告警升级" extra="告警持续未处理时，按阶梯延时升级通知">
          <a-switch v-model:checked="formState.escalation_enabled" />
        </a-form-item>
        <a-space v-if="formState.escalation_enabled" direction="vertical" style="width: 100%" :size="8">
          <a-card
            v-for="(level, idx) in escalationLevels"
            :key="idx"
            size="small"
            :title="`Level ${idx + 1}`"
          >
            <a-row :gutter="12">
              <a-col :span="8">
                <a-form-item label="等待时间(秒)">
                  <a-input-number v-model:value="level.delay_seconds" :min="1" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :span="16">
                <a-form-item label="升级通知规则">
                  <a-select
                    v-model:value="level.notice_rule_ids"
                    mode="multiple"
                    allow-clear
                    placeholder="不填则回退本规则通知配置"
                  >
                    <a-select-option v-for="rule in noticeRules" :key="rule.id" :value="Number(rule.id)">
                      {{ rule.name }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="12">
              <a-col :span="24">
                <a-form-item label="升级标题模板">
                  <a-input v-model:value="level.title_template" placeholder="示例: [Level {{level}}] {{rule_name}}" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="12">
              <a-col :span="24">
                <a-form-item label="升级内容模板">
                  <a-textarea v-model:value="level.content_template" :rows="2" placeholder="示例: 告警 {{rule_name}} 在 {{instance}} 持续未恢复" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-button danger type="link" @click="removeEscalationLevel(idx)">删除该级</a-button>
          </a-card>
          <a-button type="dashed" block @click="addEscalationLevel">
            <PlusOutlined />
            新增升级级别
          </a-button>
        </a-space>

        <!-- 消息模板 -->
        <a-divider orientation="left">消息模板</a-divider>
        <a-form-item label="告警标题模板" name="title_template" extra="支持变量: {{$severity}}, {{$rule_name}}, {{$labels.app}}, {{$labels.instance}}">
          <a-input
            v-model:value="formState.title_template"
            placeholder="示例: [{{$severity}}] {{$rule_name}} - {{$labels.app}}/{{$labels.instance}}"
          />
        </a-form-item>
        <a-form-item label="告警内容模板" name="template" extra="支持变量: {{$labels.instance}}, {{$value}} 等">
          <a-textarea
            v-model:value="formState.template"
            :rows="3"
            placeholder="示例: 实例 {{$labels.instance}} 的 CPU 使用率达到 {{$value}}%"
          />
        </a-form-item>

        <!-- 模板变量参考 -->
        <a-collapse ghost>
          <a-collapse-panel key="1" header="模板变量参考">
            <a-descriptions :column="2" size="small" bordered>
              <a-descriptions-item label="${__instance__}">监控实例ID</a-descriptions-item>
              <a-descriptions-item label="${__instancename__}">监控实例名称</a-descriptions-item>
              <a-descriptions-item label="${__instancehost__}">监控目标主机</a-descriptions-item>
              <a-descriptions-item label="${__app__}">应用类型</a-descriptions-item>
              <a-descriptions-item label="${__metrics__}">指标集名称</a-descriptions-item>
              <a-descriptions-item label="${__labels__}">标签集合</a-descriptions-item>
              <a-descriptions-item label="${__value__}">指标值</a-descriptions-item>
            </a-descriptions>
          </a-collapse-panel>
        </a-collapse>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import * as yaml from 'js-yaml'
import {
  ReloadOutlined,
  PlusOutlined,
  EllipsisOutlined,
  DeleteOutlined,
  EditOutlined,
  ExportOutlined,
  ImportOutlined
} from '@ant-design/icons-vue'
import {
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  enableAlertRule,
  disableAlertRule,
  getAlertNotices,
  getTemplates,
  type AlertRule,
  type AlertNotice,
  type MonitorTemplate
} from '@/api/monitoring'

const DEFAULT_ALERT_CONTENT_TEMPLATE = `[{{$severity}}] {{$rule_name}}
应用: {{$labels.app}}
实例: {{$labels.instance}}
指标: {{$labels.metric}}
当前值: {{$value}}
触发条件: {{$expression}}`
const DEFAULT_ALERT_TITLE_TEMPLATE = `[{{$severity}}] {{$rule_name}} - {{$labels.app}}/{{$labels.instance}}`

// 表格列定义
const columns = [
  { title: '规则名称', key: 'name', width: 180 },
  { title: '类型', key: 'type', width: 140 },
  { title: '表达式', key: 'expr', width: 200 },
  { title: '通知规则', key: 'notice_rule', width: 150 },
  { title: '标签', key: 'labels', width: 150 },
  { title: '触发配置', key: 'trigger', width: 120 },
  { title: '启用', key: 'enabled', width: 80, align: 'center' },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' }
]

// 状态
const loading = ref(false)
const saving = ref(false)
const rules = ref<AlertRule[]>([])
const searchKeyword = ref('')
const selectedRowKeys = ref<number[]>([])
const selectedRows = ref<AlertRule[]>([])
const noticeRules = ref<AlertNotice[]>([])
const ruleScope = ref<'global' | 'bound' | 'all'>('global')
const noticeRuleMap = computed(() => {
  const map = new Map<number, AlertNotice>()
  noticeRules.value.forEach(rule => {
    map.set(rule.id, rule)
  })
  return map
})

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 弹窗状态
const modalVisible = ref(false)
const editingRule = ref<AlertRule | null>(null)
const formRef = ref<FormInstance>()
const formUseCustomExpr = ref(false)
const templates = ref<MonitorTemplate[]>([])
const metricOptions = ref<{ value: string; label: string }[]>([{ value: 'value', label: 'value' }])

// 表单状态
const formState = reactive<Partial<AlertRule>>({
  name: '',
  type: 'realtime_metric',
  expr: '',
  period: 60,
  times: 1,
  metric: 'value',
  operator: '>',
  threshold: 0,
  level: 'warning',
  labels: {},
  annotations: {},
  title_template: '',
  template: '',
  datasource_type: 'promql',
  enabled: true,
  auto_recover: true,
  recover_times: 2,
  notify_on_recovered: true,
  escalation_enabled: false,
  notice_rule_id: undefined,
  notice_rule_ids: []
})

const escalationLevels = ref<Array<{
  level: number
  delay_seconds: number
  notice_rule_ids: number[]
  title_template: string
  content_template: string
}>>([])

// 标签列表
const tagList = ref<{ key: string; value: string }[]>([])

// 表单校验规则
const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  period: [{ required: true, message: '请输入执行周期', trigger: 'blur' }]
}

// 上传地址
const uploadAction = `${(import.meta as any).env?.VITE_API_BASE_URL || ''}/monitoring/alert-rules/import`

// 类型文本映射
const typeText = (type?: string) => {
  const map: Record<string, string> = {
    realtime_metric: '实时指标',
    periodic_metric: '周期指标'
  }
  return map[type || ''] || type
}

// 类型颜色映射
const typeColor = (type?: string) => {
  const map: Record<string, string> = {
    realtime_metric: 'blue',
    periodic_metric: 'green'
  }
  return map[type || ''] || 'default'
}

// 严重级别颜色
const severityColor = (severity?: string) => {
  const map: Record<string, string> = {
    critical: 'red',
    warning: 'orange',
    info: 'blue'
  }
  return map[severity || ''] || 'default'
}

const getNoticeRuleName = (id: number) => {
  const item = noticeRuleMap.value.get(id)
  return item?.name || `#${id}`
}

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const isBinaryMetric = (metric?: string) => {
  const key = String(metric || '').trim().toLowerCase()
  return key.endsWith('_ok') || key.endsWith('_up')
}

const isBinaryMetricSelected = computed(() => isBinaryMetric(String(formState.metric || '')))

const normalizeBinaryRule = (metric: string, operator: string, threshold: number) => {
  if (!isBinaryMetric(metric)) return { operator: String(operator || '>').trim() || '>', threshold: Number(threshold ?? 0) || 0 }
  const op = String(operator || '==').trim() || '=='
  if (op === '<' || op === '<=') return { operator: '==', threshold: 0 }
  if (op === '>' || op === '>=') return { operator: '==', threshold: 1 }
  if (op === '!=') return { operator: '!=', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
  return { operator: '==', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
}

const buildExpr = () => {
  const metric = String(formState.metric || 'value').trim() || 'value'
  const normalized = normalizeBinaryRule(metric, String(formState.operator || '>'), Number(formState.threshold || 0))
  return `${metric} ${normalized.operator} ${normalized.threshold}`
}

const parseTemplateMetricOptions = (content: string): { value: string; label: string }[] => {
  try {
    const doc = (yaml.load(content || '') || {}) as any
    if (!doc || typeof doc !== 'object') return [{ value: 'value', label: 'value' }]
    const options = new Map<string, { value: string; label: string }>()
    const appName = String(doc.app || '').trim()
    const groups = Array.isArray(doc.metrics) ? doc.metrics : []
    const pickI18nText = (value: any) => {
      if (typeof value === 'string') return value.trim()
      if (!value || typeof value !== 'object') return ''
      return String(value['zh-CN'] || value['en-US'] || value['zh'] || value['en'] || '').trim()
    }
    for (const group of groups) {
      const groupName = String(group?.name || '').trim()
      const groupTitle = pickI18nText(group?.i18n || group?.name) || groupName
      const fields = Array.isArray(group?.fields) ? group.fields : []
      for (const field of fields) {
        const fieldName = String(field?.field || field?.metric || '').trim()
        if (!fieldName) continue
        const fieldTitle = pickI18nText(field?.i18n || field?.name) || fieldName
        const label = groupTitle ? `${groupTitle} / ${fieldTitle} (${fieldName})` : `${fieldTitle} (${fieldName})`
        options.set(fieldName, { value: fieldName, label })
        if (Number(field?.type) === 1) {
          const okField = `${fieldName}_ok`
          options.set(okField, { value: okField, label: `${groupTitle || fieldTitle} / ${fieldTitle} 状态OK (${okField})` })
        }
      }
    }
    if (appName) options.set(`${appName}_server_up`, { value: `${appName}_server_up`, label: `实例可用性 (${appName}_server_up)` })
    if (!options.size) options.set('value', { value: 'value', label: 'value' })
    return Array.from(options.values())
  } catch {
    return [{ value: 'value', label: 'value' }]
  }
}

const loadTemplates = async () => {
  try {
    const res = await getTemplates()
    templates.value = Array.isArray((res as any)?.data) ? (res as any).data : []
    const options = new Map<string, { value: string; label: string }>()
    options.set('value', { value: 'value', label: 'value' })
    for (const tpl of templates.value) {
      for (const opt of parseTemplateMetricOptions(String(tpl.content || ''))) {
        options.set(opt.value, opt)
      }
    }
    metricOptions.value = Array.from(options.values())
  } catch {
    templates.value = []
    metricOptions.value = [{ value: 'value', label: 'value' }]
  }
}

// 加载通知规则列表
const loadNoticeRules = async () => {
  try {
    const res = await getAlertNotices({ page_size: 1000 })
    const parsed = normalizeList((res as any)?.data ?? res)
    noticeRules.value = parsed.items
  } catch (error: any) {
    console.error('加载通知规则失败:', error)
    noticeRules.value = []
  }
}

// 跳转到通知规则配置
const goToNoticeConfig = () => {
  window.open('/alert-center/notice', '_blank')
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertRules({
      q: searchKeyword.value,
      include_bound: ruleScope.value !== 'global',
      scope: ruleScope.value,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    const parsed = normalizeList((res as any)?.data ?? res)
    rules.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleScopeChange = () => {
  pagination.current = 1
  selectedRowKeys.value = []
  selectedRows.value = []
  loadData()
}

// 表格选择变化
const onSelectChange = (keys: number[], rows: AlertRule[]) => {
  selectedRowKeys.value = keys
  selectedRows.value = rows
}

// 表格分页变化
const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

const openCreateRule = async () => {
  editingRule.value = null
  resetForm()
  await Promise.all([loadNoticeRules(), loadTemplates()])
  if (metricOptions.value.length) {
    formState.metric = metricOptions.value[0].value
    const normalized = normalizeBinaryRule(String(formState.metric || 'value'), String(formState.operator || '>'), Number(formState.threshold || 0))
    formState.operator = normalized.operator
    formState.threshold = normalized.threshold
  }
  modalVisible.value = true
}

// 重置表单
const resetForm = () => {
  formState.name = ''
  formState.type = 'realtime_metric'
  formState.expr = ''
  formState.metric = 'value'
  formState.operator = '>'
  formState.threshold = 0
  formState.level = 'warning'
  formState.period = 60
  formState.times = 1
  formState.labels = {}
  formState.annotations = {}
  formState.title_template = DEFAULT_ALERT_TITLE_TEMPLATE
  formState.template = DEFAULT_ALERT_CONTENT_TEMPLATE
  formState.datasource_type = 'promql'
  formState.enabled = true
  formState.auto_recover = true
  formState.recover_times = 2
  formState.notify_on_recovered = true
  formState.escalation_enabled = false
  formState.notice_rule_id = undefined
  formState.notice_rule_ids = []
  escalationLevels.value = []
  tagList.value = []
  formUseCustomExpr.value = false
}

// 编辑规则
const handleEdit = (record: AlertRule) => {
  editingRule.value = record
  const metric = String((record as any).metric || 'value')
  const normalized = normalizeBinaryRule(metric, String((record as any).operator || '>'), Number((record as any).threshold || 0))
  Object.assign(formState, {
    name: record.name,
    type: ((record as any).type || (record as any).monitor_type || 'realtime_metric'),
    expr: (record as any).expr || '',
    metric,
    operator: normalized.operator,
    threshold: normalized.threshold,
    level: String((record as any).level || 'warning'),
    period: Number((record as any).period || 60),
    times: Number((record as any).times || 1),
    labels: { ...((record as any).labels || {}) },
    annotations: { ...((record as any).annotations || {}) },
    title_template: String((record as any).title_template || ((record as any).annotations || {}).title_template || ''),
    template: record.template,
    datasource_type: (record as any).datasource_type || 'promql',
    enabled: record.enabled,
    auto_recover: (record as any).auto_recover !== false,
    recover_times: Math.max(Number((record as any).recover_times || 2), 1),
    notify_on_recovered: (record as any).notify_on_recovered !== false,
    escalation_enabled: Boolean((record as any).escalation_config?.enabled),
    notice_rule_id: (record as any).notice_rule_id,
    notice_rule_ids: (record as any).notice_rule_ids && (record as any).notice_rule_ids.length
        ? [...(record as any).notice_rule_ids]
        : (record as any).notice_rule_id
          ? [(record as any).notice_rule_id]
          : []
  })
  escalationLevels.value = Array.isArray((record as any).escalation_config?.levels)
    ? ((record as any).escalation_config.levels as any[])
      .map((item: any, idx: number) => ({
        level: Number(item?.level || idx + 1),
        delay_seconds: Math.max(Number(item?.delay_seconds || 300), 1),
        notice_rule_ids: Array.isArray(item?.notice_rule_ids) ? item.notice_rule_ids.map((v: any) => Number(v)).filter((v: number) => v > 0) : [],
        title_template: String(item?.title_template || ''),
        content_template: String(item?.content_template || '')
      }))
    : []
  // 转换标签列表
  tagList.value = Object.entries(((record as any).labels || {}) as Record<string, string>)
    .filter(([key]) => !['severity', 'auto_recover', 'recover_times', 'notify_on_recovered'].includes(String(key)))
    .map(([key, value]) => ({ key, value }))
  formUseCustomExpr.value = Boolean(String((record as any).expr || '').trim())
  if (!metricOptions.value.some((item) => item.value === metric)) {
    metricOptions.value = [...metricOptions.value, { value: metric, label: metric }]
  }
  modalVisible.value = true
}

// 保存规则
const handleSave = async () => {
  try {
    await formRef.value?.validate()
    if (formState.escalation_enabled && !escalationLevels.value.length) {
      message.warning('已启用告警升级，请至少配置一个升级级别')
      return
    }
    saving.value = true

    // 构建标签
    const labels: Record<string, any> = { ...(formState.labels || {}) }
    labels.metric = String(formState.metric || 'value').trim() || 'value'
    labels.operator = String(formState.operator || '>').trim() || '>'
    labels.threshold = Number(formState.threshold || 0)
    labels.severity = String(formState.level || 'warning')
    labels.auto_recover = formState.auto_recover !== false
    labels.recover_times = Math.max(Number(formState.recover_times || 2), 1)
    labels.notify_on_recovered = formState.notify_on_recovered !== false
    tagList.value.forEach(tag => {
      if (tag.key && tag.value) {
        labels[tag.key] = tag.value
      }
    })

    const normalized = normalizeBinaryRule(String(formState.metric || 'value'), String(formState.operator || '>'), Number(formState.threshold || 0))
    const expr = formUseCustomExpr.value
      ? (String(formState.expr || '').trim() || buildExpr())
      : `${String(formState.metric || 'value').trim() || 'value'} ${normalized.operator} ${normalized.threshold}`

    const data = {
      ...formState,
      type: formState.type,
      monitor_type: formState.type,
      metric: String(formState.metric || 'value').trim() || 'value',
      operator: normalized.operator,
      threshold: normalized.threshold,
      level: String(formState.level || 'warning'),
      expr,
      labels,
      annotations: {
        ...(formState.annotations || {}),
        ...(String(formState.title_template || '').trim() ? { title_template: String(formState.title_template || '').trim() } : {})
      },
      escalation_config: (formState as any).escalation_enabled
        ? {
          enabled: true,
          levels: escalationLevels.value.map((item, idx) => ({
            level: idx + 1,
            delay_seconds: Math.max(Number(item.delay_seconds || 0), 1),
            notice_rule_ids: Array.isArray(item.notice_rule_ids) ? item.notice_rule_ids.filter((id) => Number(id) > 0).map((id) => Number(id)) : [],
            title_template: String(item.title_template || '').trim(),
            content_template: String(item.content_template || '').trim()
          }))
        }
        : { enabled: false, levels: [] as any[] },
      title_template: String(formState.title_template || '').trim(),
      auto_recover: formState.auto_recover !== false,
      recover_times: Math.max(Number(formState.recover_times || 2), 1),
      notify_on_recovered: formState.notify_on_recovered !== false
    }

    if (editingRule.value?.id) {
      await updateAlertRule(editingRule.value.id, data)
      message.success('更新成功')
    } else {
      await createAlertRule(data)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (error: any) {
    if (error?.response?.data?.message) {
      message.error(error.response.data.message)
    }
  } finally {
    saving.value = false
  }
}

// 取消编辑
const handleCancel = () => {
  modalVisible.value = false
  formRef.value?.resetFields()
}

// 切换启用状态
const toggleEnabled = async (record: AlertRule & { toggling?: boolean }, enabled: boolean) => {
  record.toggling = true
  try {
    if (enabled) {
      await enableAlertRule(record.id)
    } else {
      await disableAlertRule(record.id)
    }
    record.enabled = enabled
    message.success(enabled ? '已启用' : '已禁用')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
    record.enabled = !enabled
  } finally {
    record.toggling = false
  }
}

// 删除规则
const handleDelete = async (record: AlertRule) => {
  try {
    await deleteAlertRule(record.id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

// 批量删除
const handleBatchDelete = () => {
  if (!selectedRowKeys.value.length) {
    message.warning('请选择要删除的规则')
    return
  }
  Modal.confirm({
    title: '确认批量删除',
    content: `确定要删除选中的 ${selectedRowKeys.value.length} 条规则吗？`,
    onOk: async () => {
      try {
        // 这里应该调用批量删除API
        for (const id of selectedRowKeys.value) {
          await deleteAlertRule(id)
        }
        message.success('批量删除成功')
        selectedRowKeys.value = []
        loadData()
      } catch (error: any) {
        message.error(error?.response?.data?.message || '删除失败')
      }
    }
  })
}

// 导出配置
const handleExport = () => {
  message.info('导出功能开发中...')
}

// 上传前检查
const beforeUpload = (file: File) => {
  const isJson = file.type === 'application/json' || file.name.endsWith('.json')
  if (!isJson) {
    message.error('请上传 JSON 文件')
  }
  return isJson
}

// 上传状态变化
const handleUploadChange = (info: any) => {
  if (info.file.status === 'done') {
    message.success('导入成功')
    loadData()
  } else if (info.file.status === 'error') {
    message.error('导入失败')
  }
}

// 添加标签
const addTag = () => {
  tagList.value.push({ key: '', value: '' })
}

// 移除标签
const removeTag = (index: number) => {
  tagList.value.splice(index, 1)
}

const addEscalationLevel = () => {
  escalationLevels.value.push({
    level: escalationLevels.value.length + 1,
    delay_seconds: 300,
    notice_rule_ids: [],
    title_template: '',
    content_template: ''
  })
}

const removeEscalationLevel = (index: number) => {
  escalationLevels.value.splice(index, 1)
  escalationLevels.value = escalationLevels.value.map((item, idx) => ({ ...item, level: idx + 1 }))
}

onMounted(() => {
  loadTemplates()
  loadData()
  loadNoticeRules()
})

watch(
  () => formState.metric,
  (metric, prevMetric) => {
    if (isBinaryMetric(String(metric || '')) && !isBinaryMetric(String(prevMetric || ''))) {
      formState.operator = '=='
      formState.threshold = 0
      return
    }
    const normalized = normalizeBinaryRule(String(formState.metric || 'value'), String(formState.operator || '>'), Number(formState.threshold || 0))
    formState.operator = normalized.operator
    formState.threshold = normalized.threshold
  }
)
</script>
