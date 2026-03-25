# 监控平台迁移计划

## 1. 核心需求

三大功能：监控、告警、数据展示，用户交互访问仍使用现有前端 Vue 和后端 Python，管理端使用 Go

## 2. 目标架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         目标架构 (3个组件)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    HTTP API    ┌─────────────────┐    gRPC        │
│  │   Python Web    │ ◄────────────► │   Go Manager    │ ◄────────────► │
│  │   (Flask)       │                │   (Gin + gRPC)  │                │
│  │                 │                │                 │                │
│  │ • 用户界面       │                │ • 任务调度       │                │
│  │ • 权限管理       │                │ • 告警计算       │                │
│  │ • 数据展示       │                │ • 数据存储       │                │
│  │ • 告警展示       │                │                 │                │
│  └─────────────────┘                └─────────────────┘                │
│           ▲                                   │                          │
│           │                                   │                          │
│           │                                   ▼                          │
│           │                          ┌─────────────────┐                │
│           │                          │  Go Collector   │                │
│           │                          │  (多实例)        │                │
│           │                          └─────────────────┘                │
│           │                                                            │
│           └────────────────── 告警通知 ◄─────────────────────────────────┘
│                                                                         │
│  数据存储层:                                                            
│  • SQLite/PostgreSQL - 元数据、配置、告警记录 (Python Web 管理)          
│  • VictoriaMetrics - 历史时序数据 (Go Manager 写入与查询接口)      
│  • Redis - 实时数据缓存 + 消息队列 + 告警通知推送                          
│                                                                         
│  双存储架构:                                                            
│  ┌─────────────────────────────────────────────────────────────────┐   
│  │                     数据分发 (Data Dispatch)                     │   
│  └───────────────────────────┬─────────────────────────────────────┘   
│                              │                                         
│              ┌───────────────┴───────────────┐                        
│              ▼                               ▼                        
│  ┌─────────────────────────┐    ┌─────────────────────────────┐       
│  │      实时数据存储        │    │        历史数据存储          │       
│  │       (Redis)           │    │    (VictoriaMetrics)        │       
│  ├─────────────────────────┤    ├─────────────────────────────┤       
│  │ • 最新采集数据缓存       │    │ • 持久化时序数据              │       
│  │ • 快速查询 (毫秒级)      │    │ • 历史趋势分析                │       
│  │ • 容量有限 (最近5分钟)   │    │ • 大容量、高压缩              │       
│  │ • 用于实时告警计算       │    │ • 用于周期告警计算            │       
│  │ • Dashboard 实时刷新     │    │ • 报表和长期分析              │       
│  └─────────────────────────┘    └─────────────────────────────┘       
│                                                                         
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 数据口径规范（参考 HertzBeat 实现）

**指标命名**
- 非 Prometheus 采集：`__name__ = {metrics}_{field}`，例如 `cpu_usage` 来自 `metrics=cpu` + `field=usage`
- Prometheus 自动采集：`__name__ = {metrics}`，不附加字段后缀
- 统一维度：`job={app}`、`instance={instance}`，Prometheus 模式下 `job={app 去掉 _prometheus_ 前缀}`
- 诊断维度：`__monitor_id__` 作为监控实例标识
- 指标组映射：`__metrics__={metrics}`，非 Prometheus 模式下 `__metric__={field}`

**标签体系**
- 标签来源：
  - 指标字段中 `label=true` 的字段作为标签
  - 监控配置携带的自定义标签（labels）直接并入指标标签
- 必备标签：`job`、`instance`、`__monitor_id__`
- 业务标签建议：`env`、`region`、`cluster`、`app` 等稳定维度，避免高基数标签

**保留策略**
- 历史数据默认保留建议：90 天（与 HertzBeat DuckDB/IoTDB 默认值对齐）
- InfluxDB 侧由应用创建保留策略，默认 30 天
- VM/其他时序库在库侧配置保留期，应用侧仅声明默认策略与可配置项

## 3. 三大功能逻辑

### 3.1 监控功能

**核心逻辑**: 采集指标数据并存储（双存储架构）

```
用户创建监控 ──▶ Python Web 保存配置 ──▶ 调用 Go Manager 下发任务
                                                    │
                                                    ▼
                                           Go Manager 选择 Collector
                                                    │
                                                    ▼
                                           Collector 本地时间轮调度
                                                    │
                                                    ▼
                                           按 interval 定时采集
                                                    │
                                                    ▼
                                           采集结果 ──▶ Go Manager
                                                    │
                                                    ▼
                                           数据分发 (Data Dispatch)
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              │                                           │
                              ▼                                           ▼
                    ┌──────────────────┐                     ┌──────────────────────┐
                    │   实时数据存储    │                     │     历史数据存储      │
                    │    (Redis)       │                     │ (VictoriaMetrics)    │
                    ├──────────────────┤                     ├──────────────────────┤
                    │ • 最新数据缓存   │                     │ • 持久化存储         │
                    │ • 实时告警计算   │                     │ • 周期告警计算       │
                    │ • Dashboard展示 │                     │ • 历史趋势分析       │
                    └──────────────────┘                     └──────────────────────┘
```

**数据分发逻辑**:
1. **实时数据流**: 采集数据 → Redis (TTL 5分钟) → 实时告警计算 → Dashboard
2. **历史数据流**: 采集数据 → VictoriaMetrics → 周期告警计算 → 历史报表
3. **双写策略**: 同一份数据同时写入 Redis 和 VictoriaMetrics，满足不同场景需求

**关键设计**:
- Collector 本地调度：Manager 只负责下发任务，不负责定时触发
- 时间轮调度：Collector 使用 HashedWheelTimer 管理大量定时任务
- 多协议支持：HTTP、ICMP、SNMP、JDBC、Linux 命令等
- 负载均衡：Manager 使用一致性哈希分配任务到多个 Collector

### 3.2 告警功能 (参考 HertzBeat)

**核心逻辑**: 实时计算告警规则，触发通知

HertzBeat 告警系统分为四个层次：

#### 第一层：告警计算 (Calculator)

**功能**: 判断指标是否触发告警条件

**两种计算模式**:

1. **实时告警计算**
   - 触发时机：每次采集数据到达时立即计算
   - 适用场景：需要即时响应的告警（如服务宕机）
   - 计算逻辑：
     ```
     采集数据 ──▶ 匹配告警规则 ──▶ JEXL 表达式计算 ──▶ 是否触发?
     ```

2. **周期告警计算**
   - 触发时机：定时扫描历史数据（如每5分钟）
   - 适用场景：基于统计的告警（如CPU平均使用率超过80%持续5分钟）
   - 计算逻辑：
     ```
     定时触发 ──▶ 查询 VM 历史数据 ──▶ 聚合计算 ──▶ 是否触发?
     ```

3. **Collector 预计算（边缘计算）**
   - 触发时机：Collector 采集数据时本地计算
   - 适用场景：网络不稳定、需要快速响应的场景
   - 计算逻辑：
     ```
     采集数据 ──▶ Collector 本地规则匹配 ──▶ 预计算结果 ──▶ 上报 Manager
     ```
   - **预计算内容**:
     - 简单阈值判断：CPU > 80%、内存 > 90%
     - 状态检测：端口不通、服务无响应
     - 变化率计算：相比上次采集的变化幅度
   - **上报内容**:
     - 原始指标数据（必报）
     - 预计算告警标记（可选，如 trigger_alert=true）
     - 本地计算摘要（减少 Manager 计算压力）
   - **优势**:
     - 减少网络传输延迟，告警更实时
     - 减轻 Manager 计算压力
     - 网络中断时可本地缓存告警状态
   - **限制**:
     - 仅支持简单规则（单指标、即时判断）
     - 复杂规则（多指标关联、历史统计）仍需 Manager 计算

**告警规则结构**:
- 指标字段：监控哪个指标（如 cpu_usage）
- 比较操作：>、<、==、!= 等
- 阈值：触发告警的临界值
- 持续时间：持续多久才触发（防止抖动）
- 告警级别：warning、critical 等

#### 第二层：告警收敛 (Reduce)

**功能**: 防止告警风暴，减少重复通知

HertzBeat 实现了三种收敛机制：

1. **分组收敛 (Group Reduce)**
   - 逻辑：相同监控类型的告警合并为一条
   - 示例：10台 MySQL 都触发连接数告警，合并为"MySQL 连接数告警(10台)"
   - 好处：避免收到10条相似告警

2. **抑制收敛 (Inhibit Reduce)**
   - 逻辑：高级别告警抑制低级别告警
   - 示例：服务器宕机(critical) 抑制 CPU 高(warning)
   - 好处：根因告警优先，避免噪声

3. **静默收敛 (Silence Reduce)**
   - 逻辑：在指定时间段内不发送告警
   - 示例：维护窗口期间静默所有告警
   - 好处：计划内操作不触发告警

**收敛处理流程**:
```
触发告警 ──▶ 分组收敛 ──▶ 抑制收敛 ──▶ 静默收敛 ──▶ 是否发送?
                │              │              │
                ▼              ▼              ▼
            合并相似       抑制低级       检查静默期
```

#### 第三层：告警通知 (Notify)

**功能**: 将告警发送到指定渠道

**通知渠道**:
- Webhook：调用外部系统接口（最灵活）
- 邮件：SMTP 发送
- 企业微信/钉钉/飞书：通过机器人发送
- 短信：集成短信服务商

**通知内容模板**:
- 告警标题：简洁描述问题
- 告警详情：指标值、阈值、时间
- 监控对象：IP、端口、应用类型
- 处理建议：预设的解决方案

#### 第四层：告警管理 (Manage)

**功能**: 告警生命周期管理

**告警状态流转**:
```
触发 ──▶ 待处理 ──▶ 处理中 ──▶ 已恢复/已关闭
 │         │          │
 │         ▼          ▼
 │      分配给某人   标记解决
 │
 └── 自动恢复（指标恢复正常）
```

**告警升级机制**:
- 15分钟未处理：升级给主管
- 30分钟未处理：升级给经理
- 1小时未处理：电话通知

### 3.3 数据展示功能

**核心逻辑**: 查询时序数据并可视化

```
用户查看 Dashboard ──▶ Python Web 接收请求
                             │
                             ▼
                     调用 Go Manager 查询接口
                             │
                             ▼
                 Go Manager 查询 VictoriaMetrics
                             │
                             ▼
                      返回时序数据
                             │
                             ▼
                      Vue 前端渲染图表
```

