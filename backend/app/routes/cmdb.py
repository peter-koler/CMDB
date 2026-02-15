from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime
from app.models.model_category import ModelCategory
from app.models.cmdb_model import CmdbModel, ModelType
from app.models.model_region import ModelRegion
from app.models.model_field import ModelField
from app.models.ci_instance import CiInstance
from app.models.cmdb_dict import CmdbDictType, CmdbDictItem
from app.utils.auth import token_required, admin_required
from app.utils.decorators import log_operation
from app import db
import json
import os
from werkzeug.utils import secure_filename

cmdb_bp = Blueprint('cmdb', __name__, url_prefix='/api/v1/cmdb')
MODEL_ICON_UPLOAD_FOLDER = 'model_icons'
MODEL_ICON_ALLOWED_EXTENSIONS = {'png', 'svg'}
MODEL_ICON_MAX_SIZE = 2 * 1024 * 1024
KEY_FIELD_ALLOWED_CONTROL_TYPES = {'text', 'textarea', 'number', 'date', 'datetime', 'select', 'radio'}


def _extract_form_fields(form_config):
    fields = {}
    config_data = form_config or []

    if isinstance(config_data, str):
        try:
            config_data = json.loads(config_data)
        except Exception:
            return fields

    if not isinstance(config_data, list):
        return fields

    for item in config_data:
        if not isinstance(item, dict):
            continue
        control_type = item.get('controlType')
        props = item.get('props') if isinstance(item.get('props'), dict) else {}
        code = props.get('code')
        if code:
            fields[code] = control_type

        children = item.get('children')
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_control_type = child.get('controlType')
                child_props = child.get('props') if isinstance(child.get('props'), dict) else {}
                child_code = child_props.get('code')
                if child_code:
                    fields[child_code] = child_control_type

    return fields


def _normalize_key_field_codes(codes):
    if codes is None:
        return None
    if not isinstance(codes, list):
        return []
    normalized = []
    seen = set()
    for code in codes:
        if code is None:
            continue
        value = str(code).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _validate_key_field_codes(form_config, key_field_codes):
    if key_field_codes is None:
        return None

    if len(key_field_codes) > 3:
        return '关键属性最多允许 3 个'

    if len(key_field_codes) == 0:
        return None

    field_map = _extract_form_fields(form_config)
    if not field_map:
        return '当前模型未配置可用字段，无法设置关键属性'

    for code in key_field_codes:
        if code not in field_map:
            return f'关键属性字段不存在: {code}'
        control_type = field_map.get(code)
        if control_type not in KEY_FIELD_ALLOWED_CONTROL_TYPES:
            return f'字段类型不支持作为关键属性: {code}'

    return None


def _parse_bool_query(value, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'y'}:
        return True
    if normalized in {'0', 'false', 'no', 'n'}:
        return False
    return default


def _build_dict_item_tree(items):
    item_map = {}
    roots = []

    for item in items:
        item_data = item.to_dict()
        item_data['children'] = []
        item_map[item.id] = item_data

    for item in items:
        current = item_map[item.id]
        if item.parent_id and item.parent_id in item_map:
            item_map[item.parent_id]['children'].append(current)
        else:
            roots.append(current)

    def sort_tree(nodes):
        nodes.sort(key=lambda node: (node.get('sort_order', 0), node.get('id', 0)))
        for node in nodes:
            sort_tree(node['children'])

    sort_tree(roots)
    return roots


def _is_descendant_item(target_item, parent_id):
    if not parent_id:
        return False

    current = CmdbDictItem.query.get(parent_id)
    while current:
        if current.id == target_item.id:
            return True
        if not current.parent_id:
            return False
        current = CmdbDictItem.query.get(current.parent_id)
    return False


# ==================== 模型目录管理 ====================

@cmdb_bp.route('/categories', methods=['GET'])
@token_required
@admin_required
def get_categories():
    """获取模型目录树"""
    root_categories = ModelCategory.query.filter_by(parent_id=None).order_by(ModelCategory.sort_order).all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [cat.to_dict() for cat in root_categories]
    })


