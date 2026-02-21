"""通知模块权限控制"""

from typing import Optional

from app.models import User, Department


class NotificationPermissionError(Exception):
    """通知权限错误"""
    pass


def can_send_to_user(sender: User, target_user: User) -> bool:
    """
    检查发送者是否可以向目标用户发送通知

    规则:
    1. 管理员可以发送给任何用户
    2. 部门经理可以发送给自己部门的用户
    3. 普通用户只能发送给自己（如果需要）

    Args:
        sender: 发送者用户
        target_user: 目标用户

    Returns:
        bool: 是否有权限
    """
    # 管理员可以发送给任何人
    if sender.role == 'admin':
        return True

    # 部门经理可以发送给自己部门的用户
    if sender.role == 'manager':
        # 检查目标用户是否在同一部门
        if sender.department_id and target_user.department_id:
            return sender.department_id == target_user.department_id
        return False

    # 普通用户默认不能发送通知
    return False


def can_send_to_department(sender: User, department: Department) -> bool:
    """
    检查发送者是否可以向部门发送通知

    规则:
    1. 管理员可以发送给任何部门
    2. 部门经理只能发送给自己管理的部门

    Args:
        sender: 发送者用户
        department: 目标部门

    Returns:
        bool: 是否有权限
    """
    # 管理员可以发送给任何部门
    if sender.role == 'admin':
        return True

    # 部门经理只能发送给自己管理的部门
    if sender.role == 'manager':
        return sender.department_id == department.id

    return False


def can_send_broadcast(sender: User) -> bool:
    """
    检查发送者是否可以发送全员广播

    规则:
    1. 只有管理员可以发送全员广播
    2. 部门经理不能发送广播

    Args:
        sender: 发送者用户

    Returns:
        bool: 是否有权限
    """
    return sender.role == 'admin'


def validate_sender_permission(sender_id: int, recipient_type: str,
                               user_ids: Optional[list] = None,
                               department_id: Optional[int] = None) -> None:
    """
    验证发送者权限

    Args:
        sender_id: 发送者用户ID
        recipient_type: 接收者类型 ('users', 'department', 'broadcast')
        user_ids: 用户ID列表（当recipient_type为'users'时）
        department_id: 部门ID（当recipient_type为'department'时）

    Raises:
        NotificationPermissionError: 当权限验证失败时
    """
    sender = User.query.get(sender_id)
    if not sender:
        raise NotificationPermissionError("发送者不存在")

    if recipient_type == 'broadcast':
        if not can_send_broadcast(sender):
            raise NotificationPermissionError("只有管理员可以发送全员广播")

    elif recipient_type == 'department':
        if not department_id:
            raise NotificationPermissionError("部门ID不能为空")

        department = Department.query.get(department_id)
        if not department:
            raise NotificationPermissionError("部门不存在")

        if not can_send_to_department(sender, department):
            raise NotificationPermissionError("您没有权限向该部门发送通知")

    elif recipient_type == 'users':
        if not user_ids:
            raise NotificationPermissionError("用户ID列表不能为空")

        # 检查是否可以发送给每个用户
        for user_id in user_ids:
            target_user = User.query.get(user_id)
            if not target_user:
                raise NotificationPermissionError(f"用户 {user_id} 不存在")

            if not can_send_to_user(sender, target_user):
                raise NotificationPermissionError(
                    f"您没有权限向用户 {target_user.username} 发送通知"
                )

    else:
        raise NotificationPermissionError(f"不支持的接收者类型: {recipient_type}")


def get_accessible_departments(user: User) -> list:
    """
    获取用户可以访问的部门列表

    Args:
        user: 用户

    Returns:
        list: 部门ID列表
    """
    if user.role == 'admin':
        # 管理员可以访问所有部门
        return [d.id for d in Department.query.all()]

    if user.role == 'manager' and user.department_id:
        # 部门经理只能访问自己部门
        return [user.department_id]

    return []


def can_view_notification(user: User, notification) -> bool:
    """
    检查用户是否可以查看通知

    Args:
        user: 用户
        notification: 通知对象

    Returns:
        bool: 是否有权限
    """
    # 如果是接收者，可以查看
    if any(r.user_id == user.id for r in notification.recipients):
        return True

    # 如果是发送者，可以查看
    if notification.sender_id == user.id:
        return True

    # 管理员可以查看所有通知
    if user.role == 'admin':
        return True

    return False


def can_delete_notification(user: User, notification) -> bool:
    """
    检查用户是否可以删除通知

    Args:
        user: 用户
        notification: 通知对象

    Returns:
        bool: 是否有权限
    """
    # 只有发送者或管理员可以删除
    if notification.sender_id == user.id:
        return True

    if user.role == 'admin':
        return True

    return False