**展示内容**:
- 实时监控：最新指标值、状态
- 历史趋势：折线图展示指标变化
- 告警列表：当前告警、历史告警
- 拓扑视图：监控对象之间的关系

### 3.4 通知模板系统

**功能**: 灵活定义告警通知内容和格式

**模板引擎**:
- 使用 Go template 或类似模板引擎
- 支持变量替换：{{.MetricName}}、{{.MetricValue}}、{{.Threshold}} 等
- 支持条件判断：{{if eq .Severity "critical"}}...{{end}}
- 支持循环：{{range .Tags}}...{{end}}

**模板变量**:
```
{{.AlertName}}      - 告警名称
{{.MetricName}}     - 指标名称
{{.MetricValue}}    - 当前指标值
{{.Threshold}}      - 告警阈值
{{.Severity}}       - 告警级别
{{.Instance}}       - 监控对象
{{.Timestamp}}      - 触发时间
{{.Duration}}       - 持续时间
{{.Tags}}           - 标签集合
{{.Description}}    - 告警描述
```

**模板示例**:
```
【{{.Severity}}】{{.AlertName}}

监控对象: {{.Instance}}
指标: {{.MetricName}}
当前值: {{.MetricValue}}
阈值: {{.Threshold}}
时间: {{.Timestamp}}

{{if eq .Severity "critical"}}
【紧急】请立即处理！
{{else}}
请关注此告警
{{end}}
```

**多渠道模板**:
- 邮件模板：支持 HTML 格式，可包含图表链接
- Webhook 模板：JSON 格式，适配不同系统
- 企业微信/钉钉：Markdown 格式，简洁明了
- 短信模板：精简文字，控制在 70 字以内

### 3.5 外部告警接入

**功能**: 接收第三方系统的告警，统一管理和分发

**接入方式**:

1. **Webhook 接收**
   - HTTP POST 接口接收外部告警
   - 支持 Prometheus Alertmanager、Zabbix、Nagios 等
   - 告警格式转换：将不同格式转换为内部标准格式
   ```
   外部告警 ──▶ Webhook API ──▶ 格式转换 ──▶ 内部告警流程
   ```

2. **邮件接收**
   - 监听专用邮箱，解析邮件内容生成告警
   - 支持正则匹配提取关键信息
   - 适用：传统监控系统、日志告警

3. **消息队列接收**
   - 订阅 Kafka/Redis/RabbitMQ 等队列
   - 实时消费外部系统产生的告警事件
   - 适用：云原生环境、微服务架构

**外部告警处理流程**:
```
外部告警 ──▶ 接收接口 ──▶ 格式校验 ──▶ 格式转换 ──▶ 标签增强 ──▶ 进入收敛流程
                │
                ▼
           记录来源系统
           (prometheus/zabbix/...)
```

**标签增强**:
- 自动添加来源标识：source=prometheus
- 根据规则添加业务标签：app=database, team=ops
- 用于后续的分组、路由、抑制

### 3.6 异步处理架构

**功能**: 提升告警处理性能，避免阻塞

**架构设计**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      异步告警处理架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  采集数据 │    │  告警计算 │    │  告警队列 │    │  通知发送 │  │
│  │  (同步)   │───▶│  (同步)   │───▶│  (异步)   │───▶│  (异步)   │  │
│  └──────────┘    └──────────┘    └────┬─────┘    └────┬─────┘  │
│                                       │               │        │
│                                       ▼               ▼        │
│                                  ┌─────────────────────────┐   │
│                                  │      Redis 队列         │   │
│                                  │  • alert_queue          │   │
│                                  │  • notify_queue         │   │
│                                  │  • retry_queue          │   │
│                                  └─────────────────────────┘   │
│                                       │               │        │
│                                       ▼               ▼        │
│                                  ┌──────────┐    ┌──────────┐  │
│                                  │  告警消费 │    │  通知消费 │  │
│                                  │  Worker  │    │  Worker  │  │
│                                  │ (多实例) │    │ (多实例) │  │
│                                  └──────────┘    └──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**队列设计**:

1. **告警队列 (alert_queue)**
   - 存储待处理的告警事件
   - 生产者：告警计算模块
   - 消费者：告警收敛模块
   - 优先级：critical > warning > info

2. **通知队列 (notify_queue)**
   - 存储待发送的通知任务
   - 生产者：告警收敛模块（通过收敛后）
   - 消费者：通知发送 Worker
   - 支持延迟发送（如静默期后的补发）

3. **重试队列 (retry_queue)**
   - 存储发送失败的通知
   - 延迟重试：1分钟、5分钟、15分钟、1小时
   - 最大重试次数：5次
   - 超过重试次数转人工处理

**Worker 设计**:
- 多实例部署，支持水平扩展
- 优雅关闭：处理完当前任务再退出
- 健康检查：定期上报心跳
- 失败隔离：单个任务失败不影响其他任务

**性能保障**:
- 批量处理：每次拉取多条记录批量处理
- 连接池：复用 Redis、SMTP、HTTP 连接
- 限流：防止突发流量击垮下游系统
- 监控：队列长度、处理延迟、成功率等指标

## 4. 数据流详解

### 4.1 监控数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户      │     │ Python Web  │     │ Go Manager  │     │  Collector  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 创建监控           │                   │                   │
       │ ─────────────────▶│                   │                   │
       │                   │ 保存 SQLite       │                   │
       │                   │ ─────────────────▶│                   │
       │                   │                   │                   │
       │                   │ 下发任务          │                   │
       │                   │ ─────────────────▶│                   │
       │                   │                   │ 选择 Collector    │
       │                   │                   │ (一致性哈希)      │
       │                   │                   │                   │
       │                   │                   │ gRPC 下发         │
       │                   │                   │ ─────────────────▶│
       │                   │                   │                   │
       │                   │                   │                   │ 时间轮调度
       │                   │                   │                   │ (每60秒)
       │                   │                   │                   │
       │                   │                   │                   │ 采集数据
       │                   │                   │                   │
       │                   │                   │ gRPC 上报         │
       │                   │                   │ ◀─────────────────│
       │                   │                   │                   │
       │                   │                   │ 写入 VM           │
       │                   │                   │ ─────────────────▶│
       │                   │                   │                   │
       │                   │                   │ 触发告警计算      │
       │                   │                   │ (如果满足条件)    │
       │                   │                   │                   │
       │                   │ 推送告警          │                   │
       │                   │ ◀─────────────────│                   │
       │                   │                   │                   │
       │ WebSocket 通知    │                   │                   │
       │ ◀─────────────────│                   │                   │
       │                   │                   │                   │
```

### 4.2 告警数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  采集数据   │     │ Go Manager  │     │  告警收敛   │     │  通知渠道   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 上报数据          │                   │                   │
       │ ─────────────────▶│                   │                   │
       │                   │                   │                   │
       │                   │ 匹配告警规则      │                   │
       │                   │ (JEXL 表达式)     │                   │
       │                   │                   │                   │
       │                   │ 是否触发?         │                   │
       │                   │ ─────────────────▶│                   │
       │                   │                   │                   │
       │                   │                   │ 分组收敛          │
       │                   │                   │ (合并相似)        │
       │                   │                   │                   │
       │                   │                   │ 抑制收敛          │
       │                   │                   │ (高级抑制低级)    │
       │                   │                   │                   │
       │                   │                   │ 静默收敛          │
       │                   │                   │ (检查静默期)      │
       │                   │                   │                   │
       │                   │                   │ 是否发送?         │
       │                   │                   │ ─────────────────▶│
       │                   │                   │                   │
       │                   │                   │                   │ 发送通知
       │                   │                   │                   │ (Webhook/邮件等)
       │                   │                   │                   │
       │                   │ 保存告警记录      │                   │
       │                   │ (SQLite)          │                   │
       │                   │                   │                   │
       │                   │ 推送 Redis        │                   │
       │                   │ (WebSocket 订阅)  │                   │
       │                   │                   │                   │
```

## 5. 组件职责

| 组件 | 核心职责 | 关键逻辑 |
|------|----------|----------|
| **Python Web** | 用户界面、业务逻辑、数据查询 | 接收用户操作，调用 Manager API，展示数据，查询时序数据 |
| **Go Manager** | 任务调度、告警计算、数据分发、数据存储 | 一致性哈希分配任务，JEXL 计算告警，数据分发到双存储，写入时序库 |
| **Go Collector** | 指标采集、本地调度、边缘计算 | 时间轮管理定时任务，多协议采集，上报数据，本地预计算 |

### 5.1 数据存储职责细分

| 存储类型 | 存储介质 | 核心职责 | 使用场景 |
|----------|----------|----------|----------|
| **实时数据** | Redis | 缓存最新采集数据，支持毫秒级查询 | Dashboard 实时刷新、实时告警计算 |
| **历史数据** | VictoriaMetrics | 持久化存储时序数据，支持聚合查询 | 历史趋势分析、周期告警计算、报表 |
| **元数据** | SQLite/PostgreSQL | 存储配置、监控定义、告警规则 | 系统配置、监控管理、告警历史 |
| **消息队列** | Redis | 异步处理告警和通知 | 告警事件、通知任务、重试队列 |

## 6. 关键设计决策

### 6.1 为什么 Collector 本地调度？

- **容错性**: Manager 宕机不影响已有任务采集
- **性能**: 避免 Manager 成为性能瓶颈
- **实时性**: 本地调度延迟更低

### 6.2 为什么告警要三层收敛？

- **分组**: 解决告警数量过多的问题
- **抑制**: 解决告警依赖关系问题
- **静默**: 解决计划内操作告警问题

### 6.3 为什么用 Redis 做消息队列？

- **轻量级**: 单机部署，运维简单
- **多功能**: 队列 + 缓存 + Pub/Sub 一体
- **性能**: 足够支撑当前规模

## 8. 前端菜单设计

基于现有 Ant Design Vue 框架，在**监控管理**一级菜单下新增以下二级菜单，与现有角色权限系统对接：

### 8.1 菜单结构

