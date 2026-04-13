<template>
  <div class="app-page batch-scan-config-page">
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
              {{ formatDateTime(record.next_run_at) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'last_run_at'">
            <span v-if="record.last_run_at">
              {{ formatDateTime(record.last_run_at) }}
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

    <a-card :bordered="false" class="table-card">
      <template #title>关系触发器定期扫描配置</template>
      <a-table
        :columns="triggerColumns"
        :data-source="filteredTriggerConfigs"
        :loading="triggerLoading"
        :pagination="triggerPagination"
        @change="handleTriggerTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'batch_scan_enabled'">
            <a-switch
              :checked="record.batch_scan_enabled"
              @change="(checked: boolean) => handleToggleTriggerEnabled(record, checked)"
            />
          </template>
          <template v-else-if="column.key === 'next_run_at'">
            <span v-if="record.batch_scan_enabled && record.next_run_at">
              {{ formatDateTime(record.next_run_at) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'last_run_at'">
            <span v-if="record.last_run_at">
              {{ formatDateTime(record.last_run_at) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'last_run_status'">
            <a-tag v-if="record.last_run_status === 'success'" color="green">成功</a-tag>
            <a-tag v-else-if="record.last_run_status === 'failed'" color="error">失败</a-tag>
            <a-tag v-else-if="record.last_run_status === 'skipped'" color="default">跳过</a-tag>
            <span v-else class="text-muted">-</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="showTriggerConfigModal(record)">
                配置
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="handleTriggerExecute(record)"
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
        <a-form-item label="配置方式">
          <a-radio-group
            v-model:value="configCronEditorMode"
            button-style="solid"
            size="small"
            @change="handleConfigEditorModeChange"
          >
            <a-radio-button value="visual">可视化计划</a-radio-button>
            <a-radio-button value="manual">手动输入</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="Cron 表达式" name="batch_scan_cron">
          <a-input
            v-model:value="configForm.batch_scan_cron"
            placeholder="如: 0 2 * * * (每天凌晨2点)"
            :disabled="!configForm.batch_scan_enabled"
            :readonly="configCronEditorMode === 'visual'"
            :status="getCronValidationState(configForm.batch_scan_cron, configForm.batch_scan_enabled).status"
          />
        </a-form-item>
        <div v-if="configCronEditorMode === 'visual'" class="batch-scan-config-page__cron-builder">
          <a-row :gutter="[12, 12]">
            <a-col :span="24">
              <a-form-item label="执行频率" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="configVisualSchedule.mode">
                  <a-select-option value="hourly">每小时</a-select-option>
                  <a-select-option value="daily">每天</a-select-option>
                  <a-select-option value="weekly">每周</a-select-option>
                  <a-select-option value="monthly">每月</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="分钟" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="configVisualSchedule.minute" show-search>
                  <a-select-option v-for="option in minuteOptions" :key="option" :value="option">
                    {{ option.padStart(2, '0') }} 分
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="configVisualSchedule.mode !== 'hourly'">
              <a-form-item label="小时" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="configVisualSchedule.hour" show-search>
                  <a-select-option v-for="option in hourOptions" :key="option" :value="option">
                    {{ option.padStart(2, '0') }} 时
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="configVisualSchedule.mode === 'weekly'">
              <a-form-item label="星期" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="configVisualSchedule.dayOfWeek">
                  <a-select-option v-for="option in weekOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="configVisualSchedule.mode === 'monthly'">
              <a-form-item label="日期" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="configVisualSchedule.dayOfMonth" show-search>
                  <a-select-option v-for="option in dayOptions" :key="option" :value="option">
                    每月 {{ option }} 日
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </div>
        <a-form-item class="batch-scan-config-page__cron-help">
          <div
            class="batch-scan-config-page__cron-message"
            :class="{
              'is-error': getCronValidationState(configForm.batch_scan_cron, configForm.batch_scan_enabled).status === 'error',
              'is-success': getCronValidationState(configForm.batch_scan_cron, configForm.batch_scan_enabled).status === 'success'
            }"
          >
            {{ getCronValidationState(configForm.batch_scan_cron, configForm.batch_scan_enabled).message }}
          </div>
          <a-space wrap class="batch-scan-config-page__cron-presets">
            <a-button
              v-for="preset in cronPresets"
              :key="preset.value"
              size="small"
              @click="applyCronPreset(configForm, preset.value)"
            >
              {{ preset.label }}
            </a-button>
          </a-space>
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

    <a-modal
      v-model:open="triggerConfigModalVisible"
      :title="`触发器定期扫描配置 - ${currentTrigger?.name || ''}`"
      width="500px"
      @ok="handleSaveTriggerConfig"
      :confirm-loading="triggerSaveLoading"
    >
      <a-form :model="triggerConfigForm" :rules="configRules" ref="triggerConfigFormRef" layout="vertical">
        <a-form-item label="启用定期扫描" name="batch_scan_enabled">
          <a-switch v-model:checked="triggerConfigForm.batch_scan_enabled" />
        </a-form-item>
        <a-form-item label="配置方式">
          <a-radio-group
            v-model:value="triggerCronEditorMode"
            button-style="solid"
            size="small"
            @change="handleTriggerEditorModeChange"
          >
            <a-radio-button value="visual">可视化计划</a-radio-button>
            <a-radio-button value="manual">手动输入</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="Cron 表达式" name="batch_scan_cron">
          <a-input
            v-model:value="triggerConfigForm.batch_scan_cron"
            placeholder="如: 0 2 * * * (每天凌晨2点)"
            :disabled="!triggerConfigForm.batch_scan_enabled"
            :readonly="triggerCronEditorMode === 'visual'"
            :status="getCronValidationState(triggerConfigForm.batch_scan_cron, triggerConfigForm.batch_scan_enabled).status"
          />
        </a-form-item>
        <div v-if="triggerCronEditorMode === 'visual'" class="batch-scan-config-page__cron-builder">
          <a-row :gutter="[12, 12]">
            <a-col :span="24">
              <a-form-item label="执行频率" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="triggerVisualSchedule.mode">
                  <a-select-option value="hourly">每小时</a-select-option>
                  <a-select-option value="daily">每天</a-select-option>
                  <a-select-option value="weekly">每周</a-select-option>
                  <a-select-option value="monthly">每月</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="分钟" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="triggerVisualSchedule.minute" show-search>
                  <a-select-option v-for="option in minuteOptions" :key="option" :value="option">
                    {{ option.padStart(2, '0') }} 分
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="triggerVisualSchedule.mode !== 'hourly'">
              <a-form-item label="小时" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="triggerVisualSchedule.hour" show-search>
                  <a-select-option v-for="option in hourOptions" :key="option" :value="option">
                    {{ option.padStart(2, '0') }} 时
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="triggerVisualSchedule.mode === 'weekly'">
              <a-form-item label="星期" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="triggerVisualSchedule.dayOfWeek">
                  <a-select-option v-for="option in weekOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12" v-if="triggerVisualSchedule.mode === 'monthly'">
              <a-form-item label="日期" class="batch-scan-config-page__builder-item">
                <a-select v-model:value="triggerVisualSchedule.dayOfMonth" show-search>
                  <a-select-option v-for="option in dayOptions" :key="option" :value="option">
                    每月 {{ option }} 日
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </div>
        <a-form-item class="batch-scan-config-page__cron-help">
          <div
            class="batch-scan-config-page__cron-message"
            :class="{
              'is-error': getCronValidationState(triggerConfigForm.batch_scan_cron, triggerConfigForm.batch_scan_enabled).status === 'error',
              'is-success': getCronValidationState(triggerConfigForm.batch_scan_cron, triggerConfigForm.batch_scan_enabled).status === 'success'
            }"
          >
            {{ getCronValidationState(triggerConfigForm.batch_scan_cron, triggerConfigForm.batch_scan_enabled).message }}
          </div>
          <a-space wrap class="batch-scan-config-page__cron-presets">
            <a-button
              v-for="preset in cronPresets"
              :key="preset.value"
              size="small"
              @click="applyCronPreset(triggerConfigForm, preset.value)"
            >
              {{ preset.label }}
            </a-button>
          </a-space>
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
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getBatchScanConfig, updateBatchScanConfig, triggerBatchScan } from '@/api/trigger'
import { getModels } from '@/api/cmdb'
import { executeRelationTrigger, getRelationTriggers, updateRelationTrigger } from '@/api/cmdb-relation'

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

interface TriggerConfigItem {
  id: number
  name: string
  source_model_id: number | null
  source_model_name: string | null
  target_model_id: number | null
  target_model_name: string | null
  relation_type_name: string | null
  batch_scan_enabled: boolean
  batch_scan_cron: string
  next_run_at: string | null
  last_run_at: string | null
  last_run_status: string | null
  scanning?: boolean
}

const loading = ref(false)
const triggerLoading = ref(false)
const saveLoading = ref(false)
const triggerSaveLoading = ref(false)
const configModalVisible = ref(false)
const triggerConfigModalVisible = ref(false)
const configFormRef = ref()
const triggerConfigFormRef = ref()
type CronEditorMode = 'visual' | 'manual'
type VisualCronMode = 'hourly' | 'daily' | 'weekly' | 'monthly'

interface VisualScheduleState {
  mode: VisualCronMode
  minute: string
  hour: string
  dayOfMonth: string
  dayOfWeek: string
}

const searchModelId = ref<number | null>(null)
const searchEnabled = ref<boolean | null>(null)

const models = ref<any[]>([])
const configs = ref<ModelConfig[]>([])
const triggerConfigs = ref<TriggerConfigItem[]>([])
const currentModel = ref<any>(null)
const currentTrigger = ref<TriggerConfigItem | null>(null)

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const triggerPagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const configForm = reactive({
  batch_scan_enabled: false,
  batch_scan_cron: ''
})

const configCronEditorMode = ref<CronEditorMode>('visual')
const triggerCronEditorMode = ref<CronEditorMode>('visual')

const triggerConfigForm = reactive({
  batch_scan_enabled: false,
  batch_scan_cron: ''
})

const cronPattern = /^(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)\s+(\d+|\*)$/
const minuteOptions = Array.from({ length: 60 }, (_, index) => String(index))
const hourOptions = Array.from({ length: 24 }, (_, index) => String(index))
const dayOptions = Array.from({ length: 31 }, (_, index) => String(index + 1))
const weekOptions = [
  { label: '周日', value: '0' },
  { label: '周一', value: '1' },
  { label: '周二', value: '2' },
  { label: '周三', value: '3' },
  { label: '周四', value: '4' },
  { label: '周五', value: '5' },
  { label: '周六', value: '6' }
]
const cronPresets = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每天 02:00', value: '0 2 * * *' },
  { label: '每天 06:00', value: '0 6 * * *' },
  { label: '每周日 03:00', value: '0 3 * * 0' },
  { label: '每月 1 日 04:00', value: '0 4 1 * *' }
]

const createVisualScheduleState = (): VisualScheduleState => reactive({
  mode: 'daily',
  minute: '0',
  hour: '2',
  dayOfMonth: '1',
  dayOfWeek: '0'
})

const configVisualSchedule = createVisualScheduleState()
const triggerVisualSchedule = createVisualScheduleState()

const buildCronFromVisual = (state: VisualScheduleState) => {
  switch (state.mode) {
    case 'hourly':
      return `${state.minute} * * * *`
    case 'daily':
      return `${state.minute} ${state.hour} * * *`
    case 'weekly':
      return `${state.minute} ${state.hour} * * ${state.dayOfWeek}`
    case 'monthly':
      return `${state.minute} ${state.hour} ${state.dayOfMonth} * *`
    default:
      return ''
  }
}

const parseCronToVisual = (cronValue: string) => {
  const cron = (cronValue || '').trim()
  if (!cronPattern.test(cron)) return null
  const [minute, hour, dayOfMonth, month, dayOfWeek] = cron.split(/\s+/)
  if (month !== '*') return null
  if (hour === '*' && dayOfMonth === '*' && dayOfWeek === '*') {
    return { mode: 'hourly' as VisualCronMode, minute, hour: '0', dayOfMonth: '1', dayOfWeek: '0' }
  }
  if (hour !== '*' && dayOfMonth === '*' && dayOfWeek === '*') {
    return { mode: 'daily' as VisualCronMode, minute, hour, dayOfMonth: '1', dayOfWeek: '0' }
  }
  if (hour !== '*' && dayOfMonth === '*' && dayOfWeek !== '*') {
    return { mode: 'weekly' as VisualCronMode, minute, hour, dayOfMonth: '1', dayOfWeek }
  }
  if (hour !== '*' && dayOfMonth !== '*' && dayOfWeek === '*') {
    return { mode: 'monthly' as VisualCronMode, minute, hour, dayOfMonth, dayOfWeek: '0' }
  }
  return null
}

const syncVisualState = (target: VisualScheduleState, cronValue: string) => {
  const parsed = parseCronToVisual(cronValue)
  if (!parsed) return false
  target.mode = parsed.mode
  target.minute = parsed.minute
  target.hour = parsed.hour
  target.dayOfMonth = parsed.dayOfMonth
  target.dayOfWeek = parsed.dayOfWeek
  return true
}

const initCronEditor = (
  cronValue: string,
  editorMode: { value: CronEditorMode },
  visualState: VisualScheduleState
) => {
  const matched = syncVisualState(visualState, cronValue)
  editorMode.value = matched || !cronValue ? 'visual' : 'manual'
  if (editorMode.value === 'visual' && !cronValue) {
    const nextCron = buildCronFromVisual(visualState)
    return nextCron
  }
  return cronValue
}

const getCronValidationState = (value: string, enabled: boolean) => {
  const cron = (value || '').trim()
  if (!enabled && !cron) {
    return {
      status: '',
      message: '关闭定期扫描时可留空；开启后需要输入合法的 5 段 Cron 表达式。'
    }
  }
  if (!cron) {
    return {
      status: enabled ? 'error' : '',
      message: enabled ? '启用定期扫描后 Cron 表达式不能为空。' : '请输入 Cron 表达式。'
    }
  }
  if (!cronPattern.test(cron)) {
    return {
      status: 'error',
      message: 'Cron 格式错误，请使用 5 段格式，例如 0 2 * * *。'
    }
  }
  return {
    status: 'success',
    message: 'Cron 格式正确，可以保存。'
  }
}

const applyCronPreset = (
  formState: { batch_scan_enabled: boolean; batch_scan_cron: string },
  cron: string
) => {
  formState.batch_scan_enabled = true
  formState.batch_scan_cron = cron
}

const handleConfigEditorModeChange = () => {
  if (configCronEditorMode.value === 'visual') {
    if (!syncVisualState(configVisualSchedule, configForm.batch_scan_cron)) {
      configForm.batch_scan_cron = buildCronFromVisual(configVisualSchedule)
    }
  }
}

const handleTriggerEditorModeChange = () => {
  if (triggerCronEditorMode.value === 'visual') {
    if (!syncVisualState(triggerVisualSchedule, triggerConfigForm.batch_scan_cron)) {
      triggerConfigForm.batch_scan_cron = buildCronFromVisual(triggerVisualSchedule)
    }
  }
}

const validateCronField = (_rule: any, value: string) => {
  const enabled = configModalVisible.value
    ? configForm.batch_scan_enabled
    : triggerConfigModalVisible.value
      ? triggerConfigForm.batch_scan_enabled
      : false
  const validation = getCronValidationState(value, enabled)
  if (!validation.status || validation.status === 'success') {
    return Promise.resolve()
  }
  return Promise.reject(new Error(validation.message))
}

const configRules = {
  batch_scan_cron: [
    { validator: validateCronField, trigger: ['blur', 'change'] }
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

const triggerColumns = [
  { title: '触发器名称', dataIndex: 'name', key: 'name', width: 160 },
  { title: '源模型', dataIndex: 'source_model_name', key: 'source_model_name', width: 130 },
  { title: '目标模型', dataIndex: 'target_model_name', key: 'target_model_name', width: 130 },
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name', width: 120 },
  { title: '定期扫描', dataIndex: 'batch_scan_enabled', key: 'batch_scan_enabled', width: 100 },
  { title: 'Cron 表达式', dataIndex: 'batch_scan_cron', key: 'batch_scan_cron', width: 150 },
  { title: '下次执行时间', dataIndex: 'next_run_at', key: 'next_run_at', width: 180 },
  { title: '上次执行时间', dataIndex: 'last_run_at', key: 'last_run_at', width: 180 },
  { title: '上次执行状态', dataIndex: 'last_run_status', key: 'last_run_status', width: 120 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' as const }
]

const formatDateTime = (dateStr: string | null) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch {
    return dateStr
  }
}

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

const filteredTriggerConfigs = computed(() => {
  let result = triggerConfigs.value
  if (searchModelId.value !== null) {
    result = result.filter((item) => item.source_model_id === searchModelId.value || item.target_model_id === searchModelId.value)
  }
  if (searchEnabled.value !== null) {
    result = result.filter((item) => item.batch_scan_enabled === searchEnabled.value)
  }
  triggerPagination.total = result.length
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

const fetchTriggerConfigs = async () => {
  triggerLoading.value = true
  try {
    const res = await getRelationTriggers({ page: 1, per_page: 1000 })
    if (res.code === 200) {
      triggerConfigs.value = (res.data.items || []).map((item: any) => ({
        ...item,
        batch_scan_enabled: item.batch_scan_enabled || false,
        batch_scan_cron: item.batch_scan_cron || '',
        next_run_at: item.next_run_at || null,
        last_run_at: item.last_run_at || null,
        last_run_status: item.last_run_status || null
      }))
    }
  } catch (error) {
    console.error(error)
  } finally {
    triggerLoading.value = false
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
  configForm.batch_scan_cron = initCronEditor(record.batch_scan_cron, configCronEditorMode, configVisualSchedule)
  configModalVisible.value = true
}

const handleSaveConfig = async () => {
  if (!currentModel.value) return
  configForm.batch_scan_cron = configForm.batch_scan_cron.trim()
  
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
  triggerPagination.current = 1
}

const handleReset = () => {
  searchModelId.value = null
  searchEnabled.value = null
  pagination.current = 1
  triggerPagination.current = 1
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
}

const handleTriggerTableChange = (pag: any) => {
  triggerPagination.current = pag.current
  triggerPagination.pageSize = pag.pageSize
}

const handleToggleTriggerEnabled = async (record: TriggerConfigItem, checked: boolean) => {
  try {
    const res = await updateRelationTrigger(record.id, {
      batch_scan_enabled: checked,
      batch_scan_cron: record.batch_scan_cron
    })
    if (res.code === 200) {
      message.success(checked ? '已启用触发器定期扫描' : '已禁用触发器定期扫描')
      fetchTriggerConfigs()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const showTriggerConfigModal = (record: TriggerConfigItem) => {
  currentTrigger.value = record
  triggerConfigForm.batch_scan_enabled = record.batch_scan_enabled
  triggerConfigForm.batch_scan_cron = initCronEditor(record.batch_scan_cron, triggerCronEditorMode, triggerVisualSchedule)
  triggerConfigModalVisible.value = true
}

const handleSaveTriggerConfig = async () => {
  if (!currentTrigger.value) return
  triggerConfigForm.batch_scan_cron = triggerConfigForm.batch_scan_cron.trim()
  try {
    await triggerConfigFormRef.value.validate()
  } catch {
    return
  }

  triggerSaveLoading.value = true
  try {
    const res = await updateRelationTrigger(currentTrigger.value.id, {
      batch_scan_enabled: triggerConfigForm.batch_scan_enabled,
      batch_scan_cron: triggerConfigForm.batch_scan_cron
    })
    if (res.code === 200) {
      message.success('触发器定期扫描配置保存成功')
      triggerConfigModalVisible.value = false
      fetchTriggerConfigs()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    triggerSaveLoading.value = false
  }
}

const handleTriggerExecute = async (record: TriggerConfigItem) => {
  const target = triggerConfigs.value.find((item) => item.id === record.id)
  if (target) {
    target.scanning = true
  }
  try {
    const res = await executeRelationTrigger(record.id)
    if (res.code === 200) {
      message.success('已触发关系触发器扫描')
      setTimeout(() => fetchTriggerConfigs(), 1500)
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '触发失败')
  } finally {
    if (target) {
      target.scanning = false
    }
  }
}

onMounted(async () => {
  await fetchModels()
  fetchConfigs()
  fetchTriggerConfigs()
})

watch(
  configVisualSchedule,
  () => {
    if (configCronEditorMode.value === 'visual') {
      configForm.batch_scan_cron = buildCronFromVisual(configVisualSchedule)
    }
  },
  { deep: true }
)

watch(
  triggerVisualSchedule,
  () => {
    if (triggerCronEditorMode.value === 'visual') {
      triggerConfigForm.batch_scan_cron = buildCronFromVisual(triggerVisualSchedule)
    }
  },
  { deep: true }
)
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
  color: var(--app-text-muted);
}

.batch-scan-config-page__cron-help :deep(.ant-form-item-control-input) {
  min-height: auto;
}

.batch-scan-config-page__cron-message {
  margin-bottom: 8px;
  color: var(--app-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.batch-scan-config-page__cron-message.is-error {
  color: var(--ant-color-error, #ff4d4f);
}

.batch-scan-config-page__cron-message.is-success {
  color: var(--ant-color-success, #52c41a);
}

.batch-scan-config-page__cron-presets {
  width: 100%;
}

.batch-scan-config-page__cron-builder {
  margin-bottom: 8px;
  padding: 12px;
  border: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  border-radius: 10px;
  background: var(--ant-color-fill-tertiary, #fafafa);
}

.batch-scan-config-page__builder-item {
  margin-bottom: 0;
}
</style>
