<template>
  <div class="app-page alert-integration-page">
    <a-card :bordered="false" class="app-surface-card">
      <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>
          <span>外部告警接入说明</span>
        </template>
        <template #description>
          <div>
            <p>配置外部监控系统（如 Prometheus、Zabbix、SkyWalking 等）将告警推送到本平台，实现告警统一管理和分发。</p>
            <p>选择下方的告警源类型，查看接入文档并生成唯一的 Webhook URL 和 Token。</p>
          </div>
        </template>
      </a-alert>

      <!-- 告警源类型列表 -->
      <a-divider orientation="left">选择告警源类型</a-divider>
      <a-row :gutter="[16, 16]">
        <a-col :span="8" v-for="source in dataSources" :key="source.id">
          <a-card
            hoverable
            :class="['source-card', { active: selectedSource?.id === source.id }]"
            @click="selectSource(source)"
          >
            <a-space>
              <img v-if="source.icon" :src="source.icon" :alt="source.name" style="width: 32px; height: 32px;" />
              <span v-else class="source-icon">{{ source.name.charAt(0) }}</span>
              <span class="source-name">{{ source.name }}</span>
            </a-space>
            <div class="help-text help-text-spaced">
              {{ source.description }}
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 接入配置详情 -->
      <template v-if="selectedSource">
        <a-divider orientation="left">{{ selectedSource.name }} 接入配置</a-divider>
        
        <a-row :gutter="[16, 16]">
          <!-- Webhook URL -->
          <a-col :span="24">
            <a-form-item label="Webhook URL">
              <a-input-group compact>
                <a-input
                  :value="webhookUrl"
                  readonly
                  style="width: calc(100% - 200px)"
                />
                <a-button type="primary" @click="copyToClipboard(webhookUrl)">
                  复制 URL
                </a-button>
                <a-button @click="regenerateUrl" :loading="generating">
                  重新生成
                </a-button>
              </a-input-group>
              <div class="help-text help-text-spaced">
                将此 URL 配置到 {{ selectedSource.name }} 的 Webhook 接收地址
              </div>
            </a-form-item>
          </a-col>

          <!-- Token 认证 -->
          <a-col :span="24">
            <a-form-item label="认证 Token">
              <a-input-group compact>
                <a-input-password
                  :value="authToken"
                  readonly
                  style="width: calc(100% - 200px)"
                />
                <a-button type="primary" @click="copyToClipboard(authToken)">
                  复制 Token
                </a-button>
                <a-button @click="regenerateToken" :loading="generatingToken">
                  重新生成
                </a-button>
              </a-input-group>
              <div class="help-text help-text-spaced">
                在请求头中添加: <code>Authorization: Bearer {{ authToken ? '***' : 'your-token' }}</code>
              </div>
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 源系统特定配置 -->
        <a-card :title="selectedSource.name + ' 特定配置'" style="margin-top: 16px;">
          <!-- Prometheus 配置 -->
          <template v-if="selectedSource.id === 'prometheus'">
            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>Prometheus Alertmanager 配置步骤</template>
              <template #description>
                <ol style="padding-left: 20px; margin: 8px 0;">
                  <li>在 prometheus.yml 中添加 alerting 配置，指向上述 Webhook URL</li>
                  <li>配置 authentication，使用 Bearer Token</li>
                  <li>重启 Prometheus 使配置生效</li>
                </ol>
              </template>
            </a-alert>
            <a-form layout="vertical">
              <a-form-item label="Prometheus 服务器地址">
                <a-input v-model:value="sourceConfig.prometheus_url" placeholder="如：http://prometheus:9090" />
              </a-form-item>
              <a-form-item label="告警级别映射">
                <a-textarea
                  v-model:value="sourceConfig.severity_mapping"
                  :rows="3"
                  placeholder="critical:critical&#10;warning:warning&#10;info:info"
                />
              </a-form-item>
            </a-form>
          </template>

          <!-- Zabbix 配置 -->
          <template v-if="selectedSource.id === 'zabbix'">
            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>Zabbix Webhook 配置步骤</template>
              <template #description>
                <ol style="padding-left: 20px; margin: 8px 0;">
                  <li>在 Zabbix 管理界面中，进入 管理 -&gt; 媒介类型</li>
                  <li>创建新的 Webhook 媒介类型，配置 URL 为上述 Webhook URL</li>
                  <li>在消息模板中配置参数：{AlertName}, {HostName}, {TriggerSeverity} 等</li>
                  <li>为用户分配此媒介类型</li>
                </ol>
              </template>
            </a-alert>
            <a-form layout="vertical">
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="Zabbix 服务器地址">
                    <a-input v-model:value="sourceConfig.zabbix_url" placeholder="如：http://zabbix-server" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="Zabbix 版本">
                    <a-select v-model:value="sourceConfig.zabbix_version">
                      <a-select-option value="6.0">6.0+</a-select-option>
                      <a-select-option value="5.0">5.0</a-select-option>
                      <a-select-option value="4.0">4.x</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>
              <a-form-item label="告警级别映射">
                <a-textarea
                  v-model:value="sourceConfig.severity_mapping"
                  :rows="5"
                  placeholder="灾难:critical&#10;严重:error&#10;一般严重:warning&#10;警告:warning&#10;信息:info&#10;未分类:info"
                />
              </a-form-item>
            </a-form>
          </template>

          <!-- SkyWalking 配置 -->
          <template v-if="selectedSource.id === 'skywalking'">
            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>SkyWalking 告警配置步骤</template>
              <template #description>
                <ol style="padding-left: 20px; margin: 8px 0;">
                  <li>编辑 SkyWalking 的 alarm-settings.yml 文件</li>
                  <li>在 webhooks 部分添加上述 Webhook URL</li>
                  <li>重启 SkyWalking OAP 服务</li>
                </ol>
              </template>
            </a-alert>
            <a-form layout="vertical">
              <a-form-item label="SkyWalking OAP 地址">
                <a-input v-model:value="sourceConfig.skywalking_url" placeholder="如：http://skywalking-oap:12800" />
              </a-form-item>
            </a-form>
          </template>

          <!-- Nagios 配置 -->
          <template v-if="selectedSource.id === 'nagios'">
            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>Nagios 通知配置步骤</template>
              <template #description>
                <ol style="padding-left: 20px; margin: 8px 0;">
                  <li>在 Nagios 中创建自定义通知命令</li>
                  <li>使用 curl POST 到上述 Webhook URL</li>
                  <li>配置通知联系人和通知规则</li>
                </ol>
              </template>
            </a-alert>
            <a-form layout="vertical">
              <a-form-item label="Nagios 服务器地址">
                <a-input v-model:value="sourceConfig.nagios_url" placeholder="如：http://nagios-server" />
              </a-form-item>
            </a-form>
          </template>

          <!-- 自定义 Webhook 配置 -->
          <template v-if="selectedSource.id === 'custom'">
            <a-alert type="info" show-icon style="margin-bottom: 16px;">
              <template #message>自定义 Webhook 接入说明</template>
              <template #description>
                <p>接收符合以下格式的 JSON 数据：</p>
                <pre class="format-example">{{ customFormatExample }}</pre>
              </template>
            </a-alert>
          </template>

          <!-- 标签映射配置 -->
          <a-divider orientation="left">标签映射配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="默认标签（每行一个 key=value）">
                <a-textarea
                  v-model:value="sourceConfig.default_labels"
                  :rows="4"
                  placeholder="如：&#10;source=prometheus&#10;env=production&#10;team=ops"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="标签映射规则（外部标签:内部标签）">
                <a-textarea
                  v-model:value="sourceConfig.label_mapping"
                  :rows="4"
                  placeholder="如：&#10;severity:level&#10;host:instance&#10;alertname:alert_name"
                />
              </a-form-item>
            </a-col>
          </a-row>

          <!-- 保存配置 -->
          <a-row justify="end" style="margin-top: 16px;">
            <a-space>
              <a-button @click="testConnection" :loading="testing">
                测试连接
              </a-button>
              <a-button type="primary" @click="saveConfig" :loading="saving">
                保存配置
              </a-button>
            </a-space>
          </a-row>
        </a-card>

        <!-- 接入记录列表 -->
        <a-card title="接入记录" style="margin-top: 16px;">
          <a-table
            :loading="recordsLoading"
            :columns="recordColumns"
            :data-source="integrationRecords"
            row-key="id"
            :pagination="false"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-badge :status="record.status === 'active' ? 'success' : 'default'" :text="record.status === 'active' ? '活跃' : '停用'" />
              </template>
              <template v-if="column.key === 'last_alert'">
                {{ record.last_alert_at ? formatDate(record.last_alert_at) : '-' }}
              </template>
              <template v-if="column.key === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="viewRecordDetail(record)">
                    详情
                  </a-button>
                  <a-button type="link" size="small" danger @click="deleteRecord(record)">
                    删除
                  </a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </template>
    </a-space>

    <!-- 测试连接弹窗 -->
    <a-modal
      v-model:open="testModalOpen"
      title="测试连接"
      width="700px"
      @ok="sendTestAlert"
      :confirm-loading="testSending"
    >
      <a-form layout="vertical">
        <a-alert :type="testAlertType" show-icon style="margin-bottom: 16px;">
          <template #message>{{ testAlertTitle }}</template>
          <template #description>
            <pre style="margin: 0; white-space: pre-wrap; word-break: break-all;">{{ testAlertDescription }}</pre>
          </template>
        </a-alert>
        <a-form-item label="测试告警内容 (JSON)">
          <a-textarea v-model:value="testForm.content" :rows="12" />
        </a-form-item>
      </a-form>
    </a-modal>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 告警源类型列表
