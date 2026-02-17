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
          <div class="ci-toolbar">
            <div class="ci-toolbar-filters">
              <a-input-search
                v-model:value="searchKeyword"
                placeholder="搜索CI编码"
                class="toolbar-control toolbar-control-keyword"
                @search="handleSearch"
              />
              <a-select
                v-model:value="searchDept"
                placeholder="选择部门"
                class="toolbar-control"
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
                  class="toolbar-control"
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
                  class="toolbar-control"
                  @pressEnter="handleSearch"
                />
              </template>
              <a-range-picker
                v-model:value="dateRange"
                class="toolbar-control toolbar-control-date"
                @change="handleSearch"
              />
            </div>

            <div class="ci-toolbar-actions">
              <a-space wrap class="toolbar-action-all">
                <a-button type="primary" @click="handleSearch">
                  <SearchOutlined />
                  搜索
                </a-button>
                <a-button @click="handleReset">重置</a-button>
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
            </div>
          </div>
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
              <a-button size="small" @click="handleExportSelected">导出选中</a-button>
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
          <a-checkbox v-model:checked="col.visible">{{ col.settingTitle || col.title }}</a-checkbox>
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

    <!-- 批量编辑弹窗 -->
    <a-modal
      v-model:open="batchEditModalVisible"
      title="批量编辑CI属性"
      @ok="handleBatchEditOk"
      :confirm-loading="batchEditLoading"
      width="500px"
    >
      <a-alert
        message="只能编辑以下类型的属性"
        :description="`支持批量编辑的字段类型：${allowedFieldTypesText}`"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />

      <div v-if="batchEditLoading" class="batch-edit-loading">
        <a-spin tip="加载中..." />
      </div>

      <div v-else-if="batchEditableFields.length === 0" class="batch-edit-empty">
        <a-empty description="该模型没有支持批量编辑的字段" />
      </div>

      <div v-else class="batch-edit-form">
        <!-- 选择要编辑的属性 -->
        <div class="batch-edit-field">
          <div class="batch-edit-field-label required">选择属性</div>
          <div class="batch-edit-field-input">
            <a-select
              v-model:value="selectedBatchEditField"
              placeholder="请选择要编辑的属性"
              style="width: 100%"
              @change="onBatchEditFieldChange"
            >
              <a-select-option
                v-for="field in batchEditableFields"
                :key="field.code"
                :value="field.code"
              >
                {{ field.name }}
              </a-select-option>
            </a-select>
          </div>
        </div>

        <!-- 属性值编辑区域 -->
        <div v-if="currentBatchEditField" class="batch-edit-field">
          <div class="batch-edit-field-label required">
            {{ currentBatchEditField.name }}
          </div>
          <div class="batch-edit-field-input">
            <!-- 下拉选择/单选 -->
            <a-select
              v-if="currentBatchEditField.field_type === 'dropdown' || currentBatchEditField.field_type === 'select'"
              v-model:value="batchEditValue"
              :placeholder="`请选择${currentBatchEditField.name}`"
              allowClear
              style="width: 100%"
            >
              <a-select-option
                v-for="opt in currentBatchEditField.options"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </a-select-option>
            </a-select>

            <!-- 多选 -->
            <a-select
              v-else-if="currentBatchEditField.field_type === 'multiselect'"
              v-model:value="batchEditValue"
              :placeholder="`请选择${currentBatchEditField.name}`"
              mode="multiple"
              allowClear
              style="width: 100%"
            >
              <a-select-option
                v-for="opt in currentBatchEditField.options"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </a-select-option>
            </a-select>

            <!-- 数字 -->
            <a-input-number
              v-else-if="currentBatchEditField.field_type === 'number'"
              v-model:value="batchEditValue"
              :placeholder="`请输入${currentBatchEditField.name}`"
              style="width: 100%"
            />

            <!-- 日期 -->
            <a-date-picker
              v-else-if="currentBatchEditField.field_type === 'date'"
              v-model:value="batchEditValue"
              :placeholder="`请选择${currentBatchEditField.name}`"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />

            <!-- 日期时间 -->
            <a-date-picker
              v-else-if="currentBatchEditField.field_type === 'datetime'"
              v-model:value="batchEditValue"
              :placeholder="`请选择${currentBatchEditField.name}`"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%"
            />

            <!-- 时间 -->
            <a-time-picker
              v-else-if="currentBatchEditField.field_type === 'time'"
              v-model:value="batchEditValue"
              :placeholder="`请选择${currentBatchEditField.name}`"
              value-format="HH:mm:ss"
              style="width: 100%"
            />

            <!-- 多行文本 -->
            <a-textarea
              v-else-if="currentBatchEditField.field_type === 'textarea'"
              v-model:value="batchEditValue"
              :placeholder="`请输入${currentBatchEditField.name}`"
              :rows="3"
            />

            <!-- 单行文本（默认） -->
            <a-input
              v-else
              v-model:value="batchEditValue"
              :placeholder="`请输入${currentBatchEditField.name}`"
            />
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch, h } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  SearchOutlined,
  PlusOutlined,
  SettingOutlined,
  DragOutlined,
  FolderOutlined,
  ExportOutlined,
  ImportOutlined,
  InboxOutlined
} from '@ant-design/icons-vue'
import { getInstances, deleteInstance, batchDeleteInstances, batchUpdateInstances, generateCICode, exportInstances, importInstances, getImportTemplate, getBatchEditFields } from '@/api/ci'
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
const keyFieldCodes = ref<Set<string>>(new Set())
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

