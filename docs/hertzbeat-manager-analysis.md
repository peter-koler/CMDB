# HertzBeat Manager 架构分析报告

## 1. 项目概述

HertzBeat Manager 是 HertzBeat 监控系统的管理后端，负责：
- **监控配置管理**：监控任务 CRUD、监控模板管理
- **采集器管理**：Collector 注册、状态管理、任务调度
- **告警管理**：告警规则、告警通知
- **数据管理**：监控数据查询、存储管理
- **用户权限**：认证授权、多租户支持

基于 **Java 17 + Spring Boot 3.x** 构建，采用分层架构设计。

---

## 2. 模块结构

```
hertzbeat-manager/
├── src/main/java/org/apache/hertzbeat/manager/
│   ├── component/          # 业务组件
│   │   ├── listener/       # 事件监听器
│   │   ├── sd/            # 服务发现组件
│   │   ├── status/        # 状态计算组件
│   │   └── validator/     # 参数校验组件
│   ├── config/            # 配置类
│   ├── controller/        # REST API 控制器
│   ├── dao/              # 数据访问层 (JPA Repository)
│   ├── pojo/dto/         # 数据传输对象
│   ├── scheduler/        # 任务调度器
│   │   └── netty/        # Netty 通信服务
│   ├── service/          # 业务服务层
│   │   └── impl/         # 服务实现
│   └── support/          # 异常处理、工具支持
└── src/main/resources/
    ├── application.yml     # 主配置文件
    ├── define/            # YAML 监控模板
    └── db/               # 数据库迁移脚本
```

---

## 3. 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                    Controller 层                        │
│  - REST API 接口定义                                     │
│  - 请求参数校验                                          │
│  - 响应数据封装                                          │
├─────────────────────────────────────────────────────────┤
│                    Service 层                           │
│  - 业务逻辑处理                                          │
│  - 事务管理                                              │
│  - 数据转换                                              │
├─────────────────────────────────────────────────────────┤
│                    DAO 层                               │
│  - 数据库访问 (Spring Data JPA)                         │
│  - 实体映射                                              │
├─────────────────────────────────────────────────────────┤
│                    Component 层                         │
│  - 辅助业务组件                                          │
│  - 事件监听处理                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Manager 内部服务架构

### 4.1 服务总览

Manager 包含以下核心服务模块：

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HertzBeat Manager 服务架构                             │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        业务服务层 (Service)                              │   │
│  │                                                                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │   │
│  │  │ AppService  │ │MonitorService│ │CollectorService│ │AccountService│       │   │
│  │  │  模板管理   │ │ 监控任务管理 │ │ 采集器管理  │ │ 用户认证    │       │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │   │
│  │         │               │               │               │              │   │
│  │  ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐       │   │
│  │  │StatusPage   │ │  Config     │ │   Plugin    │ │   Label     │       │   │
│  │  │  状态页     │ │  配置管理   │ │   插件      │ │   标签      │       │   │
│  │  │  Service    │ │  Service    │ │  Service    │ │  Service    │       │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                            │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐     │
│  │                        调度服务层 (Scheduler)                          │     │
│  │                                                                         │     │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │     │
│  │  │CollectorJob     │    │   Consistent    │    │   ManageServer  │   │     │
│  │  │  Scheduler      │◄──►│     Hash        │    │   (Netty)       │   │     │
│  │  │                 │    │                 │    │                 │   │     │
│  │  │ • 任务分配      │    │ • 负载均衡      │    │ • 长连接管理    │   │     │
│  │  │ • 任务下发      │    │ • 节点管理      │    │ • 消息处理      │   │     │
│  │  │ • 状态管理      │    │                 │    │                 │   │     │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘   │     │
│  │                                                                         │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
│                                    │                                              │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐       │
│  │                        依赖模块 (Modules)                              │       │
│  │                                                                         │       │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │       │
│  │  │   Alerter       │    │   Warehouse     │    │    Common       │   │       │
│  │  │   (告警模块)     │    │  (数据存储)      │    │   (公共库)       │   │       │
│  │  │                 │    │                 │    │                 │   │       │
│  │  │ • 实时告警计算  │    │ • 实时数据存储  │    │ • 实体定义      │   │       │
│  │  │ • 周期告警计算  │    │ • 历史数据存储  │    │ • 消息格式      │   │       │
│  │  │ • 告警通知      │    │ • 数据查询      │    │ • 工具类        │   │       │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘   │       │
│  │                                                                         │       │
│  └─────────────────────────────────────────────────────────────────────────┘       │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 业务服务层 (Service)

