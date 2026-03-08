<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <!-- 说明卡片 -->
      <a-alert type="info" show-icon>
        <template #message>通知渠道说明</template>
        <template #description>
          <div>
            <p>通知渠道配置用于定义告警和系统消息的发送方式。</p>
            <p><strong>通用性</strong>：配置的通知渠道可同时用于系统通知和告警通知。</p>
            <p><strong>支持类型</strong>：邮件、Webhook、企业微信、钉钉、飞书、短信、Slack、Discord等。</p>
          </div>
        </template>
      </a-alert>

      <a-space>
        <a-input v-model:value="keyword" placeholder="渠道名称" style="width: 220px" />
        <a-select v-model:value="typeFilter" allow-clear placeholder="全部类型" style="width: 180px">
          <a-select-option :value="1">邮件</a-select-option>
          <a-select-option :value="2">Webhook</a-select-option>
          <a-select-option :value="4">企业微信机器人</a-select-option>
          <a-select-option :value="5">钉钉机器人</a-select-option>
          <a-select-option :value="6">飞书机器人</a-select-option>
          <a-select-option :value="10">企业微信应用</a-select-option>
          <a-select-option :value="14">飞书应用</a-select-option>
          <a-select-option :value="0">短信</a-select-option>
          <a-select-option :value="8">Slack</a-select-option>
          <a-select-option :value="9">Discord</a-select-option>
        </a-select>
        <a-select v-model:value="enableFilter" allow-clear placeholder="全部状态" style="width: 120px">
          <a-select-option :value="true">启用</a-select-option>
          <a-select-option :value="false">禁用</a-select-option>
        </a-select>
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-space>
              <component :is="getTypeIcon(record.type)" />
              <span>{{ record.type_name }}</span>
            </a-space>
          </template>
          <template v-if="column.key === 'enable'">
            <a-switch
              :checked="record.enable"
              :disabled="!canEdit"
              @change="(checked: boolean) => toggleEnabled(record, checked)"
            />
          </template>
          <template v-if="column.key === 'config_preview'">
            <a-tooltip :title="getConfigPreview(record)">
              <span class="config-preview">{{ getConfigPreview(record) }}</span>
            </a-tooltip>
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

    <!-- 新增/编辑模态框 -->
    <a-modal
      v-model:open="modalOpen"
      :title="editing?.id ? '编辑通知渠道' : '新增通知渠道'"
      :confirm-loading="saving"
      width="800px"
      @ok="saveItem"
    >
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="渠道名称" required>
              <a-input v-model:value="formState.name" placeholder="如：生产环境邮件通知" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="渠道类型" required>
              <a-select v-model:value="formState.type" :disabled="!!editing?.id" @change="onTypeChange">
                <a-select-option :value="1">邮件</a-select-option>
                <a-select-option :value="2">Webhook</a-select-option>
                <a-select-option :value="4">企业微信机器人</a-select-option>
                <a-select-option :value="5">钉钉机器人</a-select-option>
                <a-select-option :value="6">飞书机器人</a-select-option>
                <a-select-option :value="10">企业微信应用</a-select-option>
                <a-select-option :value="14">飞书应用</a-select-option>
                <a-select-option :value="0">短信</a-select-option>
                <a-select-option :value="8">Slack</a-select-option>
                <a-select-option :value="9">Discord</a-select-option>
                <a-select-option :value="11">华为云SMN</a-select-option>
                <a-select-option :value="12">Server酱</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="描述">
          <a-textarea v-model:value="formState.description" :rows="2" placeholder="渠道用途描述" />
        </a-form-item>

        <a-form-item label="启用">
          <a-switch v-model:checked="formState.enable" />
        </a-form-item>

        <!-- 邮件配置 -->
        <template v-if="formState.type === 1">
          <a-divider orientation="left">邮件服务器配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="SMTP服务器" required>
                <a-input v-model:value="formState.config.smtp_host" placeholder="如：smtp.example.com" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="SMTP端口" required>
                <a-input-number v-model:value="formState.config.smtp_port" :min="1" :max="65535" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="用户名" required>
                <a-input v-model:value="formState.config.smtp_username" placeholder="SMTP用户名" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="密码" required>
                <a-input-password v-model:value="formState.config.smtp_password" placeholder="SMTP密码" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="发件人地址" required>
                <a-input v-model:value="formState.config.email_from" placeholder="如：alert@example.com" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="使用TLS">
                <a-switch v-model:checked="formState.config.smtp_use_tls" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- Webhook配置 -->
        <template v-if="formState.type === 2">
          <a-divider orientation="left">Webhook配置</a-divider>
          <a-form-item label="Webhook URL" required>
            <a-input v-model:value="formState.config.hook_url" placeholder="https://example.com/webhook" />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="请求方法">
                <a-select v-model:value="formState.config.hook_method">
                  <a-select-option value="POST">POST</a-select-option>
                  <a-select-option value="GET">GET</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="Content-Type">
                <a-select v-model:value="formState.config.hook_content_type">
                  <a-select-option value="application/json">application/json</a-select-option>
                  <a-select-option value="application/x-www-form-urlencoded">application/x-www-form-urlencoded</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="认证类型">
            <a-select v-model:value="formState.config.hook_auth_type" allow-clear placeholder="无认证">
              <a-select-option value="Bearer">Bearer Token</a-select-option>
              <a-select-option value="Basic">Basic Auth</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item v-if="formState.config.hook_auth_type" label="认证令牌">
            <a-input-password v-model:value="formState.config.hook_auth_token" placeholder="Token或密码" />
          </a-form-item>
        </template>

        <!-- 企业微信机器人配置 -->
        <template v-if="formState.type === 4">
          <a-divider orientation="left">企业微信机器人配置</a-divider>
          <a-form-item label="Webhook Key" required>
            <a-input v-model:value="formState.config.wecom_key" placeholder="机器人Webhook中的key参数" />
            <div class="form-help">从企业微信机器人Webhook URL中提取key参数</div>
          </a-form-item>
          <a-form-item label="@手机号列表">
            <a-input v-model:value="formState.config.wecom_mentioned_mobiles" placeholder="13800138000,13900139000" />
            <div class="form-help">多个手机号用逗号分隔，通知时会@对应成员</div>
          </a-form-item>
        </template>

        <!-- 钉钉机器人配置 -->
        <template v-if="formState.type === 5">
          <a-divider orientation="left">钉钉机器人配置</a-divider>
          <a-form-item label="Access Token" required>
            <a-input v-model:value="formState.config.dingtalk_access_token" placeholder="从钉钉机器人Webhook中获取" />
          </a-form-item>
          <a-form-item label="加签密钥">
            <a-input-password v-model:value="formState.config.dingtalk_secret" placeholder="安全设置中的加签密钥" />
            <div class="form-help">如启用了加签安全设置，需填写此项</div>
          </a-form-item>
          <a-form-item label="@手机号列表">
            <a-input v-model:value="formState.config.dingtalk_at_mobiles" placeholder="13800138000,13900139000" />
          </a-form-item>
          <a-form-item label="@所有人">
            <a-switch v-model:checked="formState.config.dingtalk_is_at_all" />
          </a-form-item>
        </template>

        <!-- 飞书机器人配置 -->
        <template v-if="formState.type === 6">
          <a-divider orientation="left">飞书机器人配置</a-divider>
          <a-form-item label="Webhook Token" required>
            <a-input v-model:value="formState.config.feishu_webhook_token" placeholder="从飞书机器人Webhook中获取" />
          </a-form-item>
          <a-form-item label="加签密钥">
            <a-input-password v-model:value="formState.config.feishu_secret" placeholder="安全设置中的签名校验密钥" />
          </a-form-item>
        </template>

        <!-- 企业微信应用配置 -->
        <template v-if="formState.type === 10">
          <a-divider orientation="left">企业微信应用配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="企业ID" required>
                <a-input v-model:value="formState.config.wecom_corp_id" placeholder="CorpID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="应用ID" required>
                <a-input v-model:value="formState.config.wecom_agent_id" placeholder="AgentId" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="应用密钥" required>
            <a-input-password v-model:value="formState.config.wecom_app_secret" placeholder="Secret" />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="指定成员">
                <a-input v-model:value="formState.config.wecom_to_user" placeholder="UserID1|UserID2" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="指定部门">
                <a-input v-model:value="formState.config.wecom_to_party" placeholder="PartyID1|PartyID2" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="指定标签">
                <a-input v-model:value="formState.config.wecom_to_tag" placeholder="TagID1|TagID2" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- 飞书应用配置 -->
        <template v-if="formState.type === 14">
          <a-divider orientation="left">飞书应用配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="App ID" required>
                <a-input v-model:value="formState.config.feishu_app_id" placeholder="App ID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="App Secret" required>
                <a-input-password v-model:value="formState.config.feishu_app_secret" placeholder="App Secret" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="接收类型">
            <a-radio-group v-model:value="formState.config.feishu_receive_type">
              <a-radio :value="0">用户</a-radio>
              <a-radio :value="1">群组</a-radio>
            </a-radio-group>
          </a-form-item>
          <a-form-item v-if="formState.config.feishu_receive_type === 0" label="用户ID">
            <a-input v-model:value="formState.config.feishu_user_id" placeholder="Open ID或User ID" />
          </a-form-item>
          <a-form-item v-if="formState.config.feishu_receive_type === 1" label="群组ID">
            <a-input v-model:value="formState.config.feishu_chat_id" placeholder="Chat ID" />
          </a-form-item>
        </template>

        <!-- Slack配置 -->
        <template v-if="formState.type === 8">
          <a-divider orientation="left">Slack配置</a-divider>
          <a-form-item label="Webhook URL" required>
            <a-input v-model:value="formState.config.slack_webhook_url" placeholder="https://hooks.slack.com/services/..." />
          </a-form-item>
        </template>

        <!-- Discord配置 -->
        <template v-if="formState.type === 9">
          <a-divider orientation="left">Discord配置</a-divider>
          <a-form-item label="Webhook URL" required>
            <a-input v-model:value="formState.config.discord_webhook_url" placeholder="https://discord.com/api/webhooks/..." />
          </a-form-item>
        </template>

        <!-- 短信配置 -->
        <template v-if="formState.type === 0">
          <a-divider orientation="left">短信配置</a-divider>
          <a-form-item label="短信服务商" required>
            <a-select v-model:value="formState.config.sms_provider">
              <a-select-option value="aliyun">阿里云</a-select-option>
              <a-select-option value="tencent">腾讯云</a-select-option>
              <a-select-option value="huawei">华为云</a-select-option>
            </a-select>
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="Access Key" required>
                <a-input v-model:value="formState.config.sms_access_key" placeholder="AccessKey ID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="Secret Key" required>
                <a-input-password v-model:value="formState.config.sms_secret_key" placeholder="AccessKey Secret" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="短信签名" required>
                <a-input v-model:value="formState.config.sms_sign_name" placeholder="如：阿里云短信测试" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="模板Code" required>
                <a-input v-model:value="formState.config.sms_template_code" placeholder="SMS_12345678" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>

        <!-- 华为云SMN配置 -->
        <template v-if="formState.type === 11">
          <a-divider orientation="left">华为云SMN配置</a-divider>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="Access Key" required>
                <a-input v-model:value="formState.config.smn_ak" placeholder="Access Key" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="Secret Key" required>
                <a-input-password v-model:value="formState.config.smn_sk" placeholder="Secret Key" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="项目ID" required>
                <a-input v-model:value="formState.config.smn_project_id" placeholder="Project ID" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="区域" required>
                <a-input v-model:value="formState.config.smn_region" placeholder="如：cn-north-4" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="主题URN" required>
            <a-input v-model:value="formState.config.smn_topic_urn" placeholder="Topic URN" />
          </a-form-item>
        </template>

        <!-- Server酱配置 -->
        <template v-if="formState.type === 12">
          <a-divider orientation="left">Server酱配置</a-divider>
          <a-form-item label="SendKey" required>
            <a-input v-model:value="formState.config.serverchan_send_key" placeholder="从Server酱获取的SendKey" />
          </a-form-item>
        </template>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  MailOutlined,
  GlobalOutlined,
  MessageOutlined,
  DingdingOutlined,
  SlackOutlined,
  MobileOutlined,
  CloudOutlined,
  NotificationOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  getNoticeReceivers,
  createNoticeReceiver,
  updateNoticeReceiver,
  deleteNoticeReceiver,
  testNoticeReceiver,
  type NoticeReceiver
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const typeFilter = ref<number | undefined>(undefined)
const enableFilter = ref<boolean | undefined>(undefined)
const items = ref<NoticeReceiver[]>([])
const modalOpen = ref(false)
const editing = ref<NoticeReceiver | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const formState = reactive({
  name: '',
  type: 1,
  enable: true,
  description: '',
  config: {} as Record<string, any>
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:notice:create') || userStore.hasPermission('monitoring:alert:notice'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:notice:edit') || userStore.hasPermission('monitoring:alert:notice'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:notice:delete') || userStore.hasPermission('monitoring:alert:notice'))
const canTest = computed(() => userStore.hasPermission('monitoring:alert:notice:test') || userStore.hasPermission('monitoring:alert:notice'))

const columns = [
  { title: '渠道名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'type', width: 150 },
  { title: '配置预览', key: 'config_preview', width: 200 },
  { title: '启用', key: 'enable', width: 100 },
  { title: '操作', key: 'actions', width: 200 }
]

const typeIcons: Record<number, any> = {
  0: MobileOutlined,
  1: MailOutlined,
  2: GlobalOutlined,
  4: MessageOutlined,
  5: DingdingOutlined,
  6: NotificationOutlined,
  8: SlackOutlined,
  9: CloudOutlined,
  10: MessageOutlined,
  11: CloudOutlined,
  12: NotificationOutlined,
  14: NotificationOutlined
}

const getTypeIcon = (type: number) => {
  return typeIcons[type] || MessageOutlined
}

const getConfigPreview = (record: NoticeReceiver): string => {
  if (!record.config) return '-'
  const config = record.config
  switch (record.type) {
    case 1:
      return config.smtp_host || '-'
    case 2:
      return config.hook_url?.substring(0, 30) + '...' || '-'
    case 4:
      return '企业微信机器人'
    case 5:
      return '钉钉机器人'
    case 6:
      return '飞书机器人'
    case 10:
      return `企业: ${config.wecom_corp_id || '-'}`
    case 14:
      return '飞书应用'
    case 0:
      return `${config.sms_provider || '-'}短信`
    case 8:
      return 'Slack'
    case 9:
      return 'Discord'
    case 11:
      return '华为云SMN'
    case 12:
      return 'Server酱'
    default:
      return '-'
  }
}

const onTypeChange = () => {
  // 切换类型时清空配置
  formState.config = {}
}

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getNoticeReceivers({
      q: keyword.value || undefined,
      type: typeFilter.value,
      enable: enableFilter.value,
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

const openModal = (record?: NoticeReceiver) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.type = record?.type || 1
  formState.enable = record?.enable !== false
  formState.description = record?.description || ''
  formState.config = record?.config ? { ...record.config } : {}
  modalOpen.value = true
}

const validateForm = () => {
  if (!formState.name.trim()) throw new Error('请输入渠道名称')
  
  // 根据类型验证必填字段
  const config = formState.config
  switch (formState.type) {
    case 1: // 邮件
      if (!config.smtp_host) throw new Error('请输入SMTP服务器')
      if (!config.smtp_username) throw new Error('请输入用户名')
      if (!config.email_from) throw new Error('请输入发件人地址')
      break
    case 2: // Webhook
      if (!config.hook_url) throw new Error('请输入Webhook URL')
      break
    case 4: // 企业微信机器人
      if (!config.wecom_key) throw new Error('请输入Webhook Key')
      break
    case 5: // 钉钉
      if (!config.dingtalk_access_token) throw new Error('请输入Access Token')
      break
    case 6: // 飞书机器人
      if (!config.feishu_webhook_token) throw new Error('请输入Webhook Token')
      break
    case 10: // 企业微信应用
      if (!config.wecom_corp_id) throw new Error('请输入企业ID')
      if (!config.wecom_agent_id) throw new Error('请输入应用ID')
      if (!config.wecom_app_secret) throw new Error('请输入应用密钥')
      break
    case 14: // 飞书应用
      if (!config.feishu_app_id) throw new Error('请输入App ID')
      if (!config.feishu_app_secret) throw new Error('请输入App Secret')
      break
    case 0: // 短信
      if (!config.sms_provider) throw new Error('请选择短信服务商')
      if (!config.sms_access_key) throw new Error('请输入Access Key')
      break
    case 8: // Slack
      if (!config.slack_webhook_url) throw new Error('请输入Webhook URL')
      break
    case 9: // Discord
      if (!config.discord_webhook_url) throw new Error('请输入Webhook URL')
      break
    case 11: // 华为云SMN
      if (!config.smn_ak) throw new Error('请输入Access Key')
      if (!config.smn_topic_urn) throw new Error('请输入主题URN')
      break
    case 12: // Server酱
      if (!config.serverchan_send_key) throw new Error('请输入SendKey')
      break
  }
}

const saveItem = async () => {
  saving.value = true
  try {
    validateForm()
    
    const payload: Partial<NoticeReceiver> = {
      name: formState.name.trim(),
      type: formState.type,
      enable: formState.enable,
      description: formState.description.trim() || undefined,
      config: formState.config
    }
    
    if (editing.value?.id !== undefined && editing.value?.id !== null) {
      await updateNoticeReceiver(editing.value.id, payload)
    } else {
      await createNoticeReceiver(payload)
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

const removeItem = async (record: NoticeReceiver) => {
  await deleteNoticeReceiver(record.id)
  message.success('删除成功')
  loadData()
}

const testItem = async (record: NoticeReceiver) => {
  try {
    await testNoticeReceiver(record.id)
    message.success('测试发送成功')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '测试失败')
  }
}

const toggleEnabled = async (record: NoticeReceiver, checked: boolean) => {
  try {
    await updateNoticeReceiver(record.id, { enable: checked })
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
  typeFilter.value = undefined
  enableFilter.value = undefined
  pagination.current = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.config-preview {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}
.form-help {
  margin-top: 4px;
  color: #999;
  font-size: 12px;
}
</style>
