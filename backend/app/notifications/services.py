"""通知模块业务服务层"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, or_, and_
from flask import current_app

from app import db
from app.models import User, Department
from app.notifications.models import (
    Notification,
    NotificationRecipient,
    NotificationType,
    NotificationTemplate,
    NotificationAttachment,
    init_default_notification_types,
)
from app.notifications.utils import render_markdown, validate_notification_content
from app.notifications.websocket import (
    emit_to_user,
    emit_to_users,
    emit_read_status,
    emit_unread_status,
    emit_read_all,
)


def get_local_now():
    """获取本地时间"""
    return datetime.now(timezone.utc).astimezone()


class NotificationService:
    """通知服务类"""

    @staticmethod
    def send_to_users(
        sender_id: int,
        user_ids: List[int],
        type_id: int,
        title: str,
        content: str,
        template_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Notification, List[NotificationRecipient]]:
        """向指定用户发送通知

        Args:
            sender_id: 发送者用户ID
            user_ids: 接收者用户ID列表
            type_id: 通知类型ID
            title: 通知标题
            content: 通知内容（富文本HTML格式）
            template_id: 模板ID（可选）
            variables: 模板变量（可选）
            attachments: 附件列表（可选）

        Returns:
            (Notification对象, NotificationRecipient列表)
        """
        is_valid, error_msg = validate_notification_content(title, content)
        if not is_valid:
            raise ValueError(error_msg)

        sender = User.query.get(sender_id)
        if not sender:
            raise ValueError("发送者不存在")

        notification_type = NotificationType.query.get(type_id)
        if not notification_type:
            raise ValueError("通知类型不存在")

        if template_id and variables:
            template = NotificationTemplate.query.get(template_id)
            if template:
                try:
                    title, content = template.render(variables)
                except ValueError as e:
                    raise ValueError(f"模板渲染失败: {e}")

        retention_days = current_app.config.get("NOTIFICATION_RETENTION_DAYS", 90)
        expires_at = get_local_now() + timedelta(days=retention_days)

        # 创建通知
        notification = Notification(
            title=title,
            content=content,
            content_html=Notification.render_content(content),
            type_id=type_id,
            sender_id=sender_id,
            template_id=template_id,
            expires_at=expires_at,
        )
        db.session.add(notification)
        db.session.flush()

        if attachments:
            for att in attachments:
                attachment = NotificationAttachment(
                    notification_id=notification.id,
                    filename=att.get("filename"),
                    original_filename=att.get("original_filename"),
                    file_path=att.get("file_path"),
                    file_size=att.get("file_size"),
                    mime_type=att.get("mime_type"),
                )
                db.session.add(attachment)

        # 创建接收人记录
        recipients = []
        valid_user_ids = set()

        for user_id in set(user_ids):
            user = User.query.filter_by(id=user_id, status="active").first()
            if user:
                recipient = NotificationRecipient(
                    notification_id=notification.id,
                    user_id=user_id,
                    delivery_status="pending",
                )
                db.session.add(recipient)
                recipients.append(recipient)
                valid_user_ids.add(user_id)

        db.session.commit()

        notification_data = notification.to_dict()
        for recipient in recipients:
            notification_data["recipient_id"] = recipient.id
            emit_to_user(recipient.user_id, "notification:new", notification_data)

        current_app.logger.info(
            f"Notification sent: id={notification.id}, "
            f"sender={sender_id}, recipients={len(recipients)}"
        )

        return notification, recipients

    @staticmethod
    def send_to_department(
        sender_id: int,
        department_id: int,
        type_id: int,
        title: str,
        content: str,
        template_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Notification, List[NotificationRecipient]]:
        """向部门所有成员发送通知"""
        department = Department.query.get(department_id)
        if not department:
            raise ValueError("部门不存在")

        from app.models import User

        members = User.query.filter_by(
            department_id=department_id, status="active"
        ).all()

        if not members:
            raise ValueError("部门没有活跃成员")

        user_ids = [member.id for member in members]

        return NotificationService.send_to_users(
            sender_id=sender_id,
            user_ids=user_ids,
            type_id=type_id,
            title=title,
            content=content,
            template_id=template_id,
            variables=variables,
            attachments=attachments,
        )

    @staticmethod
    def send_broadcast(
        sender_id: int,
        type_id: int,
        title: str,
        content: str,
        template_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Notification, List[NotificationRecipient]]:
        """发送全员广播通知"""
        from app.models import User

        users = User.query.filter_by(status="active").all()

        if not users:
            raise ValueError("没有活跃用户")

        user_ids = [user.id for user in users]

        return NotificationService.send_to_users(
            sender_id=sender_id,
            user_ids=user_ids,
            type_id=type_id,
            title=title,
            content=content,
            template_id=template_id,
            variables=variables,
            attachments=attachments,
        )

    @staticmethod
    def get_user_notifications(
        user_id: int,
        is_read: Optional[bool] = None,
        type_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取用户的通知列表

        Args:
            user_id: 用户ID
            is_read: 是否已读筛选（可选）
            type_id: 类型筛选（可选）
            page: 页码
            page_size: 每页数量

        Returns:
            包含通知列表和分页信息的字典
        """
        query = NotificationRecipient.query.filter_by(user_id=user_id)

        # 应用筛选
        if is_read is not None:
            query = query.filter(NotificationRecipient.is_read == is_read)

        if type_id:
            query = query.join(Notification).filter(Notification.type_id == type_id)

        # 排序：未读优先，然后按时间倒序
        query = query.order_by(
            NotificationRecipient.is_read.asc(), NotificationRecipient.created_at.desc()
        )

        # 分页
        total = query.count()
        recipients = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [r.to_dict() for r in recipients],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """获取用户未读通知数量

        Args:
            user_id: 用户ID

        Returns:
            未读数量
        """
        return NotificationRecipient.query.filter_by(
            user_id=user_id, is_read=False
        ).count()

    @staticmethod
    def mark_as_read(recipient_id: int, user_id: int) -> NotificationRecipient:
        """标记通知为已读

        Args:
            recipient_id: 接收者记录ID
            user_id: 用户ID（用于权限验证）

        Returns:
            NotificationRecipient对象
        """
        recipient = NotificationRecipient.query.filter_by(
            id=recipient_id, user_id=user_id
        ).first()

        if not recipient:
            raise ValueError("通知不存在或无权限")

        if not recipient.is_read:
            recipient.mark_as_read()

            # WebSocket同步
            emit_read_status(
                recipient_id=recipient.id,
                notification_id=recipient.notification_id,
                user_id=user_id,
            )

        return recipient

    @staticmethod
    def mark_as_unread(recipient_id: int, user_id: int) -> NotificationRecipient:
        """标记通知为未读

        Args:
            recipient_id: 接收者记录ID
            user_id: 用户ID（用于权限验证）

        Returns:
            NotificationRecipient对象
        """
        recipient = NotificationRecipient.query.filter_by(
            id=recipient_id, user_id=user_id
        ).first()

        if not recipient:
            raise ValueError("通知不存在或无权限")

        if recipient.is_read:
            recipient.mark_as_unread()

            # WebSocket同步
            emit_unread_status(
                recipient_id=recipient.id,
                notification_id=recipient.notification_id,
                user_id=user_id,
            )

        return recipient

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """标记所有通知为已读

        Args:
            user_id: 用户ID

        Returns:
            标记为已读的数量
        """
        # 批量更新
        result = NotificationRecipient.query.filter_by(
            user_id=user_id, is_read=False
        ).update({"is_read": True, "read_at": get_local_now()})

        db.session.commit()

        emit_read_all(user_id=user_id, marked_count=result)

        return result

    @staticmethod
    def delete_notification(recipient_id: int, user_id: int) -> bool:
        """删除通知

        Args:
            recipient_id: 接收者记录ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否删除成功
        """
        recipient = NotificationRecipient.query.filter_by(
            id=recipient_id, user_id=user_id
        ).first()

        if not recipient:
            return False

        db.session.delete(recipient)
        db.session.commit()

        return True

    @staticmethod
    def search_notifications(
        user_id: int,
        query: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        type_id: Optional[int] = None,
        is_read: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """搜索通知

        Args:
            user_id: 用户ID
            query: 搜索关键词（标题和内容）
            date_from: 开始日期
            date_to: 结束日期
            type_id: 类型筛选
            is_read: 已读状态筛选
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果字典
        """
        # 基础查询：用户的通知
        base_query = NotificationRecipient.query.filter_by(user_id=user_id)

        # Join Notification表用于搜索
        base_query = base_query.join(Notification)

        # 关键词搜索
        if query:
            search_pattern = f"%{query}%"
            base_query = base_query.filter(
                or_(
                    Notification.title.ilike(search_pattern),
                    Notification.content.ilike(search_pattern),
                )
            )

        # 日期范围筛选
        if date_from:
            base_query = base_query.filter(Notification.created_at >= date_from)
        if date_to:
            base_query = base_query.filter(Notification.created_at <= date_to)

        # 类型筛选
        if type_id:
            base_query = base_query.filter(Notification.type_id == type_id)

        # 已读状态筛选
        if is_read is not None:
            base_query = base_query.filter(NotificationRecipient.is_read == is_read)

        # 排序
        base_query = base_query.order_by(Notification.created_at.desc())

        # 分页
        total = base_query.count()
        recipients = base_query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [r.to_dict() for r in recipients],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }


