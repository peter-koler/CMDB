<template>
  <div class="login-container">
    <!-- 左侧背景图区域 -->
    <div class="login-visual">
      <div class="background-image"></div>
      <div class="overlay"></div>
      
      <!-- 品牌内容 -->
      <div class="brand-content">
        <div class="brand-header">
          <div class="logo">
            <CloudServerOutlined />
          </div>
          <h1 class="brand-title">IT运维平台</h1>
        </div>
        
        <div class="brand-tagline">
          <h2>智能化运维管理</h2>
          <p>构建高效、可靠的IT基础设施管理体系</p>
        </div>
        
        <!-- 数据展示 -->
        <div class="stats-container">
          <div class="stat-item">
            <div class="stat-number">99.9%</div>
            <div class="stat-label">系统可用性</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-number">24/7</div>
            <div class="stat-label">全天候监控</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-number">&lt;1s</div>
            <div class="stat-label">响应时间</div>
          </div>
        </div>
      </div>
      
      <!-- 装饰元素 -->
      <div class="decoration-circle circle-1"></div>
      <div class="decoration-circle circle-2"></div>
      <div class="decoration-circle circle-3"></div>
    </div>

    <!-- 右侧登录表单区 -->
    <div class="login-form-wrapper">
      <div class="login-form-container">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>请登录您的账户以继续</p>
        </div>

        <a-alert
          v-if="licenseBlocked"
          type="warning"
          show-icon
          class="license-alert"
          :message="licenseWarningText"
        >
          <template #description>
            <a-space>
              <span>请先完成授权，然后再登录系统。</span>
              <a-button type="link" size="small" @click="goLicensePage">前往授权页</a-button>
            </a-space>
          </template>
        </a-alert>



        <a-form
          :model="formState"
          :rules="rules"
          @finish="handleLogin"
          class="login-form"
        >
          <a-form-item name="username">
            <a-input
              v-model:value="formState.username"
              :placeholder="t('login.usernamePlaceholder')"
              size="large"
              class="custom-input"
            >
              <template #prefix>
                <UserOutlined class="input-icon" />
              </template>
            </a-input>
          </a-form-item>

          <a-form-item name="password">
            <a-input-password
              v-model:value="formState.password"
              :placeholder="t('login.passwordPlaceholder')"
              size="large"
              class="custom-input"
            >
              <template #prefix>
                <LockOutlined class="input-icon" />
              </template>
            </a-input-password>
          </a-form-item>

          <!-- 验证码 -->
          <a-form-item name="captcha">
            <a-row :gutter="12">
              <a-col :span="12">
                <a-input
                  v-model:value="formState.captcha"
                  placeholder="请输入验证码"
                  size="large"
                  class="custom-input"
                >
                  <template #prefix>
                    <SafetyOutlined class="input-icon" />
                  </template>
                </a-input>
              </a-col>
              <a-col :span="12">
                <div
                  class="captcha-image"
                  @click="refreshCaptcha"
                  :style="{ backgroundImage: `url(${captchaImage})` }"
                  v-if="captchaImage"
                />
                <a-button
                  v-else
                  size="large"
                  block
                  @click="refreshCaptcha"
                  :loading="captchaLoading"
                >
                  获取验证码
                </a-button>
              </a-col>
            </a-row>
          </a-form-item>

          <a-form-item>
            <div class="login-options">
              <a-checkbox v-model:checked="formState.remember" class="custom-checkbox">
                {{ t('login.rememberMe') }}
              </a-checkbox>
              <a class="forgot-link">忘记密码？</a>
            </div>
          </a-form-item>

          <a-form-item>
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              size="large"
              block
              class="login-button"
            >
              {{ t('login.loginBtn') }}
            </a-button>
          </a-form-item>
        </a-form>

        <div class="form-footer">
          <p>© 2025 IT运维平台. 保留所有权利.</p>
        </div>
      </div>
    </div>

    <!-- 锁定提示对话框 -->
    <a-modal
      v-model:open="lockModalVisible"
      :closable="false"
      :maskClosable="false"
      :footer="null"
      centered
      width="420px"
      class="lock-modal"
    >
      <a-result
        status="error"
        title="账户已被锁定"
        :sub-title="lockModalMessage"
        class="lock-result"
      >
        <template #icon>
          <a-avatar :size="72" class="lock-avatar">
            <LockOutlined class="lock-avatar-icon" />
          </a-avatar>
        </template>
        <template #extra>
          <a-space direction="vertical" class="lock-actions">
            <a-statistic-countdown
              v-if="remainingSeconds > 0"
              title="剩余锁定时间"
              :value="Date.now() + remainingSeconds * 1000"
              format="mm:ss"
              :value-style="lockCountdownStyle"
            />
            <a-button type="primary" size="large" block @click="handleLockModalOk" class="lock-confirm-btn">
              我知道了
            </a-button>
          </a-space>
        </template>
      </a-result>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import {
  UserOutlined,
  LockOutlined,
  CloudServerOutlined,
  SafetyOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'
import { getCaptcha } from '@/api/auth'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const formState = reactive({
  username: '',
  password: '',
  captcha: '',
  remember: false
})

const loading = ref(false)
const lockModalVisible = ref(false)
const lockModalMessage = ref('')
const remainingSeconds = ref(0)
const captchaImage = ref('')
const captchaLoading = ref(false)
const licenseBlocked = ref(false)
const licenseWarningText = ref('')
let countdownTimer: number | null = null

const lockCountdownStyle = {
  color: 'var(--arco-danger)',
  fontSize: '24px',
  fontWeight: 600
}

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

const refreshCaptcha = async () => {
  captchaLoading.value = true
  try {
    const res = await getCaptcha()
    if (res.code === 200) {
      captchaImage.value = res.data.image
      formState.captcha = ''
    }
  } catch (error) {
    message.error('获取验证码失败')
  } finally {
    captchaLoading.value = false
  }
}

const formatRemainingTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes > 0) {
    return `${minutes}分${secs}秒`
  }
  return `${secs}秒`
}

