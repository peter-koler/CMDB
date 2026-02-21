<template>
  <div class="batch-scan-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :md="6">
            <a-form-item label="模型">
              <a-select
                v-model:value="searchModelId"
                placeholder="请选择模型"
                allowClear
                style="width: 100%"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-form-item label="状态">
              <a-select v-model:value="searchStatus" placeholder="请选择状态" allowClear style="width: 100%">
                <a-select-option value="pending">等待中</a-select-option>
                <a-select-option value="running">运行中</a-select-option>
                <a-select-option value="completed">已完成</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-form-item label="触发方式">
              <a-select v-model:value="searchTriggerSource" placeholder="请选择触发方式" allowClear style="width: 100%">
                <a-select-option value="manual">手动触发</a-select-option>
                <a-select-option value="scheduled">定时任务</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="24" :md="6">
            <a-form-item class="search-buttons">
              <a-space wrap>
                <a-button type="primary" @click="handleSearch">
                  <template #icon><SearchOutlined /></template>
                  搜索
                </a-button>
                <a-button @click="handleReset">
                  <template #icon><ReloadOutlined /></template>
                  重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="table-card">
      <a-table
        :columns="columns"
        :data-source="tasks"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'trigger_source'">
            <a-tag :color="record.trigger_source === 'manual' ? 'blue' : 'purple'">
              {{ record.trigger_source === 'manual' ? '手动' : '定时' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'duration'">
            <span v-if="record.completed_at && record.started_at">
              {{ calculateDuration(record.started_at, record.completed_at) }}
            </span>
            <span v-else-if="record.status === 'running'">运行中...</span>
            <span v-else>-</span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="showDetail(record)">
                详情
              </a-button>
              <a-button
                type="link"
                size="small"
                :disabled="record.status === 'running'"
                @click="handleRerun(record)"
              >
                重新执行
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="detailVisible"
      title="批量扫描任务详情"
      width="700px"
      :footer="null"
    >
      <a-descriptions :column="2" bordered v-if="currentTask">
        <a-descriptions-item label="任务ID">{{ currentTask.id }}</a-descriptions-item>
        <a-descriptions-item label="模型">{{ currentTask.model_name }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="getStatusColor(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="触发方式">
          {{ currentTask.trigger_source === 'manual' ? '手动触发' : '定时任务' }}
        </a-descriptions-item>
        <a-descriptions-item label="总数">{{ currentTask.total_count || 0 }}</a-descriptions-item>
        <a-descriptions-item label="已处理">{{ currentTask.processed_count || 0 }}</a-descriptions-item>
        <a-descriptions-item label="创建关系">{{ currentTask.created_count || 0 }}</a-descriptions-item>
        <a-descriptions-item label="跳过">{{ currentTask.skipped_count || 0 }}</a-descriptions-item>
        <a-descriptions-item label="失败">{{ currentTask.failed_count || 0 }}</a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ currentTask.started_at || '-' }}</a-descriptions-item>
        <a-descriptions-item label="完成时间">{{ currentTask.completed_at || '-' }}</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ currentTask.created_at }}</a-descriptions-item>
        <a-descriptions-item label="错误信息" :span="2">
          <a-alert v-if="currentTask.error_message" type="error" :message="currentTask.error_message" />
          <span v-else>-</span>
        </a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getAllBatchScanTasks, triggerBatchScan } from '@/api/trigger'
import { getModels } from '@/api/cmdb'

const loading = ref(false)
const detailVisible = ref(false)
const currentTask = ref<any>(null)

const searchModelId = ref<number | null>(null)
const searchStatus = ref<string | null>(null)
const searchTriggerSource = ref<string | null>(null)

const tasks = ref<any[]>([])
const models = ref<any[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: '任务ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '模型', dataIndex: 'model_name', key: 'model_name', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '触发方式', dataIndex: 'trigger_source', key: 'trigger_source', width: 100 },
  { title: '总数', dataIndex: 'total_count', key: 'total_count', width: 80 },
  { title: '已处理', dataIndex: 'processed_count', key: 'processed_count', width: 80 },
  { title: '创建', dataIndex: 'created_count', key: 'created_count', width: 60 },
  { title: '跳过', dataIndex: 'skipped_count', key: 'skipped_count', width: 60 },
  { title: '失败', dataIndex: 'failed_count', key: 'failed_count', width: 60 },
  { title: '耗时', key: 'duration', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' as const }
]

const getStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    completed: 'success',
    failed: 'error'
  }
  return colorMap[status] || 'default'
}

const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

const calculateDuration = (startedAt: string, completedAt: string) => {
  const start = new Date(startedAt).getTime()
  const end = new Date(completedAt).getTime()
  const seconds = Math.round((end - start) / 1000)
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}小时${Math.floor((seconds % 3600) / 60)}分`
}

const formatDateTime = (dateStr: string | null) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch {
    return dateStr
  }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await getAllBatchScanTasks({
      page: pagination.current,
      page_size: pagination.pageSize,
      model_id: searchModelId.value,
      status: searchStatus.value,
      trigger_source: searchTriggerSource.value
    })
    if (res.code === 200) {
      tasks.value = res.data
      pagination.total = res.data.total || res.data.length
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      models.value = res.data.items || res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const showDetail = (record: any) => {
  currentTask.value = record
  detailVisible.value = true
}

const handleRerun = async (record: any) => {
  try {
    const res = await triggerBatchScan(record.model_id)
    if (res.code === 202 || res.code === 200) {
      message.success('已重新触发批量扫描')
      fetchTasks()
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '操作失败')
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchTasks()
}

const handleReset = () => {
  searchModelId.value = null
  searchStatus.value = null
  searchTriggerSource.value = null
  pagination.current = 1
  fetchTasks()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchTasks()
}

onMounted(() => {
  fetchTasks()
  fetchModels()
})
</script>

<style scoped>
.batch-scan-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.search-form {
  width: 100%;
}

.table-card {
  margin-bottom: 16px;
}
</style>