| 服务接口 | 实现类 | 核心职责 | 依赖服务 |
|----------|--------|----------|----------|
| **AppService** | AppServiceImpl | 监控模板管理、YAML 解析、模板加载 | MonitorDao, DefineDao, ObjectStoreService |
| **MonitorService** | MonitorServiceImpl | 监控任务 CRUD、参数校验、任务下发 | CollectorJobScheduler, AppService, WarehouseService |
| **CollectorService** | CollectorServiceImpl | 采集器注册、状态管理、负载统计 | CollectorDao, CollectorMonitorBindDao |
| **AccountService** | AccountServiceImpl | 用户认证、权限管理、Token 管理 | Sureness 框架 |
| **StatusPageService** | StatusPageServiceImpl | 状态页组织、组件管理、状态计算 | StatusPageOrgDao, StatusPageComponentDao |
| **BulletinService** | BulletinServiceImpl | 公告发布、公告查询 | BulletinDao |
| **LabelService** | LabelServiceImpl | 标签管理、标签绑定 | LabelDao |
| **PluginService** | PluginServiceImpl | 插件上传、插件加载、插件执行 | PluginRunner |
| **ConfigService** | ConfigServiceImpl | 系统配置管理、配置持久化 | GeneralConfigService |
| **MetricsFavoriteService** | MetricsFavoriteServiceImpl | 指标收藏管理 | MetricsFavoriteDao |
| **ObjectStoreService** | ObsObjectStoreServiceImpl | 对象存储操作 (OBS/S3) | 云厂商 SDK |
| **ImExportService** | Excel/Json/YamlImExportServiceImpl | 监控数据导入导出 | MonitorService |

### 4.3 调度服务层 (Scheduler)

#### 4.3.1 CollectorJobScheduler - 任务调度核心

**职责**：
- **Collector 生命周期管理**：处理 Collector 上线、下线、心跳
- **任务分配**：使用一致性哈希算法分配监控任务到 Collector
- **任务下发**：通过 Netty 下发采集任务到 Collector
- **负载均衡**：Collector 变化时自动重新分配任务

**核心接口** (`CollectJobScheduling`):
```java
public interface CollectJobScheduling {
    // 同步采集（一次性测试）
    List<CollectRep.MetricsData> collectSyncJobData(Job job);
    List<CollectRep.MetricsData> collectSyncJobData(Job job, String collector);
    
    // 异步采集（周期性监控）
    long addAsyncCollectJob(Job job, String collector);
    long updateAsyncCollectJob(Job modifyJob, String collector);
    void cancelAsyncCollectJob(Long jobId);
    
    // 接收采集结果
    void collectSyncJobResponse(List<CollectRep.MetricsData> metricsDataList);
}
```

#### 4.3.2 ConsistentHash - 一致性哈希

**职责**：
- 实现监控任务在多个 Collector 间的均匀分配
- 支持虚拟节点（默认 16 个）提高均衡性
- Collector 上下线时最小化任务迁移

#### 4.3.3 ManageServer - Netty 通信服务

**职责**：
- 监听端口（默认 1158），管理 Collector 长连接
- 处理 Collector 消息：心跳、上线、下线、采集结果
- 维护连接状态，检测离线 Collector

**消息处理器**：

| 处理器 | 消息类型 | 职责 |
|--------|----------|------|
| **HeartbeatProcessor** | HEARTBEAT | 处理 Collector 心跳，更新最后活跃时间 |
| **CollectorOnlineProcessor** | GO_ONLINE | 处理 Collector 上线，注册到数据库 |
| **CollectorOfflineProcessor** | GO_OFFLINE | 处理 Collector 下线，触发告警 |
| **CollectOneTimeDataResponseProcessor** | RESPONSE_ONE_TIME_TASK_DATA | 接收一次性采集结果 |
| **CollectCyclicDataResponseProcessor** | RESPONSE_CYCLIC_TASK_DATA | 接收周期性采集结果，写入 CommonDataQueue |
| **CollectCyclicServiceDiscoveryDataResponseProcessor** | RESPONSE_CYCLIC_TASK_SD_DATA | 接收服务发现数据 |

### 4.4 控制器层 (Controller)

| 控制器 | 路径 | 职责 |
|--------|------|------|
| **AccountController** | `/api/account/auth` | 用户认证、Token 刷新 |
| **AppController** | `/api/apps` | 监控类型/模板管理 |
| **MonitorController** | `/api/monitor` | 单监控任务管理 |
| **MonitorsController** | `/api/monitors` | 批量监控任务管理 |
| **CollectorController** | `/api/collector` | 采集器管理 |
| **MetricsController** | `/api/metrics` | 监控指标数据查询 |
| **SummaryController** | `/api/summary` | 仪表盘统计 |
| **StatusPageController** | `/api/status` | 状态页管理 |
| **BulletinController** | `/api/bulletin` | 公告管理 |
| **LabelController** | `/api/label` | 标签管理 |
| **PluginController** | `/api/plugin` | 插件管理 |
| **GeneralConfigController** | `/api/config` | 系统配置管理 |

**统一响应格式**:
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

### 4.5 数据访问层 (DAO)

| DAO 接口 | 实体类 | 说明 |
|----------|--------|------|
| **MonitorDao** | Monitor | 监控任务表 |
| **CollectorDao** | Collector | 采集器表 |
| **CollectorMonitorBindDao** | CollectorMonitorBind | 采集器-监控绑定关系 |
| **DefineDao** | Define | 监控模板定义表 |
| **ParamDao** | Param | 监控参数表 |
| **ParamDefineDao** | ParamDefine | 参数定义表 |
| **LabelDao** | Label | 标签表 |
| **BulletinDao** | Bulletin | 公告表 |
| **StatusPageOrgDao** | StatusPageOrg | 状态页组织表 |
| **StatusPageComponentDao** | StatusPageComponent | 状态页组件表 |

---

## 5. 服务间数据交互

