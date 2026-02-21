"""
批量扫描任务模块
处理后台批量扫描逻辑
"""

import logging
from datetime import datetime
from threading import Lock

from app import db
from app.models.cmdb_relation import BatchScanTask, RelationTrigger
from app.models.ci_instance import CiInstance
from app.services.trigger_service import (
    match_trigger_condition,
    create_relation_with_skip_duplicate,
    log_trigger_execution,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

_scan_locks = {}
_lock_manager = Lock()


def _get_model_lock(model_id: int):
    """获取模型级别的锁"""
    with _lock_manager:
        if model_id not in _scan_locks:
            _scan_locks[model_id] = Lock()
        return _scan_locks[model_id]


def create_batch_scan_task(
    model_id: int, trigger_source: str, created_by: int = None
) -> BatchScanTask:
    """
    创建批量扫描任务

    Args:
        model_id: 模型 ID
        trigger_source: 触发来源 (manual/scheduled)
        created_by: 创建人 ID

    Returns:
        BatchScanTask: 任务实例

    Raises:
        ValueError: 如果已有任务在运行
    """
    running_task = BatchScanTask.query.filter_by(
        model_id=model_id, status="running"
    ).first()

    if running_task:
        raise ValueError(f"模型 {model_id} 已有扫描任务正在运行")

    total_count = CiInstance.query.filter_by(model_id=model_id).count()

    task = BatchScanTask(
        model_id=model_id,
        status="pending",
        trigger_source=trigger_source,
        total_count=total_count,
        created_by=created_by,
    )
    db.session.add(task)
    db.session.commit()

    return task


def batch_scan_model(
    model_id: int, trigger_source: str = "scheduled", created_by: int = None
) -> dict:
    """
    批量扫描模型的 CI 并创建关系

    Args:
        model_id: 模型 ID
        trigger_source: 触发来源

    Returns:
        dict: 扫描结果统计
    """
    lock = _get_model_lock(model_id)

    if not lock.acquire(blocking=False):
        logger.warning(f"模型 {model_id} 扫描任务已被锁定，跳过")
        return {"status": "skipped", "message": "任务已被锁定"}

    try:
        task = create_batch_scan_task(
            model_id=model_id, trigger_source=trigger_source, created_by=created_by
        )

        task.status = "running"
        task.started_at = datetime.utcnow()
        db.session.commit()

        triggers = RelationTrigger.query.filter_by(
            source_model_id=model_id, is_active=True
        ).all()

        if not triggers:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            db.session.commit()
            return {"status": "completed", "message": "没有活跃的触发器"}

        cis = CiInstance.query.filter_by(model_id=model_id).all()
        task.total_count = len(cis)
        db.session.commit()

        result = {
            "processed_count": 0,
            "created_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }

        for i in range(0, len(cis), BATCH_SIZE):
            batch = cis[i : i + BATCH_SIZE]

            for ci in batch:
                try:
                    for trigger in triggers:
                        target_cis = match_trigger_condition(ci, trigger)

                        if not target_cis:
                            continue

                        for target_ci in target_cis:
                            relation, created = create_relation_with_skip_duplicate(
                                source_ci_id=ci.id,
                                target_ci_id=target_ci.id,
                                relation_type_id=trigger.relation_type_id,
                            )

                            if created:
                                result["created_count"] += 1
                                log_trigger_execution(
                                    trigger_id=trigger.id,
                                    source_ci_id=ci.id,
                                    target_ci_id=target_ci.id,
                                    status="success",
                                    message="批量扫描创建关系成功",
                                )
                            else:
                                result["skipped_count"] += 1

                except Exception as e:
                    logger.error(f"处理 CI {ci.id} 失败: {e}")
                    result["failed_count"] += 1

                result["processed_count"] += 1

            task.processed_count = result["processed_count"]
            task.created_count = result["created_count"]
            task.skipped_count = result["skipped_count"]
            task.failed_count = result["failed_count"]
            db.session.commit()

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"批量扫描完成: model_id={model_id}, result={result}")
        return {"status": "completed", **result}

    except ValueError as e:
        logger.warning(f"批量扫描跳过: {e}")
        return {"status": "skipped", "message": str(e)}

    except Exception as e:
        logger.error(f"批量扫描失败: model_id={model_id}, error={e}")

        if "task" in locals():
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            db.session.commit()

        return {"status": "failed", "message": str(e)}

    finally:
        lock.release()


def get_running_task_for_model(model_id: int) -> BatchScanTask:
    """
    获取模型正在运行的任务

    Args:
        model_id: 模型 ID

    Returns:
        BatchScanTask: 正在运行的任务，没有返回 None
    """
    return BatchScanTask.query.filter_by(model_id=model_id, status="running").first()


def get_model_scan_tasks(model_id: int, status: str = None, limit: int = 20) -> list:
    """
    获取模型的扫描任务列表

    Args:
        model_id: 模型 ID
        status: 状态过滤
        limit: 返回数量限制

    Returns:
        list: 任务列表
    """
    query = BatchScanTask.query.filter_by(model_id=model_id)

    if status:
        query = query.filter_by(status=status)

    return query.order_by(BatchScanTask.created_at.desc()).limit(limit).all()


def get_all_scan_tasks(
    page: int = 1,
    page_size: int = 20,
    model_id: int = None,
    status: str = None,
    trigger_source: str = None,
) -> tuple:
    """
    获取所有扫描任务（分页）

    Args:
        page: 页码
        page_size: 每页数量
        model_id: 模型 ID 过滤
        status: 状态过滤
        trigger_source: 触发来源过滤

    Returns:
        tuple: (任务列表, 总数)
    """
    query = BatchScanTask.query

    if model_id:
        query = query.filter_by(model_id=model_id)
    if status:
        query = query.filter_by(status=status)
    if trigger_source:
        query = query.filter_by(trigger_source=trigger_source)

    total = query.count()
    tasks = (
        query.order_by(BatchScanTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return tasks, total
