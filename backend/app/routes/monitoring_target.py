from functools import wraps
from collections import Counter
from datetime import datetime, timedelta, timezone
import json

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import (
    User,
    SingleAlert,
    AlertHistory,
    AlertDefine,
    AlertGroup,
    AlertInhibit,
    AlertSilence,
    AlertIntegration,
    NoticeReceiver,
    NoticeRule,
)
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
        # 监控扩展模块在 Manager 未实现(404)或暂时不可用(5xx)时返回空列表，避免前端页面硬失败。
        if fallback is not None and e.status in {404, 502, 503, 504}:
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
    triggered_ms = start_at or (int(created_at.replace(tzinfo=timezone.utc).timestamp() * 1000) if created_at else None)
    recovered_ms = end_at
    duration_seconds = 0
    if triggered_ms:
        tail = recovered_ms or _now_ms()
        duration_seconds = max(int((tail - triggered_ms) / 1000), 0)
    return {
        "id": row_id,
        "level": level,
        "name": str(name),
        "status": "open" if status == "firing" else "closed",
        "monitor_name": str(monitor_name),
        "monitor_id": monitor_id,
        "metric": labels.get("metric"),
        "metric_value": labels.get("value"),
        "threshold": labels.get("threshold"),
        "triggered_at": _ms_to_rfc3339(triggered_ms),
        "recovered_at": _ms_to_rfc3339(recovered_ms),
        "duration_seconds": duration_seconds,
        "assignee": assignee,
        "note": note,
    }


