from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from app import db
from app.models import AlertTimelineEvent


def datetime_to_ms(value: datetime | None) -> int | None:
    if not value:
        return None
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def record_alert_timeline_event(
    alert_id: int,
    event_type: str,
    title: str,
    *,
    content: str | None = None,
    operator: str | None = None,
    payload: dict | None = None,
    json_dump: Callable[[dict], str],
    now_provider: Callable[[], datetime],
) -> None:
    row = AlertTimelineEvent(
        alert_id=alert_id,
        event_type=str(event_type or "").strip() or "event",
        title=str(title or "").strip() or "事件",
        content=(str(content).strip() if content is not None else None) or None,
        operator=(str(operator).strip() if operator is not None else None) or None,
        payload_json=json_dump(payload or {}),
        created_at=now_provider(),
    )
    db.session.add(row)


def timeline_event_from_row(
    row: AlertTimelineEvent,
    *,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> dict:
    happened_ms = datetime_to_ms(row.created_at)
    return {
        "id": f"manual-{row.id}",
        "event_type": row.event_type,
        "title": row.title,
        "content": row.content,
        "operator": row.operator,
        "source": "manual",
        "payload": row.payload,
        "happened_at": ms_to_rfc3339(happened_ms),
        "happened_ms": happened_ms,
    }


def append_base_events(
    events: list[dict],
    *,
    root_alert_id: int,
    base_item: dict,
    scope: str,
    triggered_ms: int | None,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> None:
    if triggered_ms:
        events.append(
            {
                "id": f"trigger-{root_alert_id}",
                "event_type": "triggered",
                "title": "告警产生",
                "content": f"{base_item.get('name') or '告警'} 触发",
                "operator": None,
                "source": "system",
                "payload": {"status": base_item.get("status"), "scope": scope},
                "happened_at": ms_to_rfc3339(triggered_ms),
                "happened_ms": triggered_ms,
            }
        )

    source_name = str(base_item.get("source_name") or "").strip()
    source_type = str(base_item.get("source_type") or "").strip() or "external"
    if source_type == "local":
        source_text = "本地监控"
    elif source_name:
        source_text = f"外部接入（{source_name}）"
    else:
        source_text = "外部接入"
    events.append(
        {
            "id": f"source-{root_alert_id}",
            "event_type": "source",
            "title": "告警来源",
            "content": source_text,
            "operator": None,
            "source": "system",
            "payload": {"source_type": source_type, "source_name": source_name or None},
            "happened_at": ms_to_rfc3339(triggered_ms),
            "happened_ms": triggered_ms,
        }
    )


def append_notification_events(
    events: list[dict],
    *,
    notify_rows: list,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> None:
    for row in notify_rows:
        dispatch_ms = datetime_to_ms(row.created_at)
        events.append(
            {
                "id": f"notify-dispatch-{row.id}",
                "event_type": "notification_dispatch",
                "title": "通知分派",
                "content": f"通知渠道：{row.notify_type or '-'}，接收对象：{row.receiver_type or '-'}#{row.receiver_id or '-'}",
                "operator": None,
                "source": "notification",
                "payload": {
                    "notify_type": row.notify_type,
                    "receiver_type": row.receiver_type,
                    "receiver_id": row.receiver_id,
                },
                "happened_at": ms_to_rfc3339(dispatch_ms),
                "happened_ms": dispatch_ms,
            }
        )
        if row.status in {2, 3}:
            receive_ms = row.sent_at or dispatch_ms
            events.append(
                {
                    "id": f"notify-result-{row.id}",
                    "event_type": "notification_received" if row.status == 2 else "notification_failed",
                    "title": "通知接收" if row.status == 2 else "通知失败",
                    "content": (row.content or row.error_msg or "").strip() or None,
                    "operator": None,
                    "source": "notification",
                    "payload": {"status": row.status, "notify_type": row.notify_type},
                    "happened_at": ms_to_rfc3339(receive_ms),
                    "happened_ms": receive_ms,
                }
            )


def append_escalation_events(
    events: list[dict],
    *,
    escalation_rows: list,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> None:
    for row in escalation_rows:
        try:
            ann = json.loads(row.annotations_json or "{}")
        except (TypeError, ValueError):
            ann = {}
        if not isinstance(ann, dict):
            ann = {}
        if str(ann.get("action") or "").strip().lower() != "escalated":
            continue
        level = ann.get("escalation_level")
        happened_ms = row.start_at or datetime_to_ms(row.created_at)
        events.append(
            {
                "id": f"escalation-{row.id}",
                "event_type": "escalated",
                "title": f"告警升级{f' L{level}' if level is not None else ''}",
                "content": row.content or ann.get("note") or None,
                "operator": None,
                "source": "escalation",
                "payload": {"escalation_level": level},
                "happened_at": ms_to_rfc3339(happened_ms),
                "happened_ms": happened_ms,
            }
        )


def append_closed_event(
    events: list[dict],
    *,
    root_alert_id: int,
    resolved_ms: int | None,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> None:
    if not resolved_ms:
        return
    events.append(
        {
            "id": f"closed-{root_alert_id}",
            "event_type": "closed",
            "title": "告警关闭",
            "content": "告警已关闭",
            "operator": None,
            "source": "system",
            "payload": {"status": "closed"},
            "happened_at": ms_to_rfc3339(resolved_ms),
            "happened_ms": resolved_ms,
        }
    )


def finalize_timeline(events: list[dict]) -> list[dict]:
    out = [item for item in events if item.get("happened_ms")]
    out.sort(
        key=lambda item: (int(item.get("happened_ms") or 0), str(item.get("id") or "")),
        reverse=True,
    )
    return out
