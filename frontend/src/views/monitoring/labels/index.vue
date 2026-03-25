<template>
  <div class="app-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <a-form layout="inline">
        <a-form-item label="关键字">
          <a-input v-model:value="keyword" placeholder="标签名/标签值" style="width: 220px" />
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="loading" @click="loadLabels">查询</a-button>
            <a-button @click="reset">重置</a-button>
            <a-button v-if="canCreate" type="primary" @click="openModal()">新增标签</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="labels"
        row-key="id"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'color'">
            <a-tag :color="record.color || 'default'">{{ record.color || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
              <a-popconfirm title="确认删除该标签？" @confirm="removeLabel(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
      </a-space>

      <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑标签' : '新增标签'" @ok="saveLabel" :confirm-loading="saving">
        <a-form layout="vertical" :model="formState">
          <a-form-item label="标签名" required>
            <a-input v-model:value="formState.name" />
          </a-form-item>
          <a-form-item label="标签值">
            <a-input v-model:value="formState.value" />
          </a-form-item>
          <a-form-item label="颜色">
            <a-select v-model:value="formState.color" allow-clear placeholder="选择颜色">
              <a-select-option v-for="option in colorOptions" :key="option" :value="option">
                <a-tag :color="option">{{ option }}</a-tag>
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-form>
      </a-modal>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import {
  createMonitoringLabel,
  deleteMonitoringLabel,
  getMonitoringLabels,
  type MonitoringLabel,
  updateMonitoringLabel
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const labels = ref<MonitoringLabel[]>([])
const modalOpen = ref(false)
const editing = ref<MonitoringLabel | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const colorOptions = ['blue', 'green', 'orange', 'red', 'purple', '#13c2c2']

const formState = reactive({
  name: '',
  value: '',
  color: ''
})

const canCreate = computed(() => userStore.hasPermission('monitoring:labels:create') || userStore.hasPermission('monitoring:labels'))
const canEdit = computed(() => userStore.hasPermission('monitoring:labels:edit') || userStore.hasPermission('monitoring:labels'))
const canDelete = computed(() => userStore.hasPermission('monitoring:labels:delete') || userStore.hasPermission('monitoring:labels'))

const columns = [
  { title: '标签名', dataIndex: 'name', key: 'name' },
  { title: '标签值', dataIndex: 'value', key: 'value' },
  { title: '颜色', dataIndex: 'color', key: 'color', width: 140 },
  { title: '关联监控数', dataIndex: 'monitor_count', key: 'monitor_count', width: 130 },
  { title: '操作', key: 'actions', width: 140 }
]

const normalizeList = (payload: any): { items: MonitoringLabel[]; total: number } => {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const loadLabels = async () => {
  loading.value = true
  try {
    const res = await getMonitoringLabels({ q: keyword.value || undefined, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalizeList(res?.data)
    labels.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载标签失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: MonitoringLabel) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.value = record?.value || ''
  formState.color = record?.color || ''
  modalOpen.value = true
}

const saveLabel = async () => {
  if (!formState.name.trim()) {
    message.warning('请输入标签名')
    return
  }
  saving.value = true
  try {
    const payload = { name: formState.name.trim(), value: formState.value.trim(), color: formState.color.trim() || undefined }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateMonitoringLabel(editing.value.id, payload)
    } else {
      await createMonitoringLabel(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    loadLabels()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeLabel = async (record: MonitoringLabel) => {
  try {
    await deleteMonitoringLabel(record.id)
    message.success('删除成功')
    if (labels.value.length === 1 && pagination.current > 1) {
      pagination.current -= 1
    }
    loadLabels()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadLabels()
}

const reset = () => {
  keyword.value = ''
  pagination.current = 1
  loadLabels()
}

onMounted(() => {
  loadLabels()
})
</script>