```
监控管理 (LineChartOutlined)
├── 监控大盘 (DashboardOutlined)          [新增]
├── 监控列表 (DesktopOutlined)            [新增]
├── 监控简报 (BookOutlined)               [新增]
├── 监控模板 (FileTextOutlined)          [已存在]
├── 告警中心 (BellOutlined)               [新增]
│   ├── 告警中心 (当前告警)
│   ├── 告警配置 (阈值规则)
│   ├── 外部告警接入
│   ├── 告警分组
│   ├── 告警抑制
│   ├── 告警静默
│   └── 通知配置
├── 采集器管理 (ClusterOutlined)          [新增]
├── 标签管理 (TagsOutlined)               [新增]
└── 状态页 (MobileOutlined)               [新增]
```

### 8.2 菜单详情

#### 8.2.1 监控模板（已存在）
- **权限标识**: `monitoring:template`
- **页面功能**: 
  - 左侧分类树（支持增删改）
  - 右侧 YAML 编辑器（参考 HertzBeat）
  - 模板预览和测试

#### 8.2.2 监控列表 [新增]
- **权限标识**: `monitoring:list`
- **页面功能**:
  - 表格展示所有监控实例（参考 HertzBeat 监控列表）
  - 字段：监控名称、类型、目标地址、状态、采集间隔、最近采集时间
  - 操作：新增、编辑、删除、启用/停用、查看详情
  - 批量操作：批量删除、批量修改采集间隔
  - 筛选：按类型、状态、标签筛选
  - 搜索：按名称、地址搜索

#### 8.2.3 告警中心 [新增]

**当前告警** (`monitoring:alert:current`)
- 表格展示未恢复告警
- 字段：告警级别、告警名称、监控对象、指标值、触发时间、持续时间、状态
- 操作：认领、关闭、查看详情、跳转到监控
- 告警级别颜色标识：critical(红)、warning(橙)、info(蓝)
- 实时推送：WebSocket 接收新告警

**告警历史** (`monitoring:alert:history`)
- 表格展示已恢复/已关闭告警
- 时间范围筛选（今天、近7天、近30天、自定义）
- 字段：同当前告警 + 恢复时间、处理人、处理备注
- 导出：支持导出 Excel/CSV

**告警配置** (`monitoring:alert:setting`)
- **页面路径**: `/monitoring/alert/setting`
- **核心功能**: 定义告警触发条件和规则，支持多种告警类型
- **规则类型**:
  - **实时指标告警** (`realtime_metric`): 基于实时采集数据触发，使用 JEXL 表达式
  - **周期指标告警** (`periodic_metric`): 基于时序数据库查询触发，支持 PromQL/SQL
  - **实时日志告警** (`realtime_log`): 基于实时日志匹配触发
  - **周期日志告警** (`periodic_log`): 基于日志数据库查询触发
- **页面功能**:
  - 表格展示告警规则列表
  - 字段：规则名称、类型、表达式、模板、标签、触发配置、启用状态
  - 操作：新增、编辑、删除、启用/停用、批量删除、导入/导出
  - 规则编辑器：
    - 基本信息：规则名称、规则类型
    - 告警表达式：
      - 实时指标：JEXL 表达式，支持内置变量（__app__, __metrics__, __instance__, usage, value 等）
      - 周期指标：数据源选择（PromQL/SQL）+ 查询表达式 + 执行周期
      - 日志告警：日志字段匹配表达式
    - 触发配置：连续触发次数、告警级别（critical/warning/info）
    - 标签和注释：用于告警分组和路由的标签、告警摘要
    - 消息模板：支持变量（${__instance__}, ${__labels__}, ${__value__} 等）
- **数据模型**: `alert_defines` 表
  - `id`: 规则ID
  - `name`: 规则名称
  - `type`: 规则类型（realtime_metric/periodic_metric/realtime_log/periodic_log）
  - `expr`: 告警表达式（JEXL/PromQL/SQL）
  - `period`: 执行周期（秒，周期类型使用）
  - `times`: 连续触发次数阈值
  - `labels_json`: 告警标签（JSON格式）
  - `annotations_json`: 告警注释（JSON格式）
  - `template`: 告警内容模板
  - `datasource_type`: 数据源类型（promql/sql）
  - `enabled`: 是否启用
  - `creator/modifier/created_at/updated_at`: 审计字段
- **操作权限**: view, create, edit, delete, toggle, import, export
- **参考实现**: HertzBeat `alert-setting.component.ts`

#### 8.2.4 通知渠道 [新增]

**通知渠道** (`monitoring:alert:notice:receiver`)
- 表格展示通知渠道列表
- 渠道类型：邮件、Webhook、企业微信机器人、钉钉机器人、飞书机器人、企业微信应用、飞书应用、短信、Slack、Discord、华为云SMN、Server酱
- 字段：渠道名称、类型、配置预览、启用状态、创建时间
- 操作：新增、编辑、删除、测试发送、启用/禁用
- 表单字段（根据类型动态显示）：
  - **邮件**：SMTP服务器、端口、用户名、密码、发件人地址、TLS
  - **Webhook**：URL、请求方法、Content-Type、认证类型、Token
  - **企业微信机器人**：Webhook Key、@手机号列表
  - **钉钉机器人**：Access Token、加签密钥、@手机号、@所有人
  - **飞书机器人**：Webhook Token、签名校验密钥
  - **企业微信应用**：企业ID、应用ID、应用密钥、指定成员/部门/标签
  - **飞书应用**：App ID、App Secret、接收类型(用户/群组)、用户ID/群组ID
  - **短信**：服务商(阿里云/腾讯云/华为云)、Access Key、Secret Key、签名、模板Code
  - **Slack/Discord**：Webhook URL
  - **华为云SMN**：Access Key、Secret Key、项目ID、区域、主题URN
  - **Server酱**：SendKey

#### 8.2.5 通知规则 [新增]

**通知规则** (`monitoring:alert:notice`)
- 表格展示通知规则列表
- 字段：规则名称、通知渠道、过滤方式、生效时间、启用状态
- 操作：新增、编辑、删除、测试发送、启用/禁用
- 表单字段：
  - **基本信息**：规则名称、选择通知渠道（从已配置渠道中选择）
  - **发送配置**：发送规模（单条/批量）、重试次数
  - **告警过滤**：全部告警 / 按标签过滤（支持多标签条件）
  - **生效时间**：生效星期（周一至周日）、时间段（HH:MM-HH:MM）
  - **启用状态**：是否启用规则
- 规则说明：
  - 一个通知渠道可被多个规则引用
  - 规则按标签过滤只转发匹配的告警
  - 生效时间外不发送通知

**外部告警接入** (`monitoring:alert:integration`)
- **核心功能**：接收第三方监控系统（Prometheus、Zabbix、SkyWalking 等）推送的告警，统一管理和分发
- **实现原理**：
  - 每个接入配置生成唯一的 Webhook URL（如 `/api/v1/alerts/webhook/{integration_id}`）
  - 外部系统通过 HTTP POST 推送告警数据到该 URL
  - 平台根据源系统类型解析并转换告警格式为内部标准格式
  - 转换后的告警进入统一的告警收敛和通知流程
- **支持的外部系统及配置字段**：

  **1. Prometheus Alertmanager**
  - 接入方式：在 prometheus.yml 中配置 alerting.alertmanagers 指向 HertzBeat 地址
  - 特定字段：Prometheus 服务器地址、告警级别映射（critical/error/warning/info）
  - 告警格式：包含 status, alerts[], labels, annotations, startsAt, endsAt, generatorURL
  - 认证：支持 Bearer Token 认证

  **2. Zabbix**
  - 接入方式：在 Zabbix 中创建 Webhook 媒介类型，配置 URL 为 Webhook 地址
  - 特定字段：Zabbix 服务器地址、Zabbix 版本（6.0+/5.0/4.x）、告警级别映射
  - 告警格式：包含 AlertName, HostName, HostIp, TriggerSeverity, ItemValue, EventTags 等 Zabbix 宏变量
  - 级别映射：支持将 Zabbix 级别（灾难/严重/一般严重/警告/信息/未分类）映射到内部级别

  **3. SkyWalking**
  - 接入方式：编辑 alarm-settings.yml，在 hooks.webhook 中配置 HertzBeat URL
  - 特定字段：SkyWalking OAP 地址
  - 告警格式：包含 scope, name, ruleName, alarmMessage, tags 等字段的数组
  - 标签提取：自动将 SkyWalking tags 转换为告警标签

  **4. Nagios**
  - 接入方式：在 Nagios 中配置通知命令，使用 curl POST 到 Webhook 地址
  - 特定字段：Nagios 服务器地址
  - 告警格式：包含 notification_type, host_name, service_description, state, output

  **5. 自定义 Webhook**
  - 接入方式：通用接收端点，接收符合 HertzBeat SingleAlert 格式的 JSON 数据
  - 特定字段：自定义格式说明文档
  - 告警格式：符合 SingleAlert 标准格式（content, status, labels, annotations, startAt, endAt）

- **通用配置字段**：
  - 基本信息：接入名称、源系统类型、描述
  - Webhook 地址：系统自动生成，供外部系统配置
  - 认证方式：无认证 / Token 认证 (Bearer) / Basic Auth
  - 标签映射：将外部系统的标签映射到内部标签（如 severity:level, host:instance）
  - 默认标签：为接入的告警自动添加来源标识（如 `source=prometheus`, `env=production`）

- **测试功能**：根据源系统类型生成对应的测试告警模板，模拟发送验证接入链路
- **操作权限**：view, create, edit, delete, test, toggle

**告警分组** (`monitoring:alert:group`)
- **核心功能**：将符合条件的告警分组收敛，减少通知风暴
- **配置字段**：
  - 分组名称、匹配规则（标签匹配表达式）
  - 分组等待时间（group_wait）：初次分组等待时间
  - 分组间隔（group_interval）：同一分组的通知间隔
  - 重复抑制时间（repeat_interval）：重复告警抑制时间
  - 匹配类型：全部匹配/部分匹配
- **实现原理**：
  - 告警进入时根据 group_key 进行分组
  - 同一分组内的告警合并为一条通知
  - 支持按 instance、alertname、severity 等标签分组
- **操作权限**：view, create, edit, delete, toggle

**告警抑制** (`monitoring:alert:inhibit`)
- **核心功能**：高优先级告警抑制低优先级告警，避免重复通知
- **配置字段**：
  - 抑制规则名称、启用状态
  - 源告警匹配条件（source_match）：触发抑制的告警
  - 目标告警匹配条件（target_match）：被抑制的告警
  - 相等标签（equal）：源和目标必须相同的标签
