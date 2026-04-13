<template>
  <div class="app-page relation-trigger-page">
    <a-row :gutter="16" class="relation-trigger-page__layout">
      <a-col :xs="24" :sm="8" :md="6" :lg="5" class="relation-trigger-page__tree-col">
        <a-card :bordered="false" class="relation-trigger-page__tree-card" title="模型目录">
          <a-input-search
            v-model:value="treeSearchKeyword"
            placeholder="搜索模型"
            allow-clear
            class="relation-trigger-page__tree-search"
            @change="handleTreeSearch"
          />
          <a-tree
            :tree-data="filteredModelTree"
            :selected-keys="selectedModelKeys"
            :field-names="{ title: 'name', key: 'id', children: 'children' }"
            :default-expand-all="true"
            @select="onModelSelect"
          >
            <template #title="{ name, title, is_model, is_category, is_all }">
              <span v-if="is_all" class="relation-trigger-page__all-node">{{ title || name }}</span>
              <span v-else-if="is_model" class="relation-trigger-page__model-node">{{ title || name }}</span>
              <span v-else-if="is_category" class="relation-trigger-page__category-node">
                <FolderOutlined />
                <span>{{ name }}</span>
              </span>
              <span v-else>{{ name }}</span>
            </template>
          </a-tree>
        </a-card>
      </a-col>

      <a-col :xs="24" :sm="16" :md="18" :lg="19" class="relation-trigger-page__content-col">
        <a-card :bordered="false" class="relation-trigger-page__canvas-card">
          <template #title>
            <div class="relation-trigger-page__canvas-title">
              <div>
                <div class="relation-trigger-page__title">{{ currentModelName || '关系触发器图谱' }}</div>
                <div class="relation-trigger-page__subtitle">
                  {{ graphSubtitle }}
                </div>
                <div v-if="currentScopeValue" class="relation-trigger-page__meta-bar">
                  <a-tag color="blue">模型 {{ graphOverview.modelCount }}</a-tag>
                  <a-tag color="processing">关系 {{ graphOverview.triggerCount }}</a-tag>
                  <a-tag color="default">泳道 {{ graphOverview.laneCount }}</a-tag>
                  <a-tag v-if="focusedModelId" color="gold">聚焦 {{ focusedModelName }}</a-tag>
                  <span class="relation-trigger-page__legend">
                    实线箭头表示触发方向，点击模型可聚焦链路，点击连线可查看详情。
                  </span>
                </div>
              </div>
            </div>
          </template>

          <template #extra>
            <a-space wrap>
              <a-button size="small" @click="zoomIn" :disabled="!graphReady">放大</a-button>
              <a-button size="small" @click="zoomOut" :disabled="!graphReady">缩小</a-button>
              <a-button size="small" @click="fitView" :disabled="!graphReady">自适应</a-button>
              <a-button size="small" @click="clearFocusMode" :disabled="!focusedModelId">取消聚焦</a-button>
              <a-button size="small" @click="refreshGraph" :loading="loading" :disabled="!currentScopeValue">刷新</a-button>
              <a-button type="primary" :disabled="!currentModelId" @click="showModal()">
                <template #icon><PlusOutlined /></template>
                新增触发器
              </a-button>
            </a-space>
          </template>

          <div v-if="!currentScopeValue" class="relation-trigger-page__empty-state">
            <a-empty description="请选择左侧模型查看关系触发器" />
          </div>
          <div v-else class="relation-trigger-page__graph-wrap">
            <div ref="graphViewport" class="relation-trigger-page__graph-viewport">
              <div
                ref="graphContainer"
                class="relation-trigger-page__graph"
                :style="{ width: `${graphCanvasSize.width}px`, height: `${graphCanvasSize.height}px` }"
              ></div>
            </div>
            <div
              v-if="!loading && ((isAllScope && graphData.nodes.length === 0) || (!isAllScope && activeTriggers.length === 0))"
              class="relation-trigger-page__graph-overlay"
            >
              <a-empty :description="currentScopeValue === 'all' ? '当前没有可展示的有效关系触发器' : '当前模型暂无有效关系触发器'" />
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑触发器' : '新增触发器'"
      width="640px"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
    >
      <a-form ref="formRef" :model="form" :rules="rules" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="源模型" name="source_model_id">
              <a-select
                v-model:value="form.source_model_id"
                placeholder="请选择源模型"
                style="width: 100%"
                @change="handleSourceModelChange"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标模型" name="target_model_id">
              <a-select
                v-model:value="form.target_model_id"
                placeholder="请选择目标模型"
                style="width: 100%"
                @change="handleTargetModelChange"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="关系类型" name="relation_type_id">
          <a-select v-model:value="form.relation_type_id" placeholder="请选择关系类型" style="width: 100%">
            <a-select-option v-for="rt in relationTypes" :key="rt.id" :value="rt.id">
              {{ rt.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="源字段" name="source_field">
          <a-select
            v-model:value="form.source_field"
            placeholder="请选择源字段"
            style="width: 100%"
            :loading="sourceFieldsLoading"
            :disabled="!form.source_model_id"
          >
            <a-select-option v-for="field in sourceModelFields" :key="field.code" :value="field.code">
              {{ field.name }} ({{ field.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标字段" name="target_field">
          <a-select
            v-model:value="form.target_field"
            placeholder="请选择目标字段"
            style="width: 100%"
            :loading="targetFieldsLoading"
            :disabled="!form.target_model_id"
          >
            <a-select-option v-for="field in targetModelFields" :key="field.code" :value="field.code">
              {{ field.name }} ({{ field.code }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="detailVisible"
      title="触发器详情"
      width="760px"
      :confirm-loading="executeLoading"
      ok-text="立即执行"
      @ok="handleExecuteTrigger"
    >
      <a-descriptions :column="1" bordered size="small" v-if="currentTrigger">
        <a-descriptions-item label="名称">{{ currentTrigger.name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="源模型">{{ currentTrigger.source_model_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="目标模型">{{ currentTrigger.target_model_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="关系类型">{{ currentTrigger.relation_type_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="匹配规则">{{ renderTriggerRule(currentTrigger) }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="currentTrigger.is_active ? 'green' : 'default'">
            {{ currentTrigger.is_active ? '启用' : '禁用' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="描述">{{ currentTrigger.description || '-' }}</a-descriptions-item>
      </a-descriptions>
      <a-divider>定期扫描配置</a-divider>
      <a-form :model="triggerScheduleForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="启用定期扫描">
              <a-switch v-model:checked="triggerScheduleForm.batch_scan_enabled" />
            </a-form-item>
          </a-col>
          <a-col :span="16">
            <a-form-item label="配置方式">
              <a-radio-group
                v-model:value="triggerScheduleEditorMode"
                button-style="solid"
                size="small"
                @change="handleTriggerScheduleEditorModeChange"
              >
                <a-radio-button value="visual">可视化计划</a-radio-button>
                <a-radio-button value="manual">手动输入</a-radio-button>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="Cron 表达式">
              <a-input
                v-model:value="triggerScheduleForm.batch_scan_cron"
                placeholder="如: 0 2 * * *"
                :disabled="!triggerScheduleForm.batch_scan_enabled"
                :readonly="triggerScheduleEditorMode === 'visual'"
                :status="triggerScheduleValidation.status"
              />
            </a-form-item>
            <div v-if="triggerScheduleEditorMode === 'visual'" class="relation-trigger-page__cron-builder">
              <a-row :gutter="[12, 12]">
                <a-col :span="24">
                  <a-form-item label="执行频率" class="relation-trigger-page__builder-item">
                    <a-select v-model:value="triggerVisualSchedule.mode">
                      <a-select-option value="hourly">每小时</a-select-option>
                      <a-select-option value="daily">每天</a-select-option>
                      <a-select-option value="weekly">每周</a-select-option>
                      <a-select-option value="monthly">每月</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="分钟" class="relation-trigger-page__builder-item">
                    <a-select v-model:value="triggerVisualSchedule.minute" show-search>
                      <a-select-option v-for="option in minuteOptions" :key="option" :value="option">
                        {{ option.padStart(2, '0') }} 分
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12" v-if="triggerVisualSchedule.mode !== 'hourly'">
                  <a-form-item label="小时" class="relation-trigger-page__builder-item">
                    <a-select v-model:value="triggerVisualSchedule.hour" show-search>
                      <a-select-option v-for="option in hourOptions" :key="option" :value="option">
                        {{ option.padStart(2, '0') }} 时
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12" v-if="triggerVisualSchedule.mode === 'weekly'">
                  <a-form-item label="星期" class="relation-trigger-page__builder-item">
                    <a-select v-model:value="triggerVisualSchedule.dayOfWeek">
                      <a-select-option v-for="option in weekOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12" v-if="triggerVisualSchedule.mode === 'monthly'">
                  <a-form-item label="日期" class="relation-trigger-page__builder-item">
                    <a-select v-model:value="triggerVisualSchedule.dayOfMonth" show-search>
                      <a-select-option v-for="option in dayOptions" :key="option" :value="option">
                        每月 {{ option }} 日
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>
            </div>
            <div
              class="relation-trigger-page__cron-message"
              :class="{
                'is-error': triggerScheduleValidation.status === 'error',
                'is-success': triggerScheduleValidation.status === 'success'
              }"
            >
              {{ triggerScheduleValidation.message }}
            </div>
            <a-space wrap class="relation-trigger-page__cron-presets">
              <a-button
                v-for="preset in cronPresets"
                :key="preset.value"
                size="small"
                @click="applyTriggerCronPreset(preset.value)"
              >
                {{ preset.label }}
              </a-button>
            </a-space>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="下次执行时间">
              <span>{{ formatDateTime(currentTrigger?.next_run_at || null) }}</span>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="上次执行状态">
              <a-tag v-if="currentTrigger?.last_run_status === 'success'" color="green">成功</a-tag>
              <a-tag v-else-if="currentTrigger?.last_run_status === 'failed'" color="error">失败</a-tag>
              <a-tag v-else-if="currentTrigger?.last_run_status === 'skipped'" color="default">跳过</a-tag>
              <span v-else>-</span>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="openLogModal(currentTrigger)" :disabled="!currentTrigger">日志</a-button>
          <a-button @click="handleEditFromDetail" :disabled="!currentTrigger">编辑</a-button>
          <a-button @click="handleSaveTriggerSchedule" :loading="scheduleSaveLoading" :disabled="!currentTrigger">保存扫描配置</a-button>
          <a-button @click="detailVisible = false">关闭</a-button>
          <a-button type="primary" :loading="executeLoading" :disabled="!currentTrigger" @click="handleExecuteTrigger">
            立即执行
          </a-button>
        </a-space>
      </template>
    </a-modal>

    <a-modal
      v-model:open="nodeDetailVisible"
      :title="nodeDetailTitle"
      width="980px"
      wrap-class-name="relation-trigger-page__node-modal"
      :footer="null"
    >
      <div class="relation-trigger-page__node-modal-summary">
        共 {{ nodeRelations.length }} 条关系触发器
      </div>
      <a-table
        class="relation-trigger-page__node-table"
        :columns="nodeRelationColumns"
        :data-source="nodeRelations"
        :pagination="false"
        :scroll="{ x: 900 }"
        row-key="id"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a-tooltip :title="record.name || '-'">
              <span class="relation-trigger-page__cell-ellipsis">
                {{ record.name || '-' }}
              </span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'direction'">
            <a-tag :color="record.source_model_id === currentNodeModelId ? 'blue' : 'green'">
              {{ record.source_model_id === currentNodeModelId ? '源 -> 目标' : '目标 <- 源' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'peer_model_name'">
            <a-tooltip :title="record.peer_model_name || '-'">
              <span class="relation-trigger-page__cell-ellipsis">
                {{ record.peer_model_name || '-' }}
              </span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'relation_type_name'">
            <a-tooltip :title="record.relation_type_name || '-'">
              <span class="relation-trigger-page__cell-ellipsis">
                {{ record.relation_type_name || '-' }}
              </span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="record.is_active ? 'green' : 'default'">
              {{ record.is_active ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'rule'">
            <a-tooltip :title="renderTriggerRule(record)">
              <span class="relation-trigger-page__cell-ellipsis">
                {{ renderTriggerRule(record) }}
              </span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'action'">
            <div class="relation-trigger-page__action-cell">
              <a-button type="link" size="small" @click="openTriggerDetail(record)">查看详情</a-button>
              <a-popconfirm
                title="确定删除这条关系触发器？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="handleDeleteTrigger(record)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </template>
        </template>
      </a-table>
    </a-modal>

    <a-modal
      v-model:open="logVisible"
      title="触发器执行日志"
      width="900px"
      :footer="null"
    >
      <a-table
        :columns="logColumns"
        :data-source="logs"
        :loading="logLoading"
        :pagination="logPagination"
        @change="handleLogTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'success' ? 'green' : record.status === 'failed' ? 'red' : 'default'">
              {{ record.status }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
        </template>
      </a-table>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, createApp, h, nextTick, onActivated, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { FolderOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { Graph } from '@antv/g6'
import {
  createRelationTrigger,
  deleteRelationTrigger,
  executeRelationTrigger,
  getRelationTriggers,
  getRelationTypes,
  updateRelationTrigger
} from '@/api/cmdb-relation'
import { getTriggerLogs } from '@/api/trigger'
import { getDictItemsByTypeCode, getModelDetail, getModels, getModelsTree } from '@/api/cmdb'
import { extractFieldsFromFormConfig } from '@/utils/formConfigFields'
import { getModelIconAssetUrl, getModelIconComponent } from '@/utils/cmdbModelIcons'

interface Field {
  id?: string | number
  code: string
  name: string
  field_type: string
}

interface RelationGraphNode {
  id: string
  model_id: number
  name: string
  icon?: string
  icon_url?: string
  category: string
  laneIndex: number
  x: number
  y: number
  row: number
}

interface LaneMeta {
  key: string
  label: string
  top: number
  height: number
  centerY: number
  railStartX: number
  railEndX: number
  labelX: number
  isUnknown: boolean
  count: number
}

type CronEditorMode = 'visual' | 'manual'
type VisualCronMode = 'hourly' | 'daily' | 'weekly' | 'monthly'

interface VisualScheduleState {
  mode: VisualCronMode
  minute: string
  hour: string
  dayOfMonth: string
  dayOfWeek: string
}

const loading = ref(false)
const submitLoading = ref(false)
const executeLoading = ref(false)
const scheduleSaveLoading = ref(false)
const modalVisible = ref(false)
const detailVisible = ref(false)
const nodeDetailVisible = ref(false)
const logVisible = ref(false)
const logLoading = ref(false)
const isEdit = ref(false)
const formRef = ref()
const treeSearchKeyword = ref('')
const modelTree = ref<any[]>([])
const filteredModelTree = ref<any[]>([])
const selectedModelKeys = ref<Array<string | number>>([])
const currentModelId = ref<number | null>(null)
const currentModelName = ref('')
const currentScopeValue = ref<number | 'all' | null>(null)
const models = ref<any[]>([])
const modeTypeLabelMap = ref<Record<string, string>>({})
const relationTypes = ref<any[]>([])
const triggers = ref<any[]>([])
const logs = ref<any[]>([])
const currentTrigger = ref<any>(null)
const currentNodeModelId = ref<number | null>(null)
const currentNodeModelName = ref('')
const sourceFieldsLoading = ref(false)
const targetFieldsLoading = ref(false)
const sourceModelFields = ref<Field[]>([])
const targetModelFields = ref<Field[]>([])
const graphViewport = ref<HTMLElement>()
const graphContainer = ref<HTMLElement>()
const graphReady = ref(false)
const focusedModelId = ref<number | null>(null)
const graphCanvasSize = reactive({ width: 960, height: 560 })
const allScopeNodeXMap = ref<Record<number, number>>({})
const singleScopeNodePositionMap = ref<Record<string, Record<number, { x: number; y: number }>>>({})
let graph: any = null
const builtinIconDataUrlCache: Record<string, string> = {}
const iconUrlStatus = ref<Record<string, 'ok' | 'fail'>>({})

const form = reactive({
  id: null as number | null,
  name: '',
  source_model_id: null as number | null,
  target_model_id: null as number | null,
  relation_type_id: null as number | null,
  trigger_type: 'reference',
  source_field: '',
  target_field: '',
  description: ''
})

const triggerScheduleForm = reactive({
  batch_scan_enabled: false,
  batch_scan_cron: ''
})

const triggerScheduleEditorMode = ref<CronEditorMode>('visual')
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

const syncTriggerVisualSchedule = (cronValue: string) => {
  const parsed = parseCronToVisual(cronValue)
  if (!parsed) return false
  triggerVisualSchedule.mode = parsed.mode
  triggerVisualSchedule.minute = parsed.minute
  triggerVisualSchedule.hour = parsed.hour
  triggerVisualSchedule.dayOfMonth = parsed.dayOfMonth
  triggerVisualSchedule.dayOfWeek = parsed.dayOfWeek
  return true
}

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  source_model_id: [{ required: true, message: '请选择源模型', trigger: 'change' }],
  target_model_id: [{ required: true, message: '请选择目标模型', trigger: 'change' }],
  relation_type_id: [{ required: true, message: '请选择关系类型', trigger: 'change' }],
  source_field: [{ required: true, message: '请选择源字段', trigger: 'change' }],
  target_field: [{ required: true, message: '请选择目标字段', trigger: 'change' }]
}

const logPagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const logColumns = [
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '源CI', dataIndex: 'source_ci_name', key: 'source_ci_name', width: 160 },
  { title: '目标CI', dataIndex: 'target_ci_name', key: 'target_ci_name', width: 160 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true }
]

const nodeRelationColumns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  { title: '方向', key: 'direction', width: 110 },
  { title: '对端模型', dataIndex: 'peer_model_name', key: 'peer_model_name', width: 140 },
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name', width: 120 },
  { title: '匹配规则', key: 'rule', width: 200 },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'action', width: 140, fixed: 'right' }
]

const modelMap = computed<Record<number, any>>(() => {
  const out: Record<number, any> = {}
  models.value.forEach((item) => {
    out[item.id] = item
  })
  return out
})

const relationTypeMap = computed<Record<number, any>>(() => {
  const out: Record<number, any> = {}
  relationTypes.value.forEach((item) => {
    out[item.id] = item
  })
  return out
})

const isAllScope = computed(() => currentScopeValue.value === 'all')

const graphSubtitle = computed(() => {
  if (!currentScopeValue.value) {
    return '请选择左侧模型查看触发器关系图谱。'
  }
  if (isAllScope.value) {
    return '展示全部模型（含未配置触发关系模型），按模型类型泳道分层排布，可聚焦查看触发链路。'
  }
  return '展示当前模型相关的有效触发器关系，采用层级布局，仅显示图标与连线。'
})

const activeTriggers = computed(() => triggers.value.filter((item) => item.is_active))
const laneMeta = computed(() => graphData.value.lanes || [])
const graphOverview = computed(() => ({
  modelCount: graphData.value.nodes.length,
  triggerCount: graphData.value.edges.length,
  laneCount: laneMeta.value.length
}))
const focusedModelName = computed(() => {
  if (!focusedModelId.value) return ''
  return modelMap.value[focusedModelId.value]?.name || `模型 ${focusedModelId.value}`
})
const focusedRelatedIds = computed(() => {
  if (!focusedModelId.value) return new Set<number>()
  const ids = new Set<number>([focusedModelId.value])
  activeTriggers.value.forEach((item) => {
    if (item.source_model_id === focusedModelId.value || item.target_model_id === focusedModelId.value) {
      ids.add(item.source_model_id)
      ids.add(item.target_model_id)
    }
  })
  return ids
})
const focusedLaneKey = computed(() => {
  if (!focusedModelId.value || !isAllScope.value) return ''
  const focusedNode = graphData.value.nodes.find((node) => node.model_id === focusedModelId.value)
  if (!focusedNode) return ''
  return laneMeta.value[focusedNode.laneIndex]?.key || ''
})
const laneBoundsByModelId = computed<Record<number, { minX: number; maxX: number; centerY: number }>>(() => {
  const output: Record<number, { minX: number; maxX: number; centerY: number }> = {}
  graphData.value.nodes.forEach((node) => {
    const lane = laneMeta.value[node.laneIndex]
    if (!lane) return
    output[node.model_id] = {
      minX: lane.railStartX + 30,
      maxX: lane.railEndX - 30,
      centerY: lane.centerY
    }
  })
  return output
})
const triggerScheduleValidation = computed(() => {
  const cron = triggerScheduleForm.batch_scan_cron.trim()
  if (!triggerScheduleForm.batch_scan_enabled && !cron) {
    return {
      status: '',
      message: '关闭定期扫描时可留空；开启后需要输入合法的 5 段 Cron 表达式。'
    }
  }
  if (!cron) {
    return {
      status: triggerScheduleForm.batch_scan_enabled ? 'error' : '',
      message: triggerScheduleForm.batch_scan_enabled ? '启用定期扫描后 Cron 表达式不能为空。' : '请输入 Cron 表达式。'
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
})

const nodeRelations = computed(() => {
  if (!currentNodeModelId.value) return []
  return activeTriggers.value
    .filter((item) => item.source_model_id === currentNodeModelId.value || item.target_model_id === currentNodeModelId.value)
    .map((item) => ({
      ...item,
      peer_model_name: item.source_model_id === currentNodeModelId.value
        ? item.target_model_name || '-'
        : item.source_model_name || '-'
    }))
})

const nodeDetailTitle = computed(() => currentNodeModelName.value ? `${currentNodeModelName.value} 的关系触发器` : '模型关系')

const normalizeTriggerCondition = (trigger: any) => {
  const condition = trigger?.trigger_condition
  if (condition && typeof condition === 'object') {
    return condition
  }
  if (typeof condition === 'string') {
    try {
      return JSON.parse(condition)
    } catch {
      return {}
    }
  }
  return {}
}

const UNKNOWN_LANE_LABEL = '未分类'

const normalizeLaneCategory = (category: string | undefined | null) => {
  const text = String(category || '').trim()
  if (!text) return UNKNOWN_LANE_LABEL
  const lower = text.toLowerCase()
  if (
    text === '未知'
    || text === '未分类'
    || text === '待分类'
    || lower === 'unknown'
    || lower === 'uncategorized'
    || lower === 'unset'
  ) {
    return UNKNOWN_LANE_LABEL
  }
  return text
}

const resolveModelLaneCategory = (model: any) => {
  const typeCode = String(
    model?.model_type_code
    ?? model?.config?.model_type_code
    ?? model?.mode_type
    ?? ''
  ).trim()
  if (!typeCode) return UNKNOWN_LANE_LABEL
  const typeLabel = modeTypeLabelMap.value[typeCode] || typeCode
  return normalizeLaneCategory(typeLabel)
}

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const getLaneElementKey = (laneKey: string) => encodeURIComponent(String(laneKey))
const getSingleScopeKey = () => (
  typeof currentScopeValue.value === 'number' ? `model-${currentScopeValue.value}` : ''
)
const getSingleScopeNodePositions = () => {
  const scopeKey = getSingleScopeKey()
  if (!scopeKey) return {}
  return singleScopeNodePositionMap.value[scopeKey] || {}
}
const setSingleScopeNodePosition = (modelId: number, x: number, y: number) => {
  const scopeKey = getSingleScopeKey()
  if (!scopeKey || !modelId) return
  const scopeMap = singleScopeNodePositionMap.value[scopeKey] || {}
  singleScopeNodePositionMap.value = {
    ...singleScopeNodePositionMap.value,
    [scopeKey]: {
      ...scopeMap,
      [modelId]: { x, y }
    }
  }
}
const hasSingleScopeNodePositions = () => Object.keys(getSingleScopeNodePositions()).length > 0
const syncSingleScopeNodePositionsFromGraph = () => {
  if (!graph || isAllScope.value) return
  const scopeKey = getSingleScopeKey()
  if (!scopeKey) return
  const output: Record<number, { x: number; y: number }> = {}
  const rawNodes = typeof graph.getNodeData === 'function'
    ? graph.getNodeData()
    : (typeof graph.getData === 'function' ? graph.getData()?.nodes : [])
  ;(rawNodes || []).forEach((item: any) => {
    const modelId = Number(item?.model_id ?? getModelNodeIdFromGraphNode(item?.id))
    if (!modelId || Number.isNaN(modelId)) return
    const x = Number(item?.style?.x ?? item?.x)
    const y = Number(item?.style?.y ?? item?.y)
    if (Number.isNaN(x) || Number.isNaN(y)) return
    output[modelId] = { x, y }
  })
  if (Object.keys(output).length === 0) return
  singleScopeNodePositionMap.value = {
    ...singleScopeNodePositionMap.value,
    [scopeKey]: output
  }
}

const getAllScopeVisualScale = () => {
  const viewportWidth = graphViewport.value?.clientWidth || graphCanvasSize.width || 1360
  const laneCount = Math.max(laneMeta.value.length, 1)
  const screenScale = clamp(viewportWidth / 1460, 0.88, 1.18)
  const densityScale = clamp(1.12 - (laneCount - 4) * 0.035, 0.78, 1.08)
  return clamp(screenScale * densityScale, 0.76, 1.16)
}

const buildEdgeCurveOffset = ({
  trigger,
  directionIndex,
  sameDirectionCount,
  hasReverseDirection,
  laneDistance,
  sourceX,
  targetX
}: {
  trigger: any
  directionIndex: number
  sameDirectionCount: number
  hasReverseDirection: boolean
  laneDistance: number
  sourceX: number
  targetX: number
}) => {
  const spreadOffset = sameDirectionCount > 1 ? (directionIndex - (sameDirectionCount - 1) / 2) * 30 : 0
  const horizontalDirection = sourceX <= targetX ? 1 : -1
  if (!isAllScope.value) {
    const baseOffset = hasReverseDirection ? 48 : 24
    return horizontalDirection * baseOffset + spreadOffset
  }
  const baseOffset = hasReverseDirection ? 70 : 44
  const laneOffset = laneDistance > 0 ? 88 + laneDistance * 56 : 26
  const directionSign = trigger.source_model_id === trigger.target_model_id
    ? (directionIndex % 2 === 0 ? 1 : -1)
    : horizontalDirection
  return directionSign * (baseOffset + laneOffset) + spreadOffset
}

const graphData = computed(() => {
  const nodeMap = new Map<number, RelationGraphNode>()
  const edgeFamilyCount = new Map<string, number>()
  const edgeDirectionCount = new Map<string, number>()
  const edgeDirectionIndex = new Map<string, number>()
  const laneMeta: LaneMeta[] = []
  const laneLabelX = 126
  const railStartX = 218
  const laneTopBase = 64
  const laneGap = 48
  const laneHeight = 108
  const nodeGap = 168

  activeTriggers.value.forEach((trigger) => {
    const familyKey = [trigger.source_model_id, trigger.target_model_id].sort((a, b) => a - b).join('-')
    const directionKey = `${trigger.source_model_id}-${trigger.target_model_id}`
    edgeFamilyCount.set(familyKey, (edgeFamilyCount.get(familyKey) || 0) + 1)
    edgeDirectionCount.set(directionKey, (edgeDirectionCount.get(directionKey) || 0) + 1)
  })

  const addModelNode = (model: any) => {
    if (!model?.id) return
    nodeMap.set(Number(model.id), {
      id: `model-${model.id}`,
      model_id: Number(model.id),
      name: model.name,
      icon: model.icon,
      icon_url: model.icon_url,
      category: resolveModelLaneCategory(model),
      laneIndex: 0,
      x: 0,
      y: 0,
      row: 0
    })
  }

  if (isAllScope.value) {
    models.value.forEach((model) => {
      addModelNode(model)
    })
  } else {
    activeTriggers.value.forEach((trigger) => {
      const sourceModel = modelMap.value[trigger.source_model_id]
      const targetModel = modelMap.value[trigger.target_model_id]
      if (sourceModel) addModelNode(sourceModel)
      if (targetModel) addModelNode(targetModel)
    })
  }

  activeTriggers.value.forEach((trigger) => {
    const sourceModel = modelMap.value[trigger.source_model_id]
    const targetModel = modelMap.value[trigger.target_model_id]
    if (!sourceModel || !targetModel) return
    if (!nodeMap.has(Number(sourceModel.id))) addModelNode(sourceModel)
    if (!nodeMap.has(Number(targetModel.id))) addModelNode(targetModel)
  })

  const buildRelationEdges = () => activeTriggers.value.map((trigger) => {
    const relationType = relationTypeMap.value[trigger.relation_type_id] || {}
    const directionKey = `${trigger.source_model_id}-${trigger.target_model_id}`
    const reverseKey = `${trigger.target_model_id}-${trigger.source_model_id}`
    const familyKey = [trigger.source_model_id, trigger.target_model_id].sort((a, b) => a - b).join('-')
    const currentIndex = edgeDirectionIndex.get(directionKey) || 0
    edgeDirectionIndex.set(directionKey, currentIndex + 1)
    const sameDirectionCount = edgeDirectionCount.get(directionKey) || 1
    const hasReverseDirection = edgeDirectionCount.has(reverseKey)
    const sourceNode = nodeMap.get(Number(trigger.source_model_id))
    const targetNode = nodeMap.get(Number(trigger.target_model_id))
    const laneDistance = Math.abs((sourceNode?.laneIndex ?? 0) - (targetNode?.laneIndex ?? 0))
    const curveOffset = buildEdgeCurveOffset({
      trigger,
      directionIndex: currentIndex,
      sameDirectionCount,
      hasReverseDirection,
      laneDistance,
      sourceX: sourceNode?.x ?? Number(trigger.source_model_id),
      targetX: targetNode?.x ?? Number(trigger.target_model_id)
    })

    return {
      id: `trigger-${trigger.id}`,
      source: `model-${trigger.source_model_id}`,
      target: `model-${trigger.target_model_id}`,
      label: relationType.name || trigger.relation_type_name || trigger.name,
      trigger,
      relationType,
      curveOffset: isAllScope.value || (edgeFamilyCount.get(familyKey) || 0) > 1 ? curveOffset : 0,
      familyCount: edgeFamilyCount.get(familyKey) || 1,
      directionIndex: currentIndex,
      sameDirectionCount,
      laneDistance
    }
  })

  if (!isAllScope.value) {
    return {
      nodes: Array.from(nodeMap.values()),
      edges: buildRelationEdges(),
      lanes: [],
      width: Math.max(960, graphViewport.value?.clientWidth || 0),
      height: 560
    }
  }

  const laneSet = new Set<string>()
  Array.from(nodeMap.values()).forEach((node) => {
    if (node.category !== UNKNOWN_LANE_LABEL) {
      laneSet.add(node.category)
    }
  })
  const laneKeys = Array.from(laneSet)
  if (Array.from(nodeMap.values()).some((node) => node.category === UNKNOWN_LANE_LABEL)) laneKeys.push(UNKNOWN_LANE_LABEL)

  laneKeys.forEach((laneKey, laneIndex) => {
    const nodesInLane = Array.from(nodeMap.values()).filter((node) => node.category === laneKey)
    const top = laneTopBase + laneMeta.reduce((sum, item) => sum + item.height, 0) + laneIndex * laneGap
    const centerY = top + laneHeight / 2
    laneMeta.push({
      key: laneKey,
      label: laneKey,
      top,
      height: laneHeight,
      centerY,
      railStartX,
      railEndX: railStartX + 520,
      labelX: laneLabelX,
      isUnknown: laneKey === UNKNOWN_LANE_LABEL,
      count: nodesInLane.length
    })

    nodesInLane.forEach((node, index) => {
      const row = 0
      const col = index
      const defaultX = railStartX + 58 + col * nodeGap
      const persistedX = allScopeNodeXMap.value[node.model_id]
      node.laneIndex = laneIndex
      node.row = row
      node.x = typeof persistedX === 'number' ? persistedX : defaultX
      node.y = centerY
    })
  })

  const nodes = Array.from(nodeMap.values())
  const maxX = nodes.reduce((max, node) => Math.max(max, node.x), 0)
  const maxLaneBottom = laneMeta.reduce((max, lane) => Math.max(max, lane.top + lane.height), 0)
  const width = Math.max(1360, maxX + 260, (graphViewport.value?.clientWidth || 0))
  const railEndX = Math.max(width - 52, railStartX + 420)

  laneMeta.forEach((lane) => {
    lane.railEndX = railEndX
  })

  nodes.forEach((node) => {
    const lane = laneMeta[node.laneIndex]
    if (!lane) return
    node.y = lane.centerY
    node.x = clamp(node.x, lane.railStartX + 30, lane.railEndX - 30)
  })

  return {
    nodes,
    edges: buildRelationEdges(),
    lanes: laneMeta,
    width,
    height: Math.max(620, maxLaneBottom + 96)
  }
})

const fetchModels = async () => {
  const res = await getModels({ page: 1, per_page: 1000 })
  if (res.code === 200) {
    models.value = res.data.items || []
  }
}

const flattenModeTypeDictItems = (
  items: any[],
  parentLabel = '',
  output: Record<string, string> = {}
): Record<string, string> => {
  ;(items || []).forEach((item: any) => {
    const code = String(item?.code || '').trim()
    const ownLabel = String(item?.label || item?.name || code).trim()
    const mergedLabel = parentLabel ? `${parentLabel} / ${ownLabel}` : ownLabel
    if (code) {
      output[code] = mergedLabel || code
    }
    if (Array.isArray(item?.children) && item.children.length > 0) {
      flattenModeTypeDictItems(item.children, mergedLabel, output)
    }
  })
  return output
}

const fetchModeTypeDict = async () => {
  try {
    const res = await getDictItemsByTypeCode('mode_type', { enabled: true })
    if (res.code === 200) {
      modeTypeLabelMap.value = flattenModeTypeDictItems(res.data?.items || [])
    } else {
      modeTypeLabelMap.value = {}
    }
  } catch {
    modeTypeLabelMap.value = {}
  }
}

const fetchModelTree = async () => {
  const res = await getModelsTree()
  if (res.code !== 200) return
  const treeData = Array.isArray(res.data) ? res.data : []
  const normalizedTreeData = treeData.filter((node: any) => {
    const id = String(node?.id || '').trim().toLowerCase()
    if (id === 'all-models' || id === 'all') return false
    if (node?.is_all) return false
    const title = String(node?.title || node?.name || '').trim()
    return title !== '全部'
  })
  modelTree.value = normalizedTreeData
  filteredModelTree.value = [
    { id: 'all-models', name: '全部', title: '全部', is_all: true, children: [] },
    ...normalizedTreeData
  ]
  if (!currentScopeValue.value) {
    selectedModelKeys.value = ['all-models']
    currentScopeValue.value = 'all'
    currentModelId.value = null
    currentModelName.value = '全部模型'
  }
}

const fetchRelationTypes = async () => {
  const res = await getRelationTypes({ page: 1, per_page: 1000 })
  if (res.code === 200) {
    relationTypes.value = res.data.items || []
  }
}

const fetchTriggers = async () => {
  if (!currentScopeValue.value) {
    triggers.value = []
    return
  }
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: 1,
      per_page: 1000,
      active_only: 1
    }
    if (currentScopeValue.value !== 'all') {
      params.model_id = currentScopeValue.value
    }
    const res = await getRelationTriggers(params)
    if (res.code === 200) {
      triggers.value = Array.isArray(res.data?.items) ? res.data.items : []
      focusedModelId.value = null
      await nextTick()
      if (!graph && graphContainer.value) {
        initGraph()
      }
      await renderGraph()
    }
  } finally {
    loading.value = false
  }
}

const fetchModelFields = async (modelId: number, isSource: boolean) => {
  if (isSource) sourceFieldsLoading.value = true
  else targetFieldsLoading.value = true
  try {
    const res = await getModelDetail(modelId)
    if (res.code === 200) {
      const fields = extractFieldsFromFormConfig(res.data?.form_config).map((field) => ({
        id: field.id,
        code: field.code,
        name: field.name,
        field_type: field.field_type
      }))
      if (isSource) sourceModelFields.value = fields
      else targetModelFields.value = fields
    }
  } finally {
    if (isSource) sourceFieldsLoading.value = false
    else targetFieldsLoading.value = false
  }
}

const handleSourceModelChange = (modelId: number) => {
  form.source_field = ''
  sourceModelFields.value = []
  if (modelId) void fetchModelFields(modelId, true)
}

const handleTargetModelChange = (modelId: number) => {
  form.target_field = ''
  targetModelFields.value = []
  if (modelId) void fetchModelFields(modelId, false)
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    source_model_id: currentModelId.value,
    target_model_id: null,
    relation_type_id: null,
    trigger_type: 'reference',
    source_field: '',
    target_field: '',
    description: ''
  })
  sourceModelFields.value = []
  targetModelFields.value = []
}

const showModal = async (record?: any) => {
  isEdit.value = Boolean(record)
  if (record) {
    const triggerCondition = normalizeTriggerCondition(record)
    Object.assign(form, {
      id: record.id,
      name: record.name,
      source_model_id: record.source_model_id,
      target_model_id: record.target_model_id,
      relation_type_id: record.relation_type_id,
      trigger_type: record.trigger_type,
      source_field: triggerCondition.source_field || '',
      target_field: triggerCondition.target_field || '',
      description: record.description || ''
    })
    sourceModelFields.value = []
    targetModelFields.value = []
    if (record.source_model_id) await fetchModelFields(record.source_model_id, true)
    if (record.target_model_id) await fetchModelFields(record.target_model_id, false)
  } else {
    resetForm()
    if (form.source_model_id) await fetchModelFields(form.source_model_id, true)
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitLoading.value = true
  try {
    const payload = {
      name: form.name,
      source_model_id: form.source_model_id,
      target_model_id: form.target_model_id,
      relation_type_id: form.relation_type_id,
      trigger_type: form.trigger_type,
      description: form.description,
      trigger_condition: {
        source_field: form.source_field,
        target_field: form.target_field
      }
    }
    const res = isEdit.value
      ? await updateRelationTrigger(form.id!, payload)
      : await createRelationTrigger(payload)
    if (res.code === 200) {
      message.success(isEdit.value ? '更新成功' : '创建成功')
      modalVisible.value = false
      await fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const renderTriggerRule = (trigger: any) => {
  const triggerCondition = normalizeTriggerCondition(trigger)
  const sourceField = triggerCondition.source_field || '-'
  const targetField = triggerCondition.target_field || '-'
  return `${sourceField} = ${targetField}`
}

const openTriggerDetail = (trigger: any) => {
  currentTrigger.value = trigger
  triggerScheduleForm.batch_scan_enabled = Boolean(trigger?.batch_scan_enabled)
  triggerScheduleForm.batch_scan_cron = trigger?.batch_scan_cron || ''
  const matched = syncTriggerVisualSchedule(triggerScheduleForm.batch_scan_cron)
  triggerScheduleEditorMode.value = matched || !triggerScheduleForm.batch_scan_cron ? 'visual' : 'manual'
  if (triggerScheduleEditorMode.value === 'visual' && !triggerScheduleForm.batch_scan_cron) {
    triggerScheduleForm.batch_scan_cron = buildCronFromVisual(triggerVisualSchedule)
  }
  detailVisible.value = true
}

const openNodeDetail = (modelId: number) => {
  const model = modelMap.value[modelId]
  currentNodeModelId.value = modelId
  currentNodeModelName.value = model?.name || ''
  nodeDetailVisible.value = true
}

const handleEditFromDetail = async () => {
  if (!currentTrigger.value) return
  detailVisible.value = false
  await showModal(currentTrigger.value)
}

const handleExecuteTrigger = async () => {
  if (!currentTrigger.value?.id) return
  executeLoading.value = true
  try {
    const res = await executeRelationTrigger(currentTrigger.value.id)
    if (res.code === 200) {
      const data = res.data || {}
      message.success(`执行完成：处理 ${data.processed_ci_count || 0} 个CI，创建 ${data.created_count || 0} 条关系`)
      await fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '执行失败')
  } finally {
    executeLoading.value = false
  }
}

const handleSaveTriggerSchedule = async () => {
  if (!currentTrigger.value?.id) return
  triggerScheduleForm.batch_scan_cron = triggerScheduleForm.batch_scan_cron.trim()
  if (triggerScheduleValidation.value.status === 'error') {
    message.warning(triggerScheduleValidation.value.message)
    return
  }
  scheduleSaveLoading.value = true
  try {
    const res = await updateRelationTrigger(currentTrigger.value.id, {
      batch_scan_enabled: triggerScheduleForm.batch_scan_enabled,
      batch_scan_cron: triggerScheduleForm.batch_scan_cron
    })
    if (res.code === 200) {
      message.success('触发器定期扫描配置已保存')
      currentTrigger.value = {
        ...currentTrigger.value,
        batch_scan_enabled: res.data?.batch_scan_enabled ?? triggerScheduleForm.batch_scan_enabled,
        batch_scan_cron: res.data?.batch_scan_cron ?? triggerScheduleForm.batch_scan_cron
      }
      await fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    scheduleSaveLoading.value = false
  }
}

const handleDeleteTrigger = async (record: any) => {
  if (!record?.id) return
  try {
    const res = await deleteRelationTrigger(record.id)
    if (res.code === 200) {
      message.success('删除成功')
      if (currentTrigger.value?.id === record.id) {
        currentTrigger.value = null
        detailVisible.value = false
      }
      await fetchTriggers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const openLogModal = (record: any) => {
  if (!record) return
  currentTrigger.value = record
  logPagination.current = 1
  logVisible.value = true
  void fetchLogs()
}

const fetchLogs = async () => {
  if (!currentTrigger.value?.id) return
  logLoading.value = true
  try {
    const res = await getTriggerLogs(currentTrigger.value.id, {
      page: logPagination.current,
      page_size: logPagination.pageSize
    })
    const payload = res?.data?.items ? res.data.items : res?.data
    logs.value = Array.isArray(payload) ? payload : []
    logPagination.total = res?.data?.total ?? logs.value.length
  } finally {
    logLoading.value = false
  }
}

const handleLogTableChange = (pag: any) => {
  logPagination.current = pag.current
  logPagination.pageSize = pag.pageSize
  void fetchLogs()
}

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

const findFirstModelNode = (nodes: any[]): any | null => {
  for (const node of nodes) {
    if (node.is_model) return node
    if (Array.isArray(node.children) && node.children.length) {
      const hit = findFirstModelNode(node.children)
      if (hit) return hit
    }
  }
  return null
}

const filterTree = (nodes: any[], keyword: string): any[] => {
  return nodes
    .map((node) => {
      const clone = { ...node }
      const text = String(node.title || node.name || '').toLowerCase()
      const matched = text.includes(keyword)
      if (Array.isArray(node.children) && node.children.length) {
        clone.children = filterTree(node.children, keyword)
      }
      if (matched || (clone.children && clone.children.length)) {
        return clone
      }
      return null
    })
    .filter(Boolean)
}

const handleTreeSearch = () => {
  const keyword = treeSearchKeyword.value.trim().toLowerCase()
  const allNode = { id: 'all-models', name: '全部', title: '全部', is_all: true, children: [] }
  filteredModelTree.value = keyword ? [allNode, ...filterTree(modelTree.value, keyword)] : [allNode, ...modelTree.value]
}

const getSelectedTreeNode = (info: any) => {
  return info?.node?.dataRef || info?.node || null
}

const onModelSelect = async (keys: any, info: any) => {
  selectedModelKeys.value = keys
  const node = getSelectedTreeNode(info)
  if (node?.is_all) {
    currentScopeValue.value = 'all'
    currentModelId.value = null
    currentModelName.value = '全部模型'
    focusedModelId.value = null
    await nextTick()
    if (graphContainer.value) {
      initGraph()
    }
    await fetchTriggers()
    return
  }
  if (!node?.is_model) return
  currentScopeValue.value = Number(node.model_id)
  currentModelId.value = Number(node.model_id)
  currentModelName.value = String(node.title || node.name || '')
  focusedModelId.value = null
  await nextTick()
  if (graphContainer.value) {
    initGraph()
  }
  await fetchTriggers()
}

const getThemeColor = (name: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const getAntdIconSvgMarkup = (iconName?: string) => {
  const iconComponent = getModelIconComponent(iconName)
  const container = document.createElement('div')
  const app = createApp({
    render() {
      return h(iconComponent, {
        style: {
          fontSize: '28px',
          color: getThemeColor('--app-accent', '#1677ff')
        }
      })
    }
  })
  app.mount(container)
  const svg = container.querySelector('svg') as SVGElement | null
  if (!svg) {
    app.unmount()
    return ''
  }
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  svg.setAttribute('width', '28')
  svg.setAttribute('height', '28')
  svg.style.display = 'block'
  const content = svg.outerHTML
  app.unmount()
  return content
}

const toSvgBase64DataUrl = (svg: string) => {
  const utf8 = unescape(encodeURIComponent(svg))
  const base64 = window.btoa(utf8)
  return `data:image/svg+xml;base64,${base64}`
}

const getBuiltinIconDataUrl = (iconName?: string) => {
  const cacheKey = iconName || 'AppstoreOutlined'
  if (builtinIconDataUrlCache[cacheKey]) {
    return builtinIconDataUrlCache[cacheKey]
  }
  const assetUrl = getModelIconAssetUrl(cacheKey)
  if (assetUrl) {
    builtinIconDataUrlCache[cacheKey] = assetUrl
    return assetUrl
  }
  const svg = getAntdIconSvgMarkup(cacheKey)
  const dataUrl = svg ? toSvgBase64DataUrl(svg) : ''
  builtinIconDataUrlCache[cacheKey] = dataUrl
  return dataUrl
}

const ensureIconUrlStatus = (url?: string) => {
  if (!url || iconUrlStatus.value[url]) return
  const img = new Image()
  img.onload = () => {
    iconUrlStatus.value = { ...iconUrlStatus.value, [url]: 'ok' }
    nextTick(() => renderGraph())
  }
  img.onerror = () => {
    iconUrlStatus.value = { ...iconUrlStatus.value, [url]: 'fail' }
    nextTick(() => renderGraph())
  }
  img.src = url
}

const getNodeIconSrc = (node: RelationGraphNode) => {
  if (node.icon_url) {
    ensureIconUrlStatus(node.icon_url)
    if (iconUrlStatus.value[node.icon_url] === 'ok') {
      return node.icon_url
    }
  }
  return getBuiltinIconDataUrl(node.icon || 'AppstoreOutlined')
}

const applyGraphData = async (data: { nodes: any[]; edges: any[] }) => {
  if (!graph) return
  if (typeof graph.setData === 'function') {
    graph.setData(data)
    if (typeof graph.render === 'function') {
      await graph.render()
    } else if (typeof graph.draw === 'function') {
      graph.draw()
    }
    return
  }
  if (typeof graph.changeData === 'function') {
    graph.changeData(data)
  }
}

const applyElementStates = async () => {
  if (!graph || !isAllScope.value || typeof graph.setElementState !== 'function') return
  const states: Record<string, string[]> = {}

  if (!focusedModelId.value) {
    graphData.value.nodes.forEach((node) => {
      states[String(node.id)] = []
    })
    graphData.value.edges.forEach((edge) => {
      states[String(edge.id)] = []
    })
    await graph.setElementState(states, false)
    return
  }

  const relatedNodeIds = new Set<string>()
  const activeEdgeIds = new Set<string>()
  graphData.value.edges.forEach((edge) => {
    const sourceId = String(edge.source)
    const targetId = String(edge.target)
    const focusedId = `model-${focusedModelId.value}`
    if (sourceId === focusedId || targetId === focusedId) {
      relatedNodeIds.add(sourceId)
      relatedNodeIds.add(targetId)
      activeEdgeIds.add(String(edge.id))
    }
  })

  graphData.value.nodes.forEach((node) => {
    const nodeId = String(node.id)
    if (node.model_id === focusedModelId.value || relatedNodeIds.has(nodeId)) {
      states[nodeId] = ['active']
    } else {
      states[nodeId] = ['disable']
    }
  })
  graphData.value.edges.forEach((edge) => {
    states[String(edge.id)] = activeEdgeIds.has(String(edge.id)) ? ['active'] : ['disable']
  })
  await graph.setElementState(states, false)
}

const getEdgeModel = (edgeIdOrTriggerId: string | number) => {
  const text = String(edgeIdOrTriggerId)
  const triggerId = Number(text.startsWith('trigger-') ? text.replace('trigger-', '') : text)
  if (Number.isNaN(triggerId)) return null
  return activeTriggers.value.find((item) => item.id === triggerId) || null
}

const isTriggerFocused = (trigger: any) => {
  if (!focusedModelId.value) return true
  return trigger.source_model_id === focusedModelId.value || trigger.target_model_id === focusedModelId.value
}

const getModelNodeIdFromGraphNode = (rawNodeId?: string | number) => {
  const text = String(rawNodeId || '')
  const match = text.match(/^(?:halo-)?model-(\d+)$/)
  return match ? Number(match[1]) : Number.NaN
}

const renderGraph = async ({ fit = false }: { fit?: boolean } = {}) => {
  if (!graph) return
  graphCanvasSize.width = graphData.value.width
  graphCanvasSize.height = graphData.value.height
  const allScopeScale = isAllScope.value ? getAllScopeVisualScale() : 1

  const nodes: any[] = []
  const edges: any[] = []
  const singleScopePositions = isAllScope.value ? {} : getSingleScopeNodePositions()

  if (isAllScope.value) {
    laneMeta.value.forEach((lane) => {
      const laneElementKey = getLaneElementKey(lane.key)
      const isLaneActive = Boolean(focusedModelId.value && focusedLaneKey.value === lane.key)
      const laneDimmed = Boolean(focusedModelId.value && !isLaneActive)
      const laneOpacity = laneDimmed ? 0.3 : 1
      const railAmbientOpacity = isLaneActive ? 0.24 : 0.12
      const railCoreOpacity = isLaneActive ? 0.48 : 0.34
      const railCoreColor = '#1890ff'
      const railInnerColor = '#1890ff'
      const railGlowColor = 'rgba(24, 144, 255, 0.35)'
      const labelColor = isLaneActive ? '#0f4fa8' : '#4b5563'
      const labelText = `${lane.label}  ${lane.count}`
      const railStartId = `rail-start-${laneElementKey}`
      const railEndId = `rail-end-${laneElementKey}`
      nodes.push({
        id: railStartId,
        type: 'circle',
        draggable: false,
        style: {
          x: lane.railStartX,
          y: lane.centerY,
          size: 1,
          fill: 'transparent',
          stroke: 'transparent',
          opacity: 0,
          zIndex: 0
        }
      })
      nodes.push({
        id: railEndId,
        type: 'circle',
        draggable: false,
        style: {
          x: lane.railEndX,
          y: lane.centerY,
          size: 1,
          fill: 'transparent',
          stroke: 'transparent',
          opacity: 0,
          zIndex: 0
        }
      })
      nodes.push({
        id: `rail-label-${laneElementKey}`,
        type: 'circle',
        draggable: false,
        style: {
          x: lane.labelX,
          y: lane.centerY,
          size: 2,
          fill: 'transparent',
          stroke: 'transparent',
          opacity: laneOpacity,
          labelText,
          labelPlacement: 'left',
          labelOffsetX: Math.round(10 * allScopeScale),
          labelFontSize: Math.round(14 * allScopeScale),
          labelFontWeight: isLaneActive ? 700 : 600,
          labelFill: labelColor,
          zIndex: 3
        }
      })
      edges.push({
        id: `rail-glow-${laneElementKey}`,
        source: railStartId,
        target: railEndId,
        type: 'line',
        isRail: true,
        style: {
          stroke: `rgba(24, 144, 255, ${railAmbientOpacity.toFixed(3)})`,
          lineWidth: (isLaneActive ? 18 : 16) * allScopeScale,
          shadowColor: railGlowColor,
          shadowBlur: (isLaneActive ? 22 : 18) * allScopeScale,
          opacity: laneOpacity,
          zIndex: 0
        }
      })
      edges.push({
        id: `rail-core-${laneElementKey}`,
        source: railStartId,
        target: railEndId,
        type: 'line',
        isRail: true,
        style: {
          stroke: `rgba(24, 144, 255, ${railCoreOpacity.toFixed(3)})`,
          lineWidth: (isLaneActive ? 10 : 8) * allScopeScale,
          lineCap: 'round',
          opacity: laneOpacity,
          shadowColor: railGlowColor,
          shadowBlur: (isLaneActive ? 12 : 9) * allScopeScale,
          zIndex: 1
        }
      })
      edges.push({
        id: `rail-inner-${laneElementKey}`,
        source: railStartId,
        target: railEndId,
        type: 'line',
        isRail: true,
        style: {
          stroke: railInnerColor,
          lineWidth: Math.max(1.6, 2 * allScopeScale),
          lineCap: 'round',
          opacity: laneDimmed ? 0.26 : 1,
          zIndex: 2
        }
      })
    })
  }

  graphData.value.nodes.forEach((node) => {
    const isFocusedNode = focusedModelId.value === node.model_id
    const active = !focusedModelId.value || focusedRelatedIds.value.has(node.model_id)
    const iconSize = isAllScope.value
      ? Math.round((isFocusedNode ? 22 : 20) * allScopeScale)
      : (isFocusedNode ? 42 : 36)
    const nodeSize = isAllScope.value
      ? Math.round((isFocusedNode ? 58 : 52) * allScopeScale)
      : iconSize
    const nodeOpacity = active ? 1 : 0.18
    const singleScopePos = !isAllScope.value ? singleScopePositions[node.model_id] : undefined
    nodes.push({
      id: String(node.id),
      type: isAllScope.value ? 'circle' : 'image',
      draggable: true,
      model_id: node.model_id,
      label: node.name,
      ...(isAllScope.value
        ? { x: node.x, y: node.y }
        : (singleScopePos ? { x: singleScopePos.x, y: singleScopePos.y } : {})),
      style: {
        ...(isAllScope.value
          ? { x: node.x, y: node.y }
          : (singleScopePos ? { x: singleScopePos.x, y: singleScopePos.y } : {})),
        ...(isAllScope.value
          ? {
              size: nodeSize,
              fill: '#ffffff',
              stroke: active ? '#bcd8ff' : '#d5dce8',
              lineWidth: (isFocusedNode ? 1.8 : 1.4) * allScopeScale,
              icon: true,
              iconSrc: getNodeIconSrc(node),
              iconWidth: iconSize,
              iconHeight: iconSize
            }
          : {
              img: getNodeIconSrc(node),
              src: getNodeIconSrc(node),
              size: iconSize
            }),
        labelText: node.name,
        labelPlacement: 'bottom',
        labelOffsetY: isAllScope.value ? Math.round(14 * allScopeScale) : 16,
        labelFontSize: isAllScope.value
          ? Math.round((isFocusedNode ? 13 : 11) * allScopeScale)
          : (isFocusedNode ? 16 : 13),
        labelFontWeight: isFocusedNode ? 700 : 500,
        labelFill: active ? '#1f2937' : '#94a3b8',
        opacity: nodeOpacity,
        shadowColor: active ? 'rgba(24, 144, 255, 0.24)' : 'rgba(148, 163, 184, 0.12)',
        shadowBlur: (active ? 16 : 7) * allScopeScale,
        zIndex: 30
      }
    })
  })

  graphData.value.edges.forEach((edge) => {
    const style = edge.relationType?.style || {}
    const directed = edge.relationType?.direction === 'directed'
    const arrow = style.arrow === 'none' ? false : true
    const highlighted = isTriggerFocused(edge.trigger)
    const isCrossLane = Boolean(isAllScope.value && edge.laneDistance > 0)
    const showLabel = highlighted || isCrossLane || edge.familyCount === 1 || edge.directionIndex === 0
    const labelPlacement = 'center'
    const labelOffsetY = 0
    const edgeStroke = highlighted ? (style.color || '#1d4ed8') : '#1e40af'
    const edgeOpacity = !focusedModelId.value ? 0.9 : (highlighted ? 1 : 0.32)
    edges.push({
      id: String(edge.id),
      source: String(edge.source),
      target: String(edge.target),
      label: edge.label,
      triggerId: edge.trigger.id,
      type: isAllScope.value ? 'cubic-vertical' : 'cubic-horizontal',
      style: {
        stroke: edgeStroke,
        lineWidth: highlighted ? Math.max(Number(style.lineWidth) || 2.8, 3) : 2.4,
        lineDash: style.lineType === 'dashed' ? [7, 5] : undefined,
        endArrow: directed && arrow
          ? {
              path: 'M 0,0 L 10,5 L 0,10 z',
              d: 10,
              fill: edgeStroke
            }
          : false,
        opacity: edgeOpacity,
        curveOffset: edge.curveOffset,
        shadowColor: highlighted ? 'rgba(37, 99, 235, 0.38)' : 'rgba(30, 64, 175, 0.24)',
        shadowBlur: highlighted ? 18 : 10,
        labelText: showLabel ? edge.label : '',
        labelPlacement,
        labelOffsetY,
        labelFill: highlighted ? '#0f172a' : '#334155',
        labelMaxWidth: 132,
        labelBackground: showLabel,
        labelBackgroundFill: highlighted ? 'rgba(255, 255, 255, 0.96)' : 'rgba(255, 255, 255, 0.88)',
        labelPadding: [3, 6],
        labelRadius: 6,
        zIndex: 42
      }
    })
  })

  await applyGraphData({ nodes, edges })
  graphReady.value = true
  await applyElementStates()
  handleResize()
  if (fit && typeof graph.fitView === 'function') {
    graph.fitView()
  }
}

const initGraph = () => {
  if (!graphContainer.value) return
  if (graph) {
    graph.destroy?.()
    graph = null
  }
  graph = new Graph({
    container: graphContainer.value,
    width: graphCanvasSize.width,
    height: graphCanvasSize.height,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    zoomRange: isAllScope.value ? [0.28, 1.8] : [0.35, 1.8],
    defaultNode: {
      type: 'image',
      size: 44
    },
    defaultEdge: {
      type: isAllScope.value ? 'cubic-vertical' : 'cubic-horizontal',
      style: {
        stroke: '#94a3b8',
        lineWidth: 2,
        endArrow: true
      }
    },
    layout: isAllScope.value
      ? {
          type: 'preset'
        }
      : (hasSingleScopeNodePositions()
        ? {
            type: 'preset'
          }
        : {
            type: 'dagre',
            rankdir: 'LR',
            nodesep: 56,
            ranksep: 140
          })
  } as any)

  graph.on('edge:click', (evt: any) => {
    const edgeModel = evt?.item?.getData?.() || evt?.item?.getModel?.() || evt?.target || null
    if (edgeModel?.isRail || String(edgeModel?.id || '').startsWith('rail-')) return
    const trigger = getEdgeModel(edgeModel?.triggerId || edgeModel?.id)
    if (trigger) openTriggerDetail(trigger)
  })

  graph.on('node:click', (evt: any) => {
    const node = evt?.item?.getData?.() || evt?.item?.getModel?.() || evt?.target || null
    const modelId = Number(node?.model_id ?? getModelNodeIdFromGraphNode(node?.id))
    if (Number.isNaN(modelId) || !modelId) return
    focusedModelId.value = modelId
    void renderGraph()
  })

  graph.on('node:dblclick', (evt: any) => {
    const node = evt?.item?.getData?.() || evt?.item?.getModel?.() || evt?.target || null
    const modelId = Number(node?.model_id ?? getModelNodeIdFromGraphNode(node?.id))
    if (Number.isNaN(modelId) || !modelId) return
    focusedModelId.value = modelId
    void renderGraph()
    openNodeDetail(modelId)
  })

  graph.on('node:drag', (evt: any) => {
    const node = evt?.item?.getData?.() || evt?.item?.getModel?.() || evt?.target || null
    const modelId = Number(node?.model_id ?? getModelNodeIdFromGraphNode(node?.id))
    const nodeId = String(node?.id || `model-${modelId}`)
    if (Number.isNaN(modelId) || !modelId || typeof graph.updateNodeData !== 'function') return
    if (nodeId.startsWith('rail-') || nodeId.startsWith('halo-')) return
    if (!isAllScope.value) {
      const rawX = evt?.x ?? node?.style?.x ?? node?.x ?? 0
      const rawY = evt?.y ?? node?.style?.y ?? node?.y ?? 0
      setSingleScopeNodePosition(modelId, rawX, rawY)
      graph.updateNodeData([
        {
          id: nodeId,
          x: rawX,
          y: rawY,
          style: {
            x: rawX,
            y: rawY
          }
        }
      ])
      if (typeof graph.draw === 'function') {
        graph.draw()
      } else if (typeof graph.render === 'function') {
        void graph.render()
      }
      return
    }
    const laneBounds = laneBoundsByModelId.value[modelId]
    if (!laneBounds) return
    const isFocusedNode = focusedModelId.value === modelId
    const allScopeScale = getAllScopeVisualScale()
    const nodeSize = Math.round((isFocusedNode ? 58 : 52) * allScopeScale)
    const rawX = evt?.x ?? node?.style?.x ?? node?.x ?? 0
    const nextX = clamp(rawX, laneBounds.minX, laneBounds.maxX)
    allScopeNodeXMap.value = {
      ...allScopeNodeXMap.value,
      [modelId]: nextX
    }
    graph.updateNodeData([
      {
        id: nodeId,
        x: nextX,
        y: laneBounds.centerY,
        style: {
          x: nextX,
          y: laneBounds.centerY,
          size: nodeSize
        }
      }
    ])
    if (typeof graph.draw === 'function') {
      graph.draw()
    } else if (typeof graph.render === 'function') {
      void graph.render()
    }
  })

  graph.on('canvas:click', () => {
    clearFocusMode()
  })

  graph.on('node:dragend', () => {
    if (!isAllScope.value) {
      syncSingleScopeNodePositionsFromGraph()
      void renderGraph()
      return
    }
    void renderGraph()
  })

  window.addEventListener('resize', handleResize)
  void renderGraph({ fit: true })
}

const handleResize = () => {
  if (!graph || !graphViewport.value) return
  const width = Math.max(graphViewport.value.clientWidth, graphCanvasSize.width)
  const height = Math.max(graphCanvasSize.height, 560)
  if (typeof graph.changeSize === 'function') {
    graph.changeSize(width, height)
  } else if (typeof graph.setSize === 'function') {
    graph.setSize(width, height)
  }
}

const fitView = () => {
  graph?.fitView?.()
}

const zoomIn = () => {
  if (!graph) return
  const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
  if (typeof graph.zoomTo === 'function') {
    graph.zoomTo(currentZoom * 1.2)
  } else if (typeof graph.zoomBy === 'function') {
    graph.zoomBy(1.2)
  }
}

const zoomOut = () => {
  if (!graph) return
  const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
  if (typeof graph.zoomTo === 'function') {
    graph.zoomTo(currentZoom * 0.8)
  } else if (typeof graph.zoomBy === 'function') {
    graph.zoomBy(0.8)
  }
}

const refreshGraph = async () => {
  await fetchTriggers()
}

const clearFocusMode = () => {
  if (!focusedModelId.value) return
  focusedModelId.value = null
  void renderGraph()
}

const applyTriggerCronPreset = (cron: string) => {
  triggerScheduleForm.batch_scan_enabled = true
  triggerScheduleForm.batch_scan_cron = cron
}

const handleTriggerScheduleEditorModeChange = () => {
  if (triggerScheduleEditorMode.value === 'visual') {
    if (!syncTriggerVisualSchedule(triggerScheduleForm.batch_scan_cron)) {
      triggerScheduleForm.batch_scan_cron = buildCronFromVisual(triggerVisualSchedule)
    }
  }
}

watch(
  () => [graphData.value.nodes.length, graphData.value.edges.length],
  async () => {
    await nextTick()
    await renderGraph({ fit: true })
  }
)

watch(focusedModelId, () => {
  void renderGraph()
})

watch(isAllScope, () => {
  if (!isAllScope.value) return
  allScopeNodeXMap.value = {}
})

watch(
  triggerVisualSchedule,
  () => {
    if (triggerScheduleEditorMode.value === 'visual') {
      triggerScheduleForm.batch_scan_cron = buildCronFromVisual(triggerVisualSchedule)
    }
  },
  { deep: true }
)

onMounted(async () => {
  await Promise.all([fetchModels(), fetchModeTypeDict(), fetchRelationTypes(), fetchModelTree()])
  await nextTick()
  if (graphContainer.value) {
    initGraph()
  }
  if (currentScopeValue.value) {
    await fetchTriggers()
  }
})

onActivated(async () => {
  await nextTick()
  if (!graph && graphContainer.value) {
    initGraph()
  }
  if (currentScopeValue.value) {
    await fetchTriggers()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (graph) {
    graph.destroy?.()
    graph = null
  }
})
</script>

<style scoped>
.relation-trigger-page {
  height: 100%;
}

.relation-trigger-page__layout {
  height: 100%;
}

.relation-trigger-page__tree-col,
.relation-trigger-page__content-col {
  height: 100%;
}

.relation-trigger-page__tree-card,
.relation-trigger-page__canvas-card {
  height: 100%;
}

.relation-trigger-page__tree-card :deep(.ant-card-body) {
  height: calc(100% - 56px);
  overflow: auto;
}

.relation-trigger-page__canvas-card :deep(.ant-card-body) {
  height: calc(100% - 56px);
  min-height: 600px;
  padding: 16px;
}

.relation-trigger-page__tree-search {
  margin-bottom: 12px;
}

.relation-trigger-page__model-node {
  font-weight: 500;
}

.relation-trigger-page__all-node {
  font-weight: 600;
  color: var(--app-accent);
}

.relation-trigger-page__category-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--app-text-secondary);
}

.relation-trigger-page__canvas-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.relation-trigger-page__title {
  color: var(--app-text-primary);
  font-size: 16px;
  font-weight: 600;
}

.relation-trigger-page__subtitle {
  margin-top: 4px;
  color: var(--app-text-secondary);
  font-size: 12px;
}

.relation-trigger-page__meta-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.relation-trigger-page__legend {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.relation-trigger-page__graph-wrap {
  position: relative;
  height: 100%;
  min-height: 560px;
}

.relation-trigger-page__graph-viewport {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 560px;
  overflow: auto;
}

.relation-trigger-page__graph {
  position: relative;
  min-height: 560px;
  z-index: 1;
  background: #ffffff;
}

.relation-trigger-page__graph-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.92);
}

.relation-trigger-page__cron-message {
  margin: -4px 0 8px;
  color: var(--app-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.relation-trigger-page__cron-message.is-error {
  color: var(--ant-color-error, #ff4d4f);
}

.relation-trigger-page__cron-message.is-success {
  color: var(--ant-color-success, #52c41a);
}

.relation-trigger-page__cron-presets {
  margin-bottom: 8px;
}

.relation-trigger-page__cron-builder {
  margin-bottom: 8px;
  padding: 12px;
  border: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  border-radius: 10px;
  background: var(--ant-color-fill-tertiary, #fafafa);
}

.relation-trigger-page__builder-item {
  margin-bottom: 0;
}

.relation-trigger-page__graph :deep(canvas) {
  cursor: grab;
}

.relation-trigger-page__node-modal-summary {
  margin-bottom: 12px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.relation-trigger-page__cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.relation-trigger-page__action-cell {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  white-space: nowrap;
}

.relation-trigger-page__node-table :deep(.ant-table-cell) {
  vertical-align: middle;
}

.relation-trigger-page__node-table :deep(.ant-table-thead > tr > th) {
  white-space: nowrap;
}

.relation-trigger-page__node-table :deep(.ant-table-tbody > tr > td) {
  padding-top: 10px;
  padding-bottom: 10px;
}

.relation-trigger-page__node-table :deep(.ant-table-cell-fix-right) {
  background: #fff;
}

.relation-trigger-page__node-table :deep(.ant-btn-link) {
  padding-inline: 4px;
}

.relation-trigger-page__empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 992px) {
  .relation-trigger-page__layout,
  .relation-trigger-page__tree-col,
  .relation-trigger-page__content-col,
  .relation-trigger-page__tree-card,
  .relation-trigger-page__canvas-card {
    height: auto;
  }

  .relation-trigger-page__graph {
    min-height: 420px;
  }

  .relation-trigger-page__meta-bar {
    gap: 6px;
  }
}
</style>
