<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 工具栏 -->
      <a-row justify="space-between" align="middle">
        <a-space>
          <a-button @click="loadData" :loading="loading">
            <ReloadOutlined />
            刷新
          </a-button>
          <a-button type="primary" @click="openTypeSelector">
            <PlusOutlined />
            新增配置
          </a-button>
          <a-dropdown>
            <a-button>
              <EllipsisOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="handleBatchDelete" :disabled="!selectedRowKeys.length">
                  <DeleteOutlined />
                  批量删除
                </a-menu-item>
                <a-menu-item @click="handleExport">
                  <ExportOutlined />
                  导出配置
                </a-menu-item>
                <a-menu-item>
                  <a-upload
                    :action="uploadAction"
                    :show-upload-list="false"
                    :before-upload="beforeUpload"
                    @change="handleUploadChange"
                  >
                    <ImportOutlined />
                    导入配置
                  </a-upload>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-space>
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索规则名称/表达式"
            style="width: 250px"
            @search="loadData"
            allow-clear
          />
        </a-space>
      </a-row>

      <!-- 数据表格 -->
      <a-table
        :loading="loading"
        :columns="columns"
        :data-source="rules"
        :pagination="pagination"
        row-key="id"
        :row-selection="{ selectedRowKeys, onChange: onSelectChange }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <!-- 规则名称 -->
          <template v-if="column.key === 'name'">
            <a-space direction="vertical" size="small">
              <span style="font-weight: 500">{{ record.name }}</span>
              <a-tag v-if="record.labels?.severity" :color="severityColor(record.labels.severity)">
                {{ record.labels.severity }}
              </a-tag>
            </a-space>
          </template>

          <!-- 规则类型 -->
          <template v-if="column.key === 'type'">
            <a-tag :color="typeColor(record.type)">
              {{ typeText(record.type) }}
            </a-tag>
          </template>

          <!-- 表达式 -->
          <template v-if="column.key === 'expr'">
            <a-typography-text ellipsis style="max-width: 200px" :title="record.expr">
              {{ record.expr || '-' }}
            </a-typography-text>
          </template>

          <!-- 通知规则 -->
          <template v-if="column.key === 'notice_rule'">
            <a-space v-if="record.notice_rule" direction="vertical" size="small">
              <span style="font-weight: 500">{{ record.notice_rule.name }}</span>
              <a-tag v-if="record.notice_rule.receiver_name" size="small" color="blue">
                {{ record.notice_rule.receiver_name }}
              </a-tag>
            </a-space>
            <a-tag v-else color="default">未配置</a-tag>
          </template>

          <!-- 标签 -->
          <template v-if="column.key === 'labels'">
            <a-space wrap>
              <a-tag v-for="(value, key) in record.labels" :key="key" size="small">
                {{ key }}: {{ value }}
              </a-tag>
            </a-space>
          </template>

          <!-- 触发配置 -->
          <template v-if="column.key === 'trigger'">
            <a-space direction="vertical" size="small">
              <span>连续 {{ record.times }} 次触发</span>
              <span v-if="record.period">周期: {{ record.period }}s</span>
            </a-space>
          </template>

          <!-- 启用状态 -->
          <template v-if="column.key === 'enabled'">
            <a-switch
              :checked="record.enabled"
              @change="(checked: boolean) => toggleEnabled(record, checked)"
            />
          </template>

          <!-- 操作 -->
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)">
                <EditOutlined />
                编辑
              </a-button>
              <a-popconfirm
                title="确认删除该规则？"
                @confirm="handleDelete(record)"
                ok-text="确认"
                cancel-text="取消"
              >
                <a-button type="link" size="small" danger>
                  <DeleteOutlined />
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-space>

    <!-- 类型选择弹窗 -->
    <a-modal
      v-model:open="typeSelectorVisible"
      title="选择告警规则类型"
      :footer="null"
      width="600px"
    >
      <a-row :gutter="[16, 16]">
        <a-col :span="12">
          <a-card
            hoverable
            :class="['type-card', { active: selectedType === 'realtime_metric' }]"
            @click="selectType('realtime_metric')"
          >
            <a-space direction="vertical" align="center" style="width: 100%">
              <DashboardOutlined style="font-size: 32px; color: #1890ff" />
              <span style="font-weight: 500">实时指标告警</span>
              <span style="font-size: 12px; color: #999">基于实时采集数据触发</span>
            </a-space>
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card
            hoverable
            :class="['type-card', { active: selectedType === 'periodic_metric' }]"
            @click="selectType('periodic_metric')"
          >
            <a-space direction="vertical" align="center" style="width: 100%">
              <HistoryOutlined style="font-size: 32px; color: #52c41a" />
              <span style="font-weight: 500">周期指标告警</span>
              <span style="font-size: 12px; color: #999">基于时序数据库查询</span>
            </a-space>
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card
            hoverable
            :class="['type-card', { active: selectedType === 'realtime_log' }]"
            @click="selectType('realtime_log')"
          >
            <a-space direction="vertical" align="center" style="width: 100%">
              <FileTextOutlined style="font-size: 32px; color: #fa8c16" />
              <span style="font-weight: 500">实时日志告警</span>
              <span style="font-size: 12px; color: #999">基于实时日志匹配</span>
            </a-space>
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card
            hoverable
            :class="['type-card', { active: selectedType === 'periodic_log' }]"
            @click="selectType('periodic_log')"
          >
            <a-space direction="vertical" align="center" style="width: 100%">
              <SearchOutlined style="font-size: 32px; color: #722ed1" />
              <span style="font-weight: 500">周期日志告警</span>
              <span style="font-size: 12px; color: #999">基于日志数据库查询</span>
            </a-space>
          </a-card>
        </a-col>
      </a-row>
    </a-modal>

    <!-- 规则编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingRule?.id ? '编辑告警规则' : '新增告警规则'"
      width="800px"
      :confirm-loading="saving"
      @ok="handleSave"
      @cancel="handleCancel"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        layout="vertical"
      >
        <!-- 基本信息 -->
        <a-divider orientation="left">基本信息</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="规则名称" name="name">
              <a-input v-model:value="formState.name" placeholder="请输入规则名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="规则类型">
              <a-tag :color="typeColor(formState.type)">{{ typeText(formState.type) }}</a-tag>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 告警表达式 -->
        <a-divider orientation="left">告警表达式</a-divider>
        
        <!-- 实时指标告警表达式构建器 -->
        <template v-if="formState.type === 'realtime_metric'">
          <a-alert type="info" show-icon style="margin-bottom: 16px">
            <template #message>表达式说明</template>
            <template #description>
              使用 JEXL 表达式语法，支持内置变量：__app__, __metrics__, __instance__, usage, value 等
            </template>
          </a-alert>
          <a-form-item label="告警表达式" name="expr" extra="示例: equals(__app__, 'Linux') && usage > 80">
            <a-textarea
              v-model:value="formState.expr"
              :rows="3"
              placeholder="请输入告警表达式"
            />
          </a-form-item>
        </template>

        <!-- 周期指标告警 -->
        <template v-if="formState.type === 'periodic_metric'">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="数据源" name="datasource_type">
                <a-select v-model:value="formState.datasource_type">
                  <a-select-option value="promql">Prometheus (PromQL)</a-select-option>
                  <a-select-option value="sql">SQL (VictoriaMetrics)</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="执行周期(秒)" name="period">
                <a-input-number v-model:value="formState.period" :min="60" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="查询表达式" name="expr">
            <a-textarea
              v-model:value="formState.expr"
              :rows="4"
              :placeholder="formState.datasource_type === 'promql' ? '请输入 PromQL 查询' : '请输入 SQL 查询'"
            />
          </a-form-item>
        </template>

        <!-- 日志告警 -->
        <template v-if="formState.type === 'realtime_log' || formState.type === 'periodic_log'">
          <a-alert type="info" show-icon style="margin-bottom: 16px">
            <template #message>日志告警</template>
            <template #description>
              支持日志字段匹配：log.severityText, log.body, log.attributes 等
            </template>
          </a-alert>
          <a-form-item label="匹配表达式" name="expr">
            <a-textarea
              v-model:value="formState.expr"
              :rows="3"
              placeholder="示例: log.severityText == 'ERROR' && contains(log.body, 'Exception')"
            />
          </a-form-item>
          <a-form-item v-if="formState.type === 'periodic_log'" label="执行周期(秒)" name="period">
            <a-input-number v-model:value="formState.period" :min="60" style="width: 100%" />
          </a-form-item>
        </template>

        <!-- 触发配置 -->
        <a-divider orientation="left">触发配置</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="连续触发次数" name="times" extra="连续多少次满足条件才触发告警">
              <a-input-number v-model:value="formState.times" :min="1" :max="10" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="告警级别" name="severity">
              <a-select v-model:value="(formState.labels || {}).severity">
                <a-select-option value="critical">紧急 (Critical)</a-select-option>
                <a-select-option value="warning">警告 (Warning)</a-select-option>
                <a-select-option value="info">信息 (Info)</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 标签和注释 -->
        <a-divider orientation="left">标签和注释</a-divider>
        <a-form-item label="告警标签" extra="用于告警分组和路由">
          <a-space direction="vertical" style="width: 100%">
            <a-row v-for="(tag, index) in tagList" :key="index" :gutter="8">
              <a-col :span="10">
                <a-input v-model:value="tag.key" placeholder="标签名" />
              </a-col>
              <a-col :span="10">
                <a-input v-model:value="tag.value" placeholder="标签值" />
              </a-col>
              <a-col :span="4">
                <a-button type="link" danger @click="removeTag(index)">
                  <DeleteOutlined />
                </a-button>
              </a-col>
            </a-row>
            <a-button type="dashed" block @click="addTag">
              <PlusOutlined />
              添加标签
            </a-button>
          </a-space>
        </a-form-item>

        <a-form-item label="告警注释" extra="告警的详细说明">
          <a-textarea
            v-model:value="(formState.annotations || {}).summary"
            :rows="2"
            placeholder="请输入告警摘要"
          />
        </a-form-item>

        <!-- 通知配置 -->
        <a-divider orientation="left">通知配置</a-divider>
        <a-form-item label="通知规则" extra="选择告警触发时使用的通知规则">
          <a-select
            v-model:value="formState.notice_rule_id"
            placeholder="请选择通知规则"
            allow-clear
            style="width: 100%"
          >
            <a-select-option v-for="rule in noticeRules" :key="rule.id" :value="rule.id">
              <a-space>
                <span>{{ rule.name }}</span>
                <a-tag v-if="rule.receiver_name" size="small" color="blue">
                  {{ rule.receiver_name }}
                </a-tag>
              </a-space>
            </a-select-option>
          </a-select>
          <div class="form-help">
            没有合适的规则？<a @click="goToNoticeConfig">去配置通知规则</a>
          </div>
        </a-form-item>

        <!-- 消息模板 -->
        <a-divider orientation="left">消息模板</a-divider>
        <a-form-item label="告警内容模板" name="template" extra="支持变量: {{$labels.instance}}, {{$value}} 等">
          <a-textarea
            v-model:value="formState.template"
            :rows="3"
            placeholder="示例: 实例 {{$labels.instance}} 的 CPU 使用率达到 {{$value}}%"
          />
        </a-form-item>

        <!-- 模板变量参考 -->
        <a-collapse ghost>
          <a-collapse-panel key="1" header="模板变量参考">
            <a-descriptions :column="2" size="small" bordered>
              <a-descriptions-item label="${__instance__}">监控实例ID</a-descriptions-item>
              <a-descriptions-item label="${__instancename__}">监控实例名称</a-descriptions-item>
              <a-descriptions-item label="${__instancehost__}">监控目标主机</a-descriptions-item>
              <a-descriptions-item label="${__app__}">应用类型</a-descriptions-item>
              <a-descriptions-item label="${__metrics__}">指标集名称</a-descriptions-item>
              <a-descriptions-item label="${__labels__}">标签集合</a-descriptions-item>
              <a-descriptions-item label="${__value__}">指标值</a-descriptions-item>
            </a-descriptions>
          </a-collapse-panel>
        </a-collapse>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import {
  ReloadOutlined,
  PlusOutlined,
  EllipsisOutlined,
  DeleteOutlined,
  EditOutlined,
  ExportOutlined,
  ImportOutlined,
  DashboardOutlined,
  HistoryOutlined,
  FileTextOutlined,
  SearchOutlined
} from '@ant-design/icons-vue'
import {
  getAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  enableAlertRule,
  disableAlertRule,
  getAlertNotices,
  type AlertRule,
  type AlertNotice
} from '@/api/monitoring'

