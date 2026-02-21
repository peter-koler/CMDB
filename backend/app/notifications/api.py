"""通知模块REST API端点"""

import os
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app import db
from app.models import User
from app.notifications.services import (
    NotificationService,
    NotificationTypeService,
    NotificationTemplateService,
)
from app.notifications.models import (
    NotificationAttachment,
    NotificationRecipient,
)
from app.notifications.permissions import (
    validate_sender_permission,
    NotificationPermissionError,
    can_send_broadcast,
)
from app.utils.decorators import admin_required

# 创建蓝图
notifications_bp = Blueprint(
    "notifications", __name__, url_prefix="/api/v1/notifications"
)


# ==================== 通知发送 ====================


@notifications_bp.route("", methods=["POST"])
@jwt_required()
def send_notification():
    """发送通知"""
    try:
        data = request.get_json()
        sender_id = int(get_jwt_identity())

        recipient_type = data.get("recipient_type")
        type_id = data.get("type_id")
        title = data.get("title")
        content = data.get("content")
        template_id = data.get("template_id")
        variables = data.get("variables")
        attachments = data.get("attachments", [])

        if not all([recipient_type, type_id, title, content]):
            return jsonify(
                {
                    "code": 400,
                    "message": "缺少必填字段：recipient_type, type_id, title, content",
                }
            ), 400

        if recipient_type == "users":
            user_ids = data.get("user_ids", [])
            if not user_ids:
                return jsonify({"code": 400, "message": "user_ids不能为空"}), 400

            try:
                validate_sender_permission(
                    sender_id=sender_id,
                    recipient_type="users",
                    user_ids=user_ids
                )
            except NotificationPermissionError as e:
                return jsonify({"code": 403, "message": str(e)}), 403

            notification, recipients = NotificationService.send_to_users(
                sender_id=sender_id,
                user_ids=user_ids,
                type_id=type_id,
                title=title,
                content=content,
                template_id=template_id,
                variables=variables,
                attachments=attachments,
            )

        elif recipient_type == "department":
            department_id = data.get("department_id")
            if not department_id:
                return jsonify({"code": 400, "message": "department_id不能为空"}), 400

            try:
                validate_sender_permission(
                    sender_id=sender_id,
                    recipient_type="department",
                    department_id=department_id
                )
            except NotificationPermissionError as e:
                return jsonify({"code": 403, "message": str(e)}), 403

            notification, recipients = NotificationService.send_to_department(
                sender_id=sender_id,
                department_id=department_id,
                type_id=type_id,
                title=title,
                content=content,
                template_id=template_id,
                variables=variables,
                attachments=attachments,
            )
        else:
            return jsonify(
                {"code": 400, "message": f"不支持的recipient_type: {recipient_type}"}
            ), 400

        return jsonify(
            {
                "code": 201,
                "message": "通知发送成功",
                "data": {
                    "notification": notification.to_dict(),
                    "recipient_count": len(recipients),
                },
            }
        ), 201

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except NotificationPermissionError as e:
        return jsonify({"code": 403, "message": str(e)}), 403
    except Exception as e:
        current_app.logger.error(f"发送通知失败: {e}")
        return jsonify({"code": 500, "message": "发送通知失败"}), 500


@notifications_bp.route("/broadcast", methods=["POST"])
@jwt_required()
def send_broadcast():
    """发送全员广播通知（仅管理员）"""
    try:
        data = request.get_json()
        sender_id = int(get_jwt_identity())

        type_id = data.get("type_id")
        title = data.get("title")
        content = data.get("content")
        template_id = data.get("template_id")
        variables = data.get("variables")
        attachments = data.get("attachments", [])

        if not all([type_id, title, content]):
            return jsonify(
                {
                    "code": 400,
                    "message": "缺少必填字段：type_id, title, content",
                }
            ), 400

        sender = User.query.get(sender_id)
        if not sender or not can_send_broadcast(sender):
            return jsonify(
                {"code": 403, "message": "只有管理员可以发送全员广播"}
            ), 403

        notification, recipients = NotificationService.send_broadcast(
            sender_id=sender_id,
            type_id=type_id,
            title=title,
            content=content,
            template_id=template_id,
            variables=variables,
            attachments=attachments,
        )

        return jsonify(
            {
                "code": 201,
                "message": "广播发送成功",
                "data": {
                    "notification": notification.to_dict(),
                    "recipient_count": len(recipients),
                },
            }
        ), 201

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"发送广播失败: {e}")
        return jsonify({"code": 500, "message": "发送广播失败"}), 500


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_sent_notifications():
    """获取发送的通知列表（管理员/发送者查看）"""
    try:
        # 获取查询参数
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        # TODO: 实现发送通知列表查询
        # 这里简化处理，实际应该查询Notification表

        return jsonify(
            {
                "code": 200,
                "data": {
                    "items": [],
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": 0,
                        "total_pages": 0,
                    },
                },
            }
        )

    except Exception as e:
        current_app.logger.error(f"获取发送通知列表失败: {e}")
        return jsonify({"code": 500, "message": "获取列表失败"}), 500


