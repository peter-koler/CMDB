# 服务器设备模板迁移 SOP（IPMI2 / 海康ISAPI / 大华 / 宇视 / 群晖NAS / iDRAC）

## 1. 目标

将 HertzBeat 服务器类模板迁移到本项目，并完整落地“模板 + 采集协议 + 默认策略 + 入库同步”。

## 2. 迁移对象

- `ipmi`
- `hikvision_isapi`
- `dahua`
- `uniview`
- `synology_nas`
- `idrac`

## 3. 采集协议映射

- `hikvision_isapi` / `dahua` / `uniview`：`http`（补齐 Digest Auth + xmlPath + config）
- `synology_nas` / `idrac`：`snmp`（复用现有 snmpcollector）
- `ipmi`：`ipmi`（新增 go-ipmi native collector，支持可控 tool fallback）

## 4. 本次新增/改造

1. 模板策略脚本  
- `backend/scripts/apply_server_default_alerts.py`

2. 模板同步脚本  
- `backend/scripts/sync_hertzbeat_server_templates.py`

3. collector 协议  
- `collector-go/internal/protocol/ipmicollector`（新增）
- `collector-go/internal/protocol/redfishcollector`（新增，供后续服务器模板复用）
- `collector-go/internal/protocol/httpcollector`（增强 digest/xmlPath/config）
- `collector-go/tools/ipmitool`（新增，IPMI 二进制打包与校验脚本）

4. 服务端默认策略路由  
- 新增 `server_default_alert_rules` 分发入口

## 5. 执行命令

```bash
cd backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_server_templates.py
```

```bash
cd collector-go
GOCACHE=/tmp/collector-go-gocache GOMODCACHE=/tmp/collector-go-gomodcache go test ./...
```

```bash
cd collector-go
./tools/ipmitool/scripts/install.sh --source /path/to/ipmitool-artifacts
./tools/ipmitool/scripts/verify.sh --require-current
```

## 6. 验收点

1. 模板树中可见 6 个服务器模板。
2. 创建对应任务后能触发 collector 执行。
3. 默认告警策略可一键套用。
4. `metrics/latest` 可读到核心字段（如 IPMI chassis、海康状态、NAS 资源、iDRAC 电源/温度）。

## 7. 变更清单（2026-03-19）

### 7.1 模板迁移与默认策略

- 新增模板：
  - `backend/templates/app-ipmi.yml`
  - `backend/templates/app-hikvision_isapi.yml`
  - `backend/templates/app-dahua.yml`
  - `backend/templates/app-uniview.yml`
  - `backend/templates/app-synology_nas.yml`
  - `backend/templates/app-idrac.yml`
- 新增/更新脚本：
  - `backend/scripts/apply_server_default_alerts.py`
  - `backend/scripts/sync_hertzbeat_server_templates.py`
- 后端默认策略分发与分类接入：
  - `backend/app/services/default_alert_policies.py`
  - `backend/app/routes/monitoring_target.py`
  - `backend/app/__init__.py`

### 7.2 Collector 协议与采集能力

- HTTP 协议增强（摄像头/设备接口）：
  - Digest Auth
  - `xmlPath` 解析
  - `config` 解析
  - 目录：`collector-go/internal/protocol/httpcollector/`
- 新增 Redfish 协议采集器（服务器扩展能力）：
  - 目录：`collector-go/internal/protocol/redfishcollector/`
- 新增 IPMI 协议采集器并接入注册：
  - 目录：`collector-go/internal/protocol/ipmicollector/`
  - 注册：`collector-go/internal/bootstrap/register.go`

### 7.3 IPMI 商用交付能力（重点）

- 采集主路径改为 `go-ipmi` 纯 Go 实现（默认不依赖系统 `ipmitool`）：
  - 依赖：`github.com/bougou/go-ipmi v0.8.1`
  - 文件：
    - `collector-go/internal/protocol/ipmicollector/ipmi.go`
    - `collector-go/internal/protocol/ipmicollector/native_client.go`
    - `collector-go/internal/protocol/ipmicollector/collect_native.go`
    - `collector-go/internal/protocol/ipmicollector/native_chassis.go`
    - `collector-go/internal/protocol/ipmicollector/native_sensor.go`
- 保留可控 tool 回退（仅显式开启）：
  - 环境变量：`COLLECTOR_IPMI_FALLBACK_TOOL=true`
  - 文件：`collector-go/internal/protocol/ipmicollector/collect_tool.go`
- 内置 ipmitool bundle 交付脚本（用于应急/兼容）：
  - `collector-go/tools/ipmitool/README.md`
  - `collector-go/tools/ipmitool/scripts/detect_ipmitool.sh`
  - `collector-go/tools/ipmitool/scripts/install.sh`
  - `collector-go/tools/ipmitool/scripts/verify.sh`
  - `collector-go/start.sh`
  - `manage-services.sh`
  - `.gitignore`（放开 `collector-go/tools/ipmitool/**`）

### 7.4 依赖与 vendoring

- 依赖更新：
  - `collector-go/go.mod`
  - `collector-go/go.sum`
- vendor 更新：
  - `collector-go/vendor/modules.txt`
  - `collector-go/vendor/github.com/bougou/go-ipmi/...`

### 7.5 回归结果

- 在目标环境执行：
  - `cd /Users/peter/Documents/arco/collector-go && go test ./...`
- 结果：全量通过（含 `collector-go/tests`）。

## 8. 扩展：大数据模板迁移（2026-03-19）

### 8.1 迁移范围（18个）

- `airflow`
- `hbase_master`
- `hbase_regionserver`
- `hdfs_datanode`
- `hdfs_namenode`
- `hugegraph`
- `hadoop`
- `hive`
- `iceberg`
- `clickhouse`
- `doris_be`
- `elasticsearch`
- `flink`
- `influxdb`
- `iotdb`
- `prestodb`
- `spark`
- `yarn`

### 8.2 关键实现

1. 模板与策略同步脚本：
- `backend/scripts/sync_hertzbeat_bigdata_templates.py`
- `backend/scripts/apply_bigdata_default_alerts.py`

2. collector 能力补齐：
- `collector-go/internal/protocol/jmxcollector/*`（新增 `jmx` 协议）
- `collector-go/internal/protocol/jdbccollector/*`（新增 `clickhouse` 平台）
- `collector-go/internal/bootstrap/register.go`（注册 `jmx`）

3. 默认策略分发接入：
- `backend/app/services/default_alert_policies.py`（新增 `bigdata_default_alert_rules`）
- `backend/app/routes/monitoring_target.py`（接入 bigdata 策略链路）
- `backend/app/__init__.py`（补默认分类 `bigdata`）

4. 分类统一：
- 所有本次模板统一改写 `category: bigdata`

### 8.3 执行命令

```bash
cd /Users/peter/Documents/arco/backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_bigdata_templates.py
```

```bash
cd /Users/peter/Documents/arco/collector-go
go get github.com/ClickHouse/clickhouse-go/v2@latest
go mod tidy
go mod vendor
go test ./...
```

### 8.4 联调回归（本次补充）

```bash
# collector 协议注册回归（含 jmx/ipmi）
cd /Users/peter/Documents/arco/collector-go
go test ./internal/protocol ./internal/bootstrap

# manager 模板编译回归（含 jmx 与 clickhouse jdbc）
cd /Users/peter/Documents/arco/manager-go
go test ./internal/template ./internal/collector
```