// 表格列定义
const columns = [
  { title: '规则名称', key: 'name', width: 180 },
  { title: '类型', key: 'type', width: 140 },
  { title: '表达式', key: 'expr', width: 200 },
  { title: '通知规则', key: 'notice_rule', width: 150 },
  { title: '标签', key: 'labels', width: 150 },
  { title: '触发配置', key: 'trigger', width: 120 },
  { title: '启用', key: 'enabled', width: 80, align: 'center' },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' }
]

// 状态
const loading = ref(false)
const saving = ref(false)
const rules = ref<AlertRule[]>([])
const searchKeyword = ref('')
const selectedRowKeys = ref<number[]>([])
const selectedRows = ref<AlertRule[]>([])
const noticeRules = ref<AlertNotice[]>([])

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 弹窗状态
const typeSelectorVisible = ref(false)
const modalVisible = ref(false)
const selectedType = ref('')
const editingRule = ref<AlertRule | null>(null)
const formRef = ref<FormInstance>()

// 表单状态
const formState = reactive<Partial<AlertRule>>({
  name: '',
  type: 'realtime_metric',
  expr: '',
  period: 300,
  times: 1,
  labels: { severity: 'warning' },
  annotations: { summary: '' },
  template: '',
  datasource_type: 'promql',
  enabled: true,
  notice_rule_id: undefined
})

