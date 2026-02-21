from app import db
from datetime import datetime
import json


class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active/disabled
    
    # 权限配置（JSON格式）
    menu_permissions = db.Column(db.Text, default='[]')  # ["system:user:create", "cmdb:instance:view"]
    data_permissions = db.Column(db.Text, default='{}')  # {"scope": "department", "inherit": true}
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user_roles = db.relationship('UserRole', backref='role', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_menu_permissions(self):
        """获取菜单权限列表"""
        try:
            return json.loads(self.menu_permissions) if self.menu_permissions else []
        except Exception:
            return []
    
    def set_menu_permissions(self, permissions):
        """设置菜单权限"""
        self.menu_permissions = json.dumps(permissions)
    
    def get_data_permissions(self):
        """获取数据权限配置"""
        try:
            return json.loads(self.data_permissions) if self.data_permissions else {}
        except Exception:
            return {}
    
    def set_data_permissions(self, permissions):
        """设置数据权限"""
        self.data_permissions = json.dumps(permissions)
    
    def has_permission(self, permission):
        """检查是否有指定权限"""
        perms = self.get_menu_permissions()
        # 支持通配符，如 "system:*" 匹配所有system下的权限
        for p in perms:
            if p == '*' or p == permission:
                return True
            if p.endswith('*'):
                prefix = p[:-1]
                if permission.startswith(prefix):
                    return True
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'status': self.status,
            'menu_permissions': self.get_menu_permissions(),
            'data_permissions': self.get_data_permissions(),
            'user_count': self.user_roles.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_simple_dict(self):
        """简化版字典"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'status': self.status
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关联
    user = db.relationship('User', backref='role_links', lazy='joined')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='unique_user_role'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'role': self.role.to_simple_dict() if self.role else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username
            } if self.user else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
