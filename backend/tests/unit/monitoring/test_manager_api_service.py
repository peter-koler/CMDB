from app.services.manager_api_service import ManagerAPIService, ManagerError


def test_retry_then_success(app):
    svc = ManagerAPIService()
    app.config["GO_MANAGER_MAX_RETRIES"] = 2

    calls = {"n": 0}

    def fake_transport(method, url, data, headers, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("timeout")
        return 200, b'{"ok": true}'

    svc._transport = fake_transport
    with app.app_context():
        resp = svc.request("GET", "/api/v1/monitors")
    assert resp["ok"] is True
    assert calls["n"] == 2


def test_circuit_open_after_failures(app):
    svc = ManagerAPIService()
    app.config["GO_MANAGER_MAX_RETRIES"] = 0
    app.config["GO_MANAGER_CB_FAILURE_THRESHOLD"] = 2
    app.config["GO_MANAGER_CB_RECOVERY_SECONDS"] = 60

    def always_fail(method, url, data, headers, timeout):
        raise TimeoutError("timeout")

    svc._transport = always_fail

    with app.app_context():
        for _ in range(2):
            try:
                svc.request("GET", "/api/v1/monitors")
            except ManagerError:
                pass
        try:
            svc.request("GET", "/api/v1/monitors")
            assert False, "expected circuit open error"
        except ManagerError as e:
            assert e.status == 503
            assert e.code == "UPSTREAM_UNAVAILABLE"
