# Metrics Naming and Label Specification (M0-03 Frozen)

## 1. Scope

This specification defines:

- metric naming rules
- required labels
- label whitelist and blacklist
- validation requirements for sample data

It is aligned with `docs/migration-plan.md` section 2.1.

## 2. Naming Rules

### 2.1 Non-Prometheus Collection

- Metric name rule: `__name__ = {metrics}_{field}`
- Required mapping:
  - `__metrics__ = {metrics}`
  - `__metric__ = {field}`

Example:

- `metrics=cpu`, `field=usage`
- `__name__=cpu_usage`

### 2.2 Prometheus Auto Collection

- Metric name rule: `__name__ = {metrics}`
- No `{field}` suffix in metric name
- Mapping:
  - `__metrics__ = {metrics}`
  - `__metric__` should not be required

### 2.3 Unified Dimensions

- `job = {app}`
- `instance = {instance}`
- `__monitor_id__ = {monitor_id}`
- Prometheus mode special rule:
  - If `app` starts with `_prometheus_`, then `job` should remove this prefix.
  - Example: `_prometheus_mysql` -> `job=mysql`

## 3. Label Policy

### 3.1 Required Labels

- `job`
- `instance`
- `__monitor_id__`

### 3.2 Recommended Stable Business Labels (Whitelist)

Prefer stable, low-cardinality labels:

- `env`
- `region`
- `cluster`
- `app`
- `service`
- `namespace`
- `team`
- `az`
- `dc`

### 3.3 Forbidden High-Cardinality Labels (Blacklist)

The following labels are forbidden by default:

- `timestamp`
- `time`
- `rand`
- `random`
- `uuid`
- `trace_id`
- `span_id`
- `request_id`
- `session_id`
- `pod_uid`

## 4. Validation Rules

A metric point passes validation only if:

1. Required labels exist and are non-empty.
2. Metric name follows mode-specific naming rule.
3. `__metrics__` and `__metric__` mapping is correct.
4. `job`/`instance`/`__monitor_id__` match top-level fields.
5. No blacklisted label key exists.
6. Label key matches regex: `^[a-zA-Z_][a-zA-Z0-9_]*$`.

## 5. Validation Script and Sample

- Script: `tools/monitoring/validate_metric_contract.py`
- Sample: `docs/api/metric-contract-sample.json`

Run:

```bash
python3 tools/monitoring/validate_metric_contract.py docs/api/metric-contract-sample.json
```
