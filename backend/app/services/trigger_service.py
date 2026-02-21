"""
触发器服务模块
处理 CI 触发器匹配和关系自动创建
"""

import json
import logging
from typing import Optional
from threading import Thread
from flask import current_app

from app import db
from app.models.cmdb_relation import (
    RelationTrigger,
    TriggerExecutionLog,
    CmdbRelation,
)
from app.models.ci_instance import CiInstance
from app.services.relation_service import (
    create_relation_with_validation,
    RelationServiceError,
)

logger = logging.getLogger(__name__)


def log_trigger_execution(
    trigger_id: int,
    source_ci_id: int,
    target_ci_id: Optional[int],
    status: str,
    message: str = "",
) -> TriggerExecutionLog:
    """
    记录触发器执行日志

    Args:
        trigger_id: 触发器 ID
        source_ci_id: 源 CI ID
        target_ci_id: 目标 CI ID（可为空）
        status: 状态 (success/failed/skipped)
        message: 执行消息

    Returns:
        TriggerExecutionLog: 日志记录
    """
    log = TriggerExecutionLog(
        trigger_id=trigger_id,
        source_ci_id=source_ci_id,
        target_ci_id=target_ci_id,
        status=status,
        message=message,
    )
    db.session.add(log)
    db.session.commit()
    return log


def get_matching_triggers(ci: CiInstance) -> list:
    """
    获取匹配 CI 的触发器列表

    Args:
        ci: CI 实例

    Returns:
        list: 匹配的触发器列表
    """
    triggers = RelationTrigger.query.filter(
        RelationTrigger.source_model_id == ci.model_id,
        RelationTrigger.is_active.is_(True),
    ).all()

    return triggers


def match_trigger_condition(ci: CiInstance, trigger: RelationTrigger) -> list:
    """
    精确值匹配触发条件，查找目标 CI

    Args:
        ci: 源 CI 实例
        trigger: 触发器

    Returns:
        list: 匹配的目标 CI 列表
    """
    try:
        condition = (
            json.loads(trigger.trigger_condition) if trigger.trigger_condition else {}
        )
        source_field = condition.get("source_field")
        target_field = condition.get("target_field")

        if not source_field or not target_field:
            logger.warning(f"触发器 {trigger.id} 条件不完整")
            return []

        ci_attrs = ci.get_attribute_values()
        source_value = ci_attrs.get(source_field)

        if source_value is None:
            return []

        target_cis = CiInstance.query.filter_by(model_id=trigger.target_model_id).all()

        matched = []
        for target_ci in target_cis:
            target_attrs = target_ci.get_attribute_values()
            target_value = target_attrs.get(target_field)

            if target_value is not None and str(target_value) == str(source_value):
                matched.append(target_ci)

        return matched
    except Exception as e:
        logger.error(f"匹配触发器条件失败: {e}")
        return []


def create_relation_with_skip_duplicate(
    source_ci_id: int, target_ci_id: int, relation_type_id: int
) -> tuple:
    """
    创建关系，如果已存在则跳过

    Args:
        source_ci_id: 源 CI ID
        target_ci_id: 目标 CI ID
        relation_type_id: 关系类型 ID

    Returns:
        tuple: (关系实例或 None, 是否创建成功)
    """
    existing = CmdbRelation.query.filter_by(
        source_ci_id=source_ci_id,
        target_ci_id=target_ci_id,
        relation_type_id=relation_type_id,
    ).first()

    if existing:
        return existing, False

    try:
        relation = create_relation_with_validation(
            source_ci_id=source_ci_id,
            target_ci_id=target_ci_id,
            relation_type_id=relation_type_id,
            source_type="rule",
        )
        return relation, True
    except RelationServiceError as e:
        logger.error(f"创建关系失败: {e}")
        return None, False


def process_ci_triggers(ci: CiInstance) -> dict:
    """
    处理 CI 的触发器，自动创建关系

    Args:
        ci: CI 实例

    Returns:
        dict: 处理结果统计
    """
    result = {
        "total_triggers": 0,
        "created_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
    }

    triggers = get_matching_triggers(ci)
    result["total_triggers"] = len(triggers)

    for trigger in triggers:
        try:
            target_cis = match_trigger_condition(ci, trigger)

            if not target_cis:
                log_trigger_execution(
                    trigger_id=trigger.id,
                    source_ci_id=ci.id,
                    target_ci_id=None,
                    status="skipped",
                    message="未找到匹配的目标 CI",
                )
                result["skipped_count"] += 1
                continue

            for target_ci in target_cis:
                relation, created = create_relation_with_skip_duplicate(
                    source_ci_id=ci.id,
                    target_ci_id=target_ci.id,
                    relation_type_id=trigger.relation_type_id,
                )

                if created:
                    log_trigger_execution(
                        trigger_id=trigger.id,
                        source_ci_id=ci.id,
                        target_ci_id=target_ci.id,
                        status="success",
                        message="关系创建成功",
                    )
                    result["created_count"] += 1
                else:
                    log_trigger_execution(
                        trigger_id=trigger.id,
                        source_ci_id=ci.id,
                        target_ci_id=target_ci.id,
                        status="skipped",
                        message="关系已存在",
                    )
                    result["skipped_count"] += 1

        except Exception as e:
            logger.error(f"处理触发器 {trigger.id} 失败: {e}")
            log_trigger_execution(
                trigger_id=trigger.id,
                source_ci_id=ci.id,
                target_ci_id=None,
                status="failed",
                message=str(e),
            )
            result["failed_count"] += 1

    return result


def process_ci_triggers_async(ci_id: int) -> None:
    app = current_app._get_current_object()

    def run():
        with app.app_context():
            ci = CiInstance.query.get(ci_id)
            if not ci:
                return
            process_ci_triggers(ci)

    thread = Thread(target=run)
    thread.daemon = True
    thread.start()
