<template>
  <a-layout class="basic-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
      :width="208"
      :collapsedWidth="80"
      class="layout-sider"
      breakpoint="lg"
      @collapse="onCollapse"
    >
      <div class="logo">
        <div class="logo-icon">
          <AppstoreOutlined />
        </div>
        <span v-if="!collapsed" class="logo-text">{{ t('login.title') }}</span>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        theme="dark"
        mode="inline"
        class="sider-menu"
      >
        <a-menu-item key="dashboard" @click="navigateTo('/dashboard')">
          <template #icon><DashboardOutlined /></template>
          <span>{{ t('menu.dashboard') }}</span>
        </a-menu-item>
        
        <a-sub-menu key="cmdb">
          <template #icon><CloudServerOutlined /></template>
          <template #title>{{ t('menu.cmdb') }}</template>
          <a-menu-item key="instance" @click="navigateTo('/cmdb/instance')">
            <template #icon><HddOutlined /></template>
            <span>{{ t('menu.instance') }}</span>
          </a-menu-item>
          <a-menu-item key="search" @click="navigateTo('/cmdb/search')">
            <template #icon><SearchOutlined /></template>
            <span>{{ t('menu.search') }}</span>
          </a-menu-item>
          <a-menu-item key="history" @click="navigateTo('/cmdb/history')">
            <template #icon><HistoryOutlined /></template>
            <span>{{ t('menu.history') }}</span>
          </a-menu-item>
          <a-menu-item key="topology" @click="navigateTo('/cmdb/topology')">
            <template #icon><ShareAltOutlined /></template>
            <span>{{ t('menu.topology') }}</span>
          </a-menu-item>
        </a-sub-menu>
        
        <a-sub-menu key="config" v-if="userInfo?.role === 'admin'">
          <template #icon><AppstoreOutlined /></template>
          <template #title>{{ t('menu.config') }}</template>
          <a-menu-item key="model" @click="navigateTo('/config/model')">
            <template #icon><DatabaseOutlined /></template>
            <span>{{ t('menu.model') }}</span>
          </a-menu-item>
          <a-menu-item key="relation-type" @click="navigateTo('/config/relation-type')">
            <template #icon><NodeIndexOutlined /></template>
            <span>{{ t('menu.relationType') }}</span>
          </a-menu-item>
          <a-menu-item key="relation-trigger" @click="navigateTo('/config/relation-trigger')">
            <template #icon><ThunderboltOutlined /></template>
            <span>{{ t('menu.relationTrigger') }}</span>
          </a-menu-item>
        </a-sub-menu>
        
        <a-sub-menu key="system">
          <template #icon><SettingOutlined /></template>
          <template #title>{{ t('menu.system') }}</template>
          <a-menu-item key="user" @click="navigateTo('/system/user')">
            <template #icon><UserOutlined /></template>
            <span>{{ t('menu.user') }}</span>
          </a-menu-item>
          <a-menu-item key="department" @click="navigateTo('/system/department')">
            <template #icon><ApartmentOutlined /></template>
            <span>{{ t('menu.department') }}</span>
          </a-menu-item>
          <a-menu-item key="role" @click="navigateTo('/system/role')">
            <template #icon><SafetyOutlined /></template>
            <span>{{ t('menu.role') }}</span>
          </a-menu-item>
          <a-menu-item key="system-config" @click="navigateTo('/system/config')">
            <template #icon><ToolOutlined /></template>
            <span>{{ t('menu.systemConfig') }}</span>
          </a-menu-item>
          <a-menu-item key="log" @click="navigateTo('/system/log')">
            <template #icon><FileSearchOutlined /></template>
            <span>{{ t('menu.log') }}</span>
          </a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>
    <a-layout class="layout-main">
      <a-layout-header class="layout-header">
        <div class="header-left">
          <span class="trigger" @click="toggleCollapsed">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </span>
          <a-breadcrumb class="breadcrumb" separator="/">
            <a-breadcrumb-item>
              <HomeOutlined />
            </a-breadcrumb-item>
            <a-breadcrumb-item v-if="currentMenu.parent">{{ currentMenu.parent }}</a-breadcrumb-item>
            <a-breadcrumb-item v-if="currentMenu.title">
              <span>{{ currentMenu.title }}</span>
            </a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="header-right">
          <a-space :size="8">
            <a-dropdown>
              <span class="header-action">
                <GlobalOutlined />
              </span>
              <template #overlay>
                <a-menu @click="handleLanguageChange">
                  <a-menu-item key="zh-CN" :class="{ 'active-item': appStore.language === 'zh-CN' }">
                    简体中文
                  </a-menu-item>
                  <a-menu-item key="en-US" :class="{ 'active-item': appStore.language === 'en-US' }">
                    English
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
            <a-tooltip :title="appStore.theme === 'dark' ? t('common.lightMode') : t('common.darkMode')">
              <span class="header-action" @click="toggleTheme">
                <BulbFilled v-if="appStore.theme === 'dark'" />
                <BulbOutlined v-else />
              </span>
            </a-tooltip>
            <a-dropdown>
              <span class="header-action user-info">
                <a-avatar size="small" class="user-avatar">
                  {{ userInfo?.username?.charAt(0)?.toUpperCase() }}
                </a-avatar>
                <span class="user-name">{{ userInfo?.username }}</span>
                <DownOutlined class="dropdown-icon" />
              </span>
              <template #overlay>
                <a-menu class="user-menu">
                  <a-menu-item key="profile">
                    <UserOutlined />
                    <span>{{ t('user.profile') }}</span>
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout" @click="handleLogout">
                    <LogoutOutlined />
                    <span>{{ t('common.logout') }}</span>
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </a-space>
        </div>
      </a-layout-header>
      <a-layout-content class="layout-content">
        <div class="content-wrapper">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import {
  SettingOutlined,
  UserOutlined,
  ApartmentOutlined,
  SafetyOutlined,
  ToolOutlined,
  FileSearchOutlined,
  SearchOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  GlobalOutlined,
  BulbOutlined,
  BulbFilled,
  HomeOutlined,
  DownOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ShareAltOutlined,
  HddOutlined,
  CloudServerOutlined
} from '@ant-design/icons-vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])

