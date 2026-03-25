# M0-04 Environment Baseline

## Scope

This baseline provides one-command local startup for:

- Redis
- VictoriaMetrics
- Python Web (run locally, not in Docker)
- Vue frontend (run locally, not in Docker)
- Go Manager (run locally, not in Docker in M0)

Docker scope in M0 is only data infrastructure services.

## Files

- `docker-compose.yml`
- `.env.example`

## Quick Start

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

## Health Checks

- Redis: `redis-cli ping`
- VictoriaMetrics: `GET /health`

## Stop

```bash
docker compose down
```

## Notes

- Current baseline uses PostgreSQL for Python Web metadata DB.
- Python Web and Vue frontend should run on host machine in development.
- M1 can decide whether to containerize Go Manager; M0 does not require it.
- Current runtime caveat (2026-03-23): Go Manager persistence still points to SQLite (`backend/instance/it_ops.db`), not PostgreSQL.
- Target baseline: Python Web + Go Manager both use PostgreSQL as single metadata source.

## PostgreSQL Baseline (2026-03-23)

- Compose service: `arco-postgres` (`postgres:16-alpine`)
- Default DB credentials (from `.env.example`):
  - `POSTGRES_USER=arco_user`
  - `POSTGRES_PASSWORD=arco_password`
  - `POSTGRES_DB=arco_db`
- Backend connection:
  - `DATABASE_URL=postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db`

## Database Initialization Script

Use this for first-time deployment on another host PostgreSQL instance:

1. Apply role/database/extension initialization SQL:
```bash
psql -h <host> -p <port> -U postgres -d postgres -f init-scripts/00-init-postgres.sql
```

2. Bootstrap schema/default data:
```bash
PGHOST=<host> PGPORT=<port> PGUSER=postgres PGPASSWORD=<password> \
DATABASE_URL=postgresql+psycopg2://arco_user:arco_password@<host>:<port>/arco_db \
./backend/scripts/init_postgres.sh
```

## SQLite to PostgreSQL Migration

For in-place migration from existing SQLite:

```bash
DATABASE_URL=postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db \
python3 backend/scripts/migrate_sqlite_to_postgres.py --sqlite backend/instance/it_ops.db
```

Artifacts:
- backup / report directory: `backend/migration_artifacts/`

## Metadata Shared DB Design (Python Web / Go Manager)

Source alignment: `docs/migration-plan.md` section 5.1 defines metadata as shared configuration/domain data.

Unified metadata DB in development:

- Primary: PostgreSQL (`arco_db`)
- Fallback source for legacy migration: `backend/instance/it_ops.db` (SQLite)

## Manager-Go Migration Gap (Must Close)

- Gap: Manager-Go still reads/writes SQLite while Python Web uses PostgreSQL.
- Impact: License/template/runtime state may diverge across services.
- Required closure:
  1. Add PostgreSQL store implementation for Manager-Go.
  2. Migrate legacy SQLite runtime/config data into PostgreSQL.
  3. Switch Manager-Go runtime DSN to PostgreSQL and remove SQLite from steady-state path.

Tables added for shared metadata:

### Collector Management

1. `collectors` (collector node metadata)
- Core fields: `id`, `name`, `ip`, `version`, `status`, `mode`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `name` unique
  - `status in (0-online, 1-offline)`
  - `mode in ('public', 'private')`
- Indexes:
  - `idx_collectors_name(name)` unique
  - `idx_collectors_status(status)`

2. `collector_monitor_binds` (collector-monitor assignment binding)
- Core fields: `id`, `collector`, `monitor_id`, `pinned`, `creator`, `modifier`, `created_at`, `updated_at`
- Description: 记录监控任务与 Collector 的绑定关系，支持用户固定指定或自动分配
- Constraints:
  - `collector` + `monitor_id` unique
  - `pinned in (0-auto-assigned, 1-user-pinned)`
- Indexes:
  - `idx_collector_monitor_collector(collector)`
  - `idx_collector_monitor_monitor_id(monitor_id)`

3. `status_page_orgs` (status page organization)
- Core fields: `id`, `name`, `description`, `home`, `logo`, `feedback`, `color`, `state`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `state in (0-All Systems Operational, 1-Some Systems Abnormal, 2-All Systems Abnormal)`
- Indexes:
  - `idx_status_page_orgs_name(name)`

5. `status_page_components` (status page component)
- Core fields: `id`, `org_id`, `name`, `description`, `labels_json`, `method`, `config_state`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `method in (0-auto, 1-manual)`
  - `config_state in (0-Normal, 1-Abnormal, 2-unknown)`