const dataSources = [
  {
    id: 'prometheus',
    name: 'Prometheus Alertmanager',
    description: '接收 Prometheus Alertmanager 推送的告警',
    icon: ''
  },
  {
    id: 'zabbix',
    name: 'Zabbix',
    description: '接收 Zabbix Webhook 推送的告警',
    icon: ''
  },
  {
    id: 'skywalking',
    name: 'SkyWalking',
    description: '接收 SkyWalking 告警通知',
    icon: ''
  },
  {
    id: 'nagios',
    name: 'Nagios',
    description: '接收 Nagios 通知推送',
    icon: ''
  },
  {
    id: 'custom',
    name: '自定义 Webhook',
    description: '接收符合标准格式的自定义告警',
    icon: ''
  }
]

// 状态
const selectedSource = ref<typeof dataSources[0] | null>(null)
const webhookUrl = ref('')
const authToken = ref('')
const generating = ref(false)
const generatingToken = ref(false)
const saving = ref(false)
const testing = ref(false)
const testSending = ref(false)
const testModalOpen = ref(false)
const recordsLoading = ref(false)

// 源配置
const sourceConfig = reactive({
  prometheus_url: '',
  zabbix_url: '',
  zabbix_version: '6.0',
  skywalking_url: '',
  nagios_url: '',
  severity_mapping: '',
  default_labels: '',
  label_mapping: ''
})

