#!/usr/bin/env python3
"""
为数据库模板写入差异化默认告警策略（alerts）。

当前默认阈值档位：中档（medium）

执行方式:
  cd backend
  PYTHONPATH=. python scripts/apply_db_default_alerts.py
"""

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
        template="实例不可用",
        expr=f"{metric} == 0",
        rule_type="realtime_metric",
    )


def pg_family_policies(app: str, display_name: str) -> list[dict]:
    return [
        availability_rule(app, display_name),
        rule(key=f"{app}_deadlocks_detected", name=f"{display_name}检测到死锁", metric="deadlocks", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="检测到死锁", rule_type="realtime_metric"),
        rule(key=f"{app}_conflicts_detected", name=f"{display_name}检测到冲突", metric="conflicts", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="检测到冲突"),
        rule(key=f"{app}_running_sessions_high", name=f"{display_name}运行会话数偏高", metric="running", operator=">", threshold=120, level="warning", period=300, times=2, mode="core", enabled=True, template="运行会话数偏高"),
        rule(key=f"{app}_active_sessions_high", name=f"{display_name}活跃会话数偏高", metric="active", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="活跃会话数偏高"),
        rule(key=f"{app}_state_blocked_high", name=f"{display_name}阻塞状态会话过多", metric="num", operator=">", threshold=30, level="warning", period=300, times=2, mode="extended", enabled=False, template="阻塞状态会话过多"),
        rule(key=f"{app}_blk_read_time_high", name=f"{display_name}块读取耗时过高", metric="blk_read_time", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="块读取耗时过高"),
        rule(key=f"{app}_blk_write_time_high", name=f"{display_name}块写入耗时过高", metric="blk_write_time", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="块写入耗时过高"),
        rule(key=f"{app}_query_avg_time_high", name=f"{display_name}平均SQL耗时过高", metric="avg_time", operator=">", threshold=500, level="warning", period=600, times=2, mode="extended", enabled=False, template="平均SQL耗时过高"),
        rule(key=f"{app}_cache_hit_ratio_low", name=f"{display_name}缓存命中率偏低", metric="ratio", operator="<", threshold=95, level="warning", period=600, times=2, mode="core", enabled=True, template="缓存命中率偏低", expr="ratio < 95"),
        rule(key=f"{app}_checkpoint_sync_high", name=f"{display_name}检查点同步耗时过高", metric="checkpoint_sync_time", operator=">", threshold=1000, level="warning", period=600, times=2, mode="extended", enabled=False, template="检查点同步耗时过高"),
        rule(key=f"{app}_rollback_high", name=f"{display_name}回滚次数过多", metric="rollbacks", operator=">", threshold=100, level="warning", period=600, times=2, mode="extended", enabled=False, template="回滚次数过多"),
    ]


def opengauss_policies() -> list[dict]:
    app = "opengauss"
    name = "OpenGauss"
    return [
        availability_rule(app, name),
        rule(key="opengauss_deadlocks_detected", name="OpenGauss检测到死锁", metric="deadlocks", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="检测到死锁", rule_type="realtime_metric"),
        rule(key="opengauss_conflicts_detected", name="OpenGauss检测到冲突", metric="conflicts", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="检测到冲突"),
        rule(key="opengauss_running_sessions_high", name="OpenGauss运行会话数偏高", metric="running", operator=">", threshold=120, level="warning", period=300, times=2, mode="core", enabled=True, template="运行会话数偏高"),
        rule(key="opengauss_running_sessions_critical", name="OpenGauss运行会话数过高", metric="running", operator=">", threshold=180, level="critical", period=300, times=2, mode="extended", enabled=False, template="运行会话数过高"),
        rule(key="opengauss_blk_read_time_high", name="OpenGauss块读取耗时过高", metric="blk_read_time", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="块读取耗时过高"),
        rule(key="opengauss_blk_write_time_high", name="OpenGauss块写入耗时过高", metric="blk_write_time", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="块写入耗时过高"),
        rule(key="opengauss_blk_read_burst", name="OpenGauss物理读突增", metric="blks_read", operator=">", threshold=10000, level="warning", period=300, times=2, mode="extended", enabled=False, template="物理读突增"),
        rule(key="opengauss_blk_hit_ratio_low", name="OpenGauss块命中率偏低", metric="blks_hit", operator="<", threshold=95, level="warning", period=600, times=2, mode="core", enabled=True, template="块命中率偏低", expr="((blks_hit + blks_read) > 0) && ((blks_hit / (blks_hit + blks_read)) * 100 < 95)"),
        rule(key="opengauss_blk_hit_ratio_critical", name="OpenGauss块命中率过低", metric="blks_hit", operator="<", threshold=90, level="critical", period=600, times=2, mode="extended", enabled=False, template="块命中率过低", expr="((blks_hit + blks_read) > 0) && ((blks_hit / (blks_hit + blks_read)) * 100 < 90)"),
        rule(key="opengauss_max_connections_small", name="OpenGauss最大连接数配置偏低", metric="max_connections", operator="<", threshold=200, level="info", period=3600, times=1, mode="extended", enabled=False, template="最大连接数配置偏低"),
    ]


