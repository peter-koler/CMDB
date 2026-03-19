#!/usr/bin/env python3
"""
为缓存类模板写入差异化默认告警策略（alerts）。
当前覆盖：
1) memcached
2) valkey
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
        expr=f"{metric} == 0",
        template="实例不可用",
        rule_type="realtime_metric",
    )


def memcached_policies() -> list[dict]:
    app = "memcached"
    name = "Memcached"
    return [
        availability_rule(app, name),
        rule(key="memcached_response_time_high", name="Memcached响应时间偏高", metric="responseTime", operator=">", threshold=150, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="memcached_response_time_critical", name="Memcached响应时间过高", metric="responseTime", operator=">", threshold=500, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="memcached_connections_high", name="Memcached连接数偏高", metric="curr_connections", operator=">", threshold=2000, level="warning", period=300, times=2, mode="core", enabled=True, template="连接数偏高"),
        rule(key="memcached_threads_high", name="Memcached线程数异常偏高", metric="threads", operator=">", threshold=256, level="warning", period=600, times=2, mode="extended", enabled=False, template="线程数异常偏高"),
        rule(key="memcached_get_miss_ratio_high", name="Memcached读请求未命中率偏高", metric="get_misses", operator=">", threshold=0.2, level="warning", period=300, times=2, mode="core", enabled=True, template="读请求未命中率偏高", expr="(cmd_get > 100) && ((get_misses / cmd_get) > 0.2)"),
        rule(key="memcached_get_miss_ratio_critical", name="Memcached读请求未命中率过高", metric="get_misses", operator=">", threshold=0.4, level="critical", period=300, times=1, mode="core", enabled=True, template="读请求未命中率过高", expr="(cmd_get > 100) && ((get_misses / cmd_get) > 0.4)"),
        rule(key="memcached_delete_misses_high", name="Memcached删除未命中次数偏高", metric="delete_misses", operator=">", threshold=1000, level="warning", period=600, times=2, mode="extended", enabled=False, template="删除未命中次数偏高"),
        rule(key="memcached_cmd_flush_detected", name="Memcached检测到Flush操作", metric="cmd_flush", operator=">", threshold=0, level="warning", period=60, times=1, mode="core", enabled=True, template="检测到Flush操作", rule_type="realtime_metric"),
        rule(key="memcached_memory_usage_high", name="Memcached内存占用偏高", metric="bytes", operator=">", threshold=3221225472, level="warning", period=300, times=2, mode="extended", enabled=False, template="内存占用偏高"),
        rule(key="memcached_uptime_short", name="Memcached运行时长过短", metric="uptime", operator="<", threshold=600, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短"),
    ]


def valkey_policies() -> list[dict]:
    app = "valkey"
    name = "Valkey"
    return [
        availability_rule(app, name),
        rule(key="valkey_connected_clients_high", name="Valkey连接数偏高", metric="connected_clients", operator=">", threshold=5000, level="warning", period=300, times=2, mode="core", enabled=True, template="连接数偏高"),
        rule(key="valkey_connected_clients_critical", name="Valkey连接数过高", metric="connected_clients", operator=">", threshold=10000, level="critical", period=300, times=1, mode="core", enabled=True, template="连接数过高"),
        rule(key="valkey_blocked_clients_exists", name="Valkey存在阻塞客户端", metric="blocked_clients", operator=">", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="存在阻塞客户端", rule_type="realtime_metric"),
        rule(key="valkey_memory_used_high", name="Valkey内存使用偏高", metric="used_memory", operator=">", threshold=12884901888, level="warning", period=300, times=2, mode="core", enabled=True, template="内存使用偏高"),
        rule(key="valkey_memory_fragmentation_high", name="Valkey内存碎片率偏高", metric="mem_fragmentation_ratio", operator=">", threshold=1.8, level="warning", period=300, times=2, mode="core", enabled=True, template="内存碎片率偏高"),
        rule(key="valkey_rejected_connections_exists", name="Valkey出现连接拒绝", metric="rejected_connections", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="出现连接拒绝"),
        rule(key="valkey_evicted_keys_exists", name="Valkey出现键淘汰", metric="evicted_keys", operator=">", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="出现键淘汰"),
        rule(key="valkey_rdb_bgsave_failed", name="Valkey RDB持久化失败", metric="rdb_last_bgsave_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="RDB持久化失败", expr="rdb_last_bgsave_status != 'ok'", rule_type="realtime_metric"),
        rule(key="valkey_aof_rewrite_failed", name="Valkey AOF重写失败", metric="aof_last_bgrewrite_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="AOF重写失败", expr="aof_last_bgrewrite_status != 'ok'", rule_type="realtime_metric"),
        rule(key="valkey_replication_link_down", name="Valkey主从复制链路异常", metric="master_link_status", operator="==", threshold=0, level="critical", period=120, times=1, mode="extended", enabled=False, template="主从复制链路异常", expr="master_link_status != 'up'", rule_type="realtime_metric"),
        rule(key="valkey_cluster_state_abnormal", name="Valkey集群状态异常", metric="cluster_state", operator="==", threshold=0, level="critical", period=120, times=1, mode="extended", enabled=False, template="集群状态异常", expr="cluster_state != 'ok'", rule_type="realtime_metric"),
        rule(key="valkey_uptime_short", name="Valkey运行时长过短", metric="uptime_in_seconds", operator="<", threshold=600, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短"),
    ]


POLICIES: dict[str, list[dict]] = {
    "memcached": memcached_policies(),
    "valkey": valkey_policies(),
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
