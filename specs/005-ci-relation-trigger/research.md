# 技术调研报告

## 调研目标

基于功能规格说明书中的需求，调研并确定以下技术决策：

1. 触发器匹配逻辑的实现方式
2. CI 新增/更新时触发器执行的时机
3. 后台批量扫描任务的调度方案
4. 执行日志的存储方案

## 决策记录

### 1. 触发器匹配逻辑

**决策**: 使用精确值匹配

**理由**: 
- 用户明确要求"代码简洁，避免过度设计"
- 精确匹配实现简单、性能高、易于调试
- 现有 `RelationTrigger` 模型已支持 `trigger_condition` JSON 字段存储匹配规则

**实现方案**:
```json
{
  "source_field": "server_ip",
  "target_field": "manage_ip",
  "match_type": "exact"
}
```

**备选方案**: 
- 正则匹配：复杂度高，性能差
- 通配符匹配：实现成本中等，但需求未提及

### 2. CI 新增/更新时触发器执行

**决策**: 在 CI 保存后异步执行触发器

**理由**:
- 避免阻塞 CI 保存操作
- 满足 5 秒内完成的要求
- 使用现有 Flask 应用上下文处理

**实现方案**:
- 在 `CiInstance.save()` 后调用 `trigger_service.process_ci_triggers(ci)`
- 使用 `db.session.commit()` 后的钩子

### 3. 后台批量扫描任务

**决策**: 使用 APScheduler 进行定时任务调度

**理由**:
- APScheduler 是 Python 最流行的轻量级调度框架
- 原生支持 Cron 表达式，与需求完美匹配
- 支持 Dynamic 调度器，可动态添加/修改/删除任务
- 与 Flask 集成简单，无需额外基础设施（如 Redis）
- 数据量 10,000 级别，单线程分批处理足够

**实现方案**:
- 新增 `backend/app/tasks/scheduler.py` 初始化 APScheduler
- 新增 `backend/app/tasks/batch_scan.py` 批量扫描逻辑
- 使用 BackgroundScheduler + CronTrigger
- 每批处理 100 个 CI，避免超时
- 配置变更时动态更新调度任务

**代码示例**:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

def add_batch_scan_job(model_id, cron_expression):
    trigger = CronTrigger.from_crontab(cron_expression)
    scheduler.add_job(
        batch_scan_task,
        trigger=trigger,
        id=f'batch_scan_model_{model_id}',
        args=[model_id],
        replace_existing=True
    )
```

**备选方案**:
- Celery：功能强大但需要 Redis/RabbitMQ，引入复杂度高
- 简单线程：无法支持动态 Cron 配置

### 4. 执行日志存储

**决策**: 扩展现有 `CiHistory` 模型或新增 `TriggerExecutionLog` 表

**理由**:
- 需要记录触发器执行的详细日志
- 支持问题排查和审计

**实现方案**:
新增 `TriggerExecutionLog` 模型：
```
- id: 主键
- trigger_id: 触发器 ID
- source_ci_id: 源 CI ID
- target_ci_id: 目标 CI ID（可能为空）
- status: success/failed/skipped
- message: 执行消息
- created_at: 创建时间
```

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 批量扫描超时 | 中 | 分批处理，每批 100 CI |
| 并发扫描冲突 | 低 | 使用数据库锁或状态标记 |
| 触发器规则错误 | 中 | 记录错误日志，跳过执行 |

## 依赖项

- 现有 `RelationTrigger` 模型需要扩展（增加批量扫描配置字段）
- 现有 `CmdbRelation` 模型已有 `source_type` 字段支持
- 现有 `relation_service.py` 的验证逻辑可复用