@notifications_bp.route("/<int:notification_id>", methods=["GET"])
@jwt_required()
def get_notification(notification_id: int):
    """获取通知详情"""
    try:
        # TODO: 实现通知详情查询

        return jsonify({"code": 200, "data": {}})

    except Exception as e:
        current_app.logger.error(f"获取通知详情失败: {e}")
        return jsonify({"code": 500, "message": "获取详情失败"}), 500


# ==================== 用户通知 ====================


@notifications_bp.route("/my", methods=["GET"])
@jwt_required()
def get_my_notifications():
    """获取我的通知列表"""
    try:
        user_id = int(get_jwt_identity())

        # 获取查询参数
        is_read = request.args.get("is_read")
        if is_read is not None:
            is_read = is_read.lower() == "true"

        type_id = request.args.get("type_id", type=int)
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        # 限制页大小
        max_page_size = current_app.config.get("PAGE_MAX_SIZE", 100)
        page_size = min(page_size, max_page_size)

        result = NotificationService.get_user_notifications(
            user_id=user_id,
            is_read=is_read,
            type_id=type_id,
            page=page,
            page_size=page_size,
        )

        return jsonify({"code": 200, "data": result})

    except Exception as e:
        current_app.logger.error(f"获取通知列表失败: {e}")
        return jsonify({"code": 500, "message": "获取列表失败"}), 500


@notifications_bp.route("/my/<int:recipient_id>", methods=["GET"])
@jwt_required()
def get_notification_detail(recipient_id: int):
    """获取单个通知详情"""
    try:
        user_id = int(get_jwt_identity())

        recipient = NotificationRecipient.query.filter_by(
            id=recipient_id, user_id=user_id
        ).first()

        if not recipient:
            return jsonify({"code": 404, "message": "通知不存在"}), 404

        return jsonify(
            {
                "code": 200,
                "data": recipient.to_dict(include_notification=True),
            }
        )

    except Exception as e:
        current_app.logger.error(f"获取通知详情失败: {e}")
        return jsonify({"code": 500, "message": "获取详情失败"}), 500