// 标签列表
const tagList = ref<{ key: string; value: string }[]>([])

// 表单校验规则
const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  expr: [{ required: true, message: '请输入告警表达式', trigger: 'blur' }],
  period: [{ required: true, message: '请输入执行周期', trigger: 'blur' }]
}

// 上传地址
const uploadAction = `${(import.meta as any).env?.VITE_API_BASE_URL || ''}/monitoring/alert-rules/import`

// 类型文本映射
const typeText = (type?: string) => {
  const map: Record<string, string> = {
    realtime_metric: '实时指标',
    periodic_metric: '周期指标',
    realtime_log: '实时日志',
    periodic_log: '周期日志'
  }
  return map[type || ''] || type
}

// 类型颜色映射
const typeColor = (type?: string) => {
  const map: Record<string, string> = {
    realtime_metric: 'blue',
    periodic_metric: 'green',
    realtime_log: 'orange',
    periodic_log: 'purple'
  }
  return map[type || ''] || 'default'
}

// 严重级别颜色
const severityColor = (severity?: string) => {
  const map: Record<string, string> = {
    critical: 'red',
    warning: 'orange',
    info: 'blue'
  }
  return map[severity || ''] || 'default'
}

// 加载通知规则列表
const loadNoticeRules = async () => {
  try {
    const res = await getAlertNotices({ page_size: 1000 })
    if (res.data?.code === 200) {
      const data = res.data.data
      if (Array.isArray(data)) {
        noticeRules.value = data
      } else if (data?.items) {
        noticeRules.value = data.items
      }
    }
  } catch (error: any) {
    console.error('加载通知规则失败:', error)
  }
}

