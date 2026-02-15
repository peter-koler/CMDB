from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.ci_instance import CiInstance, CiHistory, CodeSequence
from app.models.cmdb_model import CmdbModel
from app.models.model_field import ModelField
from app.models.department import Department
from app.models.user import User
from app.models.cmdb_relation import CmdbRelation, RelationTrigger
from app.services.relation_service import create_relation_with_validation, RelationServiceError
from app import db
from app.routes.auth import log_operation
from app.utils.code_generator import generate_ci_code_v2
from app.utils.data_permission import filter_by_data_permissions, check_data_permission
from datetime import datetime
import os
import json
import csv
import io
from io import StringIO

ci_bp = Blueprint("ci", __name__, url_prefix="/api/v1/cmdb/instances")

# 文件上传配置
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
    "zip",
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


def sync_reference_relations(instance, old_values=None):
    """
    同步引用属性关系
    """
    if not instance.model_id:
        return

    # 获取该模型的所有启用的 reference 类型触发器
    triggers = RelationTrigger.query.filter_by(
        source_model_id=instance.model_id, trigger_type="reference", is_active=True
    ).all()

    new_values = instance.get_attribute_values()

    for trigger in triggers:
        try:
            condition = (
                json.loads(trigger.trigger_condition)
                if trigger.trigger_condition
                else {}
            )
            source_field = condition.get("source_field")

            if not source_field:
                continue

            old_val = old_values.get(source_field) if old_values else None
            new_val = new_values.get(source_field)

            # 如果旧值存在且不等于新值，删除旧关系
            if old_val and str(old_val) != str(new_val):
                try:
                    old_target_ci_id = int(old_val)
                    old_rel = CmdbRelation.query.filter_by(
                        source_ci_id=instance.id,
                        target_ci_id=old_target_ci_id,
                        relation_type_id=trigger.relation_type_id,
                        source_type="reference",
                    ).first()
                    if old_rel:
                        db.session.delete(old_rel)
                        db.session.commit()
                except Exception:
                    db.session.rollback()

            # 如果新值存在，创建新关系
            if new_val:
                try:
                    new_target_ci_id = int(new_val)
                except (TypeError, ValueError):
                    continue

                try:
                    create_relation_with_validation(
                        source_ci_id=instance.id,
                        target_ci_id=new_target_ci_id,
                        relation_type_id=trigger.relation_type_id,
                        source_type="reference",
                    )
                except RelationServiceError:
                    # 约束检查失败时跳过，避免影响主流程
                    continue
        except Exception:
            continue


# ==================== CI实例管理 ====================


@ci_bp.route("", methods=["GET"])
@jwt_required()
def get_instances():
    """获取CI实例列表"""
    model_id = request.args.get("model_id", type=int)
    department_id = request.args.get("department_id", type=int)
    keyword = request.args.get("keyword", "")
    attr_field = request.args.get("attr_field", "")
    attr_value = request.args.get("attr_value", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = CiInstance.query

    if model_id:
        query = query.filter_by(model_id=model_id)

    if department_id:
        query = query.filter_by(department_id=department_id)

    if keyword:
        query = query.filter(CiInstance.code.contains(keyword))

    if attr_field and attr_value:
        query = query.filter(
            CiInstance.attribute_values.contains(f'"{attr_field}": "{attr_value}"')
        )

    query = filter_by_data_permissions(query, CiInstance)

    pagination = query.order_by(CiInstance.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "items": [instance.to_dict() for instance in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
            },
        }
    )


@ci_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_instance(id):
    """获取CI实例详情"""
    instance = CiInstance.query.get_or_404(id)

    # 权限检查
    if not check_data_permission(instance, int(get_jwt_identity())):
        return jsonify({"code": 403, "message": "无权限查看此CI"}), 403

    return jsonify(
        {"code": 200, "message": "success", "data": instance.to_detail_dict()}
    )


