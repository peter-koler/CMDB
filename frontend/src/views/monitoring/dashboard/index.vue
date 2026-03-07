<template>
  <div class="monitoring-dashboard-page">
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="overview-card">
          <a-statistic title="监控总数" :value="overview.total_monitors" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="overview-card">
          <a-statistic title="正常数" :value="overview.healthy_monitors" :value-style="{ color: '#52c41a' }" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="overview-card">
          <a-statistic title="异常数" :value="overview.unhealthy_monitors" :value-style="{ color: '#faad14' }" />
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :lg="6">
        <a-card :bordered="false" class="overview-card">
          <a-statistic title="当前告警数" :value="overview.open_alerts" :value-style="{ color: '#f5222d' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :lg="16">
        <a-card :bordered="false" title="告警趋势（近24小时）" class="content-card">
          <div class="bars">
            <div v-for="(point, index) in alertTrend" :key="`alert-${index}`" class="bar-item">
              <div class="bar-value">{{ point.value }}</div>
              <div class="bar-wrap">
                <div class="bar bar-danger" :style="{ height: `${barHeight(point.value, maxAlertTrend)}%` }" />
              </div>
              <div class="bar-label">{{ point.time }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" title="监控状态分布" class="content-card">
          <div v-for="item in statusDistribution" :key="item.name" class="status-item">
            <div class="status-row">
              <span>{{ item.name }}</span>
              <span>{{ item.value }}</span>
            </div>
            <a-progress
              :percent="statusPercent(item.value)"
              :show-info="false"
              :stroke-color="item.name === '正常' ? '#52c41a' : '#faad14'"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :lg="12">
        <a-card :bordered="false" title="采集成功率趋势" class="content-card">
          <div class="bars">
            <div v-for="(point, index) in successRateTrend" :key="`success-${index}`" class="bar-item">
              <div class="bar-value">{{ point.value.toFixed(1) }}%</div>
              <div class="bar-wrap">
                <div class="bar bar-success" :style="{ height: `${barHeight(point.value, 100)}%` }" />
              </div>
              <div class="bar-label">{{ point.time }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="12">
        <a-card :bordered="false" title="Top10 告警监控" class="content-card">
          <a-table
            :columns="topColumns"
            :data-source="topAlertMonitors"
            :loading="loading"
            :pagination="false"
            size="small"
            row-key="name"
          />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :span="24">
        <a-card :bordered="false" class="content-card">
          <template #title>
            最近5条告警
          </template>
          <template #extra>
            <a-space>
              <a-button type="link" @click="goToAlertCenter">查看告警中心</a-button>
              <a-button type="link" @click="goToTemplate">查看监控模板</a-button>
            </a-space>
          </template>
          <a-table
            :columns="recentColumns"
            :data-source="recentAlerts"
            :loading="loading"
            :pagination="false"
            size="small"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'level'">
                <a-tag :color="levelColor(record.level)">{{ record.level || '-' }}</a-tag>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  getMonitoringDashboard,
  type AlertItem,
  type MonitoringDashboardData,
  type MonitoringDashboardPoint
} from '@/api/monitoring'

const router = useRouter()
const loading = ref(false)

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
const recentAlerts = ref<AlertItem[]>([])

const topColumns = [
  { title: '监控对象', dataIndex: 'name', key: 'name' },
  { title: '告警次数', dataIndex: 'value', key: 'value', width: 120 }
]

const recentColumns = [
  { title: '级别', dataIndex: 'level', key: 'level', width: 100 },
  { title: '告警名称', dataIndex: 'name', key: 'name' },
  { title: '监控对象', dataIndex: 'monitor_name', key: 'monitor_name' },
  { title: '指标值', dataIndex: 'metric_value', key: 'metric_value', width: 120 },
  { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 180 }
]

const maxAlertTrend = computed(() => Math.max(...alertTrend.value.map((item) => item.value), 1))
const totalStatus = computed(() => statusDistribution.value.reduce((sum, item) => sum + item.value, 0))

const barHeight = (value: number, max: number) => {
  if (max <= 0) return 4
  return Math.max(4, Math.round((value / max) * 100))
}

const statusPercent = (value: number) => {
  if (totalStatus.value <= 0) return 0
  return Number(((value / totalStatus.value) * 100).toFixed(2))
}

const levelColor = (level: string) => {
  if (level === 'critical') return 'red'
  if (level === 'warning') return 'orange'
  return 'blue'
}

const fillPoints = (items: MonitoringDashboardPoint[]) => {
  if (Array.isArray(items) && items.length > 0) return items
  return Array.from({ length: 24 }).map((_, idx) => ({
    time: `${String(idx).padStart(2, '0')}:00`,
    value: 0
  }))
}

const loadDashboard = async () => {
  loading.value = true
  try {
    const res = await getMonitoringDashboard()
    const data = (res?.data || {}) as Partial<MonitoringDashboardData>
    Object.assign(overview, data.overview || {})
    statusDistribution.value = Array.isArray(data.status_distribution) ? data.status_distribution : []
    alertTrend.value = fillPoints(data.alert_trend || [])
    successRateTrend.value = fillPoints(data.success_rate_trend || [])
    topAlertMonitors.value = Array.isArray(data.top_alert_monitors) ? data.top_alert_monitors : []
    recentAlerts.value = Array.isArray(data.recent_alerts) ? data.recent_alerts : []
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载监控大盘失败')
  } finally {
    loading.value = false
  }
}

const goToAlertCenter = () => {
  router.push('/monitoring/alert')
}

const goToTemplate = () => {
  router.push('/monitoring/template')
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.monitoring-dashboard-page {
  min-height: 100%;
}

.overview-card,
.content-card {
  border-radius: 8px;
}

.bars {
  display: flex;
  gap: 6px;
  height: 190px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.bar-item {
  min-width: 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.bar-value {
  font-size: 11px;
  color: #8c8c8c;
  line-height: 1;
  margin-bottom: 4px;
}

.bar-wrap {
  width: 18px;
  height: 130px;
  border-radius: 9px;
  background: #f0f2f5;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}

.bar {
  width: 100%;
  border-radius: 9px;
  transition: height 0.25s ease;
}

.bar-danger {
  background: linear-gradient(180deg, #ff7875 0%, #f5222d 100%);
}

.bar-success {
  background: linear-gradient(180deg, #95de64 0%, #52c41a 100%);
}

.bar-label {
  margin-top: 4px;
  font-size: 10px;
  color: #bfbfbf;
}

.status-item + .status-item {
  margin-top: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
</style>
