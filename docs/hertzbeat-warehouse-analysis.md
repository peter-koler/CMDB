# HertzBeat Warehouse 架构分析报告

## 1. 项目概述

HertzBeat Warehouse 是 HertzBeat 监控系统的**数据存储服务**，负责：
- **数据接收**：从 CommonDataQueue 消费采集数据
- **数据分发**：将数据分发到实时存储和历史存储
- **状态计算**：根据采集结果计算监控可用性状态
- **数据查询**：提供监控数据查询 API
- **日志存储**：支持日志数据的批量存储

基于 **Java 17 + Spring Boot 3.x** 构建，采用**双存储架构**（实时 + 历史）。

---

## 2. 模块结构

```
hertzbeat-warehouse/
├── src/main/java/org/apache/hertzbeat/warehouse/
│   ├── config/                    # 配置类
│   │   └── WarehouseAutoConfiguration.java
│   ├── constants/                 # 常量定义
│   │   └── WarehouseConstants.java
│   ├── controller/                # REST API 控制器
│   │   ├── DataQueryController.java      # 数据查询接口
│   │   └── MetricsDataController.java    # 指标数据接口
│   ├── dao/                       # 数据访问层
│   │   └── HistoryDao.java
│   ├── db/                        # 查询执行器
│   │   ├── QueryExecutor.java
│   │   ├── SqlQueryExecutor.java
│   │   ├── PromqlQueryExecutor.java
│   │   ├── VictoriaMetricsQueryExecutor.java
│   │   ├── GreptimeSqlQueryExecutor.java
│   │   └── GreptimePromqlQueryExecutor.java
│   ├── listener/                  # 事件监听器
│   │   └── WareHouseApplicationReadyListener.java
│   ├── service/                   # 业务服务层
│   │   ├── DatasourceQueryService.java
│   │   ├── MetricsDataService.java
│   │   ├── WarehouseService.java
│   │   └── impl/
│   └── store/                     # 数据存储核心
│       ├── DataStorageDispatch.java         # 数据分发器
│       ├── history/                         # 历史数据存储
│       │   ├── tsdb/                        # 时序数据库实现
│       │   │   ├── vm/                      # VictoriaMetrics
│       │   │   ├── influxdb/                # InfluxDB
│       │   │   ├── tdengine/                # TDengine
│       │   │   ├── greptime/                # GreptimeDB
│       │   │   ├── iotdb/                   # IoTDB
│       │   │   ├── questdb/                 # QuestDB
│       │   │   └── duckdb/                  # DuckDB
│       │   ├── AbstractHistoryDataStorage.java
│       │   ├── HistoryDataReader.java
│       │   └── HistoryDataWriter.java
│       └── realtime/                        # 实时数据存储
│           ├── memory/                      # 内存存储
│           ├── redis/                       # Redis 存储
│           ├── AbstractRealTimeDataStorage.java
│           ├── RealTimeDataReader.java
│           └── RealTimeDataWriter.java
└── WarehouseWorkerPool.java       # 工作线程池
```

---

## 3. 双存储架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DataStorageDispatch                           │
│                              (数据分发器)                                │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼                                       ▼
┌─────────────────────────────┐     ┌─────────────────────────────────────┐
│      实时数据存储            │     │            历史数据存储              │
│   (RealTimeDataStorage)     │     │        (HistoryDataStorage)         │
├─────────────────────────────┤     ├─────────────────────────────────────┤
│  • Memory (默认)            │     │  • VictoriaMetrics (推荐)           │
│  • Redis                    │     │  • InfluxDB                         │
│                             │     │  • TDengine                         │
│  特点：                     │     │  • GreptimeDB                       │
│  - 快速查询最新数据          │     │  • IoTDB                            │
│  - 内存/缓存存储             │     │  • QuestDB                          │
│  - 容量有限                  │     │  • DuckDB                           │
└─────────────────────────────┘     │                                     │
                                    │  特点：                              │
                                    │  - 持久化存储                        │
                                    │  - 支持时间序列查询                  │
                                    │  - 大容量、高压缩                    │
                                    └─────────────────────────────────────┘
