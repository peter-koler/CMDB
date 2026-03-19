import { MIDDLEWARE_DEFAULT_POLICIES } from './middleware-default-policies'
import { WEBSERVER_DEFAULT_POLICIES } from './webserver-default-policies'

export interface DefaultPolicyItem {
  key: string
  name: string
  type: 'realtime_metric' | 'periodic_metric'
  metric: string
  operator: string
  threshold: number
  level: 'critical' | 'warning' | 'info'
  period: number
  times: number
  mode: 'core' | 'extended'
  enabled: boolean
  expr?: string
  template?: string
  notice_rule_id?: number
  labels?: Record<string, string>
  auto_recover?: boolean
  recover_times?: number
  notify_on_recovered?: boolean
}

const DB_APP_NAMES: Record<string, string> = {
  postgresql: 'PostgreSQL',
  db2: 'DB2',
  mariadb: 'MariaDB',
  sqlserver: 'SQL Server',
  kingbase: 'Kingbase',
  greenplum: 'GreenPlum',
  tidb: 'TiDB',
  mongodb_atlas: 'MongoDB Atlas',
  oceanbase: 'OceanBase',
  vastbase: 'Vastbase',
  oracle: 'Oracle',
  dm: 'DM',
  opengauss: 'OpenGauss'
}

const buildAvailabilityPolicy = (app: string, displayName: string): DefaultPolicyItem => ({
  key: `${app}_unavailable`,
  name: `${displayName}实例不可用`,
  type: 'realtime_metric',
  metric: `${app}_server_up`,
  operator: '==',
  threshold: 0,
  level: 'critical',
  period: 60,
  times: 1,
  mode: 'core',
  enabled: true,
  expr: `${app}_server_up == 0`,
  template: '实例不可用'
})

const clonePolicies = (policies: DefaultPolicyItem[]): DefaultPolicyItem[] =>
  policies.map((item) => ({ ...item, labels: item.labels ? { ...item.labels } : undefined }))

export const REDIS_DEFAULT_POLICY: DefaultPolicyItem[] = [
  { key: 'redis_unavailable', name: '实例不可用', type: 'realtime_metric', metric: 'redis_server_up', operator: '==', threshold: 0, level: 'critical', period: 60, times: 1, mode: 'core', enabled: true, expr: 'redis_server_up == 0' },
  { key: 'redis_memory_usage_high', name: '内存使用率过高', type: 'periodic_metric', metric: 'used_memory', operator: '>', threshold: 85, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: '(maxmemory > 0) && ((used_memory / maxmemory) * 100 > 85)' },
  { key: 'redis_memory_fragmentation_high', name: '内存碎片严重', type: 'periodic_metric', metric: 'mem_fragmentation_ratio', operator: '>', threshold: 2.0, level: 'warning', period: 600, times: 1, mode: 'core', enabled: true, expr: 'mem_fragmentation_ratio > 2.0' },
  { key: 'redis_connections_saturated', name: '连接数饱和', type: 'realtime_metric', metric: 'connected_clients', operator: '>', threshold: 90, level: 'critical', period: 300, times: 1, mode: 'core', enabled: true, expr: '(maxclients > 0) && ((connected_clients / maxclients) * 100 > 90)' },
  { key: 'redis_rejected_connections', name: '拒绝连接', type: 'realtime_metric', metric: 'rejected_connections', operator: '>', threshold: 0, level: 'critical', period: 300, times: 1, mode: 'core', enabled: true, expr: 'rejected_connections > 0' },
  { key: 'redis_rdb_failed', name: 'RDB 失败', type: 'realtime_metric', metric: 'rdb_last_bgsave_status_ok', operator: '==', threshold: 0, level: 'critical', period: 60, times: 1, mode: 'core', enabled: true, expr: 'rdb_last_bgsave_status_ok == 0' },
  { key: 'redis_aof_failed', name: 'AOF 失败', type: 'realtime_metric', metric: 'aof_last_bgrewrite_status_ok', operator: '==', threshold: 0, level: 'critical', period: 60, times: 1, mode: 'core', enabled: true, expr: 'aof_last_bgrewrite_status_ok == 0' },
  { key: 'redis_master_slave_lag_high', name: '主从延迟过高', type: 'periodic_metric', metric: 'master_last_io_seconds_ago', operator: '>', threshold: 5, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: 'master_last_io_seconds_ago > 5' },
  { key: 'redis_memory_usage_warn', name: '内存使用率预警', type: 'periodic_metric', metric: 'used_memory', operator: '>', threshold: 75, level: 'warning', period: 300, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_memory_fragmentation_warn', name: '内存碎片预警', type: 'periodic_metric', metric: 'mem_fragmentation_ratio', operator: '>', threshold: 1.5, level: 'warning', period: 600, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_hit_rate_drop', name: '命中率突降', type: 'periodic_metric', metric: 'keyspace_hit_rate', operator: '<', threshold: 50, level: 'warning', period: 300, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_hit_rate_abnormal', name: '命中率异常', type: 'periodic_metric', metric: 'keyspace_hit_rate', operator: '<', threshold: 30, level: 'critical', period: 300, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_master_slave_lag_warn', name: '主从延迟预警', type: 'periodic_metric', metric: 'master_last_io_seconds_ago', operator: '>', threshold: 3, level: 'warning', period: 300, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_slave_offline', name: '从节点离线', type: 'realtime_metric', metric: 'slave_online', operator: '<', threshold: 0.5, level: 'critical', period: 60, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_blocked_clients_high', name: '阻塞客户端过多', type: 'realtime_metric', metric: 'blocked_clients', operator: '>', threshold: 10, level: 'warning', period: 300, times: 1, mode: 'extended', enabled: false },
  { key: 'redis_slowlog_high', name: '慢查询过多', type: 'periodic_metric', metric: 'slowlog_length', operator: '>', threshold: 50, level: 'warning', period: 300, times: 1, mode: 'extended', enabled: false }
]

