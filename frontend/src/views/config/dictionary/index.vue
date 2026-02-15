<template>
  <div class="dict-page">
    <a-row :gutter="16" class="content-row">
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" class="table-card">
          <template #title>字典类型</template>
          <template #extra>
            <a-space>
              <a-tooltip title="新增字典类型">
                <a-button type="text" @click="openTypeModal()">
                  <PlusOutlined />
                </a-button>
              </a-tooltip>
              <a-tooltip title="删除当前字典类型">
                <a-popconfirm
                  title="确认删除当前字典类型？"
                  @confirm="handleDeleteCurrentType"
                  :disabled="!currentType"
                >
                  <a-button type="text" danger :disabled="!currentType">
                    <MinusOutlined />
                  </a-button>
                </a-popconfirm>
              </a-tooltip>
              <a-tooltip title="编辑当前字典类型">
                <a-button type="text" :disabled="!currentType" @click="openTypeModal(currentType)">
                  <EditOutlined />
                </a-button>
              </a-tooltip>
              <a-tooltip title="刷新">
                <a-button type="text" @click="fetchDictTypes">
                  <ReloadOutlined />
                </a-button>
              </a-tooltip>
            </a-space>
          </template>

          <a-spin :spinning="typeLoading">
            <div class="type-list">
              <div
                v-for="item in dictTypes"
                :key="item.id"
                class="type-list-item"
                :class="{ 'type-list-item-active': currentType?.id === item.id }"
                @click="selectType(item)"
              >
                <div class="type-main">
                  <div class="type-name">{{ item.name }}</div>
                  <div class="type-code">{{ item.code }}</div>
                </div>
                <a-tag :color="item.enabled ? 'green' : 'default'">{{ item.enabled ? '启用' : '停用' }}</a-tag>
              </div>
              <a-empty v-if="!dictTypes.length" description="暂无字典类型" />
            </div>
          </a-spin>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="16">
        <a-card :bordered="false" class="table-card">
          <template #title>
            <span>字典项{{ currentType ? `（${currentType.name}）` : '' }}</span>
          </template>
          <template #extra>
            <a-space>
              <a-button type="primary" :disabled="!currentType" @click="openItemModal()">
                <PlusOutlined />
                新增字典项
              </a-button>
            </a-space>
          </template>
          <a-table
            :columns="itemColumns"
            :data-source="dictItems"
            :loading="itemLoading"
            row-key="id"
            size="small"
            :pagination="false"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'enabled'">
                <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="openItemModal(record)">编辑</a-button>
                  <a-popconfirm title="确认删除该字典项（包含子项）？" @confirm="handleDeleteItem(record)">
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <a-modal
      v-model:open="typeModalVisible"
      :title="typeForm.id ? '编辑字典类型' : '新增字典类型'"
      @ok="handleSubmitType"
      :confirm-loading="typeSubmitting"
      width="520px"
    >
      <a-form ref="typeFormRef" :model="typeForm" :rules="typeRules" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
        <a-form-item label="编码" name="code">
          <a-input v-model:value="typeForm.code" placeholder="例如: model_type" />
        </a-form-item>
        <a-form-item label="名称" name="name">
          <a-input v-model:value="typeForm.name" placeholder="例如: 模型类型" />
        </a-form-item>
        <a-form-item label="状态" name="enabled">
          <a-switch v-model:checked="typeForm.enabled" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="typeForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="typeForm.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="itemModalVisible"
      :title="itemForm.id ? '编辑字典项' : '新增字典项'"
      @ok="handleSubmitItem"
      :confirm-loading="itemSubmitting"
      width="520px"
    >
      <a-form ref="itemFormRef" :model="itemForm" :rules="itemRules" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
        <a-form-item label="父级" name="parent_id">
          <a-tree-select
            v-model:value="itemForm.parent_id"
            :tree-data="parentTreeOptions"
            :field-names="{ label: 'label', value: 'id', children: 'children' }"
            placeholder="不选则为顶级"
            allowClear
            tree-default-expand-all
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="编码" name="code">
          <a-input v-model:value="itemForm.code" placeholder="例如: host" />
        </a-form-item>
        <a-form-item label="显示名" name="label">
          <a-input v-model:value="itemForm.label" placeholder="例如: 主机" />
        </a-form-item>
        <a-form-item label="状态" name="enabled">
          <a-switch v-model:checked="itemForm.enabled" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="itemForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { EditOutlined, MinusOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import {
  createDictItem,
  createDictType,
  deleteDictItem,
  deleteDictType,
  getDictItems,
  getDictTypes,
  updateDictItem,
  updateDictType
} from '@/api/cmdb'

const typeLoading = ref(false)
const itemLoading = ref(false)
const typeSubmitting = ref(false)
const itemSubmitting = ref(false)
const dictTypes = ref<any[]>([])
const dictItems = ref<any[]>([])
const currentType = ref<any>(null)

const typeModalVisible = ref(false)
const itemModalVisible = ref(false)
const typeFormRef = ref()
const itemFormRef = ref()

const typeForm = reactive({
  id: null as number | null,
  code: '',
  name: '',
  enabled: true,
  sort_order: 0,
  description: ''
})

const itemForm = reactive({
  id: null as number | null,
  parent_id: undefined as number | undefined,
  code: '',
  label: '',
  enabled: true,
  sort_order: 0
})