// 测试表单
const testForm = reactive({
  content: ''
})

// 接入记录
const integrationRecords = ref<any[]>([])

// 记录表格列
const recordColumns = [
  { title: '接入名称', dataIndex: 'name', key: 'name' },
  { title: 'Webhook URL', dataIndex: 'webhook_url', key: 'webhook_url', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '最近告警', dataIndex: 'last_alert_at', key: 'last_alert', width: 180 },
  { title: '操作', key: 'actions', width: 120 }
]

// 自定义格式示例
const customFormatExample = JSON.stringify({
  content: '告警内容描述',
  status: 'firing',
  labels: {
    alertname: 'CustomAlert',
    instance: '192.168.1.100:9100',
    severity: 'warning'
  },
  annotations: {
    summary: '告警摘要',
    description: '告警详细描述'
  },
  startAt: Date.now()
}, null, 2)

// 测试告警模板
const testAlertTemplates: Record<string, object> = {
  prometheus: {
    status: 'firing',
    alerts: [{
      status: 'firing',
      labels: {
        alertname: 'HighCPUUsage',
        instance: '192.168.1.100:9100',
        severity: 'warning',
        job: 'node-exporter'
      },
      annotations: {
        summary: 'High CPU usage detected',
        description: 'CPU usage is above 80% for 5 minutes'
      },
      startsAt: new Date().toISOString(),
      endsAt: null,
      generatorURL: 'http://prometheus:9090/graph'
    }]
  },
  zabbix: {
    AlertName: 'CPU usage is high',
    AlertId: '12345',
    HostName: 'Server-01',
    HostIp: '192.168.1.100',
    TriggerDescription: 'CPU usage exceeds 80%',
    TriggerSeverity: 'Warning',
    TriggerStatus: 'PROBLEM',
    ItemName: 'CPU usage',
    ItemValue: '85.5',
    EventDate: dayjs().format('YYYY-MM-DD'),
    EventTime: dayjs().format('HH:mm:ss'),
    EventTags: 'environment:production,team:ops'
  },
  skywalking: [{
    scopeId: 1,
    scope: 'SERVICE',
    name: 'order-service',
    id0: 'order-service',
    id1: '',
    ruleName: 'service_resp_time_rule',
    alarmMessage: 'Response time of order-service is above 1000ms',
    startTime: Date.now(),
    tags: [
      { key: 'level', value: 'WARNING' },
      { key: 'service', value: 'order-service' }
    ]
  }],
  nagios: {
    notification_type: 'PROBLEM',
    host_name: 'server-01',
    host_address: '192.168.1.100',
    service_description: 'CPU Load',
    state: 'WARNING',
    output: 'WARNING - CPU load is 85%',
    long_date_time: dayjs().format('YYYY-MM-DD HH:mm:ss')
  },
  custom: {
    content: '自定义告警内容',
    status: 'firing',
    labels: {
      alertname: 'CustomAlert',
      instance: 'custom-instance',
      severity: 'warning'
    },
    annotations: {
      summary: 'Custom alert summary',
      description: 'Custom alert description'
    },
    startAt: Date.now()
  }
}

