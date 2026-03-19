#!/usr/bin/env python3
"""
为操作系统模板写入差异化默认告警策略（alerts）。
"""

from __future__ import annotations

from pathlib import Path

from scripts.os_template_profiles import OS_TEMPLATE_META


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


def unix_policies(app: str, display_name: str, desktop: bool) -> list[dict]:
    load_warn = 2 if desktop else 4
    load_crit = 4 if desktop else 8
    return [
        availability_rule(app, display_name),
        rule(
            key=f"{app}_load1_high",
            name=f"{display_name}1分钟负载偏高",
            metric="load1",
            operator=">",
            threshold=load_warn,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="1分钟负载偏高",
            expr=f"(cpu_cores > 0) && (load1 > cpu_cores * {load_warn})",
        ),
        rule(
            key=f"{app}_load1_critical",
            name=f"{display_name}1分钟负载过高",
            metric="load1",
            operator=">",
            threshold=load_crit,
            level="critical",
            period=120,
            times=1,
            mode="core",
            enabled=True,
            template="1分钟负载过高",
            expr=f"(cpu_cores > 0) && (load1 > cpu_cores * {load_crit})",
        ),
        rule(
            key=f"{app}_load5_high",
            name=f"{display_name}5分钟负载偏高",
            metric="load5",
            operator=">",
            threshold=load_warn,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="5分钟负载偏高",
            expr=f"(cpu_cores > 0) && (load5 > cpu_cores * {load_warn})",
        ),
        rule(
            key=f"{app}_mem_usage_high",
            name=f"{display_name}内存使用率偏高",
            metric="mem_used_pct",
            operator=">",
            threshold=80,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="内存使用率偏高",
        ),
        rule(
            key=f"{app}_mem_usage_critical",
            name=f"{display_name}内存使用率过高",
            metric="mem_used_pct",
            operator=">",
            threshold=90,
            level="critical",
            period=300,
            times=1,
            mode="core",
            enabled=True,
            template="内存使用率过高",
        ),
        rule(
            key=f"{app}_mem_available_low",
            name=f"{display_name}可用内存不足",
            metric="memavailable_kb",
            operator="<",
            threshold=524288,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="可用内存不足",
        ),
        rule(
            key=f"{app}_uptime_short",
            name=f"{display_name}运行时长过短",
            metric="uptime_s",
            operator="<",
            threshold=1800,
            level="warning",
            period=600,
            times=1,
            mode="extended",
            enabled=False,
            template="运行时长过短",
        ),
        rule(
            key=f"{app}_kernel_release_missing",
            name=f"{display_name}内核版本采集缺失",
            metric="kernel_release",
            operator="==",
            threshold=0,
            level="warning",
            period=3600,
            times=1,
            mode="extended",
            enabled=False,
            template="内核版本采集缺失",
            expr="kernel_release == ''",
        ),
        rule(
            key=f"{app}_hostname_missing",
            name=f"{display_name}主机名采集缺失",
            metric="hostname",
            operator="==",
            threshold=0,
            level="warning",
            period=1800,
            times=1,
            mode="extended",
            enabled=False,
            template="主机名采集缺失",
            expr="hostname == ''",
        ),
        rule(
            key=f"{app}_load15_high",
            name=f"{display_name}15分钟负载持续偏高",
            metric="load15",
            operator=">",
            threshold=load_warn,
            level="warning",
            period=600,
            times=2,
            mode="extended",
            enabled=False,
            template="15分钟负载持续偏高",
            expr=f"(cpu_cores > 0) && (load15 > cpu_cores * {load_warn})",
        ),
    ]