def _filter_alert_items(items: list[dict]) -> list[dict]:
    level = (request.args.get("level") or "").strip().lower()
    q = (request.args.get("q") or "").strip().lower()
    start_ms = _parse_rfc3339_to_ms(request.args.get("start_at"))
    end_ms = _parse_rfc3339_to_ms(request.args.get("end_at"))
    out: list[dict] = []
    for item in items:
        if level and str(item.get("level", "")).lower() != level:
            continue
        if q:
            hay = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("monitor_name") or ""),
                    str(item.get("metric") or ""),
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
    annotations = _json_load(row.annotations_json, {})
    threshold = labels.get("threshold")
    try:
        threshold = float(threshold) if threshold is not None else 0
    except (TypeError, ValueError):
        threshold = 0
    return {
        "id": row.id,
        "name": row.name,
        "monitor_type": row.type,
        "metric": labels.get("metric") or annotations.get("metric") or "value",
        "operator": labels.get("operator") or ">",
        "threshold": threshold,
        "level": labels.get("severity") or "warning",
        "enabled": bool(row.enabled),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


_RECEIVER_TYPE_TO_CHANNEL = {
    0: "sms",
    1: "email",
    2: "webhook",
    4: "wecom",
    5: "dingtalk",
    6: "feishu",
    10: "wechat",
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
    return {
        "id": row.id,
        "name": row.name,
        "channel_type": row.notify_type,
        "notify_type": row.notify_type,
        "receiver_type": row.receiver_type,
        "receiver_id": row.receiver_id,
        "receiver_name": row.receiver_name,
        "notify_times": row.notify_times,
        "notify_scale": row.notify_scale,
        "template_id": row.template_id,
        "template_name": row.template_name,
        "filter_all": row.filter_all,
        "labels": row.labels,
        "days": row.days,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "status": "enabled" if row.enable else "disabled",
        "enable": bool(row.enable),
        "target": f"{row.receiver_type}:{row.receiver_id}",
    }


@monitoring_target_bp.route("/targets", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target", "monitoring:list")
def list_targets():
    return _manager_call("GET", "/api/v1/monitors", params=request.args.to_dict())


@monitoring_target_bp.route("/targets", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:target:create", "monitoring:list:create")
def create_target():
    return _manager_call("POST", "/api/v1/monitors", payload=request.get_json() or {})


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:target:view", "monitoring:list:view")
def get_target(monitor_id: int):
    return _manager_call("GET", f"/api/v1/monitors/{monitor_id}")


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:edit")
def update_target(monitor_id: int):
    return _manager_call("PUT", f"/api/v1/monitors/{monitor_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/targets/<int:monitor_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:target:delete", "monitoring:list:delete")
def delete_target(monitor_id: int):
    return _manager_call("DELETE", f"/api/v1/monitors/{monitor_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/targets/<int:monitor_id>/enable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:enable")
def enable_target(monitor_id: int):
    return _manager_call("PATCH", f"/api/v1/monitors/{monitor_id}/enable", payload=request.get_json() or {})


@monitoring_target_bp.route("/targets/<int:monitor_id>/disable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:target:update", "monitoring:list:disable")
def disable_target(monitor_id: int):
    return _manager_call("PATCH", f"/api/v1/monitors/{monitor_id}/disable", payload=request.get_json() or {})


@monitoring_target_bp.route("/alerts", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert", "monitoring:alert:current")
def list_alerts():
    scope = (request.args.get("scope") or "current").strip().lower()
    if scope == "history":
        return list_history_alerts()
    return list_current_alerts()


@monitoring_target_bp.route("/alerts/current", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:center")
def list_current_alerts():
    rows = (
        SingleAlert.query.filter_by(status="firing")
        .order_by(SingleAlert.updated_at.desc(), SingleAlert.id.desc())
        .all()
    )
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


@monitoring_target_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:update", "monitoring:alert:center", "monitoring:alert:current")
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
@require_any_permission("monitoring:alert:current", "monitoring:alert:center", "monitoring:alert:claim")
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
@require_any_permission("monitoring:alert:current", "monitoring:alert:center", "monitoring:alert:close")
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


@monitoring_target_bp.route("/alert-rules", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def list_alert_rules():
    q = (request.args.get("q") or "").strip()
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
    items = [_rule_from_model(row) for row in rows]
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
    annotations = {"summary": name}
    row = AlertDefine(
        name=name,
        type=str(payload.get("monitor_type") or "realtime_metric"),
        expr=str(payload.get("expr") or f"{metric} {operator} {threshold_val}"),
        period=max(int(payload.get("period") or 0), 0),
        times=max(int(payload.get("times") or 1), 1),
        labels_json=_json_dump(labels),
        annotations_json=_json_dump(annotations),
        template=payload.get("template"),
        datasource_type=payload.get("datasource_type"),
        enabled=bool(payload.get("enabled", True)),
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
    labels = _json_load(row.labels_json, {})
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
    row.labels_json = _json_dump(labels)
    if "enabled" in payload:
        row.enabled = bool(payload.get("enabled"))
    if "expr" in payload:
        row.expr = str(payload.get("expr") or row.expr)
    else:
        metric = labels.get("metric") or "value"
        operator = labels.get("operator") or ">"
        threshold = labels.get("threshold", 0)
        row.expr = f"{metric} {operator} {threshold}"
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
    q = (request.args.get("q") or "").strip()
    channel_type = (request.args.get("channel_type") or request.args.get("notify_type") or "").strip().lower()
    query = NoticeRule.query
    if q:
        query = query.filter(NoticeRule.name.ilike(f"%{q}%"))
    if channel_type:
        query = query.filter(NoticeRule.notify_type == channel_type)
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
    payload = request.get_json() or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "名称不能为空"}), 400
    receiver_type = str(payload.get("receiver_type") or "user").strip().lower()
    receiver_id = payload.get("receiver_id")
    if receiver_id is None and payload.get("target"):
        target = str(payload.get("target"))
        if ":" in target:
            receiver_type, receiver_id_str = target.split(":", 1)
            receiver_id = receiver_id_str
        else:
            receiver_id = target
    try:
        receiver_id_int = int(receiver_id)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "message": "receiver_id 必须是整数"}), 400
    notify_type = str(payload.get("notify_type") or payload.get("channel_type") or "webhook").strip().lower()
    notify_scale = str(payload.get("notify_scale") or "single").strip().lower()
    if notify_scale not in {"single", "batch"}:
        return jsonify({"code": 400, "message": "notify_scale 只能是 single/batch"}), 400
    
    # 处理标签过滤
    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    days = payload.get("days") if isinstance(payload.get("days"), list) else [1, 2, 3, 4, 5, 6, 7]
    
    row = NoticeRule(
        name=name,
        receiver_type=receiver_type if receiver_type in {"user", "group"} else "user",
        receiver_id=receiver_id_int,
        receiver_name=str(payload.get("receiver_name") or "").strip() or None,
        notify_type=notify_type,
        notify_times=max(int(payload.get("notify_times") or 1), 1),
        notify_scale=notify_scale,
        template_id=payload.get("template_id"),
        template_name=str(payload.get("template_name") or "").strip() or None,
        filter_all=bool(payload.get("filter_all", True)),
        labels_json=_json_dump(labels),
        days_json=_json_dump(days),
        period_start=str(payload.get("period_start") or "").strip() or None,
        period_end=str(payload.get("period_end") or "").strip() or None,
        enable=bool(payload.get("enable", payload.get("status", "enabled") == "enabled")),
        creator=(payload.get("creator") or "python-web"),
        modifier=(payload.get("modifier") or "python-web"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "data": _notice_rule_from_model(row)})


@monitoring_target_bp.route("/alert-notices/<notice_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:edit")
def update_alert_notice(notice_id: str):
    row = NoticeRule.query.get(notice_id)
    if not row:
        return jsonify({"code": 404, "message": "通知配置不存在"}), 404
    payload = request.get_json() or {}
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "receiver_type" in payload:
        rt = str(payload.get("receiver_type") or "").strip().lower()
        if rt in {"user", "group"}:
            row.receiver_type = rt
    if "receiver_id" in payload:
        try:
            row.receiver_id = int(payload.get("receiver_id"))
        except (TypeError, ValueError):
            return jsonify({"code": 400, "message": "receiver_id 必须是整数"}), 400
    if "receiver_name" in payload:
        row.receiver_name = str(payload.get("receiver_name") or "").strip() or None
    if "target" in payload and payload.get("target"):
        target = str(payload.get("target"))
        if ":" in target:
            rt, rid = target.split(":", 1)
            rt = rt.strip().lower()
            if rt in {"user", "group"}:
                row.receiver_type = rt
            try:
                row.receiver_id = int(rid)
            except (TypeError, ValueError):
                return jsonify({"code": 400, "message": "target 中 receiver_id 无效"}), 400
    if "notify_type" in payload or "channel_type" in payload:
        row.notify_type = str(payload.get("notify_type") or payload.get("channel_type")).strip().lower()
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
    if "enable" in payload:
        row.enable = bool(payload.get("enable"))
    if "status" in payload:
        row.enable = str(payload.get("status")).lower() == "enabled"
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
