<template>
  <div class="page-container">
    <a-spin :spinning="loading">
      <a-row :gutter="[16, 16]">
        <a-col :span="24">
          <a-card :bordered="false" class="config-card">
            <template #title>
              <div class="card-title">
                <SafetyCertificateOutlined class="title-icon" />
                <span>{{ t('config.token') }}</span>
              </div>
            </template>
            <a-descriptions :column="{ xs: 1, sm: 1, md: 2, lg: 2 }" bordered>
              <a-descriptions-item :label="t('config.accessTokenExpire')">
                <a-input-number 
                  v-model:value="configs.access_token_expire" 
                  :min="1" 
                  :max="1440"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">分钟</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('config.refreshTokenExpire')">
                <a-input-number 
                  v-model:value="configs.refresh_token_expire" 
                  :min="1" 
                  :max="525600"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">分钟</span>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="[16, 16]" style="margin-top: 0">
        <a-col :span="24">
          <a-card :bordered="false" class="config-card">
            <template #title>
              <div class="card-title">
                <LockOutlined class="title-icon" />
                <span>{{ t('config.password') }}</span>
              </div>
            </template>
            <a-descriptions :column="{ xs: 1, sm: 1, md: 2, lg: 2 }" bordered>
              <a-descriptions-item :label="t('config.passwordMinLength')">
                <a-input-number 
                  v-model:value="configs.password_min_length" 
                  :min="6" 
                  :max="32"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">位</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('config.passwordForceChangeDays')">
                <a-input-number 
                  v-model:value="configs.password_force_change_days" 
                  :min="0" 
                  :max="365"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">天 (0表示不强制)</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('config.passwordHistoryCount')">
                <a-input-number 
                  v-model:value="configs.password_history_count" 
                  :min="0" 
                  :max="20"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">次</span>
              </a-descriptions-item>
              <a-descriptions-item label="密码复杂度要求">
                <a-space direction="vertical">
                  <a-checkbox v-model:checked="configs.require_uppercase">
                    {{ t('config.requireUppercase') }}
                  </a-checkbox>
                  <a-checkbox v-model:checked="configs.require_lowercase">
                    {{ t('config.requireLowercase') }}
                  </a-checkbox>
                  <a-checkbox v-model:checked="configs.require_digit">
                    {{ t('config.requireDigit') }}
                  </a-checkbox>
                  <a-checkbox v-model:checked="configs.require_special">
                    {{ t('config.requireSpecial') }}
                  </a-checkbox>
                </a-space>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="[16, 16]" style="margin-top: 0">
        <a-col :xs="24" :sm="24" :md="12">
          <a-card :bordered="false" class="config-card">
            <template #title>
              <div class="card-title">
                <SecurityScanOutlined class="title-icon" />
                <span>{{ t('config.login') }}</span>
              </div>
            </template>
            <a-descriptions :column="1" bordered>
              <a-descriptions-item :label="t('config.maxLoginFailures')">
                <a-input-number 
                  v-model:value="configs.max_login_failures" 
                  :min="1" 
                  :max="20"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">次</span>
              </a-descriptions-item>
              <a-descriptions-item :label="t('config.lockDurationHours')">
                <a-input-number 
                  v-model:value="configs.lock_duration_hours" 
                  :min="1" 
                  :max="168"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">小时</span>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
        <a-col :xs="24" :sm="24" :md="12">
          <a-card :bordered="false" class="config-card">
            <template #title>
              <div class="card-title">
                <FileTextOutlined class="title-icon" />
                <span>{{ t('config.log') }}</span>
              </div>
            </template>
            <a-descriptions :column="1" bordered>
              <a-descriptions-item :label="t('config.logRetentionDays')">
                <a-input-number 
                  v-model:value="configs.log_retention_days" 
                  :min="1" 
                  :max="365"
                  style="width: 100%"
                  class="config-input"
                />
                <span class="unit">天</span>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>
      </a-row>

      <div class="footer-actions">
        <a-button type="primary" @click="handleSave" :loading="saving" size="large">
          <template #icon><SaveOutlined /></template>
          {{ t('common.save') }}
        </a-button>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import {
  SafetyCertificateOutlined,
  LockOutlined,
  SecurityScanOutlined,
  FileTextOutlined,
  SaveOutlined
} from '@ant-design/icons-vue'
import { getConfigs, updateConfigs } from '@/api/config'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)

const configs = reactive({
  access_token_expire: 30,
  refresh_token_expire: 10080,
  password_min_length: 8,
  password_force_change_days: 90,
  password_history_count: 5,
  max_login_failures: 5,
  lock_duration_hours: 24,
  log_retention_days: 30,
  require_uppercase: true,
  require_lowercase: true,
  require_digit: true,
  require_special: true
})

const fetchConfigs = async () => {
  loading.value = true
  try {
    const res = await getConfigs()
    if (res.code === 200) {
      const data = res.data
      Object.keys(configs).forEach(key => {
        if (data[key] !== undefined) {
          if (typeof configs[key] === 'boolean') {
            configs[key] = data[key].value === 'true'
          } else if (typeof configs[key] === 'number') {
            configs[key] = parseInt(data[key].value)
          }
        }
      })
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const data: Record<string, any> = {}
    Object.keys(configs).forEach(key => {
      data[key] = String(configs[key])
    })
    await updateConfigs(data)
    message.success('保存成功')
  } catch (error: any) {
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped>
.page-container {
  padding-bottom: 80px;
}

.config-card {
  border-radius: 8px;
  height: 100%;
}

.config-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
  padding: 0 24px;
}

.config-card :deep(.ant-card-body) {
  padding: 24px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.title-icon {
  color: #1890ff;
  font-size: 18px;
}

.config-input {
  max-width: 200px;
}

.unit {
  margin-left: 8px;
  color: #999;
  font-size: 13px;
}

:deep(.ant-descriptions-item-label) {
  font-weight: 500;
  background: #fafafa;
}

:deep(.ant-descriptions-item-content) {
  padding: 16px 24px;
}

.footer-actions {
  position: fixed;
  bottom: 0;
  right: 0;
  left: 208px;
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  text-align: center;
  z-index: 99;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
}

@media (max-width: 768px) {
  .footer-actions {
    left: 0;
  }
  
  .config-input {
    max-width: 100%;
  }
}
</style>
