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
          <img v-if="siteLogo" :src="siteLogo" alt="logo" class="logo-img" />
          <AppstoreOutlined v-else />
        </div>
        <span v-if="!collapsed" class="logo-text">{{ siteName }}</span>
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
        
        <a-sub-menu key="cmdb" v-if="hasAnyPermission(['cmdb:instance', 'cmdb:search', 'cmdb:model', 'cmdb:history', 'cmdb:topology']) || customViews.length > 0">
          <template #icon><CloudServerOutlined /></template>
          <template #title>{{ t('menu.cmdb') }}</template>
          <a-menu-item key="instance" v-if="hasPermission('cmdb:instance')" @click="navigateTo('/cmdb/instance')">
            <template #icon><HddOutlined /></template>
            <span>{{ t('menu.instance') }}</span>
          </a-menu-item>
          <a-menu-item key="search" v-if="hasPermission('cmdb:search')" @click="navigateTo('/cmdb/search')">
            <template #icon><SearchOutlined /></template>
            <span>{{ t('menu.search') }}</span>
          </a-menu-item>
          <a-menu-item key="history" v-if="hasPermission('cmdb:history')" @click="navigateTo('/cmdb/history')">
            <template #icon><HistoryOutlined /></template>
            <span>{{ t('menu.history') }}</span>
          </a-menu-item>
          <a-menu-item key="topology" v-if="hasPermission('cmdb:topology')" @click="navigateTo('/cmdb/topology')">
            <template #icon><ShareAltOutlined /></template>
            <span>{{ t('menu.topology') }}</span>
          </a-menu-item>
          <!-- 动态自定义视图菜单 -->
          <a-menu-item 
            v-for="view in customViews" 
            :key="`view-${view.id}`" 
            @click="navigateTo(`/cmdb/custom-view/view/${view.id}`)"
          >
            <template #icon><AppstoreOutlined /></template>
            <span>{{ view.name }}</span>
          </a-menu-item>
        </a-sub-menu>
        
        <a-sub-menu key="config" v-if="hasAnyPermission(['cmdb:model', 'cmdb:relation', 'cmdb:dict', 'cmdb:batch-scan'])">
          <template #icon><AppstoreOutlined /></template>
          <template #title>{{ t('menu.config') }}</template>
          <a-menu-item key="model" v-if="hasPermission('cmdb:model')" @click="navigateTo('/config/model')">
            <template #icon><DatabaseOutlined /></template>
            <span>{{ t('menu.model') }}</span>
          </a-menu-item>
          <a-menu-item key="relation-type" v-if="hasPermission('cmdb:model')" @click="navigateTo('/config/relation-type')">
            <template #icon><NodeIndexOutlined /></template>
            <span>{{ t('menu.relationType') }}</span>
          </a-menu-item>
          <a-menu-item key="relation-trigger" v-if="hasPermission('cmdb:model')" @click="navigateTo('/config/relation-trigger')">
            <template #icon><ThunderboltOutlined /></template>
            <span>{{ t('menu.relationTrigger') }}</span>
          </a-menu-item>
          <a-menu-item key="batch-scan-config" v-if="hasPermission('cmdb:batch-scan:config')" @click="navigateTo('/config/batch-scan-config')">
            <template #icon><SettingOutlined /></template>
            <span>扫描配置</span>
          </a-menu-item>
          <a-menu-item key="batch-scan" v-if="hasPermission('cmdb:batch-scan:view')" @click="navigateTo('/config/batch-scan')">
            <template #icon><ScanOutlined /></template>
            <span>批量扫描</span>
          </a-menu-item>
          <a-menu-item key="dictionary" v-if="hasPermission('cmdb:dict')" @click="navigateTo('/config/dictionary')">
            <template #icon><BookOutlined /></template>
            <span>{{ t('menu.dictionary') }}</span>
          </a-menu-item>
        </a-sub-menu>
        
        <a-sub-menu key="system" v-if="hasAnyPermission(['system:user', 'system:department', 'system:role', 'system:config', 'system:log', 'custom-view:manage'])">
          <template #icon><SettingOutlined /></template>
          <template #title>{{ t('menu.system') }}</template>
          <a-menu-item key="user" v-if="hasPermission('system:user')" @click="navigateTo('/system/user')">
            <template #icon><UserOutlined /></template>
            <span>{{ t('menu.user') }}</span>
          </a-menu-item>
          <a-menu-item key="department" v-if="hasPermission('system:department')" @click="navigateTo('/system/department')">
            <template #icon><ApartmentOutlined /></template>
            <span>{{ t('menu.department') }}</span>
          </a-menu-item>
          <a-menu-item key="role" v-if="hasPermission('system:role')" @click="navigateTo('/system/role')">
            <template #icon><SafetyOutlined /></template>
            <span>{{ t('menu.role') }}</span>
          </a-menu-item>
          <a-menu-item key="custom-view" v-if="hasPermission('custom-view:manage')" @click="navigateTo('/system/custom-view')">
            <template #icon><AppstoreOutlined /></template>
            <span>视图管理</span>
          </a-menu-item>
          <a-menu-item key="system-config" v-if="hasPermission('system:config')" @click="navigateTo('/system/config')">
            <template #icon><ToolOutlined /></template>
            <span>{{ t('menu.systemConfig') }}</span>
          </a-menu-item>
          <a-menu-item key="log" v-if="hasPermission('system:log')" @click="navigateTo('/system/log')">
            <template #icon><FileSearchOutlined /></template>
            <span>{{ t('menu.log') }}</span>
          </a-menu-item>
          <a-menu-item key="notification" v-if="hasPermission('system:user')" @click="navigateTo('/system/notification')">
            <template #icon><BellOutlined /></template>
            <span>{{ t('menu.notification') }}</span>
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
        </div>
        <div class="header-right">
          <a-space :size="8">
            <!-- 通知角标 -->
            <a-popover
              v-model:open="notificationVisible"
              placement="bottomRight"
              trigger="click"
              :overlay-style="{ width: '360px', padding: 0 }"
            >
              <template #content>
                <NotificationCenter
                  v-model:visible="notificationVisible"
                  @click="handleNotificationClick"
                />
              </template>
              <NotificationBadge
                :unread-count="unreadCount"
                @click="notificationVisible = true"
              />
            </a-popover>
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
                  <template #icon>
                    <img v-if="userInfo?.avatar" :src="avatarFullUrl" alt="avatar" />
                    <span v-else>{{ userInfo?.username?.charAt(0)?.toUpperCase() }}</span>
                  </template>
                </a-avatar>
                <span class="user-name">{{ userInfo?.username }}</span>
                <DownOutlined class="dropdown-icon" />
              </span>
              <template #overlay>
                <a-menu class="user-menu">
                  <a-menu-item key="profile" @click="navigateTo('/profile')">
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
import { useNotificationStore } from '@/stores/notifications'
import { getConfigs } from '@/api/config'
import { getBaseURL } from '@/utils/request'
import { getMyViews } from '@/api/custom-view'
import NotificationBadge from '@/components/notifications/NotificationBadge.vue'
import NotificationCenter from '@/components/notifications/NotificationCenter.vue'
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
  DownOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  BookOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ShareAltOutlined,
  HddOutlined,
  CloudServerOutlined,
  BellOutlined,
  ScanOutlined
} from '@ant-design/icons-vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const notificationStore = useNotificationStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])
const siteLogo = ref('')
const siteName = ref('Arco CMDB')
const notificationVisible = ref(false)
const customViews = ref<any[]>([])

