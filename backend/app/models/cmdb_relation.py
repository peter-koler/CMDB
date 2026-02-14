from app import db
from datetime import datetime
import json

class RelationType(db.Model):
    """
    关系类型定义
    定义关系的语义，如 "运行在", "包含", "连接到"
    """
    __tablename__ = 'relation_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 唯一编码，如 runs_on
    name = db.Column(db.String(100), nullable=False)  # 显示名称
    source_label = db.Column(db.String(100), nullable=False)  # 源端描述，如 "运行"
    target_label = db.Column(db.String(100), nullable=False)  # 目标端描述，如 "承载"
    direction = db.Column(db.String(20), default='directed')  # directed(有向), bidirectional(双向)
    
    # 新增字段
    source_model_ids = db.Column(db.Text, default='[]')  # JSON数组，允许的源模型ID列表
    target_model_ids = db.Column(db.Text, default='[]')  # JSON数组，允许的目标模型ID列表
    cardinality = db.Column(db.String(20), default='many_many')  # one_one/one_many/many_many
    allow_self_loop = db.Column(db.Boolean, default=False)  # 是否允许自环
    
    description = db.Column(db.Text)
    style = db.Column(db.Text, default='{}')  # JSON配置，前端拓扑图样式（颜色、线条等）
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'source_label': self.source_label,
            'target_label': self.target_label,
            'direction': self.direction,
            'source_model_ids': json.loads(self.source_model_ids) if self.source_model_ids else [],
            'target_model_ids': json.loads(self.target_model_ids) if self.target_model_ids else [],
            'cardinality': self.cardinality,
            'allow_self_loop': self.allow_self_loop,
            'description': self.description,
            'style': json.loads(self.style) if self.style else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CmdbRelation(db.Model):
    """
    CI 关系实例表
    存储实际的 CI 关联数据
    """
    __tablename__ = 'cmdb_relations'
    
    id = db.Column(db.Integer, primary_key=True)
    source_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'), nullable=False, index=True)
    target_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'), nullable=False, index=True)
    relation_type_id = db.Column(db.Integer, db.ForeignKey('relation_types.id'), nullable=False)
    
    # 关系来源：manual(手动), reference(引用属性自动), rule(规则触发器自动)
    source_type = db.Column(db.String(20), default='manual') 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联对象
    source_ci = db.relationship('CiInstance', foreign_keys=[source_ci_id], backref='source_relations')
    target_ci = db.relationship('CiInstance', foreign_keys=[target_ci_id], backref='target_relations')
    relation_type = db.relationship('RelationType')
    
    __table_args__ = (
        db.UniqueConstraint('source_ci_id', 'target_ci_id', 'relation_type_id', name='unique_ci_relation'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_ci_id': self.source_ci_id,
            'source_ci_name': self.source_ci.name if self.source_ci else None,
            'target_ci_id': self.target_ci_id,
            'target_ci_name': self.target_ci.name if self.target_ci else None,
            'relation_type_id': self.relation_type_id,
            'relation_type_name': self.relation_type.name if self.relation_type else None,
            'source_type': self.source_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RelationTrigger(db.Model):
    """
    关系触发器
    定义自动建立关系的规则
    """
    __tablename__ = 'relation_triggers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # 触发范围：源模型 -> 目标模型
    source_model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=False)
    target_model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=False)
    relation_type_id = db.Column(db.Integer, db.ForeignKey('relation_types.id'), nullable=False)
    
    # 触发类型：reference(引用属性), expression(规则表达式)
    trigger_type = db.Column(db.String(20), default='expression')
    
    # 触发条件 (JSON)
    # reference示例: {"source_field": "host_id", "target_field": "id"}
    # expression示例: {"operator": "and", "rules": [{"field": "ip", "op": "eq", "target_field": "manage_ip"}]}
    trigger_condition = db.Column(db.Text, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    source_model = db.relationship('CmdbModel', foreign_keys=[source_model_id])
    target_model = db.relationship('CmdbModel', foreign_keys=[target_model_id])
    relation_type = db.relationship('RelationType')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'source_model_id': self.source_model_id,
            'source_model_name': self.source_model.name if self.source_model else None,
            'target_model_id': self.target_model_id,
            'target_model_name': self.target_model.name if self.target_model else None,
            'relation_type_id': self.relation_type_id,
            'relation_type_name': self.relation_type.name if self.relation_type else None,
            'trigger_type': self.trigger_type,
            'trigger_condition': json.loads(self.trigger_condition) if self.trigger_condition else {},
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
