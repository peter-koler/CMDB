<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h1>{{ t('login.title') }}</h1>
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
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item name="password">
          <a-input-password
            v-model:value="formState.password"
            :placeholder="t('login.passwordPlaceholder')"
            size="large"
          >
            <template #prefix>
              <LockOutlined />
            </template>
          </a-input-password>
        </a-form-item>
        <a-form-item>
          <div class="login-options">
            <a-checkbox v-model:checked="formState.remember">
              {{ t('login.rememberMe') }}
            </a-checkbox>
          </div>
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            size="large"
            block
          >
            {{ t('login.loginBtn') }}
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
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
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 24px;
  color: #333;
  margin: 0;
}

.login-form {
  margin-top: 24px;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
