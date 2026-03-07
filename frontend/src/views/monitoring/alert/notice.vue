<template>
  <a-card :bordered="false">
    <a-space direction="vertical" style="width: 100%" :size="16">
      <a-space>
        <a-input v-model:value="keyword" placeholder="通知配置名称" style="width: 220px" />
        <a-select v-model:value="channelFilter" allow-clear placeholder="全部渠道" style="width: 160px">
          <a-select-option value="webhook">Webhook</a-select-option>
          <a-select-option value="email">邮件</a-select-option>
          <a-select-option value="wechat">企业微信</a-select-option>
          <a-select-option value="dingtalk">钉钉</a-select-option>
          <a-select-option value="feishu">飞书</a-select-option>
        </a-select>
        <a-button type="primary" :loading="loading" @click="loadData">查询</a-button>
        <a-button @click="reset">重置</a-button>
        <a-button v-if="canCreate" type="primary" @click="openModal()">新增</a-button>
      </a-space>

      <a-table :loading="loading" :columns="columns" :data-source="items" row-key="id" :pagination="pagination" @change="handleTableChange">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'enabled' ? 'green' : 'default'">{{ record.status || '-' }}</a-tag>
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

    <a-modal v-model:open="modalOpen" :title="editing?.id ? '编辑通知配置' : '新增通知配置'" :confirm-loading="saving" width="720px" @ok="saveItem">
      <a-form layout="vertical" :model="formState">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="名称" required><a-input v-model:value="formState.name" /></a-form-item></a-col>
          <a-col :span="12">
            <a-form-item label="渠道类型" required>
              <a-select v-model:value="formState.channel_type">
                <a-select-option value="webhook">Webhook</a-select-option>
                <a-select-option value="email">邮件</a-select-option>
                <a-select-option value="wechat">企业微信</a-select-option>
                <a-select-option value="dingtalk">钉钉</a-select-option>
                <a-select-option value="feishu">飞书</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <template v-if="formState.channel_type === 'webhook'">
          <a-form-item label="Webhook URL" required><a-input v-model:value="config.webhook.url" placeholder="https://..." /></a-form-item>
          <a-form-item label="请求方法"><a-select v-model:value="config.webhook.method"><a-select-option value="POST">POST</a-select-option><a-select-option value="PUT">PUT</a-select-option></a-select></a-form-item>
          <a-form-item label="Headers(JSON)"><a-textarea v-model:value="config.webhook.headers" :rows="3" placeholder='{"X-Token":"xxx"}' /></a-form-item>
        </template>

        <template v-else-if="formState.channel_type === 'email'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="SMTP服务器" required><a-input v-model:value="config.email.smtp_host" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="端口" required><a-input-number v-model:value="config.email.smtp_port" :min="1" style="width:100%" /></a-form-item></a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="用户名" required><a-input v-model:value="config.email.username" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="密码" required><a-input-password v-model:value="config.email.password" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="收件人"><a-input v-model:value="config.email.to" placeholder="多个逗号分隔" /></a-form-item>
        </template>

        <template v-else-if="formState.channel_type === 'wechat'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="CorpID" required><a-input v-model:value="config.wechat.corp_id" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="AgentID" required><a-input v-model:value="config.wechat.agent_id" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="Secret" required><a-input-password v-model:value="config.wechat.secret" /></a-form-item>
        </template>

        <template v-else-if="formState.channel_type === 'dingtalk'">
          <a-form-item label="机器人Webhook" required><a-input v-model:value="config.dingtalk.webhook" /></a-form-item>
          <a-form-item label="签名密钥"><a-input-password v-model:value="config.dingtalk.secret" /></a-form-item>
        </template>

        <template v-else-if="formState.channel_type === 'feishu'">
          <a-form-item label="机器人Webhook" required><a-input v-model:value="config.feishu.webhook" /></a-form-item>
          <a-form-item label="签名密钥"><a-input-password v-model:value="config.feishu.secret" /></a-form-item>
        </template>

        <a-form-item label="状态">
          <a-select v-model:value="formState.status">
            <a-select-option value="enabled">enabled</a-select-option>
            <a-select-option value="disabled">disabled</a-select-option>
          </a-select>
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
  createAlertNotice,
  deleteAlertNotice,
  getAlertNotices,
  testAlertNotice,
  type AlertNotice,
  updateAlertNotice
} from '@/api/monitoring'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const channelFilter = ref<string | undefined>(undefined)
const items = ref<AlertNotice[]>([])
const modalOpen = ref(false)
const editing = ref<AlertNotice | null>(null)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const formState = reactive({ name: '', channel_type: 'webhook', status: 'enabled' })
const config = reactive({
  webhook: { url: '', method: 'POST', headers: '' },
  email: { smtp_host: '', smtp_port: 25, username: '', password: '', to: '' },
  wechat: { corp_id: '', agent_id: '', secret: '' },
  dingtalk: { webhook: '', secret: '' },
  feishu: { webhook: '', secret: '' }
})

const canCreate = computed(() => userStore.hasPermission('monitoring:alert:notice:create') || userStore.hasPermission('monitoring:alert:notice'))
const canEdit = computed(() => userStore.hasPermission('monitoring:alert:notice:edit') || userStore.hasPermission('monitoring:alert:notice'))
const canDelete = computed(() => userStore.hasPermission('monitoring:alert:notice:delete') || userStore.hasPermission('monitoring:alert:notice'))
const canTest = computed(() => userStore.hasPermission('monitoring:alert:notice:test') || userStore.hasPermission('monitoring:alert:notice'))

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '渠道', dataIndex: 'channel_type', key: 'channel_type', width: 120 },
  { title: '目标', dataIndex: 'target', key: 'target' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '操作', key: 'actions', width: 160 }
]

