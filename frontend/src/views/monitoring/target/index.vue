<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-form layout="inline">
        <a-form-item label="关键字">
          <a-input v-model:value="keyword" placeholder="名称/地址" style="width: 220px" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="status" allow-clear placeholder="全部状态" style="width: 140px">
            <a-select-option value="enabled">enabled</a-select-option>
            <a-select-option value="disabled">disabled</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-space>
            <a-button type="primary" :loading="loading" @click="loadTargets">查询</a-button>
            <a-button @click="reset">重置</a-button>
            <a-button v-if="canCreate" type="primary" @click="openModal()">新增监控</a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="targets"
        row-key="id"
        :pagination="pagination"
        :row-selection="rowSelection"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.enabled === false ? 'default' : 'green'">
              {{ record.enabled === false ? 'disabled' : 'enabled' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'enabled'">
            <a-switch
              :checked="record.enabled !== false"
              :disabled="!canEdit"
              @change="(checked: boolean) => toggleTarget(record, checked)"
            />
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" :disabled="!canEdit" @click="openModal(record)">编辑</a-button>
              <a-popconfirm title="确认删除该监控？" @confirm="removeTarget(record)">
                <a-button type="link" size="small" danger :disabled="!canDelete">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
      <a-space>
        <a-button :disabled="!selectedRowKeys.length || !canDelete" danger @click="batchDelete">批量删除</a-button>
        <a-input-number v-model:value="batchInterval" :min="5" :step="5" style="width: 140px" />
        <a-button :disabled="!selectedRowKeys.length || !canEdit" @click="batchUpdateInterval">批量修改间隔</a-button>
      </a-space>
    </a-space>

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑监控' : '新增监控'" @ok="saveTarget" :confirm-loading="saving">
      <a-form layout="vertical" :model="formState">
        <a-form-item label="名称" required>
          <a-input v-model:value="formState.name" />
        </a-form-item>
        <a-form-item label="类型(app)" required>
          <a-input v-model:value="formState.app" />
        </a-form-item>
        <a-form-item label="目标地址(target)" required>
          <a-input v-model:value="formState.target" />
        </a-form-item>
        <a-form-item label="采集间隔(秒)" required>
          <a-input-number v-model:value="formState.interval" :min="5" :step="5" style="width: 100%" />
        </a-form-item>
        <a-form-item label="采集器分配">
          <a-space direction="vertical" style="width: 100%">
            <a-select
              v-model:value="formState.collector_id"
              allow-clear
              placeholder="自动分配（推荐）"
              style="width: 100%"
              :loading="collectorsLoading"
              @focus="loadCollectors"
            >
              <a-select-option v-for="c in collectors" :key="c.id" :value="c.id">
                {{ c.name || c.id }} {{ c.host ? `(${c.host})` : '' }}
              </a-select-option>
            </a-select>
            <a-checkbox v-model:checked="formState.pin_collector" :disabled="!formState.collector_id">
              固定分配到该采集器（不随负载均衡变更）
            </a-checkbox>
          </a-space>
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
import { useUserStore } from '@/stores/user'
import {
  createMonitoringTarget,
  deleteMonitoringTarget,
  disableMonitoringTarget,
  enableMonitoringTarget,
  getMonitoringTargets,
  type MonitoringTarget,
  updateMonitoringTarget,
  getCollectors,
  assignCollectorToMonitor,
  unassignCollectorFromMonitor,
  type CollectorItem
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const status = ref<string | undefined>(undefined)
const targets = ref<MonitoringTarget[]>([])
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })
const modalOpen = ref(false)
const editing = ref<MonitoringTarget | null>(null)
const selectedRowKeys = ref<number[]>([])
const batchInterval = ref<number>(60)

const formState = reactive({
  name: '',
  app: '',
  target: '',
  interval: 60,
  enabled: true,
  collector_id: undefined as string | undefined,
  pin_collector: false
})

// Collector 列表
const collectors = ref<Array<{ id: string; name?: string; host?: string; status?: string }>>([])
const collectorsLoading = ref(false)

// 加载 Collector 列表
const loadCollectors = async () => {
  collectorsLoading.value = true
  try {
    const res = await getCollectors({ status: 'online' })
    const parsed = normalizeList(res?.data)
    collectors.value = parsed.items.map((item: any) => ({
      id: String(item.id),
      name: item.name,
      host: item.host,
      status: item.status
    }))
  } catch (error) {
    collectors.value = []
  } finally {
    collectorsLoading.value = false
  }
}

const canEdit = computed(() => userStore.hasPermission('monitoring:list:edit') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:update') || userStore.hasPermission('monitoring:target'))
const canCreate = computed(() => userStore.hasPermission('monitoring:list:create') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:create') || userStore.hasPermission('monitoring:target'))
const canDelete = computed(() => userStore.hasPermission('monitoring:list:delete') || userStore.hasPermission('monitoring:list') || userStore.hasPermission('monitoring:target:delete') || userStore.hasPermission('monitoring:target'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'app', key: 'app', width: 140 },
  { title: '目标地址', dataIndex: 'target', key: 'target' },
  { title: '采集间隔(s)', dataIndex: 'interval', key: 'interval', width: 120 },
  { title: '最近采集时间', dataIndex: 'last_collected_at', key: 'last_collected_at', width: 180 },
  { title: '状态', key: 'status', width: 100 },
  { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 90 },
  { title: '操作', key: 'actions', width: 140 }
]

const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: (string | number)[]) => {
    selectedRowKeys.value = keys.map((item) => Number(item))
  }
}))

