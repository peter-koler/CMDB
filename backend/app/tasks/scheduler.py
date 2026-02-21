"""
APScheduler 调度器模块
用于管理定时任务
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

scheduler = None


def init_scheduler(app=None):
    """
    初始化调度器

    Args:
        app: Flask 应用实例
    """
    global scheduler

    if scheduler is not None:
        return scheduler

    jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")}

    executors = {"default": ThreadPoolExecutor(2)}

    job_defaults = {"coalesce": True, "max_instances": 1}

    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="Asia/Shanghai",
    )

    if app:
        with app.app_context():
            scheduler.start()
            logger.info("APScheduler 调度器已启动")
            load_batch_scan_jobs()
    else:
        scheduler.start()
        logger.info("APScheduler 调度器已启动")

    return scheduler


def load_batch_scan_jobs():
    from app.models.cmdb_model import CmdbModel

    models = CmdbModel.query.all()
    for model in models:
        config = model.get_config()
        if config.get("batch_scan_enabled") and config.get("batch_scan_cron"):
            add_batch_scan_job(model.id, config.get("batch_scan_cron"))


def add_batch_scan_job(model_id, cron_expression):
    """
    添加批量扫描定时任务

    Args:
        model_id: 模型 ID
        cron_expression: Cron 表达式

    Returns:
        bool: 是否成功
    """
    global scheduler

    if scheduler is None:
        logger.error("调度器未初始化")
        return False

    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        job_id = f"batch_scan_model_{model_id}"

        from app.tasks.batch_scan import batch_scan_model

        scheduler.add_job(
            batch_scan_model,
            trigger=trigger,
            id=job_id,
            args=[model_id, "scheduled"],
            replace_existing=True,
        )

        logger.info(f"已添加批量扫描任务: model_id={model_id}, cron={cron_expression}")
        return True
    except Exception as e:
        logger.error(f"添加批量扫描任务失败: {e}")
        return False


def remove_batch_scan_job(model_id):
    """
    移除批量扫描定时任务

    Args:
        model_id: 模型 ID

    Returns:
        bool: 是否成功
    """
    global scheduler

    if scheduler is None:
        logger.error("调度器未初始化")
        return False

    try:
        job_id = f"batch_scan_model_{model_id}"
        scheduler.remove_job(job_id)
        logger.info(f"已移除批量扫描任务: model_id={model_id}")
        return True
    except Exception as e:
        logger.error(f"移除批量扫描任务失败: {e}")
        return False


def get_scheduled_jobs():
    """
    获取所有已调度的任务

    Returns:
        list: 任务列表
    """
    global scheduler

    if scheduler is None:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        if job.id.startswith("batch_scan_model_"):
            model_id = int(job.id.replace("batch_scan_model_", ""))
            jobs.append(
                {
                    "job_id": job.id,
                    "model_id": model_id,
                    "next_run_time": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                }
            )

    return jobs
