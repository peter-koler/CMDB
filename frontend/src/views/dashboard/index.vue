<template>
  <div class="app-page ops-dashboard">
    <a-card :bordered="false" class="hero-card app-surface-card">
      <div class="hero-top">
        <div class="hero-title-wrap">
          <div class="hero-kicker">Operations Overview</div>
          <h2 class="hero-title">IT 运维总览</h2>
          <div class="hero-subtitle">聚焦可用性、告警风险、采集质量与近期处置活动</div>
        </div>
        <a-space wrap>
          <a-select v-model:value="refreshSeconds" style="width: 140px">
            <a-select-option :value="0">关闭刷新</a-select-option>
            <a-select-option :value="30">30秒</a-select-option>
            <a-select-option :value="60">1分钟</a-select-option>
            <a-select-option :value="300">5分钟</a-select-option>
          </a-select>
          <a-button :loading="loading" @click="loadDashboard">立即刷新</a-button>
          <a-button type="primary" @click="goToMonitoring">进入监控中心</a-button>
        </a-space>
      </div>
      <div class="hero-meta">
        <span>最近刷新：{{ lastUpdatedText }}</span>
        <span>当前用户：{{ userInfo?.username || '-' }}</span>
      </div>
    </a-card>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card app-surface-card">
          <a-statistic title="监控目标" :value="overview.total_monitors" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card app-surface-card">
          <a-statistic title="健康目标" :value="overview.healthy_monitors" :value-style="{ color: 'var(--app-accent)' }" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card app-surface-card">
          <a-statistic title="异常目标" :value="overview.unhealthy_monitors" :value-style="{ color: 'var(--arco-warning)' }" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card app-surface-card">
          <a-statistic title="当前告警" :value="overview.open_alerts" :value-style="{ color: 'var(--arco-danger)' }" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="采集器在线" :value="onlineCollectorCount" />
          <div class="kpi-tip">总数 {{ collectorTotal }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="8" :xl="4">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="监控健康率" :value="healthRate" suffix="%" :precision="1" />
          <div class="kpi-tip">采集成功率均值 {{ successAvg }}%</div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="值班待认领" :value="onDuty.unassignedOpen" :value-style="{ color: 'var(--arco-warning)' }" />
          <div class="kpi-tip">未分派且未关闭告警</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="升级中告警" :value="onDuty.escalatingOpen" :value-style="{ color: 'var(--arco-danger)' }" />
          <div class="kpi-tip">`escalation_level > 0`</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="高危未关闭" :value="onDuty.criticalOpen" :value-style="{ color: 'var(--arco-danger)' }" />
          <div class="kpi-tip">critical 且 open</div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="SLA 逼近" :value="slaProxy.nearBreach" :value-style="{ color: 'var(--arco-warning)' }" />
          <div class="kpi-tip">持续 15-30 分钟(open)</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="SLA 超时代理" :value="slaProxy.breached" :value-style="{ color: 'var(--arco-danger)' }" />
          <div class="kpi-tip">持续超过 30 分钟(open)</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="平均恢复时长" :value="slaProxy.avgRecoverMinutes" suffix="min" :precision="1" />
          <div class="kpi-tip">历史恢复告警样本</div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="CMDB 配置项总量" :value="cmdbOverview.ciTotal" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="CMDB 模型数" :value="cmdbOverview.modelTotal" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="有实例模型占比" :value="cmdbCoverage" suffix="%" :precision="1" />
          <div class="kpi-tip">有实例模型 {{ cmdbOverview.modelWithCi }}</div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="kpi-card">
          <a-statistic title="24h CI变更" :value="cmdbOverview.ciChanged24h" :value-style="{ color: 'var(--app-accent)' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :xl="16">
        <a-card :bordered="false" class="panel-card" title="24小时态势趋势">
          <div ref="trendChartRef" class="chart-host chart-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :xl="8">
        <a-card :bordered="false" class="panel-card" title="状态与告警级别占比">
          <div ref="statusChartRef" class="chart-host" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" class="panel-card" title="业务分组风险热度（按应用）">
          <a-table
            :columns="appRiskColumns"
            :data-source="appRiskRows"
            :pagination="false"
            size="small"
            :locale="{ emptyText: '暂无数据' }"
            row-key="app"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'open'">
                <a-tag color="red">{{ record.open }}</a-tag>
              </template>
              <template v-if="column.key === 'critical'">
                <a-tag color="volcano">{{ record.critical }}</a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="10">
        <a-card :bordered="false" class="panel-card" title="高风险监控对象 Top10">
          <a-table
            :columns="topColumns"
            :data-source="topAlertMonitors"
            :pagination="false"
            size="small"
            :locale="{ emptyText: '暂无数据' }"
            row-key="name"
          >
            <template #bodyCell="{ column, index, record }">
              <template v-if="column.key === 'rank'">
                <a-tag :color="index < 3 ? 'blue' : 'default'">#{{ index + 1 }}</a-tag>
              </template>
              <template v-if="column.key === 'value'">
                <span class="risk-count">{{ record.value }}</span>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card :bordered="false" class="panel-card" title="值班提示">
          <a-space direction="vertical" style="width: 100%" :size="8">
            <a-alert
              v-if="onDuty.criticalOpen > 0"
              type="error"
              show-icon
              :message="`有 ${onDuty.criticalOpen} 条高危告警未关闭`"
            />
            <a-alert
              v-if="slaProxy.breached > 0"
              type="warning"
              show-icon
              :message="`有 ${slaProxy.breached} 条告警已超过30分钟`"
            />
            <a-alert
              v-if="onDuty.unassignedOpen > 0"
              type="info"
              show-icon
              :message="`有 ${onDuty.unassignedOpen} 条告警未认领`"
            />
            <a-empty v-if="onDuty.criticalOpen === 0 && slaProxy.breached === 0 && onDuty.unassignedOpen === 0" description="当前无值班阻塞项" />
          </a-space>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="24">
        <a-card :bordered="false" class="panel-card" title="最近告警事件">
          <a-table
            :columns="alertColumns"
            :data-source="recentAlerts"
            :pagination="false"
            size="small"
            :locale="{ emptyText: '暂无告警' }"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                {{ record.name || '-' }}
              </template>
              <template v-if="column.key === 'monitor_name'">
                {{ record.monitor_name || '-' }}
              </template>
              <template v-if="column.key === 'level'">
                <a-tag :color="alertLevelColor(record.level)">{{ record.level || '-' }}</a-tag>
              </template>
              <template v-if="column.key === 'triggered_at'">
                {{ formatDateTime(record.triggered_at) }}
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'open' ? 'red' : 'default'">{{ record.status || '-' }}</a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :lg="12">
        <a-card :bordered="false" class="panel-card">
          <template #title>CMDB 模型热度 Top8</template>
          <template #extra>
            <a-button type="link" @click="goToCmdb">进入配置仓库</a-button>
          </template>
          <a-table
            :columns="cmdbModelColumns"
            :data-source="modelHotRows"
            :pagination="false"
            size="small"
            row-key="model_id"
            :locale="{ emptyText: '暂无 CMDB 数据' }"
          />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="12">
        <a-card :bordered="false" class="panel-card">
          <template #title>最近 CI 变更事件</template>
          <template #extra>
            <a-button type="link" @click="goToCmdbHistory">查看历史</a-button>
          </template>
          <a-table
            :columns="ciChangeColumns"
            :data-source="recentCiChanges"
            :pagination="false"
            size="small"
            row-key="id"
            :locale="{ emptyText: '暂无 CI 变更' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'operation'">
                <a-tag :color="record.operation === 'DELETE' ? 'red' : (record.operation === 'UPDATE' ? 'orange' : 'blue')">
                  {{ record.operation }}
                </a-tag>
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatDateTime(record.created_at) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :lg="16">
        <a-card :bordered="false" class="panel-card">
          <template #title>近期运维活动</template>
          <template #extra>
            <a-button type="link" @click="goToLog">查看全部</a-button>
          </template>
          <a-table
            :columns="logColumns"
            :data-source="recentLogs"
            :pagination="false"
            size="small"
            :loading="logLoading"
            :locale="{ emptyText: '暂无日志' }"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'operation_type'">
                <a-tag :color="logTypeColor(record.operation_type)">{{ logTypeText(record.operation_type) }}</a-tag>
              </template>
              <template v-if="column.key === 'status'">
                <a-badge :status="record.status === 'success' ? 'success' : 'error'" :text="record.status === 'success' ? '成功' : '失败'" />
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatDateTime(record.created_at) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" class="panel-card" title="快捷处置">
          <a-space direction="vertical" style="width: 100%" :size="10">
            <a-button block type="primary" @click="goToAlertCenter">进入告警中心</a-button>
            <a-button block @click="goToTargetList">查看监控列表</a-button>
            <a-button block @click="goToMonitoringDashboard">监控大屏</a-button>
            <a-button block @click="goToCollector">采集器管理</a-button>
            <a-button block @click="goToCmdb">CMDB 配置仓库</a-button>
            <a-button block @click="goToCmdbHistory">CMDB 变更历史</a-button>
            <a-divider style="margin: 8px 0" />
            <a-statistic title="用户总数" :value="userCount" />
            <a-statistic title="今日登录" :value="todayLogins" />
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent, type TooltipComponentOption, type LegendComponentOption, type GridComponentOption } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption, EChartsType } from 'echarts/core'
import type { LineSeriesOption, PieSeriesOption } from 'echarts/charts'
import { getMonitoringDashboard, getCollectors, getCurrentAlerts, type MonitoringDashboardData, type MonitoringDashboardPoint } from '@/api/monitoring'
import { getLogs } from '@/api/log'
import { getUsers } from '@/api/user'
import { getModelsTree } from '@/api/cmdb'
import { getInstances, getAllCiHistory } from '@/api/ci'