def mariadb_policies() -> list[dict]:
    app = "mariadb"
    name = "MariaDB"
    return [
        availability_rule(app, name),
        rule(key="mariadb_conn_util_high", name="MariaDB连接利用率偏高", metric="max_used_connections", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="连接利用率偏高", expr="(max_connections > 0) && ((max_used_connections / max_connections) * 100 > 80)"),
        rule(key="mariadb_conn_util_critical", name="MariaDB连接利用率过高", metric="max_used_connections", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="连接利用率过高", expr="(max_connections > 0) && ((max_used_connections / max_connections) * 100 > 90)"),
        rule(key="mariadb_threads_running_high", name="MariaDB活动线程偏高", metric="threads_running", operator=">", threshold=60, level="warning", period=300, times=2, mode="core", enabled=True, template="活动线程偏高"),
        rule(key="mariadb_threads_running_critical", name="MariaDB活动线程过高", metric="threads_running", operator=">", threshold=120, level="critical", period=300, times=1, mode="extended", enabled=False, template="活动线程过高"),
        rule(key="mariadb_aborted_connects_high", name="MariaDB异常连接增长", metric="aborted_connects", operator=">", threshold=10, level="warning", period=300, times=2, mode="core", enabled=True, template="异常连接增长"),
        rule(key="mariadb_aborted_clients_high", name="MariaDB异常客户端增长", metric="aborted_clients", operator=">", threshold=10, level="warning", period=300, times=2, mode="extended", enabled=False, template="异常客户端增长"),
        rule(key="mariadb_innodb_hit_low", name="MariaDB InnoDB命中率偏低", metric="innodb_buffer_hit_rate", operator="<", threshold=95, level="warning", period=600, times=2, mode="core", enabled=True, template="InnoDB命中率偏低"),
        rule(key="mariadb_query_cache_hit_low", name="MariaDB查询缓存命中率偏低", metric="query_cache_hit_rate", operator="<", threshold=60, level="warning", period=600, times=2, mode="extended", enabled=False, template="查询缓存命中率偏低"),
        rule(key="mariadb_tmp_disk_tables_high", name="MariaDB磁盘临时表过多", metric="created_tmp_disk_tables", operator=">", threshold=100, level="warning", period=300, times=2, mode="core", enabled=True, template="磁盘临时表过多"),
        rule(key="mariadb_table_locks_waited", name="MariaDB表锁等待出现", metric="table_locks_waited", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="表锁等待出现"),
        rule(key="mariadb_select_scan_high", name="MariaDB全表扫描偏多", metric="select_scan", operator=">", threshold=1000, level="warning", period=600, times=2, mode="extended", enabled=False, template="全表扫描偏多"),
        rule(key="mariadb_sort_merge_high", name="MariaDB排序合并次数偏高", metric="sort_merge_passes", operator=">", threshold=50, level="warning", period=600, times=2, mode="extended", enabled=False, template="排序合并次数偏高"),
        rule(key="mariadb_slow_query_detected", name="MariaDB慢查询出现", metric="query_time", operator=">", threshold=1000, level="warning", period=300, times=1, mode="extended", enabled=False, template="慢查询出现"),
    ]