```

---

## 4. 核心组件分析

### 4.1 数据分发器 - DataStorageDispatch

**路径**: `store/DataStorageDispatch.java`

**核心职责**：
1. **启动消费线程**：从 CommonDataQueue 轮询获取数据
2. **状态计算**：根据采集结果更新监控状态（UP/DOWN）
3. **数据分发**：同时写入历史存储和实时存储
4. **插件执行**：执行采集后插件（PostCollectPlugin）
5. **日志存储**：独立线程处理日志数据批量存储

**处理流程**：
```java
// 1. 从队列获取数据
CollectRep.MetricsData metricsData = commonDataQueue.pollMetricsDataToStorage();

// 2. 计算监控状态
calculateMonitorStatus(metricsData);

// 3. 写入历史存储（异步）
historyDataWriter.ifPresent(dataWriter -> dataWriter.saveData(metricsData));

// 4. 执行采集后插件
pluginRunner.pluginExecute(PostCollectPlugin.class, ...);

// 5. 写入实时存储（必须成功）
realTimeDataWriter.saveData(metricsData);
```

**状态计算逻辑**：
- 仅处理 `priority == 0` 的指标组（通常是 basic/基础指标）
- 采集成功 → 监控状态 = UP
- 采集失败 → 监控状态 = DOWN
- 使用 JDBC 直接更新数据库，并清除 JPA 缓存

### 4.2 历史数据存储 - HistoryDataStorage

#### 4.2.1 接口定义

**HistoryDataWriter** (`store/history/tsdb/HistoryDataWriter.java`):
```java
public interface HistoryDataWriter {
    boolean isServerAvailable();
    void saveData(CollectRep.MetricsData metricsData);
    void saveLogData(LogEntry logEntry);
    void saveLogDataBatch(List<LogEntry> logEntries);
}
```

**HistoryDataReader** (`store/history/tsdb/HistoryDataReader.java`):
```java
public interface HistoryDataReader {
    boolean isServerAvailable();
    Map<String, List<Value>> getHistoryMetricData(Long monitorId, String metric, ...);
    Map<String, List<Value>> getHistoryIntervalMetricData(Long monitorId, String metric, ...);
}
```

#### 4.2.2 支持的时序数据库

| 数据库 | 实现类 | 特点 | 适用场景 |
|--------|--------|------|---------|
| **VictoriaMetrics** | `VictoriaMetricsDataStorage` | 高性能、低资源、PromQL | ⭐ **推荐** |
| **VictoriaMetrics Cluster** | `VictoriaMetricsClusterDataStorage` | 集群版 | 大规模部署 |
| **InfluxDB** | `InfluxdbDataStorage` | 成熟生态、InfluxQL | 已有 InfluxDB |
| **TDengine** | `TdEngineDataStorage` | 国产、SQL 支持 | 国产化需求 |
| **GreptimeDB** | `GreptimeDbDataStorage` | 云原生、PromQL+SQL | 云原生场景 |
| **IoTDB** | `IotDbDataStorage` | 物联网专用 | IoT 场景 |
| **QuestDB** | `QuestdbDataStorage` | 高性能 SQL | SQL 分析场景 |
| **DuckDB** | `DuckdbDatabaseDataStorage` | 嵌入式分析 | 边缘计算 |

#### 4.2.3 VictoriaMetrics 存储格式

```
# 指标名称格式
{metrics}_{monitor_id}_{metric_field}

# 标签
__name__={metrics}_{monitor_id}_{metric_field}
job={app}
instance={host}:{port}
__monitor_id__={monitor_id}

