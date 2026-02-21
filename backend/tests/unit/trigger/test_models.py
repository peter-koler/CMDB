"""触发器模块模型单元测试"""

from datetime import datetime


class TestTriggerExecutionLog:
    """测试触发器执行日志模型"""

    def test_create_log_success(self, db_session, test_trigger, test_ci_instance):
        """测试创建成功日志"""
        from app.models.cmdb_relation import TriggerExecutionLog

        log = TriggerExecutionLog(
            trigger_id=test_trigger.id,
            source_ci_id=test_ci_instance.id,
            target_ci_id=test_ci_instance.id,
            status="success",
            message="关系创建成功",
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.trigger_id == test_trigger.id
        assert log.status == "success"
        assert log.message == "关系创建成功"

    def test_create_log_failed(self, db_session, test_trigger, test_ci_instance):
        """测试创建失败日志"""
        from app.models.cmdb_relation import TriggerExecutionLog

        log = TriggerExecutionLog(
            trigger_id=test_trigger.id,
            source_ci_id=test_ci_instance.id,
            status="failed",
            message="目标 CI 不存在",
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.status == "failed"
        assert log.target_ci_id is None

    def test_create_log_skipped(self, db_session, test_trigger, test_ci_instance):
        """测试创建跳过日志"""
        from app.models.cmdb_relation import TriggerExecutionLog

        log = TriggerExecutionLog(
            trigger_id=test_trigger.id,
            source_ci_id=test_ci_instance.id,
            target_ci_id=test_ci_instance.id,
            status="skipped",
            message="关系已存在",
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.status == "skipped"

    def test_log_to_dict(self, db_session, test_trigger, test_ci_instance):
        """测试日志序列化"""
        from app.models.cmdb_relation import TriggerExecutionLog

        log = TriggerExecutionLog(
            trigger_id=test_trigger.id,
            source_ci_id=test_ci_instance.id,
            target_ci_id=test_ci_instance.id,
            status="success",
            message="成功",
        )
        db_session.add(log)
        db_session.commit()

        data = log.to_dict()
        assert data["status"] == "success"
        assert data["message"] == "成功"
        assert "trigger_id" in data
        assert "created_at" in data


class TestBatchScanTask:
    """测试批量扫描任务模型"""

    def test_create_task(self, db_session, test_model):
        """测试创建扫描任务"""
        from app.models.cmdb_relation import BatchScanTask

        task = BatchScanTask(
            model_id=test_model.id, status="pending", trigger_source="manual"
        )
        db_session.add(task)
        db_session.commit()

        assert task.id is not None
        assert task.model_id == test_model.id
        assert task.status == "pending"
        assert task.trigger_source == "manual"
        assert task.total_count == 0
        assert task.processed_count == 0

    def test_task_status_transition(self, db_session, test_model):
        """测试任务状态转换"""
        from app.models.cmdb_relation import BatchScanTask

        task = BatchScanTask(
            model_id=test_model.id, status="pending", trigger_source="scheduled"
        )
        db_session.add(task)
        db_session.commit()

        task.status = "running"
        task.started_at = datetime.utcnow()
        db_session.commit()

        assert task.status == "running"
        assert task.started_at is not None

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.total_count = 100
        task.processed_count = 100
        task.created_count = 50
        db_session.commit()

        assert task.status == "completed"
        assert task.completed_at is not None
        assert task.total_count == 100

    def test_task_failed_with_error(self, db_session, test_model):
        """测试任务失败记录错误"""
        from app.models.cmdb_relation import BatchScanTask

        task = BatchScanTask(
            model_id=test_model.id, status="running", trigger_source="manual"
        )
        db_session.add(task)
        db_session.commit()

        task.status = "failed"
        task.error_message = "数据库连接超时"
        db_session.commit()

        assert task.status == "failed"
        assert task.error_message == "数据库连接超时"

    def test_task_to_dict(self, db_session, test_model):
        """测试任务序列化"""
        from app.models.cmdb_relation import BatchScanTask

        task = BatchScanTask(
            model_id=test_model.id,
            status="completed",
            trigger_source="manual",
            total_count=100,
            processed_count=100,
            created_count=50,
            skipped_count=40,
            failed_count=10,
        )
        db_session.add(task)
        db_session.commit()

        data = task.to_dict()
        assert data["status"] == "completed"
        assert data["total_count"] == 100
        assert data["created_count"] == 50
        assert data["model_id"] == test_model.id
        assert "duration_seconds" in data or "started_at" in data