@cmdb_bp.route('/categories', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='model_category')
def create_category():
    """创建模型目录"""
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '名称和编码不能为空'}), 400
    
    if ModelCategory.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '目录编码已存在'}), 400
    
    category = ModelCategory(
        name=data['name'],
        code=data['code'],
        parent_id=data.get('parent_id'),
        sort_order=data.get('sort_order', 0)
    )
    category.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': category.to_dict()
    })


@cmdb_bp.route('/categories/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='model_category')
def update_category(id):
    """更新模型目录"""
    category = ModelCategory.query.get_or_404(id)
    data = request.get_json()
    
    if data.get('code') and data['code'] != category.code:
        if ModelCategory.query.filter_by(code=data['code']).first():
            return jsonify({'code': 400, 'message': '目录编码已存在'}), 400
        category.code = data['code']
    
    category.name = data.get('name', category.name)
    category.parent_id = data.get('parent_id', category.parent_id)
    category.sort_order = data.get('sort_order', category.sort_order)
    category.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': category.to_dict()
    })


@cmdb_bp.route('/categories/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='model_category')
def delete_category(id):
    """删除模型目录"""
    category = ModelCategory.query.get_or_404(id)
    
    # 检查是否有子目录
    if category.children.count() > 0:
        return jsonify({'code': 400, 'message': '请先删除子目录'}), 400
    
    # 检查是否有模型
    if category.models.count() > 0:
        return jsonify({'code': 400, 'message': '该目录下存在模型，无法删除'}), 400
    
    category.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 模型类型管理 ====================

@cmdb_bp.route('/types', methods=['GET'])
@token_required
@admin_required
def get_model_types():
    """获取模型类型列表"""
    types = ModelType.query.all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': [t.to_dict() for t in types]
    })


@cmdb_bp.route('/types', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='model_type')
def create_model_type():
    """创建模型类型"""
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '名称和编码不能为空'}), 400
    
    if ModelType.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '类型编码已存在'}), 400
    
    model_type = ModelType(
        name=data['name'],
        code=data['code'],
        description=data.get('description')
    )
    model_type.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': model_type.to_dict()
    })


@cmdb_bp.route('/types/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='model_type')
def update_model_type(id):
    """更新模型类型"""
    model_type = ModelType.query.get_or_404(id)
    data = request.get_json()
    
    model_type.name = data.get('name', model_type.name)
    model_type.description = data.get('description', model_type.description)
    model_type.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': model_type.to_dict()
    })


@cmdb_bp.route('/types/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='model_type')
def delete_model_type(id):
    """删除模型类型"""
    model_type = ModelType.query.get_or_404(id)
    
    if model_type.models.count() > 0:
        return jsonify({'code': 400, 'message': '该类型下存在模型，无法删除'}), 400
    
    model_type.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 模型管理 ====================

@cmdb_bp.route('/models/tree', methods=['GET'])
@token_required
def get_models_tree():
    """获取模型树（包含CI数量）"""

    # 获取所有分类
    categories = ModelCategory.query.filter_by(parent_id=None).order_by(ModelCategory.sort_order).all()
    
    def build_category_tree(category):
        """构建分类树，包含模型"""
        # 获取该分类下的模型
        models = CmdbModel.query.filter_by(category_id=category.id).order_by(CmdbModel.created_at.desc()).all()
        
        children = []
        
        # 添加模型节点
        for model in models:
            # 获取该模型的CI数量
            ci_count = CiInstance.query.filter_by(model_id=model.id).count()
            config_data = model.get_config() if hasattr(model, 'get_config') else {}
            children.append({
                'id': f"model-{model.id}",
                'model_id': model.id,
                'name': f"{model.name} ({ci_count})",
                'title': model.name,
                'code': model.code,
                'ci_count': ci_count,
                'is_model': True,
                'icon': model.icon or 'AppstoreOutlined',
                'icon_url': config_data.get('icon_url') if isinstance(config_data, dict) else None,
                'key_field_codes': config_data.get('key_field_codes', []) if isinstance(config_data, dict) else [],
            })
        
        # 添加子分类
        for child_cat in category.children.order_by(ModelCategory.sort_order):
            children.append(build_category_tree(child_cat))
        
        return {
            'id': f"category-{category.id}",
            'category_id': category.id,
            'name': category.name,
            'code': category.code,
            'is_category': True,
            'children': children
        }
    
    tree = [build_category_tree(cat) for cat in categories]
    
    # 添加"全部"节点
    all_count = CiInstance.query.count()
    tree.insert(0, {
        'id': 'all',
        'name': f"全部 ({all_count})",
        'title': '全部',
        'ci_count': all_count,
        'is_all': True,
        'icon': 'FolderOutlined'
    })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': tree
    })


