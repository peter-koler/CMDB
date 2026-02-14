<template>
  <div class="ci-page">
    <a-row :gutter="16" class="full-height">
      <!-- 左侧模型树 -->
      <a-col :xs="24" :sm="8" :md="6" :lg="5" class="tree-col">
        <a-card :bordered="false" class="tree-card" title="模型目录">
          <a-input-search
            v-model:value="treeSearchKeyword"
            placeholder="搜索模型"
            style="width: 100%; margin-bottom: 12px"
            allowClear
            @change="handleTreeSearch"
          />
          <a-tree
            :tree-data="filteredModelTree"
            :selected-keys="selectedModelKeys"
            @select="onModelSelect"
            :field-names="{ title: 'name', key: 'id', children: 'children' }"
            :default-expand-all="true"
          >
            <template #title="{ name, title, is_model, is_all, is_category, ci_count }">
              <span v-if="is_model || is_all" class="model-node">
                <span class="model-name">{{ title || name }}</span>
                <span class="model-count">({{ ci_count || 0 }})</span>
              </span>
              <span v-else-if="is_category" class="category-node">
                <FolderOutlined />
                <span class="category-name">{{ name }}</span>
              </span>
              <span v-else>{{ name }}</span>
            </template>
          </a-tree>
        </a-card>
      </a-col>

      <!-- 右侧CI列表 -->
      <a-col :xs="24" :sm="16" :md="18" :lg="19" class="content-col">
        <a-card :bordered="false" class="search-card" :title="currentModelName ? currentModelName + ' - CI列表' : 'CI列表'">
          <a-space wrap>
            <a-input-search
              v-model:value="searchKeyword"
              placeholder="搜索CI编码或名称"
              style="width: 250px"
              @search="handleSearch"
            />
            <a-select
              v-model:value="searchDept"
              placeholder="选择部门"
              style="width: 150px"
              allowClear
            >
              <a-select-option v-for="dept in departmentOptions" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </a-select-option>
            </a-select>
            <a-range-picker v-model:value="dateRange" @change="handleSearch" />
            <a-button type="primary" @click="handleSearch">
              <SearchOutlined />
              搜索
            </a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
          <a-space wrap style="margin-left: auto">
            <a-button type="primary" @click="handleAdd" :disabled="!currentModelId">
              <PlusOutlined />
              新增CI
            </a-button>
            <a-button @click="handleExport" :disabled="!currentModelId || instances.length === 0">
              <ExportOutlined />
              导出
            </a-button>
            <a-button @click="handleImport" :disabled="!currentModelId">
              <ImportOutlined />
              导入
            </a-button>
            <a-button @click="showColumnSetting">
              <SettingOutlined />
              列设置
            </a-button>
            <a-button-group>
              <a-button :type="viewMode === 'table' ? 'primary' : 'default'" @click="viewMode = 'table'">
                <TableOutlined />
              </a-button>
              <a-button :type="viewMode === 'card' ? 'primary' : 'default'" @click="viewMode = 'card'">
                <AppstoreOutlined />
              </a-button>
            </a-button-group>
          </a-space>
        </a-card>

        <!-- 表格视图 -->
        <a-card v-if="viewMode === 'table'" :bordered="false" class="table-card">
          <a-table
            :columns="displayColumns"
            :data-source="instances"
            :loading="loading"
            :pagination="pagination"
            :row-selection="{ selectedRowKeys: selectedRowKeys, onChange: onSelectChange }"
            @change="handleTableChange"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <a-link @click="handleView(record)">{{ record.name }}</a-link>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="handleView(record)">查看</a-button>
                  <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
                  <a-button type="link" size="small" @click="handleCopy(record)">复制</a-button>
                  <a-popconfirm title="确定删除吗？" @confirm="handleDelete(record)">
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
          
          <!-- 批量操作栏 -->
          <div v-if="selectedRowKeys.length > 0" class="batch-bar">
            <span>已选择 {{ selectedRowKeys.length }} 项</span>
            <a-space>
              <a-button size="small" @click="handleBatchEdit">批量编辑</a-button>
              <a-button size="small" danger @click="handleBatchDelete">批量删除</a-button>
              <a-button size="small" @click="selectedRowKeys = []">取消选择</a-button>
            </a-space>
          </div>
        </a-card>

        <!-- 卡片视图 -->
        <a-card v-else :bordered="false" class="card-view">
          <a-row :gutter="[16, 16]">
            <a-col v-for="item in instances" :key="item.id" :xs="24" :sm="12" :md="8" :lg="6">
              <a-card hoverable class="ci-card" @click="handleView(item)">
                <div class="ci-card-header">
                  <a-avatar :size="48" style="background-color: #1890ff">
                    {{ item.name?.charAt(0)?.toUpperCase() }}
                  </a-avatar>
                  <div class="ci-card-info">
                    <div class="ci-name">{{ item.name }}</div>
                    <div class="ci-code">{{ item.code }}</div>
                  </div>
                </div>
                <div class="ci-card-body">
                  <p><span class="label">部门：</span>{{ item.department_name || '-' }}</p>
                  <p><span class="label">创建人：</span>{{ item.creator_name || '-' }}</p>
                  <p><span class="label">创建时间：</span>{{ formatDate(item.created_at) }}</p>
                </div>
                <template #actions>
                  <a-button type="link" size="small" @click.stop="handleEdit(item)">编辑</a-button>
                  <a-button type="link" size="small" @click.stop="handleCopy(item)">复制</a-button>
                  <a-popconfirm title="确定删除吗？" @confirm.stop="handleDelete(item)">
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </template>
              </a-card>
            </a-col>
          </a-row>
          <a-pagination
            v-model:current="pagination.current"
            v-model:pageSize="pagination.pageSize"
            :total="pagination.total"
            show-size-changer
            style="margin-top: 16px; text-align: right"
            @change="handleTableChange"
          />
        </a-card>
      </a-col>
    </a-row>

    <!-- CI编辑弹窗 -->
    <CiInstanceModal
      v-model:visible="editModalVisible"
      :model-id="currentModelId"
      :instance="currentInstance"
      @success="handleSuccess"
    />

    <!-- 列设置弹窗 -->
    <a-modal
      v-model:open="columnModalVisible"
      title="列设置"
      @ok="handleColumnOk"
      width="500px"
    >
      <div class="column-list">
        <div
          v-for="col in availableColumns"
          :key="col.key"
          class="column-item"
          draggable="true"
          @dragstart="dragStart($event, col)"
          @dragover.prevent
          @drop="drop($event, col)"
        >
          <a-checkbox v-model:checked="col.visible">{{ col.title }}</a-checkbox>
          <DragOutlined class="drag-icon" />
        </div>
      </div>
    </a-modal>

    <!-- 导入弹窗 -->
    <a-modal
      v-model:open="importModalVisible"
      title="批量导入CI"
      @ok="handleImportOk"
      :confirm-loading="importing"
      width="500px"
    >
      <a-alert
        message="导入说明"
        description="请先导出数据了解CSV格式，然后按相同格式编辑后导入。CSV文件第一行为表头，包括：CI编码、CI名称、部门、创建人、创建时间，以及模型的所有字段名称。"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />
      <a-upload-dragger
        :before-upload="(file: File) => {
          importFile = file
          return false
        }"
        :file-list="importFile ? [{ name: importFile.name, uid: '-1', status: 'done' }] : []"
        accept=".csv,.xlsx,.xls"
        :remove="() => { importFile = null }"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此处上传</p>
        <p class="ant-upload-hint">支持 CSV、Excel 文件</p>
      </a-upload-dragger>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  SearchOutlined,
  PlusOutlined,
  SettingOutlined,
  TableOutlined,
  AppstoreOutlined,
  DragOutlined,
  FolderOutlined,
  ExportOutlined,
  ImportOutlined,
  InboxOutlined
} from '@ant-design/icons-vue'
import { getInstances, deleteInstance, batchDeleteInstances, generateCICode, exportInstances, importInstances } from '@/api/ci'
import { getModelsTree } from '@/api/cmdb'
import { getDepartments } from '@/api/department'
import CiInstanceModal from './components/CiInstanceModal.vue'
import dayjs from 'dayjs'