@notifications_bp.route("/my/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    """获取未读通知数量"""
    try:
        user_id = int(get_jwt_identity())
        count = NotificationService.get_unread_count(user_id)

        return jsonify({"code": 200, "data": {"count": count}})

    except Exception as e:
        current_app.logger.error(f"获取未读数量失败: {e}")
        return jsonify({"code": 500, "message": "获取失败"}), 500


@notifications_bp.route("/my/<int:recipient_id>/read", methods=["PATCH"])
@jwt_required()
def mark_as_read(recipient_id: int):
    """标记通知为已读"""
    try:
        user_id = int(get_jwt_identity())

        recipient = NotificationService.mark_as_read(recipient_id, user_id)

        return jsonify(
            {"code": 200, "message": "已标记为已读", "data": recipient.to_dict()}
        )

    except ValueError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"标记已读失败: {e}")
        return jsonify({"code": 500, "message": "操作失败"}), 500


@notifications_bp.route("/my/<int:recipient_id>/unread", methods=["PATCH"])
@jwt_required()
def mark_as_unread(recipient_id: int):
    """标记通知为未读"""
    try:
        user_id = int(get_jwt_identity())

        recipient = NotificationService.mark_as_unread(recipient_id, user_id)

        return jsonify(
            {"code": 200, "message": "已标记为未读", "data": recipient.to_dict()}
        )

    except ValueError as e:
        return jsonify({"code": 404, "message": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"标记未读失败: {e}")
        return jsonify({"code": 500, "message": "操作失败"}), 500


@notifications_bp.route("/my/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_as_read():
    """标记所有通知为已读"""
    try:
        user_id = int(get_jwt_identity())

        marked_count = NotificationService.mark_all_as_read(user_id)

        return jsonify(
            {
                "code": 200,
                "message": f"已标记 {marked_count} 条通知为已读",
                "data": {"marked_count": marked_count},
            }
        )

    except Exception as e:
        current_app.logger.error(f"全部标记已读失败: {e}")
        return jsonify({"code": 500, "message": "操作失败"}), 500


@notifications_bp.route("/my/<int:recipient_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(recipient_id: int):
    """删除通知"""
    try:
        user_id = int(get_jwt_identity())

        result = NotificationService.delete_notification(recipient_id, user_id)

        if result:
            return jsonify({"code": 200, "message": "删除成功"})
        else:
            return jsonify({"code": 404, "message": "通知不存在"}), 404

    except ValueError as e:
        return jsonify({"code": 403, "message": str(e)}), 403
    except Exception as e:
        current_app.logger.error(f"删除通知失败: {e}")
        return jsonify({"code": 500, "message": "删除失败"}), 500


@notifications_bp.route("/my/search", methods=["GET"])
@jwt_required()
def search_notifications():
    """搜索通知"""
    try:
        user_id = int(get_jwt_identity())

        # 获取查询参数
        query = request.args.get("q")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        type_id = request.args.get("type_id", type=int)
        is_read = request.args.get("is_read")
        if is_read is not None:
            is_read = is_read.lower() == "true"
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        # 解析日期
        from app.notifications.utils import parse_datetime

        date_from_dt = parse_datetime(date_from) if date_from else None
        date_to_dt = parse_datetime(date_to) if date_to else None

        # 限制页大小
        max_page_size = current_app.config.get("PAGE_MAX_SIZE", 100)
        page_size = min(page_size, max_page_size)

        result = NotificationService.search_notifications(
            user_id=user_id,
            query=query,
            date_from=date_from_dt,
            date_to=date_to_dt,
            type_id=type_id,
            is_read=is_read,
            page=page,
            page_size=page_size,
        )

        return jsonify({"code": 200, "data": result})

    except Exception as e:
        current_app.logger.error(f"搜索通知失败: {e}")
        return jsonify({"code": 500, "message": "搜索失败"}), 500


# ==================== 通知类型管理 ====================


@notifications_bp.route("/types", methods=["GET"])
@jwt_required()
def list_notification_types():
    """获取通知类型列表"""
    try:
        types = NotificationTypeService.get_types()

        return jsonify({"code": 200, "data": {"items": [t.to_dict() for t in types]}})

    except Exception as e:
        current_app.logger.error(f"获取类型列表失败: {e}")
        return jsonify({"code": 500, "message": "获取失败"}), 500


@notifications_bp.route("/types", methods=["POST"])
@jwt_required()
@admin_required
def create_notification_type():
    """创建通知类型（管理员）"""
    try:
        data = request.get_json()

        name = data.get("name")
        description = data.get("description", "")
        icon = data.get("icon", "bell")
        color = data.get("color", "#1890ff")

        if not name:
            return jsonify({"code": 400, "message": "name不能为空"}), 400

        notification_type = NotificationTypeService.create_type(
            name=name, description=description, icon=icon, color=color
        )

        return jsonify(
            {"code": 201, "message": "创建成功", "data": notification_type.to_dict()}
        ), 201

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"创建类型失败: {e}")
        return jsonify({"code": 500, "message": "创建失败"}), 500


@notifications_bp.route("/types/<int:type_id>", methods=["GET"])
@jwt_required()
def get_notification_type(type_id: int):
    """获取通知类型详情"""
    try:
        notification_type = NotificationTypeService.get_type(type_id)

        if not notification_type:
            return jsonify({"code": 404, "message": "类型不存在"}), 404

        return jsonify({"code": 200, "data": notification_type.to_dict()})

    except Exception as e:
        current_app.logger.error(f"获取类型详情失败: {e}")
        return jsonify({"code": 500, "message": "获取失败"}), 500


@notifications_bp.route("/types/<int:type_id>", methods=["PATCH"])
@jwt_required()
@admin_required
def update_notification_type(type_id: int):
    """更新通知类型（管理员）"""
    try:
        data = request.get_json()

        notification_type = NotificationTypeService.update_type(
            type_id=type_id,
            name=data.get("name"),
            description=data.get("description"),
            icon=data.get("icon"),
            color=data.get("color"),
        )

        return jsonify(
            {"code": 200, "message": "更新成功", "data": notification_type.to_dict()}
        )

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"更新类型失败: {e}")
        return jsonify({"code": 500, "message": "更新失败"}), 500


@notifications_bp.route("/types/<int:type_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_notification_type(type_id: int):
    """删除通知类型（管理员）"""
    try:
        NotificationTypeService.delete_type(type_id)

        return jsonify({"code": 204, "message": "删除成功"}), 204

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"删除类型失败: {e}")
        return jsonify({"code": 500, "message": "删除失败"}), 500


# ==================== 通知模板管理 ====================


@notifications_bp.route("/templates", methods=["GET"])
@jwt_required()
def list_templates():
    """获取模板列表"""
    try:
        templates = NotificationTemplateService.get_templates()

        return jsonify(
            {"code": 200, "data": {"items": [t.to_dict() for t in templates]}}
        )

    except Exception as e:
        current_app.logger.error(f"获取模板列表失败: {e}")
        return jsonify({"code": 500, "message": "获取失败"}), 500


@notifications_bp.route("/templates", methods=["POST"])
@jwt_required()
@admin_required
def create_template():
    """创建通知模板（管理员）"""
    try:
        data = request.get_json()

        name = data.get("name")
        title_template = data.get("title_template")
        content_template = data.get("content_template")
        type_id = data.get("type_id")
        description = data.get("description", "")
        variables = data.get("variables", [])

        if not all([name, title_template, content_template, type_id]):
            return jsonify(
                {
                    "code": 400,
                    "message": "缺少必填字段：name, title_template, content_template, type_id",
                }
            ), 400

        template = NotificationTemplateService.create_template(
            name=name,
            title_template=title_template,
            content_template=content_template,
            type_id=type_id,
            description=description,
            variables=variables,
        )

        return jsonify(
            {"code": 201, "message": "创建成功", "data": template.to_dict()}
        ), 201

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"创建模板失败: {e}")
        return jsonify({"code": 500, "message": "创建失败"}), 500


@notifications_bp.route("/templates/<int:template_id>", methods=["GET"])
@jwt_required()
def get_template(template_id: int):
    """获取模板详情"""
    try:
        template = NotificationTemplateService.get_template(template_id)

        if not template:
            return jsonify({"code": 404, "message": "模板不存在"}), 404

        return jsonify({"code": 200, "data": template.to_dict()})

    except Exception as e:
        current_app.logger.error(f"获取模板详情失败: {e}")
        return jsonify({"code": 500, "message": "获取失败"}), 500


@notifications_bp.route("/templates/<int:template_id>", methods=["PATCH"])
@jwt_required()
@admin_required
def update_template(template_id: int):
    """更新模板（管理员）"""
    try:
        data = request.get_json()

        template = NotificationTemplateService.update_template(
            template_id=template_id, **data
        )

        return jsonify({"code": 200, "message": "更新成功", "data": template.to_dict()})

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"更新模板失败: {e}")
        return jsonify({"code": 500, "message": "更新失败"}), 500


@notifications_bp.route("/templates/<int:template_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_template(template_id: int):
    """删除模板（管理员）"""
    try:
        NotificationTemplateService.delete_template(template_id)

        return jsonify({"code": 204, "message": "删除成功"}), 204

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"删除模板失败: {e}")
        return jsonify({"code": 500, "message": "删除失败"}), 500


@notifications_bp.route("/templates/<int:template_id>/preview", methods=["POST"])
@jwt_required()
@admin_required
def preview_template(template_id: int):
    """预览模板渲染结果"""
    try:
        data = request.get_json()
        variables = data.get("variables", {})

        title, content = NotificationTemplateService.render_preview(
            template_id=template_id, variables=variables
        )

        return jsonify({"code": 200, "data": {"title": title, "content": content}})

    except ValueError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"预览模板失败: {e}")
        return jsonify({"code": 500, "message": "预览失败"}), 500


# ==================== 附件管理 ====================

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "notifications")
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@notifications_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_attachment():
    """上传通知附件"""
    try:
        if 'file' not in request.files:
            return jsonify({"code": 400, "message": "没有选择文件"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"code": 400, "message": "没有选择文件"}), 400

        if not allowed_file(file.filename):
            return jsonify({"code": 400, "message": "不支持的文件类型"}), 400

        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

        today = datetime.now().strftime("%Y%m%d")
        upload_dir = os.path.join(UPLOAD_FOLDER, today)
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        mime_type = file.content_type or 'application/octet-stream'

        return jsonify({
            "code": 200,
            "message": "上传成功",
            "data": {
                "filename": filename,
                "original_filename": original_filename,
                "file_path": f"{today}/{filename}",
                "file_size": file_size,
                "mime_type": mime_type,
            }
        })

    except Exception as e:
        current_app.logger.error(f"上传附件失败: {e}")
        return jsonify({"code": 500, "message": "上传失败"}), 500


@notifications_bp.route("/attachments/<int:attachment_id>/download", methods=["GET"])
@jwt_required()
def download_attachment(attachment_id: int):
    """下载通知附件"""
    try:
        user_id = int(get_jwt_identity())

        attachment = NotificationAttachment.query.get(attachment_id)
        if not attachment:
            return jsonify({"code": 404, "message": "附件不存在"}), 404

        recipient = db.session.query(NotificationRecipient).filter_by(
            notification_id=attachment.notification_id,
            user_id=user_id
        ).first()

        if not recipient:
            return jsonify({"code": 403, "message": "无权下载此附件"}), 403

        directory = os.path.join(UPLOAD_FOLDER, os.path.dirname(attachment.file_path))
        filename = os.path.basename(attachment.file_path)

        if not os.path.exists(os.path.join(directory, filename)):
            return jsonify({"code": 404, "message": "文件不存在"}), 404

        return send_from_directory(
            directory,
            filename,
            as_attachment=True,
            download_name=attachment.original_filename
        )

    except Exception as e:
        current_app.logger.error(f"下载附件失败: {e}")
        return jsonify({"code": 500, "message": "下载失败"}), 500