// 批量编辑相关
const batchEditModalVisible = ref(false)
const batchEditLoading = ref(false)
const batchEditableFields = ref<any[]>([])
const selectedBatchEditField = ref<string>('')
const batchEditValue = ref<any>(null)

// 当前选中的批量编辑字段
const currentBatchEditField = computed(() => {
  return batchEditableFields.value.find(f => f.code === selectedBatchEditField.value)
})

// 允许批量编辑的字段类型
const allowedFieldTypes = [
  'text',      // 单行文本
  'textarea',  // 多行文本
  'number',    // 数字
  'date',      // 日期
  'datetime',  // 日期时间
  'time',      // 时间控件
  'dropdown',  // 下拉选择
  'select',    // 单选
  'multiselect' // 多选
]

const allowedFieldTypesText = '单行文本、多行文本、数字、日期、日期时间、时间、下拉选择、单选、多选'

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
          await fetchModelFields(firstNode.model_id)
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
  selectedRowKeys.value = []
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

      // 关键属性优先使用模型配置；兼容历史数据（字段里可能有 isKey 标记）
      const configuredKeyCodes = Array.isArray(res?.data?.key_field_codes)
        ? res.data.key_field_codes
        : (Array.isArray(res?.data?.config?.key_field_codes) ? res.data.config.key_field_codes : [])
      let normalizedKeyCodes = configuredKeyCodes
        .map((code: any) => String(code).trim())
        .filter(Boolean)

      if (normalizedKeyCodes.length === 0) {
        normalizedKeyCodes = fields
          .filter((field: any) => Boolean(
            field.is_key ||
            field.isKey ||
            field.isKeyField ||
            field.key_field ||
            field.keyField ||
            field.isKeyAttribute
          ))
          .map((field: any) => String(field.code).trim())
          .filter(Boolean)
      }
      keyFieldCodes.value = new Set(normalizedKeyCodes)
      updateColumns()
    } else {
      modelFields.value = []
      keyFieldCodes.value = new Set()
      updateColumns()
    }
  } catch (error) {
    console.error(error)
    modelFields.value = []
    keyFieldCodes.value = new Set()
    updateColumns()
  }
}

const updateColumns = () => {
  const newColumns: any[] = [
    { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true }
  ]
  
  modelFields.value.forEach((field: any) => {
    const isKeyField = keyFieldCodes.value.has(String(field.code))
    newColumns.push({
      title: isKeyField
        ? h('span', { class: 'key-attr-title' }, [
            h('span', { class: 'key-attr-star' }, '*'),
            h('span', field.name)
          ])
        : field.name,
      settingTitle: field.name,
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
  keyFieldCodes.value = new Set()
  availableColumns.value = [
    { title: 'CI编码', dataIndex: 'code', key: 'code', width: 160, visible: true },
    { title: '操作', key: 'action', width: 180, fixed: 'right', visible: true }
  ]
}

const handleSearch = () => {
  selectedRowKeys.value = []
  pagination.current = 1
  fetchInstances()
}

const handleReset = () => {
  selectedRowKeys.value = []
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

const handleBatchEdit = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要编辑的CI')
    return
  }
  if (!currentModelId.value) {
    message.warning('请先选择模型')
    return
  }

  batchEditModalVisible.value = true
  batchEditLoading.value = true
  selectedBatchEditField.value = ''
  batchEditValue.value = null

  try {
    const res = await getBatchEditFields(currentModelId.value)
    if (res.code === 200) {
      batchEditableFields.value = res.data.fields || []
    } else {
      message.error(res.message || '获取可编辑字段失败')
      batchEditableFields.value = []
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '获取可编辑字段失败')
    batchEditableFields.value = []
  } finally {
    batchEditLoading.value = false
  }
}

const onBatchEditFieldChange = () => {
  // 切换字段时清空值
  batchEditValue.value = null
}

const handleBatchEditOk = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要编辑的CI')
    return
  }

  if (!selectedBatchEditField.value) {
    message.warning('请选择要编辑的属性')
    return
  }

  if (batchEditValue.value === undefined || batchEditValue.value === null || batchEditValue.value === '') {
    message.warning('请填写属性值')
    return
  }

  batchEditLoading.value = true
  try {
    const updates = {
      [selectedBatchEditField.value]: batchEditValue.value
    }
    const res = await batchUpdateInstances({
      ids: selectedRowKeys.value.map(Number),
      updates,
      model_id: currentModelId.value
    })
    message.success(res.message || '批量更新成功')
    batchEditModalVisible.value = false
    selectedRowKeys.value = []
    fetchInstances()
  } catch (error: any) {
    message.error(error.response?.data?.message || '批量更新失败')
  } finally {
    batchEditLoading.value = false
  }
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
    if (!currentModelId.value) {
      message.warning('请先选择模型')
      return
    }

    const res = await exportInstances({
      model_id: currentModelId.value,
      keyword: searchKeyword.value
    })

    if (res.code !== 200 || !res.data?.content) {
      message.error(res.message || '导出失败')
      return
    }

    const content = `\ufeff${res.data.content}`
    const filename = res.data.filename || `${currentModelName.value}_CI_${new Date().getTime()}.csv`
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('导出成功')
  } catch (error: any) {
    message.error(error.response?.data?.message || '导出失败')
  }
}

