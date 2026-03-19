#!/usr/bin/env python3
"""
为 WebServer 模板写入差异化默认告警策略（alerts）。

当前覆盖:
- tomcat
- jetty
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


def tomcat_policies() -> list[dict]:
    app = "tomcat"
    name = "Tomcat"
    return [
        availability_rule(app, name),
        rule(
            key="tomcat_thread_busy_high",
            name="Tomcat工作线程占用偏高",
            metric="currentThreadsBusy",
            operator=">",
            threshold=80,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="工作线程占用偏高",
            expr="(maxThreads > 0) && ((currentThreadsBusy / maxThreads) * 100 > 80)",
        ),
        rule(
            key="tomcat_thread_busy_critical",
            name="Tomcat工作线程占用过高",
            metric="currentThreadsBusy",
            operator=">",
            threshold=90,
            level="critical",
            period=120,
            times=1,
            mode="core",
            enabled=True,
            template="工作线程占用过高",
            expr="(maxThreads > 0) && ((currentThreadsBusy / maxThreads) * 100 > 90)",
        ),
        rule(
            key="tomcat_connector_connections_high",
            name="Tomcat连接数偏高",
            metric="connectionCount",
            operator=">",
            threshold=5000,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="连接数偏高",
        ),
        rule(
            key="tomcat_request_max_time_high",
            name="Tomcat请求最大耗时偏高",
            metric="maxTime",
            operator=">",
            threshold=1000,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="请求最大耗时偏高",
        ),
        rule(
            key="tomcat_request_max_time_critical",
            name="Tomcat请求最大耗时过高",
            metric="maxTime",
            operator=">",
            threshold=3000,
            level="critical",
            period=120,
            times=1,
            mode="core",
            enabled=True,
            template="请求最大耗时过高",
        ),
        rule(
            key="tomcat_heap_usage_high",
            name="Tomcat堆内存使用率偏高",
            metric="heap_used",
            operator=">",
            threshold=80,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="堆内存使用率偏高",
            expr="(heap_max > 0) && ((heap_used / heap_max) * 100 > 80)",
        ),
        rule(
            key="tomcat_heap_usage_critical",
            name="Tomcat堆内存使用率过高",
            metric="heap_used",
            operator=">",
            threshold=90,
            level="critical",
            period=300,
            times=1,
            mode="core",
            enabled=True,
            template="堆内存使用率过高",
            expr="(heap_max > 0) && ((heap_used / heap_max) * 100 > 90)",
        ),
        rule(
            key="tomcat_error_count_burst",
            name="Tomcat错误请求累计偏多",
            metric="errorCount",
            operator=">",
            threshold=1000,
            level="warning",
            period=300,
            times=2,
            mode="extended",
            enabled=False,
            template="错误请求累计偏多",
        ),
        rule(
            key="tomcat_error_rate_high",
            name="Tomcat错误率偏高",
            metric="errorCount",
            operator=">",
            threshold=2,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="错误率偏高",
            expr="(requestCount > 1000) && ((errorCount / requestCount) * 100 > 2)",
        ),
        rule(
            key="tomcat_avg_latency_high",
            name="Tomcat平均请求耗时偏高",
            metric="processingTime",
            operator=">",
            threshold=200,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="平均请求耗时偏高",
            expr="(requestCount > 0) && ((processingTime / requestCount) > 200)",
        ),
        rule(
            key="tomcat_pending_finalization_high",
            name="Tomcat对象终结队列积压",
            metric="ObjectPendingFinalizationCount",
            operator=">",
            threshold=100,
            level="warning",
            period=300,
            times=2,
            mode="extended",
            enabled=False,
            template="对象终结队列积压",
        ),
        rule(
            key="tomcat_uptime_short",
            name="Tomcat运行时长过短",
            metric="Uptime",
            operator="<",
            threshold=3600000,
            level="warning",
            period=600,
            times=1,
            mode="extended",
            enabled=False,
            template="运行时长过短",
        ),
    ]


def jetty_policies() -> list[dict]:
    app = "jetty"
    name = "Jetty"
    return [
        availability_rule(app, name),
        rule(
            key="jetty_server_state_abnormal",
            name="Jetty服务状态异常",
            metric="state",
            operator="==",
            threshold=0,
            level="critical",
            period=60,
            times=1,
            mode="core",
            enabled=True,
            template="服务状态异常",
            expr="state != 'STARTED' && state != 'RUNNING'",
            rule_type="realtime_metric",
        ),
        rule(
            key="jetty_thread_busy_high",
            name="Jetty工作线程占用偏高",
            metric="busyThreads",
            operator=">",
            threshold=80,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="工作线程占用偏高",
            expr="(maxThreads > 0) && ((busyThreads / maxThreads) * 100 > 80)",
        ),
        rule(
            key="jetty_thread_busy_critical",
            name="Jetty工作线程占用过高",
            metric="busyThreads",
            operator=">",
            threshold=90,
            level="critical",
            period=120,
            times=1,
            mode="core",
            enabled=True,
            template="工作线程占用过高",
            expr="(maxThreads > 0) && ((busyThreads / maxThreads) * 100 > 90)",
        ),
        rule(
            key="jetty_thread_queue_high",
            name="Jetty线程池排队积压偏高",
            metric="queueSize",
            operator=">",
            threshold=200,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="线程池排队积压偏高",
        ),
        rule(
            key="jetty_thread_saturation_high",
            name="Jetty线程池饱和度偏高",
            metric="busyThreads",
            operator=">",
            threshold=85,
            level="warning",
            period=240,
            times=2,
            mode="core",
            enabled=True,
            template="线程池饱和度偏高",
            expr="(threads > 0) && ((busyThreads / threads) * 100 > 85)",
        ),
        rule(
            key="jetty_queue_pressure_high",
            name="Jetty线程池排队压力偏高",
            metric="queueSize",
            operator=">",
            threshold=1,
            level="warning",
            period=240,
            times=2,
            mode="core",
            enabled=True,
            template="线程池排队压力偏高",
            expr="(maxThreads > 0) && (queueSize > maxThreads)",
        ),
        rule(
            key="jetty_idle_threads_low",
            name="Jetty空闲线程过少",
            metric="idleThreads",
            operator="<",
            threshold=2,
            level="warning",
            period=180,
            times=2,
            mode="extended",
            enabled=False,
            template="空闲线程过少",
        ),
        rule(
            key="jetty_heap_usage_high",
            name="Jetty堆内存使用率偏高",
            metric="heap_used",
            operator=">",
            threshold=80,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="堆内存使用率偏高",
            expr="(heap_max > 0) && ((heap_used / heap_max) * 100 > 80)",
        ),
        rule(
            key="jetty_heap_usage_critical",
            name="Jetty堆内存使用率过高",
            metric="heap_used",
            operator=">",
            threshold=90,
            level="critical",
            period=300,
            times=1,
            mode="core",
            enabled=True,
            template="堆内存使用率过高",
            expr="(heap_max > 0) && ((heap_used / heap_max) * 100 > 90)",
        ),
        rule(
            key="jetty_gc_time_high",
            name="Jetty GC累计耗时偏高",
            metric="CollectionTime",
            operator=">",
            threshold=300000,
            level="warning",
            period=600,
            times=2,
            mode="extended",
            enabled=False,
            template="GC累计耗时偏高",
        ),
        rule(
            key="jetty_pending_finalization_high",
            name="Jetty对象终结队列积压",
            metric="ObjectPendingFinalizationCount",
            operator=">",
            threshold=100,
            level="warning",
            period=300,
            times=2,
            mode="extended",
            enabled=False,
            template="对象终结队列积压",
        ),
        rule(
            key="jetty_uptime_short",
            name="Jetty运行时长过短",
            metric="Uptime",
            operator="<",
            threshold=3600000,
            level="warning",
            period=600,
            times=1,
            mode="extended",
            enabled=False,
            template="运行时长过短",
        ),
    ]


POLICIES: dict[str, list[dict]] = {
    "tomcat": tomcat_policies(),
    "jetty": jetty_policies(),
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
    updated = []
    missing = []
    for app, rules in POLICIES.items():
        filepath = template_dir / f"app-{app}.yml"
        if not filepath.exists():
            missing.append(str(filepath))
            continue
        raw = filepath.read_text(encoding="utf-8")
        merged = _upsert_alerts(raw, _render_alerts(rules))
        filepath.write_text(merged, encoding="utf-8")
        updated.append(app)

    print(f"[webserver-default-alerts] updated: {len(updated)} -> {', '.join(updated)}")
    if missing:
        print("[webserver-default-alerts] missing template files:")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
