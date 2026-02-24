from flask import Blueprint, request, jsonify
from app import db
from app.models import CustomView, CustomViewNode, CustomViewNodePermission, Role, CmdbModel, CiInstance
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from app.models.user import User
from app.utils.cache import cache, cached, invalidate_cache
import math
import time

custom_view_bp = Blueprint("custom_view", __name__, url_prefix="/api/v1")


def get_current_user():
    """获取当前用户"""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return User.query.get(int(identity))
    except Exception:
        pass
    return None


def check_permission(permission_code):
    """检查当前用户是否有权限"""
    current_user = get_current_user()
    if not current_user:
        return False
    
    if current_user.is_admin:
        return True
    
    # 通过 role_links 获取用户的角色
    for user_role in current_user.role_links:
        if user_role.role and user_role.role.has_permission(permission_code):
            return True
    return False


@custom_view_bp.route("/custom-views/my", methods=["GET"])
def get_my_custom_views():
    """获取当前用户有权限的视图列表（用于菜单）"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"code": 401, "message": "未登录"}), 401
    
    # 管理员返回所有视图
    if current_user.is_admin:
        views = CustomView.query.filter_by(is_active=True).order_by(CustomView.sort_order).all()
        return jsonify({
            "code": 200,
            "message": "success",
            "data": [view.to_dict() for view in views]
        })
    
    # 普通用户返回有权限的视图
    # 获取用户所有角色
    role_ids = [ur.role_id for ur in current_user.role_links]
    
    # 查询这些角色有权限访问的节点，然后通过节点获取视图ID
    from app.models.custom_view import CustomViewNodePermission, CustomViewNode
    node_permissions = CustomViewNodePermission.query.filter(
        CustomViewNodePermission.role_id.in_(role_ids)
    ).all()
    
    node_ids = [np.node_id for np in node_permissions]
    
    # 通过节点获取视图ID
    view_ids = db.session.query(CustomViewNode.view_id).filter(
        CustomViewNode.id.in_(node_ids)
    ).distinct().all()
    
    view_id_list = [v[0] for v in view_ids]
    
    if view_id_list:
        views = CustomView.query.filter(
            CustomView.id.in_(view_id_list),
            CustomView.is_active == True
        ).order_by(CustomView.sort_order).all()
    else:
        views = []
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": [view.to_dict() for view in views]
    })


@custom_view_bp.route("/custom-views", methods=["GET"])
def get_custom_views():
    """获取视图列表"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    keyword = request.args.get("keyword", "")
    is_active = request.args.get("is_active", None)
    
    query = CustomView.query
    
    if keyword:
        query = query.filter(
            db.or_(
                CustomView.name.ilike(f"%{keyword}%"),
                CustomView.code.ilike(f"%{keyword}%")
            )
        )
    
    if is_active is not None:
        is_active = is_active.lower() == "true" if isinstance(is_active, str) else bool(is_active)
        query = query.filter(CustomView.is_active == is_active)
    
    query = query.order_by(CustomView.sort_order, CustomView.id.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "items": [view.to_dict() for view in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0
        }
    })


@custom_view_bp.route("/custom-views", methods=["POST"])
def create_custom_view():
    """创建视图"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    name = data.get("name", "").strip()
    code = data.get("code", "").strip()
    
    if not name:
        return jsonify({"code": 400, "message": "视图名称不能为空"}), 400
    if not code:
        return jsonify({"code": 400, "message": "视图标识不能为空"}), 400
    
    if not all(c.isalnum() or c in "-_" for c in code):
        return jsonify({"code": 400, "message": "视图标识只能包含字母、数字、下划线和中划线"}), 400
    
    existing = CustomView.query.filter_by(code=code).first()
    if existing:
        return jsonify({"code": 400, "message": "视图标识已存在"}), 400
    
    current_user = get_current_user()
    view = CustomView(
        name=name,
        code=code,
        description=data.get("description", ""),
        icon=data.get("icon", "AppstoreOutlined"),
        is_active=data.get("is_active", True),
        sort_order=data.get("sort_order", 0),
        created_by=current_user.id if current_user else None
    )
    db.session.add(view)
    db.session.commit()
    
    return jsonify({
        "code": 201,
        "message": "创建成功",
        "data": view.to_dict()
    }), 201


@custom_view_bp.route("/custom-views/<int:view_id>", methods=["GET"])
def get_custom_view(view_id):
    """获取视图详情"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": view.to_dict()
    })


