<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>通知规则说明</template>
        <template #description>
          <div>
            <p>通知规则定义告警触发时的通知方式和接收人。</p>
            <p><strong>通知渠道</strong>：选择已配置的通知渠道（邮件、钉钉、企业微信等）。</p>
            <p><strong>标签过滤</strong>：可以按告警标签过滤，只发送匹配的告警。</p>
            <p><strong>生效时间</strong>：可以设置规则生效的星期几和时间段。</p>
          </div>
        </template>
      </a-alert>

      <a-space>
        <a-input v-model:value="keyword" placeholder="通知规则名称" style="width: 220px" />
        <a-select v-model:value="receiverFilter" allow-clear placeholder="全部通知渠道" style="width: 180px" :options="receiverOptions" />
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'receiver'">
            <a-space>
              <component :is="getReceiverIcon(record.receiver_type)" />
              <span>{{ record.receiver_name || `渠道ID: ${record.receiver_id}` }}</span>
            </a-space>
          </template>
          <template v-if="column.key === 'filter_all'">
            <a-tag :color="record.filter_all !== false ? 'blue' : 'orange'">
              {{ record.filter_all !== false ? '全部告警' : '标签匹配' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'time_limit'">
            <div v-if="record.days && record.days.length < 7">
              <span>每周: {{ formatDays(record.days) }}</span>
            </div>
            <div v-else>每天</div>
            <div v-if="record.period_start && record.period_end">
              {{ record.period_start }} - {{ record.period_end }}
            </div>
            <div v-else>全天</div>
          </template>
          <template v-if="column.key === 'enable'">
            <a-switch
              :checked="record.enable"
              :disabled="!canEdit"
              @change="(checked: boolean) => toggleEnabled(record, checked)"
            />
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑通知规则' : '新增通知规则'" :confirm-loading="saving" width="800px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="规则名称" required>
              <a-input v-model:value="formState.name" placeholder="如：生产环境告警通知" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="通知渠道" required>
              <a-select v-model:value="formState.receiver_id" placeholder="选择通知渠道" @change="onReceiverChange">
                <a-select-option v-for="r in receiverList" :key="r.id" :value="r.id">
                  {{ r.name }} ({{ r.type_name }})
                </a-select-option>
              </a-select>
              <div class="form-help">
                没有合适的渠道？<a @click="goToReceiverConfig">去配置通知渠道</a>
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="发送规模">
              <a-select v-model:value="formState.notify_scale">
                <a-select-option value="single">单条发送</a-select-option>
                <a-select-option value="batch">批量发送</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="重试次数">
              <a-input-number v-model:value="formState.notify_times" :min="1" :max="5" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">告警过滤</a-divider>

        <a-form-item label="过滤方式">
          <a-radio-group v-model:value="formState.filter_all">
            <a-radio :value="true">转发所有告警</a-radio>
            <a-radio :value="false">按标签过滤</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="!formState.filter_all" label="标签过滤条件">
          <div v-for="(item, index) in formState.labelItems" :key="index" style="margin-bottom: 8px;">
            <a-row :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="item.key" placeholder="标签键，如 severity" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="item.value" placeholder="标签值，如 critical" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeLabel(index)">删除</a-button>
              </a-col>
            </a-row>
          </div>
          <a-button type="dashed" block @click="addLabel">
            <plus-outlined /> 添加标签条件
          </a-button>
          <div style="margin-top: 4px; color: #999; font-size: 12px;">
            只有匹配所有标签条件的告警才会发送通知
          </div>
        </a-form-item>

        <a-divider orientation="left">生效时间</a-divider>

        <a-form-item label="生效星期">
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
            <a-form-item label="开始时间">
              <a-time-picker v-model:value="formState.periodStart" format="HH:mm" style="width: 100%" placeholder="全天" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="结束时间">
              <a-time-picker v-model:value="formState.periodEnd" format="HH:mm" style="width: 100%" placeholder="全天" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enable" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, MailOutlined, MessageOutlined, DingdingOutlined, MobileOutlined, GlobalOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  createAlertNotice,
  deleteAlertNotice,
  getAlertNotices,
  testAlertNotice,
  type AlertNotice,
  updateAlertNotice,
  getAllNoticeReceivers,
  type NoticeReceiver
} from '@/api/monitoring'

interface LabelItem {
  key: string
  value: string
}

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const receiverFilter = ref<string | undefined>(undefined)
const items = ref<AlertNotice[]>([])
const receiverList = ref<NoticeReceiver[]>([])
const receiverOptions = ref<{ label: string; value: string | number }[]>([])
const modalOpen = ref(false)
const editing = ref<AlertNotice | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const formState = reactive({
  name: '',
  receiver_id: undefined as number | undefined,
  notify_times: 1,
  notify_scale: 'single' as 'single' | 'batch',
  filter_all: true,
  labelItems: [] as LabelItem[],
  days: [1, 2, 3, 4, 5, 6, 7] as number[],
  periodStart: null as dayjs.Dayjs | null,
  periodEnd: null as dayjs.Dayjs | null,
  enable: true
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:notice:create') || userStore.hasPermission('monitoring:alert:notice'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:notice:edit') || userStore.hasPermission('monitoring:alert:notice'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:notice:delete') || userStore.hasPermission('monitoring:alert:notice'))
const canTest = computed(() => userStore.hasPermission('monitoring:alert:notice:test') || userStore.hasPermission('monitoring:alert:notice'))

const columns = [
  { title: '规则名称', dataIndex: 'name', key: 'name' },
  { title: '通知渠道', key: 'receiver', width: 200 },
  { title: '过滤方式', key: 'filter_all', width: 120 },
  { title: '生效时间', key: 'time_limit', width: 180 },
  { title: '启用', key: 'enable', width: 100 },
  { title: '操作', key: 'actions', width: 180 }
]

const receiverTypeIcons: Record<number, any> = {
  0: MobileOutlined,
  1: MailOutlined,
  2: GlobalOutlined,
  4: MessageOutlined,
  5: DingdingOutlined,
  6: MessageOutlined,
  8: GlobalOutlined,
  9: GlobalOutlined,
  10: MessageOutlined,
  11: GlobalOutlined,
  12: MessageOutlined,
  14: MessageOutlined
}

const getReceiverIcon = (type: number) => {
  return receiverTypeIcons[type] || MessageOutlined
}

const formatDays = (days: number[] | undefined): string => {
  if (!days || days.length === 0) return '无'
  const dayNames = ['', '一', '二', '三', '四', '五', '六', '日']
  return days.map((d: number) => `周${dayNames[d]}`).join(', ')
}

const labelsToObject = (items: LabelItem[]): Record<string, string> => {
  const result: Record<string, string> = {}
  items.forEach(item => {
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

const addLabel = () => {
  formState.labelItems.push({ key: '', value: '' })
}

const removeLabel = (index: number) => {
  formState.labelItems.splice(index, 1)
}

const loadReceivers = async () => {
  try {
    const res = await getAllNoticeReceivers()
    receiverList.value = res?.data || []
    receiverOptions.value = receiverList.value.map(r => ({
      label: `${r.name} (${r.type_name})`,
      value: r.id
    }))
  } catch (error: any) {
    console.error('加载通知渠道失败:', error)
  }
}

const onReceiverChange = (value: number) => {
  formState.receiver_id = value
}

const goToReceiverConfig = () => {
  modalOpen.value = false
  router.push('/monitoring/alert/notice-receiver')
}

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertNotices({
      q: keyword.value || undefined,
      receiver_id: receiverFilter.value,
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

const openModal = (record?: AlertNotice) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.receiver_id = (record as any)?.receiver_id
  formState.notify_times = Number((record as any)?.notify_times || 1)
  formState.notify_scale = ((record as any)?.notify_scale || 'single') as 'single' | 'batch'
  formState.filter_all = (record as any)?.filter_all !== false
  formState.labelItems = objectToLabels((record as any)?.labels)
  formState.days = (record as any)?.days || [1, 2, 3, 4, 5, 6, 7]
  
  const periodStart = (record as any)?.period_start
  const periodEnd = (record as any)?.period_end
  formState.periodStart = periodStart ? dayjs(periodStart, 'HH:mm:ss') : null
  formState.periodEnd = periodEnd ? dayjs(periodEnd, 'HH:mm:ss') : null
  
  formState.enable = (record as any)?.enable !== false
  
  // 确保至少有一个空行
  if (formState.labelItems.length === 0) addLabel()
  
  modalOpen.value = true
}

const validateForm = () => {
  if (!formState.name.trim()) throw new Error('请输入规则名称')
  if (!formState.receiver_id) throw new Error('请选择通知渠道')
  if (formState.days.length === 0) throw new Error('请至少选择一天')
}

const saveItem = async () => {
  saving.value = true
  try {
    validateForm()
    
    const payload: Partial<AlertNotice> = {
      name: formState.name.trim(),
      receiver_id: formState.receiver_id,
      notify_times: Number(formState.notify_times || 1),
      notify_scale: formState.notify_scale,
      filter_all: formState.filter_all,
      labels: formState.filter_all ? {} : labelsToObject(formState.labelItems),
      days: formState.days,
      period_start: formState.periodStart ? formState.periodStart.format('HH:mm:ss') : null,
      period_end: formState.periodEnd ? formState.periodEnd.format('HH:mm:ss') : null,
      enable: formState.enable
    }
    
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateAlertNotice(editing.value.id, payload)
    } else {
      await createAlertNotice(payload)
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

const removeItem = async (record: AlertNotice) => {
  await deleteAlertNotice(record.id)
  message.success('删除成功')
  loadData()
}

const testItem = async (record: AlertNotice) => {
  await testAlertNotice(record.id)
  message.success('测试发送成功')
}

const toggleEnabled = async (record: AlertNotice, checked: boolean) => {
  try {
    await updateAlertNotice(record.id, { enable: checked })
    record.enable = checked
    message.success(checked ? '已启用' : '已禁用')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  }
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

const reset = () => {
  keyword.value = ''
  receiverFilter.value = undefined
  pagination.current = 1
  loadData()
}

onMounted(() => {
  loadData()
  loadReceivers()
})
</script>

<style scoped>
.label-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.form-help {
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}
</style>
