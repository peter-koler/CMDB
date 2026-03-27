import request from '@/utils/request'

export interface MonitorTemplate {
  id: number
  app: string
  name: string
  category: string
  content: string
  version: number
  is_hidden: boolean
  created_at: string
  updated_at: string
}

export interface MonitorCategory {
  id: number
  name: string
  code: string
  icon?: string
  sort_order: number
  parent_id?: number
}

export const getTemplates = (params?: { category?: string }) => {
  return request({
    url: '/monitoring/templates',
    method: 'GET',
    params
  })
}

export const getTemplate = (app: string) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'GET'
  })
}

export const createTemplate = (data: Partial<MonitorTemplate>) => {
  return request({
    url: '/monitoring/templates',
    method: 'POST',
    data
  })
}

export const updateTemplate = (app: string, data: Partial<MonitorTemplate>) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'PUT',
    data
  })
}

export const deleteTemplate = (app: string) => {
  return request({
    url: `/monitoring/templates/${app}`,
    method: 'DELETE'
  })
}

export const getCategories = () => {
  return request({
    url: '/monitoring/templates/categories',
    method: 'GET'
  })
}

export const createCategory = (data: Partial<MonitorCategory>) => {
  return request({
    url: '/monitoring/templates/categories',
    method: 'POST',
    data
  })
}

export const updateCategory = (code: string, data: Partial<MonitorCategory>) => {
  return request({
    url: `/monitoring/templates/categories/${code}`,
    method: 'PUT',
    data
  })
}

export const deleteCategory = (code: string) => {
  return request({
    url: `/monitoring/templates/categories/${code}`,
    method: 'DELETE'
  })
}

export const getTemplateHierarchy = (lang: string = 'zh-CN') => {
  return request({
    url: '/monitoring/templates/hierarchy',
    method: 'GET',
    params: { lang }
  })
}

export interface AlertItem {
  id: number
  rule_id?: number
  name?: string
  content?: string
  action?: string
  escalation_level?: number
  level: 'critical' | 'warning' | 'info' | string
  status?: string
  monitor_name?: string
  monitor_id?: number
  app?: string
  instance?: string
  metric?: string
  metric_value?: number | string
  threshold?: number | string
  triggered_at?: string
  recovered_at?: string
  duration_seconds?: number
  assignee?: string
  note?: string
  scope?: 'current' | 'history' | string
  source_type?: 'local' | 'external' | string
  source_name?: string
}

export interface AlertNotificationRecord {
  id: number
  alert_id: number
  rule_id?: number
  receiver_type?: string
  receiver_id?: number
  notify_type?: string
  status?: number
  content?: string
  error_msg?: string
  retry_times?: number
  sent_at?: string
  created_at?: string
  updated_at?: string
}

export interface AlertTimelineEvent {
  id: string | number
  event_type?: string
  title?: string
  content?: string
  operator?: string
  source?: string
  payload?: Record<string, any>
  happened_at?: string
  happened_ms?: number
}

export interface AlertRule {
  id: number
  name: string
  // realtime_metric, periodic_metric, realtime_log, periodic_log
  type: string
  expr: string
  period?: number
  times: number
  labels: Record<string, any>
  annotations: Record<string, any>
  title_template?: string
  template?: string
  datasource_type?: string
  enabled: boolean
  creator?: string
  modifier?: string
  created_at?: string
  updated_at?: string
  // 关联通知规则
  notice_rule_id?: number
  notice_rule_ids?: number[]
  notice_rule?: {
    id: number
    name: string
    receiver_name?: string
    receiver_type?: number
  }
  matched_by?: string
  alert_scope?: string
  // 兼容旧字段
  monitor_type?: string
  metric?: string
  operator?: string
  threshold?: number | string
  level?: 'critical' | 'warning' | 'info' | string
  auto_recover?: boolean
  recover_times?: number
  notify_on_recovered?: boolean
  escalation_enabled?: boolean
  escalation_config?: {
    enabled?: boolean
    levels?: Array<{
      level?: number
      delay_seconds?: number
      notice_rule_ids?: number[]
      title_template?: string
      content_template?: string
    }>
  } | null
}

export interface MonitoringTarget {
  id: number
  job_id?: string
  name?: string
  app?: string
  target?: string
  endpoint?: string
  ci_id?: number
  ci_model_id?: number
  ci_name?: string
  ci_code?: string
  template_id?: number
  status?: string
  enabled?: boolean
  interval?: number
  interval_seconds?: number
  params?: Record<string, string>
  labels?: Record<string, string>
  last_collected_at?: string
  created_at?: string
  updated_at?: string
  version?: number
}