### 5.1 数据交互总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Manager 内部服务数据交互                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  1. 监控任务创建流程 (MonitorService → CollectorJobScheduler)            │   │
│  │                                                                         │   │
│  │  MonitorController                                                      │   │
│  │       │                                                                 │   │
│  │       ▼                                                                 │   │
│  │  MonitorService.addMonitor()                                            │   │
│  │       │                                                                 │   │
│  │       ├──► 保存数据库 (MonitorDao.save)                                  │   │
│  │       │                                                                 │   │
│  │       ├──► 查询模板 (AppService.getAppDefine)                            │   │
│  │       │         └──► 内存缓存 (ConcurrentHashMap)                        │   │
│  │       │                                                                 │   │
│  │       ├──► 组装 Job (模板 + 参数)                                        │   │
│  │       │                                                                 │   │
│  │       └──► 下发任务 (CollectorJobScheduler.addAsyncCollectJob)           │   │
│  │                     │                                                   │   │
│  │                     ├──► 一致性哈希选择 Collector                         │   │
│  │                     │         (ConsistentHash.getNode)                  │   │
│  │                     │                                                   │   │
│  │                     └──► Netty 发送任务 (ManageServer.sendMsg)           │   │
│  │                                                                 │       │   │
│  │                                                                 ▼       │   │
│  │                                                           Collector     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  2. 采集结果接收流程 (ManageServer → Warehouse/Alerter)                  │   │
│  │                                                                         │   │
│  │  Collector                                                              │   │
│  │       │                                                                 │   │
│  │       └──► Netty 发送采集结果                                            │   │
│  │                     │                                                   │   │
│  │                     ▼                                                   │   │
│  │  ManageServer (Netty Server)                                            │   │
│  │       │                                                                 │   │
│  │       ├──► CollectCyclicDataResponseProcessor                           │   │
│  │       │         │                                                       │   │
│  │       │         ├──► 写入 CommonDataQueue (内存/Kafka/Redis)             │   │
│  │       │         │             │                                         │   │
│  │       │         │             ├──► Alerter (实时告警计算)                │   │
│  │       │         │             │                                         │   │
│  │       │         │             └──► Warehouse (数据存储)                  │   │
│  │       │         │                                                       │   │
│  │       │         └──► 更新监控状态 (MonitorService.updateMonitorStatus)   │   │
│  │       │                                                               │   │
│  │       └──► CollectOneTimeDataResponseProcessor                        │   │
│  │                     │                                                 │   │
│  │                     └──► 同步返回结果 (collectSyncJobResponse)         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  3. 告警处理流程 (Alerter 内部)                                          │   │
│  │                                                                         │   │
│  │  CommonDataQueue                                                        │   │
│  │       │                                                                 │   │
│  │       └──► MetricsRealTimeAlertCalculator                               │   │
│  │                     │                                                   │   │
│  │                     ├──► JEXL 表达式计算                                 │   │
│  │                     │                                                   │   │
│  │                     ├──► 匹配 AlertDefine (告警规则)                     │   │
│  │                     │                                                   │   │
│  │                     └──► 生成 SingleAlert ──► AlarmCommonReduce         │   │
│  │                                                       │                 │   │
│  │                                                       ▼                 │   │
│  │                                           ┌─────────────────────┐      │   │
│  │                                           │   告警收敛处理       │      │   │
│  │                                           │ • AlarmGroupReduce  │      │   │
│  │                                           │ • AlarmInhibitReduce│      │   │
│  │                                           │ • AlarmSilenceReduce│      │   │
│  │                                           └──────────┬──────────┘      │   │
│  │                                                      │                  │   │
│  │                                                      ▼                  │   │
│  │                                           AlertNoticeDispatch           │   │
│  │                                                      │                  │   │
│  │                                                      ▼                  │   │
│  │                                           ┌─────────────────────┐      │   │
│  │                                           │    多渠道通知        │      │   │
│  │                                           │ • Email/DingTalk    │      │   │
│  │                                           │ • WeChat/FeiShu     │      │   │
│  │                                           │ • WebHook/SMS       │      │   │
│  │                                           └─────────────────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  4. 数据存储流程 (Warehouse 内部)                                        │   │
│  │                                                                         │   │
│  │  CommonDataQueue                                                        │   │
│  │       │                                                                 │   │
│  │       └──► DataStorageDispatch                                          │   │
│  │                     │                                                   │   │
│  │                     ├──► RealTimeDataStorage (Memory/Redis)             │   │
│  │                     │         • 保存最新数据                            │   │
│  │                     │         • 支持快速查询                            │   │
│  │                     │                                                   │   │
│  │                     └──► HistoryDataStorage (VictoriaMetrics/InfluxDB)  │   │
│  │                               • 持久化存储                              │   │
│  │                               • 时序分析                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 核心数据流说明

| 数据流 | 起点 | 终点 | 传输方式 | 数据格式 |
|--------|------|------|----------|----------|
| **任务下发** | CollectorJobScheduler | Collector | Netty TCP | Protobuf (Job)
| **采集结果** | Collector | ManageServer | Netty TCP | Protobuf (MetricsData)
| **数据分发** | ManageServer | CommonDataQueue | 内存/队列 | MetricsData 对象
| **告警计算** | CommonDataQueue | Alerter | 队列消费 | MetricsData 对象
| **数据存储** | CommonDataQueue | Warehouse | 队列消费 | MetricsData 对象
| **模板查询** | MonitorService | AppService | 方法调用 | Job 对象
| **状态更新** | ResponseProcessor | MonitorService | 方法调用 | Status 对象

