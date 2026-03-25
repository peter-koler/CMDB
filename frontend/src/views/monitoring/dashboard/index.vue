<template>
  <div class="app-page monitoring-visual-page">
    <a-card :bordered="false" class="toolbar-card app-surface-card">
      <div class="toolbar-inner">
        <a-space wrap>
          <a-select v-model:value="refreshSeconds" style="width: 160px">
            <a-select-option :value="0">自动刷新关闭</a-select-option>
            <a-select-option :value="30">每30秒刷新</a-select-option>
            <a-select-option :value="60">每1分钟刷新</a-select-option>
            <a-select-option :value="300">每5分钟刷新</a-select-option>
          </a-select>
          <a-button :loading="loading" @click="loadDashboard">立即刷新</a-button>
          <a-button type="primary" @click="goToAlertCenter">告警中心</a-button>
        </a-space>
        <div class="update-time">{{ lastUpdatedText }}</div>
      </div>
    </a-card>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :sm="12" :xl="6">
        <a-card :bordered="false" class="mini-card app-surface-card">
          <div class="mini-title">监控健康率</div>
          <div ref="ringHealthRef" class="mini-host" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :xl="6">
        <a-card :bordered="false" class="mini-card app-surface-card">
          <div class="mini-title">采集成功率</div>
          <div ref="ringSuccessRef" class="mini-host" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :xl="6">
        <a-card :bordered="false" class="mini-card app-surface-card">
          <div class="mini-title">异常监控占比</div>
          <div ref="ringAnomalyRef" class="mini-host" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :xl="6">
        <a-card :bordered="false" class="mini-card app-surface-card">
          <div class="mini-title">告警压力指数</div>
          <div ref="ringPressureRef" class="mini-host" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :xl="16">
        <a-card :bordered="false" title="24小时趋势：告警数 & 成功率" class="panel-card app-surface-card">
          <div ref="trendChartRef" class="panel-host panel-host-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :xl="8">
        <a-card :bordered="false" title="Top10风险监控对象" class="panel-card app-surface-card">
          <div ref="topChartRef" class="panel-host panel-host-lg" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[14, 14]" class="section">
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" title="监控状态分布" class="panel-card app-surface-card">
          <div ref="statusChartRef" class="panel-host" />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" title="告警级别占比" class="panel-card app-surface-card">
          <div ref="levelChartRef" class="panel-host" />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" title="告警脉冲" class="panel-card app-surface-card">
          <div ref="pulseChartRef" class="panel-host" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts/core'
import { GaugeChart, BarChart, PieChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  type GridComponentOption,
  type TooltipComponentOption,
  type LegendComponentOption,
  type DataZoomComponentOption
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ComposeOption, EChartsType } from 'echarts/core'
import type { GaugeSeriesOption, BarSeriesOption, PieSeriesOption, LineSeriesOption } from 'echarts/charts'
import {
  getMonitoringDashboard,
  type MonitoringDashboardData,
  type MonitoringDashboardPoint
} from '@/api/monitoring'

