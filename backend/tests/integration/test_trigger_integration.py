"""
CMDB CI 关系触发器集成测试

测试触发器自动创建关系和批量扫描功能
"""

import pytest
from app import create_app, db
from app.models.cmdb_model import CmdbModel
from app.models.model_category import ModelCategory
from app.models.cmdb_relation import RelationType, RelationTrigger
from app.models.ci_instance import CiInstance
from app.models.user import User


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """创建认证头"""
    with client.application.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "Password123!"}
    )
    token = response.json["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestTriggerIntegration:
    """触发器集成测试"""

    def test_auto_relation_creation(self, client, auth_headers):
        """测试触发器自动创建关系"""
        with client.application.app_context():
            category = ModelCategory(name="测试分类", code="test-category")
            db.session.add(category)
            db.session.commit()

            server_model = CmdbModel(
                name="服务器",
                code="server",
                category_id=category.id
            )
            db.session.add(server_model)

            app_model = CmdbModel(
                name="应用",
                code="application",
                category_id=category.id
            )
            db.session.add(app_model)
            db.session.commit()

            relation_type = RelationType(
                code="runs_on",
                name="运行在",
                source_label="运行",
                target_label="承载"
            )
            db.session.add(relation_type)
            db.session.commit()

            trigger = RelationTrigger(
                name="应用-服务器关联",
                source_model_id=app_model.id,
                target_model_id=server_model.id,
                relation_type_id=relation_type.id,
                trigger_type="reference",
                trigger_condition='{"source_field": "deploy_ip", "target_field": "ip"}',
                is_active=True
            )
            db.session.add(trigger)
            db.session.commit()

            user = User.query.first()
            server_ci = CiInstance(
                name="web-server-01",
                code="server-01",
                model_id=server_model.id,
                created_by=user.id
            )
            server_ci.set_attribute_values({"ip": "192.168.1.100", "hostname": "web-server-01"})
            db.session.add(server_ci)
            db.session.commit()

            app_ci = CiInstance(
                name="web-app",
                code="app-01",
                model_id=app_model.id,
                created_by=user.id
            )
            app_ci.set_attribute_values({"deploy_ip": "192.168.1.100", "app_name": "Web应用"})
            db.session.add(app_ci)
            db.session.commit()

            from app.services.trigger_service import process_ci_triggers
            process_ci_triggers(app_ci)

            from app.models.cmdb_relation import CmdbRelation
            relations = CmdbRelation.query.filter_by(
                source_ci_id=app_ci.id,
                relation_type_id=relation_type.id
            ).all()

            assert len(relations) > 0, "应该自动创建关系"


class TestBatchScanIntegration:
    """批量扫描集成测试"""

    def test_batch_scan_creates_relations(self, client, auth_headers):
        """测试批量扫描创建缺失关系"""
        with client.application.app_context():
            category = ModelCategory(name="测试分类", code="test-category")
            db.session.add(category)
            db.session.commit()

            server_model = CmdbModel(
                name="服务器",
                code="server",
                category_id=category.id
            )
            db.session.add(server_model)

            app_model = CmdbModel(
                name="应用",
                code="application",
                category_id=category.id
            )
            db.session.add(app_model)
            db.session.commit()

            relation_type = RelationType(
                code="runs_on",
                name="运行在",
                source_label="运行",
                target_label="承载"
            )
            db.session.add(relation_type)
            db.session.commit()

            trigger = RelationTrigger(
                name="应用-服务器关联",
                source_model_id=app_model.id,
                target_model_id=server_model.id,
                relation_type_id=relation_type.id,
                trigger_type="reference",
                trigger_condition='{"source_field": "deploy_ip", "target_field": "ip"}',
                is_active=True
            )
            db.session.add(trigger)
            db.session.commit()

            user = User.query.first()
            for i in range(3):
                server_ci = CiInstance(
                    name=f"server-{i}",
                    code=f"server-{i}",
                    model_id=server_model.id,
                    created_by=user.id
                )
                server_ci.set_attribute_values(
                    {"ip": f"192.168.1.{i+1}", "hostname": f"server-{i}"}
                )
                db.session.add(server_ci)

            for i in range(3):
                app_ci = CiInstance(
                    name=f"app-{i}",
                    code=f"app-{i}",
                    model_id=app_model.id,
                    created_by=user.id
                )
                app_ci.set_attribute_values(
                    {"deploy_ip": f"192.168.1.{i+1}", "app_name": f"app-{i}"}
                )
                db.session.add(app_ci)
            db.session.commit()

            from app.tasks.batch_scan import batch_scan_model
            batch_scan_model(app_model.id, "manual")

            from app.models.cmdb_relation import CmdbRelation
            relations = CmdbRelation.query.filter_by(
                relation_type_id=relation_type.id
            ).all()

            assert len(relations) >= 3, "应该创建至少3个关系"


class TestTriggerModelDelete:
    """触发器模型删除测试"""

    def test_model_delete_invalidates_triggers(self, client, auth_headers):
        """测试删除模型时关联触发器被失效"""
        with client.application.app_context():
            category = ModelCategory(name="测试分类", code="test-category")
            db.session.add(category)
            db.session.commit()

            server_model = CmdbModel(
                name="服务器",
                code="server",
                category_id=category.id
            )
            db.session.add(server_model)

            app_model = CmdbModel(
                name="应用",
                code="application",
                category_id=category.id
            )
            db.session.add(app_model)
            db.session.commit()

            relation_type = RelationType(
                code="runs_on",
                name="运行在",
                source_label="运行",
                target_label="承载"
            )
            db.session.add(relation_type)
            db.session.commit()

            trigger = RelationTrigger(
                name="测试触发器",
                source_model_id=app_model.id,
                target_model_id=server_model.id,
                relation_type_id=relation_type.id,
                trigger_type="reference",
                trigger_condition='{}',
                is_active=True
            )
            db.session.add(trigger)
            db.session.commit()

            trigger_id = trigger.id

            db.session.delete(server_model)
            db.session.commit()

            updated_trigger = RelationTrigger.query.get(trigger_id)
            assert updated_trigger is not None, "触发器应该还存在"
            assert updated_trigger.is_active is False, "触发器应该被标记为无效"