// 测试告警类型
const testAlertType = computed(() => {
  const types: Record<string, string> = {
    prometheus: 'info',
    zabbix: 'warning',
    skywalking: 'success',
    nagios: 'error',
    custom: 'info'
  }
  return types[selectedSource.value?.id || 'custom'] || 'info'
})

// 测试告警标题
const testAlertTitle = computed(() => {
  const titles: Record<string, string> = {
    prometheus: 'Prometheus Alertmanager 格式',
    zabbix: 'Zabbix Webhook 格式',
    skywalking: 'SkyWalking Alarm 格式',
    nagios: 'Nagios Notification 格式',
    custom: 'SingleAlert 通用格式'
  }
  return titles[selectedSource.value?.id || 'custom'] || '通用格式'
})

// 测试告警描述
const testAlertDescription = computed(() => {
  const descs: Record<string, string> = {
    prometheus: '包含 status, alerts[], labels, annotations, startsAt, endsAt 字段',
    zabbix: '包含 AlertName, HostName, TriggerSeverity, ItemValue 等 Zabbix 宏变量',
    skywalking: '包含 scope, name, ruleName, alarmMessage, tags 等字段的数组',
    nagios: '包含 notification_type, host_name, service_description, state, output 字段',
    custom: '符合 HertzBeat SingleAlert 格式的 JSON 数据'
  }
  return descs[selectedSource.value?.id || 'custom'] || ''
})

// 选择告警源
const selectSource = (source: typeof dataSources[0]) => {
  selectedSource.value = source
  // 加载该类型的配置
  loadSourceConfig(source.id)
  // 加载接入记录
  loadIntegrationRecords(source.id)
}