### 5.3 服务依赖关系

```
MonitorService
    ├──► AppService (查询模板)
    ├──► CollectorJobScheduler (下发任务)
    ├──► WarehouseService (查询数据)
    └──► MonitorDao (数据持久化)

CollectorJobScheduler
    ├──► ConsistentHash (负载均衡)
    ├──► ManageServer (网络通信)
    ├──► CollectorDao (采集器数据)
    └──► AppService (模板数据)

ManageServer
    ├──► CollectorJobScheduler (回调)
    ├──► MonitorService (状态更新)
    └──► CommonDataQueue (数据写入)

AppService
    ├──► DefineDao (模板定义)
    ├──► ObjectStoreService (对象存储)
    └──► 内存缓存 (ConcurrentHashMap)
```

---

## 6. 监控模板系统

### 6.1 模板加载

**AppServiceImpl** (`service/impl/AppServiceImpl.java`)

- 实现 `InitializingBean`，启动时加载模板
- 支持多存储源：
  - JAR 内置模板 (`define/*.yml`)
  - 本地文件系统
  - 数据库 (`Define` 表)
  - 对象存储 (OBS/S3)

### 6.2 内存缓存

```java
// 模板内存缓存
private final ConcurrentHashMap<String, Job> appDefines = new ConcurrentHashMap<>();

// 根据 app 名称获取模板
public Job getAppDefine(String app) {
    return appDefines.get(app);
}
```

### 6.3 模板结构

```yaml
app: mysql                    # 应用类型标识
category: db                  # 分类
type: jdbc                    # 采集协议
name:                         # 多语言名称
  zh-CN: MySQL监控
  en-US: MySQL Monitoring
params:                       # 参数定义
  - field: host
    name:
      zh-CN: 主机
    type: host
    required: true
metrics:                      # 指标定义
  - name: basic
    priority: 0
    fields:                   # 字段定义
      - field: version
        type: 1               # 0-数字, 1-字符串
        unit: ''
    protocol:                 # 协议配置
      jdbc:
        url: jdbc:mysql://^o^host^o^:^o^port^o^
        sql: SHOW STATUS
```

---

## 7. 数据流架构

### 7.1 监控任务创建流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   前端请求   │ -> │  Monitor    │ -> │  Monitor    │ -> │  Collector  │
│  (新增监控)  │    │  Controller │    │  Service    │    │ JobScheduler│
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   数据库    │ <- │    DAO      │ <- │  组装 Job   │ <- │  AppService │
│  (Monitor)  │    │   Layer     │    │  (模板+参数) │    │ (模板查询)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 7.2 采集数据接收流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Collector                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │  执行采集任务    │ -> │ 封装 MetricsData │ -> │ Netty 发送响应       │ │
│  │  (JDBC/HTTP...) │    │  (Protobuf)     │    │                     │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ TCP + Protobuf
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Manager                                    │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────┐ │
│  │   ManageServer      │ -> │  ResponseProcessor  │ -> │CommonDataQueue│
│  │   (Netty Server)    │    │  (消息处理器)        │    │  (数据队列)  │ │
│  └─────────────────────┘    └─────────────────────┘    └──────┬──────┘ │
└─────────────────────────────────────────────────────────────────┼───────┘
                                                                  │
                                                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Warehouse                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────┐ │
│  │ DataStorageDispatch │ -> │  历史数据存储        │ -> │ 实时数据存储 │ │
│  │   (数据分发器)       │    │ (VictoriaMetrics)   │    │ (Memory)    │ │
│  └─────────────────────┘    └─────────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. 配置管理

### 8.1 主要配置类

| 配置类 | 配置前缀 | 说明 |
|--------|----------|------|
| **SchedulerProperties** | `scheduler.server` | 调度服务配置 |
| **StatusProperties** | `status` | 状态计算配置 |
| **PrometheusProxyConfig** | `prometheus-proxy` | Prometheus 代理配置 |

### 8.2 调度服务配置

```yaml
scheduler:
  server:
    enabled: true
    port: 1158                    # Netty 监听端口
    idle-state-event-trigger-time: 100000  # 空闲检测时间(毫秒)
```

---

## 9. 安全设计

### 9.1 认证授权

- **JWT Token**：使用 Sureness 框架
- **Token 刷新**：支持 Refresh Token 机制
- **API 权限**：基于角色的访问控制

### 9.2 YAML 模板安全

**AppController** 中校验危险字符串：
```java
private static final String[] RISKY_STR_ARR = {
    "ScriptEngineManager", "URLClassLoader", "ClassLoader",
    "FileSystemXmlApplicationContext", "GroovyScriptEngine", ...
};
```

防止通过 YAML 注入恶意代码。

---

## 10. 与现有系统集成建议

### 10.1 Python 后端参考架构

