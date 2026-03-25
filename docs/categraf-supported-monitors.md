# Categraf 支持的监控类型汇总

> 本文档自动整理自 Categraf 项目源码
> 生成时间：2026-03-20
> Categraf 版本：v0.3.x+

---

## 📊 监控类型概览

Categraf 是一款 All-in-One 的数据采集器，内置支持 **100+ 种监控插件**，涵盖以下大类：

| 类别 | 数量 | 说明 |
|------|------|------|
| 系统资源监控 | 15+ | CPU、内存、磁盘、网络等 |
| 数据库监控 | 15+ | MySQL、Redis、MongoDB、PostgreSQL 等 |
| 消息队列监控 | 8+ | Kafka、RabbitMQ、NSQ、NATS 等 |
| Web 服务监控 | 10+ | Nginx、Apache、Tomcat、PHP-FPM 等 |
| 容器/K8s 监控 | 8+ | Docker、Kubernetes、cAdvisor 等 |
| 云服务监控 | 5+ | 阿里云、AWS CloudWatch、Google Cloud 等 |
| 网络设备监控 | 8+ | SNMP、Ping、IPMI、交换机 等 |
| 应用中间件监控 | 20+ | Elasticsearch、Jenkins、LDAP 等 |
| Java/JMX 监控 | 12+ | 通过 Jolokia 支持各类 Java 应用 |
| 其他监控 | 15+ | 日志、进程、证书、自定义脚本等 |

---

## 🔧 一、系统资源监控

### 1.1 基础系统指标

| 插件名 | 配置文件 | 说明 | 支持平台 |
|--------|----------|------|----------|
| `cpu` | `input.cpu/cpu.toml` | CPU 使用率、负载统计 | Linux/Windows/macOS |
| `mem` | `input.mem/mem.toml` | 内存使用率、交换分区 | Linux/Windows/macOS |
| `disk` | `input.disk/disk.toml` | 磁盘使用率、挂载点 | Linux/Windows/macOS |
| `diskio` | `input.diskio/diskio.toml` | 磁盘 IO 统计 | Linux/Windows |
| `net` | `input.net/net.toml` | 网络流量、接口统计 | Linux/Windows/macOS |
| `netstat` | `input.netstat/netstat.toml` | 网络连接统计 | Linux |
| `netstat_filter` | `input.netstat_filter/netstat_filter.toml` | 过滤特定网络连接 | Linux |
| `processes` | `input.processes/processes.toml` | 进程数量统计 | Linux |
| `procstat` | `input.procstat/procstat.toml` | 指定进程监控 | Linux/Windows |
| `system` | `input.system/system.toml` | 系统负载、运行时间 | Linux/Windows/macOS |
| `systemd` | `input.systemd/systemd.toml` | Systemd 服务状态 | Linux |

### 1.2 内核级监控

| 插件名 | 配置文件 | 说明 | 支持平台 |
|--------|----------|------|----------|
| `kernel` | `input.kernel/kernel.toml` | 内核统计信息 | Linux |
| `kernel_vmstat` | `input.kernel_vmstat/kernel_vmstat.toml` | 虚拟内存统计 | Linux |
| `linux_sysctl_fs` | `input.linux_sysctl_fs/linux_sysctl_fs.toml` | 文件系统 sysctl | Linux |
| `conntrack` | `input.conntrack/conntrack.toml` | 连接跟踪表 | Linux |
| `sockstat` | `input.sockstat/sockstat.toml` | Socket 统计 | Linux |
| `iptables` | `input.iptables/iptables.toml` | IPTables 规则统计 | Linux |
| `ipvs` | `input.ipvs/ipvs.toml` | IPVS 连接统计 | Linux |
| `ethtool` | `input.ethtool/ethtool.toml` | 网卡硬件统计 | Linux |

### 1.3 硬件监控

| 插件名 | 配置文件 | 说明 | 支持平台 |
|--------|----------|------|----------|
| `ipmi` | `input.ipmi/conf.toml` | IPMI 硬件监控 | Linux/Windows |
| `smart` | `input.smart/smart.toml` | 硬盘 SMART 信息 | Linux |
| `nvidia_smi` | `input.nvidia_smi/nvidia_smi.toml` | NVIDIA GPU 监控 | Linux/Windows |
| `amd_rocm_smi` | `input.amd_rocm_smi/rocm.toml` | AMD GPU 监控 | Linux |
| `dcgm` | `input.dcgm/exporter.toml` | NVIDIA DCGM GPU 监控 | Linux |

---

## 🗄️ 二、数据库监控

### 2.1 MySQL 监控

**配置文件**: `conf/input.mysql/mysql.toml`

**监控指标类别**:

| 指标类别 | 具体指标 | 说明 |
|----------|----------|------|
| **连接状态** | `threads_connected`, `threads_running`, `connections`, `max_used_connections`, `aborted_clients`, `aborted_connects` | 连接数、活跃线程、拒绝连接 |
| **查询统计** | `queries`, `questions`, `slow_queries`, `prepared_stmt_count` | 总查询数、慢查询、预处理语句 |
| **命令统计** | `com_select`, `com_insert`, `com_update`, `com_delete`, `com_replace`, `com_commit`, `com_rollback` | 各类 SQL 命令执行次数 |
| **InnoDB 存储** | `innodb_buffer_pool_size`, `innodb_data_reads`, `innodb_data_writes`, `innodb_row_lock_waits`, `innodb_row_lock_time` | 缓冲池、读写操作、行锁等待 |
| **表缓存** | `open_files`, `open_tables`, `table_locks_waited`, `created_tmp_tables`, `created_tmp_disk_tables` | 打开表数、临时表创建 |
| **网络流量** | `bytes_sent`, `bytes_received` | 发送/接收字节数 |
| **查询缓存** | `qcache_hits`, `qcache_inserts`, `qcache_lowmem_prunes` | 查询缓存命中、插入、修剪 |
| **线程状态** | `threads_cached`, `threads_created` | 线程缓存、创建数 |
| **复制状态** | `seconds_behind_master`, `slave_io_running`, `slave_sql_running`, `exec_master_log_pos` | 主从延迟、IO/SQL 线程状态 |
| **Galera 集群** | `wsrep_cluster_size`, `wsrep_local_recv_queue_avg`, `wsrep_flow_control_paused` | 集群节点数、流控暂停 |
| **自定义查询** | 支持自定义 SQL 查询指标 | 灵活配置业务指标 |

**扩展功能**:
- `extra_status_metrics`: 额外的状态指标
- `extra_innodb_metrics`: 额外的 InnoDB 指标
- `gather_processlist_processes_by_state/user`: 按状态/用户统计进程
- `gather_schema_size`: 数据库大小统计
- `gather_table_size`: 表大小统计
- `gather_slave_status`: 复制状态采集

---

### 2.2 Redis 监控

**配置文件**: `conf/input.redis/redis.toml`

**监控指标类别**:

| 指标类别 | 具体指标 | 说明 |
|----------|----------|------|
| **服务状态** | `up`, `ping_use_seconds`, `scrape_use_seconds` | 存活状态、连接延迟、采集耗时 |
| **内存使用** | `used_memory`, `used_memory_rss`, `used_memory_peak`, `mem_fragmentation_ratio`, `maxmemory` | 内存使用、碎片率、峰值 |
| **连接状态** | `connected_clients`, `blocked_clients`, `connected_slaves`, `rejected_connections` | 客户端连接、阻塞客户端、从节点 |
| **命令统计** | `total_commands_processed`, `instantaneous_ops_per_sec`, `cmdstat_calls/usec/usec_per_call` | 总命令数、QPS、各命令耗时 |
| **键值统计** | `total_keys`, `expired_keys`, `evicted_keys`, `keyspace_hits`, `keyspace_misses`, `keyspace_hitrate` | 键总数、过期/淘汰数、命中率 |
| **持久化** | `rdb_bgsave_in_progress`, `rdb_last_save_time`, `rdb_last_bgsave_status`, `aof_enabled`, `aof_rewrite_in_progress` | RDB/AOF 状态、最后保存时间 |
| **复制状态** | `role`, `master_repl_offset`, `replication_offset/lag` | 主从角色、复制偏移量、延迟 |
| **慢查询** | `slow_log` (支持按客户端、命令采集) | 慢查询日志采集 |
| **Keyspace** | `keyspace_keys/expires/avg_ttl` (按 db) | 各数据库键统计 |
| **自定义命令** | 支持自定义 Redis 命令采集 | 灵活获取特定数据 |

---

### 2.3 MongoDB 监控

**配置文件**: `conf/input.mongodb/mongodb.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **数据库统计** (`enable_db_stats`) | 各数据库大小、集合数、索引数、数据量 |
| **诊断数据** (`enable_diagnostic_data`) | 服务器状态、内存、连接、锁、操作统计 |
| **副本集状态** (`enable_replicaset_status`) | 副本集成员状态、延迟、选举信息 |
| **Top 指标** (`enable_top_metrics`) | 各集合读写操作耗时统计 |
| **索引统计** (`enable_index_stats`) | 索引访问次数、大小 |
| **集合统计** (`enable_coll_stats`) | 集合文档数、大小、存储效率 |

---

### 2.4 PostgreSQL 监控

**配置文件**: `conf/input.postgresql/postgresql.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **连接统计** | 活跃连接数、空闲连接、等待连接 |
| **数据库统计** | 事务提交/回滚数、死锁、冲突 |
| **表统计** | 顺序扫描次数、索引扫描、插入/更新/删除行数 |
| **索引统计** | 索引扫描次数、索引大小 |
| **复制延迟** | 流复制延迟字节数 |
| **自定义查询** | 支持自定义 SQL 查询指标 |

---

### 2.5 Elasticsearch 监控

