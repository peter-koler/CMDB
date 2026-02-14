from app import db
from datetime import datetime

class SystemConfig(db.Model):
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    config_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_value(cls, key, default=None):
        config = cls.query.filter_by(config_key=key).first()
        return config.config_value if config else default
    
    @classmethod
    def set_value(cls, key, value, updated_by=None):
        config = cls.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            config.updated_by = updated_by
        else:
            config = cls(config_key=key, config_value=value, updated_by=updated_by)
            db.session.add(config)
        db.session.commit()
    
    @classmethod
    def get_all_config(cls):
        configs = cls.query.all()
        return {c.config_key: c.config_value for c in configs}
    
    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