```python
# 分层架构示例

# 1. Controller 层 (FastAPI/Flask)
@app.post("/api/monitor")
def add_monitor(monitor_dto: MonitorDto):
    monitor_service.add_monitor(monitor_dto)
    return {"code": 0, "msg": "success"}

# 2. Service 层
class MonitorService:
    def add_monitor(self, monitor_dto):
        # 参数校验
        self.validate(monitor_dto)
        # 保存数据库
        monitor = self.monitor_dao.save(monitor_dto.monitor)
        # 下发任务到 Collector
        self.collector_scheduler.add_job(job, collector)

# 3. DAO 层 (SQLAlchemy)
class MonitorDao:
    def save(self, monitor):
        db.session.add(monitor)
        db.session.commit()
        return monitor

# 4. 调度器 (类似 CollectorJobScheduler)
class CollectorScheduler:
    def __init__(self):
        self.consistent_hash = ConsistentHash()
        self.manage_server = ManageServer()
    
    def add_job(self, job, collector):
        # 选择 Collector
        if not collector:
            collector = self.consistent_hash.get_node(job.monitor_id)
        # 通过 Netty 下发
        self.manage_server.send_job(collector, job)
```

### 10.2 关键设计要点

1. **分层清晰**：Controller -> Service -> DAO，职责单一
2. **异步处理**：任务调度、数据采集使用异步机制
3. **内存缓存**：模板定义、Collector 状态缓存到内存
4. **一致性哈希**：实现任务的均匀分配和动态迁移
5. **Netty 通信**：TCP 长连接保证实时性和可靠性

---

## 11. 总结

| 模块 | 核心技术 | 职责 |
|------|----------|------|
| **Controller** | Spring MVC | REST API 接口 |
| **Service** | Spring Transaction | 业务逻辑 |
| **DAO** | Spring Data JPA | 数据访问 |
| **Scheduler** | Netty + 一致性哈希 | 任务调度 |
| **Template** | SnakeYAML | 模板管理 |
| **Security** | Sureness + JWT | 认证授权 |

HertzBeat Manager 采用经典的分层架构，通过 Netty 与 Collector 通信，使用一致性哈希实现负载均衡，是一个设计良好的微服务管理后端。

---

## 12. Python + Go 混合架构方案

基于 HertzBeat 架构分析，推荐采用 **Python (前端业务层) + Go (核心服务层)** 的混合架构：

### 12.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Python + Go 混合架构设计                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      前端业务层 (Python/FastAPI)                 │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   Web UI     │  │   API Gateway │  │   WebSocket Server   │   │   │
│  │  │   (Vue)      │  │   (FastAPI)   │  │   (通知推送)          │   │   │
│  │  │              │  │              │  │                      │   │   │
│  │  │ • 监控管理    │  │ • 用户认证    │  │ • 告警实时推送        │   │   │
│  │  │ • 告警展示    │  │ • 权限控制    │  │ • 状态更新           │   │   │
│  │  │ • Dashboard  │  │ • 请求路由    │  │ • 前端交互           │   │   │
│  │  │ • 报表分析    │  │ • 限流熔断    │  │                      │   │   │
│  │  └──────────────┘  └──────┬───────┘  └──────────┬───────────┘   │   │
│  │                           │                     │               │   │
│  │  职责: 用户交互、业务逻辑、权限管理、通知推送                        │   │
│  │  优势: 开发效率高、生态丰富、团队熟悉                                │   │
│  │                                                                  │   │
│  └───────────────────────────┬─────────────────────────────────────┘   │
│                              │                                          │
│                              │ HTTP/gRPC/WebSocket                      │
│                              │                                          │
│  ┌───────────────────────────┴─────────────────────────────────────┐   │
│  │                      核心服务层 (Go)                             │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   Manager    │  │  Collector   │  │   Warehouse          │   │   │
│  │  │   (Go)       │  │  (Go)        │  │   (Go)               │   │   │
│  │  │              │  │              │  │                      │   │   │
│  │  │ • 任务调度    │  │ • 指标采集    │  │ • 数据存储           │   │   │
│  │  │ • 负载均衡    │  │ • 协议实现    │  │ • 时序数据库写入      │   │   │
│  │  │ • 告警计算    │  │ • 时间轮调度  │  │ • 数据查询           │   │   │
│  │  │ • 规则引擎    │  │ • 并发采集    │  │ • 数据聚合           │   │   │
│  │  │ • 一致性哈希  │  │ • 结果上报    │  │ • 数据清理           │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  │                                                                  │   │
│  │  职责: 高性能计算、并发处理、数据采集、实时告警                      │   │
│  │  优势: 性能高、资源占用低、部署简单、并发能力强                       │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  数据存储层:                                                             │
│  • PostgreSQL/MySQL (元数据、配置)                                       │
│  • VictoriaMetrics/InfluxDB (时序数据)                                   │
│  • Redis (缓存、分布式锁、消息队列)                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 各层职责划分

| 层级 | 技术 | 职责 | 数据操作 |
|------|------|------|---------|
| **前端层** | Python/FastAPI | 用户界面、API网关、WebSocket推送 | 只查询时序数据库 |
| **核心层** | Go | 任务调度、数据采集、告警计算、数据写入 | 写入时序数据库 |
| **存储层** | 多种数据库 | 数据持久化、缓存、消息队列 | - |