export const MYSQL_DEFAULT_POLICY: DefaultPolicyItem[] = [
  { key: 'mysql_unavailable', name: 'MySQL实例不可用', type: 'realtime_metric', metric: 'mysql_server_up', operator: '==', threshold: 0, level: 'critical', period: 60, times: 1, mode: 'core', enabled: true, expr: 'mysql_server_up == 0' },
  { key: 'mysql_connections_util_high', name: 'MySQL连接利用率过高', type: 'periodic_metric', metric: 'max_used_connections', operator: '>', threshold: 90, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: '(max_connections > 0) && ((max_used_connections / max_connections) * 100 > 90)' },
  { key: 'mysql_threads_running_high', name: 'MySQL活动线程过高', type: 'periodic_metric', metric: 'threads_running', operator: '>', threshold: 100, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: 'threads_running > 100' },
  { key: 'mysql_aborted_connects_high', name: 'MySQL连接失败持续增长', type: 'periodic_metric', metric: 'aborted_connects', operator: '>', threshold: 10, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: 'aborted_connects > 10' },
  { key: 'mysql_innodb_hit_rate_low', name: 'MySQL InnoDB 缓冲命中率偏低', type: 'periodic_metric', metric: 'innodb_buffer_hit_rate', operator: '<', threshold: 90, level: 'warning', period: 600, times: 1, mode: 'core', enabled: true, expr: 'innodb_buffer_hit_rate < 90' },
  { key: 'mysql_table_lock_wait_high', name: 'MySQL表锁等待过高', type: 'periodic_metric', metric: 'table_locks_waited', operator: '>', threshold: 10, level: 'warning', period: 300, times: 1, mode: 'core', enabled: true, expr: 'table_locks_waited > 10' }
]

export const getBuiltinDefaultPolicyByApp = (appRaw: string): DefaultPolicyItem[] => {
  const app = String(appRaw || '').trim().toLowerCase()
  if (app === 'redis') return clonePolicies(REDIS_DEFAULT_POLICY)
  if (app === 'mysql') return clonePolicies(MYSQL_DEFAULT_POLICY)
  const middleware = MIDDLEWARE_DEFAULT_POLICIES[app as keyof typeof MIDDLEWARE_DEFAULT_POLICIES]
  if (middleware) return clonePolicies(middleware as DefaultPolicyItem[])
  const webserver = WEBSERVER_DEFAULT_POLICIES[app as keyof typeof WEBSERVER_DEFAULT_POLICIES]
  if (webserver) return clonePolicies(webserver as DefaultPolicyItem[])
  const dbName = DB_APP_NAMES[app]
  if (!dbName) return []
  return [buildAvailabilityPolicy(app, dbName)]
}
