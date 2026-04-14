<template>
  <div class="app-page search-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
        <!-- 搜索栏 -->
        <a-row :gutter="16">
          <a-col :xs="24" :sm="12" :md="8">
            <a-input-search
              v-model:value="searchKeyword"
              placeholder="搜索CI编码、名称或属性值"
              enter-button="搜索"
              size="large"
              @search="handleSearch"
            />
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-select
              v-model:value="searchModelId"
              placeholder="选择模型(可选)"
              allowClear
              style="width: 100%"
              @change="handleSearch"
            >
              <a-select-option v-for="model in modelList" :key="model.id" :value="model.id">
                {{ model.name }}
              </a-select-option>
            </a-select>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-select
              v-model:value="searchDeptId"
              placeholder="选择部门(可选)"
              allowClear
              style="width: 100%"
              @change="handleSearch"
            >
              <a-select-option v-for="dept in deptList" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </a-select-option>
            </a-select>
          </a-col>
          <a-col :xs="24" :sm="12" :md="4">
            <a-space>
              <a-dropdown>
                <a-button :disabled="!searched || searchResults.length === 0">
                  <DownloadOutlined />
                  导出
                  <DownOutlined />
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item key="selected" @click="handleExportSelected" :disabled="selectedRowKeys.length === 0">
                      导出选中 ({{ selectedRowKeys.length }}条)
                    </a-menu-item>
                    <a-menu-item key="all" @click="handleExportAll">
                      导出全部 ({{ totalCount }}条)
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
              <a-button @click="showColumnSettings">
                <SettingOutlined />
                列设置
              </a-button>
            </a-space>
          </a-col>
        </a-row>

        <a-alert
          v-if="searched"
          :message="`找到 ${totalCount} 条结果`"
          type="info"
          show-icon
        />

        <a-table
          :columns="displayColumns"
          :data-source="searchResults"
          :loading="loading"
          :pagination="pagination"
          row-key="id"
          :row-selection="rowSelection"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'index'">
              {{ (pagination.current - 1) * pagination.pageSize + index + 1 }}
            </template>
            <template v-else-if="column.key === 'code'">
              <a @click="handleView(record)" class="ci-link">
                {{ record.code }}
              </a>
            </template>
            <template v-else-if="column.key === 'key_attrs'">
              <span v-if="record.display_subtitles && record.display_subtitles.length">
                {{ record.display_subtitles.join(' | ') }}
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'model'">
              {{ record.model_name }}
            </template>
            <template v-else-if="column.key === 'department'">
              {{ record.department_name }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDateTime(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="handleView(record)">查看</a-button>
                <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              </a-space>
            </template>
            <template v-else-if="column.dataIndex && column.dataIndex.startsWith('attr_')">
              {{ getAttributeValue(record, column.dataIndex.replace('attr_', '')) }}
            </template>
          </template>
        </a-table>
      </a-space>
    </a-card>

    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentInstanceId"
      @edit="handleEditFromDetail"
    />

    <!-- 列设置弹窗 -->
    <a-modal
      v-model:open="columnModalVisible"
      title="列设置"
      @ok="handleColumnOk"
      width="600px"
    >
      <div class="column-settings">
        <div class="column-settings-header">
          <a-checkbox
            :checked="isAllColumnsSelected"
            :indeterminate="isIndeterminate"
            @change="handleSelectAllColumns"
          >
            全选
          </a-checkbox>
          <span class="column-settings-tip">拖拽可调整列顺序</span>
        </div>
        <div class="column-list">
          <div
            v-for="(col, index) in availableColumns"
            :key="col.key"
            class="column-item"
            draggable="true"
            @dragstart="dragStart($event, index)"
            @dragover.prevent
            @drop="drop($event, index)"
          >
            <a-checkbox v-model:checked="col.visible">{{ col.title }}</a-checkbox>
            <DragOutlined class="drag-icon" />
          </div>
        </div>
      </div>
    </a-modal>

    <!-- 导出列选择弹窗 -->
    <a-modal
      v-model:open="exportModalVisible"
      :title="exportType === 'selected' ? '导出选中记录' : '导出全部记录'"
      @ok="handleExportConfirm"
      width="600px"
    >
      <div class="export-settings">
        <div class="export-settings-header">
          <a-checkbox
            :checked="isAllExportColumnsSelected"
            :indeterminate="isExportIndeterminate"
            @change="handleSelectAllExportColumns"
          >
            全选
          </a-checkbox>
          <span class="export-settings-tip">选择要导出的列</span>
        </div>
        <div class="export-column-list">
          <a-checkbox-group v-model:value="selectedExportColumns" style="width: 100%">
            <a-row>
              <a-col :span="12" v-for="col in exportableColumns" :key="col.key">
                <a-checkbox :value="col.key">{{ col.title }}</a-checkbox>
              </a-col>
            </a-row>
          </a-checkbox-group>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownloadOutlined, DownOutlined, SettingOutlined, DragOutlined } from '@ant-design/icons-vue'
import { searchInstances } from '@/api/ci'
import { getModelsTree } from '@/api/cmdb'
import { getDepartments } from '@/api/department'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'
import dayjs from 'dayjs'

const router = useRouter()

const searchKeyword = ref('')
const searchModelId = ref<number | null>(null)
const searchDeptId = ref<number | null>(null)
const searchResults = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)
const totalCount = ref(0)

