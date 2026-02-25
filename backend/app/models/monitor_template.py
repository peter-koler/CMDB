from app import db
from datetime import datetime

class MonitorTemplate(db.Model):
    __tablename__ = 'monitor_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    app = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, default=1)
    is_hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'app': self.app,
            'name': self.name,
            'category': self.category,
            'content': self.content,
            'version': self.version,
            'is_hidden': self.is_hidden,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MonitorCategory(db.Model):
    __tablename__ = 'monitor_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    icon = db.Column(db.String(50))
    sort_order = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('monitor_categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    children = db.relationship('MonitorCategory', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    
    def to_dict(self, include_children=False):
        result = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'icon': self.icon,
            'sort_order': self.sort_order,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_children:
            result['children'] = [child.to_dict(True) for child in self.children]
        return result
