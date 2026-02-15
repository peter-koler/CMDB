<template>
  <div class="relation-trigger-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item label="关键词">
              <a-input
                v-model:value="searchKeyword"
                placeholder="请输入触发器名称"
                allowClear
              />
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
                <a-button type="primary" @click="showModal()">
                  <template #icon><PlusOutlined /></template>
                  新增触发器
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
        :data-source="triggers"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="toggleTrigger(record)">
                {{ record.is_active ? '禁用' : '启用' }}
              </a-button>
              <a-button type="link" size="small" @click="showModal(record)">
                编辑
              </a-button>
              <a-popconfirm
                title="确定删除该触发器吗？"
                @confirm="handleDelete(record.id)"
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

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑触发器' : '新增触发器'"
      width="600px"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
    >
      <a-form :model="form" :rules="rules" ref="formRef" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="源模型" name="source_model_id">
              <a-select v-model:value="form.source_model_id" placeholder="请选择源模型" style="width: 100%">
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标模型" name="target_model_id">
              <a-select v-model:value="form.target_model_id" placeholder="请选择目标模型" style="width: 100%">
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="关系类型" name="relation_type_id">
          <a-select v-model:value="form.relation_type_id" placeholder="请选择关系类型" style="width: 100%">
            <a-select-option v-for="rt in relationTypes" :key="rt.id" :value="rt.id">
              {{ rt.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="源字段" name="source_field">
          <a-input v-model:value="form.source_field" placeholder="请输入源字段编码" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getRelationTriggers, createRelationTrigger, updateRelationTrigger, deleteRelationTrigger, toggleRelationTrigger, getRelationTypes } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const searchKeyword = ref('')
const formRef = ref()

const triggers = ref<any[]>([])
const models = ref<any[]>([])
const relationTypes = ref<any[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '源模型', dataIndex: 'source_model_name', key: 'source_model_name', width: 120 },
  { title: '目标模型', dataIndex: 'target_model_name', key: 'target_model_name', width: 120 },
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name', width: 120 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 100 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 180, fixed: 'right' as const }
]

const form = reactive({
  id: null as number | null,
  name: '',
  source_model_id: null as number | null,
  target_model_id: null as number | null,
  relation_type_id: null as number | null,
  trigger_type: 'reference',
  source_field: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

const fetchTriggers = async () => {
  loading.value = true
  try {
    const res = await getRelationTriggers({
      page: pagination.current,
      per_page: pagination.pageSize,
      keyword: searchKeyword.value
    })
    if (res.code === 200) {
      triggers.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      models.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchRelationTypes = async () => {
  try {
    const res = await getRelationTypes({ per_page: 1000 })
    if (res.code === 200) {
      relationTypes.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const showModal = (record?: any) => {
  isEdit.value = !!record
  if (record) {
    Object.assign(form, {
      id: record.id,
      name: record.name,
      source_model_id: record.source_model_id,
      target_model_id: record.target_model_id,
      relation_type_id: record.relation_type_id,
      trigger_type: record.trigger_type,
      source_field: record.trigger_condition?.source_field || '',
      description: record.description || ''
    })
  } else {
    Object.assign(form, {
      id: null,
      name: '',
      source_model_id: null,
      target_model_id: null,
      relation_type_id: null,
      trigger_type: 'reference',
      source_field: '',
      description: ''
    })
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    let res
    const data = {
      ...form,
      trigger_condition: {
        source_field: form.source_field,
        target_field: 'id'
      }
    }
    if (isEdit.value) {
      res = await updateRelationTrigger(form.id!, data)
    } else {
      res = await createRelationTrigger(data)
    }
    if (res.code === 200) {
      message.success(isEdit.value ? '更新成功' : '创建成功')
      modalVisible.value = false
      fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    const res = await deleteRelationTrigger(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const toggleTrigger = async (record: any) => {
  try {
    const res = await toggleRelationTrigger(record.id)
    if (res.code === 200) {
      message.success(record.is_active ? '已禁用' : '已启用')
      fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchTriggers()
}

const handleReset = () => {
  searchKeyword.value = ''
  pagination.current = 1
  fetchTriggers()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchTriggers()
}

onMounted(() => {
  fetchTriggers()
  fetchModels()
  fetchRelationTypes()
})
</script>

<style scoped>
.relation-trigger-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.search-form {
  width: 100%;
}

.table-card {
  margin-bottom: 16px;
}
</style>
