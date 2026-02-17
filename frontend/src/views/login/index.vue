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
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { 
  UserOutlined, 
  LockOutlined, 
  CloudServerOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/user'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const formState = reactive({
  username: '',
  password: '',
  remember: false
})

const loading = ref(false)

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  loading.value = true
  try {
    const success = await userStore.loginAction(formState.username, formState.password)
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
    } else {
      message.error('用户名或密码错误')
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const rememberMe = localStorage.getItem('rememberMe')
  if (rememberMe === 'true') {
    formState.remember = true
    formState.username = localStorage.getItem('savedUsername') || ''
  }
})
</script>

<style scoped>
/* 导入 Plus Jakarta Sans 字体 */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.login-container {
  display: flex;
  min-height: 100vh;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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
    rgba(30, 64, 175, 0.92) 0%,
    rgba(30, 58, 138, 0.88) 50%,
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
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
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
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: #22C55E;
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
  background: rgba(255, 255, 255, 0.2);
}

/* 装饰圆形 */
.decoration-circle {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 1;
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  right: -100px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: 10%;
  left: -50px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.1) 0%, transparent 70%);
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 40%;
  right: 10%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.05) 0%, transparent 70%);
}

/* 右侧表单区 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background-color: #F8FAFC;
}

.login-form-container {
  width: 100%;
  max-width: 440px;
  background: white;
  border-radius: 20px;
  padding: 48px;
  box-shadow: 
    0 4px 6px -1px rgba(0, 0, 0, 0.05),
    0 10px 15px -3px rgba(0, 0, 0, 0.05),
    0 20px 25px -5px rgba(0, 0, 0, 0.03);
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 8px 0;
}

.form-header p {
  font-size: 15px;
  color: #64748B;
  margin: 0;
}

/* 自定义输入框样式 */
.custom-input :deep(.ant-input) {
  border-radius: 10px;
  border-color: #E2E8F0;
  padding-left: 44px;
  height: 52px;
  font-size: 15px;
  transition: all 0.2s ease;
  background: #F8FAFC;
}

.custom-input :deep(.ant-input:hover) {
  border-color: #3B82F6;
  background: white;
}

.custom-input :deep(.ant-input:focus) {
  border-color: #1E40AF;
  background: white;
  box-shadow: 0 0 0 4px rgba(30, 64, 175, 0.08);
}

.custom-input :deep(.ant-input-prefix) {
  left: 16px;
}

.input-icon {
  color: #94A3B8;
  font-size: 18px;
  transition: color 0.2s ease;
}

.custom-input :deep(.ant-input:focus) + .ant-input-prefix .input-icon {
  color: #1E40AF;
}

/* 登录选项 */
.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.custom-checkbox :deep(.ant-checkbox-checked .ant-checkbox-inner) {
  background-color: #1E40AF;
  border-color: #1E40AF;
}

.custom-checkbox :deep(.ant-checkbox-wrapper:hover .ant-checkbox-inner) {
  border-color: #1E40AF;
}

.forgot-link {
  color: #3B82F6;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.2s ease;
}

.forgot-link:hover {
  color: #1E40AF;
}

/* 登录按钮 */
.login-button {
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
  border: none;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.login-button:hover {
  background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(30, 64, 175, 0.35);
}

.login-button:active {
  transform: translateY(0);
}

/* 页脚 */
.form-footer {
  margin-top: 32px;
  text-align: center;
  border-top: 1px solid #E2E8F0;
  padding-top: 24px;
}

.form-footer p {
  font-size: 13px;
  color: #94A3B8;
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
</style>
