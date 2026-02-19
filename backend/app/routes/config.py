import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from app.models.config import SystemConfig
from app.routes.auth import log_operation

config_bp = Blueprint("config", __name__, url_prefix="/api/v1/configs")

CONFIG_DESCRIPTIONS = {
    "access_token_expire": "Access Token有效期（分钟）",
    "refresh_token_expire": "Refresh Token有效期（分钟）",
    "password_min_length": "密码最小长度",
    "password_force_change_days": "强制修改密码周期（天）",
    "password_history_count": "密码历史检查次数",
    "max_login_failures": "最大登录失败次数",
    "lock_duration_hours": "账户锁定时长（小时）",
    "log_retention_days": "日志保留天数",
    "require_uppercase": "密码需要大写字母",
    "require_lowercase": "密码需要小写字母",
    "require_digit": "密码需要数字",
    "require_special": "密码需要特殊字符",
    "site_logo": "系统Logo",
    "site_name": "系统名称",
}

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@config_bp.route("", methods=["GET"])
@jwt_required()
def get_configs():
    configs = SystemConfig.query.all()
    data = {}
    for config in configs:
        desc = CONFIG_DESCRIPTIONS.get(config.config_key, "")
        data[config.config_key] = {"value": config.config_value, "description": desc}
    return jsonify({"code": 200, "data": data})


@config_bp.route("", methods=["PUT"])
@jwt_required()
def update_configs():
    if not require_admin():
        return jsonify({"code": 403, "message": "无权限修改配置"}), 403

    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()

    for key, value in data.items():
        if key in CONFIG_DESCRIPTIONS:
            SystemConfig.set_value(key, str(value), int(identity))

    log_operation(
        int(identity), claims.get("username"), "UPDATE", "config", None, "更新系统配置"
    )

    return jsonify({"code": 200, "message": "配置更新成功"})


@config_bp.route("/logo", methods=["POST"])
@jwt_required()
def upload_logo():
    if not require_admin():
        return jsonify({"code": 403, "message": "无权限上传Logo"}), 403

    if "file" not in request.files:
        return jsonify({"code": 400, "message": "未找到上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 400, "message": "未选择文件"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "code": 400,
                    "message": "不支持的文件格式，请上传 png, jpg, jpeg, gif, svg, webp 格式的图片",
                }
            ),
            400,
        )

    # 检查文件大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({"code": 400, "message": "文件大小超过2MB限制"}), 400

    # 确保上传目录存在
    upload_folder = os.path.join(current_app.root_path, "..", "uploads", "logos")
    os.makedirs(upload_folder, exist_ok=True)

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"logo_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(upload_folder, filename)

    # 删除旧logo
    old_logo = SystemConfig.get_value("site_logo", "")
    if old_logo:
        old_filepath = os.path.join(upload_folder, os.path.basename(old_logo))
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except:
                pass

    # 保存文件
    file.save(filepath)

    # 更新配置
    identity = get_jwt_identity()
    file_url = f"/api/v1/configs/logo/{filename}"
    SystemConfig.set_value("site_logo", file_url, int(identity))

    # 记录日志
    claims = get_jwt()
    log_operation(
        int(identity), claims.get("username"), "UPDATE", "config", None, "上传系统Logo"
    )

    return jsonify(
        {"code": 200, "message": "Logo上传成功", "data": {"logo_url": file_url}}
    )


@config_bp.route("/logo/<filename>", methods=["GET"])
def get_logo(filename):
    upload_folder = os.path.join(current_app.root_path, "..", "uploads", "logos")
    return send_from_directory(upload_folder, filename)


@config_bp.route("/logo", methods=["DELETE"])
@jwt_required()
def delete_logo():
    if not require_admin():
        return jsonify({"code": 403, "message": "无权限删除Logo"}), 403

    identity = get_jwt_identity()
    claims = get_jwt()

    # 删除旧logo文件
    old_logo = SystemConfig.get_value("site_logo", "")
    if old_logo:
        upload_folder = os.path.join(current_app.root_path, "..", "uploads", "logos")
        old_filepath = os.path.join(upload_folder, os.path.basename(old_logo))
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except:
                pass

    # 清空配置
    SystemConfig.set_value("site_logo", "", int(identity))

    log_operation(
        int(identity), claims.get("username"), "UPDATE", "config", None, "删除系统Logo"
    )

    return jsonify({"code": 200, "message": "Logo删除成功"})