echarts.use([LineChart, PieChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

type ECOption = ComposeOption<
  LineSeriesOption
  | PieSeriesOption
  | TooltipComponentOption
  | LegendComponentOption
  | GridComponentOption
>

const router = useRouter()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)

const loading = ref(false)
const logLoading = ref(false)
const refreshSeconds = ref(60)
const lastUpdatedAt = ref(0)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const overview = reactive({
  total_monitors: 0,
  healthy_monitors: 0,
  unhealthy_monitors: 0,
  open_alerts: 0
})

const statusDistribution = ref<Array<{ name: string; value: number }>>([])
const alertTrend = ref<MonitoringDashboardPoint[]>([])
const successRateTrend = ref<MonitoringDashboardPoint[]>([])
const topAlertMonitors = ref<Array<{ name: string; value: number }>>([])
const recentAlerts = ref<any[]>([])
const currentAlerts = ref<any[]>([])
const recentLogs = ref<any[]>([])

const collectorTotal = ref(0)
const onlineCollectorCount = ref(0)
const userCount = ref(0)
const todayLogins = ref(0)
const modelHotRows = ref<Array<{ model_id: number; title: string; code: string; ci_count: number }>>([])
const recentCiChanges = ref<any[]>([])

const cmdbOverview = reactive({
  ciTotal: 0,
  modelTotal: 0,
  modelWithCi: 0,
  ciChanged24h: 0
})

const trendChartRef = ref<HTMLDivElement | null>(null)
const statusChartRef = ref<HTMLDivElement | null>(null)
let trendChart: EChartsType | null = null
let statusChart: EChartsType | null = null

const topColumns = [
  { title: '排名', key: 'rank', width: 74 },
  { title: '监控对象', dataIndex: 'name', key: 'name' },
  { title: '告警次数', dataIndex: 'value', key: 'value', width: 100 }
]

const appRiskColumns = [
  { title: '应用', dataIndex: 'app', key: 'app' },
  { title: 'Open', dataIndex: 'open', key: 'open', width: 88 },
  { title: 'Critical', dataIndex: 'critical', key: 'critical', width: 96 }
]

const alertColumns = [
  { title: '告警名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '对象', dataIndex: 'monitor_name', key: 'monitor_name', ellipsis: true, width: 160 },
  { title: '级别', dataIndex: 'level', key: 'level', width: 100 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 160 }
]

const logColumns = [
  { title: '用户', dataIndex: 'username', key: 'username', width: 100 },
  { title: '类型', dataIndex: 'operation_type', key: 'operation_type', width: 90 },
  { title: '描述', dataIndex: 'operation_desc', key: 'operation_desc', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 }
]

const cmdbModelColumns = [
  { title: '模型', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: 'CI数', dataIndex: 'ci_count', key: 'ci_count', width: 90 }
]

const ciChangeColumns = [
  { title: 'CI', dataIndex: 'ci_name', key: 'ci_name', ellipsis: true },
  { title: '动作', dataIndex: 'operation', key: 'operation', width: 90 },
  { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 100 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 }
]

const healthRate = computed(() => {
  if (!overview.total_monitors) return 0
  return Number(((overview.healthy_monitors / overview.total_monitors) * 100).toFixed(1))
})

const onDuty = computed(() => {
  const items = currentAlerts.value || []
  let unassignedOpen = 0
  let escalatingOpen = 0
  let criticalOpen = 0
  for (const item of items) {
    const status = String(item?.status || '').toLowerCase()
    const isOpen = status === 'open'
    if (!isOpen) continue
    const assignee = String(item?.assignee || '').trim()
    const level = String(item?.level || '').toLowerCase()
    const escalationLevel = Number(item?.escalation_level || 0)
    if (!assignee) unassignedOpen += 1
    if (escalationLevel > 0) escalatingOpen += 1
    if (level === 'critical') criticalOpen += 1
  }
  return { unassignedOpen, escalatingOpen, criticalOpen }
})

const slaProxy = computed(() => {
  const items = currentAlerts.value || []
  let nearBreach = 0
  let breached = 0
  const recoveredDurations: number[] = []
  for (const item of items) {
    const status = String(item?.status || '').toLowerCase()
    const seconds = Number(item?.duration_seconds || 0)
    if (status === 'open') {
      if (seconds >= 1800) breached += 1
      else if (seconds >= 900) nearBreach += 1
    }
    if (status === 'closed' && seconds > 0) {
      recoveredDurations.push(seconds / 60)
    }
  }
  const avgRecoverMinutes = recoveredDurations.length
    ? recoveredDurations.reduce((a, b) => a + b, 0) / recoveredDurations.length
    : 0
  return {
    nearBreach,
    breached,
    avgRecoverMinutes: Number(avgRecoverMinutes.toFixed(1))
  }
})

const appRiskRows = computed(() => {
  const bucket: Record<string, { app: string; open: number; critical: number }> = {}
  for (const item of currentAlerts.value || []) {
    const app = String(item?.app || 'unknown').trim() || 'unknown'
    const status = String(item?.status || '').toLowerCase()
    const level = String(item?.level || '').toLowerCase()
    if (!bucket[app]) {
      bucket[app] = { app, open: 0, critical: 0 }
    }
    if (status === 'open') bucket[app].open += 1
    if (status === 'open' && level === 'critical') bucket[app].critical += 1
  }
  return Object.values(bucket)
    .sort((a, b) => {
      if (b.critical !== a.critical) return b.critical - a.critical
      return b.open - a.open
    })
    .slice(0, 8)
})

const successAvg = computed(() => {
  if (!successRateTrend.value.length) return 0
  const sum = successRateTrend.value.reduce((acc, item) => acc + Number(item.value || 0), 0)
  return Number((sum / successRateTrend.value.length).toFixed(1))
})

const cmdbCoverage = computed(() => {
  if (!cmdbOverview.modelTotal) return 0
  return Number(((cmdbOverview.modelWithCi / cmdbOverview.modelTotal) * 100).toFixed(1))
})

const lastUpdatedText = computed(() => {
  if (!lastUpdatedAt.value) return '尚未刷新'
  return dayjs(lastUpdatedAt.value).format('YYYY-MM-DD HH:mm:ss')
})

function fillPoints(items: MonitoringDashboardPoint[]) {
  if (Array.isArray(items) && items.length > 0) return items
  return Array.from({ length: 24 }).map((_, idx) => ({ time: `${String(idx).padStart(2, '0')}:00`, value: 0 }))
}

function ensureChart(el: HTMLDivElement | null, current: EChartsType | null) {
  if (!el) return null
  if (current) return current
  return echarts.init(el)
}

function renderTrendChart() {
  trendChart = ensureChart(trendChartRef.value, trendChart)
  if (!trendChart) return
  const alertSeries = fillPoints(alertTrend.value)
  const successSeries = fillPoints(successRateTrend.value)
  const x = alertSeries.map((item) => item.time)
  const option: ECOption = {
    color: ['#1f4fbf', '#13c2c2'],
    tooltip: { trigger: 'axis' },
    legend: { top: 4 },
    grid: { left: 44, right: 48, top: 36, bottom: 26 },
    xAxis: { type: 'category', data: x, boundaryGap: false },
    yAxis: [
      {
        type: 'value',
        name: '告警数',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#edf1f6' } }
      },
      {
        type: 'value',
        name: '成功率%',
        min: 0,
        max: 100,
        position: 'right',
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '告警数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: alertSeries.map((item) => Number(item.value || 0)),
        areaStyle: { opacity: 0.1 }
      },
      {
        name: '采集成功率',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        yAxisIndex: 1,
        data: successSeries.map((item) => Number(item.value || 0))
      }
    ]
  }
  trendChart.setOption(option, true)
}

function renderStatusChart() {
  statusChart = ensureChart(statusChartRef.value, statusChart)
  if (!statusChart) return

  const statusData = (statusDistribution.value || []).filter((item) => Number(item.value || 0) > 0)
  const levelBucket: Record<string, number> = { critical: 0, warning: 0, info: 0, other: 0 }
  for (const item of recentAlerts.value) {
    const level = String(item?.level || '').toLowerCase()
    if (level in levelBucket) levelBucket[level] += 1
    else levelBucket.other += 1
  }
  const levelData = [
    { name: 'critical', value: levelBucket.critical },
    { name: 'warning', value: levelBucket.warning },
    { name: 'info', value: levelBucket.info },
    { name: 'other', value: levelBucket.other }
  ].filter((item) => item.value > 0)

  const option: ECOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, left: 'center' },
    series: [
      {
        name: '状态分布',
        type: 'pie',
        radius: ['38%', '60%'],
        center: ['32%', '45%'],
        label: { formatter: '{b}\n{d}%' },
        data: statusData.length ? statusData : [{ name: '暂无', value: 1 }]
      },
      {
        name: '级别分布',
        type: 'pie',
        radius: ['38%', '60%'],
        center: ['72%', '45%'],
        label: { formatter: '{b}\n{d}%' },
        data: levelData.length ? levelData : [{ name: '暂无', value: 1 }]
      }
    ]
  }
  statusChart.setOption(option, true)
}