export interface MonitoringConnectivityTestItem {
  metrics: string
  protocol: string
  success: boolean
  code?: string
  message?: string
  raw_latency_ms?: number
  field_count?: number
  fields?: Record<string, string>
  debug?: Record<string, string>
}

export interface MonitoringConnectivityTestResult {
  monitor_id: number
  monitor_name?: string
  app?: string
  target?: string
  collector_id?: string
  collector_addr?: string
  success: boolean
  completed: boolean
  timed_out: boolean
  metrics_total: number
  metrics_finished: number
  summary?: string
  started_at?: string
  finished_at?: string
  items: MonitoringConnectivityTestItem[]
}

export const getMonitoringTargets = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/targets',
    method: 'GET',
    params
  })
}

export const getMonitoringTarget = (monitorId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}`,
    method: 'GET'
  })
}

export const testMonitoringTargetConnectivity = (monitorId: number, params?: { timeout_ms?: number }) => {
  return request<MonitoringConnectivityTestResult>({
    url: `/monitoring/targets/${monitorId}/connectivity-test`,
    method: 'POST',
    params
  })
}

export const createMonitoringTarget = (data: Partial<MonitoringTarget>) => {
  return request({
    url: '/monitoring/targets',
    method: 'POST',
    data
  })
}

export const updateMonitoringTarget = (monitorId: number, data: Partial<MonitoringTarget>) => {
  return request({
    url: `/monitoring/targets/${monitorId}`,
    method: 'PUT',
    data
  })
}

export const deleteMonitoringTarget = (monitorId: number, version?: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}`,
    method: 'DELETE',
    params: version ? { version } : undefined
  })
}

export const enableMonitoringTarget = (monitorId: number, data?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/enable`,
    method: 'PATCH',
    data
  })
}

export const disableMonitoringTarget = (monitorId: number, data?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/disable`,
    method: 'PATCH',
    data
  })
}

export interface MetricSeriesItem {
  __name__?: string
  __metrics__?: string
  __metric__?: string
  [key: string]: string | undefined
}

export interface MetricRangePoint {
  timestamp: number
  value: number
}

export interface MetricRangeSeries {
  name: string
  labels?: Record<string, string>
  points: MetricRangePoint[]
}

export interface MetricLatestItem {
  name: string
  value?: number
  text?: string
  timestamp?: number
  stale?: boolean
}

export const getTargetMetricSeries = (monitorId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics/series`,
    method: 'GET',
    params
  })
}

export const queryTargetMetricRange = (monitorId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics/query-range`,
    method: 'GET',
    params
  })
}

export const getTargetMetricLatest = (monitorId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics/latest`,
    method: 'GET',
    params
  })
}

export const exportTargetMetric = (monitorId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics/export`,
    method: 'GET',
    params,
    responseType: 'blob'
  })
}

export const getTargetMetricsView = (monitorId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics-view`,
    method: 'GET'
  })
}

export const saveTargetMetricsView = (monitorId: number, data: { visible_fields_by_group: Record<string, string[]> }) => {
  return request({
    url: `/monitoring/targets/${monitorId}/metrics-view`,
    method: 'PUT',
    data
  })
}

export const getCurrentAlerts = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/alerts/current',
    method: 'GET',
    params
  })
}

export const getAlertDetail = (alertId: number) => {
  return request({
    url: `/monitoring/alerts/${alertId}`,
    method: 'GET'
  })
}

export const getAlertRuleByAlertId = (alertId: number) => {
  return request({
    url: `/monitoring/alerts/${alertId}/rule`,
    method: 'GET'
  })
}

export const getAlertNotifications = (alertId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/alerts/${alertId}/notifications`,
    method: 'GET',
    params
  })
}

export const getAlertTimeline = (alertId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/alerts/${alertId}/timeline`,
    method: 'GET',
    params
  })
}

export const getAlertHistory = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/alerts/history',
    method: 'GET',
    params
  })
}

export const claimAlert = (alertId: number, data?: Record<string, any>) => {
  return request({
    url: `/monitoring/alerts/${alertId}/claim`,
    method: 'POST',
    data
  })
}

export const closeAlert = (alertId: number, data?: Record<string, any>) => {
  return request({
    url: `/monitoring/alerts/${alertId}/close`,
    method: 'POST',
    data
  })
}

export const deleteAlert = (alertId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/alerts/${alertId}`,
    method: 'DELETE',
    params
  })
}