### 12.3 数据流设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据流向 (Python + Go)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  配置数据 (PostgreSQL)                                                   │
│  ─────────────────────                                                   │
│  Python API ◀── 读写 ──▶ PostgreSQL ◀── 读取 ──▶ Go Manager             │
│    (用户配置)              (监控任务、告警规则)           (任务调度)       │
│                                                                         │
│  采集数据流                                                              │
│  ───────────                                                             │
│  Go Collector ── Netty/gRPC ──▶ Go Manager ── 队列 ──▶ Go Warehouse     │
│       │                            │                      │            │
│       │                            │                      ▼            │
│       │                            │              VictoriaMetrics       │
│       │                            │              (时序数据库)           │
│       │                            │                      ▲            │
│       │                            │                      │            │
│       │                            └────── HTTP API ──────┘            │
│       │                                                   │            │
│       │              ┌────────────────────────────────────┘            │
│       │              │                                                 │
│       └──────────────┼── HTTP/WebSocket ──▶ Python API Gateway        │
│                      │                      (FastAPI)                  │
│                      │                          │                     │
│                      │                          ▼                     │
│                      │              ┌─────────────────────┐            │
│                      │              │   Python 业务系统    │            │
│                      │              │   • 用户管理         │            │
│                      │              │   • Dashboard       │            │
│                      │              │   • 告警展示         │            │
│                      │              └─────────────────────┘            │
│                      │                                                 │
│                      └────── 查询时序数据 ──────────────────────────────┘
│                                                                         │
│  关键设计:                                                               │
│  • Collector 不直接写入时序数据库 ❌                                      │
│  • Collector 发送数据到 Manager 的队列 ✅                                 │
│  • Warehouse 从队列消费并写入时序数据库 ✅                                │
│  • Python 只查询，不写入时序数据库 ✅                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.4 组件交互流程

#### 1. 用户创建监控

```
用户 ──▶ Python API Gateway ──▶ Go Manager ──▶ Go Collector
         (权限校验)              (任务调度)      (执行采集)
              │                      │              │
              │                      ▼              │
              │               PostgreSQL           │
              │               (保存任务)            │
              │                      │              │
              ▼                      ▼              ▼
         WebSocket推送 ◀── 告警计算 ◀── 采集结果上报
         (实时通知)       (Go Manager)   (Go Collector)
```

#### 2. 告警触发流程

```
Go Collector ──▶ Go Manager ──▶ 告警规则计算
                     │
                     ▼
              触发告警 ──▶ HTTP调用 ──▶ Python API
                     │                    │
                     ▼                    ▼
              保存告警记录           WebSocket推送
              (PostgreSQL)           (通知用户)
```

### 12.5 API 设计示例

#### Python 层 (FastAPI)

```python
# Python FastAPI - 用户交互层
from fastapi import FastAPI, WebSocket

app = FastAPI()

# 监控管理（转发到 Go Manager）
@app.post("/api/v1/monitors")
async def create_monitor(monitor: MonitorCreate):
    # 权限校验
    await check_permission(current_user, "monitor:create")
    # 转发到 Go Manager
    response = await http_client.post(
        f"{GO_MANAGER_URL}/api/v1/monitors",
        json=monitor.dict()
    )
    return response.json()

# 告警查询（Python 直接查数据库）
@app.get("/api/v1/alerts")
async def get_alerts(status: str = None):
    # 直接查询 PostgreSQL
    alerts = await db.fetch_all(
        "SELECT * FROM alerts WHERE status = :status",
        {"status": status}
    )
    return alerts

# WebSocket 实时推送
@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 订阅 Redis 频道，接收 Go Manager 发布的消息
    async for message in redis_subscriber:
        await websocket.send_json(message)

# 时序数据查询（只查询，不写入）
@app.get("/api/v1/metrics/query")
async def query_metrics(
    monitor_id: int,
    metric: str,
    start: datetime,
    end: datetime
):
    # 查询 VictoriaMetrics (只读)
    url = "http://victoria-metrics:8428/api/v1/query_range"
    params = {
        "query": f"{metric}{{monitor_id=\"{monitor_id}\"}}",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step": "1m"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            return data["data"]["result"]
```

#### Go 层

```go
// Go Manager - 核心服务
package main

import (
    "github.com/gin-gonic/gin"
)

func main() {
    r := gin.Default()
    
    // 内部 API，只接受来自 Python 层的请求
    internal := r.Group("/api/v1", internalAuth())
    {
        // 监控管理
        internal.POST("/monitors", createMonitor)
        internal.GET("/monitors", listMonitors)
        internal.DELETE("/monitors/:id", deleteMonitor)
        
        // 任务调度
        internal.POST("/jobs", scheduleJob)
        internal.DELETE("/jobs/:id", cancelJob)
        
        // 告警规则
        internal.POST("/alert-rules", createAlertRule)
        internal.GET("/alert-rules", listAlertRules)
    }
    
    // Collector 连接（gRPC/Netty）
    collectorServer := NewCollectorServer()
    go collectorServer.Start(":8081")
    
    r.Run(":8080")
}

// Go Warehouse - 数据存储服务
func (w *Warehouse) Start() {
    // 从队列消费数据
    for metricsData := range w.dataQueue {
        // 写入时序数据库
        w.historyStorage.SaveData(metricsData)
        // 写入实时缓存
        w.realTimeStorage.SaveData(metricsData)
    }
}
```

### 12.6 各组件数据库操作

| 数据库 | Go 操作 | Python 操作 |
|--------|---------|-------------|
| **VictoriaMetrics** | 写入（Warehouse）、查询（Manager告警计算） | 只查询（Dashboard展示） |
| **PostgreSQL** | 写入告警记录、读取配置 | 读写业务数据、更新告警状态 |
| **Redis** | 读写缓存、发布告警消息 | 订阅消息、读写会话 |

