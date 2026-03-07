<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-space>
        <a-input v-model:value="keyword" placeholder="静默名称" style="width: 220px" />
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'enabled'">
            <a-tag :color="record.enabled ? 'green' : 'default'">{{ record.enabled ? '启用' : '停用' }}</a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
              <a-popconfirm title="确认删除？" @confirm="removeItem(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警静默' : '新增告警静默'" :confirm-loading="saving" width="700px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-form-item label="名称" required><a-input v-model:value="formState.name" /></a-form-item>
        <a-form-item label="匹配规则"><a-input v-model:value="formState.matcher" placeholder="如 env=prod" /></a-form-item>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="开始时间(RFC3339)" required><a-input v-model:value="formState.start_at" placeholder="2026-03-07T00:00:00Z" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="结束时间(RFC3339)" required><a-input v-model:value="formState.end_at" placeholder="2026-03-07T23:59:59Z" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="原因"><a-input v-model:value="formState.reason" placeholder="维护窗口" /></a-form-item>
        <a-form-item label="启用"><a-switch v-model:checked="formState.enabled" /></a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { createAlertSilence, deleteAlertSilence, getAlertSilences, type AlertSilence, updateAlertSilence } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const items = ref<AlertSilence[]>([])
const modalOpen = ref(false)
const editing = ref<AlertSilence | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({ name: '', matcher: '', start_at: '', end_at: '', reason: '', enabled: true })

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:silence:create') || userStore.hasPermission('monitoring:alert:silence'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:silence:edit') || userStore.hasPermission('monitoring:alert:silence'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:silence:delete') || userStore.hasPermission('monitoring:alert:silence'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '匹配规则', dataIndex: 'matcher', key: 'matcher' },
  { title: '开始时间', dataIndex: 'start_at', key: 'start_at', width: 180 },
  { title: '结束时间', dataIndex: 'end_at', key: 'end_at', width: 180 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', width: 120 }
]

const normalize = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertSilences({ q: keyword.value || undefined, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalize(res?.data)
    items.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: AlertSilence) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.matcher = record?.matcher || ''
  formState.start_at = record?.start_at || ''
  formState.end_at = record?.end_at || ''
  formState.reason = (record as any)?.reason || ''
  formState.enabled = record?.enabled !== false
  modalOpen.value = true
}

const validateWindow = () => {
  if (!formState.start_at.trim() || !formState.end_at.trim()) throw new Error('请填写开始/结束时间')
  const start = dayjs(formState.start_at)
  const end = dayjs(formState.end_at)
  if (!start.isValid() || !end.isValid()) throw new Error('时间格式不合法，请使用 RFC3339')
  if (end.valueOf() <= start.valueOf()) throw new Error('结束时间必须晚于开始时间')
}

const saveItem = async () => {
  if (!formState.name.trim()) return message.warning('请输入名称')
  saving.value = true
  try {
    validateWindow()
    const payload = {
      name: formState.name.trim(),
      matcher: formState.matcher.trim() || undefined,
      start_at: formState.start_at.trim(),
      end_at: formState.end_at.trim(),
      reason: formState.reason.trim() || undefined,
      enabled: formState.enabled
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateAlertSilence(editing.value.id, payload)
    } else {
      await createAlertSilence(payload)
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

const removeItem = async (record: AlertSilence) => {
  await deleteAlertSilence(record.id)
  message.success('删除成功')
  loadData()
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

const reset = () => {
  keyword.value = ''
  pagination.current = 1
  loadData()
}

onMounted(loadData)
</script>