const userInfo = computed(() => userStore.userInfo)
const unreadCount = computed(() => notificationStore.unreadCount)
const avatarFullUrl = computed(() => {
  if (!userInfo.value?.avatar) return ''
  if (userInfo.value.avatar.startsWith('http')) return userInfo.value.avatar
  return getBaseURL() + userInfo.value.avatar
})

onMounted(async () => {
  if (!userStore.userInfo) {
    await userStore.getUserInfo()
  }
  updateSelectedKeys()

  // 加载站点配置
  try {
    const res = await getConfigs()
    if (res.code === 200) {
      if (res.data.site_logo?.value) {
        siteLogo.value = getBaseURL() + res.data.site_logo.value
      }
      if (res.data.site_name?.value) {
        siteName.value = res.data.site_name.value
      }
    }
  } catch (error) {
    console.error('加载站点配置失败:', error)
  }

  // 加载用户的自定义视图
  try {
    const res = await getMyViews()
    if (res.code === 200) {
      customViews.value = res.data || []
    } else if (res.code === 401) {
      // Token 失效，不继续执行
      return
    }
  } catch (error: any) {
    console.error('加载自定义视图失败:', error)
    // 如果是 401 错误，拦截器会处理跳转
    if (error?.response?.status === 401) {
      return
    }
  }

  // 初始化通知模块
  try {
    await notificationStore.initialize()
    // 连接WebSocket
    const token = localStorage.getItem('token')
    if (token) {
      notificationStore.connectWebSocket(token)
    }
  } catch (error: any) {
    console.error('初始化通知模块失败:', error)
    // 如果是 401 错误，不显示错误，因为拦截器会处理跳转
    if (error?.response?.status === 401) {
      return
    }
  }
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
  } else if (path.includes('/config/batch-scan-config')) {
    selectedKeys.value = ['batch-scan-config']
    openKeys.value = ['config']
  } else if (path.includes('/config/batch-scan')) {
    selectedKeys.value = ['batch-scan']
    openKeys.value = ['config']
  } else if (path.includes('/config/dictionary')) {
    selectedKeys.value = ['dictionary']
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

const hasPermission = (permission: string) => {
  if (!userInfo.value) return false
  if (userInfo.value.role === 'admin') return true
  const permissions = userInfo.value.permissions || []
  if (permissions.includes('*')) return true
  if (permissions.includes(permission)) return true
  for (const p of permissions) {
    if (p.endsWith(':*')) {
      const prefix = p.slice(0, -1)
      if (permission.startsWith(prefix)) return true
    }
  }
  return false
}

const hasAnyPermission = (permissionList: string[]) => {
  if (!userInfo.value) return false
  if (userInfo.value.role === 'admin') return true
  const permissions = userInfo.value.permissions || []
  if (permissions.includes('*')) return true
  for (const permission of permissionList) {
    if (hasPermission(permission)) return true
  }
  return false
}

const handleNotificationClick = (notification: any) => {
  console.log('通知点击:', notification)
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
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 4px;
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

.sider-menu::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
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