- **实现原理**：
  - 当源告警（如集群宕机）触发时
  - 自动抑制目标告警（如该集群下所有服务不可用）
  - 抑制期间目标告警不发送通知，但记录到历史
- **典型场景**：
  - 网络中断抑制该网络下所有主机告警
  - 数据库宕机抑制依赖该库的所有应用告警
- **操作权限**：view, create, edit, delete, toggle

**告警静默** (`monitoring:alert:silence`)
- **核心功能**：在指定时间段内静默特定告警，用于维护窗口或已知问题
- **配置字段**：
  - 静默名称、匹配条件（标签匹配）
  - 静默类型：一次性 / 周期性
  - 时间范围：开始时间、结束时间
  - 匹配类型：全部告警 / 部分匹配
- **实现原理**：
  - 告警进入时先检查是否匹配静默规则
  - 匹配成功的告警标记为 silenced 状态
  - 静默期间不发送通知，但记录到历史
- **典型场景**：
  - 计划内维护期间静默相关告警
  - 已知问题修复期间临时静默
- **操作权限**：view, create, edit, delete, toggle

#### 8.2.5 采集器管理 [新增]
- **权限标识**: `monitoring:collector`
- **页面功能**（参考 HertzBeat Advanced -> Collector）：
  - 表格展示所有 Collector 实例
  - 字段：Collector ID、名称、IP地址、状态、版本、心跳时间、任务数
  - 状态标识：在线(绿)、离线(红)
  - 操作：查看详情、删除
  - 详情页：
    - 基本信息：运行时长、系统负载、内存使用
    - 任务列表：当前分配的所有监控任务

#### 8.2.6 监控简报 [新增]
- **权限标识**: `monitoring:bulletin`
- **页面功能**（参考 HertzBeat Bulletin）：
  - 以简报形式展示监控状态概览
  - 按监控类型分组统计
  - 异常监控高亮显示
  - 支持导出简报为 PDF/图片
  - 定时生成简报并发送邮件

#### 8.2.7 标签管理 [新增]
- **权限标识**: `monitoring:labels`
- **页面功能**（参考 HertzBeat Advanced -> Labels）：
  - 管理监控对象的标签
  - 字段：标签名、标签值、颜色、关联监控数
  - 操作：新增、编辑、删除
  - 标签用于：
    - 监控筛选和分组
    - 告警路由
    - 权限控制（按标签隔离）
  - 批量打标签/移除标签

#### 8.2.8 状态页 [新增]
- **权限标识**: `monitoring:status`
- **页面功能**（参考 HertzBeat Advanced -> Status）：
  - 创建对外公开的服务状态页
  - 配置展示哪些监控的状态
  - 自定义状态页样式（Logo、标题、主题色）
  - 历史事件时间线展示
  - 订阅状态变更通知
  - 公开访问链接管理

#### 8.2.9 监控大盘 [新增]
- **权限标识**: `monitoring:dashboard`
- **页面功能**:
  - 全局概览卡片：监控总数、正常数、异常数、告警数
  - 图表区域（参考 HertzBeat Dashboard）：
    - 监控状态分布饼图
    - 告警趋势折线图（近24小时）
    - 采集成功率趋势
    - Top10 告警监控排行
  - 实时告警列表（最近5条）
  - 快捷入口：快速添加监控、查看告警

### 8.3 权限设计

| 菜单 | 权限标识 | 操作权限 |
|------|----------|----------|
| 监控大盘 | `monitoring:dashboard` | view |
| 监控列表 | `monitoring:list` | view, create, edit, delete, enable, disable |
| 监控简报 | `monitoring:bulletin` | view, export |
| 监控模板 | `monitoring:template` | view, create, edit, delete |
| 告警中心 | `monitoring:alert:center` | view, claim, close |
| 告警配置 | `monitoring:alert:setting` | view, create, edit, delete, enable, disable |
| 外部告警接入 | `monitoring:alert:integration` | view, create, edit, delete, test, toggle |
| 告警分组 | `monitoring:alert:group` | view, create, edit, delete, toggle |
| 告警抑制 | `monitoring:alert:inhibit` | view, create, edit, delete, toggle |
| 告警静默 | `monitoring:alert:silence` | view, create, edit, delete, toggle |
| 通知规则 | `monitoring:alert:notice` | view, create, edit, delete, test, toggle |
| 通知渠道 | `monitoring:alert:notice` | view, create, edit, delete, test, toggle |
| 采集器管理 | `monitoring:collector` | view, delete |
| 标签管理 | `monitoring:labels` | view, create, edit, delete |
| 状态页 | `monitoring:status` | view, create, edit, delete |

### 8.4 页面风格规范

- **UI 框架**: Ant Design Vue 4.x（与现有系统一致）
- **布局**: 列表页使用 Card + Table，编辑页使用 Form + Card
- **按钮**: 主操作使用 `type="primary"`，危险操作使用 `danger`
- **表单**: 参考 HertzBeat 的表单设计，标签右对齐，输入框宽度统一
- **表格**: 支持分页、排序、筛选，操作列固定右侧
- **颜色**: 状态使用 Tag 组件，告警级别使用预设颜色
- **图标**: 使用 `@ant-design/icons-vue`，与现有菜单风格一致

### 8.5 与现有系统集成

- **角色管理**: 在角色管理页面的权限树中新增监控管理权限节点
- **菜单管理**: 自动注册到菜单表，支持动态显示/隐藏
- **操作日志**: 关键操作（增删改）记录到操作日志


## 9. 成功标准

- [ ] 监控：支持 1000+ 监控点，采集成功率 > 99%
- [ ] 告警：延迟 < 30秒，收敛率 > 80%，无误报
- [ ] 展示：Dashboard 加载 < 3秒，支持实时刷新
- [ ] 前端：所有菜单与角色权限正确对接，页面风格统一

## 7. 迁移阶段

- [ ] 阶段 1：准备（1-2天）
  - 清理 Python 代码
  - 确保现有功能正常
- [ ] 阶段 2：Go Manager（1周）
  - 实现任务调度（一致性哈希）
  - 实现告警计算（JEXL 表达式）
  - 实现告警收敛（分组、抑制、静默）
  - 实现数据分发（Data Dispatch）
  - 实现实时数据存储（Redis）
  - 实现历史数据存储（VictoriaMetrics）
  - 实现数据查询 API（PromQL）
- [ ] 阶段 3：Go Collector（3-5天）
  - 完善 gRPC 通信
  - 测试各协议采集器
- [ ] 阶段 4：Python 对接（3-5天）
  - 调用 Manager API
  - 告警展示页面
- [ ] 阶段 5：测试优化（1周）
  - 端到端测试
  - 告警功能测试
  - 性能测试

## 10. 可执行开发任务清单（Backlog）

以下任务按“可直接进入迭代”粒度拆分，默认优先级 `P0 > P1 > P2`。

### 10.1 里程碑 M0：基线与契约冻结（2-3天）

- [x] `M0-01` [P0] 冻结跨服务 API 契约（Python Web <-> Go Manager）
  - 交付物：`docs/api/manager-openapi.yaml`、错误码表、鉴权方案
  - 验收标准：创建监控、更新监控、查询监控、查询告警、告警确认接口可联调
- [x] `M0-02` [P0] 冻结 gRPC 契约（Go Manager <-> Go Collector）
  - 交付物：`proto/collector.proto`、版本策略（向后兼容字段规则）
  - 验收标准：任务下发、心跳、采集上报、回执状态全覆盖
  - 产物路径：`collector-go/proto/collector.proto`、`docs/api/collector-grpc-versioning.md`
- [x] `M0-03` [P0] 明确统一指标口径与标签规范
  - 交付物：指标命名规范文档、标签白名单/黑名单、高基数标签限制策略
  - 验收标准：示例采集数据能通过校验脚本
  - 产物路径：`docs/api/metric-label-spec.md`、`docs/api/metric-contract-sample.json`、`tools/monitoring/validate_metric_contract.py`
- [x] `M0-04` [P1] 环境基线与配置模板
  - 交付物：`docker-compose`（Redis + VictoriaMetrics）、`.env.example`
  - 验收标准：本地一键启动，健康检查全部通过
  - 产物路径：`docker-compose.yml`、`.env.example`、`docs/api/m0-env-baseline.md`
  - 当前状态：已验收通过（Redis healthy，VictoriaMetrics `/health` 返回 `OK`）

### 10.2 里程碑 M1：Go Manager 核心能力（1-2周）

- [x] `M1-01` [P0] 监控任务模型与生命周期管理
  - 交付物：任务 CRUD、启停、版本号（乐观锁）机制
  - 验收标准：并发更新不丢失；停用任务 10 秒内不再下发
  - 产物路径：`manager-go/internal/store/monitor_store.go`、`manager-go/internal/httpapi/server.go`、`manager-go/internal/scheduler/dispatch_scheduler.go`
  - 验收依据：`manager-go/internal/store/monitor_store_test.go`、`manager-go/internal/scheduler/dispatch_scheduler_test.go`
- [x] `M1-02` [P0] Collector 注册与一致性哈希分配
  - 交付物：Collector 注册表、节点上下线重平衡
  - 验收标准：任一 Collector 下线后，任务在 30 秒内完成再分配
  - 产物路径：`manager-go/internal/collector/registry.go`
  - 验收依据：`manager-go/internal/collector/registry_test.go`
- [x] `M1-03` [P0] 数据分发双写（Redis + VictoriaMetrics）
  - 交付物：写入 pipeline、失败重试、幂等键
  - 验收标准：双写成功率 >= 99.9%，单路失败不阻塞另一条链路
  - 产物路径：`manager-go/internal/dispatch/dispatcher.go`、`manager-go/internal/dispatch/pipeline.go`、`manager-go/internal/dispatch/redis_sink.go`、`manager-go/internal/dispatch/vm_sink.go`
  - 验收依据：`manager-go/internal/dispatch/dispatcher_test.go`（重试、幂等、单路失败隔离）
- [x] `M1-04` [P0] 实时告警计算引擎（表达式 + 持续时间）
  - 交付物：规则解析、阈值判断、去抖动窗口
  - 验收标准：规则单测覆盖关键算子，误触发率低于基线
  - 产物路径：`manager-go/internal/alert/engine.go`、`manager-go/cmd/manager/main.go`
  - 验收依据：`manager-go/internal/alert/engine_test.go`（比较算子、`&&/||`、持续时间去抖）
  - 实现说明：当前为 JEXL 子集实现（比较与逻辑运算），用于实时告警计算主链路