def sqlserver_policies() -> list[dict]:
    app = "sqlserver"
    name = "SQLServer"
    return [
        availability_rule(app, name),
        rule(key="sqlserver_connections_high", name="SQLServer连接数偏高", metric="user_connection", operator=">", threshold=300, level="warning", period=300, times=2, mode="core", enabled=True, template="连接数偏高"),
        rule(key="sqlserver_connections_critical", name="SQLServer连接数过高", metric="user_connection", operator=">", threshold=500, level="critical", period=300, times=1, mode="core", enabled=True, template="连接数过高"),
        rule(key="sqlserver_buffer_hit_low", name="SQLServer缓存命中率偏低", metric="buffer_cache_hit_ratio", operator="<", threshold=95, level="warning", period=300, times=2, mode="core", enabled=True, template="缓存命中率偏低"),
        rule(key="sqlserver_buffer_hit_critical", name="SQLServer缓存命中率过低", metric="buffer_cache_hit_ratio", operator="<", threshold=90, level="critical", period=300, times=2, mode="extended", enabled=False, template="缓存命中率过低"),
        rule(key="sqlserver_ple_low", name="SQLServer页生命周期偏低", metric="page_life_expectancy", operator="<", threshold=300, level="warning", period=300, times=2, mode="core", enabled=True, template="页生命周期偏低"),
        rule(key="sqlserver_ple_critical", name="SQLServer页生命周期过低", metric="page_life_expectancy", operator="<", threshold=120, level="critical", period=300, times=2, mode="extended", enabled=False, template="页生命周期过低"),
        rule(key="sqlserver_page_reads_high", name="SQLServer页面读取速率高", metric="page_reads_sec", operator=">", threshold=5000, level="warning", period=300, times=2, mode="core", enabled=True, template="页面读取速率高"),
        rule(key="sqlserver_page_writes_high", name="SQLServer页面写入速率高", metric="page_writes_sec", operator=">", threshold=3000, level="warning", period=300, times=2, mode="extended", enabled=False, template="页面写入速率高"),
        rule(key="sqlserver_checkpoint_pages_high", name="SQLServer检查点脏页刷新偏高", metric="checkpoint_pages_sec", operator=">", threshold=1000, level="warning", period=300, times=2, mode="extended", enabled=False, template="检查点脏页刷新偏高"),
        rule(key="sqlserver_target_pages_gap", name="SQLServer目标页与数据库页偏差过大", metric="database_pages", operator="<", threshold=80, level="warning", period=600, times=2, mode="extended", enabled=False, template="目标页与数据库页偏差过大", expr="(target_pages > 0) && ((database_pages / target_pages) * 100 < 80)"),
    ]


def db2_policies() -> list[dict]:
    app = "db2"
    name = "DB2"
    return [
        availability_rule(app, name),
        rule(key="db2_tablespace_used_high", name="DB2表空间使用率偏高", metric="used_percentage", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="表空间使用率偏高"),
        rule(key="db2_tablespace_used_critical", name="DB2表空间使用率过高", metric="used_percentage", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="表空间使用率过高"),
        rule(key="db2_tablespace_free_low", name="DB2表空间剩余容量不足", metric="free", operator="<", threshold=10, level="warning", period=600, times=2, mode="extended", enabled=False, template="表空间剩余容量不足", expr="(total > 0) && ((free / total) * 100 < 10)"),
        rule(key="db2_waiting_locks_detected", name="DB2出现锁等待", metric="waiting_locks", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="出现锁等待"),
        rule(key="db2_waiting_locks_critical", name="DB2锁等待过多", metric="waiting_locks", operator=">", threshold=10, level="critical", period=300, times=1, mode="core", enabled=True, template="锁等待过多"),
        rule(key="db2_process_count_high", name="DB2进程数偏高", metric="process_count", operator=">", threshold=200, level="warning", period=300, times=2, mode="core", enabled=True, template="进程数偏高"),
        rule(key="db2_process_count_critical", name="DB2进程数过高", metric="process_count", operator=">", threshold=400, level="critical", period=300, times=1, mode="extended", enabled=False, template="进程数过高"),
        rule(key="db2_avg_exec_time_high", name="DB2平均执行耗时偏高", metric="avg_exe_time", operator=">", threshold=300, level="warning", period=600, times=2, mode="extended", enabled=False, template="平均执行耗时偏高"),
        rule(key="db2_avg_exec_time_critical", name="DB2平均执行耗时过高", metric="avg_exe_time", operator=">", threshold=800, level="critical", period=600, times=2, mode="extended", enabled=False, template="平均执行耗时过高"),
        rule(key="db2_status_count_high", name="DB2异常状态计数偏高", metric="count", operator=">", threshold=1000, level="warning", period=300, times=2, mode="extended", enabled=False, template="异常状态计数偏高"),
    ]


