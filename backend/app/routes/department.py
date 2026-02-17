from flask import Blueprint, request, jsonify
from app.models.department import Department, DepartmentUser
from app.models.user import User
from app import db
from app.utils.auth import token_required, admin_required
from app.utils.decorators import log_operation

dept_bp = Blueprint('department', __name__, url_prefix='/api/v1/departments')


# ==================== 部门管理 ====================

@dept_bp.route('', methods=['GET'])
@token_required
def get_departments():
    """获取部门树"""
    root_departments = Department.query.filter_by(parent_id=None).order_by(Department.sort_order).all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [dept.to_dict() for dept in root_departments]
    })


@dept_bp.route('', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='department')
def create_department():
    """创建部门"""
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '部门名称和编码不能为空'}), 400
    
    # 检查编码是否已存在
    if Department.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '部门编码已存在'}), 400
    
    # 检查父部门是否存在
    parent_id = data.get('parent_id')
    if parent_id:
        parent = Department.query.get(parent_id)
        if not parent:
            return jsonify({'code': 400, 'message': '父部门不存在'}), 400
    
    department = Department(
        name=data['name'],
        code=data['code'],
        parent_id=parent_id,
        manager_id=data.get('manager_id'),
        sort_order=data.get('sort_order', 0)
    )
    department.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': department.to_dict()
    })


@dept_bp.route('/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='department')
def update_department(id):
    """更新部门"""
    department = Department.query.get_or_404(id)
    data = request.get_json()
    
    # 检查编码是否被其他部门使用
    if data.get('code') and data['code'] != department.code:
        existing = Department.query.filter_by(code=data['code']).first()
        if existing:
            return jsonify({'code': 400, 'message': '部门编码已存在'}), 400
        department.code = data['code']
    
    # 检查父部门是否合法（不能设置自己或子部门为父部门）
    new_parent_id = data.get('parent_id')
    if new_parent_id is not None:
        if new_parent_id == id:
            return jsonify({'code': 400, 'message': '不能将自己设为父部门'}), 400
        # 检查是否将子部门设为父部门
        children_ids = department.get_all_children_ids()
        if new_parent_id in children_ids:
            return jsonify({'code': 400, 'message': '不能将子部门设为父部门'}), 400
        
        parent = Department.query.get(new_parent_id)
        if not parent:
            return jsonify({'code': 400, 'message': '父部门不存在'}), 400
        department.parent_id = new_parent_id
    
    department.name = data.get('name', department.name)
    department.manager_id = data.get('manager_id', department.manager_id)
    department.sort_order = data.get('sort_order', department.sort_order)
    department.save()
    
    # 更新所有子部门的路径
    if new_parent_id is not None:
        _update_children_path(department)
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': department.to_dict()
    })


def _update_children_path(department):
    """递归更新子部门路径"""
    for child in department.children:
        child.update_path()
        db.session.commit()
        _update_children_path(child)


@dept_bp.route('/sort', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='department')
def update_department_sort():
    """更新部门排序"""
    data = request.get_json()
    updates = data.get('updates', [])
    
    for item in updates:
        dept_id = item.get('id')
        sort_order = item.get('sort_order')
        
        department = Department.query.get(dept_id)
        if department:
            department.sort_order = sort_order
            db.session.add(department)
    
    db.session.commit()
    
    return jsonify({
        'code': 200,
        'message': '排序更新成功'
    })


@dept_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='department')
def delete_department(id):
    """删除部门"""
    department = Department.query.get_or_404(id)
    
    # 检查是否有子部门
    if department.children.count() > 0:
        return jsonify({'code': 400, 'message': '请先删除子部门'}), 400
    
    # 检查是否有关联用户
    if department.department_users.count() > 0:
        return jsonify({'code': 400, 'message': '该部门下存在用户，无法删除'}), 400
    
    department.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 部门用户管理 ====================

@dept_bp.route('/<int:dept_id>/users', methods=['GET'])
@token_required
def get_department_users(dept_id):
    """获取部门下的用户"""
    Department.query.get_or_404(dept_id)
    
    # 支持分页
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = DepartmentUser.query.filter_by(department_id=dept_id)
    pagination = query.order_by(DepartmentUser.is_leader.desc()).paginate(
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


@dept_bp.route('/<int:dept_id>/users', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='department_user')
def add_department_users(dept_id):
    """批量添加用户到部门"""
    Department.query.get_or_404(dept_id)
    data = request.get_json()
    
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return jsonify({'code': 400, 'message': '请选择要添加的用户'}), 400
    
    added_count = 0
    for user_id in user_ids:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            continue
        
        # 检查是否已关联
        existing = DepartmentUser.query.filter_by(
            department_id=dept_id, user_id=user_id
        ).first()
        if existing:
            continue
        
        dept_user = DepartmentUser(
            department_id=dept_id,
            user_id=user_id,
            is_leader=data.get('is_leader', False)
        )
        dept_user.save()
        added_count += 1
    
    return jsonify({
        'code': 200,
        'message': f'成功添加 {added_count} 个用户',
        'data': {'added_count': added_count}
    })


@dept_bp.route('/<int:dept_id>/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='department_user')
def remove_department_user(dept_id, user_id):
    """从部门移除用户"""
    dept_user = DepartmentUser.query.filter_by(
        department_id=dept_id, user_id=user_id
    ).first_or_404()
    
    dept_user.delete()
    
    return jsonify({
        'code': 200,
        'message': '移除成功'
    })


@dept_bp.route('/<int:dept_id>/users/<int:user_id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='department_user')
def update_department_user(dept_id, user_id):
    """更新部门用户信息（如设置负责人）"""
    dept_user = DepartmentUser.query.filter_by(
        department_id=dept_id, user_id=user_id
    ).first_or_404()
    
    data = request.get_json()
    dept_user.is_leader = data.get('is_leader', dept_user.is_leader)
    dept_user.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': dept_user.to_dict()
    })


@dept_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user_departments(user_id):
    """获取用户的所有部门"""
    User.query.get_or_404(user_id)
    
    dept_users = DepartmentUser.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [{
            'id': dept_user.department.id,
            'name': dept_user.department.name,
            'code': dept_user.department.code,
            'is_leader': dept_user.is_leader,
            'joined_at': dept_user.joined_at.isoformat() if dept_user.joined_at else None
        } for dept_user in dept_users]
    })