- [x] `M1-05` [P1] 周期告警计算（基于 VM 查询）
  - 交付物：周期任务调度器、聚合查询执行器
  - 验收标准：5 分钟窗口类规则可稳定触发
  - 产物路径：`manager-go/internal/alert/periodic.go`、`manager-go/internal/alert/vm_query.go`、`manager-go/cmd/manager/main.go`
  - 验收依据：`manager-go/internal/alert/periodic_test.go`、`manager-go/internal/alert/vm_query_test.go`
- [x] `M1-06` [P0] 告警收敛（分组/抑制/静默）
  - 交付物：收敛策略配置与执行链路
  - 验收标准：压测场景下告警条数压缩率 >= 80%
  - 产物路径：`manager-go/internal/alert/reduce.go`、`manager-go/cmd/manager/main.go`
  - 验收依据：`manager-go/internal/alert/reduce_test.go`
- [x] `M1-07` [P0] 告警异步队列与 Worker
  - 交付物：`alert_queue`、`notify_queue`、`retry_queue`、退避重试
  - 验收标准：通知失败可重试，最大重试后进入死信/人工处理
  - 产物路径：`manager-go/internal/alert/async.go`、`manager-go/cmd/manager/main.go`
  - 验收依据：`manager-go/internal/alert/async_test.go`
- [x] `M1-08` [P1] 通知渠道插件（Webhook/邮件/企业微信）
  - 交付物：统一发送接口、模板渲染器、测试发送 API
  - 验收标准：三类渠道可用，模板变量替换正确
  - 产物路径：`manager-go/internal/notify/service.go`、`manager-go/internal/notify/template.go`、`manager-go/internal/httpapi/server.go`
  - 验收依据：`manager-go/internal/notify/service_test.go`、`manager-go/internal/httpapi/server_test.go`

#### 10.2.1 M1 收尾执行计划（从“模块完成”到“端到端完成”）

- 目标：完成 `用户 -> Python Web -> Go Manager -> Go Collector -> 数据/告警/通知` 闭环。
- 当前判定（2026-03-07）：
  - `M1-01`：已完成并可用（任务 CRUD/启停/版本锁已在主链路生效）。
  - `M1-02`：已接入主链路（Collector 注册、心跳、过期剔除与一致性哈希分配已生效）。
  - `M1-03`：已接入主链路（新增 metrics/reports 上报入口，collector 上报为主输入）。
  - `M1-04/M1-05/M1-06`：核心能力已接入主链路。
  - `M1-07`：已补齐死信查询与人工重试闭环。
  - `M1-08`：已切换告警主发送链路到 `notify.Service`（支持多渠道配置）。

##### A. 收尾任务清单（建议 5-7 天）

- [x] `M1-R1` [P0] 接入 Collector 注册与一致性哈希分配到调度主链路
  - 范围：在 Manager 启动流程接入 `collector.Registry`，调度时按 monitor 选择 collector 并下发任务。
  - 产物：`manager-go/cmd/manager/main.go`、`manager-go/internal/collector/*`、相关 transport/handler。
  - 验收：任一 collector 下线后，30 秒内任务再分配成功。
  - 完成说明（2026-03-07）：已接入注册/心跳/过期剔除、任务一致性哈希分配与任务拉取接口（`/api/v1/collectors/*`）。

- [x] `M1-R2` [P0] 接入 Collector 上报数据作为双写主输入
  - 范围：补齐 Manager 接收 collector 指标入口（gRPC/HTTP 按既有契约）；dispatch pipeline 以上报点为主。
  - 产物：Manager 接收端实现 + `dispatch` 接线改造 + 配置项。
  - 验收：Redis/VM 双写成功率达标，单路失败不阻塞另一条链路。
  - 完成说明（2026-03-07）：新增指标上报入口 `POST /api/v1/metrics` 与 `POST /api/v1/collectors/{id}/reports`，已接入 dispatch pipeline；当存在在线 collector 时，Manager 不再默认生成本地点作为主输入。

- [x] `M1-R3` [P0] 告警发送主链路切换到通知插件
  - 范围：用 `notify.Service` 实现 Sender，替换 `logSender`；支持 webhook/email/wecom 渠道选择与模板渲染。
  - 产物：`manager-go/cmd/manager/main.go`、`manager-go/internal/notify/*`、渠道配置模型。
  - 验收：真实告警触发后可成功发送到三类渠道（至少各 1 条）。
  - 完成说明（2026-03-07）：告警异步队列已接入 `notify.Service` 发送器，支持通过环境变量配置 `webhook/email/wecom` 多渠道、模板与标题。

- [x] `M1-R4` [P1] 死信与人工处理闭环
  - 范围：通知超过最大重试后写入死信存储；提供查询/重试接口。
  - 产物：死信存储模型、API、回放逻辑、审计字段。
  - 验收：失败通知可查询、可人工重放、可审计追踪。
  - 完成说明（2026-03-07）：新增内存死信存储 `DeadLetterStore`，队列失败自动落死信；新增 `GET /api/v1/dead-letters` 与 `POST /api/v1/dead-letters/{id}/retry`。

- [x] `M1-R5` [P1] 联调与回归测试补齐
  - 范围：补端到端测试覆盖创建监控、分配 collector、采集上报、告警触发、通知发送。
  - 产物：集成测试脚本与 CI 任务。
  - 验收：关键链路 E2E 全通过，异常路径（collector 下线、通知失败）可复现并恢复。
  - 完成说明（2026-03-07）：补充 `manager-go/internal/httpapi/server_test.go` 覆盖 collector 注册/分配、metrics 上报、alerts 与 dead-letters API；`manager-go` 全量单测通过。

##### B. 完成口径（M1 统一验收标准）

- Python Web 创建 monitor 后，Manager 可见且已分配到在线 Collector。
- Collector 实际采集数据可在 VM 查询到，且 Redis 存在对应消息。
- 实时/周期告警触发后 10 秒内进入通知发送链路。
- 通知失败重试后进入死信，可人工重试成功。

### 10.3 里程碑 M2：Go Collector 能力完善（1周）

- [x] `M2-01` [P0] 本地调度器（时间轮）与任务执行框架
  - 交付物：任务装载/卸载、调度精度监控
  - 验收标准：1000 任务场景下调度漂移受控
  - 产物路径：`collector-go/internal/scheduler/wheel.go`、`collector-go/internal/dispatcher/dispatcher.go`
  - 验收依据：`collector-go/internal/scheduler/wheel_test.go`、`collector-go/internal/dispatcher/dispatcher_test.go`
- [x] `M2-02` [P0] 协议采集器 MVP（HTTP/ICMP/Linux）
  - 交付物：统一采集结果结构、错误分类
  - 验收标准：核心协议采集通过集成测试
  - 产物路径：`collector-go/internal/protocol/httpcollector/http.go`、`collector-go/internal/protocol/pingcollector/ping.go`、`collector-go/internal/protocol/linuxcollector/linux.go`
  - 验收依据：`collector-go/internal/protocol/httpcollector/http_test.go`、`collector-go/internal/protocol/pingcollector/ping_test.go`、`collector-go/internal/protocol/linuxcollector/linux_test.go`
- [x] `M2-03` [P1] 边缘预计算（简单阈值/状态变化）
  - 交付物：可选预计算开关、摘要上报字段
  - 验收标准：开启后不影响原始指标上报完整性
  - 产物路径：`collector-go/internal/precompute/evaluator.go`、`collector-go/internal/dispatcher/dispatcher.go`、`collector-go/internal/config/config.go`、`collector-go/config/collector.json`
  - 验收依据：`collector-go/internal/precompute/evaluator_test.go`、`collector-go/internal/dispatcher/dispatcher_test.go`
- [x] `M2-04` [P0] 离线缓存与重传机制
  - 交付物：网络抖动缓存队列、恢复后重传
  - 验收标准：短时断网不丢关键采集数据
  - 产物路径：`collector-go/internal/queue/disk.go`、`collector-go/internal/queue/factory.go`、`collector-go/internal/transport/grpc_server.go`、`collector-go/internal/config/config.go`
  - 验收依据：`collector-go/internal/queue/disk_test.go`

#### 10.3.1 M2-03/M2-04 执行方案（已确认）

1. 定义 `M2-03` 预计算协议与配置
   - 目标：明确哪些规则在 Collector 本地计算，以及上报字段格式
   - 计划产物：
     - 预计算配置：开关、规则列表、严重级别
     - 上报字段：`precompute_triggered`、`precompute_summary`（或等价字段）
   - 涉及模块：
     - `collector-go/proto/collector.proto`
     - `collector-go/internal/model/model.go`
     - `collector-go/internal/config/config.go`
     - `collector-go/config/collector.json`
   - 验收标准：
     - 关闭开关时行为与当前一致
     - 开启后上报中可见预计算摘要字段

2. 实现 `M2-03` 本地预计算引擎（轻量规则）
   - 目标：支持简单阈值和状态变化判断，不影响原始采集数据
   - 计划产物：
     - 预计算模块（按 task/metric 规则执行）
     - 与 `dispatcher` 执行链路集成
     - 规则计算异常隔离（不阻断采集）
   - 涉及模块：
     - `collector-go/internal/dispatcher/dispatcher.go`
     - `collector-go/internal/precompute/*`（新增）
   - 验收标准：
     - 命中规则仅附加摘要，不改写原始 `fields`
     - 规则异常时采集和上报仍可继续

3. 定义 `M2-04` 离线缓存与重传机制
   - 目标：Manager 不可达或网络抖动时不丢关键采集结果
   - 计划产物：
     - 离线判定条件
     - 缓存容量上限、TTL、重传顺序
     - 丢弃策略与幂等键策略
   - 涉及模块：
     - `collector-go/internal/config/config.go`
     - `collector-go/config/collector.json`
     - 配套设计说明文档
   - 验收标准：
     - 关键行为均可配置
     - 达到容量上限时有可观测告警和明确退化行为

4. 实现持久化结果队列（磁盘）
   - 目标：提供进程重启可恢复的缓存能力
   - 计划产物：
     - 新增 `disk` backend（append-only + 游标）
     - 接入 `queue.ResultQueue` 工厂
   - 涉及模块：
     - `collector-go/internal/queue/disk.go`（新增）
     - `collector-go/internal/queue/factory.go`
   - 验收标准：
     - 断网期间可持续入队
     - 网络恢复后按顺序重传
     - 重启后仍可继续补发未发送数据

