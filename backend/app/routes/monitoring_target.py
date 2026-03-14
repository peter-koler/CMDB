from functools import wraps
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import re

from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    User,
    Monitor,
    MonitorParam,
    MonitorTemplate,
    CiInstance,
    SingleAlert,
    AlertHistory,
    AlertDefine,
    AlertGroup,
    AlertInhibit,
    AlertSilence,
    AlertIntegration,
    AlertNotification,
    NoticeReceiver,
    NoticeRule,
)
from app.notifications.models import Notification, NotificationRecipient
from app.notifications.websocket import socketio
from app.services.manager_api_service import ManagerError, manager_api_service


monitoring_target_bp = Blueprint("monitoring_target", __name__, url_prefix="/api/v1/monitoring")


def _auth_header() -> str:
    return request.headers.get("Authorization", "")


def _has_permission(permissions: set[str], target: str) -> bool:
    if "*" in permissions or target in permissions:
        return True
    for item in permissions:
        if item.endswith("*") and target.startswith(item[:-1]):
            return True
        if item.endswith(":*") and target.startswith(item[:-1]):
            return True
    return False


def require_any_permission(*required: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            user = User.query.get(int(identity)) if identity else None
            if not user:
                return jsonify({"code": 401, "message": "用户未登录"}), 401
            if user.is_admin:
                return fn(*args, **kwargs)

            permissions = set()
            for role_link in user.role_links:
                if role_link.role:
                    permissions.update(role_link.role.get_menu_permissions())

            allowed = any(_has_permission(permissions, permission) for permission in required)
            if not allowed:
                return jsonify({"code": 403, "message": "无权限访问"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _emit_alert_event(event: str, payload: dict):
    if socketio:
        socketio.emit(event, payload, namespace="/notifications")


def _manager_call(method: str, path: str, payload=None, params=None, fallback=None):
    try:
        data = manager_api_service.request(
            method=method,
            path=path,
            payload=payload,
            params=params,
            auth_header=_auth_header(),
        )
        return jsonify({"code": 200, "data": data})
    except ManagerError as e:
        current_app.logger.warning(
            "[MonitoringProxy] manager call failed method=%s path=%s status=%s code=%s message=%s",
            method,
            path,
            e.status,
            e.code,
            e.message,
        )
        # 监控扩展模块在 Manager 未实现(404)或暂时不可用(5xx)时返回空列表，避免前端页面硬失败。
        if fallback is not None and e.status in {404, 502, 503, 504}:
            current_app.logger.info(
                "[MonitoringProxy] fallback activated method=%s path=%s status=%s",
                method,
                path,
                e.status,
            )
            return jsonify({"code": 200, "data": fallback()})
        return jsonify({"code": e.status, "message": e.message, "error_code": e.code}), e.status


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
    # 缺省按健康处理，避免旧接口无状态字段时把全部实例算作异常。
    return True


def _fetch_manager_payload(path: str, params=None):
    try:
        return manager_api_service.request(
            method="GET",
            path=path,
            params=params,
            auth_header=_auth_header(),
        )
    except ManagerError as e:
        if e.status in {404, 502, 503, 504}:
            return {"items": [], "total": 0}
        raise


def _fetch_manager_payload_any(candidates: list[tuple[str, dict | None]]):
    for path, params in candidates:
        payload = _fetch_manager_payload(path, params=params)
        items = _normalize_items(payload)
        if items:
            return payload
    return {"items": [], "total": 0}


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


def _page_args() -> tuple[int, int]:
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20
    page = max(page, 1)
    page_size = max(min(page_size, 200), 1)
    return page, page_size


def _paginate_items(items: list[dict], page: int, page_size: int) -> tuple[list[dict], int]:
    total = len(items)
    start = (page - 1) * page_size
    if start >= total:
        return [], total
    return items[start : start + page_size], total


def _list_response(items: list[dict], total: int, page: int, page_size: int):
    return jsonify(
        {"code": 200, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}
    )


def _monitor_item_from_row(row: Monitor, params_by_monitor: dict[int, dict[str, str]] | None = None) -> dict:
    annotations = _json_load(row.annotations_json, {})
    if not isinstance(annotations, dict):
        annotations = {}
    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    if params_by_monitor is not None:
        params = params_by_monitor.get(row.id, {})
    else:
        params_rows = MonitorParam.query.filter_by(monitor_id=row.id).all()
        params = {str(p.field): str(p.param_value or "") for p in params_rows}
    enabled = int(row.status or 0) != 0
    return {
        "id": row.id,
        "job_id": str(row.job_id) if row.job_id is not None else None,
        "name": row.name,
        "app": row.app,
        "target": row.instance,
        "endpoint": row.instance,
        "interval_seconds": int(row.intervals or 0),
        "interval": int(row.intervals or 0),
        "enabled": enabled,
        "status": "enabled" if enabled else "disabled",
        "template_id": annotations.get("template_id"),
        "version": annotations.get("manager_version") or 1,
        "ci_id": annotations.get("ci_id"),
        "ci_model_id": annotations.get("ci_model_id"),
        "ci_name": annotations.get("ci_name"),
        "ci_code": annotations.get("ci_code"),
        "labels": labels,
        "params": params,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _load_monitors_from_db_fallback() -> dict:
    page, page_size = _page_args()
    q = (request.args.get("q") or "").strip().lower()
    status = (request.args.get("status") or "").strip().lower()
    rows = Monitor.query.order_by(Monitor.updated_at.desc(), Monitor.id.desc()).all()
    monitor_ids = [row.id for row in rows]
    params_by_monitor: dict[int, dict[str, str]] = {}
    if monitor_ids:
        params_rows = MonitorParam.query.filter(MonitorParam.monitor_id.in_(monitor_ids)).all()
        for item in params_rows:
            bucket = params_by_monitor.setdefault(int(item.monitor_id), {})
            bucket[str(item.field)] = str(item.param_value or "")
    items = [_monitor_item_from_row(row, params_by_monitor=params_by_monitor) for row in rows]

    if status in {"enabled", "disabled"}:
        want_enabled = status == "enabled"
        items = [item for item in items if bool(item.get("enabled")) == want_enabled]

    if q:
        def _match(item: dict) -> bool:
            hay = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("app") or ""),
                    str(item.get("target") or ""),
                    str(item.get("ci_code") or ""),
                    str(item.get("ci_name") or ""),
                    str(item.get("job_id") or ""),
                ]
            ).lower()
            return q in hay

        items = [item for item in items if _match(item)]

    page_items, total = _paginate_items(items, page, page_size)
    return {"items": page_items, "total": total, "page": page, "page_size": page_size}


def _set_target_enabled_fallback(monitor_id: int, enabled: bool) -> dict:
    row = Monitor.query.get(monitor_id)
    if not row:
        raise ValueError("监控任务不存在")
    row.status = 1 if enabled else 0
    row.modifier = "python-web"
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return _monitor_item_from_row(row)


def _get_target_from_db_fallback(monitor_id: int) -> dict:
    row = Monitor.query.get(monitor_id)
    if not row:
        return {"id": monitor_id, "fallback_error": "not_found"}
    return _monitor_item_from_row(row)


def _json_load(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _json_dump(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _coerce_label_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    return text


def _merge_ci_labels(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return payload
    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    merged = {str(k): _coerce_label_value(v) for k, v in labels.items() if str(k).strip()}

    ci_id = payload.get("ci_id")
    ci_code = payload.get("ci_code")
    ci_name = payload.get("ci_name")
    ci_row = None
    if ci_id not in (None, ""):
        try:
            ci_row = CiInstance.query.get(int(ci_id))
        except (TypeError, ValueError):
            ci_row = None
    if ci_row is None and ci_code not in (None, ""):
        ci_row = CiInstance.query.filter_by(code=str(ci_code).strip()).first()

    if ci_row:
        merged["ci.id"] = str(ci_row.id)
        merged["ci.code"] = str(ci_row.code or "")
        merged["ci.name"] = str(ci_row.name or "")
        attrs = ci_row.get_attribute_values()
        if isinstance(attrs, dict):
            for key, raw in attrs.items():
                attr_key = str(key or "").strip()
                if not attr_key:
                    continue
                value = _coerce_label_value(raw)
                if value == "":
                    continue
                merged[f"ci.{attr_key}"] = value
        payload["ci_id"] = ci_row.id
        payload["ci_code"] = ci_row.code
        payload["ci_name"] = ci_row.name
    else:
        ci_id_text = str(ci_id).strip() if ci_id not in (None, "") else ""
        ci_code_text = str(ci_code).strip() if ci_code not in (None, "") else ""
        ci_name_text = str(ci_name).strip() if ci_name not in (None, "") else ""
        if ci_id_text:
            merged["ci.id"] = ci_id_text
        if ci_code_text:
            merged["ci.code"] = ci_code_text
        if ci_name_text:
            merged["ci.name"] = ci_name_text
    payload["labels"] = merged
    return payload


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


def _extract_alert_item(
    *,
    row_id: int,
    labels_json: str | None,
    annotations_json: str | None,
    content: str | None,
    status: str,
    start_at: int | None,
    end_at: int | None,
    created_at: datetime | None,
) -> dict:
    labels = _json_load(labels_json, {})
    annotations = _json_load(annotations_json, {})
    rule_id = _extract_rule_id(labels, annotations)
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
    triggered_ms = start_at or (int(created_at.replace(tzinfo=timezone.utc).timestamp() * 1000) if created_at else None)
    recovered_ms = end_at
    duration_seconds = 0
    if triggered_ms:
        tail = recovered_ms or _now_ms()
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
    source_type, source_name = _normalize_source_value(source_value)
    if not source_type:
        if monitor_id:
            source_type = "local"
        else:
            source_type = "external"
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
        "triggered_at": _ms_to_rfc3339(triggered_ms),
        "recovered_at": _ms_to_rfc3339(recovered_ms),
        "duration_seconds": duration_seconds,
        "assignee": assignee,
        "note": note,
        "action": action,
        "escalation_level": escalation_level,
        "source_type": source_type,
        "source_name": source_name,
    }


def _extract_rule_id(labels: dict, annotations: dict) -> int | None:
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


def _normalize_source_value(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    raw = str(value).strip()
    if not raw:
        return None, None
    normalized = raw.lower()
    if normalized in {"local", "internal", "hertzbeat", "hb", "self"}:
        return "local", None
    return "external", raw


def _notification_from_model(row: AlertNotification) -> dict:
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
        "sent_at": _ms_to_rfc3339(row.sent_at),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _system_notify_status_code(delivery_status: str | None) -> int:
    state = str(delivery_status or "").strip().lower()
    # 站内消息创建成功即视为送达，notification_recipients 默认常为 pending。
    if state in {"", "pending"}:
        return 2
    if state in {"delivered", "success", "sent"}:
        return 2
    if state in {"failed", "permanent_failure"}:
        return 3
    if state in {"sending", "processing"}:
        return 1
    return 0


def _get_alert_context(alert_id: int) -> dict:
    row = SingleAlert.query.get(alert_id)
    if row:
        labels = _json_load(row.labels_json, {})
        return {
            "rule_name": str(labels.get("alertname") or "").strip(),
            "monitor_id": str(labels.get("monitor_id") or "").strip(),
        }
    history = AlertHistory.query.get(alert_id)
    if history:
        labels = _json_load(history.labels_json, {})
        return {
            "rule_name": str(labels.get("alertname") or "").strip(),
            "monitor_id": str(labels.get("monitor_id") or "").strip(),
        }
    return {"rule_name": "", "monitor_id": ""}


def _list_system_notifications_for_alert(alert_id: int) -> list[dict]:
    notify_type = (request.args.get("notify_type") or "").strip().lower()
    receiver_type = (request.args.get("receiver_type") or "").strip().lower()
    status = request.args.get("status")
    q = (request.args.get("q") or "").strip().lower()
    start_ms = _parse_rfc3339_to_ms(request.args.get("start_at"))
    end_ms = _parse_rfc3339_to_ms(request.args.get("end_at"))

    if notify_type and notify_type != "system":
        return []
    if receiver_type and receiver_type != "user":
        return []

    ctx = _get_alert_context(alert_id)
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
                "sent_at": _ms_to_rfc3339(sent_at_ms) if sent_at_ms else None,
                "created_at": recipient.created_at.isoformat() if recipient.created_at else None,
                "updated_at": notice.created_at.isoformat() if notice.created_at else None,
            }
        )
    return items


def _filter_alert_items(items: list[dict]) -> list[dict]:
    level = (request.args.get("level") or "").strip().lower()
    status = (request.args.get("status") or "").strip().lower()
    name = (request.args.get("name") or "").strip().lower()
    monitor_name = (request.args.get("monitor_name") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    monitor_id = (request.args.get("monitor_id") or "").strip()
    app = (request.args.get("app") or "").strip().lower()
    instance = (request.args.get("instance") or "").strip().lower()
    metric = (request.args.get("metric") or "").strip().lower()
    assignee = (request.args.get("assignee") or "").strip().lower()
    rule_id = (request.args.get("rule_id") or "").strip()
    start_ms = _parse_rfc3339_to_ms(request.args.get("start_at"))
    end_ms = _parse_rfc3339_to_ms(request.args.get("end_at"))
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
        if name:
            item_name = str(item.get("name") or "").strip().lower()
            if name not in item_name:
                continue
        if monitor_name:
            item_monitor_name = str(item.get("monitor_name") or "").strip().lower()
            if monitor_name not in item_monitor_name:
                continue
        if instance:
            item_instance = str(item.get("instance") or "").strip().lower()
            if instance not in item_instance:
                continue
        if metric:
            item_metric = str(item.get("metric") or "").strip().lower()
            if item_metric != metric:
                continue
        if rule_id:
            item_rule_id = str(item.get("rule_id") or "").strip()
            if item_rule_id != rule_id:
                continue
        if assignee:
            item_assignee = str(item.get("assignee") or "").strip().lower()
            if assignee not in item_assignee:
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
            ts = _parse_rfc3339_to_ms(item.get("triggered_at"))
            if start_ms and (not ts or ts < start_ms):
                continue
            if end_ms and (not ts or ts > end_ms):
                continue
        out.append(item)
    return out


def _rule_from_model(row: AlertDefine) -> dict:
    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    annotations = _json_load(row.annotations_json, {})
    if not isinstance(annotations, dict):
        annotations = {}
    threshold = labels.get("threshold")
    try:
        threshold = float(threshold) if threshold is not None else 0
    except (TypeError, ValueError):
        threshold = 0
    
    # 获取关联的通知规则信息
    notice_rule_info = None
    if row.notice_rule:
        notice_rule_info = {
            "id": row.notice_rule.id,
            "name": row.notice_rule.name,
            "receiver_name": row.notice_rule.receiver_name or (row.notice_rule.receiver.name if row.notice_rule.receiver else None),
            "receiver_type": row.notice_rule.receiver_type or (row.notice_rule.receiver.type if row.notice_rule.receiver else None),
        }
    
    notice_rule_ids = row.notice_rule_ids if hasattr(row, "notice_rule_ids") else []
    if not notice_rule_ids and row.notice_rule_id:
        notice_rule_ids = [row.notice_rule_id]
    auto_recover = _to_bool(labels.get("auto_recover"), True)
    recover_times = max(_to_int(labels.get("recover_times"), 2), 1)
    notify_on_recovered = _to_bool(labels.get("notify_on_recovered"), True)
    escalation_config = None
    raw_escalation = str(getattr(row, "escalation_config", "") or "").strip()
    if raw_escalation:
        try:
            escalation_config = json.loads(raw_escalation)
        except (TypeError, ValueError):
            escalation_config = None
    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "monitor_type": row.type,
        "expr": row.expr,
        "period": row.period,
        "times": row.times,
        "metric": labels.get("metric") or annotations.get("metric") or "value",
        "operator": labels.get("operator") or ">",
        "threshold": threshold,
        "level": labels.get("severity") or "warning",
        "labels": labels,
        "annotations": annotations,
        "title_template": annotations.get("title_template"),
        "template": row.template,
        "datasource_type": row.datasource_type,
        "enabled": bool(row.enabled),
        "notice_rule_id": row.notice_rule_id,
        "notice_rule_ids": notice_rule_ids,
        "notice_rule": notice_rule_info,
        "auto_recover": auto_recover,
        "recover_times": recover_times,
        "notify_on_recovered": notify_on_recovered,
        "escalation_config": escalation_config,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _monitor_payload(monitor_id: int) -> dict:
    try:
        payload = _fetch_manager_payload(f"/api/v1/monitors/{monitor_id}")
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _rule_match_monitor(row: AlertDefine, monitor: dict) -> bool:
    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    monitor_id = str(monitor.get("id") or "").strip()
    app = str(monitor.get("app") or "").strip().lower()
    target = str(monitor.get("target") or "").strip().lower()

    want_monitor_id = str(labels.get("monitor_id") or "").strip()
    if want_monitor_id and want_monitor_id != monitor_id:
        return False
    want_app = str(labels.get("app") or "").strip().lower()
    if want_app and app and want_app != app:
        return False
    want_instance = str(labels.get("instance") or "").strip().lower()
    if want_instance and target and want_instance != target:
        return False
    return True


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


def _validate_notice_rule_ids(ids: list[int]) -> str | None:
    if not ids:
        return None
    existing = NoticeRule.query.filter(NoticeRule.id.in_(ids)).all()
    if len(existing) != len(set(ids)):
        return "指定的通知规则不存在"
    return None


def _rule_scope(row: AlertDefine, monitor_id: int) -> str:
    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    want_monitor_id = str(labels.get("monitor_id") or "").strip()
    if want_monitor_id == str(monitor_id):
        return "target"
    return "global"


def _redis_default_alert_rules() -> list[dict]:
    # Core-first defaults for commercial usability.
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


def _normalize_template_alert_rule(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    if not name:
        return None

    kind = str(item.get("type") or item.get("monitor_type") or "").strip().lower()
    schedule = str(item.get("schedule") or "").strip().lower()
    if not kind:
        if schedule in {"periodic", "period"}:
            kind = "periodic_metric"
        else:
            kind = "realtime_metric"
    elif kind in {"realtime", "periodic"}:
        kind = f"{kind}_metric"
    if kind not in {"realtime_metric", "periodic_metric"}:
        kind = "realtime_metric"

    metric = str(item.get("metric") or "value").strip() or "value"
    operator = str(item.get("operator") or ">").strip() or ">"
    threshold = _to_float(item.get("threshold"), 0)
    level = str(item.get("level") or item.get("severity") or "warning").strip() or "warning"
    period = max(_to_int(item.get("period"), 300 if kind == "periodic_metric" else 60), 0)
    times = max(_to_int(item.get("times"), 1), 1)
    mode = str(item.get("mode") or "").strip().lower()
    enabled = _to_bool(
        item.get("enabled") if item.get("enabled") is not None else item.get("default_enabled"),
        default=(mode == "core"),
    )
    expr = str(item.get("expr") or "").strip()
    if not expr:
        expr = f"{metric} {operator} {threshold}"
    template_text = str(item.get("template") or name).strip() or name
    notice_rule_ids = None
    if isinstance(item, dict):
        parsed_ids, _ = _extract_notice_rule_ids(item)
        if parsed_ids is not None:
            notice_rule_ids = parsed_ids
    notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
    recovery_labels: dict = {}
    _apply_recovery_config_to_labels(recovery_labels, item)
    return {
        "name": name,
        "type": kind,
        "metric": metric,
        "operator": operator,
        "threshold": threshold,
        "level": level,
        "period": period,
        "times": times,
        "expr": expr,
        "enabled": enabled,
        "template": template_text,
        "notice_rule_id": notice_rule_id,
        "notice_rule_ids": notice_rule_ids or [],
        "auto_recover": bool(recovery_labels.get("auto_recover", True)),
        "recover_times": max(_to_int(recovery_labels.get("recover_times"), 2), 1),
        "notify_on_recovered": bool(recovery_labels.get("notify_on_recovered", True)),
    }


def _template_default_alert_rules(template_content: str) -> list[dict]:
    raw_items = _extract_yaml_list_section(template_content, "alerts")
    out: list[dict] = []
    for item in raw_items:
        normalized = _normalize_template_alert_rule(item)
        if normalized:
            out.append(normalized)
    return out


def _load_monitor_default_alert_rules(monitor: dict) -> list[dict]:
    template = None
    template_id = monitor.get("template_id")
    if template_id is not None:
        try:
            template = MonitorTemplate.query.get(int(template_id))
        except (TypeError, ValueError):
            template = None
    if template is None:
        app = str(monitor.get("app") or "").strip().lower()
        if app:
            template = MonitorTemplate.query.filter_by(app=app).first()

    if template and template.content:
        rules = _template_default_alert_rules(template.content)
        if rules:
            return rules

    app = str(monitor.get("app") or "").strip().lower()
    if app == "redis":
        return _redis_default_alert_rules()
    return []


def _apply_default_rules_for_monitor(monitor_id: int, monitor: dict | None = None) -> dict:
    monitor = monitor or _monitor_payload(monitor_id)
    if not monitor:
        raise ValueError("监控任务不存在")

    app = str(monitor.get("app") or "").strip().lower()
    defaults = _load_monitor_default_alert_rules(monitor)
    if not defaults:
        raise ValueError("当前模板未配置默认告警策略")
    monitor_target = str(monitor.get("target") or "")
    existing_rows = AlertDefine.query.order_by(AlertDefine.id.asc()).all()
    existing_map: dict[str, AlertDefine] = {}
    for row in existing_rows:
        labels = _json_load(row.labels_json, {})
        if not isinstance(labels, dict):
            continue
        if str(labels.get("monitor_id") or "").strip() != str(monitor_id):
            continue
        existing_map[row.name] = row

    created = 0
    updated = 0
    for item in defaults:
        notice_rule_ids = item.get("notice_rule_ids") if isinstance(item.get("notice_rule_ids"), list) else []
        notice_rule_ids = [int(v) for v in notice_rule_ids if isinstance(v, int) or str(v).strip().isdigit()]
        notice_rule_ids = [v for v in notice_rule_ids if v > 0]
        # 兼容旧字段，仅配置了 notice_rule_id 时自动补全数组
        raw_notice_rule_id = item.get("notice_rule_id")
        if not notice_rule_ids and raw_notice_rule_id is not None:
            try:
                parsed_notice_rule_id = int(raw_notice_rule_id)
                if parsed_notice_rule_id > 0:
                    notice_rule_ids = [parsed_notice_rule_id]
            except (TypeError, ValueError):
                notice_rule_ids = []
        notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
        escalation_config_raw = ""
        if "escalation_config" in item:
            escalation_config_raw, _ = _normalize_escalation_config(item.get("escalation_config"))
            escalation_config_raw = escalation_config_raw or ""

        labels = {
            "monitor_id": monitor_id,
            "app": app,
            "instance": monitor_target,
            "metric": item["metric"],
            "operator": item["operator"],
            "threshold": item["threshold"],
            "severity": item["level"],
            "source": "template_default",
        }
        _apply_recovery_config_to_labels(labels, item)
        annotations = {
            "summary": item["name"],
            "template": item["template"],
            "app": app,
        }
        row = existing_map.get(item["name"])
        if row is None:
            row = AlertDefine(
                name=item["name"],
                type=item["type"],
                expr=item["expr"],
                period=item["period"],
                times=item["times"],
                labels_json=_json_dump(labels),
                annotations_json=_json_dump(annotations),
                template=item["template"],
                enabled=bool(item["enabled"]),
                notice_rule_id=notice_rule_id,
                notice_rule_ids_json=_json_dump(notice_rule_ids),
                escalation_config=escalation_config_raw,
                creator="python-web",
                modifier="python-web",
            )
            db.session.add(row)
            created += 1
        else:
            row.type = item["type"]
            row.expr = item["expr"]
            row.period = item["period"]
            row.times = item["times"]
            row.labels_json = _json_dump(labels)
            row.annotations_json = _json_dump(annotations)
            row.template = item["template"]
            row.enabled = bool(item["enabled"])
            row.notice_rule_id = notice_rule_id
            row.notice_rule_ids_json = _json_dump(notice_rule_ids)
            row.escalation_config = escalation_config_raw
            row.modifier = "python-web"
            row.updated_at = _now_naive_utc()
            updated += 1
    db.session.commit()
    return {
        "monitor_id": monitor_id,
        "app": app,
        "created": created,
        "updated": updated,
        "total": created + updated,
    }


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


def _receiver_from_model(row: NoticeReceiver) -> dict:
    channel_type = _receiver_channel_name(row.type)
    endpoint = row.hook_url or row.email or row.phone or row.wechat_id or ""
    return {
        "id": row.id,
        "name": row.name,
        "type": channel_type,
        "endpoint": endpoint,
        "status": "enabled",
    }


def _notice_rule_from_model(row: NoticeRule) -> dict:
    """将通知规则模型转换为字典"""
    # 获取关联的渠道信息
    receiver = row.receiver
    receiver_type = row.receiver_type or (receiver.type if receiver else None)
    receiver_name = row.receiver_name or (receiver.name if receiver else None)
    
    return {
        "id": row.id,
        "name": row.name,
        "receiver_channel_id": row.receiver_channel_id,
        "receiver_id": row.receiver_channel_id,  # 兼容前端字段名
        "receiver_type": receiver_type,
        "receiver_name": receiver_name,
        "notify_times": row.notify_times,
        "notify_scale": row.notify_scale,
        "template_id": row.template_id,
        "template_name": row.template_name,
        "filter_all": row.filter_all,
        "labels": row.labels,
        "days": row.days,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "recipient_type": row.recipient_type,
        "recipient_ids": row.recipient_ids,
        "include_sub_departments": bool(row.include_sub_departments),
        "status": "enabled" if row.enable else "disabled",
        "enable": bool(row.enable),
    }


@monitoring_target_bp.route("/targets", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target", "monitoring:list")
def list_targets():
    return _manager_call(
        "GET",
        "/api/v1/monitors",
        params=request.args.to_dict(),
        fallback=_load_monitors_from_db_fallback
    )


@monitoring_target_bp.route("/targets", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:target:create", "monitoring:list:create")
def create_target():
    payload = request.get_json() or {}
    apply_default_alerts = bool(payload.pop("apply_default_alerts", False))
    payload = _merge_ci_labels(payload)

    # 前端兼容字段：interval -> interval_seconds
    if "interval_seconds" not in payload and "interval" in payload:
        payload["interval_seconds"] = payload.get("interval")
    try:
        interval_seconds = int(payload.get("interval_seconds") or 0)
    except (TypeError, ValueError):
        interval_seconds = 0
    if interval_seconds < 10:
        return jsonify({"code": 400, "message": "采集间隔最小为10秒"}), 400
    payload["interval_seconds"] = interval_seconds

    # 目标地址默认由参数中的 host/port 构造，回退到 CI 标识
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    host = str(params.get("host") or "").strip()
    port = str(params.get("port") or "").strip()
    if not payload.get("target"):
        if host:
            payload["target"] = f"{host}:{port or '6379'}"
        elif payload.get("ci_code"):
            payload["target"] = f"ci:{payload.get('ci_code')}"
        elif payload.get("ci_id"):
            payload["target"] = f"ci:{payload.get('ci_id')}"

    response = _manager_call("POST", "/api/v1/monitors", payload=payload)
    if not apply_default_alerts:
        return response

    status_code = getattr(response, "status_code", 200)
    if status_code >= 300:
        return response

    body = response.get_json(silent=True) or {}
    data = body.get("data") if isinstance(body, dict) else None
    monitor_id = 0
    if isinstance(data, dict):
        try:
            monitor_id = int(data.get("id") or data.get("monitor_id") or 0)
        except (TypeError, ValueError):
            monitor_id = 0

    if monitor_id <= 0:
        return response

    try:
        apply_result = _apply_default_rules_for_monitor(monitor_id)
        if isinstance(data, dict):
            data["alert_defaults"] = {
                "applied": True,
                **apply_result,
            }
            body["data"] = data
            return jsonify(body)
    except Exception as exc:
        if isinstance(data, dict):
            data["alert_defaults"] = {
                "applied": False,
                "reason": str(exc),
            }
            body["data"] = data
            return jsonify(body)
    return response


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def get_target(monitor_id: int):
    response = _manager_call(
        "GET",
        f"/api/v1/monitors/{monitor_id}",
        fallback=lambda: _get_target_from_db_fallback(monitor_id),
    )
    status_code = getattr(response, "status_code", 200)
    if status_code == 200:
        body = response.get_json(silent=True) or {}
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and data.get("fallback_error") == "not_found":
            return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    return response


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:edit")
def update_target(monitor_id: int):
    payload = _merge_ci_labels(request.get_json() or {})
    return _manager_call("PUT", f"/api/v1/monitors/{monitor_id}", payload=payload)


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:target:delete", "monitoring:list:delete")
def delete_target(monitor_id: int):
    return _manager_call("DELETE", f"/api/v1/monitors/{monitor_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/targets/<int:monitor_id>/enable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:enable")
def enable_target(monitor_id: int):
    def _fallback():
        try:
            return _set_target_enabled_fallback(monitor_id, True)
        except ValueError:
            return {"id": monitor_id, "enabled": True, "fallback_error": "not_found"}

    response = _manager_call(
        "PATCH",
        f"/api/v1/monitors/{monitor_id}/enable",
        payload=request.get_json() or {},
        fallback=_fallback,
    )
    status_code = getattr(response, "status_code", 200)
    if status_code == 200:
        body = response.get_json(silent=True) or {}
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and data.get("fallback_error") == "not_found":
            return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    return response


@monitoring_target_bp.route("/targets/<int:monitor_id>/disable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:disable")
def disable_target(monitor_id: int):
    def _fallback():
        try:
            return _set_target_enabled_fallback(monitor_id, False)
        except ValueError:
            return {"id": monitor_id, "enabled": False, "fallback_error": "not_found"}

    response = _manager_call(
        "PATCH",
        f"/api/v1/monitors/{monitor_id}/disable",
        payload=request.get_json() or {},
        fallback=_fallback,
    )
    status_code = getattr(response, "status_code", 200)
    if status_code == 200:
        body = response.get_json(silent=True) or {}
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and data.get("fallback_error") == "not_found":
            return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    return response


@monitoring_target_bp.route("/targets/<int:monitor_id>/collector", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:target:assign", "monitoring:target:update")
def assign_collector_to_target(monitor_id: int):
    """为监控任务指定 Collector（固定分配）"""
    data = request.get_json() or {}
    return _manager_call(
        "POST",
        f"/api/v1/monitors/{monitor_id}/collector",
        payload=data,
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/collector", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:target:assign", "monitoring:target:update")
def unassign_collector_from_target(monitor_id: int):
    """取消监控任务的 Collector 固定分配，改为自动分配"""
    return _manager_call("DELETE", f"/api/v1/monitors/{monitor_id}/collector")


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics/series", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def get_target_metric_series(monitor_id: int):
    params = request.args.to_dict()
    params["monitor_id"] = monitor_id
    return _manager_call(
        "GET",
        "/api/v1/metrics/series",
        params=params,
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics/query-range", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def query_target_metric_range(monitor_id: int):
    params = request.args.to_dict()
    params["monitor_id"] = monitor_id
    return _manager_call(
        "GET",
        "/api/v1/metrics/query-range",
        params=params,
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics/latest", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def get_target_metric_latest(monitor_id: int):
    params = request.args.to_dict()
    params["monitor_id"] = monitor_id
    return _manager_call(
        "GET",
        "/api/v1/metrics/latest",
        params=params,
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics/export", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def export_target_metric_range(monitor_id: int):
    params = request.args.to_dict()
    params["monitor_id"] = monitor_id
    try:
        status, headers, raw = manager_api_service.request_raw(
            method="GET",
            path="/api/v1/metrics/export",
            params=params,
            auth_header=_auth_header(),
        )
        resp = make_response(raw, status)
        resp.headers["Content-Type"] = headers.get("Content-Type", "text/csv; charset=utf-8")
        if headers.get("Content-Disposition"):
            resp.headers["Content-Disposition"] = headers["Content-Disposition"]
        return resp
    except ManagerError as e:
        return jsonify({"code": e.status, "message": e.message, "error_code": e.code}), e.status


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics-view", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def get_target_metrics_view(monitor_id: int):
    return _manager_call(
        "GET",
        f"/api/v1/monitors/{monitor_id}/metrics-view",
        fallback=lambda: {"monitor_id": monitor_id, "visible_fields_by_group": {}},
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/metrics-view", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:edit")
def save_target_metrics_view(monitor_id: int):
    payload = request.get_json() or {}
    return _manager_call(
        "PUT",
        f"/api/v1/monitors/{monitor_id}/metrics-view",
        payload=payload,
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/rules", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:view", "monitoring:list:view")
def list_target_alert_rules(monitor_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    rows = AlertDefine.query.order_by(AlertDefine.updated_at.desc(), AlertDefine.id.desc()).all()
    items = []
    for row in rows:
        if not _rule_match_monitor(row, monitor):
            continue
        item = _rule_from_model(row)
        item["scope"] = _rule_scope(row, monitor_id)
        items.append(item)
    page, page_size = _page_args()
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/rules", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def create_target_alert_rule(monitor_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    payload = request.get_json() or {}

    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "规则名称不能为空"}), 400

    metric = str(payload.get("metric") or "value").strip() or "value"
    operator = str(payload.get("operator") or ">").strip() or ">"
    level = str(payload.get("level") or "warning").strip() or "warning"
    rule_type = str(payload.get("type") or payload.get("monitor_type") or "realtime_metric").strip() or "realtime_metric"
    period = 0
    times = 1
    threshold_val = 0.0
    try:
        threshold_val = float(payload.get("threshold", 0))
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "threshold 必须是数字"}), 400
    try:
        period = max(int(payload.get("period") or 0), 0)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "period 必须是整数"}), 400
    try:
        times = max(int(payload.get("times") or 1), 1)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "times 必须是整数"}), 400

    notice_rule_ids, err = _extract_notice_rule_ids(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400
    if notice_rule_ids is not None:
        validate_msg = _validate_notice_rule_ids(notice_rule_ids)
        if validate_msg:
            return jsonify({"code": 400, "message": validate_msg}), 400
    notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
    escalation_config_raw, escalation_err = _normalize_escalation_config(payload.get("escalation_config"))
    if escalation_err:
        return jsonify({"code": 400, "message": escalation_err}), 400

    labels = {
        "monitor_id": monitor_id,
        "app": monitor.get("app"),
        "instance": monitor.get("target"),
        "metric": metric,
        "operator": operator,
        "threshold": threshold_val,
        "severity": level,
    }
    _apply_recovery_config_to_labels(labels, payload)
    custom_labels = payload.get("labels")
    if isinstance(custom_labels, dict):
        for key, value in custom_labels.items():
            label_key = str(key or "").strip()
            if not label_key:
                continue
            if label_key in {"monitor_id", "app", "instance", "metric", "operator", "threshold", "severity"}:
                continue
            labels[label_key] = str(value or "").strip()
    _apply_recovery_config_to_labels(labels, payload)
    annotations = {"summary": name}
    if isinstance(payload.get("annotations"), dict):
        for key, value in payload.get("annotations").items():
            ann_key = str(key or "").strip()
            if ann_key:
                annotations[ann_key] = value
    title_template = str(payload.get("title_template") or "").strip()
    if title_template:
        annotations["title_template"] = title_template
    expr = str(payload.get("expr") or "").strip() or f"{metric} {operator} {threshold_val}"

    row = AlertDefine(
        name=name,
        type=rule_type,
        expr=expr,
        period=period,
        times=times,
        labels_json=_json_dump(labels),
        annotations_json=_json_dump(annotations),
        template=str(payload.get("template") or "").strip() or None,
        datasource_type=payload.get("datasource_type"),
        enabled=bool(payload.get("enabled", True)),
        notice_rule_id=notice_rule_id,
        notice_rule_ids_json=_json_dump(notice_rule_ids or []),
        escalation_config=escalation_config_raw or "",
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    db.session.commit()
    item = _rule_from_model(row)
    item["scope"] = "target"
    return jsonify({"code": 200, "data": item})


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/rules/<int:rule_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def update_target_alert_rule(monitor_id: int, rule_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    payload = request.get_json() or {}

    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "type" in payload:
        row.type = str(payload.get("type") or row.type).strip() or row.type
    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    if "period" in payload:
        try:
            row.period = max(int(payload.get("period") or 0), 0)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "period 必须是整数"}), 400
    if "times" in payload:
        try:
            row.times = max(int(payload.get("times") or 1), 1)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "times 必须是整数"}), 400
    if "template" in payload:
        row.template = str(payload.get("template") or "").strip() or None

    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    labels["monitor_id"] = monitor_id
    labels["app"] = monitor.get("app")
    labels["instance"] = monitor.get("target")
    if "metric" in payload:
        labels["metric"] = str(payload.get("metric") or "value").strip() or "value"
    if "operator" in payload:
        labels["operator"] = str(payload.get("operator") or ">").strip() or ">"
    if "threshold" in payload:
        try:
            labels["threshold"] = float(payload.get("threshold"))
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "threshold 必须是数字"}), 400
    if "level" in payload:
        labels["severity"] = str(payload.get("level") or "warning").strip() or "warning"
    if "labels" in payload and isinstance(payload.get("labels"), dict):
        for key, value in payload.get("labels").items():
            label_key = str(key or "").strip()
            if not label_key:
                continue
            if label_key in {"monitor_id", "app", "instance", "metric", "operator", "threshold", "severity"}:
                continue
            labels[label_key] = str(value or "").strip()
    _apply_recovery_config_to_labels(labels, payload)
    row.labels_json = _json_dump(labels)
    annotations = _json_load(row.annotations_json, {})
    if not isinstance(annotations, dict):
        annotations = {}
    if "annotations" in payload and isinstance(payload.get("annotations"), dict):
        for key, value in payload.get("annotations").items():
            ann_key = str(key or "").strip()
            if ann_key:
                annotations[ann_key] = value
    if "title_template" in payload:
        title_template = str(payload.get("title_template") or "").strip()
        if title_template:
            annotations["title_template"] = title_template
        else:
            annotations.pop("title_template", None)
    row.annotations_json = _json_dump(annotations)

    if "expr" in payload:
        row.expr = str(payload.get("expr") or "").strip() or row.expr
    else:
        metric = labels.get("metric") or "value"
        operator = labels.get("operator") or ">"
        threshold = labels.get("threshold", 0)
        row.expr = f"{metric} {operator} {threshold}"

    notice_rule_ids, err = _extract_notice_rule_ids(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400
    if notice_rule_ids is not None:
        validate_msg = _validate_notice_rule_ids(notice_rule_ids)
        if validate_msg:
            return jsonify({"code": 400, "message": validate_msg}), 400
        row.notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
        row.notice_rule_ids_json = _json_dump(notice_rule_ids or [])
    if "escalation_config" in payload:
        escalation_config_raw, escalation_err = _normalize_escalation_config(payload.get("escalation_config"))
        if escalation_err:
            return jsonify({"code": 400, "message": escalation_err}), 400
        row.escalation_config = escalation_config_raw or ""

    row.updated_at = _now_naive_utc()
    db.session.commit()
    item = _rule_from_model(row)
    item["scope"] = "target"
    return jsonify({"code": 200, "data": item})


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/rules/<int:rule_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def delete_target_alert_rule(monitor_id: int, rule_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    if not _rule_match_monitor(row, monitor):
        return jsonify({"code": 403, "message": "规则不属于该监控实例"}), 403
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True, "id": rule_id}})


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/rules/apply-defaults", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def apply_target_default_alert_rules(monitor_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    try:
        result = _apply_default_rules_for_monitor(monitor_id, monitor)
    except ValueError as exc:
        return jsonify({"code": 400, "message": str(exc)}), 400
    return jsonify({"code": 200, "data": result})


