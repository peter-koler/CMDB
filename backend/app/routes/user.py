from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.user import User
from app.models.config import SystemConfig
from app.models.operation_log import OperationLog
from app.models.password_history import PasswordHistory
from app.routes.auth import validate_password, log_operation
from datetime import datetime
import bcrypt

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

def require_admin():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return False
    return True

@user_bp.route('', methods=['GET'])
@jwt_required()
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '')
    role = request.args.get('role', '')
    status = request.args.get('status', '')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    query = User.query.filter(User.deleted_at.is_(None))
    
    if keyword:
        query = query.filter(
            db.or_(
                User.username.like(f'%{keyword}%'),
                User.email.like(f'%{keyword}%'),
                User.department.like(f'%{keyword}%')
            )
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if status:
        query = query.filter(User.status == status)
    
    if sort_order == 'desc':
        query = query.order_by(getattr(User, sort_by).desc())
    else:
        query = query.order_by(getattr(User, sort_by).asc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [u.to_dict() for u in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages
        }
    })

@user_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限创建用户'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    phone = data.get('phone')
    department = data.get('department')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'code': 400, 'message': '用户名已存在'}), 400
    
    ok, msg = validate_password(password)
    if not ok:
        return jsonify({'code': 400, 'message': msg}), 400
    
    user = User(
        username=username,
        email=email,
        phone=phone,
        department=department,
        role=role,
        status='active'
    )
    user.set_password(password)
    user.save()
    
    log_operation(int(identity), claims.get('username'), 'CREATE', 'user', user.id, f'创建用户: {username}')
    
    return jsonify({
        'code': 200,
        'message': '用户创建成功',
        'data': user.to_dict()
    })

@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限查看用户'}), 403
    
    user = User.query.get(user_id)
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    return jsonify({
        'code': 200,
        'data': user.to_dict()
    })

@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限更新用户'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(user_id)
    
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    
    if 'email' in data:
        user.email = data['email']
    if 'phone' in data:
        user.phone = data['phone']
    if 'department' in data:
        user.department = data['department']
    if 'role' in data:
        user.role = data['role']
    if 'status' in data:
        user.status = data['status']
    
    user.save()
    
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'user', user.id, f'更新用户: {user.username}')
    
    return jsonify({
        'code': 200,
        'message': '用户更新成功',
        'data': user.to_dict()
    })

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限删除用户'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(user_id)
    
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    if user.username == 'admin':
        return jsonify({'code': 400, 'message': '不能删除管理员账户'}), 400
    
    username = user.username
    user.delete()
    
    log_operation(int(identity), claims.get('username'), 'DELETE', 'user', user_id, f'删除用户: {username}')
    
    return jsonify({
        'code': 200,
        'message': '用户删除成功'
    })

@user_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@jwt_required()
def reset_password(user_id):
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限重置密码'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(user_id)
    
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    new_password = data.get('new_password')
    
    if not new_password:
        return jsonify({'code': 400, 'message': '新密码不能为空'}), 400
    
    ok, msg = validate_password(new_password)
    if not ok:
        return jsonify({'code': 400, 'message': msg}), 400
    
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    PasswordHistory.add_history(user.id, password_hash)
    
    user.set_password(new_password)
    user.last_password_change = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save()
    
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'password', user.id, f'重置用户密码: {user.username}')
    
    return jsonify({
        'code': 200,
        'message': '密码重置成功'
    })

@user_bp.route('/<int:user_id>/unlock', methods=['POST'])
@jwt_required()
def unlock_user(user_id):
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限解锁用户'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(user_id)
    
    if not user or user.deleted_at:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    user.locked_until = None
    user.failed_login_attempts = 0
    user.save()
    
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'user', user.id, f'解锁用户: {user.username}')
    
    return jsonify({
        'code': 200,
        'message': '用户解锁成功'
    })