const startCountdown = (seconds: number) => {
  remainingSeconds.value = seconds
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
  countdownTimer = window.setInterval(() => {
    remainingSeconds.value--
    if (remainingSeconds.value <= 0) {
      if (countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }
  }, 1000)
}

const handleLockModalOk = () => {
  lockModalVisible.value = false
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  // 清空密码输入框
  formState.password = ''
}

const goLicensePage = () => {
  router.push('/license')
}

const handleLogin = async () => {
  loading.value = true
  licenseBlocked.value = false
  licenseWarningText.value = ''
  try {
    const success = await userStore.loginAction(formState.username, formState.password, formState.captcha)
    if (success) {
      if (formState.remember) {
        localStorage.setItem('rememberMe', 'true')
        localStorage.setItem('savedUsername', formState.username)
      } else {
        localStorage.removeItem('rememberMe')
        localStorage.removeItem('savedUsername')
      }
      message.success('登录成功')
      router.push('/')
      return
    }
    message.error('登录失败')
  } catch (error: any) {
    const response = error.response
    if (response?.status === 402) {
      licenseBlocked.value = true
      licenseWarningText.value = response?.data?.message || '系统未授权或 License 已过期'
    } else if (response?.status === 400) {
      // 验证码错误或过期
      message.error(response.data?.message || '验证码错误')
      refreshCaptcha()
    } else if (response?.status === 401) {
      const data = response.data

      if (data?.data?.locked) {
        // 账户被锁定，显示对话框
        const seconds = data.data.remaining_seconds || 0
        lockModalMessage.value = data?.message || '账户已被锁定，请稍后再试'
        lockModalVisible.value = true
        startCountdown(seconds)
      } else if (data?.data?.failed_attempts !== undefined) {
        // 密码错误，显示错误次数
        message.error(data?.message || `用户名或密码错误，还剩 ${data.data.remaining_attempts} 次尝试机会`)
        refreshCaptcha()
      } else {
        message.error(data?.message || '用户名或密码错误')
        refreshCaptcha()
      }
    } else {
      message.error(error.response?.data?.message || '登录失败')
      refreshCaptcha()
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const rememberMe = localStorage.getItem('rememberMe')
  const savedUsername = localStorage.getItem('savedUsername')
  if (rememberMe === 'true' && savedUsername) {
    formState.remember = true
    // 使用 nextTick 确保 DOM 更新后再设置值
    nextTick(() => {
      formState.username = savedUsername
    })
  }
  // 页面加载时获取验证码
  refreshCaptcha()
})
</script>

<style scoped>
/* 导入 Plus Jakarta Sans 字体 */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.login-container {
  display: flex;
  min-height: 100vh;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --login-form-bg: var(--arco-surface);
  --login-form-bg-muted: var(--arco-surface-muted);
  --login-form-border: var(--arco-border-strong);
  --login-form-text: var(--app-text-primary);
  --login-form-text-secondary: var(--app-text-secondary);
  --login-form-text-muted: var(--app-text-muted);
  --login-focus-ring: color-mix(in srgb, var(--app-accent) 14%, transparent);
  --login-glass-bg: color-mix(in srgb, white 14%, transparent);
  --login-glass-border: color-mix(in srgb, white 20%, transparent);
  --login-glass-strong: color-mix(in srgb, white 20%, transparent);
  --login-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.05),
    0 10px 15px -3px rgba(0, 0, 0, 0.05),
    0 20px 25px -5px rgba(0, 0, 0, 0.03);
}

/* 左侧视觉区域 */
.login-visual {
  flex: 1.2;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

/* 背景图 */
.background-image {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: url('https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1920&q=80');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  filter: saturate(1.1) contrast(1.05);
}

/* 深色遮罩层 */
.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--arco-primary-active) 88%, transparent) 0%,
    color-mix(in srgb, var(--arco-primary) 78%, transparent) 50%,
    rgba(15, 23, 42, 0.85) 100%
  );
}