echarts.use([GaugeChart, BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

type ECOption = ComposeOption<
  | GaugeSeriesOption
  | BarSeriesOption
  | PieSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | LegendComponentOption
  | DataZoomComponentOption
>

const router = useRouter()
const loading = ref(false)
const refreshSeconds = ref(60)
const lastUpdatedAt = ref<number>(0)
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
const recentAlerts = ref<Array<{ level?: string }>>([])

const ringHealthRef = ref<HTMLDivElement | null>(null)
const ringSuccessRef = ref<HTMLDivElement | null>(null)
const ringAnomalyRef = ref<HTMLDivElement | null>(null)
const ringPressureRef = ref<HTMLDivElement | null>(null)
const trendChartRef = ref<HTMLDivElement | null>(null)
const topChartRef = ref<HTMLDivElement | null>(null)
const statusChartRef = ref<HTMLDivElement | null>(null)
const levelChartRef = ref<HTMLDivElement | null>(null)
const pulseChartRef = ref<HTMLDivElement | null>(null)

let ringHealthChart: EChartsType | null = null
let ringSuccessChart: EChartsType | null = null
let ringAnomalyChart: EChartsType | null = null
let ringPressureChart: EChartsType | null = null
let trendChart: EChartsType | null = null
let topChart: EChartsType | null = null
let statusChart: EChartsType | null = null
let levelChart: EChartsType | null = null
let pulseChart: EChartsType | null = null
const brandBlue = '#2f6fed'
const brandBlueSoft = '#5f8fda'
const brandSlate = '#7a8799'
const lineGridColor = '#edf1f6'

const lastUpdatedText = computed(() => {
  if (!lastUpdatedAt.value) return '尚未刷新'
  return `最近刷新: ${dayjs(lastUpdatedAt.value).format('YYYY-MM-DD HH:mm:ss')}`
})

const healthRate = computed(() => {
  if (!overview.total_monitors) return 0
  return Number(((overview.healthy_monitors / overview.total_monitors) * 100).toFixed(1))
})

const successAvg = computed(() => {
  if (!successRateTrend.value.length) return 0
  const sum = successRateTrend.value.reduce((acc, one) => acc + Number(one.value || 0), 0)
  return Number((sum / successRateTrend.value.length).toFixed(1))
})

const anomalyRate = computed(() => {
  if (!overview.total_monitors) return 0
  return Number(((overview.unhealthy_monitors / overview.total_monitors) * 100).toFixed(1))
})

const alertPressure = computed(() => {
  if (!overview.total_monitors) return 0
  return Number(Math.min(100, (overview.open_alerts / overview.total_monitors) * 100).toFixed(1))
})

const levelDistribution = computed(() => {
  const bucket: Record<string, number> = {
    严重: 0,
    警告: 0,
    提示: 0,
    其他: 0
  }
  for (const alert of recentAlerts.value || []) {
    const level = String(alert.level || '').toLowerCase()
    if (level === 'critical') bucket['严重'] += 1
    else if (level === 'warning') bucket['警告'] += 1
    else if (level === 'info') bucket['提示'] += 1
    else bucket['其他'] += 1
  }
  return Object.keys(bucket).map((name) => ({ name, value: bucket[name] }))
})

function fillPoints(items: MonitoringDashboardPoint[]) {
  if (Array.isArray(items) && items.length > 0) return items
  return Array.from({ length: 24 }).map((_, idx) => ({ time: `${String(idx).padStart(2, '0')}:00`, value: 0 }))
}

function ensureChart(refEl: HTMLDivElement | null, current: EChartsType | null) {
  if (!refEl) return null
  if (current) return current
  return echarts.init(refEl)
}

function buildRingOption(title: string, value: number, color: string): ECOption {
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 225,
        endAngle: -45,
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [value / 100, color],
              [1, '#edf0f6']
            ]
          }
        },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}%',
          offsetCenter: [0, '8%'],
          fontSize: 24,
          fontWeight: 700,
          color: color
        },
        title: {
          show: true,
          offsetCenter: [0, '54%'],
          fontSize: 12,
          color: '#8c8c8c'
        },
        data: [{ value: Number(value.toFixed(1)), name: title }]
      }
    ]
  }
}

function renderRingCharts() {
  ringHealthChart = ensureChart(ringHealthRef.value, ringHealthChart)
  ringSuccessChart = ensureChart(ringSuccessRef.value, ringSuccessChart)
  ringAnomalyChart = ensureChart(ringAnomalyRef.value, ringAnomalyChart)
  ringPressureChart = ensureChart(ringPressureRef.value, ringPressureChart)

  ringHealthChart?.setOption(buildRingOption('健康率', healthRate.value, brandBlue), true)
  ringSuccessChart?.setOption(buildRingOption('成功率', successAvg.value, brandBlueSoft), true)
  ringAnomalyChart?.setOption(buildRingOption('异常率', anomalyRate.value, '#6f84a1'), true)
  ringPressureChart?.setOption(buildRingOption('压力指数', alertPressure.value, brandSlate), true)
}

