# 快速开始指南

## 前置条件

- Python 3.11+
- 后端服务已启动
- 数据库迁移已执行

## 功能验证步骤

### 1. 创建测试模型

```bash
# 创建源模型（服务器）
curl -X POST http://localhost:5000/api/models \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "服务器",
    "code": "server",
    "category_id": 1,
    "fields": [
      {"name": "IP地址", "code": "ip", "field_type": "text"},
      {"name": "主机名", "code": "hostname", "field_type": "text"}
    ]
  }'

# 创建目标模型（应用）
curl -X POST http://localhost:5000/api/models \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "应用",
    "code": "application",
    "category_id": 1,
    "fields": [
      {"name": "部署IP", "code": "deploy_ip", "field_type": "text"},
      {"name": "应用名", "code": "app_name", "field_type": "text"}
    ]
  }'
```

### 2. 创建关系类型

```bash
curl -X POST http://localhost:5000/api/relation-types \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "runs_on",
    "name": "运行在",
    "source_label": "运行",
    "target_label": "承载",
    "direction": "directed"
  }'
```

### 3. 创建触发器规则

```bash
curl -X POST http://localhost:5000/api/models/1/triggers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "应用-服务器关联",
    "source_model_id": 2,
    "target_model_id": 1,
    "relation_type_id": 1,
    "trigger_type": "reference",
    "trigger_condition": {
      "source_field": "deploy_ip",
      "target_field": "ip"
    },
    "is_active": true
  }'
```

### 4. 验证自动关系创建

```bash
# 创建服务器 CI
curl -X POST http://localhost:5000/api/ci-instances \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "name": "web-server-01",
    "attribute_values": {
      "ip": "192.168.1.100",
      "hostname": "web-server-01"
    }
  }'

# 创建应用 CI（应自动创建关系）
curl -X POST http://localhost:5000/api/ci-instances \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 2,
    "name": "web-app",
    "attribute_values": {
      "deploy_ip": "192.168.1.100",
      "app_name": "Web应用"
    }
  }'

# 验证关系已创建
curl http://localhost:5000/api/relations \
  -H "Authorization: Bearer <token>"
```

### 5. 测试批量扫描

```bash
# 配置模型启用批量扫描
curl -X PUT http://localhost:5000/api/batch-scan/config/2 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_scan_enabled": true,
    "batch_scan_cron": "0 2 * * *"
  }'

# 获取批量扫描配置
curl http://localhost:5000/api/batch-scan/config/2 \
  -H "Authorization: Bearer <token>"

# 手动触发批量扫描
curl -X POST http://localhost:5000/api/models/2/batch-scan \
  -H "Authorization: Bearer <token>"

# 查看扫描任务状态
curl http://localhost:5000/api/models/2/batch-scan \
  -H "Authorization: Bearer <token>"
```

### 6. 查看批量扫描历史

```bash
# 获取所有批量扫描任务历史
curl http://localhost:5000/api/batch-scan/tasks \
  -H "Authorization: Bearer <token>"

# 按状态过滤
curl "http://localhost:5000/api/batch-scan/tasks?status=completed" \
  -H "Authorization: Bearer <token>"

# 按模型过滤
curl "http://localhost:5000/api/batch-scan/tasks?model_id=2" \
  -H "Authorization: Bearer <token>"

# 查看任务详情
curl http://localhost:5000/api/batch-scan/tasks/1 \
  -H "Authorization: Bearer <token>"
```

## 预期结果

1. 创建应用 CI 后，自动创建与服务器 CI 的关系
2. 触发器执行日志记录在 `TriggerExecutionLog` 表
3. 批量扫描能够处理历史数据并创建缺失的关系
4. 重复执行不会创建重复关系
5. 批量扫描历史页面展示所有任务的执行时间和结果
6. Cron 表达式配置变更后，新的执行计划立即生效

## 前端页面

### 批量扫描历史页面

访问路径：`/cmdb/batch-scan/history`

功能：
- 展示所有模型的批量扫描任务列表
- 显示执行时间、状态、处理数量、创建关系数量
- 支持按模型、状态、时间范围过滤
- 点击任务可查看详细执行结果

### 触发器配置页面

访问路径：`/cmdb/models/{model_id}/triggers`

功能：
- 配置触发器规则（源字段、目标字段、关系类型）
- 启用/禁用触发器
- 查看触发器执行日志

### 批量扫描配置

在模型配置页面中：
- 启用/禁用批量扫描
- 配置 Cron 表达式设置执行计划
- 查看下次执行时间和上次执行状态

## 常见问题

### Q: 触发器没有执行？

检查：
1. 触发器 `is_active` 是否为 `true`
2. 源字段和目标字段是否匹配
3. 查看执行日志 `GET /api/triggers/{id}/logs`

### Q: 批量扫描失败？

检查：
1. 模型是否启用 `batch_scan_enabled`
2. 是否有其他扫描任务正在运行
3. 查看任务详情 `GET /api/batch-scan/tasks/{id}`

### Q: Cron 表达式无效？

支持的标准 Cron 表达式格式：
```
┌───────────── 分钟 (0-59)
│ ┌───────────── 小时 (0-23)
│ │ ┌───────────── 日期 (1-31)
│ │ │ ┌───────────── 月份 (1-12)
│ │ │ │ ┌───────────── 星期几 (0-6, 0=周日)
│ │ │ │ │
* * * * *
```

示例：
- `0 2 * * *` - 每天凌晨 2 点
- `0 */6 * * *` - 每 6 小时
- `30 1 * * 1` - 每周一凌晨 1:30
