<template>
  <div class="history-page">
    <a-card :bordered="false">
      <a-space direction="vertical" style="width: 100%" :size="16">
        <a-row :gutter="16">
          <a-col :xs="24" :sm="12" :md="6">
            <a-input-search
              v-model:value="searchCiId"
              placeholder="输入CI ID"
              allowClear
              @search="handleSearch"
            />
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-select
              v-model:value="filterOperation"
              placeholder="操作类型"
              allowClear
              style="width: 100%"
              @change="handleSearch"
            >
              <a-select-option value="CREATE">创建</a-select-option>
              <a-select-option value="UPDATE">更新</a-select-option>
              <a-select-option value="DELETE">删除</a-select-option>
            </a-select>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-range-picker
              v-model:value="dateRange"
              style="width: 100%"
              @change="handleSearch"
            />
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-button type="primary" @click="handleSearch">查询</a-button>
            <a-button style="margin-left: 8px" @click="handleReset">重置</a-button>
          </a-col>
        </a-row>

        <a-table
          :columns="columns"
          :data-source="historyList"
          :loading="loading"
          :pagination="pagination"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'ci'">
              <a @click="viewCi(record)" style="color: #1890ff; cursor: pointer;">
                {{ record.ci?.name || record.ci_id }}
              </a>
            </template>
            <template v-else-if="column.key === 'operation'">
              <a-tag :color="getHistoryColor(record.operation)">
                {{ getOperationText(record.operation) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'change'">
              <div v-if="record.old_value || record.new_value">
                <div v-if="record.attribute_name" style="font-weight: 500; margin-bottom: 4px;">
                  {{ record.attribute_name }}
                </div>
                <span v-if="record.old_value" style="color: #cf132d; text-decoration: line-through;">
                  {{ truncate(record.old_value, 30) }}
                </span>
                <span v-if="record.old_value && record.new_value"> → </span>
                <span v-if="record.new_value" style="color: #3f8600;">
                  {{ truncate(record.new_value, 30) }}
                </span>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDateTime(record.created_at) }}
            </template>
          </template>
        </a-table>
      </a-space>
    </a-card>

    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentCiId"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAllCiHistory } from '@/api/ci'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'
import dayjs from 'dayjs'

const searchCiId = ref<string>('')
const filterOperation = ref<string | undefined>(undefined)
const dateRange = ref<any[]>([])

const historyList = ref<any[]>([])
const loading = ref(false)

const detailDrawerVisible = ref(false)
const currentCiId = ref<number | null>(null)

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: 'CI名称', key: 'ci', width: 150 },
  { title: '操作类型', dataIndex: 'operation', key: 'operation', width: 100 },
  { title: '变更内容', key: 'change' },
  { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 100 },
  { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address', width: 120 },
  { title: '操作时间', dataIndex: 'created_at', key: 'created_at', width: 160 }
]

onMounted(() => {
  fetchHistory()
})

const fetchHistory = async () => {
  loading.value = true
  
  try {
    const params: any = {
      page: pagination.value.current,
      per_page: pagination.value.pageSize
    }
    
    if (searchCiId.value) {
      params.ci_id = parseInt(searchCiId.value)
    }
    
    if (filterOperation.value) {
      params.operation = filterOperation.value
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD')
      params.date_to = dateRange.value[1].format('YYYY-MM-DD')
    }
    
    const res = await getAllCiHistory(params)
    if (res.code === 200) {
      historyList.value = res.data.items || []
      pagination.value.total = res.data.total || 0
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.value.current = 1
  fetchHistory()
}

const handleReset = () => {
  searchCiId.value = ''
  filterOperation.value = undefined
  dateRange.value = []
  pagination.value.current = 1
  fetchHistory()
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchHistory()
}

const viewCi = (record: any) => {
  currentCiId.value = record.ci_id
  detailDrawerVisible.value = true
}

const formatDateTime = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const getHistoryColor = (operation: string) => {
  const colorMap: Record<string, string> = {
    'CREATE': 'green',
    'UPDATE': 'blue',
    'DELETE': 'red'
  }
  return colorMap[operation] || 'gray'
}

const getOperationText = (operation: string) => {
  const textMap: Record<string, string> = {
    'CREATE': '创建',
    'UPDATE': '更新',
    'DELETE': '删除'
  }
  return textMap[operation] || operation
}

const truncate = (str: string, maxLen: number) => {
  if (!str) return ''
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
}
</script>

<style scoped>
.history-page {
  padding: 16px;
}
</style>
