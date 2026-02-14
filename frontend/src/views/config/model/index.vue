<template>
  <div class="model-page">
    <a-row :gutter="16" class="full-height">
      <!-- 左侧目录树 -->
      <a-col :xs="24" :sm="8" :md="6" :lg="5" class="tree-col">
        <a-card :bordered="false" class="tree-card" title="模型目录">
          <template #extra>
            <a-space>
              <a-button type="text" size="small" @click="showCategoryModal()">
                <PlusOutlined />
              </a-button>
              <a-button type="text" size="small" @click="refreshCategories">
                <ReloadOutlined />
              </a-button>
            </a-space>
          </template>
          <a-tree
            :tree-data="categoryTree"
            :selected-keys="selectedCategoryKeys"
            :expanded-keys="expandedKeys"
            @select="onCategorySelect"
            @expand="onExpand"
            :field-names="{ title: 'name', key: 'id', children: 'children' }"
          >
            <template #title="{ name, id }">
              <a-dropdown :trigger="['contextmenu']">
                <span>{{ name }}</span>
                <template #overlay>
                  <a-menu @click="(e: any) => handleCategoryMenuClick(e, id)">
                    <a-menu-item key="add">添加子目录</a-menu-item>
                    <a-menu-item key="edit">编辑</a-menu-item>
                    <a-menu-item key="delete" danger>删除</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </template>
          </a-tree>
        </a-card>
      </a-col>

      <!-- 右侧模型列表 -->
      <a-col :xs="24" :sm="16" :md="18" :lg="19" class="content-col">
        <a-card :bordered="false" class="search-card">
          <a-form layout="inline" class="search-form">
            <a-row :gutter="[16, 16]" style="width: 100%">
              <a-col :xs="24" :sm="12" :md="8">
                <a-form-item label="模型名称">
                  <a-input
                    v-model:value="searchKeyword"
                    placeholder="请输入模型名称或编码"
                    allowClear
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :sm="12" :md="8">
                <a-form-item label="模型类型">
                  <a-select
                    v-model:value="searchType"
                    placeholder="请选择模型类型"
                    style="width: 100%"
                    allowClear
                  >
                    <a-select-option v-for="type in modelTypes" :key="type.id" :value="type.id">
                      {{ type.name }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="24" :sm="24" :md="8">
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
                    <a-button type="primary" @click="showModelModal()">
                      <template #icon><PlusOutlined /></template>
                      新增模型
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
            :data-source="models"
            :loading="loading"
            :pagination="pagination"
            @change="handleTableChange"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'icon'">
                <component :is="record.icon || 'AppstoreOutlined'" />
              </template>
              <template v-else-if="column.key === 'category'">
                {{ record.category_name }}
              </template>
              <template v-else-if="column.key === 'type'">
                {{ record.model_type_name || '-' }}
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space wrap>
                  <a-button type="link" size="small" @click="openDesigner(record)">
                    设计
                  </a-button>
                  <a-button type="link" size="small" @click="showModelModal(record)">
                    编辑
                  </a-button>
                  <a-button type="link" size="small" @click="exportModelData(record.id)">
                    导出
                  </a-button>
                  <a-popconfirm
                    title="确定删除该模型吗？"
                    @confirm="handleDeleteModel(record.id)"
                  >
                    <a-button type="link" size="small" danger>
                      删除
                    </a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- 目录编辑弹窗 -->
    <a-modal
      v-model:open="categoryModalVisible"
      :title="isEditCategory ? '编辑目录' : '新增目录'"
      @ok="handleCategorySubmit"
      :confirm-loading="categoryLoading"
    >
      <a-form :model="categoryForm" :rules="categoryRules" ref="categoryFormRef">
        <a-form-item label="目录名称" name="name">
          <a-input v-model:value="categoryForm.name" placeholder="请输入目录名称" />
        </a-form-item>
        <a-form-item label="目录编码" name="code">
          <a-input v-model:value="categoryForm.code" placeholder="请输入目录编码" :disabled="isEditCategory" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="categoryForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 模型编辑弹窗 -->
    <a-modal
      v-model:open="modelModalVisible"
      :title="isEditModel ? '编辑模型' : '新增模型'"
      @ok="handleModelSubmit"
      :confirm-loading="modelLoading"
      width="600px"
    >
      <a-form :model="modelForm" :rules="modelRules" ref="modelFormRef" :label-col="{ span: 4 }" :wrapper-col="{ span: 20 }">
        <a-form-item label="模型名称" name="name">
          <a-input v-model:value="modelForm.name" placeholder="请输入模型名称" />
        </a-form-item>
        <a-form-item label="模型编码" name="code">
          <a-input v-model:value="modelForm.code" placeholder="请输入模型编码" :disabled="isEditModel" />
        </a-form-item>
        <a-form-item label="所属目录" name="category_id">
          <a-tree-select
            v-model:value="modelForm.category_id"
            :tree-data="categoryTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="请选择所属目录"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="模型类型" name="model_type_id">
          <a-select v-model:value="modelForm.model_type_id" placeholder="请选择模型类型" allowClear>
            <a-select-option v-for="type in modelTypes" :key="type.id" :value="type.id">
              {{ type.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模型图标" name="icon">
          <a-input v-model:value="modelForm.icon" placeholder="请输入图标名称，如：AppstoreOutlined" />
        </a-form-item>
        <a-form-item label="模型描述" name="description">
          <a-textarea v-model:value="modelForm.description" :rows="3" placeholder="请输入模型描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 模型设计器抽屉 -->
    <ModelDesigner
      v-model:visible="designerVisible"
      :model="currentModel"
      @save="handleDesignerSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined
} from '@ant-design/icons-vue'
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  getModelTypes,
  getModels,
  createModel,
  updateModel,
  deleteModel,
  exportModel
} from '@/api/cmdb'
import ModelDesigner from './components/ModelDesigner.vue'

// 目录树
const categoryTree = ref<any[]>([])
const selectedCategoryKeys = ref<string[]>([])
const expandedKeys = ref<string[]>([])
const currentCategoryId = ref<number | null>(null)

// 模型类型
const modelTypes = ref<any[]>([])

// 模型列表
const loading = ref(false)
const models = ref<any[]>([])
const searchKeyword = ref('')
const searchType = ref<number | null>(null)

const columns = [
  { title: '图标', key: 'icon', width: 80 },
  { 
    title: '模型名称', 
    dataIndex: 'name', 
    key: 'name',
    customRender: ({ record }: { record: any }) => {
      return h('a', {
        onClick: () => openDesigner(record),
        style: { cursor: 'pointer', color: '#1890ff' }
      }, record.name)
    }
  },
  { title: '模型编码', dataIndex: 'code', key: 'code' },
  { title: '所属目录', key: 'category' },
  { title: '模型类型', key: 'type' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 250 }
]

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 目录编辑
const categoryModalVisible = ref(false)
const categoryLoading = ref(false)
const isEditCategory = ref(false)
const categoryFormRef = ref()
const categoryForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  parent_id: null as number | null,
  sort_order: 0
})

