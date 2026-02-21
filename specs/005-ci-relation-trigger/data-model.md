# 数据模型设计

## 实体关系图

```
┌─────────────────┐     ┌─────────────────┐
│   CmdbModel     │     │  RelationType   │
│─────────────────│     │─────────────────│
│ id              │     │ id              │
│ name            │     │ code            │
│ code            │     │ name            │
│ batch_scan_enabled │  │ ...             │
│ batch_scan_cron │     └────────┬────────┘
└────────┬────────┘              │
         │                       │
         │ source/target         │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           RelationTrigger               │
│─────────────────────────────────────────│
│ id                                      │
│ name                                    │
│ source_model_id  ───────► CmdbModel     │
│ target_model_id  ───────► CmdbModel     │
│ relation_type_id ───────► RelationType  │
│ trigger_type                            │
│ trigger_condition (JSON)                │
│ is_active                               │
└─────────────────────────────────────────┘
         │
         │ 执行记录
         ▼
┌─────────────────────────────────────────┐
│        TriggerExecutionLog              │
│─────────────────────────────────────────│
│ id                                      │
│ trigger_id  ───────► RelationTrigger    │
│ source_ci_id ──────► CiInstance         │
│ target_ci_id ──────► CiInstance (可空)  │
│ status (success/failed/skipped)         │
│ message                                 │
│ created_at                              │
└─────────────────────────────────────────┘
```

## 模型定义

### 1. RelationTrigger (扩展现有模型)

现有字段保持不变，新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| source_model_id | Integer FK | 源模型 ID（已有） |
| target_model_id | Integer FK | 目标模型 ID（已有） |
| relation_type_id | Integer FK | 关系类型 ID（已有） |
| trigger_type | String(20) | 触发类型：reference/expression（已有） |
| trigger_condition | Text (JSON) | 触发条件（已有） |
| is_active | Boolean | 是否启用（已有） |

**trigger_condition JSON 结构（精确匹配）**:
```json
{
  "source_field": "server_ip",
  "target_field": "manage_ip"
}
```

### 2. CmdbModel (扩展现有模型)

在 `config` JSON 字段中新增配置项：

```json
{
  "batch_scan_enabled": true,
  "batch_scan_cron": "0 2 * * *"
}
```

| 配置项 | 类型 | 说明 |
|--------|------|------|
| batch_scan_enabled | Boolean | 是否启用批量扫描 |
| batch_scan_cron | String | Cron 表达式（默认每天凌晨 2 点） |

### 3. TriggerExecutionLog (新增模型)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| trigger_id | Integer | FK, NOT NULL | 触发器 ID |
| source_ci_id | Integer | FK, NOT NULL | 源 CI ID |
| target_ci_id | Integer | FK, NULLABLE | 目标 CI ID（失败时可能为空） |
| status | String(20) | NOT NULL | 状态：success/failed/skipped |
| message | Text | NULLABLE | 执行消息或错误信息 |
| created_at | DateTime | NOT NULL | 创建时间 |

**索引**:
- `idx_trigger_log_trigger_id` ON (trigger_id)
- `idx_trigger_log_created_at` ON (created_at)
- `idx_trigger_log_status` ON (status)

### 4. BatchScanTask (新增模型)

用于跟踪批量扫描任务状态和执行历史：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| model_id | Integer | FK, NOT NULL | 模型 ID |
| status | String(20) | NOT NULL | 状态：pending/running/completed/failed |
| total_count | Integer | DEFAULT 0 | 总 CI 数量 |
| processed_count | Integer | DEFAULT 0 | 已处理数量 |
| created_count | Integer | DEFAULT 0 | 创建关系数量 |
| skipped_count | Integer | DEFAULT 0 | 跳过数量（关系已存在） |
| failed_count | Integer | DEFAULT 0 | 失败数量 |
| error_message | Text | NULLABLE | 错误信息 |
| trigger_source | String(20) | NOT NULL | 触发来源：manual/scheduled |
| started_at | DateTime | NULLABLE | 开始时间 |
| completed_at | DateTime | NULLABLE | 完成时间 |
| created_at | DateTime | NOT NULL | 创建时间 |
| created_by | Integer | FK, NULLABLE | 创建人（手动触发时有值） |

**索引**:
- `idx_batch_scan_model_id` ON (model_id)
- `idx_batch_scan_status` ON (status)
- `idx_batch_scan_created_at` ON (created_at)

## 状态转换

### TriggerExecutionLog.status

```
pending ──► success (关系创建成功)
        ──► failed  (执行失败)
        ──► skipped (跳过，如关系已存在)
```

### BatchScanTask.status

```
pending ──► running ──► completed
                  ───► failed
```

## 数据完整性约束

1. **关系唯一性**: `CmdbRelation` 已有唯一约束 (source_ci_id, target_ci_id, relation_type_id)
2. **触发器引用完整性**: 删除模型或关系类型时，关联触发器应设置 `is_active = False`
3. **批量扫描并发控制**: 同一模型同时只能有一个 `running` 状态的扫描任务