function renderCharts() {
  nextTick(() => {
    renderTrendChart()
    renderStatusChart()
  })
}

function resizeCharts() {
  trendChart?.resize()
  statusChart?.resize()
}

function disposeCharts() {
  trendChart?.dispose()
  statusChart?.dispose()
  trendChart = null
  statusChart = null
}

function alertLevelColor(level?: string) {
  const v = String(level || '').toLowerCase()
  if (v === 'critical') return 'red'
  if (v === 'warning') return 'orange'
  if (v === 'info') return 'blue'
  return 'default'
}

function logTypeColor(type?: string) {
  const colors: Record<string, string> = {
    LOGIN: 'blue',
    LOGOUT: 'default',
    CREATE: 'green',
    UPDATE: 'orange',
    DELETE: 'red'
  }
  return colors[String(type || '').toUpperCase()] || 'default'
}

function logTypeText(type?: string) {
  const texts: Record<string, string> = {
    LOGIN: '登录',
    LOGOUT: '登出',
    CREATE: '创建',
    UPDATE: '更新',
    DELETE: '删除'
  }
  const key = String(type || '').toUpperCase()
  return texts[key] || key || '-'
}

function formatDateTime(raw?: string) {
  if (!raw) return '-'
  return dayjs(raw).format('MM-DD HH:mm:ss')
}

