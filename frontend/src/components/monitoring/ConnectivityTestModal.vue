<template>
  <a-modal
    :open="open"
    title="连通测试结果"
    width="960px"
    :footer="null"
    @cancel="emit('update:open', false)"
  >
    <a-spin :spinning="loading">
      <a-empty v-if="!result && !loading" description="暂无测试结果" />
      <a-space v-else direction="vertical" style="width: 100%" :size="16">
        <a-alert
          :type="result?.success ? 'success' : 'warning'"
          show-icon
          :message="result?.success ? '连通测试通过' : '连通测试存在异常'"
          :description="result?.summary || 'collector 已返回测试结果'"
        />

        <a-descriptions bordered size="small" :column="{ xs: 1, sm: 1, md: 2 }">
          <a-descriptions-item label="监控任务">{{ result?.monitor_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="目标地址">{{ result?.target || '-' }}</a-descriptions-item>
          <a-descriptions-item label="采集器">{{ result?.collector_id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="采集器地址">{{ result?.collector_addr || '-' }}</a-descriptions-item>
          <a-descriptions-item label="模板类型">{{ result?.app || '-' }}</a-descriptions-item>
          <a-descriptions-item label="执行窗口">{{ formatStartedAt(result?.started_at) }} - {{ formatFinishedAt(result?.finished_at) }}</a-descriptions-item>
        </a-descriptions>

        <a-row :gutter="[12, 12]">
          <a-col :xs="12" :sm="8" :md="6">
            <a-statistic title="指标组总数" :value="result?.metrics_total || 0" />
          </a-col>
          <a-col :xs="12" :sm="8" :md="6">
            <a-statistic title="已返回" :value="result?.metrics_finished || 0" />
          </a-col>
          <a-col :xs="12" :sm="8" :md="6">
            <a-statistic title="通过" :value="successCount" :value-style="{ color: '#389e0d' }" />
          </a-col>
          <a-col :xs="12" :sm="8" :md="6">
            <a-statistic title="异常" :value="failedCount" :value-style="{ color: '#cf1322' }" />
          </a-col>
        </a-row>

        <a-table
          size="small"
          :pagination="false"
          :data-source="tableItems"
          :row-key="(record: MonitoringConnectivityTestItem, index: number) => `${record.metrics}-${index}`"
          :scroll="{ x: 860 }"
        >
          <a-table-column title="指标组" data-index="metrics" key="metrics" width="160" />
          <a-table-column title="协议" data-index="protocol" key="protocol" width="100" />
          <a-table-column title="结果" key="success" width="100">
            <template #default="{ record }">
              <a-tag :color="record.success ? 'green' : 'red'">
                {{ record.success ? '通过' : '失败' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="延迟" key="raw_latency_ms" width="110">
            <template #default="{ record }">
              {{ formatLatency(record.raw_latency_ms) }}
            </template>
          </a-table-column>
          <a-table-column title="字段数" key="field_count" width="100">
            <template #default="{ record }">
              {{ record.field_count ?? 0 }}
            </template>
          </a-table-column>
          <a-table-column title="异常/说明" key="message" ellipsis>
            <template #default="{ record }">
              <span>{{ record.message || (record.success ? '连接正常' : '-') }}</span>
            </template>
          </a-table-column>
          <a-table-column title="调试信息" key="debug" width="120">
            <template #default="{ record }">
              <a-popover placement="leftTop" trigger="click">
                <template #content>
                  <pre class="debug-block">{{ formatDebug(record) }}</pre>
                </template>
                <a-button type="link" size="small">查看</a-button>
              </a-popover>
            </template>
          </a-table-column>
        </a-table>
      </a-space>
    </a-spin>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type {
  MonitoringConnectivityTestItem,
  MonitoringConnectivityTestResult
} from '@/api/monitoring'

const props = defineProps<{
  open: boolean
  loading?: boolean
  result?: MonitoringConnectivityTestResult | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const tableItems = computed(() => props.result?.items || [])
const successCount = computed(() => tableItems.value.filter((item) => item.success).length)
const failedCount = computed(() => tableItems.value.filter((item) => !item.success).length)

const formatLatency = (value?: number) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-'
  }
  return `${value} ms`
}

const formatStartedAt = (value?: string) => value || '-'
const formatFinishedAt = (value?: string) => value || '-'

const formatDebug = (record: MonitoringConnectivityTestItem) => {
  const payload = {
    message: record.message || '',
    debug: record.debug || {},
    fields: record.fields || {}
  }
  return JSON.stringify(payload, null, 2)
}
</script>

<style scoped>
.debug-block {
  margin: 0;
  max-width: 420px;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
}
</style>
