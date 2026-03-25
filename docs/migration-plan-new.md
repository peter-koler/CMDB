# 监控平台技术文档

> 本文档描述基于 Go + Python + Vue 的监控平台架构设计与实现细节
> 
> 文档版本：v1.3 | 最后更新：2026-03-25

---

## 目录

1. [系统架构](#1-系统架构)
2. [核心功能](#2-核心功能)
3. [组件详解](#3-组件详解)
4. [数据模型](#4-数据模型)
5. [数据流](#5-数据流)
6. [接口规范](#6-接口规范)
7. [部署架构](#7-部署架构)
8. [附录](#附录)

---

## 1. 系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              监控平台架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐         HTTP          ┌──────────────────┐           │
│  │                  │ ◄────────────────────► │                  │           │
│  │   前端 (Vue 3)    │                        │   Python Web     │           │
│  │                  │                        │   (Flask)        │           │
│  │ • 监控配置        │                        │                  │           │
│  │ • 数据展示        │                        │ • 用户管理        │           │
│  │ • 告警管理        │                        │ • 权限控制        │           │
│  │ • 采集器管理      │                        │ • 数据查询        │           │
│  │ • License管理     │                        │ • 告警展示        │           │
│  └──────────────────┘                        │ • 模板管理        │           │
│                                              └────────┬─────────┘           │
│                                                     │                      │
│                                              HTTP   │   gRPC               │
│                                                     ▼                      │
│                                              ┌──────────────────┐         │
│                                              │                  │         │
│                                              │   Go Manager     │◄────────┤
│                                              │                  │   gRPC  │
│                                              │ • 任务调度        │         │
│                                              │ • 告警计算        │         │
│                                              │ • 数据分发        │         │
│                                              │ • Collector管理   │         │
│                                              │ • License管理     │         │
│                                              │ • 模板运行时      │         │
│                                              └────────┬─────────┘         │
│                                                     │                      │
│                                              gRPC   │                      │
│                                                     ▼                      │
│                                              ┌──────────────────┐         │
│                                              │                  │         │
│                                              │  Go Collector    │         │
│                                              │   (多实例)        │         │
│                                              │                  │         │
│                                              │ • 本地调度        │         │
│                                              │ • 指标采集        │         │
│                                              │ • 批量上报        │         │
│                                              │ • SSH解析优化     │         │
│                                              └──────────────────┘         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              数据存储层                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   PostgreSQL     │  │   Redis          │  │ VictoriaMetrics  │          │
│  │                  │  │                  │  │                  │          │
│  │ • 元数据          │  │ • 实时数据缓存    │  │ • 历史时序数据    │          │
│  │ • 配置信息        │  │ • 消息队列        │  │ • 告警计算        │          │
│  │ • 告警记录        │  │ • 分布式锁        │  │ • 趋势分析        │          │
│  │ • License数据     │  │ • 升级队列        │  │ • 长期存储        │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 前端 | Vue 3 + TypeScript + Vite | 3.4+ |
| UI 框架 | Ant Design Vue | 4.x |
| 后端 | Python + Flask | 3.11 + 3.0 |
| ORM | Flask-SQLAlchemy | 3.1 |
| Manager | Go + Gin + gRPC | 1.21+ |
| Collector | Go | 1.21+ |
| 数据库 | PostgreSQL | 14+ |
| 缓存 | Redis | 6+ |
| 时序库 | VictoriaMetrics | 1.9+ |

---

## 2. 核心功能

### 2.1 监控功能

**功能描述**：采集各类指标数据并存储

**核心流程**：
```
用户创建监控 ──▶ Python Web 保存配置 ──▶ 调用 Manager 下发任务
                                                    │
                                                    ▼
                                           Manager 选择 Collector
                                                    │
                                                    ▼
                                           Collector 本地时间轮调度
                                                    │
                                                    ▼
                                           按 interval 定时采集
                                                    │
                                                    ▼
                                           采集结果 ──▶ Manager
                                                    │
                                                    ▼
                                           数据分发 (双写)
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              │                                           │
                              ▼                                           ▼
                    ┌──────────────────┐                     ┌──────────────────────┐
                    │   Redis (实时)    │                     │ VictoriaMetrics      │
                    │                  │                     │ (历史)               │
                    │ • 最新数据缓存   │                     │ • 持久化存储         │
                    │ • 实时告警计算   │                     │ • 周期告警计算       │
                    │ • TTL 5分钟      │                     │ • 长期存储           │
                    └──────────────────┘                     └──────────────────────┘
```

**关键特性**：
- Collector 本地调度：Manager 只下发任务，不触发定时采集
- 时间轮调度：使用 HashedWheelTimer 管理大量定时任务
- 多协议支持：HTTP、ICMP、SNMP、JDBC、SSH、JMX 等
- 负载均衡：一致性哈希分配任务到多个 Collector
- SSH 解析优化：支持单行/多行输出解析，智能识别表头和数据行
- OS SSH 单连接 Bundle：同一监控轮次内将多个 SSH metric 合并为一次远端执行，按 `bundleSection` 拆分结果并对齐时间戳

### 2.2 告警功能

**功能描述**：基于采集数据计算告警规则，触发通知

**告警计算三层架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                      告警计算架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  第一层：告警计算 (Calculator)                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 实时告警：采集数据到达立即计算                      │   │
│  │ • 周期告警：定时扫描历史数据（如每5分钟）              │   │
│  │ • 表达式：支持 JEXL 表达式判断阈值                    │   │
│  │ • 算术运算：支持 + - * / () 与 && || 组合             │   │
│  │ • 跨字段比值：支持 used_memory/maxmemory 等比值规则   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  第二层：告警收敛 (Reducer)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 分组收敛：相同类型告警合并（支持 group_key/interval）│   │
│  │ • 抑制收敛：高级别告警抑制低级别（DB 配置驱动）        │   │
│  │ • 静默收敛：维护窗口期间不发送告警（DB 配置驱动）      │   │
│  │ • 重复抑制：repeat_interval 防止持续抖动告警风暴      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  第三层：告警通知 (Notifier)                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 渠道：Webhook、邮件、企业微信、钉钉、短信、系统通知  │   │
│  │ • 模板：支持变量替换、条件判断（规则模板+通知模板）    │   │
│  │ • 过滤：支持 filter_all/labels/days/period 高级过滤   │   │
│  │ • 批量：支持 notify_scale=single/batch 批量发送       │   │
│  │ • 限频：支持 notify_times 限制窗口内发送次数          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**告警状态流转**：
```
触发 ──▶ 待处理 ──▶ 处理中 ──▶ 已恢复/已关闭
 │         │          │
 │         ▼          ▼
 │      分配给某人   标记解决
 │
 └── 自动恢复（指标恢复正常）
```

**告警升级机制**：
```
首轮通知(Level 0) ──▶ 等待时间 ──▶ 升级通知(Level 1) ──▶ 等待时间 ──▶ 升级通知(Level 2)
     │                      │                              │
     │                      │                              └── 升级到部门负责人
     │                      └── 升级到上级经理
     └── 原通知规则

说明：
- 告警触发后，若在指定时间内未被处理（状态仍为"待处理"），自动升级通知给更高级别接收人
- 支持多级升级阶梯，每级可配置不同的等待时间和通知规则
- 升级前会反查告警状态，若已处理或恢复则终止升级流程
```

**规则来源与绑定**：
- **模板默认规则**：监控模板定义默认告警项（如 Redis 核心 8 条）
- **实例级覆写**：监控实例可继承模板默认规则，并允许覆写阈值、级别、通知规则等
- **规则热加载**：manager-go 每 60 秒自动从共享 DB 热加载规则

**Redis 默认告警规则（示例）**：
| 规则名称 | 类型 | 默认状态 | 说明 |
|---------|------|---------|------|
| 实例不可用 | 实时 | 启用 | 采集器上报异常 |
| 内存使用率过高 | 周期 | 启用 | used_memory/maxmemory > 85% |
| 连接数饱和 | 实时 | 启用 | connected_clients/maxclients > 90% |
| RDB 失败 | 实时 | 启用 | rdb_last_bgsave_status != ok |

### 2.3 数据展示功能

**功能描述**：查询时序数据并可视化展示

**展示内容**：
- 实时监控：最新指标值、状态
- 历史趋势：折线图展示指标变化
- 告警列表：当前告警、历史告警
- 采集器状态：在线状态、任务数、性能指标
- 监控指标面板：实时指标展示和趋势分析

### 2.4 License 管理功能

**功能描述**：软件授权许可证管理

**核心能力**：
- 机器码生成：基于硬件信息生成唯一标识
- 许可证验证：验证许可证有效性和过期时间
- 时钟回拨检测：防止通过修改系统时间绕过授权
- 多模块授权：支持不同功能模块的独立授权

---

## 3. 组件详解

### 3.1 前端 (Vue 3)

**目录结构**：
```
frontend/src/
├── api/                    # API 接口定义
│   ├── monitoring.ts       # 监控相关接口[BasicLayout](../frontend/src/layouts/BasicLayout.vue)
│   ├── alert.ts            # 告警相关接口
│   └── license.ts          # License 管理接口
├── views/                  # 页面组件
│   ├── monitoring/
│   │   ├── target/         # 监控目标管理
│   │   ├── collector/      # 采集器管理
│   │   ├── alert/          # 告警管理
│   │   └── metrics/        # 指标展示面板
│   └── license/            # License 管理页面
├── components/             # 公共组件
│   └── monitoring/
│       └── metrics/        # 监控指标组件
├── layouts/                # 布局组件
├── router/                 # 路由配置
└── stores/                 # Pinia 状态管理
```

**核心页面**：

| 页面 | 功能 | 路径 |
|------|------|------|
| 监控目标 | CRUD 监控配置 | /monitoring/targets |
| 采集器管理 | 查看 Collector 状态、任务分配 | /monitoring/collectors |
| 告警规则 | 配置告警阈值、通知方式 | /monitoring/alert-rules |
| 告警历史 | 查看告警记录、处理状态 | /monitoring/alert-history |
| License 管理 | 许可证上传、状态查看 | /license |
| 指标面板 | 实时指标展示和趋势 | /monitoring/metrics |

### 3.2 Python Web (Flask)

**目录结构**：
```
backend/
├── app/
│   ├── models/             # 数据模型
│   │   └── hertzbeat_models.py
│   ├── routes/             # API 路由
│   │   ├── monitoring_target.py
│   │   ├── collector.py
│   │   └── license.py      # License 管理路由
│   └── services/           # 业务服务
│       └── manager_api_service.py
├── templates/              # 监控模板 (YAML)
│   ├── app-*.yml           # 各类监控模板
├── scripts/                # 运维脚本
│   ├── init_postgres.sh    # PostgreSQL 初始化
│   ├── migrate_sqlite_to_postgres.py  # 数据迁移
│   └── diagnose_os_monitor.py         # OS 监控诊断
├── config.py               # 配置
└── run.py                  # 启动入口
```

**核心职责**：
- 用户认证与权限管理
- 监控配置 CRUD
- 数据查询代理（转发到 Manager）
- 告警展示与处理
- License 管理接口

**与 Manager 交互**：
```python
# 下发任务到 Manager
def create_monitor(data):
    # 保存到数据库
    monitor = Monitor(**data)
    db.session.add(monitor)
    db.session.commit()
    
    # 调用 Manager API 下发任务
    requests.post(f"{MANAGER_URL}/api/v1/monitors", json={
        "monitor_id": monitor.id,
        "app": monitor.app,
        "interval_ms": monitor.intervals * 1000,
        ...
    })
```

### 3.3 Go Manager

**目录结构**：
```
manager-go/
├── cmd/manager/            # 启动入口
│   └── main.go
├── internal/
│   ├── alert/              # 告警计算引擎
│   │   ├── engine.go       # 实时告警表达式引擎
│   │   ├── periodic.go     # 周期告警评估器
│   │   ├── reduce.go       # 告警收敛（分组/抑制/静默）
│   │   ├── event_store.go  # 告警事件存储
│   │   ├── async.go        # 异步通知队列
│   │   └── escalation.go   # 告警升级队列
│   ├── collector/          # Collector 管理
│   │   ├── client.go       # gRPC 客户端
│   │   ├── manager.go      # 任务调度
│   │   ├── registry.go     # 注册中心
│   │   └── scheduler.go    # 负载均衡
│   ├── httpapi/            # HTTP API
│   │   └── server.go
│   ├── notify/             # 通知服务
│   │   ├── service.go      # 通知发送服务
│   │   └── template.go     # 模板渲染
│   ├── store/              # 数据存储
│   │   ├── alert_runtime_store.go  # 告警共享存储适配层
│   │   ├── collector_store.go
│   │   └── monitor_store.go
│   ├── template/           # 模板管理
│   │   ├── registry.go     # 模板运行时注册表
│   │   └── store.go        # 模板存储
│   ├── license/            # License 管理
│   │   └── manager.go      # 许可证管理器
│   ├── dispatch/           # 数据分发
│   │   ├── dispatcher.go   # 分发器
│   │   ├── redis_sink.go   # Redis 写入
│   │   └── vm_sink.go      # VictoriaMetrics 写入
│   ├── scheduler/          # 任务调度
│   │   └── dispatch_scheduler.go
│   ├── dbutil/             # 数据库工具
│   │   └── dsn.go          # DSN 处理工具
│   └── pb/                 # protobuf 定义
│       └── proto/
│           └── collector.proto
├── config/                 # 配置文件
│   └── manager.yaml        # Manager 运行时配置
├── proto/                  # protobuf 源文件
└── start.sh                # 启动脚本
```

**核心模块**：

#### 3.3.1 多数据源配置支持

Manager-Go 支持为不同功能模块配置独立的数据源：

```go
type runtimeConfig struct {
    ManagerAddr                     string `yaml:"manager_addr"`
    PythonWebDB                     string `yaml:"python_web_db"`
    ManagerDatabaseURL              string `yaml:"manager_database_url"`
    MonitorDSN                      string `yaml:"monitor_dsn"`        // 监控配置数据源
    CollectorDSN                    string `yaml:"collector_dsn"`      // 采集器数据源
    AlertRuntimeDSN                 string `yaml:"alert_runtime_dsn"`  // 告警运行时数据源
    TemplateDSN                     string `yaml:"template_dsn"`       // 模板数据源
    LicenseDSN                      string `yaml:"license_dsn"`        // License 数据源
    RedisAddr                       string `yaml:"redis_addr"`
    VictoriaMetricsURL              string `yaml:"victoria_metrics_url"`
    CollectorHeartbeatTimeoutSecond int    `yaml:"collector_heartbeat_timeout_seconds"`
}
```

**配置优先级**：
1. 配置文件中的特定 DSN 字段（如 `monitor_dsn`）
2. 环境变量（如 `MANAGER_MONITOR_DSN`）
3. 基础 DSN（`manager_database_url` 或 `DATABASE_URL`）
4. 回退到 SQLite（`python_web_db`）

#### 3.3.2 告警计算引擎 (Alert Engine)

```go
// 实时告警表达式引擎
type Engine struct {
    mu     sync.Mutex
    states map[string]condState  // 告警状态缓存
}

type Rule struct {
    ID              int64
    Name            string
    Expression      string        // 支持算术运算 + - * / ()
    DurationSeconds int
    Severity        string        // critical/warning/info
    Enabled         bool
}

type Event struct {
    RuleID       int64
    MonitorID    int64
    App          string
    Instance     string
    Severity     string
    State        State           // normal/pending/firing
    TriggeredAt  time.Time
}
```

**关键特性**：
- **表达式能力**：支持算术运算（`+ - * / ()`）与逻辑组合（`&& ||`）
- **跨字段比值**：支持 `used_memory/maxmemory`、`connected_clients/maxclients` 等比值规则
- **状态流转**：normal → pending → firing → resolved
- **指标快照**：monitor 级指标快照缓存（5 分钟 TTL），支持跨字段引用

#### 3.3.3 告警升级 (Escalation)

```go
// 升级队列 - 基于 Redis ZSET 实现延时队列
type EscalationQueue struct {
    Key    string          // "alert:escalation:queue"
    Member string          // group_key (告警分组键)
    Score  int64           // next_trigger_timestamp (下次触发时间戳)
}

// 阶段跟踪 - 记录当前升级状态
type EscalationStage struct {
    Key        string      // "alert:escalation:stage:{group_key}"
    Fields     map[string]interface{}
    // current_level: 当前处于第几个阶梯 (0, 1, 2...)
    // started_at: 升级流程开始时间
    // last_escalated_at: 上次升级时间
}

type EscalationConfig struct {
    Enabled     bool              `json:"enabled"`      // 是否启用升级
    Levels      []EscalationLevel `json:"levels"`       // 升级阶梯配置
}

type EscalationLevel struct {
    Level           int           `json:"level"`           // 阶梯级别
    WaitDuration    time.Duration `json:"wait_duration"`   // 等待时间
    NoticeRuleID    int64         `json:"notice_rule_id"`  // 通知规则ID
    Template        string        `json:"template"`        // 升级通知内容模板
    Description     string        `json:"description"`     // 说明
}
```

**升级流程**：
1. 告警触发时，若配置了升级策略，将告警加入延时队列
2. Escalation Worker 定时扫描队列，检查到期的升级任务
3. 升级前反查告警状态，若已处理则终止流程
4. 发送升级通知，更新阶段状态，进入下一级等待

#### 3.3.4 告警收敛 (Reducer)

```go
type Reducer struct {
    silences      []SilenceRule   // 静默规则（DB 配置驱动）
    inhibits      []InhibitRule   // 抑制规则（DB 配置驱动）
    groups        []GroupRule     // 分组规则（DB 配置驱动）
    groupWindow   time.Duration
    inhibitWindow time.Duration
}
```

**收敛策略**：
- **分组收敛**：按 `group_key` 分组，`group_interval` 控制发送窗口
- **抑制收敛**：critical 告警抑制 warning/info 告警（支持自定义 source/target 匹配）
- **静默收敛**：支持一次性/周期性静默，按标签匹配
- **重复抑制**：`repeat_interval` 防止持续抖动告警风暴

#### 3.3.5 通知服务 (Notify)

```go
type NoticeDispatch struct {
    workerPool          *AlerterWorkerPool
    noticeConfigService NoticeConfigService
    alertNotifyHandlerMap map[byte]AlertNotifyHandler
}
```

**通知能力**：
- **渠道映射**：`receiver.type=1(email)/2(webhook)/4(wecom)` 等
- **模板渲染**：支持 `notice_templates.content` 覆盖默认模板
- **高级过滤**：`filter_all/labels_json/days_json/period_start/period_end`
- **批量发送**：`notify_scale=single/batch`，批量窗口 10 秒或 20 条
- **发送限频**：`notify_times` 限制 24h 窗口内发送次数

#### 3.3.6 模板运行时 (Template Registry)

```go
type Registry struct {
    mu        sync.RWMutex
    templates map[string]*Template  // app -> Template
    store     Store                 // 底层存储
}

type Template struct {
    App         string
    Name        string
    Category    string        // os/db/service/custom
    Params      []Param       // 输入参数定义
    Metrics     []MetricGroup // 指标组定义
    Alerts      []AlertRule   // 默认告警规则
}
```

**特性**：
- 从 PostgreSQL 加载模板定义
- 支持热重载（60 秒间隔）
- 内存缓存加速访问
- 支持多语言（zh-CN/en-US/ja-JP/zh-TW）

#### 3.3.7 License 管理

```go
type Manager struct {
    store       Store
    machineCode string
    license     *License
}

type License struct {
    MachineCode string
    ExpireAt    time.Time
    Modules     []string  // 授权模块列表
    Signature   string    // 签名验证
}
```

**功能**：
- 机器码生成：基于 CPU、MAC 等硬件信息
- 许可证验证：RSA 签名验证
- 过期检查：支持永久授权和限时授权
- 时钟回拨检测：防止时间篡改

### 3.4 模板编译与任务分发

#### 3.4.1 模板编译原理

监控模板（YAML）在 Manager 中会被编译成可执行的 MetricsTask，核心流程：

```
监控模板 (YAML)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  metrics: [                                                 │
│    { name: cpu, protocol: ssh, ... },      ──────┐         │
│    { name: memory, protocol: http, ... }, ───────┤         │
│    { name: disk, protocol: snmp, ... }     ──────┤         │
│  ]                                                 │         │
└────────────────────────────────────────────────────┼─────────┘
                                                     │
                                                     ▼
                                           ┌──────────────────┐
                                           │   模板编译器      │
                                           │  (Compiler)      │
                                           │                  │
                                           │ • 逐个编译 metric │
                                           │ • 验证 protocol  │
                                           │ • 提取协议配置    │
                                           │ • 生成 Task      │
                                           └────────┬─────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │  MetricsTask[]   │
                                           │                  │
                                           │ • Task 1: ssh    │
                                           │ • Task 2: http   │
                                           │ • Task 3: snmp   │
                                           └────────┬─────────┘
                                                    │
                                                    ▼
                                           Collector 执行
```

**编译约束**：

| 约束 | 说明 | 示例 |
|------|------|------|
| **必须有 protocol** | 每个 metric 必须指定采集协议 | `protocol: ssh` |
| **协议配置块必须存在** | protocol 值对应配置块必须存在 | `protocol: ssh` 必须有 `ssh:` 配置 |
| **一 metric 一 Task** | 每个 metric 编译成一个独立任务 | 3 个 metric = 3 个 Task |

**支持的协议类型**：

| 协议 | 配置块 | 典型用途 |
|------|--------|----------|
| SSH | `ssh:` | Linux/Unix 系统监控 |
| HTTP | `http:` | Web 服务、API 监控 |
| SNMP | `snmp:` | 网络设备监控 |
| JDBC | `jdbc:` | 数据库监控 |
| JMX | `jmx:` | Java 应用监控 |
| ICMP | `ping:` | 网络连通性监控 |

**编译后的 Task 结构**：

```protobuf
message MetricsTask {
    string name = 1;                    // metric 名称，如 "cpu"
    string protocol = 2;                // 协议类型，如 "ssh"
    int64 timeout_ms = 3;               // 超时时间
    int32 priority = 4;                 // 优先级
    map<string, string> params = 5;     // 所有参数（含协议配置）
    string exec_kind = 6;               // 执行类型："pull"
    repeated FieldSpec field_specs = 7; // 字段定义
    repeated CalculateSpec calculate_specs = 8; // 计算规则
}
```

#### 3.4.2 任务执行流程

Collector 收到 Task 后，根据 protocol 选择对应的执行器：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  收到 Task       │────►│ 解析 protocol   │────►│ 选择执行器       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┼──────────────────────────┐
                              │                          │                          │
                              ▼                          ▼                          ▼
                       ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
                       │ SSHCollector│           │HTTPCollector│           │SNMPCollector│
                       │             │           │             │           │             │
                       │ • 建立连接   │           │ • 发送请求   │           │ • SNMP Get   │
                       │ • 执行脚本   │           │ • 解析响应   │           │ • 解析 OID   │
                       │ • 解析输出   │           │ • 提取指标   │           │ • 提取指标   │
                       └──────┬──────┘           └──────┬──────┘           └──────┬──────┘
                              │                          │                          │
                              └──────────────────────────┼──────────────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   返回指标数据   │
                                                │                 │
                                                │ • 字段名        │
                                                │ • 字段值        │
                                                │ • 单位          │
                                                └─────────────────┘
```

**设计优势**：
- **模板与执行解耦**：模板编译成 Task 后，Collector 只关心 Task 内容
- **灵活扩展**：新增协议只需新增 Protocol Collector，无需修改模板系统
- **细粒度控制**：每个 metric 独立配置超时、优先级、字段定义

#### 3.4.3 OS SSH Bundle 执行基线（2026-03-25）

**适用模板**：
- `linux` / `ubuntu` / `debian` / `centos` / `almalinux` / `opensuse`
- `freebsd` / `redhat` / `rockylinux` / `euleros` / `fedora` / `darwin`

**模板语义（统一）**：
1. 每个模板新增隐藏参数 `bundleScript`
2. 每个 SSH metric 注入：
   - `bundleScript: ^_^bundleScript^_^`
   - `bundleSection: <metric-name>`
3. 每个 SSH metric 移除 `script:`（pure bundle）
4. `interface` 统一字段：
   - `interface_name`
   - `ip_address`
   - `mac_address`
   - `receive_bytes`
   - `transmit_bytes`

**运行语义（统一）**：
1. Manager 仍按“一 metric 一 task”编译（模型不变）
2. Collector 在同一轮将 SSH task 合并为一次远端执行
3. 按 `bundleSection` 从统一输出拆分每个 metric 的结果
4. 同轮结果使用同一快照时间戳，避免跨 metric 时间漂移
5. 调试日志输出：
   - `ssh-bundle-cmd`
   - `ssh-bundle-output`

### 3.5 Go Collector

**目录结构**：
```
collector-go/
├── cmd/collector/          # 启动入口
│   └── main.go
├── internal/
│   ├── collector/          # 采集器核心
│   │   ├── collector.go    # 采集器实例
│   │   ├── scheduler.go    # 时间轮调度器
│   │   └── reporter.go     # 结果上报
│   ├── protocol/           # 协议实现
│   │   ├── httpcollector/  # HTTP 协议
│   │   ├── sshcollector/   # SSH 协议
│   │   │   ├── ssh.go
│   │   │   ├── bundle.go   # SSH bundle 单连接快照执行
│   │   │   ├── parse.go    # 输出解析（支持单行/多行）
│   │   │   └── parse_test.go
│   │   ├── snmpcollector/  # SNMP 协议
│   │   ├── jdbccollector/  # JDBC 协议
│   │   └── jmxcollector/   # JMX 协议
│   └── pb/                 # protobuf 定义
├── config/
│   └── collector.json      # 采集器配置
└── start.sh
```

**SSH 解析优化**：

SSH 协议采集支持智能解析命令输出，自动识别表头和数据行：

- **单行解析模式**：适用于 `top`、`ps` 等输出单行结果的命令
- **多行解析模式**：适用于 `df`、`free` 等输出多行表格的命令
- **智能评分算法**：根据字段类型匹配度选择最佳数据行，排除表头干扰

---

## 4. 数据模型

### 4.1 核心实体关系

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  monitor_categories   │     │  monitor_templates    │     │  alert_defines      │
│  (监控分类)           │◄────┤  (监控模板)           │◄────┤  (告警规则定义)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  monitors       │     │  collectors     │     │  alert_events   │
│  (监控实例)           │────►│  (采集器)             │     │  (告警事件)          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               │
         ▼                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  monitor_params │     │  collector_tasks│     │  notice_rules   │
│  (监控参数)           │     │  (采集任务)           │     │  (通知规则)          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 4.2 关键表结构

#### monitors（监控实例表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 监控 ID |
| name | VARCHAR(100) | 监控名称 |
| app | VARCHAR(100) | 监控类型（对应模板 app） |
| host | VARCHAR(100) | 目标主机 |
| intervals | INT | 采集间隔（秒） |
| status | TINYINT | 状态：0-暂停，1-启用 |
| collector_id | BIGINT | 绑定的采集器 ID |
| params | JSON | 监控参数（模板定义的参数值） |

#### alert_defines（告警规则定义表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 规则 ID |
| monitor_id | BIGINT FK | 所属监控实例 |
| template_rule_id | BIGINT | 模板规则 ID（实例覆写时关联） |
| expr | VARCHAR(500) | 告警表达式 |
| severity | TINYINT | 级别：0-info, 1-warning, 2-critical |
| duration | INT | 持续时长（秒） |
| notice_rule_ids | JSON | 通知规则 ID 列表 |
| escalation_config | JSON | 升级配置 |
| enabled | TINYINT | 是否启用 |

**escalation_config JSON 结构**：
```json
{
  "enabled": true,
  "levels": [
    {
      "level": 1,
      "wait_duration": "10m",
      "notice_rule_id": 101,
      "template": "告警已持续10分钟未处理，升级到上级经理",
      "description": "升级到上级经理"
    },
    {
      "level": 2,
      "wait_duration": "30m",
      "notice_rule_id": 102,
      "template": "告警已持续40分钟未处理，升级到部门负责人",
      "description": "升级到部门负责人"
    }
  ]
}
```

#### collectors（采集器表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 采集器 ID |
| name | VARCHAR(100) | 采集器名称 |
| code | VARCHAR(100) | 唯一标识码 |
| status | TINYINT | 状态：0-离线，1-在线 |
| ip_addr | VARCHAR(50) | IP 地址 |
| last_heartbeat_at | TIMESTAMP | 最后心跳时间 |
| task_count | INT | 当前任务数 |

#### notice_rules（通知规则表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 规则 ID |
| name | VARCHAR(100) | 规则名称 |
| receiver_type | TINYINT | 接收类型：1-email, 2-webhook, 4-wecom |
| receiver_config | JSON | 接收配置 |
| filter_all | TINYINT | 是否接收所有告警 |
| labels_json | JSON | 标签过滤条件 |
| days_json | JSON | 生效日期 |
| period_start | TIME | 生效时段开始 |
| period_end | TIME | 生效时段结束 |
| notify_scale | TINYINT | 发送模式：1-single, 2-batch |
| notify_times | INT | 24h 内最大发送次数 |

### 4.3 Redis 数据结构

#### 实时指标缓存

```
Key: monitor:metrics:{monitor_id}
Type: Hash
Field: {metric_name}
Value: {value}
TTL: 300s
```

#### 告警升级队列

```
Key: alert:escalation:queue
Type: ZSET
Member: {group_key}
Score: {next_trigger_timestamp}

Key: alert:escalation:stage:{group_key}
Type: Hash
Field: current_level, started_at, last_escalated_at
```

---

## 5. 数据流

### 5.1 监控数据采集流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Collector │────►│   Protocol  │────►│   Parser    │────►│   Reporter  │
│  时间轮调度  │     │   协议采集   │     │   结果解析   │     │   结果上报   │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                                                                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Victoria   │◄────│   Manager   │◄────│   gRPC      │◄────│   Collector │
│   Metrics   │     │   数据分发   │     │   流式传输   │     │   批量上报   │
└─────────────┘     └──────┬──────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  实时缓存   │
                    └─────────────┘
```

### 5.2 告警计算流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Metrics   │────►│   Engine    │────►│   Reducer   │────►│   Notifier  │
│   指标到达   │     │   告警计算   │     │   告警收敛   │     │   通知发送   │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                    │
                                                                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Escalation│◄────│   Queue     │◄────│   Event     │◄────│   Alert     │
│   升级检查   │     │   延时队列   │     │   事件存储   │     │   状态判断   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## 6. 接口规范

### 6.1 HTTP API

#### Python Web API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/monitors | 获取监控列表 |
| POST | /api/v1/monitors | 创建监控 |
| PUT | /api/v1/monitors/:id | 更新监控 |
| DELETE | /api/v1/monitors/:id | 删除监控 |
| GET | /api/v1/monitors/:id/metrics | 获取监控指标 |
| GET | /api/v1/collectors | 获取采集器列表 |
| POST | /api/v1/collectors/:id/assign | 分配监控任务 |
| GET | /api/v1/alerts | 获取告警列表 |
| POST | /api/v1/alerts/:id/ack | 确认告警 |
| POST | /api/v1/alerts/:id/resolve | 解决告警 |
| GET | /api/v1/license/status | 获取 License 状态 |
| POST | /api/v1/license/upload | 上传 License |

#### Manager-Go API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/monitors | 获取监控任务列表 |
| POST | /api/v1/monitors | 创建监控任务 |
| PUT | /api/v1/monitors/:id | 更新监控任务 |
| DELETE | /api/v1/monitors/:id | 删除监控任务 |
| GET | /api/v1/collectors | 获取 Collector 列表 |
| POST | /api/v1/collectors/:id/heartbeat | Collector 心跳 |
| GET | /api/v1/metrics/query | 查询指标数据 |
| GET | /api/v1/alert/rules | 获取告警规则 |
| POST | /api/v1/alert/rules | 创建告警规则 |
| GET | /api/v1/alert/silences | 获取静默规则列表 |
| POST | /api/v1/alert/silences | 创建静默规则 |
| PUT | /api/v1/alert/silences/:id | 更新静默规则 |
| DELETE | /api/v1/alert/silences/:id | 删除静默规则 |
| GET | /api/v1/alert/inhibits | 获取抑制规则列表 |
| POST | /api/v1/alert/inhibits | 创建抑制规则 |
| PUT | /api/v1/alert/inhibits/:id | 更新抑制规则 |
| DELETE | /api/v1/alert/inhibits/:id | 删除抑制规则 |
| GET | /api/v1/license/status | 获取 License 状态 |
| GET | /api/v1/license/machine-code | 获取机器码 |
| GET | /api/v1/templates | 获取模板列表 |
| GET | /api/v1/templates/:app | 获取模板详情 |

### 6.2 gRPC 接口

```protobuf
service CollectorService {
    // 双向流：建立长连接
    rpc Connect(stream CollectorFrame) returns (stream ManagerFrame);
}

// 上行消息（Collector -> Manager）
message CollectorFrame {
    oneof payload {
        RegisterReq register = 1;      // 注册请求
        Heartbeat heartbeat = 2;       // 心跳
        CollectRep report = 3;         // 采集结果上报
    }
}

// 下行消息（Manager -> Collector）
message ManagerFrame {
    oneof payload {
        RegisterResp register_resp = 1;  // 注册响应
        Heartbeat heartbeat = 2;         // 心跳响应
        CollectTask task = 3;            // 任务下发
    }
}
```

---

## 7. 部署架构

### 7.1 单机部署

```
┌─────────────────────────────────────────────────────────────┐
│                         单机部署                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Nginx     │  │  Python Web │  │   Manager   │         │
│  │   (80/443)  │  │   (:5000)   │  │   (:8080)   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                │
│         └────────────────┴────────────────┘                │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  PostgreSQL │  │    Redis    │  │      VM     │         │
│  │   (:5432)   │  │   (:6379)   │  │   (:8428)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 分布式部署

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              分布式部署                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           接入层                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   Nginx     │  │   Nginx     │  │   Nginx     │                 │   │
│  │  │  (LB)       │  │  (LB)       │  │  (LB)       │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          应用层                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Python Web  │  │ Python Web  │  │   Manager   │  │  Manager   │ │   │
│  │  │  (Instance1)│  │  (Instance2)│  │  (Instance1)│  │ (Instance2)│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          数据层                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ PostgreSQL  │  │    Redis    │  │  Victoria   │  │ Collector  │ │   │
│  │  │  (Primary)  │  │  (Cluster)  │  │  (Cluster)  │  │  (Multiple)│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 附录

### A.1 监控模板清单

#### 操作系统监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-centos.yml | OS | SSH | CentOS 系统监控 |
| app-ubuntu.yml | OS | SSH | Ubuntu 系统监控 |
| app-debian.yml | OS | SSH | Debian 系统监控 |
| app-redhat.yml | OS | SSH | RHEL 系统监控 |
| app-rockylinux.yml | OS | SSH | Rocky Linux 监控 |
| app-almalinux.yml | OS | SSH | AlmaLinux 监控 |
| app-fedora.yml | OS | SSH | Fedora 系统监控 |
| app-opensuse.yml | OS | SSH | openSUSE 监控 |
| app-euleros.yml | OS | SSH | EulerOS 监控 |
| app-macos.yml | OS | SSH | macOS 系统监控 |
| app-darwin.yml | OS | SSH | Darwin 系统监控 |
| app-freebsd.yml | OS | SSH | FreeBSD 系统监控 |
| app-windows.yml | OS | WMI/SSH | Windows 系统监控 |
| app-linux.yml | OS | SSH | 通用 Linux 监控 |

#### 数据库监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-mysql.yml | DB | JDBC | MySQL 数据库监控 |
| app-mariadb.yml | DB | JDBC | MariaDB 监控 |
| app-postgresql.yml | DB | JDBC | PostgreSQL 监控 |
| app-oracle.yml | DB | JDBC | Oracle 数据库监控 |
| app-sqlserver.yml | DB | JDBC | SQL Server 监控 |
| app-db2.yml | DB | JDBC | DB2 数据库监控 |
| app-mongodb_atlas.yml | DB | 协议 | MongoDB Atlas 监控 |
| app-redis.yml | DB | 协议 | Redis 监控 |
| app-memcached.yml | DB | 协议 | Memcached 监控 |
| app-elasticsearch.yml | DB | HTTP | Elasticsearch 监控 |
| app-clickhouse.yml | DB | HTTP | ClickHouse 监控 |
| app-influxdb.yml | DB | HTTP | InfluxDB 监控 |
| app-iotdb.yml | DB | 协议 | IoTDB 监控 |
| app-opengauss.yml | DB | JDBC | openGauss 监控 |
| app-oceanbase.yml | DB | JDBC | OceanBase 监控 |
| app-tidb.yml | DB | JDBC | TiDB 监控 |
| app-dm.yml | DB | JDBC | 达梦数据库监控 |
| app-kingbase.yml | DB | JDBC | 人大金仓监控 |
| app-vastbase.yml | DB | JDBC | 海量数据库监控 |
| app-greenplum.yml | DB | JDBC | Greenplum 监控 |

#### 大数据监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-hadoop.yml | BigData | 协议 | Hadoop 监控 |
| app-hdfs_namenode.yml | BigData | 协议 | HDFS NameNode |
| app-hdfs_datanode.yml | BigData | 协议 | HDFS DataNode |
| app-hbase_master.yml | BigData | 协议 | HBase Master |
| app-hbase_regionserver.yml | BigData | 协议 | HBase RegionServer |
| app-hive.yml | BigData | 协议 | Hive 监控 |
| app-spark.yml | BigData | 协议 | Spark 监控 |
| app-yarn.yml | BigData | 协议 | YARN 监控 |
| app-flink.yml | BigData | HTTP | Flink 监控 |
| app-kafka.yml | BigData | 协议 | Kafka 监控 |
| app-kafka_client.yml | BigData | 协议 | Kafka Client |
| app-zookeeper.yml | BigData | 协议 | ZooKeeper 监控 |
| app-airflow.yml | BigData | HTTP | Airflow 监控 |
| app-prestodb.yml | BigData | HTTP | PrestoDB 监控 |
| app-doris_be.yml | BigData | HTTP | Doris BE 监控 |
| app-iceberg.yml | BigData | HTTP | Iceberg 监控 |
| app-hugegraph.yml | BigData | HTTP | HugeGraph 监控 |

#### 中间件与应用监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-nginx.yml | Middleware | HTTP | Nginx 监控 |
| app-tomcat.yml | Middleware | HTTP | Tomcat 监控 |
| app-jetty.yml | Middleware | HTTP | Jetty 监控 |
| app-rabbitmq.yml | Middleware | HTTP | RabbitMQ 监控 |
| app-rocketmq.yml | Middleware | 协议 | RocketMQ 监控 |
| app-activemq.yml | Middleware | 协议 | ActiveMQ 监控 |
| app-pulsar.yml | Middleware | HTTP | Pulsar 监控 |
| app-apollo.yml | Middleware | HTTP | Apollo 监控 |
| app-shenyu.yml | Middleware | HTTP | ShenYu 网关监控 |
| app-spring_gateway.yml | Middleware | HTTP | Spring Gateway |
| app-ftp.yml | Service | FTP | FTP 服务监控 |
| app-smtp.yml | Service | SMTP | SMTP 服务监控 |
| app-pop3.yml | Service | POP3 | POP3 服务监控 |
| app-imap.yml | Service | IMAP | IMAP 服务监控 |
| app-ntp.yml | Service | NTP | NTP 服务监控 |
| app-dns.yml | Service | DNS | DNS 服务监控 |
| app-ping.yml | Service | ICMP | Ping 监控 |
| app-port.yml | Service | TCP | 端口监控 |
| app-udp_port.yml | Service | UDP | UDP 端口监控 |
| app-website.yml | Service | HTTP | 网站监控 |
| app-api.yml | Service | HTTP | API 监控 |
| app-websocket.yml | Service | WS | WebSocket 监控 |
| app-ssl_cert.yml | Service | TLS | SSL 证书监控 |
| app-mqtt.yml | Service | MQTT | MQTT 监控 |

#### 云原生与容器监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-kubernetes.yml | CloudNative | HTTP | Kubernetes 监控 |
| app-docker.yml | CloudNative | HTTP | Docker 监控 |
| app-consul_sd.yml | CloudNative | HTTP | Consul 服务发现 |
| app-dns_sd.yml | CloudNative | DNS | DNS 服务发现 |
| app-coreos.yml | CloudNative | SSH | CoreOS 监控 |

#### 网络设备监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-huawei_switch.yml | Network | SNMP | 华为交换机 |
| app-h3c_switch.yml | Network | SNMP | H3C 交换机 |
| app-cisco_switch.yml | Network | SNMP | 思科交换机 |
| app-tplink_switch.yml | Network | SNMP | TP-Link 交换机 |
| app-hpe_switch.yml | Network | SNMP | HPE 交换机 |

#### 视频与安防监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-hikvision_isapi.yml | Security | HTTP | 海康威视 ISAPI |
| app-dahua.yml | Security | HTTP | 大华设备监控 |
| app-uniview.yml | Security | HTTP | 宇视设备监控 |

#### 存储与其他监控

| 模板 | 类型 | 协议 | 说明 |
|------|------|------|------|
| app-synology_nas.yml | Storage | SNMP | 群晖 NAS |
| app-idrac.yml | Hardware | SNMP | Dell iDRAC |
| app-ipmi.yml | Hardware | IPMI | IPMI 监控 |
| app-nvidia.yml | Hardware | 协议 | NVIDIA GPU |
| app-deepseek.yml | AI | HTTP | DeepSeek API |
| app-valkey.yml | DB | 协议 | Valkey 监控 |

### A.2 运维工具脚本

| 脚本 | 路径 | 说明 |
|------|------|------|
| init_postgres.sh | backend/scripts/ | PostgreSQL 初始化 |
| migrate_sqlite_to_postgres.py | backend/scripts/ | SQLite 到 PostgreSQL 迁移 |
| diagnose_os_monitor.py | backend/scripts/ | OS 监控诊断工具 |

**OS 监控诊断工具用法**：
```bash
# 诊断指定监控实例
python3 backend/scripts/diagnose_os_monitor.py --monitor-id 3

# 输出内容：
# - 数据库配置检查
# - Manager API 连通性
# - 采集日志分析
# - 指标数据验证
```

### A.3 Manager-Go 配置示例

```yaml
# config/manager.yaml
manager_addr: ":8080"
python_web_db: "../backend/instance/it_ops.db"
manager_database_url: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"

# 多数据源配置（可选，默认使用 manager_database_url）
monitor_dsn: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"
collector_dsn: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"
alert_runtime_dsn: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"
template_dsn: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"
license_dsn: "postgres://user:pass@localhost:5432/arco_db?sslmode=disable"

redis_addr: "127.0.0.1:6379"
victoria_metrics_url: "http://127.0.0.1:8428"
collector_heartbeat_timeout_seconds: 30
```

### A.4 环境变量清单

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | Python Web 数据库连接 | - |
| MANAGER_DATABASE_URL | Manager 基础数据库 | DATABASE_URL |
| MANAGER_MONITOR_DSN | 监控配置数据源 | MANAGER_DATABASE_URL |
| MANAGER_COLLECTOR_DSN | 采集器数据源 | MANAGER_DATABASE_URL |
| MANAGER_ALERT_RUNTIME_DSN | 告警运行时数据源 | MANAGER_DATABASE_URL |
| MANAGER_TEMPLATE_DSN | 模板数据源 | MANAGER_DATABASE_URL |
| MANAGER_LICENSE_DSN | License 数据源 | MANAGER_DATABASE_URL |
| REDIS_ADDR | Redis 地址 | 127.0.0.1:6379 |
| VICTORIA_METRICS_URL | VM 地址 | http://127.0.0.1:8428 |
| MANAGER_ADDR | Manager 监听地址 | :8080 |
| COLLECTOR_HEARTBEAT_TIMEOUT_SECONDS | 采集器心跳超时 | 30 |

---

*文档版本：v1.3*  
*最后更新：2026-03-24*