function normalizeAlertRecord(item: any) {
  const level = String(item?.level || '').trim() || 'warning'
  const statusRaw = String(item?.status || '').toLowerCase()
  const normalizedStatus = statusRaw === 'firing' ? 'open' : statusRaw
  const status = (normalizedStatus === 'closed' || normalizedStatus === 'resolved' || normalizedStatus === 'recovered') ? 'closed' : 'open'
  const name = String(item?.name || item?.title || item?.content || item?.app || '').trim() || '-'
  const monitorName = String(item?.monitor_name || item?.instance || item?.target || item?.app || '').trim() || '-'
  return {
    ...item,
    level,
    status,
    name,
    monitor_name: monitorName,
    triggered_at: item?.triggered_at || item?.start_at || item?.created_at || ''
  }
}

function flattenModelNodes(tree: any[]) {
  const out: Array<{ model_id: number; title: string; code: string; ci_count: number }> = []
  const stack = Array.isArray(tree) ? [...tree] : []
  while (stack.length) {
    const node = stack.pop()
    if (!node || typeof node !== 'object') continue
    if (node.is_model && node.model_id) {
      out.push({
        model_id: Number(node.model_id),
        title: String(node.title || node.name || '-'),
        code: String(node.code || '-'),
        ci_count: Number(node.ci_count || 0)
      })
    }
    if (Array.isArray(node.children)) {
      stack.push(...node.children)
    }
  }
  return out
}

