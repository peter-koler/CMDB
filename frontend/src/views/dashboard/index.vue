<template>
  <div class="dashboard-container">
    <a-row :gutter="[16, 16]">
      <a-col :xs="24" :sm="12" :md="12" :lg="6">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon user-icon">
              <UserOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-title">用户总数</div>
              <div class="stat-value">{{ stats.userCount }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="12" :lg="6">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon login-icon">
              <LoginOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-title">今日登录</div>
              <div class="stat-value">{{ stats.todayLogins }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="12" :lg="6">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon operation-icon">
              <HistoryOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-title">操作日志</div>
              <div class="stat-value">{{ stats.operationCount }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12" :md="12" :lg="6">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon active-icon">
              <CheckCircleOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-title">活跃用户</div>
              <div class="stat-value">{{ stats.activeUsers }}</div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[16, 16]" style="margin-top: 16px">
      <a-col :xs="24" :lg="16">
        <a-card :bordered="false" class="content-card">
          <template #title>
            <div class="card-title">
              <HistoryOutlined class="title-icon" />
              <span>最近操作日志</span>
            </div>
          </template>
          <template #extra>
            <a-button type="link" @click="goToLog">查看全部</a-button>
          </template>
          <a-table
            :columns="logColumns"
            :data-source="recentLogs"
            :loading="logLoading"
            :pagination="false"
            size="small"
            row-key="id"
            :scroll="{ x: 600 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'operation_type'">
                <a-tag :color="getTypeColor(record.operation_type)" size="small">
                  {{ getTypeText(record.operation_type) }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-badge 
                  :status="record.status === 'success' ? 'success' : 'error'" 
                  :text="record.status === 'success' ? '成功' : '失败'" 
                />
              </template>
              <template v-else-if="column.key === 'created_at'">
                <span class="time-text">{{ formatDate(record.created_at) }}</span>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" class="content-card">
          <template #title>
            <div class="card-title">
              <ClockCircleOutlined class="title-icon" />
              <span>系统信息</span>
            </div>
          </template>
          <a-descriptions :column="1" class="system-info">
            <a-descriptions-item label="系统名称">IT运维平台</a-descriptions-item>
            <a-descriptions-item label="版本号">v1.0.0</a-descriptions-item>
            <a-descriptions-item label="当前用户">{{ userInfo?.username }}</a-descriptions-item>
            <a-descriptions-item label="用户角色">{{ userInfo?.role === 'admin' ? '管理员' : '普通用户' }}</a-descriptions-item>
            <a-descriptions-item label="服务器时间">{{ serverTime }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-card :bordered="false" class="content-card quick-card">
          <template #title>
            <div class="card-title">
              <ThunderboltOutlined class="title-icon" />
              <span>快捷操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <a-row :gutter="8">
              <a-col :span="24">
                <a-button type="primary" block @click="goToUser" v-permission="'user:create'">
                  <template #icon><UserAddOutlined /></template>
                  新增用户
                </a-button>
              </a-col>
            </a-row>
            <a-row :gutter="8" style="margin-top: 8px">
              <a-col :span="12">
                <a-button block @click="goToConfig" v-permission="'config:view'">
                  <template #icon><SettingOutlined /></template>
                  系统配置
                </a-button>
              </a-col>
              <a-col :span="12">
                <a-button block @click="goToLog" v-permission="'log:view'">
                  <template #icon><FileSearchOutlined /></template>
                  查看日志
                </a-button>
              </a-col>
            </a-row>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  UserOutlined,
  LoginOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  UserAddOutlined,
  SettingOutlined,
  FileSearchOutlined
} from '@ant-design/icons-vue'
import { getUsers } from '@/api/user'
import { getLogs } from '@/api/log'

const router = useRouter()
const userStore = useUserStore()

const userInfo = computed(() => userStore.userInfo)

const stats = reactive({
  userCount: 0,
  todayLogins: 0,
  operationCount: 0,
  activeUsers: 0
})

const logLoading = ref(false)
const recentLogs = ref([])
const serverTime = ref('')

const logColumns = [
  { title: '用户', dataIndex: 'username', key: 'username', width: 100 },
  { title: '操作', key: 'operation_type', width: 80 },
  { title: '描述', dataIndex: 'operation_desc', key: 'operation_desc', ellipsis: true },
  { title: '状态', key: 'status', width: 80 },
  { title: '时间', key: 'created_at', width: 160 }
]

let timer: number | null = null

const fetchStats = async () => {
  try {
    const userRes = await getUsers({ per_page: 1 })
    if (userRes.code === 200) {
      stats.userCount = userRes.data.total
    }
    
    const today = new Date().toISOString().split('T')[0]
    const loginRes = await getLogs({ 
      operation_type: 'LOGIN', 
      status: 'success',
      date_from: today,
      date_to: today,
      per_page: 1 
    })
    if (loginRes.code === 200) {
      stats.todayLogins = loginRes.data.total
    }
    
    const logRes = await getLogs({ per_page: 1 })
    if (logRes.code === 200) {
      stats.operationCount = logRes.data.total
    }
    
    const activeRes = await getUsers({ status: 'active', per_page: 1 })
    if (activeRes.code === 200) {
      stats.activeUsers = activeRes.data.total
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchRecentLogs = async () => {
  logLoading.value = true
  try {
    const res = await getLogs({ per_page: 5 })
    if (res.code === 200) {
      recentLogs.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  } finally {
    logLoading.value = false
  }
}

const updateServerTime = () => {
  serverTime.value = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    LOGIN: 'blue',
    LOGOUT: 'default',
    CREATE: 'green',
    UPDATE: 'orange',
    DELETE: 'red'
  }
  return colors[type] || 'default'
}

const getTypeText = (type: string) => {
  const texts: Record<string, string> = {
    LOGIN: '登录',
    LOGOUT: '登出',
    CREATE: '创建',
    UPDATE: '更新',
    DELETE: '删除'
  }
  return texts[type] || type
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const goToUser = () => router.push('/system/user')
const goToConfig = () => router.push('/system/config')
const goToLog = () => router.push('/system/log')

onMounted(() => {
  fetchStats()
  fetchRecentLogs()
  updateServerTime()
  timer = window.setInterval(updateServerTime, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 0;
}

.stat-card {
  border-radius: 8px;
  overflow: hidden;
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
  margin-right: 16px;
  flex-shrink: 0;
}

.user-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.operation-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.active-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #333;
}

.content-card {
  border-radius: 8px;
  height: 100%;
}

.content-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
  padding: 0 24px;
  min-height: 48px;
}

.content-card :deep(.ant-card-body) {
  padding: 16px 24px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
}

.title-icon {
  color: #1890ff;
}

.time-text {
  color: #666;
  font-size: 12px;
}

.system-info :deep(.ant-descriptions-item-label) {
  color: #666;
}

.system-info :deep(.ant-descriptions-item-content) {
  color: #333;
}

.quick-card {
  margin-top: 16px;
}

.quick-actions {
  padding: 8px 0;
}

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  font-weight: 500;
  padding: 12px 8px;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 12px 8px;
}

@media (max-width: 992px) {
  .quick-card {
    margin-top: 16px;
  }
}
</style>