5. 实现传输层重传与确认语义
   - 目标：发送失败不丢弃，支持可控重试与补发
   - 计划产物：
     - gRPC 发送失败重试
     - 发送窗口控制
     - 失败回写缓存队列
   - 涉及模块：
     - `collector-go/internal/transport/grpc_server.go`
   - 验收标准：
     - 连接中断恢复后可补发
     - 重复发送可通过幂等键去重

6. 补齐测试与压测（M2 验收闭环）
   - 目标：将 M2 验收标准转化为可重复执行的测试资产
   - 计划产物：
     - 单测：预计算规则、磁盘队列边界、重传状态机
     - 集成测试：断网 -> 缓存 -> 恢复 -> 补发
     - 压测：1000 任务调度漂移与队列堆积
   - 涉及模块：
     - `collector-go/tests/*`
     - `collector-go/internal/*_test.go`
   - 验收标准：
     - `go test ./...` 通过
     - 新增关键场景测试稳定通过
     - 输出 M2 验收报告（调度、补发、数据完整性）

### 10.4 里程碑 M3：Python Web 与前端对接（1-2周）

- [x] `M3-01` [P0] Python Web 适配 Manager API
  - 交付物：客户端 SDK/Service 层、超时重试、熔断降级
  - 验收标准：原监控管理流程在新后端可闭环
  - 产物路径：`backend/app/services/manager_api_service.py`、`backend/app/routes/monitoring_target.py`、`backend/app/routes/__init__.py`、`backend/config.py`
  - 验收依据：`backend/tests/unit/monitoring/test_manager_api_service.py`
- [x] `M3-02` [P0] 告警中心页面（当前/历史/规则）
  - 交付物：列表、筛选、认领/关闭、WebSocket 实时刷新
  - 验收标准：关键交互可用，权限控制正确
  - 产物路径：`frontend/src/views/monitoring/alert/index.vue`、`frontend/src/api/monitoring.ts`、`frontend/src/router/index.ts`、`frontend/src/layouts/BasicLayout.vue`、`backend/app/routes/monitoring_target.py`、`backend/app/routes/role.py`、`backend/tests/unit/monitoring/test_monitoring_target_routes.py`
  - 验收依据：`backend/tests/unit/monitoring/test_manager_api_service.py`、`backend/tests/unit/monitoring/test_monitoring_target_routes.py` 通过；`frontend` 构建通过（`npm run -s build`）
- [x] `M3-03` [P1] 监控大盘页面
  - 交付物：概览卡片、趋势图、Top10、最近告警
  - 验收标准：默认查询加载时间 < 3 秒
  - 产物路径：`frontend/src/views/monitoring/dashboard/index.vue`、`frontend/src/api/monitoring.ts`、`frontend/src/router/index.ts`、`frontend/src/layouts/BasicLayout.vue`、`backend/app/routes/monitoring_target.py`
  - 验收依据：`backend/tests/unit/monitoring/test_monitoring_target_routes.py` 通过；`frontend` 构建通过（`npm run -s build`）
- [x] `M3-04` [P1] 采集器管理、标签管理、状态页
  - 交付物：对应菜单路由、CRUD、权限点接入
  - 验收标准：角色权限树可准确控制菜单与操作
  - 产物路径：`frontend/src/views/monitoring/collector/index.vue`、`frontend/src/views/monitoring/labels/index.vue`、`frontend/src/views/monitoring/status/index.vue`、`frontend/src/views/monitoring/target/index.vue`、`frontend/src/views/monitoring/bulletin/index.vue`、`frontend/src/views/monitoring/alert/integration.vue`、`frontend/src/views/monitoring/alert/group.vue`、`frontend/src/views/monitoring/alert/inhibit.vue`、`frontend/src/views/monitoring/alert/silence.vue`、`frontend/src/views/monitoring/alert/notice.vue`、`frontend/src/router/index.ts`、`frontend/src/layouts/BasicLayout.vue`、`frontend/src/i18n/zh-CN.ts`、`frontend/src/i18n/en-US.ts`、`backend/app/routes/role.py`、`backend/app/routes/monitoring_target.py`
  - 验收依据：`backend/tests/unit/monitoring/test_monitoring_target_routes.py` 通过（含 dashboard/collector/integration 权限测试）；`frontend` 构建通过（`npm run -s build`）

#### 10.4.1 M3 阶段补充说明（截至 2026-03-08）

- 菜单结构已按第 8 章对齐：`监控大盘/监控列表/监控简报/监控模板/告警中心子菜单/采集器管理/标签管理/状态页`
- 告警中心子模块已拆分独立页面并接入权限：`current/history/rule/integration/group/inhibit/silence/notice-receiver/notice`
- 字段口径已补齐到可用级：监控列表批量操作、采集器详情字段、状态页公开链接与配置字段、通知渠道动态表单、静默时间窗口校验
- 对旧权限做了兼容映射：`monitoring:list` 兼容 `monitoring:target`

#### 10.4.2 M3 阶段详细完成清单（2026-03-08 更新）

**前端页面实现**

| 页面 | 路径 | 状态 | 主要功能 |
|------|------|------|----------|
| 监控大盘 | `frontend/src/views/monitoring/dashboard/index.vue` | ✅ 已完成 | 概览卡片、趋势图、Top10、最近告警 |
| 监控列表 | `frontend/src/views/monitoring/target/index.vue` | ✅ 已完成 | 表格展示、批量操作、筛选搜索、CRUD |
| 监控简报 | `frontend/src/views/monitoring/bulletin/index.vue` | ✅ 已完成 | 状态概览、异常高亮、导出功能 |
| 采集器管理 | `frontend/src/views/monitoring/collector/index.vue` | ✅ 已完成 | 采集器列表、状态显示、详情查看 |
| 标签管理 | `frontend/src/views/monitoring/labels/index.vue` | ✅ 已完成 | 标签CRUD、颜色配置、关联监控数 |
| 状态页 | `frontend/src/views/monitoring/status/index.vue` | ✅ 已完成 | 状态页配置、组件管理、事件时间线 |
| 当前告警 | `frontend/src/views/monitoring/alert/current.vue` | ✅ 已完成 | 未恢复告警列表、认领关闭、WebSocket实时推送 |
| 告警历史 | `frontend/src/views/monitoring/alert/history.vue` | ✅ 已完成 | 历史告警查询、时间筛选、导出功能 |
| 告警配置 | `frontend/src/views/monitoring/alert/setting.vue` | ✅ 已完成 | 告警规则CRUD、JEXL表达式、触发配置 |
| 外部告警接入 | `frontend/src/views/monitoring/alert/integration.vue` | ✅ 已完成 | 多系统接入(Prometheus/Zabbix/SkyWalking/Nagios)、Webhook配置、认证方式 |
| 告警分组 | `frontend/src/views/monitoring/alert/group.vue` | ✅ 已完成 | 分组规则、等待时间、间隔配置 |
| 告警抑制 | `frontend/src/views/monitoring/alert/inhibit.vue` | ✅ 已完成 | 抑制规则、源/目标匹配、相等标签 |
| 告警静默 | `frontend/src/views/monitoring/alert/silence.vue` | ✅ 已完成 | 静默规则、一次性/周期性、时间窗口 |
| 通知渠道 | `frontend/src/views/monitoring/alert/notice-receiver.vue` | ✅ 已完成 | 多渠道配置(邮件/钉钉/企业微信/飞书/Webhook等)、测试发送 |
| 通知规则 | `frontend/src/views/monitoring/alert/notice.vue` | ✅ 已完成 | 通知规则、标签过滤、生效时间、引用通知渠道 |

**后端 API 实现**

| 模块 | 路径 | 状态 | 主要功能 |
|------|------|------|----------|
| Manager API 服务 | `backend/app/services/manager_api_service.py` | ✅ 已完成 | Go Manager 客户端SDK、超时重试、熔断降级 |
| 监控目标路由 | `backend/app/routes/monitoring_target.py` | ✅ 已完成 | 监控CRUD、告警规则、通知规则、采集器、状态页等全量接口 |
| 角色权限路由 | `backend/app/routes/role.py` | ✅ 已完成 | 新增监控相关权限标识 |
| 数据模型 | `backend/app/models/hertzbeat_models.py` | ✅ 已完成 | 23张表SQLAlchemy模型定义、外键约束、索引 |

**数据库表实现（共23张）**

| 类别 | 表名 | 状态 | 说明 |
|------|------|------|------|
| 采集器管理 | `collectors` | ✅ | 采集器注册信息、状态、版本 |
| 采集器管理 | `collector_monitor_binds` | ✅ | 采集器与监控任务分配关系 |
| 监控配置 | `monitors` | ✅ | 监控任务定义、调度策略、状态 |
| 监控配置 | `monitor_params` | ✅ | 监控任务具体参数 |
| 监控配置 | `monitor_binds` | ✅ | 监控对象之间关系绑定 |
| 监控配置 | `monitor_defines` | ✅ | YAML格式监控协议定义 |
| 基础数据 | `tags` | ✅ | 监控标签/标记 |
| 告警配置 | `alert_defines` | ✅ | 告警触发条件、表达式、阈值 |
| 告警配置 | `alert_silences` | ✅ | 静默时间段、匹配规则、周期性配置 |
| 告警配置 | `alert_inhibits` | ✅ | 告警抑制规则 |
| 告警配置 | `alert_groups` | ✅ | 告警分组收敛规则 |
| 告警配置 | `notice_rules` | ✅ | 通知路由规则、标签过滤、生效时间 |
| 告警配置 | `notice_receivers` | ✅ | 通知渠道配置 |
| 告警配置 | `notice_templates` | ✅ | 通知内容模板 |
| 告警配置 | `alert_labels` | ✅ | 告警专用标签 |
| 状态页 | `status_page_orgs` | ✅ | 状态页组织信息、主题配置 |
| 状态页 | `status_page_components` | ✅ | 服务组件定义、状态计算 |
| 状态页 | `status_page_incidents` | ✅ | 故障事件记录、时间线 |
| 运行时数据 | `single_alerts` | ✅ | 实时告警实例 |
| 运行时数据 | `group_alerts` | ✅ | 收敛后的分组告警 |
| 运行时数据 | `alert_history` | ✅ | 已恢复告警历史归档 |
| 运行时数据 | `alert_notifications` | ✅ | 通知发送日志、状态追踪 |
| 数据仓库 | `metrics_history` | ✅ | 时序指标数据 |

