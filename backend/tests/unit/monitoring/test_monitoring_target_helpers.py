from app.services.monitoring_target_helpers import _mysql_default_alert_rules


def test_mysql_default_alert_rules_contains_core_rules():
    rules = _mysql_default_alert_rules()
    assert isinstance(rules, list)
    assert len(rules) >= 5

    names = {str(item.get("name")) for item in rules if isinstance(item, dict)}
    assert "MySQL实例不可用" in names
    assert "MySQL连接利用率过高" in names

    down_rule = next(item for item in rules if item.get("name") == "MySQL实例不可用")
    assert down_rule.get("expr") == "mysql_server_up == 0"
    assert down_rule.get("enabled") is True
