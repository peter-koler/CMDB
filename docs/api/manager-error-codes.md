# Manager API Error Codes (M0-01 Frozen)

## Scope

This table defines stable error codes used by `docs/api/manager-openapi.yaml`.

## Error Code Table

| Code | HTTP | Meaning | Typical Cause |
|---|---:|---|---|
| `AUTH_UNAUTHORIZED` | 401 | Missing/invalid access token | No bearer token, expired token, invalid signature |
| `AUTH_FORBIDDEN` | 403 | Permission denied | User lacks required permission for action |
| `MONITOR_NOT_FOUND` | 404 | Monitor does not exist | Monitor id is invalid or deleted |
| `MONITOR_CONFLICT` | 409 | Monitor state/version conflict | Optimistic lock version mismatch |
| `MONITOR_INVALID_CONFIG` | 422 | Monitor payload is semantically invalid | Invalid interval/params/template mismatch |
| `ALERT_NOT_FOUND` | 404 | Alert does not exist | Alert id is invalid or archived |
| `ALERT_STATE_CONFLICT` | 409 | Alert cannot transition to requested state | Already recovered/closed or already acknowledged |
| `INVALID_ARGUMENT` | 400 | Generic invalid request argument | Missing path/query/body field or bad format |
| `VALIDATION_FAILED` | 422 | Request validation failed | Schema validation errors |
| `RATE_LIMITED` | 429 | Too many requests | Burst traffic exceeds rate limit |
| `INTERNAL_ERROR` | 500 | Internal service failure | Unexpected runtime or dependency error |
| `UPSTREAM_UNAVAILABLE` | 503 | Required dependency unavailable | Redis/VM/DB unavailable or timeout |

## Notes

- Codes are stable API contract and must not be renamed without versioning.
- Response shape is defined by `ErrorResponse` schema in OpenAPI.
