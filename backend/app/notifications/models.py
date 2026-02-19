from app import db
from datetime import datetime
import markdown
import bleach
from markupsafe import Markup

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
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"], "code": ["class"]}


class NotificationType(db.Model):
    """通知类型定义"""

    __tablename__ = "notification_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default="bell")
    color = db.Column(db.String(20), default="#1890ff")
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
        """将Markdown内容渲染为安全HTML"""
        html = markdown.markdown(content, extensions=["nl2br", "fenced_code"])
        clean_html = bleach.clean(
            html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            self.read_at = datetime.utcnow()
            db.session.commit()

    def mark_as_unread(self):
        """标记为未读"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "notification": self.notification.to_dict() if self.notification else None,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "delivery_status": self.delivery_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    type = db.relationship("NotificationType", back_populates="templates")
    notifications = db.relationship(
        "Notification", back_populates="template", lazy="dynamic"
    )

    def render(self, variables_dict):
        """渲染模板"""
        try:
            title = self.title_template.format(**variables_dict)
            content = self.content_template.format(**variables_dict)
            return title, content
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

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