@custom_view_bp.route("/custom-views/<int:view_id>", methods=["PUT"])
def update_custom_view(view_id):
    """更新视图"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"code": 400, "message": "视图名称不能为空"}), 400
        view.name = name
    
    if "description" in data:
        view.description = data["description"]
    
    if "icon" in data:
        view.icon = data["icon"]
    
    if "is_active" in data:
        view.is_active = data["is_active"]
    
    if "sort_order" in data:
        view.sort_order = data["sort_order"]
    
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "更新成功",
        "data": view.to_dict()
    })


@custom_view_bp.route("/custom-views/<int:view_id>", methods=["DELETE"])
def delete_custom_view(view_id):
    """删除视图"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    for node in view.nodes.all():
        for perm in node.role_permissions.all():
            db.session.delete(perm)
    
    db.session.delete(view)
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "删除成功",
        "data": None
    })


@custom_view_bp.route("/custom-views/<int:view_id>/nodes", methods=["GET"])
def get_view_nodes(view_id):
    """获取视图节点树"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    root_nodes = CustomViewNode.query.filter_by(
        view_id=view_id,
        parent_id=None
    ).order_by(CustomViewNode.sort_order).all()
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": [node.to_dict() for node in root_nodes]
    })


@custom_view_bp.route("/custom-view-nodes", methods=["POST"])
def create_node():
    """创建节点"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    view_id = data.get("view_id")
    parent_id = data.get("parent_id")
    name = data.get("name", "").strip()
    
    if not name:
        return jsonify({"code": 400, "message": "节点名称不能为空"}), 400
    
    if not view_id:
        return jsonify({"code": 400, "message": "视图ID不能为空"}), 400
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    if parent_id:
        parent = CustomViewNode.query.get(parent_id)
        if not parent:
            return jsonify({"code": 404, "message": "父节点不存在"}), 404
        if parent.view_id != view_id:
            return jsonify({"code": 400, "message": "父节点不属于该视图"}), 400
        if parent.get_level() >= 4:
            return jsonify({"code": 400, "message": "节点层级最多5层"}), 400
    
    existing = CustomViewNode.query.filter_by(
        view_id=view_id,
        parent_id=parent_id,
        name=name
    ).first()
    if existing:
        return jsonify({"code": 400, "message": "同级节点名称不能重复"}), 400
    
    node = CustomViewNode(
        view_id=view_id,
        parent_id=parent_id,
        name=name,
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True)
    )
    
    filter_config = data.get("filter_config")
    if filter_config:
        if parent_id is None:
            return jsonify({"code": 400, "message": "根节点不能设置筛选条件"}), 400
        node.set_filter_config(filter_config)
    
    db.session.add(node)
    db.session.commit()
    
    # 清除该视图的缓存
    invalidate_cache(f"view_nodes_tree:{view_id}")
    
    return jsonify({
        "code": 201,
        "message": "创建成功",
        "data": node.to_dict()
    }), 201