function renderTrendChart() {
  trendChart = ensureChart(trendChartRef.value, trendChart)
  if (!trendChart) return

  const alerts = fillPoints(alertTrend.value)
  const success = fillPoints(successRateTrend.value)
  const x = alerts.map((item) => item.time)

  const option: ECOption = {
    color: ['#7f8fa6', brandBlue],
    tooltip: { trigger: 'axis' },
    legend: { top: 4 },
    grid: { left: 50, right: 56, top: 36, bottom: 46 },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 14, bottom: 12 }
    ],
    xAxis: {
      type: 'category',
      data: x,
      boundaryGap: false,
      axisLabel: { hideOverlap: true }
    },
    yAxis: [
      {
        type: 'value',
        name: '告警数',
        minInterval: 1,
        splitLine: { lineStyle: { color: lineGridColor } }
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
        type: 'bar',
        data: alerts.map((item) => Number(item.value || 0)),
        yAxisIndex: 0,
        barMaxWidth: 16,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: '#8fa2b8'
        }
      },
      {
        name: '成功率',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        yAxisIndex: 1,
        data: success.map((item) => Number(item.value || 0)),
        lineStyle: { width: 3 },
        areaStyle: { opacity: 0.08 }
      }
    ]
  }

  trendChart.setOption(option, true)
}

function renderTopChart() {
  topChart = ensureChart(topChartRef.value, topChart)
  if (!topChart) return

  const rows = (topAlertMonitors.value || []).slice(0, 10)
  const names = rows.map((item) => item.name)
  const values = rows.map((item) => Number(item.value || 0))

  const option: ECOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 132, right: 16, top: 10, bottom: 22 },
    xAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: lineGridColor } }
    },
    yAxis: {
      type: 'category',
      data: names.length ? names : ['暂无数据'],
      inverse: true,
      axisLabel: { width: 110, overflow: 'truncate' }
    },
    series: [
      {
        type: 'bar',
        data: values.length ? values : [0],
        barMaxWidth: 18,
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          color: brandBlue
        },
        label: { show: true, position: 'right' }
      }
    ]
  }

  topChart.setOption(option, true)
}

function renderStatusChart() {
  statusChart = ensureChart(statusChartRef.value, statusChart)
  if (!statusChart) return

  const data = (statusDistribution.value.length ? statusDistribution.value : [
    { name: '正常', value: overview.healthy_monitors },
    { name: '异常', value: overview.unhealthy_monitors }
  ]).filter((item) => item.value > 0)

  const option: ECOption = {
    color: [brandBlue, '#7f97b8', '#9fb3cc', '#c3d0e0'],
    tooltip: { trigger: 'item' },
    legend: { bottom: 2, left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '68%'],
        center: ['50%', '45%'],
        label: { formatter: '{b} {d}%' },
        data: data.length ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#d9d9d9' } }]
      }
    ]
  }

  statusChart.setOption(option, true)
}

function renderLevelChart() {
  levelChart = ensureChart(levelChartRef.value, levelChart)
  if (!levelChart) return

  const data = levelDistribution.value.filter((item) => item.value > 0)

  const option: ECOption = {
    color: ['#d07070', '#d2a169', '#6f95c9', '#a3adba'],
    tooltip: { trigger: 'item' },
    legend: { bottom: 2, left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '45%'],
        label: { formatter: '{b}\n{c}' },
        data: data.length ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#d9d9d9' } }]
      }
    ]
  }

  levelChart.setOption(option, true)
}

