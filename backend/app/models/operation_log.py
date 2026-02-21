from app import db
from datetime import datetime

class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    username = db.Column(db.String(50), index=True)
    operation_type = db.Column(db.String(20), nullable=False, index=True)
    operation_object = db.Column(db.String(50))
    object_id = db.Column(db.Integer)
    operation_desc = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    status = db.Column(db.String(20), default='success', index=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'operation_type': self.operation_type,
            'operation_object': self.operation_object,
            'object_id': self.object_id,
            'operation_desc': self.operation_desc,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