function normalizeCiChange(item: any) {
  return {
    id: item?.id || `${item?.ci_id || ''}-${item?.created_at || ''}`,
    ci_name: item?.ci?.name || item?.ci?.code || '-',
    operation: String(item?.operation || '-').toUpperCase(),
    operator_name: item?.operator_name || '-',
    created_at: item?.created_at || ''
  }
}

async function loadCmdbStats() {
  const now = dayjs()
  const from24h = now.subtract(24, 'hour')
  const [treeRes, instanceRes, historyRes, history24Res] = await Promise.allSettled([
    getModelsTree(),
    getInstances({ page: 1, per_page: 1 }),
    getAllCiHistory({ page: 1, per_page: 6 }),
    getAllCiHistory({
      page: 1,
      per_page: 1,
      date_from: from24h.format('YYYY-MM-DDTHH:mm:ss'),
      date_to: now.format('YYYY-MM-DDTHH:mm:ss')
    })
  ])

  if (treeRes.status === 'fulfilled') {
    const tree = Array.isArray(treeRes.value?.data) ? treeRes.value.data : []
    const models = flattenModelNodes(tree)
    cmdbOverview.modelTotal = models.length
    cmdbOverview.modelWithCi = models.filter((m) => m.ci_count > 0).length
    modelHotRows.value = models.sort((a, b) => b.ci_count - a.ci_count).slice(0, 8)
    if (!cmdbOverview.ciTotal) {
      cmdbOverview.ciTotal = models.reduce((sum, m) => sum + Number(m.ci_count || 0), 0)
    }
  } else {
    modelHotRows.value = []
  }

  if (instanceRes.status === 'fulfilled') {
    cmdbOverview.ciTotal = Number(instanceRes.value?.data?.total || 0)
  }

  if (historyRes.status === 'fulfilled') {
    const items = Array.isArray(historyRes.value?.data?.items) ? historyRes.value.data.items : []
    recentCiChanges.value = items.map(normalizeCiChange)
  } else {
    recentCiChanges.value = []
  }

  if (history24Res.status === 'fulfilled') {
    cmdbOverview.ciChanged24h = Number(history24Res.value?.data?.total || 0)
  } else {
    cmdbOverview.ciChanged24h = 0
  }
}

