<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-space>
        <a-input v-model:value="keyword" placeholder="集成名称/类型" style="width: 220px" />
        <a-select v-model:value="typeFilter" allow-clear placeholder="全部类型" style="width: 160px">
          <a-select-option value="prometheus">prometheus</a-select-option>
          <a-select-option value="zabbix">zabbix</a-select-option>
          <a-select-option value="nagios">nagios</a-select-option>
          <a-select-option value="custom">custom</a-select-option>
        </a-select>
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="items"
        row-key="id"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'enabled' ? 'green' : 'default'">{{ record.status || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
              <a-button type="link" size="small" :disabled="!canTest" @click="testItem(record)">测试</a-button>
              <a-popconfirm title="确认删除？" @confirm="removeItem(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <a-modal
      v-model:open="modalOpen"
      :title="editing?.id ? '编辑告警集成' : '新增告警集成'"
      :confirm-loading="saving"
      width="720px"
      @ok="saveItem"
    >
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="名称" required>
              <a-input v-model:value="formState.name" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="类型" required>
              <a-select v-model:value="formState.type">
                <a-select-option value="prometheus">prometheus</a-select-option>
                <a-select-option value="zabbix">zabbix</a-select-option>
                <a-select-option value="nagios">nagios</a-select-option>
                <a-select-option value="custom">custom</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="接收URL" required>
          <a-input v-model:value="formState.endpoint" placeholder="https://.../webhook" />
        </a-form-item>

        <a-form-item label="标签映射(JSON)">
          <a-textarea v-model:value="formState.label_mapping" :rows="4" placeholder='{"severity":"level","instance":"host"}' />
        </a-form-item>

        <a-form-item label="格式转换模板(JSON)">
          <a-textarea v-model:value="formState.format_template" :rows="4" placeholder='{"name":"{{ alertname }}","level":"{{ severity }}"}' />
        </a-form-item>

        <a-form-item label="状态">
          <a-select v-model:value="formState.status">
            <a-select-option value="enabled">enabled</a-select-option>
            <a-select-option value="disabled">disabled</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  createAlertIntegration,
  deleteAlertIntegration,
  getAlertIntegrations,
  testAlertIntegration,
  type AlertIntegration,
  updateAlertIntegration
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const typeFilter = ref<string | undefined>(undefined)
const items = ref<AlertIntegration[]>([])
const modalOpen = ref(false)
const editing = ref<AlertIntegration | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const formState = reactive({
  name: '',
  type: 'prometheus',
  endpoint: '',
  label_mapping: '',
  format_template: '',
  status: 'enabled'
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:integration:create') || userStore.hasPermission('monitoring:alert:integration'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:integration:edit') || userStore.hasPermission('monitoring:alert:integration'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:integration:delete') || userStore.hasPermission('monitoring:alert:integration'))
const canTest = computed(() => userStore.hasPermission('monitoring:alert:integration:test') || userStore.hasPermission('monitoring:alert:integration'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type', width: 140 },
  { title: '接收URL', dataIndex: 'endpoint', key: 'endpoint' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
  { title: '操作', key: 'actions', width: 160 }
]

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const parseJsonMaybe = (value: string, label: string) => {
  const text = value.trim()
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`${label} 不是合法 JSON`)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertIntegrations({
      q: keyword.value || undefined,
      type: typeFilter.value,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    const parsed = normalizeList(res?.data)
    items.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: AlertIntegration) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.type = record?.type || 'prometheus'
  formState.endpoint = record?.endpoint || ''
  formState.status = record?.status || 'enabled'
  formState.label_mapping = JSON.stringify((record as any)?.label_mapping || {}, null, 2)
  formState.format_template = JSON.stringify((record as any)?.format_template || {}, null, 2)
  modalOpen.value = true
}

const saveItem = async () => {
  if (!formState.name.trim() || !formState.type.trim() || !formState.endpoint.trim()) {
    return message.warning('请填写完整必填字段')
  }
  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      type: formState.type.trim(),
      endpoint: formState.endpoint.trim(),
      status: formState.status,
      label_mapping: parseJsonMaybe(formState.label_mapping, '标签映射'),
      format_template: parseJsonMaybe(formState.format_template, '格式转换模板')
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateAlertIntegration(editing.value.id, payload)
    } else {
      await createAlertIntegration(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    loadData()
  } catch (error: any) {
    message.error(error?.message || error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeItem = async (record: AlertIntegration) => {
  await deleteAlertIntegration(record.id)
  message.success('删除成功')
  loadData()
}

const testItem = async (record: AlertIntegration) => {
  await testAlertIntegration(record.id)
  message.success('测试发送成功')
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

const reset = () => {
  keyword.value = ''
  typeFilter.value = undefined
  pagination.current = 1
  loadData()
}

onMounted(loadData)
</script>
