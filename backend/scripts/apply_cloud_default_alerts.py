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
        period=30,
        times=1,
        mode="core",
        enabled=True,
        expr=f"{metric} == 0",
        template="实例不可用",
        rule_type="realtime_metric",
    )


POLICIES: dict[str, list[dict]] = {
    "docker": [
        availability_rule("docker", "Docker"),
        rule(
            key="docker_containers_stopped_nonzero",
            name="Docker存在已停止容器",
            metric="containers_stopped",
            operator=">",
            threshold=0,
            level="warning",
            period=180,
            times=2,
            mode="core",
            enabled=True,
            template="存在已停止容器",
        ),
        rule(
            key="docker_container_cpu_usage_high",
            name="Docker容器CPU使用率过高",
            metric="cpu_usage",
            operator=">",
            threshold=90,
            level="warning",
            period=120,
            times=2,
            mode="core",
            enabled=True,
            template="容器CPU使用率过高",
        ),
        rule(
            key="docker_container_memory_usage_high",
            name="Docker容器内存使用率过高",
            metric="memory_usage",
            operator=">",
            threshold=90,
            level="warning",
            period=120,
            times=2,
            mode="core",
            enabled=True,
            template="容器内存使用率过高",
        ),
        rule(
            key="docker_container_state_abnormal",
            name="Docker容器状态异常",
            metric="state",
            operator="==",
            threshold=0,
            level="critical",
            period=60,
            times=1,
            mode="extended",
            enabled=False,
            expr="state != 'running'",
            template="容器状态异常",
            rule_type="realtime_metric",
        ),
    ],
    "kubernetes": [
        availability_rule("kubernetes", "Kubernetes"),
        rule(
            key="kubernetes_node_not_ready",
            name="Kubernetes节点非Ready",
            metric="is_ready",
            operator="==",
            threshold=0,
            level="critical",
            period=30,
            times=1,
            mode="core",
            enabled=True,
            expr="is_ready != 'True'",
            template="节点非Ready",
            rule_type="realtime_metric",
        ),
        rule(
            key="kubernetes_namespace_not_active",
            name="Kubernetes命名空间状态异常",
            metric="status",
            operator="==",
            threshold=0,
            level="warning",
            period=60,
            times=1,
            mode="core",
            enabled=True,
            expr="status != 'Active'",
            template="命名空间状态异常",
            rule_type="realtime_metric",
        ),
        rule(
            key="kubernetes_pod_not_running",
            name="Kubernetes Pod状态异常",
            metric="status",
            operator="==",
            threshold=0,
            level="critical",
            period=60,
            times=1,
            mode="core",
            enabled=True,
            expr="status != 'Running' && status != 'Succeeded'",
            template="Pod状态异常",
            rule_type="realtime_metric",
        ),
        rule(
            key="kubernetes_apiserver_latency_high",
            name="Kubernetes API响应时延过高",
            metric="responseTime",
            operator=">",
            threshold=1500,
            level="warning",
            period=120,
            times=2,
            mode="core",
            enabled=True,
            template="API响应时延过高",
        ),
        rule(
            key="kubernetes_allocatable_cpu_low",
            name="Kubernetes可分配CPU比例偏低",
            metric="allocatable_cpu",
            operator="<",
            threshold=1,
            level="warning",
            period=300,
            times=2,
            mode="extended",
            enabled=False,
            expr="capacity_cpu > 0 && (allocatable_cpu / capacity_cpu) < 0.8",
            template="可分配CPU比例偏低",
        ),
        rule(
            key="kubernetes_allocatable_memory_low",
            name="Kubernetes可分配内存比例偏低",
            metric="allocatable_memory",
            operator="<",
            threshold=1,
            level="warning",
            period=300,
            times=2,
            mode="extended",
            enabled=False,
            expr="capacity_memory > 0 && (allocatable_memory / capacity_memory) < 0.8",
            template="可分配内存比例偏低",
        ),
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
    print(f"[cloud-alerts] updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
