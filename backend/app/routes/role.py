from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.role import Role, UserRole
from app.models.user import User
from app import db
from app.utils.decorators import log_operation

role_bp = Blueprint('role', __name__, url_prefix='/api/v1/roles')


def require_admin():
    """检查是否是管理员"""
    claims = get_jwt()
    return claims.get('role') == 'admin'


# ==================== 角色管理 ====================

@role_bp.route('', methods=['GET'])
@jwt_required()
def get_roles():
    """获取角色列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '')
    
    query = Role.query
    
    if keyword:
        query = query.filter(
            db.or_(
                Role.name.contains(keyword),
                Role.code.contains(keyword)
            )
        )
    
    pagination = query.order_by(Role.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [role.to_dict() for role in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@role_bp.route('', methods=['POST'])
@jwt_required()
def create_role():
    """创建角色"""
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限创建角色'}), 403
    
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '角色名称和编码不能为空'}), 400
    
    # 检查编码是否已存在
    if Role.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '角色编码已存在'}), 400
    
    role = Role(
        name=data['name'],
        code=data['code'],
        description=data.get('description'),
        status=data.get('status', 'active')
    )
    
    # 设置权限
    if 'menu_permissions' in data:
        role.set_menu_permissions(data['menu_permissions'])
    if 'data_permissions' in data:
        role.set_data_permissions(data['data_permissions'])
    
    role.save()
    
    # 记录操作日志
    identity = get_jwt_identity()
    claims = get_jwt()
    log_operation(int(identity), claims.get('username'), 'CREATE', 'role', role.id, f'创建角色: {role.name}')
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': role.to_dict()
    })


@role_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_role(id):
    """更新角色"""
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限更新角色'}), 403
    
    role = Role.query.get_or_404(id)
    data = request.get_json()
    
    # 检查编码是否被其他角色使用
    if data.get('code') and data['code'] != role.code:
        existing = Role.query.filter_by(code=data['code']).first()
        if existing:
            return jsonify({'code': 400, 'message': '角色编码已存在'}), 400
        role.code = data['code']
    
    role.name = data.get('name', role.name)
    role.description = data.get('description', role.description)
    role.status = data.get('status', role.status)
    
    # 更新权限
    if 'menu_permissions' in data:
        role.set_menu_permissions(data['menu_permissions'])
    if 'data_permissions' in data:
        role.set_data_permissions(data['data_permissions'])
    
    role.save()
    
    # 记录操作日志
    identity = get_jwt_identity()
    claims = get_jwt()
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'role', role.id, f'更新角色: {role.name}')
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': role.to_dict()
    })


@role_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_role(id):
    """删除角色"""
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限删除角色'}), 403
    
    role = Role.query.get_or_404(id)
    
    # 检查是否有用户关联
    if role.user_roles.count() > 0:
        return jsonify({'code': 400, 'message': '该角色下存在用户，无法删除'}), 400
    
    role_name = role.name
    role.delete()
    
    # 记录操作日志
    identity = get_jwt_identity()
    claims = get_jwt()
    log_operation(int(identity), claims.get('username'), 'DELETE', 'role', id, f'删除角色: {role_name}')
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 角色用户管理 ====================

@role_bp.route('/<int:role_id>/users', methods=['GET'])
@jwt_required()
def get_role_users(role_id):
    """获取角色的用户列表"""
    role = Role.query.get_or_404(role_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = UserRole.query.filter_by(role_id=role_id)
    pagination = query.order_by(UserRole.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@role_bp.route('/<int:role_id>/users', methods=['POST'])
@jwt_required()
def add_role_users(role_id):
    """分配用户到角色"""
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限分配角色'}), 403
    
    role = Role.query.get_or_404(role_id)
    data = request.get_json()
    
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return jsonify({'code': 400, 'message': '请选择要分配的用户'}), 400
    
    added_count = 0
    for user_id in user_ids:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            continue
        
        # 检查是否已关联
        existing = UserRole.query.filter_by(
            role_id=role_id, user_id=user_id
        ).first()
        if existing:
            continue
        
        user_role = UserRole(role_id=role_id, user_id=user_id)
        user_role.save()
        added_count += 1
    
    # 记录操作日志
    identity = get_jwt_identity()
    claims = get_jwt()
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'role', role_id, f'为角色 {role.name} 分配 {added_count} 个用户')
    
    return jsonify({
        'code': 200,
        'message': f'成功分配 {added_count} 个用户',
        'data': {'added_count': added_count}
    })


@role_bp.route('/<int:role_id>/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_role_user(role_id, user_id):
    """移除用户的角色"""
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限移除角色'}), 403
    
    user_role = UserRole.query.filter_by(
        role_id=role_id, user_id=user_id
    ).first_or_404()
    
    user_role.delete()
    
    # 记录操作日志
    identity = get_jwt_identity()
    claims = get_jwt()
    log_operation(int(identity), claims.get('username'), 'DELETE', 'role_user', user_role.id, '移除用户角色')
    
    return jsonify({
        'code': 200,
        'message': '移除成功'
    })


# ==================== 菜单权限树 ====================

@role_bp.route('/menus/tree', methods=['GET'])
@jwt_required()
def get_menu_tree():
    """获取菜单权限树"""
    menu_tree = [
        {
            'key': 'system',
            'title': '系统管理',
            'children': [
                {
                    'key': 'system:user',
                    'title': '用户管理',
                    'actions': [
                        {'key': 'system:user:view', 'title': '查看'},
                        {'key': 'system:user:create', 'title': '创建'},
                        {'key': 'system:user:update', 'title': '编辑'},
                        {'key': 'system:user:delete', 'title': '删除'},
                        {'key': 'system:user:reset_password', 'title': '重置密码'}
                    ]
                },
                {
                    'key': 'system:department',
                    'title': '部门管理',
                    'actions': [
                        {'key': 'system:department:view', 'title': '查看'},
                        {'key': 'system:department:create', 'title': '创建'},
                        {'key': 'system:department:update', 'title': '编辑'},
                        {'key': 'system:department:delete', 'title': '删除'}
                    ]
                },
                {
                    'key': 'system:role',
                    'title': '角色管理',
                    'actions': [
                        {'key': 'system:role:view', 'title': '查看'},
                        {'key': 'system:role:create', 'title': '创建'},
                        {'key': 'system:role:update', 'title': '编辑'},
                        {'key': 'system:role:delete', 'title': '删除'},
                        {'key': 'system:role:assign', 'title': '分配权限'}
                    ]
                },
                {
                    'key': 'system:config',
                    'title': '系统配置',
                    'actions': [
                        {'key': 'system:config:view', 'title': '查看'},
                        {'key': 'system:config:update', 'title': '编辑'}
                    ]
                },
                {
                    'key': 'system:log',
                    'title': '日志审计',
                    'actions': [
                        {'key': 'system:log:view', 'title': '查看'},
                        {'key': 'system:log:export', 'title': '导出'}
                    ]
                }
            ]
        },
        {
            'key': 'cmdb',
            'title': 'CMDB',
            'children': [
                {
                    'key': 'cmdb:model',
                    'title': '模型管理',
                    'actions': [
                        {'key': 'cmdb:model:view', 'title': '查看'},
                        {'key': 'cmdb:model:create', 'title': '创建'},
                        {'key': 'cmdb:model:update', 'title': '编辑'},
                        {'key': 'cmdb:model:delete', 'title': '删除'},
                        {'key': 'cmdb:model:design', 'title': '设计字段'}
                    ]
                },
                {
                    'key': 'cmdb:instance',
                    'title': '配置仓库',
                    'actions': [
                        {'key': 'cmdb:instance:view', 'title': '查看'},
                        {'key': 'cmdb:instance:create', 'title': '创建'},
                        {'key': 'cmdb:instance:update', 'title': '编辑'},
                        {'key': 'cmdb:instance:delete', 'title': '删除'},
                        {'key': 'cmdb:instance:import', 'title': '导入'},
                        {'key': 'cmdb:instance:export', 'title': '导出'}
                    ]
                },
                {
                    'key': 'cmdb:search',
                    'title': '全文搜索',
                    'actions': [
                        {'key': 'cmdb:search:search', 'title': '搜索'}
                    ]
                }
            ]
        }
    ]
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': menu_tree
    })
