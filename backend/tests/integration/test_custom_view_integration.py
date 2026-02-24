"""自定义视图集成测试"""

import json
import pytest


class TestCustomViewIntegration:
    """自定义视图端到端集成测试"""

    def test_complete_view_workflow(self, client, db_session, test_admin):
        """测试完整的视图工作流程"""
        from app.models.custom_view import CustomView, CustomViewNode

        # 1. 登录获取 token
        login_res = client.post("/api/v1/auth/login", json={
            "username": "adminuser",
            "password": "Password123!"
        })
        assert login_res.status_code == 200
        token = json.loads(login_res.data)["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 创建视图
        create_res = client.post("/api/v1/custom-views", 
            json={
                "name": "集成测试视图",
                "code": "integration_test_view",
                "description": "用于集成测试",
                "sort_order": 1
            },
            headers=headers
        )
        assert create_res.status_code == 201
        view_data = json.loads(create_res.data)["data"]
        view_id = view_data["id"]
        assert view_data["name"] == "集成测试视图"

        # 3. 获取视图列表
        list_res = client.get("/api/v1/custom-views", headers=headers)
        assert list_res.status_code == 200
        list_data = json.loads(list_res.data)["data"]
        assert any(v["id"] == view_id for v in list_data["items"])

        # 4. 获取单个视图
        get_res = client.get(f"/api/v1/custom-views/{view_id}", headers=headers)
        assert get_res.status_code == 200
        get_data = json.loads(get_res.data)["data"]
        assert get_data["name"] == "集成测试视图"

        # 5. 创建根节点
        root_res = client.post("/api/v1/custom-view-nodes",
            json={
                "view_id": view_id,
                "name": "根节点",
                "sort_order": 1
            },
            headers=headers
        )
        assert root_res.status_code == 201
        root_data = json.loads(root_res.data)["data"]
        root_id = root_data["id"]
        assert root_data["parent_id"] is None

        # 6. 创建子节点
        child_res = client.post("/api/v1/custom-view-nodes",
            json={
                "view_id": view_id,
                "parent_id": root_id,
                "name": "子节点",
                "sort_order": 1
            },
            headers=headers
        )
        assert child_res.status_code == 201
        child_data = json.loads(child_res.data)["data"]
        child_id = child_data["id"]
        assert child_data["parent_id"] == root_id

        # 7. 获取视图节点树
        tree_res = client.get(f"/api/v1/custom-views/{view_id}/nodes", headers=headers)
        assert tree_res.status_code == 200
        tree_data = json.loads(tree_res.data)["data"]
        assert len(tree_data) == 1
        assert tree_data[0]["name"] == "根节点"
        assert len(tree_data[0]["children"]) == 1
        assert tree_data[0]["children"][0]["name"] == "子节点"

        # 8. 更新子节点筛选配置
        filter_config = {
            "model_id": 1,
            "conditions": [
                {"field": "name", "operator": "eq", "value": "test"}
            ]
        }
        update_res = client.put(f"/api/v1/custom-view-nodes/{child_id}",
            json={
                "name": "子节点",
                "filter_config": filter_config
            },
            headers=headers
        )
        assert update_res.status_code == 200
        update_data = json.loads(update_res.data)["data"]
        assert update_data["filter_config"] == filter_config

        # 9. 移动节点
        move_res = client.put(f"/api/v1/custom-view-nodes/{child_id}/move",
            json={
                "target_parent_id": None,
                "target_position": 1
            },
            headers=headers
        )
        assert move_res.status_code == 200

        # 10. 删除子节点
        delete_child_res = client.delete(f"/api/v1/custom-view-nodes/{child_id}", headers=headers)
        assert delete_child_res.status_code == 200

        # 11. 删除视图（物理删除）
        delete_view_res = client.delete(f"/api/v1/custom-views/{view_id}", headers=headers)
        assert delete_view_res.status_code == 200

        # 验证视图已物理删除
        view = db_session.query(CustomView).get(view_id)
        assert view is None

    def test_view_node_tree_structure(self, client, db_session, test_admin):
        """测试视图节点树形结构"""
        from app.models.custom_view import CustomView, CustomViewNode

        # 登录
        login_res = client.post("/api/v1/auth/login", json={
            "username": "adminuser",
            "password": "Password123!"
        })
        token = json.loads(login_res.data)["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 创建视图
        view = CustomView(name="树形测试视图", code="tree_test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        # 创建三级节点结构
        level1 = CustomViewNode(view_id=view.id, name="一级节点", sort_order=1)
        db_session.add(level1)
        db_session.commit()

        level2 = CustomViewNode(view_id=view.id, parent_id=level1.id, name="二级节点", sort_order=1)
        db_session.add(level2)
        db_session.commit()

        level3 = CustomViewNode(view_id=view.id, parent_id=level2.id, name="三级节点", sort_order=1)
        db_session.add(level3)
        db_session.commit()

        # 获取树形结构
        tree_res = client.get(f"/api/v1/custom-views/{view.id}/nodes", headers=headers)
        assert tree_res.status_code == 200
        tree_data = json.loads(tree_res.data)["data"]

        # 验证树形结构
        assert len(tree_data) == 1
        assert tree_data[0]["name"] == "一级节点"
        assert tree_data[0]["level"] == 0
        assert len(tree_data[0]["children"]) == 1
        assert tree_data[0]["children"][0]["name"] == "二级节点"
        assert tree_data[0]["children"][0]["level"] == 1
        assert len(tree_data[0]["children"][0]["children"]) == 1
        assert tree_data[0]["children"][0]["children"][0]["name"] == "三级节点"
        assert tree_data[0]["children"][0]["children"][0]["level"] == 2

    def test_permission_control(self, client, db_session, test_user, test_admin):
        """测试权限控制"""
        from app.models.custom_view import CustomView

        # 创建视图
        view = CustomView(name="权限测试视图", code="permission_test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        # 普通用户无权限访问
        user_login = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "Password123!"
        })
        user_token = json.loads(user_login.data)["data"]["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        user_res = client.get("/api/v1/custom-views", headers=user_headers)
        assert user_res.status_code == 403

        # 管理员可以访问
        admin_login = client.post("/api/v1/auth/login", json={
            "username": "adminuser",
            "password": "Password123!"
        })
        admin_token = json.loads(admin_login.data)["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        admin_res = client.get("/api/v1/custom-views", headers=admin_headers)
        assert admin_res.status_code == 200

    def test_node_filter_operations(self, client, db_session, test_admin):
        """测试节点筛选操作符"""
        from app.models.custom_view import CustomView, CustomViewNode

        # 登录
        login_res = client.post("/api/v1/auth/login", json={
            "username": "adminuser",
            "password": "Password123!"
        })
        token = json.loads(login_res.data)["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 创建视图和节点
        view = CustomView(name="筛选测试视图", code="filter_test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        parent = CustomViewNode(view_id=view.id, name="父节点", sort_order=1)
        db_session.add(parent)
        db_session.commit()

        child = CustomViewNode(view_id=view.id, parent_id=parent.id, name="子节点", sort_order=1)
        db_session.add(child)
        db_session.commit()

        # 测试各种操作符
        operators = ["eq", "ne", "contains", "gt", "gte", "lt", "lte", "startswith", "endswith"]
        for op in operators:
            filter_config = {
                "model_id": 1,
                "conditions": [
                    {"field": "name", "operator": op, "value": "test"}
                ]
            }
            res = client.put(f"/api/v1/custom-view-nodes/{child.id}",
                json={"name": "子节点", "filter_config": filter_config},
                headers=headers
            )
            assert res.status_code == 200, f"操作符 {op} 失败"

    @pytest.mark.skip(reason="导入导出功能尚未实现")
    def test_view_import_export(self, client, db_session, test_admin):
        """测试视图导入导出"""
        from app.models.custom_view import CustomView, CustomViewNode

        # 登录
        login_res = client.post("/api/v1/auth/login", json={
            "username": "adminuser",
            "password": "Password123!"
        })
        token = json.loads(login_res.data)["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 创建测试数据
        view = CustomView(name="导出测试视图", code="export_test_view", is_active=True)
        db_session.add(view)
        db_session.commit()

        node = CustomViewNode(view_id=view.id, name="测试节点", sort_order=1)
        db_session.add(node)
        db_session.commit()

        # 测试导出
        export_res = client.post("/api/v1/custom-views/export",
            json={"ids": [view.id]},
            headers=headers
        )
        assert export_res.status_code == 200
        export_data = json.loads(export_res.data)["data"]
        assert "views" in export_data
        assert len(export_data["views"]) == 1

        # 测试导入
        import_data = {
            "views": [{
                "name": "导入测试视图",
                "code": "import_test_view",
                "description": "导入测试",
                "sort_order": 1,
                "nodes": [{
                    "name": "导入节点",
                    "sort_order": 1,
                    "is_active": True
                }]
            }]
        }
        import_res = client.post("/api/v1/custom-views/import",
            json=import_data,
            headers=headers
        )
        assert import_res.status_code == 200
        import_result = json.loads(import_res.data)["data"]
        assert import_result["success"] == 1