const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)

const modelList = ref<any[]>([])
const deptList = ref<any[]>([])

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

// 分页配置
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50', '100'],
  showTotal: (total: number) => `共 ${total} 条`
})

// 基础列定义
const baseColumns = [
  { title: '序号', key: 'index', width: 60, visible: true, fixed: 'left' },
  { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true, fixed: 'left' },
  { title: '关键属性', key: 'key_attrs', width: 200, visible: true },
  { title: '模型', dataIndex: 'model_name', key: 'model', width: 120, visible: true },
  { title: '部门', dataIndex: 'department_name', key: 'department', width: 120, visible: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180, visible: true },
  { title: '操作', key: 'action', width: 120, fixed: 'right', visible: true }
]

// 可用列（包含动态属性列）
const availableColumns = ref<any[]>([...baseColumns])

// 显示的列
const displayColumns = computed(() => {
  return availableColumns.value.filter(col => col.visible)
})

// 列设置弹窗
const columnModalVisible = ref(false)
const dragIndex = ref<number | null>(null)

// 导出相关
const exportModalVisible = ref(false)
const exportType = ref<'selected' | 'all'>('all')
const selectedExportColumns = ref<string[]>([])

// 可导出的列
const exportableColumns = computed(() => {
  return availableColumns.value.filter(col => col.key !== 'action' && col.key !== 'index')
})

// 列全选状态
const isAllColumnsSelected = computed(() => {
  const selectableColumns = availableColumns.value.filter(col => col.key !== 'action')
  return selectableColumns.every(col => col.visible)
})

const isIndeterminate = computed(() => {
  const selectableColumns = availableColumns.value.filter(col => col.key !== 'action')
  const visibleCount = selectableColumns.filter(col => col.visible).length
  return visibleCount > 0 && visibleCount < selectableColumns.length
})

// 导出列全选状态
const isAllExportColumnsSelected = computed(() => {
  return selectedExportColumns.value.length === exportableColumns.value.length
})

const isExportIndeterminate = computed(() => {
  return selectedExportColumns.value.length > 0 && selectedExportColumns.value.length < exportableColumns.value.length
})

onMounted(() => {
  fetchModels()
  fetchDepartments()
  // 从本地存储加载列设置
  loadColumnSettings()
})