/* 品牌内容 */
.brand-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: white;
  max-width: 520px;
  padding: 40px;
}

.brand-header {
  margin-bottom: 48px;
}

.logo {
  width: 80px;
  height: 80px;
  background: var(--login-glass-bg);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  backdrop-filter: blur(10px);
  border: 1px solid var(--login-glass-border);
}

.logo :deep(.anticon) {
  font-size: 40px;
  color: white;
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.02em;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.brand-tagline {
  margin-bottom: 56px;
}

.brand-tagline h2 {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 16px 0;
  opacity: 0.95;
}

.brand-tagline p {
  font-size: 17px;
  font-weight: 400;
  opacity: 0.75;
  margin: 0;
  line-height: 1.6;
}

/* 数据统计 */
.stats-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding: 24px 32px;
  background: color-mix(in srgb, white 10%, transparent);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  border: 1px solid var(--login-glass-border);
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--arco-success);
  margin-bottom: 4px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.stat-label {
  font-size: 14px;
  font-weight: 500;
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--login-glass-strong);
}

/* 装饰圆形 */
.decoration-circle {
  position: absolute;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, white 12%, transparent);
  z-index: 1;
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  right: -100px;
  background: radial-gradient(circle, color-mix(in srgb, var(--arco-primary) 18%, transparent) 0%, transparent 70%);
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: 10%;
  left: -50px;
  background: radial-gradient(circle, color-mix(in srgb, var(--arco-success) 14%, transparent) 0%, transparent 70%);
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 40%;
  right: 10%;
  background: radial-gradient(circle, color-mix(in srgb, white 8%, transparent) 0%, transparent 70%);
}

/* 右侧表单区 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background-color: var(--arco-app-bg);
}

.login-form-container {
  width: 100%;
  max-width: 440px;
  background: var(--login-form-bg);
  border-radius: 20px;
  padding: 48px;
  box-shadow: var(--login-shadow);
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: var(--login-form-text);
  margin: 0 0 8px 0;
}

.form-header p {
  font-size: 15px;
  color: var(--login-form-text-secondary);
  margin: 0;
}

.license-alert {
  margin-bottom: 20px;
}

/* 自定义输入框样式 */
.custom-input :deep(.ant-input) {
  border-radius: 10px;
  border-color: var(--login-form-border);
  padding-left: 44px;
  height: 52px;
  font-size: 15px;
  transition: all 0.2s ease;
  background: var(--login-form-bg-muted);
}

.custom-input :deep(.ant-input:hover) {
  border-color: var(--arco-primary-hover);
  background: var(--login-form-bg);
}

.custom-input :deep(.ant-input:focus) {
  border-color: var(--app-accent);
  background: var(--login-form-bg);
  box-shadow: 0 0 0 4px var(--login-focus-ring);
}

.custom-input :deep(.ant-input-prefix) {
  left: 16px;
}

.input-icon {
  color: var(--login-form-text-muted);
  font-size: 18px;
  transition: color 0.2s ease;
}

