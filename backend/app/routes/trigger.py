"""
触发器 API 路由
提供触发器管理和批量扫描相关接口
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.cmdb_relation import (
    RelationTrigger,
    TriggerExecutionLog,
    BatchScanTask,
)
from app.models.cmdb_model import CmdbModel
from app.tasks.batch_scan import (
    batch_scan_model,
    get_model_scan_tasks,
    get_all_scan_tasks,
)
from app.tasks.scheduler import add_batch_scan_job, remove_batch_scan_job
import json
import logging

logger = logging.getLogger(__name__)

trigger_bp = Blueprint("trigger", __name__, url_prefix="/api/v1")


@trigger_bp.route("/models/<int:model_id>/triggers", methods=["GET"])
@jwt_required()
def get_triggers(model_id):
    """获取模型的触发器列表"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    triggers = RelationTrigger.query.filter_by(source_model_id=model_id).all()
    return jsonify({"code": 200, "message": "success", "data": [t.to_dict() for t in triggers]})


@trigger_bp.route("/models/<int:model_id>/triggers", methods=["POST"])
@jwt_required()
def create_trigger(model_id):
    """创建触发器"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    data = request.get_json()

    required_fields = [
        "name",
        "target_model_id",
        "relation_type_id",
        "trigger_condition",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"code": 400, "message": f"缺少必填字段: {field}"}), 400

    trigger = RelationTrigger(
        name=data["name"],
        source_model_id=model_id,
        target_model_id=data["target_model_id"],
        relation_type_id=data["relation_type_id"],
        trigger_type=data.get("trigger_type", "reference"),
        trigger_condition=json.dumps(data["trigger_condition"]),
        is_active=data.get("is_active", True),
        description=data.get("description"),
    )

    db.session.add(trigger)
    db.session.commit()

    return jsonify({"code": 201, "message": "success", "data": trigger.to_dict()}), 201


@trigger_bp.route("/triggers/<int:trigger_id>", methods=["GET"])
@jwt_required()
def get_trigger(trigger_id):
    """获取触发器详情"""
    trigger = RelationTrigger.query.get(trigger_id)
    if not trigger:
        return jsonify({"code": 404, "message": "触发器不存在"}), 404

    return jsonify({"code": 200, "message": "success", "data": trigger.to_dict()})


@trigger_bp.route("/triggers/<int:trigger_id>", methods=["PUT"])
@jwt_required()
def update_trigger(trigger_id):
    """更新触发器"""
    trigger = RelationTrigger.query.get(trigger_id)
    if not trigger:
        return jsonify({"code": 404, "message": "触发器不存在"}), 404

    data = request.get_json()

    if "name" in data:
        trigger.name = data["name"]
    if "trigger_condition" in data:
        trigger.trigger_condition = json.dumps(data["trigger_condition"])
    if "is_active" in data:
        trigger.is_active = data["is_active"]
    if "description" in data:
        trigger.description = data["description"]

    db.session.commit()

    return jsonify({"code": 200, "message": "success", "data": trigger.to_dict()})


@trigger_bp.route("/triggers/<int:trigger_id>", methods=["DELETE"])
@jwt_required()
def delete_trigger(trigger_id):
    """删除触发器"""
    trigger = RelationTrigger.query.get(trigger_id)
    if not trigger:
        return jsonify({"code": 404, "message": "触发器不存在"}), 404

    db.session.delete(trigger)
    db.session.commit()

    return jsonify({"code": 200, "message": "success"})


@trigger_bp.route("/triggers/<int:trigger_id>/logs", methods=["GET"])
@jwt_required()
def get_trigger_logs(trigger_id):
    """获取触发器执行日志"""
    trigger = RelationTrigger.query.get(trigger_id)
    if not trigger:
        return jsonify({"code": 404, "message": "触发器不存在"}), 404

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    status = request.args.get("status")

    query = TriggerExecutionLog.query.filter_by(trigger_id=trigger_id)

    if status:
        query = query.filter_by(status=status)

    total = query.count()
    logs = (
        query.order_by(TriggerExecutionLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": [log.to_dict() for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@trigger_bp.route("/models/<int:model_id>/batch-scan", methods=["POST"])
@jwt_required()
def trigger_batch_scan(model_id):
    """触发批量扫描"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    from threading import Thread

    user_id = get_jwt_identity()
    app = current_app._get_current_object()

    def run():
        with app.app_context():
            batch_scan_model(model_id, "manual", int(user_id))

    thread = Thread(target=run)
    thread.daemon = True
    thread.start()

    return jsonify({"code": 202, "message": "任务已触发"}), 202