def tidb_policies() -> list[dict]:
    app = "tidb"
    name = "TiDB"
    return [
        availability_rule(app, name),
        rule(key="tidb_connections_high", name="TiDB连接数偏高", metric="connections", operator=">", threshold=400, level="warning", period=300, times=2, mode="core", enabled=True, template="连接数偏高"),
        rule(key="tidb_connections_critical", name="TiDB连接数过高", metric="connections", operator=">", threshold=700, level="critical", period=300, times=1, mode="core", enabled=True, template="连接数过高"),
        rule(key="tidb_conn_util_high", name="TiDB连接利用率偏高", metric="connections", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="连接利用率偏高", expr="(max_connections > 0) && ((connections / max_connections) * 100 > 80)"),
        rule(key="tidb_conn_util_critical", name="TiDB连接利用率过高", metric="connections", operator=">", threshold=90, level="critical", period=300, times=1, mode="extended", enabled=False, template="连接利用率过高", expr="(max_connections > 0) && ((connections / max_connections) * 100 > 90)"),
        rule(key="tidb_store_usage_high", name="TiDB存储使用率偏高", metric="used_size", operator=">", threshold=80, level="warning", period=600, times=2, mode="core", enabled=True, template="存储使用率偏高", expr="(capacity > 0) && ((used_size / capacity) * 100 > 80)"),
        rule(key="tidb_store_usage_critical", name="TiDB存储使用率过高", metric="used_size", operator=">", threshold=90, level="critical", period=600, times=1, mode="core", enabled=True, template="存储使用率过高", expr="(capacity > 0) && ((used_size / capacity) * 100 > 90)"),
        rule(key="tidb_available_low", name="TiDB剩余容量不足", metric="available", operator="<", threshold=21474836480, level="warning", period=600, times=2, mode="core", enabled=True, template="剩余容量不足"),
        rule(key="tidb_available_critical", name="TiDB剩余容量严重不足", metric="available", operator="<", threshold=10737418240, level="critical", period=600, times=1, mode="extended", enabled=False, template="剩余容量严重不足"),
        rule(key="tidb_uptime_short", name="TiDB节点疑似频繁重启", metric="uptime", operator="<", threshold=3600, level="warning", period=600, times=1, mode="extended", enabled=False, template="节点疑似频繁重启"),
        rule(key="tidb_store_used_abs_high", name="TiDB存储写入量偏大", metric="used_size", operator=">", threshold=1099511627776, level="warning", period=600, times=2, mode="extended", enabled=False, template="存储写入量偏大"),
    ]


