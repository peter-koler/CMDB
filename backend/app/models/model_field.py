from app import db
from datetime import datetime
import json


class ModelField(db.Model):
    __tablename__ = 'model_fields'
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('model_regions.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(50), nullable=False)  # text, number, select, multiselect, cascade, dropdown, reference, file, image, richtext, date, datetime
    is_required = db.Column(db.Boolean, default=False)
    is_unique = db.Column(db.Boolean, default=False)
    default_value = db.Column(db.Text)
    options = db.Column(db.Text, default='[]')  # JSON格式，用于select/multiselect/dropdown/cascade
    validation_rules = db.Column(db.Text, default='{}')  # JSON格式验证规则
    reference_model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=True)  # 引用类型关联的模型
    
    reference_model = db.relationship('CmdbModel', foreign_keys=[reference_model_id], lazy='joined')
    date_format = db.Column(db.String(50))  # 时间格式，如 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:mm:ss'
    sort_order = db.Column(db.Integer, default=0)
    config = db.Column(db.Text, default='{}')  # JSON格式额外配置
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'region_id': self.region_id,
            'name': self.name,
            'code': self.code,
            'field_type': self.field_type,
            'is_required': self.is_required,
            'is_unique': self.is_unique,
            'default_value': self.default_value,
            'options': json.loads(self.options) if self.options else [],
            'validation_rules': json.loads(self.validation_rules) if self.validation_rules else {},
            'reference_model_id': self.reference_model_id,
            'reference_model_name': self.reference_model.name if self.reference_model else None,
            'date_format': self.date_format,
            'sort_order': self.sort_order,
            'config': json.loads(self.config) if self.config else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
