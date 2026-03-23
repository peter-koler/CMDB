# collector-go 设计与实现说明

本项目基于 `docs/hertzbeat-collector-analysis.md` 的分析结论，使用 Go 实现一个轻量、高性能、跨平台的采集器。

## 1. 目标与设计原则

- 参考 HertzBeat Collector 的核心思想：`Manager 负责下发，Collector 负责本地循环调度`。
- 兼顾扩展性和运行性能：时间轮 + 协程池 + 协议 SPI 注册。
- 协议与调度解耦：新增协议不修改核心调度逻辑。
- 保持跨平台：优先使用 Go 标准库；系统差异点单独处理。

## 2. 架构总览

```
Manager(gRPC Stream)
    -> Collector gRPC Transport
    -> Dispatcher
    -> Hashed Wheel Timer
    -> WorkerPool
    -> Protocol Collector(http/icmp/snmp/jdbc/linux)
    -> Transform Pipeline
    -> Queue(memory | kafka)
    -> gRPC Stream Report 回传
```

对应 HertzBeat 分工：
- `Manager`: 负责任务选择与一次下发，不负责每轮计时。
- `Collector`: 接收任务后本地按 interval 持续执行。

## 3. 模块说明

### 3.1 gRPC 通信层

- Proto: `proto/collector.proto`
- 生成代码: `internal/pb/collector.pb.go`, `internal/pb/collector_grpc.pb.go`
- 服务实现: `internal/transport/grpc_server.go`

实现点：
- 双向 Stream 长连接。
- Manager -> Collector: `upsert/delete/heartbeat`。
- Collector -> Manager: `report/heartbeat`。
- 支持心跳检测和任务实时下发。

### 3.2 调度引擎（Hashed Wheel Timer）

- 文件: `internal/scheduler/wheel.go`
- 采用统一 tick 驱动桶轮转，避免“每任务一个 sleep goroutine”。
- 支持高密度周期任务调度，贴近 HertzBeat 时间轮思路。

### 3.3 并发控制（WorkerPool）

- 文件: `internal/worker/pool.go`
- 固定 worker + 有界队列，限制峰值并发。
- 避免任务集中触发时打爆采集端或目标端。

### 3.4 任务分发与执行

- 文件: `internal/dispatcher/dispatcher.go`
- 流程：
  1. 注册 Job 到时间轮。
  2. 到期后提交到 WorkerPool。
  3. 按协议类型查找 Collector。
  4. 执行采集、转换字段、推送队列。

### 3.5 协议 SPI 注册机制

- 注册中心: `internal/protocol/registry.go`
- 自动导入: `internal/bootstrap/register.go`
- 机制: 每个协议包通过 `init()` 调用 `protocol.Register(...)`

已实现协议：
- `http`: `internal/protocol/httpcollector/http.go`
- `icmp`: `internal/protocol/pingcollector/ping.go`
- `snmp`: `internal/protocol/snmpcollector/snmp.go`
- `jdbc`: `internal/protocol/jdbccollector/jdbc.go`
- `linux`: `internal/protocol/linuxcollector/linux.go`

说明：
- `icmp` 使用系统 `ping`，兼容 Windows/macOS/Linux 参数差异。
- `snmp` 当前通过 `snmpget` 命令适配，便于离线环境部署。
- `jdbc` 当前为外部 SQL 命令适配器，后续可替换为原生 driver。

### 3.6 数据处理与队列

- 转换: `internal/pipeline/transform.go`
- 队列接口与实现:
  - `internal/queue/queue.go`
  - `internal/queue/memory.go`
  - `internal/queue/kafka_exec.go`
  - `internal/queue/fanout.go`
  - `internal/queue/factory.go`

支持：
- `memory`: 本地内存队列。
- `kafka`: fanout 模式，内存保留本地消费能力，同时异步转发到 Kafka。

## 4. 配置与启动

配置文件：`config/collector.json`

关键项：
- `server.addr`: gRPC 监听地址
- `scheduler.tick_ms/wheel_size`: 时间轮参数
- `worker.size/queue_size`: 协程池参数
- `queue.backend`: `memory` 或 `kafka`
- `stream.heartbeat_ms`: 心跳周期
- `logging.level`: 日志级别（`info` / `debug`）

说明：
- Collector 的调试日志级别已改为只读取配置文件 `logging.level`，不再依赖系统环境变量。

启动：

```bash
go run ./cmd/collector -config config/collector.json
```

### 4.1 IPMI 采集二进制策略（商用默认）

- 默认使用内置 `go-ipmi`（纯 Go）进行采集，不依赖系统 `ipmitool`。
- 采集器支持可控回退：设置 `COLLECTOR_IPMI_FALLBACK_TOOL=true` 时，native 失败后回退到内置 `ipmitool`。
- Collector 启动时优先使用内置路径：
  - `tools/ipmitool/bin/ipmitool-<os>-<arch>`
  - `tools/ipmitool/bin/ipmitool`
- 可通过 `COLLECTOR_IPMITOOL_BIN` 指定企业自带二进制绝对路径。
- 仅在显式开启 `COLLECTOR_ALLOW_SYSTEM_IPMITOOL=true` 时，才回退系统 `PATH`。

建议部署规范：
- 将平台签名后的 `ipmitool` 二进制随 collector 一起打包到 `tools/ipmitool/bin/`。
- 对 Linux/macOS 确保执行权限（`chmod +x`）。
- 将镜像/安装包交付链路纳入安全审计，避免运行节点依赖系统软件版本漂移。

交付脚本：
- 安装 bundle：`./tools/ipmitool/scripts/install.sh --source /path/to/ipmitool-artifacts`
- 发布前校验：`./tools/ipmitool/scripts/verify.sh --require-current`
- 详细规则：`tools/ipmitool/README.md`

Manager 示例客户端：

```bash
go run ./cmd/manager-sim -addr 127.0.0.1:50051
```

## 5. 回归测试

已覆盖核心路径：
- 时间轮周期调度
- WorkerPool 并发上限
- 协议注册有效性
- 队列后端工厂选择
- gRPC 一次下发后 Collector 本地循环执行

执行：

```bash
go test ./...
```

## 6. 与 analysis.md 的对应关系

- `Manager 下发一次，Collector 本地循环`: 已实现。
- `Hashed Wheel Timer 调度`: 已实现。
- `WorkerPool 并发控制`: 已实现。
- `SPI 协议扩展`: 已实现。
- `到期 -> 执行 -> 转换 -> 队列`: 已实现。
- `跨平台考虑`: 已覆盖路径处理与 ICMP 差异。
- `gRPC Stream + 心跳 + 实时下发`: 已实现。

## 7. 当前边界与后续建议

- `jdbc/snmp` 当前是命令适配模式，建议下一步补原生库实现。
- Kafka 当前使用 `kcat` 执行器，建议后续接入原生 Go Kafka client。
- 生产环境建议补充：重试策略、限流策略、鉴权与 TLS、任务幂等与持久化。