const userInfo = computed(() => userStore.userInfo)

const menuMap: Record<string, { parent: string; title: string }> = {
  '/dashboard': { parent: '', title: t('menu.dashboard') },
  '/cmdb/instance': { parent: t('menu.cmdb'), title: t('menu.instance') },
  '/cmdb/search': { parent: t('menu.cmdb'), title: t('menu.search') },
  '/cmdb/history': { parent: t('menu.cmdb'), title: t('menu.history') },
  '/cmdb/topology': { parent: t('menu.cmdb'), title: t('menu.topology') },
  '/config/model': { parent: t('menu.config'), title: t('menu.model') },
  '/config/relation-type': { parent: t('menu.config'), title: t('menu.relationType') },
  '/config/relation-trigger': { parent: t('menu.config'), title: t('menu.relationTrigger') },
  '/system/user': { parent: t('menu.system'), title: t('menu.user') },
  '/system/department': { parent: t('menu.system'), title: t('menu.department') },
  '/system/role': { parent: t('menu.system'), title: t('menu.role') },
  '/system/config': { parent: t('menu.system'), title: t('menu.systemConfig') },
  '/system/log': { parent: t('menu.system'), title: t('menu.log') }
}

const currentMenu = computed(() => {
  return menuMap[route.path] || { parent: '', title: '' }
})

onMounted(async () => {
  if (!userStore.userInfo) {
    await userStore.getUserInfo()
  }
  updateSelectedKeys()
})

watch(() => route.path, () => {
  updateSelectedKeys()
})

const updateSelectedKeys = () => {
  const path = route.path
  if (path.includes('/dashboard')) {
    selectedKeys.value = ['dashboard']
    openKeys.value = []
  } else if (path.includes('/cmdb/instance')) {
    selectedKeys.value = ['instance']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/search')) {
    selectedKeys.value = ['search']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/history')) {
    selectedKeys.value = ['history']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/topology')) {
    selectedKeys.value = ['topology']
    openKeys.value = ['cmdb']
  } else if (path.includes('/config/model')) {
    selectedKeys.value = ['model']
    openKeys.value = ['config']
  } else if (path.includes('/config/relation-type')) {
    selectedKeys.value = ['relation-type']
    openKeys.value = ['config']
  } else if (path.includes('/config/relation-trigger')) {
    selectedKeys.value = ['relation-trigger']
    openKeys.value = ['config']
  } else if (path.includes('/system/user')) {
    selectedKeys.value = ['user']
    openKeys.value = ['system']
  } else if (path.includes('/system/department')) {
    selectedKeys.value = ['department']
    openKeys.value = ['system']
  } else if (path.includes('/system/role')) {
    selectedKeys.value = ['role']
    openKeys.value = ['system']
  } else if (path.includes('/system/config')) {
    selectedKeys.value = ['system-config']
    openKeys.value = ['system']
  } else if (path.includes('/system/log')) {
    selectedKeys.value = ['log']
    openKeys.value = ['system']
  }
}