const typeRules = {
  code: [{ required: true, message: '请输入字典编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }]
}

const itemRules = {
  code: [{ required: true, message: '请输入字典项编码', trigger: 'blur' }],
  label: [{ required: true, message: '请输入字典项显示名', trigger: 'blur' }]
}

const itemColumns = [
  { title: '显示名', dataIndex: 'label', key: 'label', width: 170 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 150 },
  { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 80 },
  { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
  { title: '操作', key: 'action', width: 140 }
]

const parentTreeOptions = computed(() => {
  if (!itemForm.id) return dictItems.value
  return removeNodeAndDescendants(dictItems.value, itemForm.id)
})

const removeNodeAndDescendants = (nodes: any[], excludeId: number): any[] => {
  const result: any[] = []
  nodes.forEach((node) => {
    if (node.id === excludeId) return
    const children = removeNodeAndDescendants(node.children || [], excludeId)
    result.push({ ...node, children })
  })
  return result
}

const fetchDictTypes = async () => {
  typeLoading.value = true
  try {
    const res = await getDictTypes()
    if (res.code === 200) {
      dictTypes.value = res.data || []
      if (dictTypes.value.length === 0) {
        currentType.value = null
        dictItems.value = []
        return
      }

      const selected = currentType.value
        ? dictTypes.value.find((item: any) => item.id === currentType.value.id)
        : null
      currentType.value = selected || dictTypes.value[0]
      fetchDictItems(currentType.value.id)
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '获取字典类型失败')
  } finally {
    typeLoading.value = false
  }
}

const fetchDictItems = async (typeId: number) => {
  itemLoading.value = true
  try {
    const res = await getDictItems(typeId)
    if (res.code === 200) {
      dictItems.value = res.data?.items || []
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '获取字典项失败')
  } finally {
    itemLoading.value = false
  }
}

const selectType = (record: any) => {
  currentType.value = record
  fetchDictItems(record.id)
}

const openTypeModal = (record?: any) => {
  if (record) {
    Object.assign(typeForm, {
      id: record.id,
      code: record.code,
      name: record.name,
      enabled: record.enabled,
      sort_order: record.sort_order || 0,
      description: record.description || ''
    })
  } else {
    Object.assign(typeForm, {
      id: null,
      code: '',
      name: '',
      enabled: true,
      sort_order: 0,
      description: ''
    })
  }
  typeModalVisible.value = true
}

const handleSubmitType = async () => {
  try {
    await typeFormRef.value?.validate()
    typeSubmitting.value = true
    const payload = {
      code: typeForm.code,
      name: typeForm.name,
      enabled: typeForm.enabled,
      sort_order: typeForm.sort_order,
      description: typeForm.description
    }
    if (typeForm.id) {
      await updateDictType(typeForm.id, payload)
      message.success('更新成功')
    } else {
      await createDictType(payload)
      message.success('创建成功')
    }
    typeModalVisible.value = false
    fetchDictTypes()
  } catch (error: any) {
    if (error?.errorFields) return
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    typeSubmitting.value = false
  }
}

const handleDeleteType = async (record: any) => {
  try {
    await deleteDictType(record.id)
    message.success('删除成功')
    fetchDictTypes()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const handleDeleteCurrentType = async () => {
  if (!currentType.value) return
  await handleDeleteType(currentType.value)
}

const openItemModal = (record?: any) => {
  if (!currentType.value) {
    message.warning('请先选择字典类型')
    return
  }
  if (record) {
    Object.assign(itemForm, {
      id: record.id,
      parent_id: record.parent_id || undefined,
      code: record.code,
      label: record.label,
      enabled: record.enabled,
      sort_order: record.sort_order || 0
    })
  } else {
    Object.assign(itemForm, {
      id: null,
      parent_id: undefined,
      code: '',
      label: '',
      enabled: true,
      sort_order: 0
    })
  }
  itemModalVisible.value = true
}

const handleSubmitItem = async () => {
  if (!currentType.value) {
    message.warning('请先选择字典类型')
    return
  }
  try {
    await itemFormRef.value?.validate()
    itemSubmitting.value = true
    const payload = {
      parent_id: itemForm.parent_id,
      code: itemForm.code,
      label: itemForm.label,
      enabled: itemForm.enabled,
      sort_order: itemForm.sort_order
    }
    if (itemForm.id) {
      await updateDictItem(itemForm.id, payload)
      message.success('更新成功')
    } else {
      await createDictItem(currentType.value.id, payload)
      message.success('创建成功')
    }
    itemModalVisible.value = false
    fetchDictItems(currentType.value.id)
  } catch (error: any) {
    if (error?.errorFields) return
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    itemSubmitting.value = false
  }
}

const handleDeleteItem = async (record: any) => {
  try {
    await deleteDictItem(record.id)
    message.success('删除成功')
    if (currentType.value) {
      fetchDictItems(currentType.value.id)
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

onMounted(() => {
  fetchDictTypes()
})
</script>

<style scoped>
.dict-page {
  height: 100%;
}

.content-row {
  height: 100%;
  min-height: 620px;
}

.table-card {
  height: 100%;
}

.table-card :deep(.ant-card-body) {
  padding: 16px;
  height: calc(100% - 56px);
  overflow: auto;
}

.type-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-list-item:hover {
  border-color: #91caff;
  background: #f6fbff;
}

.type-list-item-active {
  border-color: #1677ff;
  background: #e6f4ff;
}

.type-main {
  min-width: 0;
}

.type-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
}

.type-code {
  margin-top: 2px;
  font-size: 12px;
  color: #8c8c8c;
}

@media (max-width: 768px) {
  .content-row {
    min-height: auto;
  }
}
</style>