// 模型树（带分类和CI数量）
const modelTree = ref<any[]>([])
const filteredModelTree = ref<any[]>([])
const selectedModelKeys = ref<string[]>([])
const currentModelId = ref<number | null>(null)
const currentModelName = ref<string>('')
const treeSearchKeyword = ref('')

const instances = ref<any[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const searchDept = ref<number | null>(null)
const dateRange = ref<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
const departmentOptions = ref<any[]>([])

const viewMode = ref<'table' | 'card'>('table')
const selectedRowKeys = ref<string[]>([])

const columns = [
  { title: '编码', dataIndex: 'code', key: 'code', width: 160 },
  { title: '名称', key: 'name', width: 150 },
  { title: '部门', dataIndex: 'department_name', key: 'department_name', width: 120 },
  { title: '创建人', dataIndex: 'creator_name', key: 'creator_name', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' }
]

const availableColumns = ref(columns.map(col => ({ ...col, visible: true })))
const displayColumns = computed(() => availableColumns.value.filter(col => col.visible))

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const editModalVisible = ref(false)
const currentInstance = ref<any>(null)
const columnModalVisible = ref(false)

let dragItem: any = null

onMounted(() => {
  fetchModels()
  fetchDepartments()
  // 从localStorage读取视图偏好
  const savedViewMode = localStorage.getItem('ci_view_mode')
  if (savedViewMode) {
    viewMode.value = savedViewMode as 'table' | 'card'
  }
})

watch(viewMode, (val) => {
  localStorage.setItem('ci_view_mode', val)
})

const fetchModels = async () => {
  try {
    const res = await getModelsTree()
    if (res.code === 200) {
      modelTree.value = res.data
      filteredModelTree.value = res.data
      
      // 默认选中"全部"或第一个模型
      if (modelTree.value.length > 0) {
        const firstNode = modelTree.value[0]
        selectedModelKeys.value = [firstNode.id]
        
        // 如果是模型节点，直接加载
        if (firstNode.is_model) {
          currentModelId.value = firstNode.model_id
          currentModelName.value = firstNode.title
          fetchInstances()
        } else if (firstNode.is_all) {
          // "全部"节点，加载所有CI
          currentModelId.value = null
          currentModelName.value = '全部'
          fetchInstances()
        }
      }
    }
  } catch (error) {
    console.error(error)
  }
}

// 树形搜索
const handleTreeSearch = () => {
  if (!treeSearchKeyword.value) {
    filteredModelTree.value = modelTree.value
    return
  }
  
  const keyword = treeSearchKeyword.value.toLowerCase()
  
  const filterTree = (nodes: any[]): any[] => {
    return nodes.map(node => {
      const newNode = { ...node }
      
      // 检查当前节点是否匹配
      const isMatch = node.name?.toLowerCase().includes(keyword) || 
                     node.title?.toLowerCase().includes(keyword)
      
      // 如果有子节点，递归过滤
      if (node.children && node.children.length > 0) {
        newNode.children = filterTree(node.children)
      }
      
      // 如果当前节点匹配，或者有匹配的子节点，保留该节点
      if (isMatch || (newNode.children && newNode.children.length > 0)) {
        return newNode
      }
      
      return null
    }).filter(Boolean)
  }
  
  filteredModelTree.value = filterTree(modelTree.value)
}

const fetchDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      departmentOptions.value = flattenDepartments(res.data)
    }
  } catch (error) {
    console.error(error)
  }
}

