<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>告警分组说明</template>
        <template #description>
          <div>
            <p>告警分组将具有相同标签的告警聚合在一起，减少通知轰炸。</p>
            <p><strong>分组等待</strong>：首次收到告警后等待一段时间，收集同组告警一起发送。</p>
            <p><strong>分组间隔</strong>：同一组的告警发送间隔。</p>
            <p><strong>重复间隔</strong>：相同告警的重复通知间隔。</p>
          </div>
        </template>
      </a-alert>

      <a-space>
        <a-input v-model:value="keyword" placeholder="分组名称" style="width: 220px" />
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'group_labels'">
            <a-space wrap>
              <a-tag v-for="label in parseLabels(record.group_labels)" :key="label">{{ label }}</a-tag>
              <span v-if="!record.group_labels || parseLabels(record.group_labels).length === 0">-</span>
            </a-space>
          </template>
          <template v-if="column.key === 'timing'">
            <div>等待: {{ formatDuration(record.group_wait) }}</div>
            <div>间隔: {{ formatDuration(record.group_interval) }}</div>
            <div>重复: {{ formatDuration(record.repeat_interval) }}</div>
          </template>
          <template v-if="column.key === 'enabled'">
            <a-switch
              :checked="record.enabled"
              :disabled="!canEdit"
              @change="(checked: boolean) => toggleEnabled(record, checked)"
            />
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警分组' : '新增告警分组'" :confirm-loading="saving" width="700px" @ok="saveItem">
      <a-form layout="vertical" :model="formState" :rules="formRules">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="名称" name="name" required>
              <a-input v-model:value="formState.name" placeholder="如：instance-group" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="分组键" name="group_key" required>
              <a-input v-model:value="formState.group_key" placeholder="唯一标识，如：group-by-instance" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="匹配类型">
          <a-radio-group v-model:value="formState.match_type">
            <a-radio :value="0">匹配所有告警</a-radio>
            <a-radio :value="1">按标签匹配</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="formState.match_type === 1" label="分组标签">
          <a-select
            v-model:value="formState.group_labels"
            mode="tags"
            placeholder="输入标签键，如：instance, alertname"
            style="width: 100%"
          />
          <div style="margin-top: 4px; color: #999; font-size: 12px;">
            按这些标签的值进行分组，相同值的告警会被分到同一组
          </div>
        </a-form-item>

        <a-divider orientation="left">分组时间配置</a-divider>

        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="分组等待 (group_wait)">
              <a-input-number v-model:value="formState.group_wait" :min="0" :step="5" style="width: 100%" addon-after="秒" />
              <div style="color: #999; font-size: 12px;">首次告警后等待时间</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="分组间隔 (group_interval)">
              <a-input-number v-model:value="formState.group_interval" :min="0" :step="60" style="width: 100%" addon-after="秒" />
              <div style="color: #999; font-size: 12px;">同组告警发送间隔</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="重复间隔 (repeat_interval)">
              <a-input-number v-model:value="formState.repeat_interval" :min="0" :step="300" style="width: 100%" addon-after="秒" />
              <div style="color: #999; font-size: 12px;">相同告警重复间隔</div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { createAlertGroup, deleteAlertGroup, getAlertGroups, updateAlertGroup, updateAlertGroupEnabled, type AlertGroup } from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const toggling = ref<number | string | null>(null)
const keyword = ref('')
const items = ref<AlertGroup[]>([])
const modalOpen = ref(false)
const editing = ref<AlertGroup | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({
  name: '',
  group_key: '',
  match_type: 0,
  group_labels: [] as string[],
  group_wait: 30,
  group_interval: 300,
  repeat_interval: 14400,
  enabled: true
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  group_key: [{ required: true, message: '请输入分组键', trigger: 'blur' }]
}

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:group:create') || userStore.hasPermission('monitoring:alert:group'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:group:edit') || userStore.hasPermission('monitoring:alert:group'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:group:delete') || userStore.hasPermission('monitoring:alert:group'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '分组键', dataIndex: 'group_key', key: 'group_key', width: 180 },
  { title: '分组标签', key: 'group_labels', width: 200 },
  { title: '时间配置', key: 'timing', width: 180 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', width: 120 }
]

const parseLabels = (labels: string | string[] | undefined): string[] => {
  if (!labels) return []
  if (Array.isArray(labels)) return labels
  try {
    const parsed = JSON.parse(labels)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return labels.split(',').map(x => x.trim()).filter(Boolean)
  }
}

const formatDuration = (seconds: number | undefined): string => {
  if (seconds === undefined || seconds === null) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

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
  formState.group_key = (record as any)?.group_key || ''
  formState.match_type = (record as any)?.match_type ?? 0
  formState.group_labels = parseLabels((record as any)?.group_labels)
  formState.group_wait = (record as any)?.group_wait ?? 30
  formState.group_interval = (record as any)?.group_interval ?? 300
  formState.repeat_interval = (record as any)?.repeat_interval ?? 14400
  formState.enabled = record?.enabled !== false
  modalOpen.value = true
}

const saveItem = async () => {
  if (!formState.name.trim()) return message.warning('请输入名称')
  if (!formState.group_key.trim()) return message.warning('请输入分组键')

  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      group_key: formState.group_key.trim(),
      match_type: formState.match_type,
      group_labels: formState.match_type === 1 ? formState.group_labels : [],
      group_wait: formState.group_wait,
      group_interval: formState.group_interval,
      repeat_interval: formState.repeat_interval,
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

const toggleEnabled = async (record: AlertGroup, enabled: boolean) => {
  toggling.value = record.id
  try {
    await updateAlertGroupEnabled(record.id, enabled)
    message.success(enabled ? '已启用' : '已停用')
    record.enabled = enabled
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  } finally {
    toggling.value = null
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