@monitoring_target_bp.route("/templates/<int:template_id>/alerts/apply", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def apply_template_alert_rules(template_id: int):
    template = MonitorTemplate.query.get(template_id)
    if not template:
        return jsonify({"code": 404, "message": "模板不存在"}), 404

    payload = request.get_json() or {}
    monitor_ids_raw = payload.get("monitor_ids")
    monitor_ids: list[int] = []
    if isinstance(monitor_ids_raw, list):
        for item in monitor_ids_raw:
            try:
                monitor_id = int(item)
            except (TypeError, ValueError):
                continue
            if monitor_id > 0 and monitor_id not in monitor_ids:
                monitor_ids.append(monitor_id)

    if not monitor_ids:
        single_monitor_id = payload.get("monitor_id")
        try:
            if single_monitor_id is not None:
                parsed_single_id = int(single_monitor_id)
                if parsed_single_id > 0:
                    monitor_ids.append(parsed_single_id)
        except (TypeError, ValueError):
            pass

    if not monitor_ids:
        monitor_payload = _fetch_manager_payload("/api/v1/monitors", params={"page": 1, "page_size": 10000})
        for item in _normalize_items(monitor_payload):
            try:
                monitor_id = int(item.get("id") or 0)
            except (TypeError, ValueError):
                continue
            if monitor_id <= 0:
                continue
            monitor_template_id = item.get("template_id")
            if monitor_template_id is not None:
                try:
                    if int(monitor_template_id) == template_id:
                        monitor_ids.append(monitor_id)
                except (TypeError, ValueError):
                    continue
            else:
                app = str(item.get("app") or "").strip().lower()
                if app and app == str(template.app or "").strip().lower():
                    monitor_ids.append(monitor_id)

    if not monitor_ids:
        return jsonify(
            {
                "code": 200,
                "data": {
                    "template_id": template_id,
                    "template_app": template.app,
                    "monitor_total": 0,
                    "created": 0,
                    "updated": 0,
                    "applied": 0,
                    "failed": [],
                },
            }
        )

    created = 0
    updated = 0
    applied = 0
    failed: list[dict] = []
    expected_app = str(template.app or "").strip().lower()
    for monitor_id in monitor_ids:
        monitor = _monitor_payload(monitor_id)
        if not monitor:
            failed.append({"monitor_id": monitor_id, "reason": "监控任务不存在"})
            continue

        monitor_template_id = monitor.get("template_id")
        if monitor_template_id is not None:
            try:
                if int(monitor_template_id) != template_id:
                    failed.append({"monitor_id": monitor_id, "reason": "监控任务与模板不匹配"})
                    continue
            except (TypeError, ValueError):
                failed.append({"monitor_id": monitor_id, "reason": "监控任务模板ID非法"})
                continue

        app = str(monitor.get("app") or "").strip().lower()
        if expected_app and app and app != expected_app:
            failed.append({"monitor_id": monitor_id, "reason": "监控任务应用类型与模板不匹配"})
            continue

        try:
            result = _apply_default_rules_for_monitor(monitor_id, monitor)
        except Exception as exc:
            failed.append({"monitor_id": monitor_id, "reason": str(exc)})
            continue

        created += int(result.get("created") or 0)
        updated += int(result.get("updated") or 0)
        applied += 1

    return jsonify(
        {
            "code": 200,
            "data": {
                "template_id": template_id,
                "template_app": template.app,
                "monitor_total": len(monitor_ids),
                "created": created,
                "updated": updated,
                "applied": applied,
                "failed": failed,
            },
        }
    )


@monitoring_target_bp.route("/targets/<int:monitor_id>/alerts/reload", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting", "monitoring:target:update", "monitoring:list:edit")
def reload_target_alert_rules(monitor_id: int):
    monitor = _monitor_payload(monitor_id)
    if not monitor:
        return jsonify({"code": 404, "message": "监控任务不存在"}), 404
    return jsonify(
        {
            "code": 200,
            "data": {
                "monitor_id": monitor_id,
                "reloaded": True,
                "strategy": "manager-auto-reload-60s",
                "reloaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }
    )


@monitoring_target_bp.route("/alerts", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert", "monitoring:alert:current", "monitoring:alert:my")
def list_alerts():
    scope = (request.args.get("scope") or "current").strip().lower()
    if scope == "history":
        return list_history_alerts()
    return list_current_alerts()


@monitoring_target_bp.route("/alerts/current", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:center")
def list_current_alerts():
    status = (request.args.get("status") or "").strip().lower()
    query = SingleAlert.query
    if status == "closed":
        query = query.filter_by(status="resolved")
    elif status in {"", "open"}:
        query = query.filter_by(status="firing")
    rows = query.order_by(SingleAlert.updated_at.desc(), SingleAlert.id.desc()).all()
    items = [
        _extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
        )
        for row in rows
    ]
    items = _filter_alert_items(items)
    page, page_size = _page_args()
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/history", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:history", "monitoring:alert:center")
def list_history_alerts():
    rows = AlertHistory.query.order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc()).all()
    items = [
        _extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
        )
        for row in rows
    ]
    items = _filter_alert_items(items)
    page, page_size = _page_args()
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/<int:alert_id>", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:history", "monitoring:alert:center")
def get_alert_detail(alert_id: int):
    row = SingleAlert.query.get(alert_id)
    if row:
        labels = _json_load(row.labels_json, {})
        annotations = _json_load(row.annotations_json, {})
        item = _extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
        )
        item["rule_id"] = _extract_rule_id(labels, annotations)
        item["scope"] = "current"
        return jsonify({"code": 200, "data": item})

    history = AlertHistory.query.get(alert_id)
    if history:
        labels = _json_load(history.labels_json, {})
        annotations = _json_load(history.annotations_json, {})
        item = _extract_alert_item(
            row_id=history.id,
            labels_json=history.labels_json,
            annotations_json=history.annotations_json,
            content=history.content,
            status=history.status,
            start_at=history.start_at,
            end_at=history.end_at,
            created_at=history.created_at,
        )
        item["rule_id"] = _extract_rule_id(labels, annotations)
        item["scope"] = "history"
        return jsonify({"code": 200, "data": item})

    return jsonify({"code": 404, "message": "告警不存在"}), 404