export const getAlertRules = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/alert-rules',
    method: 'GET',
    params
  })
}

export const getTargetAlertRules = (monitorId: number, params?: Record<string, any>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/rules`,
    method: 'GET',
    params
  })
}

export const createTargetAlertRule = (monitorId: number, data: Partial<AlertRule>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/rules`,
    method: 'POST',
    data
  })
}

export const updateTargetAlertRule = (monitorId: number, ruleId: number, data: Partial<AlertRule>) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/rules/${ruleId}`,
    method: 'PUT',
    data
  })
}

export const deleteTargetAlertRule = (monitorId: number, ruleId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/rules/${ruleId}`,
    method: 'DELETE'
  })
}

export const applyTargetDefaultAlertRules = (monitorId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/rules/apply-defaults`,
    method: 'POST'
  })
}

export const applyTemplateAlertRules = (templateId: number, data?: { monitor_ids?: number[]; monitor_id?: number }) => {
  return request({
    url: `/monitoring/templates/${templateId}/alerts/apply`,
    method: 'POST',
    data
  })
}

export const reloadTargetAlertRules = (monitorId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}/alerts/reload`,
    method: 'POST'
  })
}

export const createAlertRule = (data: Partial<AlertRule>) => {
  return request({
    url: '/monitoring/alert-rules',
    method: 'POST',
    data
  })
}

export const updateAlertRule = (ruleId: number, data: Partial<AlertRule>) => {
  return request({
    url: `/monitoring/alert-rules/${ruleId}`,
    method: 'PUT',
    data
  })
}

export const deleteAlertRule = (ruleId: number, version?: number) => {
  return request({
    url: `/monitoring/alert-rules/${ruleId}`,
    method: 'DELETE',
    params: version ? { version } : undefined
  })
}

export const enableAlertRule = (ruleId: number, version?: number) => {
  return request({
    url: `/monitoring/alert-rules/${ruleId}/enable`,
    method: 'PATCH',
    data: version ? { version } : {}
  })
}

export const disableAlertRule = (ruleId: number, version?: number) => {
  return request({
    url: `/monitoring/alert-rules/${ruleId}/disable`,
    method: 'PATCH',
    data: version ? { version } : {}
  })
}

export interface AlertIntegration {
  id: string | number
  name: string
  source: 'prometheus' | 'zabbix' | 'skywalking' | 'nagios' | 'custom' | string
  description?: string
  webhook_url?: string
  severity_mapping?: string
  default_labels?: string
  label_mapping?: string
  source_config?: string | Record<string, any>
  auth_type?: 'none' | 'token' | 'basic' | string
  auth_token?: string
  auth_username?: string
  auth_password?: string
  status?: 'enabled' | 'disabled' | string
  created_at?: string
  updated_at?: string
}

export const getAlertIntegrations = (params?: Record<string, any>) => request({ url: '/monitoring/alert-integrations', method: 'GET', params })
export const createAlertIntegration = (data: Partial<AlertIntegration>) => request({ url: '/monitoring/alert-integrations', method: 'POST', data })
export const updateAlertIntegration = (id: string | number, data: Partial<AlertIntegration>) => request({ url: `/monitoring/alert-integrations/${id}`, method: 'PUT', data })
export const deleteAlertIntegration = (id: string | number) => request({ url: `/monitoring/alert-integrations/${id}`, method: 'DELETE' })
export const testAlertIntegration = (id: string | number, data?: Record<string, any>) => request({ url: `/monitoring/alert-integrations/${id}/test`, method: 'POST', data })
export const toggleAlertIntegration = (id: string | number, enabled: boolean) => request({ 
  url: `/monitoring/alert-integrations/${id}/toggle`, 
  method: 'PATCH', 
  data: { enabled } 
})

export interface AlertGroup {
  id: string | number
  name: string
  group_key?: string
  match_type?: number
  group_labels?: string | string[]
  group_wait?: number
  group_interval?: number
  repeat_interval?: number
  enabled?: boolean
}

