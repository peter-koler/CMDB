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
                <img
                  v-if="record.icon_url"
                  :src="record.icon_url"
                  style="width: 20px; height: 20px; object-fit: contain;"
                />
                <component v-else :is="iconComponentMap[record.icon] || AppstoreOutlined" />
              </template>
              <template v-else-if="column.key === 'category'">
                {{ record.category_name }}
              </template>
              <template v-else-if="column.key === 'type'">
                {{ record.model_type_name || '-' }}
              </template>
              <template v-else-if="column.key === 'key_fields'">
                <a-tag v-if="record.key_field_codes?.length">
                  {{ record.key_field_codes.join(', ') }}
                </a-tag>
                <span v-else>-</span>
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
      <a-form :model="categoryForm" :rules="categoryRules" ref="categoryFormRef" :label-col="{ span: 4 }" :wrapper-col="{ span: 20 }">
        <a-form-item label="上级目录" name="parent_id">
          <a-tree-select
            v-model:value="categoryForm.parent_id"
            :tree-data="categoryTreeForSelect"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="请选择上级目录（不选则为顶级目录）"
            allowClear
            style="width: 100%"
            :dropdown-style="{ maxHeight: '300px', overflow: 'auto' }"
          />
        </a-form-item>
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
          <a-space direction="vertical" style="width: 100%">
            <div class="icon-picker">
              <button
                v-for="icon in builtinIconOptions"
                :key="icon"
                type="button"
                class="icon-picker-item"
                :class="{ 'icon-picker-item-selected': iconSelectionMode === 'builtin' && modelForm.icon === icon }"
                @click="selectBuiltinIcon(icon)"
              >
                <component :is="iconComponentMap[icon] || AppstoreOutlined" />
              </button>
              <button
                v-if="hasUploadedIcon"
                type="button"
                class="icon-picker-item"
                :class="{ 'icon-picker-item-selected': iconSelectionMode === 'custom' }"
                @click="iconSelectionMode = 'custom'"
              >
                <img :src="modelForm.icon_url" class="icon-picker-image" />
              </button>
            </div>
            <a-upload
              :show-upload-list="false"
              :before-upload="beforeUploadModelIcon"
              accept=".png,.svg"
            >
              <a-button :loading="iconUploading">
                上传自定义图标（png/svg，<=2MB）
              </a-button>
            </a-upload>
            <a-space align="center">
              <span style="color: #999;">当前生效图标：</span>
              <img v-if="iconSelectionMode === 'custom' && hasUploadedIcon" :src="modelForm.icon_url" style="width: 20px; height: 20px; object-fit: contain;" />
              <component v-else :is="iconComponentMap[modelForm.icon] || AppstoreOutlined" />
            </a-space>
          </a-space>
        </a-form-item>
        <a-form-item label="关键属性" name="key_field_codes">
          <a-select
            v-model:value="modelForm.key_field_codes"
            mode="multiple"
            :max-tag-count="3"
            placeholder="请选择关键属性（最多3个）"
            :options="keyFieldOptions"
            :disabled="keyFieldOptions.length === 0"
          />
          <div style="color: #999; margin-top: 4px;">
            {{ keyFieldOptions.length === 0 ? '当前模型暂无可用字段，请先在模型设计中配置文本/数字/枚举/日期类字段。' : '按选择顺序展示，空值将自动跳过。' }}
          </div>
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
import { ref, reactive, onMounted, h, computed } from 'vue'
import { message } from 'ant-design-vue'
import {
  ApiOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  ContainerOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  GlobalOutlined,
  HddOutlined,
  LaptopOutlined,
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
  getModelDetail,
  createModel,
  updateModel,
  deleteModel,
  exportModel,
  uploadModelIcon
} from '@/api/cmdb'
import ModelDesigner from './components/ModelDesigner.vue'

// 目录树
const categoryTree = ref<any[]>([])
const selectedCategoryKeys = ref<string[]>([])
const expandedKeys = ref<string[]>([])
const currentCategoryId = ref<number | null>(null)

// 用于选择的目录树（过滤掉当前编辑的目录）
const categoryTreeForSelect = computed(() => {
  if (!isEditCategory.value || !categoryForm.id) {
    return categoryTree.value
  }
  const filterTree = (items: any[]): any[] => {
    return items
      .filter(item => item.id !== categoryForm.id)
      .map(item => ({
        ...item,
        children: item.children ? filterTree(item.children) : []
      }))
  }
  return filterTree(categoryTree.value)
})

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
  { title: '关键属性', key: 'key_fields', width: 220 },
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
const iconUploading = ref(false)
const iconSelectionMode = ref<'builtin' | 'custom'>('builtin')
const isEditModel = ref(false)
const modelFormRef = ref()
const builtinIconOptions = [
  'AppstoreOutlined',
  'DatabaseOutlined',
  'CloudServerOutlined',
  'ClusterOutlined',
  'HddOutlined',
  'ApiOutlined',
  'DeploymentUnitOutlined',
  'ContainerOutlined',
  'LaptopOutlined',
  'GlobalOutlined'
]
const iconComponentMap: Record<string, any> = {
  AppstoreOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  HddOutlined,
  ApiOutlined,
  DeploymentUnitOutlined,
  ContainerOutlined,
  LaptopOutlined,
  GlobalOutlined
}
const KEY_FIELD_ALLOWED_CONTROL_TYPES = ['text', 'textarea', 'number', 'date', 'datetime', 'select', 'radio']
const keyFieldOptions = ref<{ label: string; value: string }[]>([])

const modelForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  category_id: null as number | null,
  model_type_id: null as number | null,
  icon: 'AppstoreOutlined',
  icon_url: '',
  key_field_codes: [] as string[],
  description: ''
})

const modelRules = {
  name: [{ required: true, message: '请输入模型名称' }],
  code: [{ required: true, message: '请输入模型编码' }],
  category_id: [{ required: true, message: '请选择所属目录' }]
}
const hasUploadedIcon = computed(() => !!modelForm.icon_url)

const selectBuiltinIcon = (icon: string) => {
  modelForm.icon = icon
  iconSelectionMode.value = 'builtin'
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

const extractFieldOptionsFromFormConfig = (formConfig: any): { label: string; value: string }[] => {
  let config = formConfig
  if (!config) return []
  if (typeof config === 'string') {
    try {
      config = JSON.parse(config)
    } catch {
      return []
    }
  }
  if (!Array.isArray(config)) return []

  const result: { label: string; value: string }[] = []
  const seen = new Set<string>()

  const pushField = (item: any) => {
    const controlType = item?.controlType
    const code = item?.props?.code
    const label = item?.props?.label || code
    if (!code || !KEY_FIELD_ALLOWED_CONTROL_TYPES.includes(controlType)) return
    if (seen.has(code)) return
    seen.add(code)
    result.push({ label, value: code })
  }

  config.forEach((item: any) => {
    pushField(item)
    if (Array.isArray(item?.children)) {
      item.children.forEach((child: any) => pushField(child))
    }
  })

  return result
}

// 获取目录树
const fetchCategories = async () => {
  try {
    const res = await getCategories()
    if (res.code === 200) {
      categoryTree.value = res.data
      // 自动展开所有目录
      const getAllIds = (items: any[]): number[] => {
        const ids: number[] = []
        items.forEach(item => {
          ids.push(item.id)
          if (item.children && item.children.length > 0) {
            ids.push(...getAllIds(item.children))
          }
        })
        return ids
      }
      expandedKeys.value = getAllIds(res.data).map(String)
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
const onCategorySelect = (selectedKeys: any) => {
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
const showModelModal = async (model?: any) => {
  isEditModel.value = !!model
  if (model) {
    let detail = model
    try {
      const res = await getModelDetail(model.id)
      if (res.code === 200) {
        detail = res.data
      }
    } catch (error) {
      console.error(error)
    }

    keyFieldOptions.value = extractFieldOptionsFromFormConfig(detail.form_config)
    Object.assign(modelForm, {
      ...detail,
      icon: detail.icon || 'AppstoreOutlined',
      icon_url: detail.icon_url || detail.config?.icon_url || '',
      key_field_codes: detail.key_field_codes || detail.config?.key_field_codes || []
    })
    iconSelectionMode.value = modelForm.icon_url ? 'custom' : 'builtin'
  } else {
    keyFieldOptions.value = []
    Object.assign(modelForm, {
      id: null,
      name: '',
      code: '',
      category_id: currentCategoryId.value,
      model_type_id: null,
      icon: 'AppstoreOutlined',
      icon_url: '',
      key_field_codes: [],
      description: ''
    })
    iconSelectionMode.value = 'builtin'
  }
  modelModalVisible.value = true
}

// 提交模型
const handleModelSubmit = async () => {
  try {
    await modelFormRef.value.validate()
    if (modelForm.key_field_codes.length > 3) {
      message.warning('关键属性最多只能选择 3 个')
      return
    }
    modelLoading.value = true
    const payload = {
      ...modelForm,
      icon_url: iconSelectionMode.value === 'custom' ? modelForm.icon_url : '',
      key_field_codes: modelForm.key_field_codes.slice(0, 3)
    }

    if (isEditModel.value) {
      await updateModel(modelForm.id!, payload)
      message.success('更新成功')
    } else {
      await createModel(payload)
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

const beforeUploadModelIcon = async (file: File) => {
  const isAllowedType = ['image/png', 'image/svg+xml'].includes(file.type)
  if (!isAllowedType) {
    message.error('仅支持 PNG 或 SVG 格式')
    return false
  }
  const isLt2M = file.size / 1024 / 1024 <= 2
  if (!isLt2M) {
    message.error('图标大小不能超过 2MB')
    return false
  }

  iconUploading.value = true
  try {
    const res = await uploadModelIcon(file)
    if (res.code === 200) {
      modelForm.icon_url = res.data.url
      iconSelectionMode.value = 'custom'
      message.success('图标上传成功')
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '图标上传失败')
  } finally {
    iconUploading.value = false
  }
  return false
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
      icon_url: data.icon_url ?? currentModel.value?.icon_url ?? '',
      key_field_codes: data.key_field_codes ?? currentModel.value?.key_field_codes ?? [],
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

.icon-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: 8px;
}

.icon-picker-item {
  width: 44px;
  height: 44px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  color: #595959;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.2s ease;
}

.icon-picker-image {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.icon-picker-item:hover {
  border-color: #40a9ff;
  color: #1677ff;
}

.icon-picker-item-selected {
  border-color: #1677ff;
  background: #e6f4ff;
  color: #1677ff;
}
</style>
