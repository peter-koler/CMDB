#!/usr/bin/env python3
"""
为服务器设备模板写入差异化默认告警策略（alerts）。
覆盖：
- ipmi
- hikvision_isapi
- dahua
- uniview
- synology_nas
- idrac
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
        name=f"{display_name}设备不可用",
        metric=metric,
        operator="==",
        threshold=0,
        level="critical",
        period=60,
        times=1,
        mode="core",
        enabled=True,
        expr=f"{metric} == 0",
        template="设备不可用",
        rule_type="realtime_metric",
    )


def ipmi_policies() -> list[dict]:
    app = "ipmi"
    name = "IPMI2"
    return [
        availability_rule(app, name),
        rule(key="ipmi_system_power_off", name="IPMI系统电源异常", metric="system_power", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="系统电源异常", expr="system_power != 'on'", rule_type="realtime_metric"),
        rule(key="ipmi_power_fault", name="IPMI主电源故障", metric="power_fault", operator="==", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="主电源故障", expr="power_fault == 'true'", rule_type="realtime_metric"),
        rule(key="ipmi_power_overload", name="IPMI电源过载", metric="power_overload", operator="==", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="电源过载", expr="power_overload == 'true'", rule_type="realtime_metric"),
        rule(key="ipmi_fan_fault", name="IPMI风扇故障", metric="fan_fault", operator="==", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="风扇故障", expr="fan_fault == 'true'", rule_type="realtime_metric"),
        rule(key="ipmi_drive_fault", name="IPMI磁盘故障", metric="drive_fault", operator="==", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="磁盘故障", expr="drive_fault == 'true'", rule_type="realtime_metric"),
        rule(key="ipmi_sensor_temp_alert", name="IPMI温度传感器异常", metric="sensor_type", operator="==", threshold=0, level="warning", period=120, times=1, mode="extended", enabled=False, template="温度传感器异常", expr="sensor_type == 'Temperature' && sensor_reading == 'na'", rule_type="realtime_metric"),
        rule(key="ipmi_sensor_fan_alert", name="IPMI风扇传感器异常", metric="sensor_type", operator="==", threshold=0, level="warning", period=120, times=1, mode="extended", enabled=False, template="风扇传感器异常", expr="sensor_type == 'Fan' && sensor_reading == 'na'", rule_type="realtime_metric"),
        rule(key="ipmi_power_control_fault", name="IPMI电源控制异常", metric="power_control_fault", operator="==", threshold=1, level="warning", period=300, times=2, mode="extended", enabled=False, template="电源控制异常", expr="power_control_fault == 'true'"),
        rule(key="ipmi_panel_lockout", name="IPMI前面板锁定激活", metric="front_panel_lockout_active", operator="==", threshold=1, level="warning", period=300, times=1, mode="extended", enabled=False, template="前面板锁定激活", expr="front_panel_lockout_active == 'true'"),
    ]


def hikvision_policies() -> list[dict]:
    app = "hikvision_isapi"
    name = "海康 ISAPI"
    return [
        availability_rule(app, name),
        rule(key="hikvision_cpu_high", name="海康设备CPU偏高", metric="CPU_utilization", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="CPU偏高"),
        rule(key="hikvision_cpu_critical", name="海康设备CPU过高", metric="CPU_utilization", operator=">", threshold=95, level="critical", period=120, times=1, mode="core", enabled=True, template="CPU过高"),
        rule(key="hikvision_memory_high", name="海康设备内存使用偏高", metric="memory_usage", operator=">", threshold=2048, level="warning", period=300, times=2, mode="core", enabled=True, template="内存使用偏高"),
        rule(key="hikvision_memory_low", name="海康设备可用内存偏低", metric="memory_available", operator="<", threshold=256, level="critical", period=120, times=1, mode="core", enabled=True, template="可用内存偏低"),
        rule(key="hikvision_response_time_high", name="海康设备响应时间偏高", metric="response_time", operator=">", threshold=1000, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="hikvision_response_time_critical", name="海康设备响应时间过高", metric="response_time", operator=">", threshold=3000, level="critical", period=120, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="hikvision_upload_time_high", name="海康上传耗时偏高", metric="avg_upload_time", operator=">", threshold=2000, level="warning", period=600, times=2, mode="extended", enabled=False, template="上传耗时偏高"),
        rule(key="hikvision_net1_down", name="海康网口1速度异常", metric="net_port_1_speed", operator="<", threshold=1, level="warning", period=300, times=2, mode="extended", enabled=False, template="网口1速度异常"),
        rule(key="hikvision_net2_down", name="海康网口2速度异常", metric="net_port_2_speed", operator="<", threshold=1, level="warning", period=300, times=2, mode="extended", enabled=False, template="网口2速度异常"),
        rule(key="hikvision_uptime_short", name="海康设备运行时长过短", metric="device_uptime", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短", expr="device_uptime == ''", rule_type="realtime_metric"),
    ]


def dahua_policies() -> list[dict]:
    app = "dahua"
    name = "大华设备"
    return [
        availability_rule(app, name),
        rule(key="dahua_network_missing", name="大华网络配置缺失", metric="eth0_ip_address", operator="==", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="网络配置缺失", expr="eth0_ip_address == ''", rule_type="realtime_metric"),
        rule(key="dahua_gateway_missing", name="大华默认网关缺失", metric="eth0_gateway", operator="==", threshold=0, level="warning", period=300, times=1, mode="core", enabled=True, template="默认网关缺失", expr="eth0_gateway == ''", rule_type="realtime_metric"),
        rule(key="dahua_dns_missing", name="大华DNS未配置", metric="eth0_dns1", operator="==", threshold=0, level="warning", period=600, times=1, mode="core", enabled=True, template="DNS未配置", expr="eth0_dns1 == ''", rule_type="realtime_metric"),
        rule(key="dahua_mtu_abnormal", name="大华MTU配置异常", metric="eth0_mtu", operator="<", threshold=1200, level="warning", period=600, times=2, mode="extended", enabled=False, template="MTU配置异常"),
        rule(key="dahua_ntp_missing", name="大华NTP地址缺失", metric="ntp_address", operator="==", threshold=0, level="warning", period=600, times=1, mode="core", enabled=True, template="NTP地址缺失", expr="ntp_address == ''", rule_type="realtime_metric"),
        rule(key="dahua_ntp_port_abnormal", name="大华NTP端口异常", metric="ntp_port", operator="!=", threshold=123, level="warning", period=600, times=2, mode="extended", enabled=False, template="NTP端口异常"),
        rule(key="dahua_ntp_period_too_long", name="大华NTP同步周期过长", metric="ntp_update_period", operator=">", threshold=86400, level="warning", period=1800, times=1, mode="extended", enabled=False, template="NTP同步周期过长"),
        rule(key="dahua_active_user_exists", name="大华存在活跃用户登录", metric="Name", operator="==", threshold=0, level="warning", period=300, times=1, mode="extended", enabled=False, template="存在活跃用户登录", expr="Name != ''", rule_type="realtime_metric"),
        rule(key="dahua_domain_missing", name="大华域名未配置", metric="domain_name", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="域名未配置", expr="domain_name == ''", rule_type="realtime_metric"),
    ]


def uniview_policies() -> list[dict]:
    app = "uniview"
    name = "宇视设备"
    return [
        availability_rule(app, name),
        rule(key="uniview_ntp_disabled", name="宇视NTP未启用", metric="Enabled", operator="==", threshold=0, level="warning", period=600, times=1, mode="core", enabled=True, template="NTP未启用", expr="Enabled == 'false'", rule_type="realtime_metric"),
        rule(key="uniview_ntp_server_missing", name="宇视NTP服务器缺失", metric="IPAddress", operator="==", threshold=0, level="warning", period=600, times=1, mode="core", enabled=True, template="NTP服务器缺失", expr="IPAddress == ''", rule_type="realtime_metric"),
        rule(key="uniview_ntp_port_abnormal", name="宇视NTP端口异常", metric="Port", operator="!=", threshold=123, level="warning", period=600, times=2, mode="extended", enabled=False, template="NTP端口异常"),
        rule(key="uniview_sync_interval_too_long", name="宇视NTP同步周期过长", metric="SynchronizeInterval", operator=">", threshold=86400, level="warning", period=1800, times=1, mode="extended", enabled=False, template="NTP同步周期过长"),
        rule(key="uniview_firmware_missing", name="宇视固件版本缺失", metric="FirmwareVersion", operator="==", threshold=0, level="warning", period=3600, times=1, mode="core", enabled=True, template="固件版本缺失", expr="FirmwareVersion == ''", rule_type="realtime_metric"),
        rule(key="uniview_model_missing", name="宇视设备型号缺失", metric="DeviceModel", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="设备型号缺失", expr="DeviceModel == ''", rule_type="realtime_metric"),
        rule(key="uniview_serial_missing", name="宇视序列号缺失", metric="SerialNumber", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="序列号缺失", expr="SerialNumber == ''", rule_type="realtime_metric"),
        rule(key="uniview_device_name_missing", name="宇视设备名称缺失", metric="DeviceName", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="设备名称缺失", expr="DeviceName == ''", rule_type="realtime_metric"),
        rule(key="uniview_ntp_ip_loopback", name="宇视NTP地址配置异常", metric="IPAddress", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="NTP地址配置异常", expr="IPAddress == '127.0.0.1'", rule_type="realtime_metric"),
    ]


def synology_policies() -> list[dict]:
    app = "synology_nas"
    name = "群晖 NAS"
    return [
        availability_rule(app, name),
        rule(key="synology_system_status_abnormal", name="群晖系统状态异常", metric="systemStatus", operator="!=", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="系统状态异常"),
        rule(key="synology_power_status_abnormal", name="群晖电源状态异常", metric="powerStatus", operator="!=", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="电源状态异常"),
        rule(key="synology_thermal_status_abnormal", name="群晖温控状态异常", metric="thermalStatus", operator="!=", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="温控状态异常"),
        rule(key="synology_cpu_high", name="群晖CPU使用率偏高", metric="cpuUtilization", operator=">", threshold=85, level="warning", period=300, times=2, mode="core", enabled=True, template="CPU使用率偏高"),
        rule(key="synology_cpu_critical", name="群晖CPU使用率过高", metric="cpuUtilization", operator=">", threshold=95, level="critical", period=120, times=1, mode="core", enabled=True, template="CPU使用率过高"),
        rule(key="synology_mem_high", name="群晖内存使用率偏高", metric="memUtilization", operator=">", threshold=85, level="warning", period=300, times=2, mode="core", enabled=True, template="内存使用率偏高"),
        rule(key="synology_disk_health_bad", name="群晖磁盘健康状态异常", metric="diskHealthStatus", operator="!=", threshold=1, level="critical", period=300, times=1, mode="core", enabled=True, template="磁盘健康状态异常"),
        rule(key="synology_raid_status_bad", name="群晖RAID状态异常", metric="raidStatus", operator="!=", threshold=1, level="critical", period=300, times=1, mode="core", enabled=True, template="RAID状态异常"),
        rule(key="synology_temperature_high", name="群晖温度偏高", metric="temperature", operator=">", threshold=70, level="warning", period=300, times=2, mode="extended", enabled=False, template="温度偏高"),
        rule(key="synology_space_iola15_high", name="群晖存储负载偏高", metric="spaceIOLA15", operator=">", threshold=30, level="warning", period=300, times=2, mode="extended", enabled=False, template="存储负载偏高"),
    ]


def idrac_policies() -> list[dict]:
    app = "idrac"
    name = "Dell iDRAC"
    return [
        availability_rule(app, name),
        rule(key="idrac_global_abnormal", name="iDRAC全局状态异常", metric="global", operator="!=", threshold=3, level="critical", period=60, times=1, mode="core", enabled=True, template="全局状态异常"),
        rule(key="idrac_power_abnormal", name="iDRAC电源状态异常", metric="power", operator="!=", threshold=3, level="critical", period=60, times=1, mode="core", enabled=True, template="电源状态异常"),
        rule(key="idrac_storage_abnormal", name="iDRAC存储状态异常", metric="storage", operator="!=", threshold=3, level="critical", period=120, times=1, mode="core", enabled=True, template="存储状态异常"),
        rule(key="idrac_lcd_abnormal", name="iDRAC LCD状态异常", metric="lcd", operator="!=", threshold=3, level="warning", period=300, times=1, mode="extended", enabled=False, template="LCD状态异常"),
        rule(key="idrac_uptime_short", name="iDRAC运行时长过短", metric="up_time", operator="<", threshold=3600, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短"),
        rule(key="idrac_psu_input_wattage_high", name="iDRAC电源输入功率偏高", metric="input_wattage", operator=">", threshold=800, level="warning", period=300, times=2, mode="core", enabled=True, template="电源输入功率偏高"),
        rule(key="idrac_psu_status_bad", name="iDRAC电源模块状态异常", metric="status", operator="!=", threshold=3, level="critical", period=120, times=1, mode="core", enabled=True, template="电源模块状态异常"),
        rule(key="idrac_temp_high", name="iDRAC温度读数偏高", metric="reading", operator=">", threshold=75, level="warning", period=300, times=2, mode="core", enabled=True, template="温度读数偏高"),
        rule(key="idrac_fan_speed_low", name="iDRAC风扇转速偏低", metric="current_speed", operator="<", threshold=1000, level="warning", period=300, times=2, mode="extended", enabled=False, template="风扇转速偏低"),
    ]


POLICIES: dict[str, list[dict]] = {
    "ipmi": ipmi_policies(),
    "hikvision_isapi": hikvision_policies(),
    "dahua": dahua_policies(),
    "uniview": uniview_policies(),
    "synology_nas": synology_policies(),
    "idrac": idrac_policies(),
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