function renderPulseChart() {
  pulseChart = ensureChart(pulseChartRef.value, pulseChart)
  if (!pulseChart) return

  const alerts = fillPoints(alertTrend.value)
  const vals = alerts.map((one) => Number(one.value || 0))
  const x = alerts.map((one) => one.time)
  const moving: number[] = []
  for (let i = 0; i < vals.length; i++) {
    const start = Math.max(0, i - 2)
    const slice = vals.slice(start, i + 1)
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length
    moving.push(Number(avg.toFixed(2)))
  }

  const option: ECOption = {
    color: [brandBlue, '#9aa8b8'],
    tooltip: { trigger: 'axis' },
    legend: { top: 4 },
    grid: { left: 42, right: 16, top: 32, bottom: 30 },
    xAxis: { type: 'category', data: x, axisLabel: { hideOverlap: true } },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: lineGridColor } }
    },
    series: [
      {
        name: '实时脉冲',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: vals,
        areaStyle: {
          opacity: 0.12,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(47,111,237,0.22)' },
            { offset: 1, color: 'rgba(47,111,237,0.04)' }
          ])
        }
      },
      {
        name: '平滑脉冲',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: moving
      }
    ]
  }

  pulseChart.setOption(option, true)
}

function renderAllCharts() {
  nextTick(() => {
    renderRingCharts()
    renderTrendChart()
    renderTopChart()
    renderStatusChart()
    renderLevelChart()
    renderPulseChart()
  })
}

function resizeCharts() {
  ringHealthChart?.resize()
  ringSuccessChart?.resize()
  ringAnomalyChart?.resize()
  ringPressureChart?.resize()
  trendChart?.resize()
  topChart?.resize()
  statusChart?.resize()
  levelChart?.resize()
  pulseChart?.resize()
}

function disposeCharts() {
  ringHealthChart?.dispose()
  ringSuccessChart?.dispose()
  ringAnomalyChart?.dispose()
  ringPressureChart?.dispose()
  trendChart?.dispose()
  topChart?.dispose()
  statusChart?.dispose()
  levelChart?.dispose()
  pulseChart?.dispose()
  ringHealthChart = null
  ringSuccessChart = null
  ringAnomalyChart = null
  ringPressureChart = null
  trendChart = null
  topChart = null
  statusChart = null
  levelChart = null
  pulseChart = null
}

function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (!refreshSeconds.value) return
  refreshTimer = setInterval(() => {
    loadDashboard()
  }, refreshSeconds.value * 1000)
}

async function loadDashboard() {
  loading.value = true
  try {
    const res = await getMonitoringDashboard()
    const data = (res?.data || {}) as Partial<MonitoringDashboardData>
    Object.assign(overview, data.overview || {})
    statusDistribution.value = Array.isArray(data.status_distribution) ? data.status_distribution : []
    alertTrend.value = Array.isArray(data.alert_trend) ? data.alert_trend : []
    successRateTrend.value = Array.isArray(data.success_rate_trend) ? data.success_rate_trend : []
    topAlertMonitors.value = Array.isArray(data.top_alert_monitors) ? data.top_alert_monitors : []
    recentAlerts.value = Array.isArray(data.recent_alerts) ? (data.recent_alerts as any[]) : []
    lastUpdatedAt.value = Date.now()
    renderAllCharts()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载监控展示失败')
  } finally {
    loading.value = false
  }
}

function goToAlertCenter() {
  router.push('/alert-center/current')
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
.monitoring-visual-page {
  min-height: 100%;
  padding-bottom: 8px;
}

.section {
  margin-top: 14px;
}

.toolbar-card,
.panel-card,
.mini-card {
  border-radius: var(--arco-radius-md);
  border: 1px solid var(--arco-border);
  box-shadow: none;
}

.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.update-time {
  color: var(--arco-text-secondary);
  font-size: 12px;
}

.mini-card {
  background: var(--arco-surface);
}

.mini-title {
  font-size: 13px;
  color: var(--arco-text-secondary);
  margin-bottom: 8px;
  font-weight: 600;
}

.mini-host {
  width: 100%;
  height: 168px;
}

.panel-host {
  width: 100%;
  height: 280px;
}

.panel-host-lg {
  height: 320px;
}

@media (max-width: 992px) {
  .mini-host {
    height: 152px;
  }

  .panel-host,
  .panel-host-lg {
    height: 286px;
  }
}
</style>
