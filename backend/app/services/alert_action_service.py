from __future__ import annotations

from datetime import datetime
from typing import Callable

from app import db
from app.models import AlertHistory, SingleAlert


def apply_acknowledge(
    alert_id: int,
    *,
    payload: dict,
    current_username: str | None,
    json_load: Callable[[str | None, dict], dict],
    json_dump: Callable[[dict], str],
    now_provider: Callable[[], datetime],
    record_timeline_event: Callable[..., None],
) -> SingleAlert | None:
    row = SingleAlert.query.get(alert_id)
    if not row:
        return None
    labels = json_load(row.labels_json, {})
    annotations = json_load(row.annotations_json, {})
    assignee = str(payload.get("assignee") or (current_username or "system"))
    labels["assignee"] = assignee
    note = payload.get("note")
    if note:
        annotations["note"] = str(note)
    row.labels_json = json_dump(labels)
    row.annotations_json = json_dump(annotations)
    row.modifier = assignee
    row.updated_at = now_provider()
    record_timeline_event(
        alert_id=row.id,
        event_type="acknowledge",
        title="告警受理",
        content=(f"处理人：{assignee}" + (f"；备注：{str(note).strip()}" if note else "")),
        operator=(current_username or assignee),
        payload={"assignee": assignee, "note": str(note).strip() if note else None},
    )
    db.session.commit()
    return row


def apply_claim(
    alert_id: int,
    *,
    payload: dict,
    current_username: str | None,
    json_load: Callable[[str | None, dict], dict],
    json_dump: Callable[[dict], str],
    now_provider: Callable[[], datetime],
    record_timeline_event: Callable[..., None],
) -> SingleAlert | None:
    row = SingleAlert.query.get(alert_id)
    if not row:
        return None
    labels = json_load(row.labels_json, {})
    annotations = json_load(row.annotations_json, {})
    assignee = str(payload.get("assignee") or (current_username or "system"))
    labels["assignee"] = assignee
    note = payload.get("note")
    if note:
        annotations["note"] = str(note)
    row.labels_json = json_dump(labels)
    row.annotations_json = json_dump(annotations)
    row.modifier = assignee
    row.updated_at = now_provider()
    record_timeline_event(
        alert_id=row.id,
        event_type="dispatch",
        title="告警分派",
        content=(f"分派给：{assignee}" + (f"；备注：{str(note).strip()}" if note else "")),
        operator=(current_username or assignee),
        payload={"assignee": assignee, "note": str(note).strip() if note else None},
    )
    db.session.commit()
    return row


def apply_close(
    alert_id: int,
    *,
    operator: str | None,
    now_ms_provider: Callable[[], int],
    now_provider: Callable[[], datetime],
    record_timeline_event: Callable[..., None],
) -> SingleAlert | None:
    row = SingleAlert.query.get(alert_id)
    if not row:
        return None
    now_ms = now_ms_provider()
    if row.start_at is None:
        row.start_at = now_ms
    if row.status != "resolved":
        row.status = "resolved"
        row.end_at = now_ms
        row.updated_at = now_provider()
        duration_ms = max((row.end_at or now_ms) - (row.start_at or now_ms), 0)
        history = AlertHistory(
            alert_id=row.id,
            alert_type="single",
            labels_json=row.labels_json or "{}",
            annotations_json=row.annotations_json or "{}",
            content=row.content,
            status=row.status,
            trigger_times=max(row.trigger_times or 1, 1),
            start_at=row.start_at,
            end_at=row.end_at,
            duration_ms=duration_ms,
            created_at=now_provider(),
        )
        db.session.add(history)
        record_timeline_event(
            alert_id=row.id,
            event_type="closed",
            title="告警关闭",
            content="手动关闭告警",
            operator=(operator or "system"),
            payload={"status": "closed"},
        )
        db.session.commit()
    return row


def apply_delete(
    alert_id: int,
    *,
    scope: str,
) -> dict | None:
    deleted_current = False
    deleted_history = False
    cascade_history = False

    if scope in {"", "all", "current"}:
        row = SingleAlert.query.get(alert_id)
        if row:
            db.session.delete(row)
            deleted_current = True
        if scope in {"", "all"}:
            removed = AlertHistory.query.filter_by(alert_id=alert_id).delete(
                synchronize_session=False
            )
            cascade_history = bool(removed)
            deleted_history = deleted_history or cascade_history

    if scope in {"", "all", "history"}:
        row = AlertHistory.query.get(alert_id)
        if row:
            db.session.delete(row)
            deleted_history = True

    if not deleted_current and not deleted_history:
        db.session.rollback()
        return None

    db.session.commit()
    return {
        "id": alert_id,
        "scope": scope or "all",
        "deleted_current": deleted_current,
        "deleted_history": deleted_history,
        "cascade_history": cascade_history,
    }