@cmdb_bp.route('/models', methods=['GET'])
@token_required
@admin_required
def get_models():
    """获取模型列表"""
    category_id = request.args.get('category_id', type=int)
    model_type_id = request.args.get('model_type_id', type=int)
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = CmdbModel.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)

    if model_type_id:
        query = query.filter_by(model_type_id=model_type_id)
    
    if keyword:
        query = query.filter(
            db.or_(
                CmdbModel.name.contains(keyword),
                CmdbModel.code.contains(keyword)
            )
        )
    
    pagination = query.order_by(CmdbModel.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'items': [model.to_dict() for model in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page
        }
    })


@cmdb_bp.route('/models/<int:id>', methods=['GET'])
@token_required
def get_model_detail(id):
    """获取模型详情"""
    model = CmdbModel.query.get_or_404(id)
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': model.to_full_dict()
    })


@cmdb_bp.route('/models', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='cmdb_model')
def create_model():
    """创建模型"""
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '名称和编码不能为空'}), 400
    
    if not data.get('category_id'):
        return jsonify({'code': 400, 'message': '请选择模型目录'}), 400
    
    if CmdbModel.query.filter_by(code=data['code']).first():
        return jsonify({'code': 400, 'message': '模型编码已存在'}), 400

    key_field_codes = _normalize_key_field_codes(data.get('key_field_codes'))
    validate_error = _validate_key_field_codes(data.get('form_config', []), key_field_codes)
    if validate_error:
        return jsonify({'code': 400, 'message': validate_error}), 400

    config_data = data.get('config', {})
    if not isinstance(config_data, dict):
        config_data = {}
    config_data['icon_url'] = data.get('icon_url')
    config_data['key_field_codes'] = key_field_codes if key_field_codes is not None else []
    
    model = CmdbModel(
        name=data['name'],
        code=data['code'],
        icon=data.get('icon', 'AppstoreOutlined'),
        category_id=data['category_id'],
        model_type_id=data.get('model_type_id'),
        description=data.get('description'),
        config=json.dumps(config_data, ensure_ascii=False),
        form_config=json.dumps(data.get('form_config', []), ensure_ascii=False),
        created_by=request.current_user.id
    )
    model.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': model.to_dict()
    })


@cmdb_bp.route('/models/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='cmdb_model')
def update_model(id):
    """更新模型"""
    model = CmdbModel.query.get_or_404(id)
    data = request.get_json()
    
    if data.get('code') and data['code'] != model.code:
        if CmdbModel.query.filter_by(code=data['code']).first():
            return jsonify({'code': 400, 'message': '模型编码已存在'}), 400
        model.code = data['code']
    
    form_config_for_validate = data.get('form_config')
    if form_config_for_validate is None:
        form_config_for_validate = model.form_config

    key_field_codes = _normalize_key_field_codes(data.get('key_field_codes'))
    if key_field_codes is None:
        key_field_codes = model.key_field_codes

    validate_error = _validate_key_field_codes(form_config_for_validate, key_field_codes)
    if validate_error:
        return jsonify({'code': 400, 'message': validate_error}), 400

    model.name = data.get('name', model.name)
    model.icon = data.get('icon', model.icon)
    model.category_id = data.get('category_id', model.category_id)
    model.model_type_id = data.get('model_type_id', model.model_type_id)
    model.description = data.get('description', model.description)

    config_data = model.get_config()
    if 'config' in data and isinstance(data.get('config'), dict):
        config_data.update(data['config'])
    if 'icon_url' in data:
        config_data['icon_url'] = data.get('icon_url')
    config_data['key_field_codes'] = key_field_codes
    model.config = json.dumps(config_data, ensure_ascii=False)

    if 'form_config' in data:
        model.form_config = json.dumps(data['form_config'], ensure_ascii=False)
    
    model.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': model.to_dict()
    })