const handleExportSelected = async () => {
  if (!currentModelId.value) {
    message.warning('请先选择模型')
    return
  }
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要导出的CI')
    return
  }

  try {
    const res = await exportInstances({
      model_id: currentModelId.value,
      keyword: searchKeyword.value,
      ids: selectedRowKeys.value
    })

    if (res.code !== 200 || !res.data?.content) {
      message.error(res.message || '导出失败')
      return
    }

    const content = `\ufeff${res.data.content}`
    const filename = res.data.filename || `${currentModelName.value}_CI_${new Date().getTime()}.csv`
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('导出成功')
  } catch (error: any) {
    message.error(error.response?.data?.message || '导出失败')
  }
}

const importModalVisible = ref(false)
const importing = ref(false)
const importFileList = ref<any[]>([])
const templateLoading = ref(false)
const importTemplate = ref<{ filename: string; content: string } | null>(null)

const beforeUpload = (file: File) => {
  importFileList.value = [file]
  return false
}

const handleDownloadTemplate = async () => {
  if (!currentModelId.value) return
  
  templateLoading.value = true
  try {
    const res = await getImportTemplate(currentModelId.value)
    if (res.code === 200) {
      // 创建 Blob 对象，注意加上 BOM 避免中文乱码
      const blob = new Blob(['\ufeff' + res.data.content], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = res.data.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(link.href)
      message.success('模板下载成功')
    }
  } catch (error) {
    console.error(error)
    message.error('模板下载失败')
  } finally {
    templateLoading.value = false
  }
}

const handleImport = () => {
  if (!currentModelId.value) return
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

const dragStart = (_e: DragEvent, col: any) => {
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
  width: 100%;
}

.search-card :deep(.ant-card-body) {
  padding: 16px 24px;
}

.ci-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ci-toolbar-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.ci-toolbar-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  width: 100%;
}

.toolbar-action-all {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  width: 100%;
}

.toolbar-control {
  width: 160px;
}

.toolbar-control-keyword {
  width: 220px;
}

.toolbar-control-date {
  width: 260px;
}

@media (max-width: 992px) {
  .ci-toolbar-actions {
    justify-content: flex-start;
  }

  .toolbar-action-all {
    justify-content: flex-start;
  }

  .toolbar-control-date {
    width: 220px;
  }
}

@media (max-width: 576px) {
  .search-card :deep(.ant-card-body) {
    padding: 12px;
  }

  .ci-toolbar-filters {
    min-width: 100%;
  }

  .toolbar-control,
  .toolbar-control-keyword,
  .toolbar-control-date {
    width: 100%;
  }
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

.import-template-action {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-start;
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

:deep(.key-attr-title) {
  display: inline-flex;
  align-items: center;
}

:deep(.key-attr-star) {
  color: #f5222d;
  margin-right: 2px;
  font-weight: 600;
}

/* 批量编辑样式 */
.batch-edit-form {
  padding: 8px 0;
}

.batch-edit-field {
  margin-bottom: 16px;
}

.batch-edit-field-label {
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}

.batch-edit-field-label.required::before {
  content: '* ';
  color: #f5222d;
}

.batch-edit-field-input {
  width: 100%;
}

.batch-edit-loading {
  padding: 40px 0;
  text-align: center;
}

.batch-edit-empty {
  padding: 40px 0;
}

:deep(.ant-tree-treenode) {
  padding: 4px 0;
}

:deep(.ant-tree-node-content-wrapper) {
  padding: 2px 4px;
}
</style>
