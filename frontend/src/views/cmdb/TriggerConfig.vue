<template>
  <div class="trigger-config-page">
    <a-row :gutter="16">
      <a-col :xs="24" :sm="8">
        <a-card :bordered="false" title="选择模型">
          <a-form layout="vertical">
            <a-form-item label="选择模型">
              <a-select
                v-model:value="selectedModelId"
                placeholder="请选择模型"
                style="width: 100%"
                @change="handleModelChange"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="16">
        <a-card :bordered="false" title="Cron 表达式示例">
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="每天凌晨2点">0 2 * * *</a-descriptions-item>
            <a-descriptions-item label="每天早上6点">0 6 * * *</a-descriptions-item>
            <a-descriptions-item label="每周日凌晨3点">0 3 * * 0</a-descriptions-item>
            <a-descriptions-item label="每月1日凌晨4点">0 4 1 * *</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>

    <template v-if="selectedModelId">
      <a-card :bordered="false" class="config-card">
        <template #title>
          <a-space>
            <span>触发器规则</span>
            <a-badge :count="triggers.length" :number-style="{ backgroundColor: '#52c41a' }" />
          </a-space>
        </template>
        <template #extra>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            新建触发器
          </a-button>
        </template>

        <a-table
          :columns="triggerColumns"
          :data-source="triggers"
          :loading="triggerLoading"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'is_active'">
              <a-switch
                :checked="record.is_active"
                size="small"
                @change="(checked: boolean) => handleToggleTrigger(record, checked)"
              />
            </template>
            <template v-else-if="column.key === 'trigger_condition'">
              <a-tooltip :title="JSON.stringify(record.trigger_condition)">
                <span class="condition-text">
                  {{ record.trigger_condition?.source_field }} = {{ record.trigger_condition?.target_field }}
                </span>
              </a-tooltip>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="showEditModal(record)">编辑</a-button>
                <a-button type="link" size="small" @click="showLogsModal(record)">日志</a-button>
                <a-popconfirm
                  title="确定删除此触发器？"
                  @confirm="handleDeleteTrigger(record)"
                >
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-card>

      <a-card :bordered="false" class="config-card">
        <template #title>
          <a-space>
            <span>批量扫描配置</span>
            <a-tag v-if="config.batch_scan_enabled" color="green">已启用</a-tag>
            <a-tag v-else color="default">已禁用</a-tag>
          </a-space>
        </template>
        <a-form :model="form" :rules="rules" ref="formRef" layout="vertical">
          <a-row :gutter="16">
            <a-col :xs="24" :sm="8">
              <a-form-item label="启用批量扫描" name="batch_scan_enabled">
                <a-switch v-model:checked="form.batch_scan_enabled" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="8">
              <a-form-item label="Cron 表达式" name="batch_scan_cron">
                <a-input
                  v-model:value="form.batch_scan_cron"
                  placeholder="如: 0 2 * * *"
                  :disabled="!form.batch_scan_enabled"
                />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :sm="8">
              <a-form-item label="操作">
                <a-space>
                  <a-button type="primary" @click="handleSubmit" :loading="submitLoading">
                    保存配置
                  </a-button>
                  <a-button @click="handleTestScan" :loading="scanLoading">
                    立即执行
                  </a-button>
                </a-space>
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="16">
            <a-col :xs="24" :sm="12">
              <a-statistic title="下次执行时间" :value="config.next_run_at || '-'" :value-style="{ fontSize: '16px' }" />
            </a-col>
            <a-col :xs="24" :sm="12">
              <a-space direction="vertical" :size="0">
                <span>上次执行: {{ config.last_run_at || '-' }}</span>
                <span>状态:
                  <a-tag v-if="config.last_run_status === 'completed'" color="green">成功</a-tag>
                  <a-tag v-else-if="config.last_run_status === 'failed'" color="error">失败</a-tag>
                  <a-tag v-else-if="config.last_run_status === 'running'" color="processing">运行中</a-tag>
                  <span v-else>-</span>
                </span>
              </a-space>
            </a-col>
          </a-row>
        </a-form>
      </a-card>
    </template>

    <a-modal
      v-model:open="triggerModalVisible"
      :title="isEdit ? '编辑触发器' : '新建触发器'"
      width="600px"
      @ok="handleTriggerSubmit"
      :confirm-loading="triggerSubmitLoading"
    >
      <a-form :model="triggerForm" :rules="triggerRules" ref="triggerFormRef" layout="vertical">
        <a-form-item label="触发器名称" name="name">
          <a-input v-model:value="triggerForm.name" placeholder="请输入触发器名称" />
        </a-form-item>
        <a-form-item label="目标模型" name="target_model_id">
          <a-select
            v-model:value="triggerForm.target_model_id"
            placeholder="请选择目标模型"
            @change="handleTargetModelChange"
          >
            <a-select-option v-for="model in models" :key="model.id" :value="model.id">
              {{ model.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="关系类型" name="relation_type_id">
          <a-select v-model:value="triggerForm.relation_type_id" placeholder="请选择关系类型">
            <a-select-option v-for="rt in relationTypes" :key="rt.id" :value="rt.id">
              {{ rt.name }} ({{ rt.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="触发条件" required>
          <a-row :gutter="8">
            <a-col :span="11">
              <a-form-item name="source_field" no-style>
                <a-select
                  v-model:value="triggerForm.source_field"
                  placeholder="选择源字段"
                  :loading="sourceFieldsLoading"
                >
                  <a-select-option v-for="field in sourceModelFields" :key="field.code" :value="field.code">
                    {{ field.name }} ({{ field.code }})
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="2" style="text-align: center; line-height: 32px;">=</a-col>
            <a-col :span="11">
              <a-form-item name="target_field" no-style>
                <a-select
                  v-model:value="triggerForm.target_field"
                  placeholder="选择目标字段"
                  :loading="targetFieldsLoading"
                  :disabled="!triggerForm.target_model_id"
                >
                  <a-select-option v-for="field in targetModelFields" :key="field.code" :value="field.code">
                    {{ field.name }} ({{ field.code }})
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="triggerForm.description" placeholder="请输入描述" :rows="2" />
        </a-form-item>
        <a-form-item label="启用状态" name="is_active">
          <a-switch v-model:checked="triggerForm.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="logsModalVisible"
      :title="`执行日志 - ${currentTrigger?.name || ''}`"
      width="800px"
      :footer="null"
    >
      <a-table
        :columns="logColumns"
        :data-source="logs"
        :loading="logsLoading"
        :pagination="logsPagination"
        row-key="id"
        size="small"
        @change="handleLogsTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag v-if="record.status === 'success'" color="green">成功</a-tag>
            <a-tag v-else-if="record.status === 'failed'" color="error">失败</a-tag>
            <a-tag v-else-if="record.status === 'skipped'" color="warning">跳过</a-tag>
          </template>
        </template>
      </a-table>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import {
  getModelTriggers,
  createTrigger,
  updateTrigger,
  deleteTrigger,
  getTriggerLogs,
  getBatchScanConfig,
  updateBatchScanConfig,
  triggerBatchScan
} from '@/api/trigger'
import { getModels, getModelDetail } from '@/api/cmdb'
import { getRelationTypes } from '@/api/cmdb-relation'

interface Field {
  id: number
  code: string
  name: string
  field_type: string
}

interface Trigger {
  id: number
  name: string
  source_model_id: number
  source_model_name: string
  target_model_id: number
  target_model_name: string
  relation_type_id: number
  relation_type_name: string
  trigger_condition: { source_field: string; target_field: string }
  is_active: boolean
  description: string
}

const selectedModelId = ref<number | null>(null)
const submitLoading = ref(false)
const scanLoading = ref(false)
const triggerLoading = ref(false)
const triggerSubmitLoading = ref(false)
const logsLoading = ref(false)
const sourceFieldsLoading = ref(false)
const targetFieldsLoading = ref(false)
const formRef = ref()
const triggerFormRef = ref()

const models = ref<any[]>([])
const triggers = ref<Trigger[]>([])
const relationTypes = ref<any[]>([])
const logs = ref<any[]>([])
const currentTrigger = ref<Trigger | null>(null)
const sourceModelFields = ref<Field[]>([])
const targetModelFields = ref<Field[]>([])

const triggerModalVisible = ref(false)
const logsModalVisible = ref(false)
const isEdit = ref(false)

const config = reactive<any>({
  batch_scan_enabled: false,
  batch_scan_cron: '',
  next_run_at: null,
  last_run_at: null,
  last_run_status: null
})

const form = reactive({
  batch_scan_enabled: false,
  batch_scan_cron: ''
})

const triggerForm = reactive({
  id: 0,
  name: '',
  target_model_id: undefined as number | undefined,
  relation_type_id: undefined as number | undefined,
  source_field: '',
  target_field: '',
  description: '',
  is_active: true
})

const rules = {
  batch_scan_cron: [
    { pattern: /^(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)$/, message: '格式错误，例: 0 2 * * *', trigger: 'blur' }
  ]
}

const triggerRules = {
  name: [{ required: true, message: '请输入触发器名称', trigger: 'blur' }],
  target_model_id: [{ required: true, message: '请选择目标模型', trigger: 'change' }],
  relation_type_id: [{ required: true, message: '请选择关系类型', trigger: 'change' }],
  source_field: [{ required: true, message: '请选择源字段', trigger: 'change' }],
  target_field: [{ required: true, message: '请选择目标字段', trigger: 'change' }]
}

const triggerColumns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '目标模型', dataIndex: 'target_model_name', key: 'target_model_name' },
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name' },
  { title: '匹配条件', key: 'trigger_condition' },
  { title: '启用', dataIndex: 'is_active', key: 'is_active', width: 80 },
  { title: '操作', key: 'action', width: 180 }
]

const logColumns = [
  { title: '源 CI', dataIndex: 'source_ci_name', key: 'source_ci_name' },
  { title: '目标 CI', dataIndex: 'target_ci_name', key: 'target_ci_name' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
  { title: '消息', dataIndex: 'message', key: 'message' },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 }
]

const logsPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      models.value = res.data.items || res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchRelationTypes = async () => {
  try {
    const res = await getRelationTypes({})
    if (res.code === 200) {
      relationTypes.value = res.data.items || res.data
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
      const fields = res.data.fields || []
      if (isSource) {
        sourceModelFields.value = fields
      } else {
        targetModelFields.value = fields
      }
    }
  } catch (error) {
    console.error(error)
  } finally {
    if (isSource) {
      sourceFieldsLoading.value = false
    } else {
      targetFieldsLoading.value = false
    }
  }
}

const fetchTriggers = async () => {
  if (!selectedModelId.value) return
  triggerLoading.value = true
  try {
    const res = await getModelTriggers(selectedModelId.value)
    if (res.code === 200) {
      triggers.value = res.data.data || []
    }
  } catch (error) {
    console.error(error)
  } finally {
    triggerLoading.value = false
  }
}

const fetchConfig = async () => {
  if (!selectedModelId.value) return
  try {
    const res = await getBatchScanConfig(selectedModelId.value)
    if (res.code === 200) {
      Object.assign(config, res.data)
      form.batch_scan_enabled = res.data.batch_scan_enabled
      form.batch_scan_cron = res.data.batch_scan_cron || ''
    }
  } catch (error) {
    console.error(error)
  }
}

const handleModelChange = () => {
  fetchTriggers()
  fetchConfig()
  if (selectedModelId.value) {
    fetchModelFields(selectedModelId.value, true)
  }
}

const handleTargetModelChange = (modelId: number) => {
  triggerForm.target_field = ''
  targetModelFields.value = []
  if (modelId) {
    fetchModelFields(modelId, false)
  }
}

const showCreateModal = () => {
  isEdit.value = false
  Object.assign(triggerForm, {
    id: 0,
    name: '',
    target_model_id: undefined,
    relation_type_id: undefined,
    source_field: '',
    target_field: '',
    description: '',
    is_active: true
  })
  targetModelFields.value = []
  triggerModalVisible.value = true
}

const showEditModal = async (record: Trigger) => {
  isEdit.value = true
  Object.assign(triggerForm, {
    id: record.id,
    name: record.name,
    target_model_id: record.target_model_id,
    relation_type_id: record.relation_type_id,
    source_field: record.trigger_condition?.source_field || '',
    target_field: record.trigger_condition?.target_field || '',
    description: record.description || '',
    is_active: record.is_active
  })
  if (record.target_model_id) {
    await fetchModelFields(record.target_model_id, false)
  }
  triggerModalVisible.value = true
}

const handleTriggerSubmit = async () => {
  try {
    await triggerFormRef.value.validate()
  } catch {
    return
  }

  triggerSubmitLoading.value = true
  try {
    const data = {
      name: triggerForm.name,
      target_model_id: triggerForm.target_model_id,
      relation_type_id: triggerForm.relation_type_id,
      trigger_condition: {
        source_field: triggerForm.source_field,
        target_field: triggerForm.target_field
      },
      description: triggerForm.description,
      is_active: triggerForm.is_active
    }

    if (isEdit.value) {
      await updateTrigger(triggerForm.id, data)
      message.success('更新成功')
    } else {
      await createTrigger(selectedModelId.value!, data)
      message.success('创建成功')
    }
    triggerModalVisible.value = false
    fetchTriggers()
  } catch (error: any) {
    message.error(error.response?.data?.error || '操作失败')
  } finally {
    triggerSubmitLoading.value = false
  }
}

const handleToggleTrigger = async (record: Trigger, checked: boolean) => {
  try {
    await updateTrigger(record.id, { is_active: checked })
    message.success('状态更新成功')
    fetchTriggers()
  } catch (error: any) {
    message.error(error.response?.data?.error || '操作失败')
  }
}

const handleDeleteTrigger = async (record: Trigger) => {
  try {
    await deleteTrigger(record.id)
    message.success('删除成功')
    fetchTriggers()
  } catch (error: any) {
    message.error(error.response?.data?.error || '删除失败')
  }
}

const showLogsModal = async (record: Trigger) => {
  currentTrigger.value = record
  logsPagination.current = 1
  logsModalVisible.value = true
  await fetchLogs()
}

const fetchLogs = async () => {
  if (!currentTrigger.value) return
  logsLoading.value = true
  try {
    const res = await getTriggerLogs(currentTrigger.value.id, {
      page: logsPagination.current,
      page_size: logsPagination.pageSize
    })
    if (res.code === 200) {
      logs.value = res.data.data || []
      logsPagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    logsLoading.value = false
  }
}

const handleLogsTableChange = (pag: any) => {
  logsPagination.current = pag.current
  fetchLogs()
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    const res = await updateBatchScanConfig(selectedModelId.value!, {
      batch_scan_enabled: form.batch_scan_enabled,
      batch_scan_cron: form.batch_scan_cron
    })
    if (res.code === 200) {
      message.success('配置保存成功')
      Object.assign(config, res.data)
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '保存失败')
  } finally {
    submitLoading.value = false
  }
}

const handleTestScan = async () => {
  scanLoading.value = true
  try {
    const res = await triggerBatchScan(selectedModelId.value!)
    if (res.code === 202 || res.code === 200) {
      message.success('已触发批量扫描任务')
      setTimeout(() => fetchConfig(), 2000)
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '触发失败')
  } finally {
    scanLoading.value = false
  }
}

onMounted(() => {
  fetchModels()
  fetchRelationTypes()
})
</script>

<style scoped>
.trigger-config-page {
  padding: 16px;
}

.config-card {
  margin-top: 16px;
}

.condition-text {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