class NotificationTypeService:
    """通知类型服务类"""

    @staticmethod
    def get_types() -> List[NotificationType]:
        """获取所有通知类型"""
        return NotificationType.query.all()

    @staticmethod
    def get_type(type_id: int) -> Optional[NotificationType]:
        """获取指定类型"""
        return NotificationType.query.get(type_id)

    @staticmethod
    def create_type(
        name: str, description: str = "", icon: str = "bell", color: str = "#1890ff"
    ) -> NotificationType:
        """创建通知类型

        Args:
            name: 类型名称（唯一）
            description: 描述
            icon: 图标
            color: 颜色

        Returns:
            NotificationType对象
        """
        # 检查名称是否已存在
        if NotificationType.query.filter_by(name=name).first():
            raise ValueError(f'通知类型名称 "{name}" 已存在')

        notification_type = NotificationType(
            name=name, description=description, icon=icon, color=color, is_system=False
        )
        db.session.add(notification_type)
        db.session.commit()

        return notification_type

    @staticmethod
    def update_type(
        type_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
    ) -> NotificationType:
        """更新通知类型

        Args:
            type_id: 类型ID
            name: 新名称（可选）
            description: 新描述（可选）
            icon: 新图标（可选）
            color: 新颜色（可选）

        Returns:
            NotificationType对象
        """
        notification_type = NotificationType.query.get(type_id)
        if not notification_type:
            raise ValueError("通知类型不存在")

        # 系统类型不允许修改名称
        if notification_type.is_system and name and name != notification_type.name:
            raise ValueError("系统类型的名称不能修改")

        # 检查新名称是否冲突
        if name and name != notification_type.name:
            if NotificationType.query.filter_by(name=name).first():
                raise ValueError(f'通知类型名称 "{name}" 已存在')
            notification_type.name = name

        if description is not None:
            notification_type.description = description
        if icon is not None:
            notification_type.icon = icon
        if color is not None:
            notification_type.color = color

        db.session.commit()
        return notification_type

    @staticmethod
    def delete_type(type_id: int) -> bool:
        """删除通知类型

        Args:
            type_id: 类型ID

        Returns:
            是否删除成功
        """
        notification_type = NotificationType.query.get(type_id)
        if not notification_type:
            raise ValueError("通知类型不存在")

        # 系统类型不能删除
        if notification_type.is_system:
            raise ValueError("系统类型不能删除")

        # 检查是否有关联的通知
        if notification_type.notifications.count() > 0:
            raise ValueError("该类型下存在通知，无法删除")

        db.session.delete(notification_type)
        db.session.commit()

        return True