@trigger_bp.route("/models/<int:model_id>/batch-scan", methods=["GET"])
@jwt_required()
def get_model_batch_scan_tasks(model_id):
    """获取模型的批量扫描任务列表"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    status = request.args.get("status")
    tasks = get_model_scan_tasks(model_id, status=status)

    return jsonify({"code": 200, "message": "success", "data": [task.to_dict() for task in tasks]})


@trigger_bp.route("/batch-scan/tasks", methods=["GET"])
@jwt_required()
def get_all_batch_scan_tasks():
    """获取所有批量扫描任务历史"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    model_id = request.args.get("model_id", type=int)
    status = request.args.get("status")
    trigger_source = request.args.get("trigger_source")

    tasks, total = get_all_scan_tasks(
        page=page,
        page_size=page_size,
        model_id=model_id,
        status=status,
        trigger_source=trigger_source,
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": [task.to_dict() for task in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@trigger_bp.route("/batch-scan/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_batch_scan_task(task_id):
    """获取批量扫描任务详情"""
    task = BatchScanTask.query.get(task_id)
    if not task:
        return jsonify({"code": 404, "message": "任务不存在"}), 404

    return jsonify({"code": 200, "message": "success", "data": task.to_dict()})


@trigger_bp.route("/batch-scan/config/<int:model_id>", methods=["GET"])
@jwt_required()
def get_batch_scan_config(model_id):
    """获取模型批量扫描配置"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    config = model.get_config()

    from app.tasks.scheduler import get_scheduled_jobs

    scheduled_jobs = get_scheduled_jobs()

    next_run_at = None
    for job in scheduled_jobs:
        if job["model_id"] == model_id:
            next_run_at = job["next_run_time"]
            break

    last_task = (
        BatchScanTask.query.filter_by(model_id=model_id)
        .order_by(BatchScanTask.created_at.desc())
        .first()
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "model_id": model_id,
                "model_name": model.name,
                "batch_scan_enabled": config.get("batch_scan_enabled", False),
                "batch_scan_cron": config.get("batch_scan_cron", ""),
                "next_run_at": next_run_at,
                "last_run_at": last_task.created_at.isoformat()
                if last_task and last_task.completed_at
                else None,
                "last_run_status": last_task.status if last_task else "none",
            }
        }
    )


@trigger_bp.route("/batch-scan/config/<int:model_id>", methods=["PUT"])
@jwt_required()
def update_batch_scan_config(model_id):
    """更新模型批量扫描配置"""
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404

    data = request.get_json()

    config = model.get_config()

    if "batch_scan_enabled" in data:
        config["batch_scan_enabled"] = data["batch_scan_enabled"]

    if "batch_scan_cron" in data:
        cron = data["batch_scan_cron"]
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(cron)
            config["batch_scan_cron"] = cron
        except Exception as e:
            return jsonify({"code": 400, "message": f"无效的 Cron 表达式: {e}"}), 400

    model.set_config(config)
    db.session.commit()

    if config.get("batch_scan_enabled"):
        add_batch_scan_job(model_id, config.get("batch_scan_cron", "0 2 * * *"))
    else:
        remove_batch_scan_job(model_id)

    return get_batch_scan_config(model_id)
