<template>
  <div class="monitor-target-detail-page">
    <a-card :bordered="false">
      <div class="detail-header">
        <a-space>
          <a-button @click="goBack">返回列表</a-button>
          <a-button :loading="loading" @click="reloadDetail">刷新</a-button>
        </a-space>
        <a-space v-if="targetDetail">
          <a-tag color="blue">{{ targetDetail.app || '-' }}</a-tag>
          <a-tag :color="targetDetail.enabled === false ? 'default' : 'green'">
            {{ targetDetail.enabled === false ? 'disabled' : 'enabled' }}
          </a-tag>
        </a-space>
      </div>

      <a-spin :spinning="loading">
        <a-empty v-if="!targetDetail" description="监控任务不存在或已删除" />
        <a-tabs v-else v-model:activeKey="detailTab">
          <a-tab-pane key="basic" tab="基本信息">
            <a-descriptions bordered :column="2" size="small">
              <a-descriptions-item label="任务ID">{{ targetDetail.id }}</a-descriptions-item>
              <a-descriptions-item label="任务标识">{{ targetDetail.job_id || '-' }}</a-descriptions-item>
              <a-descriptions-item label="名称">{{ targetDetail.name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="模板(app)">{{ targetDetail.app || '-' }}</a-descriptions-item>
              <a-descriptions-item label="CI编码">{{ targetDetail.ci_code || '-' }}</a-descriptions-item>
              <a-descriptions-item label="CI名称">{{ targetDetail.ci_name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="目标地址">{{ targetDetail.target || '-' }}</a-descriptions-item>
              <a-descriptions-item label="采集间隔">{{ normalizedInterval(targetDetail) }}s</a-descriptions-item>
              <a-descriptions-item label="状态">
                <a-tag :color="targetDetail.enabled === false ? 'default' : 'green'">
                  {{ targetDetail.enabled === false ? 'disabled' : 'enabled' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="创建时间">{{ targetDetail.created_at || '-' }}</a-descriptions-item>
            </a-descriptions>
          </a-tab-pane>

          <a-tab-pane key="metrics" tab="指标">
            <MonitorMetricsPanel
              v-if="targetDetail"
              :key="`metrics-${targetDetail.id}-${metricsPanelVersion}`"
              :monitor-id="targetDetail.id"
              :app="String(targetDetail.app || '')"
              :interval-seconds="normalizedInterval(targetDetail)"
              :template-content="targetTemplateContent"
              :monitor-name="String(targetDetail.name || '')"
              :target="String(targetDetail.target || '')"
              :ci-code="String(targetDetail.ci_code || '')"
            />
          </a-tab-pane>

          <a-tab-pane key="alerts" tab="告警">
            <a-space direction="vertical" style="width: 100%" :size="12">
              <a-spin :spinning="targetAlertSummaryLoading">
                <a-row :gutter="12">
                  <a-col :span="4"><a-statistic title="当前告警" :value="targetAlertSummary.open_total" /></a-col>
                  <a-col :span="4"><a-statistic title="Critical" :value="targetAlertSummary.critical_total" value-style="color: #cf1322" /></a-col>
                  <a-col :span="4"><a-statistic title="Warning" :value="targetAlertSummary.warning_total" value-style="color: #d48806" /></a-col>
                  <a-col :span="4"><a-statistic title="Info" :value="targetAlertSummary.info_total" value-style="color: #1677ff" /></a-col>
                  <a-col :span="8"><a-statistic title="最近24h历史告警" :value="targetAlertSummary.history_24h" /></a-col>
                </a-row>
              </a-spin>

              <a-space>
                <a-button :loading="targetAlertLoading || targetAlertSummaryLoading" @click="refreshTargetAlerts">刷新规则</a-button>
                <a-button type="primary" :disabled="!canEdit || !targetDetail?.id" @click="applyDefaultAlertRulesForTarget">应用默认规则</a-button>
                <a-button type="primary" ghost :disabled="!canEdit || !targetDetail?.id" @click="openCreateTargetAlertRule">新增规则</a-button>
                <a-button :disabled="!canEdit || !targetDetail?.id" @click="restoreDefaultAlertRulesForTarget">恢复默认</a-button>
                <a-button :disabled="!canEdit || !targetAlertSelectedRuleIds.length" @click="batchUpdateTargetAlertRules(true)">批量启用</a-button>
                <a-button :disabled="!canEdit || !targetAlertSelectedRuleIds.length" @click="batchUpdateTargetAlertRules(false)">批量禁用</a-button>
                <a-button danger :disabled="!canEdit || !targetAlertSelectedRuleIds.length" @click="batchDeleteTargetAlertRules">批量删除</a-button>
              </a-space>

              <a-card size="small" title="最近告警变更">
                <a-empty v-if="!targetAlertSummary.recent.length" description="暂无告警变更" />
                <a-table
                  v-else
                  size="small"
                  :pagination="false"
                  :data-source="targetAlertSummary.recent"
                  :row-key="(record: any) => String(record.id)"
                >
                  <a-table-column title="级别" data-index="level" key="level" width="90" />
                  <a-table-column title="状态" data-index="status" key="status" width="90" />
                  <a-table-column title="名称" data-index="name" key="name">
                    <template #default="{ record }">
                      <a-button type="link" size="small" @click="openAlertDetail(record)">
                        {{ record?.name || '-' }}
                      </a-button>
                    </template>
                  </a-table-column>
                  <a-table-column title="触发时间" data-index="triggered_at" key="triggered_at" width="180" />
                </a-table>
              </a-card>

              <a-table
                :loading="targetAlertLoading"
                :data-source="targetAlertRules"
                :pagination="false"
                row-key="id"
                size="small"
                :row-selection="targetAlertRowSelection"
              >
                <a-table-column title="规则名称" data-index="name" key="name" />
                <a-table-column title="类型" data-index="monitor_type" key="monitor_type" width="120" />
                <a-table-column title="分组" key="rule_group" width="100">
                  <template #default="{ record }">
                    <a-tag :color="ruleGroupTagColor(record)">{{ ruleGroupText(record) }}</a-tag>
                  </template>
                </a-table-column>
                <a-table-column title="表达式" data-index="expr" key="expr" ellipsis />
                <a-table-column title="级别" data-index="level" key="level" width="90" />
                <a-table-column title="来源" data-index="scope" key="scope" width="80" />
                <a-table-column title="启用" key="enabled" width="90">
                  <template #default="{ record }">
                    <a-switch
                      :checked="record.enabled !== false"
                      :disabled="!canEdit"
                      @change="(checked: boolean) => toggleTargetAlertRule(record, checked)"
                    />
                  </template>
                </a-table-column>
                <a-table-column title="操作" key="actions" width="130">
                  <template #default="{ record }">
                    <a-space :size="4">
                      <a-button type="link" size="small" :disabled="!canEdit" @click="openTargetAlertRuleEditor(record)">编辑</a-button>
                      <a-popconfirm title="确认删除该规则？" @confirm="removeTargetAlertRule(record)">
                        <a-button type="link" size="small" danger :disabled="!canEdit">删除</a-button>
                      </a-popconfirm>
                    </a-space>
                  </template>
                </a-table-column>
              </a-table>
            </a-space>
          </a-tab-pane>
        </a-tabs>
      </a-spin>
    </a-card>

    <a-modal
      v-model:open="targetAlertEditorOpen"
      :title="editingTargetAlertRule?.id ? '编辑实例告警规则' : '新增实例告警规则'"
      width="640px"
      :confirm-loading="targetAlertSaving"
      @ok="saveTargetAlertRule"
    >
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="规则名称" required>
              <a-input v-model:value="targetAlertForm.name" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="规则类型">
              <a-select v-model:value="targetAlertForm.type">
                <a-select-option value="realtime_metric">实时指标</a-select-option>
                <a-select-option value="periodic_metric">周期指标</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="12">
          <a-col :span="10">
            <a-form-item label="监控指标" extra="支持派生变量：<app>_server_up（可用性）与 *_ok（字符串状态映射为1/0）">
              <a-select v-model:value="targetAlertForm.metric" show-search option-filter-prop="label" placeholder="请选择模板指标">
                <a-select-option v-for="opt in targetAlertMetricOptions" :key="opt.value" :value="opt.value" :label="opt.label">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="操作符">
              <a-select v-model:value="targetAlertForm.operator">
                <template v-if="targetAlertIsBinaryMetric">
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
            <a-form-item :label="targetAlertIsBinaryMetric ? '状态值' : '阈值'" :extra="targetAlertIsBinaryMetric ? '0=异常，1=正常' : undefined">
              <a-select v-if="targetAlertIsBinaryMetric" v-model:value="targetAlertForm.threshold">
                <a-select-option :value="0">0（异常）</a-select-option>
                <a-select-option :value="1">1（正常）</a-select-option>
              </a-select>
              <a-input-number v-else v-model:value="targetAlertForm.threshold" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="级别">
              <a-select v-model:value="targetAlertForm.level">
                <a-select-option value="critical">critical</a-select-option>
                <a-select-option value="warning">warning</a-select-option>
                <a-select-option value="info">info</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8"><a-form-item label="评估周期(秒)"><a-input-number v-model:value="targetAlertForm.period" :min="0" style="width: 100%" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="触发次数(times)"><a-input-number v-model:value="targetAlertForm.times" :min="1" style="width: 100%" /></a-form-item></a-col>
        </a-row>

        <a-row :gutter="12">
          <a-col :span="20">
            <a-form-item label="通知规则">
              <a-select
                v-model:value="targetAlertForm.notice_rule_ids"
                mode="multiple"
                allow-clear
                placeholder="不指定则沿用默认通知策略"
              >
                <a-select-option v-for="item in targetAlertNoticeOptions" :key="item.id" :value="Number(item.id)">
                  {{ item.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="4"><a-form-item label="启用"><a-switch v-model:checked="targetAlertForm.enabled" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="自动恢复关闭">
              <a-switch v-model:checked="targetAlertForm.auto_recover" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="恢复次数(N)">
              <a-input-number v-model:value="targetAlertForm.recover_times" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="发送恢复通知">
              <a-switch v-model:checked="targetAlertForm.notify_on_recovered" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">告警升级</a-divider>
        <a-form-item label="启用告警升级" extra="告警持续未处理时，按阶梯延时升级通知">
          <a-switch v-model:checked="targetAlertForm.escalation_enabled" />
        </a-form-item>
        <a-space v-if="targetAlertForm.escalation_enabled" direction="vertical" style="width: 100%" :size="8">
          <a-card
            v-for="(level, idx) in targetAlertEscalationLevels"
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
                    <a-select-option v-for="item in targetAlertNoticeOptions" :key="item.id" :value="Number(item.id)">
                      {{ item.name }}
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
            <a-button danger type="link" @click="removeTargetEscalationLevel(idx)">删除该级</a-button>
          </a-card>
          <a-button type="dashed" block @click="addTargetEscalationLevel">
            新增升级级别
          </a-button>
        </a-space>

        <a-form-item>
          <a-space>
            <a-switch v-model:checked="targetAlertFormUseCustomExpr" />
            <span>高级模式：自定义表达式</span>
          </a-space>
        </a-form-item>
        <a-form-item v-if="targetAlertFormUseCustomExpr" label="表达式">
          <a-textarea v-model:value="targetAlertForm.expr" :rows="3" placeholder="例如：(used_memory / maxmemory) * 100 > 85" />
        </a-form-item>

        <a-divider orientation="left">消息模板</a-divider>
        <a-form-item label="告警标题模板" extra="支持变量: {{$severity}}, {{$rule_name}}, {{$labels.app}}, {{$labels.instance}}">
          <a-input
            v-model:value="targetAlertForm.title_template"
            placeholder="示例: [{{$severity}}] {{$rule_name}} - {{$labels.app}}/{{$labels.instance}}"
          />
        </a-form-item>
        <a-form-item label="告警内容模板" extra="支持变量: {{$labels.instance}}, {{$value}} 等">
          <a-textarea
            v-model:value="targetAlertForm.template"
            :rows="3"
            placeholder="示例: 实例 {{$labels.instance}} 的 {{$labels.metric}} 当前值 {{$value}}"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import * as yaml from 'js-yaml'
import { useUserStore } from '@/stores/user'
import MonitorMetricsPanel from '@/components/monitoring/metrics/MonitorMetricsPanel.vue'
import {
  applyTargetDefaultAlertRules,
  createTargetAlertRule,
  deleteTargetAlertRule,
  getAlertHistory,
  getAlertNotices,
  getCurrentAlerts,
  getMonitoringTarget,
  getTargetAlertRules,
  getTemplates,
  updateTargetAlertRule,
  type AlertItem,
  type AlertNotice,
  type AlertRule,
  type MonitoringTarget,
  type MonitorTemplate
} from '@/api/monitoring'

interface MetricOption { value: string; label: string }
const DEFAULT_ALERT_CONTENT_TEMPLATE = `[{{$severity}}] {{$rule_name}}
应用: {{$labels.app}}
实例: {{$labels.instance}}
指标: {{$labels.metric}}
当前值: {{$value}}
触发条件: {{$expression}}`
const DEFAULT_ALERT_TITLE_TEMPLATE = `[{{$severity}}] {{$rule_name}} - {{$labels.app}}/{{$labels.instance}}`

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const targetDetail = ref<MonitoringTarget | null>(null)
const detailTab = ref<'basic' | 'metrics' | 'alerts'>('basic')
const metricsPanelVersion = ref(0)

const templates = ref<MonitorTemplate[]>([])
const targetTemplateContent = computed(() => {
  const app = String(targetDetail.value?.app || '').trim()
  if (!app) return ''
  return String(templates.value.find((item) => item.app === app)?.content || '')
})

const canEdit = computed(() => userStore.hasPermission('monitoring:list:edit') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:update') || userStore.hasPermission('monitoring:target'))
const monitorId = computed(() => Number(route.params.id || 0))

const targetAlertLoading = ref(false)
const targetAlertRules = ref<AlertRule[]>([])
const targetAlertSelectedRuleIds = ref<number[]>([])
const targetAlertSummaryLoading = ref(false)
const targetAlertSummary = reactive({
  open_total: 0,
  critical_total: 0,
  warning_total: 0,
  info_total: 0,
  history_24h: 0,
  recent: [] as AlertItem[]
})
const targetAlertEditorOpen = ref(false)
const targetAlertSaving = ref(false)
const editingTargetAlertRule = ref<AlertRule | null>(null)
const targetAlertNoticeOptions = ref<AlertNotice[]>([])
const targetAlertMetricOptions = ref<MetricOption[]>([{ value: 'value', label: 'value' }])
const targetAlertForm = reactive({
  name: '',
  type: 'realtime_metric' as 'realtime_metric' | 'periodic_metric',
  expr: '',
  title_template: '',
  template: '',
  metric: 'value',
  operator: '>',
  threshold: 0,
  level: 'warning',
  period: 60,
  times: 1,
  auto_recover: true,
  recover_times: 2,
  notify_on_recovered: true,
  escalation_enabled: false,
  notice_rule_id: undefined as number | undefined,
  notice_rule_ids: [] as number[],
  enabled: true
})
const targetAlertEscalationLevels = ref<Array<{
  level: number
  delay_seconds: number
  notice_rule_ids: number[]
  title_template: string
  content_template: string
}>>([])
const targetAlertFormUseCustomExpr = ref(false)

const CORE_RULE_HINTS = ['实例不可用', '内存使用率过高', '内存碎片严重', '连接数饱和', '拒绝连接', 'RDB', 'AOF', '主从延迟过高']

const targetAlertRowSelection = computed(() => ({
  selectedRowKeys: targetAlertSelectedRuleIds.value,
  onChange: (keys: (string | number)[]) => {
    targetAlertSelectedRuleIds.value = keys.map((item) => Number(item))
  }
}))

const isBinaryMetric = (metric: string) => {
  const key = String(metric || '').trim().toLowerCase()
  return key.endsWith('_ok') || key.endsWith('_up')
}

const normalizeBinaryRule = (metric: string, operator: string, threshold: number) => {
  if (!isBinaryMetric(metric)) return { operator: String(operator || '>').trim() || '>', threshold: Number(threshold ?? 0) || 0 }
  const op = String(operator || '==').trim() || '=='
  if (op === '<' || op === '<=') return { operator: '==', threshold: 0 }
  if (op === '>' || op === '>=') return { operator: '==', threshold: 1 }
  if (op === '!=') return { operator: '!=', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
  return { operator: '==', threshold: Number(threshold) >= 0.5 ? 1 : 0 }
}

const targetAlertIsBinaryMetric = computed(() => isBinaryMetric(targetAlertForm.metric))

function normalizeList(payload: any): { items: any[]; total: number } {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: Number(payload.total) || payload.items.length }
  return { items: [], total: 0 }
}

function normalizedInterval(record: MonitoringTarget): number {
  return Number(record.interval_seconds || record.interval || 0)
}

function parseTemplateMetricOptions(content: string): MetricOption[] {
  try {
    const doc = (yaml.load(content || '') || {}) as any
    if (!doc || typeof doc !== 'object') return [{ value: 'value', label: 'value' }]
    const options = new Map<string, MetricOption>()
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

async function loadTemplates(force = false) {
  if (templates.value.length && !force) return
  try {
    const res = await getTemplates()
    templates.value = Array.isArray(res?.data) ? res.data : []
  } catch {
    templates.value = []
  }
}

async function loadTargetDetail() {
  if (!monitorId.value) {
    targetDetail.value = null
    return
  }
  loading.value = true
  try {
    await loadTemplates()
    const res = await getMonitoringTarget(monitorId.value)
    targetDetail.value = (res as any)?.data || null
    if (!targetDetail.value) message.warning('监控任务不存在')
  } catch (error: any) {
    targetDetail.value = null
    message.error(error?.response?.data?.message || '加载任务详情失败')
  } finally {
    loading.value = false
  }
}

async function reloadDetail() {
  await loadTargetDetail()
  if (detailTab.value === 'metrics') {
    metricsPanelVersion.value += 1
  }
  if (detailTab.value === 'alerts') {
    await refreshTargetAlerts()
  }
}

function ruleGroupText(record: AlertRule): string {
  const source = String((record as any)?.labels?.source || '').toLowerCase()
  if (source === 'template_default') {
    const name = String(record?.name || '')
    return CORE_RULE_HINTS.some((hint) => name.includes(hint)) ? '核心' : '扩展'
  }
  if (String((record as any)?.scope || '').toLowerCase() === 'target') return '实例覆写'
  return '自定义'
}

function ruleGroupTagColor(record: AlertRule): string {
  const text = ruleGroupText(record)
  if (text === '核心') return 'green'
  if (text === '扩展') return 'orange'
  if (text === '实例覆写') return 'blue'
  return 'default'
}

async function loadTargetAlertRules() {
  if (!targetDetail.value?.id) return
  targetAlertLoading.value = true
  try {
    const res = await getTargetAlertRules(targetDetail.value.id)
    const parsed = normalizeList((res as any)?.data || res)
    targetAlertRules.value = (parsed.items || []) as AlertRule[]
    targetAlertSelectedRuleIds.value = targetAlertSelectedRuleIds.value.filter((id) => targetAlertRules.value.some((item) => Number(item.id) === Number(id)))
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载实例告警规则失败')
  } finally {
    targetAlertLoading.value = false
  }
}

function resetTargetAlertSummary() {
  targetAlertSummary.open_total = 0
  targetAlertSummary.critical_total = 0
  targetAlertSummary.warning_total = 0
  targetAlertSummary.info_total = 0
  targetAlertSummary.history_24h = 0
  targetAlertSummary.recent = []
}

async function loadTargetAlertSummary() {
  if (!targetDetail.value?.id) return
  targetAlertSummaryLoading.value = true
  try {
    const monitorIdVal = targetDetail.value.id
    const [currentRes, historyRes] = await Promise.all([
      getCurrentAlerts({ monitor_id: monitorIdVal, page: 1, page_size: 200 }),
      getAlertHistory({ monitor_id: monitorIdVal, page: 1, page_size: 100 })
    ])
    const currentItems = (normalizeList((currentRes as any)?.data || currentRes).items || []) as AlertItem[]
    const historyItems = (normalizeList((historyRes as any)?.data || historyRes).items || []) as AlertItem[]

    targetAlertSummary.open_total = currentItems.length
    targetAlertSummary.critical_total = currentItems.filter((item) => String(item.level || '').toLowerCase() === 'critical').length
    targetAlertSummary.warning_total = currentItems.filter((item) => String(item.level || '').toLowerCase() === 'warning').length
    targetAlertSummary.info_total = currentItems.filter((item) => String(item.level || '').toLowerCase() === 'info').length
    targetAlertSummary.history_24h = historyItems.length
    targetAlertSummary.recent = currentItems
      .filter((item) => {
        const status = String(item.status || '').toLowerCase()
        return !status || status === 'open'
      })
      .slice(0, 8)
  } catch (error: any) {
    resetTargetAlertSummary()
    message.error(error?.response?.data?.message || '加载告警摘要失败')
  } finally {
    targetAlertSummaryLoading.value = false
  }
}

function openAlertDetail(record: AlertItem) {
  const alertId = Number((record as any)?.id || 0)
  if (!alertId) {
    message.warning('告警ID无效，无法跳转详情')
    return
  }
  router.push(`/alert-center/detail/${alertId}`)
}

async function refreshTargetAlerts() {
  await Promise.all([loadTargetAlertRules(), loadTargetAlertSummary()])
}

async function toggleTargetAlertRule(record: AlertRule, enabled: boolean) {
  if (!targetDetail.value?.id || !record?.id) return
  try {
    await updateTargetAlertRule(targetDetail.value.id, Number(record.id), { enabled })
    message.success('规则状态已更新')
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '更新规则失败')
  }
}

async function applyDefaultAlertRulesForTarget() {
  if (!targetDetail.value?.id) return
  try {
    const res = await applyTargetDefaultAlertRules(targetDetail.value.id)
    const payload = (res as any)?.data || {}
    message.success(`默认规则应用完成: 新增 ${payload.created || 0}，更新 ${payload.updated || 0}`)
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '应用默认规则失败')
  }
}

async function restoreDefaultAlertRulesForTarget() {
  await applyDefaultAlertRulesForTarget()
}

async function batchUpdateTargetAlertRules(enabled: boolean) {
  if (!targetDetail.value?.id || !targetAlertSelectedRuleIds.value.length) return
  const selected = targetAlertRules.value.filter((item) => targetAlertSelectedRuleIds.value.includes(Number(item.id)))
  try {
    await Promise.all(selected.map((item) => updateTargetAlertRule(targetDetail.value!.id!, Number(item.id), { enabled } as any)))
    message.success(enabled ? '批量启用成功' : '批量禁用成功')
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量更新规则失败')
  }
}

async function batchDeleteTargetAlertRules() {
  if (!targetDetail.value?.id || !targetAlertSelectedRuleIds.value.length) return
  try {
    await Promise.all(targetAlertSelectedRuleIds.value.map((id) => deleteTargetAlertRule(targetDetail.value!.id!, Number(id))))
    targetAlertSelectedRuleIds.value = []
    message.success('批量删除成功')
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量删除失败')
  }
}

async function loadTargetAlertNoticeOptions() {
  try {
    const res = await getAlertNotices({ page_size: 1000 })
    targetAlertNoticeOptions.value = (normalizeList((res as any)?.data || res).items || []) as AlertNotice[]
  } catch {
    targetAlertNoticeOptions.value = []
  }
}

async function loadTargetAlertMetricOptions() {
  const app = String(targetDetail.value?.app || '').trim()
  if (!app) {
    targetAlertMetricOptions.value = [{ value: 'value', label: 'value' }]
    return
  }
  await loadTemplates()
  const tpl = templates.value.find((item) => item.app === app)
  targetAlertMetricOptions.value = parseTemplateMetricOptions(String(tpl?.content || ''))
}

function buildTargetAlertExpr() {
  const metric = String(targetAlertForm.metric || 'value').trim() || 'value'
  const normalized = normalizeBinaryRule(metric, String(targetAlertForm.operator || '>').trim() || '>', Number(targetAlertForm.threshold ?? 0))
  return `${metric} ${normalized.operator} ${Number.isFinite(normalized.threshold) ? normalized.threshold : 0}`
}

async function openTargetAlertRuleEditor(record: AlertRule) {
  editingTargetAlertRule.value = record
  targetAlertForm.name = String(record.name || '')
  targetAlertForm.type = String((record as any).type || (record as any).monitor_type || '').includes('periodic') ? 'periodic_metric' : 'realtime_metric'
  targetAlertForm.expr = String((record as any).expr || '')
  targetAlertForm.title_template = String((record as any).title_template || (record as any).annotations?.title_template || '')
  targetAlertForm.template = String((record as any).template || '')
  targetAlertForm.metric = String((record as any).metric || 'value')
  const normalized = normalizeBinaryRule(targetAlertForm.metric, String((record as any).operator || '>'), Number((record as any).threshold || 0))
  targetAlertForm.operator = normalized.operator
  targetAlertForm.threshold = normalized.threshold
  targetAlertForm.level = String((record as any).level || 'warning')
  targetAlertForm.period = Number((record as any).period || 60)
  targetAlertForm.times = Number((record as any).times || 1)
  targetAlertForm.auto_recover = (record as any).auto_recover !== false
  targetAlertForm.recover_times = Math.max(Number((record as any).recover_times || 2), 1)
  targetAlertForm.notify_on_recovered = (record as any).notify_on_recovered !== false
  targetAlertForm.escalation_enabled = Boolean((record as any).escalation_config?.enabled)
  const noticeRuleIds = Array.isArray((record as any).notice_rule_ids)
    ? ((record as any).notice_rule_ids as number[])
    : []
  targetAlertForm.notice_rule_ids = noticeRuleIds.length
    ? [...noticeRuleIds]
    : (record as any).notice_rule_id
      ? [Number((record as any).notice_rule_id)]
      : []
  targetAlertForm.notice_rule_id = (record as any).notice_rule_id ? Number((record as any).notice_rule_id) : undefined
  targetAlertForm.enabled = (record as any).enabled !== false
  targetAlertEscalationLevels.value = Array.isArray((record as any).escalation_config?.levels)
    ? ((record as any).escalation_config.levels as any[])
      .map((item: any, idx: number) => ({
        level: Number(item?.level || idx + 1),
        delay_seconds: Math.max(Number(item?.delay_seconds || 300), 1),
        notice_rule_ids: Array.isArray(item?.notice_rule_ids) ? item.notice_rule_ids.map((v: any) => Number(v)).filter((v: number) => v > 0) : [],
        title_template: String(item?.title_template || ''),
        content_template: String(item?.content_template || '')
      }))
    : []
  targetAlertFormUseCustomExpr.value = Boolean(String(targetAlertForm.expr || '').trim())

  await Promise.all([loadTargetAlertNoticeOptions(), loadTargetAlertMetricOptions()])
  if (!targetAlertMetricOptions.value.some((item) => item.value === targetAlertForm.metric)) {
    targetAlertMetricOptions.value = [...targetAlertMetricOptions.value, { value: targetAlertForm.metric, label: targetAlertForm.metric }]
  }
  targetAlertEditorOpen.value = true
}

async function openCreateTargetAlertRule() {
  if (!targetDetail.value?.id) return
  editingTargetAlertRule.value = null
  targetAlertForm.name = ''
  targetAlertForm.type = 'realtime_metric'
  targetAlertForm.expr = ''
  targetAlertForm.title_template = DEFAULT_ALERT_TITLE_TEMPLATE
  targetAlertForm.template = DEFAULT_ALERT_CONTENT_TEMPLATE
  targetAlertForm.metric = 'value'
  targetAlertForm.operator = '>'
  targetAlertForm.threshold = 0
  targetAlertForm.level = 'warning'
  targetAlertForm.period = 60
  targetAlertForm.times = 1
  targetAlertForm.auto_recover = true
  targetAlertForm.recover_times = 2
  targetAlertForm.notify_on_recovered = true
  targetAlertForm.escalation_enabled = false
  targetAlertForm.notice_rule_id = undefined
  targetAlertForm.notice_rule_ids = []
  targetAlertForm.enabled = true
  targetAlertEscalationLevels.value = []
  targetAlertFormUseCustomExpr.value = false

  await Promise.all([loadTargetAlertNoticeOptions(), loadTargetAlertMetricOptions()])
  if (targetAlertMetricOptions.value.length) {
    targetAlertForm.metric = targetAlertMetricOptions.value[0].value
    const normalized = normalizeBinaryRule(targetAlertForm.metric, targetAlertForm.operator, targetAlertForm.threshold)
    targetAlertForm.operator = normalized.operator
    targetAlertForm.threshold = normalized.threshold
  }
  targetAlertEditorOpen.value = true
}

async function saveTargetAlertRule() {
  if (!targetDetail.value?.id || !targetAlertForm.name.trim()) {
    message.warning('规则名称不能为空')
    return
  }
  if (targetAlertForm.escalation_enabled && !targetAlertEscalationLevels.value.length) {
    message.warning('已启用告警升级，请至少配置一个升级级别')
    return
  }

  targetAlertSaving.value = true
  try {
    const metric = String(targetAlertForm.metric || '').trim()
    if (!metric) {
      message.warning('请选择监控指标')
      return
    }

    const normalized = normalizeBinaryRule(metric, targetAlertForm.operator, Number(targetAlertForm.threshold))
    const payload = {
      name: targetAlertForm.name.trim(),
      type: targetAlertForm.type,
      expr: targetAlertFormUseCustomExpr.value ? String(targetAlertForm.expr || '').trim() || buildTargetAlertExpr() : buildTargetAlertExpr(),
      title_template: String(targetAlertForm.title_template || '').trim(),
      template: String(targetAlertForm.template || '').trim() || undefined,
      metric,
      operator: normalized.operator,
      threshold: normalized.threshold,
      level: targetAlertForm.level,
      period: Number(targetAlertForm.period),
      times: Number(targetAlertForm.times),
      auto_recover: Boolean(targetAlertForm.auto_recover),
      recover_times: Math.max(Number(targetAlertForm.recover_times || 2), 1),
      notify_on_recovered: Boolean(targetAlertForm.notify_on_recovered),
      escalation_config: targetAlertForm.escalation_enabled
        ? {
          enabled: true,
          levels: targetAlertEscalationLevels.value.map((item, idx) => ({
            level: idx + 1,
            delay_seconds: Math.max(Number(item.delay_seconds || 0), 1),
            notice_rule_ids: Array.isArray(item.notice_rule_ids) ? item.notice_rule_ids.filter((id) => Number(id) > 0).map((id) => Number(id)) : [],
            title_template: String(item.title_template || '').trim(),
            content_template: String(item.content_template || '').trim()
          }))
        }
        : { enabled: false, levels: [] as any[] },
      notice_rule_ids: targetAlertForm.notice_rule_ids,
      notice_rule_id: targetAlertForm.notice_rule_id,
      labels: {},
      enabled: targetAlertForm.enabled
    } as any

    if (editingTargetAlertRule.value?.id) {
      await updateTargetAlertRule(targetDetail.value.id, Number(editingTargetAlertRule.value.id), payload)
      message.success('规则已更新')
    } else {
      await createTargetAlertRule(targetDetail.value.id, payload)
      message.success('规则已新增')
    }

    targetAlertEditorOpen.value = false
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '更新规则失败')
  } finally {
    targetAlertSaving.value = false
  }
}

async function removeTargetAlertRule(record: AlertRule) {
  if (!targetDetail.value?.id || !record?.id) return
  try {
    await deleteTargetAlertRule(targetDetail.value.id, Number(record.id))
    message.success('规则已删除')
    await refreshTargetAlerts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除规则失败')
  }
}

function addTargetEscalationLevel() {
  targetAlertEscalationLevels.value.push({
    level: targetAlertEscalationLevels.value.length + 1,
    delay_seconds: 300,
    notice_rule_ids: [],
    title_template: '',
    content_template: ''
  })
}

function removeTargetEscalationLevel(index: number) {
  targetAlertEscalationLevels.value.splice(index, 1)
  targetAlertEscalationLevels.value = targetAlertEscalationLevels.value.map((item, idx) => ({ ...item, level: idx + 1 }))
}

function goBack() {
  router.push('/monitoring/list')
}

watch(
  () => route.params.id,
  async () => {
    detailTab.value = 'basic'
    await loadTargetDetail()
  },
  { immediate: true }
)

watch(
  () => detailTab.value,
  async (tab) => {
    if (tab === 'alerts') {
      await refreshTargetAlerts()
      return
    }
    if (tab === 'metrics') {
      metricsPanelVersion.value += 1
    }
  }
)

watch(
  () => targetAlertForm.metric,
  (metric, prevMetric) => {
    if (isBinaryMetric(metric) && !isBinaryMetric(String(prevMetric || ''))) {
      targetAlertForm.operator = '=='
      targetAlertForm.threshold = 0
      return
    }
    const normalized = normalizeBinaryRule(targetAlertForm.metric, targetAlertForm.operator, targetAlertForm.threshold)
    targetAlertForm.operator = normalized.operator
    targetAlertForm.threshold = normalized.threshold
  }
)

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.monitor-target-detail-page {
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
</style>