def mongodb_atlas_policies() -> list[dict]:
    app = "mongodb_atlas"
    name = "MongoDB Atlas"
    return [
        availability_rule(app, name),
        rule(key="mongodb_atlas_current_conn_high", name="MongoDB Atlas当前连接偏高", metric="current", operator=">", threshold=600, level="warning", period=300, times=2, mode="core", enabled=True, template="当前连接偏高"),
        rule(key="mongodb_atlas_current_conn_critical", name="MongoDB Atlas当前连接过高", metric="current", operator=">", threshold=900, level="critical", period=300, times=1, mode="core", enabled=True, template="当前连接过高"),
        rule(key="mongodb_atlas_available_conn_low", name="MongoDB Atlas可用连接不足", metric="available", operator="<", threshold=100, level="warning", period=300, times=2, mode="core", enabled=True, template="可用连接不足"),
        rule(key="mongodb_atlas_available_conn_critical", name="MongoDB Atlas可用连接严重不足", metric="available", operator="<", threshold=50, level="critical", period=300, times=1, mode="core", enabled=True, template="可用连接严重不足"),
        rule(key="mongodb_atlas_requests_high", name="MongoDB Atlas请求量偏高", metric="numRequests", operator=">", threshold=12000, level="warning", period=300, times=2, mode="core", enabled=True, template="请求量偏高"),
        rule(key="mongodb_atlas_bytes_in_high", name="MongoDB Atlas入流量偏高", metric="bytesIn", operator=">", threshold=104857600, level="warning", period=300, times=2, mode="extended", enabled=False, template="入流量偏高"),
        rule(key="mongodb_atlas_bytes_out_high", name="MongoDB Atlas出流量偏高", metric="bytesOut", operator=">", threshold=104857600, level="warning", period=300, times=2, mode="extended", enabled=False, template="出流量偏高"),
        rule(key="mongodb_atlas_query_ops_high", name="MongoDB Atlas查询操作偏高", metric="query", operator=">", threshold=8000, level="warning", period=300, times=2, mode="extended", enabled=False, template="查询操作偏高"),
        rule(key="mongodb_atlas_update_ops_high", name="MongoDB Atlas更新操作偏高", metric="update", operator=">", threshold=5000, level="warning", period=300, times=2, mode="extended", enabled=False, template="更新操作偏高"),
        rule(key="mongodb_atlas_storage_size_high", name="MongoDB Atlas存储占用偏高", metric="storageSize", operator=">", threshold=536870912000, level="warning", period=600, times=2, mode="extended", enabled=False, template="存储占用偏高"),
        rule(key="mongodb_atlas_index_size_high", name="MongoDB Atlas索引占用偏高", metric="indexSize", operator=">", threshold=107374182400, level="warning", period=600, times=2, mode="extended", enabled=False, template="索引占用偏高"),
    ]


def oceanbase_policies() -> list[dict]:
    app = "oceanbase"
    name = "OceanBase"
    return [
        availability_rule(app, name),
        rule(key="oceanbase_process_high", name="OceanBase活动进程偏高", metric="num", operator=">", threshold=120, level="warning", period=300, times=2, mode="core", enabled=True, template="活动进程偏高"),
        rule(key="oceanbase_process_critical", name="OceanBase活动进程过高", metric="num", operator=">", threshold=200, level="critical", period=300, times=1, mode="core", enabled=True, template="活动进程过高"),
        rule(key="oceanbase_conn_util_high", name="OceanBase连接利用率偏高", metric="num", operator=">", threshold=70, level="warning", period=300, times=2, mode="core", enabled=True, template="连接利用率偏高", expr="(max_connections > 0) && ((num / max_connections) * 100 > 70)"),
        rule(key="oceanbase_conn_util_critical", name="OceanBase连接利用率过高", metric="num", operator=">", threshold=85, level="critical", period=300, times=1, mode="extended", enabled=False, template="连接利用率过高", expr="(max_connections > 0) && ((num / max_connections) * 100 > 85)"),
        rule(key="oceanbase_select_high", name="OceanBase查询吞吐偏高", metric="sql_select_count", operator=">", threshold=25000, level="warning", period=300, times=2, mode="core", enabled=True, template="查询吞吐偏高"),
        rule(key="oceanbase_insert_high", name="OceanBase插入吞吐偏高", metric="sql_insert_count", operator=">", threshold=10000, level="warning", period=300, times=2, mode="extended", enabled=False, template="插入吞吐偏高"),
        rule(key="oceanbase_update_high", name="OceanBase更新吞吐偏高", metric="sql_update_count", operator=">", threshold=10000, level="warning", period=300, times=2, mode="extended", enabled=False, template="更新吞吐偏高"),
        rule(key="oceanbase_delete_high", name="OceanBase删除吞吐偏高", metric="sql_delete_count", operator=">", threshold=5000, level="warning", period=300, times=2, mode="extended", enabled=False, template="删除吞吐偏高"),
        rule(key="oceanbase_write_ops_high", name="OceanBase写入操作总量偏高", metric="sql_update_count", operator=">", threshold=15000, level="warning", period=300, times=2, mode="core", enabled=True, template="写入操作总量偏高", expr="(sql_insert_count + sql_update_count + sql_delete_count) > 15000"),
        rule(key="oceanbase_write_ops_critical", name="OceanBase写入操作总量过高", metric="sql_update_count", operator=">", threshold=30000, level="critical", period=300, times=1, mode="extended", enabled=False, template="写入操作总量过高", expr="(sql_insert_count + sql_update_count + sql_delete_count) > 30000"),
        rule(key="oceanbase_max_connections_small", name="OceanBase最大连接配置偏低", metric="max_connections", operator="<", threshold=200, level="info", period=3600, times=1, mode="extended", enabled=False, template="最大连接配置偏低"),
    ]


