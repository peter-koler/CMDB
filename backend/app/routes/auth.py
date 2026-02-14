from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity, get_jwt
)
from app import db
from app.models.user import User
from app.models.config import SystemConfig
from app.models.operation_log import OperationLog
from app.models.password_history import PasswordHistory
from datetime import datetime, timedelta
import bcrypt
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

def validate_password(password):
    min_length = int(SystemConfig.get_value('password_min_length', '8'))
    require_uppercase = SystemConfig.get_value('require_uppercase', 'true') == 'true'
    require_lowercase = SystemConfig.get_value('require_lowercase', 'true') == 'true'
    require_digit = SystemConfig.get_value('require_digit', 'true') == 'true'
    require_special = SystemConfig.get_value('require_special', 'true') == 'true'
    
    if len(password) < min_length:
        return False, f'密码长度至少{min_length}位'
    if require_uppercase and not re.search(r'[A-Z]', password):
        return False, '密码必须包含大写字母'
    if require_lowercase and not re.search(r'[a-z]', password):
        return False, '密码必须包含小写字母'
    if require_digit and not re.search(r'\d', password):
        return False, '密码必须包含数字'
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, '密码必须包含特殊字符'
    return True, 'OK'

def log_operation(user_id, username, operation_type, operation_object=None, object_id=None, 
                  operation_desc=None, status='success', error_message=None):
    log = OperationLog(
        user_id=user_id,
        username=username,
        operation_type=operation_type,
        operation_object=operation_object,
        object_id=object_id,
        operation_desc=operation_desc,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status=status,
        error_message=error_message
    )
    log.save()

def check_and_update_lockout(user):
    max_failures = int(SystemConfig.get_value('max_login_failures', '5'))
    lock_duration = int(SystemConfig.get_value('lock_duration_hours', '24'))
    
    if user.locked_until and user.locked_until > datetime.utcnow():
        return False, '账户已被锁定，请稍后再试'
    
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.locked_until = None
        user.failed_login_attempts = 0
        user.save()
    
    return True, 'OK'

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        log_operation(None, username, 'LOGIN', 'user', None, '登录尝试', 'failed', '用户不存在')
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    
    if user.deleted_at:
        log_operation(user.id, username, 'LOGIN', 'user', user.id, '登录尝试', 'failed', '账户已删除')
        return jsonify({'code': 401, 'message': '账户已被禁用'}), 401
    
    if user.status == 'disabled':
        log_operation(user.id, username, 'LOGIN', 'user', user.id, '登录尝试', 'failed', '账户已禁用')
        return jsonify({'code': 401, 'message': '账户已被禁用'}), 401
    
    ok, msg = check_and_update_lockout(user)
    if not ok:
        return jsonify({'code': 401, 'message': msg}), 401
    
    if not user.check_password(password):
        user.failed_login_attempts += 1
        max_failures = int(SystemConfig.get_value('max_login_failures', '5'))
        
        if user.failed_login_attempts >= max_failures:
            lock_duration = int(SystemConfig.get_value('lock_duration_hours', '24'))
            user.locked_until = datetime.utcnow() + timedelta(hours=lock_duration)
        
        user.save()
        log_operation(user.id, username, 'LOGIN', 'user', user.id, '登录尝试', 'failed', '密码错误')
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save()
    
    access_token_expires = int(SystemConfig.get_value('access_token_expire', '30'))
    refresh_token_expires = int(SystemConfig.get_value('refresh_token_expire', '10080'))
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'username': user.username, 'role': 'admin' if user.is_admin else 'user'},
        expires_delta=timedelta(minutes=access_token_expires)
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        expires_delta=timedelta(minutes=refresh_token_expires)
    )
    
    log_operation(user.id, username, 'LOGIN', 'user', user.id, '用户登录成功')
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': access_token_expires * 60,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': 'admin' if user.is_admin else 'user',
                'email': user.email
            }
        }
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    identity = get_jwt_identity()
    claims = get_jwt()
    username = claims.get('username')
    
    log_operation(int(identity), username, 'LOGOUT', 'user', int(identity), '用户登出')
    
    return jsonify({'code': 200, 'message': '登出成功'})

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    
    if not user or user.deleted_at or user.status == 'disabled':
        return jsonify({'code': 401, 'message': '无效的令牌'}), 401
    
    access_token_expires = int(SystemConfig.get_value('access_token_expire', '30'))
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'username': user.username, 'role': 'admin' if user.is_admin else 'user'},
        expires_delta=timedelta(minutes=access_token_expires)
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': access_token_expires * 60
        }
    })

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    permissions = set()
    if user.is_admin:
        permissions.add('*')
        permissions.update(['user:create', 'user:view', 'user:update', 'user:delete', 
                       'config:view', 'config:update', 'log:view', 'log:export',
                       'model:view', 'instance:view', 'department:view', 'role:view'])
    else:
        permissions.update(['user:view', 'log:view'])
    
    # Merge permissions from roles
    for ur in user.role_links:
        if ur.role:
            for p in ur.role.get_menu_permissions():
                permissions.add(p)
    
    return jsonify({
        'code': 200,
        'data': {
            'id': user.id,
            'username': user.username,
            'role': 'admin' if user.is_admin else 'user',
            'permissions': list(permissions),
            'department_id': user.department_id,
            'department_name': user.department.name if user.department else None,
            'email': user.email,
            'phone': user.phone,
            'avatar': None
        }
    })

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    data = request.get_json()
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '旧密码和新密码不能为空'}), 400
    
    if not user.check_password(old_password):
        log_operation(user.id, user.username, 'UPDATE', 'password', user.id, '修改密码', 'failed', '旧密码错误')
        return jsonify({'code': 400, 'message': '旧密码错误'}), 400
    
    ok, msg = validate_password(new_password)
    if not ok:
        return jsonify({'code': 400, 'message': msg}), 400
    
    if PasswordHistory.check_password_history(user.id, new_password):
        return jsonify({'code': 400, 'message': '新密码不能与最近使用的密码相同'}), 400
    
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    PasswordHistory.add_history(user.id, password_hash)
    
    user.set_password(new_password)
    user.last_password_change = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save()
    
    log_operation(user.id, user.username, 'UPDATE', 'password', user.id, '修改密码成功')
    
    return jsonify({'code': 200, 'message': '密码修改成功'})
