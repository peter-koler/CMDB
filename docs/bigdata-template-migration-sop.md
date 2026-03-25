# 大数据监控模板迁移 SOP（Airflow/HBase/HDFS/Hadoop/Hive/Iceberg/ClickHouse/Doris BE/ES/Flink/InfluxDB/IoTDB/PrestoDB/Spark/Yarn）

## 1. 目标

将 HertzBeat 大数据类模板迁移到本项目，并完整落地：

- 模板迁移
- collector 采集协议能力补齐
- 默认告警策略（实时 + 周期）
- 分类统一与入库同步

## 2. 本次覆盖范围

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

## 3. 采集协议落地

1. `http` 采集
- 复用并增强已有 `httpcollector`（已支持 `default/jsonPath/prometheus/website/config/xmlPath`）

2. `jdbc` 采集
- 在 `jdbccollector` 增加 `clickhouse` 平台支持（`mysql` + `clickhouse`）

3. `jmx` 采集
- 新增 `jmxcollector` 协议实现（按 `host/port/url/objectName` 拉取 JMX JSON 结构并映射字段）
- 支持 `service:jmx:rmi://...` URL 的 host/port 解析回退

## 4. 分类与策略

1. 分类统一
- 所有本次模板统一写入 `category: bigdata`
- 同步时确保分类存在：`大数据(bigdata)`

2. 默认策略
- 新增 `apply_bigdata_default_alerts.py`
- 每个模板至少包含：
  - 可用性实时规则（`<app>_server_up == 0`）
  - 业务/性能周期规则（按服务指标差异化阈值）

## 5. 新增/修改文件

### 5.1 backend

- `backend/scripts/apply_bigdata_default_alerts.py`
- `backend/scripts/sync_hertzbeat_bigdata_templates.py`
- `backend/app/services/default_alert_policies.py`
- `backend/app/routes/monitoring_target.py`
- `backend/app/__init__.py`

### 5.2 collector-go

- `collector-go/internal/protocol/jmxcollector/`
  - `jmx.go`
  - `config.go`
  - `http_fetch.go`
  - `collect_map.go`
  - `config_test.go`
  - `collect_map_test.go`
- `collector-go/internal/protocol/jdbccollector/jdbc.go`
- `collector-go/internal/protocol/jdbccollector/clickhouse.go`
- `collector-go/internal/protocol/jdbccollector/timeout.go`
- `collector-go/internal/protocol/jdbccollector/clickhouse_test.go`
- `collector-go/internal/bootstrap/register.go`

### 5.3 templates

- `backend/templates/app-airflow.yml`
- `backend/templates/app-hbase_master.yml`
- `backend/templates/app-hbase_regionserver.yml`
- `backend/templates/app-hdfs_datanode.yml`
- `backend/templates/app-hdfs_namenode.yml`
- `backend/templates/app-hugegraph.yml`
- `backend/templates/app-hadoop.yml`
- `backend/templates/app-hive.yml`
- `backend/templates/app-iceberg.yml`
- `backend/templates/app-clickhouse.yml`
- `backend/templates/app-doris_be.yml`
- `backend/templates/app-elasticsearch.yml`
- `backend/templates/app-flink.yml`
- `backend/templates/app-influxdb.yml`
- `backend/templates/app-iotdb.yml`
- `backend/templates/app-prestodb.yml`
- `backend/templates/app-spark.yml`
- `backend/templates/app-yarn.yml`

## 6. 执行命令

### 6.1 模板同步

```bash
cd /Users/peter/Documents/arco/backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_bigdata_templates.py
```

### 6.2 collector 依赖补齐（ClickHouse JDBC）

```bash
cd /Users/peter/Documents/arco/collector-go
go get github.com/ClickHouse/clickhouse-go/v2@latest
go mod tidy
go mod vendor
```

### 6.3 回归

```bash
cd /Users/peter/Documents/arco/collector-go
go test ./...
```

```bash
cd /Users/peter/Documents/arco/backend
python3 -m compileall app scripts
```

## 7. 验收点

1. 模板树出现 `bigdata` 分类，并可见 18 个模板。
2. 新建目标时可正常下发任务，`metrics/latest` 有数据回传。
3. 默认策略可一键应用，包含实时与周期两类。
4. `clickhouse`、`hadoop`、`spark` 模板在 collector 侧分别命中 `jdbc/jmx` 采集器。