export const getAlertGroups = (params?: Record<string, any>) => request({ url: '/monitoring/alert-groups', method: 'GET', params })
export const createAlertGroup = (data: Partial<AlertGroup>) => request({ url: '/monitoring/alert-groups', method: 'POST', data })
export const updateAlertGroup = (id: string | number, data: Partial<AlertGroup>) => request({ url: `/monitoring/alert-groups/${id}`, method: 'PUT', data })
export const deleteAlertGroup = (id: string | number) => request({ url: `/monitoring/alert-groups/${id}`, method: 'DELETE' })
export const updateAlertGroupEnabled = (id: string | number, enabled: boolean) => request({ url: `/monitoring/alert-groups/${id}/enabled`, method: 'PATCH', data: { enabled } })

export interface AlertInhibit {
  id: string | number
  name: string
  source_labels?: string | Record<string, string>
  target_labels?: string | Record<string, string>
  equal_labels?: string | string[]
  enabled?: boolean
}

export const getAlertInhibits = (params?: Record<string, any>) => request({ url: '/monitoring/alert-inhibits', method: 'GET', params })
export const createAlertInhibit = (data: Partial<AlertInhibit>) => request({ url: '/monitoring/alert-inhibits', method: 'POST', data })
export const updateAlertInhibit = (id: string | number, data: Partial<AlertInhibit>) => request({ url: `/monitoring/alert-inhibits/${id}`, method: 'PUT', data })
export const deleteAlertInhibit = (id: string | number) => request({ url: `/monitoring/alert-inhibits/${id}`, method: 'DELETE' })
export const updateAlertInhibitEnabled = (id: string | number, enabled: boolean) => request({ url: `/monitoring/alert-inhibits/${id}/enabled`, method: 'PATCH', data: { enabled } })

export interface AlertSilence {
  id: string | number
  name: string
  type?: number
  match_type?: number
  labels?: string | Record<string, string>
  days?: number[] | string
  start_time?: number
  end_time?: number
  reason?: string
  enabled?: boolean
}

export const getAlertSilences = (params?: Record<string, any>) => request({ url: '/monitoring/alert-silences', method: 'GET', params })
export const createAlertSilence = (data: Partial<AlertSilence>) => request({ url: '/monitoring/alert-silences', method: 'POST', data })
export const updateAlertSilence = (id: string | number, data: Partial<AlertSilence>) => request({ url: `/monitoring/alert-silences/${id}`, method: 'PUT', data })
export const deleteAlertSilence = (id: string | number) => request({ url: `/monitoring/alert-silences/${id}`, method: 'DELETE' })
export const updateAlertSilenceEnabled = (id: string | number, enabled: boolean) => request({ url: `/monitoring/alert-silences/${id}/enabled`, method: 'PATCH', data: { enabled } })

export interface AlertNotice {
  id: string | number
  name: string
  channel_type?: string
  notify_type?: string
  receiver_type?: 'user' | 'group' | string
  receiver_id?: number
  receiver_name?: string
  notify_times?: number
  notify_scale?: 'single' | 'batch' | string
  template_id?: number
  template_name?: string
  filter_all?: boolean
  labels?: Record<string, string>
  days?: number[]
  period_start?: string
  period_end?: string
  enable?: boolean
  target?: string
  status?: string
  recipient_type?: 'user' | 'department' | string
  recipient_ids?: number[]
  include_sub_departments?: boolean
}

export const getAlertNotices = (params?: Record<string, any>) => request({ url: '/monitoring/alert-notices', method: 'GET', params })
export const createAlertNotice = (data: Partial<AlertNotice>) => request({ url: '/monitoring/alert-notices', method: 'POST', data })
export const updateAlertNotice = (id: string | number, data: Partial<AlertNotice>) => request({ url: `/monitoring/alert-notices/${id}`, method: 'PUT', data })
export const deleteAlertNotice = (id: string | number) => request({ url: `/monitoring/alert-notices/${id}`, method: 'DELETE' })
export const testAlertNotice = (id: string | number, data?: Record<string, any>) => request({ url: `/monitoring/alert-notices/${id}/test`, method: 'POST', data })

export interface MonitoringDashboardPoint {
  time: string
  value: number
}

export interface MonitoringDashboardData {
  overview: {
    total_monitors: number
    healthy_monitors: number
    unhealthy_monitors: number
    open_alerts: number
  }
  status_distribution: Array<{ name: string; value: number }>
  alert_trend: MonitoringDashboardPoint[]
  success_rate_trend: MonitoringDashboardPoint[]
  top_alert_monitors: Array<{ name: string; value: number }>
  recent_alerts: AlertItem[]
}

