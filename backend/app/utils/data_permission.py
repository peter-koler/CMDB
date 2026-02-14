from flask import request
from flask_jwt_extended import get_jwt_identity, get_jwt
from app.models.user import User
from app.models.department import Department
from app.models.role import Role, UserRole
import json

def get_current_user():
    """获取当前用户"""
    identity = get_jwt_identity()
    return User.query.get(int(identity))

def is_super_admin():
    """检查是否是超级管理员"""
    claims = get_jwt()
    role = claims.get('role')
    return role == 'admin'

def get_user_data_scope():
    """
    获取用户的数据权限范围
    返回: 'all', 'department', 'department_and_children', 'self'
    """
    user = get_current_user()
    if not user:
        return 'self'
    
    if user.role == 'admin':
        return 'all'
    
    scopes = set()
    user_roles = UserRole.query.filter_by(user_id=user.id).all()
    for ur in user_roles:
        role = Role.query.get(ur.role_id)
        if role:
            data_perms = role.get_data_permissions()
            scope = data_perms.get('scope', 'self')
            scopes.add(scope)
    
    # 权限优先级: all > department_and_children > department > self
    if 'all' in scopes:
        return 'all'
    if 'department_and_children' in scopes:
        return 'department_and_children'
    if 'department' in scopes:
        return 'department'
    
    return 'self'

def filter_by_data_permissions(query, model_class):
    """
    根据用户数据权限过滤查询
    """
    user = get_current_user()
    if not user:
        return query.filter(model_class.id == -1)
    
    if user.role == 'admin':
        return query
    
    scope = get_user_data_scope()
    
    if scope == 'all':
        return query
    
    elif scope == 'department':
        if user.department_id:
            return query.filter(model_class.department_id == user.department_id)
        return query.filter(model_class.created_by == user.id)
    
    elif scope == 'department_and_children':
        if user.department_id:
            dept = Department.query.get(user.department_id)
            if dept:
                child_depts = get_child_department_ids(dept.id)
                child_depts.append(user.department_id)
                return query.filter(model_class.department_id.in_(child_depts))
        return query.filter(model_class.created_by == user.id)
    
    else:
        return query.filter(model_class.created_by == user.id)

def get_child_department_ids(parent_id):
    """获取子部门ID列表"""
    children = Department.query.filter_by(parent_id=parent_id).all()
    ids = []
    for child in children:
        ids.append(child.id)
        ids.extend(get_child_department_ids(child.id))
    return ids

def check_data_permission(instance, user_id):
    """
    检查用户是否有操作某条数据的权限
    返回: True/False
    """
    user = User.query.get(user_id)
    if not user:
        return False
    
    if user.role == 'admin':
        return True
    
    scope = get_user_data_scope()
    
    if scope == 'all':
        return True
    
    elif scope == 'department':
        if user.department_id and instance.department_id == user.department_id:
            return True
        return instance.created_by == user_id
    
    elif scope == 'department_and_children':
        if user.department_id:
            child_depts = get_child_department_ids(user.department_id)
            child_depts.append(user.department_id)
            if instance.department_id in child_depts:
                return True
        return instance.created_by == user_id
    
    else:
        return instance.created_by == user_id