@custom_view_bp.route("/custom-view-nodes/<int:node_id>", methods=["GET"])
def get_node(node_id):
    """获取节点详情"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": node.to_dict()
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>", methods=["PUT"])
def update_node(node_id):
    """更新节点"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"code": 400, "message": "节点名称不能为空"}), 400
        
        existing = CustomViewNode.query.filter(
            CustomViewNode.view_id == node.view_id,
            CustomViewNode.parent_id == node.parent_id,
            CustomViewNode.name == name,
            CustomViewNode.id != node_id
        ).first()
        if existing:
            return jsonify({"code": 400, "message": "同级节点名称不能重复"}), 400
        node.name = name
    
    if "sort_order" in data:
        node.sort_order = data["sort_order"]
    
    if "is_active" in data:
        node.is_active = data["is_active"]
    
    if "filter_config" in data:
        if node.is_root():
            return jsonify({"code": 400, "message": "根节点不能设置筛选条件"}), 400
        node.set_filter_config(data["filter_config"])
    
    db.session.commit()
    
    # 清除该视图的缓存
    invalidate_cache(f"view_nodes_tree:{node.view_id}")
    
    return jsonify({
        "code": 200,
        "message": "更新成功",
        "data": node.to_dict()
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>", methods=["DELETE"])
def delete_node(node_id):
    """删除节点"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    view_id = node.view_id
    
    for child in node.get_all_children():
        for perm in child.role_permissions.all():
            db.session.delete(perm)
    
    for perm in node.role_permissions.all():
        db.session.delete(perm)
    
    db.session.delete(node)
    db.session.commit()
    
    # 清除该视图的缓存
    invalidate_cache(f"view_nodes_tree:{view_id}")
    
    return jsonify({
        "code": 200,
        "message": "删除成功",
        "data": None
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>/move", methods=["PUT"])
def move_node(node_id):
    """移动节点"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    new_parent_id = data.get("parent_id")
    sort_order = data.get("sort_order", 0)
    
    if new_parent_id is not None:
        new_parent = CustomViewNode.query.get(new_parent_id)
        if not new_parent:
            return jsonify({"code": 404, "message": "目标父节点不存在"}), 404
        if new_parent.view_id != node.view_id:
            return jsonify({"code": 400, "message": "目标父节点不属于该视图"}), 400
        
        if new_parent.get_level() >= 4:
            return jsonify({"code": 400, "message": "移动后节点层级将超过5层"}), 400
        
        existing = CustomViewNode.query.filter(
            CustomViewNode.view_id == node.view_id,
            CustomViewNode.parent_id == new_parent_id,
            CustomViewNode.name == node.name,
            CustomViewNode.id != node_id
        ).first()
        if existing:
            return jsonify({"code": 400, "message": "目标父节点下已有同名节点"}), 400
    
    node.parent_id = new_parent_id
    node.sort_order = sort_order
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "移动成功",
        "data": node.to_dict()
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>/cis", methods=["GET"])
def get_node_cis(node_id):
    """获取节点筛选的CI列表"""
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    view = node.view
    current_user = get_current_user()
    
    has_view_permission = False
    if current_user and current_user.is_admin:
        has_view_permission = True
    elif current_user:
        # 获取用户的所有角色ID
        user_role_ids = [ur.role_id for ur in current_user.role_links]
        # 检查是否有视图的查看权限
        from app.models.role import Role
        for role_id in user_role_ids:
            role = Role.query.get(role_id)
            if role and role.has_permission(f"custom-view:{view.code}:view"):
                has_view_permission = True
                break
            # 检查节点权限
            for perm in node.role_permissions.all():
                if role_id == perm.role_id:
                    has_view_permission = True
                    break
            if has_view_permission:
                break
    
    if not has_view_permission:
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    filter_config = node.get_filter_config()
    if not filter_config:
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 20
            }
        })
    
    model_id = filter_config.get("model_id")
    conditions = filter_config.get("conditions", [])
    
    if not model_id:
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 20
            }
        })
    
    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 404, "message": "模型不存在"}), 404
    
    # 自定义视图权限检查：只要有节点权限就可以查看
    # 不需要额外的模型查看权限（因为节点本身就是一种权限控制）
    # 如果后续需要更细粒度的控制，可以在这里添加
    
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    keyword = request.args.get("keyword", "")
    
    # 获取前端传递的属性筛选参数
    attr_field = request.args.get("attr_field", "")
    attr_value = request.args.get("attr_value", "")
    
    # 获取所有该模型的CI实例
    query = CiInstance.query.filter_by(model_id=model_id)
    
    # 先获取所有记录（因为属性存储在JSON字段中，需要在Python中过滤）
    all_instances = query.all()
    filtered_instances = []
    
    for ci in all_instances:
        # 获取属性值
        attrs = ci.get_attribute_values()
        
        # 检查关键字搜索
        if keyword:
            keyword_match = (
                keyword.lower() in ci.code.lower() or
                keyword.lower() in (ci.name or "").lower() or
                any(keyword.lower() in str(v).lower() for v in attrs.values())
            )
            if not keyword_match:
                continue
        
        # 检查前端传递的属性筛选条件
        if attr_field and attr_value:
            field_value = attrs.get(attr_field)
            if field_value is None or attr_value.lower() not in str(field_value).lower():
                continue
        
        # 检查节点配置的筛选条件
        condition_match = True
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not field or value is None or value == "":
                continue
            
            # 获取字段值（优先从attributes中获取）
            field_value = attrs.get(field)
            
            # 执行条件判断
            if operator == "eq":
                if str(field_value) != str(value):
                    condition_match = False
                    break
            elif operator == "ne":
                if str(field_value) == str(value):
                    condition_match = False
                    break
            elif operator == "contains":
                if value.lower() not in str(field_value).lower():
                    condition_match = False
                    break
            elif operator == "not_contains":
                if value.lower() in str(field_value).lower():
                    condition_match = False
                    break
            elif operator == "gt":
                try:
                    if float(field_value) <= float(value):
                        condition_match = False
                        break
                except (ValueError, TypeError):
                    condition_match = False
                    break
            elif operator == "gte":
                try:
                    if float(field_value) < float(value):
                        condition_match = False
                        break
                except (ValueError, TypeError):
                    condition_match = False
                    break
            elif operator == "lt":
                try:
                    if float(field_value) >= float(value):
                        condition_match = False
                        break
                except (ValueError, TypeError):
                    condition_match = False
                    break
            elif operator == "lte":
                try:
                    if float(field_value) > float(value):
                        condition_match = False
                        break
                except (ValueError, TypeError):
                    condition_match = False
                    break
            elif operator == "in":
                if isinstance(value, list):
                    if str(field_value) not in [str(v) for v in value]:
                        condition_match = False
                        break
                else:
                    if str(field_value) != str(value):
                        condition_match = False
                        break
            elif operator == "not_in":
                if isinstance(value, list):
                    if str(field_value) in [str(v) for v in value]:
                        condition_match = False
                        break
                else:
                    if str(field_value) == str(value):
                        condition_match = False
                        break
        
        if condition_match:
            filtered_instances.append(ci)
    
    # 分页
    total = len(filtered_instances)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = filtered_instances[start_idx:end_idx]
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "items": [ci.to_simple_dict() for ci in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0
        }
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>/permissions", methods=["GET"])
def get_node_permissions(node_id):
    """获取节点权限列表"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    permissions = CustomViewNodePermission.query.filter_by(node_id=node_id).all()
    
    result = []
    for perm in permissions:
        role = Role.query.get(perm.role_id)
        if role:
            result.append({
                "id": perm.id,
                "node_id": perm.node_id,
                "role_id": perm.role_id,
                "role_name": role.name,
                "created_at": perm.created_at.strftime("%Y-%m-%d %H:%M:%S") if perm.created_at else None
            })
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": result
    })


@custom_view_bp.route("/custom-views/permissions/tree", methods=["GET"])
def get_custom_view_permissions_tree():
    """获取自定义视图权限树（用于角色权限配置）"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    views = CustomView.query.filter_by(is_active=True).order_by(CustomView.sort_order).all()
    
    tree = []
    for view in views:
        view_node = {
            "key": f"view_{view.id}",
            "title": view.name,
            "code": view.code,
            "children": []
        }
        
        root_nodes = CustomViewNode.query.filter_by(
            view_id=view.id,
            parent_id=None
        ).order_by(CustomViewNode.sort_order).all()
        
        for root_node in root_nodes:
            node_data = build_node_tree(root_node)
            if node_data:
                view_node["children"].append(node_data)
        
        if view_node["children"]:
            tree.append(view_node)
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": tree
    })


