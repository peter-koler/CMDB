<template>
  <div class="app-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <a-form layout="inline">
        <a-form-item label="关键字">
          <a-input v-model:value="keyword" placeholder="状态页名称/slug" style="width: 240px" />
        </a-form-item>
        <a-form-item label="访问属性">
          <a-select v-model:value="publicFilter" allow-clear placeholder="全部" style="width: 120px">
            <a-select-option :value="true">公开</a-select-option>
            <a-select-option :value="false">私有</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="statusFilter" allow-clear placeholder="全部状态" style="width: 140px">
            <a-select-option value="active">active</a-select-option>
            <a-select-option value="maintenance">maintenance</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="loading" @click="loadStatusPages">查询</a-button>
            <a-button @click="reset">重置</a-button>
            <a-button v-if="canCreate" type="primary" @click="openModal()">新增状态页</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="statusPages"
        row-key="id"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'is_public'">
            <a-tag :color="record.is_public ? 'green' : 'default'">{{ record.is_public ? '公开' : '私有' }}</a-tag>
          </template>
          <template v-if="column.key === 'public_url'">
            <a-typography-link v-if="record.slug" :href="`/status/${record.slug}`" target="_blank">
              /status/{{ record.slug }}
            </a-typography-link>
            <span v-else>-</span>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
              <a-popconfirm title="确认删除该状态页？" @confirm="removeStatusPage(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
      </a-space>

      <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑状态页' : '新增状态页'" @ok="saveStatusPage" :confirm-loading="saving">
        <a-form layout="vertical" :model="formState">
          <a-form-item label="名称" required>
            <a-input v-model:value="formState.name" />
          </a-form-item>
          <a-form-item label="Slug">
            <a-input v-model:value="formState.slug" />
          </a-form-item>
          <a-form-item label="状态">
            <a-input v-model:value="formState.status" placeholder="active / maintenance" />
          </a-form-item>
          <a-form-item label="页面标题">
            <a-input v-model:value="formState.title" placeholder="用于状态页展示标题" />
          </a-form-item>
          <a-form-item label="Logo URL">
            <a-input v-model:value="formState.logo" placeholder="https://..." />
          </a-form-item>
          <a-form-item label="主题色">
            <a-input v-model:value="formState.theme_color" placeholder="#1677ff" />
          </a-form-item>
          <a-form-item label="展示监控ID">
            <a-input v-model:value="formState.monitor_ids" placeholder="逗号分隔，如 1,2,3" />
          </a-form-item>
          <a-form-item label="订阅对象">
            <a-input v-model:value="formState.subscribers" placeholder="邮箱/用户ID，逗号分隔" />
          </a-form-item>
          <a-form-item label="公开访问">
            <a-switch v-model:checked="formState.is_public" />
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
  createStatusPage,
  deleteStatusPage,
  getStatusPages,
  type StatusPageItem,
  updateStatusPage
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const publicFilter = ref<boolean | undefined>(undefined)
const statusFilter = ref<string | undefined>(undefined)
const statusPages = ref<StatusPageItem[]>([])
const modalOpen = ref(false)
const editing = ref<StatusPageItem | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const formState = reactive({
  name: '',
  slug: '',
  status: '',
  is_public: false,
  title: '',
  logo: '',
  theme_color: '#1677ff',
  monitor_ids: '',
  subscribers: ''
})

const canCreate = computed(() => userStore.hasPermission('monitoring:status:create') || userStore.hasPermission('monitoring:status'))
const canEdit = computed(() => userStore.hasPermission('monitoring:status:edit') || userStore.hasPermission('monitoring:status'))
const canDelete = computed(() => userStore.hasPermission('monitoring:status:delete') || userStore.hasPermission('monitoring:status'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: 'Slug', dataIndex: 'slug', key: 'slug' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 130 },
  { title: '主题色', dataIndex: 'theme_color', key: 'theme_color', width: 110 },
  { title: '访问属性', dataIndex: 'is_public', key: 'is_public', width: 110 },
  { title: '公开链接', key: 'public_url', width: 190 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', width: 140 }
]

const normalizeList = (payload: any): { items: StatusPageItem[]; total: number } => {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const loadStatusPages = async () => {
  loading.value = true
  try {
    const res = await getStatusPages({
      q: keyword.value || undefined,
      is_public: publicFilter.value,
      status: statusFilter.value,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    const parsed = normalizeList(res?.data)
    statusPages.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载状态页失败')
  } finally {
    loading.value = false
  }
}

const openModal = (record?: StatusPageItem) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.slug = record?.slug || ''
  formState.status = record?.status || ''
  formState.is_public = !!record?.is_public
  formState.title = (record as any)?.title || ''
  formState.logo = (record as any)?.logo || ''
  formState.theme_color = (record as any)?.theme_color || '#1677ff'
  formState.monitor_ids = Array.isArray((record as any)?.monitor_ids) ? (record as any).monitor_ids.join(',') : ((record as any)?.monitor_ids || '')
  formState.subscribers = Array.isArray((record as any)?.subscribers) ? (record as any).subscribers.join(',') : ((record as any)?.subscribers || '')
  modalOpen.value = true
}

const saveStatusPage = async () => {
  if (!formState.name.trim()) {
    message.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      slug: formState.slug.trim() || undefined,
      status: formState.status.trim() || undefined,
      is_public: formState.is_public,
      title: formState.title.trim() || undefined,
      logo: formState.logo.trim() || undefined,
      theme_color: formState.theme_color.trim() || undefined,
      monitor_ids: formState.monitor_ids
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      subscribers: formState.subscribers
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateStatusPage(editing.value.id, payload)
    } else {
      await createStatusPage(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    loadStatusPages()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeStatusPage = async (record: StatusPageItem) => {
  try {
    await deleteStatusPage(record.id)
    message.success('删除成功')
    if (statusPages.value.length === 1 && pagination.current > 1) {
      pagination.current -= 1
    }
    loadStatusPages()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadStatusPages()
}

const reset = () => {
  keyword.value = ''
  publicFilter.value = undefined
  statusFilter.value = undefined
  pagination.current = 1
  loadStatusPages()
}

onMounted(() => {
  loadStatusPages()
})
</script>
