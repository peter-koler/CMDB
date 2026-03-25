<template>
  <a-modal
    :open="open"
    :title="`趋势明细 - ${metricTitle || metricName}`"
    width="980px"
    :footer="null"
    @cancel="emit('update:open', false)"
  >
    <a-space direction="vertical" style="width: 100%" :size="12">
      <a-space wrap>
        <a-select v-if="!isStringMetric" v-model:value="chartType" style="width: 140px">
          <a-select-option value="line">折线图</a-select-option>
          <a-select-option value="bar">柱状图</a-select-option>
          <a-select-option value="table">表格</a-select-option>
        </a-select>
        <a-tag v-else color="blue">字符串指标：仅表格展示</a-tag>
        <a-segmented v-model:value="rangePreset" :options="rangeOptions" @change="handlePresetChange" />
        <a-range-picker
          v-model:value="customRange"
          show-time
          format="YYYY-MM-DD HH:mm:ss"
          @change="handleCustomRangeChange"
        />
        <a-button :loading="loading" @click="load">刷新</a-button>
        <a-button v-if="chartType === 'table'" :disabled="!tableRows.length" @click="exportExcel">下载Excel</a-button>
      </a-space>

      <a-alert
        type="info"
        show-icon
        :message="`监控对象: ${target || '-'} | 指标: ${metricTitle || metricName} (${metricName})`"
      />

      <a-spin :spinning="loading">
        <a-empty v-if="!hasDisplayData" description="当前时间范围暂无数据" />

        <template v-else>
          <div
            v-if="!isStringMetric && chartType !== 'table'"
            ref="chartRef"
            class="echart-wrap"
          />

          <a-table
            v-else
            :pagination="{ pageSize: 20, showSizeChanger: true, showQuickJumper: true }"
            :data-source="tableRows"
            :row-key="(row: any, idx: number) => `${row.timestamp}_${idx}`"
            size="small"
          >
            <a-table-column title="时间" data-index="time" key="time" width="220" />
            <a-table-column title="值" data-index="value_text" key="value_text" width="140" />
            <a-table-column title="monitor_id" data-index="monitor_id" key="monitor_id" width="120" />
            <a-table-column title="CI编码" data-index="ci_code" key="ci_code" width="140" />
            <a-table-column title="监控对象" data-index="target" key="target" />
            <a-table-column title="监控指标" data-index="metric_name" key="metric_name" width="200" />
          </a-table>
        </template>
      </a-spin>
    </a-space>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import dayjs, { type Dayjs } from 'dayjs'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts/core'
import type { EChartsType } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
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
import type { LineSeriesOption, BarSeriesOption } from 'echarts/charts'
import {
  fetchTrendSeries,
  formatMetricValue,
  resolveQueryStep
} from '@/composables/useMonitorMetrics'
import { exportTargetMetric, getTargetMetricLatest } from '@/api/monitoring'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, CanvasRenderer])

type ECOption = ComposeOption<
  LineSeriesOption | BarSeriesOption | TooltipComponentOption | GridComponentOption | DataZoomComponentOption | LegendComponentOption
>

