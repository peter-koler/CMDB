from flask import Blueprint, request, jsonify, Response, current_app
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
from app.services.trigger_service import process_trigger_for_model
from app.tasks.scheduler import add_trigger_scan_job, get_scheduled_jobs, remove_trigger_scan_job
from app.models.ci_instance import CiInstance
from app.models.hertzbeat_models import SingleAlert, Monitor
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
from apscheduler.triggers.cron import CronTrigger

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


def _parse_id_list_param(name, single_name=None):
    values = []
    raw_values = request.args.getlist(name)
    if not raw_values and single_name:
        single = request.args.get(single_name)
        if single is not None:
            raw_values = [single]
    for raw in raw_values:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        for part in [segment.strip() for segment in text.split(',')]:
            if not part:
                continue
            try:
                values.append(int(part))
            except (TypeError, ValueError):
                continue
    output = []
    seen = set()
    for value in values:
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _collect_open_alert_ci_ids(ci_nodes):
    ci_id_set = set()
    ci_code_to_id = {}
    ci_code_lower_to_id = {}
    ci_name_lower_to_id = {}
    for node in (ci_nodes or []):
        try:
            ci_id = int(node.get('id') or 0)
        except (TypeError, ValueError):
            ci_id = 0
        if ci_id <= 0:
            continue
        ci_id_set.add(ci_id)
        code = str(node.get('code') or '').strip()
        if code:
            ci_code_to_id[code] = ci_id
            ci_code_lower_to_id[code.lower()] = ci_id
        name = str(node.get('name') or '').strip()
        if name:
            ci_name_lower_to_id[name.lower()] = ci_id
    if not ci_id_set:
        return set()
    open_alert_ci_ids = set()
    alerts = SingleAlert.query.filter_by(status='firing').all()
    monitor_ci_binding_cache = {}
    for alert in alerts:
        annotations = alert.annotations if hasattr(alert, 'annotations') else {}
        labels = alert.labels if hasattr(alert, 'labels') else {}
        if not isinstance(annotations, dict):
            annotations = {}
        if not isinstance(labels, dict):
            labels = {}

        ci_id_candidates = [
            annotations.get('ci_id'),
            annotations.get('ci.id'),
            annotations.get('ciId'),
            labels.get('ci_id'),
            labels.get('ci.id'),
            labels.get('ciId'),
        ]
        matched = False
        for candidate in ci_id_candidates:
            try:
                ci_id = int(candidate or 0)
            except (TypeError, ValueError):
                ci_id = 0
            if ci_id > 0 and ci_id in ci_id_set:
                open_alert_ci_ids.add(ci_id)
                matched = True
                break
        if matched:
            continue

        ci_code_candidates = [
            annotations.get('ci_code'),
            annotations.get('ci.code'),
            annotations.get('ciCode'),
            annotations.get('ci_name'),
            annotations.get('ci.name'),
            annotations.get('ciName'),
            labels.get('ci_code'),
            labels.get('ci.code'),
            labels.get('ciCode'),
            labels.get('ci_name'),
            labels.get('ci.name'),
            labels.get('ciName'),
        ]
        for candidate in ci_code_candidates:
            code = str(candidate or '').strip()
            if not code:
                continue
            ci_id = (
                ci_code_to_id.get(code)
                or ci_code_lower_to_id.get(code.lower())
                or ci_name_lower_to_id.get(code.lower())
            )
            if ci_id:
                open_alert_ci_ids.add(ci_id)
                matched = True
                break
        if matched:
            continue

        content_text = str(getattr(alert, 'content', '') or '').strip()
        if content_text:
            lowered_content = content_text.lower()
            for code, ci_id in ci_code_to_id.items():
                if code and code.lower() in lowered_content:
                    open_alert_ci_ids.add(ci_id)
                    matched = True
                    break
            if matched:
                continue
            for name_lower, ci_id in ci_name_lower_to_id.items():
                if name_lower and name_lower in lowered_content:
                    open_alert_ci_ids.add(ci_id)
                    break
        if matched:
            continue

        monitor_id_candidates = [
            annotations.get('monitor_id'),
            annotations.get('monitor.id'),
            annotations.get('monitorId'),
            labels.get('monitor_id'),
            labels.get('monitor.id'),
            labels.get('monitorId'),
        ]
        monitor_id = 0
        for candidate in monitor_id_candidates:
            try:
                monitor_id = int(candidate or 0)
            except (TypeError, ValueError):
                monitor_id = 0
            if monitor_id > 0:
                break
        if monitor_id <= 0:
            continue
        if monitor_id in monitor_ci_binding_cache:
            mapped_ci_id = monitor_ci_binding_cache[monitor_id]
        else:
            mapped_ci_id = 0
            monitor_row = Monitor.query.get(monitor_id)
            if monitor_row:
                try:
                    monitor_annotations = json.loads(monitor_row.annotations_json or '{}')
                except Exception:
                    monitor_annotations = {}
                if isinstance(monitor_annotations, dict):
                    try:
                        candidate_ci_id = int(monitor_annotations.get('ci_id') or 0)
                    except (TypeError, ValueError):
                        candidate_ci_id = 0
                    if candidate_ci_id > 0:
                        mapped_ci_id = candidate_ci_id
                    else:
                        candidate_ci_code = str(monitor_annotations.get('ci_code') or '').strip()
                        if candidate_ci_code:
                            mapped_ci_id = (
                                ci_code_to_id.get(candidate_ci_code)
                                or ci_code_lower_to_id.get(candidate_ci_code.lower())
                                or 0
                            )
            monitor_ci_binding_cache[monitor_id] = mapped_ci_id
        if mapped_ci_id and mapped_ci_id in ci_id_set:
            open_alert_ci_ids.add(mapped_ci_id)
    return open_alert_ci_ids


