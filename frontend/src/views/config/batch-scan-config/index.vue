<template>
  <div class="batch-scan-config-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item label="模型">
              <a-select
                v-model:value="searchModelId"
                placeholder="请选择模型"
                allowClear
                showSearch
                :filter-option="filterOption"
                style="width: 100%"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item label="状态">
              <a-select v-model:value="searchEnabled" placeholder="请选择状态" allowClear style="width: 100%">
                <a-select-option :value="true">已启用</a-select-option>
                <a-select-option :value="false">已禁用</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="24" :md="8">
            <a-form-item class="search-buttons">
              <a-space wrap>
                <a-button type="primary" @click="handleSearch">
                  <template #icon><SearchOutlined /></template>
                  搜索
                </a-button>
                <a-button @click="handleReset">
                  <template #icon><ReloadOutlined /></template>
                  重置
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="table-card">
      <a-table
        :columns="columns"
        :data-source="filteredConfigs"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
        row-key="model_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'batch_scan_enabled'">
            <a-switch
              :checked="record.batch_scan_enabled"
              @change="(checked: boolean) => handleToggleEnabled(record, checked)"
            />
          </template>
          <template v-else-if="column.key === 'next_run_at'">
            <span v-if="record.batch_scan_enabled && record.next_run_at">
              {{ record.next_run_at }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'last_run_status'">
            <a-tag v-if="record.last_run_status === 'completed'" color="green">成功</a-tag>
            <a-tag v-else-if="record.last_run_status === 'failed'" color="error">失败</a-tag>
            <a-tag v-else-if="record.last_run_status === 'running'" color="processing">运行中</a-tag>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="showConfigModal(record)">
                配置
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="handleTriggerScan(record)"
                :loading="record.scanning"
              >
                立即执行
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="configModalVisible"
      :title="`批量扫描配置 - ${currentModel?.name || ''}`"
      width="500px"
      @ok="handleSaveConfig"
      :confirm-loading="saveLoading"
    >
      <a-form :model="configForm" :rules="configRules" ref="configFormRef" layout="vertical">
        <a-form-item label="启用批量扫描" name="batch_scan_enabled">
          <a-switch v-model:checked="configForm.batch_scan_enabled" />
        </a-form-item>
        <a-form-item label="Cron 表达式" name="batch_scan_cron">
          <a-input
            v-model:value="configForm.batch_scan_cron"
            placeholder="如: 0 2 * * * (每天凌晨2点)"
            :disabled="!configForm.batch_scan_enabled"
          />
        </a-form-item>
        <a-form-item label="Cron 表达式示例">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="每天凌晨2点">0 2 * * *</a-descriptions-item>
            <a-descriptions-item label="每天早上6点">0 6 * * *</a-descriptions-item>
            <a-descriptions-item label="每周日凌晨3点">0 3 * * 0</a-descriptions-item>
            <a-descriptions-item label="每月1日凌晨4点">0 4 1 * *</a-descriptions-item>
            <a-descriptions-item label="每小时整点">0 * * * *</a-descriptions-item>
          </a-descriptions>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getBatchScanConfig, updateBatchScanConfig, triggerBatchScan } from '@/api/trigger'
import { getModels } from '@/api/cmdb'

interface ModelConfig {
  model_id: number
  model_name: string
  batch_scan_enabled: boolean
  batch_scan_cron: string
  next_run_at: string | null
  last_run_at: string | null
  last_run_status: string | null
  scanning?: boolean
}

const loading = ref(false)
const saveLoading = ref(false)
const configModalVisible = ref(false)
const configFormRef = ref()

const searchModelId = ref<number | null>(null)
const searchEnabled = ref<boolean | null>(null)

const models = ref<any[]>([])
const configs = ref<ModelConfig[]>([])
const currentModel = ref<any>(null)

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const configForm = reactive({
  batch_scan_enabled: false,
  batch_scan_cron: ''
})

const configRules = {
  batch_scan_cron: [
    { pattern: /^(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)$/, message: '格式错误，例: 0 2 * * *', trigger: 'blur' }
  ]
}