def build_node_tree(node: CustomViewNode):
    """递归构建节点树"""
    node_data = {
        "key": f"node_{node.id}",
        "title": node.name,
        "code": f"custom-view:{node.view.code}:node:{node.id}",
        "children": []
    }
    
    children = node.children.order_by(CustomViewNode.sort_order).all()
    for child in children:
        child_data = build_node_tree(child)
        if child_data:
            node_data["children"].append(child_data)
    
    return node_data


def register_view_permissions():
    """注册视图权限到角色"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    view_id = data.get("view_id")
    role_ids = data.get("role_ids", [])
    
    if not view_id:
        return jsonify({"code": 400, "message": "视图ID不能为空"}), 400
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    for role_id in role_ids:
        role = Role.query.get(role_id)
        if not role:
            continue
        
        view_perm = f"custom-view:{view.code}:view"
        edit_perm = f"custom-view:{view.code}:edit"
        
        menu_perms = role.get_menu_permissions()
        
        if view_perm not in menu_perms:
            menu_perms.append(view_perm)
        if edit_perm not in menu_perms:
            menu_perms.append(edit_perm)
        
        role.set_menu_permissions(menu_perms)
        
        root_nodes = CustomViewNode.query.filter_by(
            view_id=view_id,
            parent_id=None
        ).all()
        
        for node in root_nodes:
            perm = CustomViewNodePermission.query.filter_by(
                node_id=node.id,
                role_id=role_id
            ).first()
            if not perm:
                perm = CustomViewNodePermission(node_id=node.id, role_id=role_id)
                db.session.add(perm)
            
            for child in node.get_all_children():
                child_perm = CustomViewNodePermission.query.filter_by(
                    node_id=child.id,
                    role_id=role_id
                ).first()
                if not child_perm:
                    child_perm = CustomViewNodePermission(node_id=child.id, role_id=role_id)
                    db.session.add(child_perm)
    
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "权限注册成功",
        "data": None
    })


@custom_view_bp.route("/permissions/unregister", methods=["POST"])
def unregister_view_permissions():
    """注销视图权限"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    view_id = data.get("view_id")
    role_ids = data.get("role_ids", [])
    
    if not view_id:
        return jsonify({"code": 400, "message": "视图ID不能为空"}), 400
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    for role_id in role_ids:
        role = Role.query.get(role_id)
        if not role:
            continue
        
        view_perm = f"custom-view:{view.code}:view"
        edit_perm = f"custom-view:{view.code}:edit"
        
        menu_perms = role.get_menu_permissions()
        
        if view_perm in menu_perms:
            menu_perms.remove(view_perm)
        if edit_perm in menu_perms:
            menu_perms.remove(edit_perm)
        
        role.set_menu_permissions(menu_perms)
        
        nodes = CustomViewNode.query.filter_by(view_id=view_id).all()
        for node in nodes:
            perm = CustomViewNodePermission.query.filter_by(
                node_id=node.id,
                role_id=role_id
            ).first()
            if perm:
                db.session.delete(perm)
    
    db.session.commit()
    
    return jsonify({
        "code": 200,
        "message": "权限注销成功",
        "data": None
    })


