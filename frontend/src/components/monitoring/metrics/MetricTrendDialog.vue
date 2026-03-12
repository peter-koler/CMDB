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
        <a-select v-model:value="chartType" style="width: 140px">
          <a-select-option value="line">折线图</a-select-option>
          <a-select-option value="bar">柱状图</a-select-option>
          <a-select-option value="table">表格</a-select-option>
        </a-select>
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
        <a-empty v-if="!points.length" description="当前时间范围暂无数据" />

        <template v-else>
          <div v-if="chartType === 'line'" class="chart-wrap">
            <svg viewBox="0 0 640 260" preserveAspectRatio="none" class="metric-svg">
              <rect x="0" y="0" width="640" height="260" fill="#fafafa" />
              <line x1="24" y1="20" x2="24" y2="232" stroke="#d9d9d9" stroke-width="1" />
              <line x1="24" y1="232" x2="620" y2="232" stroke="#d9d9d9" stroke-width="1" />
              <polyline :points="linePoints" fill="none" stroke="#1677ff" stroke-width="2" stroke-linecap="round" />
            </svg>
          </div>

          <div v-else-if="chartType === 'bar'" class="chart-wrap">
            <svg viewBox="0 0 640 260" preserveAspectRatio="none" class="metric-svg">
              <rect x="0" y="0" width="640" height="260" fill="#fafafa" />
              <line x1="24" y1="20" x2="24" y2="232" stroke="#d9d9d9" stroke-width="1" />
              <line x1="24" y1="232" x2="620" y2="232" stroke="#d9d9d9" stroke-width="1" />
              <rect
                v-for="(bar, idx) in bars"
                :key="idx"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="bar.height"
                fill="#69b1ff"
              />
            </svg>
          </div>

          <a-table
            v-else
            :pagination="{ pageSize: 20, showSizeChanger: true, showQuickJumper: true }"
            :data-source="tableRows"
            :row-key="(row: any) => row.timestamp"
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
import { computed, ref, watch } from 'vue'
import dayjs, { type Dayjs } from 'dayjs'
import { message } from 'ant-design-vue'
import {
  buildBarRects,
  buildLinePolyline,
  fetchTrendSeries,
  formatMetricValue,
  resolveQueryStep,
  type BarRect
} from '@/composables/useMonitorMetrics'
import { exportTargetMetric } from '@/api/monitoring'

const props = defineProps<{
  open: boolean
  monitorId: number
  intervalSeconds: number
  metricName: string
  metricTitle: string
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

const rangeOptions = [
  { label: '最近1小时', value: '1h' },
  { label: '最近1天', value: '1d' },
  { label: '最近1周', value: '1w' },
  { label: '最近1月', value: '1m' },
  { label: '自定义', value: 'custom' }
]

const linePoints = computed(() => buildLinePolyline(points.value, 640, 260))
const bars = computed<BarRect[]>(() => buildBarRects(points.value, 640, 260, 90))

const tableRows = computed(() => {
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

async function load() {
  if (!props.monitorId || !props.metricName) {
    points.value = []
    return
  }
  loading.value = true
  try {
    const range = resolveRange()
    points.value = await fetchTrendSeries(
      props.monitorId,
      props.metricName,
      range.from,
      range.to,
      props.intervalSeconds
    )
  } catch {
    points.value = []
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
  () => [props.open, props.metricName],
  ([open, metricName]) => {
    if (!open || !metricName) return
    load()
  },
  { immediate: true }
)
</script>

<style scoped>
.chart-wrap {
  width: 100%;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}

.metric-svg {
  width: 100%;
  height: 280px;
}
</style>
