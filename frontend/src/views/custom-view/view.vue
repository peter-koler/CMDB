<template>
  <div class="custom-view-page">
    <a-row :gutter="16" class="full-height">
      <a-col :xs="24" :sm="8" :md="6" :lg="5" class="tree-col">
        <a-card :bordered="false" class="tree-card" :title="viewInfo.name">
          <a-input-search
            v-model:value="treeSearchKeyword"
            placeholder="搜索节点"
            style="width: 100%; margin-bottom: 12px"
            allowClear
            @change="handleTreeSearch"
          />
          <a-tree
            v-if="filteredTreeData.length > 0"
            :tree-data="filteredTreeData"
            :selected-keys="selectedNodeKeys"
            :expanded-keys="expandedKeys"
            :auto-expand-parent="autoExpandParent"
            @select="onNodeSelect"
            @expand="onExpand"
            :field-names="{ title: 'title', key: 'key', children: 'children' }"
          >
            <template #title="{ title, data }">
              <span class="node-title">
                <span>{{ title }}</span>
                <a-tag v-if="data.filter_config && data.filter_config.model_id" size="small" color="blue">
                  {{ getModelName(data.filter_config.model_id) }}
                </a-tag>
              </span>
            </template>
          </a-tree>
          <a-empty v-else description="暂无节点" />
        </a-card>
      </a-col>

      <a-col :xs="24" :sm="16" :md="18" :lg="19" class="content-col">
        <a-card :bordered="false" class="search-card" :title="currentNodeName ? currentNodeName + ' - CI列表' : '请选择节点'">
          <div class="ci-toolbar" v-if="currentNodeId">
            <div class="ci-toolbar-filters">
              <a-input-search
                v-model:value="searchKeyword"
                placeholder="搜索CI编码或名称"
                class="toolbar-control toolbar-control-keyword"
                @search="handleSearch"
              />
              <template v-if="currentModelId && currentModelFields.length > 0">
                <a-select
                  v-model:value="attrFilterField"
                  placeholder="选择属性筛选"
                  class="toolbar-control"
                  allowClear
                  @change="handleAttrFieldChange"
                >
                  <a-select-option v-for="field in currentModelFields" :key="field.code" :value="field.code">
                    {{ field.name }}
                  </a-select-option>
                </a-select>
                <a-input
                  v-if="attrFilterField"
                  v-model:value="attrFilterValue"
                  placeholder="输入属性值"
                  class="toolbar-control"
                  @pressEnter="handleSearch"
                />
              </template>
            </div>
            <div class="ci-toolbar-actions">
              <a-space wrap>
                <a-button type="primary" @click="handleSearch">
                  <SearchOutlined />
                  搜索
                </a-button>
                <a-button @click="handleReset">
                  <ReloadOutlined />
                  重置
                </a-button>
                <a-button type="primary" @click="handleAdd" v-if="currentModelId">
                  <PlusOutlined />
                  新增CI
                </a-button>
                <a-button @click="handleExport" v-if="instances.length > 0">
                  <ExportOutlined />
                  导出
                </a-button>
                <a-button @click="handleImport" v-if="currentModelId">
                  <ImportOutlined />
                  导入
                </a-button>
                <a-button @click="showColumnSetting" v-if="currentModelId && currentModelFields.length > 0">
                  <SettingOutlined />
                  列设置
                </a-button>
              </a-space>
            </div>
          </div>
        </a-card>

        <a-card :bordered="false" class="table-card" v-if="currentNodeId">
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
              <template v-else>
                {{ getAttributeValue(record, column.dataIndex) }}
              </template>
            </template>
          </a-table>

          <div v-if="selectedRowKeys.length > 0" class="batch-bar">
            <span>已选择 {{ selectedRowKeys.length }} 项</span>
            <a-space>
              <a-button size="small" @click="handleBatchEdit">批量编辑</a-button>
              <a-button size="small" danger @click="handleBatchDelete">批量删除</a-button>
              <a-button size="small" @click="handleExportSelected">导出选中</a-button>
              <a-button size="small" @click="selectedRowKeys = []">取消选择</a-button>
            </a-space>
          </div>
        </a-card>

        <a-card :bordered="false" v-if="!currentNodeId">
          <a-empty description="请在左侧选择一个节点查看CI列表" />
        </a-card>
      </a-col>
    </a-row>

    <!-- CI 编辑弹窗 -->
    <CiInstanceModal
      v-model:visible="editModalVisible"
      :model-id="currentModelId"
      :instance="currentInstance"
      @success="handleSuccess"
    />

    <!-- CI 详情抽屉 -->
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
        description="请先下载当前模型导入模板（Excel可直接打开CSV），按模板填写后上传。系统将自动校验CI名称与模型必填属性。"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />
      <div class="import-template-action">
        <a-button :loading="templateLoading" @click="handleDownloadTemplate">
          下载当前模型导入模板
        </a-button>
      </div>
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
  DragOutlined,
  ExportOutlined,
  ImportOutlined,
  InboxOutlined,
  ReloadOutlined
} from '@ant-design/icons-vue'
import { getCustomView, getViewNodesTree, getNodeCis } from '@/api/custom-view'
import { getModels, getModelDetail } from '@/api/cmdb'
import { getInstances, deleteInstance, batchDeleteInstances, exportInstances, importInstances, getImportTemplate } from '@/api/ci'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'
import CiInstanceModal from '@/views/cmdb/instance/components/CiInstanceModal.vue'

