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


def test_monitoring_dashboard_returns_aggregated_payload(app, client, test_admin, monkeypatch):
    def fake_request(method, path, payload=None, params=None, auth_header=None):
        if path == "/api/v1/monitors":
            return {
                "items": [
                    {"id": 1, "name": "web-api", "status": "up"},
                    {"id": 2, "name": "mysql", "status": "down"},
                ],
                "total": 2,
            }
        if path == "/api/v1/alerts":
            if params and params.get("status") == "pending":
                return {
                    "items": [
                        {"id": 101, "level": "critical", "monitor_name": "web-api"},
                        {"id": 102, "level": "warning", "monitor_name": "web-api"},
                    ],
                    "total": 2,
                }
            return {
                "items": [
                    {"id": 201, "triggered_at": "2026-03-07T01:20:00Z", "monitor_name": "web-api"},
                    {"id": 202, "triggered_at": "2026-03-07T01:40:00Z", "monitor_name": "mysql"},
                ],
                "total": 2,
            }
        raise ManagerError(status=404, code="NOT_FOUND", message="not found")

    monkeypatch.setattr("app.routes.monitoring_target.manager_api_service.request", fake_request)
    headers = _auth_headers(app, test_admin.id, username=test_admin.username, role="admin")

    resp = client.get(f"{API_PREFIX}/dashboard", headers=headers)

    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["code"] == 200
    assert payload["data"]["overview"]["total_monitors"] == 2
    assert payload["data"]["overview"]["healthy_monitors"] == 1
    assert payload["data"]["overview"]["unhealthy_monitors"] == 1
    assert payload["data"]["overview"]["open_alerts"] == 2
    assert len(payload["data"]["alert_trend"]) == 24
    assert payload["data"]["top_alert_monitors"][0]["name"] == "web-api"


def test_monitoring_dashboard_permission_denied_without_permission(app, client, db_session):
    user = User(username="dashboard_limited", email="dashboard_limited@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/dashboard", headers=headers)

    assert resp.status_code == 403
    payload = json.loads(resp.data)
    assert payload["code"] == 403


def test_collectors_permission_denied_without_permission(app, client, db_session):
    user = User(username="collector_limited", email="collector_limited@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/collectors", headers=headers)

    assert resp.status_code == 403
    payload = json.loads(resp.data)
    assert payload["code"] == 403


def test_collectors_permission_granted_with_role(app, client, db_session, monkeypatch):
    user = User(username="collector_ops", email="collector_ops@example.com")
    user.set_password("Password123!")
    role = Role(name="collector_ops", code="collector_ops", status="active")
    role.set_menu_permissions(["monitoring:collector"])
    db.session.add_all([user, role])
    db.session.commit()

    link = UserRole(user_id=user.id, role_id=role.id)
    db.session.add(link)
    db.session.commit()

    monkeypatch.setattr(
        "app.routes.monitoring_target.manager_api_service.request",
        lambda **kwargs: {"items": [{"id": "c1", "status": "online"}], "total": 1},
    )

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/collectors", headers=headers)

    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["code"] == 200
    assert payload["data"]["total"] == 1


def test_alert_integration_permission_denied_without_permission(app, client, db_session):
    user = User(username="integration_limited", email="integration_limited@example.com")
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/alert-integrations", headers=headers)

    assert resp.status_code == 403
    payload = json.loads(resp.data)
    assert payload["code"] == 403


def test_alert_integration_permission_granted_with_role(app, client, db_session, monkeypatch):
    user = User(username="integration_ops", email="integration_ops@example.com")
    user.set_password("Password123!")
    role = Role(name="integration_ops", code="integration_ops", status="active")
    role.set_menu_permissions(["monitoring:alert:integration"])
    db.session.add_all([user, role])
    db.session.commit()

    link = UserRole(user_id=user.id, role_id=role.id)
    db.session.add(link)
    db.session.commit()

    monkeypatch.setattr(
        "app.routes.monitoring_target.manager_api_service.request",
        lambda **kwargs: {"items": [{"id": "i1", "name": "prometheus"}], "total": 1},
    )

    headers = _auth_headers(app, user.id, username=user.username)
    resp = client.get(f"{API_PREFIX}/alert-integrations", headers=headers)

    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["code"] == 200
    assert payload["data"]["total"] == 1
