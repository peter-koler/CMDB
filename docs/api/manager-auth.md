# Manager API Authentication and Authorization (M0-01 Frozen)

## Authentication

- Scheme: `Bearer JWT` in `Authorization` header.
- Token issuer: Python Web auth service.
- Manager verifies token signature and expiry.
- Required claims:
  - `sub`: user id
  - `exp`: expiry timestamp
  - `roles`: role list
  - `perms`: permission list

## Authorization Mapping

| API | Permission |
|---|---|
| `POST /api/v1/monitors` | `monitoring:list:create` |
| `PUT /api/v1/monitors/{monitor_id}` | `monitoring:list:edit` |
| `GET /api/v1/monitors` | `monitoring:list:view` |
| `GET /api/v1/monitors/{monitor_id}` | `monitoring:list:view` |
| `GET /api/v1/alerts` | `monitoring:alert:center:view` |
| `POST /api/v1/alerts/{alert_id}/acknowledge` | `monitoring:alert:center:claim` |

## Security Requirements

- All endpoints in `manager-openapi.yaml` require bearer token.
- Manager must log `request_id`, `sub`, resource id, action, result for audit.
- Sensitive fields in logs must be masked (credentials/tokens).

## Compatibility Rule

- New permissions can be added.
- Existing permission keys in this file are frozen for M0 and should remain backward compatible.