@monitoring_target_bp.route("/alerts/<int:alert_id>/notifications", methods=["GET"])
@jwt_required()
@require_any_permission(
    "monitoring:alert:current",
    "monitoring:alert:my",
    "monitoring:alert:history",
    "monitoring:alert:center",
    "monitoring:alert:notice",
    "monitoring:alert:notice:view",
)
def list_alert_notifications(alert_id: int):
    query = AlertNotification.query.filter_by(alert_id=alert_id)
    notify_type = (request.args.get("notify_type") or "").strip().lower()
    receiver_type = (request.args.get("receiver_type") or "").strip().lower()
    status = request.args.get("status")
    q = (request.args.get("q") or "").strip().lower()
    start_ms = _parse_rfc3339_to_ms(request.args.get("start_at"))
    end_ms = _parse_rfc3339_to_ms(request.args.get("end_at"))
    if notify_type:
        query = query.filter(AlertNotification.notify_type == notify_type)
    if receiver_type:
        query = query.filter(AlertNotification.receiver_type == receiver_type)
    if status is not None and str(status).strip() != "":
        try:
            status_val = int(status)
            query = query.filter(AlertNotification.status == status_val)
        except (TypeError, ValueError):
            pass
    if start_ms or end_ms:
        query = query.filter(AlertNotification.sent_at.isnot(None))
        if start_ms:
            query = query.filter(AlertNotification.sent_at >= start_ms)
        if end_ms:
            query = query.filter(AlertNotification.sent_at <= end_ms)

    rows = query.order_by(
        AlertNotification.sent_at.is_(None),
        AlertNotification.sent_at.desc(),
        AlertNotification.id.desc(),
    ).all()
    items = []
    if q:
        for row in rows:
            hay = " ".join(
                [
                    str(row.notify_type or ""),
                    str(row.receiver_type or ""),
                    str(row.receiver_id or ""),
                    str(row.content or ""),
                    str(row.error_msg or ""),
                ]
            ).lower()
            if q in hay:
                items.append(_notification_from_model(row))
    else:
        items = [_notification_from_model(row) for row in rows]
    page, page_size = _page_args()
    if not items:
        items = _list_system_notifications_for_alert(alert_id)
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/<int:alert_id>/rule", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:history", "monitoring:alert:center")
def get_alert_rule(alert_id: int):
    row = SingleAlert.query.get(alert_id)
    scope = "current"
    if not row:
        row = AlertHistory.query.get(alert_id)
        scope = "history"
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404

    labels = _json_load(row.labels_json, {})
    annotations = _json_load(row.annotations_json, {})
    rule_id = _extract_rule_id(labels, annotations)
    alert_metric = str(labels.get("metric") or annotations.get("metric") or "").strip()
    monitor_id = None
    try:
        monitor_id = int(labels.get("monitor_id")) if labels.get("monitor_id") is not None else None
    except (TypeError, ValueError):
        monitor_id = None

    matched_by = None
    rule = None

    if rule_id:
        rule = AlertDefine.query.get(rule_id)
        matched_by = "rule_id"

    if not rule:
        notice_row = (
            AlertNotification.query.filter(
                AlertNotification.alert_id == alert_id,
                AlertNotification.rule_id.isnot(None),
            )
            .order_by(
                AlertNotification.sent_at.is_(None),
                AlertNotification.sent_at.desc(),
                AlertNotification.id.desc(),
            )
            .first()
        )
        if notice_row and notice_row.rule_id:
            rule = AlertDefine.query.get(int(notice_row.rule_id))
            matched_by = "notification_rule"

    if not rule and monitor_id:
        monitor = _monitor_payload(monitor_id)
        for row_rule in AlertDefine.query.order_by(AlertDefine.updated_at.desc(), AlertDefine.id.desc()).all():
            if not _rule_match_monitor(row_rule, monitor):
                continue
            rule_labels = _json_load(row_rule.labels_json, {})
            rule_annotations = _json_load(row_rule.annotations_json, {})
            rule_metric = str(rule_labels.get("metric") or rule_annotations.get("metric") or "").strip()
            if alert_metric and rule_metric and alert_metric != rule_metric:
                continue
            rule = row_rule
            matched_by = "heuristic"
            break

    if not rule:
        return jsonify({"code": 404, "message": "未找到匹配的告警规则"}), 404

    payload = _rule_from_model(rule)
    payload["matched_by"] = matched_by
    payload["alert_scope"] = scope
    return jsonify({"code": 200, "data": payload})


