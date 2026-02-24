"""自定义视图模型单元测试"""

import pytest
from datetime import datetime


class TestCustomView:
    """测试自定义视图模型"""

    def test_create_view(self, db_session):
        """测试创建视图"""
        from app.models.custom_view import CustomView

        view = CustomView(
            name="测试视图",
            code="test_view",
            description="测试描述",
            sort_order=1,
            is_active=True
        )
        db_session.add(view)
        db_session.commit()

        assert view.id is not None
        assert view.name == "测试视图"
        assert view.code == "test_view"
        assert view.description == "测试描述"
        assert view.sort_order == 1
        assert view.is_active is True
        assert view.created_at is not None

    def test_view_to_dict(self, db_session):
        """测试视图转字典"""
        from app.models.custom_view import CustomView

        view = CustomView(
            name="测试视图",
            code="test_view",
            description="测试描述"
        )
        db_session.add(view)
        db_session.commit()

        data = view.to_dict()
        assert data["id"] == view.id
        assert data["name"] == "测试视图"
        assert data["code"] == "test_view"
        assert data["description"] == "测试描述"
        assert "created_at" in data

    def test_view_soft_delete(self, db_session):
        """测试视图软删除"""
        from app.models.custom_view import CustomView

        view = CustomView(
            name="测试视图",
            code="test_view",
            is_active=True
        )
        db_session.add(view)
        db_session.commit()

        view.is_active = False
        db_session.commit()

        assert view.is_active is False


class TestCustomViewNode:
    """测试自定义视图节点模型"""

    def test_create_root_node(self, db_session):
        """测试创建根节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(
            view_id=view.id,
            name="根节点",
            sort_order=1,
            is_active=True
        )
        db_session.add(node)
        db_session.commit()

        assert node.id is not None
        assert node.view_id == view.id
        assert node.parent_id is None
        assert node.name == "根节点"
        assert node.is_root() is True
        assert node.get_level() == 0

    def test_create_child_node(self, db_session):
        """测试创建子节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        parent = CustomViewNode(
            view_id=view.id,
            name="父节点",
            sort_order=1
        )
        db_session.add(parent)
        db_session.commit()

        child = CustomViewNode(
            view_id=view.id,
            parent_id=parent.id,
            name="子节点",
            sort_order=1
        )
        db_session.add(child)
        db_session.commit()

        assert child.parent_id == parent.id
        assert child.is_root() is False
        assert child.get_level() == 1
        assert parent in child.get_ancestors()

    def test_node_filter_config(self, db_session):
        """测试节点筛选配置"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(
            view_id=view.id,
            name="测试节点",
            sort_order=1
        )
        db_session.add(node)
        db_session.commit()

        filter_config = {
            "model_id": 1,
            "conditions": [
                {"field": "name", "operator": "eq", "value": "test"}
            ]
        }
        node.set_filter_config(filter_config)
        db_session.commit()

        assert node.get_filter_config() == filter_config

    def test_node_to_dict(self, db_session):
        """测试节点转字典"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(
            view_id=view.id,
            name="测试节点",
            sort_order=1,
            is_active=True
        )
        db_session.add(node)
        db_session.commit()

        data = node.to_dict()
        assert data["id"] == node.id
        assert data["name"] == "测试节点"
        assert data["is_root"] is True
        assert data["level"] == 0
        assert "children" in data

    def test_get_all_children(self, db_session):
        """测试获取所有子节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        # 创建三级节点
        level1 = CustomViewNode(view_id=view.id, name="一级节点", sort_order=1)
        db_session.add(level1)
        db_session.commit()

        level2 = CustomViewNode(view_id=view.id, parent_id=level1.id, name="二级节点", sort_order=1)
        db_session.add(level2)
        db_session.commit()

        level3 = CustomViewNode(view_id=view.id, parent_id=level2.id, name="三级节点", sort_order=1)
        db_session.add(level3)
        db_session.commit()

        children = level1.get_all_children()
        assert len(children) == 2
        assert level2 in children
        assert level3 in children


class TestCustomViewNodePermission:
    """测试节点权限模型"""

    def test_create_permission(self, db_session):
        """测试创建权限"""
        from app.models.custom_view import CustomView, CustomViewNode, CustomViewNodePermission

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        permission = CustomViewNodePermission(
            node_id=node.id,
            role_id=1
        )
        db_session.add(permission)
        db_session.commit()

        assert permission.id is not None
        assert permission.node_id == node.id
        assert permission.role_id == 1

    def test_permission_to_dict(self, db_session):
        """测试权限转字典"""
        from app.models.custom_view import CustomView, CustomViewNode, CustomViewNodePermission

        view = CustomView(name="测试视图", code="test_view")
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        permission = CustomViewNodePermission(
            node_id=node.id,
            role_id=1
        )
        db_session.add(permission)
        db_session.commit()

        data = permission.to_dict()
        assert data["id"] == permission.id
        assert data["node_id"] == node.id
        assert data["role_id"] == 1
        assert "created_at" in data
