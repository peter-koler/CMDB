from __future__ import annotations

from typing import Callable

from app.models import AlertDefine, AlertNotification
from app.services.alert_query_service import extract_rule_id


def resolve_rule_for_alert(
    alert_id: int,
    *,
    labels: dict,
    annotations: dict,
    json_load: Callable[[str | None, dict], dict],
    monitor_payload_loader: Callable[[int], dict],
    rule_match_monitor: Callable[[AlertDefine, dict], bool],
) -> tuple[AlertDefine | None, str | None]:
    if not isinstance(labels, dict):
        labels = {}
    if not isinstance(annotations, dict):
        annotations = {}

    rule_id = extract_rule_id(labels, annotations)
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
        monitor = monitor_payload_loader(monitor_id)
        for row_rule in AlertDefine.query.order_by(AlertDefine.updated_at.desc(), AlertDefine.id.desc()).all():
            if not rule_match_monitor(row_rule, monitor):
                continue
            rule_labels = json_load(row_rule.labels_json, {})
            rule_annotations = json_load(row_rule.annotations_json, {})
            rule_metric = str(rule_labels.get("metric") or rule_annotations.get("metric") or "").strip()
            if alert_metric and rule_metric and alert_metric != rule_metric:
                continue
            rule = row_rule
            matched_by = "heuristic"
            break

    return rule, matched_by
