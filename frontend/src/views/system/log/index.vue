<template>
  <div class="page-container">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :lg="6">
            <a-form-item label="时间范围">
              <a-range-picker 
                v-model:value="dateRange" 
                style="width: 100%"
                :placeholder="['开始时间', '结束时间']"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="4">
            <a-form-item :label="t('log.username')">
              <a-select
                v-model:value="searchUser"
                :placeholder="t('log.username')"
                style="width: 100%"
                allowClear
                showSearch
                :filter-option="filterOption"
              >
                <a-select-option v-for="user in users" :key="user.id" :value="user.id">
                  {{ user.username }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="4">
            <a-form-item :label="t('log.operationType')">
              <a-select
                v-model:value="searchType"
                :placeholder="t('log.operationType')"
                style="width: 100%"
                allowClear
              >
                <a-select-option value="LOGIN">登录</a-select-option>
                <a-select-option value="LOGOUT">登出</a-select-option>
                <a-select-option value="CREATE">创建</a-select-option>
                <a-select-option value="UPDATE">更新</a-select-option>
                <a-select-option value="DELETE">删除</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :lg="4">
            <a-form-item :label="t('log.status')">
              <a-select
                v-model:value="searchStatus"
                :placeholder="t('log.status')"
                style="width: 100%"
                allowClear
              >
                <a-select-option value="success">成功</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :lg="6">
            <a-form-item class="search-buttons">
              <a-space wrap>
                <a-button type="primary" @click="handleSearch">
                  <template #icon><SearchOutlined /></template>
                  {{ t('common.search') }}
                </a-button>
                <a-button @click="handleReset">
                  <template #icon><ReloadOutlined /></template>
                  {{ t('common.reset') }}
                </a-button>
                <a-button @click="handleExport">
                  <template #icon><ExportOutlined /></template>
                  导出
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="table-card">
      <template #title>
        <div class="table-title">
          <span class="title-text">{{ t('log.title') }}</span>
        </div>
      </template>
      <a-table
        :columns="columns"
        :data-source="logs"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
        row-key="id"
        :scroll="{ x: 1200 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            <a-space>
              <a-avatar :style="{ backgroundColor: '#1890ff' }" :size="28">
                {{ record.username?.charAt(0)?.toUpperCase() }}
              </a-avatar>
              <span>{{ record.username }}</span>
            </a-space>
          </template>
          <template v-else-if="column.key === 'operation_type'">
            <a-tag :color="getTypeColor(record.operation_type)">
              {{ getTypeText(record.operation_type) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge 
              :status="record.status === 'success' ? 'success' : 'error'" 
              :text="record.status === 'success' ? '成功' : '失败'" 
            />
          </template>
          <template v-else-if="column.key === 'operation_desc'">
            <a-tooltip :title="record.operation_desc" v-if="record.operation_desc && record.operation_desc.length > 30">
              <span>{{ record.operation_desc?.substring(0, 30) + '...' }}</span>
            </a-tooltip>
            <span v-else>{{ record.operation_desc || '-' }}</span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            <span class="time-text">{{ formatDate(record.created_at) }}</span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { SearchOutlined, ExportOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getLogs, exportLogs } from '@/api/log'
import { getUsers } from '@/api/user'
import dayjs from 'dayjs'

const { t } = useI18n()

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: t('log.username'), key: 'username', width: 150 },
  { title: t('log.operationType'), key: 'operation_type', width: 100 },
  { title: t('log.operationObject'), dataIndex: 'operation_object', key: 'operation_object', width: 100 },
  { title: t('log.operationDesc'), key: 'operation_desc', width: 200 },
  { title: t('log.ipAddress'), dataIndex: 'ip_address', key: 'ip_address', width: 140 },
  { title: t('log.status'), key: 'status', width: 80 },
  { title: t('log.createdAt'), key: 'created_at', width: 180 }
]

const loading = ref(false)
const logs = ref([])
const users = ref<any[]>([])
const dateRange = ref<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
const searchUser = ref<number | undefined>()
const searchType = ref('')
const searchStatus = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  pageSizeOptions: ['10', '20', '50', '100'],
  showTotal: (total: number) => `共 ${total} 条记录`
})

const fetchUsers = async () => {
  try {
    const res = await getUsers({ per_page: 1000 })
    if (res.code === 200) {
      users.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      per_page: pagination.pageSize
    }
    if (dateRange.value) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD')
      params.date_to = dateRange.value[1].format('YYYY-MM-DD')
    }
    if (searchUser.value) {
      params.user_id = searchUser.value
    }
    if (searchType.value) {
      params.operation_type = searchType.value
    }
    if (searchStatus.value) {
      params.status = searchStatus.value
    }
    
    const res = await getLogs(params)
    if (res.code === 200) {
      logs.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchLogs()
}

const handleReset = () => {
  dateRange.value = null
  searchUser.value = undefined
  searchType.value = ''
  searchStatus.value = ''
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchLogs()
}

const handleExport = async () => {
  try {
    const params: any = {}
    if (dateRange.value) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD')
      params.date_to = dateRange.value[1].format('YYYY-MM-DD')
    }
    if (searchUser.value) {
      params.user_id = searchUser.value
    }
    if (searchType.value) {
      params.operation_type = searchType.value
    }
    if (searchStatus.value) {
      params.status = searchStatus.value
    }
    
    const res = await exportLogs(params)
    if (res.code === 200) {
      const blob = new Blob([res.data.csv], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `logs_${Date.now()}.csv`
      link.click()
    }
  } catch (error) {
    console.error(error)
  }
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
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const filterOption = (input: string, option: any) => {
  return option.children?.[0]?.children?.toLowerCase().includes(input.toLowerCase())
}

onMounted(() => {
  fetchUsers()
  fetchLogs()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card {
  border-radius: 8px;
}

.search-card :deep(.ant-card-body) {
  padding: 16px 24px;
}

.search-form :deep(.ant-form-item) {
  margin-bottom: 0;
  width: 100%;
}

.search-form :deep(.ant-form-item-label) {
  padding-bottom: 0;
}

.search-buttons {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 576px) {
  .search-buttons {
    justify-content: flex-start;
  }
}

.table-card {
  border-radius: 8px;
}

.table-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
  padding: 0 24px;
}

.table-card :deep(.ant-card-body) {
  padding: 24px;
}

.table-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.title-text {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.time-text {
  color: #666;
  font-size: 13px;
}

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  font-weight: 500;
}

:deep(.ant-table-tbody > tr:hover > td) {
  background: #e6f7ff;
}

:deep(.ant-table-wrapper) {
  overflow-x: auto;
}
</style>
