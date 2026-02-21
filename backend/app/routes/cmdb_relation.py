from flask import Blueprint, request, jsonify, Response
from datetime import datetime
from collections import deque
import csv
import io
from app.models.cmdb_relation import (
    RelationType,
    CmdbRelation,
    RelationTrigger,
    TriggerExecutionLog,
)
from app.models.ci_instance import CiInstance
from app.models.department import Department
from app.models.role import UserRole, Role
from app.services.relation_service import (
    create_relation_with_validation,
    RelationServiceError,
    parse_relation_style,
)
from app.utils.auth import token_required, admin_required
from app.utils.decorators import log_operation
from app import db
import json

cmdb_relation_bp = Blueprint('cmdb_relation', __name__, url_prefix='/api/v1/cmdb')


def _get_child_department_ids(parent_id):
    children = Department.query.filter_by(parent_id=parent_id).all()
    ids = []
    for child in children:
        ids.append(child.id)
        ids.extend(_get_child_department_ids(child.id))
    return ids


def _get_user_data_scope(user):
    if user.is_admin:
        return 'all'

    scopes = set()
    user_roles = UserRole.query.filter_by(user_id=user.id).all()
    for user_role in user_roles:
        role = Role.query.get(user_role.role_id)
        if not role:
            continue
        data_permissions = role.get_data_permissions()
        scope = data_permissions.get('scope', 'self')
        scopes.add(scope)

    if 'all' in scopes:
        return 'all'
    if 'department_and_children' in scopes:
        return 'department_and_children'
    if 'department' in scopes:
        return 'department'
    return 'self'


def _get_accessible_department_ids(user, scope):
    if scope != 'department_and_children' or not user.department_id:
        return set()
    ids = set(_get_child_department_ids(user.department_id))
    ids.add(user.department_id)
    return ids


def _can_access_instance(ci, user, scope, dept_ids):
    if user.is_admin or scope == 'all':
        return True

    if scope == 'department':
        if user.department_id and ci.department_id == user.department_id:
            return True
        return ci.created_by == user.id

    if scope == 'department_and_children':
        if ci.department_id in dept_ids:
            return True
        return ci.created_by == user.id

    return ci.created_by == user.id


