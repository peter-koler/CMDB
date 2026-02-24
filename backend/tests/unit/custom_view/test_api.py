"""自定义视图 API 单元测试"""

import json
import pytest

API_PREFIX = "/api/v1"


class TestCustomViewAPI:
    """测试视图管理 API"""

    def _get_auth_headers(self, client, username="adminuser", password="Password123!"):
        """获取认证头"""
        login_res = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code}, {login_res.data.decode()}")
            return None
        token = json.loads(login_res.data)["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_list_views(self, client, db_session, test_admin):
        """测试获取视图列表"""
        from app.models.custom_view import CustomView

        # 创建测试视图
        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        # 获取认证头
        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.get(f"{API_PREFIX}/custom-views", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert "data" in data
        assert "items" in data["data"]

    def test_create_view(self, client, test_admin):
        """测试创建视图"""
        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.post(f"{API_PREFIX}/custom-views", 
            json={
                "name": "新视图",
                "code": "new_view",
                "description": "测试描述",
                "sort_order": 1
            },
            headers=headers
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["code"] == 201
        assert data["data"]["name"] == "新视图"

    def test_create_view_duplicate_code(self, client, db_session, test_admin):
        """测试创建视图重复编码"""
        from app.models.custom_view import CustomView

        # 创建已有视图
        view = CustomView(name="已有视图", code="existing_code", is_active=True)
        db_session.add(view)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.post(f"{API_PREFIX}/custom-views", 
            json={
                "name": "新视图",
                "code": "existing_code",
                "description": "测试描述"
            },
            headers=headers
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["code"] == 400

    def test_get_view(self, client, db_session, test_admin):
        """测试获取单个视图"""
        from app.models.custom_view import CustomView

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.get(f"{API_PREFIX}/custom-views/{view.id}", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert data["data"]["name"] == "测试视图"

    def test_update_view(self, client, db_session, test_admin):
        """测试更新视图"""
        from app.models.custom_view import CustomView

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.put(f"{API_PREFIX}/custom-views/{view.id}", 
            json={
                "name": "更新后的视图",
                "description": "更新后的描述"
            },
            headers=headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert data["data"]["name"] == "更新后的视图"

    def test_delete_view(self, client, db_session, test_admin):
        """测试删除视图"""
        from app.models.custom_view import CustomView

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()
        view_id = view.id

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.delete(f"{API_PREFIX}/custom-views/{view_id}", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200

        # 验证已物理删除
        deleted_view = db_session.query(CustomView).get(view_id)
        assert deleted_view is None


class TestCustomViewNodeAPI:
    """测试节点管理 API"""

    def _get_auth_headers(self, client, username="adminuser", password="Password123!"):
        """获取认证头"""
        login_res = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code}, {login_res.data.decode()}")
            return None
        token = json.loads(login_res.data)["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_root_node(self, client, db_session, test_admin):
        """测试创建根节点"""
        from app.models.custom_view import CustomView

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.post(f"{API_PREFIX}/custom-view-nodes", 
            json={
                "view_id": view.id,
                "name": "根节点",
                "sort_order": 1
            },
            headers=headers
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["code"] == 201
        assert data["data"]["name"] == "根节点"
        assert data["data"]["parent_id"] is None

    def test_create_child_node(self, client, db_session, test_admin):
        """测试创建子节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        parent = CustomViewNode(view_id=view.id, name="父节点", sort_order=1)
        db_session.add(parent)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.post(f"{API_PREFIX}/custom-view-nodes", 
            json={
                "view_id": view.id,
                "parent_id": parent.id,
                "name": "子节点",
                "sort_order": 1
            },
            headers=headers
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["code"] == 201
        assert data["data"]["parent_id"] == parent.id

    def test_get_view_nodes(self, client, db_session, test_admin):
        """测试获取视图节点树"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.get(f"{API_PREFIX}/custom-views/{view.id}/nodes", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "测试节点"

    def test_update_node(self, client, db_session, test_admin):
        """测试更新节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.put(f"{API_PREFIX}/custom-view-nodes/{node.id}", 
            json={
                "name": "更新后的节点",
                "sort_order": 2
            },
            headers=headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert data["data"]["name"] == "更新后的节点"

    def test_delete_node(self, client, db_session, test_admin):
        """测试删除节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.delete(f"{API_PREFIX}/custom-view-nodes/{node.id}", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200

    def test_move_node(self, client, db_session, test_admin):
        """测试移动节点"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        node1 = CustomViewNode(view_id=view.id, name="节点1", sort_order=1)
        node2 = CustomViewNode(view_id=view.id, name="节点2", sort_order=2)
        db_session.add(node1)
        db_session.add(node2)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        response = client.put(f"{API_PREFIX}/custom-view-nodes/{node2.id}/move", 
            json={
                "target_parent_id": node1.id,
                "target_position": 0
            },
            headers=headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200


class TestCustomViewNodeFilterAPI:
    """测试节点筛选 API"""

    def _get_auth_headers(self, client, username="adminuser", password="Password123!"):
        """获取认证头"""
        login_res = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code}, {login_res.data.decode()}")
            return None
        token = json.loads(login_res.data)["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_update_node_filter_config(self, client, db_session, test_admin):
        """测试更新节点筛选配置"""
        from app.models.custom_view import CustomView, CustomViewNode

        view = CustomView(name="测试视图", code="test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        parent = CustomViewNode(view_id=view.id, name="父节点", sort_order=1)
        db_session.add(parent)
        db_session.commit()

        child = CustomViewNode(view_id=view.id, parent_id=parent.id, name="子节点", sort_order=1)
        db_session.add(child)
        db_session.commit()

        headers = self._get_auth_headers(client)
        assert headers is not None

        filter_config = {
            "model_id": 1,
            "conditions": [
                {"field": "name", "operator": "eq", "value": "test"}
            ]
        }

        response = client.put(f"{API_PREFIX}/custom-view-nodes/{child.id}", 
            json={
                "name": "子节点",
                "filter_config": filter_config
            },
            headers=headers
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["code"] == 200
        assert data["data"]["filter_config"] == filter_config


class TestCustomViewPermissionAPI:
    """测试权限控制 API"""

    def _get_auth_headers(self, client, username, password="Password123!"):
        """获取认证头"""
        login_res = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code}, {login_res.data.decode()}")
            return None
        token = json.loads(login_res.data)["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_no_permission_access_denied(self, client, test_user):
        """测试无权限访问被拒绝"""
        headers = self._get_auth_headers(client, "testuser", "Password123!")
        assert headers is not None

        response = client.get(f"{API_PREFIX}/custom-views", headers=headers)
        assert response.status_code == 403

    def test_admin_can_access(self, client, test_admin):
        """测试管理员可以访问"""
        headers = self._get_auth_headers(client, "adminuser", "Password123!")
        assert headers is not None

        response = client.get(f"{API_PREFIX}/custom-views", headers=headers)
        assert response.status_code == 200