const props = defineProps<{
  open: boolean
  monitorId: number
  intervalSeconds: number
  metricName: string
  metricTitle: string
  metricType?: 'number' | 'string' | 'time'
  monitorName?: string
  target?: string
  app?: string
  ciCode?: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const chartType = ref<'line' | 'bar' | 'table'>('line')
const rangePreset = ref<'1h' | '1d' | '1w' | '1m' | 'custom'>('1h')
const customRange = ref<[Dayjs, Dayjs] | null>(null)
const loading = ref(false)
const points = ref<Array<{ timestamp: number; value: number }>>([])
const stringPoints = ref<Array<{ timestamp: number; text: string }>>([])
const chartRef = ref<HTMLDivElement | null>(null)
let chart: EChartsType | null = null

function getThemeColor(name: string, fallback: string) {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const isStringMetric = computed(() => props.metricType === 'string')

const rangeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近1天', value: '1d' },
  { label: '最近1周', value: '1w' },
  { label: '最近1月', value: '1m' },
  { label: '自定义', value: 'custom' }
]

const hasDisplayData = computed(() => {
  if (isStringMetric.value) return stringPoints.value.length > 0
  return points.value.length > 0
})

const tableRows = computed(() => {
  if (isStringMetric.value) {
    return [...stringPoints.value]
      .sort((a, b) => b.timestamp - a.timestamp)
      .map((point) => ({
        timestamp: point.timestamp,
        time: dayjs(point.timestamp).format('YYYY-MM-DD HH:mm:ss'),
        value_text: point.text,
        monitor_id: props.monitorId,
        monitor_name: props.monitorName || '',
        app: props.app || '',
        target: props.target || '',
        ci_code: props.ciCode || '',
        metric_name: props.metricName,
        metric_title: props.metricTitle
      }))
  }

  return [...points.value]
    .sort((a, b) => b.timestamp - a.timestamp)
    .map((point) => ({
      timestamp: point.timestamp,
      time: dayjs(point.timestamp).format('YYYY-MM-DD HH:mm:ss'),
      value: point.value,
      value_text: formatMetricValue(point.value),
      monitor_id: props.monitorId,
      monitor_name: props.monitorName || '',
      app: props.app || '',
      target: props.target || '',
      ci_code: props.ciCode || '',
      metric_name: props.metricName,
      metric_title: props.metricTitle
    }))
})

function resolveRange() {
  const now = dayjs()
  if (rangePreset.value === 'custom' && customRange.value) {
    return {
      from: customRange.value[0].unix(),
      to: customRange.value[1].unix()
    }
  }
  if (rangePreset.value === '1d') return { from: now.subtract(1, 'day').unix(), to: now.unix() }
  if (rangePreset.value === '1w') return { from: now.subtract(7, 'day').unix(), to: now.unix() }
  if (rangePreset.value === '1m') return { from: now.subtract(30, 'day').unix(), to: now.unix() }
  return { from: now.subtract(1, 'hour').unix(), to: now.unix() }
}

function normalizeList(payload: any): { items: any[]; total: number } {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: Number(payload.total) || payload.items.length }
  return { items: [], total: 0 }
}

function ensureChartTypeByMetric() {
  if (isStringMetric.value) {
    chartType.value = 'table'
  } else if (chartType.value !== 'line' && chartType.value !== 'bar' && chartType.value !== 'table') {
    chartType.value = 'line'
  }
}

function ensureChartInstance() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
}

function disposeChart() {
  if (chart) {
    chart.dispose()
    chart = null
  }
}

function buildChartOption(): ECOption {
  const sorted = [...points.value].sort((a, b) => a.timestamp - b.timestamp)
  const xData = sorted.map((point) => dayjs(point.timestamp).format('MM-DD HH:mm'))
  const yData = sorted.map((point) => point.value)
  const isBar = chartType.value === 'bar'
  const accentColor = getThemeColor('--app-accent', '#1677ff')
  const borderColor = getThemeColor('--app-border', '#f0f0f0')
  return {
    animationDuration: 260,
    color: [accentColor],
    grid: {
      left: 56,
      right: 18,
      top: 28,
      bottom: 56
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      valueFormatter: (value) => formatMetricValue(Number(value))
    },
    legend: {
      data: [props.metricTitle || props.metricName]
    },
    dataZoom: [
      { type: 'inside', filterMode: 'none' },
      { type: 'slider', height: 16, bottom: 16 }
    ],
    xAxis: {
      type: 'category',
      boundaryGap: isBar,
      data: xData,
      axisLabel: { hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: {
        formatter: (value: number) => formatMetricValue(value)
      },
      splitLine: {
        lineStyle: { color: borderColor }
      }
    },
    series: [
      isBar
        ? {
            name: props.metricTitle || props.metricName,
            type: 'bar',
            data: yData,
            barMaxWidth: 18,
            itemStyle: {
              borderRadius: [4, 4, 0, 0]
            }
          }
        : {
            name: props.metricTitle || props.metricName,
            type: 'line',
            data: yData,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2 },
            areaStyle: { opacity: 0.14 }
          }
    ]
  }
}

function renderChart() {
  if (!props.open || isStringMetric.value || chartType.value === 'table' || !points.value.length) {
    return
  }
  ensureChartInstance()
  if (!chart) return
  chart.setOption(buildChartOption(), true)
  chart.resize()
}