def _parse_json_safe(value, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data
        except Exception:
            return default
    return default


def _extract_form_field_codes(form_config):
    result = []
    config_data = _parse_json_safe(form_config, [])
    if not isinstance(config_data, list):
        return result

    for item in config_data:
        if not isinstance(item, dict):
            continue
        props = item.get('props') if isinstance(item.get('props'), dict) else {}
        code = props.get('code')
        if code:
            result.append(code)
        children = item.get('children')
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_props = child.get('props') if isinstance(child.get('props'), dict) else {}
                child_code = child_props.get('code')
                if child_code:
                    result.append(child_code)
    return result


def _format_display_value(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ', '.join([str(v) for v in value if v is not None]).strip()
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _build_ci_display(ci):
    title = (ci.name or '').strip() or (ci.code or '')
    subtitles = []

    model = ci.model
    config_data = _parse_json_safe(model.config if model else {}, {}) if model else {}
    key_field_codes = config_data.get('key_field_codes', [])
    if not isinstance(key_field_codes, list):
        key_field_codes = []
    key_field_codes = [str(code).strip() for code in key_field_codes if str(code).strip()][:3]

    if key_field_codes:
        attrs = ci.get_attribute_values() if hasattr(ci, 'get_attribute_values') else {}
        for code in key_field_codes:
            value = _format_display_value(attrs.get(code))
            if value:
                subtitles.append(value)

    return {
        'display_title': title,
        'display_subtitles': subtitles,
        'model_icon': model.icon if model else 'AppstoreOutlined',
        'model_icon_url': config_data.get('icon_url') if isinstance(config_data, dict) else None,
    }


def _build_ci_node(ci, is_center=False):
    display_data = _build_ci_display(ci)
    return {
        'id': ci.id,
        'name': ci.name,
        'code': ci.code,
        'model_id': ci.model_id,
        'model_name': ci.model.name if ci.model else '',
        'model_icon': display_data['model_icon'],
        'model_icon_url': display_data['model_icon_url'],
        'display_title': display_data['display_title'],
        'display_subtitles': display_data['display_subtitles'],
        'is_center': is_center,
    }


def _collect_relations_by_depth(start_ci_id, max_depth, current_user, scope, dept_ids):
    visited_nodes = {start_ci_id: 0}
    visited_relations = set()
    queue = deque([(start_ci_id, 0)])
    relation_list = []

    while queue:
        current_ci_id, current_depth = queue.popleft()
        if current_depth >= max_depth:
            continue

        source_relations = CmdbRelation.query.filter_by(source_ci_id=current_ci_id).all()
        target_relations = CmdbRelation.query.filter_by(target_ci_id=current_ci_id).all()

        for rel in source_relations + target_relations:
            if rel.id in visited_relations:
                continue
            if not rel.source_ci or not rel.target_ci:
                continue
            if not _can_access_instance(rel.source_ci, current_user, scope, dept_ids):
                continue
            if not _can_access_instance(rel.target_ci, current_user, scope, dept_ids):
                continue

            visited_relations.add(rel.id)
            relation_list.append(rel)

            next_nodes = [rel.source_ci_id, rel.target_ci_id]
            for next_ci_id in next_nodes:
                next_depth = current_depth + 1
                existing_depth = visited_nodes.get(next_ci_id)
                if existing_depth is None or next_depth < existing_depth:
                    visited_nodes[next_ci_id] = next_depth
                    queue.append((next_ci_id, next_depth))

    return relation_list


def _build_topology_data(all_relations, model_id=None, keyword='', limit_nodes=True):
    nodes = []
    edges = []
    node_ids = set()
    kw = keyword.lower().strip() if keyword else ''

    def _match_ci_keyword(ci):
        if not kw:
            return True
        name = (ci.name or '').lower()
        code = (ci.code or '').lower()
        if kw in name or kw in code:
            return True

        try:
            attrs = ci.get_attribute_values() or {}
        except Exception:
            attrs = {}
        for value in attrs.values():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                text = ','.join([str(v) for v in value if v is not None]).lower()
            elif isinstance(value, dict):
                text = json.dumps(value, ensure_ascii=False).lower()
            else:
                text = str(value).lower()
            if kw in text:
                return True
        return False

    for rel in all_relations:
        source_ci = rel.source_ci
        target_ci = rel.target_ci

        if not source_ci or not target_ci:
            continue

        if model_id and source_ci.model_id != model_id and target_ci.model_id != model_id:
            continue

        if kw:
            source_match = _match_ci_keyword(source_ci)
            target_match = _match_ci_keyword(target_ci)
            if not source_match and not target_match:
                continue

        if source_ci.id not in node_ids:
            nodes.append(_build_ci_node(source_ci, is_center=False))
            node_ids.add(source_ci.id)

        if target_ci.id not in node_ids:
            nodes.append(_build_ci_node(target_ci, is_center=False))
            node_ids.add(target_ci.id)

        edges.append({
            'id': rel.id,
            'source': rel.source_ci_id,
            'target': rel.target_ci_id,
            'relation_type_id': rel.relation_type_id,
            'relation_type_name': rel.relation_type.name if rel.relation_type else '',
            'direction': rel.relation_type.direction if rel.relation_type else 'directed',
            'style': parse_relation_style(rel.relation_type.style) if rel.relation_type else {},
            'source_type': rel.source_type,
            'created_at': rel.created_at.isoformat() if rel.created_at else None,
        })

    if limit_nodes and len(nodes) > 500:
        nodes = nodes[:500]
        limited_ids = {n['id'] for n in nodes}
        edges = [e for e in edges if e['source'] in limited_ids and e['target'] in limited_ids]

    return nodes, edges

# ==================== 关系类型管理 ====================

@cmdb_relation_bp.route('/relation-types', methods=['GET'])
@token_required
def get_relation_types():
    """获取关系类型列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '')
    
    query = RelationType.query
    
    if keyword:
        query = query.filter(
            db.or_(
                RelationType.name.contains(keyword),
                RelationType.code.contains(keyword)
            )
        )
    
    pagination = query.order_by(RelationType.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [rt.to_dict() for rt in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@cmdb_relation_bp.route('/relation-types', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='relation_type')
def create_relation_type():
    """新增关系类型"""
    data = request.get_json()
    
    if not data.get('code') or not data.get('name'):
        return jsonify({'code': 400, 'message': '编码和名称不能为空'}), 400
    
    if RelationType.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '关系类型编码已存在'}), 400
    
    relation_type = RelationType(
        code=data['code'],
        name=data['name'],
        source_label=data.get('source_label', ''),
        target_label=data.get('target_label', ''),
        direction=data.get('direction', 'directed'),
        source_model_ids=json.dumps(data.get('source_model_ids', [])),
        target_model_ids=json.dumps(data.get('target_model_ids', [])),
        cardinality=data.get('cardinality', 'many_many'),
        allow_self_loop=data.get('allow_self_loop', False),
        description=data.get('description', ''),
        style=json.dumps(data.get('style', {}))
    )
    relation_type.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': relation_type.to_dict()
    })


@cmdb_relation_bp.route('/relation-types/<int:id>', methods=['GET'])
@token_required
def get_relation_type(id):
    """获取关系类型详情"""
    relation_type = RelationType.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': relation_type.to_dict()
    })


@cmdb_relation_bp.route('/relation-types/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='relation_type')
def update_relation_type(id):
    """更新关系类型"""
    relation_type = RelationType.query.get_or_404(id)
    data = request.get_json()
    
    if data.get('code') and data['code'] != relation_type.code:
        if RelationType.query.filter_by(code=data['code']).first():
            return jsonify({'code': 400, 'message': '关系类型编码已存在'}), 400
        relation_type.code = data['code']
    
    relation_type.name = data.get('name', relation_type.name)
    relation_type.source_label = data.get('source_label', relation_type.source_label)
    relation_type.target_label = data.get('target_label', relation_type.target_label)
    relation_type.direction = data.get('direction', relation_type.direction)
    
    if 'source_model_ids' in data:
        relation_type.source_model_ids = json.dumps(data['source_model_ids'])
    if 'target_model_ids' in data:
        relation_type.target_model_ids = json.dumps(data['target_model_ids'])
    
    relation_type.cardinality = data.get('cardinality', relation_type.cardinality)
    relation_type.allow_self_loop = data.get('allow_self_loop', relation_type.allow_self_loop)
    relation_type.description = data.get('description', relation_type.description)
    
    if 'style' in data:
        relation_type.style = json.dumps(data['style'])
    
    relation_type.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': relation_type.to_dict()
    })


@cmdb_relation_bp.route('/relation-types/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='relation_type')
def delete_relation_type(id):
    """删除关系类型"""
    relation_type = RelationType.query.get_or_404(id)
    
    # 检查是否有关联的关系实例
    if CmdbRelation.query.filter_by(relation_type_id=id).count() > 0:
        return jsonify({'code': 400, 'message': '该关系类型下存在关系实例，无法删除'}), 400
    
    # 检查是否有关联的触发器
    if RelationTrigger.query.filter_by(relation_type_id=id).count() > 0:
        return jsonify({'code': 400, 'message': '该关系类型下存在触发器，无法删除'}), 400
    
    relation_type.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })

# ==================== 关系实例管理 ====================

@cmdb_relation_bp.route('/instances/<int:id>/relations', methods=['GET'])
@token_required
def get_instance_relations(id):
    """获取 CI 的关联关系"""
    depth = request.args.get('depth', 1, type=int)
    depth = max(1, min(4, depth))
    
    ci = CiInstance.query.get_or_404(id)
    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)

    if not _can_access_instance(ci, current_user, scope, dept_ids):
        return jsonify({'code': 403, 'message': '无权限查看此CI'}), 403
    
    nodes = []
    edges = []
    out_relations = []
    in_relations = []
    
    # 添加中心节点
    nodes.append(_build_ci_node(ci, is_center=True))
    
    relation_pool = _collect_relations_by_depth(
        start_ci_id=id,
        max_depth=depth,
        current_user=current_user,
        scope=scope,
        dept_ids=dept_ids,
    )

    # 获取中心CI的出边关系（列表）
    source_relations = [rel for rel in relation_pool if rel.source_ci_id == id]
    for rel in source_relations:
        target_ci = rel.target_ci
        if target_ci:
            # 添加节点
            if not any(n['id'] == target_ci.id for n in nodes):
                nodes.append(_build_ci_node(target_ci, is_center=False))
            # 添加边
            edges.append({
                'id': rel.id,
                'source': rel.source_ci_id,
                'target': rel.target_ci_id,
                'relation_type_id': rel.relation_type_id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_type': rel.source_type,
                'direction': rel.relation_type.direction if rel.relation_type else 'directed',
                'style': parse_relation_style(rel.relation_type.style) if rel.relation_type else {}
            })
            # 添加到出边列表
            target_display = _build_ci_display(target_ci)
            out_relations.append({
                'id': rel.id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'target_ci_id': target_ci.id,
                'target_ci_name': target_ci.name,
                'target_ci_code': target_ci.code,
                'target_ci_model_id': target_ci.model_id,
                'target_ci_model_name': target_ci.model.name if target_ci.model else '',
                'target_model_icon': target_display['model_icon'],
                'target_model_icon_url': target_display['model_icon_url'],
                'target_display_title': target_display['display_title'],
                'target_display_subtitles': target_display['display_subtitles'],
                'source_type': rel.source_type,
                'created_at': rel.created_at.isoformat() if rel.created_at else None
            })
    
    # 获取中心CI的入边关系（列表）
    target_relations = [rel for rel in relation_pool if rel.target_ci_id == id]
    for rel in target_relations:
        source_ci = rel.source_ci
        if source_ci:
            # 添加节点
            if not any(n['id'] == source_ci.id for n in nodes):
                nodes.append(_build_ci_node(source_ci, is_center=False))
            # 添加边
            edges.append({
                'id': rel.id,
                'source': rel.source_ci_id,
                'target': rel.target_ci_id,
                'relation_type_id': rel.relation_type_id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_type': rel.source_type,
                'direction': rel.relation_type.direction if rel.relation_type else 'directed',
                'style': parse_relation_style(rel.relation_type.style) if rel.relation_type else {}
            })
            # 添加到入边列表
            source_display = _build_ci_display(source_ci)
            in_relations.append({
                'id': rel.id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_ci_id': source_ci.id,
                'source_ci_name': source_ci.name,
                'source_ci_code': source_ci.code,
                'source_ci_model_id': source_ci.model_id,
                'source_ci_model_name': source_ci.model.name if source_ci.model else '',
                'source_model_icon': source_display['model_icon'],
                'source_model_icon_url': source_display['model_icon_url'],
                'source_display_title': source_display['display_title'],
                'source_display_subtitles': source_display['display_subtitles'],
                'source_type': rel.source_type,
                'created_at': rel.created_at.isoformat() if rel.created_at else None
            })

    # depth > 1 时，补充多层节点和边（不影响中心CI关系列表）
    for rel in relation_pool:
        if rel.source_ci_id == id or rel.target_ci_id == id:
            continue

        if rel.source_ci and not any(n['id'] == rel.source_ci_id for n in nodes):
            nodes.append(_build_ci_node(rel.source_ci, is_center=False))
        if rel.target_ci and not any(n['id'] == rel.target_ci_id for n in nodes):
            nodes.append(_build_ci_node(rel.target_ci, is_center=False))

        if not any(e['id'] == rel.id for e in edges):
            edges.append({
                'id': rel.id,
                'source': rel.source_ci_id,
                'target': rel.target_ci_id,
                'relation_type_id': rel.relation_type_id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_type': rel.source_type,
                'direction': rel.relation_type.direction if rel.relation_type else 'directed',
                'style': parse_relation_style(rel.relation_type.style) if rel.relation_type else {}
            })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'nodes': nodes,
            'edges': edges,
            'out_relations': out_relations,
            'in_relations': in_relations
        }
    })


@cmdb_relation_bp.route('/relations', methods=['POST'])
@token_required
@log_operation(operation_type='CREATE', operation_object='relation')
def create_relation():
    """新增关系"""
    data = request.get_json()
    
    source_ci_id = data.get('source_ci_id')
    target_ci_id = data.get('target_ci_id')
    relation_type_id = data.get('relation_type_id')
    
    if not source_ci_id or not target_ci_id or not relation_type_id:
        return jsonify({'code': 400, 'message': '参数不完整'}), 400
    
    source_ci = CiInstance.query.get(source_ci_id)
    target_ci = CiInstance.query.get(target_ci_id)

    if not source_ci or not target_ci:
        return jsonify({'code': 404, 'message': '资源不存在'}), 404

    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)

    if not _can_access_instance(source_ci, current_user, scope, dept_ids):
        return jsonify({'code': 403, 'message': '无权限操作源CI'}), 403
    if not _can_access_instance(target_ci, current_user, scope, dept_ids):
        return jsonify({'code': 403, 'message': '无权限操作目标CI'}), 403

    try:
        relation = create_relation_with_validation(
            source_ci_id=source_ci_id,
            target_ci_id=target_ci_id,
            relation_type_id=relation_type_id,
            source_type='manual',
        )
    except RelationServiceError as exc:
        return jsonify({'code': exc.status_code, 'message': exc.message}), exc.status_code
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': relation.to_dict()
    })


@cmdb_relation_bp.route('/relations/<int:id>', methods=['DELETE'])
@token_required
@log_operation(operation_type='DELETE', operation_object='relation')
def delete_relation(id):
    """删除关系"""
    relation = CmdbRelation.query.get_or_404(id)
    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)

    if not relation.source_ci or not relation.target_ci:
        return jsonify({'code': 404, 'message': '资源不存在'}), 404

    if not _can_access_instance(relation.source_ci, current_user, scope, dept_ids):
        return jsonify({'code': 403, 'message': '无权限删除该关系'}), 403
    if not _can_access_instance(relation.target_ci, current_user, scope, dept_ids):
        return jsonify({'code': 403, 'message': '无权限删除该关系'}), 403

    relation.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })

# ==================== 拓扑图数据 ====================

@cmdb_relation_bp.route('/topology', methods=['GET'])
@token_required
def get_topology():
    """获取拓扑图数据"""
    model_id = request.args.get('model_id', type=int)
    ci_id = request.args.get('ci_id', type=int)
    keyword = request.args.get('keyword', '')
    depth = request.args.get('depth', 1, type=int)
    depth = max(1, min(4, depth))
    
    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)
    
    # 如果指定了 CI ID，从该 CI 开始按 depth 展开
    if ci_id:
        all_relations = _collect_relations_by_depth(
            start_ci_id=ci_id,
            max_depth=depth,
            current_user=current_user,
            scope=scope,
            dept_ids=dept_ids,
        )
        
        center_ci = CiInstance.query.get(ci_id)
        if center_ci:
            if not _can_access_instance(center_ci, current_user, scope, dept_ids):
                return jsonify({'code': 403, 'message': '无权限查看此CI'}), 403
    else:
        all_relations = []
        for rel in CmdbRelation.query.all():
            if not rel.source_ci or not rel.target_ci:
                continue
            if not _can_access_instance(rel.source_ci, current_user, scope, dept_ids):
                continue
            if not _can_access_instance(rel.target_ci, current_user, scope, dept_ids):
                continue
            all_relations.append(rel)

    topology_nodes, topology_edges = _build_topology_data(
        all_relations=all_relations,
        model_id=model_id,
        keyword=keyword,
    )

    # 指定起点时保留中心节点，即使其没有命中过滤
    if ci_id:
        center_exists = any(n['id'] == ci_id for n in topology_nodes)
        center_ci = CiInstance.query.get(ci_id)
        if center_ci and not center_exists:
            topology_nodes.insert(0, _build_ci_node(center_ci, is_center=True))
            topology_nodes = topology_nodes[:500]
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'nodes': topology_nodes,
            'edges': topology_edges
        }
    })


@cmdb_relation_bp.route('/topology/export', methods=['GET'])
@token_required
def export_topology():
    """导出拓扑图数据（CSV）"""
    export_format = request.args.get('format', 'csv')
    model_id = request.args.get('model_id', type=int)
    ci_id = request.args.get('ci_id', type=int)
    keyword = request.args.get('keyword', '')
    depth = request.args.get('depth', 1, type=int)
    depth = max(1, min(4, depth))

    if export_format not in ['csv', 'excel']:
        return jsonify({'code': 400, 'message': '不支持的导出格式'}), 400

    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)

    if ci_id:
        center_ci = CiInstance.query.get(ci_id)
        if center_ci and not _can_access_instance(center_ci, current_user, scope, dept_ids):
            return jsonify({'code': 403, 'message': '无权限查看此CI'}), 403
        all_relations = _collect_relations_by_depth(
            start_ci_id=ci_id,
            max_depth=depth,
            current_user=current_user,
            scope=scope,
            dept_ids=dept_ids,
        )
    else:
        all_relations = []
        for rel in CmdbRelation.query.all():
            if not rel.source_ci or not rel.target_ci:
                continue
            if not _can_access_instance(rel.source_ci, current_user, scope, dept_ids):
                continue
            if not _can_access_instance(rel.target_ci, current_user, scope, dept_ids):
                continue
            all_relations.append(rel)

    _, edges = _build_topology_data(
        all_relations=all_relations,
        model_id=model_id,
        keyword=keyword,
        limit_nodes=False,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'relation_id',
        'source_ci_id',
        'source_ci_name',
        'source_ci_code',
        'source_model_name',
        'target_ci_id',
        'target_ci_name',
        'target_ci_code',
        'target_model_name',
        'relation_type_id',
        'relation_type_name',
        'direction',
        'source_type',
        'created_at',
    ])

    for edge in edges:
        rel = next((r for r in all_relations if r.id == edge['id']), None)
        if not rel or not rel.source_ci or not rel.target_ci:
            continue
        writer.writerow([
            rel.id,
            rel.source_ci_id,
            rel.source_ci.name,
            rel.source_ci.code,
            rel.source_ci.model.name if rel.source_ci.model else '',
            rel.target_ci_id,
            rel.target_ci.name,
            rel.target_ci.code,
            rel.target_ci.model.name if rel.target_ci.model else '',
            rel.relation_type_id,
            rel.relation_type.name if rel.relation_type else '',
            rel.relation_type.direction if rel.relation_type else 'directed',
            rel.source_type,
            rel.created_at.isoformat() if rel.created_at else '',
        ])

    content = output.getvalue()
    output.close()

    filename_suffix = datetime.now().strftime('%Y%m%d%H%M%S')
    if export_format == 'excel':
        # 当前无 xlsx 依赖，excel 格式先返回 CSV 文件，便于 Excel 打开
        filename = f'topology_{filename_suffix}.csv'
    else:
        filename = f'topology_{filename_suffix}.csv'

    response = Response(
        content,
        mimetype='text/csv; charset=utf-8'
    )
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

# ==================== 关系触发器管理 ====================

@cmdb_relation_bp.route('/relation-triggers', methods=['GET'])
@token_required
def get_relation_triggers():
    """获取触发器列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '')
    
    query = RelationTrigger.query
    
    if keyword:
        query = query.filter(RelationTrigger.name.contains(keyword))
    
    pagination = query.order_by(RelationTrigger.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [rt.to_dict() for rt in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@cmdb_relation_bp.route('/relation-triggers', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='relation_trigger')
def create_relation_trigger():
    """新增触发器"""
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'code': 400, 'message': '名称不能为空'}), 400
    
    trigger = RelationTrigger(
        name=data['name'],
        source_model_id=data.get('source_model_id'),
        target_model_id=data.get('target_model_id'),
        relation_type_id=data.get('relation_type_id'),
        trigger_type=data.get('trigger_type', 'reference'),
        trigger_condition=json.dumps(data.get('trigger_condition', {})),
        is_active=data.get('is_active', True),
        description=data.get('description', '')
    )
    trigger.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': trigger.to_dict()
    })