- Indexes:
  - `idx_status_page_components_org_id(org_id)`
  - Foreign key: `org_id` -> `status_page_orgs(id)`

6. `status_page_incidents` (status page incident)
- Core fields: `id`, `org_id`, `name`, `description`, `state`, `start_time`, `end_time`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `state in (0-Investigating, 1-Identified, 2-Monitoring, 3-Resolved)`
- Indexes:
  - `idx_status_page_incidents_org_id(org_id)`
  - `idx_status_page_incidents_state(state)`

7. `alert_defines` (alert rule definition)
- Core fields: `id`, `name`, `type`, `expr`, `period`, `times`, `labels_json`, `annotations_json`, `template`, `datasource_type`, `enabled`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in ('realtime_metric', 'periodic_metric', 'realtime_log', 'periodic_log')`
  - `times >= 1`
  - `period >= 0`
- Indexes:
  - `idx_alert_defines_name(name)`
  - `idx_alert_defines_type(type)`
  - `idx_alert_defines_enabled(enabled)`

8. `alert_silences` (alert silence rule)
- Core fields: `id`, `name`, `type`, `match_type`, `labels_json`, `days_json`, `times`, `start_time`, `end_time`, `enabled`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in (0-one-time, 1-cyclic)`
  - `match_type in (0-all, 1-partial)`
- Indexes:
  - `idx_alert_silences_enabled(enabled)`
  - `idx_alert_silences_time(start_time, end_time)`
- Notes:
  - `days_json`: JSON array for cyclic silence days [1,2,3,4,5,6,7] (Monday to Sunday)

9. `alert_inhibits` (alert inhibit rule)
- Core fields: `id`, `name`, `source_labels_json`, `target_labels_json`, `equal_labels_json`, `enabled`, `creator`, `modifier`, `created_at`, `updated_at`
- Indexes:
  - `idx_alert_inhibits_enabled(enabled)`

10. `alert_groups` (alert group converge)
- Core fields: `id`, `name`, `group_key`, `match_type`, `labels_json`, `group_wait`, `group_interval`, `repeat_interval`, `enabled`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `group_key` unique
  - `match_type in (0-all, 1-partial)`
- Indexes:
  - `idx_alert_groups_group_key(group_key)` unique

11. `notice_rules` (alert notification rule)
- Core fields: `id`, `name`, `receiver_type`, `receiver_id`, `notify_type`, `notify_times`, `notify_scale`, `enable`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `receiver_type in ('user', 'group')`
  - `notify_type in ('email', 'sms', 'webhook', 'wecom', 'dingtalk', 'feishu')`
  - `notify_scale in ('single', 'batch')`
- Indexes:
  - `idx_notice_rules_receiver(receiver_type, receiver_id)`

12. `notice_receivers` (notification receiver)
- Core fields: `id`, `name`, `type`, `phone`, `email`, `hook_url`, `hook_auth_type`, `hook_auth_token`, `wechat_id`, `app_id`, `access_token`, `tg_bot_token`, `tg_user_id`, `tg_message_thread_id`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in (0-SMS, 1-Email, 2-Webhook, 3-WeChat Official, 4-WeCom Robot, 5-DingTalk Robot, 6-FeiShu Robot, 7-Telegram Bot, 8-Slack WebHook, 9-Discord Bot, 10-WeCom App, 11-Slack, 12-Discord, 13-Gotify, 14-FeiShu App)`
  - `hook_auth_type in ('None', 'Basic', 'Bearer')`
- Indexes:
  - `idx_notice_receivers_name(name)`
  - `idx_notice_receivers_type(type)`

13. `notice_templates` (notification template)
- Core fields: `id`, `name`, `type`, `preset`, `content`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in (0-SMS, 1-Email, 2-Webhook, 3-WeChat Official, 4-WeCom Robot, 5-DingTalk Robot, 6-FeiShu Robot, 7-Telegram Bot, 8-Slack WebHook, 9-Discord Bot, 10-WeCom App)`
  - `preset` boolean (true-预设模板, false-自定义)
- Indexes:
  - `idx_notice_templates_name(name)`
  - `idx_notice_templates_type(type)`
  - `idx_notice_templates_preset(preset)`

