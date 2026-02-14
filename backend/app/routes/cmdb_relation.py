from flask import Blueprint, request, jsonify
from datetime import datetime
from app.models.cmdb_relation import RelationType, CmdbRelation, RelationTrigger
from app.models.ci_instance import CiInstance
from app.models.cmdb_model import CmdbModel
from app.utils.auth import token_required, admin_required
from app.utils.decorators import log_operation
from app import db
import json

cmdb_relation_bp = Blueprint('cmdb_relation', __name__, url_prefix='/api/v1/cmdb')

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
    
    nodes = []
    edges = []
    out_relations = []
    in_relations = []
    
    # 添加中心节点
    nodes.append({
        'id': ci.id,
        'name': ci.name,
        'code': ci.code,
        'model_id': ci.model_id,
        'model_name': ci.model.name if ci.model else '',
        'model_icon': ci.model.icon if ci.model else 'AppstoreOutlined',
        'is_center': True
    })
    
    # 获取出边关系
    source_relations = CmdbRelation.query.filter_by(source_ci_id=id).all()
    for rel in source_relations:
        target_ci = rel.target_ci
        if target_ci:
            # 添加节点
            if not any(n['id'] == target_ci.id for n in nodes):
                nodes.append({
                    'id': target_ci.id,
                    'name': target_ci.name,
                    'code': target_ci.code,
                    'model_id': target_ci.model_id,
                    'model_name': target_ci.model.name if target_ci.model else '',
                    'model_icon': target_ci.model.icon if target_ci.model else 'AppstoreOutlined',
                    'is_center': False
                })
            # 添加边
            edges.append({
                'id': rel.id,
                'source': rel.source_ci_id,
                'target': rel.target_ci_id,
                'relation_type_id': rel.relation_type_id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_type': rel.source_type,
                'direction': rel.relation_type.direction if rel.relation_type else 'directed',
                'style': rel.relation_type.style if rel.relation_type else {}
            })
            # 添加到出边列表
            out_relations.append({
                'id': rel.id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'target_ci_id': target_ci.id,
                'target_ci_name': target_ci.name,
                'target_ci_code': target_ci.code,
                'target_ci_model_name': target_ci.model.name if target_ci.model else '',
                'source_type': rel.source_type,
                'created_at': rel.created_at.isoformat() if rel.created_at else None
            })
    
    # 获取入边关系
    target_relations = CmdbRelation.query.filter_by(target_ci_id=id).all()
    for rel in target_relations:
        source_ci = rel.source_ci
        if source_ci:
            # 添加节点
            if not any(n['id'] == source_ci.id for n in nodes):
                nodes.append({
                    'id': source_ci.id,
                    'name': source_ci.name,
                    'code': source_ci.code,
                    'model_id': source_ci.model_id,
                    'model_name': source_ci.model.name if source_ci.model else '',
                    'model_icon': source_ci.model.icon if source_ci.model else 'AppstoreOutlined',
                    'is_center': False
                })
            # 添加边
            edges.append({
                'id': rel.id,
                'source': rel.source_ci_id,
                'target': rel.target_ci_id,
                'relation_type_id': rel.relation_type_id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_type': rel.source_type,
                'direction': rel.relation_type.direction if rel.relation_type else 'directed',
                'style': rel.relation_type.style if rel.relation_type else {}
            })
            # 添加到入边列表
            in_relations.append({
                'id': rel.id,
                'relation_type_name': rel.relation_type.name if rel.relation_type else '',
                'source_ci_id': source_ci.id,
                'source_ci_name': source_ci.name,
                'source_ci_code': source_ci.code,
                'source_ci_model_name': source_ci.model.name if source_ci.model else '',
                'source_type': rel.source_type,
                'created_at': rel.created_at.isoformat() if rel.created_at else None
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
    
    # 获取相关对象
    source_ci = CiInstance.query.get(source_ci_id)
    target_ci = CiInstance.query.get(target_ci_id)
    relation_type = RelationType.query.get(relation_type_id)
    
    if not source_ci or not target_ci or not relation_type:
        return jsonify({'code': 404, 'message': '资源不存在'}), 404
    
    # 1. 唯一性检查
    existing = CmdbRelation.query.filter_by(
        source_ci_id=source_ci_id,
        target_ci_id=target_ci_id,
        relation_type_id=relation_type_id
    ).first()
    if existing:
        return jsonify({'code': 400, 'message': '该关系已存在'}), 400
    
    # 2. 自环检查
    if not relation_type.allow_self_loop and source_ci_id == target_ci_id:
        return jsonify({'code': 400, 'message': '不允许创建自环关系'}), 400
    
    # 3. 模型白名单检查
    source_model_ids = json.loads(relation_type.source_model_ids) if relation_type.source_model_ids else []
    target_model_ids = json.loads(relation_type.target_model_ids) if relation_type.target_model_ids else []
    
    if source_model_ids and source_ci.model_id not in source_model_ids:
        return jsonify({'code': 400, 'message': '该关系类型不允许此源模型'}), 400
    
    if target_model_ids and target_ci.model_id not in target_model_ids:
        return jsonify({'code': 400, 'message': '该关系类型不允许此目标模型'}), 400
    
    # 4. 基数限制检查
    if relation_type.cardinality == 'one_one':
        # 源只能有一个
        if CmdbRelation.query.filter_by(source_ci_id=source_ci_id, relation_type_id=relation_type_id).count() > 0:
            return jsonify({'code': 400, 'message': '源端已有此类型关系（1:1限制）'}), 400
        # 目标只能有一个
        if CmdbRelation.query.filter_by(target_ci_id=target_ci_id, relation_type_id=relation_type_id).count() > 0:
            return jsonify({'code': 400, 'message': '目标端已有此类型关系（1:1限制）'}), 400
    elif relation_type.cardinality == 'one_many':
        # 目标只能有一个
        if CmdbRelation.query.filter_by(target_ci_id=target_ci_id, relation_type_id=relation_type_id).count() > 0:
            return jsonify({'code': 400, 'message': '目标端已有此类型关系（1:N限制）'}), 400
    
    # 创建关系
    relation = CmdbRelation(
        source_ci_id=source_ci_id,
        target_ci_id=target_ci_id,
        relation_type_id=relation_type_id,
        source_type='manual'
    )
    relation.save()
    
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
    
    nodes = []
    edges = []
    
    # 基础查询
    query = CmdbRelation.query
    
    # 如果指定了 CI ID，从该 CI 开始
    if ci_id:
        # 获取该 CI 的出边和入边
        source_relations = CmdbRelation.query.filter_by(source_ci_id=ci_id).all()
        target_relations = CmdbRelation.query.filter_by(target_ci_id=ci_id).all()
        all_relations = source_relations + target_relations
        
        # 添加中心节点
        center_ci = CiInstance.query.get(ci_id)
        if center_ci:
            nodes.append({
                'id': center_ci.id,
                'name': center_ci.name,
                'code': center_ci.code,
                'model_id': center_ci.model_id,
                'model_name': center_ci.model.name if center_ci.model else '',
                'model_icon': center_ci.model.icon if center_ci.model else 'AppstoreOutlined'
            })
    else:
        # 否则获取所有关系
        all_relations = CmdbRelation.query.all()
    
    # 处理所有关系
    for rel in all_relations:
        source_ci = rel.source_ci
        target_ci = rel.target_ci
        
        if not source_ci or not target_ci:
            continue
        
        # 模型过滤
        if model_id:
            if source_ci.model_id != model_id and target_ci.model_id != model_id:
                continue
        
        # 关键词过滤
        if keyword:
            source_match = keyword.lower() in source_ci.name.lower() or keyword.lower() in source_ci.code.lower()
            target_match = keyword.lower() in target_ci.name.lower() or keyword.lower() in target_ci.code.lower()
            if not source_match and not target_match:
                continue
        
        # 添加源节点
        if not any(n['id'] == source_ci.id for n in nodes):
            nodes.append({
                'id': source_ci.id,
                'name': source_ci.name,
                'code': source_ci.code,
                'model_id': source_ci.model_id,
                'model_name': source_ci.model.name if source_ci.model else '',
                'model_icon': source_ci.model.icon if source_ci.model else 'AppstoreOutlined'
            })
        
        # 添加目标节点
        if not any(n['id'] == target_ci.id for n in nodes):
            nodes.append({
                'id': target_ci.id,
                'name': target_ci.name,
                'code': target_ci.code,
                'model_id': target_ci.model_id,
                'model_name': target_ci.model.name if target_ci.model else '',
                'model_icon': target_ci.model.icon if target_ci.model else 'AppstoreOutlined'
            })
        
        # 添加边
        edges.append({
            'id': rel.id,
            'source': rel.source_ci_id,
            'target': rel.target_ci_id,
            'relation_type_id': rel.relation_type_id,
            'relation_type_name': rel.relation_type.name if rel.relation_type else '',
            'direction': rel.relation_type.direction if rel.relation_type else 'directed',
            'style': rel.relation_type.style if rel.relation_type else {}
        })
    
    # 限制节点数量，避免过多
    if len(nodes) > 500:
        nodes = nodes[:500]
        node_ids = [n['id'] for n in nodes]
        edges = [e for e in edges if e['source'] in node_ids and e['target'] in node_ids]
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'nodes': nodes,
            'edges': edges
        }
    })

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
