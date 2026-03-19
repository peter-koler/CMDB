#!/usr/bin/env python3
"""
为应用服务类模板写入差异化默认告警策略（alerts）。
"""

from __future__ import annotations

from pathlib import Path

from scripts.service_template_profiles import ALL_SERVICE_APPS, SERVICE_TEMPLATE_META


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


def ping_like_policies(app: str, display_name: str, warn_ms: int, crit_ms: int) -> list[dict]:
    return [
        availability_rule(app, display_name),
        rule(key=f"{app}_latency_high", name=f"{display_name}响应时间偏高", metric="responseTime", operator=">", threshold=warn_ms, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key=f"{app}_latency_critical", name=f"{display_name}响应时间过高", metric="responseTime", operator=">", threshold=crit_ms, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
    ]


def web_api_policies(app: str, display_name: str) -> list[dict]:
    rules = ping_like_policies(app, display_name, 800, 2000)
    rules.extend(
        [
            rule(key=f"{app}_status_code_abnormal", name=f"{display_name}状态码异常", metric="statusCode", operator=">=", threshold=400, level="critical", period=120, times=1, mode="core", enabled=True, template="状态码异常", expr="statusCode >= 400"),
            rule(key=f"{app}_keyword_mismatch", name=f"{display_name}关键字校验失败", metric="keyword", operator="==", threshold=0, level="warning", period=180, times=1, mode="extended", enabled=False, template="关键字校验失败", expr="keyword == 'false'"),
        ]
    )
    return rules


def api_code_policies() -> list[dict]:
    app = "api_code"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="api_code_latency_high", name="HTTP API状态码响应时间偏高", metric="responseTime", operator=">", threshold=800, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="api_code_latency_critical", name="HTTP API状态码响应时间过高", metric="responseTime", operator=">", threshold=2000, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="api_code_code_abnormal", name="HTTP API状态码异常", metric="code", operator=">=", threshold=400, level="critical", period=120, times=1, mode="core", enabled=True, template="状态码异常", expr="code >= 400"),
    ]


def ssl_cert_policies() -> list[dict]:
    app = "ssl_cert"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="ssl_cert_expired", name="SSL证书已过期", metric="expired", operator="==", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="证书已过期", expr="expired == 'true'"),
        rule(key="ssl_cert_expire_soon", name="SSL证书即将过期", metric="days_remaining", operator="<", threshold=30, level="warning", period=3600, times=1, mode="core", enabled=True, template="证书即将过期"),
        rule(key="ssl_cert_expire_critical", name="SSL证书7天内过期", metric="days_remaining", operator="<", threshold=7, level="critical", period=1800, times=1, mode="core", enabled=True, template="证书即将过期"),
    ]


def nginx_policies() -> list[dict]:
    app = "nginx"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="nginx_latency_high", name="Nginx响应时间偏高", metric="responseTime", operator=">", threshold=500, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="nginx_latency_critical", name="Nginx响应时间过高", metric="responseTime", operator=">", threshold=1500, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="nginx_active_high", name="Nginx活跃连接过高", metric="active", operator=">", threshold=10000, level="warning", period=180, times=2, mode="core", enabled=True, template="活跃连接过高"),
        rule(key="nginx_waiting_high", name="Nginx等待连接积压", metric="waiting", operator=">", threshold=3000, level="warning", period=180, times=2, mode="core", enabled=True, template="等待连接积压"),
        rule(key="nginx_dropped_increase", name="Nginx丢弃连接异常", metric="dropped", operator=">", threshold=0, level="warning", period=180, times=1, mode="extended", enabled=False, template="丢弃连接异常"),
    ]


def mail_policies(app: str) -> list[dict]:
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key=f"{app}_latency_high", name=f"{display_name}响应时间偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key=f"{app}_latency_critical", name=f"{display_name}响应时间过高", metric="responseTime", operator=">", threshold=3000, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key=f"{app}_mailbox_size_large", name=f"{display_name}邮箱容量偏大", metric="mailbox_size", operator=">", threshold=1048576, level="warning", period=3600, times=1, mode="extended", enabled=False, template="邮箱容量偏大"),
    ]


def smtp_policies() -> list[dict]:
    app = "smtp"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="smtp_latency_high", name="SMTP响应时间偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="smtp_latency_critical", name="SMTP响应时间过高", metric="responseTime", operator=">", threshold=3000, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="smtp_response_failed", name="SMTP握手失败", metric="response", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="握手失败", expr="response == 'false'"),
    ]


