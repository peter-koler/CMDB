"""通知模块权限控制单元测试"""

import pytest
from app.notifications.permissions import (
    can_send_to_user,
    can_send_to_department,
    can_send_broadcast,
    validate_sender_permission,
    NotificationPermissionError,
    get_accessible_departments
)
from app.models import Department


class TestCanSendToUser:
    """测试用户发送权限"""

    def test_admin_can_send_to_any_user(self, test_admin, test_user):
        """管理员可以发送给任何用户"""
        assert can_send_to_user(test_admin, test_user) is True

    def test_manager_can_send_to_same_department(self, test_manager, test_user):
        """部门经理可以发送给同部门用户"""
        # 设置同部门
        test_user.department_id = test_manager.department_id
        assert can_send_to_user(test_manager, test_user) is True

    def test_manager_cannot_send_to_other_department(self, test_manager, test_user):
        """部门经理不能发送给其他部门用户"""
        # 设置不同部门
        test_user.department_id = test_manager.department_id + 1
        assert can_send_to_user(test_manager, test_user) is False

    def test_manager_cannot_send_to_user_without_department(self, test_manager, test_user):
        """部门经理不能发送给无部门用户"""
        test_user.department_id = None
        assert can_send_to_user(test_manager, test_user) is False

    def test_normal_user_cannot_send(self, test_user, another_user):
        """普通用户不能发送通知"""
        assert can_send_to_user(test_user, another_user) is False


class TestCanSendToDepartment:
    """测试部门发送权限"""

    def test_admin_can_send_to_any_department(self, test_admin, test_department):
        """管理员可以发送给任何部门"""
        assert can_send_to_department(test_admin, test_department) is True

    def test_manager_can_send_to_own_department(self, test_manager, test_department):
        """部门经理可以发送给自己部门"""
        test_department.id = test_manager.department_id
        assert can_send_to_department(test_manager, test_department) is True

    def test_manager_cannot_send_to_other_department(self, test_manager, test_department):
        """部门经理不能发送给其他部门"""
        test_department.id = test_manager.department_id + 1
        assert can_send_to_department(test_manager, test_department) is False

    def test_normal_user_cannot_send_to_department(self, test_user, test_department):
        """普通用户不能发送给部门"""
        assert can_send_to_department(test_user, test_department) is False


class TestCanSendBroadcast:
    """测试广播权限"""

    def test_admin_can_send_broadcast(self, test_admin):
        """管理员可以发送广播"""
        assert can_send_broadcast(test_admin) is True

    def test_manager_cannot_send_broadcast(self, test_manager):
        """部门经理不能发送广播"""
        assert can_send_broadcast(test_manager) is False

    def test_normal_user_cannot_send_broadcast(self, test_user):
        """普通用户不能发送广播"""
        assert can_send_broadcast(test_user) is False


class TestValidateSenderPermission:
    """测试权限验证"""

    def test_validate_users_permission_success(self, db_session, test_admin, test_user):
        """验证用户发送权限成功"""
        db_session.add(test_admin)
        db_session.add(test_user)
        db_session.commit()

        # 不应该抛出异常
        validate_sender_permission(
            sender_id=test_admin.id,
            recipient_type="users",
            user_ids=[test_user.id]
        )

    def test_validate_users_permission_failure(self, db_session, test_user, another_user):
        """验证用户发送权限失败"""
        db_session.add(test_user)
        db_session.add(another_user)
        db_session.commit()

        with pytest.raises(NotificationPermissionError):
            validate_sender_permission(
                sender_id=test_user.id,
                recipient_type="users",
                user_ids=[another_user.id]
            )

    def test_validate_department_permission_success(self, db_session, test_manager, test_department):
        """验证部门发送权限成功"""
        test_manager.department_id = test_department.id
        db_session.add(test_manager)
        db_session.add(test_department)
        db_session.commit()

        validate_sender_permission(
            sender_id=test_manager.id,
            recipient_type="department",
            department_id=test_department.id
        )

    def test_validate_department_permission_failure(self, db_session, test_user, test_department):
        """验证部门发送权限失败"""
        db_session.add(test_user)
        db_session.add(test_department)
        db_session.commit()

        with pytest.raises(NotificationPermissionError):
            validate_sender_permission(
                sender_id=test_user.id,
                recipient_type="department",
                department_id=test_department.id
            )

    def test_validate_broadcast_permission_success(self, db_session, test_admin):
        """验证广播权限成功"""
        db_session.add(test_admin)
        db_session.commit()

        validate_sender_permission(
            sender_id=test_admin.id,
            recipient_type="broadcast"
        )

    def test_validate_broadcast_permission_failure(self, db_session, test_manager):
        """验证广播权限失败"""
        db_session.add(test_manager)
        db_session.commit()

        with pytest.raises(NotificationPermissionError):
            validate_sender_permission(
                sender_id=test_manager.id,
                recipient_type="broadcast"
            )

    def test_validate_sender_not_exist(self, db_session):
        """验证不存在的发送者"""
        with pytest.raises(NotificationPermissionError) as exc_info:
            validate_sender_permission(
                sender_id=99999,
                recipient_type="broadcast"
            )
        assert "发送者不存在" in str(exc_info.value)

    def test_validate_invalid_recipient_type(self, db_session, test_admin):
        """验证无效的接收者类型"""
        db_session.add(test_admin)
        db_session.commit()

        with pytest.raises(NotificationPermissionError) as exc_info:
            validate_sender_permission(
                sender_id=test_admin.id,
                recipient_type="invalid_type"
            )
        assert "不支持的接收者类型" in str(exc_info.value)


class TestGetAccessibleDepartments:
    """测试获取可访问部门"""

    def test_admin_can_access_all_departments(self, db_session, test_admin):
        """管理员可以访问所有部门"""
        # 创建多个部门
        dept1 = Department(name="Dept1", code="D1")
        dept2 = Department(name="Dept2", code="D2")
        db_session.add_all([dept1, dept2])
        db_session.commit()

        accessible = get_accessible_departments(test_admin)
        assert len(accessible) == 2
        assert dept1.id in accessible
        assert dept2.id in accessible

    def test_manager_can_access_own_department(self, db_session, test_manager):
        """部门经理只能访问自己部门"""
        dept = Department(name="ManagerDept", code="MD")
        db_session.add(dept)
        db_session.commit()

        test_manager.department_id = dept.id

        accessible = get_accessible_departments(test_manager)
        assert len(accessible) == 1
        assert dept.id in accessible

    def test_manager_without_department(self, test_manager):
        """无部门的经理没有可访问部门"""
        test_manager.department_id = None
        accessible = get_accessible_departments(test_manager)
        assert len(accessible) == 0

    def test_normal_user_no_access(self, test_user):
        """普通用户没有部门访问权限"""
        accessible = get_accessible_departments(test_user)
        assert len(accessible) == 0