**配置文件**: `conf/input.elasticsearch/elasticsearch.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **集群健康** (`cluster_health`) | 状态(green/yellow/red)、节点数、分片数、未分配分片 |
| **集群统计** (`cluster_stats`) | 索引数、文档数、存储大小、字段缓存 |
| **节点统计** (`node_stats`) | JVM 内存、GC、线程池、索引、操作系统、文件系统 |
| **索引统计** (`export_indices`) | 各索引文档数、存储大小、搜索/索引操作 |
| **分片统计** (`export_shards`) | 分片级别指标 |
| **ILM 策略** (`export_ilm`) | 索引生命周期管理策略状态 |
| **快照** (`export_snapshots`) | 仓库、快照状态 |
| **数据流** (`export_data_stream`) | 数据流统计 |

---

### 2.6 其他数据库

| 数据库 | 监控内容 |
|--------|----------|
| **Oracle** | 表空间、会话、锁、SQL、ASM、等待事件 |
| **ClickHouse** | 查询性能、合并、复制、分布式表 |
| **SQL Server** | 连接、锁、缓冲区、等待统计 |
| **Greenplum** | 段节点状态、查询性能、资源队列 |

---

## 📨 三、消息队列监控

### 3.1 Kafka 监控

**配置文件**: `conf/input.kafka/kafka.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **Broker 指标** | 消息流入/流出速率、请求处理时间、网络处理器空闲率 |
| **Controller 指标** | 活跃控制器数、离线分区数、UnderReplicated 分区 |
| **副本管理** | 分区 Leader 数、ISR 扩缩容速率、副本延迟 |
| **Topic 指标** | 各 Topic 字节流入/流出、消息数、请求速率 |
| **消费者延迟** | 消费者组延迟、消费速率 |
| **请求指标** | 各类请求(produce/fetch等)的速率和延迟 |
| **日志清理** | 日志清理速率、延迟 |

### 3.2 RabbitMQ 监控

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **概览** | 连接数、通道数、交换机数、队列数、消费者数 |
| **消息统计** | 消息发布/确认/投递/返回速率、磁盘读写字节 |
| **队列深度** | 各队列消息数、就绪/未确认消息 |
| **节点状态** | 内存使用、磁盘使用、文件描述符、Erlang 进程 |

### 3.3 其他消息队列

| 消息队列 | 监控内容 |
|----------|----------|
| **NSQ** | Topic/Channel 深度、消息速率、连接数、超时数 |
| **NATS** | 连接数、订阅数、消息流入/流出、内存使用 |
| **RocketMQ** | 消费偏移量、消费进度、消息堆积 |
| **ActiveMQ** | 队列深度、消费者数、消息入队/出队速率 |
| **Kafka Connect** | 连接器状态、任务状态、偏移量提交 |

---

## 🌐 四、Web 服务监控

### 4.1 Nginx 监控

**配置文件**: `conf/input.nginx/nginx.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **连接状态** | 活跃连接数、已接受/已处理/总请求数 |
| **连接详情** | 读取、写入、等待连接数 |
| **Upstream 检查** | 后端服务器健康状态、活跃/失败检查次数 |

### 4.2 Apache 监控

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **工作进程** | 空闲/忙碌工作进程数 |
| **请求统计** | 每秒请求数、总访问数、总发送字节 |
| **得分板** | 各状态进程数(等待、读取、发送等) |

### 4.3 PHP-FPM 监控

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **进程状态** | 活跃/空闲进程数、总进程数、最大活跃进程数 |
| **请求统计** | 已接受连接数、慢请求数、最大监听队列长度 |
| **队列状态** | 当前监听队列长度、队列满次数 |

### 4.4 HTTP 探测监控

**配置文件**: `conf/input.http_response/http_response.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **可用性** | HTTP 响应码、响应状态(up/down) |
| **性能** | 响应时间(DNS、连接、TLS、首字节、总时间) |
| **内容检查** | 响应体匹配、正则匹配 |
| **证书** | SSL 证书过期时间、颁发者信息 |

### 4.5 网络探测

| 插件 | 监控内容 |
|------|----------|
| **ping** | ICMP 延迟、丢包率 |
| **net_response** | TCP/UDP 端口连通性、响应时间 |
| **dns_query** | DNS 解析时间、解析结果 |
| **whois** | 域名到期时间 |
| **x509_cert** | SSL 证书过期时间、颁发者、主题 |

---

## 🐳 五、容器与 Kubernetes 监控

### 5.1 Docker 监控

**配置文件**: `conf/input.docker/docker.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **容器状态** | 运行中/停止/暂停容器数、容器总数 |
| **容器资源** | CPU 使用、内存使用/限制、网络 IO、块设备 IO |
| **容器详情** | 各容器的 CPU、内存、网络、存储指标 |
| **镜像** | 镜像数量、占用空间 |
| **存储驱动** | 存储驱动信息、数据空间使用 |

### 5.2 Kubernetes 监控

**配置文件**: `conf/input.kubernetes/kubernetes.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **节点资源** | CPU、内存、磁盘、Pod 容量和使用率 |
| **Pod 状态** | Pod 阶段(Running/Pending/Failed)、重启次数 |
| **容器资源** | 各容器 CPU、内存使用/限制 |
| **网络** | Pod 网络流入/流出字节数 |
| **存储卷** | PVC 使用、存储容量 |

### 5.3 cAdvisor 监控

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **容器资源** | CPU 使用(用户/系统/总量)、内存使用(工作集/缓存/限制) |
| **网络统计** | 接收/发送字节数、包数、错误数 |
| **文件系统** | 读写字节数、IOPS |
| **进程** | 进程数、线程数、文件描述符 |

---

## ☁️ 六、云服务监控

### 6.1 阿里云监控

**配置文件**: `conf/input.aliyun/cloud.toml`

**监控产品**:

| 产品 | 监控内容 |
|------|----------|
| **ECS** | CPU、内存、磁盘、网络、负载 |
| **RDS** | 连接数、QPS、TPS、磁盘空间、延迟 |
| **Redis** | 连接数、QPS、内存使用、命中率 |
| **SLB** | 流量、连接数、响应时间、状态码 |
| **OSS** | 存储量、请求数、流量 |
| **CDN** | 流量、带宽、命中率、状态码 |

### 6.2 AWS CloudWatch

**监控产品**:

| 产品 | 监控内容 |
|------|----------|
| **EC2** | CPU、磁盘、网络、状态检查 |
| **RDS** | 连接数、CPU、存储、延迟 |
| **ELB** | 请求数、延迟、HTTP 状态码 |
| **S3** | 请求数、错误率、延迟 |
| **Lambda** | 调用次数、错误率、持续时间 |

### 6.3 Google Cloud

**监控产品**:

| 产品 | 监控内容 |
|------|----------|
| **Compute Engine** | CPU、磁盘、网络、防火墙 |
| **Cloud SQL** | 连接数、查询数、存储 |
| **Cloud Storage** | 请求数、流量、错误率 |

### 6.4 VMware vSphere

**监控内容**:

| 对象 | 监控指标 |
|------|----------|
| **数据中心** | CPU、内存、存储汇总 |
| **集群** | 资源池使用、HA 状态 |
| **主机** | CPU、内存、磁盘、网络、硬件状态 |
| **虚拟机** | CPU、内存、磁盘、网络、电源状态 |
| **数据存储** | 容量、使用率、延迟 |

---

## 🔌 七、网络设备监控

### 7.1 SNMP 通用监控

**配置文件**: `conf/input.snmp/snmp.toml`

**监控能力**:

| 功能 | 说明 |
|------|------|
| **设备发现** | 自动发现 SNMP 设备 |
| **OID 采集** | 支持自定义 OID 列表采集 |
| **Table 采集** | 自动采集 SNMP Table (如接口表) |
| **MIB 支持** | 支持标准 MIB 和私有 MIB |
| **版本支持** | SNMP v1/v2c/v3 |

**典型监控指标**:
- 接口流量(入/出字节数、包数、错误数、丢弃数)
- 设备信息(系统描述、运行时间、联系人)
- CPU/内存使用率
- 存储使用
- 温度/风扇/电源状态

**MIB 支持说明**:

Categraf 的 SNMP 监控**不内置特定品牌的 MIB 文件**，而是采用以下方式工作：

| MIB 类型 | 说明 | 配置方式 |
|----------|------|----------|
| **标准 MIB** | RFC 定义的标准 MIB (如 IF-MIB、RFC1213-MIB) | 自动识别，无需额外配置 |
| **私有 MIB** | 各厂商自定义的 MIB | 需手动加载到 `path` 配置项 |

**标准 MIB (所有品牌通用)**:
```
IF-MIB::ifTable          - 接口表 (流量、状态、速率)
RFC1213-MIB::sysUpTime   - 系统运行时间
RFC1213-MIB::sysName     - 系统名称
HOST-RESOURCES-MIB       - CPU、内存、存储
ENTITY-MIB               - 物理实体 (温度、风扇、电源)
```

**私有 MIB (需手动加载)**:
| 品牌 | 私有 MIB 示例 | 用途 |
|------|---------------|------|
| **华为** | HUAWEI-ENTITY-EXTENT-MIB | 扩展实体信息 |
| **华三** | HH3C-ENTITY-EXT-MIB | 扩展实体信息 |
| **思科** | CISCO-PROCESS-MIB | CPU 进程详情 |
| **锐捷** | RUIJIE-SYSTEM-MIB | 系统信息 |

**MIB 文件加载配置**:
```toml
[[instances]]
# 指定 MIB 文件路径
path = ["/usr/share/snmp/mibs", "/opt/custom-mibs"]
# 选择翻译器: gosmi 或 netsnmp
translator = "gosmi"
```

**支持品牌**: 所有支持标准 SNMP 协议的设备
- 思科 (Cisco)
- 华为 (Huawei)
- 华三 (H3C)
- 锐捷 (Ruijie)
- 中兴 (ZTE)
- 山石网科 (Hillstone)
- 深信服 (Sangfor)
- 绿盟 (NSFOCUS)
- 天融信 (Topsec)
- 迈普 (Maipu)
- 烽火 (Fiberhome)
- 瞻博 (Juniper)
- Arista
- 戴尔 (Dell)
- 惠普 (HP/Aruba)
- 海康威视 (Hikvision)
- 大华 (Dahua)
- 等所有标准 SNMP 设备

---

### 7.2 交换机专用监控 (switch_legacy)