function normalizeCollectorList(payload: any) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

async function loadOpsStats() {
  try {
    const [collectorRes, usersRes, loginRes, logsRes, currentAlertsRes] = await Promise.all([
      getCollectors({ page: 1, page_size: 200 }),
      getUsers({ per_page: 1 }),
      getLogs({
        operation_type: 'LOGIN',
        status: 'success',
        date_from: dayjs().format('YYYY-MM-DD'),
        date_to: dayjs().format('YYYY-MM-DD'),
        per_page: 1
      }),
      getLogs({ per_page: 6 }),
      getCurrentAlerts({ page: 1, page_size: 200 })
    ])

    const collectorItems = normalizeCollectorList(collectorRes?.data)
    collectorTotal.value = collectorItems.length
    onlineCollectorCount.value = collectorItems.filter((item: any) => {
      const status = typeof item?.status === 'number' ? item.status : String(item?.status || '').toLowerCase()
      return status === 0 || status === 'online' || status === 'up' || status === 'healthy' || status === '0'
    }).length

    userCount.value = Number(usersRes?.data?.total || 0)
    todayLogins.value = Number(loginRes?.data?.total || 0)
    recentLogs.value = Array.isArray(logsRes?.data?.items) ? logsRes.data.items : []
    currentAlerts.value = Array.isArray(currentAlertsRes?.data?.items) ? currentAlertsRes.data.items.map(normalizeAlertRecord) : []
  } catch (error) {
    console.error(error)
  }
}

