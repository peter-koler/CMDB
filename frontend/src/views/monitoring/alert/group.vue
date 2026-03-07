<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-space>
        <a-input v-model:value="keyword" placeholder="分组名称" style="width: 220px" />
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警分组' : '新增告警分组'" :confirm-loading="saving" width="680px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-form-item label="名称" required><a-input v-model:value="formState.name" /></a-form-item>
        <a-form-item label="匹配规则"><a-input v-model:value="formState.matcher" placeholder="如 env=prod,app=mysql" /></a-form-item>
        <a-form-item label="通知目标(Notice IDs)"><a-input v-model:value="formState.notice_ids" placeholder="逗号分隔，如 1,2" /></a-form-item>
        <a-form-item label="启用"><a-switch v-model:checked="formState.enabled" /></a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { createAlertGroup, deleteAlertGroup, getAlertGroups, type AlertGroup, updateAlertGroup } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const items = ref<AlertGroup[]>([])
const modalOpen = ref(false)
const editing = ref<AlertGroup | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({ name: '', matcher: '', notice_ids: '', enabled: true })

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:group:create') || userStore.hasPermission('monitoring:alert:group'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:group:edit') || userStore.hasPermission('monitoring:alert:group'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:group:delete') || userStore.hasPermission('monitoring:alert:group'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '匹配规则', dataIndex: 'matcher', key: 'matcher' },
  { title: '通知目标', dataIndex: 'notice_ids', key: 'notice_ids' },
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
    const res = await getAlertGroups({ q: keyword.value || undefined, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalize(res?.data)
    items.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: AlertGroup) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.matcher = record?.matcher || ''
  const noticeIds = (record as any)?.notice_ids
  formState.notice_ids = Array.isArray(noticeIds) ? noticeIds.join(',') : (noticeIds || '')
  formState.enabled = record?.enabled !== false
  modalOpen.value = true
}

const saveItem = async () => {
  if (!formState.name.trim()) return message.warning('请输入名称')
  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      matcher: formState.matcher.trim() || undefined,
      notice_ids: formState.notice_ids.split(',').map((x) => x.trim()).filter(Boolean),
      enabled: formState.enabled
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateAlertGroup(editing.value.id, payload)
    } else {
      await createAlertGroup(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const removeItem = async (record: AlertGroup) => {
  await deleteAlertGroup(record.id)
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
