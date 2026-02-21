from app import db
from datetime import datetime
import json


class CiInstance(db.Model):
    __tablename__ = "ci_instances"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(
        db.Integer, db.ForeignKey("cmdb_models.id"), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(
        db.String(16), unique=True, nullable=False, index=True
    )  # 16位BASE编码
    attribute_values = db.Column(db.Text, default="{}")  # JSON格式存储动态属性值
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=True
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关联
    model = db.relationship("CmdbModel", backref="ci_instances", lazy="joined")
    department = db.relationship("Department", backref="ci_instances", lazy="joined")
    creator = db.relationship("User", foreign_keys=[created_by], lazy="joined")
    updater = db.relationship("User", foreign_keys=[updated_by], lazy="joined")

    def get_attribute_values(self):
        """获取属性值字典"""
        try:
            return json.loads(self.attribute_values) if self.attribute_values else {}
        except Exception:
            return {}

    def set_attribute_values(self, values):
        """设置属性值"""
        self.attribute_values = json.dumps(values, ensure_ascii=False)

    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "code": self.code,
            "attributes": self.get_attribute_values(),
            "department_id": self.department_id,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "model_name": self.model.name if self.model else None,
            "model_code": self.model.code if self.model else None,
            "department_name": self.department.name if self.department else None,
            "creator_name": self.creator.username if self.creator else None,
        }

    def to_detail_dict(self):
        """详情展示用的字典，包含完整的模型信息"""
        data = self.to_dict()
        if self.model:
            model_config = {}
            try:
                model_config = (
                    json.loads(self.model.config) if self.model.config else {}
                )
            except Exception:
                model_config = {}
            data["model"] = {
                "id": self.model.id,
                "name": self.model.name,
                "code": self.model.code,
                "icon": self.model.icon,
                "icon_url": model_config.get("icon_url"),
                "key_field_codes": model_config.get("key_field_codes", []),
                "form_config": self.model.form_config,
                "fields": [
                    {
                        "id": f.id,
                        "code": f.code,
                        "name": f.name,
                        "field_type": f.field_type,
                    }
                    for f in self.model.fields
                ]
                if self.model.fields
                else [],
            }
        if self.department:
            data["department"] = {
                "id": self.department.id,
                "name": self.department.name,
            }
        if self.creator:
            data["creator"] = {"id": self.creator.id, "username": self.creator.username}
        return data

    def to_list_dict(self, fields=None):
        """列表展示用的简化字典"""
        data = {
            "id": self.id,
            "code": self.code,
            "model_id": self.model_id,
            "model_name": self.model.name if self.model else None,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "creator_name": self.creator.username if self.creator else None,
            "attributes": self.get_attribute_values(),
        }

        return data

    def save(self, process_triggers=True):
        db.session.add(self)
        db.session.commit()

        if process_triggers:
            try:
                from app.services.trigger_service import process_ci_triggers, process_ci_triggers_async
                from flask import current_app

                if current_app and current_app.config.get("TESTING"):
                    process_ci_triggers(self)
                else:
                    process_ci_triggers_async(self.id)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"处理触发器失败: {e}")

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CiHistory(db.Model):
    __tablename__ = "ci_history"

    id = db.Column(db.Integer, primary_key=True)
    ci_id = db.Column(
        db.Integer, db.ForeignKey("ci_instances.id"), nullable=False, index=True
    )
    operation = db.Column(db.String(50), nullable=False)  # CREATE/UPDATE/DELETE
    attribute_name = db.Column(db.String(100))  # 变更的属性名
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    operator_name = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关联
    ci = db.relationship("CiInstance", backref="histories", lazy="joined")
    operator = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "ci_id": self.ci_id,
            "ci": {
                "id": self.ci_id,
                "name": self.ci.name if self.ci else None,
                "code": self.ci.code if self.ci else None,
            }
            if self.ci
            else None,
            "operation": self.operation,
            "attribute_name": self.attribute_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()


class CodeSequence(db.Model):
    __tablename__ = "code_sequences"

    id = db.Column(db.Integer, primary_key=True)
    sequence_type = db.Column(db.String(50), nullable=False)
    sequence_date = db.Column(db.String(8), nullable=False)  # YYYYMMDD
    current_value = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint("sequence_type", "sequence_date", name="unique_sequence"),
    )

    @classmethod
    def get_next_value(cls, sequence_type="ci"):
        """获取下一个序号"""
        from datetime import datetime

        today = datetime.now().strftime("%Y%m%d")

        sequence = cls.query.filter_by(
            sequence_type=sequence_type, sequence_date=today
        ).first()

        if not sequence:
            sequence = cls(
                sequence_type=sequence_type, sequence_date=today, current_value=0
            )
            db.session.add(sequence)

        sequence.current_value += 1
        db.session.commit()

        return sequence.current_value

    def save(self):
        db.session.add(self)
        db.session.commit()