@monitoring_target_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:update", "monitoring:alert:center", "monitoring:alert:current", "monitoring:alert:my")
def acknowledge_alert(alert_id: int):
    payload = request.get_json() or {}
    row = SingleAlert.query.get(alert_id)
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    labels = _json_load(row.labels_json, {})
    annotations = _json_load(row.annotations_json, {})
    identity = get_jwt_identity()
    current_user = User.query.get(int(identity)) if identity else None
    assignee = str(payload.get("assignee") or (current_user.username if current_user else "system"))
    labels["assignee"] = assignee
    note = payload.get("note")
    if note:
        annotations["note"] = str(note)
    row.labels_json = _json_dump(labels)
    row.annotations_json = _json_dump(annotations)
    row.modifier = assignee
    row.updated_at = _now_naive_utc()
    db.session.commit()
    response = jsonify(
        {
            "code": 200,
            "data": _extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
            ),
        }
    )
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "acknowledge"})
    return response


@monitoring_target_bp.route("/alerts/<int:alert_id>/claim", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:center", "monitoring:alert:claim")
def claim_alert(alert_id: int):
    payload = request.get_json() or {}
    row = SingleAlert.query.get(alert_id)
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    labels = _json_load(row.labels_json, {})
    annotations = _json_load(row.annotations_json, {})
    identity = get_jwt_identity()
    current_user = User.query.get(int(identity)) if identity else None
    assignee = str(payload.get("assignee") or (current_user.username if current_user else "system"))
    labels["assignee"] = assignee
    note = payload.get("note")
    if note:
        annotations["note"] = str(note)
    row.labels_json = _json_dump(labels)
    row.annotations_json = _json_dump(annotations)
    row.modifier = assignee
    row.updated_at = _now_naive_utc()
    db.session.commit()
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "claim"})
    return jsonify(
        {
            "code": 200,
            "data": _extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
            ),
        }
    )