const toggleCollapsed = () => {
  collapsed.value = !collapsed.value
}

const onCollapse = (collapsedValue: boolean) => {
  collapsed.value = collapsedValue
}

const navigateTo = (path: string) => {
  router.push(path)
}

const handleLogout = async () => {
  await userStore.logoutAction()
  router.push('/login')
}

const handleLanguageChange = ({ key }: { key: string }) => {
  appStore.setLanguage(key as 'zh-CN' | 'en-US')
  location.reload()
}

const toggleTheme = () => {
  appStore.setTheme(appStore.theme === 'dark' ? 'light' : 'dark')
}
</script>

<style scoped>
.basic-layout {
  min-height: 100vh;
}

.layout-sider {
  background: linear-gradient(180deg, #001529 0%, #002140 100%);
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 10;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  border-radius: 6px;
  color: white;
  font-size: 18px;
  flex-shrink: 0;
}

.logo-text {
  margin-left: 12px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
}

.sider-menu {
  border-right: none !important;
}

.sider-menu :deep(.ant-menu-submenu-title) {
  margin: 4px 8px;
  border-radius: 6px;
  height: 40px;
  line-height: 40px;
}

.sider-menu :deep(.ant-menu-item) {
  margin: 4px 8px;
  border-radius: 6px;
  height: 40px;
  line-height: 40px;
}

.sider-menu :deep(.ant-menu-item-selected) {
  background: linear-gradient(90deg, #1890ff 0%, #36cfc9 100%) !important;
}

.layout-main {
  background: #f0f2f5;
  min-height: 100vh;
}

.layout-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  position: relative;
  z-index: 9;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.trigger {
  font-size: 18px;
  cursor: pointer;
  color: #666;
  transition: color 0.3s;
  display: flex;
  align-items: center;
}

.trigger:hover {
  color: #1890ff;
}

.breadcrumb {
  font-size: 14px;
}

.breadcrumb :deep(.ant-breadcrumb-link) {
  display: flex;
  align-items: center;
}

.breadcrumb :deep(.ant-breadcrumb-separator) {
  margin: 0 8px;
}

.breadcrumb :deep(ol li:last-child .ant-breadcrumb-separator) {
  display: none;
}

.header-right {
  display: flex;
  align-items: center;
}

.header-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
  color: #666;
}

.header-action:hover {
  background: rgba(0, 0, 0, 0.025);
  color: #1890ff;
}

.user-info {
  width: auto;
  padding: 0 8px;
  gap: 8px;
}

.user-avatar {
  background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
  font-size: 12px;
}

.user-name {
  color: #333;
  font-size: 14px;
}

.dropdown-icon {
  font-size: 10px;
  color: #999;
}

.user-menu :deep(.ant-dropdown-menu-item) {
  padding: 8px 16px;
}

.active-item {
  color: #1890ff !important;
  background: #e6f7ff !important;
}

.layout-content {
  margin: 0;
  padding: 24px;
  min-height: calc(100vh - 56px);
}

.content-wrapper {
  background: transparent;
  min-height: 100%;
}

@media (max-width: 992px) {
  .layout-header {
    padding: 0 16px;
  }
  
  .layout-content {
    padding: 16px;
  }
  
  .breadcrumb {
    display: none;
  }
  
  .user-name {
    display: none;
  }
  
  .dropdown-icon {
    display: none;
  }
  
  .user-info {
    width: 36px;
    padding: 0;
    justify-content: center;
  }
}

@media (max-width: 576px) {
  .header-left {
    gap: 8px;
  }
  
  .trigger {
    font-size: 16px;
  }
}
</style>