14. `tags` (monitoring tags for monitors)
- Core fields: `id`, `name`, `tag_value`, `description`, `type`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in (0-Auto, 1-User, 2-System)`
  - `name` + `tag_value` unique
- Indexes:
  - `idx_tags_name_value(name, tag_value)` unique
- Note: Used for monitor categorization (e.g., env=prod, team=ops)

15. `alert_labels` (alert labels for alert rules)
- Core fields: `id`, `name`, `value`, `color`, `description`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `name` + `value` unique
- Indexes:
  - `idx_alert_labels_name_value(name, value)` unique
- Note: Used for alert rule matching (e.g., severity=critical, service=database)

### Runtime Data Tables (Alert Data / History)

13. `single_alerts` (single alert instance)
- Core fields: `id`, `fingerprint`, `labels_json`, `annotations_json`, `content`, `status`, `trigger_times`, `start_at`, `active_at`, `end_at`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `fingerprint` unique
  - `status in ('firing', 'resolved')`
  - `trigger_times >= 1`
- Indexes:
  - `idx_single_alerts_fingerprint(fingerprint)` unique
  - `idx_single_alerts_status(status)`
  - `idx_single_alerts_time(start_at, end_at)`

14. `group_alerts` (grouped alert)
- Core fields: `id`, `group_key`, `status`, `group_labels_json`, `common_labels_json`, `common_annotations_json`, `alert_fingerprints_json`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `group_key` unique
  - `status in ('firing', 'resolved')`
- Indexes:
  - `idx_group_alerts_group_key(group_key)` unique
  - `idx_group_alerts_status(status)`

15. `alert_history` (alert history archive)
- Core fields: `id`, `alert_id`, `alert_type`, `labels_json`, `annotations_json`, `content`, `status`, `trigger_times`, `start_at`, `end_at`, `duration_ms`, `created_at`
- Constraints:
  - `alert_type in ('single', 'group')`
  - `status in ('firing', 'resolved')`
- Indexes:
  - `idx_alert_history_alert_id(alert_id)`
  - `idx_alert_history_type(alert_type)`
  - `idx_alert_history_time(created_at)`
  - `idx_alert_history_status(status)`

16. `alert_notifications` (alert notification log)
- Core fields: `id`, `alert_id`, `rule_id`, `receiver_type`, `receiver_id`, `notify_type`, `status`, `content`, `error_msg`, `retry_times`, `sent_at`, `created_at`, `updated_at`
- Constraints:
  - `status in (0-pending, 1-sending, 2-success, 3-failed)`
  - `notify_type in ('email', 'sms', 'webhook', 'wecom', 'dingtalk', 'feishu')`
- Indexes:
  - `idx_alert_notifications_alert_id(alert_id)`
  - `idx_alert_notifications_status(status)`
  - `idx_alert_notifications_time(sent_at)`

### Monitoring Task & Runtime Data Tables

17. `monitors` (monitoring task definition)
- Core fields: `id`, `job_id`, `name`, `app`, `scrape`, `instance`, `intervals`, `schedule_type`, `cron_expression`, `status`, `type`, `labels_json`, `annotations_json`, `description`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `status in (0-Paused, 1-Up, 2-Down)`
  - `type in (0-Normal, 1-Push Auto Create, 2-Discovery Auto Create)`
  - `schedule_type in ('interval', 'cron')`
  - `intervals >= 10`
- Indexes:
  - `idx_monitors_app(app)`
  - `idx_monitors_instance(instance)`
  - `idx_monitors_name(name)`
  - `idx_monitors_status(status)`

18. `monitor_params` (monitor task parameters)
- Core fields: `id`, `monitor_id`, `field`, `param_value`, `type`, `created_at`, `updated_at`
- Constraints:
  - `monitor_id` + `field` unique
  - `type in (0-number, 1-string, 2-encrypted, 3-json, 4-array)`
- Indexes:
  - `idx_monitor_params_monitor_id(monitor_id)`
  - `idx_monitor_params_field(field)`
  - Foreign key: `monitor_id` -> `monitors(id)`

19. `monitor_binds` (monitor relationship binding)
- Core fields: `id`, `key_str`, `biz_id`, `monitor_id`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `key_str` format: `ip:port`
- Indexes:
  - `idx_monitor_binds_biz_id(biz_id)`
  - `idx_monitor_binds_monitor_id(monitor_id)`
  - Foreign key: `monitor_id` -> `monitors(id)`

20. `collector_monitor_binds` (collector-task assignment)
- Core fields: `id`, `collector`, `monitor_id`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `collector` + `monitor_id` unique
- Indexes:
  - `idx_collector_monitor_collector(collector)`
  - `idx_collector_monitor_monitor_id(monitor_id)`
  - Foreign key: `monitor_id` -> `monitors(id)`

21. `monitor_defines` (monitor template definitions)
- Core fields: `app`, `content`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `app` primary key
  - `content` YAML format
- Indexes:
  - `idx_monitor_defines_app(app)`

22. `tags` (monitoring labels/tags)
- Core fields: `id`, `name`, `tag_value`, `description`, `type`, `creator`, `modifier`, `created_at`, `updated_at`
- Constraints:
  - `type in (0-Auto-generated, 1-User-generated, 2-System Preset)`
  - `name` + `tag_value` unique
- Indexes:
  - `idx_tags_name(name)`
  - `idx_tags_type(type)`
  - `idx_tags_name_value(name, tag_value)` unique

### Metrics Data Warehouse Tables

23. `metrics_history` (time-series metrics data)
- Core fields: `id`, `instance`, `app`, `metrics`, `metric`, `metric_labels_json`, `metric_type`, `str_value`, `int32_value`, `double_value`, `timestamp`
- Constraints:
  - `metric_type in (0-Number, 1-String)`
  - `timestamp` millisecond precision
- Indexes:
  - `idx_metrics_history_instance(instance)`
  - `idx_metrics_history_app(app)`
  - `idx_metrics_history_metrics(metrics)`
  - `idx_metrics_history_metric(metric)`
  - `idx_metrics_history_time(timestamp)`
  - Composite: `idx_metrics_history_query(instance, app, metrics, metric, timestamp)`

Cross-service contract constraints:

- Use UTC for `created_at/updated_at`.
- Update operations must increase `version` for optimistic locking.
- JSON payloads are UTF-8 and stored as text (`*_json`) for SQLite portability.

## Table Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Configuration Tables                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌──────────────────┐         ┌─────────────────┐  │
│  │   monitors   │◄────────┤ monitor_params   │         │  monitor_defines│  │
│  │  (监控任务)   │         │  (监控参数)       │         │  (监控模板定义)  │
│  └──────┬───────┘         └──────────────────┘         └─────────────────┘  │
│         │                                                                    │
│         │    ┌──────────────────────────────┐                               │
│         └───►│  collector_monitor_binds     │                               │
│              │  (采集器-任务分配)             │                               │
│              └──────────────┬───────────────┘                               │
│                             │                                                │
│                             ▼                                                │
│              ┌──────────────────────────────┐                               │
│              │        collectors            │                               │
│              │      (采集器节点)             │                               │
│              └──────────────────────────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Alert Configuration Tables                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │alert_defines │    │alert_silences│    │alert_inhibits│                  │
│  │  (告警规则)   │    │  (静默规则)   │    │  (抑制规则)   │                  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘                  │
│         │                                                                    │
│         │    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│         └───►│ alert_groups │◄───┤ notice_rules │◄───┤notice_receivers│     │
│              │  (分组收敛)   │    │  (通知规则)   │    │  (通知接收人)  │     │
│              └──────────────┘    └──────┬───────┘    └──────┬───────┘     │
│                                         │                   │              │
│                              ┌──────────┴──────────┐       │              │
│                              │   notice_templates  │◄──────┘              │
│                              │    (通知模板)        │                      │
│                              └─────────────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Status Page Tables                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌─────────────────────┐                           │
│  │ status_page_orgs │◄───┤status_page_components│                          │
│  │  (状态页组织)     │    │   (状态页组件)       │                          │
│  └────────┬─────────┘    └──────────┬──────────┘                           │
│           │                         │                                       │
│           │    ┌────────────────────┴──────────────┐                       │
│           └───►│     status_page_incidents         │                       │
│                │       (状态页事件)                 │                       │
│                └───────────────────────────────────┘                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           Runtime Data Tables                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ single_alerts│    │ group_alerts │    │alert_history │                  │
│  │  (单条告警)   │───►│  (分组告警)   │───►│  (告警历史)   │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘                  │
│         │                   │                                               │
│         │    ┌──────────────┴──────────────┐                               │
│         └───►│   alert_notifications       │                               │
│              │     (通知发送记录)            │                               │
│              └─────────────────────────────┘                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        metrics_history                              │   │
│  │                     (时序指标数据仓库)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Relationships

1. **Monitor Task Flow**: `monitors` → `monitor_params` (1:N), `monitors` → `collector_monitor_binds` → `collectors` (N:M)
2. **Alert Flow**: `alert_defines` trigger → `single_alerts` → `alert_groups` → `notice_rules` → `notice_receivers`/`notice_templates`
3. **Status Page Flow**: `status_page_orgs` → `status_page_components` (1:N), `status_page_incidents` link to components
4. **Label System**: `tags` can be referenced by `monitors`, `alert_defines` via `labels_json`

Sync rule:

- Python Web model declaration + table sync to SQLite is the baseline.
- Go Manager can later reuse the same tables and implement persistence logic without schema drift.