def oracle_policies() -> list[dict]:
    app = "oracle"
    name = "Oracle"
    return [
        availability_rule(app, name),
        rule(key="oracle_tablespace_used_high", name="Oracle表空间使用率偏高", metric="used_percentage", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="表空间使用率偏高"),
        rule(key="oracle_tablespace_used_critical", name="Oracle表空间使用率过高", metric="used_percentage", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="表空间使用率过高"),
        rule(key="oracle_free_space_low", name="Oracle剩余表空间不足", metric="free_percentage", operator="<", threshold=10, level="warning", period=600, times=2, mode="core", enabled=True, template="剩余表空间不足"),
        rule(key="oracle_process_count_high", name="Oracle进程数偏高", metric="process_count", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="进程数偏高"),
        rule(key="oracle_process_count_critical", name="Oracle进程数过高", metric="process_count", operator=">", threshold=800, level="critical", period=300, times=1, mode="extended", enabled=False, template="进程数过高"),
        rule(key="oracle_qps_high", name="Oracle查询吞吐偏高", metric="qps", operator=">", threshold=5000, level="warning", period=300, times=2, mode="core", enabled=True, template="查询吞吐偏高"),
        rule(key="oracle_tps_high", name="Oracle事务吞吐偏高", metric="tps", operator=">", threshold=3000, level="warning", period=300, times=2, mode="extended", enabled=False, template="事务吞吐偏高"),
        rule(key="oracle_commit_wait_high", name="Oracle提交等待时间偏高", metric="commit_wait_time", operator=">", threshold=1000, level="warning", period=600, times=2, mode="core", enabled=True, template="提交等待时间偏高"),
        rule(key="oracle_user_io_wait_high", name="Oracle用户IO等待时间偏高", metric="user_io_wait_time", operator=">", threshold=1000, level="warning", period=600, times=2, mode="core", enabled=True, template="用户IO等待时间偏高"),
        rule(key="oracle_buffer_cache_low", name="Oracle缓冲区命中率偏低", metric="buffer_cache_hit_ratio", operator="<", threshold=95, level="warning", period=600, times=2, mode="core", enabled=True, template="缓冲区命中率偏低"),
        rule(key="oracle_library_cache_low", name="Oracle库缓存命中率偏低", metric="lib_cache_hit_ratio", operator="<", threshold=95, level="warning", period=600, times=2, mode="extended", enabled=False, template="库缓存命中率偏低"),
        rule(key="oracle_top_sql_cpu_high", name="Oracle热点SQL CPU消耗偏高", metric="cpu_secs", operator=">", threshold=60, level="warning", period=600, times=2, mode="extended", enabled=False, template="热点SQL CPU消耗偏高"),
        rule(key="oracle_password_expiry_soon", name="Oracle用户密码即将过期", metric="expiry_seconds", operator="<", threshold=604800, level="warning", period=3600, times=1, mode="extended", enabled=False, template="用户密码即将过期"),
    ]


