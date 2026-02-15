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
              placeholder="搜索CI编码"
              style="width: 200px"
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
            <template v-if="currentModelId && modelFields.length > 0">
              <a-select
                v-model:value="attrFilterField"
                placeholder="选择属性筛选"
                style="width: 150px"
                allowClear
                @change="handleAttrFieldChange"
              >
                <a-select-option v-for="field in modelFields" :key="field.code" :value="field.code">
                  {{ field.name }}
                </a-select-option>
              </a-select>
              <a-input
                v-if="attrFilterField"
                v-model:value="attrFilterValue"
                placeholder="输入属性值"
                style="width: 150px"
                @pressEnter="handleSearch"
              />
            </template>
            <a-range-picker v-model:value="dateRange" @change="handleSearch" />
            <a-button type="primary" @click="handleSearch">
              <SearchOutlined />
              搜索
            </a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
          <a-space wrap style="margin-left: auto">
            <a-button type="primary" @click="handleAdd" v-if="currentModelId">
              <PlusOutlined />
              新增CI
            </a-button>
            <a-button @click="handleExport" v-if="currentModelId && instances.length > 0">
              <ExportOutlined />
              导出
            </a-button>
            <a-button @click="handleImport" v-if="currentModelId">
              <ImportOutlined />
              导入
            </a-button>
            <a-button @click="showColumnSetting" v-if="currentModelId && modelFields.length > 0">
              <SettingOutlined />
              列设置
            </a-button>
          </a-space>
        </a-card>

        <!-- 表格视图 -->
        <a-card :bordered="false" class="table-card">
          <a-table
            :columns="displayColumns"
            :data-source="instances"
            :loading="loading"
            :pagination="pagination"
            :row-selection="currentModelId ? { selectedRowKeys: selectedRowKeys, onChange: onSelectChange } : undefined"
            @change="handleTableChange"
            row-key="id"
            :scroll="{ x: 'max-content' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'code'">
                <a @click="handleView(record)" style="color: #1890ff; cursor: pointer;">{{ record.code }}</a>
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
      </a-col>
    </a-row>

    <!-- CI编辑弹窗 -->
    <CiInstanceModal
      v-model:visible="editModalVisible"
      :model-id="currentModelId"
      :instance="currentInstance"
      @success="handleSuccess"
    />

    <!-- CI详情抽屉 -->
    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentInstanceId"
      @edit="handleEditFromDetail"
      @deleted="handleSuccess"
    />

    <!-- 列设置弹窗 -->
    <a-modal
      v-model:open="columnModalVisible"
      title="列设置 - 选择要显示的属性"
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
        description="请上传CSV格式文件，第一行为表头，包含所有必填属性字段。系统将自动验证数据并导入。"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />
      <a-upload-dragger
        v-model:fileList="importFileList"
        :before-upload="beforeUpload"
        accept=".csv"
        :max-count="1"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p class="ant-upload-hint">支持 .csv 格式文件</p>
      </a-upload-dragger>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
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
import { getModelsTree, getModelDetail } from '@/api/cmdb'
import { getDepartments } from '@/api/department'
import CiInstanceModal from './components/CiInstanceModal.vue'
import CiDetailDrawer from './components/CiDetailDrawer.vue'
import dayjs from 'dayjs'
const route = useRoute()

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
const modelFields = ref<any[]>([])
const attrFilterField = ref<string | null>(null)
const attrFilterValue = ref<string>('')

const selectedRowKeys = ref<string[]>([])

const baseColumns = [
  { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true },
  { title: '操作', key: 'action', width: 180, fixed: 'right', visible: true }
]

const availableColumns = ref<any[]>([...baseColumns])
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
const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)
const columnModalVisible = ref(false)

let dragItem: any = null

onMounted(() => {
  fetchModels()
  fetchDepartments()
})

watch(
  () => route.query,
  () => {
    if (modelTree.value.length > 0) {
      applyRouteSelection()
    }
  }
)

const findModelNodeByModelId = (nodes: any[], modelId: number): any | null => {
  for (const node of nodes) {
    if (node.is_model && Number(node.model_id) === Number(modelId)) {
      return node
    }
    if (node.children?.length) {
      const found = findModelNodeByModelId(node.children, modelId)
      if (found) return found
    }
  }
  return null
}