def windows_policies(app: str, display_name: str) -> list[dict]:
    return [
        availability_rule(app, display_name),
        rule(key=f"{app}_processes_high", name=f"{display_name}进程数偏高", metric="processes", operator=">", threshold=300, level="warning", period=300, times=2, mode="core", enabled=True, template="进程数偏高"),
        rule(key=f"{app}_processes_critical", name=f"{display_name}进程数过高", metric="processes", operator=">", threshold=500, level="critical", period=180, times=1, mode="core", enabled=True, template="进程数过高"),
        rule(key=f"{app}_users_missing", name=f"{display_name}在线用户为0", metric="numUsers", operator="<", threshold=1, level="warning", period=600, times=2, mode="extended", enabled=False, template="在线用户为0"),
        rule(key=f"{app}_memory_low", name=f"{display_name}物理内存容量偏低", metric="memory", operator="<", threshold=1048576, level="warning", period=1800, times=1, mode="extended", enabled=False, template="物理内存容量偏低"),
        rule(key=f"{app}_uptime_short", name=f"{display_name}运行时长过短", metric="uptime", operator="<", threshold=60000, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短"),
        rule(key=f"{app}_descr_missing", name=f"{display_name}系统描述采集缺失", metric="descr", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="系统描述采集缺失", expr="descr == ''"),
        rule(key=f"{app}_hostname_missing", name=f"{display_name}主机名采集缺失", metric="name", operator="==", threshold=0, level="warning", period=1800, times=1, mode="extended", enabled=False, template="主机名采集缺失", expr="name == ''"),
        rule(key=f"{app}_location_missing", name=f"{display_name}位置信息未配置", metric="location", operator="==", threshold=0, level="info", period=3600, times=1, mode="extended", enabled=False, template="位置信息未配置", expr="location == ''"),
        rule(key=f"{app}_uptime_reset", name=f"{display_name}疑似重启", metric="uptime", operator="<", threshold=3600000, level="warning", period=600, times=1, mode="core", enabled=True, template="疑似重启"),
        rule(
            key=f"{app}_processes_zero",
            name=f"{display_name}进程数异常为0",
            metric="processes",
            operator="<=",
            threshold=0,
            level="warning",
            period=900,
            times=2,
            mode="extended",
            enabled=False,
            template="进程数异常为0",
        ),
    ]


def nvidia_policies(app: str, display_name: str) -> list[dict]:
    return [
        availability_rule(app, display_name),
        rule(key="nvidia_gpu_util_high", name="NVIDIA GPU利用率偏高", metric="gpu_utilization_pct", operator=">", threshold=90, level="warning", period=180, times=2, mode="core", enabled=True, template="GPU利用率偏高"),
        rule(key="nvidia_gpu_util_critical", name="NVIDIA GPU利用率过高", metric="gpu_utilization_pct", operator=">", threshold=98, level="critical", period=120, times=1, mode="core", enabled=True, template="GPU利用率过高"),
        rule(key="nvidia_gpu_temp_high", name="NVIDIA GPU温度偏高", metric="gpu_temperature_c", operator=">", threshold=80, level="warning", period=180, times=2, mode="core", enabled=True, template="GPU温度偏高"),
        rule(key="nvidia_gpu_temp_critical", name="NVIDIA GPU温度过高", metric="gpu_temperature_c", operator=">", threshold=88, level="critical", period=120, times=1, mode="core", enabled=True, template="GPU温度过高"),
        rule(
            key="nvidia_gpu_mem_usage_high",
            name="NVIDIA GPU显存使用率偏高",
            metric="gpu_memory_used_mb",
            operator=">",
            threshold=80,
            level="warning",
            period=300,
            times=2,
            mode="core",
            enabled=True,
            template="GPU显存使用率偏高",
            expr="(gpu_memory_total_mb > 0) && ((gpu_memory_used_mb / gpu_memory_total_mb) * 100 > 80)",
        ),
        rule(
            key="nvidia_gpu_mem_usage_critical",
            name="NVIDIA GPU显存使用率过高",
            metric="gpu_memory_used_mb",
            operator=">",
            threshold=90,
            level="critical",
            period=300,
            times=1,
            mode="core",
            enabled=True,
            template="GPU显存使用率过高",
            expr="(gpu_memory_total_mb > 0) && ((gpu_memory_used_mb / gpu_memory_total_mb) * 100 > 90)",
        ),
        rule(key="nvidia_mem_usage_high", name="NVIDIA主机内存使用率偏高", metric="mem_used_pct", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="主机内存使用率偏高"),
        rule(key="nvidia_mem_usage_critical", name="NVIDIA主机内存使用率过高", metric="mem_used_pct", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="主机内存使用率过高"),
        rule(key="nvidia_gpu_name_missing", name="NVIDIA GPU名称采集缺失", metric="gpu_name", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="GPU名称采集缺失", expr="gpu_name == ''"),
        rule(key="nvidia_gpu_mem_total_missing", name="NVIDIA GPU总显存采集缺失", metric="gpu_memory_total_mb", operator="<", threshold=1, level="warning", period=1800, times=1, mode="extended", enabled=False, template="GPU总显存采集缺失"),
    ]


def _build_policies() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for app, meta in OS_TEMPLATE_META.items():
        profile = meta["profile"]
        display_name = meta["name_en"]
        if profile == "windows":
            out[app] = windows_policies(app, display_name)
        elif profile == "gpu":
            out[app] = nvidia_policies(app, display_name)
        else:
            out[app] = unix_policies(app, display_name, desktop=(profile == "desktop"))
    return out


POLICIES: dict[str, list[dict]] = _build_policies()


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

    print(f"[os-default-alerts] updated: {len(updated)} -> {', '.join(updated)}")
    if missing:
        print("[os-default-alerts] missing template files:")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