**关键功能实现细节**

1. **外部告警接入**
   - 支持系统：Prometheus、Zabbix、SkyWalking、Nagios、自定义Webhook
   - 认证方式：无认证、Token认证(Bearer)、Basic Auth
   - 配置字段：各系统特定字段（如Zabbix版本、Prometheus地址等）
   - 测试功能：根据源系统类型生成对应测试模板

2. **告警规则配置**
   - 规则类型：实时指标告警、周期指标告警、实时日志告警、周期日志告警
   - 表达式：JEXL表达式支持（实时）、PromQL/SQL（周期）
   - 触发配置：连续触发次数、告警级别、标签、注释
   - 消息模板：支持变量替换

3. **告警收敛**
   - 分组收敛：按标签分组、等待时间、间隔配置
   - 抑制收敛：源/目标匹配、相等标签
   - 静默收敛：一次性/周期性、时间窗口、标签匹配

4. **通知配置**
   - 接收者类型：用户、用户组
   - 通知类型：Webhook、邮件、短信、企业微信、钉钉、飞书
   - 过滤方式：全部告警、按标签过滤
   - 生效时间：星期选择、时间段配置
   - 通知模板：支持模板选择

5. **权限控制**
   - 菜单权限：所有监控菜单已接入角色权限系统
   - 操作权限：view/create/edit/delete/toggle/test/export等细粒度控制
   - 权限标识：`monitoring:dashboard/list/bulletin/template/alert:*`等

### 10.5 里程碑 M4：质量与上线（1周）

- [ ] `M4-01` [P0] 端到端回归（创建监控 -> 采集 -> 告警 -> 通知 -> 恢复）
  - 交付物：E2E 测试用例集与报告
  - 验收标准：主链路通过率 100%
- [ ] `M4-02` [P0] 性能压测（1000+ 监控点）
  - 交付物：压测脚本、指标看板、瓶颈分析
  - 验收标准：满足“成功标准”中的监控/告警指标
- [ ] `M4-03` [P0] 灰度发布与回滚预案
  - 交付物：灰度开关、回滚手册、演练记录
  - 验收标准：15 分钟内可切回旧链路
- [ ] `M4-04` [P1] 运行手册与值班流程
  - 交付物：告警分级、值班、故障 SOP
  - 验收标准：值班人员可独立完成常见故障处置

### 10.6 跨阶段通用任务（持续进行）

- [ ] `X-01` [P0] 可观测性：日志、指标、追踪（Manager/Collector/Web）
- [ ] `X-02` [P0] 安全：API 鉴权、Webhook 签名校验、敏感信息加密
- [ ] `X-03` [P1] 测试基线：单测、集成测试、契约测试、回归流水线
- [ ] `X-04` [P1] 数据治理：TTL、归档、删除策略和审计记录

### 10.7 当前状态汇总（截至 2026-03-08）

**已完成**

- `M0`：契约冻结、指标口径、环境基线
- `M1`：Manager 核心能力（任务调度、双写、告警计算、收敛、异步通知）
- `M2`：Collector 核心能力（调度、采集、预计算、离线缓存）
- `M3`：Python 对接 + 前端核心页面（含监控大盘、监控菜单与权限对齐、告警中心子模块拆分）
  - ✅ 14个前端页面全部实现
  - ✅ 后端API全量实现（monitoring_target.py、role.py）
  - ✅ 23张数据库表模型定义完成
  - ✅ 外部告警接入（Prometheus/Zabbix/SkyWalking/Nagios）
  - ✅ 告警规则配置（JEXL表达式、多规则类型）
  - ✅ 告警收敛（分组/抑制/静默）
  - ✅ 通知配置（标签过滤、生效时间、模板选择）
  - ✅ 权限控制（菜单权限、操作权限）

**剩余工作**

- `M4-01` 端到端回归：补齐创建监控 -> 采集 -> 告警 -> 通知 -> 恢复完整链路用例与报告
- `M4-02` 性能压测：1000+ 监控点压测脚本、指标看板、瓶颈分析与达标确认
- `M4-03` 灰度发布与回滚预案：开关、回滚手册、演练记录
- `M4-04` 运行手册与值班流程：告警分级、值班流程、故障 SOP
- `X-01~X-04` 跨阶段持续项：可观测性、安全、测试基线、数据治理

## 11. 计划审查（问题、影响、修正）

### 11.1 关键问题（按优先级）

1. `P0` API/gRPC 契约未冻结，存在并行开发返工风险
   - 影响：Web、Manager、Collector 三方联调容易反复改接口
   - 修正：先完成 `M0-01`、`M0-02`，未冻结前不进入大规模功能开发
2. `P0` 时序数据口径虽有规范，但缺少“校验机制”
   - 影响：同一指标可能出现命名/标签漂移，导致查询和告警规则失效
   - 修正：增加采集结果校验器与 CI 检查（命名、必备标签、高基数限制）
3. `P0` 双写链路缺少幂等与失败隔离细则
   - 影响：高峰时可能出现重复写入、部分写入或链路阻塞
   - 修正：引入幂等键、异步缓冲、单路失败降级与补偿机制
4. `P1` 告警计算表达式使用 JEXL，但未定义 Go 侧实现方案
   - 影响：规则语义可能与预期不一致，迁移时规则不可复用
   - 修正：明确表达式子集，提供兼容层或转换器，并附规则回归测试
5. `P1` 通知系统有渠道清单，但缺少限流/熔断/回执统一模型
   - 影响：下游抖动时通知风暴、重复发送、状态不可追踪
   - 修正：统一通知状态机（待发送/发送中/成功/失败/放弃）与限流策略
6. `P1` 迁移阶段时间估算偏乐观（尤其 Manager + 告警 + 双存储）
   - 影响：里程碑延期，前后端联调窗口被压缩
   - 修正：按 M0~M4 重排里程碑并设置“契约冻结”与“压测达标”两个硬门槛
7. `P2` 文档章节编号存在跳跃（先 9 后 7）
   - 影响：评审与跟踪引用不便
   - 修正：下一次文档整理时统一重排章节编号

### 11.2 建议的执行门槛（Go/No-Go）

- 进入 M1 前：API + gRPC 契约冻结并评审通过
- 进入 M3 前：M1/M2 主链路联调通过，双写与告警核心链路稳定
- 进入上线前：通过 1000+ 监控点压测且满足"成功标准"

## 12. 数据模型设计

### 12.1 表清单概览（共 25 张表）

| 序号 | 表名 | 中文名 | 类别 | 说明 |
|------|------|--------|------|------|
| 1 | `collectors` | 采集器节点 | 采集器管理 | 采集器注册信息、状态、版本 |
| 2 | `monitors` | 监控任务 | 监控配置 | 监控目标定义、调度策略、状态 |
| 3 | `monitor_params` | 监控参数 | 监控配置 | 监控任务的具体参数（端口、凭证等） |
| 4 | `monitor_binds` | 监控绑定 | 监控配置 | 监控对象之间的关系绑定 |
| 5 | `collector_monitor_binds` | 采集器任务分配 | 采集器管理 | 采集器与监控任务的分配关系 |
| 6 | `monitor_defines` | 监控模板 | 监控配置 | YAML 格式的监控协议定义 |
| 7 | `tags` | 标签 | 基础数据 | 监控标签/标记，支持自动/手动/系统预设 |
| 8 | `alert_defines` | 告警规则 | 告警配置 | 告警触发条件、表达式、阈值定义 |
| 9 | `alert_silences` | 告警静默 | 告警配置 | 静默时间段、匹配规则 |
| 10 | `alert_inhibits` | 告警抑制 | 告警配置 | 告警抑制规则（高优先级抑制低优先级） |
| 11 | `alert_groups` | 告警分组 | 告警配置 | 告警分组收敛规则 |
| 12 | `notice_rules` | 通知规则 | 告警配置 | 告警通知路由规则 |
| 13 | `notice_receivers` | 通知接收人 | 告警配置 | 通知渠道配置（邮件、Webhook、IM 等） |
| 14 | `notice_templates` | 通知模板 | 告警配置 | 通知内容模板（支持 Freemarker） |
| 15 | `labels` | 告警标签 | 告警配置 | 告警专用标签 |
| 16 | `status_page_orgs` | 状态页组织 | 状态页 | 状态页组织信息、主题配置 |
| 17 | `status_page_components` | 状态页组件 | 状态页 | 服务组件定义、状态计算方式 |
| 18 | `status_page_incidents` | 状态页事件 | 状态页 | 故障事件记录、时间线 |
| 19 | `single_alerts` | 单条告警 | 运行时数据 | 实时告警实例（firing/resolved） |
| 20 | `group_alerts` | 分组告警 | 运行时数据 | 收敛后的分组告警 |
| 21 | `alert_history` | 告警历史 | 运行时数据 | 已恢复告警的历史归档 |
| 22 | `alert_notifications` | 告警通知记录 | 运行时数据 | 通知发送日志、状态追踪 |
| 23 | `metrics_history` | 指标历史 | 数据仓库 | 时序指标数据（VictoriaMetrics 补充） |

### 12.2 表分类说明

#### 配置类表（13 张）
存储系统配置、规则定义，变更频率低：
- **采集器管理**: `collectors`, `collector_monitor_binds`
- **监控配置**: `monitors`, `monitor_params`, `monitor_binds`, `monitor_defines`
- **告警配置**: `alert_defines`, `alert_silences`, `alert_inhibits`, `alert_groups`, `notice_rules`, `notice_receivers`, `notice_templates`
- **基础数据**: `tags`

#### 状态页类表（3 张）
存储状态页相关配置：
- `status_page_orgs`, `status_page_components`, `status_page_incidents`

#### 运行时数据表（4 张）
存储告警运行时数据，生命周期短，数据量大：
- `single_alerts`, `group_alerts`, `alert_history`, `alert_notifications`

#### 数据仓库表（1 张）
存储时序指标数据：
- `metrics_history`

### 12.3 核心关系说明

```
监控任务流:
  monitors → monitor_params (1:N)
  monitors → collector_monitor_binds → collectors (N:M)

告警处理流:
  alert_defines → single_alerts → alert_groups → notice_rules
                                          ↓
                              notice_receivers / notice_templates

状态页流:
  status_page_orgs → status_page_components (1:N)
                   → status_page_incidents
```

