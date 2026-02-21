from app import db
from datetime import datetime
import json


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    path = db.Column(db.String(500), default='')
    role_ids = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    children = db.relationship('Department', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    department_users = db.relationship('DepartmentUser', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    department_roles = db.relationship('DepartmentRole', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_role_ids(self):
        try:
            return json.loads(self.role_ids) if self.role_ids else []
        except Exception:
            return []
    
    def set_role_ids(self, role_ids):
        self.role_ids = json.dumps(role_ids)
    
    def update_path(self):
        if self.parent_id:
            parent = Department.query.get(self.parent_id)
            if parent:
                self.path = f"{parent.path}{self.id}/"
        else:
            self.path = f"/{self.id}/"
    
    def get_all_children_ids(self):
        ids = []
        for child in self.children:
            ids.append(child.id)
            ids.extend(child.get_all_children_ids())
        return ids
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'parent_id': self.parent_id,
            'manager_id': self.manager_id,
            'sort_order': self.sort_order,
            'path': self.path,
            'role_ids': self.get_role_ids(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'children': [child.to_dict() for child in self.children.order_by(Department.sort_order)]
        }
    
    def to_simple_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'parent_id': self.parent_id,
            'manager_id': self.manager_id,
            'sort_order': self.sort_order,
            'path': self.path,
            'role_ids': self.get_role_ids(),
            'user_count': self.department_users.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        self.update_path()
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class DepartmentRole(db.Model):
    __tablename__ = 'department_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    role = db.relationship('Role', backref='department_links')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'role_id', name='unique_dept_role'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'department_id': self.department_id,
            'role_id': self.role_id,
            'role': {
                'id': self.role.id,
                'name': self.role.name,
                'code': self.role.code
            } if self.role else None
        }


class DepartmentUser(db.Model):
    __tablename__ = 'department_users'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_leader = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.now)
    
    # 用户关系
    user = db.relationship('User', backref='department_links', lazy='joined')
    
    __table_args__ = (
        db.UniqueConstraint('department_id', 'user_id', name='unique_dept_user'),
    )
    
    def to_dict(self):
        roles = []
        if self.user:
            for ur in self.user.role_links:
                if ur.role:
                    roles.append({
                        'id': ur.role.id,
                        'name': ur.role.name,
                        'code': ur.role.code
                    })
        
        return {
            'id': self.id,
            'department_id': self.department_id,
            'user_id': self.user_id,
            'is_leader': self.is_leader,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
                'phone': self.user.phone,
                'roles': roles
            } if self.user else None
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
