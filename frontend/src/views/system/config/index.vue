<template>
  <div class="page-container">
    <a-spin :spinning="loading">
      <!-- Logo配置 -->
      <a-row :gutter="[16, 16]">
        <a-col :span="24">
          <a-card :bordered="false" class="config-card">
            <template #title>
              <div class="card-title">
                <PictureOutlined class="title-icon" />
                <span>界面配置</span>
              </div>
            </template>
            <a-descriptions :column="{ xs: 1, sm: 1, md: 2, lg: 2 }" bordered>
              <a-descriptions-item label="系统Logo">
                <div class="logo-upload-container">
                  <a-upload
                    name="file"
                    :show-upload-list="false"
                    :before-upload="beforeUpload"
                    :custom-request="handleLogoUpload"
                    accept=".png,.jpg,.jpeg,.gif,.svg,.webp"
                  >
                    <div class="logo-preview" v-if="logoUrl">
                      <img :src="logoUrl" alt="logo" class="logo-image" />
                      <div class="logo-overlay">
                        <EditOutlined class="overlay-icon" />
                        <span>更换Logo</span>
                      </div>
                    </div>
                    <div class="logo-upload-placeholder" v-else>
                      <PlusOutlined class="upload-icon" />
                      <div class="upload-text">点击上传Logo</div>
                      <div class="upload-hint">支持 PNG, JPG, SVG 格式，最大 2MB</div>
                    </div>
                  </a-upload>
                  <a-button 
                    v-if="logoUrl" 
                    type="link" 
                    danger 
                    @click="handleDeleteLogo"
                    class="delete-logo-btn"
                  >
                    <DeleteOutlined />
                    删除Logo
                  </a-button>
                </div>
              </a-descriptions-item>
              <a-descriptions-item label="系统名称">
                <a-input 
                  v-model:value="configs.site_name" 
                  placeholder="请输入系统名称"
                  style="width: 100%"
                  class="config-input"
                  :maxLength="50"
                />
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
  SaveOutlined,
  PictureOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'
import { getConfigs, updateConfigs, uploadLogo, deleteLogo } from '@/api/config'
import { getBaseURL } from '@/utils/request'

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
  require_special: true,
  site_name: 'Arco CMDB'
})

const logoUrl = ref('')
const uploading = ref(false)

const fetchConfigs = async () => {
  loading.value = true
  try {
    const res = await getConfigs()
    if (res.code === 200) {
      const data = res.data
      ;(Object.keys(configs) as Array<keyof typeof configs>).forEach(key => {
        if (data[key] !== undefined) {
          if (typeof configs[key] === 'boolean') {
            ;(configs as any)[key] = data[key].value === 'true'
          } else if (typeof configs[key] === 'number') {
            ;(configs as any)[key] = parseInt(data[key].value)
          } else {
            ;(configs as any)[key] = data[key].value
          }
        }
      })
      // 加载Logo
      if (data.site_logo?.value) {
        logoUrl.value = getBaseURL() + data.site_logo.value
      }
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
    const data: Record<string, string> = {}
    ;(Object.keys(configs) as Array<keyof typeof configs>).forEach(key => {
      data[key as string] = String(configs[key])
    })
    await updateConfigs(data)
    message.success('保存成功')
    // 刷新页面以应用新的系统名称
    window.location.reload()
  } catch (error: any) {
    message.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const beforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    message.error('只能上传图片文件!')
    return false
  }
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isLt2M) {
    message.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

const handleLogoUpload = async ({ file }: { file: File }) => {
  uploading.value = true
  try {
    const res = await uploadLogo(file)
    if (res.code === 200) {
      logoUrl.value = getBaseURL() + res.data.logo_url
      message.success('Logo上传成功')
    } else {
      message.error(res.message || '上传失败')
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const handleDeleteLogo = async () => {
  try {
    const res = await deleteLogo()
    if (res.code === 200) {
      logoUrl.value = ''
      message.success('Logo删除成功')
    } else {
      message.error(res.message || '删除失败')
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
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

.logo-upload-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.logo-preview {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px dashed #d9d9d9;
  transition: all 0.3s;
}

.logo-preview:hover {
  border-color: #1890ff;
}

.logo-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 8px;
}

.logo-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s;
}

.logo-preview:hover .logo-overlay {
  opacity: 1;
}

.overlay-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.logo-upload-placeholder {
  width: 120px;
  height: 120px;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #fafafa;
}

.logo-upload-placeholder:hover {
  border-color: #1890ff;
  background: #e6f7ff;
}

.upload-icon {
  font-size: 32px;
  color: #999;
  margin-bottom: 8px;
}

.upload-text {
  color: #666;
  font-size: 14px;
}

.upload-hint {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
  text-align: center;
  padding: 0 8px;
}

.delete-logo-btn {
  margin-top: 8px;
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