const columns = [
  { title: '模型名称', dataIndex: 'model_name', key: 'model_name', width: 150 },
  { title: '批量扫描', dataIndex: 'batch_scan_enabled', key: 'batch_scan_enabled', width: 100 },
  { title: 'Cron 表达式', dataIndex: 'batch_scan_cron', key: 'batch_scan_cron', width: 150 },
  { title: '下次执行时间', dataIndex: 'next_run_at', key: 'next_run_at', width: 180 },
  { title: '上次执行时间', dataIndex: 'last_run_at', key: 'last_run_at', width: 180 },
  { title: '上次执行状态', dataIndex: 'last_run_status', key: 'last_run_status', width: 120 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' as const }
]

const filterOption = (input: string, option: any) => {
  return option.children?.[0]?.children?.toLowerCase().includes(input.toLowerCase())
}

const filteredConfigs = computed(() => {
  let result = configs.value
  if (searchModelId.value !== null) {
    result = result.filter(c => c.model_id === searchModelId.value)
  }
  if (searchEnabled.value !== null) {
    result = result.filter(c => c.batch_scan_enabled === searchEnabled.value)
  }
  pagination.total = result.length
  return result
})

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      models.value = res.data.items || res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchConfigs = async () => {
  loading.value = true
  try {
    const modelList = models.value
    
    const configPromises = modelList.map(async (model) => {
      try {
        const res = await getBatchScanConfig(model.id)
        if (res.code === 200) {
          return {
            model_id: model.id,
            model_name: model.name,
            batch_scan_enabled: res.data.batch_scan_enabled || false,
            batch_scan_cron: res.data.batch_scan_cron || '',
            next_run_at: res.data.next_run_at || null,
            last_run_at: res.data.last_run_at || null,
            last_run_status: res.data.last_run_status || null
          }
        }
      } catch (error) {
        console.error(error)
      }
      return {
        model_id: model.id,
        model_name: model.name,
        batch_scan_enabled: false,
        batch_scan_cron: '',
        next_run_at: null,
        last_run_at: null,
        last_run_status: null
      }
    })

    configs.value = await Promise.all(configPromises)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleToggleEnabled = async (record: ModelConfig, checked: boolean) => {
  try {
    const res = await updateBatchScanConfig(record.model_id, {
      batch_scan_enabled: checked,
      batch_scan_cron: record.batch_scan_cron
    })
    if (res.code === 200) {
      message.success(checked ? '已启用批量扫描' : '已禁用批量扫描')
      fetchConfigs()
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '操作失败')
  }
}

const showConfigModal = (record: ModelConfig) => {
  currentModel.value = models.value.find(m => m.id === record.model_id)
  configForm.batch_scan_enabled = record.batch_scan_enabled
  configForm.batch_scan_cron = record.batch_scan_cron
  configModalVisible.value = true
}

const handleSaveConfig = async () => {
  if (!currentModel.value) return
  
  try {
    await configFormRef.value.validate()
  } catch {
    return
  }

  saveLoading.value = true
  try {
    const res = await updateBatchScanConfig(currentModel.value.id, {
      batch_scan_enabled: configForm.batch_scan_enabled,
      batch_scan_cron: configForm.batch_scan_cron
    })
    if (res.code === 200) {
      message.success('配置保存成功')
      configModalVisible.value = false
      fetchConfigs()
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '保存失败')
  } finally {
    saveLoading.value = false
  }
}

const handleTriggerScan = async (record: ModelConfig) => {
  const config = configs.value.find(c => c.model_id === record.model_id)
  if (config) {
    config.scanning = true
  }
  
  try {
    const res = await triggerBatchScan(record.model_id)
    if (res.code === 202 || res.code === 200) {
      message.success('已触发批量扫描任务')
      setTimeout(() => fetchConfigs(), 2000)
    }
  } catch (error: any) {
    message.error(error.response?.data?.error || '触发失败')
  } finally {
    if (config) {
      config.scanning = false
    }
  }
}

const handleSearch = () => {
  pagination.current = 1
}

const handleReset = () => {
  searchModelId.value = null
  searchEnabled.value = null
  pagination.current = 1
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
}

onMounted(async () => {
  await fetchModels()
  fetchConfigs()
})
</script>

<style scoped>
.batch-scan-config-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.search-form {
  width: 100%;
}

.table-card {
  margin-bottom: 16px;
}

.text-muted {
  color: #999;
}
</style>
