from functools import wraps
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
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
        if fallback is not None and e.status == 404:
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
    return _manager_call("GET", "/api/v1/alerts", params=request.args.to_dict(), fallback=lambda: {"items": [], "total": 0})


@monitoring_target_bp.route("/alerts/current", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:center")
def list_current_alerts():
    params = request.args.to_dict()
    params.setdefault("scope", "current")
    return _manager_call("GET", "/api/v1/alerts", params=params, fallback=lambda: {"items": [], "total": 0})


@monitoring_target_bp.route("/alerts/history", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:history", "monitoring:alert:center")
def list_history_alerts():
    return _manager_call(
        "GET",
        "/api/v1/alerts/history",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:update", "monitoring:alert:center", "monitoring:alert:current")
def acknowledge_alert(alert_id: int):
    response = _manager_call(
        "POST",
        f"/api/v1/alerts/{alert_id}/acknowledge",
        payload=request.get_json() or {},
    )
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "acknowledge"})
    return response


@monitoring_target_bp.route("/alerts/<int:alert_id>/claim", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:center", "monitoring:alert:claim")
def claim_alert(alert_id: int):
    payload = request.get_json() or {}
    try:
        data = manager_api_service.request(
            method="POST",
            path=f"/api/v1/alerts/{alert_id}/claim",
            payload=payload,
            auth_header=_auth_header(),
        )
    except ManagerError as e:
        if e.status == 404:
            return acknowledge_alert(alert_id)
        return jsonify({"code": e.status, "message": e.message, "error_code": e.code}), e.status
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "claim"})
    return jsonify({"code": 200, "data": data})


@monitoring_target_bp.route("/alerts/<int:alert_id>/close", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:center", "monitoring:alert:close")
def close_alert(alert_id: int):
    response = _manager_call(
        "POST",
        f"/api/v1/alerts/{alert_id}/close",
        payload=request.get_json() or {},
    )
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "close"})
    return response


@monitoring_target_bp.route("/alert-rules", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def list_alert_rules():
    return _manager_call(
        "GET",
        "/api/v1/alert-rules",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-rules", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def create_alert_rule():
    return _manager_call("POST", "/api/v1/alert-rules", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def update_alert_rule(rule_id: int):
    return _manager_call("PUT", f"/api/v1/alert-rules/{rule_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def delete_alert_rule(rule_id: int):
    return _manager_call("DELETE", f"/api/v1/alert-rules/{rule_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-rules/<int:rule_id>/enable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def enable_alert_rule(rule_id: int):
    return _manager_call("PATCH", f"/api/v1/alert-rules/{rule_id}/enable", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-rules/<int:rule_id>/disable", methods=["PATCH"])
@jwt_required()
@require_any_permission("monitoring:alert:rule", "monitoring:alert:setting")
def disable_alert_rule(rule_id: int):
    return _manager_call("PATCH", f"/api/v1/alert-rules/{rule_id}/disable", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-integrations", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:view")
def list_alert_integrations():
    return _manager_call(
        "GET",
        "/api/v1/alert-integrations",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-integrations", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:create")
def create_alert_integration():
    return _manager_call("POST", "/api/v1/alert-integrations", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-integrations/<integration_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:edit")
def update_alert_integration(integration_id: str):
    return _manager_call("PUT", f"/api/v1/alert-integrations/{integration_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-integrations/<integration_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:delete")
def delete_alert_integration(integration_id: str):
    return _manager_call("DELETE", f"/api/v1/alert-integrations/{integration_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-integrations/<integration_id>/test", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:integration", "monitoring:alert:integration:test")
def test_alert_integration(integration_id: str):
    return _manager_call("POST", f"/api/v1/alert-integrations/{integration_id}/test", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-groups", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:view")
def list_alert_groups():
    return _manager_call(
        "GET",
        "/api/v1/alert-groups",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-groups", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:create")
def create_alert_group():
    return _manager_call("POST", "/api/v1/alert-groups", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-groups/<group_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:edit")
def update_alert_group(group_id: str):
    return _manager_call("PUT", f"/api/v1/alert-groups/{group_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-groups/<group_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:group", "monitoring:alert:group:delete")
def delete_alert_group(group_id: str):
    return _manager_call("DELETE", f"/api/v1/alert-groups/{group_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-inhibits", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:view")
def list_alert_inhibits():
    return _manager_call(
        "GET",
        "/api/v1/alert-inhibits",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-inhibits", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:create")
def create_alert_inhibit():
    return _manager_call("POST", "/api/v1/alert-inhibits", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-inhibits/<inhibit_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:edit")
def update_alert_inhibit(inhibit_id: str):
    return _manager_call("PUT", f"/api/v1/alert-inhibits/{inhibit_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-inhibits/<inhibit_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:inhibit", "monitoring:alert:inhibit:delete")
def delete_alert_inhibit(inhibit_id: str):
    return _manager_call("DELETE", f"/api/v1/alert-inhibits/{inhibit_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-silences", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:view")
def list_alert_silences():
    return _manager_call(
        "GET",
        "/api/v1/alert-silences",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-silences", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:create")
def create_alert_silence():
    return _manager_call("POST", "/api/v1/alert-silences", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-silences/<silence_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:edit")
def update_alert_silence(silence_id: str):
    return _manager_call("PUT", f"/api/v1/alert-silences/{silence_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-silences/<silence_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:silence", "monitoring:alert:silence:delete")
def delete_alert_silence(silence_id: str):
    return _manager_call("DELETE", f"/api/v1/alert-silences/{silence_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-notices", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:view")
def list_alert_notices():
    return _manager_call(
        "GET",
        "/api/v1/alert-notices",
        params=request.args.to_dict(),
        fallback=lambda: {"items": [], "total": 0},
    )


@monitoring_target_bp.route("/alert-notices", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:create")
def create_alert_notice():
    return _manager_call("POST", "/api/v1/alert-notices", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-notices/<notice_id>", methods=["PUT"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:edit")
def update_alert_notice(notice_id: str):
    return _manager_call("PUT", f"/api/v1/alert-notices/{notice_id}", payload=request.get_json() or {})


@monitoring_target_bp.route("/alert-notices/<notice_id>", methods=["DELETE"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:delete")
def delete_alert_notice(notice_id: str):
    return _manager_call("DELETE", f"/api/v1/alert-notices/{notice_id}", params=request.args.to_dict())


@monitoring_target_bp.route("/alert-notices/<notice_id>/test", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:notice", "monitoring:alert:notice:test")
def test_alert_notice(notice_id: str):
    return _manager_call("POST", f"/api/v1/alert-notices/{notice_id}/test", payload=request.get_json() or {})


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
