<template>
  <a-config-provider :theme="themeConfig" :locale="antdLocale">
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { startTokenExpirationCheck, stopTokenExpirationCheck } from '@/utils/tokenManager'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import enUS from 'ant-design-vue/es/locale/en_US'

const appStore = useAppStore()
const userStore = useUserStore()

onMounted(() => {
  if (userStore.token) {
    startTokenExpirationCheck()
  }
})

onUnmounted(() => {
  stopTokenExpirationCheck()
})

const themeConfig = computed(() => ({
  algorithm: appStore.theme === 'dark' ? undefined : undefined,
  token: {
    colorPrimary: '#1890ff',
    colorBgContainer: appStore.theme === 'dark' ? '#141414' : '#ffffff',
    colorBgElevated: appStore.theme === 'dark' ? '#1f1f1f' : '#ffffff',
    colorText: appStore.theme === 'dark' ? '#ffffffd9' : '#000000d9',
  }
}))

const antdLocale = computed(() => {
  return appStore.language === 'en-US' ? enUS : zhCN
})
</script>
