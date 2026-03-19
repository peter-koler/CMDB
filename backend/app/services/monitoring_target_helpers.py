from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import re


def _normalize_items(payload) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _safe_total(payload, items: list[dict]) -> int:
    if isinstance(payload, dict):
        total = payload.get("total")
        if isinstance(total, int):
            return total
        if isinstance(total, str) and total.isdigit():
            return int(total)
    return len(items)


def _parse_time(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _monitor_is_healthy(item: dict) -> bool:
    raw = item.get("status")
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"up", "online", "ok", "healthy", "normal", "running", "success"}:
            return True
        if normalized in {"down", "offline", "error", "critical", "abnormal", "failed"}:
            return False
    enabled = item.get("enabled")
    if isinstance(enabled, bool):
        return enabled
    return True


def _hourly_alert_trend(history_alerts: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    hour_floor = now.replace(minute=0, second=0, microsecond=0)
    points = [hour_floor - timedelta(hours=23 - i) for i in range(24)]
    counts = {point: 0 for point in points}

    for alert in history_alerts:
        ts = _parse_time(alert.get("triggered_at"))
        if not ts:
            continue
        bucket = ts.replace(minute=0, second=0, microsecond=0)
        if bucket in counts:
            counts[bucket] += 1

    return [{"time": point.strftime("%H:00"), "value": counts[point]} for point in points]


def _top_alert_monitors(current_alerts: list[dict], limit: int = 10) -> list[dict]:
    counter: Counter[str] = Counter()
    for alert in current_alerts:
        key = alert.get("monitor_name") or alert.get("instance") or alert.get("monitor_id")
        if key is None:
            continue
        counter[str(key)] += 1
    return [{"name": name, "value": value} for name, value in counter.most_common(limit)]


def _paginate_items(items: list[dict], page: int, page_size: int) -> tuple[list[dict], int]:
    total = len(items)
    start = (page - 1) * page_size
    if start >= total:
        return [], total
    return items[start : start + page_size], total


def _json_load(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _json_dump(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse_rfc3339_to_ms(raw: str | None) -> int | None:
    dt = _parse_time(raw)
    if not dt:
        return None
    return int(dt.timestamp() * 1000)


def _ms_to_rfc3339(value: int | None) -> str | None:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _now_naive_utc() -> datetime:
    return datetime.utcnow()


def _extract_notice_rule_ids(payload: dict) -> tuple[list[int] | None, str | None]:
    if "notice_rule_ids" in payload:
        raw = payload.get("notice_rule_ids")
    elif "notice_rule_id" in payload:
        raw = payload.get("notice_rule_id")
    else:
        return None, None
    if raw is None or raw == "":
        return [], None
    if isinstance(raw, list):
        candidates = raw
    else:
        candidates = [raw]
    ids: list[int] = []
    for item in candidates:
        if item is None or str(item).strip() == "":
            continue
        try:
            val = int(item)
        except (TypeError, ValueError):
            return None, "notice_rule_ids 必须是整数数组"
        if val <= 0:
            continue
        if val not in ids:
            ids.append(val)
    return ids, None


def _normalize_escalation_config(raw) -> tuple[str | None, str | None]:
    if raw is None or raw == "":
        return "", None

    payload = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return "", None
        try:
            payload = json.loads(text)
        except (TypeError, ValueError):
            return None, "escalation_config 必须是合法 JSON"

    enabled = True
    levels_raw = payload
    if isinstance(payload, dict):
        enabled = bool(payload.get("enabled", True))
        levels_raw = payload.get("levels", [])
    if not isinstance(levels_raw, list):
        return None, "escalation_config.levels 必须是数组"

    levels: list[dict] = []
    for idx, item in enumerate(levels_raw):
        if not isinstance(item, dict):
            return None, f"escalation_config.levels[{idx}] 必须是对象"
        try:
            delay_seconds = int(item.get("delay_seconds") or item.get("wait_seconds") or 0)
        except (TypeError, ValueError):
            return None, f"escalation_config.levels[{idx}].delay_seconds 必须是整数"
        if delay_seconds <= 0:
            return None, f"escalation_config.levels[{idx}].delay_seconds 必须大于0"
        notice_rule_ids: list[int] = []
        raw_ids = item.get("notice_rule_ids")
        if raw_ids is None and "notice_rule_id" in item:
            raw_ids = [item.get("notice_rule_id")]
        if raw_ids is None:
            raw_ids = []
        if not isinstance(raw_ids, list):
            raw_ids = [raw_ids]
        for v in raw_ids:
            if v in (None, ""):
                continue
            try:
                notice_id = int(v)
            except (TypeError, ValueError):
                return None, f"escalation_config.levels[{idx}].notice_rule_ids 必须是整数数组"
            if notice_id > 0 and notice_id not in notice_rule_ids:
                notice_rule_ids.append(notice_id)
        levels.append(
            {
                "level": max(int(item.get("level") or (idx + 1)), 1),
                "delay_seconds": delay_seconds,
                "notice_rule_ids": notice_rule_ids,
                "title_template": str(item.get("title_template") or "").strip(),
                "content_template": str(item.get("content_template") or item.get("template") or "").strip(),
            }
        )

    if enabled and not levels:
        return None, "escalation_config 启用时 levels 不能为空"
    normalized = {"enabled": enabled, "levels": levels}
    return _json_dump(normalized), None


def _parse_scalar(value: str):
    raw = str(value or "").strip()
    if raw == "":
        return ""
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except (TypeError, ValueError):
        return raw


def _extract_yaml_list_section(content: str, section_name: str) -> list[dict]:
    lines = (content or "").splitlines()
    section_index = -1
    section_indent = 0
    section_pattern = re.compile(rf"^(\s*){re.escape(section_name)}\s*:\s*$")
    for idx, line in enumerate(lines):
        if line.strip().startswith("#"):
            continue
        matched = section_pattern.match(line)
        if matched:
            section_index = idx
            section_indent = len(matched.group(1))
            break
    if section_index < 0:
        return []

    section_lines: list[str] = []
    for line in lines[section_index + 1 :]:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            section_lines.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= section_indent:
            break
        section_lines.append(line)

    items: list[dict] = []
    current: dict | None = None
    current_indent = None
    for line in section_lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped.startswith("- "):
            if current:
                items.append(current)
            current = {}
            current_indent = indent
            rest = stripped[2:].strip()
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue
        if current is None:
            continue
        if current_indent is not None and indent <= current_indent:
            items.append(current)
            current = None
            current_indent = None
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        current[key.strip()] = _parse_scalar(value)
    if current:
        items.append(current)
    return items


def _to_bool(value, default=False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _apply_recovery_config_to_labels(labels: dict, payload: dict):
    if not isinstance(labels, dict) or not isinstance(payload, dict):
        return
    payload_labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}

    if "auto_recover" in payload:
        labels["auto_recover"] = _to_bool(payload.get("auto_recover"), True)
    elif "auto_recover" in payload_labels:
        labels["auto_recover"] = _to_bool(payload_labels.get("auto_recover"), True)
    elif "auto_recover" not in labels:
        labels["auto_recover"] = True

    if "recover_times" in payload:
        labels["recover_times"] = max(_to_int(payload.get("recover_times"), 2), 1)
    elif "recover_times" in payload_labels:
        labels["recover_times"] = max(_to_int(payload_labels.get("recover_times"), 2), 1)
    elif "recover_times" not in labels:
        labels["recover_times"] = 2

    if "notify_on_recovered" in payload:
        labels["notify_on_recovered"] = _to_bool(payload.get("notify_on_recovered"), True)
    elif "notify_on_recovered" in payload_labels:
        labels["notify_on_recovered"] = _to_bool(payload_labels.get("notify_on_recovered"), True)
    elif "notify_on_recovered" not in labels:
        labels["notify_on_recovered"] = True


def _redis_default_alert_rules() -> list[dict]:
    return [
        {
            "name": "Redis实例不可用",
            "type": "realtime_metric",
            "metric": "redis_server_up",
            "operator": "==",
            "threshold": 0,
            "level": "critical",
            "period": 60,
            "times": 1,
            "expr": "redis_server_up == 0",
            "enabled": True,
            "template": "实例不可用",
        },
        {
            "name": "Redis内存使用率过高",
            "type": "periodic_metric",
            "metric": "used_memory",
            "operator": ">",
            "threshold": 85,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "(maxmemory > 0) && ((used_memory / maxmemory) * 100 > 85)",
            "enabled": True,
            "template": "内存使用率过高",
        },
        {
            "name": "Redis内存碎片严重",
            "type": "periodic_metric",
            "metric": "mem_fragmentation_ratio",
            "operator": ">",
            "threshold": 2.0,
            "level": "warning",
            "period": 600,
            "times": 1,
            "expr": "mem_fragmentation_ratio > 2.0",
            "enabled": True,
            "template": "内存碎片严重",
        },
        {
            "name": "Redis连接数饱和",
            "type": "realtime_metric",
            "metric": "connected_clients",
            "operator": ">",
            "threshold": 90,
            "level": "critical",
            "period": 300,
            "times": 1,
            "expr": "(maxclients > 0) && ((connected_clients / maxclients) * 100 > 90)",
            "enabled": True,
            "template": "连接数饱和",
        },
        {
            "name": "Redis拒绝连接",
            "type": "realtime_metric",
            "metric": "rejected_connections",
            "operator": ">",
            "threshold": 0,
            "level": "critical",
            "period": 300,
            "times": 1,
            "expr": "rejected_connections > 0",
            "enabled": True,
            "template": "拒绝连接",
        },
        {
            "name": "Redis主从延迟过高",
            "type": "periodic_metric",
            "metric": "master_last_io_seconds_ago",
            "operator": ">",
            "threshold": 5,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "master_last_io_seconds_ago > 5",
            "enabled": True,
            "template": "主从延迟",
        },
        {
            "name": "RedisRDB失败",
            "type": "realtime_metric",
            "metric": "rdb_last_bgsave_status_ok",
            "operator": "==",
            "threshold": 0,
            "level": "critical",
            "period": 60,
            "times": 1,
            "expr": "rdb_last_bgsave_status_ok == 0",
            "enabled": True,
            "template": "RDB失败",
        },
        {
            "name": "RedisAOF失败",
            "type": "realtime_metric",
            "metric": "aof_last_bgrewrite_status_ok",
            "operator": "==",
            "threshold": 0,
            "level": "critical",
            "period": 60,
            "times": 1,
            "expr": "aof_last_bgrewrite_status_ok == 0",
            "enabled": True,
            "template": "AOF失败",
        },
    ]


def _mysql_default_alert_rules() -> list[dict]:
    return [
        {
            "name": "MySQL实例不可用",
            "type": "realtime_metric",
            "metric": "mysql_server_up",
            "operator": "==",
            "threshold": 0,
            "level": "critical",
            "period": 60,
            "times": 1,
            "expr": "mysql_server_up == 0",
            "enabled": True,
            "template": "实例不可用",
        },
        {
            "name": "MySQL连接利用率过高",
            "type": "periodic_metric",
            "metric": "max_used_connections",
            "operator": ">",
            "threshold": 90,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "(max_connections > 0) && ((max_used_connections / max_connections) * 100 > 90)",
            "enabled": True,
            "template": "连接利用率过高",
        },
        {
            "name": "MySQL活动线程过高",
            "type": "periodic_metric",
            "metric": "threads_running",
            "operator": ">",
            "threshold": 100,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "threads_running > 100",
            "enabled": True,
            "template": "活动线程过高",
        },
        {
            "name": "MySQL连接失败持续增长",
            "type": "periodic_metric",
            "metric": "aborted_connects",
            "operator": ">",
            "threshold": 10,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "aborted_connects > 10",
            "enabled": True,
            "template": "连接失败持续增长",
        },
        {
            "name": "MySQL InnoDB 缓冲命中率偏低",
            "type": "periodic_metric",
            "metric": "innodb_buffer_hit_rate",
            "operator": "<",
            "threshold": 90,
            "level": "warning",
            "period": 600,
            "times": 1,
            "expr": "innodb_buffer_hit_rate < 90",
            "enabled": True,
            "template": "InnoDB 缓冲命中率偏低",
        },
        {
            "name": "MySQL表锁等待过高",
            "type": "periodic_metric",
            "metric": "table_locks_waited",
            "operator": ">",
            "threshold": 10,
            "level": "warning",
            "period": 300,
            "times": 1,
            "expr": "table_locks_waited > 10",
            "enabled": True,
            "template": "表锁等待过高",
        },
    ]


_RECEIVER_TYPE_TO_CHANNEL = {
    0: "sms",
    1: "email",
    2: "webhook",
    4: "wecom",
    5: "dingtalk",
    6: "feishu",
    10: "wechat",
    15: "system",
}
_CHANNEL_TO_RECEIVER_TYPE = {v: k for k, v in _RECEIVER_TYPE_TO_CHANNEL.items()}


def _receiver_channel_name(receiver_type: int) -> str:
    return _RECEIVER_TYPE_TO_CHANNEL.get(receiver_type, "webhook")


def _resolve_receiver_type(channel: str | None) -> int:
    if not channel:
        return 2
    return _CHANNEL_TO_RECEIVER_TYPE.get(channel.strip().lower(), 2)
