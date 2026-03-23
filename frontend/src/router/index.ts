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
    path: '/license',
    name: 'License',
    component: () => import('@/views/license/index.vue'),
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
            path: 'topology-manage',
            name: 'TopologyManage',
            component: () => import('@/views/cmdb/topology-manage/index.vue'),
            meta: { title: '拓扑图', icon: 'ClusterOutlined', permission: 'cmdb:topology' }
          },
          {
            path: 'topology-template',
            name: 'TopologyTemplate',
            component: () => import('@/views/cmdb/topology-template/index.vue'),
            meta: { title: '拓扑模板', icon: 'ApartmentOutlined', permission: 'cmdb:topology' }
          },
          {
            path: 'topology-template/edit/:id',
            name: 'TopologyTemplateEdit',
            component: () => import('@/views/cmdb/topology-template/edit.vue'),
            meta: { title: '编辑拓扑模板', icon: 'EditOutlined', permission: 'cmdb:topology', hideInMenu: true }
          },
          {
            path: 'trigger-config',
            name: 'TriggerConfig',
            component: () => import('@/views/cmdb/TriggerConfig.vue'),
            meta: { title: '触发器配置', icon: 'SettingOutlined', permission: 'cmdb:model' }
          },
          {
            path: 'custom-view/view/:id',
            name: 'CustomViewDisplay',
            component: () => import('@/views/custom-view/view.vue'),
            meta: { title: '视图展示', hideMenu: true }
          }
        ]
      },
      {
        path: 'custom-view-design/:id',
        name: 'CustomViewDesign',
        component: () => import('@/views/system/custom-view/design.vue'),
        meta: { title: '视图设计', hideMenu: true }
      },
      {
        path: 'monitoring',
        name: 'Monitoring',
        meta: { title: '监控管理', icon: 'LineChartOutlined' },
        children: [
          {
            path: 'dashboard',
            name: 'MonitoringDashboard',
            component: () => import('@/views/monitoring/dashboard/index.vue'),
            meta: { title: '监控展示', icon: 'DashboardOutlined', permission: 'monitoring:dashboard' }
          },
          {
            path: 'list',
            name: 'MonitoringList',
            component: () => import('@/views/monitoring/target/index.vue'),
            meta: { title: '监控列表', icon: 'DesktopOutlined', permission: 'monitoring:list' }
          },
          {
            path: 'target/:id',
            name: 'MonitoringTargetDetail',
            component: () => import('@/views/monitoring/target/detail.vue'),
            meta: { title: '监控任务详情', permission: 'monitoring:list', hideInMenu: true }
          },
          {
            path: 'target',
            redirect: '/monitoring/list'
          },
          {
            path: 'bulletin',
            name: 'MonitoringBulletin',
            component: () => import('@/views/monitoring/bulletin/index.vue'),
            meta: { title: '监控简报', icon: 'BookOutlined', permission: 'monitoring:bulletin' }
          },
          {
            path: 'template',
            name: 'MonitoringTemplate',
            component: () => import('@/views/monitoring/template/index.vue'),
            meta: { title: '监控模板', icon: 'FileTextOutlined', permission: 'monitoring:template' }
          },
          {
            path: 'collector',
            name: 'MonitoringCollector',
            component: () => import('@/views/monitoring/collector/index.vue'),
            meta: { title: '采集器管理', icon: 'ClusterOutlined', permission: 'monitoring:collector' }
          },
          {
            path: 'labels',
            name: 'MonitoringLabels',
            component: () => import('@/views/monitoring/labels/index.vue'),
            meta: { title: '标签管理', icon: 'TagsOutlined', permission: 'monitoring:labels' }
          },
          {
            path: 'status',
            name: 'MonitoringStatus',
            component: () => import('@/views/monitoring/status/index.vue'),
            meta: { title: '状态页', icon: 'MobileOutlined', permission: 'monitoring:status' }
          }
        ]
      },
      {
        path: 'alert-center',
        name: 'AlertCenter',
        meta: { title: '告警中心', icon: 'BellOutlined' },
        children: [
          {
            path: 'current',
            name: 'MonitoringAlertCurrent',
            component: () => import('@/views/monitoring/alert/index.vue'),
            meta: { title: '当前告警', icon: 'BellOutlined', permission: 'monitoring:alert:current' }
          },
          {
            path: 'my',
            name: 'MonitoringAlertMy',
            component: () => import('@/views/monitoring/alert/index.vue'),
            meta: { title: '我的告警', icon: 'UserOutlined', permission: 'monitoring:alert:my' }
          },
          {
            path: 'history',
            name: 'MonitoringAlertHistory',
            component: () => import('@/views/monitoring/alert/index.vue'),
            meta: { title: '告警历史', icon: 'HistoryOutlined', permission: 'monitoring:alert:history' }
          },
          {
            path: 'detail/:id',
            name: 'MonitoringAlertDetail',
            component: () => import('@/views/monitoring/alert/detail.vue'),
            meta: { title: '告警明细', permission: 'monitoring:alert:detail', hideInMenu: true }
          },
          {
            path: '',
            redirect: '/alert-center/current'
          },
          {
            path: 'rule',
            name: 'MonitoringAlertRule',
            component: () => import('@/views/monitoring/alert/index.vue'),
            meta: { title: '告警配置', icon: 'FileProtectOutlined', permission: 'monitoring:alert:rule' }
          },
          {
            path: 'integration',
            name: 'MonitoringAlertIntegration',
            component: () => import('@/views/monitoring/alert/integration.vue'),
            meta: { title: '告警集成', icon: 'ApiOutlined', permission: 'monitoring:alert:integration' }
          },
          {
            path: 'group',
            name: 'MonitoringAlertGroup',
            component: () => import('@/views/monitoring/alert/group.vue'),
            meta: { title: '告警分组', icon: 'ClusterOutlined', permission: 'monitoring:alert:group' }
          },
          {
            path: 'inhibit',
            name: 'MonitoringAlertInhibit',
            component: () => import('@/views/monitoring/alert/inhibit.vue'),
            meta: { title: '告警抑制', icon: 'StopOutlined', permission: 'monitoring:alert:inhibit' }
          },
          {
            path: 'silence',
            name: 'MonitoringAlertSilence',
            component: () => import('@/views/monitoring/alert/silence.vue'),
            meta: { title: '告警静默', icon: 'SoundOutlined', permission: 'monitoring:alert:silence' }
          },
          {
            path: 'notice',
            name: 'MonitoringAlertNotice',
            component: () => import('@/views/monitoring/alert/notice.vue'),
            meta: { title: '通知规则', icon: 'NotificationOutlined', permission: 'monitoring:alert:notice' }
          },
          {
            path: 'notice-receiver',
            name: 'MonitoringAlertNoticeReceiver',
            component: () => import('@/views/monitoring/alert/notice-receiver.vue'),
            meta: { title: '通知渠道', icon: 'MailOutlined', permission: 'monitoring:alert:notice' }
          },
          {
            path: 'setting',
            name: 'MonitoringAlertSetting',
            component: () => import('@/views/monitoring/alert/setting.vue'),
            meta: { title: '告警配置', icon: 'SettingOutlined', permission: 'monitoring:alert:setting' }
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
            path: 'custom-view',
            name: 'CustomView',
            component: () => import('@/views/system/custom-view/index.vue'),
            meta: { title: '视图管理', icon: 'AppstoreOutlined', permission: 'custom-view:manage' }
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
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/index.vue'),
        meta: { title: '个人中心', icon: 'UserOutlined', hideInMenu: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const routePermissionAliases: Record<string, string[]> = {
  'monitoring:list': ['monitoring:target'],
  'monitoring:alert:current': ['monitoring:alert:center'],
  'monitoring:alert:my': ['monitoring:alert:center'],
  'monitoring:alert:history': ['monitoring:alert:center'],
  'monitoring:alert:setting': ['monitoring:alert:rule', 'monitoring:alert:center'],
  'monitoring:alert:rule': ['monitoring:alert:setting', 'monitoring:alert:center'],
  'monitoring:alert:integration': ['monitoring:alert:external', 'monitoring:alert:center'],
  'monitoring:alert:external': ['monitoring:alert:integration', 'monitoring:alert:center'],
  'monitoring:alert:group': ['monitoring:alert:center'],
  'monitoring:alert:inhibit': ['monitoring:alert:center'],
  'monitoring:alert:silence': ['monitoring:alert:center'],
  'monitoring:alert:notice': ['monitoring:alert:center'],
  'monitoring:alert:detail': ['monitoring:alert:current', 'monitoring:alert:my', 'monitoring:alert:history', 'monitoring:alert:center']
}

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
        // getUserInfo 失败（可能是 401 或其他错误）
        // 401 会在请求拦截器中处理跳转，这里也做保险处理
        userStore.clearToken()
        next('/login')
        return
      }
    }

    // 检查权限
    if (to.meta.permission) {
      const required = to.meta.permission as string
      const aliases = routePermissionAliases[required] || []
      const allowed = userStore.hasPermission(required) || aliases.some((item) => userStore.hasPermission(item))
      if (!allowed) {
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
    }
    
    next()
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
