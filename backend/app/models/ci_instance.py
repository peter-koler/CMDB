from app import db
from datetime import datetime
import json


class CiInstance(db.Model):
    __tablename__ = 'ci_instances'
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)  # 16位BASE编码
    attribute_values = db.Column(db.Text, default='{}')  # JSON格式存储动态属性值
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    model = db.relationship('CmdbModel', backref='ci_instances', lazy='joined')
    department = db.relationship('Department', backref='ci_instances', lazy='joined')
    creator = db.relationship('User', foreign_keys=[created_by], lazy='joined')
    updater = db.relationship('User', foreign_keys=[updated_by], lazy='joined')
    
    def get_attribute_values(self):
        """获取属性值字典"""
        try:
            return json.loads(self.attribute_values) if self.attribute_values else {}
        except:
            return {}
    
    def set_attribute_values(self, values):
        """设置属性值"""
        self.attribute_values = json.dumps(values, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'name': self.name,
            'code': self.code,
            'attribute_values': self.get_attribute_values(),
            'department_id': self.department_id,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'model_name': self.model.name if self.model else None,
            'model_code': self.model.code if self.model else None,
            'department_name': self.department.name if self.department else None,
            'creator_name': self.creator.username if self.creator else None
        }
    
    def to_list_dict(self, fields=None):
        """列表展示用的简化字典"""
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'model_id': self.model_id,
            'model_name': self.model.name if self.model else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'creator_name': self.creator.username if self.creator else None
        }
        
        # 如果指定了字段，添加前3个属性字段
        if fields and self.model:
            attr_values = self.get_attribute_values()
            model_fields = self.model.fields.order_by('sort_order').limit(3).all()
            for field in model_fields:
                field_code = field.code
                if field_code in attr_values:
                    data[field_code] = attr_values[field_code]
        
        return data
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CiHistory(db.Model):
    __tablename__ = 'ci_history'
    
    id = db.Column(db.Integer, primary_key=True)
    ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'), nullable=False, index=True)
    operation = db.Column(db.String(50), nullable=False)  # CREATE/UPDATE/DELETE
    attribute_name = db.Column(db.String(100))  # 变更的属性名
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator_name = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 关联
    ci = db.relationship('CiInstance', backref='histories', lazy='joined')
    operator = db.relationship('User', lazy='joined')
    
    def to_dict(self):
        return {
            'id': self.id,
            'ci_id': self.ci_id,
            'operation': self.operation,
            'attribute_name': self.attribute_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()


class CiRelation(db.Model):
    __tablename__ = 'ci_relations'
    
    id = db.Column(db.Integer, primary_key=True)
    source_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'), nullable=False)
    target_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'), nullable=False)
    relation_type = db.Column(db.String(50), nullable=False)  # contain/depend/parent/associate
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    source_ci = db.relationship('CiInstance', foreign_keys=[source_ci_id], backref='source_relations')
    target_ci = db.relationship('CiInstance', foreign_keys=[target_ci_id], backref='target_relations')
    
    __table_args__ = (
        db.UniqueConstraint('source_ci_id', 'target_ci_id', 'relation_type', name='unique_ci_relation'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_ci_id': self.source_ci_id,
            'target_ci_id': self.target_ci_id,
            'relation_type': self.relation_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'source_ci': {
                'id': self.source_ci.id,
                'name': self.source_ci.name,
                'code': self.source_ci.code
            } if self.source_ci else None,
            'target_ci': {
                'id': self.target_ci.id,
                'name': self.target_ci.name,
                'code': self.target_ci.code
            } if self.target_ci else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()


class CodeSequence(db.Model):
    __tablename__ = 'code_sequences'
    
    id = db.Column(db.Integer, primary_key=True)
    sequence_type = db.Column(db.String(50), nullable=False)
    sequence_date = db.Column(db.String(8), nullable=False)  # YYYYMMDD
    current_value = db.Column(db.Integer, default=0)
    
    __table_args__ = (
        db.UniqueConstraint('sequence_type', 'sequence_date', name='unique_sequence'),
    )
    
    @classmethod
    def get_next_value(cls, sequence_type='ci'):
        """获取下一个序号"""
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        
        sequence = cls.query.filter_by(
            sequence_type=sequence_type,
            sequence_date=today
        ).first()
        
        if not sequence:
            sequence = cls(
                sequence_type=sequence_type,
                sequence_date=today,
                current_value=0
            )
            db.session.add(sequence)
        
        sequence.current_value += 1
        db.session.commit()
        
        return sequence.current_value
    
    def save(self):
        db.session.add(self)
        db.session.commit()