# 示例
hzb_basic_12345_version{job="mysql",instance="127.0.0.1:3306",__monitor_id__="12345"} 8.0.32 1704067200000
```

### 4.3 实时数据存储 - RealTimeDataStorage

#### 4.3.1 接口定义

**RealTimeDataWriter** (`store/realtime/RealTimeDataWriter.java`):
```java
public interface RealTimeDataWriter {
    boolean isServerAvailable();
    void saveData(CollectRep.MetricsData metricsData);
}
```

**RealTimeDataReader** (`store/realtime/RealTimeDataReader.java`):
```java
public interface RealTimeDataReader {
    boolean isServerAvailable();
    CollectRep.MetricsData getCurrentMetricsData(Long monitorId, String metric);
    List<CollectRep.MetricsData> getCurrentMetricsData(Long monitorId);
}
```

#### 4.3.2 实现方式

| 实现 | 类 | 存储结构 | 特点 |
|------|-----|---------|------|
| **内存** | `MemoryDataStorage` | `ConcurrentHashMap` | 默认、最快、重启丢失 |
| **Redis** | `RedisDataStorage` | Hash | 持久化、分布式 |

**内存存储结构**：
```java
// monitorId -> metricsName -> MetricsData
Map<Long, Map<String, CollectRep.MetricsData>> monitorMetricsDataMap;
```

### 4.4 工作线程池 - WarehouseWorkerPool

**路径**: `WarehouseWorkerPool.java`

**配置**：
- 核心线程数：2
- 最大线程数：Integer.MAX_VALUE（无上限）
- 空闲线程存活：10 秒
- 任务队列：`SynchronousQueue`（直接提交）
- 拒绝策略：`AbortPolicy`（直接拒绝）

**用途**：
- 执行数据存储线程
- 执行日志存储线程

---

## 5. 数据流架构

### 5.1 完整数据流

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
│  ┌─────────────────────┐    ┌─────────────────────┐                     │
│  │   ManageServer      │ -> │  ResponseProcessor  │                     │
│  │   (Netty Server)    │    │  (消息处理器)        │                     │
│  └─────────────────────┘    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CommonDataQueue                               │
│                    (内存队列 / Kafka / Redis)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Warehouse                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     DataStorageDispatch                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │  获取数据    │->│ 计算状态     │->│ 分发存储     │             │   │
│  │  └─────────────┘  └─────────────┘  └──────┬──────┘             │   │
│  └───────────────────────────────────────────┼────────────────────┘   │
│                                              │                        │
│                   ┌──────────────────────────┼──────────────────┐     │
│                   │                          │                   │     │
│                   ▼                          ▼                   ▼     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │ │
│  │   历史数据存储          │  │   实时数据存储          │             │ │
│  │  VictoriaMetrics       │  │   Memory/Redis         │             │ │
│  └────────────────────────┘  └────────────────────────┘             │ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 数据存储线程模型

```
┌─────────────────────────────────────────────────────────────────┐
│                    WarehouseWorkerPool                          │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │  Persistent Thread  │    │   Log Data Thread   │            │
│  │  (数据存储线程)      │    │   (日志存储线程)     │            │
│  │                     │    │                     │            │
│  │  while (!stopped) { │    │  while (!stopped) { │            │
│  │    data = queue.poll│    │    logs = queue.poll│            │
│  │    process(data)    │    │    batchSave(logs)  │            │
│  │  }                  │    │  }                  │            │
│  └─────────────────────┘    └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 配置说明

### 6.1 历史数据存储配置

```yaml
warehouse:
  store:
    victoria-metrics:
      enabled: true
      url: http://localhost:8428
      health-check:
        url: /health
        interval: 10
    # 其他存储配置...
    influxdb:
      enabled: false
      server-url: http://localhost:8086
    tdengine:
      enabled: false
      url: jdbc:TAOS://localhost:6030/hertzbeat
```

### 6.2 实时数据存储配置

```yaml
warehouse:
  real-time:
    memory:
      enabled: true
      init-size: 16  # 初始容量
    redis:
      enabled: false
      host: localhost
      port: 6379
```

---

## 7. API 接口

### 7.1 数据查询接口

**DataQueryController** (`/api/warehouse/query`):

```java
@PostMapping("/api/warehouse/query")
public ResponseEntity<Message<List<DatasourceQueryData>>> query(
    @RequestBody List<DatasourceQuery> queries)
```

支持多种查询类型：
- **PromQL**: 适用于 VictoriaMetrics、GreptimeDB
- **SQL**: 适用于 TDengine、InfluxDB、GreptimeDB