@custom_view_bp.route("/custom-view-nodes/<int:node_id>/permissions", methods=["POST"])
def grant_node_permission(node_id):
    """授予节点权限"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "message": "请求参数错误"}), 400
    
    role_id = data.get("role_id")
    if not role_id:
        return jsonify({"code": 400, "message": "角色ID不能为空"}), 400
    
    role = Role.query.get(role_id)
    if not role:
        return jsonify({"code": 404, "message": "角色不存在"}), 404
    
    existing = CustomViewNodePermission.query.filter_by(
        node_id=node_id,
        role_id=role_id
    ).first()
    
    if existing:
        return jsonify({"code": 400, "message": "该角色已有该节点权限"}), 400
    
    perm = CustomViewNodePermission(node_id=node_id, role_id=role_id)
    db.session.add(perm)
    
    for child in node.get_all_children():
        child_perm = CustomViewNodePermission.query.filter_by(
            node_id=child.id,
            role_id=role_id
        ).first()
        if not child_perm:
            child_perm = CustomViewNodePermission(node_id=child.id, role_id=role_id)
            db.session.add(child_perm)
    
    db.session.commit()
    
    # 清除该视图的缓存
    invalidate_cache(f"view_nodes_tree:{node.view_id}")
    
    return jsonify({
        "code": 201,
        "message": "授权成功",
        "data": perm.to_dict()
    }), 201


@custom_view_bp.route("/custom-view-nodes/<int:node_id>/permissions/<int:role_id>", methods=["DELETE"])
def revoke_node_permission(node_id, role_id):
    """撤销节点权限"""
    if not check_permission("custom-view:manage"):
        return jsonify({"code": 403, "message": "无权限"}), 403
    
    node = CustomViewNode.query.get(node_id)
    if not node:
        return jsonify({"code": 404, "message": "节点不存在"}), 404
    
    perm = CustomViewNodePermission.query.filter_by(
        node_id=node_id,
        role_id=role_id
    ).first()
    
    if not perm:
        return jsonify({"code": 404, "message": "权限不存在"}), 404
    
    for child in node.get_all_children():
        child_perm = CustomViewNodePermission.query.filter_by(
            node_id=child.id,
            role_id=role_id
        ).first()
        if child_perm:
            db.session.delete(child_perm)
    
    db.session.delete(perm)
    db.session.commit()
    
    # 清除该视图的缓存
    invalidate_cache(f"view_nodes_tree:{node.view_id}")
    
    return jsonify({
        "code": 200,
        "message": "撤销成功",
        "data": None
    })


@custom_view_bp.route("/custom-views/<int:view_id>/nodes/tree", methods=["GET"])
def get_view_nodes_tree(view_id):
    """获取视图节点树（带权限过滤）- 优化版本，带缓存"""
    start_time = time.time()
    
    view = CustomView.query.get(view_id)
    if not view:
        return jsonify({"code": 404, "message": "视图不存在"}), 404
    
    current_user = get_current_user()
    
    # 生成缓存键
    user_id = current_user.id if current_user else 0
    cache_key = f"view_nodes_tree:{view_id}:user:{user_id}"
    
    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify({
            "code": 200,
            "message": "success",
            "data": cached_result,
            "cached": True
        })
    
    has_view_permission = False
    if current_user and current_user.is_admin:
        has_view_permission = True
    elif current_user:
        # 获取用户的所有角色ID
        user_role_ids = [ur.role_id for ur in current_user.role_links]
        from app.models.role import Role
        for role_id in user_role_ids:
            role = Role.query.get(role_id)
            if role and role.has_permission(f"custom-view:{view.code}:view"):
                has_view_permission = True
                break
    
    result = []
    
    if has_view_permission:
        # 使用 joinedload 预加载子节点，减少查询次数
        root_nodes = CustomViewNode.query.filter_by(
            view_id=view_id,
            parent_id=None,
            is_active=True
        ).order_by(CustomViewNode.sort_order).all()
        
        result = [node.to_dict() for node in root_nodes]
    else:
        if not current_user:
            return jsonify({"code": 403, "message": "无权限"}), 403
        
        # 批量查询权限，减少数据库往返
        user_role_ids = [ur.role_id for ur in current_user.role_links]
        
        # 一次性查询所有有权限的节点ID
        permitted_node_ids = set()
        perms = CustomViewNodePermission.query.join(CustomViewNode).filter(
            CustomViewNode.view_id == view_id,
            CustomViewNodePermission.role_id.in_(user_role_ids)
        ).all()
        
        for perm in perms:
            permitted_node_ids.add(perm.node_id)
        
        # 批量获取祖先节点，避免N+1查询
        parent_ids = set()
        if permitted_node_ids:
            # 获取所有相关节点及其祖先
            all_node_ids = set(permitted_node_ids)
            nodes_to_check = list(permitted_node_ids)
            
            while nodes_to_check:
                nodes = CustomViewNode.query.filter(
                    CustomViewNode.id.in_(nodes_to_check)
                ).all()
                nodes_to_check = []
                for node in nodes:
                    if node.parent_id and node.parent_id not in all_node_ids:
                        all_node_ids.add(node.parent_id)
                        parent_ids.add(node.parent_id)
                        nodes_to_check.append(node.parent_id)
        
        visible_node_ids = permitted_node_ids | parent_ids
        
        # 只查询根节点，减少数据量
        root_nodes = CustomViewNode.query.filter_by(
            view_id=view_id,
            parent_id=None,
            is_active=True
        ).order_by(CustomViewNode.sort_order).all()
        
        def filter_node(node):
            if node.id in visible_node_ids:
                filtered_children = [filter_node(child) for child in node.children.all()]
                node_dict = node.to_dict()
                node_dict["children"] = filtered_children
                return node_dict
            return None
        
        for node in root_nodes:
            filtered = filter_node(node)
            if filtered:
                result.append(filtered)
    
    # 缓存结果（5分钟）
    cache.set(cache_key, result, expire_seconds=300)
    
    return jsonify({
        "code": 200,
        "message": "success",
        "data": result
    })