const route = useRoute()

const viewId = computed(() => Number(route.params.id))

const viewInfo = ref<any>({})
const treeData = ref<any[]>([])
const filteredTreeData = ref<any[]>([])
const treeSearchKeyword = ref('')
const expandedKeys = ref<number[]>([])
const autoExpandParent = ref(true)
const selectedNodeKeys = ref<number[]>([])
const currentNodeId = ref<number | null>(null)
const currentNodeName = ref('')

const searchKeyword = ref('')
const attrFilterField = ref<string | null>(null)
const attrFilterValue = ref('')
const loading = ref(false)
const instances = ref<any[]>([])
const selectedRowKeys = ref<number[]>([])

const cmdbModels = ref<any[]>([])
const currentModelFields = ref<any[]>([])
const currentModelId = ref<number | null>(null)

// CI 详情抽屉
const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)

// CI 编辑弹窗
const editModalVisible = ref(false)
const currentInstance = ref<any>(null)

// 列设置
const columnModalVisible = ref(false)
const baseColumns = [
  { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true },
  { title: '操作', key: 'action', width: 180, fixed: 'right', visible: true }
]
const availableColumns = ref<any[]>([...baseColumns])
const displayColumns = computed(() => availableColumns.value.filter(col => col.visible))

// 导入
const importModalVisible = ref(false)
const importing = ref(false)
const importFileList = ref<any[]>([])
const templateLoading = ref(false)

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

let dragItem: any = null

onMounted(async () => {
  await fetchViewInfo()
  await fetchTreeData()
  await fetchModels()
})