// 加载源配置
const loadSourceConfig = (sourceId: string) => {
  // 这里应该从后端加载配置
  // 设置默认值
  switch (sourceId) {
    case 'prometheus':
      sourceConfig.severity_mapping = 'critical:critical\nwarning:warning\ninfo:info'
      sourceConfig.default_labels = 'source=prometheus'
      break
    case 'zabbix':
      sourceConfig.severity_mapping = '灾难:critical\n严重:error\n一般严重:warning\n警告:warning\n信息:info\n未分类:info'
      sourceConfig.default_labels = 'source=zabbix'
      break
    case 'skywalking':
      sourceConfig.default_labels = 'source=skywalking'
      break
    case 'nagios':
      sourceConfig.default_labels = 'source=nagios'
      break
    case 'custom':
      sourceConfig.default_labels = 'source=custom'
      break
  }
  
  // 生成 Webhook URL 和 Token（实际应该从后端获取）
  generateWebhookUrl()
  generateAuthToken()
}

// 加载接入记录
const loadIntegrationRecords = async (sourceId: string) => {
  recordsLoading.value = true
  try {
    // 这里应该调用后端 API 加载该类型的接入记录
    // 模拟数据
    integrationRecords.value = []
  } finally {
    recordsLoading.value = false
  }
}

// 生成 Webhook URL
const generateWebhookUrl = () => {
  const baseUrl = window.location.origin
  const sourceId = selectedSource.value?.id || 'custom'
  const token = Math.random().toString(36).substring(2, 15)
  webhookUrl.value = `${baseUrl}/api/v1/alerts/webhook/${sourceId}/${token}`
}

// 生成认证 Token
const generateAuthToken = () => {
  authToken.value = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

// 重新生成 URL
const regenerateUrl = () => {
  generating.value = true
  setTimeout(() => {
    generateWebhookUrl()
    generating.value = false
    message.success('Webhook URL 已重新生成')
  }, 500)
}

// 重新生成 Token
const regenerateToken = () => {
  generatingToken.value = true
  setTimeout(() => {
    generateAuthToken()
    generatingToken.value = false
    message.success('认证 Token 已重新生成')
  }, 500)
}

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
  message.success('已复制到剪贴板')
}

// 保存配置
const saveConfig = async () => {
  saving.value = true
  try {
    // 这里应该调用后端 API 保存配置
    await new Promise(resolve => setTimeout(resolve, 500))
    message.success('配置已保存')
    // 刷新接入记录
    if (selectedSource.value) {
      loadIntegrationRecords(selectedSource.value.id)
    }
  } finally {
    saving.value = false
  }
}

// 测试连接
const testConnection = () => {
  if (!selectedSource.value) return
  testForm.content = JSON.stringify(testAlertTemplates[selectedSource.value.id], null, 2)
  testModalOpen.value = true
}

// 发送测试告警
const sendTestAlert = async () => {
  testSending.value = true
  try {
    // 这里应该调用后端 API 发送测试告警
    await new Promise(resolve => setTimeout(resolve, 500))
    message.success('测试告警已发送')
    testModalOpen.value = false
  } finally {
    testSending.value = false
  }
}

// 查看记录详情
const viewRecordDetail = (record: any) => {
  Modal.info({
    title: '接入详情',
    content: JSON.stringify(record, null, 2),
    width: 600
  })
}

// 删除记录
const deleteRecord = (record: any) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除此接入配置吗？',
    onOk: async () => {
      // 这里应该调用后端 API 删除记录
      message.success('已删除')
      if (selectedSource.value) {
        loadIntegrationRecords(selectedSource.value.id)
      }
    }
  })
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  // 默认选择第一个告警源
  if (dataSources.length > 0) {
    selectSource(dataSources[0])
  }
})
</script>

<style scoped>
.source-card {
  cursor: pointer;
  transition: all 0.3s;
}
.source-card:hover {
  border-color: var(--app-accent);
  box-shadow: var(--app-shadow-sm);
}
.source-card.active {
  border-color: var(--app-accent);
  background-color: var(--app-accent-soft);
}

.source-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--app-text-primary);
}

.help-text {
  color: var(--app-text-muted);
  font-size: 12px;
}

.help-text-spaced {
  margin-top: 8px;
}

.format-example {
  padding: 12px;
  overflow-x: auto;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--app-surface-subtle);
  color: var(--app-text-primary);
}

.source-icon {
  width: 32px;
  height: 32px;
  background: var(--app-accent);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}
</style>