async function loadDashboard() {
  loading.value = true
  logLoading.value = true
  try {
    const res = await getMonitoringDashboard()
    const data = (res?.data || {}) as Partial<MonitoringDashboardData>
    Object.assign(overview, data.overview || {})
    statusDistribution.value = Array.isArray(data.status_distribution) ? data.status_distribution : []
    alertTrend.value = Array.isArray(data.alert_trend) ? data.alert_trend : []
    successRateTrend.value = Array.isArray(data.success_rate_trend) ? data.success_rate_trend : []
    topAlertMonitors.value = Array.isArray(data.top_alert_monitors) ? data.top_alert_monitors.slice(0, 10) : []
    recentAlerts.value = Array.isArray(data.recent_alerts) ? data.recent_alerts.map(normalizeAlertRecord).slice(0, 8) : []
    await loadOpsStats()
    await loadCmdbStats()
    lastUpdatedAt.value = Date.now()
    renderCharts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载首页总览失败')
  } finally {
    loading.value = false
    logLoading.value = false
  }
}

function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (!refreshSeconds.value) return
  refreshTimer = setInterval(() => loadDashboard(), refreshSeconds.value * 1000)
}

function goToMonitoring() {
  router.push('/monitoring/list')
}

function goToMonitoringDashboard() {
  router.push('/monitoring/dashboard')
}

function goToAlertCenter() {
  router.push('/alert-center/current')
}

function goToTargetList() {
  router.push('/monitoring/list')
}

function goToCollector() {
  router.push('/monitoring/collector')
}

function goToLog() {
  router.push('/system/log')
}

function goToCmdb() {
  router.push('/cmdb/instance')
}

function goToCmdbHistory() {
  router.push('/cmdb/history')
}

watch(refreshSeconds, () => {
  startAutoRefresh()
})

onMounted(() => {
  loadDashboard()
  startAutoRefresh()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
</script>

<style scoped>
.ops-dashboard {
  min-height: 100%;
  gap: 14px;
  padding-bottom: 8px;
}

.section {
  margin-top: 14px;
}

.hero-card,
.kpi-card,
.panel-card {
  border-radius: var(--arco-radius-md);
  border: 1px solid var(--arco-border);
  box-shadow: none;
}

.hero-card {
  background:
    radial-gradient(circle at top right, rgba(9, 96, 189, 0.08), transparent 28%),
    var(--arco-surface);
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-kicker {
  color: var(--arco-text-tertiary);
  letter-spacing: 0.08em;
  font-size: 11px;
  text-transform: uppercase;
}

.hero-title {
  margin: 2px 0 4px;
  font-size: 28px;
  line-height: 1.2;
  color: var(--arco-text);
}

.hero-subtitle {
  color: var(--arco-text-secondary);
  font-size: 13px;
}

.hero-meta {
  display: flex;
  gap: 18px;
  margin-top: 12px;
  color: var(--arco-text-secondary);
  font-size: 12px;
  flex-wrap: wrap;
}

.kpi-tip {
  margin-top: 6px;
  color: var(--arco-text-tertiary);
  font-size: 12px;
}

.chart-host {
  width: 100%;
  height: 300px;
}

.chart-lg {
  height: 360px;
}

.risk-count {
  font-weight: 700;
  color: var(--arco-danger);
}

@media (max-width: 992px) {
  .hero-title {
    font-size: 24px;
  }

  .chart-host {
    height: 280px;
  }

  .chart-lg {
    height: 320px;
  }
}
</style>