### 12.7 优势总结

| 方面 | 优势 |
|------|------|
| **开发效率** | Python 做业务层，开发快；Go 做核心，性能高 |
| **性能** | Go 处理高并发采集和计算，无性能瓶颈 |
| **维护性** | 职责清晰，Python 团队专注业务，Go 团队专注性能 |
| **扩展性** | Go 服务可水平扩展，Python 层无状态 |
| **部署** | Go 单二进制文件部署简单，Python 用 Docker |

### 12.8 项目目录结构规划

基于现有项目结构，建议按以下方式组织代码：

```
/Users/peter/Documents/arco/
├── backend/                    # Python 后端 (业务层)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models/            # 数据模型
│   │   ├── routes/            # API 路由
│   │   ├── services/          # 业务服务
│   │   └── utils/             # 工具函数
│   ├── migrations/            # 数据库迁移
│   ├── templates/             # YAML 监控模板
│   └── tests/                 # 测试用例
│
├── frontend/                   # Vue 前端
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── components/        # 组件
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── utils/             # 工具函数
│   │   └── views/             # 页面视图
│   └── package.json
│
├── collector-go/               # Go 采集器 (已实现)
│   ├── cmd/
│   │   ├── collector/         # 采集器主程序
│   │   └── manager-sim/       # Manager 模拟器
│   ├── internal/
│   │   ├── bootstrap/         # 启动初始化
│   │   ├── config/            # 配置管理
│   │   ├── dispatcher/        # 任务分发
│   │   ├── model/             # 数据模型
│   │   ├── pb/                # Protobuf 生成代码
│   │   ├── pipeline/          # 数据处理管道
│   │   ├── protocol/          # 协议采集器
│   │   ├── queue/             # 队列系统
│   │   ├── scheduler/         # 时间轮调度器
│   │   ├── tpl/               # 模板管理
│   │   ├── transport/         # gRPC 通信
│   │   └── worker/            # 工作线程池
│   ├── proto/                 # Protobuf 定义
│   └── config/                # 配置文件
│
├── manager-go/                 # Go Manager (待实现)
│   ├── cmd/
│   │   └── manager/           # Manager 主程序
│   ├── internal/
│   │   ├── api/               # HTTP API
│   │   ├── scheduler/         # 任务调度
│   │   │   ├── consistent_hash.go
│   │   │   └── job_scheduler.go
│   │   ├── alerter/           # 告警引擎
│   │   │   ├── calculator.go
│   │   │   ├── rule_engine.go
│   │   │   └── notifier.go
│   │   ├── warehouse/         # 数据存储
│   │   │   ├── data_queue.go
│   │   │   └── storage.go
│   │   ├── transport/         # 网络通信
│   │   │   ├── grpc_server.go
│   │   │   └── collector_client.go
│   │   └── tpl/               # 模板管理
│   └── proto/
│
├── web-app/                    # Python Web 应用 (可选)
│   └── ...
│
└── docs/                       # 文档
    ├── hertzbeat-manager-analysis.md
    ├── hertzbeat-collector-analysis.md
    └── hertzbeat-alerter-analysis.md
```

### 12.9 各组件详细说明

#### 12.9.1 Collector-Go (已实现)

**位置**: `/Users/peter/Documents/arco/collector-go/`

**核心功能**:
- **gRPC 通信**: 与 Manager 双向 Stream 长连接
- **时间轮调度**: `internal/scheduler/wheel.go` - 统一 tick 驱动桶轮转
- **工作线程池**: `internal/worker/pool.go` - 固定 worker + 有界队列
- **协议 SPI**: `internal/protocol/registry.go` - 支持动态协议注册
- **队列系统**: `internal/queue/` - 内存队列 + Kafka 支持

**已实现协议**:
- HTTP: `internal/protocol/httpcollector/http.go`
- ICMP: `internal/protocol/pingcollector/ping.go`
- SNMP: `internal/protocol/snmpcollector/snmp.go`
- JDBC: `internal/protocol/jdbccollector/jdbc.go`
- Linux: `internal/protocol/linuxcollector/linux.go`

**数据模型** (`internal/model/model.go`):
```go
type Job struct {
    ID       int64         `json:"id"`
    Monitor  int64         `json:"monitor_id"`
    App      string        `json:"app"`
    Interval time.Duration `json:"interval"`
    Tasks    []MetricsTask `json:"tasks"`
}

type Result struct {
    JobID      int64             `json:"job_id"`
    MonitorID  int64             `json:"monitor_id"`
    App        string            `json:"app"`
    Metrics    string            `json:"metrics"`
    Protocol   string            `json:"protocol"`
    Code       string            `json:"code"`
    Time       time.Time         `json:"time"`
    Success    bool              `json:"success"`
    Message    string            `json:"message"`
    Fields     map[string]string `json:"fields"`
    RawLatency time.Duration     `json:"raw_latency"`
}
```

#### 12.9.2 Manager-Go (待实现)

**位置**: `/Users/peter/Documents/arco/manager-go/` (建议新建)

**核心模块**:

