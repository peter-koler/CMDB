from app import db
from datetime import datetime, timezone
import markdown
import bleach
import re

def get_local_now():
    """获取本地时间（不带时区信息，用于数据库存储）"""
    return datetime.now()


def format_datetime(dt):
    """格式化时间为ISO格式，带时区信息"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# Allowed HTML tags for notification content
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "a",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
    "blockquote",
    "img",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "span",
    "div",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "code": ["class"],
    "img": ["src", "alt", "title", "width", "height"],
    "span": ["style", "class"],
    "div": ["style", "class"],
    "table": ["style", "class"],
    "td": ["style", "class", "colspan", "rowspan"],
    "th": ["style", "class", "colspan", "rowspan"],
}


class NotificationType(db.Model):
    """通知类型定义"""

    __tablename__ = "notification_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default="bell")
    color = db.Column(db.String(20), default="#1890ff")
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_local_now)
    updated_at = db.Column(
        db.DateTime, default=get_local_now, onupdate=get_local_now
    )

    # Relationships
    notifications = db.relationship(
        "Notification", back_populates="type", lazy="dynamic"
    )
    templates = db.relationship(
        "NotificationTemplate", back_populates="type", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "is_system": self.is_system,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }


class Notification(db.Model):
    """通知实体"""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Markdown格式
    content_html = db.Column(db.Text, nullable=False)  # 渲染后的HTML

    # Foreign Keys
    type_id = db.Column(
        db.Integer, db.ForeignKey("notification_types.id"), nullable=False
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    template_id = db.Column(
        db.Integer, db.ForeignKey("notification_templates.id"), nullable=True
    )

    # Timestamps
    created_at = db.Column(db.DateTime, default=get_local_now)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Archive status
    is_archived = db.Column(db.Boolean, default=False)

    # Relationships
    type = db.relationship("NotificationType", back_populates="notifications")
    sender = db.relationship("User", backref="sent_notifications")
    template = db.relationship("NotificationTemplate", back_populates="notifications")
    recipients = db.relationship(
        "NotificationRecipient",
        back_populates="notification",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __init__(self, **kwargs):
        super(Notification, self).__init__(**kwargs)
        if self.content and not self.content_html:
            self.content_html = self.render_content(self.content)

    @staticmethod
    def render_content(content):
        """将内容渲染为安全HTML（支持富文本）"""
        if not content:
            return ""
        sanitized = re.sub(
            r"<(script|style)[^>]*>.*?</\1>",
            "",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        html = markdown.markdown(sanitized)
        clean_html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
        return clean_html

    def to_dict(self, include_content_html=True):
        data = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type.to_dict() if self.type else None,
            "sender": {
                "id": self.sender.id,
                "username": self.sender.username,
                "display_name": self.sender.username,
            }
            if self.sender
            else None,
            "created_at": format_datetime(self.created_at),
            "expires_at": format_datetime(self.expires_at),
            "attachments": [a.to_dict() for a in self.attachments] if self.attachments else [],
        }
        if include_content_html:
            data["content_html"] = self.content_html
        return data


class NotificationRecipient(db.Model):
    """通知接收人状态"""

    __tablename__ = "notification_recipients"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer, db.ForeignKey("notifications.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Read status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)

    # Delivery tracking
    delivery_status = db.Column(
        db.String(20), default="pending"
    )  # pending, delivered, failed, permanent_failure
    delivery_attempts = db.Column(db.Integer, default=0)
    last_attempt_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=get_local_now)

    # Relationships
    notification = db.relationship("Notification", back_populates="recipients")
    user = db.relationship("User", backref="notification_recipients")

    # Indexes for performance
    __table_args__ = (
        db.Index("idx_recipients_user_read", "user_id", "is_read", "created_at"),
        db.Index("idx_recipients_user_created", "user_id", "created_at"),
        db.Index("idx_recipients_notification", "notification_id"),
        db.UniqueConstraint(
            "notification_id", "user_id", name="uq_recipient_notification_user"
        ),
    )

    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = get_local_now()
            db.session.commit()

    def mark_as_unread(self):
        """标记为未读"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            db.session.commit()

    def to_dict(self, include_notification=True):
        data = {
            "id": self.id,
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "is_read": self.is_read,
            "read_at": format_datetime(self.read_at),
            "delivery_status": self.delivery_status,
            "created_at": format_datetime(self.created_at),
        }
        if include_notification:
            data["notification"] = self.notification.to_dict() if self.notification else None
        return data


class NotificationAttachment(db.Model):
    """通知附件"""

    __tablename__ = "notification_attachments"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer, db.ForeignKey("notifications.id"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_now)

    notification = db.relationship("Notification", backref="attachments")

    def to_dict(self):
        return {
            "id": self.id,
            "notification_id": self.notification_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "download_url": f"/api/v1/notifications/attachments/{self.id}/download",
            "created_at": format_datetime(self.created_at),
        }


class NotificationTemplate(db.Model):
    """通知模板"""

    __tablename__ = "notification_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    title_template = db.Column(db.String(255), nullable=False)
    content_template = db.Column(db.Text, nullable=False)
    variables = db.Column(db.JSON, default=list)  # 变量名列表

    # Foreign Key
    type_id = db.Column(
        db.Integer, db.ForeignKey("notification_types.id"), nullable=False
    )

    # Timestamps
    created_at = db.Column(db.DateTime, default=get_local_now)
    updated_at = db.Column(
        db.DateTime, default=get_local_now, onupdate=get_local_now
    )

    # Relationships
    type = db.relationship("NotificationType", back_populates="templates")
    notifications = db.relationship(
        "Notification", back_populates="template", lazy="dynamic"
    )

    def render(self, variables_dict):
        """渲染模板"""
        pattern = re.compile(r"{{\s*(\w+)\s*}}")

        def replace(template):
            def replacer(match):
                key = match.group(1)
                if key not in variables_dict:
                    raise ValueError(f"Missing template variable: {key}")
                return str(variables_dict[key])

            return pattern.sub(replacer, template)

        title = replace(self.title_template)
        content = replace(self.content_template)
        return title, content

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "title_template": self.title_template,
            "content_template": self.content_template,
            "variables": self.variables,
            "type_id": self.type_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def init_default_notification_types():
    """初始化默认通知类型"""
    default_types = [
        {
            "name": "system",
            "description": "系统警报和公告",
            "icon": "warning",
            "color": "#ff4d4f",
            "is_system": True,
        },
        {
            "name": "task",
            "description": "任务分配和更新",
            "icon": "check-circle",
            "color": "#52c41a",
            "is_system": True,
        },
        {
            "name": "message",
            "description": "直接消息",
            "icon": "message",
            "color": "#1890ff",
            "is_system": True,
        },
        {
            "name": "announcement",
            "description": "一般公告",
            "icon": "notification",
            "color": "#faad14",
            "is_system": True,
        },
    ]

    for type_data in default_types:
        if not NotificationType.query.filter_by(name=type_data["name"]).first():
            notification_type = NotificationType(**type_data)
            db.session.add(notification_type)

    db.session.commit()