@ci_bp.route("", methods=["POST"])
@jwt_required()
def create_instance():
    """创建CI实例"""
    data = request.get_json()
    identity = get_jwt_identity()
    claims = get_jwt()

    if not data.get("model_id"):
        return jsonify({"code": 400, "message": "请选择模型"}), 400

    model = CmdbModel.query.get(data["model_id"])
    if not model:
        return jsonify({"code": 400, "message": "模型不存在"}), 400

    code = generate_ci_code_v2()

    attribute_values = data.get("attribute_values", {})

    instance = CiInstance(
        model_id=data["model_id"],
        name=code,
        code=code,
        department_id=data.get("department_id"),
        created_by=int(identity),
        updated_by=int(identity),
    )
    instance.set_attribute_values(attribute_values)
    instance.save()

    # 同步引用属性关系
    sync_reference_relations(instance)

    _log_ci_history(
        instance.id, "CREATE", None, None, None, identity, claims.get("username")
    )

    log_operation(
        int(identity),
        claims.get("username"),
        "CREATE",
        "ci_instance",
        instance.id,
        f"创建CI: {instance.code}",
    )

    return jsonify({"code": 200, "message": "创建成功", "data": instance.to_dict()})


@ci_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def update_instance(id):
    """更新CI实例"""
    instance = CiInstance.query.get_or_404(id)
    data = request.get_json()
    identity = get_jwt_identity()
    claims = get_jwt()

    if not check_data_permission(instance, int(identity)):
        return jsonify({"code": 403, "message": "无权限编辑此CI"}), 403

    old_values = instance.get_attribute_values()

    if "department_id" in data:
        instance.department_id = data["department_id"]

    if "attribute_values" in data:
        new_values = data["attribute_values"]
        instance.set_attribute_values(new_values)

        for key, new_val in new_values.items():
            old_val = old_values.get(key)
            if old_val != new_val:
                _log_ci_history(
                    instance.id,
                    "UPDATE",
                    key,
                    str(old_val),
                    str(new_val),
                    int(identity),
                    claims.get("username"),
                )

    instance.updated_by = int(identity)
    instance.save()

    # 同步引用属性关系
    sync_reference_relations(instance, old_values)

    log_operation(
        int(identity),
        claims.get("username"),
        "UPDATE",
        "ci_instance",
        instance.id,
        f"更新CI: {instance.code}",
    )

    return jsonify({"code": 200, "message": "更新成功", "data": instance.to_dict()})


@ci_bp.route("/<int:id>/relations-count", methods=["GET"])
@jwt_required()
def get_instance_relations_count(id):
    """获取CI的关联关系数量"""
    instance = CiInstance.query.get_or_404(id)

    # 权限检查
    identity = get_jwt_identity()
    if not check_data_permission(instance, int(identity)):
        return jsonify({"code": 403, "message": "无权限查看此CI"}), 403

    out_relations_count = CmdbRelation.query.filter_by(source_ci_id=id).count()
    in_relations_count = CmdbRelation.query.filter_by(target_ci_id=id).count()

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "out_relations": out_relations_count,
                "in_relations": in_relations_count,
                "total": out_relations_count + in_relations_count,
            },
        }
    )


@ci_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_instance(id):
    """删除CI实例（硬删除）"""
    instance = CiInstance.query.get_or_404(id)
    identity = get_jwt_identity()
    claims = get_jwt()

    # 权限检查
    if not check_data_permission(instance, int(identity)):
        return jsonify({"code": 403, "message": "无权限删除此CI"}), 403

    # 检查是否有关联的关系
    out_relations_count = CmdbRelation.query.filter_by(source_ci_id=id).count()
    in_relations_count = CmdbRelation.query.filter_by(target_ci_id=id).count()

    # 删除所有关联的关系
    if out_relations_count + in_relations_count > 0:
        CmdbRelation.query.filter_by(source_ci_id=id).delete()
        CmdbRelation.query.filter_by(target_ci_id=id).delete()
        db.session.commit()

    # 记录变更历史
    _log_ci_history(
        instance.id, "DELETE", None, None, None, identity, claims.get("username")
    )

    instance_code = instance.code
    instance_name = instance.name

    instance.delete()

    # 记录操作日志
    log_operation(
        int(identity),
        claims.get("username"),
        "DELETE",
        "ci_instance",
        id,
        f"删除CI: {instance_name} ({instance_code})",
    )

    return jsonify({"code": 200, "message": "删除成功"})


