from app import db
from datetime import datetime


class ModelRegion(db.Model):
    __tablename__ = 'model_regions'
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    layout = db.Column(db.String(20), default='2')  # 1, 2, 3, 4 列
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fields = db.relationship('ModelField', backref='region', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'name': self.name,
            'code': self.code,
            'layout': self.layout,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