export const getMonitoringDashboard = () => {
  return request<MonitoringDashboardData>({
    url: '/monitoring/dashboard',
    method: 'GET'
  })
}

export interface CollectorItem {
  id: string
  name?: string
  ip?: string
  status?: string | number
  version?: string
  updated_at?: string
  task_count?: number
  mode?: string
  created_at?: string
}

export const getCollectors = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/collectors',
    method: 'GET',
    params
  })
}

export const deleteCollector = (collectorId: string) => {
  return request({
    url: `/monitoring/collectors/${collectorId}`,
    method: 'DELETE'
  })
}

// 下线 Collector（踢出）
export const offlineCollector = (collectorId: string) => {
  return request({
    url: `/monitoring/collectors/${collectorId}/offline`,
    method: 'POST'
  })
}

// 获取 Collector 绑定的 Monitor 列表
export const getCollectorMonitors = (collectorId: string) => {
  return request({
    url: `/monitoring/collectors/${collectorId}/monitors`,
    method: 'GET'
  })
}

// 为 Monitor 指定 Collector（固定分配）
export const assignCollectorToMonitor = (monitorId: number, collectorId: string, pinned: boolean = true) => {
  return request({
    url: `/monitoring/targets/${monitorId}/collector`,
    method: 'POST',
    data: { collector_id: collectorId, pinned }
  })
}

// 取消 Monitor 的 Collector 固定分配
export const unassignCollectorFromMonitor = (monitorId: number) => {
  return request({
    url: `/monitoring/targets/${monitorId}/collector`,
    method: 'DELETE'
  })
}

export interface MonitoringLabel {
  id: string | number
  name: string
  value?: string
  color?: string
  monitor_count?: number
}

export const getMonitoringLabels = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/labels',
    method: 'GET',
    params
  })
}

export const createMonitoringLabel = (data: Partial<MonitoringLabel>) => {
  return request({
    url: '/monitoring/labels',
    method: 'POST',
    data
  })
}

export const updateMonitoringLabel = (labelId: string | number, data: Partial<MonitoringLabel>) => {
  return request({
    url: `/monitoring/labels/${labelId}`,
    method: 'PUT',
    data
  })
}

export const deleteMonitoringLabel = (labelId: string | number) => {
  return request({
    url: `/monitoring/labels/${labelId}`,
    method: 'DELETE'
  })
}

export interface StatusPageItem {
  id: string | number
  name: string
  slug?: string
  status?: string
  is_public?: boolean
  updated_at?: string
}

export const getStatusPages = (params?: Record<string, any>) => {
  return request({
    url: '/monitoring/status-pages',
    method: 'GET',
    params
  })
}

export const createStatusPage = (data: Partial<StatusPageItem>) => {
  return request({
    url: '/monitoring/status-pages',
    method: 'POST',
    data
  })
}

export const updateStatusPage = (statusId: string | number, data: Partial<StatusPageItem>) => {
  return request({
    url: `/monitoring/status-pages/${statusId}`,
    method: 'PUT',
    data
  })
}

export const deleteStatusPage = (statusId: string | number) => {
  return request({
    url: `/monitoring/status-pages/${statusId}`,
    method: 'DELETE'
  })
}

// ==================== 通知渠道配置 ====================

export interface NoticeReceiver {
  id: string | number
  name: string
  type: number
  type_name?: string
  enable?: boolean
  description?: string
  config?: Record<string, any>
  creator?: string
  modifier?: string
  created_at?: string
  updated_at?: string
}

export const getNoticeReceivers = (params?: Record<string, any>) => request({ url: '/monitoring/notice-receivers', method: 'GET', params })
export const getAllNoticeReceivers = () => request({ url: '/monitoring/notice-receivers/all', method: 'GET' })
export const getNoticeReceiver = (id: string | number) => request({ url: `/monitoring/notice-receivers/${id}`, method: 'GET' })
export const createNoticeReceiver = (data: Partial<NoticeReceiver>) => request({ url: '/monitoring/notice-receivers', method: 'POST', data })
export const updateNoticeReceiver = (id: string | number, data: Partial<NoticeReceiver>) => request({ url: `/monitoring/notice-receivers/${id}`, method: 'PUT', data })
export const deleteNoticeReceiver = (id: string | number) => request({ url: `/monitoring/notice-receivers/${id}`, method: 'DELETE' })
export const testNoticeReceiver = (id: string | number) => request({ url: `/monitoring/notice-receivers/${id}/test`, method: 'POST' })
