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
          <template v-else-if="column.key === 'trigger_rule'">
            <span>
              {{ record.trigger_condition?.source_field || '-' }}
              =
              {{ record.trigger_condition?.target_field || '-' }}
            </span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="toggleTrigger(record)">
                {{ record.is_active ? '禁用' : '启用' }}
              </a-button>
              <a-button type="link" size="small" @click="showModal(record)">
                编辑
              </a-button>
              <a-button type="link" size="small" @click="openLogModal(record)">
                日志
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
              <a-select 
                v-model:value="form.source_model_id" 
                placeholder="请选择源模型" 
                style="width: 100%"
                @change="handleSourceModelChange"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标模型" name="target_model_id">
              <a-select 
                v-model:value="form.target_model_id" 
                placeholder="请选择目标模型" 
                style="width: 100%"
                @change="handleTargetModelChange"
              >
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
          <a-select
            v-model:value="form.source_field"
            placeholder="请选择源字段"
            style="width: 100%"
            :loading="sourceFieldsLoading"
            :disabled="!form.source_model_id"
          >
            <a-select-option v-for="field in sourceModelFields" :key="field.code" :value="field.code">
              {{ field.name }} ({{ field.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标字段" name="target_field">
          <a-select
            v-model:value="form.target_field"
            placeholder="请选择目标字段"
            style="width: 100%"
            :loading="targetFieldsLoading"
            :disabled="!form.target_model_id"
          >
            <a-select-option v-for="field in targetModelFields" :key="field.code" :value="field.code">
              {{ field.name }} ({{ field.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="logVisible"
      title="触发器执行日志"
      width="900px"
      :footer="null"
    >
      <a-table
        :columns="logColumns"
        :data-source="logs"
        :loading="logLoading"
        :pagination="logPagination"
        @change="handleLogTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'success' ? 'green' : record.status === 'failed' ? 'red' : 'default'">
              {{ record.status }}
            </a-tag>
          </template>
        </template>
      </a-table>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getRelationTriggers, createRelationTrigger, updateRelationTrigger, deleteRelationTrigger, toggleRelationTrigger, getRelationTypes } from '@/api/cmdb-relation'
import { getTriggerLogs } from '@/api/trigger'
import { getModels, getModelDetail } from '@/api/cmdb'

interface Field {
  id: number
  code: string
  name: string
  field_type: string
}

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const searchKeyword = ref('')
const formRef = ref()
const logVisible = ref(false)
const logLoading = ref(false)
const sourceFieldsLoading = ref(false)
const targetFieldsLoading = ref(false)

const triggers = ref<any[]>([])
const models = ref<any[]>([])
const relationTypes = ref<any[]>([])
const logs = ref<any[]>([])
const currentTrigger = ref<any>(null)
const sourceModelFields = ref<Field[]>([])
const targetModelFields = ref<Field[]>([])

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
  { title: '匹配规则', key: 'trigger_rule', width: 180 },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 100 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 240, fixed: 'right' as const }
]

const form = reactive({
  id: null as number | null,
  name: '',
  source_model_id: null as number | null,
  target_model_id: null as number | null,
  relation_type_id: null as number | null,
  trigger_type: 'reference',
  source_field: '',
  target_field: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  source_model_id: [{ required: true, message: '请选择源模型', trigger: 'change' }],
  target_model_id: [{ required: true, message: '请选择目标模型', trigger: 'change' }],
  relation_type_id: [{ required: true, message: '请选择关系类型', trigger: 'change' }],
  source_field: [{ required: true, message: '请选择源字段', trigger: 'change' }],
  target_field: [{ required: true, message: '请选择目标字段', trigger: 'change' }]
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

const fetchModelFields = async (modelId: number, isSource: boolean) => {
  if (isSource) {
    sourceFieldsLoading.value = true
  } else {
    targetFieldsLoading.value = true
  }
  try {
    const res = await getModelDetail(modelId)
    if (res.code === 200) {
      let fields = res.data?.fields || []
      if (fields.length === 0 && res.data?.form_config) {
        try {
          const formConfig = typeof res.data.form_config === 'string' 
            ? JSON.parse(res.data.form_config) 
            : res.data.form_config
          fields = formConfig.map((item: any) => ({
            code: item.props?.code,
            name: item.props?.label
          })).filter((f: any) => f.code && f.name)
        } catch (e) {
          console.error('parse form_config error:', e)
        }
      }
      if (isSource) {
        sourceModelFields.value = fields
      } else {
        targetModelFields.value = fields
      }
    }
  } catch (error) {
    console.error('fetchModelFields error:', error)
  } finally {
    if (isSource) {
      sourceFieldsLoading.value = false
    } else {
      targetFieldsLoading.value = false
    }
  }
}

const handleSourceModelChange = (modelId: number) => {
  form.source_field = ''
  sourceModelFields.value = []
  if (modelId) {
    fetchModelFields(modelId, true)
  }
}

const handleTargetModelChange = (modelId: number) => {
  form.target_field = ''
  targetModelFields.value = []
  if (modelId) {
    fetchModelFields(modelId, false)
  }
}

const showModal = async (record?: any) => {
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
      target_field: record.trigger_condition?.target_field || '',
      description: record.description || ''
    })
    sourceModelFields.value = []
    targetModelFields.value = []
    if (record.source_model_id) {
      await fetchModelFields(record.source_model_id, true)
    }
    if (record.target_model_id) {
      await fetchModelFields(record.target_model_id, false)
    }
  } else {
    Object.assign(form, {
      id: null,
      name: '',
      source_model_id: null,
      target_model_id: null,
      relation_type_id: null,
      trigger_type: 'reference',
      source_field: '',
      target_field: '',
      description: ''
    })
    sourceModelFields.value = []
    targetModelFields.value = []
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
    const data = {
      name: form.name,
      source_model_id: form.source_model_id,
      target_model_id: form.target_model_id,
      relation_type_id: form.relation_type_id,
      trigger_type: form.trigger_type,
      description: form.description,
      trigger_condition: {
        source_field: form.source_field,
        target_field: form.target_field
      }
    }
    const res = isEdit.value
      ? await updateRelationTrigger(form.id!, data)
      : await createRelationTrigger(data)
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

const logPagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const logColumns = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '源CI', dataIndex: 'source_ci_name', key: 'source_ci_name', width: 160 },
  { title: '目标CI', dataIndex: 'target_ci_name', key: 'target_ci_name', width: 160 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true }
]

const openLogModal = (record: any) => {
  currentTrigger.value = record
  logPagination.current = 1
  logVisible.value = true
  fetchLogs()
}

const fetchLogs = async () => {
  if (!currentTrigger.value) return
  logLoading.value = true
  try {
    const res = await getTriggerLogs(currentTrigger.value.id, {
      page: logPagination.current,
      page_size: logPagination.pageSize
    })
    const payload = res?.data?.items ? res.data.items : res?.data
    const data = Array.isArray(payload) ? payload : []
    const total = res?.data?.total ?? res?.total ?? data.length
    logs.value = data
    logPagination.total = total
  } catch (error) {
    console.error(error)
  } finally {
    logLoading.value = false
  }
}

const handleLogTableChange = (pag: any) => {
  logPagination.current = pag.current
  logPagination.pageSize = pag.pageSize
  fetchLogs()
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