### 7.2 指标数据接口

**MetricsDataController**:
- 查询监控实时指标数据
- 查询历史指标数据

---

## 8. 与现有系统集成建议

### 8.1 Python 后端参考架构

```python
# 1. 数据分发器
class DataStorageDispatch:
    def __init__(self):
        self.worker_pool = ThreadPoolExecutor()
        self.history_writer = VictoriaMetricsStorage()
        self.realtime_writer = MemoryStorage()
    
    def start(self):
        # 启动消费线程
        self.worker_pool.submit(self._persistent_loop)
    
    def _persistent_loop(self):
        while self.running:
            # 从队列获取数据
            data = common_data_queue.poll_metrics_data()
            
            # 计算监控状态
            self._calculate_monitor_status(data)
            
            # 写入历史存储
            self.history_writer.save_data(data)
            
            # 写入实时存储
            self.realtime_writer.save_data(data)

# 2. 历史数据存储接口
class HistoryDataStorage(ABC):
    @abstractmethod
    def save_data(self, metrics_data: MetricsData):
        pass
    
    @abstractmethod
    def query_history(self, monitor_id: int, metric: str, 
                      start: datetime, end: datetime) -> List[Value]:
        pass

# 3. VictoriaMetrics 实现
class VictoriaMetricsStorage(HistoryDataStorage):
    def __init__(self, url: str):
        self.url = url
        self.import_path = "/api/v1/import"
        self.export_path = "/api/v1/export"
    
    def save_data(self, data: MetricsData):
        # 转换为 VictoriaMetrics 格式
        vm_data = self._to_vm_format(data)
        # HTTP 写入
        requests.post(f"{self.url}{self.import_path}", data=vm_data)
    
    def _to_vm_format(self, data: MetricsData) -> str:
        # 格式: metric{labels} value timestamp
        lines = []
        for value in data.values:
            metric_name = f"{data.metrics}_{data.id}_{value.field}"
            labels = f"job=\"{data.app}\",instance=\"{data.host}\""
            line = f"{metric_name}{{{labels}}} {value.value} {data.time}"
            lines.append(line)
        return "\n".join(lines)

# 4. 实时数据存储接口
class RealTimeDataStorage(ABC):
    @abstractmethod
    def save_data(self, metrics_data: MetricsData):
        pass
    
    @abstractmethod
    def get_current_data(self, monitor_id: int, metric: str) -> MetricsData:
        pass

# 5. 内存实现
class MemoryStorage(RealTimeDataStorage):
    def __init__(self):
        # monitor_id -> metric -> data
        self.data_map: Dict[int, Dict[str, MetricsData]] = {}
    
    def save_data(self, data: MetricsData):
        if data.monitor_id not in self.data_map:
            self.data_map[data.monitor_id] = {}
        self.data_map[data.monitor_id][data.metric] = data
    
    def get_current_data(self, monitor_id: int, metric: str) -> MetricsData:
        return self.data_map.get(monitor_id, {}).get(metric)
```

### 8.2 关键设计要点

1. **双存储架构**：实时存储（快速查询）+ 历史存储（持久化）
2. **异步消费**：独立线程从队列消费数据，不阻塞采集流程
3. **批量写入**：日志数据支持批量存储，减少 IO
4. **状态计算**：优先指标组（priority=0）决定监控可用性
5. **插件扩展**：支持采集后插件，实现自定义数据处理

---

## 9. 常见问题解答

### 9.1 实时数据是用来做什么的？

**实时数据存储的主要用途**：

| 用途 | 说明 | 场景 |
|------|------|------|
| **最新数据查询** | 查看监控对象的当前状态 | 仪表盘实时展示 |
| **告警判断** | 基于最新数据进行告警规则匹配 | 实时告警触发 |
| **快速响应** | 内存/Redis 查询，毫秒级返回 | 前端页面刷新 |
| **减少历史库压力** | 高频查询走实时存储，历史存储只用于分析 | 性能优化 |

