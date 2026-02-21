import pytest

from app import create_app, db
from app.models.user import User
from app.models.department import Department
from app.models.model_category import ModelCategory
from app.models.cmdb_model import CmdbModel
from app.models.cmdb_relation import RelationType, RelationTrigger
from app.models.ci_instance import CiInstance
from app.notifications.models import NotificationType, Notification


@pytest.fixture
def app():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session
        db.session.remove()


@pytest.fixture
def test_user(db_session):
    user = User(username="testuser", email="test@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_admin(db_session):
    user = User(username="adminuser", email="admin@example.com", role="admin")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_manager(db_session):
    department = Department(name="ManagerDept", code="MGRD")
    db_session.add(department)
    db_session.commit()
    user = User(
        username="manageruser",
        email="manager@example.com",
        role="manager",
        department_id=department.id,
    )
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_department(db_session):
    department = Department(name="TestDept", code="TD")
    db_session.add(department)
    db_session.commit()
    return department


@pytest.fixture
def another_user(db_session):
    user = User(username="anotheruser", email="another@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_notification_type(db_session):
    notification_type = NotificationType(
        name="test_type", description="Test description", icon="bell", color="#1890ff"
    )
    db_session.add(notification_type)
    db_session.commit()
    return notification_type


@pytest.fixture
def test_notification(db_session, test_user, test_notification_type):
    notification = Notification(
        title="Test Notification",
        content="Test content",
        type_id=test_notification_type.id,
        sender_id=test_user.id,
    )
    db_session.add(notification)
    db_session.commit()
    return notification


@pytest.fixture
def test_model_category(db_session):
    category = ModelCategory(name="测试分类", code="test-category")
    db_session.add(category)
    db_session.commit()
    return category


@pytest.fixture
def test_model(db_session, test_model_category):
    model = CmdbModel(name="服务器", code="server", category_id=test_model_category.id)
    db_session.add(model)
    db_session.commit()
    return model


@pytest.fixture
def test_target_model(db_session, test_model_category):
    model = CmdbModel(
        name="应用", code="application", category_id=test_model_category.id
    )
    db_session.add(model)
    db_session.commit()
    return model


@pytest.fixture
def test_ci_instance(db_session, test_model, test_user):
    ci = CiInstance(
        name="web-server-01",
        code="server-01",
        model_id=test_model.id,
        created_by=test_user.id,
    )
    ci.set_attribute_values({"ip": "192.168.1.100", "hostname": "web-server-01"})
    db_session.add(ci)
    db_session.commit()
    return ci


@pytest.fixture
def test_relation_type(db_session):
    relation_type = RelationType(
        code="runs_on", name="运行在", source_label="运行", target_label="承载"
    )
    db_session.add(relation_type)
    db_session.commit()
    return relation_type


@pytest.fixture
def test_trigger(db_session, test_model, test_target_model, test_relation_type):
    trigger = RelationTrigger(
        name="测试触发器",
        source_model_id=test_model.id,
        target_model_id=test_target_model.id,
        relation_type_id=test_relation_type.id,
        trigger_type="reference",
        trigger_condition="{}",
        is_active=True,
    )
    db_session.add(trigger)
    db_session.commit()
    return trigger
