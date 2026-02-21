from app import db
from datetime import datetime
import bcrypt

class PasswordHistory(db.Model):
    __tablename__ = 'password_histories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def check_password_history(cls, user_id, password, count=5):
        histories = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).limit(count).all()
        for history in histories:
            if bcrypt.checkpw(password.encode('utf-8'), history.password_hash.encode('utf-8')):
                return True
        return False
    
    @classmethod
    def add_history(cls, user_id, password_hash):
        from app.models.config import SystemConfig
        count_value = SystemConfig.get_value('password_history_count', '5')
        count = int(count_value) if count_value else 5
        
        history = cls(user_id=user_id, password_hash=password_hash)
        history.save()
        
        all_histories = cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).all()
        if len(all_histories) > count:
            for old in all_histories[count:]:
                db.session.delete(old)
            db.session.commit()
