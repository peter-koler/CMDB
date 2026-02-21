import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '首页', icon: 'DashboardOutlined' }
      },
      {
        path: 'config',
        name: 'Config',
        meta: { title: '配置管理', icon: 'AppstoreOutlined' },
        children: [
          {
            path: 'model',
            name: 'Model',
            component: () => import('@/views/config/model/index.vue'),
            meta: { title: '模型管理', icon: 'DatabaseOutlined', permission: 'cmdb:model' }
          },
          {
            path: 'relation-type',
            name: 'RelationType',
            component: () => import('@/views/config/relation-type/index.vue'),
            meta: { title: '关系类型', icon: 'NodeIndexOutlined', permission: 'cmdb:model' }
          },
          {
            path: 'relation-trigger',
            name: 'RelationTrigger',
            component: () => import('@/views/config/relation-trigger/index.vue'),
            meta: { title: '关系触发器', icon: 'ThunderboltOutlined', permission: 'cmdb:model' }
          },
          {
            path: 'batch-scan-config',
            name: 'BatchScanConfig',
            component: () => import('@/views/config/batch-scan-config/index.vue'),
            meta: { title: '扫描配置', icon: 'SettingOutlined', permission: 'cmdb:batch-scan:config' }
          },
          {
            path: 'batch-scan',
            name: 'BatchScan',
            component: () => import('@/views/config/batch-scan/index.vue'),
            meta: { title: '批量扫描', icon: 'ScanOutlined', permission: 'cmdb:batch-scan:view' }
          },
          {
            path: 'dictionary',
            name: 'Dictionary',
            component: () => import('@/views/config/dictionary/index.vue'),
            meta: { title: '字典管理', icon: 'BookOutlined', permission: 'cmdb:dict' }
          }
        ]
      },
      {
        path: 'cmdb',
        name: 'CMDB',
        meta: { title: 'CMDB', icon: 'CloudServerOutlined' },
        children: [
          {
            path: 'instance',
            name: 'Instance',
            component: () => import('@/views/cmdb/instance/index.vue'),
            meta: { title: '配置仓库', icon: 'HddOutlined', permission: 'cmdb:instance' }
          },
          {
            path: 'search',
            name: 'Search',
            component: () => import('@/views/cmdb/search/index.vue'),
            meta: { title: '全文搜索', icon: 'SearchOutlined', permission: 'cmdb:search' }
          },
          {
            path: 'history',
            name: 'CiHistory',
            component: () => import('@/views/cmdb/history/index.vue'),
            meta: { title: '变更历史', icon: 'HistoryOutlined', permission: 'cmdb:history' }
          },
          {
            path: 'topology',
            name: 'Topology',
            component: () => import('@/views/cmdb/topology/index.vue'),
            meta: { title: '拓扑视图', icon: 'BranchOutlined', permission: 'cmdb:topology' }
          },
          {
            path: 'trigger-config',
            name: 'TriggerConfig',
            component: () => import('@/views/cmdb/TriggerConfig.vue'),
            meta: { title: '触发器配置', icon: 'SettingOutlined', permission: 'cmdb:model' }
          }
        ]
      },
      {
        path: 'system',
        name: 'System',
        meta: { title: '系统管理', icon: 'SettingOutlined' },
        children: [
          {
            path: 'user',
            name: 'User',
            component: () => import('@/views/system/user/index.vue'),
            meta: { title: '用户管理', icon: 'UserOutlined', permission: 'system:user' }
          },
          {
            path: 'department',
            name: 'Department',
            component: () => import('@/views/system/department/index.vue'),
            meta: { title: '部门管理', icon: 'ApartmentOutlined', permission: 'system:department' }
          },
          {
            path: 'role',
            name: 'Role',
            component: () => import('@/views/system/role/index.vue'),
            meta: { title: '角色管理', icon: 'SafetyOutlined', permission: 'system:role' }
          },
          {
            path: 'config',
            name: 'SystemConfig',
            component: () => import('@/views/system/config/index.vue'),
            meta: { title: '系统配置', icon: 'ToolOutlined', permission: 'system:config' }
          },
          {
            path: 'log',
            name: 'Log',
            component: () => import('@/views/system/log/index.vue'),
            meta: { title: '日志审计', icon: 'FileSearchOutlined', permission: 'system:log' }
          },
          {
            path: 'notification',
            name: 'SystemNotification',
            component: () => import('@/views/notifications/index.vue'),
            meta: { title: '通知管理', icon: 'BellOutlined', permission: 'system:user' }
          },
          {
            path: 'notification/send',
            name: 'SystemSendNotification',
            component: () => import('@/views/notifications/send.vue'),
            meta: { title: '发送通知', icon: 'SendOutlined', permission: 'system:user', hideInMenu: true }
          },
          {
            path: 'notification/detail/:id',
            name: 'SystemNotificationDetail',
            component: () => import('@/views/notifications/detail.vue'),
            meta: { title: '通知详情', icon: 'FileTextOutlined', hideInMenu: true }
          }
        ]
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/notifications/index.vue'),
        meta: { title: '通知中心', icon: 'BellOutlined' }
      },
      {
        path: 'notifications/send',
        name: 'SendNotification',
        component: () => import('@/views/notifications/send.vue'),
        meta: { title: '发送通知', icon: 'SendOutlined', permission: 'system:user' }
      },
      {
        path: 'notifications/detail/:id',
        name: 'NotificationDetail',
        component: () => import('@/views/notifications/detail.vue'),
        meta: { title: '通知详情', icon: 'FileTextOutlined', hideInMenu: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false) {
    if (!userStore.token) {
      next('/login')
      return
    }

    // 确保用户信息已加载
    if (!userStore.userInfo) {
      const success = await userStore.getUserInfo()
      if (!success) {
        userStore.clearToken()
        next('/login')
        return
      }
    }

    // 检查权限
    if (to.meta.permission && !userStore.hasPermission(to.meta.permission as string)) {
      // 如果没有权限，且不是从首页来的，取消导航
      // 或者重定向到 403 (暂时没有) 或 Dashboard
      if (from.path === '/') {
         next('/dashboard')
      } else {
         // 简单的提示或取消
         // 这里选择不做跳转，或者跳转到 Dashboard
         // 实际项目中通常跳转到 403 页面
         console.warn('无权访问页面:', to.path)
         next(false)
      }
      return
    }
    
    next()
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