@monitoring_target_bp.route("/alerts/<int:alert_id>/close", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:center", "monitoring:alert:close")
def close_alert(alert_id: int):
    row = SingleAlert.query.get(alert_id)
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    now_ms = _now_ms()
    if row.start_at is None:
        row.start_at = now_ms
    if row.status != "resolved":
        row.status = "resolved"
        row.end_at = now_ms
        row.updated_at = _now_naive_utc()
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
            created_at=_now_naive_utc(),
        )
        db.session.add(history)
        db.session.commit()
    response = jsonify(
        {
            "code": 200,
            "data": _extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
            ),
        }
    )
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "close"})
    return response


@monitoring_target_bp.route("/alerts/<int:alert_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:center", "monitoring:alert:close", "monitoring:alert:history")
def delete_alert(alert_id: int):
    scope = (request.args.get("scope") or "").strip().lower()
    deleted_current = False
    deleted_history = False
    cascade_history = False

    if scope in {"", "all", "current"}:
        row = SingleAlert.query.get(alert_id)
        if row:
            db.session.delete(row)
            deleted_current = True
        if scope in {"", "all"}:
            removed = AlertHistory.query.filter_by(alert_id=alert_id).delete(synchronize_session=False)
            cascade_history = bool(removed)
            deleted_history = deleted_history or cascade_history

    if scope in {"", "all", "history"}:
        row = AlertHistory.query.get(alert_id)
        if row:
            db.session.delete(row)
            deleted_history = True

    if not deleted_current and not deleted_history:
        db.session.rollback()
        return jsonify({"code": 404, "message": "告警不存在"}), 404

    db.session.commit()
    _emit_alert_event(
        "monitoring:alert:update",
        {"id": alert_id, "action": "delete", "scope": scope or "all"},
    )
    return jsonify(
        {
            "code": 200,
            "data": {
                "id": alert_id,
                "scope": scope or "all",
                "deleted_current": deleted_current,
                "deleted_history": deleted_history,
                "cascade_history": cascade_history,
            },
        }
    )


@monitoring_target_bp.route("/alert-rules", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def list_alert_rules():
    q = (request.args.get("q") or "").strip()
    include_bound = _to_bool(request.args.get("include_bound"), default=False)
    scope = str(request.args.get("scope") or "global").strip().lower()
    if scope not in {"global", "bound", "all"}:
        scope = "global"
    if include_bound and scope == "global":
        scope = "all"
    query = AlertDefine.query
    if q:
        query = query.filter(
            db.or_(
                AlertDefine.name.ilike(f"%{q}%"),
                AlertDefine.expr.ilike(f"%{q}%"),
                AlertDefine.labels_json.ilike(f"%{q}%"),
            )
        )
    rows = query.order_by(AlertDefine.updated_at.desc(), AlertDefine.id.desc()).all()
    page, page_size = _page_args()
    items = []
    for row in rows:
        item = _rule_from_model(row)
        labels = item.get("labels") if isinstance(item, dict) else {}
        monitor_id = ""
        source = ""
        instance = ""
        if isinstance(labels, dict):
            monitor_id = str(labels.get("monitor_id") or "").strip()
            source = str(labels.get("source") or "").strip().lower()
            instance = str(labels.get("instance") or "").strip()
        is_bound_rule = bool(monitor_id) or source in {"template_default", "instance_override", "target"} or bool(instance)
        # 默认仅展示全局告警规则，实例绑定规则在“监控任务详情-告警”里管理
        if scope == "global" and is_bound_rule:
            continue
        if scope == "bound" and (not is_bound_rule):
            continue
        items.append(item)
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alert-rules", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def create_alert_rule():
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    metric = str(payload.get("metric") or "value").strip() or "value"
    if not name:
        return jsonify({"code": 400, "message": "规则名称不能为空"}), 400
    level = str(payload.get("level") or "warning")
    operator = str(payload.get("operator") or ">")
    threshold = payload.get("threshold", 0)
    try:
        threshold_val = float(threshold)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "threshold 必须是数字"}), 400
    labels = {
        "metric": metric,
        "severity": level,
        "operator": operator,
        "threshold": threshold_val,
    }
    _apply_recovery_config_to_labels(labels, payload)
    annotations = {"summary": name}
    if isinstance(payload.get("annotations"), dict):
        for key, value in payload.get("annotations").items():
            ann_key = str(key or "").strip()
            if ann_key:
                annotations[ann_key] = value
    title_template = str(payload.get("title_template") or "").strip()
    if title_template:
        annotations["title_template"] = title_template
    
    # 处理通知规则关联
    notice_rule_ids, err = _extract_notice_rule_ids(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400
    if notice_rule_ids is not None:
        validate_msg = _validate_notice_rule_ids(notice_rule_ids)
        if validate_msg:
            return jsonify({"code": 400, "message": validate_msg}), 400
    notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
    
    monitor_type = str(payload.get("type") or payload.get("monitor_type") or "realtime_metric").strip() or "realtime_metric"
    row = AlertDefine(
        name=name,
        type=monitor_type,
        expr=str(payload.get("expr") or f"{metric} {operator} {threshold_val}"),
        period=max(int(payload.get("period") or 0), 0),
        times=max(int(payload.get("times") or 1), 1),
        labels_json=_json_dump(labels),
        annotations_json=_json_dump(annotations),
        template=payload.get("template"),
        datasource_type=payload.get("datasource_type"),
        enabled=bool(payload.get("enabled", True)),
        notice_rule_id=notice_rule_id,
        notice_rule_ids_json=_json_dump(notice_rule_ids or []),
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": _rule_from_model(row)})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def update_alert_rule(rule_id: int):
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "type" in payload or "monitor_type" in payload:
        row.type = str(payload.get("type") or payload.get("monitor_type") or row.type).strip() or row.type
    labels = _json_load(row.labels_json, {})
    if not isinstance(labels, dict):
        labels = {}
    if "metric" in payload:
        labels["metric"] = str(payload.get("metric") or "value").strip() or "value"
    if "level" in payload:
        labels["severity"] = str(payload.get("level") or "warning")
    if "operator" in payload:
        labels["operator"] = str(payload.get("operator") or ">")
    if "threshold" in payload:
        try:
            labels["threshold"] = float(payload.get("threshold"))
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "threshold 必须是数字"}), 400
    _apply_recovery_config_to_labels(labels, payload)
    row.labels_json = _json_dump(labels)
    annotations = _json_load(row.annotations_json, {})
    if not isinstance(annotations, dict):
        annotations = {}
    if "annotations" in payload and isinstance(payload.get("annotations"), dict):
        for key, value in payload.get("annotations").items():
            ann_key = str(key or "").strip()
            if ann_key:
                annotations[ann_key] = value
    if "title_template" in payload:
        title_template = str(payload.get("title_template") or "").strip()
        if title_template:
            annotations["title_template"] = title_template
        else:
            annotations.pop("title_template", None)
    row.annotations_json = _json_dump(annotations)
    if "period" in payload:
        try:
            row.period = max(int(payload.get("period") or 0), 0)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "period 必须是整数"}), 400
    if "times" in payload:
        try:
            row.times = max(int(payload.get("times") or 1), 1)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "times 必须是整数"}), 400
    if "template" in payload:
        row.template = str(payload.get("template") or "").strip() or None
    if "datasource_type" in payload:
        row.datasource_type = str(payload.get("datasource_type") or "").strip() or None
    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    if "expr" in payload:
        row.expr = str(payload.get("expr") or row.expr)
    else:
        metric = labels.get("metric") or "value"
        operator = labels.get("operator") or ">"
        threshold = labels.get("threshold", 0)
        row.expr = f"{metric} {operator} {threshold}"
    
    # 处理通知规则关联更新
    notice_rule_ids, err = _extract_notice_rule_ids(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400
    if notice_rule_ids is not None:
        validate_msg = _validate_notice_rule_ids(notice_rule_ids)
        if validate_msg:
            return jsonify({"code": 400, "message": validate_msg}), 400
        row.notice_rule_id = notice_rule_ids[0] if notice_rule_ids else None
        row.notice_rule_ids_json = _json_dump(notice_rule_ids or [])
    
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _rule_from_model(row)})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def delete_alert_rule(rule_id: int):
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>/enable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def enable_alert_rule(rule_id: int):
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    row.enabled = True
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _rule_from_model(row)})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>/disable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def disable_alert_rule(rule_id: int):
    row = AlertDefine.query.get(rule_id)
    if not row:
        return jsonify({"code": 404, "message": "规则不存在"}), 404
    row.enabled = False
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _rule_from_model(row)})