def dm_policies() -> list[dict]:
    app = "dm"
    name = "DM"
    return [
        availability_rule(app, name),
        rule(key="dm_sql_thread_high", name="DM SQL线程偏高", metric="dm_sql_thd", operator=">", threshold=50, level="warning", period=300, times=2, mode="core", enabled=True, template="SQL线程偏高"),
        rule(key="dm_sql_thread_critical", name="DM SQL线程过高", metric="dm_sql_thd", operator=">", threshold=80, level="critical", period=300, times=1, mode="core", enabled=True, template="SQL线程过高"),
        rule(key="dm_io_thread_high", name="DM IO线程偏高", metric="dm_io_thd", operator=">", threshold=50, level="warning", period=300, times=2, mode="core", enabled=True, template="IO线程偏高"),
        rule(key="dm_io_thread_critical", name="DM IO线程过高", metric="dm_io_thd", operator=">", threshold=80, level="critical", period=300, times=1, mode="core", enabled=True, template="IO线程过高"),
        rule(key="dm_quit_thread_detected", name="DM退出线程告警", metric="dm_quit_thd", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="检测到退出线程", rule_type="realtime_metric"),
        rule(key="dm_thread_sum_high", name="DM线程总量偏高", metric="dm_sql_thd", operator=">", threshold=120, level="warning", period=300, times=2, mode="extended", enabled=False, template="线程总量偏高", expr="(dm_sql_thd + dm_io_thd + dm_quit_thd) > 120"),
        rule(key="dm_thread_sum_critical", name="DM线程总量过高", metric="dm_sql_thd", operator=">", threshold=180, level="critical", period=300, times=1, mode="extended", enabled=False, template="线程总量过高", expr="(dm_sql_thd + dm_io_thd + dm_quit_thd) > 180"),
        rule(key="dm_sql_thread_util_high", name="DM SQL线程占比偏高", metric="dm_sql_thd", operator=">", threshold=50, level="warning", period=300, times=2, mode="extended", enabled=False, template="SQL线程占比偏高", expr="(MAX_SESSIONS > 0) && ((dm_sql_thd / MAX_SESSIONS) * 100 > 50)"),
        rule(key="dm_io_thread_util_high", name="DM IO线程占比偏高", metric="dm_io_thd", operator=">", threshold=50, level="warning", period=300, times=2, mode="extended", enabled=False, template="IO线程占比偏高", expr="(MAX_SESSIONS > 0) && ((dm_io_thd / MAX_SESSIONS) * 100 > 50)"),
        rule(key="dm_max_sessions_small", name="DM最大会话配置偏低", metric="MAX_SESSIONS", operator="<", threshold=200, level="info", period=3600, times=1, mode="extended", enabled=False, template="最大会话配置偏低"),
    ]


POLICIES: dict[str, list[dict]] = {
    "postgresql": pg_family_policies("postgresql", "PostgreSQL"),
    "db2": db2_policies(),
    "mariadb": mariadb_policies(),
    "sqlserver": sqlserver_policies(),
    "kingbase": pg_family_policies("kingbase", "Kingbase"),
    "greenplum": pg_family_policies("greenplum", "GreenPlum"),
    "tidb": tidb_policies(),
    "mongodb_atlas": mongodb_atlas_policies(),
    "oceanbase": oceanbase_policies(),
    "vastbase": pg_family_policies("vastbase", "Vastbase"),
    "oracle": oracle_policies(),
    "dm": dm_policies(),
    "opengauss": opengauss_policies(),
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


def _upsert_alerts(content: str, alerts_text: str) -> str:
    marker = "\nalerts:\n"
    if marker in content:
        return content.split(marker, 1)[0].rstrip() + "\n\n" + alerts_text
    return content.rstrip() + "\n\n" + alerts_text


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    template_dir = backend_dir / "templates"
    updated = 0
    for app, alerts in POLICIES.items():
        path = template_dir / f"app-{app}.yml"
        if not path.exists():
            print(f"[skip] missing template: {path}")
            continue
        raw = path.read_text(encoding="utf-8")
        merged = _upsert_alerts(raw, _render_alerts(alerts))
        path.write_text(merged, encoding="utf-8")
        updated += 1
        print(f"[ok] updated alerts: app-{app}.yml ({len(alerts)} rules)")
    print(f"[done] templates updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