def _log_ci_history(
    ci_id, operation, attribute_name, old_value, new_value, operator_id, operator_name
):
    """记录CI变更历史"""
    history = CiHistory(
        ci_id=ci_id,
        operation=operation,
        attribute_name=attribute_name,
        old_value=old_value,
        new_value=new_value,
        operator_id=int(operator_id),
        operator_name=operator_name,
        ip_address=request.remote_addr,
    )
    history.save()


# ==================== 批量操作 ====================


@ci_bp.route("/batch-update", methods=["POST"])
@jwt_required()
def batch_update():
    """批量更新CI属性"""
    data = request.get_json()
    ids = data.get("ids", [])
    updates = data.get("updates", {})

    if not ids:
        return jsonify({"code": 400, "message": "请选择要更新的CI"}), 400

    identity = get_jwt_identity()
    claims = get_jwt()

    updated_count = 0
    for id in ids:
        instance = CiInstance.query.get(id)
        if not instance:
            continue

        # 权限检查
        if not require_admin() and instance.created_by != int(identity):
            continue

        # 更新属性
        attr_values = instance.get_attribute_values()
        for key, value in updates.items():
            attr_values[key] = value
            _log_ci_history(
                instance.id,
                "UPDATE",
                key,
                None,
                str(value),
                int(identity),
                claims.get("username"),
            )

        instance.set_attribute_values(attr_values)
        instance.updated_by = int(identity)
        instance.save()
        updated_count += 1

    log_operation(
        int(identity),
        claims.get("username"),
        "UPDATE",
        "ci_instance",
        None,
        f"批量更新 {updated_count} 个CI",
    )

    return jsonify(
        {
            "code": 200,
            "message": f"成功更新 {updated_count} 个CI",
            "data": {"updated_count": updated_count},
        }
    )


@ci_bp.route("/batch-delete", methods=["POST"])
@jwt_required()
def batch_delete():
    """批量删除CI"""
    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"code": 400, "message": "请选择要删除的CI"}), 400

    identity = get_jwt_identity()
    claims = get_jwt()

    deleted_count = 0
    for id in ids:
        instance = CiInstance.query.get(id)
        if not instance:
            continue

        # 权限检查
        if not require_admin() and instance.created_by != int(identity):
            continue

        _log_ci_history(
            instance.id,
            "DELETE",
            None,
            None,
            None,
            int(identity),
            claims.get("username"),
        )
        instance.delete()
        deleted_count += 1

    log_operation(
        int(identity),
        claims.get("username"),
        "DELETE",
        "ci_instance",
        None,
        f"批量删除 {deleted_count} 个CI",
    )

    return jsonify(
        {
            "code": 200,
            "message": f"成功删除 {deleted_count} 个CI",
            "data": {"deleted_count": deleted_count},
        }
    )


# ==================== 变更历史 ====================


@ci_bp.route("/<int:ci_id>/history", methods=["GET"])
@jwt_required()
def get_instance_history(ci_id):
    """获取CI变更历史"""
    identity = get_jwt_identity()
    instance = CiInstance.query.get_or_404(ci_id)

    # 权限检查
    if not require_admin() and instance.created_by != int(identity):
        return jsonify({"code": 403, "message": "无权限查看此CI历史"}), 403

    query = CiHistory.query.filter_by(ci_id=ci_id)
    histories = query.order_by(CiHistory.created_at.desc()).all()

    return jsonify(
        {"code": 200, "message": "success", "data": [h.to_dict() for h in histories]}
    )