const normalizeList = (payload: any): { items: MonitoringTarget[]; total: number } => {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  return { items: [], total: 0 }
}

const loadTargets = async () => {
  loading.value = true
  try {
    const res = await getMonitoringTargets({
      q: keyword.value || undefined,
      status: status.value || undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    const parsed = normalizeList(res?.data)
    targets.value = parsed.items
    pagination.total = parsed.total
    selectedRowKeys.value = selectedRowKeys.value.filter((id) => targets.value.some((item) => item.id === id))
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载监控目标失败')
  } finally {
    loading.value = false
  }
}

const toggleTarget = async (record: MonitoringTarget, checked: boolean) => {
  try {
    if (checked) {
      await enableMonitoringTarget(record.id, { version: record.version })
    } else {
      await disableMonitoringTarget(record.id, { version: record.version })
    }
    message.success('操作成功')
    loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
    loadTargets()
  }
}

const openModal = (record?: MonitoringTarget) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.app = record?.app || ''
  formState.target = record?.target || record?.endpoint || ''
  formState.interval = Number(record?.interval || 60)
  formState.enabled = record?.enabled !== false
  formState.collector_id = undefined
  formState.pin_collector = false
  modalOpen.value = true
  // 加载 Collector 列表
  loadCollectors()
}

const saveTarget = async () => {
  if (!formState.name.trim() || !formState.app.trim() || !formState.target.trim()) {
    message.warning('请填写完整的必填字段')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: formState.name.trim(),
      app: formState.app.trim(),
      target: formState.target.trim(),
      interval: formState.interval,
      enabled: formState.enabled
    }
    let monitorId: number
    if (editing.value?.id) {
      await updateMonitoringTarget(editing.value.id, { ...payload, version: editing.value.version })
      monitorId = editing.value.id
    } else {
      const res = await createMonitoringTarget(payload)
      monitorId = res?.data?.id || res?.data?.monitor_id
    }

    // 处理 Collector 分配
    if (formState.collector_id && formState.pin_collector && monitorId) {
      // 固定分配到指定 Collector
      await assignCollectorToMonitor(monitorId, formState.collector_id)
    } else if (!formState.collector_id && editing.value?.id) {
      // 取消固定分配（如果之前有）
      try {
        await unassignCollectorFromMonitor(editing.value.id)
      } catch (e) {
        // 忽略取消分配失败的错误（可能本来就没有绑定）
      }
    }

    message.success('保存成功')
    modalOpen.value = false
    loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeTarget = async (record: MonitoringTarget) => {
  try {
    await deleteMonitoringTarget(record.id, record.version)
    message.success('删除成功')
    if (targets.value.length === 1 && pagination.current > 1) {
      pagination.current -= 1
    }
    loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

const batchDelete = async () => {
  if (!selectedRowKeys.value.length) return
  try {
    for (const id of selectedRowKeys.value) {
      const record = targets.value.find((item) => item.id === id)
      await deleteMonitoringTarget(id, record?.version)
    }
    selectedRowKeys.value = []
    message.success('批量删除成功')
    loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量删除失败')
  }
}

const batchUpdateInterval = async () => {
  if (!selectedRowKeys.value.length) return
  if (!batchInterval.value || batchInterval.value < 5) {
    message.warning('请输入合法的采集间隔')
    return
  }
  try {
    for (const id of selectedRowKeys.value) {
      const record = targets.value.find((item) => item.id === id)
      if (!record) continue
      await updateMonitoringTarget(id, {
        name: record.name,
        app: record.app,
        target: record.target || record.endpoint,
        interval: batchInterval.value,
        enabled: record.enabled !== false,
        version: record.version
      })
    }
    message.success('批量修改成功')
    loadTargets()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '批量修改失败')
  }
}

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadTargets()
}

const reset = () => {
  keyword.value = ''
  status.value = undefined
  pagination.current = 1
  selectedRowKeys.value = []
  loadTargets()
}

onMounted(() => {
  loadTargets()
})
</script>