def _generate_webhook_token() -> str:
    """生成唯一的 Webhook Token"""
    import secrets
    return secrets.token_urlsafe(32)


def _integration_from_model(row: AlertIntegration) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "source": row.source,
        "description": row.description,
        "webhook_url": row.webhook_url,
        "severity_mapping": row.severity_mapping,
        "default_labels": row.default_labels,
        "label_mapping": row.label_mapping,
        "source_config": row.source_config,
        "auth_type": row.auth_type,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@monitoring_target_bp.route("/alert-integrations", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:view")
def list_alert_integrations():
    """列出外部告警集成配置"""
    q = (request.args.get("q") or "").strip()
    source_filter = (request.args.get("source") or "").strip().lower()
    status_filter = (request.args.get("status") or "").strip().lower()
    query = AlertIntegration.query
    if q:
        query = query.filter(AlertIntegration.name.ilike(f"%{q}%"))
    if source_filter:
        query = query.filter(AlertIntegration.source == source_filter)
    if status_filter:
        query = query.filter(AlertIntegration.status == status_filter)
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(AlertIntegration.updated_at.desc(), AlertIntegration.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _list_response([_integration_from_model(row) for row in rows], total, page, page_size)


@monitoring_target_bp.route("/alert-integrations", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:create")
def create_alert_integration():
    """创建外部告警集成配置"""
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    source = str(payload.get("source") or "custom").strip().lower()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    if source not in ("prometheus", "zabbix", "skywalking", "nagios", "custom"):
        return jsonify({"code": 400, "message": "不支持的源系统类型"}), 400

    row = AlertIntegration(
        name=name,
        source=source,
        description=str(payload.get("description") or "").strip() or None,
        webhook_token=_generate_webhook_token(),
        severity_mapping=str(payload.get("severity_mapping") or "").strip() or None,
        default_labels=str(payload.get("default_labels") or "").strip() or None,
        label_mapping=str(payload.get("label_mapping") or "").strip() or None,
        source_config=str(payload.get("source_config") or "").strip() or None,
        auth_type=str(payload.get("auth_type") or "none").strip().lower(),
        auth_token=str(payload.get("auth_token") or "").strip() or None,
        auth_username=str(payload.get("auth_username") or "").strip() or None,
        auth_password=str(payload.get("auth_password") or "").strip() or None,
        status=str(payload.get("status") or "enabled").strip().lower(),
        creator="python-web",
        modifier="python-web",
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": _integration_from_model(row)})


@monitoring_target_bp.route("/alert-integrations/<integration_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:edit")
def update_alert_integration(integration_id: str):
    """更新外部告警集成配置"""
    row = AlertIntegration.query.get(integration_id)
    if not row:
        return jsonify({"code": 404, "message": "集成不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "source" in payload:
        source = str(payload.get("source") or "").strip().lower()
        if source in ("prometheus", "zabbix", "skywalking", "nagios", "custom"):
            row.source = source
    if "description" in payload:
        row.description = str(payload.get("description") or "").strip() or None
    if "severity_mapping" in payload:
        row.severity_mapping = str(payload.get("severity_mapping") or "").strip() or None
    if "default_labels" in payload:
        row.default_labels = str(payload.get("default_labels") or "").strip() or None
    if "label_mapping" in payload:
        row.label_mapping = str(payload.get("label_mapping") or "").strip() or None
    if "source_config" in payload:
        row.source_config = str(payload.get("source_config") or "").strip() or None
    if "auth_type" in payload:
        row.auth_type = str(payload.get("auth_type") or "none").strip().lower()
    if "auth_token" in payload:
        row.auth_token = str(payload.get("auth_token") or "").strip() or None
    if "auth_username" in payload:
        row.auth_username = str(payload.get("auth_username") or "").strip() or None
    if "auth_password" in payload:
        row.auth_password = str(payload.get("auth_password") or "").strip() or None
    if "status" in payload:
        row.status = str(payload.get("status") or "enabled").strip().lower()
    row.modifier = "python-web"
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _integration_from_model(row)})


@monitoring_target_bp.route("/alert-integrations/<integration_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:delete")
def delete_alert_integration(integration_id: str):
    """删除外部告警集成配置"""
    row = AlertIntegration.query.get(integration_id)
    if not row:
        return jsonify({"code": 404, "message": "集成不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-integrations/<integration_id>/toggle", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:edit")
def toggle_alert_integration(integration_id: str):
    """启用/禁用外部告警集成"""
    row = AlertIntegration.query.get(integration_id)
    if not row:
        return jsonify({"code": 404, "message": "集成不存在"}), 404
    payload = request.get_json() or {}
    enabled = payload.get("enabled")
    if enabled is True:
        row.status = "enabled"
    elif enabled is False:
        row.status = "disabled"
    row.modifier = "python-web"
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _integration_from_model(row)})


@monitoring_target_bp.route("/alert-integrations/<integration_id>/test", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:test")
def test_alert_integration(integration_id: str):
    """测试外部告警集成"""
    row = AlertIntegration.query.get(integration_id)
    if not row:
        return jsonify({"code": 404, "message": "集成不存在"}), 404
    # payload = request.get_json() or {}
    # TODO: 实现测试告警处理逻辑
    # 将测试内容解析并进入告警收敛流程
    return jsonify({"code": 200, "data": {"tested": True, "id": row.id, "message": "测试告警已接收"}})


@monitoring_target_bp.route("/alert-groups", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:view")
def list_alert_groups():
    q = (request.args.get("q") or "").strip()
    query = AlertGroup.query
    if q:
        query = query.filter(AlertGroup.name.ilike(f"%{q}%"))
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(AlertGroup.updated_at.desc(), AlertGroup.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        group_labels = _json_load(row.labels_json, [])
        if not isinstance(group_labels, list):
            group_labels = []
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "group_key": row.group_key,
                "match_type": row.match_type or 0,
                "group_labels": group_labels,
                "group_wait": row.group_wait or 30,
                "group_interval": row.group_interval or 300,
                "repeat_interval": row.repeat_interval or 14400,
                "enabled": bool(row.enabled),
            }
        )
    return _list_response(items, total, page, page_size)


@monitoring_target_bp.route("/alert-groups", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:create")
def create_alert_group():
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    group_key = str(payload.get("group_key") or "").strip() or name
    group_labels = payload.get("group_labels") if isinstance(payload.get("group_labels"), list) else []
    row = AlertGroup(
        name=name,
        group_key=group_key,
        match_type=int(payload.get("match_type") or 0),
        labels_json=_json_dump(group_labels),
        group_wait=payload.get("group_wait", 30),
        group_interval=payload.get("group_interval", 300),
        repeat_interval=payload.get("repeat_interval", 14400),
        enabled=bool(payload.get("enabled", True)),
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"code": 409, "message": "group_key 已存在"}), 409
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "group_key": row.group_key,
        "match_type": row.match_type,
        "group_labels": group_labels,
        "group_wait": row.group_wait,
        "group_interval": row.group_interval,
        "repeat_interval": row.repeat_interval,
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-groups/<group_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:edit")
def update_alert_group(group_id: str):
    row = AlertGroup.query.get(group_id)
    if not row:
        return jsonify({"code": 404, "message": "分组不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "group_key" in payload:
        row.group_key = str(payload.get("group_key") or "").strip() or row.group_key
    if "match_type" in payload:
        row.match_type = int(payload.get("match_type") or 0)
    if "group_labels" in payload and isinstance(payload.get("group_labels"), list):
        row.labels_json = _json_dump(payload.get("group_labels"))
    if "group_wait" in payload:
        row.group_wait = payload.get("group_wait")
    if "group_interval" in payload:
        row.group_interval = payload.get("group_interval")
    if "repeat_interval" in payload:
        row.repeat_interval = payload.get("repeat_interval")
    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"code": 409, "message": "group_key 已存在"}), 409
    group_labels = _json_load(row.labels_json, [])
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "group_key": row.group_key,
        "match_type": row.match_type,
        "group_labels": group_labels if isinstance(group_labels, list) else [],
        "group_wait": row.group_wait,
        "group_interval": row.group_interval,
        "repeat_interval": row.repeat_interval,
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-groups/<group_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:delete")
def delete_alert_group(group_id: str):
    row = AlertGroup.query.get(group_id)
    if not row:
        return jsonify({"code": 404, "message": "分组不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-groups/<group_id>/enabled", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:edit")
def update_alert_group_enabled(group_id: str):
    row = AlertGroup.query.get(group_id)
    if not row:
        return jsonify({"code": 404, "message": "分组不存在"}), 404
    payload = request.get_json() or {}
    row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": {"id": row.id, "enabled": bool(row.enabled)}})


@monitoring_target_bp.route("/alert-inhibits", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:view")
def list_alert_inhibits():
    q = (request.args.get("q") or "").strip()
    query = AlertInhibit.query
    if q:
        query = query.filter(AlertInhibit.name.ilike(f"%{q}%"))
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(AlertInhibit.updated_at.desc(), AlertInhibit.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        source = _json_load(row.source_labels_json, {})
        target = _json_load(row.target_labels_json, {})
        equal_labels = _json_load(row.equal_labels_json, [])
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "source_labels": source if isinstance(source, dict) else {},
                "target_labels": target if isinstance(target, dict) else {},
                "equal_labels": equal_labels if isinstance(equal_labels, list) else [],
                "enabled": bool(row.enabled),
            }
        )
    return _list_response(items, total, page, page_size)


@monitoring_target_bp.route("/alert-inhibits", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:create")
def create_alert_inhibit():
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    source_labels = payload.get("source_labels") if isinstance(payload.get("source_labels"), dict) else {}
    target_labels = payload.get("target_labels") if isinstance(payload.get("target_labels"), dict) else {}
    equal_labels = payload.get("equal_labels") if isinstance(payload.get("equal_labels"), list) else []
    row = AlertInhibit(
        name=name,
        source_labels_json=_json_dump(source_labels),
        target_labels_json=_json_dump(target_labels),
        equal_labels_json=_json_dump(equal_labels),
        enabled=bool(payload.get("enabled", True)),
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "source_labels": source_labels,
        "target_labels": target_labels,
        "equal_labels": equal_labels,
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-inhibits/<inhibit_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:edit")
def update_alert_inhibit(inhibit_id: str):
    row = AlertInhibit.query.get(inhibit_id)
    if not row:
        return jsonify({"code": 404, "message": "抑制规则不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "source_labels" in payload and isinstance(payload.get("source_labels"), dict):
        row.source_labels_json = _json_dump(payload.get("source_labels"))
    if "target_labels" in payload and isinstance(payload.get("target_labels"), dict):
        row.target_labels_json = _json_dump(payload.get("target_labels"))
    if "equal_labels" in payload and isinstance(payload.get("equal_labels"), list):
        row.equal_labels_json = _json_dump(payload.get("equal_labels"))
    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "source_labels": _json_load(row.source_labels_json, {}),
        "target_labels": _json_load(row.target_labels_json, {}),
        "equal_labels": _json_load(row.equal_labels_json, []),
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-inhibits/<inhibit_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:delete")
def delete_alert_inhibit(inhibit_id: str):
    row = AlertInhibit.query.get(inhibit_id)
    if not row:
        return jsonify({"code": 404, "message": "抑制规则不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-inhibits/<inhibit_id>/enabled", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:edit")
def update_alert_inhibit_enabled(inhibit_id: str):
    row = AlertInhibit.query.get(inhibit_id)
    if not row:
        return jsonify({"code": 404, "message": "抑制规则不存在"}), 404
    payload = request.get_json() or {}
    row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": {"id": row.id, "enabled": bool(row.enabled)}})


@monitoring_target_bp.route("/alert-silences", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:view")
def list_alert_silences():
    q = (request.args.get("q") or "").strip()
    query = AlertSilence.query
    if q:
        query = query.filter(AlertSilence.name.ilike(f"%{q}%"))
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(AlertSilence.updated_at.desc(), AlertSilence.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        labels = _json_load(row.labels_json, {})
        days = _json_load(row.days_json, [])
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "type": row.type or 0,
                "match_type": row.match_type or 0,
                "labels": labels if isinstance(labels, dict) else {},
                "reason": labels.get("reason") if isinstance(labels, dict) else None,
                "days": days if isinstance(days, list) else [],
                "start_time": row.start_time,
                "end_time": row.end_time,
                "enabled": bool(row.enabled),
            }
        )
    return _list_response(items, total, page, page_size)


@monitoring_target_bp.route("/alert-silences", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:create")
def create_alert_silence():
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400

    silence_type = int(payload.get("type") or 0)
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")

    if not start_time or not end_time:
        return jsonify({"code": 400, "message": "开始时间和结束时间不能为空"}), 400
    if end_time <= start_time:
        return jsonify({"code": 400, "message": "结束时间必须晚于开始时间"}), 400

    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    if payload.get("reason"):
        labels["reason"] = str(payload.get("reason"))

    days = payload.get("days") if isinstance(payload.get("days"), list) else []

    row = AlertSilence(
        name=name,
        type=silence_type,
        match_type=int(payload.get("match_type") or 0),
        labels_json=_json_dump(labels),
        days_json=_json_dump(days) if silence_type == 1 else _json_dump([]),
        times=payload.get("times"),
        start_time=start_time,
        end_time=end_time,
        enabled=bool(payload.get("enabled", True)),
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "match_type": row.match_type,
        "labels": labels,
        "reason": labels.get("reason"),
        "days": days if silence_type == 1 else [],
        "start_time": row.start_time,
        "end_time": row.end_time,
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-silences/<silence_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:edit")
def update_alert_silence(silence_id: str):
    row = AlertSilence.query.get(silence_id)
    if not row:
        return jsonify({"code": 404, "message": "静默规则不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "type" in payload:
        row.type = int(payload.get("type") or 0)
    if "match_type" in payload:
        row.match_type = int(payload.get("match_type") or 0)

    labels = _json_load(row.labels_json, {})
    if "labels" in payload and isinstance(payload.get("labels"), dict):
        labels = payload.get("labels")
    if "reason" in payload:
        labels["reason"] = str(payload.get("reason") or "").strip()
    row.labels_json = _json_dump(labels)

    if "days" in payload and isinstance(payload.get("days"), list):
        row.days_json = _json_dump(payload.get("days"))

    if "start_time" in payload:
        row.start_time = payload.get("start_time")
    if "end_time" in payload:
        row.end_time = payload.get("end_time")

    if row.start_time and row.end_time and row.end_time <= row.start_time:
        return jsonify({"code": 400, "message": "静默时间范围不合法"}), 400

    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    db.session.commit()

    days = _json_load(row.days_json, [])
    return jsonify({"code": 200, "data": {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "match_type": row.match_type,
        "labels": labels,
        "reason": labels.get("reason"),
        "days": days if isinstance(days, list) else [],
        "start_time": row.start_time,
        "end_time": row.end_time,
        "enabled": bool(row.enabled)
    }})


@monitoring_target_bp.route("/alert-silences/<silence_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:delete")
def delete_alert_silence(silence_id: str):
    row = AlertSilence.query.get(silence_id)
    if not row:
        return jsonify({"code": 404, "message": "静默规则不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-silences/<silence_id>/enabled", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:edit")
def update_alert_silence_enabled(silence_id: str):
    row = AlertSilence.query.get(silence_id)
    if not row:
        return jsonify({"code": 404, "message": "静默规则不存在"}), 404
    payload = request.get_json() or {}
    row.enabled = bool(payload.get("enabled"))
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": {"id": row.id, "enabled": bool(row.enabled)}})


@monitoring_target_bp.route("/alert-notices", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:view")
def list_alert_notices():
    """获取通知规则列表"""
    q = (request.args.get("q") or "").strip()
    receiver_id = request.args.get("receiver_id")
    query = NoticeRule.query
    if q:
        query = query.filter(NoticeRule.name.ilike(f"%{q}%"))
    if receiver_id:
        try:
            query = query.filter(NoticeRule.receiver_channel_id == int(receiver_id))
        except (TypeError, ValueError):
            pass
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(NoticeRule.updated_at.desc(), NoticeRule.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _list_response([_notice_rule_from_model(row) for row in rows], total, page, page_size)


@monitoring_target_bp.route("/alert-notices", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:create")
def create_alert_notice():
    """创建通知规则"""
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    
    # 获取通知渠道ID
    receiver_channel_id = payload.get("receiver_id") or payload.get("receiver_channel_id")
    if receiver_channel_id is None:
        return jsonify({"code": 400, "message": "请选择通知渠道"}), 400
    try:
        receiver_channel_id = int(receiver_channel_id)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "receiver_id 必须是整数"}), 400
    
    # 验证通知渠道是否存在
    receiver = NoticeReceiver.query.get(receiver_channel_id)
    if not receiver:
        return jsonify({"code": 400, "message": "指定的通知渠道不存在"}), 400
    
    notify_scale = str(payload.get("notify_scale") or "single").strip().lower()
    if notify_scale not in {"single", "batch"}:
        return jsonify({"code": 400, "message": "notify_scale 只能是 single/batch"}), 400
    
    # 处理标签过滤
    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    days = payload.get("days") if isinstance(payload.get("days"), list) else [1, 2, 3, 4, 5, 6, 7]
    recipient_type = str(payload.get("recipient_type") or "user").strip().lower()
    if recipient_type not in {"user", "department"}:
        return jsonify({"code": 400, "message": "recipient_type 只能是 user/department"}), 400
    recipient_ids = payload.get("recipient_ids") if isinstance(payload.get("recipient_ids"), list) else []
    include_sub_departments = bool(payload.get("include_sub_departments", True))
    
    row = NoticeRule(
        name=name,
        receiver_channel_id=receiver_channel_id,
        receiver_name=receiver.name,
        receiver_type=receiver.type,
        notify_times=max(int(payload.get("notify_times") or 1), 1),
        notify_scale=notify_scale,
        template_id=payload.get("template_id"),
        template_name=str(payload.get("template_name") or "").strip() or None,
        filter_all=bool(payload.get("filter_all", True)),
        labels_json=_json_dump(labels),
        days_json=_json_dump(days),
        period_start=str(payload.get("period_start") or "").strip() or None,
        period_end=str(payload.get("period_end") or "").strip() or None,
        recipient_type=recipient_type,
        recipient_ids_json=_json_dump(recipient_ids),
        include_sub_departments=include_sub_departments,
        enable=bool(payload.get("enable", True)),
        creator=get_jwt_identity(),
        modifier=get_jwt_identity(),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": _notice_rule_from_model(row)})


@monitoring_target_bp.route("/alert-notices/<notice_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:edit")
def update_alert_notice(notice_id: str):
    """更新通知规则"""
    row = NoticeRule.query.get(notice_id)
    if not row:
        return jsonify({"code": 404, "message": "通知配置不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "receiver_id" in payload or "receiver_channel_id" in payload:
        receiver_channel_id = payload.get("receiver_id") or payload.get("receiver_channel_id")
        if receiver_channel_id is not None:
            try:
                receiver_channel_id = int(receiver_channel_id)
                receiver = NoticeReceiver.query.get(receiver_channel_id)
                if receiver:
                    row.receiver_channel_id = receiver_channel_id
                    row.receiver_name = receiver.name
                    row.receiver_type = receiver.type
            except (TypeError, ValueError):
                return jsonify({"code": 400, "message": "receiver_id 必须是整数"}), 400
    if "notify_times" in payload:
        try:
            row.notify_times = max(int(payload.get("notify_times")), 1)
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "notify_times 必须是整数"}), 400
    if "notify_scale" in payload:
        scale = str(payload.get("notify_scale") or "").strip().lower()
        if scale not in {"single", "batch"}:
            return jsonify({"code": 400, "message": "notify_scale 只能是 single/batch"}), 400
        row.notify_scale = scale
    if "template_id" in payload:
        row.template_id = payload.get("template_id")
    if "template_name" in payload:
        row.template_name = str(payload.get("template_name") or "").strip() or None
    if "filter_all" in payload:
        row.filter_all = bool(payload.get("filter_all"))
    if "labels" in payload and isinstance(payload.get("labels"), dict):
        row.labels_json = _json_dump(payload.get("labels"))
    if "days" in payload and isinstance(payload.get("days"), list):
        row.days_json = _json_dump(payload.get("days"))
    if "period_start" in payload:
        row.period_start = str(payload.get("period_start") or "").strip() or None
    if "period_end" in payload:
        row.period_end = str(payload.get("period_end") or "").strip() or None
    if "recipient_type" in payload:
        recipient_type = str(payload.get("recipient_type") or "user").strip().lower()
        if recipient_type not in {"user", "department"}:
            return jsonify({"code": 400, "message": "recipient_type 只能是 user/department"}), 400
        row.recipient_type = recipient_type
    if "recipient_ids" in payload and isinstance(payload.get("recipient_ids"), list):
        row.recipient_ids_json = _json_dump(payload.get("recipient_ids"))
    if "include_sub_departments" in payload:
        row.include_sub_departments = bool(payload.get("include_sub_departments"))
    if "enable" in payload:
        row.enable = bool(payload.get("enable"))
    row.modifier = get_jwt_identity()
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": _notice_rule_from_model(row)})


@monitoring_target_bp.route("/alert-notices/<notice_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:delete")
def delete_alert_notice(notice_id: str):
    row = NoticeRule.query.get(notice_id)
    if not row:
        return jsonify({"code": 404, "message": "通知配置不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/alert-notices/<notice_id>/test", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:test")
def test_alert_notice(notice_id: str):
    row = NoticeRule.query.get(notice_id)
    if not row:
        return jsonify({"code": 404, "message": "通知配置不存在"}), 404
    return jsonify({"code": 200, "data": {"tested": True, "id": row.id}})


# ==================== 通知渠道配置 API ====================

@monitoring_target_bp.route("/notice-receivers", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:view")
def list_notice_receivers():
    """获取通知渠道列表"""
    q = (request.args.get("q") or "").strip()
    type_filter = request.args.get("type")
    enable_filter = request.args.get("enable")
    
    query = NoticeReceiver.query
    if q:
        query = query.filter(NoticeReceiver.name.ilike(f"%{q}%"))
    if type_filter is not None:
        try:
            query = query.filter(NoticeReceiver.type == int(type_filter))
        except (TypeError, ValueError):
            pass
    if enable_filter is not None:
        query = query.filter(NoticeReceiver.enable == (enable_filter.lower() == "true"))
    
    page, page_size = _page_args()
    total = query.count()
    rows = (
        query.order_by(NoticeReceiver.updated_at.desc(), NoticeReceiver.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return _list_response([row.to_dict() for row in rows], total, page, page_size)


@monitoring_target_bp.route("/notice-receivers/all", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:view")
def list_all_notice_receivers():
    """获取所有启用的通知渠道（用于下拉选择）"""
    rows = NoticeReceiver.query.filter_by(enable=True).order_by(NoticeReceiver.name).all()
    return jsonify({
        "code": 200,
        "data": [{"id": r.id, "name": r.name, "type": r.type, "type_name": r.type_name} for r in rows]
    })


@monitoring_target_bp.route("/notice-receivers/<receiver_id>", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:view")
def get_notice_receiver(receiver_id: str):
    """获取单个通知渠道详情"""
    row = NoticeReceiver.query.get(receiver_id)
    if not row:
        return jsonify({"code": 404, "message": "通知渠道不存在"}), 404
    return jsonify({"code": 200, "data": row.to_dict()})


@monitoring_target_bp.route("/notice-receivers", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:create")
def create_notice_receiver():
    """创建通知渠道"""
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    
    try:
        type_val = int(payload.get("type", NoticeReceiver.TYPE_EMAIL))
    except (TypeError, ValueError):
        type_val = NoticeReceiver.TYPE_EMAIL
    
    row = NoticeReceiver(
        name=name,
        type=type_val,
        enable=bool(payload.get("enable", True)),
        description=str(payload.get("description") or "").strip() or None,
        creator=get_jwt_identity(),
        modifier=get_jwt_identity(),
    )
    
    # 根据类型设置配置
    config = payload.get("config") or {}
    _apply_receiver_config(row, config)
    
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": row.to_dict()})


@monitoring_target_bp.route("/notice-receivers/<receiver_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:edit")
def update_notice_receiver(receiver_id: str):
    """更新通知渠道"""
    row = NoticeReceiver.query.get(receiver_id)
    if not row:
        return jsonify({"code": 404, "message": "通知渠道不存在"}), 404
    
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "type" in payload:
        try:
            row.type = int(payload.get("type"))
        except (TypeError, ValueError):
            pass
    if "enable" in payload:
        row.enable = bool(payload.get("enable"))
    if "description" in payload:
        row.description = str(payload.get("description") or "").strip() or None
    
    # 更新配置
    if "config" in payload:
        _apply_receiver_config(row, payload.get("config") or {})
    
    row.modifier = get_jwt_identity()
    row.updated_at = _now_naive_utc()
    db.session.commit()
    return jsonify({"code": 200, "data": row.to_dict()})


@monitoring_target_bp.route("/notice-receivers/<receiver_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:delete")
def delete_notice_receiver(receiver_id: str):
    """删除通知渠道"""
    row = NoticeReceiver.query.get(receiver_id)
    if not row:
        return jsonify({"code": 404, "message": "通知渠道不存在"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "data": {"deleted": True}})


@monitoring_target_bp.route("/notice-receivers/<receiver_id>/test", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:test")
def test_notice_receiver(receiver_id: str):
    """测试通知渠道"""
    row = NoticeReceiver.query.get(receiver_id)
    if not row:
        return jsonify({"code": 404, "message": "通知渠道不存在"}), 404
    
    # TODO: 实现实际的发送测试逻辑
    return jsonify({"code": 200, "data": {"tested": True, "id": row.id, "type": row.type}})


def _apply_receiver_config(row: NoticeReceiver, config: dict):
    """应用通知渠道配置"""
    # 邮件配置
    row.smtp_host = config.get("smtp_host") or row.smtp_host
    row.smtp_port = config.get("smtp_port") or row.smtp_port
    row.smtp_username = config.get("smtp_username") or row.smtp_username
    row.smtp_password = config.get("smtp_password") or row.smtp_password
    row.smtp_use_tls = config.get("smtp_use_tls", row.smtp_use_tls)
    row.email_from = config.get("email_from") or row.email_from
    row.email_to = config.get("email_to") or row.email_to
    
    # Webhook配置
    row.hook_url = config.get("hook_url") or row.hook_url
    row.hook_auth_type = config.get("hook_auth_type") or row.hook_auth_type
    row.hook_auth_token = config.get("hook_auth_token") or row.hook_auth_token
    row.hook_method = config.get("hook_method") or row.hook_method
    row.hook_content_type = config.get("hook_content_type") or row.hook_content_type
    
    # 企业微信机器人
    row.wecom_key = config.get("wecom_key") or row.wecom_key
    row.wecom_mentioned_mobiles = config.get("wecom_mentioned_mobiles") or row.wecom_mentioned_mobiles
    
    # 企业微信应用
    row.wecom_corp_id = config.get("wecom_corp_id") or row.wecom_corp_id
    row.wecom_agent_id = config.get("wecom_agent_id") or row.wecom_agent_id
    row.wecom_app_secret = config.get("wecom_app_secret") or row.wecom_app_secret
    row.wecom_to_user = config.get("wecom_to_user") or row.wecom_to_user
    row.wecom_to_party = config.get("wecom_to_party") or row.wecom_to_party
    row.wecom_to_tag = config.get("wecom_to_tag") or row.wecom_to_tag
    
    # 钉钉
    row.dingtalk_access_token = config.get("dingtalk_access_token") or row.dingtalk_access_token
    row.dingtalk_secret = config.get("dingtalk_secret") or row.dingtalk_secret
    row.dingtalk_at_mobiles = config.get("dingtalk_at_mobiles") or row.dingtalk_at_mobiles
    row.dingtalk_is_at_all = config.get("dingtalk_is_at_all", row.dingtalk_is_at_all)
    
    # 飞书机器人
    row.feishu_webhook_token = config.get("feishu_webhook_token") or row.feishu_webhook_token
    row.feishu_secret = config.get("feishu_secret") or row.feishu_secret
    
    # 飞书应用
    row.feishu_app_id = config.get("feishu_app_id") or row.feishu_app_id
    row.feishu_app_secret = config.get("feishu_app_secret") or row.feishu_app_secret
    row.feishu_receive_type = config.get("feishu_receive_type", row.feishu_receive_type)
    row.feishu_user_id = config.get("feishu_user_id") or row.feishu_user_id
    row.feishu_chat_id = config.get("feishu_chat_id") or row.feishu_chat_id
    
    # Slack
    row.slack_webhook_url = config.get("slack_webhook_url") or row.slack_webhook_url
    
    # Discord
    row.discord_webhook_url = config.get("discord_webhook_url") or row.discord_webhook_url
    
    # 短信
    row.sms_provider = config.get("sms_provider") or row.sms_provider
    row.sms_access_key = config.get("sms_access_key") or row.sms_access_key
    row.sms_secret_key = config.get("sms_secret_key") or row.sms_secret_key
    row.sms_sign_name = config.get("sms_sign_name") or row.sms_sign_name
    row.sms_template_code = config.get("sms_template_code") or row.sms_template_code
    row.sms_phone_numbers = config.get("sms_phone_numbers") or row.sms_phone_numbers
    
    # 华为云SMN
    row.smn_ak = config.get("smn_ak") or row.smn_ak
    row.smn_sk = config.get("smn_sk") or row.smn_sk
    row.smn_project_id = config.get("smn_project_id") or row.smn_project_id
    row.smn_region = config.get("smn_region") or row.smn_region
    row.smn_topic_urn = config.get("smn_topic_urn") or row.smn_topic_urn
    
    # Server酱
    row.serverchan_send_key = config.get("serverchan_send_key") or row.serverchan_send_key
    
    # Gotify
    row.gotify_url = config.get("gotify_url") or row.gotify_url
    row.gotify_token = config.get("gotify_token") or row.gotify_token
    row.gotify_priority = config.get("gotify_priority", row.gotify_priority)


@monitoring_target_bp.route("/alerts/realtime/publish", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert", "monitoring:alert:center")
def publish_alert_event():
    payload = request.get_json() or {}
    _emit_alert_event("monitoring:alert:new", payload)
    return jsonify({"code": 200, "data": {"published": True}})


@monitoring_target_bp.route("/dashboard", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:dashboard", "monitoring:dashboard:view")
def monitoring_dashboard():
    try:
        monitor_payload = _fetch_manager_payload("/api/v1/monitors", params={"page": 1, "page_size": 5000})
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        current_alert_payload = _fetch_manager_payload_any(
            [
                ("/api/v1/alerts", {"page": 1, "page_size": 200, "status": "pending"}),
                ("/api/v1/alerts", {"page": 1, "page_size": 200, "scope": "current"}),
            ]
        )
        history_alert_payload = _fetch_manager_payload_any(
            [
                (
                    "/api/v1/alerts",
                    {
                        "page": 1,
                        "page_size": 1000,
                        "from": start.isoformat().replace("+00:00", "Z"),
                        "to": now.isoformat().replace("+00:00", "Z"),
                    },
                ),
                ("/api/v1/alerts/history", {"range": "24h", "page": 1, "page_size": 1000}),
            ]
        )
    except ManagerError as e:
        return jsonify({"code": e.status, "message": e.message, "error_code": e.code}), e.status

    monitors = _normalize_items(monitor_payload)
    current_alerts = _normalize_items(current_alert_payload)
    history_alerts = _normalize_items(history_alert_payload)

    total_monitors = _safe_total(monitor_payload, monitors)
    healthy_monitors = sum(1 for item in monitors if _monitor_is_healthy(item))
    unhealthy_monitors = max(total_monitors - healthy_monitors, 0)
    open_alerts = _safe_total(current_alert_payload, current_alerts)

    success_rate = round((healthy_monitors / total_monitors * 100), 2) if total_monitors > 0 else 100.0
    success_rate_trend = _hourly_alert_trend(history_alerts)
    for item in success_rate_trend:
        item["value"] = success_rate

    data = {
        "overview": {
            "total_monitors": total_monitors,
            "healthy_monitors": healthy_monitors,
            "unhealthy_monitors": unhealthy_monitors,
            "open_alerts": open_alerts,
        },
        "status_distribution": [
            {"name": "正常", "value": healthy_monitors},
            {"name": "异常", "value": unhealthy_monitors},
        ],
        "alert_trend": _hourly_alert_trend(history_alerts),
        "success_rate_trend": success_rate_trend,
        "top_alert_monitors": _top_alert_monitors(current_alerts),
        "recent_alerts": current_alerts[:5],
    }
    return jsonify({"code": 200, "data": data})


@monitoring_target_bp.route("/collectors", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:collector", "monitoring:collector:view")
def list_collectors():
    return _manager_call(
        "GET",
        "/api/v1/collectors",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/collectors/<collector_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:collector:delete", "monitoring:collector")
def delete_collector(collector_id: str):
    return _manager_call("DELETE", f"/api/v1/collectors/{collector_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/collectors/<collector_id>/offline", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:collector:offline", "monitoring:collector:manage")
def offline_collector(collector_id: str):
    """下线 Collector（踢出）并重新平衡任务"""
    return _manager_call("POST", f"/api/v1/collectors/{collector_id}/offline", params=request.args.to_dict())


@monitoring_target_bp.route("/collectors/<collector_id>/monitors", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:collector:view", "monitoring:collector")
def get_collector_monitors(collector_id: str):
    """获取 Collector 绑定的 Monitor 列表"""
    return _manager_call(
        "GET",
        f"/api/v1/collectors/{collector_id}/monitors",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/labels", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:labels", "monitoring:labels:view")
def list_labels():
    return _manager_call(
        "GET",
        "/api/v1/labels",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/labels", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:labels:create", "monitoring:labels")
def create_label():
    return _manager_call("POST", "/api/v1/labels", payload=request.get_json() or {})


@monitoring_target_bp.route("/labels/<label_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:labels:edit", "monitoring:labels")
def update_label(label_id: str):
    return _manager_call("PUT", f"/api/v1/labels/{label_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/labels/<label_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:labels:delete", "monitoring:labels")
def delete_label(label_id: str):
    return _manager_call("DELETE", f"/api/v1/labels/{label_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/status-pages", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:status", "monitoring:status:view")
def list_status_pages():
    return _manager_call(
        "GET",
        "/api/v1/status-pages",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/status-pages", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:status:create", "monitoring:status")
def create_status_page():
    return _manager_call("POST", "/api/v1/status-pages", payload=request.get_json() or {})


@monitoring_target_bp.route("/status-pages/<status_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:status:edit", "monitoring:status")
def update_status_page(status_id: str):
    return _manager_call("PUT", f"/api/v1/status-pages/{status_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/status-pages/<status_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:status:delete", "monitoring:status")
def delete_status_page(status_id: str):
    return _manager_call("DELETE", f"/api/v1/status-pages/{status_id}", params=request.args.to_dict())