def _get_topology_depth_limit():
    try:
        depth_limit = int(current_app.config.get('CMDB_TOPOLOGY_MAX_DEPTH', 10))
    except (TypeError, ValueError):
        depth_limit = 10
    return max(1, depth_limit)


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


def _match_ci_keyword(ci, keyword=''):
    kw = keyword.lower().strip() if keyword else ''
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


def _build_topology_data(all_relations, model_id=None, model_ids=None, keyword='', limit_nodes=True):
    nodes = []
    edges = []
    node_ids = set()
    kw = keyword.lower().strip() if keyword else ''
    model_id_set = set()
    if model_ids:
        for value in model_ids:
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                continue
            if ivalue > 0:
                model_id_set.add(ivalue)
    elif model_id:
        model_id_set = {model_id}

    for rel in all_relations:
        source_ci = rel.source_ci
        target_ci = rel.target_ci

        if not source_ci or not target_ci:
            continue

        if model_id_set and source_ci.model_id not in model_id_set and target_ci.model_id not in model_id_set:
            continue

        if kw:
            source_match = _match_ci_keyword(source_ci, kw)
            target_match = _match_ci_keyword(target_ci, kw)
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
        source_model_ids='[]',
        target_model_ids='[]',
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
    relation_type.source_model_ids = '[]'
    relation_type.target_model_ids = '[]'
    
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
    model_ids = _parse_id_list_param('model_ids', single_name='model_id')
    ci_ids = _parse_id_list_param('ci_ids', single_name='ci_id')
    keyword = request.args.get('keyword', '')
    depth = request.args.get('depth', 1, type=int)
    depth = max(1, depth)
    depth_limit = _get_topology_depth_limit()
    if depth > depth_limit:
        return jsonify({
            'code': 400,
            'message': f'深度不能超过 {depth_limit} 层'
        }), 400
    
    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)
    
    # 如果指定了 CI ID，从这些 CI 开始按 depth 展开并去重
    if ci_ids:
        all_relations = []
        center_cis = []
        relation_ids = set()
        for ci_id in ci_ids:
            center_ci = CiInstance.query.get(ci_id)
            if center_ci and not _can_access_instance(center_ci, current_user, scope, dept_ids):
                return jsonify({'code': 403, 'message': '无权限查看此CI'}), 403
            if center_ci:
                center_cis.append(center_ci)
            related_relations = _collect_relations_by_depth(
                start_ci_id=ci_id,
                max_depth=depth,
                current_user=current_user,
                scope=scope,
                dept_ids=dept_ids,
            )
            for rel in related_relations:
                if rel.id in relation_ids:
                    continue
                relation_ids.add(rel.id)
                all_relations.append(rel)
    else:
        all_relations = []
        center_cis = []
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
        model_ids=model_ids,
        keyword=keyword,
        limit_nodes=not bool(model_ids or ci_ids),
    )

    # 指定起点时保留中心节点，即使其没有命中过滤
    if center_cis:
        existing_ids = {n['id'] for n in topology_nodes}
        for center_ci in center_cis:
            if center_ci.id in existing_ids:
                continue
            topology_nodes.insert(0, _build_ci_node(center_ci, is_center=True))
            existing_ids.add(center_ci.id)

    # 补齐无关系的 CI：用户筛选后应展示命中的全部 CI，而不仅是有关系的 CI
    if model_ids or ci_ids:
        ci_query = CiInstance.query
        if model_ids and ci_ids:
            ci_query = ci_query.filter(
                db.or_(
                    CiInstance.model_id.in_(model_ids),
                    CiInstance.id.in_(ci_ids),
                )
            )
        elif model_ids:
            ci_query = ci_query.filter(CiInstance.model_id.in_(model_ids))
        elif ci_ids:
            ci_query = ci_query.filter(CiInstance.id.in_(ci_ids))

        existing_ids = {n['id'] for n in topology_nodes}
        for ci in ci_query.all():
            if not _can_access_instance(ci, current_user, scope, dept_ids):
                continue
            if not _match_ci_keyword(ci, keyword):
                continue
            if ci.id in existing_ids:
                continue
            topology_nodes.append(_build_ci_node(ci, is_center=False))
            existing_ids.add(ci.id)

    open_alert_ci_ids = _collect_open_alert_ci_ids(topology_nodes)
    for node in topology_nodes:
        node['has_open_alert'] = node.get('id') in open_alert_ci_ids
    
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
    model_ids = _parse_id_list_param('model_ids', single_name='model_id')
    ci_ids = _parse_id_list_param('ci_ids', single_name='ci_id')
    keyword = request.args.get('keyword', '')
    depth = request.args.get('depth', 1, type=int)
    depth = max(1, depth)
    depth_limit = _get_topology_depth_limit()
    if depth > depth_limit:
        return jsonify({
            'code': 400,
            'message': f'深度不能超过 {depth_limit} 层'
        }), 400

    if export_format not in ['csv', 'excel']:
        return jsonify({'code': 400, 'message': '不支持的导出格式'}), 400

    current_user = request.current_user
    scope = _get_user_data_scope(current_user)
    dept_ids = _get_accessible_department_ids(current_user, scope)

    if ci_ids:
        all_relations = []
        relation_ids = set()
        for ci_id in ci_ids:
            center_ci = CiInstance.query.get(ci_id)
            if center_ci and not _can_access_instance(center_ci, current_user, scope, dept_ids):
                return jsonify({'code': 403, 'message': '无权限查看此CI'}), 403
            related_relations = _collect_relations_by_depth(
                start_ci_id=ci_id,
                max_depth=depth,
                current_user=current_user,
                scope=scope,
                dept_ids=dept_ids,
            )
            for rel in related_relations:
                if rel.id in relation_ids:
                    continue
                relation_ids.add(rel.id)
                all_relations.append(rel)
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
        model_ids=model_ids,
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
    model_id = request.args.get('model_id', type=int)
    active_only = request.args.get('active_only')
    
    query = RelationTrigger.query
    
    if keyword:
        query = query.filter(RelationTrigger.name.contains(keyword))
    if model_id:
        query = query.filter(
            db.or_(
                RelationTrigger.source_model_id == model_id,
                RelationTrigger.target_model_id == model_id
            )
        )
    if active_only not in (None, ""):
        is_active = str(active_only).strip().lower() in {"1", "true", "yes", "on"}
        query = query.filter(RelationTrigger.is_active.is_(is_active))
    
    pagination = query.order_by(RelationTrigger.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    scheduled_jobs = get_scheduled_jobs()
    trigger_next_run_map = {
        job["trigger_id"]: job.get("next_run_time")
        for job in scheduled_jobs
        if job.get("job_type") == "trigger" and job.get("trigger_id") is not None
    }
    trigger_ids = [rt.id for rt in pagination.items]
    latest_logs = {}
    if trigger_ids:
        latest_log_rows = (
            TriggerExecutionLog.query
            .filter(TriggerExecutionLog.trigger_id.in_(trigger_ids))
            .order_by(TriggerExecutionLog.trigger_id.asc(), TriggerExecutionLog.created_at.desc())
            .all()
        )
        for row in latest_log_rows:
            if row.trigger_id not in latest_logs:
                latest_logs[row.trigger_id] = row
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [
                {
                    **rt.to_dict(),
                    'next_run_at': trigger_next_run_map.get(rt.id),
                    'last_run_at': latest_logs[rt.id].created_at.isoformat() if latest_logs.get(rt.id) and latest_logs[rt.id].created_at else None,
                    'last_run_status': latest_logs[rt.id].status if latest_logs.get(rt.id) else 'none',
                }
                for rt in pagination.items
            ],
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

    batch_scan_enabled = data.get('batch_scan_enabled', False)
    batch_scan_cron = (data.get('batch_scan_cron') or '').strip()
    if batch_scan_cron:
        try:
            CronTrigger.from_crontab(batch_scan_cron)
        except Exception as exc:
            return jsonify({'code': 400, 'message': f'无效的 Cron 表达式: {exc}'}), 400
    if batch_scan_enabled and not batch_scan_cron:
        return jsonify({'code': 400, 'message': '启用定期扫描时 Cron 表达式不能为空'}), 400
    
    trigger = RelationTrigger(
        name=data['name'],
        source_model_id=data.get('source_model_id'),
        target_model_id=data.get('target_model_id'),
        relation_type_id=data.get('relation_type_id'),
        trigger_type=data.get('trigger_type', 'reference'),
        trigger_condition=json.dumps(data.get('trigger_condition', {})),
        is_active=data.get('is_active', True),
        batch_scan_enabled=batch_scan_enabled,
        batch_scan_cron=batch_scan_cron,
        description=data.get('description', '')
    )
    trigger.save()

    if trigger.is_active and trigger.batch_scan_enabled and trigger.batch_scan_cron:
        add_trigger_scan_job(trigger.id, trigger.batch_scan_cron)
    
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
    batch_scan_enabled = trigger.batch_scan_enabled
    batch_scan_cron = trigger.batch_scan_cron or ''
    if 'batch_scan_enabled' in data:
        trigger.batch_scan_enabled = data.get('batch_scan_enabled', False)
        batch_scan_enabled = trigger.batch_scan_enabled
    if 'batch_scan_cron' in data:
        cron = (data.get('batch_scan_cron') or '').strip()
        if cron:
            try:
                CronTrigger.from_crontab(cron)
            except Exception as exc:
                return jsonify({'code': 400, 'message': f'无效的 Cron 表达式: {exc}'}), 400
        trigger.batch_scan_cron = cron
        batch_scan_cron = cron
    if batch_scan_enabled and not batch_scan_cron:
        return jsonify({'code': 400, 'message': '启用定期扫描时 Cron 表达式不能为空'}), 400
    trigger.description = data.get('description', trigger.description)
    
    trigger.save()

    if trigger.is_active and trigger.batch_scan_enabled and trigger.batch_scan_cron:
        add_trigger_scan_job(trigger.id, trigger.batch_scan_cron)
    else:
        remove_trigger_scan_job(trigger.id)
    
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
    remove_trigger_scan_job(id)
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

    if trigger.is_active and trigger.batch_scan_enabled and trigger.batch_scan_cron:
        add_trigger_scan_job(trigger.id, trigger.batch_scan_cron)
    else:
        remove_trigger_scan_job(trigger.id)
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': trigger.to_dict()
    })


@cmdb_relation_bp.route('/relation-triggers/<int:id>/execute', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='relation_trigger')
def execute_relation_trigger(id):
    """立即执行当前触发器，重建源模型下实例关系"""
    trigger = RelationTrigger.query.get_or_404(id)
    result = process_trigger_for_model(trigger)
    return jsonify({
        'code': 200,
        'message': '执行完成',
        'data': {
            'trigger_id': trigger.id,
            'trigger_name': trigger.name,
            **result,
        }
    })
