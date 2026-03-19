from __future__ import annotations

from copy import deepcopy

from scripts.apply_cache_default_alerts import POLICIES as CACHE_POLICIES
from scripts.apply_bigdata_default_alerts import POLICIES as BIGDATA_POLICIES
from scripts.apply_db_default_alerts import POLICIES as DB_POLICIES
from scripts.apply_middleware_default_alerts import POLICIES as MIDDLEWARE_POLICIES
from scripts.apply_os_default_alerts import POLICIES as OS_POLICIES
from scripts.apply_server_default_alerts import POLICIES as SERVER_POLICIES
from scripts.apply_service_default_alerts import POLICIES as SERVICE_POLICIES
from scripts.apply_webserver_default_alerts import POLICIES as WEBSERVER_POLICIES


def _clone_rules(items: list[dict]) -> list[dict]:
    return [deepcopy(item) for item in items]


def database_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = DB_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def bigdata_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = BIGDATA_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def cache_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = CACHE_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def middleware_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = MIDDLEWARE_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def server_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = SERVER_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def webserver_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = WEBSERVER_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def os_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = OS_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)


def service_default_alert_rules(app: str) -> list[dict]:
    app_key = str(app or "").strip().lower()
    rules = SERVICE_POLICIES.get(app_key)
    if not rules:
        return []
    return _clone_rules(rules)