const categoryRules = {
  name: [{ required: true, message: '请输入目录名称' }],
  code: [{ required: true, message: '请输入目录编码' }]
}

// 模型编辑
const modelModalVisible = ref(false)
const modelLoading = ref(false)
const isEditModel = ref(false)
const modelFormRef = ref()
const modelForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  category_id: null as number | null,
  model_type_id: null as number | null,
  icon: 'AppstoreOutlined',
  description: ''
})

const modelRules = {
  name: [{ required: true, message: '请输入模型名称' }],
  code: [{ required: true, message: '请输入模型编码' }],
  category_id: [{ required: true, message: '请选择所属目录' }]
}

// 设计器
const designerVisible = ref(false)
const currentModel = ref<any>(null)

// 初始化
onMounted(() => {
  fetchCategories()
  fetchModelTypes()
  fetchModels()
})

// 获取目录树
const fetchCategories = async () => {
  try {
    const res = await getCategories()
    if (res.code === 200) {
      categoryTree.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

// 获取模型类型
const fetchModelTypes = async () => {
  try {
    const res = await getModelTypes()
    if (res.code === 200) {
      modelTypes.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

// 获取模型列表
const fetchModels = async () => {
  loading.value = true
  try {
    const res = await getModels({
      page: pagination.current,
      per_page: pagination.pageSize,
      category_id: currentCategoryId.value,
      keyword: searchKeyword.value,
      model_type_id: searchType.value
    })
    if (res.code === 200) {
      models.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 目录选择
const onCategorySelect = (selectedKeys: any, info: any) => {
  selectedCategoryKeys.value = selectedKeys
  currentCategoryId.value = selectedKeys[0] || null
  pagination.current = 1
  fetchModels()
}

const onExpand = (keys: any) => {
  expandedKeys.value = keys
}

// 刷新目录
const refreshCategories = () => {
  fetchCategories()
}

// 目录右键菜单
const handleCategoryMenuClick = (e: any, id: number) => {
  if (e.key === 'add') {
    showCategoryModal(null, id)
  } else if (e.key === 'edit') {
    const category = findCategory(categoryTree.value, id)
    if (category) {
      showCategoryModal(category)
    }
  } else if (e.key === 'delete') {
    handleDeleteCategory(id)
  }
}

const findCategory = (tree: any[], id: number): any => {
  for (const item of tree) {
    if (item.id === id) return item
    if (item.children) {
      const found = findCategory(item.children, id)
      if (found) return found
    }
  }
  return null
}

// 显示目录弹窗
const showCategoryModal = (category?: any, parentId?: number) => {
  isEditCategory.value = !!category
  if (category) {
    Object.assign(categoryForm, category)
  } else {
    Object.assign(categoryForm, {
      id: null,
      name: '',
      code: '',
      parent_id: parentId || null,
      sort_order: 0
    })
  }
  categoryModalVisible.value = true
}

// 提交目录
const handleCategorySubmit = async () => {
  try {
    await categoryFormRef.value.validate()
    categoryLoading.value = true
    
    if (isEditCategory.value) {
      await updateCategory(categoryForm.id!, categoryForm)
      message.success('更新成功')
    } else {
      await createCategory(categoryForm)
      message.success('创建成功')
    }
    
    categoryModalVisible.value = false
    fetchCategories()
  } catch (error: any) {
    if (error.response) {
      message.error(error.response?.data?.message || '操作失败')
    }
  } finally {
    categoryLoading.value = false
  }
}

// 删除目录
const handleDeleteCategory = async (id: number) => {
  try {
    await deleteCategory(id)
    message.success('删除成功')
    fetchCategories()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  fetchModels()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchType.value = null
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchModels()
}

// 显示模型弹窗
const showModelModal = (model?: any) => {
  isEditModel.value = !!model
  if (model) {
    Object.assign(modelForm, model)
  } else {
    Object.assign(modelForm, {
      id: null,
      name: '',
      code: '',
      category_id: currentCategoryId.value,
      model_type_id: null,
      icon: 'AppstoreOutlined',
      description: ''
    })
  }
  modelModalVisible.value = true
}

// 提交模型
const handleModelSubmit = async () => {
  try {
    await modelFormRef.value.validate()
    modelLoading.value = true
    
    if (isEditModel.value) {
      await updateModel(modelForm.id!, modelForm)
      message.success('更新成功')
    } else {
      await createModel(modelForm)
      message.success('创建成功')
    }
    
    modelModalVisible.value = false
    fetchModels()
  } catch (error: any) {
    if (error.response) {
      message.error(error.response?.data?.message || '操作失败')
    }
  } finally {
    modelLoading.value = false
  }
}

// 删除模型
const handleDeleteModel = async (id: number) => {
  try {
    await deleteModel(id)
    message.success('删除成功')
    fetchModels()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

// 导出模型
const exportModelData = async (id: number) => {
  try {
    const res = await exportModel(id)
    if (res.code === 200) {
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `model_${id}.json`
      link.click()
      message.success('导出成功')
    }
  } catch (error) {
    message.error('导出失败')
  }
}

// 打开设计器
const openDesigner = (model: any) => {
  currentModel.value = model
  designerVisible.value = true
}

const handleDesignerSave = async (data: any) => {
  try {
    await updateModel(data.id, {
      name: data.name,
      code: data.code,
      icon: data.icon,
      category_id: data.category_id,
      model_type_id: data.model_type_id,
      description: data.description,
      form_config: data.form_config
    })
    message.success('保存成功')
    fetchModels()
  } catch (error) {
    console.error(error)
  }
}
</script>

<style scoped>
.model-page {
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
  border-radius: 8px;
}

.tree-card :deep(.ant-card-body) {
  padding: 12px;
  height: calc(100% - 56px);
  overflow: auto;
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
  flex: 1;
}

.table-card :deep(.ant-card-body) {
  padding: 24px;
}
</style>
