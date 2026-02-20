<template>
  <div class="send-notification-page">
    <a-card :bordered="false">
      <template #title>
        <div class="page-header">
          <a-button type="link" @click="goBack">
            <ArrowLeftOutlined />
          </a-button>
          <span class="page-title">{{ t('notifications.sendNotification') }}</span>
        </div>
      </template>

      <a-form
        :model="formState"
        :rules="rules"
        layout="vertical"
        @finish="handleSubmit"
      >
        <!-- 接收者类型 -->
        <a-form-item :label="t('notifications.recipientType')" name="recipient_type">
          <a-radio-group v-model:value="formState.recipient_type">
            <a-radio value="users">{{ t('notifications.specificUsers') }}</a-radio>
            <a-radio value="department">{{ t('notifications.department') }}</a-radio>
            <a-radio value="broadcast">{{ t('notifications.broadcast') }}</a-radio>
          </a-radio-group>
        </a-form-item>

        <!-- 用户选择 -->
        <a-form-item
          v-if="formState.recipient_type === 'users'"
          :label="t('notifications.selectUsers')"
          name="user_ids"
        >
          <a-select
            v-model:value="formState.user_ids"
            mode="multiple"
            :placeholder="t('notifications.selectUsersPlaceholder')"
            :options="userOptions"
            show-search
            :filter-option="filterUserOption"
            style="width: 100%"
          />
        </a-form-item>

        <!-- 部门选择 -->
        <a-form-item
          v-if="formState.recipient_type === 'department'"
          :label="t('notifications.selectDepartment')"
          name="department_id"
        >
          <a-tree-select
            v-model:value="formState.department_id"
            :tree-data="departmentTree"
            :placeholder="t('notifications.selectDepartmentPlaceholder')"
            style="width: 100%"
            tree-default-expand-all
          />
        </a-form-item>

        <!-- 通知类型 -->
        <a-form-item :label="t('notifications.type')" name="type_id">
          <a-select
            v-model:value="formState.type_id"
            :placeholder="t('notifications.selectType')"
            style="width: 200px"
          >
            <a-select-option
              v-for="type in types"
              :key="type.id"
              :value="type.id"
            >
              <component :is="getIconComponent(type.icon)" />
              {{ type.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <!-- 标题 -->
        <a-form-item :label="t('notifications.title')" name="title">
          <a-input
            v-model:value="formState.title"
            :placeholder="t('notifications.titlePlaceholder')"
            :max-length="100"
            show-count
          />
        </a-form-item>

        <!-- 内容 -->
        <a-form-item :label="t('notifications.content')" name="content">
          <a-textarea
            v-model:value="formState.content"
            :placeholder="t('notifications.contentPlaceholder')"
            :rows="6"
            :max-length="2000"
            show-count
          />
          <div class="form-hint">{{ t('notifications.markdownSupport') }}</div>
        </a-form-item>

        <!-- 预览 -->
        <a-form-item :label="t('notifications.preview')">
          <a-card class="preview-card" size="small">
            <div class="preview-header">
              <span class="preview-title">{{ formState.title || t('notifications.previewTitle') }}</span>
            </div>
            <div class="preview-content" v-html="renderedContent" />
          </a-card>
        </a-form-item>

        <!-- 提交按钮 -->
        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="submitting">
              <SendOutlined />
              {{ t('notifications.send') }}
            </a-button>
            <a-button @click="goBack">
              {{ t('common.cancel') }}
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '@/stores/notifications'
import { sendNotification, sendBroadcast } from '@/api/notifications'
import { getUsers } from '@/api/user'
import { getDepartments } from '@/api/department'
import { message } from 'ant-design-vue'
// Markdown渲染和HTML净化（简化版本，不使用外部库）
const renderMarkdown = (text: string): string => {
  if (!text) return ''
  // 简单的Markdown转换
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}
import {
  ArrowLeftOutlined,
  SendOutlined,
  BellOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  MessageOutlined,
  MailOutlined,
  AlertOutlined,
  StarOutlined,
  FileTextOutlined,
  SettingOutlined
} from '@ant-design/icons-vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const store = useNotificationStore()

const types = computed(() => store.types)
const submitting = ref(false)
const userOptions = ref<{ label: string; value: number }[]>([])
const departmentTree = ref<any[]>([])

const formState = reactive({
  recipient_type: 'users',
  user_ids: [] as number[],
  department_id: undefined as number | undefined,
  type_id: undefined as number | undefined,
  title: '',
  content: ''
})

const rules = {
  recipient_type: [{ required: true, message: t('validations.required') }],
  user_ids: [{ required: true, message: t('validations.required'), type: 'array' }],
  department_id: [{ required: true, message: t('validations.required') }],
  type_id: [{ required: true, message: t('validations.required') }],
  title: [
    { required: true, message: t('validations.required') },
    { max: 100, message: t('validations.maxLength', { max: 100 }) }
  ],
  content: [
    { required: true, message: t('validations.required') },
    { max: 2000, message: t('validations.maxLength', { max: 2000 }) }
  ]
}

const iconMap: Record<string, any> = {
  bell: BellOutlined,
  info: InfoCircleOutlined,
  success: CheckCircleOutlined,
  warning: WarningOutlined,
  message: MessageOutlined,
  mail: MailOutlined,
  alert: AlertOutlined,
  star: StarOutlined,
  file: FileTextOutlined,
  setting: SettingOutlined
}

const getIconComponent = (iconName?: string) => {
  return iconMap[iconName || 'bell'] || BellOutlined
}

const renderedContent = computed(() => {
  if (!formState.content) return t('notifications.previewContent')
  return renderMarkdown(formState.content)
})

onMounted(async () => {
  await Promise.all([
    store.fetchTypes(),
    loadUsers(),
    loadDepartments()
  ])
})

const loadUsers = async () => {
  try {
    const res = await getUsers({ per_page: 1000 })
    if (res.code === 200) {
      userOptions.value = res.data.items.map((user: any) => ({
        label: `${user.username} (${user.email || '-'})`,
        value: user.id
      }))
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

const loadDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      departmentTree.value = buildTree(res.data)
    }
  } catch (error) {
    console.error('加载部门列表失败:', error)
  }
}

const buildTree = (departments: any[]): any[] => {
  const map = new Map()
  const roots: any[] = []

  departments.forEach(dept => {
    map.set(dept.id, {
      title: dept.name,
      value: dept.id,
      key: dept.id,
      children: []
    })
  })

  departments.forEach(dept => {
    const node = map.get(dept.id)
    if (dept.parent_id && map.has(dept.parent_id)) {
      map.get(dept.parent_id).children.push(node)
    } else {
      roots.push(node)
    }
  })

  return roots
}

const filterUserOption = (input: string, option: any) => {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    let res

    if (formState.recipient_type === 'broadcast') {
      res = await sendBroadcast({
        type_id: formState.type_id!,
        title: formState.title,
        content: formState.content
      })
    } else {
      res = await sendNotification({
        recipient_type: formState.recipient_type as 'users' | 'department',
        user_ids: formState.recipient_type === 'users' ? formState.user_ids : undefined,
        department_id: formState.recipient_type === 'department' ? formState.department_id : undefined,
        type_id: formState.type_id!,
        title: formState.title,
        content: formState.content
      })
    }

    if (res.code === 201 || res.code === 200) {
      message.success(t('notifications.sendSuccess'))
      goBack()
    } else {
      message.error(res.message || t('notifications.sendFailed'))
    }
  } catch (error) {
    console.error('发送通知失败:', error)
    message.error(t('notifications.sendFailed'))
  } finally {
    submitting.value = false
  }
}

const goBack = () => {
  // 根据来源路径返回不同的页面
  const isSystemRoute = route.path.startsWith('/system')
  if (isSystemRoute) {
    router.push('/system/notification')
  } else {
    router.push('/notifications')
  }
}
</script>

<style scoped>
.send-notification-page {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
}

.form-hint {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.preview-card {
  background: #fafafa;
}

.preview-header {
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
}

.preview-title {
  font-size: 16px;
  font-weight: 500;
}

.preview-content {
  line-height: 1.8;
  color: #262626;
}

.preview-content :deep(p) {
  margin-bottom: 12px;
}

.preview-content :deep(img) {
  max-width: 100%;
  border-radius: 4px;
}
</style>
