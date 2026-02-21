"""通知模块模型单元测试"""

import pytest
from datetime import datetime
from app.notifications.models import (
    NotificationType,
    Notification,
    NotificationRecipient,
    NotificationTemplate,
)


class TestNotificationType:
    """测试通知类型模型"""

    def test_create_notification_type(self, db_session):
        """测试创建通知类型"""
        notification_type = NotificationType(
            name="test_type",
            description="Test description",
            icon="bell",
            color="#1890ff"
        )
        db_session.add(notification_type)
        db_session.commit()

        assert notification_type.id is not None
        assert notification_type.name == "test_type"
        assert notification_type.icon == "bell"
        assert notification_type.color == "#1890ff"
        assert notification_type.is_system is False

    def test_notification_type_to_dict(self, db_session):
        """测试通知类型序列化"""
        notification_type = NotificationType(
            name="test_type",
            description="Test description"
        )
        db_session.add(notification_type)
        db_session.commit()

        data = notification_type.to_dict()
        assert data["name"] == "test_type"
        assert data["description"] == "Test description"
        assert "id" in data
        assert "created_at" in data


class TestNotification:
    """测试通知模型"""

    def test_create_notification(self, db_session, test_user, test_notification_type):
        """测试创建通知"""
        notification = Notification(
            title="Test Notification",
            content="This is a test notification",
            type_id=test_notification_type.id,
            sender_id=test_user.id
        )
        db_session.add(notification)
        db_session.commit()

        assert notification.id is not None
        assert notification.title == "Test Notification"
        assert notification.content == "This is a test notification"
        assert notification.content_html is not None
        assert notification.type_id == test_notification_type.id
        assert notification.sender_id == test_user.id

    def test_notification_render_content(self):
        """测试内容渲染"""
        content = "**Bold** and *italic* text"
        html = Notification.render_content(content)

        assert "<strong>Bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_notification_render_content_with_xss(self):
        """测试XSS防护"""
        content = "<script>alert('xss')</script>Normal text"
        html = Notification.render_content(content)

        assert "<script>" not in html
        assert "alert" not in html
        assert "Normal text" in html

    def test_notification_to_dict(self, db_session, test_user, test_notification_type):
        """测试通知序列化"""
        notification = Notification(
            title="Test Notification",
            content="Test content",
            type_id=test_notification_type.id,
            sender_id=test_user.id
        )
        db_session.add(notification)
        db_session.commit()

        data = notification.to_dict()
        assert data["title"] == "Test Notification"
        assert data["content"] == "Test content"
        assert "content_html" in data
        assert data["type"] is not None
        assert data["sender"] is not None

    def test_notification_to_dict_without_html(self, db_session, test_user, test_notification_type):
        """测试不包含HTML的通知序列化"""
        notification = Notification(
            title="Test Notification",
            content="Test content",
            type_id=test_notification_type.id,
            sender_id=test_user.id
        )
        db_session.add(notification)
        db_session.commit()

        data = notification.to_dict(include_content_html=False)
        assert "content_html" not in data


class TestNotificationRecipient:
    """测试通知接收者模型"""

    def test_create_recipient(self, db_session, test_notification, test_user):
        """测试创建接收者记录"""
        recipient = NotificationRecipient(
            notification_id=test_notification.id,
            user_id=test_user.id
        )
        db_session.add(recipient)
        db_session.commit()

        assert recipient.id is not None
        assert recipient.notification_id == test_notification.id
        assert recipient.user_id == test_user.id
        assert recipient.is_read is False
        assert recipient.delivery_status == "pending"

    def test_mark_as_read(self, db_session, test_notification, test_user):
        """测试标记为已读"""
        recipient = NotificationRecipient(
            notification_id=test_notification.id,
            user_id=test_user.id
        )
        db_session.add(recipient)
        db_session.commit()

        recipient.mark_as_read()
        db_session.commit()

        assert recipient.is_read is True
        assert recipient.read_at is not None

    def test_mark_as_unread(self, db_session, test_notification, test_user):
        """测试标记为未读"""
        recipient = NotificationRecipient(
            notification_id=test_notification.id,
            user_id=test_user.id,
            is_read=True,
            read_at=datetime.utcnow()
        )
        db_session.add(recipient)
        db_session.commit()

        recipient.mark_as_unread()
        db_session.commit()

        assert recipient.is_read is False
        assert recipient.read_at is None

    def test_recipient_to_dict(self, db_session, test_notification, test_user):
        """测试接收者序列化"""
        recipient = NotificationRecipient(
            notification_id=test_notification.id,
            user_id=test_user.id
        )
        db_session.add(recipient)
        db_session.commit()

        data = recipient.to_dict()
        assert data["id"] == recipient.id
        assert data["notification_id"] == test_notification.id
        assert data["user_id"] == test_user.id
        assert data["is_read"] is False
        assert "notification" in data


class TestNotificationTemplate:
    """测试通知模板模型"""

    def test_create_template(self, db_session, test_notification_type):
        """测试创建模板"""
        template = NotificationTemplate(
            name="test_template",
            title_template="Hello {{name}}",
            content_template="Welcome to {{place}}",
            type_id=test_notification_type.id
        )
        db_session.add(template)
        db_session.commit()

        assert template.id is not None
        assert template.name == "test_template"
        assert template.title_template == "Hello {{name}}"
        assert template.content_template == "Welcome to {{place}}"

    def test_template_render(self, db_session, test_notification_type):
        """测试模板渲染"""
        template = NotificationTemplate(
            name="test_template",
            title_template="Hello {{name}}",
            content_template="Welcome to {{place}}",
            type_id=test_notification_type.id
        )
        db_session.add(template)
        db_session.commit()

        variables = {"name": "John", "place": "Home"}
        title, content = template.render(variables)

        assert title == "Hello John"
        assert content == "Welcome to Home"

    def test_template_render_missing_variable(self, db_session, test_notification_type):
        """测试模板渲染缺少变量"""
        template = NotificationTemplate(
            name="test_template",
            title_template="Hello {{name}}",
            content_template="Welcome",
            type_id=test_notification_type.id
        )
        db_session.add(template)
        db_session.commit()

        with pytest.raises(ValueError) as exc_info:
            template.render({})

        assert "name" in str(exc_info.value)

    def test_template_to_dict(self, db_session, test_notification_type):
        """测试模板序列化"""
        template = NotificationTemplate(
            name="test_template",
            title_template="Hello {{name}}",
            content_template="Welcome",
            type_id=test_notification_type.id
        )
        db_session.add(template)
        db_session.commit()

        data = template.to_dict()
        assert data["name"] == "test_template"
        assert data["title_template"] == "Hello {{name}}"
        assert "id" in data
