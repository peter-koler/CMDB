<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-space>
        <a-input v-model:value="keyword" placeholder="抑制规则名称" style="width: 220px" />
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警抑制' : '新增告警抑制'" :confirm-loading="saving" width="700px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-form-item label="名称" required><a-input v-model:value="formState.name" /></a-form-item>
        <a-form-item label="源匹配规则"><a-input v-model:value="formState.source_matcher" placeholder="如 severity=critical" /></a-form-item>
        <a-form-item label="目标匹配规则"><a-input v-model:value="formState.target_matcher" placeholder="如 alertname=cpu_high" /></a-form-item>
        <a-form-item label="相等标签"><a-input v-model:value="formState.equal_labels" placeholder="逗号分隔，如 cluster,instance" /></a-form-item>
        <a-form-item label="启用"><a-switch v-model:checked="formState.enabled" /></a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { createAlertInhibit, deleteAlertInhibit, getAlertInhibits, type AlertInhibit, updateAlertInhibit } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const items = ref<AlertInhibit[]>([])
const modalOpen = ref(false)
const editing = ref<AlertInhibit | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({ name: '', source_matcher: '', target_matcher: '', equal_labels: '', enabled: true })

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:inhibit:create') || userStore.hasPermission('monitoring:alert:inhibit'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:inhibit:edit') || userStore.hasPermission('monitoring:alert:inhibit'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:inhibit:delete') || userStore.hasPermission('monitoring:alert:inhibit'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '源匹配', dataIndex: 'source_matcher', key: 'source_matcher' },
  { title: '目标匹配', dataIndex: 'target_matcher', key: 'target_matcher' },
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
    const res = await getAlertInhibits({ q: keyword.value || undefined, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalize(res?.data)
    items.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: AlertInhibit) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.source_matcher = record?.source_matcher || ''
  formState.target_matcher = record?.target_matcher || ''
  const labels = (record as any)?.equal_labels
  formState.equal_labels = Array.isArray(labels) ? labels.join(',') : (labels || '')
  formState.enabled = record?.enabled !== false
  modalOpen.value = true
}

const saveItem = async () => {
  if (!formState.name.trim()) return message.warning('请输入名称')
  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      source_matcher: formState.source_matcher.trim() || undefined,
      target_matcher: formState.target_matcher.trim() || undefined,
      equal_labels: formState.equal_labels.split(',').map((x) => x.trim()).filter(Boolean),
      enabled: formState.enabled
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateAlertInhibit(editing.value.id, payload)
    } else {
      await createAlertInhibit(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

const removeItem = async (record: AlertInhibit) => {
  await deleteAlertInhibit(record.id)
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
