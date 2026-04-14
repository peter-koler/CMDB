<template>
  <div class="app-page history-page">
    <a-card :bordered="false" class="app-surface-card">
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
            <a-dropdown style="margin-left: 8px">
              <a-button>
                导出Excel
                <DownOutlined />
              </a-button>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="selected" @click="handleExportSelected" :disabled="selectedRowKeys.length === 0">
                    导出选中 ({{ selectedRowKeys.length }}条)
                  </a-menu-item>
                  <a-menu-item key="all" @click="handleExportAll">
                    导出全部 ({{ pagination.total }}条)
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-col>
        </a-row>

        <a-table
          :columns="columns"
          :data-source="historyList"
          :loading="loading"
          :pagination="pagination"
          row-key="id"
          :row-selection="rowSelection"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'ci'">
              <a @click="viewCi(record)" class="ci-link">
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
                <div v-if="record.attribute_name" class="history-attr-name">
                  {{ record.attribute_name }}
                </div>
                <span v-if="record.old_value" class="history-old-value">
                  {{ truncate(record.old_value, 30) }}
                </span>
                <span v-if="record.old_value && record.new_value"> → </span>
                <span v-if="record.new_value" class="history-new-value">
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
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
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

// 选中行
const selectedRowKeys = ref<number[]>([])
const selectedRows = ref<any[]>([])

// 行选择配置
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: number[], rows: any[]) => {
    selectedRowKeys.value = keys
    selectedRows.value = rows
  }
}))

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['20', '30', '50'],
  showTotal: (total: number) => `共 ${total} 条`
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

// 导出数据到CSV
const exportToCSV = (data: any[], filename: string) => {
  if (data.length === 0) {
    message.warning('暂无数据可导出')
    return
  }

  // 准备导出数据
  const exportData = data.map((record: any) => ({
    'CI名称': record.ci?.name || record.ci_id || '-',
    '操作类型': getOperationText(record.operation),
    '变更属性': record.attribute_name || '-',
    '变更前': record.old_value || '-',
    '变更后': record.new_value || '-',
    '操作人': record.operator_name || '-',
    'IP地址': record.ip_address || '-',
    '操作时间': formatDateTime(record.created_at)
  }))

  // 创建CSV内容
  const headers = Object.keys(exportData[0])
  const csvContent = [
    headers.join(','),
    ...exportData.map((row: any) =>
      headers.map((header: string) => {
        const value = row[header as keyof typeof row] || ''
        // 处理包含逗号或换行符的值
        if (typeof value === 'string' && (value.includes(',') || value.includes('\n') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`
        }
        return value
      }).join(',')
    )
  ].join('\n')

  // 添加BOM以支持中文
  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })

  // 下载文件
  const link = document.createElement('a')
  const timestamp = dayjs().format('YYYYMMDD_HHmmss')
  link.href = URL.createObjectURL(blob)
  link.download = `${filename}_${timestamp}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)

  message.success('导出成功')
}

// 导出选中的数据
const handleExportSelected = () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要导出的记录')
    return
  }
  exportToCSV(selectedRows.value, '变更历史_选中')
}

// 导出全部数据
const handleExportAll = () => {
  exportToCSV(historyList.value, '变更历史_全部')
}
</script>

<style scoped>
.history-page {
  padding: 16px;
}

.ci-link {
  color: var(--app-accent);
  cursor: pointer;
}

.history-attr-name {
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--app-text-primary);
}

.history-old-value {
  color: var(--arco-danger);
  text-decoration: line-through;
}

.history-new-value {
  color: var(--arco-success);
}
</style>