async function load() {
  ensureChartTypeByMetric()
  if (!props.monitorId || !props.metricName) {
    points.value = []
    stringPoints.value = []
    disposeChart()
    return
  }
  loading.value = true
  try {
    const range = resolveRange()
    if (isStringMetric.value) {
      const rangeSeconds = Math.max(range.to - range.from, 60)
      const step = resolveQueryStep(rangeSeconds, props.intervalSeconds)
      const res = await getTargetMetricLatest(props.monitorId, {
        name: props.metricName,
        from: range.from,
        to: range.to,
        step
      })
      const parsed = normalizeList((res as any)?.data || res)
      const item = parsed.items?.[0] || null
      const ts = Number(item?.timestamp)
      const textRaw = item?.text
      const text = textRaw === undefined || textRaw === null ? '' : String(textRaw).trim()
      if (Number.isFinite(ts) && ts > 0 && text) {
        stringPoints.value = [{ timestamp: ts, text }]
      } else if (Number.isFinite(ts) && ts > 0 && Number.isFinite(Number(item?.value))) {
        const value = Number(item?.value)
        stringPoints.value = [{ timestamp: ts, text: value >= 0.5 ? 'OK' : 'FAIL' }]
      } else {
        stringPoints.value = []
      }
      points.value = []
      disposeChart()
    } else {
      points.value = await fetchTrendSeries(
        props.monitorId,
        props.metricName,
        range.from,
        range.to,
        props.intervalSeconds
      )
      stringPoints.value = []
      await nextTick()
      renderChart()
    }
  } catch {
    points.value = []
    stringPoints.value = []
    disposeChart()
  } finally {
    loading.value = false
  }
}

function handlePresetChange(value: string | number) {
  rangePreset.value = value as any
  if (rangePreset.value !== 'custom') customRange.value = null
  load()
}

function handleCustomRangeChange(value: [Dayjs, Dayjs] | null) {
  customRange.value = value
  if (value && value[0] && value[1]) {
    rangePreset.value = 'custom'
    load()
  }
}

function exportExcel() {
  if (!tableRows.value.length || !props.monitorId || !props.metricName) return
  if (isStringMetric.value) {
    const header = ['monitor_id', 'monitor_name', 'app', 'ci_code', 'target', 'metric_name', 'metric_title', 'time', 'value']
    const lines = [header.join(',')]
    for (const row of tableRows.value) {
      lines.push([
        row.monitor_id,
        row.monitor_name,
        row.app,
        row.ci_code,
        row.target,
        row.metric_name,
        row.metric_title,
        row.time,
        row.value_text
      ]
        .map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`)
        .join(','))
    }
    const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const ts = dayjs().format('YYYYMMDD_HHmmss')
    link.download = `${props.metricName}_${ts}.csv`
    link.click()
    URL.revokeObjectURL(url)
    return
  }

  const range = resolveRange()
  const rangeSeconds = Math.max(range.to - range.from, 60)
  const step = resolveQueryStep(rangeSeconds, props.intervalSeconds)
  exportTargetMetric(props.monitorId, {
    name: props.metricName,
    from: range.from,
    to: range.to,
    step
  })
    .then((blobData: any) => {
      const blob = blobData instanceof Blob ? blobData : new Blob([blobData], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const ts = dayjs().format('YYYYMMDD_HHmmss')
      link.download = `${props.metricName}_${ts}.csv`
      link.click()
      URL.revokeObjectURL(url)
    })
    .catch(() => {
      message.error('导出失败')
    })
}

watch(
  () => [props.open, props.metricName, props.metricType],
  ([open, metricName]) => {
    if (!open || !metricName) return
    ensureChartTypeByMetric()
    load()
  },
  { immediate: true }
)

watch(
  () => [chartType.value, points.value.length, props.open],
  async ([type, count, open]) => {
    if (!open || type === 'table' || isStringMetric.value || count <= 0) {
      if (type === 'table' || isStringMetric.value || !open) disposeChart()
      return
    }
    await nextTick()
    renderChart()
  }
)

const handleResize = () => {
  if (chart) chart.resize()
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      disposeChart()
      return
    }
    await nextTick()
    renderChart()
  }
)

if (typeof window !== 'undefined') {
  window.addEventListener('resize', handleResize)
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleResize)
  }
  disposeChart()
})
</script>

<style scoped>
.echart-wrap {
  width: 100%;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  height: 280px;
  background: var(--app-surface-card);
}
</style>
