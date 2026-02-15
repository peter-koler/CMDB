from app import db
from datetime import datetime
import json


class CmdbModel(db.Model):
    __tablename__ = 'cmdb_models'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default='AppstoreOutlined')
    category_id = db.Column(db.Integer, db.ForeignKey('model_categories.id'), nullable=False)
    model_type_id = db.Column(db.Integer, db.ForeignKey('model_types.id'), nullable=True)
    description = db.Column(db.Text)
    config = db.Column(db.Text, default='{}')  # JSON格式存储额外配置
    form_config = db.Column(db.Text, default='[]')  # JSON格式存储表单配置（用于拖拽设计器）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    regions = db.relationship('ModelRegion', backref='model', lazy='dynamic', cascade='all, delete-orphan')
    fields = db.relationship('ModelField', backref='model', lazy='dynamic', cascade='all, delete-orphan',
                             foreign_keys='ModelField.model_id')

    def get_config(self):
        try:
            return json.loads(self.config) if self.config else {}
        except Exception:
            return {}

    def set_config(self, config_data):
        self.config = json.dumps(config_data or {}, ensure_ascii=False)

    @property
    def icon_url(self):
        return self.get_config().get('icon_url')

    @property
    def key_field_codes(self):
        value = self.get_config().get('key_field_codes', [])
        return value if isinstance(value, list) else []
    
    def to_dict(self):
        config_data = self.get_config()
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'icon': self.icon,
            'icon_url': config_data.get('icon_url'),
            'key_field_codes': self.key_field_codes,
            'category_id': self.category_id,
            'model_type_id': self.model_type_id,
            'description': self.description,
            'config': config_data,
            'form_config': json.loads(self.form_config) if self.form_config else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'category_name': self.category.name if self.category else None,
            'model_type_name': self.model_type.name if self.model_type else None
        }
    
    def to_full_dict(self):
        data = self.to_dict()
        data['regions'] = [region.to_dict() for region in self.regions]
        data['fields'] = [field.to_dict() for field in self.fields]
        return data
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class ModelType(db.Model):
    __tablename__ = 'model_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    models = db.relationship('CmdbModel', backref='model_type', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