const normalizeList = (payload: any) => {
  if (Array.isArray(payload?.items)) return { items: payload.items, total: payload.total || payload.items.length }
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  return { items: [], total: 0 }
}

const parseHeaders = (text: string) => {
  const value = text.trim()
  if (!value) return undefined
  try {
    return JSON.parse(value)
  } catch {
    throw new Error('Headers 不是合法 JSON')
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAlertNotices({ q: keyword.value || undefined, channel_type: channelFilter.value, page: pagination.current, page_size: pagination.pageSize })
    const parsed = normalizeList(res?.data)
    items.value = parsed.items
    pagination.total = parsed.total
  } catch (error: any) {
    message.error(error?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const resetConfig = () => {
  config.webhook = { url: '', method: 'POST', headers: '' }
  config.email = { smtp_host: '', smtp_port: 25, username: '', password: '', to: '' }
  config.wechat = { corp_id: '', agent_id: '', secret: '' }
  config.dingtalk = { webhook: '', secret: '' }
  config.feishu = { webhook: '', secret: '' }
}

const openModal = (record?: AlertNotice) => {
  editing.value = record || null
  formState.name = record?.name || ''
  formState.channel_type = record?.channel_type || 'webhook'
  formState.status = record?.status || 'enabled'
  resetConfig()

  const cfg = (record as any)?.config || {}
  if (formState.channel_type === 'webhook') {
    config.webhook.url = cfg.url || ''
    config.webhook.method = cfg.method || 'POST'
    config.webhook.headers = JSON.stringify(cfg.headers || {}, null, 2)
  }
  if (formState.channel_type === 'email') {
    config.email.smtp_host = cfg.smtp_host || ''
    config.email.smtp_port = Number(cfg.smtp_port || 25)
    config.email.username = cfg.username || ''
    config.email.password = cfg.password || ''
    config.email.to = Array.isArray(cfg.to) ? cfg.to.join(',') : (cfg.to || '')
  }
  if (formState.channel_type === 'wechat') {
    config.wechat.corp_id = cfg.corp_id || ''
    config.wechat.agent_id = cfg.agent_id || ''
    config.wechat.secret = cfg.secret || ''
  }
  if (formState.channel_type === 'dingtalk') {
    config.dingtalk.webhook = cfg.webhook || ''
    config.dingtalk.secret = cfg.secret || ''
  }
  if (formState.channel_type === 'feishu') {
    config.feishu.webhook = cfg.webhook || ''
    config.feishu.secret = cfg.secret || ''
  }

  modalOpen.value = true
}

const buildPayloadConfig = () => {
  if (formState.channel_type === 'webhook') {
    if (!config.webhook.url.trim()) throw new Error('Webhook URL 必填')
    return {
      target: config.webhook.url.trim(),
      config: {
        url: config.webhook.url.trim(),
        method: config.webhook.method,
        headers: parseHeaders(config.webhook.headers)
      }
    }
  }
  if (formState.channel_type === 'email') {
    if (!config.email.smtp_host.trim() || !config.email.username.trim() || !config.email.password.trim()) throw new Error('邮件渠道必填项未完整填写')
    return {
      target: config.email.to.trim() || undefined,
      config: {
        smtp_host: config.email.smtp_host.trim(),
        smtp_port: config.email.smtp_port,
        username: config.email.username.trim(),
        password: config.email.password,
        to: config.email.to.split(',').map((x) => x.trim()).filter(Boolean)
      }
    }
  }
  if (formState.channel_type === 'wechat') {
    if (!config.wechat.corp_id.trim() || !config.wechat.agent_id.trim() || !config.wechat.secret.trim()) throw new Error('企业微信渠道必填项未完整填写')
    return { config: { corp_id: config.wechat.corp_id.trim(), agent_id: config.wechat.agent_id.trim(), secret: config.wechat.secret } }
  }
  if (formState.channel_type === 'dingtalk') {
    if (!config.dingtalk.webhook.trim()) throw new Error('钉钉 Webhook 必填')
    return { target: config.dingtalk.webhook.trim(), config: { webhook: config.dingtalk.webhook.trim(), secret: config.dingtalk.secret || undefined } }
  }
  if (formState.channel_type === 'feishu') {
    if (!config.feishu.webhook.trim()) throw new Error('飞书 Webhook 必填')
    return { target: config.feishu.webhook.trim(), config: { webhook: config.feishu.webhook.trim(), secret: config.feishu.secret || undefined } }
  }
  return {}
}

const saveItem = async () => {
  if (!formState.name.trim() || !formState.channel_type) return message.warning('请填写完整必填字段')
  saving.value = true
  try {
    const cfg = buildPayloadConfig()
    const payload = {
      name: formState.name.trim(),
      channel_type: formState.channel_type,
      status: formState.status,
      ...cfg
    }
    if (editing.value?.id !== undefined && editing.value?.id !== null) await updateAlertNotice(editing.value.id, payload)
    else await createAlertNotice(payload)
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

const handleTableChange = (pager: any) => {
  pagination.current = pager.current
  pagination.pageSize = pager.pageSize
  loadData()
}

const reset = () => {
  keyword.value = ''
  channelFilter.value = undefined
  pagination.current = 1
  loadData()
}

onMounted(loadData)
</script>
