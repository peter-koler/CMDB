from __future__ import annotations

import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.models.cmdb_topology_template import CmdbTopologyTemplate
from app.utils.auth import token_required
from app.utils.decorators import log_operation


cmdb_topology_template_bp = Blueprint("cmdb_topology_template", __name__, url_prefix="/api/v1/cmdb/topology-templates")


def _operator_id():
    current_user = getattr(request, "current_user", None)
    if not current_user:
        return None
    try:
        value = int(getattr(current_user, "id", 0))
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _normalize_query_text(value):
    return str(value or "").strip()


def _validate_payload(payload: dict):
    name = _normalize_query_text(payload.get("name"))
    if not name:
        return "模板名称不能为空"
    return None


@cmdb_topology_template_bp.route("", methods=["GET"])
@token_required
def list_topology_templates():
    keyword = _normalize_query_text(request.args.get("keyword"))

    query = CmdbTopologyTemplate.query
    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            db.or_(
                CmdbTopologyTemplate.name.ilike(like_keyword),
                CmdbTopologyTemplate.description.ilike(like_keyword),
            )
        )

    rows = query.order_by(CmdbTopologyTemplate.updated_at.desc(), CmdbTopologyTemplate.id.desc()).all()
    return jsonify({"code": 200, "message": "success", "data": {"items": [row.to_dict() for row in rows], "total": len(rows)}})


@cmdb_topology_template_bp.route("/<string:template_id>", methods=["GET"])
@token_required
def get_topology_template(template_id: str):
    row = CmdbTopologyTemplate.query.get(template_id)
    if not row:
        return jsonify({"code": 404, "message": "模板不存在"}), 404
    return jsonify({"code": 200, "message": "success", "data": row.to_dict()})


@cmdb_topology_template_bp.route("", methods=["POST"])
@token_required
@log_operation(operation_type="CREATE", operation_object="cmdb_topology_template")
def create_topology_template():
    payload = request.get_json() or {}
    err = _validate_payload(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400

    row = CmdbTopologyTemplate(
        id=str(payload.get("id") or f"tpl-{uuid.uuid4().hex[:16]}"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    row.apply_payload(payload, _operator_id())

    if CmdbTopologyTemplate.query.get(row.id):
        return jsonify({"code": 409, "message": "模板ID已存在"}), 409

    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "message": "创建成功", "data": row.to_dict()})


@cmdb_topology_template_bp.route("/<string:template_id>", methods=["PUT"])
@token_required
@log_operation(operation_type="UPDATE", operation_object="cmdb_topology_template")
def update_topology_template(template_id: str):
    row = CmdbTopologyTemplate.query.get(template_id)
    if not row:
        return jsonify({"code": 404, "message": "模板不存在"}), 404

    payload = request.get_json() or {}
    err = _validate_payload(payload)
    if err:
        return jsonify({"code": 400, "message": err}), 400

    row.apply_payload(payload, _operator_id())
    row.updated_at = datetime.now()
    db.session.commit()

    return jsonify({"code": 200, "message": "更新成功", "data": row.to_dict()})


@cmdb_topology_template_bp.route("/<string:template_id>", methods=["DELETE"])
@token_required
@log_operation(operation_type="DELETE", operation_object="cmdb_topology_template")
def delete_topology_template(template_id: str):
    row = CmdbTopologyTemplate.query.get(template_id)
    if not row:
        return jsonify({"code": 404, "message": "模板不存在"}), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify({"code": 200, "message": "删除成功"})


@cmdb_topology_template_bp.route("/<string:template_id>/clone", methods=["POST"])
@token_required
@log_operation(operation_type="CREATE", operation_object="cmdb_topology_template")
def clone_topology_template(template_id: str):
    source = CmdbTopologyTemplate.query.get(template_id)
    if not source:
        return jsonify({"code": 404, "message": "模板不存在"}), 404

    payload = source.to_dict()
    payload["id"] = f"tpl-{uuid.uuid4().hex[:16]}"
    payload["name"] = f"{source.name}-副本"

    row = CmdbTopologyTemplate(id=payload["id"], created_at=datetime.now(), updated_at=datetime.now())
    row.apply_payload(payload, _operator_id())

    db.session.add(row)
    db.session.commit()
    return jsonify({"code": 200, "message": "复制成功", "data": row.to_dict()})
