<template>
  <div class="app-page alert-detail-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <div class="alert-detail-header">
        <div>
          <div class="alert-title">{{ alertDetail?.name || '告警明细' }}</div>
          <div class="alert-time">最新一次告警时间：{{ formatTime(alertDetail?.triggered_at) }}</div>
        </div>
        <a-space>
          <a-button type="primary" :disabled="!canClaim || !alertDetail?.id || actionDisabled" @click="handleClaim">受理</a-button>
          <a-button danger :disabled="!canClose || !alertDetail?.id || actionDisabled" @click="handleClose">关闭</a-button>
        </a-space>
      </div>

      <a-space wrap class="alert-chip-group">
        <a-tag class="alert-chip alert-chip--neutral">告警来源：{{ alertSource }}</a-tag>
        <a-tag class="alert-chip alert-chip--neutral">告警对象：{{ alertDetail?.monitor_name || monitorDetail?.name || '-' }}</a-tag>
        <a-tag class="alert-chip" :color="levelColor(alertDetail?.level)">告警等级：{{ alertDetail?.level || '-' }}</a-tag>
        <a-tag class="alert-chip" :color="statusColor(alertDetail?.status)">告警状态：{{ alertDetail?.status || '-' }}</a-tag>
      </a-space>

      <a-descriptions :column="2" bordered size="small">
        <a-descriptions-item label="告警名称">{{ alertDetail?.name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="告警ID">{{ alertDetail?.id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="监控任务">{{ monitorDetail?.name || alertDetail?.monitor_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="监控任务ID">{{ alertDetail?.monitor_id || '-' }}</a-descriptions-item>
        <a-descriptions-item label="指标">{{ alertDetail?.metric || '-' }}</a-descriptions-item>
        <a-descriptions-item label="指标值">{{ alertDetail?.metric_value ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="阈值">{{ alertDetail?.threshold ?? '-' }}</a-descriptions-item>
        <a-descriptions-item label="实例">{{ alertDetail?.instance || '-' }}</a-descriptions-item>
        <a-descriptions-item label="目标">{{ monitorDetail?.target || '-' }}</a-descriptions-item>
        <a-descriptions-item label="CI编码">{{ monitorDetail?.ci_code || '-' }}</a-descriptions-item>
        <a-descriptions-item label="CI名称">{{ monitorDetail?.ci_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="告警描述" :span="2">{{ alertDescription }}</a-descriptions-item>
      </a-descriptions>

      <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
        <a-tab-pane key="metrics" tab="指标分析">
          <a-space direction="vertical" style="width: 100%" :size="12">
            <a-space wrap>
              <a-segmented v-model:value="metricRangePreset" :options="rangeOptions" @change="loadMetricTrend" />
              <a-range-picker
                v-model:value="metricCustomRange"
                show-time
                format="YYYY-MM-DD HH:mm:ss"
                @change="handleMetricCustomRangeChange"
              />
              <a-button :loading="metricLoading" @click="loadMetricTrend">刷新</a-button>
            </a-space>

            <a-alert
              type="info"
              show-icon
              :message="`监控对象: ${monitorDetail?.target || alertDetail?.monitor_name || '-'} | 指标: ${alertDetail?.metric || '-'}${resolvedMetricName && resolvedMetricName !== alertDetail?.metric ? ` (时序: ${resolvedMetricName})` : ''}`"
            />

            <a-spin :spinning="metricLoading">
              <a-empty v-if="!metricAvailable" description="当前告警无可用指标信息" />
              <a-empty v-else-if="!metricPoints.length" description="当前时间范围暂无指标数据" />
              <div v-else ref="metricChartRef" class="metric-chart" />
            </a-spin>
          </a-space>
        </a-tab-pane>

        <a-tab-pane key="related" tab="关联告警">
          <a-table
            :loading="relatedLoading"
            :data-source="relatedAlerts"
            :pagination="relatedPagination"
            row-key="id"
            @change="handleRelatedTableChange"
          >
            <a-table-column title="级别" data-index="level" key="level" width="90">
              <template #default="{ record }">
                <a-tag :color="levelColor(record.level)">
                  {{ record.escalation_level ? `L${record.escalation_level}` : (record.level || '-') }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="告警名称" data-index="name" key="name" />
            <a-table-column title="告警状态" data-index="status" key="status" width="110">
              <template #default="{ record }">
                <a-tag :color="statusColor(record.status)">{{ record.status || '-' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="触发时间" data-index="triggered_at" key="triggered_at" width="180">
              <template #default="{ record }">{{ formatTime(record.triggered_at) }}</template>
            </a-table-column>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="history" tab="历史告警">
          <a-table
            :loading="historyLoading"
            :data-source="historyAlerts"
            :pagination="historyPagination"
            row-key="id"
            @change="handleHistoryTableChange"
          >
            <a-table-column title="级别" data-index="level" key="level" width="90">
              <template #default="{ record }">
                <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="告警名称" data-index="name" key="name" />
            <a-table-column title="触发时间" data-index="triggered_at" key="triggered_at" width="180">
              <template #default="{ record }">{{ formatTime(record.triggered_at) }}</template>
            </a-table-column>
            <a-table-column title="恢复时间" data-index="recovered_at" key="recovered_at" width="180">
              <template #default="{ record }">{{ formatTime(record.recovered_at) }}</template>
            </a-table-column>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="process" tab="处理历史">
          <a-table
            :loading="processLoading"
            :data-source="processEvents"
            :pagination="processPagination"
            row-key="id"
            @change="handleProcessTableChange"
          >
            <a-table-column title="阶段" data-index="event_type" key="event_type" width="150">
              <template #default="{ record }">
                <a-tag :color="timelineTypeColor(record.event_type)">{{ timelineTypeText(record.event_type) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="事件" data-index="title" key="title" width="180" />
            <a-table-column title="详情" data-index="content" key="content" />
            <a-table-column title="处理人" data-index="operator" key="operator" width="140" />
            <a-table-column title="发生时间" data-index="happened_at" key="happened_at" width="180">
              <template #default="{ record }">{{ formatTime(record.happened_at) }}</template>
            </a-table-column>
          </a-table>
          <a-empty v-if="!processLoading && !processEvents.length" description="暂无处理历史" />
        </a-tab-pane>

        <a-tab-pane key="escalation" tab="升级记录">
          <a-table
            :loading="escalationLoading"
            :data-source="escalationRecords"
            :pagination="escalationPagination"
            row-key="id"
            @change="handleEscalationTableChange"
          >
            <a-table-column title="级别" data-index="level" key="level" width="90">
              <template #default="{ record }">
                <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="升级内容" data-index="content" key="content">
              <template #default="{ record }">
                {{ record.content || record.note || '-' }}
              </template>
            </a-table-column>
            <a-table-column title="发生时间" data-index="triggered_at" key="triggered_at" width="180">
              <template #default="{ record }">{{ formatTime(record.triggered_at) }}</template>
            </a-table-column>
          </a-table>
          <a-empty v-if="!escalationLoading && !escalationRecords.length" description="暂无升级记录" />
        </a-tab-pane>

        <a-tab-pane key="topology" tab="资源拓扑">
          <AlertTopology :ci-id="monitorDetail?.ci_id" />
        </a-tab-pane>

        <a-tab-pane key="rules" tab="告警规则">
          <a-table :loading="rulesLoading" :data-source="alertRules" row-key="id" :pagination="false">
            <a-table-column title="规则名称" data-index="name" key="name" />
            <a-table-column title="类型" data-index="monitor_type" key="monitor_type" width="140" />
            <a-table-column title="表达式" data-index="expr" key="expr" />
            <a-table-column title="启用" data-index="enabled" key="enabled" width="90">
              <template #default="{ record }">
                <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="通知规则" data-index="notice_rule_id" key="notice_rule_id" width="120" />
            <a-table-column title="匹配方式" data-index="matched_by" key="matched_by" width="120">
              <template #default="{ record }">
                <a-tag>{{ record.matched_by || '-' }}</a-tag>
              </template>
            </a-table-column>
          </a-table>
          <a-empty v-if="!rulesLoading && !alertRules.length" description="未找到触发该告警的规则" />
        </a-tab-pane>

        <a-tab-pane key="notices" tab="告警通知">
          <a-form layout="inline" :model="noticeFilters">
            <a-form-item label="状态">
              <a-select v-model:value="noticeFilters.status" allow-clear style="width: 140px" placeholder="全部状态">
                <a-select-option :value="0">待发送</a-select-option>
                <a-select-option :value="1">发送中</a-select-option>
                <a-select-option :value="2">成功</a-select-option>
                <a-select-option :value="3">失败</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="通知类型">
              <a-select v-model:value="noticeFilters.notify_type" allow-clear style="width: 160px" placeholder="全部类型">
                <a-select-option value="email">email</a-select-option>
                <a-select-option value="sms">sms</a-select-option>
                <a-select-option value="webhook">webhook</a-select-option>
                <a-select-option value="wecom">wecom</a-select-option>
                <a-select-option value="dingtalk">dingtalk</a-select-option>
                <a-select-option value="feishu">feishu</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="接收人类型">
              <a-select v-model:value="noticeFilters.receiver_type" allow-clear style="width: 160px" placeholder="全部类型">
                <a-select-option value="user">user</a-select-option>
                <a-select-option value="group">group</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="关键词">
              <a-input v-model:value="noticeFilters.keyword" allow-clear style="width: 220px" placeholder="内容/错误/接收人" />
            </a-form-item>
            <a-form-item label="发送时间">
              <a-range-picker
                v-model:value="noticeTimeRange"
                show-time
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 320px"
              />
            </a-form-item>
            <a-form-item>
              <a-space>
                <a-button type="primary" :loading="noticesLoading" @click="loadAlertNotifications">查询</a-button>
                <a-button @click="resetNoticeFilters">重置</a-button>
              </a-space>
            </a-form-item>
          </a-form>

          <a-table
            :loading="noticesLoading"
            :data-source="alertNotifications"
            row-key="id"
            :pagination="noticePagination"
            @change="handleNoticeTableChange"
          >
            <a-table-column title="通知渠道" data-index="notify_type" key="notify_type" width="120">
              <template #default="{ record }">
                {{ notificationChannelText(record.notify_type) }}
              </template>
            </a-table-column>
            <a-table-column title="接收人类型" data-index="receiver_type" key="receiver_type" width="120" />
            <a-table-column title="接收人ID" data-index="receiver_id" key="receiver_id" width="120" />
            <a-table-column title="状态" data-index="status" key="status" width="100">
              <template #default="{ record }">
                <a-tag :color="notificationStatusColor(record.status)">{{ notificationStatusText(record.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="发送时间" data-index="sent_at" key="sent_at" width="180">
              <template #default="{ record }">{{ formatTime(record.sent_at) }}</template>
            </a-table-column>
            <a-table-column title="内容" data-index="content" key="content" />
            <a-table-column title="错误信息" data-index="error_msg" key="error_msg" />
          </a-table>
          <a-empty v-if="!noticesLoading && !alertNotifications.length" description="暂无告警通知记录" />
        </a-tab-pane>
      </a-tabs>
      </a-space>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import dayjs, { type Dayjs } from 'dayjs'
import { message, Modal } from 'ant-design-vue'
import * as echarts from 'echarts/core'
import type { EChartsType } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  type TooltipComponentOption,
  type GridComponentOption,
  type DataZoomComponentOption,
  type LegendComponentOption
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption } from 'echarts/core'
import type { LineSeriesOption } from 'echarts/charts'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  claimAlert,
  closeAlert,
  getAlertDetail,
  getAlertHistory,
  getAlertNotifications,
  getAlertRuleByAlertId,
  getAlertTimeline,
  getCurrentAlerts,
  getTargetMetricSeries,
  getMonitoringTarget,
  type AlertItem,
  type AlertNotificationRecord,
  type AlertRule,
  type AlertTimelineEvent,
  type MonitoringTarget
} from '@/api/monitoring'
import { fetchTrendSeries, formatMetricValue } from '@/composables/useMonitorMetrics'
import AlertTopology from './components/AlertTopology.vue'

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, CanvasRenderer])

type ECOption = ComposeOption<
  LineSeriesOption | TooltipComponentOption | GridComponentOption | DataZoomComponentOption | LegendComponentOption
>

const route = useRoute()
const userStore = useUserStore()
const alertDetail = ref<AlertItem | null>(null)
const monitorDetail = ref<MonitoringTarget | null>(null)
const activeTab = ref<'metrics' | 'related' | 'history' | 'process' | 'escalation' | 'topology' | 'rules' | 'notices'>('metrics')

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

const relatedAlerts = ref<AlertItem[]>([])
const relatedLoading = ref(false)
const relatedPagination = reactive({ current: 1, pageSize: 10, total: 0 })

const historyAlerts = ref<AlertItem[]>([])
const historyLoading = ref(false)
const historyPagination = reactive({ current: 1, pageSize: 10, total: 0 })
const processEvents = ref<AlertTimelineEvent[]>([])
const processLoading = ref(false)
const processPagination = reactive({ current: 1, pageSize: 10, total: 0 })
const escalationRecords = ref<AlertItem[]>([])
const escalationLoading = ref(false)
const escalationPagination = reactive({ current: 1, pageSize: 10, total: 0 })

const alertRules = ref<AlertRule[]>([])
const rulesLoading = ref(false)

const alertNotifications = ref<AlertNotificationRecord[]>([])
const noticesLoading = ref(false)
const noticeFilters = reactive({
  status: undefined as number | undefined,
  notify_type: undefined as string | undefined,
  receiver_type: undefined as string | undefined,
  keyword: ''
})
const noticeTimeRange = ref<[Dayjs, Dayjs] | null>(null)
const noticePagination = reactive({ current: 1, pageSize: 10, total: 0 })

const metricLoading = ref(false)
const metricPoints = ref<Array<{ timestamp: number; value: number }>>([])
const resolvedMetricName = ref('')
const metricChartRef = ref<HTMLDivElement | null>(null)
let metricChart: EChartsType | null = null

const metricRangePreset = ref<'1h' | '1d' | '1w' | '1m' | 'custom'>('1h')
const metricCustomRange = ref<[Dayjs, Dayjs] | null>(null)

const rangeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近1天', value: '1d' },
  { label: '最近1周', value: '1w' },
  { label: '最近1月', value: '1m' },
  { label: '自定义', value: 'custom' }
]

const metricAvailable = computed(() => Boolean(alertDetail.value?.monitor_id && alertDetail.value?.metric))

const alertSource = computed(() => {
  if (!alertDetail.value) return '-'
  const sourceType = String(alertDetail.value.source_type || '').toLowerCase()
  const sourceName = String(alertDetail.value.source_name || '').trim()
  if (sourceType === 'local') return '本地监控'
  if (sourceType === 'external') return sourceName ? `外部告警接入（${sourceName}）` : '外部告警接入'
  if (sourceName) return sourceName
  return '外部告警接入'
})

const alertDescription = computed(() => alertDetail.value?.note || '-')

const actionDisabled = computed(() => {
  if (!alertDetail.value) return true
  return String(alertDetail.value.status || '').toLowerCase() !== 'open'
})

const formatTime = (timeStr?: string) => {
  if (!timeStr) return '-'
  return dayjs(timeStr).format('YYYY-MM-DD HH:mm:ss')
}

const levelColor = (level?: string) => {
  if (level === 'critical') return 'red'
  if (level === 'warning') return 'orange'
  return 'blue'
}

const statusColor = (status?: string) => {
  if (status === 'open') return 'red'
  if (status === 'closed') return 'default'
  return 'blue'
}

const notificationStatusText = (status?: number) => {
  if (status === 1) return '发送中'
  if (status === 2) return '成功'
  if (status === 3) return '失败'
  return '待发送'
}

const notificationStatusColor = (status?: number) => {
  if (status === 2) return 'green'
  if (status === 3) return 'red'
  if (status === 1) return 'blue'
  return 'default'
}

const notificationChannelText = (notifyType?: string) => {
  const key = String(notifyType || '').trim().toLowerCase()
  if (key === 'system') return '站内消息'
  if (key === 'email') return '邮件'
  if (key === 'sms') return '短信'
  if (key === 'webhook') return 'Webhook'
  if (key === 'wecom') return '企业微信'
  if (key === 'dingtalk') return '钉钉'
  if (key === 'feishu') return '飞书'
  return notifyType || '-'
}

const timelineTypeText = (eventType?: string) => {
  const key = String(eventType || '').trim().toLowerCase()
  if (key === 'triggered') return '产生'
  if (key === 'source') return '来源'
  if (key === 'dispatch') return '分派'
  if (key === 'acknowledge') return '受理'
  if (key === 'notification_dispatch') return '通知分派'
  if (key === 'notification_received') return '通知接收'
  if (key === 'notification_failed') return '通知失败'
  if (key === 'closed') return '关闭'
  if (key === 'escalated') return '升级'
  return eventType || '-'
}

const timelineTypeColor = (eventType?: string) => {
  const key = String(eventType || '').trim().toLowerCase()
  if (key === 'triggered') return 'red'
  if (key === 'source') return 'blue'
  if (key === 'dispatch') return 'purple'
  if (key === 'acknowledge') return 'cyan'
  if (key === 'notification_dispatch') return 'orange'
  if (key === 'notification_received') return 'green'
  if (key === 'notification_failed') return 'red'
  if (key === 'closed') return 'default'
  if (key === 'escalated') return 'magenta'
  return 'default'
}

const normalizeList = (payload: any): { items: any[]; total: number } => {
  if (!payload) return { items: [], total: 0 }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const resolveRange = () => {
  const now = dayjs()
  if (metricRangePreset.value === 'custom' && metricCustomRange.value) {
    return {
      from: metricCustomRange.value[0].unix(),
      to: metricCustomRange.value[1].unix()
    }
  }
  if (metricRangePreset.value === '1d') return { from: now.subtract(1, 'day').unix(), to: now.unix() }
  if (metricRangePreset.value === '1w') return { from: now.subtract(7, 'day').unix(), to: now.unix() }
  if (metricRangePreset.value === '1m') return { from: now.subtract(30, 'day').unix(), to: now.unix() }
  return { from: now.subtract(1, 'hour').unix(), to: now.unix() }
}

const resolveAlertMetricName = async (monitorId: number, rawMetric: string): Promise<string> => {
  const metric = String(rawMetric || '').trim()
  if (!monitorId || !metric) return metric
  const now = dayjs()
  const from = now.subtract(7, 'day').unix()
  const to = now.unix()
  try {
    const res = await getTargetMetricSeries(monitorId, { from, to })
    const payload = (res as any)?.data || res
    const items = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : []
    if (!items.length) return metric

    const exact = items.find((item: any) => String(item?.__name__ || '').trim() === metric)
    if (exact) return metric

    const byMetricLabel = items.find((item: any) => String(item?.__metric__ || '').trim() === metric)
    if (byMetricLabel && String(byMetricLabel?.__name__ || '').trim()) {
      return String(byMetricLabel.__name__).trim()
    }

    const suffix = `_${metric}`
    const suffixMatches = items
      .map((item: any) => String(item?.__name__ || '').trim())
      .filter((name: string) => name.endsWith(suffix))
    if (suffixMatches.length === 1) return suffixMatches[0]
  } catch {
    // keep raw metric as fallback
  }
  return metric
}

const ensureMetricChart = () => {
  if (!metricChartRef.value) return
  if (!metricChart) metricChart = echarts.init(metricChartRef.value)
}

const buildMetricChartOption = (): ECOption => {
  const sorted = [...metricPoints.value].sort((a, b) => a.timestamp - b.timestamp)
  const xData = sorted.map((point) => dayjs(point.timestamp).format('MM-DD HH:mm'))
  const yData = sorted.map((point) => point.value)
  return {
    grid: { left: 40, right: 24, top: 30, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const one = Array.isArray(params) ? params[0] : params
        const val = one?.data
        return `${one?.axisValueLabel || ''}<br/>指标值：${formatMetricValue(val)}`
      }
    },
    xAxis: { type: 'category', data: xData, boundaryGap: false },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16 }],
    series: [
      {
        type: 'line',
        smooth: true,
        data: yData,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: '#1677ff' },
        areaStyle: { color: 'rgba(22,119,255,0.12)' }
      }
    ]
  }
}

const renderMetricChart = () => {
  if (!metricChart) return
  if (!metricPoints.value.length) {
    metricChart.clear()
    return
  }
  metricChart.setOption(buildMetricChartOption(), true)
}

const resizeMetricChart = () => {
  metricChart?.resize()
}

const loadMetricTrend = async () => {
  if (!metricAvailable.value) {
    metricPoints.value = []
    renderMetricChart()
    return
  }
  metricLoading.value = true
  try {
    const range = resolveRange()
    const monitorId = Number(alertDetail.value?.monitor_id)
    const metric = String(alertDetail.value?.metric || '')
    const queryMetric = await resolveAlertMetricName(monitorId, metric)
    resolvedMetricName.value = queryMetric
    const intervalSeconds = Number(monitorDetail.value?.interval_seconds || monitorDetail.value?.interval || 60)
    metricPoints.value = await fetchTrendSeries(monitorId, queryMetric, range.from, range.to, intervalSeconds)
    await nextTick()
    ensureMetricChart()
    renderMetricChart()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '指标数据加载失败')
  } finally {
    metricLoading.value = false
  }
}

const handleMetricCustomRangeChange = () => {
  metricRangePreset.value = 'custom'
  loadMetricTrend()
}

const loadAlertDetail = async () => {
  const alertId = Number(route.params.id)
  if (!Number.isFinite(alertId) || alertId <= 0) {
    message.error('告警ID无效')
    return
  }
  const res = await getAlertDetail(alertId)
  alertDetail.value = (res as any)?.data || null
  resolvedMetricName.value = ''
  if (!alertDetail.value) {
    message.warning('告警不存在或已删除')
    return
  }
  if (alertDetail.value.monitor_id) {
    try {
      const res = await getMonitoringTarget(alertDetail.value.monitor_id)
      monitorDetail.value = (res as any)?.data || null
    } catch {
      monitorDetail.value = null
    }
  }
  if (activeTab.value === 'metrics') loadMetricTrend()
  if (activeTab.value === 'related') loadRelatedAlerts()
  if (activeTab.value === 'history') loadHistoryAlerts()
  if (activeTab.value === 'process') loadProcessTimeline()
  if (activeTab.value === 'escalation') loadEscalationRecords()
  if (activeTab.value === 'rules') loadAlertRules()
  if (activeTab.value === 'notices') loadAlertNotifications()
}

const loadRelatedAlerts = async () => {
  if (!alertDetail.value?.monitor_id) return
  relatedLoading.value = true
  try {
    const res = await getCurrentAlerts({
      page: relatedPagination.current,
      page_size: relatedPagination.pageSize,
      monitor_id: alertDetail.value.monitor_id,
      status: 'open'
    } as any)
    const parsed = normalizeList((res as any)?.data || res)
    const sameMonitor = (item: AlertItem) => Number(item.monitor_id) === Number(alertDetail.value?.monitor_id)
    const items = parsed.items || []
    const filtered = items.filter(
      (item: AlertItem) => Number(item.id) !== Number(alertDetail.value?.id) && sameMonitor(item)
    )
    const allMatch = items.length > 0 && items.every((item: AlertItem) => sameMonitor(item))
    relatedAlerts.value = filtered
    relatedPagination.total = allMatch ? parsed.total : filtered.length
  } finally {
    relatedLoading.value = false
  }
}

const loadHistoryAlerts = async () => {
  if (!alertDetail.value?.name && !alertDetail.value?.rule_id) return
  historyLoading.value = true
  try {
    const params: Record<string, any> = {
      page: historyPagination.current,
      page_size: historyPagination.pageSize
    }
    if (alertDetail.value?.rule_id) {
      params.rule_id = alertDetail.value.rule_id
    } else if (alertDetail.value?.name) {
      params.name = alertDetail.value.name
    }
    const res = await getAlertHistory({
      ...params
    } as any)
    const parsed = normalizeList((res as any)?.data || res)
    const items = parsed.items || []
    const sameRule = (item: AlertItem) => {
      if (alertDetail.value?.rule_id) return Number(item.rule_id) === Number(alertDetail.value.rule_id)
      return String(item.name || '').trim() === String(alertDetail.value?.name || '').trim()
    }
    const filtered = items.filter((item: AlertItem) => sameRule(item))
    const allMatch = items.length > 0 && items.every((item: AlertItem) => sameRule(item))
    historyAlerts.value = filtered
    historyPagination.total = allMatch ? parsed.total : filtered.length
  } finally {
    historyLoading.value = false
  }
}

const loadProcessTimeline = async () => {
  if (!alertDetail.value?.id) return
  processLoading.value = true
  try {
    const res = await getAlertTimeline(alertDetail.value.id, {
      page: processPagination.current,
      page_size: processPagination.pageSize
    })
    const parsed = normalizeList((res as any)?.data || res)
    processEvents.value = (parsed.items || []) as AlertTimelineEvent[]
    processPagination.total = parsed.total
  } finally {
    processLoading.value = false
  }
}

const loadEscalationRecords = async () => {
  if (!alertDetail.value?.rule_id && !alertDetail.value?.name) return
  escalationLoading.value = true
  try {
    const params: Record<string, any> = {
      page: escalationPagination.current,
      page_size: escalationPagination.pageSize
    }
    if (alertDetail.value?.rule_id) {
      params.rule_id = alertDetail.value.rule_id
    } else if (alertDetail.value?.name) {
      params.name = alertDetail.value.name
    }
    if (alertDetail.value?.monitor_id) {
      params.monitor_id = alertDetail.value.monitor_id
    }
    const res = await getAlertHistory(params)
    const parsed = normalizeList((res as any)?.data || res)
    const items = (parsed.items || []) as AlertItem[]
    const filtered = items.filter((item) => String(item.action || '').toLowerCase() === 'escalated')
    escalationRecords.value = filtered
    escalationPagination.total = filtered.length
  } finally {
    escalationLoading.value = false
  }
}

const loadAlertRules = async () => {
  if (!alertDetail.value?.id) return
  rulesLoading.value = true
  try {
    const res = await getAlertRuleByAlertId(alertDetail.value.id)
    const payload = (res as any)?.data || null
    alertRules.value = payload ? [payload] : []
  } finally {
    rulesLoading.value = false
  }
}

const loadAlertNotifications = async () => {
  if (!alertDetail.value?.id) return
  noticesLoading.value = true
  try {
    const res = await getAlertNotifications(alertDetail.value.id, {
      page: noticePagination.current,
      page_size: noticePagination.pageSize,
      status: noticeFilters.status,
      notify_type: noticeFilters.notify_type,
      receiver_type: noticeFilters.receiver_type,
      q: noticeFilters.keyword || undefined,
      start_at: noticeTimeRange.value?.[0]?.toISOString(),
      end_at: noticeTimeRange.value?.[1]?.toISOString()
    })
    const parsed = normalizeList((res as any)?.data || res)
    alertNotifications.value = parsed.items || []
    noticePagination.total = parsed.total
  } finally {
    noticesLoading.value = false
  }
}

const handleTabChange = (key: string) => {
  if (key === 'metrics') loadMetricTrend()
  if (key === 'related') loadRelatedAlerts()
  if (key === 'history') loadHistoryAlerts()
  if (key === 'process') loadProcessTimeline()
  if (key === 'escalation') loadEscalationRecords()
  if (key === 'rules') loadAlertRules()
  if (key === 'notices') loadAlertNotifications()
}

const handleRelatedTableChange = (pager: any) => {
  relatedPagination.current = pager.current
  relatedPagination.pageSize = pager.pageSize
  loadRelatedAlerts()
}

const handleHistoryTableChange = (pager: any) => {
  historyPagination.current = pager.current
  historyPagination.pageSize = pager.pageSize
  loadHistoryAlerts()
}

const handleProcessTableChange = (pager: any) => {
  processPagination.current = pager.current
  processPagination.pageSize = pager.pageSize
  loadProcessTimeline()
}

const handleEscalationTableChange = (pager: any) => {
  escalationPagination.current = pager.current
  escalationPagination.pageSize = pager.pageSize
  loadEscalationRecords()
}

const handleNoticeTableChange = (pager: any) => {
  noticePagination.current = pager.current
  noticePagination.pageSize = pager.pageSize
  loadAlertNotifications()
}

const resetNoticeFilters = () => {
  noticeFilters.status = undefined
  noticeFilters.notify_type = undefined
  noticeFilters.receiver_type = undefined
  noticeFilters.keyword = ''
  noticeTimeRange.value = null
  noticePagination.current = 1
  loadAlertNotifications()
}

const handleClaim = async () => {
  if (!alertDetail.value?.id) return
  if (actionDisabled.value) return
  try {
    await claimAlert(alertDetail.value.id)
    message.success('认领成功')
    await loadAlertDetail()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '认领失败')
  }
}

const handleClose = async () => {
  if (!alertDetail.value?.id) return
  if (actionDisabled.value) return
  Modal.confirm({
    title: '确认关闭',
    content: `确定要关闭告警 "${alertDetail.value.name}" 吗？`,
    onOk: async () => {
      try {
        await closeAlert(alertDetail.value!.id)
        message.success('关闭成功')
        await loadAlertDetail()
      } catch (error: any) {
        message.error(error?.response?.data?.message || '关闭失败')
      }
    }
  })
}

onMounted(() => {
  loadAlertDetail()
  window.addEventListener('resize', resizeMetricChart)
})

onBeforeUnmount(() => {
  if (metricChart) {
    metricChart.dispose()
    metricChart = null
  }
  window.removeEventListener('resize', resizeMetricChart)
})

watch(
  () => route.params.id,
  () => {
    relatedPagination.current = 1
    historyPagination.current = 1
    processPagination.current = 1
    escalationPagination.current = 1
    noticePagination.current = 1
    noticeFilters.status = undefined
    noticeFilters.notify_type = undefined
    noticeFilters.receiver_type = undefined
    noticeFilters.keyword = ''
    noticeTimeRange.value = null
    metricRangePreset.value = '1h'
    metricCustomRange.value = null
    processEvents.value = []
    escalationRecords.value = []
    loadAlertDetail()
  }
)
</script>

<style scoped>
.alert-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.alert-title {
  font-size: 18px;
  font-weight: 600;
}

.alert-time {
  color: var(--app-text-muted);
  font-size: 12px;
  margin-top: 4px;
}

.metric-chart {
  width: 100%;
  height: 360px;
}

.alert-chip-group :deep(.ant-tag) {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
}

.alert-chip-group :deep(.alert-chip--neutral) {
  border: 1px solid var(--app-border);
  background: var(--app-surface-subtle);
  color: var(--app-text-primary);
}
</style>
