<template>
  <a-layout class="basic-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      :trigger="null"
      collapsible
      :width="siderWidth"
      :collapsedWidth="siderCollapsedWidth"
      class="layout-sider"
      breakpoint="lg"
      @collapse="onCollapse"
    >
      <div class="logo" @click="navigateTo('/dashboard')">
        <div class="logo-icon">
          <img v-if="siteLogo" :src="siteLogo" alt="logo" class="logo-img" />
          <AppstoreOutlined v-else />
        </div>
        <div v-if="!collapsed" class="logo-copy">
          <span class="logo-text">{{ siteName }}</span>
          <span class="logo-subtitle">Operations Console</span>
        </div>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        theme="light"
        mode="inline"
        class="sider-menu"
      >
        <a-menu-item key="dashboard" @click="navigateTo('/dashboard')">
          <template #icon><DashboardOutlined /></template>
          <span>{{ t('menu.dashboard') }}</span>
        </a-menu-item>

        <a-sub-menu
          key="cmdb"
          v-if="hasAnyPermission(['cmdb:instance', 'cmdb:search', 'cmdb:model', 'cmdb:history', 'cmdb:topology']) || customViews.length > 0"
        >
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
          <a-menu-item key="topology-template" v-if="hasPermission('cmdb:topology')" @click="navigateTo('/cmdb/topology-template')">
            <template #icon><ApartmentOutlined /></template>
            <span>{{ t('menu.topologyTemplate') }}</span>
          </a-menu-item>
          <a-menu-item key="topology-manage" v-if="hasPermission('cmdb:topology')" @click="navigateTo('/cmdb/topology-manage')">
            <template #icon><ClusterOutlined /></template>
            <span>{{ t('menu.topologyManage') }}</span>
          </a-menu-item>
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

        <a-sub-menu
          key="monitoring"
          v-if="hasAnyPermission(['monitoring:template', 'monitoring:list', 'monitoring:target', 'monitoring:bulletin', 'monitoring:dashboard', 'monitoring:collector', 'monitoring:labels', 'monitoring:status'])"
        >
          <template #icon><LineChartOutlined /></template>
          <template #title>{{ t('menu.monitoring') }}</template>
          <a-menu-item key="monitoring-dashboard" v-if="hasPermission('monitoring:dashboard')" @click="navigateTo('/monitoring/dashboard')">
            <template #icon><DashboardOutlined /></template>
            <span>{{ t('menu.monitoringDashboard') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-list" v-if="hasAnyPermission(['monitoring:list', 'monitoring:target'])" @click="navigateTo('/monitoring/list')">
            <template #icon><AimOutlined /></template>
            <span>{{ t('menu.monitoringList') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-bulletin" v-if="hasPermission('monitoring:bulletin')" @click="navigateTo('/monitoring/bulletin')">
            <template #icon><BookOutlined /></template>
            <span>{{ t('menu.monitoringBulletin') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-template" v-if="hasPermission('monitoring:template')" @click="navigateTo('/monitoring/template')">
            <template #icon><FileTextOutlined /></template>
            <span>{{ t('menu.monitoringTemplate') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-collector" v-if="hasPermission('monitoring:collector')" @click="navigateTo('/monitoring/collector')">
            <template #icon><ClusterOutlined /></template>
            <span>{{ t('menu.monitoringCollector') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-labels" v-if="hasPermission('monitoring:labels')" @click="navigateTo('/monitoring/labels')">
            <template #icon><TagsOutlined /></template>
            <span>{{ t('menu.monitoringLabels') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-status" v-if="hasPermission('monitoring:status')" @click="navigateTo('/monitoring/status')">
            <template #icon><MobileOutlined /></template>
            <span>{{ t('menu.monitoringStatus') }}</span>
          </a-menu-item>
        </a-sub-menu>

        <a-sub-menu
          key="alert-center"
          v-if="hasAnyPermission(['monitoring:alert:center', 'monitoring:alert:current', 'monitoring:alert:my', 'monitoring:alert:history', 'monitoring:alert:rule', 'monitoring:alert:setting', 'monitoring:alert:integration', 'monitoring:alert:external', 'monitoring:alert:group', 'monitoring:alert:inhibit', 'monitoring:alert:silence', 'monitoring:alert:notice'])"
        >
          <template #icon><BellOutlined /></template>
          <template #title>{{ t('menu.monitoringAlertCenter') }}</template>
          <a-menu-item key="monitoring-alert-current" v-if="hasAnyPermission(['monitoring:alert:current', 'monitoring:alert:center'])" @click="navigateTo('/alert-center/current')">
            <span>{{ t('menu.monitoringAlertCurrent') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-my" v-if="hasAnyPermission(['monitoring:alert:my', 'monitoring:alert:center'])" @click="navigateTo('/alert-center/my')">
            <span>我的告警</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-history" v-if="hasAnyPermission(['monitoring:alert:history', 'monitoring:alert:center'])" @click="navigateTo('/alert-center/history')">
            <span>{{ t('menu.monitoringAlertHistory') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-setting" v-if="hasAnyPermission(['monitoring:alert:setting', 'monitoring:alert:rule'])" @click="navigateTo('/alert-center/setting')">
            <span>告警配置</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-integration" v-if="hasAnyPermission(['monitoring:alert:integration', 'monitoring:alert:external'])" @click="navigateTo('/alert-center/integration')">
            <span>外部告警接入</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-group" v-if="hasPermission('monitoring:alert:group')" @click="navigateTo('/alert-center/group')">
            <span>{{ t('menu.monitoringAlertGroup') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-inhibit" v-if="hasPermission('monitoring:alert:inhibit')" @click="navigateTo('/alert-center/inhibit')">
            <span>{{ t('menu.monitoringAlertInhibit') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-silence" v-if="hasPermission('monitoring:alert:silence')" @click="navigateTo('/alert-center/silence')">
            <span>{{ t('menu.monitoringAlertSilence') }}</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-notice" v-if="hasPermission('monitoring:alert:notice')" @click="navigateTo('/alert-center/notice')">
            <span>通知规则</span>
          </a-menu-item>
          <a-menu-item key="monitoring-alert-notice-receiver" v-if="hasPermission('monitoring:alert:notice')" @click="navigateTo('/alert-center/notice-receiver')">
            <span>通知渠道</span>
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
          <button class="header-trigger" type="button" @click="toggleCollapsed">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </button>
          <div class="header-divider" />
          <div class="header-context">
            <nav v-if="breadcrumbItems.length" class="header-breadcrumb" aria-label="Breadcrumb">
              <template v-for="(item, index) in breadcrumbItems" :key="item.key">
                <a
                  v-if="item.path && index < breadcrumbItems.length - 1"
                  href="#"
                  class="header-breadcrumb-node header-breadcrumb-link"
                  @click.prevent="navigateTo(item.path)"
                >
                  <component :is="item.icon" v-if="item.icon" class="header-breadcrumb-icon" />
                  <span class="header-breadcrumb-text">{{ item.title }}</span>
                </a>
                <span v-else class="header-breadcrumb-node header-breadcrumb-current">
                  <component :is="item.icon" v-if="item.icon" class="header-breadcrumb-icon" />
                  <span class="header-breadcrumb-text">{{ item.title }}</span>
                </span>
                <RightOutlined
                  v-if="index < breadcrumbItems.length - 1"
                  class="header-breadcrumb-separator"
                />
              </template>
            </nav>
            <div v-else class="header-title">{{ currentPageTitle }}</div>
            <div class="header-title header-title-mobile">{{ currentPageTitle }}</div>
          </div>
        </div>

        <div class="header-right">
          <a-space :size="10">
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
              <button class="header-action" type="button">
                <GlobalOutlined />
              </button>
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
              <button class="header-action" type="button" @click="toggleTheme">
                <BulbFilled v-if="appStore.theme === 'dark'" />
                <BulbOutlined v-else />
              </button>
            </a-tooltip>

            <a-dropdown>
              <button class="header-action user-info" type="button">
                <a-avatar size="small" class="user-avatar">
                  <template #icon>
                    <img v-if="userInfo?.avatar" :src="avatarFullUrl" alt="avatar" />
                    <span v-else>{{ userInfo?.username?.charAt(0)?.toUpperCase() }}</span>
                  </template>
                </a-avatar>
                <span class="user-name">{{ userInfo?.username }}</span>
                <DownOutlined class="dropdown-icon" />
              </button>
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
import { useRouter, useRoute, type RouteRecordNormalized } from 'vue-router'
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
  RightOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  BookOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ShareAltOutlined,
  ClusterOutlined,
  HddOutlined,
  CloudServerOutlined,
  BellOutlined,
  ScanOutlined,
  LineChartOutlined,
  FileTextOutlined,
  AimOutlined,
  TagsOutlined,
  MobileOutlined,
  EditOutlined,
  DesktopOutlined,
  FileProtectOutlined,
  ApiOutlined,
  StopOutlined,
  SoundOutlined,
  NotificationOutlined,
  MailOutlined,
  SendOutlined
} from '@ant-design/icons-vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const notificationStore = useNotificationStore()

const collapsed = ref(Boolean(appStore.sidebarCollapsed))
const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])
const siteLogo = ref('')
const siteName = ref('Arco CMDB')
const notificationVisible = ref(false)
const customViews = ref<any[]>([])
const siderWidth = 240
const siderCollapsedWidth = 60

const breadcrumbIconMap = {
  SettingOutlined,
  UserOutlined,
  ApartmentOutlined,
  SafetyOutlined,
  ToolOutlined,
  FileSearchOutlined,
  SearchOutlined,
  HistoryOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  BookOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ShareAltOutlined,
  ClusterOutlined,
  HddOutlined,
  CloudServerOutlined,
  BellOutlined,
  ScanOutlined,
  LineChartOutlined,
  FileTextOutlined,
  AimOutlined,
  TagsOutlined,
  MobileOutlined,
  EditOutlined,
  DesktopOutlined,
  FileProtectOutlined,
  ApiOutlined,
  StopOutlined,
  SoundOutlined,
  NotificationOutlined,
  MailOutlined,
  SendOutlined
} as const

const breadcrumbIconAliases = {
  BranchOutlined: ShareAltOutlined
} as const

type BreadcrumbIconKey = keyof typeof breadcrumbIconMap

type BreadcrumbItem = {
  key: string
  title: string
  path?: string
  icon?: (typeof breadcrumbIconMap)[BreadcrumbIconKey]
}

const userInfo = computed(() => userStore.userInfo)
const unreadCount = computed(() => notificationStore.unreadCount)
const avatarFullUrl = computed(() => {
  if (!userInfo.value?.avatar) return ''
  if (userInfo.value.avatar.startsWith('http')) return userInfo.value.avatar
  return getBaseURL() + userInfo.value.avatar
})

const resolveMatchedPath = (rawPath: string) => {
  if (!rawPath || rawPath.includes(':')) {
    return undefined
  }
  return rawPath
}

const resolveBreadcrumbTitle = (record: RouteRecordNormalized) => {
  if (record.name === 'CustomViewDisplay') {
    const id = Number(route.params.id)
    const view = customViews.value.find((item) => Number(item.id) === id)
    return view?.name || String(record.meta?.title || '视图展示')
  }
  return String(record.meta?.title || '')
}

const resolveBreadcrumbIcon = (iconKey: unknown) => {
  if (typeof iconKey !== 'string') {
    return undefined
  }
  return (
    breadcrumbIconMap[iconKey as BreadcrumbIconKey] ||
    breadcrumbIconAliases[iconKey as keyof typeof breadcrumbIconAliases]
  )
}

const resolveBreadcrumbFallbackIcon = (routeName: string) => {
  if (routeName === 'CustomViewDisplay' || routeName === 'CustomViewDesign') {
    return AppstoreOutlined
  }
  if (routeName === 'MonitoringTargetDetail') {
    return DesktopOutlined
  }
  if (routeName === 'MonitoringAlertDetail') {
    return BellOutlined
  }
  return undefined
}

const resolveVirtualBreadcrumbs = () => {
  const routeName = String(route.name || '')
  if (routeName === 'SystemSendNotification' || routeName === 'SystemNotificationDetail') {
    return [{ key: 'notification-parent', title: '通知管理', path: '/system/notification', icon: BellOutlined }]
  }
  if (routeName === 'SendNotification' || routeName === 'NotificationDetail') {
    return [{ key: 'notifications-parent', title: '通知中心', path: '/notifications', icon: BellOutlined }]
  }
  if (routeName === 'TopologyTemplateEdit') {
    return [{ key: 'topology-template-parent', title: '拓扑模板', path: '/cmdb/topology-template', icon: ApartmentOutlined }]
  }
  if (routeName === 'CustomViewDesign') {
    return [{ key: 'custom-view-parent', title: '视图管理', path: '/system/custom-view', icon: AppstoreOutlined }]
  }
  if (routeName === 'MonitoringTargetDetail') {
    return [{ key: 'monitoring-list-parent', title: '监控列表', path: '/monitoring/list', icon: DesktopOutlined }]
  }
  if (routeName === 'MonitoringAlertDetail') {
    return [{ key: 'alert-current-parent', title: '当前告警', path: '/alert-center/current', icon: BellOutlined }]
  }
  return []
}

const breadcrumbItems = computed(() => {
  const matchedItems = route.matched
    .filter((record) => record.meta?.title)
    .map((record) => ({
      key: String(record.name || record.path),
      title: resolveBreadcrumbTitle(record),
      path: resolveMatchedPath(record.path),
      icon:
        resolveBreadcrumbIcon(record.meta?.icon) ||
        resolveBreadcrumbFallbackIcon(String(record.name || ''))
    }))
  const virtualItems = resolveVirtualBreadcrumbs()
  if (!virtualItems.length || matchedItems.length === 0) {
    return matchedItems
  }
  return [
    ...matchedItems.slice(0, -1),
    ...virtualItems,
    matchedItems[matchedItems.length - 1]
  ]
})

const currentPageTitle = computed(() => {
  const items = breadcrumbItems.value
  return items.length ? items[items.length - 1].title : siteName.value
})

onMounted(async () => {
  if (!userStore.userInfo) {
    await userStore.getUserInfo()
  }
  updateSelectedKeys()

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

  try {
    const res = await getMyViews()
    if (res.code === 200) {
      customViews.value = res.data || []
      updateSelectedKeys()
    } else if (res.code === 401) {
      return
    }
  } catch (error: any) {
    console.error('加载自定义视图失败:', error)
    if (error?.response?.status === 401) {
      return
    }
  }

  try {
    await notificationStore.initialize()
    const token = localStorage.getItem('token')
    if (token) {
      notificationStore.connectWebSocket(token)
    }
  } catch (error: any) {
    console.error('初始化通知模块失败:', error)
    if (error?.response?.status === 401) {
      return
    }
  }
})

watch(
  () => route.path,
  () => {
    updateSelectedKeys()
  }
)

watch(
  () => collapsed.value,
  (value) => {
    appStore.sidebarCollapsed = value
  }
)

const updateSelectedKeys = () => {
  const path = route.path
  if (path === '/dashboard') {
    selectedKeys.value = ['dashboard']
    openKeys.value = []
  } else if (path.includes('/monitoring/dashboard')) {
    selectedKeys.value = ['monitoring-dashboard']
    openKeys.value = ['monitoring']
  } else if (path.includes('/cmdb/instance')) {
    selectedKeys.value = ['instance']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/search')) {
    selectedKeys.value = ['search']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/history')) {
    selectedKeys.value = ['history']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/topology-template')) {
    selectedKeys.value = ['topology-template']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/topology-manage')) {
    selectedKeys.value = ['topology-manage']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/topology')) {
    selectedKeys.value = ['topology']
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/trigger-config')) {
    selectedKeys.value = []
    openKeys.value = ['cmdb']
  } else if (path.includes('/cmdb/custom-view/view/')) {
    selectedKeys.value = [`view-${route.params.id}`]
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
  } else if (path.includes('/monitoring/template')) {
    selectedKeys.value = ['monitoring-template']
    openKeys.value = ['monitoring']
  } else if (path.includes('/monitoring/list') || path.includes('/monitoring/target')) {
    selectedKeys.value = ['monitoring-list']
    openKeys.value = ['monitoring']
  } else if (path.includes('/monitoring/bulletin')) {
    selectedKeys.value = ['monitoring-bulletin']
    openKeys.value = ['monitoring']
  } else if (path.includes('/alert-center')) {
    openKeys.value = ['alert-center']
    if (path.includes('/current')) selectedKeys.value = ['monitoring-alert-current']
    else if (path.includes('/my')) selectedKeys.value = ['monitoring-alert-my']
    else if (path.includes('/history')) selectedKeys.value = ['monitoring-alert-history']
    else if (path.includes('/rule') || path.includes('/setting')) selectedKeys.value = ['monitoring-alert-setting']
    else if (path.includes('/integration')) selectedKeys.value = ['monitoring-alert-integration']
    else if (path.includes('/group')) selectedKeys.value = ['monitoring-alert-group']
    else if (path.includes('/inhibit')) selectedKeys.value = ['monitoring-alert-inhibit']
    else if (path.includes('/silence')) selectedKeys.value = ['monitoring-alert-silence']
    else if (path.includes('/notice-receiver')) selectedKeys.value = ['monitoring-alert-notice-receiver']
    else if (path.includes('/notice')) selectedKeys.value = ['monitoring-alert-notice']
    else selectedKeys.value = ['monitoring-alert-current']
  } else if (path.includes('/monitoring/collector')) {
    selectedKeys.value = ['monitoring-collector']
    openKeys.value = ['monitoring']
  } else if (path.includes('/monitoring/labels')) {
    selectedKeys.value = ['monitoring-labels']
    openKeys.value = ['monitoring']
  } else if (path.includes('/monitoring/status')) {
    selectedKeys.value = ['monitoring-status']
    openKeys.value = ['monitoring']
  } else if (path.includes('/system/user')) {
    selectedKeys.value = ['user']
    openKeys.value = ['system']
  } else if (path.includes('/system/department')) {
    selectedKeys.value = ['department']
    openKeys.value = ['system']
  } else if (path.includes('/system/role')) {
    selectedKeys.value = ['role']
    openKeys.value = ['system']
  } else if (path.includes('/system/custom-view') || path.includes('/custom-view-design')) {
    selectedKeys.value = ['custom-view']
    openKeys.value = ['system']
  } else if (path.includes('/system/config')) {
    selectedKeys.value = ['system-config']
    openKeys.value = ['system']
  } else if (path.includes('/system/log')) {
    selectedKeys.value = ['log']
    openKeys.value = ['system']
  } else if (path.includes('/system/notification') || path.includes('/notifications')) {
    selectedKeys.value = ['notification']
    openKeys.value = ['system']
  } else {
    selectedKeys.value = []
    openKeys.value = []
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
  if (notification) {
    notificationVisible.value = false
  }
}
</script>

<style scoped>
.basic-layout {
  height: 100vh;
  overflow: hidden;
  background: var(--arco-app-bg);
}

.layout-sider {
  height: 100vh;
  background: color-mix(in srgb, var(--arco-surface) 96%, var(--arco-app-bg) 4%) !important;
  border-right: 1px solid color-mix(in srgb, var(--arco-border) 78%, transparent 22%);
  box-shadow: none;
  overflow: hidden;
}

.layout-sider :deep(.ant-layout-sider-children) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.logo {
  display: flex;
  align-items: center;
  gap: 13px;
  height: var(--layout-header-height);
  padding: 0 18px;
  border-bottom: 1px solid var(--arco-border);
  cursor: pointer;
  background: color-mix(in srgb, var(--arco-surface) 98%, var(--arco-app-bg) 2%);
}

.logo-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--arco-primary) 0%, var(--arco-primary-gradient-end) 100%);
  color: #fff;
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

.logo-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.logo-text {
  color: var(--arco-text);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-subtitle {
  color: var(--arco-text-tertiary);
  font-size: 12px;
  line-height: 1.2;
}

.sider-menu {
  flex: 1;
  overflow: auto;
  padding: 16px 14px 24px;
  background: transparent;
  border-inline-end: 0 !important;
}

.sider-menu :deep(.ant-menu-item),
.sider-menu :deep(.ant-menu-submenu-title) {
  margin: 6px 0;
  padding-inline: 18px !important;
  border-radius: 12px;
  height: 46px;
  line-height: 46px;
  color: color-mix(in srgb, var(--arco-text) 90%, var(--arco-text-secondary) 10%);
  font-size: 16px;
  font-weight: 500;
  transition:
    color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

.sider-menu :deep(.ant-menu-item .ant-menu-title-content),
.sider-menu :deep(.ant-menu-submenu-title .ant-menu-title-content) {
  transition: color 0.2s ease;
}

.sider-menu :deep(.ant-menu-item .anticon),
.sider-menu :deep(.ant-menu-submenu-title .anticon) {
  color: color-mix(in srgb, var(--arco-text-secondary) 72%, var(--arco-text-tertiary) 28%);
  font-size: 16px;
  transition: color 0.2s ease;
}

.sider-menu :deep(.ant-menu-submenu-title) {
  color: color-mix(in srgb, var(--arco-text) 94%, var(--arco-text-secondary) 6%);
  font-weight: 600;
}

.sider-menu :deep(.ant-menu-submenu-arrow) {
  color: var(--arco-text-tertiary);
}

.sider-menu :deep(.ant-menu-inline .ant-menu-item) {
  padding-inline-start: 22px !important;
}

.sider-menu :deep(.ant-menu-item:hover),
.sider-menu :deep(.ant-menu-submenu-title:hover) {
  color: var(--arco-text);
  background: color-mix(in srgb, var(--arco-fill) 80%, var(--arco-surface) 20%);
}

.sider-menu :deep(.ant-menu-item:hover .anticon),
.sider-menu :deep(.ant-menu-submenu-title:hover .anticon),
.sider-menu :deep(.ant-menu-submenu-title:hover .ant-menu-title-content),
.sider-menu :deep(.ant-menu-submenu-title:hover .ant-menu-submenu-arrow) {
  color: var(--arco-primary);
}

.sider-menu :deep(.ant-menu-item-selected) {
  position: relative;
  color: var(--arco-primary) !important;
  background: color-mix(in srgb, var(--arco-primary) 14%, var(--arco-surface) 86%) !important;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--arco-primary) 8%, transparent 92%);
}

.sider-menu :deep(.ant-menu-item-selected .anticon),
.sider-menu :deep(.ant-menu-submenu-selected > .ant-menu-submenu-title .anticon),
.sider-menu :deep(.ant-menu-submenu-selected > .ant-menu-submenu-title .ant-menu-title-content),
.sider-menu :deep(.ant-menu-submenu-selected > .ant-menu-submenu-title .ant-menu-submenu-arrow) {
  color: var(--arco-primary) !important;
}

.sider-menu :deep(.ant-menu-item-selected::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  bottom: 9px;
  width: 3px;
  border-radius: 999px;
  background: var(--arco-primary);
}

.sider-menu :deep(.ant-menu-sub.ant-menu-inline) {
  background: transparent;
  margin-top: 2px;
}

.layout-main {
  min-width: 0;
  height: 100vh;
  background: var(--arco-app-bg);
  overflow: hidden;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  height: var(--layout-header-height);
  padding: 0 26px;
  background: var(--arco-surface);
  border-bottom: 1px solid var(--arco-border);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  min-width: 0;
}

.header-left {
  gap: 14px;
  flex: 1;
}

.header-trigger,
.header-action {
  width: 38px;
  height: 38px;
  border: 1px solid var(--arco-border);
  border-radius: 10px;
  background: var(--arco-surface);
  color: var(--arco-text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.header-trigger:hover,
.header-action:hover {
  color: var(--arco-primary);
  border-color: var(--arco-primary-soft);
  background: var(--arco-primary-soft);
}

.header-divider {
  width: 1px;
  height: 28px;
  background: var(--arco-border);
  flex-shrink: 0;
}

.header-context {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}

.header-title {
  color: var(--arco-text);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: none;
}

.header-breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  white-space: nowrap;
}

.header-breadcrumb-node {
  min-width: 0;
  max-width: 220px;
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  line-height: 1;
  text-decoration: none;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

.header-breadcrumb-link {
  color: var(--arco-text-secondary);
}

.header-breadcrumb-link:hover {
  color: var(--arco-primary);
  background: var(--arco-primary-soft);
}

.header-breadcrumb-current {
  color: var(--arco-text);
  font-weight: 600;
  border-color: color-mix(in srgb, var(--arco-primary) 14%, var(--arco-border) 86%);
  background: color-mix(in srgb, var(--arco-primary) 10%, var(--arco-surface) 90%);
  box-shadow: var(--app-shadow-sm);
}

.header-breadcrumb-icon,
.header-breadcrumb-separator {
  flex-shrink: 0;
}

.header-breadcrumb-icon {
  font-size: 12px;
}

.header-breadcrumb-separator {
  color: var(--arco-text-quaternary);
  font-size: 10px;
}

.header-breadcrumb-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-info {
  width: auto;
  padding: 0 10px;
  gap: 8px;
}

.user-avatar {
  background: linear-gradient(135deg, var(--arco-primary) 0%, var(--arco-primary-gradient-end-strong) 100%);
}

.user-name {
  max-width: 120px;
  color: var(--arco-text);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dropdown-icon {
  font-size: 10px;
  color: var(--arco-text-tertiary);
}

.user-menu :deep(.ant-dropdown-menu-item) {
  padding: 8px 14px;
}

.active-item {
  color: var(--arco-primary) !important;
  background: var(--arco-primary-soft) !important;
}

.layout-content {
  height: calc(100vh - var(--layout-header-height));
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--arco-app-bg);
}

.content-wrapper {
  min-height: 100%;
  padding: var(--layout-content-padding);
}

@media (max-width: 992px) {
  .layout-header {
    padding: 0 16px;
  }

  .user-name,
  .dropdown-icon,
  .header-divider {
    display: none;
  }

  .user-info {
    width: 36px;
    padding: 0;
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .layout-header {
    gap: 10px;
    padding: 0 14px;
  }

  .header-left {
    gap: 10px;
  }

  .header-breadcrumb-node {
    max-width: 180px;
    height: 32px;
    padding: 0 10px;
    border-radius: 9px;
    font-size: 13px;
  }

  .header-right :deep(.ant-space) {
    gap: 8px !important;
  }
}

@media (max-width: 576px) {
  .layout-header {
    height: 54px;
    padding: 0 12px;
  }

  .header-breadcrumb {
    display: none;
  }

  .header-title {
    display: block;
    font-size: 15px;
  }

  .header-trigger,
  .header-action,
  .user-info {
    width: 34px;
    height: 34px;
    border-radius: 8px;
  }

  .header-right :deep(.ant-space) {
    gap: 6px !important;
  }

  .content-wrapper {
    padding: 14px;
  }
}
</style>
