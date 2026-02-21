from app import db
from datetime import datetime
import json


class RelationType(db.Model):
    """
    关系类型定义
    定义关系的语义，如 "运行在", "包含", "连接到"
    """

    __tablename__ = "relation_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    source_label = db.Column(db.String(100), nullable=False)
    target_label = db.Column(db.String(100), nullable=False)
    direction = db.Column(db.String(20), default="directed")

    source_model_ids = db.Column(db.Text, default="[]")
    target_model_ids = db.Column(db.Text, default="[]")
    cardinality = db.Column(db.String(20), default="many_many")
    allow_self_loop = db.Column(db.Boolean, default=False)

    description = db.Column(db.Text)
    style = db.Column(db.Text, default="{}")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "source_label": self.source_label,
            "target_label": self.target_label,
            "direction": self.direction,
            "source_model_ids": json.loads(self.source_model_ids)
            if self.source_model_ids
            else [],
            "target_model_ids": json.loads(self.target_model_ids)
            if self.target_model_ids
            else [],
            "cardinality": self.cardinality,
            "allow_self_loop": self.allow_self_loop,
            "description": self.description,
            "style": json.loads(self.style) if self.style else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CmdbRelation(db.Model):
    """
    CI 关系实例表
    存储实际的 CI 关联数据
    """

    __tablename__ = "cmdb_relations"

    id = db.Column(db.Integer, primary_key=True)
    source_ci_id = db.Column(
        db.Integer, db.ForeignKey("ci_instances.id"), nullable=False, index=True
    )
    target_ci_id = db.Column(
        db.Integer, db.ForeignKey("ci_instances.id"), nullable=False, index=True
    )
    relation_type_id = db.Column(
        db.Integer, db.ForeignKey("relation_types.id"), nullable=False
    )

    source_type = db.Column(db.String(20), default="manual")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    source_ci = db.relationship(
        "CiInstance", foreign_keys=[source_ci_id], backref="source_relations"
    )
    target_ci = db.relationship(
        "CiInstance", foreign_keys=[target_ci_id], backref="target_relations"
    )
    relation_type = db.relationship("RelationType")

    __table_args__ = (
        db.UniqueConstraint(
            "source_ci_id",
            "target_ci_id",
            "relation_type_id",
            name="unique_ci_relation",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "source_ci_id": self.source_ci_id,
            "source_ci_name": self.source_ci.name if self.source_ci else None,
            "target_ci_id": self.target_ci_id,
            "target_ci_name": self.target_ci.name if self.target_ci else None,
            "relation_type_id": self.relation_type_id,
            "relation_type_name": self.relation_type.name
            if self.relation_type
            else None,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class RelationTrigger(db.Model):
    """
    关系触发器
    定义自动建立关系的规则
    """

    __tablename__ = "relation_triggers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    source_model_id = db.Column(
        db.Integer,
        db.ForeignKey("cmdb_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_model_id = db.Column(
        db.Integer,
        db.ForeignKey("cmdb_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    relation_type_id = db.Column(
        db.Integer, db.ForeignKey("relation_types.id"), nullable=False
    )

    trigger_type = db.Column(db.String(20), default="expression")
    trigger_condition = db.Column(db.Text, nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    source_model = db.relationship("CmdbModel", foreign_keys=[source_model_id])
    target_model = db.relationship("CmdbModel", foreign_keys=[target_model_id])
    relation_type = db.relationship("RelationType")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "source_model_id": self.source_model_id,
            "source_model_name": self.source_model.name if self.source_model else None,
            "target_model_id": self.target_model_id,
            "target_model_name": self.target_model.name if self.target_model else None,
            "relation_type_id": self.relation_type_id,
            "relation_type_name": self.relation_type.name
            if self.relation_type
            else None,
            "trigger_type": self.trigger_type,
            "trigger_condition": json.loads(self.trigger_condition)
            if self.trigger_condition
            else {},
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class TriggerExecutionLog(db.Model):
    """
    触发器执行日志
    记录每次触发器执行的详细信息
    """

    __tablename__ = "trigger_execution_logs"

    id = db.Column(db.Integer, primary_key=True)
    trigger_id = db.Column(
        db.Integer,
        db.ForeignKey("relation_triggers.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_ci_id = db.Column(
        db.Integer, db.ForeignKey("ci_instances.id", ondelete="CASCADE"), nullable=False
    )
    target_ci_id = db.Column(
        db.Integer, db.ForeignKey("ci_instances.id", ondelete="SET NULL"), nullable=True
    )
    status = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trigger = db.relationship("RelationTrigger", backref="execution_logs")
    source_ci = db.relationship("CiInstance", foreign_keys=[source_ci_id])
    target_ci = db.relationship("CiInstance", foreign_keys=[target_ci_id])

    __table_args__ = (
        db.Index("idx_trigger_log_trigger_id", "trigger_id"),
        db.Index("idx_trigger_log_created_at", "created_at"),
        db.Index("idx_trigger_log_status", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "trigger_id": self.trigger_id,
            "trigger_name": self.trigger.name if self.trigger else None,
            "source_ci_id": self.source_ci_id,
            "source_ci_name": self.source_ci.name if self.source_ci else None,
            "target_ci_id": self.target_ci_id,
            "target_ci_name": self.target_ci.name if self.target_ci else None,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()


class BatchScanTask(db.Model):
    """
    批量扫描任务
    跟踪批量扫描任务的执行状态和历史
    """

    __tablename__ = "batch_scan_tasks"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(
        db.Integer, db.ForeignKey("cmdb_models.id", ondelete="CASCADE"), nullable=False
    )
    status = db.Column(db.String(20), nullable=False, default="pending")
    total_count = db.Column(db.Integer, default=0)
    processed_count = db.Column(db.Integer, default=0)
    created_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    trigger_source = db.Column(db.String(20), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    model = db.relationship("CmdbModel", backref="batch_scan_tasks")
    creator = db.relationship("User", backref="batch_scan_tasks")

    __table_args__ = (
        db.Index("idx_batch_scan_model_id", "model_id"),
        db.Index("idx_batch_scan_status", "status"),
        db.Index("idx_batch_scan_created_at", "created_at"),
    )

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "model_name": self.model.name if self.model else None,
            "status": self.status,
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "created_count": self.created_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "error_message": self.error_message,
            "trigger_source": self.trigger_source,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "created_by_name": self.creator.username if self.creator else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
