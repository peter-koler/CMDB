<template>
  <div class="app-page monitoring-target-ci-selector-page">
    <div class="app-page__header monitoring-target-ci-selector-page__header">
      <div>
        <a-space>
          <a-button @click="goBack">返回</a-button>
          <div>
            <div class="monitoring-target-ci-selector-page__title">选择 CI 实例</div>
            <div class="monitoring-target-ci-selector-page__subtitle">
              默认展示当前模型下尚未纳入监控的 CI，可按关键属性筛选或列出全部实例。
            </div>
          </div>
        </a-space>
      </div>
      <div class="app-toolbar">
        <a-space>
          <a-button @click="goBack">取消</a-button>
          <a-button type="primary" :disabled="!selectedRow" @click="confirmSelection">确定</a-button>
        </a-space>
      </div>
    </div>

    <a-card :bordered="false" class="app-surface-card">
      <a-spin :spinning="loading">
        <a-form layout="vertical">
          <a-row :gutter="[16, 0]">
            <a-col v-for="fieldCode in searchableFieldCodes" :key="fieldCode" :xs="24" :md="8">
              <a-form-item :label="selectedModel?.fieldLabelMap[fieldCode] || fieldCode">
                <a-input
                  v-model:value="searchState[fieldCode]"
                  :placeholder="`请输入${selectedModel?.fieldLabelMap[fieldCode] || fieldCode}`"
                  @pressEnter="handleSearch"
                />
              </a-form-item>
            </a-col>
          </a-row>

          <div class="monitoring-target-ci-selector-page__actions">
            <a-space wrap>
              <a-button type="primary" @click="handleSearch">搜索</a-button>
              <a-button @click="handleReset">重置搜索条件</a-button>
            </a-space>
            <a-button @click="handleListAll">列出全部</a-button>
          </div>
        </a-form>

        <a-alert
          :message="scope === 'all' ? '当前展示该模型全部 CI 实例。' : '当前默认展示未纳入监控的 CI 实例。'"
          type="info"
          show-icon
          class="monitoring-target-ci-selector-page__alert"
        />

        <a-table
          row-key="id"
          :columns="tableColumns"
          :data-source="rows"
          :pagination="paginationConfig"
          :loading="loading"
          :row-selection="rowSelection"
          :scroll="{ x: 1080 }"
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'index'">
              {{ (pagination.page - 1) * pagination.perPage + index + 1 }}
            </template>
            <template v-else-if="column.key === 'monitored'">
              <a-tag :color="record.monitored ? 'orange' : 'green'">
                {{ record.monitored ? '已监控' : '未监控' }}
              </a-tag>
            </template>
            <template v-else-if="String(column.key).startsWith('key:')">
              {{ formatAttribute(record.attributes, String(column.key).slice(4)) }}
            </template>
            <template v-else-if="String(column.key).startsWith('extra:')">
              {{ formatAttribute(record.attributes, String(column.key).slice(6)) }}
            </template>
            <template v-else-if="column.key === 'ciid'">
              {{ record.id }}
            </template>
          </template>
        </a-table>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { getModels } from '@/api/cmdb'
import { getMonitoringTargetCiOptions } from '@/api/ci'
import {
  buildCiSelectionValue,
  createModelOption,
  getMonitoringTargetDraftKey,
  readMonitoringTargetDraft,
  writeMonitoringTargetDraft,
  type ModelOption
} from './form-helpers'

interface CiSelectorRow {
  id: number
  code: string
  attributes: Record<string, any>
  monitored: boolean
  monitor_count: number
  monitor_names: string[]
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const modelsLoading = ref(false)
const modelOptions = ref<ModelOption[]>([])
const rows = ref<CiSelectorRow[]>([])
const selectedRow = ref<CiSelectorRow | null>(null)
const selectedRowKeys = ref<number[]>([])
const scope = ref<'unmonitored' | 'all'>('unmonitored')
const pagination = reactive({
  page: 1,
  perPage: 10,
  total: 0
})
const searchState = reactive<Record<string, string>>({})

const modelId = computed(() => Number(route.query.modelId || 0))
const mode = computed<'create' | 'edit'>(() => (String(route.query.mode || 'create') === 'edit' ? 'edit' : 'create'))
const targetId = computed(() => Number(route.query.targetId || 0))
const category = computed(() => String(route.query.category || ''))
const draftKey = computed(() => String(route.query.draftKey || getMonitoringTargetDraftKey(mode.value, targetId.value, category.value)))
const returnTo = computed(() => String(route.query.returnTo || '/monitoring/list'))
const selectedModel = computed(() => modelOptions.value.find((item) => item.id === modelId.value))
const searchableFieldCodes = computed(() => selectedModel.value?.keyFieldCodes?.length ? selectedModel.value.keyFieldCodes : ['name', 'ip'])
const extraFieldCodes = computed(() => {
  const model = selectedModel.value
  if (!model) return []
  return model.orderedFieldCodes.filter((code) => !model.keyFieldCodes.includes(code)).slice(0, 2)
})

const tableColumns = computed(() => {
  const columns: Array<Record<string, any>> = [
    { title: '序号', key: 'index', width: 72, fixed: 'left' }
  ]
  searchableFieldCodes.value.forEach((fieldCode) => {
    columns.push({
      title: selectedModel.value?.fieldLabelMap[fieldCode] || fieldCode,
      key: `key:${fieldCode}`,
      width: 180
    })
  })
  columns.push({ title: '是否监控', key: 'monitored', width: 120 })
  extraFieldCodes.value.forEach((fieldCode) => {
    columns.push({
      title: selectedModel.value?.fieldLabelMap[fieldCode] || fieldCode,
      key: `extra:${fieldCode}`,
      width: 180
    })
  })
  columns.push({ title: 'CIID', key: 'ciid', width: 120 })
  return columns
})

const rowSelection = computed(() => ({
  type: 'radio' as const,
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: Array<string | number>, selectedRows: CiSelectorRow[]) => {
    selectedRowKeys.value = keys.map((item) => Number(item))
    selectedRow.value = selectedRows[0] || null
  }
}))

