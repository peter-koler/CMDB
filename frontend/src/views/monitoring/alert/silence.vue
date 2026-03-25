<template>
  <div class="app-page alert-silence-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>告警静默说明</template>
        <template #description>
          <div>
            <p>告警静默用于在特定时间段内阻止告警通知发送，适用于计划内维护窗口。</p>
            <p><strong>一次性静默</strong>：在指定时间段内静默告警（如：2024-01-15 02:00-06:00）。</p>
            <p><strong>周期性静默</strong>：按星期几循环静默（如：每周六、周日 00:00-06:00）。</p>
          </div>
        </template>
      </a-alert>

      <a-space>
        <a-input v-model:value="keyword" placeholder="静默名称" style="width: 220px" />
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag :color="record.type === 0 ? 'blue' : 'purple'">
              {{ record.type === 0 ? '一次性' : '周期性' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'match_type'">
            <span>{{ record.match_type === 0 ? '全部告警' : '标签匹配' }}</span>
          </template>
          <template v-if="column.key === 'labels'">
            <div class="label-preview">
              <a-tag v-for="(value, key) in parseLabels(record.labels)" :key="key">
                {{ key }}={{ value }}
              </a-tag>
              <span v-if="record.match_type === 0">全部</span>
              <span v-else-if="!record.labels || Object.keys(parseLabels(record.labels)).length === 0">-</span>
            </div>
          </template>
          <template v-if="column.key === 'time_range'">
            <div v-if="record.type === 0">
              <div>{{ formatTime(record.start_time) }}</div>
              <div>至 {{ formatTime(record.end_time) }}</div>
            </div>
            <div v-else>
              <div>每周: {{ formatDays(record.days) }}</div>
              <div>{{ formatTimeOnly(record.start_time) }} - {{ formatTimeOnly(record.end_time) }}</div>
            </div>
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑告警静默' : '新增告警静默'" :confirm-loading="saving" width="750px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="16">
            <a-form-item label="名称" required>
              <a-input v-model:value="formState.name" placeholder="如：weekend-maintenance" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="静默类型">
              <a-radio-group v-model:value="formState.type">
                <a-radio :value="0">一次性</a-radio>
                <a-radio :value="1">周期性</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="匹配类型">
          <a-radio-group v-model:value="formState.match_type">
            <a-radio :value="0">匹配所有告警</a-radio>
            <a-radio :value="1">按标签匹配</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="formState.match_type === 1" label="匹配标签">
          <div v-for="(item, index) in formState.labels" :key="index" style="margin-bottom: 8px;">
            <a-row :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="item.key" placeholder="标签键，如 app" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="item.value" placeholder="标签值，如 mysql" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeLabel(index)">删除</a-button>
              </a-col>
            </a-row>
          </div>
          <a-button type="dashed" block @click="addLabel">
            <plus-outlined /> 添加标签
          </a-button>
        </a-form-item>

        <!-- 一次性静默时间配置 -->
        <template v-if="formState.type === 0">
          <a-divider orientation="left">静默时间范围</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="开始时间" required>
                <a-date-picker
                  v-model:value="formState.startDate"
                  show-time
                  format="YYYY-MM-DD HH:mm:ss"
                  style="width: 100%"
                  placeholder="选择开始时间"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="结束时间" required>
                <a-date-picker
                  v-model:value="formState.endDate"
                  show-time
                  format="YYYY-MM-DD HH:mm:ss"
                  style="width: 100%"
                  placeholder="选择结束时间"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- 周期性静默时间配置 -->
        <template v-if="formState.type === 1">
          <a-divider orientation="left">周期性静默配置</a-divider>
          <a-form-item label="星期几" required>
            <a-checkbox-group v-model:value="formState.days">
              <a-checkbox :value="1">周一</a-checkbox>
              <a-checkbox :value="2">周二</a-checkbox>
              <a-checkbox :value="3">周三</a-checkbox>
              <a-checkbox :value="4">周四</a-checkbox>
              <a-checkbox :value="5">周五</a-checkbox>
              <a-checkbox :value="6">周六</a-checkbox>
              <a-checkbox :value="7">周日</a-checkbox>
            </a-checkbox-group>
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="开始时间" required>
                <a-time-picker
                  v-model:value="formState.startTime"
                  format="HH:mm"
                  style="width: 100%"
                  placeholder="选择开始时间"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="结束时间" required>
                <a-time-picker
                  v-model:value="formState.endTime"
                  format="HH:mm"
                  style="width: 100%"
                  placeholder="选择结束时间"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <a-form-item label="静默原因">
          <a-textarea
            v-model:value="formState.reason"
            :rows="2"
            placeholder="如：系统维护窗口、版本升级等"
          />
        </a-form-item>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { createAlertSilence, deleteAlertSilence, getAlertSilences, updateAlertSilence, updateAlertSilenceEnabled, type AlertSilence } from '@/api/monitoring'

interface LabelItem {
  key: string
  value: string
}

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const toggling = ref<number | string | null>(null)
const keyword = ref('')
const items = ref<AlertSilence[]>([])
const modalOpen = ref(false)
const editing = ref<AlertSilence | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const formState = reactive({
  name: '',
  type: 0,
  match_type: 0,
  labels: [] as LabelItem[],
  startDate: null as dayjs.Dayjs | null,
  endDate: null as dayjs.Dayjs | null,
  days: [] as number[],
  startTime: null as dayjs.Dayjs | null,
  endTime: null as dayjs.Dayjs | null,
  reason: '',
  enabled: true
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:silence:create') || userStore.hasPermission('monitoring:alert:silence'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:silence:edit') || userStore.hasPermission('monitoring:alert:silence'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:silence:delete') || userStore.hasPermission('monitoring:alert:silence'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '类型', key: 'type', width: 100 },
  { title: '匹配', key: 'match_type', width: 100 },
  { title: '标签', key: 'labels', width: 200 },
  { title: '时间范围', key: 'time_range', width: 220 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 100 },
  { title: '操作', key: 'actions', width: 120 }
]

const parseLabels = (labels: string | Record<string, string> | undefined): Record<string, string> => {
  if (!labels) return {}
  if (typeof labels === 'object') return labels
  try {
    return JSON.parse(labels)
  } catch {
    return {}
  }
}

const labelsToObject = (labels: LabelItem[]): Record<string, string> => {
  const result: Record<string, string> = {}
  labels.forEach(item => {
    if (item.key.trim()) {
      result[item.key.trim()] = item.value.trim()
    }
  })
  return result
}

const objectToLabels = (obj: Record<string, string> | undefined): LabelItem[] => {
  if (!obj) return []
  return Object.entries(obj).map(([key, value]) => ({ key, value }))
}

const formatTime = (timestamp: number | undefined): string => {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm')
}

const formatTimeOnly = (timestamp: number | undefined): string => {
  if (!timestamp) return '-'
  return dayjs(timestamp).format('HH:mm')
}

const formatDays = (days: number[] | string | undefined): string => {
  if (!days) return '-'
  const dayArr = Array.isArray(days) ? days : JSON.parse(days as string)
  const dayNames = ['', '一', '二', '三', '四', '五', '六', '日']
  return dayArr.map((d: number) => `周${dayNames[d]}`).join(', ')
}

const addLabel = () => {
  formState.labels.push({ key: '', value: '' })
}

const removeLabel = (index: number) => {
  formState.labels.splice(index, 1)
}

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
  formState.type = (record as any)?.type ?? 0
  formState.match_type = (record as any)?.match_type ?? 0
  formState.labels = objectToLabels(parseLabels((record as any)?.labels))
  formState.reason = (record as any)?.reason || ''
  formState.enabled = record?.enabled !== false

  // 时间处理
  const startTime = (record as any)?.start_time
  const endTime = (record as any)?.end_time

  if (formState.type === 0) {
    // 一次性静默
    formState.startDate = startTime ? dayjs(startTime) : null
    formState.endDate = endTime ? dayjs(endTime) : null
    formState.days = []
    formState.startTime = null
    formState.endTime = null
  } else {
    // 周期性静默
    formState.startDate = null
    formState.endDate = null
    formState.days = (record as any)?.days ? JSON.parse((record as any).days) : []
    formState.startTime = startTime ? dayjs().startOf('day').add(dayjs(startTime).hour(), 'hour').add(dayjs(startTime).minute(), 'minute') : null
    formState.endTime = endTime ? dayjs().startOf('day').add(dayjs(endTime).hour(), 'hour').add(dayjs(endTime).minute(), 'minute') : null
  }

  // 确保至少有一个空行
  if (formState.labels.length === 0) addLabel()

  modalOpen.value = true
}

const validateForm = () => {
  if (!formState.name.trim()) throw new Error('请输入名称')

  if (formState.type === 0) {
    // 一次性静默
    if (!formState.startDate || !formState.endDate) throw new Error('请选择开始和结束时间')
    if (formState.endDate.valueOf() <= formState.startDate.valueOf()) throw new Error('结束时间必须晚于开始时间')
  } else {
    // 周期性静默
    if (formState.days.length === 0) throw new Error('请至少选择一天')
    if (!formState.startTime || !formState.endTime) throw new Error('请选择开始和结束时间')
  }
}

const saveItem = async () => {
  saving.value = true
  try {
    validateForm()

    let startTime: number
    let endTime: number

    if (formState.type === 0) {
      // 一次性静默 - 使用时间戳
      startTime = formState.startDate!.valueOf()
      endTime = formState.endDate!.valueOf()
    } else {
      // 周期性静默 - 使用当天的时间戳作为模板
      const baseDate = dayjs().startOf('day')
      const startMinutes = formState.startTime!.hour() * 60 + formState.startTime!.minute()
      const endMinutes = formState.endTime!.hour() * 60 + formState.endTime!.minute()
      startTime = baseDate.add(startMinutes, 'minute').valueOf()
      endTime = baseDate.add(endMinutes, 'minute').valueOf()
    }

    const payload = {
      name: formState.name.trim(),
      type: formState.type,
      match_type: formState.match_type,
      labels: formState.match_type === 1 ? labelsToObject(formState.labels) : {},
      days: formState.type === 1 ? formState.days : [],
      start_time: startTime,
      end_time: endTime,
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

const toggleEnabled = async (record: AlertSilence, enabled: boolean) => {
  toggling.value = record.id
  try {
    await updateAlertSilenceEnabled(record.id, enabled)
    message.success(enabled ? '已启用' : '已停用')
    record.enabled = enabled
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  } finally {
    toggling.value = null
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

<style scoped>
.label-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