| 模块 | 文件 | 职责 |
|------|------|------|
| **API Gateway** | `internal/api/` | HTTP API，供 Python 层调用 |
| **任务调度器** | `internal/scheduler/job_scheduler.go` | 任务分配、状态管理 |
| **一致性哈希** | `internal/scheduler/consistent_hash.go` | Collector 负载均衡 |
| **告警引擎** | `internal/alerter/` | 规则计算、收敛、通知 |
| **数据队列** | `internal/warehouse/data_queue.go` | 接收 Collector 数据 |
| **gRPC Server** | `internal/transport/grpc_server.go` | 管理 Collector 连接 |

**与 Collector 交互**:
```go
// Manager 下发任务到 Collector
func (m *Manager) dispatchJob(job *Job, collectorID string) error {
    client := m.collectorClients[collectorID]
    return client.UpsertJob(context.Background(), job)
}

// Manager 接收 Collector 上报数据
func (m *Manager) receiveResult(result *Result) {
    // 1. 写入数据队列
    m.dataQueue.Push(result)
    
    // 2. 触发告警计算
    m.alerter.Evaluate(result)
    
    // 3. 更新监控状态
    m.updateMonitorStatus(result.MonitorID, result.Success)
}
```

#### 12.9.3 Alerter (告警引擎)

**位置**: `manager-go/internal/alerter/`

**核心组件**:
- **Rule Engine**: 告警规则匹配
- **Calculator**: 阈值计算（JEXL 表达式）
- **Reducer**: 告警收敛（分组、抑制、静默）
- **Notifier**: 多渠道通知（Webhook、Email、钉钉等）

**告警流程**:
```
采集数据 ──▶ Rule Engine ──▶ Calculator ──▶ Reducer ──▶ Notifier
                │              │             │           │
                ▼              ▼             ▼           ▼
            规则匹配       阈值计算      告警收敛     发送通知
```

#### 12.9.4 Warehouse (数据存储)

**位置**: `manager-go/internal/warehouse/`

**职责**:
- 从数据队列消费采集结果
- 写入时序数据库（VictoriaMetrics/InfluxDB）
- 写入实时缓存（Redis/Memory）

**数据流**:
```go
func (w *Warehouse) Start() {
    for result := range w.dataQueue {
        // 1. 写入时序数据库
        w.historyStorage.Write(result)
        
        // 2. 写入实时缓存
        w.realTimeStorage.Write(result)
        
        // 3. 发布到 Redis，供 Python 订阅
        w.redisClient.Publish("metrics:realtime", result)
    }
}
```

#### 12.9.5 Web-App (Python 业务层)

**位置**: `/Users/peter/Documents/arco/backend/` (现有)

**核心功能**:
- 用户管理、权限控制
- 监控配置管理
- Dashboard 展示
- 告警展示和处理
- 通知推送（WebSocket）

**与 Go Manager 交互**:
```python
# 创建监控任务
@app.post("/api/v1/monitors")
async def create_monitor(monitor: MonitorCreate):
    # 1. 保存到本地数据库
    await db.execute("INSERT INTO monitors ...")
    
    # 2. 调用 Go Manager 下发任务
    response = await http_client.post(
        f"{MANAGER_URL}/api/v1/jobs",
        json=monitor.to_job_dict()
    )
    return response.json()

# 查询时序数据
@app.get("/api/v1/metrics/query")
async def query_metrics(params: QueryParams):
    # 直接查询 VictoriaMetrics
    return await victoria_metrics_client.query(params)
```

### 12.10 实施路线图

#### 阶段 1: 完善 Collector-Go (已完成基础)
- [x] 基础架构搭建
- [x] 时间轮调度器
- [x] 工作线程池
- [x] 协议 SPI 机制
- [x] gRPC 通信
- [ ] 完善更多协议（Redis、MySQL、PostgreSQL）
- [ ] 添加单元测试和集成测试

#### 阶段 2: 实现 Manager-Go
- [ ] 项目初始化 (`manager-go/`)
- [ ] HTTP API 框架 (Gin/Echo)
- [ ] gRPC Server (管理 Collector)
- [ ] 一致性哈希实现
- [ ] 任务调度器
- [ ] 模板管理服务

#### 阶段 3: 实现 Alerter
- [ ] 告警规则引擎
- [ ] 阈值计算器
- [ ] 告警收敛器
- [ ] 通知分发器
- [ ] Webhook 支持

#### 阶段 4: 实现 Warehouse
- [ ] 数据队列消费
- [ ] VictoriaMetrics 写入
- [ ] Redis 缓存写入
- [ ] 数据查询接口

#### 阶段 5: Python 层对接
- [ ] 对接 Manager API
- [ ] Dashboard 数据展示
- [ ] 告警页面
- [ ] 用户权限集成

#### 阶段 6: 集成测试与优化
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 文档完善
- [ ] 部署脚本

### 12.11 技术选型建议

| 组件 | 技术 | 理由 |
|------|------|------|
| **Go Web 框架** | Gin | 性能优秀、生态丰富 |
| **Go gRPC** | 官方库 | 高性能、支持 Stream |
| **时序数据库** | VictoriaMetrics | 兼容 Prometheus、性能优秀 |
| **缓存** | Redis | 支持 Pub/Sub、分布式锁 |
| **消息队列** | Kafka/Redis | 高吞吐量、持久化 |
| **Python Web** | FastAPI | 异步支持、类型提示 |
| **前端** | Vue 3 + TypeScript | 已在使用、生态好 |

这种架构既发挥了 Python 的开发效率优势，又利用了 Go 的性能优势，是一个平衡开发效率和系统性能的优秀方案。
