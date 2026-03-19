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
        name=f"{display_name}设备不可用",
        metric=metric,
        operator="==",
        threshold=0,
        level="critical",
        period=30,
        times=1,
        mode="core",
        enabled=True,
        expr=f"{metric} == 0",
        template="设备不可用",
        rule_type="realtime_metric",
    )


POLICIES: dict[str, list[dict]] = {
    "cisco_switch": [
        availability_rule("cisco_switch", "Cisco交换机"),
        rule(key="cisco_switch_response_slow", name="Cisco交换机响应时延偏高", metric="responseTime", operator=">", threshold=1200, level="warning", period=120, times=2, mode="core", enabled=True, template="响应时延偏高"),
        rule(key="cisco_switch_port_down", name="Cisco交换机端口运行状态异常", metric="oper_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, expr="oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口运行状态异常", rule_type="realtime_metric"),
        rule(key="cisco_switch_in_errors_high", name="Cisco交换机入方向错误包偏高", metric="in_errors", operator=">", threshold=1000, level="warning", period=300, times=2, mode="core", enabled=True, template="入方向错误包偏高"),
        rule(key="cisco_switch_out_discards_high", name="Cisco交换机出方向丢弃包偏高", metric="out_discards", operator=">", threshold=2000, level="warning", period=300, times=2, mode="extended", enabled=False, template="出方向丢弃包偏高"),
        rule(key="cisco_switch_admin_oper_mismatch", name="Cisco交换机端口配置与状态不一致", metric="admin_status", operator="==", threshold=0, level="warning", period=180, times=1, mode="extended", enabled=False, expr="(admin_status == '1' || admin_status == 'up' || admin_status == 'up(1)') && oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口配置与状态不一致", rule_type="realtime_metric"),
    ],
    "hpe_switch": [
        availability_rule("hpe_switch", "HPE交换机"),
        rule(key="hpe_switch_response_slow", name="HPE交换机响应时延偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=120, times=2, mode="core", enabled=True, template="响应时延偏高"),
        rule(key="hpe_switch_port_down", name="HPE交换机端口运行状态异常", metric="oper_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, expr="oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口运行状态异常", rule_type="realtime_metric"),
        rule(key="hpe_switch_in_discards_high", name="HPE交换机入方向丢弃包偏高", metric="in_discards", operator=">", threshold=1200, level="warning", period=300, times=2, mode="core", enabled=True, template="入方向丢弃包偏高"),
        rule(key="hpe_switch_out_errors_high", name="HPE交换机出方向错误包偏高", metric="out_errors", operator=">", threshold=800, level="warning", period=300, times=2, mode="core", enabled=True, template="出方向错误包偏高"),
        rule(key="hpe_switch_speed_low", name="HPE交换机端口速率异常偏低", metric="speed", operator="<", threshold=100, level="warning", period=300, times=2, mode="extended", enabled=False, template="端口速率异常偏低"),
    ],
    "huawei_switch": [
        availability_rule("huawei_switch", "Huawei交换机"),
        rule(key="huawei_switch_response_slow", name="Huawei交换机响应时延偏高", metric="responseTime", operator=">", threshold=900, level="warning", period=120, times=2, mode="core", enabled=True, template="响应时延偏高"),
        rule(key="huawei_switch_port_down", name="Huawei交换机端口运行状态异常", metric="oper_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, expr="oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口运行状态异常", rule_type="realtime_metric"),
        rule(key="huawei_switch_admin_oper_mismatch", name="Huawei交换机端口管理态与运行态不一致", metric="admin_status", operator="==", threshold=0, level="warning", period=180, times=1, mode="core", enabled=True, expr="(admin_status == '1' || admin_status == 'up' || admin_status == 'up(1)') && oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口管理态与运行态不一致", rule_type="realtime_metric"),
        rule(key="huawei_switch_in_errors_high", name="Huawei交换机入方向错误包偏高", metric="in_errors", operator=">", threshold=600, level="warning", period=300, times=2, mode="core", enabled=True, template="入方向错误包偏高"),
        rule(key="huawei_switch_out_discards_high", name="Huawei交换机出方向丢弃包偏高", metric="out_discards", operator=">", threshold=1000, level="warning", period=300, times=2, mode="extended", enabled=False, template="出方向丢弃包偏高"),
    ],
    "tplink_switch": [
        availability_rule("tplink_switch", "TP-Link交换机"),
        rule(key="tplink_switch_response_slow", name="TP-Link交换机响应时延偏高", metric="responseTime", operator=">", threshold=1500, level="warning", period=120, times=2, mode="core", enabled=True, template="响应时延偏高"),
        rule(key="tplink_switch_port_down", name="TP-Link交换机端口运行状态异常", metric="oper_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, expr="oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口运行状态异常", rule_type="realtime_metric"),
        rule(key="tplink_switch_in_discards_high", name="TP-Link交换机入方向丢弃包偏高", metric="in_discards", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="入方向丢弃包偏高"),
        rule(key="tplink_switch_out_errors_high", name="TP-Link交换机出方向错误包偏高", metric="out_errors", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="出方向错误包偏高"),
        rule(key="tplink_switch_mtu_abnormal", name="TP-Link交换机MTU配置异常", metric="mtu", operator="<", threshold=1280, level="warning", period=600, times=2, mode="extended", enabled=False, template="MTU配置异常"),
    ],
    "h3c_switch": [
        availability_rule("h3c_switch", "H3C交换机"),
        rule(key="h3c_switch_response_slow", name="H3C交换机响应时延偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=120, times=2, mode="core", enabled=True, template="响应时延偏高"),
        rule(key="h3c_switch_port_down", name="H3C交换机端口运行状态异常", metric="oper_status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, expr="oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口运行状态异常", rule_type="realtime_metric"),
        rule(key="h3c_switch_admin_oper_mismatch", name="H3C交换机端口管理态与运行态不一致", metric="admin_status", operator="==", threshold=0, level="warning", period=180, times=1, mode="core", enabled=True, expr="(admin_status == '1' || admin_status == 'up' || admin_status == 'up(1)') && oper_status != '1' && oper_status != 'up' && oper_status != 'up(1)'", template="端口管理态与运行态不一致", rule_type="realtime_metric"),
        rule(key="h3c_switch_in_errors_high", name="H3C交换机入方向错误包偏高", metric="in_errors", operator=">", threshold=800, level="warning", period=300, times=2, mode="core", enabled=True, template="入方向错误包偏高"),
        rule(key="h3c_switch_out_discards_high", name="H3C交换机出方向丢弃包偏高", metric="out_discards", operator=">", threshold=1200, level="warning", period=300, times=2, mode="extended", enabled=False, template="出方向丢弃包偏高"),
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
    print(f"[network-alerts] updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