const fetchModels = async () => {
  try {
    const res = await getModelsTree()
    if (res.code === 200) {
      const models: any[] = []
      const flattenModels = (items: any[]) => {
        items.forEach(item => {
          if (item.is_model) {
            models.push({ id: item.model_id, name: item.title || item.name })
          }
          if (item.children) {
            flattenModels(item.children)
          }
        })
      }
      flattenModels(res.data)
      modelList.value = models
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      const depts: any[] = []
      const flattenDepts = (items: any[]) => {
        items.forEach(item => {
          depts.push({ id: item.id, name: item.name })
          if (item.children) {
            flattenDepts(item.children)
          }
        })
      }
      flattenDepts(res.data)
      deptList.value = depts
    }
  } catch (error) {
    console.error(error)
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    message.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  searched.value = true
  // 清空选中
  selectedRowKeys.value = []
  selectedRows.value = []

  try {
    const res = await searchInstances({
      keyword: searchKeyword.value,
      model_id: searchModelId.value,
      department_id: searchDeptId.value,
      page: pagination.value.current,
      per_page: pagination.value.pageSize
    })

    if (res.code === 200) {
      searchResults.value = res.data.items || []
      totalCount.value = res.data.total || 0
      pagination.value.total = res.data.total || 0
      
      // 收集所有属性列
      collectAttributeColumns(res.data.items || [])
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 收集动态属性列
const collectAttributeColumns = (items: any[]) => {
  const attrKeys = new Set<string>()
  
  items.forEach(item => {
    if (item.attributes) {
      Object.keys(item.attributes).forEach(key => {
        if (item.attributes[key] !== null && item.attributes[key] !== undefined && item.attributes[key] !== '') {
          attrKeys.add(key)
        }
      })
    }
  })
  
  // 添加新的属性列（如果不存在）
  attrKeys.forEach(key => {
    const existingCol = availableColumns.value.find(col => col.dataIndex === `attr_${key}`)
    if (!existingCol) {
      availableColumns.value.splice(availableColumns.value.length - 1, 0, {
        title: key,
        dataIndex: `attr_${key}`,
        key: `attr_${key}`,
        width: 120,
        visible: false
      })
    }
  })
}

// 获取属性值
const getAttributeValue = (record: any, attrKey: string) => {
  if (record.attributes && record.attributes[attrKey] !== undefined) {
    return record.attributes[attrKey]
  }
  return '-'
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  handleSearch()
}

const handleView = (record: any) => {
  currentInstanceId.value = record.id
  detailDrawerVisible.value = true
}

const handleEditFromDetail = (instance: any) => {
  router.push({
    path: '/cmdb/instance',
    query: { modelId: instance.model_id }
  })
}

const handleEdit = (record: any) => {
  router.push({
    path: '/cmdb/instance',
    query: { modelId: record.model_id }
  })
}

const formatDateTime = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

// 列设置
const showColumnSettings = () => {
  columnModalVisible.value = true
}

const handleColumnOk = () => {
  columnModalVisible.value = false
  // 保存到本地存储
  saveColumnSettings()
}

const saveColumnSettings = () => {
  const settings = availableColumns.value.map(col => ({
    key: col.key,
    visible: col.visible
  }))
  localStorage.setItem('search_column_settings', JSON.stringify(settings))
}

const loadColumnSettings = () => {
  try {
    const settings = localStorage.getItem('search_column_settings')
    if (settings) {
      const parsed = JSON.parse(settings)
      parsed.forEach((setting: any) => {
        const col = availableColumns.value.find(c => c.key === setting.key)
        if (col) {
          col.visible = setting.visible
        }
      })
    }
  } catch (e) {
    console.error('加载列设置失败:', e)
  }
}

const handleSelectAllColumns = (e: any) => {
  const checked = e.target.checked
  availableColumns.value.forEach(col => {
    if (col.key !== 'action') {
      col.visible = checked
    }
  })
}

// 拖拽排序
const dragStart = (e: DragEvent, index: number) => {
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }
}

const drop = (e: DragEvent, index: number) => {
  e.preventDefault()
  if (dragIndex.value === null || dragIndex.value === index) return
  
  const item = availableColumns.value[dragIndex.value]
  availableColumns.value.splice(dragIndex.value, 1)
  availableColumns.value.splice(index, 0, item)
  
  dragIndex.value = null
}

// 导出功能
const handleExportSelected = () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要导出的记录')
    return
  }
  exportType.value = 'selected'
  selectedExportColumns.value = exportableColumns.value.filter(col => col.visible).map(col => col.key)
  exportModalVisible.value = true
}

const handleExportAll = () => {
  if (searchResults.value.length === 0) {
    message.warning('暂无数据可导出')
    return
  }
  exportType.value = 'all'
  selectedExportColumns.value = exportableColumns.value.filter(col => col.visible).map(col => col.key)
  exportModalVisible.value = true
}

const handleSelectAllExportColumns = (e: any) => {
  const checked = e.target.checked
  if (checked) {
    selectedExportColumns.value = exportableColumns.value.map(col => col.key)
  } else {
    selectedExportColumns.value = []
  }
}

const handleExportConfirm = () => {
  if (selectedExportColumns.value.length === 0) {
    message.warning('请至少选择一列导出')
    return
  }
  
  const dataToExport = exportType.value === 'selected' ? selectedRows.value : searchResults.value
  const filename = exportType.value === 'selected' ? '搜索结果_选中' : '搜索结果_全部'
  
  exportToCSV(dataToExport, filename)
  exportModalVisible.value = false
}

const exportToCSV = (data: any[], filename: string) => {
  // 准备导出数据
  const exportData = data.map((record: any) => {
    const row: Record<string, string> = {}
    
    selectedExportColumns.value.forEach(colKey => {
      const col = exportableColumns.value.find(c => c.key === colKey)
      if (!col) return
      
      let value = ''
      if (col.key === 'code') {
        value = record.code || '-'
      } else if (col.key === 'key_attrs') {
        value = record.display_subtitles ? record.display_subtitles.join(' | ') : '-'
      } else if (col.key === 'model') {
        value = record.model_name || '-'
      } else if (col.key === 'department') {
        value = record.department_name || '-'
      } else if (col.key === 'created_at') {
        value = formatDateTime(record.created_at)
      } else if (col.dataIndex && col.dataIndex.startsWith('attr_')) {
        const attrKey = col.dataIndex.replace('attr_', '')
        value = getAttributeValue(record, attrKey)
      } else {
        value = record[col.dataIndex] || '-'
      }
      
      row[col.title] = value
    })
    
    return row
  })

  if (exportData.length === 0) {
    message.warning('暂无数据可导出')
    return
  }

  // 创建CSV内容
  const headers = Object.keys(exportData[0])
  const csvContent = [
    headers.join(','),
    ...exportData.map((row: any) =>
      headers.map((header: string) => {
        const value = row[header] || ''
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
</script>

<style scoped>
.search-page {
  padding: 16px;
}

.ci-link {
  color: var(--app-accent);
  cursor: pointer;
}

.column-settings {
  max-height: 400px;
  overflow-y: auto;
}

.column-settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.column-settings-tip {
  color: #999;
  font-size: 12px;
}

.column-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.column-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
  cursor: move;
}

.drag-icon {
  color: #999;
  cursor: move;
}

.export-settings {
  max-height: 400px;
  overflow-y: auto;
}

.export-settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 16px;
}

.export-settings-tip {
  color: #999;
  font-size: 12px;
}

.export-column-list {
  padding: 8px 0;
}
</style>