.custom-input :deep(.ant-input:focus) + .ant-input-prefix .input-icon {
  color: var(--app-accent);
}

/* 登录选项 */
.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.custom-checkbox :deep(.ant-checkbox-checked .ant-checkbox-inner) {
  background-color: var(--app-accent);
  border-color: var(--app-accent);
}

.custom-checkbox :deep(.ant-checkbox-wrapper:hover .ant-checkbox-inner) {
  border-color: var(--app-accent);
}

.forgot-link {
  color: var(--arco-primary-hover);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.2s ease;
}

.forgot-link:hover {
  color: var(--app-accent);
}

/* 登录按钮 */
.login-button {
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--arco-primary-active) 0%, var(--arco-primary-gradient-end) 100%);
  border: none;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.login-button:hover {
  background: linear-gradient(135deg, var(--arco-primary-active) 0%, var(--arco-primary-hover) 100%);
  transform: translateY(-1px);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--app-accent) 34%, transparent);
}

.login-button:active {
  transform: translateY(0);
}

/* 页脚 */
.form-footer {
  margin-top: 32px;
  text-align: center;
  border-top: 1px solid var(--login-form-border);
  padding-top: 24px;
}

.form-footer p {
  font-size: 13px;
  color: var(--login-form-text-muted);
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .login-container {
    flex-direction: column;
  }
  
  .login-visual {
    flex: none;
    min-height: 280px;
    padding: 40px 24px;
  }
  
  .brand-content {
    padding: 0;
  }
  
  .brand-header {
    margin-bottom: 24px;
  }
  
  .logo {
    width: 60px;
    height: 60px;
    border-radius: 16px;
  }
  
  .logo :deep(.anticon) {
    font-size: 28px;
  }
  
  .brand-title {
    font-size: 28px;
  }
  
  .brand-tagline {
    display: none;
  }
  
  .stats-container {
    padding: 16px 24px;
    gap: 24px;
  }
  
  .stat-number {
    font-size: 24px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  .stat-divider {
    height: 32px;
  }
  
  .login-form-wrapper {
    padding: 32px 24px;
  }
  
  .login-form-container {
    padding: 32px 24px;
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }
  
  .decoration-circle {
    display: none;
  }
}

@media (max-width: 640px) {
  .login-visual {
    min-height: 220px;
  }
  
  .brand-title {
    font-size: 24px;
  }
  
  .stats-container {
    padding: 12px 20px;
    gap: 16px;
  }
  
  .stat-number {
    font-size: 20px;
  }
  
  .form-header h2 {
    font-size: 24px;
  }
  
  .custom-input :deep(.ant-input) {
    height: 48px;
  }
  
  .login-button {
    height: 48px;
  }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .login-button,
  .custom-input :deep(.ant-input),
  .forgot-link,
  .input-icon {
    transition: none;
  }
  
  .login-button:hover {
    transform: none;
  }
}

/* 锁定对话框样式 */
.lock-modal :deep(.ant-modal-content) {
  border-radius: 16px;
  overflow: hidden;
}

.lock-modal :deep(.ant-modal-body) {
  padding: 32px 24px;
}

.lock-result :deep(.ant-result-icon) {
  margin-bottom: 24px;
}

.lock-result :deep(.ant-result-title) {
  font-size: 20px;
  font-weight: 600;
  color: var(--login-form-text);
  margin-bottom: 8px;
}

.lock-result :deep(.ant-result-subtitle) {
  font-size: 14px;
  color: var(--login-form-text-secondary);
  line-height: 1.6;
}

.lock-result :deep(.ant-result-extra) {
  margin-top: 24px;
}

.lock-result :deep(.ant-statistic-title) {
  font-size: 12px;
  color: var(--login-form-text-muted);
  margin-bottom: 4px;
}

.lock-avatar {
  background-color: color-mix(in srgb, var(--arco-danger) 12%, var(--login-form-bg));
  color: var(--arco-danger);
}

.lock-avatar-icon {
  font-size: 32px;
}

.lock-actions {
  width: 100%;
}

.lock-confirm-btn {
  margin-top: 16px;
}

/* 验证码图片样式 */
.captcha-image {
  width: 100%;
  height: 40px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid var(--login-form-border);
  transition: all 0.3s ease;
}

.captcha-image:hover {
  border-color: var(--app-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--app-accent) 20%, transparent);
}
</style>