def ntp_policies() -> list[dict]:
    app = "ntp"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="ntp_latency_high", name="NTP响应时间偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="ntp_offset_large", name="NTP时间偏移过大", metric="offset", operator=">", threshold=1000, level="warning", period=300, times=2, mode="core", enabled=True, template="时间偏移过大", expr="abs(offset) > 1000"),
        rule(key="ntp_delay_high", name="NTP网络延迟过高", metric="delay", operator=">", threshold=1000, level="warning", period=180, times=2, mode="extended", enabled=False, template="网络延迟过高"),
        rule(key="ntp_stratum_high", name="NTP层级过高", metric="stratum", operator=">", threshold=10, level="warning", period=600, times=1, mode="extended", enabled=False, template="层级过高"),
    ]


def dns_policies() -> list[dict]:
    app = "dns"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="dns_latency_high", name="DNS响应时间偏高", metric="responseTime", operator=">", threshold=500, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="dns_latency_critical", name="DNS响应时间过高", metric="responseTime", operator=">", threshold=1500, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="dns_status_abnormal", name="DNS响应状态异常", metric="status", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="响应状态异常", expr="status != 'NOERROR'"),
        rule(key="dns_no_answer", name="DNS无应答记录", metric="answerRowCount", operator="==", threshold=0, level="warning", period=300, times=2, mode="extended", enabled=False, template="无应答记录"),
    ]


def ftp_policies() -> list[dict]:
    app = "ftp"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="ftp_inactive", name="FTP服务不可用", metric="isActive", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="服务不可用", expr="isActive == 'false'"),
        rule(key="ftp_latency_high", name="FTP响应时间偏高", metric="responseTime", operator=">", threshold=1500, level="warning", period=180, times=2, mode="core", enabled=True, template="响应时间偏高"),
    ]


def websocket_policies() -> list[dict]:
    app = "websocket"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="websocket_latency_high", name="WebSocket握手耗时偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=180, times=2, mode="core", enabled=True, template="握手耗时偏高"),
        rule(key="websocket_response_code_abnormal", name="WebSocket握手状态异常", metric="responseCode", operator="!=", threshold=101, level="critical", period=120, times=1, mode="core", enabled=True, template="握手状态异常", expr="responseCode != '101'"),
        rule(key="websocket_upgrade_missing", name="WebSocket升级头缺失", metric="upgrade", operator="==", threshold=0, level="warning", period=180, times=2, mode="extended", enabled=False, template="升级头缺失", expr="upgrade == ''"),
    ]


def mqtt_policies() -> list[dict]:
    app = "mqtt"
    display_name = SERVICE_TEMPLATE_META[app]["name_zh"]
    return [
        availability_rule(app, display_name),
        rule(key="mqtt_latency_high", name="MQTT连接响应偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=180, times=2, mode="core", enabled=True, template="连接响应偏高"),
        rule(key="mqtt_subscribe_failed", name="MQTT订阅失败", metric="canSubscribe", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="订阅失败", expr="canSubscribe == 'false'"),
        rule(key="mqtt_publish_failed", name="MQTT发布失败", metric="canPublish", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="发布失败", expr="canPublish == 'false'"),
        rule(key="mqtt_receive_failed", name="MQTT回环接收失败", metric="canReceive", operator="==", threshold=0, level="warning", period=180, times=2, mode="core", enabled=True, template="回环接收失败", expr="canReceive == 'false'"),
    ]


POLICIES: dict[str, list[dict]] = {
    "website": web_api_policies("website", SERVICE_TEMPLATE_META["website"]["name_zh"]),
    "api": web_api_policies("api", SERVICE_TEMPLATE_META["api"]["name_zh"]),
    "api_code": api_code_policies(),
    "ping": ping_like_policies("ping", SERVICE_TEMPLATE_META["ping"]["name_zh"], 150, 500),
    "port": ping_like_policies("port", SERVICE_TEMPLATE_META["port"]["name_zh"], 300, 1000),
    "udp_port": ping_like_policies("udp_port", SERVICE_TEMPLATE_META["udp_port"]["name_zh"], 500, 1500),
    "ssl_cert": ssl_cert_policies(),
    "nginx": nginx_policies(),
    "imap": mail_policies("imap"),
    "pop3": mail_policies("pop3"),
    "smtp": smtp_policies(),
    "ntp": ntp_policies(),
    "dns": dns_policies(),
    "ftp": ftp_policies(),
    "websocket": websocket_policies(),
    "mqtt": mqtt_policies(),
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
    for app in ALL_SERVICE_APPS:
        rules = POLICIES.get(app, [])
        if not rules:
            continue
        filepath = template_dir / f"app-{app}.yml"
        if not filepath.exists():
            missing.append(str(filepath))
            continue
        raw = filepath.read_text(encoding="utf-8")
        merged = _upsert_alerts(raw, _render_alerts(rules))
        filepath.write_text(merged, encoding="utf-8")
        updated.append(app)

    print(f"[service-default-alerts] updated: {len(updated)} -> {', '.join(updated)}")
    if missing:
        print("[service-default-alerts] missing template files:")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