@cmdb_relation_bp.route('/relation-triggers/<int:id>', methods=['GET'])
@token_required
def get_relation_trigger(id):
    """获取触发器详情"""
    trigger = RelationTrigger.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': trigger.to_dict()
    })


@cmdb_relation_bp.route('/relation-triggers/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='relation_trigger')
def update_relation_trigger(id):
    """更新触发器"""
    trigger = RelationTrigger.query.get_or_404(id)
    data = request.get_json()
    
    trigger.name = data.get('name', trigger.name)
    trigger.source_model_id = data.get('source_model_id', trigger.source_model_id)
    trigger.target_model_id = data.get('target_model_id', trigger.target_model_id)
    trigger.relation_type_id = data.get('relation_type_id', trigger.relation_type_id)
    trigger.trigger_type = data.get('trigger_type', trigger.trigger_type)
    
    if 'trigger_condition' in data:
        trigger.trigger_condition = json.dumps(data['trigger_condition'])
    
    trigger.is_active = data.get('is_active', trigger.is_active)
    trigger.description = data.get('description', trigger.description)
    
    trigger.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': trigger.to_dict()
    })


@cmdb_relation_bp.route('/relation-triggers/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='relation_trigger')
def delete_relation_trigger(id):
    """删除触发器"""
    trigger = RelationTrigger.query.get_or_404(id)
    TriggerExecutionLog.query.filter_by(trigger_id=id).delete(
        synchronize_session=False
    )
    trigger.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


@cmdb_relation_bp.route('/relation-triggers/<int:id>/toggle', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='relation_trigger')
def toggle_relation_trigger(id):
    """启用/禁用触发器"""
    trigger = RelationTrigger.query.get_or_404(id)
    trigger.is_active = not trigger.is_active
    trigger.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': trigger.to_dict()
    })