class NotificationTemplateService:
    """通知模板服务类"""

    @staticmethod
    def get_templates() -> List[NotificationTemplate]:
        """获取所有模板"""
        return NotificationTemplate.query.all()

    @staticmethod
    def get_template(template_id: int) -> Optional[NotificationTemplate]:
        """获取指定模板"""
        return NotificationTemplate.query.get(template_id)

    @staticmethod
    def create_template(
        name: str,
        title_template: str,
        content_template: str,
        type_id: int,
        description: str = "",
        variables: List[str] = None,
    ) -> NotificationTemplate:
        """创建通知模板

        Args:
            name: 模板名称
            title_template: 标题模板
            content_template: 内容模板
            type_id: 类型ID
            description: 描述
            variables: 变量名列表

        Returns:
            NotificationTemplate对象
        """
        # 验证类型存在
        notification_type = NotificationType.query.get(type_id)
        if not notification_type:
            raise ValueError("通知类型不存在")

        template = NotificationTemplate(
            name=name,
            description=description,
            title_template=title_template,
            content_template=content_template,
            type_id=type_id,
            variables=variables or [],
        )
        db.session.add(template)
        db.session.commit()

        return template

    @staticmethod
    def update_template(template_id: int, **kwargs) -> NotificationTemplate:
        """更新模板"""
        template = NotificationTemplate.query.get(template_id)
        if not template:
            raise ValueError("模板不存在")

        allowed_fields = [
            "name",
            "description",
            "title_template",
            "content_template",
            "type_id",
            "variables",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(template, field, value)

        db.session.commit()
        return template

    @staticmethod
    def delete_template(template_id: int) -> bool:
        """删除模板"""
        template = NotificationTemplate.query.get(template_id)
        if not template:
            raise ValueError("模板不存在")

        # 检查是否有关联的通知
        if template.notifications.count() > 0:
            raise ValueError("该模板正在使用中，无法删除")

        db.session.delete(template)
        db.session.commit()

        return True

    @staticmethod
    def render_preview(template_id: int, variables: Dict[str, Any]) -> Tuple[str, str]:
        """预览模板渲染结果

        Args:
            template_id: 模板ID
            variables: 变量值字典

        Returns:
            (标题, 内容)
        """
        template = NotificationTemplate.query.get(template_id)
        if not template:
            raise ValueError("模板不存在")

        return template.render(variables)


def init_notification_module():
    """初始化通知模块"""
    # 初始化默认通知类型
    init_default_notification_types()
