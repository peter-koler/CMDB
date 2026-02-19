"""
Arco CMDB 平台站内通知模块

模块结构:
- models.py: 数据模型
- services.py: 业务服务
- api.py: REST API
- websocket.py: WebSocket事件
- utils.py: 工具函数
"""

from app.notifications.models import (
    Notification,
    NotificationRecipient,
    NotificationType,
    NotificationTemplate,
    init_default_notification_types,
)

__all__ = [
    "Notification",
    "NotificationRecipient",
    "NotificationType",
    "NotificationTemplate",
    "init_default_notification_types",
]