## 13. gRPC 连接架构（Manager ↔ Collector）

### 13.1 架构设计

Manager 与 Collector 之间采用 **gRPC 双向流（Bidirectional Streaming）** 进行通信，Manager 作为 gRPC Client，Collector 作为 gRPC Server。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Manager ↔ Collector gRPC 连接架构                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────────┐              ┌─────────────────────┐          │
│   │    manager-go       │              │    collector-go     │          │
│   │   (gRPC Client)     │              │   (gRPC Server)     │          │
│   │                     │              │                     │          │
│   │  ┌───────────────┐  │   gRPC       │  ┌───────────────┐  │          │
│   │  │ ClientManager │  │◄────────────►│  │  GRPCServer   │  │          │
│   │  │               │  │ 双向流        │  │               │  │          │
│   │  │ • 连接池管理   │  │              │  │ • 任务接收     │  │          │
│   │  │ • 心跳检测     │  │              │  │ • 结果上报     │  │          │
│   │  │ • 断线重连     │  │              │  │ • 心跳响应     │  │          │
│   │  └───────────────┘  │              │  └───────────────┘  │          │
│   │         │           │              │         │           │          │
│   │         ▼           │              │         ▼           │          │
│   │  ┌───────────────┐  │              │  ┌───────────────┐  │          │
│   │  │ TaskScheduler │  │              │  │  TimeWheel    │  │          │
│   │  │               │  │              │  │   Scheduler   │  │          │
│   │  │ • 任务下发     │  │              │  │               │  │          │
│   │  │ • 批量调度     │  │              │  │ • 本地调度     │  │          │
│   │  │ • 负载均衡     │  │              │  │ • 定时执行     │  │          │
│   │  └───────────────┘  │              │  └───────────────┘  │          │
│   │                     │              │                     │          │
│   └─────────────────────┘              └─────────────────────┘          │
│                                                                          │
│   连接建立流程:                                                           │
│   1. Manager 调用 grpc.Dial() 建立 TCP 连接                               │
│   2. Manager 调用 Connect() 创建双向流                                    │
│   3. Collector 接收连接，启动接收协程                                     │
│   4. Manager 启动心跳协程和接收协程                                        │
│   5. 连接建立完成，可以双向通信                                            │
│                                                                          │
│   消息流向:                                                               │
│   • Manager → Collector: 任务下发 (UpsertTask/DeleteTask/Heartbeat)       │
│   • Collector → Manager: 结果上报 (CollectRep/CommandAck/Heartbeat)       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 13.2 连接状态管理

```
┌─────────────────────────────────────────────────────────────────┐
│                      连接状态转换图                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐                                               │
│   │  离线状态   │◄─────────────────────────────────────────┐    │
│   │ (Offline)   │                                          │    │
│   └──────┬──────┘                                          │    │
│          │ Connect()                                       │    │
│          ▼                                                │    │
│   ┌─────────────┐     连接成功      ┌─────────────┐        │    │
│   │  连接中...  │ ─────────────────►│   在线状态   │        │    │
│   │(Connecting)│                   │ (Connected) │        │    │
│   └─────────────┘                   └──────┬──────┘        │    │
│                                            │               │    │
│                                            │ 心跳超时/      │    │
│                                            │ 网络异常        │    │
│                                            ▼               │    │
│                                     ┌─────────────┐        │    │
│                                     │  重连中...   │────────┘    │
│                                     │(Reconnecting)│ 超过最大重试 │
│                                     └─────────────┘             │
│                                                                  │
│   状态说明:                                                       │
│   • Offline: 初始状态或超过最大重试次数                            │
│   • Connecting: 正在建立 gRPC 连接                                │
│   • Connected: 连接正常，可以收发消息                              │
│   • Reconnecting: 检测到断线，正在尝试重连                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 13.3 心跳机制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `heartbeat_interval` | 5s | 心跳发送间隔 |
| `heartbeat_timeout` | 15s | 心跳超时时间（3倍间隔） |
| `reconnect_backoff` | 5s | 重连退避时间 |
| `max_reconnect_attempts` | 10 | 最大重连次数 |

**心跳流程**:
1. Manager 每 5 秒发送一次 Heartbeat 消息
2. Collector 收到后可以选择性回复（可选优化）
3. 如果 Manager 连续 3 次未收到响应，判定为断线
4. 触发重连流程

### 13.4 任务下发流程

```
用户创建监控 ──▶ Python Web 保存到 DB
                      │
                      ▼
              调用 Manager API
                      │
                      ▼
              Manager 选择 Collector
                      │
                      ▼
              构建 CollectTask
                      │
                      ▼
              gRPC stream.Send(CollectorFrame)
                      │
                      ▼
              Collector 接收并注册到时间轮
                      │
                      ▼
              Collector 返回 CommandAck
```

### 13.5 结果上报流程

```
Collector 时间轮触发采集
        │
        ▼
执行采集任务
        │
        ▼
采集结果入队
        │
        ▼
批量上报器聚合结果
        │
        ▼
gRPC stream.Send(ManagerFrame)
        │
        ▼
Manager 接收并处理
        │
        ├──▶ 写入 Redis（实时数据）
        ├──▶ 写入 VictoriaMetrics（历史数据）
        └──▶ 触发告警计算
```

### 13.6 批量上报机制

**设计目标**: 减少网络往返，提高吞吐量

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `batch_size` | 100 | 批量大小 |
| `batch_interval` | 1s | 批量超时时间 |
| `queue_size` | 10000 | 结果队列大小 |

**批量策略**:
1. 采集结果先进入内存队列
2. 达到 batch_size 立即发送
3. 或等待 batch_interval 超时后发送
4. 队列满时丢弃最旧数据（避免 OOM）

### 13.7 文件位置

| 组件 | 文件路径 | 说明 |
|------|----------|------|
| Proto | `manager-go/proto/collector.proto` | gRPC 协议定义 |
| Proto | `collector-go/proto/collector.proto` | gRPC 协议定义（同源） |
| Manager Client | `manager-go/internal/collector/client.go` | 单连接管理 |
| Manager Manager | `manager-go/internal/collector/manager.go` | 连接池管理 |
| Manager Scheduler | `manager-go/internal/collector/scheduler.go` | 任务调度 |
| Manager Store | `manager-go/internal/store/collector_store.go` | Collector 数据持久化 |
| Collector Server | `collector-go/internal/transport/grpc_server.go` | gRPC Server |
| Collector Batch | `collector-go/internal/transport/batch_reporter.go` | 批量上报 |

### 13.8 Collector 状态管理

#### 13.8.1 状态定义

参考 HertzBeat 设计，Collector 状态存储在 `collectors` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER | 主键，自增 |
| `name` | VARCHAR(100) | Collector 唯一标识名 |
| `ip` | VARCHAR(100) | Collector IP 地址 |
| `version` | VARCHAR(50) | Collector 版本号 |
| `status` | TINYINT | 0-online, 1-offline |
| `mode` | VARCHAR(20) | public/private |
| `creator` | VARCHAR(100) | 创建者 |
| `modifier` | VARCHAR(100) | 修改者 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

#### 13.8.2 状态流转

```
Collector 注册
      │
      ▼
┌─────────────┐     连接成功      ┌─────────────┐
│   离线状态   │ ───────────────► │   在线状态   │
│  (status=1) │                  │  (status=0) │
└─────────────┘                  └──────┬──────┘
     ▲                                  │
     │                                  │ 心跳超时/断线
     │         重连成功                  ▼
     └────────────────────────────┌─────────────┐
                                  │  重连中...   │
                                  │ (Reconnect) │
                                  └─────────────┘
```

#### 13.8.3 状态持久化流程

1. **Collector 注册时**:
   - Manager 接收注册请求
   - 解析 IP 地址（从 addr 中提取）
   - 写入 `collectors` 表（CreateOrUpdate）
   - 初始状态为 `offline`

2. **连接状态变更时**:
   - 连接成功 → 更新 `status=0` (online)
   - 断线/重连 → 更新 `status=1` (offline)

3. **Python Web 查询时**:
   - 调用 Manager API `/api/v1/collectors`
   - Manager 从数据库查询 `collectors` 表
   - 返回完整 Collector 信息（含状态、IP、版本等）

#### 13.8.4 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/collectors` | GET | 获取 Collector 列表 |
| `/api/v1/collectors` | POST | 注册 Collector |
| `/api/v1/collectors/<id>` | DELETE | 注销 Collector |
| `/api/v1/collectors/<id>/offline` | POST | 下线 Collector（踢出） |
| `/api/v1/collectors/<id>/monitors` | GET | 获取 Collector 绑定的 Monitor 列表 |

### 13.9 Collector 任务分配

#### 13.9.1 分配策略

支持两种任务分配方式：

1. **自动分配**（默认）
   - 使用一致性哈希算法根据 Monitor ID 选择 Collector
   - 负载均衡，自动分散任务
   - Collector 上下线时自动重新平衡

2. **用户固定指定**
   - 用户为特定 Monitor 指定 Collector
   - 记录在 `collector_monitor_binds` 表，`pinned=1`
   - 指定的 Collector 离线时，任务临时重新分配

#### 13.9.2 任务重新平衡

触发条件：
- Collector 上线/下线
- 用户手动踢出 Collector
- 用户取消固定分配

重新平衡流程：
```
Collector 状态变更
        │
        ▼
  触发 ReBalanceJobs()
        │
        ├──▶ 获取所有在线 Collector
        │
        ├──▶ 获取所有启用的 Monitor
        │
        ├──▶ 获取用户固定绑定 (pinned=1)
        │
        └──▶ 遍历 Monitor 重新分配
                 │
                 ├──▶ 有固定绑定且 Collector 在线 → 保持分配
                 │
                 ├──▶ 有固定绑定但 Collector 离线 → 临时重新分配
                 │
                 └──▶ 无固定绑定 → 一致性哈希自动分配
```

#### 13.9.3 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/monitors/<id>/collector` | POST | 为 Monitor 指定 Collector（固定分配） |
| `/api/v1/monitors/<id>/collector` | DELETE | 取消固定分配，改为自动分配 |

### 12.4 详细表结构

详细字段定义、约束、索引请参考：`docs/api/m0-env-baseline.md`
