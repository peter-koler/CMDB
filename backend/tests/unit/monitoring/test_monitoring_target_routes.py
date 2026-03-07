import json

from flask_jwt_extended import create_access_token

from app import db
from app.models.role import Role, UserRole
from app.models.user import User
from app.services.manager_api_service import ManagerError


API_PREFIX = "/api/v1/monitoring"


def _auth_headers(app, user_id: int, username: str = "tester", role: str = "user"):
    with app.app_context():
        token = create_access_token(
            identity=str(user_id),
            additional_claims={"username": username, "role": role},
        )
    return {"Authorization": f"Bearer {token}"}


def test_current_alerts_fallback_when_manager_endpoint_missing(app, client, test_admin, monkeypatch):
    def fake_request(**kwargs):
        raise ManagerError(status=404, code="NOT_FOUND", message="not found")

    monkeypatch.setattr("app.routes.monitoring_target.manager_api_service.request", fake_request)
    headers = _auth_headers(app, test_admin.id, username=test_admin.username, role="admin")

    resp = client.get(f"{API_PREFIX}/alerts/current", headers=headers)

    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["code"] == 200
    assert payload["data"]["items"] == []


def test_alert_center_permission_denied_for_user_without_permissions(app, client, db_session):
    user = User(username="limited", email="limited@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/alerts/current", headers=headers)

    assert resp.status_code == 403
    payload = json.loads(resp.data)
    assert payload["code"] == 403


def test_alert_center_permission_granted_for_user_with_role(app, client, db_session, monkeypatch):
    user = User(username="ops", email="ops@example.com")
    user.set_password("Password123!")
    role = Role(name="ops", code="ops", status="active")
    role.set_menu_permissions(["monitoring:alert:center"])
    db.session.add_all([user, role])
    db.session.commit()

    link = UserRole(user_id=user.id, role_id=role.id)
    db.session.add(link)
    db.session.commit()

    monkeypatch.setattr(
        "app.routes.monitoring_target.manager_api_service.request",
        lambda **kwargs: {"items": [{"id": 1, "level": "warning"}], "total": 1},
    )

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/alerts/current", headers=headers)

    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["code"] == 200
    assert payload["data"]["total"] == 1
