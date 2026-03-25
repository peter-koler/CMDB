<template>
  <a-config-provider :theme="themeConfig" :locale="antdLocale">
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { theme as antdTheme } from 'ant-design-vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import {
  startIdleLogoutCheck,
  startTokenExpirationCheck,
  stopIdleLogoutCheck,
  stopTokenExpirationCheck
} from '@/utils/tokenManager'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import enUS from 'ant-design-vue/es/locale/en_US'

const appStore = useAppStore()
const userStore = useUserStore()

const applyThemeAttribute = (mode: 'light' | 'dark') => {
  document.documentElement.dataset.theme = mode
}

onMounted(() => {
  applyThemeAttribute(appStore.theme)
  if (userStore.token) {
    startTokenExpirationCheck()
    startIdleLogoutCheck()
  }
})

onUnmounted(() => {
  stopTokenExpirationCheck()
  stopIdleLogoutCheck()
})

watch(
  () => appStore.theme,
  (mode) => {
    applyThemeAttribute(mode)
  },
  { immediate: true }
)

const themeConfig = computed(() => ({
  algorithm:
    appStore.theme === 'dark'
      ? antdTheme.darkAlgorithm
      : antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: appStore.theme === 'dark' ? '#4f8cff' : '#0075e6',
    colorBgBase: appStore.theme === 'dark' ? '#111827' : '#f7f8fa',
    colorBgLayout: appStore.theme === 'dark' ? '#111827' : '#f7f8fa',
    colorBgContainer: appStore.theme === 'dark' ? '#161b22' : '#ffffff',
    colorBgElevated: appStore.theme === 'dark' ? '#1d2430' : '#ffffff',
    colorBorder: appStore.theme === 'dark' ? '#293244' : '#f0f0f0',
    colorBorderSecondary: appStore.theme === 'dark' ? '#384355' : '#f0f0f0',
    colorText: appStore.theme === 'dark' ? 'rgba(255,255,255,0.92)' : '#1f2937',
    colorTextSecondary: appStore.theme === 'dark' ? 'rgba(255,255,255,0.68)' : '#667085',
    colorFillAlter: appStore.theme === 'dark' ? '#1a2230' : '#f6f8fb',
    borderRadius: 12,
    controlHeight: 40,
    controlHeightLG: 44,
    fontSize: 15,
    fontSizeSM: 13,
    fontSizeLG: 16,
    fontFamily: "'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
  }
}))

const antdLocale = computed(() => {
  return appStore.language === 'en-US' ? enUS : zhCN
})
</script>
