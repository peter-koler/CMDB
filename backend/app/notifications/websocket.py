"""WebSocket事件处理器"""

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
from app import db
from app.models import User
from app.notifications.models import NotificationRecipient
import functools

# SocketIO实例将在应用初始化时设置
socketio = None


def init_socketio(app):
    """初始化SocketIO"""
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get("SOCKETIO_CORS_ALLOWED_ORIGINS", "*"),
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
        logger=app.debug,
        engineio_logger=app.debug,
    )
    register_handlers()
    return socketio


def authenticated_only(f):
    """装饰器：仅允许已认证用户访问"""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not hasattr(request, "user_id") or not request.user_id:
            emit("auth_error", {"message": "Authentication required"})
            disconnect()
            return
        return f(*args, **kwargs)

    return wrapped


def register_handlers():
    """注册所有WebSocket事件处理器"""

    @socketio.on("connect", namespace="/notifications")
    def handle_connect():
        """处理客户端连接"""
        try:
            # 从请求中获取JWT token
            token = request.args.get("token") or request.headers.get(
                "Authorization", ""
            ).replace("Bearer ", "")

            if not token:
                emit("auth_error", {"message": "Token missing"})
                disconnect()
                return

            # 解码token获取用户ID
            decoded = decode_token(token)
            user_id = decoded.get("sub")

            if not user_id:
                emit("auth_error", {"message": "Invalid token"})
                disconnect()
                return

            # 验证用户存在且活跃
            user = User.query.filter_by(id=int(user_id), status="active").first()
            if not user:
                emit("auth_error", {"message": "User not found or inactive"})
                disconnect()
                return

            # 保存用户ID到请求上下文
            request.user_id = user.id

            # 加入用户专属房间
            user_room = f"user:{user.id}"
            join_room(user_room)

            # 加入部门房间（如果用户有所属部门）
            if user.department_id:
                dept_room = f"dept:{user.department_id}"
                join_room(dept_room)

            emit(
                "authenticated",
                {"user_id": user.id, "connected_at": db.func.now().isoformat()},
            )

        except Exception as e:
            emit("auth_error", {"message": str(e)})
            disconnect()

    @socketio.on("disconnect", namespace="/notifications")
    def handle_disconnect():
        """处理客户端断开连接"""
        if hasattr(request, "user_id") and request.user_id:
            # 离开所有房间
            leave_room(f"user:{request.user_id}")

    @socketio.on("notification:acknowledge", namespace="/notifications")
    @authenticated_only
    def handle_acknowledge(data):
        """处理客户端确认收到通知"""
        try:
            recipient_id = data.get("recipient_id")
            if not recipient_id:
                return

            # 更新投递状态
            recipient = NotificationRecipient.query.filter_by(
                id=recipient_id, user_id=request.user_id
            ).first()

            if recipient and recipient.delivery_status == "pending":
                recipient.delivery_status = "delivered"
                db.session.commit()

        except Exception as e:
            emit("error", {"message": f"Failed to acknowledge: {str(e)}"})


def emit_to_user(user_id: int, event: str, data: dict):
    """向特定用户发送事件

    Args:
        user_id: 用户ID
        event: 事件名称
        data: 事件数据
    """
    if socketio:
        socketio.emit(event, data, room=f"user:{user_id}", namespace="/notifications")


def emit_to_department(department_id: int, event: str, data: dict):
    """向部门所有成员发送事件

    Args:
        department_id: 部门ID
        event: 事件名称
        data: 事件数据
    """
    if socketio:
        socketio.emit(
            event, data, room=f"dept:{department_id}", namespace="/notifications"
        )


def emit_to_users(user_ids: list, event: str, data: dict):
    """向多个用户发送事件

    Args:
        user_ids: 用户ID列表
        event: 事件名称
        data: 事件数据
    """
    if socketio:
        for user_id in user_ids:
            socketio.emit(
                event, data, room=f"user:{user_id}", namespace="/notifications"
            )


def broadcast_notification(notification_data: dict, recipient_ids: list = None):
    """广播通知给指定接收者

    Args:
        notification_data: 通知数据
        recipient_ids: 接收者用户ID列表（可选）
    """
    event_data = {
        "id": notification_data.get("id"),
        "title": notification_data.get("title"),
        "content": notification_data.get("content"),
        "content_html": notification_data.get("content_html"),
        "type": notification_data.get("type"),
        "sender": notification_data.get("sender"),
        "created_at": notification_data.get("created_at"),
        "recipient_id": notification_data.get("recipient_id"),
    }

    if recipient_ids:
        # 发送给特定用户
        emit_to_users(recipient_ids, "notification:new", event_data)
    else:
        # 广播给所有连接的用户
        if socketio:
            socketio.emit(
                "notification:new",
                event_data,
                namespace="/notifications",
                broadcast=True,
            )


def emit_read_status(recipient_id: int, notification_id: int, user_id: int):
    """发送通知已读状态同步事件

    Args:
        recipient_id: 接收者记录ID
        notification_id: 通知ID
        user_id: 用户ID
    """
    if socketio:
        socketio.emit(
            "notification:read",
            {
                "recipient_id": recipient_id,
                "notification_id": notification_id,
                "read_at": db.func.now().isoformat(),
            },
            room=f"user:{user_id}",
            namespace="/notifications",
        )


def emit_unread_status(recipient_id: int, notification_id: int, user_id: int):
    """发送通知未读状态同步事件

    Args:
        recipient_id: 接收者记录ID
        notification_id: 通知ID
        user_id: 用户ID
    """
    if socketio:
        socketio.emit(
            "notification:unread",
            {"recipient_id": recipient_id, "notification_id": notification_id},
            room=f"user:{user_id}",
            namespace="/notifications",
        )


def emit_read_all(user_id: int, marked_count: int):
    """发送全部已读事件

    Args:
        user_id: 用户ID
        marked_count: 标记为已读的数量
    """
    if socketio:
        socketio.emit(
            "notifications:read_all",
            {"marked_count": marked_count, "read_at": db.func.now().isoformat()},
            room=f"user:{user_id}",
            namespace="/notifications",
        )
