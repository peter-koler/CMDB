from functools import wraps
from datetime import datetime, timedelta, timezone
import json

from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

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
    AlertNotification,
    AlertTimelineEvent,
    NoticeRule,
)
from app.notifications.websocket import socketio
from app.services.alert_timeline_service import (
    append_base_events,
    append_closed_event,
    append_escalation_events,
    append_notification_events,
    finalize_timeline,
    record_alert_timeline_event,
    timeline_event_from_row,
)
from app.services.alert_query_service import (
    extract_alert_item,
    extract_rule_id,
    filter_alert_items,
)
from app.services.alert_notification_service import (
    list_system_notifications_for_alert,
    notification_from_model,
)
from app.services.alert_rule_match_service import resolve_rule_for_alert
from app.services.alert_action_service import (
    apply_acknowledge,
    apply_claim,
    apply_close,
    apply_delete,
)
from app.services.default_alert_policies import (
    bigdata_default_alert_rules,
    cache_default_alert_rules,
    database_default_alert_rules,
    middleware_default_alert_rules,
    os_default_alert_rules,
    server_default_alert_rules,
    service_default_alert_rules,
    webserver_default_alert_rules,
)
from app.services.manager_api_service import ManagerError, manager_api_service
from app.services.monitoring_target_helpers import (
    _apply_recovery_config_to_labels,
    _extract_notice_rule_ids,
    _extract_yaml_list_section,
    _hourly_alert_trend,
    _json_dump,
    _json_load,
    _mysql_default_alert_rules,
    _monitor_is_healthy,
    _ms_to_rfc3339,
    _normalize_escalation_config,
    _normalize_items,
    _now_ms,
    _now_naive_utc,
    _paginate_items,
    _parse_rfc3339_to_ms,
    _redis_default_alert_rules,
    _safe_total,
    _to_bool,
    _to_float,
    _to_int,
    _top_alert_monitors,
)


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
    query = Monitor.query
    if status in {"enabled", "disabled"}:
        query = query.filter(Monitor.status == (1 if status == "enabled" else 0))
    if q:
        query_term = f"%{q}%"
        query = query.filter(
            db.or_(
                Monitor.name.ilike(query_term),
                Monitor.app.ilike(query_term),
                Monitor.instance.ilike(query_term),
                Monitor.annotations_json.ilike(query_term),
            )
        )
    total = query.count()
    rows = (
        query.order_by(Monitor.updated_at.desc(), Monitor.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    monitor_ids = [row.id for row in rows]
    params_by_monitor: dict[int, dict[str, str]] = {}
    if monitor_ids:
        params_rows = MonitorParam.query.filter(MonitorParam.monitor_id.in_(monitor_ids)).all()
        for item in params_rows:
            bucket = params_by_monitor.setdefault(int(item.monitor_id), {})
            bucket[str(item.field)] = str(item.param_value or "")
    items = [_monitor_item_from_row(row, params_by_monitor=params_by_monitor) for row in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


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
    if app == "mysql":
        return _mysql_default_alert_rules()
    rules = bigdata_default_alert_rules(app)
    if rules:
        return rules
    rules = database_default_alert_rules(app)
    if rules:
        return rules
    rules = cache_default_alert_rules(app)
    if rules:
        return rules
    rules = middleware_default_alert_rules(app)
    if rules:
        return rules
    rules = webserver_default_alert_rules(app)
    if rules:
        return rules
    rules = server_default_alert_rules(app)
    if rules:
        return rules
    rules = service_default_alert_rules(app)
    if rules:
        return rules
    return os_default_alert_rules(app)


def _apply_default_rules_for_monitor(monitor_id: int, monitor: dict | None = None) -> dict:
    monitor = monitor or _monitor_payload(monitor_id)
    if not monitor:
        raise ValueError("监控任务不存在")

    app = str(monitor.get("app") or "").strip().lower()
    defaults = _load_monitor_default_alert_rules(monitor)
    if not defaults:
        raise ValueError("当前模板未配置默认告警策略")
    monitor_target = str(monitor.get("target") or "")
    existing_rows = (
        AlertDefine.query.filter(
            db.or_(
                AlertDefine.labels_json.ilike(f'%"monitor_id":{monitor_id}%'),
                AlertDefine.labels_json.ilike(f'%"monitor_id":"{monitor_id}"%'),
            )
        )
        .order_by(AlertDefine.id.asc())
        .all()
    )
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
    page, page_size = _page_args()
    has_advanced_filters = any(
        key not in {"page", "page_size", "status"} and str(value).strip()
        for key, value in request.args.items()
    )
    if not has_advanced_filters:
        total = query.count()
        rows = (
            query.order_by(SingleAlert.updated_at.desc(), SingleAlert.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
    else:
        rows = query.order_by(SingleAlert.updated_at.desc(), SingleAlert.id.desc()).all()
        total = None
    items = [
        extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
            json_load=_json_load,
            ms_to_rfc3339=_ms_to_rfc3339,
            now_ms_provider=_now_ms,
        )
        for row in rows
    ]
    items = filter_alert_items(
        items,
        query_args=request.args,
        parse_rfc3339_to_ms=_parse_rfc3339_to_ms,
    )
    if total is None:
        page_items, total = _paginate_items(items, page, page_size)
    else:
        page_items = items
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/history", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:history", "monitoring:alert:center")
def list_history_alerts():
    page, page_size = _page_args()
    has_advanced_filters = any(
        key not in {"page", "page_size"} and str(value).strip()
        for key, value in request.args.items()
    )
    query = AlertHistory.query
    if not has_advanced_filters:
        total = query.count()
        rows = (
            query.order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
    else:
        rows = query.order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc()).all()
        total = None
    items = [
        extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
            json_load=_json_load,
            ms_to_rfc3339=_ms_to_rfc3339,
            now_ms_provider=_now_ms,
        )
        for row in rows
    ]
    items = filter_alert_items(
        items,
        query_args=request.args,
        parse_rfc3339_to_ms=_parse_rfc3339_to_ms,
    )
    if total is None:
        page_items, total = _paginate_items(items, page, page_size)
    else:
        page_items = items
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/<int:alert_id>", methods=["GET"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:history", "monitoring:alert:center")
def get_alert_detail(alert_id: int):
    row = SingleAlert.query.get(alert_id)
    if row:
        labels = _json_load(row.labels_json, {})
        annotations = _json_load(row.annotations_json, {})
        item = extract_alert_item(
            row_id=row.id,
            labels_json=row.labels_json,
            annotations_json=row.annotations_json,
            content=row.content,
            status=row.status,
            start_at=row.start_at,
            end_at=row.end_at,
            created_at=row.created_at,
            json_load=_json_load,
            ms_to_rfc3339=_ms_to_rfc3339,
            now_ms_provider=_now_ms,
        )
        item["rule_id"] = extract_rule_id(labels, annotations)
        item["scope"] = "current"
        return jsonify({"code": 200, "data": item})

    history = AlertHistory.query.get(alert_id)
    if history:
        labels = _json_load(history.labels_json, {})
        annotations = _json_load(history.annotations_json, {})
        item = extract_alert_item(
            row_id=history.id,
            labels_json=history.labels_json,
            annotations_json=history.annotations_json,
            content=history.content,
            status=history.status,
            start_at=history.start_at,
            end_at=history.end_at,
            created_at=history.created_at,
            json_load=_json_load,
            ms_to_rfc3339=_ms_to_rfc3339,
            now_ms_provider=_now_ms,
        )
        item["rule_id"] = extract_rule_id(labels, annotations)
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
                items.append(
                    notification_from_model(
                        row,
                        ms_to_rfc3339=_ms_to_rfc3339,
                    )
                )
    else:
        items = [
            notification_from_model(
                row,
                ms_to_rfc3339=_ms_to_rfc3339,
            )
            for row in rows
        ]
    page, page_size = _page_args()
    if not items:
        items = list_system_notifications_for_alert(
            alert_id,
            query_args=request.args,
            parse_rfc3339_to_ms=_parse_rfc3339_to_ms,
            ms_to_rfc3339=_ms_to_rfc3339,
            json_load=_json_load,
        )
    page_items, total = _paginate_items(items, page, page_size)
    return _list_response(page_items, total, page, page_size)


@monitoring_target_bp.route("/alerts/<int:alert_id>/timeline", methods=["GET"])
@jwt_required()
@require_any_permission(
    "monitoring:alert:current",
    "monitoring:alert:my",
    "monitoring:alert:history",
    "monitoring:alert:center",
)
def list_alert_timeline(alert_id: int):
    current = SingleAlert.query.get(alert_id)
    history = None
    scope = "current"
    root_alert_id = alert_id
    if not current:
        history = AlertHistory.query.get(alert_id)
        if not history:
            return jsonify({"code": 404, "message": "告警不存在"}), 404
        scope = "history"
        root_alert_id = int(history.alert_id or alert_id)
        current = SingleAlert.query.get(root_alert_id)

    base_labels_json = current.labels_json if current else history.labels_json
    base_annotations_json = current.annotations_json if current else history.annotations_json
    base_content = current.content if current else history.content
    base_status = current.status if current else history.status
    base_start_at = current.start_at if current else history.start_at
    base_end_at = current.end_at if current else history.end_at
    base_created_at = current.created_at if current else history.created_at

    base_item = extract_alert_item(
        row_id=root_alert_id,
        labels_json=base_labels_json,
        annotations_json=base_annotations_json,
        content=base_content,
        status=base_status,
        start_at=base_start_at,
        end_at=base_end_at,
        created_at=base_created_at,
        json_load=_json_load,
        ms_to_rfc3339=_ms_to_rfc3339,
        now_ms_provider=_now_ms,
    )
    triggered_ms = _parse_rfc3339_to_ms(base_item.get("triggered_at"))

    events: list[dict] = []
    append_base_events(
        events,
        root_alert_id=root_alert_id,
        base_item=base_item,
        scope=scope,
        triggered_ms=triggered_ms,
        ms_to_rfc3339=_ms_to_rfc3339,
    )

    manual_rows = (
        AlertTimelineEvent.query.filter_by(alert_id=root_alert_id)
        .order_by(AlertTimelineEvent.created_at.desc(), AlertTimelineEvent.id.desc())
        .all()
    )
    events.extend(
        [
            timeline_event_from_row(
                row,
                ms_to_rfc3339=_ms_to_rfc3339,
            )
            for row in manual_rows
        ]
    )

    notify_rows = (
        AlertNotification.query.filter_by(alert_id=root_alert_id)
        .order_by(AlertNotification.created_at.desc(), AlertNotification.id.desc())
        .all()
    )
    append_notification_events(
        events,
        notify_rows=notify_rows,
        ms_to_rfc3339=_ms_to_rfc3339,
    )

    escalation_rows = (
        AlertHistory.query.filter_by(alert_id=root_alert_id, alert_type="single", status="firing")
        .order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc())
        .all()
    )
    append_escalation_events(
        events,
        escalation_rows=escalation_rows,
        ms_to_rfc3339=_ms_to_rfc3339,
    )

    resolved_ms = base_end_at if base_status == "resolved" else None
    append_closed_event(
        events,
        root_alert_id=root_alert_id,
        resolved_ms=resolved_ms,
        ms_to_rfc3339=_ms_to_rfc3339,
    )

    events = finalize_timeline(events)
    page, page_size = _page_args()
    page_items, total = _paginate_items(events, page, page_size)
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
    rule, matched_by = resolve_rule_for_alert(
        alert_id,
        labels=labels,
        annotations=annotations,
        json_load=_json_load,
        monitor_payload_loader=_monitor_payload,
        rule_match_monitor=_rule_match_monitor,
    )

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
    identity = get_jwt_identity()
    current_user = User.query.get(int(identity)) if identity else None
    row = apply_acknowledge(
        alert_id,
        payload=payload,
        current_username=(current_user.username if current_user else None),
        json_load=_json_load,
        json_dump=_json_dump,
        now_provider=_now_naive_utc,
        record_timeline_event=lambda **kwargs: record_alert_timeline_event(
            json_dump=_json_dump,
            now_provider=_now_naive_utc,
            **kwargs,
        ),
    )
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    response = jsonify(
        {
            "code": 200,
            "data": extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
                json_load=_json_load,
                ms_to_rfc3339=_ms_to_rfc3339,
                now_ms_provider=_now_ms,
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
    identity = get_jwt_identity()
    current_user = User.query.get(int(identity)) if identity else None
    row = apply_claim(
        alert_id,
        payload=payload,
        current_username=(current_user.username if current_user else None),
        json_load=_json_load,
        json_dump=_json_dump,
        now_provider=_now_naive_utc,
        record_timeline_event=lambda **kwargs: record_alert_timeline_event(
            json_dump=_json_dump,
            now_provider=_now_naive_utc,
            **kwargs,
        ),
    )
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    _emit_alert_event("monitoring:alert:update", {"id": alert_id, "action": "claim"})
    return jsonify(
        {
            "code": 200,
            "data": extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
                json_load=_json_load,
                ms_to_rfc3339=_ms_to_rfc3339,
                now_ms_provider=_now_ms,
            ),
        }
    )


@monitoring_target_bp.route("/alerts/<int:alert_id>/close", methods=["POST"])
@jwt_required()
@require_any_permission("monitoring:alert:current", "monitoring:alert:my", "monitoring:alert:center", "monitoring:alert:close")
def close_alert(alert_id: int):
    identity = get_jwt_identity()
    current_user = User.query.get(int(identity)) if identity else None
    row = apply_close(
        alert_id,
        operator=(current_user.username if current_user else "system"),
        now_ms_provider=_now_ms,
        now_provider=_now_naive_utc,
        record_timeline_event=lambda **kwargs: record_alert_timeline_event(
            json_dump=_json_dump,
            now_provider=_now_naive_utc,
            **kwargs,
        ),
    )
    if not row:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    response = jsonify(
        {
            "code": 200,
            "data": extract_alert_item(
                row_id=row.id,
                labels_json=row.labels_json,
                annotations_json=row.annotations_json,
                content=row.content,
                status=row.status,
                start_at=row.start_at,
                end_at=row.end_at,
                created_at=row.created_at,
                json_load=_json_load,
                ms_to_rfc3339=_ms_to_rfc3339,
                now_ms_provider=_now_ms,
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
    result = apply_delete(alert_id, scope=scope)
    if not result:
        return jsonify({"code": 404, "message": "告警不存在"}), 404
    _emit_alert_event(
        "monitoring:alert:update",
        {"id": alert_id, "action": "delete", "scope": scope or "all"},
    )
    return jsonify({"code": 200, "data": result})


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