@ci_bp.route("/history", methods=["GET"])
@jwt_required()
def get_all_history():
    """获取所有CI变更历史（支持筛选）"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    operator_id = request.args.get("operator_id", type=int)
    ci_id = request.args.get("ci_id", type=int)
    operation = request.args.get("operation", type=str)
    date_from = request.args.get("date_from", type=str)
    date_to = request.args.get("date_to", type=str)

    query = CiHistory.query

    if ci_id:
        query = query.filter_by(ci_id=ci_id)

    if operator_id:
        query = query.filter_by(operator_id=operator_id)

    if operation:
        query = query.filter_by(operation=operation)

    if date_from:
        query = query.filter(CiHistory.created_at >= datetime.fromisoformat(date_from))

    if date_to:
        query = query.filter(CiHistory.created_at <= datetime.fromisoformat(date_to))

    pagination = query.order_by(CiHistory.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "items": [h.to_dict() for h in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
            },
        }
    )


# ==================== 全文搜索 ====================


@ci_bp.route("/search", methods=["POST"])
@jwt_required()
def search_instances():
    """全文搜索CI"""
    data = request.get_json()
    keyword = data.get("keyword", "")
    model_id = data.get("model_id")
    department_id = data.get("department_id")
    page = data.get("page", 1)
    per_page = data.get("per_page", 20)

    if not keyword:
        return jsonify({"code": 400, "message": "请输入搜索关键词"}), 400

    # 构建查询
    query = CiInstance.query.filter(
        db.or_(
            CiInstance.code.contains(keyword),
            CiInstance.name.contains(keyword),
            CiInstance.attribute_values.contains(keyword),
        )
    )

    if model_id:
        query = query.filter_by(model_id=model_id)
    if department_id:
        query = query.filter_by(department_id=department_id)

    # 数据权限过滤
    if not require_admin():
        identity = get_jwt_identity()
        query = query.filter_by(created_by=int(identity))

    pagination = query.order_by(CiInstance.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "items": [instance.to_dict() for instance in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "keyword": keyword,
            },
        }
    )


# ==================== 文件上传 ====================


@ci_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    """上传文件"""
    if "file" not in request.files:
        return jsonify({"code": 400, "message": "没有选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 400, "message": "没有选择文件"}), 400

    if not allowed_file(file.filename):
        return jsonify({"code": 400, "message": "不支持的文件类型"}), 400

    # 生成唯一文件名
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

    # 按日期创建子目录
    today = datetime.now().strftime("%Y%m%d")
    upload_dir = os.path.join(UPLOAD_FOLDER, today)
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return jsonify(
        {
            "code": 200,
            "message": "上传成功",
            "data": {
                "filename": filename,
                "path": f"{today}/{filename}",
                "url": f"/api/v1/cmdb/instances/files/{today}/{filename}",
            },
        }
    )


@ci_bp.route("/files/<path:filepath>", methods=["GET"])
def download_file(filepath):
    """下载文件"""
    normalized_filepath = (filepath or "").replace("\\", "/").strip("/")
    if not normalized_filepath:
        return jsonify({"code": 404, "message": "文件不存在"}), 404

    filename = os.path.basename(normalized_filepath)
    rel_dir = os.path.dirname(normalized_filepath)

    # 兼容历史部署：优先 backend/uploads，再兜底当前工作目录 uploads
    candidate_roots = [UPLOAD_FOLDER, os.path.abspath("uploads")]
    for root in candidate_roots:
        directory = os.path.join(root, rel_dir)
        fullpath = os.path.join(directory, filename)
        if os.path.exists(fullpath):
            return send_from_directory(directory, filename)

    return jsonify({"code": 404, "message": "文件不存在"}), 404


# ==================== 编码预生成 ====================


@ci_bp.route("/generate-code", methods=["GET"])
@jwt_required()
def generate_code():
    """预生成CI编码"""
    code = generate_ci_code_v2()

    return jsonify({"code": 200, "message": "success", "data": {"code": code}})


# ==================== 批量导入导出 ====================


@ci_bp.route("/export", methods=["POST"])
@jwt_required()
def export_instances():
    """批量导出CI数据"""
    data = request.get_json()
    model_id = data.get("model_id")
    ids = data.get("ids", [])
    keyword = data.get("keyword", "")

    if not model_id:
        return jsonify({"code": 400, "message": "请指定模型ID"}), 400

    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 400, "message": "模型不存在"}), 400

    query = CiInstance.query.filter_by(model_id=model_id)

    if ids:
        query = query.filter(CiInstance.id.in_(ids))

    if keyword:
        query = query.filter(
            db.or_(CiInstance.code.contains(keyword), CiInstance.name.contains(keyword))
        )

    query = filter_by_data_permissions(query, CiInstance)

    instances = query.all()

    fields = (
        ModelField.query.filter_by(model_id=model_id, is_active=True)
        .order_by(ModelField.sort_order)
        .all()
    )

    output = io.StringIO()
    headers = ["CI编码", "CI名称", "部门", "创建人", "创建时间"]
    field_names = [
        "code",
        "name",
        "department_name",
        "created_by_username",
        "created_at",
    ]

    for field in fields:
        headers.append(field.name)
        field_names.append(f"attr_{field.code}")

    writer = csv.writer(output)
    writer.writerow(headers)

    for instance in instances:
        attr_values = instance.get_attribute_values()
        row = [
            instance.code or "",
            instance.name or "",
            instance.department.name if instance.department else "",
            instance.creator.username if instance.creator else "",
            instance.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if instance.created_at
            else "",
        ]

        for field in fields:
            value = attr_values.get(field.code, "")
            if isinstance(value, list):
                value = ",".join(map(str, value))
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            row.append(str(value))

        writer.writerow(row)

    output.seek(0)

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "filename": f"{model.name}_CI_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
                "content": output.getvalue(),
            },
        }
    )


@ci_bp.route("/import", methods=["POST"])
@jwt_required()
def import_instances():
    """批量导入CI数据"""
    identity = get_jwt_identity()
    claims = get_jwt()

    if "file" not in request.files:
        return jsonify({"code": 400, "message": "请上传文件"}), 400

    file = request.files["file"]
    model_id = request.form.get("model_id", type=int)

    if not model_id:
        return jsonify({"code": 400, "message": "请指定模型ID"}), 400

    model = CmdbModel.query.get(model_id)
    if not model:
        return jsonify({"code": 400, "message": "模型不存在"}), 400

    fields = (
        ModelField.query.filter_by(model_id=model_id, is_active=True)
        .order_by(ModelField.sort_order)
        .all()
    )
    field_codes = [f.code for f in fields]

    try:
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        reader = csv.reader(stream)
        header = next(reader)

        name_idx = None
        code_idx = None
        field_indices = {}

        for i, col in enumerate(header):
            col = col.strip()
            if col == "CI名称":
                name_idx = i
            elif col == "CI编码":
                code_idx = i
            elif col in field_codes:
                field_indices[col] = i

        success_count = 0
        error_messages = []

        for row_idx, row in enumerate(reader, start=2):
            try:
                name = row[name_idx].strip() if name_idx is not None else ""
                code = row[code_idx].strip() if code_idx is not None else ""

                if not name:
                    error_messages.append(f"第{row_idx}行: CI名称不能为空")
                    continue

                if not code:
                    code = generate_ci_code_v2()

                attr_values = {}
                for field_code, idx in field_indices.items():
                    if idx < len(row):
                        value = row[idx].strip()
                        field = next((f for f in fields if f.code == field_code), None)
                        if field and field.field_type == "number" and value:
                            try:
                                value = int(value)
                            except:
                                try:
                                    value = float(value)
                                except:
                                    pass
                        attr_values[field_code] = value

                instance = CiInstance(
                    code=code,
                    name=name,
                    model_id=model_id,
                    attribute_values=json.dumps(attr_values),
                    created_by=int(identity),
                )
                db.session.add(instance)
                success_count += 1

            except Exception as e:
                error_messages.append(f"第{row_idx}行: {str(e)}")

        db.session.commit()

        log_operation(
            int(identity),
            claims.get("username"),
            "CREATE",
            "ci_instance",
            None,
            f"批量导入 {success_count} 个CI",
        )

        return jsonify(
            {
                "code": 200,
                "message": f"导入完成，成功{success_count}条"
                + (f"，失败{len(error_messages)}条" if error_messages else ""),
                "data": {
                    "success_count": success_count,
                    "error_messages": error_messages[:10],
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 400, "message": f"导入失败: {str(e)}"}), 400