// 跳转到通知规则配置
const goToNoticeConfig = () => {
  window.open('/monitoring/alert/notice', '_blank')
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertRules({
      q: searchKeyword.value,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    if (res.data?.code === 200) {
      const data = res.data.data
      if (Array.isArray(data)) {
        rules.value = data
        pagination.total = data.length
      } else if (data?.items) {
        rules.value = data.items
        pagination.total = data.total || data.items.length
      }
    }
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 表格选择变化
const onSelectChange = (keys: number[], rows: AlertRule[]) => {
  selectedRowKeys.value = keys
  selectedRows.value = rows
}

// 表格分页变化
const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

// 打开类型选择器
const openTypeSelector = () => {
  selectedType.value = ''
  typeSelectorVisible.value = true
}

// 选择类型
const selectType = (type: string) => {
  selectedType.value = type
  typeSelectorVisible.value = false
  editingRule.value = null
  resetForm()
  formState.type = type
  modalVisible.value = true
}

// 重置表单
const resetForm = () => {
  formState.name = ''
  formState.type = 'realtime_metric'
  formState.expr = ''
  formState.period = 300
  formState.times = 1
  formState.labels = { severity: 'warning' }
  formState.annotations = { summary: '' }
  formState.template = ''
  formState.datasource_type = 'promql'
  formState.enabled = true
  formState.notice_rule_id = undefined
  tagList.value = []
}

// 编辑规则
const handleEdit = (record: AlertRule) => {
  editingRule.value = record
  Object.assign(formState, {
    name: record.name,
    type: record.type,
    expr: record.expr,
    period: record.period,
    times: record.times,
    labels: { ...record.labels },
    annotations: { ...record.annotations },
    template: record.template,
    datasource_type: record.datasource_type,
    enabled: record.enabled,
    notice_rule_id: record.notice_rule_id
  })
  // 转换标签列表
  tagList.value = Object.entries(record.labels || {})
    .filter(([key]) => key !== 'severity')
    .map(([key, value]) => ({ key, value }))
  modalVisible.value = true
}

// 保存规则
const handleSave = async () => {
  try {
    await formRef.value?.validate()
    saving.value = true

    // 构建标签
    const labels: Record<string, string> = { ...formState.labels }
    tagList.value.forEach(tag => {
      if (tag.key && tag.value) {
        labels[tag.key] = tag.value
      }
    })

    const data = {
      ...formState,
      labels,
      annotations: formState.annotations
    }

    if (editingRule.value?.id) {
      await updateAlertRule(editingRule.value.id, data)
      message.success('更新成功')
    } else {
      await createAlertRule(data)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (error: any) {
    if (error?.response?.data?.message) {
      message.error(error.response.data.message)
    }
  } finally {
    saving.value = false
  }
}

// 取消编辑
const handleCancel = () => {
  modalVisible.value = false
  formRef.value?.resetFields()
}

// 切换启用状态
const toggleEnabled = async (record: AlertRule & { toggling?: boolean }, enabled: boolean) => {
  record.toggling = true
  try {
    if (enabled) {
      await enableAlertRule(record.id)
    } else {
      await disableAlertRule(record.id)
    }
    record.enabled = enabled
    message.success(enabled ? '已启用' : '已禁用')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
    record.enabled = !enabled
  } finally {
    record.toggling = false
  }
}

// 删除规则
const handleDelete = async (record: AlertRule) => {
  try {
    await deleteAlertRule(record.id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '删除失败')
  }
}

// 批量删除
const handleBatchDelete = () => {
  if (!selectedRowKeys.value.length) {
    message.warning('请选择要删除的规则')
    return
  }
  Modal.confirm({
    title: '确认批量删除',
    content: `确定要删除选中的 ${selectedRowKeys.value.length} 条规则吗？`,
    onOk: async () => {
      try {
        // 这里应该调用批量删除API
        for (const id of selectedRowKeys.value) {
          await deleteAlertRule(id)
        }
        message.success('批量删除成功')
        selectedRowKeys.value = []
        loadData()
      } catch (error: any) {
        message.error(error?.response?.data?.message || '删除失败')
      }
    }
  })
}

// 导出配置
const handleExport = () => {
  message.info('导出功能开发中...')
}

// 上传前检查
const beforeUpload = (file: File) => {
  const isJson = file.type === 'application/json' || file.name.endsWith('.json')
  if (!isJson) {
    message.error('请上传 JSON 文件')
  }
  return isJson
}

// 上传状态变化
const handleUploadChange = (info: any) => {
  if (info.file.status === 'done') {
    message.success('导入成功')
    loadData()
  } else if (info.file.status === 'error') {
    message.error('导入失败')
  }
}

// 添加标签
const addTag = () => {
  tagList.value.push({ key: '', value: '' })
}

// 移除标签
const removeTag = (index: number) => {
  tagList.value.splice(index, 1)
}

onMounted(() => {
  loadData()
  loadNoticeRules()
})
</script>

<style scoped>
.type-card {
  cursor: pointer;
  transition: all 0.3s;
}
.type-card:hover {
  border-color: #1890ff;
}
.type-card.active {
  border-color: #1890ff;
  background-color: #e6f7ff;
}
</style>
