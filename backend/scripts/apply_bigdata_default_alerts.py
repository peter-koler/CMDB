#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def rule(
    *,
    key: str,
    name: str,
    metric: str,
    operator: str,
    threshold,
    level: str,
    period: int,
    times: int,
    mode: str,
    enabled: bool,
    template: str,
    expr: str | None = None,
    rule_type: str = "periodic_metric",
) -> dict:
    return {
        "key": key,
        "name": name,
        "type": rule_type,
        "metric": metric,
        "operator": operator,
        "threshold": threshold,
        "level": level,
        "period": period,
        "times": times,
        "mode": mode,
        "enabled": enabled,
        "expr": expr or f"{metric} {operator} {threshold}",
        "template": template,
    }


def availability_rule(app: str, display_name: str) -> dict:
    metric = f"{app}_server_up"
    return rule(
        key=f"{app}_unavailable",
        name=f"{display_name}实例不可用",
        metric=metric,
        operator="==",
        threshold=0,
        level="critical",
        period=60,
        times=1,
        mode="core",
        enabled=True,
        expr=f"{metric} == 0",
        template="实例不可用",
        rule_type="realtime_metric",
    )


POLICIES: dict[str, list[dict]] = {
    "airflow": [
        availability_rule("airflow", "Airflow"),
        rule(key="airflow_scheduler_unhealthy", name="Airflow调度器不健康", metric="scheduler", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="调度器不健康", expr="scheduler != 'healthy'", rule_type="realtime_metric"),
        rule(key="airflow_metadb_unhealthy", name="Airflow元数据库不健康", metric="metadatabase", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="元数据库不健康", expr="metadatabase != 'healthy'", rule_type="realtime_metric"),
    ],
    "hbase_master": [
        availability_rule("hbase_master", "HBase Master"),
        rule(key="hbase_master_dead_region_server", name="HBase Master存在失联RegionServer", metric="numDeadRegionServers", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="存在失联RegionServer", rule_type="realtime_metric"),
        rule(key="hbase_master_rit_over_threshold", name="HBase Master RIT超阈值", metric="ritCountOverThreshold", operator=">", threshold=0, level="warning", period=300, times=2, mode="core", enabled=True, template="RIT超阈值"),
    ],
    "hbase_regionserver": [
        availability_rule("hbase_regionserver", "HBase RegionServer"),
        rule(key="hbase_rs_slow_put", name="HBase RegionServer慢写请求", metric="slowPutCount", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="慢写请求"),
        rule(key="hbase_rs_request_drop", name="HBase RegionServer请求吞吐异常", metric="totalRequestCount", operator="<", threshold=1, level="warning", period=600, times=2, mode="extended", enabled=False, template="请求吞吐异常"),
    ],
    "hdfs_datanode": [
        availability_rule("hdfs_datanode", "HDFS DataNode"),
        rule(key="hdfs_datanode_remaining_low", name="HDFS DataNode剩余空间不足", metric="Remaining", operator="<", threshold=10737418240, level="critical", period=300, times=1, mode="core", enabled=True, template="剩余空间不足"),
        rule(key="hdfs_datanode_thread_blocked", name="HDFS DataNode阻塞线程偏高", metric="ThreadsBlocked", operator=">", threshold=20, level="warning", period=300, times=2, mode="extended", enabled=False, template="阻塞线程偏高"),
    ],
    "hdfs_namenode": [
        availability_rule("hdfs_namenode", "HDFS NameNode"),
        rule(key="hdfs_namenode_corrupt_blocks", name="HDFS NameNode损坏块存在", metric="CorruptBlocks", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="损坏块存在", rule_type="realtime_metric"),
        rule(key="hdfs_namenode_dead_nodes", name="HDFS NameNode存在失联DataNode", metric="NumDeadDataNodes", operator=">", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="存在失联DataNode"),
    ],
    "hugegraph": [
        availability_rule("hugegraph", "HugeGraph"),
        rule(key="hugegraph_instances_low", name="HugeGraph实例数异常", metric="instances", operator="<", threshold=1, level="critical", period=120, times=1, mode="core", enabled=True, template="实例数异常"),
        rule(key="hugegraph_token_cache_miss", name="HugeGraph token缓存命中下降", metric="token-hugegraph-miss", operator=">", threshold=10000, level="warning", period=600, times=2, mode="extended", enabled=False, template="token缓存命中下降"),
    ],
    "hadoop": [
        availability_rule("hadoop", "Hadoop"),
        rule(key="hadoop_uptime_short", name="Hadoop JVM疑似频繁重启", metric="Uptime", operator="<", threshold=1800000, level="warning", period=300, times=1, mode="core", enabled=True, template="JVM疑似频繁重启"),
        rule(key="hadoop_thread_high", name="Hadoop活跃线程偏高", metric="ThreadCount", operator=">", threshold=500, level="warning", period=300, times=2, mode="extended", enabled=False, template="活跃线程偏高"),
    ],
    "hive": [
        availability_rule("hive", "Hive"),
        rule(key="hive_response_high", name="Hive响应时间偏高", metric="responseTime", operator=">", threshold=2000, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="hive_heap_used_high", name="Hive堆内存使用偏高", metric="used", operator=">", threshold=3221225472, level="warning", period=300, times=2, mode="extended", enabled=False, template="堆内存使用偏高"),
    ],
    "iceberg": [
        availability_rule("iceberg", "Iceberg"),
        rule(key="iceberg_response_high", name="Iceberg响应时间偏高", metric="responseTime", operator=">", threshold=2000, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="iceberg_thread_count_high", name="Iceberg线程数偏高", metric="thread_count", operator=">", threshold=400, level="warning", period=300, times=2, mode="extended", enabled=False, template="线程数偏高"),
    ],
    "clickhouse": [
        availability_rule("clickhouse", "ClickHouse"),
        rule(key="clickhouse_response_high", name="ClickHouse响应时间偏高", metric="responseTime", operator=">", threshold=1500, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="clickhouse_metric_value_missing", name="ClickHouse指标值异常为空", metric="value", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="指标值异常为空", expr="value == ''", rule_type="realtime_metric"),
    ],
    "doris_be": [
        availability_rule("doris_be", "Doris BE"),
        rule(key="doris_be_metric_value_missing", name="Doris BE指标暴露异常", metric="value", operator="==", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="指标暴露异常", expr="value == ''", rule_type="realtime_metric"),
        rule(key="doris_be_disk_pressure", name="Doris BE磁盘压力偏高", metric="value", operator=">", threshold=90, level="warning", period=300, times=2, mode="extended", enabled=False, template="磁盘压力偏高", expr="path != '' && value > 90"),
    ],
    "elasticsearch": [
        availability_rule("elasticsearch", "Elasticsearch"),
        rule(key="es_cluster_status_red", name="Elasticsearch集群状态RED", metric="status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="集群状态RED", expr="status == 'red'", rule_type="realtime_metric"),
        rule(key="es_unassigned_shards", name="Elasticsearch存在未分配分片", metric="unassigned_shards", operator=">", threshold=0, level="warning", period=300, times=2, mode="core", enabled=True, template="存在未分配分片"),
        rule(key="es_heap_used_percent_high", name="Elasticsearch堆内存使用率偏高", metric="heap_used_percent", operator=">", threshold=85, level="warning", period=300, times=2, mode="core", enabled=True, template="堆内存使用率偏高"),
    ],
    "flink": [
        availability_rule("flink", "Flink"),
        rule(key="flink_jobs_failed", name="Flink失败作业存在", metric="jobs_failed", operator=">", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="失败作业存在", rule_type="realtime_metric"),
        rule(key="flink_slot_usage_high", name="Flink Slot使用率偏高", metric="slots_used", operator=">", threshold=0, level="warning", period=300, times=2, mode="core", enabled=True, template="Slot使用率偏高", expr="slots_total > 0 && (slots_used / slots_total) > 0.9"),
    ],
    "influxdb": [
        availability_rule("influxdb", "InfluxDB"),
        rule(key="influxdb_http_error", name="InfluxDB HTTP错误码激增", metric="response_code", operator=">", threshold=499, level="warning", period=300, times=1, mode="core", enabled=True, template="HTTP错误码激增"),
        rule(key="influxdb_bucket_status_abnormal", name="InfluxDB Bucket状态异常", metric="status", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="Bucket状态异常", expr="status != 'active'", rule_type="realtime_metric"),
    ],
    "iotdb": [
        availability_rule("iotdb", "IoTDB"),
        rule(key="iotdb_cluster_status_down", name="IoTDB集群节点状态异常", metric="status", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="集群节点状态异常", expr="status != 'Running'", rule_type="realtime_metric"),
        rule(key="iotdb_connection_high", name="IoTDB连接数偏高", metric="connection", operator=">", threshold=5000, level="warning", period=300, times=2, mode="extended", enabled=False, template="连接数偏高"),
    ],
    "prestodb": [
        availability_rule("prestodb", "PrestoDB"),
        rule(key="prestodb_failed_ratio_high", name="PrestoDB请求失败比例偏高", metric="recentFailureRatio", operator=">", threshold=0.1, level="warning", period=300, times=2, mode="core", enabled=True, template="请求失败比例偏高"),
        rule(key="prestodb_queued_queries_high", name="PrestoDB排队查询偏高", metric="queuedQueries", operator=">", threshold=100, level="warning", period=300, times=2, mode="core", enabled=True, template="排队查询偏高"),
    ],
    "spark": [
        availability_rule("spark", "Spark"),
        rule(key="spark_uptime_short", name="Spark JVM疑似频繁重启", metric="Uptime", operator="<", threshold=1800000, level="warning", period=300, times=1, mode="core", enabled=True, template="JVM疑似频繁重启"),
        rule(key="spark_thread_count_high", name="Spark活跃线程偏高", metric="ThreadCount", operator=">", threshold=500, level="warning", period=300, times=2, mode="extended", enabled=False, template="活跃线程偏高"),
    ],
    "yarn": [
        availability_rule("yarn", "Apache Yarn"),
        rule(key="yarn_lost_nodes", name="Yarn存在丢失节点", metric="NumLostNMs", operator=">", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="存在丢失节点"),
        rule(key="yarn_unhealthy_nodes", name="Yarn存在不健康节点", metric="NumUnhealthyNMs", operator=">", threshold=0, level="warning", period=120, times=1, mode="core", enabled=True, template="存在不健康节点"),
        rule(key="yarn_pending_container_high", name="Yarn待调度容器偏高", metric="PendingContainers", operator=">", threshold=1000, level="warning", period=300, times=2, mode="extended", enabled=False, template="待调度容器偏高"),
    ],
}


def _yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _render_alerts(alerts: list[dict]) -> str:
    lines = ["alerts:"]
    for item in alerts:
        lines.append(f"  - key: {_yaml_scalar(item['key'])}")
        lines.append(f"    name: {_yaml_scalar(item['name'])}")
        lines.append(f"    type: {_yaml_scalar(item['type'])}")
        lines.append(f"    metric: {_yaml_scalar(item['metric'])}")
        lines.append(f"    operator: {_yaml_scalar(item['operator'])}")
        lines.append(f"    threshold: {_yaml_scalar(item['threshold'])}")
        lines.append(f"    level: {_yaml_scalar(item['level'])}")
        lines.append(f"    period: {_yaml_scalar(item['period'])}")
        lines.append(f"    times: {_yaml_scalar(item['times'])}")
        lines.append(f"    mode: {_yaml_scalar(item['mode'])}")
        lines.append(f"    enabled: {_yaml_scalar(item['enabled'])}")
        lines.append(f"    expr: {_yaml_scalar(item['expr'])}")
        lines.append(f"    template: {_yaml_scalar(item['template'])}")
    return "\n".join(lines) + "\n"


def _upsert_alerts(original: str, alerts_block: str) -> str:
    lines = original.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("alerts:"):
            start = idx
            break
    if start is None:
        base = original.rstrip() + "\n\n"
        return base + alerts_block

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        line = lines[idx]
        if line.strip() == "":
            continue
        if not line.startswith(" "):
            end = idx
            break
    return "\n".join(lines[:start]) + ("\n" if start > 0 else "") + alerts_block + "\n".join(lines[end:])


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    templates_dir = root / "templates"
    updated = 0
    for app, alerts in POLICIES.items():
        path = templates_dir / f"app-{app}.yml"
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        merged = _upsert_alerts(raw, _render_alerts(alerts))
        if merged != raw:
            path.write_text(merged, encoding="utf-8")
            updated += 1
    print(f"[bigdata-alerts] updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