**API 示例**：
```
GET /api/monitor/{monitorId}/metrics/{metrics}
返回：当前最新的采集数据（从 Memory/Redis 读取）
```

### 9.2 CommonDataQueue 的数据从哪里来？

**数据流向**：

```
Collector (采集器)
    │
    │ Netty 发送 MetricsData (Protobuf)
    ▼
Manager (Netty Server 接收)
    │
    │ 写入 CommonDataQueue
    ▼
CommonDataQueue (内存队列/Kafka/Redis)
    │
    │ 消费
    ▼
Warehouse (DataStorageDispatch)
    │
    ├─> 实时存储 (Memory/Redis)
    └─> 历史存储 (VictoriaMetrics/InfluxDB)
```

**CommonDataQueue 是中间件，不是数据源**：
- **生产者**：Manager 的 Netty ResponseProcessor
- **消费者**：Warehouse 的 DataStorageDispatch
- **作用**：解耦 Manager 和 Warehouse，支持异步处理

### 9.3 CommonDataQueue 的实现方式

| 实现方式 | 类 | 配置 | 适用场景 |
|----------|-----|------|---------|
| **内存队列** (默认) | `InMemoryCommonDataQueue` | `common.queue.type = memory` | 单机部署、开发测试 |
| **Kafka** | `KafkaCommonDataQueue` | `common.queue.type = kafka` | 分布式部署、生产环境 |
| **Redis** | `RedisCommonDataQueue` | `common.queue.type = redis` | 中等规模、已有 Redis |

**配置示例**：
```yaml
common:
  queue:
    type: memory  # 或 kafka、redis
    
    # Kafka 配置
    kafka:
      servers: localhost:9092
      metrics-data-topic: hertzbeat-metrics-data
      
    # Redis 配置
    redis:
      host: localhost
      port: 6379
```

### 9.4 实时数据 vs 历史数据的区别

| 特性 | 实时数据 | 历史数据 |
|------|---------|---------|
| **存储位置** | Memory / Redis | VictoriaMetrics / InfluxDB |
| **数据量** | 只保留最新一条 | 保留全部历史数据 |
| **查询速度** | 极快（内存级） | 较快（时序数据库优化） |
| **查询范围** | 只能查最新数据 | 可查询任意时间范围 |
| **用途** | 实时监控、告警 | 趋势分析、报表、故障排查 |
| **数据格式** | Protobuf MetricsData | 时序数据库格式 |

### 9.5 数据存储的可靠性

```
Collector 采集数据
    │
    ▼
Manager 接收并写入 CommonDataQueue
    │
    ├─> 如果 Warehouse 正常：数据被消费，写入实时+历史存储
    │
    └─> 如果 Warehouse 故障：数据在队列中堆积，等待恢复后消费
        (内存队列有大小限制，Kafka/Redis 可持久化)
```

**注意**：
- **内存队列**：进程重启数据丢失，适合开发测试
- **Kafka/Redis**：数据持久化，适合生产环境

---

## 10. 总结

| 模块 | 核心技术 | 职责 |
|------|----------|------|
| **DataStorageDispatch** | 线程池 + 队列消费 | 数据分发和状态计算 |
| **HistoryDataStorage** | VictoriaMetrics/InfluxDB/TDengine | 历史数据持久化 |
| **RealTimeDataStorage** | Memory/Redis | 实时数据快速查询 |
| **WarehouseWorkerPool** | ThreadPoolExecutor | 异步任务执行 |
| **QueryExecutor** | SQL/PromQL | 数据查询接口 |
| **CommonDataQueue** | 内存/Kafka/Redis | 数据缓冲队列 |

### 核心设计思想

1. **双存储分离**：实时存储用于快速查询，历史存储用于持久化分析
2. **队列解耦**：CommonDataQueue 解耦 Manager 和 Warehouse
3. **异步处理**：独立线程消费数据，不阻塞采集流程
4. **可插拔存储**：支持多种时序数据库，按需选择

HertzBeat Warehouse 采用**双存储架构**和**队列缓冲**机制，实现了高性能、可扩展的监控数据存储服务。
