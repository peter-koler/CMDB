<template>
  <div class="profile-page">
    <a-row :gutter="[24, 24]">
      <a-col :xs="24" :sm="24" :lg="8">
        <a-card class="profile-card" :bordered="false">
          <div class="avatar-section">
            <div class="avatar-wrapper" @click="triggerAvatarUpload">
              <a-avatar :size="100" class="user-avatar">
                <template #icon>
                  <img v-if="profileData.avatar" :src="avatarUrl" alt="avatar" class="avatar-img" />
                  <span v-else class="avatar-text">{{ profileData.username?.charAt(0)?.toUpperCase() }}</span>
                </template>
              </a-avatar>
              <div class="avatar-overlay">
                <CameraOutlined />
                <span>{{ t('profile.changeAvatar') }}</span>
              </div>
            </div>
            <input
              ref="avatarInput"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              style="display: none"
              @change="handleAvatarChange"
            />
            <h3 class="username">{{ profileData.username }}</h3>
            <div class="user-meta">
              <a-tag :color="profileData.role === 'admin' ? 'error' : 'processing'" class="role-tag">
                {{ profileData.role === 'admin' ? t('user.admin') : t('user.user') }}
              </a-tag>
            </div>
            <div v-if="profileData.department_name" class="department-info">
              <ApartmentOutlined class="dept-icon" />
              <span>{{ profileData.department_name }}</span>
            </div>
          </div>
          <a-divider style="margin: 16px 0" />
          <div class="user-stats">
            <div class="stat-item">
              <span class="stat-label">{{ t('user.email') }}</span>
              <span class="stat-value">{{ profileData.email || '-' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">{{ t('user.phone') }}</span>
              <span class="stat-value">{{ profileData.phone || '-' }}</span>
            </div>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="24" :lg="16">
        <a-card :bordered="false" class="form-section">
          <a-tabs v-model:activeKey="activeTab">
            <a-tab-pane key="info" :tab="t('profile.basicInfo')">
              <a-form
                :model="profileData"
                layout="vertical"
                class="profile-form"
                @finish="handleSave"
              >
                <a-row :gutter="24">
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('user.username')">
                      <a-input v-model:value="profileData.username" disabled>
                        <template #prefix>
                          <UserOutlined class="input-icon" />
                        </template>
                      </a-input>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('user.role')">
                      <a-input :value="profileData.role === 'admin' ? t('user.admin') : t('user.user')" disabled>
                        <template #prefix>
                          <SafetyOutlined class="input-icon" />
                        </template>
                      </a-input>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('user.email')" name="email" :rules="emailRules">
                      <a-input v-model:value="profileData.email" :placeholder="t('profile.emailPlaceholder')">
                        <template #prefix>
                          <MailOutlined class="input-icon" />
                        </template>
                      </a-input>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('user.phone')" name="phone" :rules="phoneRules">
                      <a-input v-model:value="profileData.phone" :placeholder="t('profile.phonePlaceholder')">
                        <template #prefix>
                          <PhoneOutlined class="input-icon" />
                        </template>
                      </a-input>
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-form-item class="form-actions">
                  <a-button type="primary" html-type="submit" :loading="saving">
                    <template #icon><SaveOutlined /></template>
                    {{ t('common.save') }}
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>
            <a-tab-pane key="password" :tab="t('profile.changePassword')">
              <a-form
                :model="passwordData"
                layout="vertical"
                class="profile-form"
                @finish="handleChangePassword"
              >
                <a-row :gutter="24">
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('profile.oldPassword')" name="oldPassword" :rules="[{ required: true, message: t('profile.oldPasswordRequired') }]">
                      <a-input-password v-model:value="passwordData.oldPassword" :placeholder="t('profile.oldPassword')">
                        <template #prefix>
                          <LockOutlined class="input-icon" />
                        </template>
                      </a-input-password>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12"></a-col>
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('profile.newPassword')" name="newPassword" :rules="[{ required: true, message: t('profile.newPasswordRequired') }]">
                      <a-input-password v-model:value="passwordData.newPassword" :placeholder="t('profile.newPassword')">
                        <template #prefix>
                          <LockOutlined class="input-icon" />
                        </template>
                      </a-input-password>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :sm="12">
                    <a-form-item :label="t('profile.confirmPassword')" name="confirmPassword" :rules="confirmPasswordRules">
                      <a-input-password v-model:value="passwordData.confirmPassword" :placeholder="t('profile.confirmPassword')">
                        <template #prefix>
                          <LockOutlined class="input-icon" />
                        </template>
                      </a-input-password>
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-form-item class="form-actions">
                  <a-button type="primary" html-type="submit" :loading="changingPassword">
                    <template #icon><KeyOutlined /></template>
                    {{ t('profile.changePassword') }}
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { 
  CameraOutlined, 
  ApartmentOutlined, 
  UserOutlined,
  SafetyOutlined,
  MailOutlined,
  PhoneOutlined,
  LockOutlined,
  SaveOutlined,
  KeyOutlined
} from '@ant-design/icons-vue'
import { getProfile, updateProfile, uploadAvatar, changePassword } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { getBaseURL } from '@/utils/request'

const { t } = useI18n()
const userStore = useUserStore()

const avatarInput = ref<HTMLInputElement>()
const saving = ref(false)
const changingPassword = ref(false)
const activeTab = ref('info')

const profileData = reactive({
  username: '',
  email: '',
  phone: '',
  avatar: '',
  role: '',
  department_name: ''
})

const passwordData = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const avatarUrl = computed(() => {
  if (!profileData.avatar) return ''
  if (profileData.avatar.startsWith('http')) return profileData.avatar
  return getBaseURL() + profileData.avatar
})

const emailRules = [
  { type: 'email', message: t('profile.invalidEmail') }
]

const phoneRules = [
  { pattern: /^1[3-9]\d{9}$/, message: t('profile.invalidPhone') }
]

const confirmPasswordRules = [
  { required: true, message: t('profile.confirmPasswordRequired') },
  { validator: (_rule: any, value: string) => {
    if (value !== passwordData.newPassword) {
      return Promise.reject(t('profile.passwordMismatch'))
    }
    return Promise.resolve()
  }}
]

const loadProfile = async () => {
  try {
    const res = await getProfile()
    if (res.code === 200) {
      Object.assign(profileData, res.data)
    }
  } catch (error) {
    console.error('Failed to load profile:', error)
  }
}

const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const handleAvatarChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  if (file.size > 2 * 1024 * 1024) {
    message.error(t('profile.avatarTooLarge'))
    return
  }

  try {
    const res = await uploadAvatar(file)
    if (res.code === 200) {
      profileData.avatar = res.data.avatar
      message.success(t('profile.avatarUpdated'))
      await userStore.getUserInfo()
    }
  } catch (error) {
    message.error(t('profile.avatarUploadFailed'))
  } finally {
    target.value = ''
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await updateProfile({
      email: profileData.email,
      phone: profileData.phone
    })
    if (res.code === 200) {
      message.success(t('common.saveSuccess'))
      await userStore.getUserInfo()
    }
  } catch (error) {
    message.error(t('common.saveFailed'))
  } finally {
    saving.value = false
  }
}

const handleChangePassword = async () => {
  changingPassword.value = true
  try {
    const res = await changePassword(passwordData.oldPassword, passwordData.newPassword)
    if (res.code === 200) {
      message.success(t('profile.passwordChanged'))
      passwordData.oldPassword = ''
      passwordData.newPassword = ''
      passwordData.confirmPassword = ''
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || t('profile.passwordChangeFailed'))
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile-page {
  max-width: 1200px;
  margin: 0 auto;
}

.profile-card {
  background: linear-gradient(180deg, #f0f5ff 0%, #ffffff 100%);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.avatar-section {
  text-align: center;
  padding: 32px 24px 16px;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
  cursor: pointer;
  margin-bottom: 16px;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.user-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.35);
  border: 3px solid #fff;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-text {
  font-size: 40px;
  font-weight: 600;
  color: white;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
  font-size: 20px;
}

.avatar-overlay span {
  font-size: 12px;
  margin-top: 4px;
}

.username {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 600;
  color: #1f1f1f;
}

.user-meta {
  margin-bottom: 8px;
}

.role-tag {
  font-size: 12px;
  padding: 2px 12px;
  border-radius: 12px;
}

.department-info {
  color: #666;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 16px;
}

.dept-icon {
  font-size: 12px;
}

.user-stats {
  padding: 0 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #8c8c8c;
  font-size: 13px;
}

.stat-value {
  color: #1f1f1f;
  font-size: 14px;
  font-weight: 500;
}

.form-section {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  min-height: 400px;
}

.form-section :deep(.ant-card-body) {
  padding: 0;
}

.form-section :deep(.ant-tabs-nav) {
  padding: 0 24px;
  margin-bottom: 0;
  background: #fafafa;
}

.form-section :deep(.ant-tabs-tab) {
  padding: 16px 0;
}

.profile-form {
  padding: 24px;
}

.input-icon {
  color: #bfbfbf;
}

.form-actions {
  margin-top: 24px;
  margin-bottom: 0;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

@media (max-width: 768px) {
  .profile-card {
    margin-bottom: 0;
  }

  .avatar-section {
    padding: 24px 16px 12px;
  }

  .profile-form {
    padding: 16px;
  }

  .form-section :deep(.ant-tabs-nav) {
    padding: 0 16px;
  }
}
</style>
