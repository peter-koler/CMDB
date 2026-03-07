<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-row :gutter="[16, 16]">
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card size="small"><a-statistic title="监控总数" :value="overview.total_monitors" /></a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card size="small"><a-statistic title="正常" :value="overview.healthy_monitors" :value-style="{ color: '#52c41a' }" /></a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card size="small"><a-statistic title="异常" :value="overview.unhealthy_monitors" :value-style="{ color: '#faad14' }" /></a-card>
        </a-col>
        <a-col :xs="24" :sm="12" :lg="6">
          <a-card size="small"><a-statistic title="当前告警" :value="overview.open_alerts" :value-style="{ color: '#f5222d' }" /></a-card>
        </a-col>
      </a-row>

      <a-space>
        <a-button type="primary" :loading="loading" @click="load">刷新</a-button>
        <a-button @click="exportCsv">导出CSV</a-button>
        <a-button @click="printView">导出PDF</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="topAlertMonitors" row-key="name" :pagination="false" />
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { getMonitoringDashboard } from '@/api/monitoring'

const loading = ref(false)
const topAlertMonitors = ref<Array<{ name: string; value: number }>>([])
const overview = reactive({
  total_monitors: 0,
  healthy_monitors: 0,
  unhealthy_monitors: 0,
  open_alerts: 0
})

const columns = [
  { title: 'Top 告警对象', dataIndex: 'name', key: 'name' },
  { title: '告警次数', dataIndex: 'value', key: 'value', width: 120 }
]

const load = async () => {
  loading.value = true
  try {
    const res = await getMonitoringDashboard()
    const data = res?.data || {}
    Object.assign(overview, data.overview || {})
    topAlertMonitors.value = Array.isArray(data.top_alert_monitors) ? data.top_alert_monitors : []
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载简报失败')
  } finally {
    loading.value = false
  }
}

const exportCsv = () => {
  const lines = ['name,value', ...topAlertMonitors.value.map((item) => `${item.name},${item.value}`)]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `monitoring-bulletin-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const printView = () => {
  window.print()
}

onMounted(() => {
  load()
})
</script>