const applyRouteSelection = async () => {
  const routeModelId = Number(route.query.modelId)
  const routeCiId = Number(route.query.ciId)

  if (routeModelId) {
    const targetNode = findModelNodeByModelId(modelTree.value, routeModelId)
    if (targetNode) {
      selectedModelKeys.value = [targetNode.id]
      currentModelId.value = targetNode.model_id
      currentModelName.value = targetNode.title
      await fetchModelFields(targetNode.model_id)
      pagination.current = 1
      await fetchInstances()
    }
  }

  if (routeCiId) {
    currentInstanceId.value = routeCiId
    detailDrawerVisible.value = true
  }
}

const fetchModels = async () => {
  try {
    const res = await getModelsTree()
    if (res.code === 200) {
      modelTree.value = res.data
      filteredModelTree.value = res.data

      // 路由带模型/CI时按路由优先
      const routeModelId = Number(route.query.modelId)
      const routeCiId = Number(route.query.ciId)
      if ((routeModelId || routeCiId) && modelTree.value.length > 0) {
        await applyRouteSelection()
        return
      }

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
    
    if (attrFilterField.value && attrFilterValue.value) {
      params.attr_field = attrFilterField.value
      params.attr_value = attrFilterValue.value
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

const onModelSelect = async (keys: any, info: any) => {
  selectedModelKeys.value = keys
  const node = info.node
  
  if (node.is_model) {
    currentModelId.value = node.model_id
    currentModelName.value = node.title
    await fetchModelFields(node.model_id)
  } else if (node.is_all) {
    currentModelId.value = null
    currentModelName.value = '全部'
    modelFields.value = []
    resetColumns()
  } else if (node.is_category) {
    currentModelId.value = null
    currentModelName.value = node.name
    modelFields.value = []
    resetColumns()
  }
  
  pagination.current = 1
  fetchInstances()
}

const fetchModelFields = async (modelId: number) => {
  try {
    const res = await getModelDetail(modelId)
    if (res.code === 200 && res.data.form_config) {
      let formConfig = res.data.form_config
      if (typeof formConfig === 'string') {
        formConfig = JSON.parse(formConfig)
      }
      const fields: any[] = []
      if (Array.isArray(formConfig)) {
        formConfig.forEach((item: any) => {
          if (item.controlType === 'group' && item.children) {
            item.children.forEach((child: any) => {
              if (child.props && child.props.code) {
                fields.push({
                  code: child.props.code,
                  name: child.props.label || child.props.code,
                  ...child.props
                })
              }
            })
          } else if (item.props && item.props.code) {
            fields.push({
              code: item.props.code,
              name: item.props.label || item.props.code,
              ...item.props
            })
          }
        })
      }
      modelFields.value = fields
      updateColumns()
    } else {
      modelFields.value = []
    }
  } catch (error) {
    console.error(error)
    modelFields.value = []
  }
}

const updateColumns = () => {
  const newColumns: any[] = [
    { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true }
  ]
  
  modelFields.value.forEach((field: any) => {
    newColumns.push({
      title: field.name,
      key: `attr_${field.code}`,
      width: 150,
      visible: true,
      customRender: ({ record }: any) => {
        const attrs = record.attributes || record.attribute_values || {}
        const val = attrs[field.code]
        if (val === null || val === undefined) return '-'
        if (typeof val === 'object') return JSON.stringify(val)
        return val
      }
    })
  })
  
  newColumns.push({ title: '操作', key: 'action', width: 180, fixed: 'right', visible: true })
  
  availableColumns.value = newColumns
}

const resetColumns = () => {
  availableColumns.value = [
    { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true },
    { title: '操作', key: 'action', width: 180, fixed: 'right', visible: true }
  ]
}

const handleSearch = () => {
  pagination.current = 1
  fetchInstances()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchDept.value = null
  attrFilterField.value = null
  attrFilterValue.value = ''
  dateRange.value = null
  handleSearch()
}

const handleAttrFieldChange = () => {
  attrFilterValue.value = ''
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
  currentInstanceId.value = record.id
  detailDrawerVisible.value = true
}

const handleEditFromDetail = (instance: any) => {
  currentInstance.value = instance
  currentInstanceId.value = instance.id
  detailDrawerVisible.value = false
  editModalVisible.value = true
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
const importFileList = ref<any[]>([])

const beforeUpload = (file: File) => {
  importFileList.value = [file]
  return false
}

const handleImport = () => {
  importFileList.value = []
  importModalVisible.value = true
}

const handleImportOk = async () => {
  if (importFileList.value.length === 0) {
    message.warning('请选择要导入的文件')
    return
  }
  
  try {
    importing.value = true
    const res = await importInstances(importFileList.value[0], currentModelId.value!)
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
