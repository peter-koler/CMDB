import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const theme = ref<'light' | 'dark'>(localStorage.getItem('theme') as 'light' | 'dark' || 'light')
  const language = ref<'zh-CN' | 'en-US'>(localStorage.getItem('language') as 'zh-CN' | 'en-US' || 'zh-CN')
  const sidebarCollapsed = ref(false)

  const setTheme = (newTheme: 'light' | 'dark') => {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
  }

  const setLanguage = (newLanguage: 'zh-CN' | 'en-US') => {
    language.value = newLanguage
    localStorage.setItem('language', newLanguage)
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    theme,
    language,
    sidebarCollapsed,
    setTheme,
    setLanguage,
    toggleSidebar
  }
})