const paginationConfig = computed(() => ({
  current: pagination.page,
  pageSize: pagination.perPage,
  total: pagination.total,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (total: number) => `共 ${total} 条`,
  onChange: (page: number, pageSize: number) => {
    pagination.page = page
    pagination.perPage = pageSize
    fetchRows()
  },
  onShowSizeChange: (page: number, pageSize: number) => {
    pagination.page = page
    pagination.perPage = pageSize
    fetchRows()
  }
}))

function formatAttribute(attributes: Record<string, any>, fieldCode: string) {
  const value = attributes?.[fieldCode]
  if (value === undefined || value === null || String(value).trim() === '') return '-'
  return String(value)
}

async function loadModels() {
  if (modelOptions.value.length) return
  modelsLoading.value = true
  try {
    const res = await getModels({ page: 1, per_page: 1000 })
    const items = Array.isArray(res?.data?.items) ? res.data.items : Array.isArray(res?.data) ? res.data : []
    modelOptions.value = items.map((item: any) => createModelOption(item))
  } catch {
    modelOptions.value = []
  } finally {
    modelsLoading.value = false
  }
}

async function fetchRows() {
  if (!modelId.value) return
  loading.value = true
  try {
    const params: Record<string, any> = {
      model_id: modelId.value,
      page: pagination.page,
      per_page: pagination.perPage,
      scope: scope.value
    }
    searchableFieldCodes.value.forEach((fieldCode) => {
      const value = String(searchState[fieldCode] || '').trim()
      if (value) params[`attr_${fieldCode}`] = value
    })
    const res = await getMonitoringTargetCiOptions(params)
    const data = res?.data || {}
    rows.value = Array.isArray(data.items) ? data.items : []
    pagination.total = Number(data.total) || 0

    if (selectedRow.value) {
      const next = rows.value.find((item) => item.id === selectedRow.value?.id) || null
      selectedRow.value = next
      selectedRowKeys.value = next ? [next.id] : []
    }
  } catch (error: any) {
    rows.value = []
    pagination.total = 0
    message.error(error?.response?.data?.message || '加载 CI 实例失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  scope.value = 'unmonitored'
  pagination.page = 1
  fetchRows()
}

function handleReset() {
  searchableFieldCodes.value.forEach((fieldCode) => {
    searchState[fieldCode] = ''
  })
  scope.value = 'unmonitored'
  pagination.page = 1
  fetchRows()
}

function handleListAll() {
  scope.value = 'all'
  pagination.page = 1
  fetchRows()
}

function goBack() {
  router.push(returnTo.value)
}

function confirmSelection() {
  if (!selectedRow.value || !selectedModel.value) {
    message.warning('请选择一个 CI 实例')
    return
  }
  const draft = readMonitoringTargetDraft(draftKey.value) || {}
  const selectedValue = buildCiSelectionValue(selectedRow.value, selectedModel.value)
  writeMonitoringTargetDraft(draftKey.value, {
    ...draft,
    ci_model_id: modelId.value,
    ci_id: selectedValue.id,
    ci_code: selectedValue.code,
    ci_display: selectedValue.display,
    ci_attributes: selectedValue.attributes
  })
  router.push(returnTo.value)
}

onMounted(async () => {
  await loadModels()
  if (!modelId.value) {
    message.warning('请先选择 CI 模型')
    goBack()
    return
  }
  const draft = readMonitoringTargetDraft(draftKey.value) || {}
  const currentCiId = Number(draft.ci_id || 0)
  if (currentCiId > 0) {
    selectedRowKeys.value = [currentCiId]
  }
  searchableFieldCodes.value.forEach((fieldCode) => {
    searchState[fieldCode] = ''
  })
  await fetchRows()
  if (currentCiId > 0) {
    const row = rows.value.find((item) => item.id === currentCiId) || null
    selectedRow.value = row
    selectedRowKeys.value = row ? [row.id] : []
  }
})
</script>

<style scoped>
.monitoring-target-ci-selector-page {
  min-height: 100%;
}

.monitoring-target-ci-selector-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.monitoring-target-ci-selector-page__title {
  color: var(--app-text-primary);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.monitoring-target-ci-selector-page__subtitle {
  margin-top: 4px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.monitoring-target-ci-selector-page__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.monitoring-target-ci-selector-page__alert {
  margin-bottom: 16px;
}

@media (max-width: 960px) {
  .monitoring-target-ci-selector-page__header,
  .monitoring-target-ci-selector-page__actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