@cmdb_bp.route('/models/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='cmdb_model')
def delete_model(id):
    """删除模型"""
    model = CmdbModel.query.get_or_404(id)
    
    # 检查是否有关联的CI实例
    count = CiInstance.query.filter_by(model_id=id).count()
    if count > 0:
        return jsonify({'code': 400, 'message': f'该模型下存在{count}个CI实例，无法删除'}), 400
    
    model.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


@cmdb_bp.route('/models/icon-upload', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='UPLOAD', operation_object='cmdb_model_icon')
def upload_model_icon():
    """上传模型图标"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '没有选择文件'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'code': 400, 'message': '没有选择文件'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in MODEL_ICON_ALLOWED_EXTENSIONS:
        return jsonify({'code': 400, 'message': '仅支持 png/svg 格式'}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MODEL_ICON_MAX_SIZE:
        return jsonify({'code': 400, 'message': '图标大小不能超过 2MB'}), 400

    today = datetime.now().strftime('%Y%m%d')
    upload_dir = os.path.join(MODEL_ICON_UPLOAD_FOLDER, today)
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    return jsonify({
        'code': 200,
        'message': '上传成功',
        'data': {
            'filename': unique_name,
            'path': f'{today}/{unique_name}',
            'url': f'/api/v1/cmdb/models/icon-files/{today}/{unique_name}',
        }
    })


@cmdb_bp.route('/models/icon-files/<path:filepath>', methods=['GET'])
def get_model_icon_file(filepath):
    """获取模型图标文件"""
    directory = os.path.join(MODEL_ICON_UPLOAD_FOLDER, os.path.dirname(filepath))
    filename = os.path.basename(filepath)
    full_path = os.path.join(directory, filename)
    if not os.path.exists(full_path):
        return jsonify({'code': 404, 'message': '文件不存在'}), 404
    return send_from_directory(directory, filename)


# ==================== 模型区域管理 ====================

@cmdb_bp.route('/models/<int:model_id>/regions', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='model_region')
def create_region(model_id):
    """创建模型区域"""
    model = CmdbModel.query.get_or_404(model_id)
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '名称和编码不能为空'}), 400
    
    region = ModelRegion(
        model_id=model_id,
        name=data['name'],
        code=data['code'],
        layout=data.get('layout', '2'),
        sort_order=data.get('sort_order', 0)
    )
    region.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': region.to_dict()
    })


@cmdb_bp.route('/regions/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='model_region')
def update_region(id):
    """更新模型区域"""
    region = ModelRegion.query.get_or_404(id)
    data = request.get_json()
    
    region.name = data.get('name', region.name)
    region.code = data.get('code', region.code)
    region.layout = data.get('layout', region.layout)
    region.sort_order = data.get('sort_order', region.sort_order)
    region.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': region.to_dict()
    })


@cmdb_bp.route('/regions/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='model_region')
def delete_region(id):
    """删除模型区域"""
    region = ModelRegion.query.get_or_404(id)
    
    if region.fields.count() > 0:
        return jsonify({'code': 400, 'message': '该区域下存在字段，无法删除'}), 400
    
    region.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 模型字段管理 ====================

@cmdb_bp.route('/models/<int:model_id>/fields', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='model_field')
def create_field(model_id):
    """创建模型字段"""
    model = CmdbModel.query.get_or_404(model_id)
    data = request.get_json()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'code': 400, 'message': '名称和编码不能为空'}), 400
    
    if not data.get('field_type'):
        return jsonify({'code': 400, 'message': '字段类型不能为空'}), 400
    
    field = ModelField(
        model_id=model_id,
        region_id=data.get('region_id'),
        name=data['name'],
        code=data['code'],
        field_type=data['field_type'],
        is_required=data.get('is_required', False),
        is_unique=data.get('is_unique', False),
        default_value=data.get('default_value'),
        options=json.dumps(data.get('options', [])),
        validation_rules=json.dumps(data.get('validation_rules', {})),
        reference_model_id=data.get('reference_model_id'),
        date_format=data.get('date_format'),
        sort_order=data.get('sort_order', 0),
        config=json.dumps(data.get('config', {}))
    )
    field.save()
    
    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': field.to_dict()
    })


@cmdb_bp.route('/fields/<int:id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='model_field')
def update_field(id):
    """更新模型字段"""
    field = ModelField.query.get_or_404(id)
    data = request.get_json()
    
    field.name = data.get('name', field.name)
    field.code = data.get('code', field.code)
    field.field_type = data.get('field_type', field.field_type)
    field.is_required = data.get('is_required', field.is_required)
    field.is_unique = data.get('is_unique', field.is_unique)
    field.default_value = data.get('default_value', field.default_value)
    field.region_id = data.get('region_id', field.region_id)
    field.reference_model_id = data.get('reference_model_id', field.reference_model_id)
    field.date_format = data.get('date_format', field.date_format)
    field.sort_order = data.get('sort_order', field.sort_order)
    
    if 'options' in data:
        field.options = json.dumps(data['options'])
    if 'validation_rules' in data:
        field.validation_rules = json.dumps(data['validation_rules'])
    if 'config' in data:
        field.config = json.dumps(data['config'])
    
    field.save()
    
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': field.to_dict()
    })


@cmdb_bp.route('/fields/<int:id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='model_field')
def delete_field(id):
    """删除模型字段"""
    field = ModelField.query.get_or_404(id)
    field.delete()
    
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


# ==================== 导入导出 ====================

@cmdb_bp.route('/models/<int:id>/export', methods=['GET'])
@token_required
@admin_required
@log_operation(operation_type='EXPORT', operation_object='cmdb_model')
def export_model(id):
    """导出模型配置"""
    model = CmdbModel.query.get_or_404(id)
    
    export_data = {
        'model': model.to_full_dict(),
        'export_time': datetime.utcnow().isoformat(),
        'version': '1.0'
    }
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': export_data
    })


@cmdb_bp.route('/models/import', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='IMPORT', operation_object='cmdb_model')
def import_model():
    """导入模型配置"""
    data = request.get_json()
    
    if not data.get('model'):
        return jsonify({'code': 400, 'message': '无效的导入数据'}), 400
    
    model_data = data['model']
    
    # 检查编码是否已存在
    if CmdbModel.query.filter_by(code=model_data['code']).first():
        return jsonify({'code': 400, 'message': '模型编码已存在'}), 400
    
    key_field_codes = _normalize_key_field_codes(model_data.get('key_field_codes'))
    validate_error = _validate_key_field_codes(model_data.get('form_config', []), key_field_codes)
    if validate_error:
        return jsonify({'code': 400, 'message': validate_error}), 400

    config_data = model_data.get('config', {})
    if not isinstance(config_data, dict):
        config_data = {}
    config_data['icon_url'] = model_data.get('icon_url')
    config_data['key_field_codes'] = key_field_codes if key_field_codes is not None else []

    # 创建模型
    model = CmdbModel(
        name=model_data['name'],
        code=model_data['code'],
        icon=model_data.get('icon', 'AppstoreOutlined'),
        category_id=model_data.get('category_id'),
        description=model_data.get('description'),
        config=json.dumps(config_data, ensure_ascii=False),
        form_config=json.dumps(model_data.get('form_config', []), ensure_ascii=False),
        created_by=request.current_user.id
    )
    model.save()
    
    # 导入区域
    region_map = {}
    for region_data in model_data.get('regions', []):
        region = ModelRegion(
            model_id=model.id,
            name=region_data['name'],
            code=region_data['code'],
            layout=region_data.get('layout', '2'),
            sort_order=region_data.get('sort_order', 0)
        )
        region.save()
        region_map[region_data['id']] = region.id
    
    # 导入字段
    for field_data in model_data.get('fields', []):
        field = ModelField(
            model_id=model.id,
            region_id=region_map.get(field_data.get('region_id')),
            name=field_data['name'],
            code=field_data['code'],
            field_type=field_data['field_type'],
            is_required=field_data.get('is_required', False),
            is_unique=field_data.get('is_unique', False),
            default_value=field_data.get('default_value'),
            options=json.dumps(field_data.get('options', [])),
            validation_rules=json.dumps(field_data.get('validation_rules', {})),
            date_format=field_data.get('date_format'),
            sort_order=field_data.get('sort_order', 0),
            config=json.dumps(field_data.get('config', {}))
        )
        field.save()
    
    return jsonify({
        'code': 200,
        'message': '导入成功',
        'data': model.to_full_dict()
    })


# ==================== 字段排序 ====================

@cmdb_bp.route('/fields/sort', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='model_field')
def sort_fields():
    """批量更新字段排序"""
    data = request.get_json()
    field_orders = data.get('field_orders', [])
    
    for item in field_orders:
        field = ModelField.query.get(item['id'])
        if field:
            field.sort_order = item['sort_order']
    
    db.session.commit()
    
    return jsonify({
        'code': 200,
        'message': '排序更新成功'
    })


# ==================== 字典管理 ====================

@cmdb_bp.route('/dict/types', methods=['GET'])
@token_required
def get_dict_types():
    """获取字典类型列表"""
    keyword = request.args.get('keyword', '').strip()
    enabled = _parse_bool_query(request.args.get('enabled'), None)

    query = CmdbDictType.query
    if keyword:
        query = query.filter(
            db.or_(
                CmdbDictType.name.contains(keyword),
                CmdbDictType.code.contains(keyword)
            )
        )
    if enabled is not None:
        query = query.filter_by(enabled=enabled)

    items = query.order_by(CmdbDictType.sort_order.asc(), CmdbDictType.id.asc()).all()
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': items and [item.to_dict() for item in items] or []
    })


@cmdb_bp.route('/dict/types', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='cmdb_dict_type')
def create_dict_type():
    """创建字典类型"""
    data = request.get_json() or {}
    code = str(data.get('code', '')).strip()
    name = str(data.get('name', '')).strip()

    if not code or not name:
        return jsonify({'code': 400, 'message': '编码和名称不能为空'}), 400

    if CmdbDictType.query.filter_by(code=code).first():
        return jsonify({'code': 400, 'message': '字典编码已存在'}), 400

    item = CmdbDictType(
        code=code,
        name=name,
        description=data.get('description'),
        enabled=bool(data.get('enabled', True)),
        sort_order=int(data.get('sort_order', 0)),
        created_by=request.current_user.id
    )
    item.save()

    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': item.to_dict()
    })


@cmdb_bp.route('/dict/types/<int:type_id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='cmdb_dict_type')
def update_dict_type(type_id):
    """更新字典类型"""
    dict_type = CmdbDictType.query.get_or_404(type_id)
    data = request.get_json() or {}

    if 'code' in data:
        code = str(data.get('code', '')).strip()
        if not code:
            return jsonify({'code': 400, 'message': '编码不能为空'}), 400
        if code != dict_type.code and CmdbDictType.query.filter_by(code=code).first():
            return jsonify({'code': 400, 'message': '字典编码已存在'}), 400
        dict_type.code = code

    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return jsonify({'code': 400, 'message': '名称不能为空'}), 400
        dict_type.name = name

    if 'description' in data:
        dict_type.description = data.get('description')
    if 'enabled' in data:
        dict_type.enabled = bool(data.get('enabled'))
    if 'sort_order' in data:
        dict_type.sort_order = int(data.get('sort_order', 0))

    dict_type.save()
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': dict_type.to_dict()
    })


@cmdb_bp.route('/dict/types/<int:type_id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='cmdb_dict_type')
def delete_dict_type(type_id):
    """删除字典类型"""
    dict_type = CmdbDictType.query.get_or_404(type_id)
    dict_type.delete()
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })


@cmdb_bp.route('/dict/types/<int:type_id>/items', methods=['GET'])
@token_required
def get_dict_items(type_id):
    """按字典类型获取字典项树"""
    dict_type = CmdbDictType.query.get_or_404(type_id)
    enabled = _parse_bool_query(request.args.get('enabled'), None)

    query = CmdbDictItem.query.filter_by(type_id=dict_type.id)
    if enabled is not None:
        query = query.filter_by(enabled=enabled)
    items = query.order_by(CmdbDictItem.sort_order.asc(), CmdbDictItem.id.asc()).all()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'type': dict_type.to_dict(),
            'items': _build_dict_item_tree(items)
        }
    })


@cmdb_bp.route('/dict/items/by-type-code/<string:type_code>', methods=['GET'])
@token_required
def get_dict_items_by_type_code(type_code):
    """按字典编码获取字典项树"""
    dict_type = CmdbDictType.query.filter_by(code=type_code).first()
    if not dict_type:
        return jsonify({'code': 404, 'message': '字典类型不存在'}), 404

    enabled = _parse_bool_query(request.args.get('enabled'), True)
    query = CmdbDictItem.query.filter_by(type_id=dict_type.id)
    if enabled is not None:
        query = query.filter_by(enabled=enabled)
    items = query.order_by(CmdbDictItem.sort_order.asc(), CmdbDictItem.id.asc()).all()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'type': dict_type.to_dict(),
            'items': _build_dict_item_tree(items)
        }
    })


@cmdb_bp.route('/dict/types/<int:type_id>/items', methods=['POST'])
@token_required
@admin_required
@log_operation(operation_type='CREATE', operation_object='cmdb_dict_item')
def create_dict_item(type_id):
    """创建字典项"""
    dict_type = CmdbDictType.query.get_or_404(type_id)
    data = request.get_json() or {}

    code = str(data.get('code', '')).strip()
    label = str(data.get('label', '')).strip()
    parent_id = data.get('parent_id')
    if parent_id in ('', None):
        parent_id = None

    if not code or not label:
        return jsonify({'code': 400, 'message': '编码和显示名不能为空'}), 400

    if parent_id:
        parent_item = CmdbDictItem.query.get(parent_id)
        if not parent_item or parent_item.type_id != dict_type.id:
            return jsonify({'code': 400, 'message': '父级字典项不存在'}), 400

    existed = CmdbDictItem.query.filter_by(
        type_id=dict_type.id,
        parent_id=parent_id,
        code=code
    ).first()
    if existed:
        return jsonify({'code': 400, 'message': '同级字典编码已存在'}), 400

    item = CmdbDictItem(
        type_id=dict_type.id,
        parent_id=parent_id,
        code=code,
        label=label,
        enabled=bool(data.get('enabled', True)),
        sort_order=int(data.get('sort_order', 0)),
        created_by=request.current_user.id
    )
    item.save()

    return jsonify({
        'code': 200,
        'message': '创建成功',
        'data': item.to_dict()
    })


@cmdb_bp.route('/dict/items/<int:item_id>', methods=['PUT'])
@token_required
@admin_required
@log_operation(operation_type='UPDATE', operation_object='cmdb_dict_item')
def update_dict_item(item_id):
    """更新字典项"""
    item = CmdbDictItem.query.get_or_404(item_id)
    data = request.get_json() or {}

    target_parent_id = item.parent_id
    if 'parent_id' in data:
        value = data.get('parent_id')
        target_parent_id = None if value in ('', None) else int(value)
        if target_parent_id:
            parent_item = CmdbDictItem.query.get(target_parent_id)
            if not parent_item or parent_item.type_id != item.type_id:
                return jsonify({'code': 400, 'message': '父级字典项不存在'}), 400
            if _is_descendant_item(item, target_parent_id):
                return jsonify({'code': 400, 'message': '不能将节点移动到自己的子节点下'}), 400

    target_code = item.code
    if 'code' in data:
        target_code = str(data.get('code', '')).strip()
        if not target_code:
            return jsonify({'code': 400, 'message': '编码不能为空'}), 400

    existed = CmdbDictItem.query.filter_by(
        type_id=item.type_id,
        parent_id=target_parent_id,
        code=target_code
    ).first()
    if existed and existed.id != item.id:
        return jsonify({'code': 400, 'message': '同级字典编码已存在'}), 400

    item.parent_id = target_parent_id
    item.code = target_code

    if 'label' in data:
        label = str(data.get('label', '')).strip()
        if not label:
            return jsonify({'code': 400, 'message': '显示名不能为空'}), 400
        item.label = label
    if 'enabled' in data:
        item.enabled = bool(data.get('enabled'))
    if 'sort_order' in data:
        item.sort_order = int(data.get('sort_order', 0))

    item.save()
    return jsonify({
        'code': 200,
        'message': '更新成功',
        'data': item.to_dict()
    })


@cmdb_bp.route('/dict/items/<int:item_id>', methods=['DELETE'])
@token_required
@admin_required
@log_operation(operation_type='DELETE', operation_object='cmdb_dict_item')
def delete_dict_item(item_id):
    """删除字典项（包含子项）"""
    item = CmdbDictItem.query.get_or_404(item_id)
    item.delete()
    return jsonify({
        'code': 200,
        'message': '删除成功'
    })
