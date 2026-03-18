from __future__ import annotations

from datetime import timezone
from typing import Callable, Mapping

from app import db
from app.models import AlertHistory, AlertNotification, SingleAlert
from app.notifications.models import Notification, NotificationRecipient


def notification_from_model(
    row: AlertNotification,
    *,
    ms_to_rfc3339: Callable[[int | None], str | None],
) -> dict:
    return {
        "id": row.id,
        "alert_id": row.alert_id,
        "rule_id": row.rule_id,
        "receiver_type": row.receiver_type,
        "receiver_id": row.receiver_id,
        "notify_type": row.notify_type,
        "status": row.status,
        "content": row.content,
        "error_msg": row.error_msg,
        "retry_times": row.retry_times,
        "sent_at": ms_to_rfc3339(row.sent_at),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _system_notify_status_code(delivery_status: str | None) -> int:
    state = str(delivery_status or "").strip().lower()
    if state in {"", "pending"}:
        return 2
    if state in {"delivered", "success", "sent"}:
        return 2
    if state in {"failed", "permanent_failure"}:
        return 3
    if state in {"sending", "processing"}:
        return 1
    return 0


def _get_alert_context(
    alert_id: int,
    *,
    json_load: Callable[[str | None, dict], dict],
) -> dict:
    row = SingleAlert.query.get(alert_id)
    if row:
        labels = json_load(row.labels_json, {})
        return {
            "rule_name": str(labels.get("alertname") or "").strip(),
            "monitor_id": str(labels.get("monitor_id") or "").strip(),
        }
    history = AlertHistory.query.get(alert_id)
    if history:
        labels = json_load(history.labels_json, {})
        return {
            "rule_name": str(labels.get("alertname") or "").strip(),
            "monitor_id": str(labels.get("monitor_id") or "").strip(),
        }
    return {"rule_name": "", "monitor_id": ""}


def list_system_notifications_for_alert(
    alert_id: int,
    *,
    query_args: Mapping[str, str],
    parse_rfc3339_to_ms: Callable[[str | None], int | None],
    ms_to_rfc3339: Callable[[int | None], str | None],
    json_load: Callable[[str | None, dict], dict],
) -> list[dict]:
    notify_type = str(query_args.get("notify_type") or "").strip().lower()
    receiver_type = str(query_args.get("receiver_type") or "").strip().lower()
    status = query_args.get("status")
    q = str(query_args.get("q") or "").strip().lower()
    start_ms = parse_rfc3339_to_ms(query_args.get("start_at"))
    end_ms = parse_rfc3339_to_ms(query_args.get("end_at"))

    if notify_type and notify_type != "system":
        return []
    if receiver_type and receiver_type != "user":
        return []

    ctx = _get_alert_context(alert_id, json_load=json_load)
    monitor_id = str(ctx.get("monitor_id") or "").strip()
    rule_name = str(ctx.get("rule_name") or "").strip()
    if not monitor_id:
        return []

    query = (
        db.session.query(NotificationRecipient, Notification)
        .join(Notification, NotificationRecipient.notification_id == Notification.id)
        .filter(Notification.content.ilike(f"%monitor={monitor_id}%"))
        .order_by(Notification.created_at.desc(), NotificationRecipient.id.desc())
    )
    if rule_name:
        query = query.filter(
            db.or_(
                Notification.title.ilike(f"%{rule_name}%"),
                Notification.content.ilike(f"%{rule_name}%"),
            )
        )

    items: list[dict] = []
    for recipient, notice in query.all():
        status_code = _system_notify_status_code(recipient.delivery_status)
        if status is not None and str(status).strip() != "":
            try:
                status_val = int(status)
                if status_code != status_val:
                    continue
            except (TypeError, ValueError):
                pass
        sent_at_ms = None
        if notice.created_at:
            sent_at_ms = int(notice.created_at.replace(tzinfo=timezone.utc).timestamp() * 1000)
        if start_ms and (not sent_at_ms or sent_at_ms < start_ms):
            continue
        if end_ms and (not sent_at_ms or sent_at_ms > end_ms):
            continue
        if q:
            hay = " ".join(
                [
                    str(notice.title or ""),
                    str(notice.content or ""),
                    str(recipient.user_id or ""),
                    str(recipient.delivery_status or ""),
                ]
            ).lower()
            if q not in hay:
                continue
        items.append(
            {
                "id": int(recipient.id) + 10_000_000,
                "alert_id": alert_id,
                "rule_id": None,
                "receiver_type": "user",
                "receiver_id": recipient.user_id,
                "notify_type": "system",
                "status": status_code,
                "content": notice.content,
                "error_msg": None,
                "retry_times": recipient.delivery_attempts or 0,
                "sent_at": ms_to_rfc3339(sent_at_ms) if sent_at_ms else None,
                "created_at": recipient.created_at.isoformat() if recipient.created_at else None,
                "updated_at": notice.created_at.isoformat() if notice.created_at else None,
            }
        )
    return items