const fetchViewInfo = async () => {
  try {
    const res = await getCustomView(viewId.value)
    if (res.code === 200) {
      viewInfo.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchTreeData = async () => {
  try {
    const res = await getViewNodesTree(viewId.value)
    if (res.code === 200) {
      treeData.value = convertToTreeData(res.data)
      filteredTreeData.value = treeData.value
      const keys: number[] = []
      const getKeys = (nodes: any[]) => {
        nodes.forEach(node => {
          keys.push(node.key)
          if (node.children) getKeys(node.children)
        })
      }
      getKeys(treeData.value)
      expandedKeys.value = keys
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      cmdbModels.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const convertToTreeData = (nodes: any[]): any[] => {
  return nodes.map(node => ({
    key: node.id,
    title: node.name,
    data: node,
    children: node.children ? convertToTreeData(node.children) : [],
    isLeaf: !node.children || node.children.length === 0
  }))
}

const getModelName = (modelId: number | string) => {
  const model = cmdbModels.value.find(m => m.id === Number(modelId))
  return model ? model.name : ''
}

// 树形搜索
const handleTreeSearch = () => {
  if (!treeSearchKeyword.value) {
    filteredTreeData.value = treeData.value
    return
  }

  const keyword = treeSearchKeyword.value.toLowerCase()

  const filterTree = (nodes: any[]): any[] => {
    return nodes.map(node => {
      const newNode = { ...node }

      const isMatch = node.title?.toLowerCase().includes(keyword)

      if (node.children && node.children.length > 0) {
        newNode.children = filterTree(node.children)
      }

      if (isMatch || (newNode.children && newNode.children.length > 0)) {
        return newNode
      }

      return null
    }).filter(Boolean)
  }

  filteredTreeData.value = filterTree(treeData.value)
}

const onNodeSelect = async (keys: number[]) => {
  if (keys.length > 0) {
    selectedNodeKeys.value = keys
    currentNodeId.value = keys[0]

    const findNode = (nodes: any[], key: number): any => {
      for (const node of nodes) {
        if (node.key === key) return node.data
        if (node.children) {
          const found = findNode(node.children, key)
          if (found) return found
        }
      }
      return null
    }

    const node = findNode(treeData.value, keys[0])
    if (node) {
      currentNodeName.value = node.name
      currentModelId.value = node.filter_config?.model_id || null
      await fetchModelFields(node.filter_config?.model_id)
      await fetchCIs()
    }
  } else {
    selectedNodeKeys.value = []
    currentNodeId.value = null
    currentNodeName.value = ''
    currentModelId.value = null
    instances.value = []
  }
}

const onExpand = (keys: number[]) => {
  expandedKeys.value = keys
  autoExpandParent.value = false
}

const fetchCIs = async () => {
  if (!currentNodeId.value) return

  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value
    }
    
    // 添加属性筛选参数
    if (attrFilterField.value && attrFilterValue.value) {
      params.attr_field = attrFilterField.value
      params.attr_value = attrFilterValue.value
    }
    
    const res = await getNodeCis(currentNodeId.value, params)
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

const fetchModelFields = async (modelId: number | string | null) => {
  if (!modelId) {
    currentModelFields.value = []
    resetColumns()
    return
  }

  try {
    const res = await getModelDetail(Number(modelId))
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
      currentModelFields.value = fields
      buildColumns()
    }
  } catch (error) {
    console.error(error)
  }
}

const buildColumns = () => {
  const newColumns = [
    { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true }
  ]

  // 添加模型字段列
  currentModelFields.value.forEach((field: any) => {
    if (!['id', 'code', 'created_at', 'updated_at'].includes(field.code)) {
      newColumns.push({
        title: field.name,
        dataIndex: field.code,
        key: field.code,
        ellipsis: true,
        visible: true
      })
    }
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
  fetchCIs()
}

const handleReset = () => {
  searchKeyword.value = ''
  attrFilterField.value = null
  attrFilterValue.value = ''
  pagination.current = 1
  fetchCIs()
}

const handleAttrFieldChange = () => {
  attrFilterValue.value = ''
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchCIs()
}

const onSelectChange = (keys: number[]) => {
  selectedRowKeys.value = keys
}

// 新增 CI
const handleAdd = () => {
  currentInstance.value = null
  editModalVisible.value = true
}

// 查看 CI
const handleView = (record: any) => {
  currentInstanceId.value = record.id
  detailDrawerVisible.value = true
}

// 编辑 CI
const handleEdit = (record: any) => {
  currentInstance.value = record
  editModalVisible.value = true
}

// 复制 CI
const handleCopy = async (record: any) => {
  try {
    const res = await getInstances({
      model_id: record.model_id,
      code: record.code,
      page: 1,
      page_size: 1
    })
    if (res.code === 200 && res.data.items.length > 0) {
      const fullInstance = res.data.items[0]
      currentInstance.value = {
        ...fullInstance,
        id: null,
        code: null,
        name: fullInstance.name + '_副本'
      }
      editModalVisible.value = true
    }
  } catch (error) {
    message.error('获取CI详情失败')
  }
}

// 获取属性值
const getAttributeValue = (record: any, dataIndex: string) => {
  // 对于系统字段（id, code, created_at, updated_at），直接从 record 获取
  const systemFields = ['id', 'code', 'created_at', 'updated_at', 'created_by', 'updated_by']
  if (systemFields.includes(dataIndex)) {
    return record[dataIndex] !== undefined ? record[dataIndex] : ''
  }
  
  // 对于其他字段，优先从 attributes 中获取（模型属性）
  if (record.attributes && record.attributes[dataIndex] !== undefined && record.attributes[dataIndex] !== null) {
    return record.attributes[dataIndex]
  }
  
  // 如果 attributes 中没有，再从 record 直接获取
  if (record[dataIndex] !== undefined && record[dataIndex] !== null) {
    return record[dataIndex]
  }
  
  return ''
}

// 删除 CI
const handleDelete = async (record: any) => {
  try {
    const res = await deleteInstance(record.id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchCIs()
    } else {
      message.error(res.message || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const handleDetailSuccess = () => {
  fetchCIs()
}

const handleSuccess = () => {
  fetchCIs()
}

const handleEditFromDetail = (instance: any) => {
  currentInstance.value = instance
  currentInstanceId.value = instance.id
  detailDrawerVisible.value = false
  editModalVisible.value = true
}

// 列设置
const showColumnSetting = () => {
  columnModalVisible.value = true
}

const handleColumnOk = () => {
  columnModalVisible.value = false
}

const dragStart = (e: DragEvent, col: any) => {
  dragItem = col
}

const drop = (_e: DragEvent, col: any) => {
  if (!dragItem || dragItem === col) return

  const fromIndex = availableColumns.value.indexOf(dragItem)
  const toIndex = availableColumns.value.indexOf(col)

  availableColumns.value.splice(fromIndex, 1)
  availableColumns.value.splice(toIndex, 0, dragItem)

  dragItem = null
}

// 导入
const handleImport = () => {
  if (!currentModelId.value) {
    message.warning('请先选择节点')
    return
  }
  importModalVisible.value = true
}

const handleDownloadTemplate = async () => {
  if (!currentModelId.value) return
  templateLoading.value = true
  try {
    const res = await getImportTemplate(currentModelId.value)
    if (res.code === 200) {
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `导入模板_${currentModelId.value}.csv`
      link.click()
      message.success('模板下载成功')
    }
  } catch (error) {
    message.error('模板下载失败')
  } finally {
    templateLoading.value = false
  }
}

const beforeUpload = (file: any) => {
  importFileList.value = [file]
  return false
}

const handleImportOk = async () => {
  if (!currentModelId.value || importFileList.value.length === 0) {
    message.warning('请选择文件')
    return
  }
  importing.value = true
  try {
    const file = importFileList.value[0]
    const res = await importInstances(currentModelId.value, file)
    if (res.code === 200) {
      message.success(`导入成功：${res.data.success} 条，失败：${res.data.failed} 条`)
      importModalVisible.value = false
      importFileList.value = []
      fetchCIs()
    } else {
      message.error(res.message || '导入失败')
    }
  } catch (error) {
    message.error('导入失败')
  } finally {
    importing.value = false
  }
}

// 导出
const handleExport = async () => {
  if (!currentModelId.value) {
    message.warning('请先选择节点')
    return
  }
  try {
    const res = await exportInstances({
      model_id: currentModelId.value,
      keyword: searchKeyword.value
    })
    if (res.code === 200) {
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `CI导出_${currentModelId.value}_${new Date().getTime()}.csv`
      link.click()
      message.success('导出成功')
    }
  } catch (error) {
    message.error('导出失败')
  }
}

const handleExportSelected = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要导出的CI')
    return
  }
  try {
    const res = await exportInstances({
      model_id: currentModelId.value,
      ids: selectedRowKeys.value
    })
    if (res.code === 200) {
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `CI导出_选中_${new Date().getTime()}.csv`
      link.click()
      message.success('导出成功')
    }
  } catch (error) {
    message.error('导出失败')
  }
}

// 批量操作
const handleBatchEdit = () => {
  message.info('批量编辑功能开发中')
}

const handleBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要删除的CI')
    return
  }
  try {
    const res = await batchDeleteInstances(selectedRowKeys.value)
    if (res.code === 200) {
      message.success('批量删除成功')
      selectedRowKeys.value = []
      fetchCIs()
    } else {
      message.error(res.message || '批量删除失败')
    }
  } catch (error) {
    message.error('批量删除失败')
  }
}
</script>

<style scoped>
.custom-view-page {
  height: calc(100vh - 100px);
  background: #f0f2f5;
}

.full-height {
  height: 100%;
}

.tree-col {
  height: 100%;
}

.tree-card {
  height: 100%;
  overflow: auto;
}

.content-col {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-card {
  flex-shrink: 0;
}

.table-card {
  flex: 1;
  overflow: auto;
}

.node-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ci-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}

.ci-toolbar-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-control {
  width: auto;
}

.toolbar-control-keyword {
  width: 250px;
}

.toolbar-control-attr {
  width: 200px;
}

.ci-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.batch-bar {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
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
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: move;
}

.column-item:hover {
  background: #f5f5f5;
}

.drag-icon {
  color: #999;
  cursor: move;
}

.import-template-action {
  margin-bottom: 16px;
  text-align: center;
}
</style>