**配置文件**: `conf/input.switch_legacy/switch_legacy.toml`

**插件说明**: 专门用于交换机监控，fork 自 [swcollector](https://github.com/gaochao1/swcollector)，可自动探测网络设备型号

**支持品牌** (自动识别):

| 品牌 | 说明 |
|------|------|
| **华为 (Huawei)** | 全系列交换机、路由器、防火墙 |
| **华三 (H3C)** | 全系列交换机、路由器、防火墙 |
| **思科 (Cisco)** | 全系列交换机、路由器、防火墙 |
| **锐捷 (Ruijie)** | 全系列交换机、路由器 |
| **中兴 (ZTE)** | 交换机、路由器 |
| **迈普 (Maipu)** | 交换机、路由器 |
| **烽火 (Fiberhome)** | 交换机、路由器 |
| **山石网科 (Hillstone)** | 防火墙 |
| **深信服 (Sangfor)** | 防火墙、AC、AF |
| **Juniper** | 交换机、路由器、防火墙 |
| **HPE/Aruba** | 交换机 |
| **Dell** | 交换机 |
| **Ruckus** | 交换机 |
| **D-Link** | 交换机 |
| **TP-Link** | 交换机 |
| **Netgear** | 交换机 |
| **Extreme** | 交换机 |
| **Brocade** | 交换机 |
| **Foundry** | 交换机 |

**监控指标**:

| 指标类别 | 具体指标 | 说明 |
|----------|----------|------|
| **接口流量** | `if_in`, `if_out`, `if_in_speed_percent`, `if_out_speed_percent` | 入/出流量(bps)、带宽利用率 |
| **接口状态** | `if_oper_status`, `if_speed` | 接口状态(Up/Down)、接口速率 |
| **包统计** | `if_in_pkts`, `if_out_pkts` | 入/出单播包速率 |
| **广播包** | `if_in_broadcast_pkt`, `if_out_broadcast_pkt` | 广播包速率 |
| **组播包** | `if_in_multicast_pkt`, `if_out_multicast_pkt` | 组播包速率 |
| **丢包/错包** | `if_in_discards`, `if_out_discards`, `if_in_errors`, `if_out_errors` | 丢弃/错误包统计 |
| **未知协议** | `if_in_unknown_protos` | 未知协议包统计 |
| **队列长度** | `if_out_qlen` | 输出队列长度 |
| **CPU 使用率** | `cpu_util` | 设备 CPU 利用率 |
| **内存使用率** | `mem_util` | 设备内存利用率 |
| **Ping 监控** | `ping_latency_ms`, `ping_packet_loss` | 设备连通性 |
| **自定义 OID** | 支持自定义 OID 采集 | 扩展监控能力 |

**端口信息采集说明**:

switch_legacy 插件可以采集**每个端口**的详细信息，包括：

| 采集项 | 指标名 | 说明 |
|--------|--------|------|
| **端口状态** | `if_oper_status` | 1=Up, 2=Down, 3=Testing, 4=Unknown, 5=Dormant, 6=NotPresent, 7=LowerLayerDown |
| **端口速率** | `if_speed` | 接口速率(bps)，如 1000000000 = 1Gbps |
| **入站流量** | `if_in` | 入站流量速率(bps) |
| **出站流量** | `if_out` | 出站流量速率(bps) |
| **带宽利用率** | `if_in_speed_percent`, `if_out_speed_percent` | 相对于接口速率的百分比 |
| **单播包** | `if_in_pkts`, `if_out_pkts` | 单播包速率(pps) |
| **广播包** | `if_in_broadcast_pkt`, `if_out_broadcast_pkt` | 广播包速率(pps) |
| **组播包** | `if_in_multicast_pkt`, `if_out_multicast_pkt` | 组播包速率(pps) |
| **入站丢包** | `if_in_discards` | 入站丢弃包速率 |
| **出站丢包** | `if_out_discards` | 出站丢弃包速率 |
| **入站错包** | `if_in_errors` | 入站错误包速率 |
| **出站错包** | `if_out_errors` | 出站错误包速率 |
| **未知协议** | `if_in_unknown_protos` | 未知协议包速率 |
| **输出队列** | `if_out_qlen` | 输出队列长度 |

**采集的端口范围**:
- 自动发现设备所有物理端口和逻辑端口
- 支持通过 `ignore_ifaces` 配置排除特定端口（如 Vlanif、Loopback 等）
- 每个端口都有 `ifname` 标签标识端口名称（如 GigabitEthernet0/0/1）
- 可选 `ifindex` 标签标识端口索引

**配置示例** (启用完整端口监控):
```toml
[[instances]]
ips = ["192.168.1.1", "192.168.1.2"]
community = "public"

# 启用接口流量采集
gather_flow_metrics = true

# 启用接口状态采集
gather_oper_status = true

# 启用单播包统计
gather_pkt = true

# 启用广播包统计
gather_broadcast_pkt = true

# 启用组播包统计
gather_multicast_pkt = true

# 启用丢包统计
gather_discards = true

# 启用错包统计
gather_errors = true

# 启用未知协议统计
gather_unknown_protos = true

# 启用输出队列统计
gather_out_qlen = true

# 排除不需要监控的接口
ignore_ifaces = ["Vlanif", "LoopBack", "NULL", "InLoopBack"]

# 添加端口索引标签（可选）
index_tag = true
```

**端口状态值说明**:
```
1 = Up           (端口正常开启)
2 = Down         (端口关闭)
3 = Testing      (测试中)
4 = Unknown      (未知状态)
5 = Dormant      (休眠状态)
6 = NotPresent   (端口不存在)
7 = LowerLayerDown (下层链路故障)
```

**自动识别机制**:

switch_legacy 插件**内置了各品牌的 OID 映射表**，通过 `gaochao1/sw` 库自动识别设备型号：

| 品牌 | 自动识别方式 | 内置 OID 覆盖 |
|------|-------------|--------------|
| **华为** | 自动探测 sysObjectID | CPU、内存、接口流量 |
| **华三** | 自动探测 sysObjectID | CPU、内存、接口流量 |
| **思科** | 自动探测 sysObjectID | CPU、内存、接口流量 |
| **锐捷** | 自动探测 sysObjectID | CPU、内存、接口流量 |
| **其他品牌** | 自动探测 sysObjectID | 通用 OID 适配 |

**内置 OID 映射表详情**:

| 品牌 | Enterprise Number | CPU OID | 内存 OID | 说明 |
|------|-------------------|---------|----------|------|
| **华为 (Huawei)** | 2011 | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5 | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7 | hwEntityCpuUsage / hwEntityMemUsage |
| **华三 (H3C)** | 25506 | 1.3.6.1.4.1.25506.2.6.1.1.1.1.6 | 1.3.6.1.4.1.25506.2.6.1.1.1.1.8 | hh3cEntityCpuUsage / hh3cEntityMemUsage |
| **思科 (Cisco)** | 9 | 1.3.6.1.4.1.9.9.109.1.1.1.1.7 | 1.3.6.1.4.1.9.9.48.1.1.1.5 | cpmCPUTotal5min / ciscoMemoryPoolUsed |
| **锐捷 (Ruijie)** | 4881 | 1.3.6.1.4.1.4881.1.1.10.2.36.1.1.3 | 1.3.6.1.4.1.4881.1.1.10.2.35.1.1.2 | rgCpuUsage / rgRamUsage |
| **中兴 (ZTE)** | 3902 | 1.3.6.1.4.1.3902.3.1.1.1.1.1.0 | 1.3.6.1.4.1.3902.3.1.1.1.2.1.0 | zxCpuUsage / zxMemUsage |
| **迈普 (Maipu)** | 5651 | 1.3.6.1.4.1.5651.2.2.2.1.1.0 | 1.3.6.1.4.1.5651.2.2.2.1.2.0 | mpCpuUsage / mpMemUsage |
| **烽火 (Fiberhome)** | 3807 | 1.3.6.1.4.1.3807.1.1.4.1.0 | 1.3.6.1.4.1.3807.1.1.4.2.0 | fhCpuUsage / fhMemUsage |
| **山石 (Hillstone)** | 28557 | 1.3.6.1.4.1.28557.2.1.1.1.1.0 | 1.3.6.1.4.1.28557.2.1.1.1.2.0 | hsCpuUsage / hsMemUsage |
| **Juniper** | 2636 | 1.3.6.1.4.1.2636.3.1.13.1.8 | 1.3.6.1.4.1.2636.3.1.13.1.11 | jnxOperatingCPU / jnxOperatingBuffer |
| **H3C 旧版** | 2011 | 1.3.6.1.4.1.2011.10.2.6.1.1.1.1.6 | 1.3.6.1.4.1.2011.10.2.6.1.1.1.1.8 | 早期 H3C 设备 |
| **D-Link** | 171 | 1.3.6.1.4.1.171.12.1.1.6.1.0 | 1.3.6.1.4.1.171.12.1.1.2.0 | dlinkCpuUsage / dlinkMemUsage |
| **TP-Link** | 11863 | 1.3.6.1.4.1.11863.1.1.1.1.1.0 | 1.3.6.1.4.1.11863.1.1.1.1.2.0 | tplinkCpuUsage / tplinkMemUsage |
| **Netgear** | 4526 | 1.3.6.1.4.1.4526.10.1.1.1.1.0 | 1.3.6.1.4.1.4526.10.1.1.1.2.0 | ngCpuUsage / ngMemUsage |
| **Extreme** | 1916 | 1.3.6.1.4.1.1916.1.1.1.1.0 | 1.3.6.1.4.1.1916.1.1.1.2.0 | extremeCpuUsage / extremeMemUsage |
| **Brocade** | 1588 | 1.3.6.1.4.1.1588.2.1.1.1.1.0 | 1.3.6.1.4.1.1588.2.1.1.1.2.0 | brocadeCpuUsage / brocadeMemUsage |
| **Dell** | 674 | 1.3.6.1.4.1.674.10895.5000.2.6132.1.1.1.1.0 | 1.3.6.1.4.1.674.10895.5000.2.6132.1.1.1.2.0 | dellCpuUsage / dellMemUsage |
| **HP/Aruba** | 11 | 1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0 | 1.3.6.1.4.1.11.2.14.11.5.1.9.6.2.0 | hpCpuUsage / hpMemUsage |
| **Ruckus** | 25053 | 1.3.6.1.4.1.25053.1.1.1.1.1.0 | 1.3.6.1.4.1.25053.1.1.1.1.2.0 | ruckusCpuUsage / ruckusMemUsage |
| **Foundry** | 1991 | 1.3.6.1.4.1.1991.1.1.2.1.50.0 | 1.3.6.1.4.1.1991.1.1.2.1.55.0 | foundryCpuUsage / foundryMemUsage |

**交换机硬件状态监控 OID (温度/风扇/电源)**:

switch_legacy 插件**默认不采集**温度、风扇、电源等硬件信息，但可以通过 **SNMP 通用插件** 或 **自定义 OID** 方式采集。

**华为交换机硬件 OID**:
```
温度: 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11 (hwEntityTemperature)
风扇状态: 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.15 (hwEntityFanStatus)
电源状态: 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.16 (hwEntityPowerStatus)
```

**华三交换机硬件 OID**:
```
温度: 1.3.6.1.4.1.25506.2.6.1.1.1.1.12 (hh3cEntityTemperature)
风扇状态: 1.3.6.1.4.1.25506.2.6.1.1.1.1.15 (hh3cEntityFanStatus)
电源状态: 1.3.6.1.4.1.25506.2.6.1.1.1.1.16 (hh3cEntityPowerStatus)
```

**思科交换机硬件 OID** (ENTITY-MIB):
```
温度: 1.3.6.1.4.1.9.9.91.1.1.1.1.4 (entSensorValue)
风扇状态: 1.3.6.1.4.1.9.9.91.1.1.1.1.5 (entSensorStatus)
电源状态: 1.3.6.1.4.1.9.9.91.1.1.1.1.6 (entSensorType)
```

**标准 ENTITY-MIB OID (通用)**:
```
实体描述: 1.3.6.1.2.1.47.1.1.1.1.2 (entPhysicalDescr)
实体类型: 1.3.6.1.2.1.47.1.1.1.1.5 (entPhysicalClass)
实体名称: 1.3.6.1.2.1.47.1.1.1.1.7 (entPhysicalName)
```

**硬件监控配置示例** (华为交换机):
```toml
# 使用 SNMP 插件采集硬件信息
[[instances]]
agents = ["udp://192.168.1.1:161"]
version = 2
community = "public"

# 温度
[[instances.field]]
oid = "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11"
name = "temperature"

# 风扇状态
[[instances.field]]
oid = "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.15"
name = "fan_status"

# 电源状态
[[instances.field]]
oid = "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.16"
name = "power_status"
```

**或使用 switch_legacy 自定义 OID**:
```toml
[[instances]]
ips = ["192.168.1.1"]
community = "public"

[[instances.customs]]
metric = "temperature"
OID = "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11"
tags = { sensor = "entity" }

[[instances.customs]]
metric = "fan_status"
OID = "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.15"
tags = { sensor = "fan" }
```

**标准接口流量 OID (所有品牌通用)**:
```
入站字节数: IF-MIB::ifHCInOctets  (1.3.6.1.2.1.31.1.1.1.6)
出站字节数: IF-MIB::ifHCOutOctets (1.3.6.1.2.1.31.1.1.1.10)
入站包数:   IF-MIB::ifHCInUcastPkts  (1.3.6.1.2.1.31.1.1.1.7)
出站包数:   IF-MIB::ifHCOutUcastPkts (1.3.6.1.2.1.31.1.1.1.11)
接口状态:   IF-MIB::ifOperStatus  (1.3.6.1.2.1.2.2.1.8)
接口速率:   IF-MIB::ifHighSpeed   (1.3.6.1.2.1.31.1.1.1.15)
```

**重要说明：交换机、路由器、防火墙的 OID 差异**

| 设备类型 | OID 特点 | 兼容性 |
|----------|----------|--------|
| **交换机** | 各品牌 OID 相对统一 | ✅ 内置 OID 映射表覆盖良好 |
| **路由器** | 部分品牌与交换机相同，部分不同 | ⚠️ 可能需要自定义 OID |
| **防火墙** | 通常使用独立的 OID 分支 | ⚠️ 可能需要自定义 OID |

**华为设备 OID 差异示例**:

| 设备类型 | CPU OID | 内存 OID | 说明 |
|----------|---------|----------|------|
| **交换机 (S系列)** | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5 | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7 | 通用实体 MIB |
| **路由器 (AR系列)** | 1.3.6.1.4.1.2011.6.1.1.1.2.0 | 1.3.6.1.4.1.2011.6.1.2.1.1.2.0 | 旧版 MIB |
| **防火墙 (USG系列)** | 1.3.6.1.4.1.2011.6.1.1.1.2.0 | 1.3.6.1.4.1.2011.6.1.2.1.1.2.0 | 与路由器相同 |

**华三设备 OID 差异示例**:

| 设备类型 | CPU OID | 内存 OID | 说明 |
|----------|---------|----------|------|
| **交换机 (S系列)** | 1.3.6.1.4.1.25506.2.6.1.1.1.1.6 | 1.3.6.1.4.1.25506.2.6.1.1.1.1.8 | hh3cEntity 系列 |
| **路由器 (MSR系列)** | 与交换机相同 | 与交换机相同 | 统一 OID |
| **防火墙 (F系列)** | 与交换机相同 | 与交换机相同 | 统一 OID |

**思科设备 OID 差异示例**:

| 设备类型 | CPU OID | 内存 OID | 说明 |
|----------|---------|----------|------|
| **交换机 (Catalyst)** | 1.3.6.1.4.1.9.9.109.1.1.1.1.7 | 1.3.6.1.4.1.9.9.48.1.1.1.5 | cpmCPUTotal5min |
| **路由器 (ISR系列)** | 与交换机相同 | 与交换机相同 | 统一 OID |
| **防火墙 (ASA)** | 1.3.6.1.4.1.9.9.109.1.1.1.1.7 | 1.3.6.1.4.1.9.9.48.1.1.1.5 | 与交换机相同 |

**使用建议**:

1. **交换机**: 直接使用 `switch_legacy` 插件，内置 OID 映射表覆盖良好
2. **路由器**: 先尝试 `switch_legacy` 插件，如无法采集再使用自定义 OID
3. **防火墙**: 
   - 华为 USG 防火墙：可能需要使用 `1.3.6.1.4.1.2011.6.x` 系列的 OID
   - 华三 F100/F500 系列：通常与交换机 OID 相同
   - 其他品牌：建议使用 SNMP 插件 + 自定义 OID

**自定义 OID 配置示例** (华为防火墙):
```toml
[[instances]]
ips = ["192.168.1.1"]
community = "public"

# 启用自定义 OID 采集
gather_cpu_metrics = false  # 关闭自动采集
gather_mem_metrics = false

[[instances.customs]]
metric = "cpu_util"
OID = "1.3.6.1.4.1.2011.6.1.1.1.2.0"  # 华为防火墙 CPU OID
tags = { type = "firewall" }

[[instances.customs]]
metric = "mem_util"
OID = "1.3.6.1.4.1.2011.6.1.2.1.1.2.0"  # 华为防火墙内存 OID
tags = { type = "firewall" }
```

**工作原理**:
1. 插件通过 SNMP 读取设备的 `sysObjectID` (1.3.6.1.2.1.1.2.0)
2. 根据 sysObjectID 中的 Enterprise Number 识别品牌
3. 自动匹配对应品牌的 CPU/内存 OID 进行采集
4. 接口流量使用标准 IF-MIB OID，所有品牌通用
5. **注意**: 内置 OID 映射表主要针对交换机优化，路由器/防火墙可能需要自定义 OID

**配置特点**:
- 支持 IP 段批量配置 (如 `172.16.4/24`)
- 支持 IP 范围配置 (如 `192.168.56.102-192.168.56.120`)
- **自动识别设备型号和 OID，无需手动配置 MIB**
- 支持并发采集，可配置并发度
- 支持名称映射 (IP 映射为易读名称)
- 支持自定义 OID 扩展监控

---

### 7.3 安全设备监控

#### 7.3.1 防火墙监控

**支持方式**: SNMP 通用监控 + switch_legacy 插件

**支持品牌及监控方式**:

| 品牌 | 监控方式 | CPU/内存 OID | 接口流量 | 特殊说明 |
|------|----------|--------------|----------|----------|
| **华为 USG** | SNMP + 自定义 OID | `1.3.6.1.4.1.2011.6.x` | 标准 IF-MIB | 需自定义 OID |
| **华三 F100/F500** | switch_legacy | 与交换机相同 | 标准 IF-MIB | 直接使用 |
| **山石网科** | switch_legacy | 内置 OID | 标准 IF-MIB | 直接使用 |
| **深信服 AF/AC** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |
| **思科 ASA** | switch_legacy | 与交换机相同 | 标准 IF-MIB | 直接使用 |
| **Juniper SRX** | switch_legacy | 内置 OID | 标准 IF-MIB | 直接使用 |
| **天融信** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |
| **绿盟** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |
| **启明星辰** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |
| **奇安信** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |
| **安恒** | SNMP + 自定义 OID | 需查询设备 MIB | 标准 IF-MIB | 需自定义 OID |

**防火墙特有监控指标** (通过 SNMP Trap):
- 安全策略命中数
- 会话数/并发连接数
- 攻击拦截次数
- VPN 隧道状态
- 高可用性 (HA) 状态切换

**配置示例** (华为 USG 防火墙):
```toml
[[instances]]
ips = ["192.168.1.1"]
community = "public"
gather_cpu_metrics = false
gather_mem_metrics = false

[[instances.customs]]
metric = "cpu_util"
OID = "1.3.6.1.4.1.2011.6.1.1.1.2.0"

[[instances.customs]]
metric = "mem_util"
OID = "1.3.6.1.4.1.2011.6.1.2.1.1.2.0"
```

---

#### 7.3.2 WAF (Web 应用防火墙) 监控

**监控方式**: HTTP 探测 + 日志分析

| WAF 品牌 | 监控方式 | 监控内容 |
|----------|----------|----------|
| **深信服 WAF** | HTTP 探测 | 服务可用性、响应时间 |
| **安恒 WAF** | HTTP 探测 | 服务可用性、响应时间 |
| **启明 WAF** | HTTP 探测 | 服务可用性、响应时间 |
| **绿盟 WAF** | HTTP 探测 | 服务可用性、响应时间 |
| **阿里云 WAF** | 阿里云 API | 访问日志、拦截统计 |
| **腾讯云 WAF** | 腾讯云 API | 访问日志、拦截统计 |
| **F5 ASM** | SNMP + HTTP | 服务状态、攻击统计 |
| **Imperva** | SNMP + HTTP | 服务状态、攻击统计 |

**监控指标**:
- WAF 服务可用性
- HTTP 响应时间
- SSL 证书过期时间 (x509_cert 插件)
- 攻击拦截统计 (通过日志)

---

#### 7.3.3 IDS/IPS 监控

**监控方式**: SNMP Trap + Syslog

| 品牌 | 监控方式 | 告警类型 |
|------|----------|----------|
| **绿盟 IDS** | SNMP Trap | 入侵检测事件 |
| **启明 IDS** | SNMP Trap | 入侵检测事件 |
| **安恒 IDS** | SNMP Trap | 入侵检测事件 |
| **思科 Firepower** | SNMP + Trap | 入侵阻断事件 |
| **Juniper IDP** | SNMP + Trap | 入侵检测事件 |

**典型告警**:
- 高危攻击检测
- 恶意流量阻断
- 策略违规
- 设备故障

---

#### 7.3.4 VPN 设备监控

**监控方式**: SNMP + 接口流量

| VPN 类型 | 监控内容 |
|----------|----------|
| **IPSec VPN** | 隧道状态、流量、错误数 |
| **SSL VPN** | 在线用户数、并发连接数 |
| **MPLS VPN** | 接口流量、路由状态 |

**监控指标**:
- VPN 隧道状态 (Up/Down)
- 隧道流量 (入/出)
- 在线用户数
- 认证失败次数

---

#### 7.3.5 堡垒机监控

**监控方式**: SNMP + 日志

| 品牌 | 监控内容 |
|------|----------|
| **齐治堡垒机** | 系统状态、在线会话数 |
| **绿盟堡垒机** | 系统状态、在线会话数 |
| **安恒堡垒机** | 系统状态、在线会话数 |
| **启明堡垒机** | 系统状态、在线会话数 |

**监控指标**:
- 系统 CPU/内存
- 在线会话数
- 登录失败次数
- 命令审计统计

---

#### 7.3.6 日志审计系统监控

**监控方式**: SNMP + 进程监控

| 品牌 | 监控内容 |
|------|----------|
| **奇安信日志审计** | 系统状态、日志接收速率 |
| **安恒日志审计** | 系统状态、日志接收速率 |
| **启明日志审计** | 系统状态、日志接收速率 |

**监控指标**:
- 系统资源使用率
- 日志接收速率 (EPS)
- 存储使用率
- 告警规则触发数

---

#### 7.3.7 数据库审计监控

**监控方式**: SNMP + 接口流量

| 品牌 | 监控内容 |
|------|----------|
| **安恒数据库审计** | 系统状态、审计会话数 |
| **绿盟数据库审计** | 系统状态、审计会话数 |
| **启明数据库审计** | 系统状态、审计会话数 |

---

#### 7.3.8 漏洞扫描系统监控

**监控方式**: SNMP + API

| 品牌 | 监控内容 |
|------|----------|
| **绿盟 RSAS** | 系统状态、扫描任务数 |
| **启明天镜** | 系统状态、扫描任务数 |
| **安恒明鉴** | 系统状态、扫描任务数 |
| **Nessus** | API 采集 | 任务状态、漏洞统计 |
| **OpenVAS** | API 采集 | 任务状态、漏洞统计 |

---

#### 7.3.9 安全设备监控总结

| 设备类型 | 推荐监控方式 | 难度 |
|----------|--------------|------|
| **防火墙** | switch_legacy / SNMP + 自定义 OID | ⭐⭐ |
| **WAF** | HTTP 探测 + x509_cert | ⭐ |
| **IDS/IPS** | SNMP Trap | ⭐⭐ |
| **VPN** | SNMP + 接口流量 | ⭐⭐ |
| **堡垒机** | SNMP + procstat | ⭐⭐ |
| **日志审计** | SNMP + exec 脚本 | ⭐⭐⭐ |
| **数据库审计** | SNMP + 接口流量 | ⭐⭐ |
| **漏扫系统** | API + SNMP | ⭐⭐⭐ |

**通用配置建议**:
1. **网络层监控**: 所有安全设备都支持 SNMP，可监控 CPU/内存/接口流量
2. **应用层监控**: WAF/堡垒机/日志审计建议通过 HTTP API 或日志分析
3. **告警接收**: 配置 SNMP Trap 接收安全事件告警
4. **证书监控**: WAF/VPN 设备使用 x509_cert 监控 SSL 证书过期

---

### 7.4 视频设备监控

#### 7.4.1 摄像头 (IPC) 监控

**监控方式**: SNMP + Ping + HTTP 探测

**支持品牌**:

| 品牌 | Enterprise Number | 监控方式 | 支持协议 |
|------|-------------------|----------|----------|
| **海康威视 (Hikvision)** | 39165 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **大华 (Dahua)** | 1004849 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **宇视 (Uniview)** | 42646 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **天地伟业 (Tiandy)** | - | SNMP + HTTP | SNMP v2c, HTTP API |
| **英飞拓 (Infinova)** | - | SNMP + HTTP | SNMP v2c, HTTP API |
| **科达 (Kedacom)** | - | SNMP + HTTP | SNMP v2c, HTTP API |
| **华为 (Huawei)** | 2011 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **安讯士 (Axis)** | 368 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **博世 (Bosch)** | 4413 | SNMP + HTTP | SNMP v2c/v3, HTTP API |
| **索尼 (Sony)** | 1347 | SNMP + HTTP | SNMP v2c, HTTP API |

**监控指标**:

| 指标类别 | 具体指标 | 获取方式 |
|----------|----------|----------|
| **设备在线状态** | 连通性、延迟 | Ping |
| **视频流状态** | 码流、帧率、分辨率 | HTTP API / SNMP |
| **存储状态** | SD 卡容量、使用率 | SNMP |
| **系统状态** | CPU、内存、温度 | SNMP |
| **图像质量** | 亮度、对比度、信噪比 | SNMP |
| **告警事件** | 移动侦测、遮挡告警 | SNMP Trap |

**海康威视 SNMP OID 示例**:
```
设备信息: 1.3.6.1.4.1.39165.1.1.0 (设备型号)
CPU 使用率: 1.3.6.1.4.1.39165.1.2.0
内存使用率: 1.3.6.1.4.1.39165.1.3.0
温度: 1.3.6.1.4.1.39165.1.4.0
视频流状态: 1.3.6.1.4.1.39165.1.5.0
SD 卡状态: 1.3.6.1.4.1.39165.1.6.0
```

**大华 SNMP OID 示例**:
```
设备信息: 1.3.6.1.4.1.1004849.1.1.0 (设备型号)
CPU 使用率: 1.3.6.1.4.1.1004849.1.2.0
内存使用率: 1.3.6.1.4.1.1004849.1.3.0
温度: 1.3.6.1.4.1.1004849.1.4.0
视频流状态: 1.3.6.1.4.1.1004849.1.5.0
SD 卡状态: 1.3.6.1.4.1.1004849.1.6.0
```

**配置示例** (海康威视摄像头):
```toml
# 方法1: SNMP 监控
[[instances]]
agents = ["udp://192.168.1.100:161"]
version = 2
community = "public"

[[instances.field]]
oid = "1.3.6.1.4.1.39165.1.2.0"
name = "cpu_util"

[[instances.field]]
oid = "1.3.6.1.4.1.39165.1.3.0"
name = "mem_util"

[[instances.field]]
oid = "1.3.6.1.4.1.39165.1.4.0"
name = "temperature"
```

---

#### 7.4.2 NVR/DVR 监控

**监控方式**: SNMP + HTTP API

**支持品牌**:

| 品牌 | 设备类型 | 监控内容 |
|------|----------|----------|
| **海康威视** | NVR/DVR | 通道状态、存储、CPU、内存 |
| **大华** | NVR/DVR | 通道状态、存储、CPU、内存 |
| **宇视** | NVR | 通道状态、存储、CPU、内存 |
| **科达** | NVR | 通道状态、存储、CPU、内存 |
| **天地伟业** | NVR | 通道状态、存储、CPU、内存 |

**监控指标**:

| 指标类别 | 具体指标 |
|----------|----------|
| **系统状态** | CPU 使用率、内存使用率、温度 |
| **存储状态** | 硬盘容量、使用率、健康状态 |
| **通道状态** | 在线通道数、离线通道数 |
| **录像状态** | 录像计划执行状态、录像完整性 |
| **网络状态** | 网络流量、连接数 |

**海康 NVR SNMP OID 示例**:
```
在线通道数: 1.3.6.1.4.1.39165.2.1.0
总通道数: 1.3.6.1.4.1.39165.2.2.0
硬盘数量: 1.3.6.1.4.1.39165.2.3.0
硬盘总容量: 1.3.6.1.4.1.39165.2.4.0
硬盘已用容量: 1.3.6.1.4.1.39165.2.5.0
CPU 使用率: 1.3.6.1.4.1.39165.2.6.0
内存使用率: 1.3.6.1.4.1.39165.2.7.0
```

---

#### 7.4.3 视频管理平台监控

**监控方式**: HTTP API + 进程监控

| 平台 | 监控内容 |
|------|----------|
| **海康威视 iVMS-8700** | 服务状态、并发连接数、存储状态 |
| **大华 DSS** | 服务状态、并发连接数、存储状态 |
| **宇视 VM** | 服务状态、并发连接数、存储状态 |
| **华为 VCN** | 服务状态、并发连接数、存储状态 |

**监控指标**:
- 平台服务状态 (CMS/DMS/PCS 等)
- 在线设备数
- 在线用户数
- 并发视频流数
- 存储池使用率
- 告警事件数

---

#### 7.4.4 视频设备监控总结

| 设备类型 | 推荐监控方式 | 难度 |
|----------|--------------|------|
| **摄像头 (IPC)** | SNMP + Ping | ⭐⭐ |
| **NVR/DVR** | SNMP + HTTP API | ⭐⭐ |
| **视频管理平台** | HTTP API + procstat | ⭐⭐⭐ |

**通用配置建议**:
1. **基础监控**: 所有摄像头/NVR 都支持 SNMP，可监控 CPU/内存/温度/存储
2. **在线状态**: 使用 Ping 监控设备连通性
3. **视频质量**: 通过 HTTP API 获取码流、帧率等视频参数
4. **告警接收**: 配置 SNMP Trap 接收移动侦测、遮挡等告警
5. **批量配置**: 使用 IP 段批量添加摄像头监控

**注意事项**:
- 部分低端摄像头可能不支持 SNMP，需要通过 Ping 和 HTTP 探测监控
- SNMP 需要在设备 Web 界面手动开启
- 不同型号设备的 OID 可能略有差异，建议查阅设备 MIB 文档

---

### 7.5 gNMI 协议监控

**配置文件**: `conf/input.gnmi/gnmi.toml`

**插件说明**: 支持 gNMI (gRPC Network Management Interface) 协议，用于现代网络设备的遥测数据采集

**支持品牌**:

| 品牌 | 设备系列 | 说明 |
|------|----------|------|
| **思科 (Cisco)** | IOS XR 6.5.1+, NX-OS 9.3+, IOS XE 16.12+ | 全面支持 gNMI |
| **Juniper** | JunOS 18.4+ | 支持 gNMI 和 Juniper Header Extension |
| **Arista** | EOS 4.24+ | 支持 OpenConfig gNMI |
| **诺基亚 (Nokia)** | SR Linux | 支持 gNMI |
| **华为 (Huawei)** | 部分高端设备 | 需确认具体型号支持 |

**监控指标**:

| 指标类别 | 说明 |
|----------|------|
| **接口计数器** | 入/出字节数、包数、错误数、丢弃数、广播/组播包 |
| **接口状态** | 管理状态、操作状态、描述、速率 |
| **QoS 统计** | 队列统计、丢弃统计 |
| **BGP 状态** | 邻居状态、前缀统计 |
| **组件状态** | 温度、电压、风扇转速 |

**采集模式**:
- **sample**: 定期采样
- **on_change**: 变化时推送
- **target_defined**: 设备定义的模式

---

### 7.4 SNMP Trap 接收

**配置文件**: `conf/input.snmp_trap/trap.toml`

**功能**: 接收 SNMP Trap/Inform 告警消息

**支持品牌**: 所有支持 SNMP Trap 的设备
- 防火墙、交换机、路由器、服务器、存储设备等

**典型告警类型**:
- 链路 Up/Down
- CPU/内存阈值告警
- 温度告警
- 电源故障
- 风扇故障
- 安全事件

---

### 7.5 其他网络监控

| 插件 | 监控内容 | 适用场景 |
|------|----------|----------|
| **ping** | ICMP 延迟、丢包率 | 网络连通性探测 |
| **net_response** | TCP/UDP 端口连通性 | 服务可用性探测 |
| **dns_query** | DNS 解析时间 | DNS 服务监控 |
| **ntp** | NTP 时间同步偏移 | 时间同步监控 |
| **chrony** | Chrony 时间同步状态 | 时间同步监控 |
| **arp_packet** | ARP 包监控 | IP 冲突检测 |
| **x509_cert** | SSL 证书过期 | 证书监控 |

---

### 7.6 网络设备监控对比

| 监控方式 | 支持品牌 | 采集协议 | 实时性 | 适用场景 |
|----------|----------|----------|--------|----------|
| **SNMP** | 所有品牌 | SNMP v1/v2c/v3 | 轮询(秒级) | 通用监控，兼容性好 |
| **switch_legacy** | 主流厂商 | SNMP v2c | 轮询(秒级) | 交换机专用，自动识别 |
| **gNMI** | Cisco/Juniper/Arista | gRPC/gNMI | 推送(毫秒级) | 现代设备，高精度遥测 |
| **SNMP Trap** | 所有品牌 | SNMP Trap | 事件触发 | 告警接收 |

---

### 7.7 推荐配置

**中小企业场景** (华为/华三/锐捷交换机):
```toml
# switch_legacy 插件
[[instances]]
ips = ["192.168.1.1-192.168.1.50"]
community = "public"
gather_cpu_metrics = true
gather_mem_metrics = true
gather_flow_metrics = true
```

**大型企业场景** (多品牌混合):
```toml
# SNMP 插件 - 通用监控
[[instances]]
agents = ["udp://192.168.1.1:161", "udp://192.168.1.2:161"]
version = 2
community = "public"

[[instances.table]]
oid = "IF-MIB::ifTable"
name = "interface"
```

**现代网络场景** (Cisco/Arista):
```toml
# gNMI 插件
[[instances]]
addresses = ["192.168.1.1:9339"]
username = "admin"
password = "admin"

[[instances.subscription]]
name = "ifcounters"
path = "/interfaces/interface/state/counters"
subscription_mode = "sample"
sample_interval = "10s"
```

---

## ☕ 八、Java/JMX 监控（通过 Jolokia）

Categraf 通过 **Jolokia** (JMX-HTTP 桥接器) 支持 Java 应用监控。

### 8.1 监控模式

| 模式 | 插件名 | 说明 |
|------|--------|------|
| Agent 模式 | `jolokia_agent` | 直连部署在应用内的 Jolokia Agent |
| Proxy 模式 | `jolokia_proxy` | 通过中央 Jolokia Proxy 访问多个目标 |

### 8.2 JVM 通用监控

**配置文件**: `conf/input.jolokia_agent_misc/java.toml`

**监控指标类别**:

| 指标类别 | 具体指标 | 说明 |
|----------|----------|------|
| **运行时** | `Uptime` | JVM 运行时间 |
| **内存** | `HeapMemoryUsage`, `NonHeapMemoryUsage`, `ObjectPendingFinalizationCount` | 堆内存、非堆内存、待终结对象 |
| **垃圾回收** | `CollectionTime`, `CollectionCount` | GC 次数和耗时 |
| **线程** | `ThreadCount`, `DaemonThreadCount`, `PeakThreadCount`, `TotalStartedThreadCount` | 线程数、守护线程、峰值 |
| **类加载** | `LoadedClassCount`, `UnloadedClassCount`, `TotalLoadedClassCount` | 已加载/卸载类数 |
| **内存池** | `Usage`, `PeakUsage`, `CollectionUsage` | 各内存池使用情况 |

### 8.3 Kafka 监控

**配置文件**: `conf/input.jolokia_agent_misc/kafka.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **Controller** | 活跃控制器、离线分区数 |
| **ReplicaManager** | Leader 数、ISR 变化、副本延迟 |
| **Purgatory** | 延迟操作数(生产/获取) |
| **ZooKeeper** | 会话过期监听 |
| **请求处理** | 各类请求速率和延迟 |
| **Topic 指标** | 各 Topic 字节流入/流出、消息数 |
| **分区指标** | 分区日志大小、UnderReplicated 分区 |

### 8.4 Tomcat 监控

**配置文件**: `conf/input.jolokia_agent_misc/tomcat.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **JVM 指标** | 内存、GC、线程、类加载 |
| **线程池** | 最大线程、当前线程、忙碌线程 |
| **全局请求处理器** | 请求数、字节收发、处理时间、错误数 |
| **Servlet** | 处理时间、错误数、请求数 |
| **JSP** | 重载次数、JSP 数、卸载次数 |
| **缓存** | 命中次数、查找次数 |

### 8.5 其他 Java 中间件

| 中间件 | 监控内容 |
|--------|----------|
| **ActiveMQ** | 队列深度、消费者数、生产者数、消息速率 |
| **Cassandra** | 读写延迟、缓存命中率、Compaction、线程池 |
| **ZooKeeper** | 连接数、延迟、节点数、Watch 数 |
| **Hadoop HDFS** | NameNode/DataNode 状态、块报告、容量 |
| **JBoss/WildFly** | 数据源、线程池、事务、JMS |
| **WebLogic** | 数据源、JMS、EJB、Servlet、线程池 |
| **Bitbucket** | 仓库统计、拉取/推送操作 |
| **Kafka Connect** | 连接器状态、任务状态、偏移量 |

---

## 🛠️ 九、应用中间件监控

### 9.1 Elasticsearch 监控

**配置文件**: `conf/input.elasticsearch/elasticsearch.toml`

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **集群健康** | 状态、节点数、分片数、未分配分片 |
| **节点统计** | JVM、线程池、索引、操作系统、文件系统 |
| **索引统计** | 文档数、存储大小、搜索/索引操作 |
| **ILM** | 生命周期策略状态 |
| **快照** | 仓库、快照状态 |

### 9.2 Jenkins 监控

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **执行器** | 空闲/忙碌执行器数、队列长度 |
| **作业** | 作业数量、构建次数、成功/失败率 |
| **节点** | 在线/离线节点数 |

### 9.3 LDAP 监控

**配置文件**: `conf/input.ldap/ldap.toml`

**支持类型**: OpenLDAP、389 Directory Server

**监控指标类别**:

| 指标类别 | 说明 |
|----------|------|
| **连接** | 当前连接数、最大连接数 |
| **操作** | 搜索、添加、修改、删除操作数 |
| **条目** | 数据库条目数 |
| **缓存** | 条目缓存命中率 |

### 9.4 其他中间件

| 中间件 | 监控内容 |
|--------|----------|
| **Consul** | 服务数、健康检查、KV 存储、Raft 状态 |
| **BIND** | 查询统计、缓存命中率、区域传输 |
| **InfluxDB** | 数据库、分片、写入/查询速率 |
| **Logstash** | 事件处理速率、JVM、管道状态 |
| **HAProxy** | 会话数、流量、后端健康状态 |
| **Supervisor** | 进程状态、运行时间、重启次数 |

---

## 📝 十、日志与文本监控

### 10.1 mtail 日志监控

**配置文件**: `conf/input.mtail/mtail.toml`

**功能**: 从日志文件中提取指标

**典型用法**:
- 统计 HTTP 状态码分布
- 统计错误日志出现次数
- 提取业务指标(如订单量、支付金额)

**示例**:
```mtail
# 统计 Nginx 状态码
counter http_requests_total by status, method

/^(?P<remote_addr>\S+) \S+ \S+ \[\S+ \S+\] "(?P<method>\S+) \S+ \S+" (?P<status>\d{3})/ {
  http_requests_total[$status][$method]++
}
```

### 10.2 其他日志监控

| 插件 | 功能 |
|------|------|
| **filecount** | 监控目录文件数量、总大小、最新修改时间 |
| **exec** | 执行自定义脚本，采集脚本输出 |
| **prometheus** | 采集 Prometheus Exporter 指标 |
| **node_exporter** | 嵌入式 Node Exporter |
| **self_metrics** | Categraf 自身运行指标 |

---

## 📋 十一、其他监控

| 插件 | 监控内容 |
|------|----------|
| **nfsclient** | NFS 客户端挂载统计、读写操作 |
| **ipmi** | 服务器硬件(温度、电压、风扇、电源) |
| **smart** | 硬盘 SMART 健康状态、温度、坏道 |

---

## 📁 配置文件目录结构

```
conf/
├── config.toml              # 主配置文件
├── logs.toml                # 日志采集配置
├── input.{plugin}/          # 各插件配置目录
│   └── {plugin}.toml        # 插件配置文件
└── input.jolokia_agent_misc/ # Java 监控模板
    ├── java.toml
    ├── kafka.toml
    ├── tomcat.toml
    └── ...
```

---

## 🚀 快速开始

### 启用监控插件

1. **复制配置模板**
   ```bash
   cd /path/to/categraf
   cp conf/input.cpu/cpu.toml conf/input.cpu/cpu.toml.active
   ```

2. **编辑配置文件**
   ```toml
   # conf/input.cpu/cpu.toml.active
   [[instances]]
     ## 默认配置即可工作
   ```

3. **测试采集**
   ```bash
   ./categraf --test --inputs cpu
   ```

4. **启动采集**
   ```bash
   ./categraf
   ```

### 常用插件组合

```bash
# 系统基础监控
./categraf --inputs cpu:mem:disk:diskio:net:system

# 数据库监控
./categraf --inputs mysql:redis:postgresql

# Web 服务监控
./categraf --inputs nginx:phpfpm:http_response

# K8s 监控
./categraf --inputs docker:cadvisor:kubernetes
```

---

## 📊 数据输出格式

Categraf 采集的指标统一转换为 **Prometheus 格式**，支持推送到：

- **Nightingale** (推荐)
- **Prometheus** (Remote Write)
- **VictoriaMetrics**
- **Thanos**
- **InfluxDB** (通过转换)

---

## 🔗 相关链接

- **Categraf GitHub**: https://github.com/flashcatcloud/categraf
- **Nightingale 监控**: https://github.com/ccfos/nightingale
- **官方文档**: https://flashcat.cloud/blog/monitor-agent-categraf-introduction/
- **Jolokia 官网**: https://jolokia.org/

---

## 💡 借鉴建议：如何丰富您的网络设备监控

如果您希望借鉴 Categraf 来丰富自己的网络设备监控系统，以下是建议的实施路径：

### 1. 技术架构参考

| 组件 | Categraf 实现 | 借鉴建议 |
|------|---------------|----------|
| **插件架构** | 基于 Go interface 的插件系统 | 设计统一的采集器接口，便于扩展 |
| **配置管理** | TOML 配置文件 + 热加载 | 采用结构化配置，支持动态更新 |
| **数据采集** | 支持多种协议 (SNMP/gNMI/HTTP) | 根据设备类型选择合适协议 |
| **指标处理** | 自动计算速率、百分比 | 实现增量计算和异常值过滤 |
| **标签系统** | 丰富的标签维度 | 设计合理的标签体系，便于查询和分组 |

### 2. 网络设备监控实施步骤

#### 步骤 1: 设备发现与分类
```python
# 示例：自动发现设备类型
def discover_device(ip, community):
    # 读取 sysObjectID (1.3.6.1.2.1.1.2.0)
    oid = "1.3.6.1.2.1.1.2.0"
    sys_object_id = snmp_get(ip, community, oid)
    
    # 根据 Enterprise Number 识别品牌
    if "1.3.6.1.4.1.2011" in sys_object_id:
        return {"brand": "Huawei", "type": "switch"}
    elif "1.3.6.1.4.1.25506" in sys_object_id:
        return {"brand": "H3C", "type": "switch"}
    # ... 其他品牌
```

#### 步骤 2: 建立 OID 映射库
```yaml
# oid_mapping.yaml
huawei:
  switch:
    cpu: "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5"
    memory: "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.7"
    temperature: "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11"
    fan: "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.15"
    power: "1.3.6.1.4.1.2011.5.25.31.1.1.1.1.16"
  firewall:
    cpu: "1.3.6.1.4.1.2011.6.x.x"  # 防火墙使用不同的 OID
    
h3c:
  switch:
    cpu: "1.3.6.1.4.1.25506.2.6.1.1.1.1.6"
    memory: "1.3.6.1.4.1.25506.2.6.1.1.1.1.8"
```

#### 步骤 3: 端口信息采集实现
```python
# 核心逻辑参考
class InterfaceCollector:
    def collect(self, ip, community):
        # 1. 获取接口列表
        if_table = snmp_walk(ip, community, "1.3.6.1.2.1.2.2.1")
        
        # 2. 获取接口流量 (64位计数器)
        in_octets = snmp_walk(ip, community, "1.3.6.1.2.1.31.1.1.1.6")  # ifHCInOctets
        out_octets = snmp_walk(ip, community, "1.3.6.1.2.1.31.1.1.1.10") # ifHCOutOctets
        
        # 3. 获取接口状态
        oper_status = snmp_walk(ip, community, "1.3.6.1.2.1.2.2.1.8")   # ifOperStatus
        
        # 4. 计算速率 (需要保存上次采集值)
        for if_index in if_table:
            rate_in = (in_octets[if_index] - last_in_octets[if_index]) / interval
            rate_out = (out_octets[if_index] - last_out_octets[if_index]) / interval
            
        return metrics
```

#### 步骤 4: 告警规则设计
```yaml
# alert_rules.yaml
rules:
  - name: interface_down
    expr: if_oper_status != 1
    severity: critical
    summary: "接口 {{ $labels.ifname }} 状态 Down"
    
  - name: high_bandwidth_usage
    expr: if_in_speed_percent > 80 or if_out_speed_percent > 80
    severity: warning
    summary: "接口 {{ $labels.ifname }} 带宽利用率超过 80%"
    
  - name: high_error_rate
    expr: rate(if_in_errors[5m]) > 100
    severity: warning
    summary: "接口 {{ $labels.ifname }} 错包率过高"
```

### 3. 核心功能实现建议

| 功能 | 实现要点 | 参考 Categraf |
|------|----------|---------------|
| **自动发现** | 通过 SNMP 读取 sysObjectID 识别设备 | `switch_legacy` 插件 |
| **OID 适配** | 建立品牌-设备类型-OID 映射表 | `gaochao1/sw` 库 |
| **流量计算** | 保存历史值，计算差值和速率 | `gatherFlowMetrics` 方法 |
| **并发采集** | 使用协程池控制并发数 | `semaphore` 实现 |
| **异常处理** | 数据校验、范围检查、错误恢复 | `limitCheck` 函数 |
| **标签体系** | 设备 IP、端口名、索引等维度 | `tags` 设计 |

### 4. 推荐的监控维度

#### 设备层面
- **基础指标**: CPU、内存、温度、风扇、电源
- **连通性**: Ping 延迟、丢包率
- **硬件状态**: 单板状态、光模块状态

#### 端口层面
- **状态**: Up/Down、速率、双工模式
- **流量**: 入/出带宽、利用率、峰值
- **包统计**: 单播/广播/组播包数
- **质量**: 丢包数、错包数、CRC 错误

#### 协议层面
- **路由**: 路由表大小、BGP 邻居状态
- **生成树**: STP 状态、拓扑变化
- **VLAN**: VLAN 配置、MAC 地址表

### 5. 扩展建议

| 扩展方向 | 实现思路 |
|----------|----------|
| **配置管理** | 集成 Ansible/Terraform 实现配置下发 |
| **拓扑发现** | 通过 LLDP/CDP 协议自动发现网络拓扑 |
| **流量分析** | 集成 sFlow/NetFlow 进行流量分析 |
| **配置备份** | 定期备份设备配置，支持对比和恢复 |
| **自动化运维** | 基于监控数据实现自动故障隔离 |

### 6. 开源组件推荐

| 用途 | 推荐组件 | 说明 |
|------|----------|------|
| SNMP 库 | `github.com/gosnmp/gosnmp` | Go 语言 SNMP 库 |
| 交换机采集 | `github.com/gaochao1/sw` | 参考 Categraf 使用的库 |
| 时序数据库 | Prometheus/VictoriaMetrics | 存储监控数据 |
| 可视化 | Grafana | 仪表盘展示 |
| 告警管理 | Alertmanager | 告警路由和通知 |

---

## 📚 附录：常用 OID 速查表

### 标准 MIB-II OID
```
系统信息:
  sysDescr:       1.3.6.1.2.1.1.1.0
  sysObjectID:    1.3.6.1.2.1.1.2.0
  sysUpTime:      1.3.6.1.2.1.1.3.0
  sysContact:     1.3.6.1.2.1.1.4.0
  sysName:        1.3.6.1.2.1.1.5.0

接口信息:
  ifNumber:       1.3.6.1.2.1.2.1.0
  ifTable:        1.3.6.1.2.1.2.2
  ifXTable:       1.3.6.1.2.1.31.1.1

IP 信息:
  ipAdEntAddr:    1.3.6.1.2.1.4.20.1.1
  ipRouteTable:   1.3.6.1.2.1.4.21
```

### 接口状态值
```
1: up(1)              - 接口正常
2: down(2)            - 接口关闭
3: testing(3)         - 测试中
4: unknown(4)         - 未知
5: dormant(5)         - 休眠
6: notPresent(6)      - 不存在
7: lowerLayerDown(7)  - 下层故障
```

### 接口详细数据 OID 列表

#### IF-MIB (标准接口 MIB)
```
接口基本信息 (ifTable - 1.3.6.1.2.1.2.2.1):
  ifIndex:           1.3.6.1.2.1.2.2.1.1    - 接口索引
  ifDescr:           1.3.6.1.2.1.2.2.1.2    - 接口描述
  ifType:            1.3.6.1.2.1.2.2.1.3    - 接口类型
  ifMtu:             1.3.6.1.2.1.2.2.1.4    - MTU 大小
  ifSpeed:           1.3.6.1.2.1.2.2.1.5    - 接口速率 (32位)
  ifPhysAddress:     1.3.6.1.2.1.2.2.1.6    - MAC 地址
  ifAdminStatus:     1.3.6.1.2.1.2.2.1.7    - 管理状态
  ifOperStatus:      1.3.6.1.2.1.2.2.1.8    - 操作状态
  ifLastChange:      1.3.6.1.2.1.2.2.1.9    - 最后状态变化时间
  ifName:            1.3.6.1.2.1.31.1.1.1.1 - 接口名称

接口流量统计 (32位计数器 - 已废弃，建议用 64位):
  ifInOctets:        1.3.6.1.2.1.2.2.1.10   - 入站字节数
  ifInUcastPkts:     1.3.6.1.2.1.2.2.1.11   - 入站单播包数
  ifInNUcastPkts:    1.3.6.1.2.1.2.2.1.12   - 入站非单播包数
  ifInDiscards:      1.3.6.1.2.1.2.2.1.13   - 入站丢弃包数
  ifInErrors:        1.3.6.1.2.1.2.2.1.14   - 入站错误包数
  ifInUnknownProtos: 1.3.6.1.2.1.2.2.1.15   - 入站未知协议包数
  ifOutOctets:       1.3.6.1.2.1.2.2.1.16   - 出站字节数
  ifOutUcastPkts:    1.3.6.1.2.1.2.2.1.17   - 出站单播包数
  ifOutNUcastPkts:   1.3.6.1.2.1.2.2.1.18   - 出站非单播包数
  ifOutDiscards:     1.3.6.1.2.1.2.2.1.19   - 出站丢弃包数
  ifOutErrors:       1.3.6.1.2.1.2.2.1.20   - 出站错误包数
  ifOutQLen:         1.3.6.1.2.1.2.2.1.21   - 输出队列长度

接口扩展统计 (ifXTable - 64位计数器):
  ifHCInOctets:      1.3.6.1.2.1.31.1.1.1.6  - 入站字节数 (64位)
  ifHCInUcastPkts:   1.3.6.1.2.1.31.1.1.1.7  - 入站单播包数 (64位)
  ifHCInMulticastPkts:  1.3.6.1.2.1.31.1.1.1.8  - 入站组播包数 (64位)
  ifHCInBroadcastPkts:  1.3.6.1.2.1.31.1.1.1.9  - 入站广播包数 (64位)
  ifHCOutOctets:     1.3.6.1.2.1.31.1.1.1.10 - 出站字节数 (64位)
  ifHCOutUcastPkts:  1.3.6.1.2.1.31.1.1.1.11 - 出站单播包数 (64位)
  ifHCOutMulticastPkts: 1.3.6.1.2.1.31.1.1.1.12 - 出站组播包数 (64位)
  ifHCOutBroadcastPkts: 1.3.6.1.2.1.31.1.1.1.13 - 出站广播包数 (64位)
  ifHighSpeed:       1.3.6.1.2.1.31.1.1.1.15 - 高速接口速率 (Mbps)
  ifAlias:           1.3.6.1.2.1.31.1.1.1.18 - 接口别名
```

#### EtherLike-MIB (以太网扩展 MIB)
```
以太网接口统计 (dot3StatsTable):
  dot3StatsAlignmentErrors:    1.3.6.1.2.1.10.7.2.1.2  - 对齐错误
  dot3StatsFCSErrors:          1.3.6.1.2.1.10.7.2.1.3  - FCS 错误
  dot3StatsSingleCollisionFrames: 1.3.6.1.2.1.10.7.2.1.4 - 单冲突帧
  dot3StatsMultipleCollisionFrames: 1.3.6.1.2.1.10.7.2.1.5 - 多冲突帧
  dot3StatsSQETestErrors:      1.3.6.1.2.1.10.7.2.1.6  - SQE 测试错误
  dot3StatsDeferredTransmissions: 1.3.6.1.2.1.10.7.2.1.7 - 延迟传输
  dot3StatsLateCollisions:     1.3.6.1.2.1.10.7.2.1.8  - 延迟冲突
  dot3StatsExcessiveCollisions: 1.3.6.1.2.1.10.7.2.1.9 - 过多冲突
  dot3StatsInternalMacTransmitErrors: 1.3.6.1.2.1.10.7.2.1.10 - MAC 发送错误
  dot3StatsCarrierSenseErrors: 1.3.6.1.2.1.10.7.2.1.11 - 载波侦测错误
  dot3StatsFrameTooLongs:      1.3.6.1.2.1.10.7.2.1.13 - 超长帧
  dot3StatsInternalMacReceiveErrors: 1.3.6.1.2.1.10.7.2.1.16 - MAC 接收错误
  dot3StatsSymbolErrors:       1.3.6.1.2.1.10.7.2.1.18 - 符号错误
```

#### Q-BRIDGE-MIB (VLAN 相关)
```
VLAN 统计:
  dot1qTpFdbEntry:             1.3.6.1.2.1.17.7.1.2.2.1 - MAC 地址表
  dot1qVlanStaticName:         1.3.6.1.2.1.17.7.1.4.3.1.1 - VLAN 名称
  dot1qVlanStaticEgressPorts:  1.3.6.1.2.1.17.7.1.4.3.1.2 - VLAN 出口端口
  dot1qVlanForbiddenEgressPorts: 1.3.6.1.2.1.17.7.1.4.3.1.3 - 禁止出口端口
  dot1qVlanStaticUntaggedPorts: 1.3.6.1.2.1.17.7.1.4.3.1.4 - 非标记端口
```

#### 华为私有 MIB (HUAWEI-IF-EXT-MIB)
```
接口扩展信息:
  hwIfMonitorInputRate:        1.3.6.1.4.1.2011.5.25.157.1.1.1.1.1 - 入站速率
  hwIfMonitorOutputRate:       1.3.6.1.4.1.2011.5.25.157.1.1.1.1.2 - 出站速率
  hwIfMonitorInputErrorRate:   1.3.6.1.4.1.2011.5.25.157.1.1.1.1.3 - 入站错误率
  hwIfMonitorOutputErrorRate:  1.3.6.1.4.1.2011.5.25.157.1.1.1.1.4 - 出站错误率
  hwIfMonitorInputBandwidthUtilization: 1.3.6.1.4.1.2011.5.25.157.1.1.1.1.5 - 入站带宽利用率
  hwIfMonitorOutputBandwidthUtilization: 1.3.6.1.4.1.2011.5.25.157.1.1.1.1.6 - 出站带宽利用率
  hwIfFlowControl:             1.3.6.1.4.1.2011.5.25.157.1.1.1.1.7 - 流控状态
  hwIfDuplex:                  1.3.6.1.4.1.2011.5.25.157.1.1.1.1.8 - 双工模式
```

#### 华三私有 MIB (HH3C-IF-EXT-MIB)
```
接口扩展信息:
  hh3cIfMonitorInputRate:      1.3.6.1.4.1.25506.2.70.2.1.1.1.1 - 入站速率
  hh3cIfMonitorOutputRate:     1.3.6.1.4.1.25506.2.70.2.1.1.1.2 - 出站速率
  hh3cIfMonitorInputBandwidthUtilization: 1.3.6.1.4.1.25506.2.70.2.1.1.1.3 - 入站带宽利用率
  hh3cIfMonitorOutputBandwidthUtilization: 1.3.6.1.4.1.25506.2.70.2.1.1.1.4 - 出站带宽利用率
  hh3cIfDuplex:                1.3.6.1.4.1.25506.2.70.2.1.1.1.5 - 双工模式
  hh3cIfFlowControl:           1.3.6.1.4.1.25506.2.70.2.1.1.1.6 - 流控状态
```

### 端口数据分类总结

| 数据类别 | 标准 MIB | 私有 MIB | 说明 |
|----------|----------|----------|------|
| **基础信息** | ifTable/ifXTable | - | 名称、描述、类型、速率、MAC |
| **状态信息** | ifOperStatus/ifAdminStatus | - | Up/Down、管理状态 |
| **流量统计** | ifXTable (64位) | 华为/华三扩展 | 字节数、包数、带宽利用率 |
| **包类型统计** | ifXTable | - | 单播、组播、广播包数 |
| **错误统计** | ifTable | EtherLike-MIB | 丢包、错包、CRC 错误 |
| **队列信息** | ifOutQLen | - | 输出队列长度 |
| **以太网特性** | EtherLike-MIB | - | 冲突、延迟、FCS 错误 |
| **VLAN 信息** | Q-BRIDGE-MIB | - | VLAN 配置、MAC 地址表 |
| **扩展指标** | - | 华为/华三 MIB | 双工模式、流控状态、实时速率 |

---

*本文档基于 Categraf 源码自动生成，如有更新请以官方文档为准。*
