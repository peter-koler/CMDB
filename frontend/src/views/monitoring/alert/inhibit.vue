<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>告警抑制说明</template>
        <template #description>
          <div>
            <p>告警抑制用于避免重复/冗余告警。当源告警存在时，抑制目标告警的发送。</p>
            <p><strong>典型场景</strong>：磁盘已满时抑制磁盘使用率告警；网络中断时抑制主机不可达告警。</p>
            <p><strong>抑制条件</strong>：源告警匹配 + 目标告警匹配 + 相等标签值相同。</p>
          </div>
        </template>
      </a-alert>

      <a-space>
        <a-input v-model:value="keyword" placeholder="抑制规则名称" style="width: 220px" />
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'source_labels'">
            <div class="label-preview">
              <a-tag v-for="(value, key) in parseLabels(record.source_labels)" :key="key" color="red">
                {{ key }}={{ value }}
              </a-tag>
              <span v-if="!record.source_labels || Object.keys(parseLabels(record.source_labels)).length === 0">-</span>
            </div>
          </template>
          <template v-if="column.key === 'target_labels'">
            <div class="label-preview">
              <a-tag v-for="(value, key) in parseLabels(record.target_labels)" :key="key" color="orange">
                {{ key }}={{ value }}
              </a-tag>
              <span v-if="!record.target_labels || Object.keys(parseLabels(record.target_labels)).length === 0">-</span>
            </div>
          </template>
          <template v-if="column.key === 'equal_labels'">
            <a-space wrap>
              <a-tag v-for="label in parseArrayLabels(record.equal_labels)" :key="label">{{ label }}</a-tag>
              <span v-if="!record.equal_labels || parseArrayLabels(record.equal_labels).length === 0">-</span>
            </a-space>
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警抑制' : '新增告警抑制'" :confirm-loading="saving" width="750px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-form-item label="名称" required>
          <a-input v-model:value="formState.name" placeholder="如：disk-full-inhibit-usage" />
        </a-form-item>

        <a-divider orientation="left">源告警匹配条件</a-divider>
        <a-alert type="info" show-icon style="margin-bottom: 16px;">
          <template #message>源告警</template>
          <template #description>当此告警存在时，会抑制目标告警</template>
        </a-alert>
        <a-form-item label="源告警标签">
          <div v-for="(item, index) in formState.sourceLabels" :key="index" style="margin-bottom: 8px;">
            <a-row :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="item.key" placeholder="标签键，如 severity" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="item.value" placeholder="标签值，如 critical" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeSourceLabel(index)">删除</a-button>
              </a-col>
            </a-row>
          </div>
          <a-button type="dashed" block @click="addSourceLabel">
            <plus-outlined /> 添加源告警标签
          </a-button>
        </a-form-item>

        <a-divider orientation="left">目标告警匹配条件</a-divider>
        <a-alert type="warning" show-icon style="margin-bottom: 16px;">
          <template #message>目标告警</template>
          <template #description>当源告警存在时，此告警将被抑制不发送</template>
        </a-alert>
        <a-form-item label="目标告警标签">
          <div v-for="(item, index) in formState.targetLabels" :key="index" style="margin-bottom: 8px;">
            <a-row :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="item.key" placeholder="标签键，如 alertname" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="item.value" placeholder="标签值，如 disk_high_usage" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeTargetLabel(index)">删除</a-button>
              </a-col>
            </a-row>
          </div>
          <a-button type="dashed" block @click="addTargetLabel">
            <plus-outlined /> 添加目标告警标签
          </a-button>
        </a-form-item>

        <a-divider orientation="left">相等标签配置</a-divider>
        <a-form-item label="相等标签 (Equal Labels)">
          <a-select
            v-model:value="formState.equal_labels"
            mode="tags"
            placeholder="输入标签键，如：instance, cluster"
            style="width: 100%"
          />
          <div style="margin-top: 4px; color: #999; font-size: 12px;">
            源告警和目标告警的这些标签值必须相同才会触发抑制（如相同的 instance）
          </div>
        </a-form-item>

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
import { PlusOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { createAlertInhibit, deleteAlertInhibit, getAlertInhibits, updateAlertInhibit, updateAlertInhibitEnabled, type AlertInhibit } from '@/api/monitoring'

interface LabelItem {
  key: string
  value: string
}

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const toggling = ref<number | string | null>(null)
const keyword = ref('')
const items = ref<AlertInhibit[]>([])
const modalOpen = ref(false)
const editing = ref<AlertInhibit | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({
  name: '',
  sourceLabels: [] as LabelItem[],
  targetLabels: [] as LabelItem[],
  equal_labels: [] as string[],
  enabled: true
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:inhibit:create') || userStore.hasPermission('monitoring:alert:inhibit'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:inhibit:edit') || userStore.hasPermission('monitoring:alert:inhibit'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:inhibit:delete') || userStore.hasPermission('monitoring:alert:inhibit'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '源告警标签', key: 'source_labels', width: 200 },
  { title: '目标告警标签', key: 'target_labels', width: 200 },
  { title: '相等标签', key: 'equal_labels', width: 150 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', width: 120 }
]

const parseLabels = (labels: string | Record<string, string> | undefined): Record<string, string> => {
  if (!labels) return {}
  if (typeof labels === 'object') return labels
  try {
    return JSON.parse(labels)
  } catch {
    const result: Record<string, string> = {}
    labels.split(',').forEach(item => {
      const [key, value] = item.split('=').map(x => x.trim())
      if (key) result[key] = value || ''
    })
    return result
  }
}

const parseArrayLabels = (labels: string | string[] | undefined): string[] => {
  if (!labels) return []
  if (Array.isArray(labels)) return labels
  try {
    const parsed = JSON.parse(labels)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return labels.split(',').map(x => x.trim()).filter(Boolean)
  }
}

const labelsToArray = (labels: LabelItem[]): Record<string, string> => {
  const result: Record<string, string> = {}
  labels.forEach(item => {
    if (item.key.trim()) {
      result[item.key.trim()] = item.value.trim()
    }
  })
  return result
}

const arrayToLabels = (labels: Record<string, string> | undefined): LabelItem[] => {
  if (!labels) return []
  return Object.entries(labels).map(([key, value]) => ({ key, value }))
}

const addSourceLabel = () => {
  formState.sourceLabels.push({ key: '', value: '' })
}

const removeSourceLabel = (index: number) => {
  formState.sourceLabels.splice(index, 1)
}

const addTargetLabel = () => {
  formState.targetLabels.push({ key: '', value: '' })
}

const removeTargetLabel = (index: number) => {
  formState.targetLabels.splice(index, 1)
}

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
  formState.sourceLabels = arrayToLabels(parseLabels((record as any)?.source_labels))
  formState.targetLabels = arrayToLabels(parseLabels((record as any)?.target_labels))
  formState.equal_labels = parseArrayLabels((record as any)?.equal_labels)
  formState.enabled = record?.enabled !== false

  // 确保至少有一个空行
  if (formState.sourceLabels.length === 0) addSourceLabel()
  if (formState.targetLabels.length === 0) addTargetLabel()

  modalOpen.value = true
}

const saveItem = async () => {
  if (!formState.name.trim()) return message.warning('请输入名称')

  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      source_labels: labelsToArray(formState.sourceLabels),
      target_labels: labelsToArray(formState.targetLabels),
      equal_labels: formState.equal_labels,
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

const toggleEnabled = async (record: AlertInhibit, enabled: boolean) => {
  toggling.value = record.id
  try {
    await updateAlertInhibitEnabled(record.id, enabled)
    message.success(enabled ? '已启用' : '已停用')
    record.enabled = enabled
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  } finally {
    toggling.value = null
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

<style scoped>
.label-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
