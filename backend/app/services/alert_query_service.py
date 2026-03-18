from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping


def extract_rule_id(labels: dict, annotations: dict) -> int | None:
    if not isinstance(labels, dict):
        labels = {}
    if not isinstance(annotations, dict):
        annotations = {}
    for key in (
        "rule_id",
        "alert_rule_id",
        "alert_rule",
        "alert_rule_id",
        "ruleId",
        "alertRuleId",
        "alert_ruleId",
    ):
        raw = labels.get(key) if key in labels else annotations.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def normalize_source_value(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    raw = str(value).strip()
    if not raw:
        return None, None
    normalized = raw.lower()
    if normalized in {"local", "internal", "hertzbeat", "hb", "self"}:
        return "local", None
    return "external", raw


def extract_alert_item(
    *,
    row_id: int,
    labels_json: str | None,
    annotations_json: str | None,
    content: str | None,
    status: str,
    start_at: int | None,
    end_at: int | None,
    created_at: datetime | None,
    json_load: Callable[[str | None, dict], dict],
    ms_to_rfc3339: Callable[[int | None], str | None],
    now_ms_provider: Callable[[], int],
) -> dict:
    labels = json_load(labels_json, {})
    annotations = json_load(annotations_json, {})
    rule_id = extract_rule_id(labels, annotations)
    level = str(labels.get("severity") or annotations.get("severity") or "warning")
    name = (
        labels.get("alertname")
        or annotations.get("summary")
        or annotations.get("title")
        or content
        or f"alert-{row_id}"
    )
    monitor_name = (
        labels.get("monitor_name")
        or labels.get("instance")
        or labels.get("app")
        or labels.get("target")
        or "-"
    )
    monitor_id = labels.get("monitor_id")
    try:
        monitor_id = int(monitor_id) if monitor_id is not None else None
    except (TypeError, ValueError):
        monitor_id = None
    assignee = labels.get("assignee") or annotations.get("assignee")
    note = annotations.get("note")
    app = str(labels.get("app") or "")
    instance = str(labels.get("instance") or labels.get("target") or "")
    action = str(annotations.get("action") or labels.get("action") or "").strip().lower() or None
    escalation_level = annotations.get("escalation_level", labels.get("escalation_level"))
    try:
        escalation_level = int(escalation_level) if escalation_level is not None else None
    except (TypeError, ValueError):
        escalation_level = None
    triggered_ms = start_at or (
        int(created_at.replace(tzinfo=timezone.utc).timestamp() * 1000) if created_at else None
    )
    recovered_ms = end_at
    duration_seconds = 0
    if triggered_ms:
        tail = recovered_ms or now_ms_provider()
        duration_seconds = max(int((tail - triggered_ms) / 1000), 0)
    source_keys = (
        "source",
        "integration",
        "integration_source",
        "provider",
        "alert_source",
        "origin",
        "from",
    )
    source_value = None
    for key in source_keys:
        if key in labels and labels.get(key):
            source_value = labels.get(key)
            break
        if key in annotations and annotations.get(key):
            source_value = annotations.get(key)
            break
    source_type, source_name = normalize_source_value(source_value)
    if not source_type:
        source_type = "local" if monitor_id else "external"
    return {
        "id": row_id,
        "level": level,
        "name": str(name),
        "content": str(content or ""),
        "status": "open" if status == "firing" else "closed",
        "monitor_name": str(monitor_name),
        "monitor_id": monitor_id,
        "app": app,
        "instance": instance,
        "metric": labels.get("metric"),
        "metric_value": labels.get("value"),
        "threshold": labels.get("threshold"),
        "rule_id": rule_id,
        "triggered_at": ms_to_rfc3339(triggered_ms),
        "recovered_at": ms_to_rfc3339(recovered_ms),
        "duration_seconds": duration_seconds,
        "assignee": assignee,
        "note": note,
        "action": action,
        "escalation_level": escalation_level,
        "source_type": source_type,
        "source_name": source_name,
    }


def filter_alert_items(
    items: list[dict],
    *,
    query_args: Mapping[str, str],
    parse_rfc3339_to_ms: Callable[[str | None], int | None],
) -> list[dict]:
    level = str(query_args.get("level") or "").strip().lower()
    status = str(query_args.get("status") or "").strip().lower()
    name = str(query_args.get("name") or "").strip().lower()
    monitor_name = str(query_args.get("monitor_name") or "").strip().lower()
    q = str(query_args.get("q") or "").strip().lower()
    monitor_id = str(query_args.get("monitor_id") or "").strip()
    app = str(query_args.get("app") or "").strip().lower()
    instance = str(query_args.get("instance") or "").strip().lower()
    metric = str(query_args.get("metric") or "").strip().lower()
    assignee = str(query_args.get("assignee") or "").strip().lower()
    rule_id = str(query_args.get("rule_id") or "").strip()
    start_ms = parse_rfc3339_to_ms(query_args.get("start_at"))
    end_ms = parse_rfc3339_to_ms(query_args.get("end_at"))

    out: list[dict] = []
    for item in items:
        if level and str(item.get("level", "")).lower() != level:
            continue
        if status in {"open", "closed"} and str(item.get("status", "")).lower() != status:
            continue
        if monitor_id and str(item.get("monitor_id") or "") != monitor_id:
            continue
        if app and str(item.get("app") or "").strip().lower() != app:
            continue
        if name and name not in str(item.get("name") or "").strip().lower():
            continue
        if monitor_name and monitor_name not in str(item.get("monitor_name") or "").strip().lower():
            continue
        if instance and instance not in str(item.get("instance") or "").strip().lower():
            continue
        if metric and str(item.get("metric") or "").strip().lower() != metric:
            continue
        if rule_id and str(item.get("rule_id") or "").strip() != rule_id:
            continue
        if assignee and assignee not in str(item.get("assignee") or "").strip().lower():
            continue
        if q:
            hay = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("monitor_name") or ""),
                    str(item.get("metric") or ""),
                    str(item.get("assignee") or ""),
                    str(item.get("note") or ""),
                ]
            ).lower()
            if q not in hay:
                continue
        if start_ms or end_ms:
            ts = parse_rfc3339_to_ms(item.get("triggered_at"))
            if start_ms and (not ts or ts < start_ms):
                continue
            if end_ms and (not ts or ts > end_ms):
                continue
        out.append(item)
    return out
