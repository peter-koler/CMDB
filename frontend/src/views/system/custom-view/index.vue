<template>
  <div class="custom-view-page">
    <a-card :bordered="false">
      <div class="search-bar">
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索视图名称或标识"
            style="width: 300px"
            @search="handleSearch"
          />
          <a-select
            v-model:value="filterStatus"
            placeholder="筛选状态"
            style="width: 120px"
            allowClear
            @change="handleSearch"
          >
            <a-select-option value="true">启用</a-select-option>
            <a-select-option value="false">禁用</a-select-option>
          </a-select>
          <a-button type="primary" @click="showViewModal()">
            <PlusOutlined />
            新增视图
          </a-button>
          <a-button @click="handleExport">
            <ExportOutlined />
            导出
          </a-button>
          <a-button @click="showImportModal">
            <ImportOutlined />
            导入
          </a-button>
        </a-space>
      </div>

      <a-table
        :columns="columns"
        :data-source="views"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'icon'">
            <component :is="record.icon" />
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleDesign(record)">
                设计
              </a-button>
              <a-button type="link" size="small" @click="showViewModal(record)">
                编辑
              </a-button>
              <a-button type="link" size="small" @click="handlePreview(record)">
                预览
              </a-button>
              <a-popconfirm title="确定删除该视图吗？" @confirm="handleDelete(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="viewModalVisible"
      :title="isEdit ? '编辑视图' : '新增视图'"
      @ok="handleViewSubmit"
    >
      <a-form :model="viewForm" :rules="viewRules" ref="viewFormRef">
        <a-form-item label="视图名称" name="name">
          <a-input v-model:value="viewForm.name" placeholder="请输入视图名称" />
        </a-form-item>
        <a-form-item label="视图标识" name="code">
          <a-input v-model:value="viewForm.code" placeholder="请输入视图标识" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="图标" name="icon">
          <a-input v-model:value="viewForm.icon" placeholder="请输入图标名称" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="viewForm.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="viewForm.is_active" checked-children="启用" un-checked-children="禁用" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="viewForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="importModalVisible"
      title="导入视图"
      @ok="handleImport"
    >
      <a-upload-dragger
        v-model:fileList="fileList"
        name="file"
        accept=".xlsx,.xls,.csv"
        :multiple="false"
        :before-upload="beforeUpload"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此处上传</p>
        <p class="ant-upload-hint">支持 .xlsx, .xls, .csv 格式文件</p>
      </a-upload-dragger>
      <div style="margin-top: 16px">
        <a-button type="link" @click="handleDownloadTemplate">
          下载导入模板
        </a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, ExportOutlined, ImportOutlined, InboxOutlined } from '@ant-design/icons-vue'
import {
  getCustomViews,
  createCustomView,
  updateCustomView,
  deleteCustomView
} from '@/api/custom-view'

const router = useRouter()
const loading = ref(false)
const views = ref<any[]>([])
const searchKeyword = ref('')
const filterStatus = ref<string | null>(null)

const columns = [
  { title: '视图名称', dataIndex: 'name', key: 'name' },
  { title: '视图标识', dataIndex: 'code', key: 'code' },
  { title: '图标', key: 'icon', width: 80 },
  { title: '节点数量', dataIndex: 'node_count', key: 'node_count', width: 100 },
  { title: '状态', key: 'is_active', width: 80 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 220 }
]

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const viewModalVisible = ref(false)
const isEdit = ref(false)
const viewFormRef = ref()
const viewForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  icon: 'AppstoreOutlined',
  description: '',
  is_active: true,
  sort_order: 0
})

const viewRules = {
  name: [{ required: true, message: '请输入视图名称' }],
  code: [{ required: true, message: '请输入视图标识' }]
}

const importModalVisible = ref(false)
const fileList = ref<any[]>([])

onMounted(() => {
  fetchViews()
})

const fetchViews = async () => {
  loading.value = true
  try {
    const res = await getCustomViews({
      page: pagination.current,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value,
      is_active: filterStatus.value
    })
    if (res.code === 200) {
      views.value = res.data.items
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
  fetchViews()
}

const showViewModal = (view?: any) => {
  isEdit.value = !!view
  if (view) {
    Object.assign(viewForm, view)
  } else {
    Object.assign(viewForm, {
      id: null,
      name: '',
      code: '',
      icon: 'AppstoreOutlined',
      description: '',
      is_active: true,
      sort_order: 0
    })
  }
  viewModalVisible.value = true
}

const handleViewSubmit = async () => {
  try {
    await viewFormRef.value.validate()
    
    if (isEdit.value) {
      await updateCustomView(viewForm.id!, viewForm)
      message.success('更新成功')
    } else {
      await createCustomView(viewForm)
      message.success('创建成功')
    }
    
    viewModalVisible.value = false
    fetchViews()
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteCustomView(id)
    message.success('删除成功')
    fetchViews()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const handleDesign = (record: any) => {
  router.push(`/custom-view-design/${record.id}`)
}

const handlePreview = (record: any) => {
  router.push(`/cmdb/custom-view/view/${record.id}`)
}

const showImportModal = () => {
  fileList.value = []
  importModalVisible.value = true
}

const beforeUpload = (file: File) => {
  const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || 
                  file.type === 'application/vnd.ms-excel' ||
                  file.name.endsWith('.csv')
  if (!isExcel) {
    message.error('只支持 Excel 或 CSV 文件')
    return false
  }
  return false
}

const handleImport = async () => {
  if (fileList.value.length === 0) {
    message.warning('请选择要导入的文件')
    return
  }
  message.success('导入功能开发中')
}

const handleDownloadTemplate = () => {
  message.info('模板下载功能开发中')
}

const handleExport = () => {
  message.info('导出功能开发中')
}
</script>

<style scoped>
.custom-view-page {
  padding: 16px;
}

.search-bar {
  margin-bottom: 16px;
}
</style>