const flattenDepartments = (tree: any[], result: any[] = []) => {
  for (const item of tree) {
    result.push({ id: item.id, name: item.name })
    if (item.children) {
      flattenDepartments(item.children, result)
    }
  }
  return result
}

const fetchInstances = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      per_page: pagination.pageSize,
      keyword: searchKeyword.value
    }
    
    // 如果选中了特定模型，添加model_id筛选
    if (currentModelId.value) {
      params.model_id = currentModelId.value
    }
    
    if (searchDept.value) {
      params.department_id = searchDept.value
    }
    if (dateRange.value) {
      params.date_from = dateRange.value[0].format('YYYY-MM-DD')
      params.date_to = dateRange.value[1].format('YYYY-MM-DD')
    }
    
    const res = await getInstances(params)
    if (res.code === 200) {
      instances.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onModelSelect = (keys: any, info: any) => {
  selectedModelKeys.value = keys
  const node = info.node
  
  if (node.is_model) {
    // 点击了模型节点
    currentModelId.value = node.model_id
    currentModelName.value = node.title
  } else if (node.is_all) {
    // 点击了"全部"节点
    currentModelId.value = null
    currentModelName.value = '全部'
  } else if (node.is_category) {
    // 点击了分类节点，显示该分类下所有模型的CI
    currentModelId.value = null
    currentModelName.value = node.name
    // 可以在这里添加按分类筛选的逻辑
  }
  
  pagination.current = 1
  fetchInstances()
}

const handleSearch = () => {
  pagination.current = 1
  fetchInstances()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchDept.value = null
  dateRange.value = null
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchInstances()
}

const onSelectChange = (keys: string[]) => {
  selectedRowKeys.value = keys
}

const handleAdd = async () => {
  currentInstance.value = null
  editModalVisible.value = true
}

const handleView = (record: any) => {
  // 查看详情，可以跳转到详情页或打开抽屉
  message.info('查看功能开发中')
}

const handleEdit = (record: any) => {
  currentInstance.value = record
  editModalVisible.value = true
}

const handleCopy = async (record: any) => {
  try {
    // 生成新编码
    const res = await generateCICode()
    if (res.code === 200) {
      const newCode = res.data.code
      currentInstance.value = {
        ...record,
        id: null,
        code: newCode,
        name: record.name + '_复制'
      }
      editModalVisible.value = true
    }
  } catch (error) {
    message.error('复制失败')
  }
}

const handleDelete = async (record: any) => {
  try {
    await deleteInstance(record.id)
    message.success('删除成功')
    fetchInstances()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const handleBatchEdit = () => {
  message.info('批量编辑功能开发中')
}

const handleBatchDelete = async () => {
  try {
    await batchDeleteInstances({ ids: selectedRowKeys.value.map(Number) })
    message.success(`成功删除 ${selectedRowKeys.value.length} 个CI`)
    selectedRowKeys.value = []
    fetchInstances()
  } catch (error: any) {
    message.error(error.response?.data?.message || '批量删除失败')
  }
}

const handleSuccess = () => {
  fetchInstances()
}

const showColumnSetting = () => {
  columnModalVisible.value = true
}

const handleExport = async () => {
  try {
    const res = await exportInstances({
      model_id: currentModelId.value,
      keyword: searchKeyword.value,
      ids: selectedRowKeys.value.length > 0 ? selectedRowKeys.value : []
    })
    
    if (res.data) {
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `${currentModelName.value}_CI_${new Date().getTime()}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      message.success('导出成功')
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '导出失败')
  }
}

const importModalVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)

const handleImport = () => {
  importFile.value = null
  importModalVisible.value = true
}

const handleImportOk = async () => {
  if (!importFile.value) {
    message.warning('请选择要导入的文件')
    return
  }
  
  try {
    importing.value = true
    const res = await importInstances(importFile.value, currentModelId.value!)
    message.success(res.message || '导入成功')
    importModalVisible.value = false
    fetchInstances()
  } catch (error: any) {
    message.error(error.response?.data?.message || '导入失败')
  } finally {
    importing.value = false
  }
}

const handleColumnOk = () => {
  columnModalVisible.value = false
}

const dragStart = (e: DragEvent, col: any) => {
  dragItem = col
}

const drop = (e: DragEvent, col: any) => {
  if (!dragItem || dragItem === col) return
  
  const fromIndex = availableColumns.value.indexOf(dragItem)
  const toIndex = availableColumns.value.indexOf(col)
  
  availableColumns.value.splice(fromIndex, 1)
  availableColumns.value.splice(toIndex, 0, dragItem)
  
  dragItem = null
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}
</script>

<style scoped>
.ci-page {
  height: 100%;
}

.full-height {
  height: 100%;
}

.tree-col {
  height: 100%;
}

.content-col {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tree-card {
  height: 100%;
}

.tree-card :deep(.ant-card-body) {
  height: calc(100% - 56px);
  overflow: auto;
}

.search-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.search-card :deep(.ant-card-body) {
  padding: 16px 24px;
}

.table-card {
  flex: 1;
}

.table-card :deep(.ant-card-body) {
  padding: 24px;
}

.card-view {
  flex: 1;
}

.card-view :deep(.ant-card-body) {
  padding: 24px;
}

.ci-card {
  cursor: pointer;
}

.ci-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.ci-card-info {
  flex: 1;
}

.ci-name {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}

.ci-code {
  font-size: 12px;
  color: #999;
}

.ci-card-body {
  font-size: 13px;
  color: #666;
}

.ci-card-body p {
  margin: 4px 0;
}

.label {
  color: #999;
}

.batch-bar {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f0f2f5;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.column-list {
  max-height: 400px;
  overflow-y: auto;
}

.column-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  border-bottom: 1px solid #f0f0f0;
  cursor: move;
}

.drag-icon {
  color: #999;
  cursor: move;
}

.model-node {
  display: flex;
  align-items: center;
  gap: 4px;
}

.model-name {
  font-weight: 500;
}

.model-count {
  color: #999;
  font-size: 12px;
}

.category-node {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
}

.category-name {
  font-weight: 500;
}

:deep(.ant-tree-treenode) {
  padding: 4px 0;
}

:deep(.ant-tree-node-content-wrapper) {
  padding: 2px 4px;
}
</style>
