# CMDB CI 关系触发器优化需求说明

## 项目状态

**当前进度**: 91.3% (42/46 任务完成)

**已完成功能**:
- ✅ 触发器规则配置与管理 (后端 API + 前端页面)
- ✅ CI 保存后自动触发关系创建
- ✅ 批量扫描手动触发与定时任务
- ✅ 执行日志记录
- ✅ Cron 表达式配置
- ✅ 批量扫描配置页面
- ✅ 触发器列表管理页面
- ✅ 批量扫描历史页面
- ✅ 模型属性字段从 form_config 获取
- ✅ 后端 API 返回格式统一

**待完成功能**:
- ⏳ 触发器匹配逻辑单元测试
- ⏳ 批量扫描任务单元测试
## 背景与目标
系统需要在新增或更新 CI 时自动生成符合规则的关系，并支持后台批量扫描历史数据，定期补齐缺失关系，降低人工维护成本，确保模型关系一致性。

## 术语
- CI：配置项实例
- 关系触发器：定义源模型、目标模型与字段匹配规则的关系生成规则
- 批量扫描：对模型下所有 CI 进行规则匹配并自动建立关系

## 范围
### 包含
- 触发器规则配置与管理
- CI 保存后自动触发关系创建
- 批量扫描手动触发与定时任务
- 执行日志与扫描历史展示
- Cron 表达式配置

### 不包含
- 复杂匹配（正则/通配符）
- 多级触发器链路
- 分布式任务调度基础设施（如 Celery）

## 功能需求

### FR-001 触发器规则配置 ✅ 已完成
管理员可创建、查看、编辑、删除触发器规则，字段包括：
- 触发器名称
- 源模型与目标模型
- 关系类型
- 触发条件（源字段、目标字段，精确值匹配）
- 启用状态与描述

**实现文件**:
- 后端 API: `backend/app/routes/trigger.py`
- 数据模型: `backend/app/models/cmdb_relation.py` (RelationTrigger)
- 前端 API: `frontend/src/api/trigger.ts`

### FR-002 CI 新增/更新触发 ✅ 已完成
CI 新增或更新后，系统根据触发器规则自动创建关系，若关系已存在则跳过。

**实现文件**:
- 触发器服务: `backend/app/services/trigger_service.py`
- 核心方法: `process_ci_triggers()`, `match_trigger_condition()`, `create_relation_with_skip_duplicate()`

### FR-003 批量扫描配置 ✅ 已完成
管理员可为模型配置批量扫描开关与 Cron 表达式，支持手动触发与定时执行。

**实现文件**:
- 后端 API: `backend/app/routes/trigger.py`
- 调度器: `backend/app/tasks/scheduler.py`
- 前端页面: `frontend/src/views/config/batch-scan-config/index.vue` (独立配置页面)
- 菜单入口: 配置管理 → 扫描配置
- 权限控制: `cmdb:batch-scan:config` (配置权限), `cmdb:batch-scan:trigger` (触发执行权限)

### FR-004 批量扫描执行 ✅ 已完成
扫描任务按批次处理该模型所有 CI，建立符合条件的关系，并记录统计信息。

**实现文件**:
- 批量扫描任务: `backend/app/tasks/batch_scan.py`
- 核心方法: `batch_scan_model()`, `create_batch_scan_task()`
- 分批处理: 每批 100 CI

### FR-005 触发器查看与管理 ✅ 已完成
页面提供触发器列表与编辑功能，支持按模型查看配置。

**实现文件**:
- 后端 API: `backend/app/routes/trigger.py`
- 前端页面: `frontend/src/views/cmdb/TriggerConfig.vue`
- 前端 API: `frontend/src/api/trigger.ts`

### FR-006 执行日志记录 ✅ 已完成
系统记录每次触发器执行结果（成功/失败/跳过），用于审计与排错。

**实现文件**:
- 数据模型: `backend/app/models/cmdb_relation.py` (TriggerExecutionLog)
- 日志记录: `backend/app/services/trigger_service.py` (`log_trigger_execution()`)

### FR-007 批量扫描历史 ✅ 已完成
页面展示扫描任务历史与结果统计，支持详情查看。

**实现文件**:
- 后端 API: `backend/app/routes/trigger.py`
- 前端页面: `frontend/src/views/config/batch-scan/index.vue`
- 前端 API: `frontend/src/api/trigger.ts`

### FR-008 Cron 配置 ✅ 已完成
支持 Cron 表达式配置执行时间点，修改后立即生效。

**实现文件**:
- 后端验证: `backend/app/routes/trigger.py` (update_batch_scan_config)
- 调度器动态管理: `backend/app/tasks/scheduler.py` (`add_batch_scan_job()`, `remove_batch_scan_job()`)

### FR-009 任务详情 ✅ 已完成
支持查看单次扫描任务处理数量、创建数量、失败原因与耗时。

**实现文件**:
- 后端 API: `backend/app/routes/trigger.py` (get_batch_scan_task)
- 前端弹窗: `frontend/src/views/config/batch-scan/index.vue`

## 非功能需求
- 关系创建应在 5 秒内完成（P95）
- 批量扫描支持 10,000+ CI 不超时
- API P95 < 500ms
- 错误应被记录并可追溯

## 数据模型摘要

### RelationTrigger ✅ 已实现
触发器规则，字段包含源模型、目标模型、关系类型、触发条件（JSON）。

```python
class RelationTrigger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source_model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'))
    target_model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'))
    relation_type_id = db.Column(db.Integer, db.ForeignKey('relation_types.id'))
    trigger_type = db.Column(db.String(20), default='expression')
    trigger_condition = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
```

### TriggerExecutionLog ✅ 已实现
触发器执行日志，记录源 CI、目标 CI、状态与消息。

```python
class TriggerExecutionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trigger_id = db.Column(db.Integer, db.ForeignKey('relation_triggers.id'))
    source_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'))
    target_ci_id = db.Column(db.Integer, db.ForeignKey('ci_instances.id'))
    status = db.Column(db.String(20), nullable=False)  # success/failed/skipped
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### BatchScanTask ✅ 已实现
批量扫描任务状态、统计与执行时间信息。

```python
class BatchScanTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('cmdb_models.id'))
    status = db.Column(db.String(20), default='pending')  # pending/running/completed/failed
    total_count = db.Column(db.Integer, default=0)
    processed_count = db.Column(db.Integer, default=0)
    created_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    trigger_source = db.Column(db.String(20))  # manual/scheduled
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
```

### CmdbModel.config 扩展 ✅ 已实现
包含 `batch_scan_enabled` 与 `batch_scan_cron` 配置项。

## 触发器匹配规则
精确值匹配：
- source_field 与 target_field 字段值相等时命中
- 不支持正则与通配符

## 关键流程

### CI 保存触发 ✅ 已实现
1. 保存 CI
2. 读取该模型启用的触发器
3. 匹配条件并建立关系
4. 记录执行日志

### 批量扫描 ✅ 已实现
1. 创建扫描任务记录
2. 读取模型触发器
3. 分批遍历 CI（默认每批 100）
4. 匹配并创建关系
5. 更新任务统计与状态

## 接口摘要

### 触发器 API ✅ 已实现
| 接口 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/models/{model_id}/triggers` | GET | 获取触发器列表 | ✅ |
| `/api/models/{model_id}/triggers` | POST | 创建触发器 | ✅ |
| `/api/triggers/{trigger_id}` | GET | 获取触发器详情 | ✅ |
| `/api/triggers/{trigger_id}` | PUT | 更新触发器 | ✅ |
| `/api/triggers/{trigger_id}` | DELETE | 删除触发器 | ✅ |
| `/api/triggers/{trigger_id}/logs` | GET | 获取执行日志 | ✅ |

### 批量扫描 API ✅ 已实现
| 接口 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/models/{model_id}/batch-scan` | POST | 触发批量扫描 | ✅ |
| `/api/models/{model_id}/batch-scan` | GET | 获取模型扫描任务 | ✅ |
| `/api/batch-scan/tasks` | GET | 获取所有扫描任务 | ✅ |
| `/api/batch-scan/tasks/{task_id}` | GET | 获取任务详情 | ✅ |
| `/api/batch-scan/config/{model_id}` | GET | 获取扫描配置 | ✅ |
| `/api/batch-scan/config/{model_id}` | PUT | 更新扫描配置 | ✅ |

## 验收场景

### 已验证 ✅
1. 新增/更新 CI 自动创建关系，若不匹配不创建
2. 手动触发扫描可补齐历史关系
3. 批量扫描历史页面展示任务统计与详情
4. Cron 配置修改后定时任务生效
5. 触发器执行失败可在日志中查看原因
6. 触发器列表页面管理功能

## 问题修复记录

### 2026-02-21 修复记录

#### 1. 模型字段下拉框为空问题
**问题描述**: 新增触发器时，源字段和目标字段下拉框无法获取模型属性信息。

**原因分析**:
- 模型的字段信息存储在 `form_config` 字段中（JSON 字符串格式）
- `fields` 关系使用 `lazy="dynamic"`，需要调用 `.all()` 方法
- 前端仅从 `res.data.fields` 获取，未解析 `form_config`

**修复方案**:
1. 后端 `cmdb_model.py` 的 `to_full_dict()` 方法中，将 `self.fields` 改为 `self.fields.all()`
2. 前端 `relation-trigger/index.vue` 的 `fetchModelFields()` 方法增加 `form_config` 解析逻辑：
   ```typescript
   if (fields.length === 0 && res.data?.form_config) {
     const formConfig = typeof res.data.form_config === 'string' 
       ? JSON.parse(res.data.form_config) 
       : res.data.form_config
     fields = formConfig.map((item: any) => ({
       code: item.props?.code,
       name: item.props?.label
     })).filter((f: any) => f.code && f.name)
   }
   ```

**涉及文件**:
- `backend/app/models/cmdb_model.py`
- `frontend/src/views/config/relation-trigger/index.vue`

#### 2. 批量扫描配置 API 404 错误
**问题描述**: 扫描配置页面启用批量扫描时，API 返回 404。

**原因分析**:
- `trigger_bp` 的 `url_prefix` 设置为 `/api`，而前端请求的是 `/api/v1/batch-scan/config/{id}`

**修复方案**:
将 `trigger_bp` 的 `url_prefix` 从 `/api` 改为 `/api/v1`

**涉及文件**:
- `backend/app/routes/trigger.py`

#### 3. 批量扫描配置保存无响应
**问题描述**: 点击确定后没有成功/失败提示。

**原因分析**:
- 后端 API 返回格式不统一，缺少 `code` 字段
- 前端检查 `res.code === 200`，但后端返回 `{"data": {...}}`

**修复方案**:
统一所有 API 返回格式为：
```json
{
  "code": 200,
  "message": "success",
  "data": {...}
}
```

**涉及文件**:
- `backend/app/routes/trigger.py` (所有 API 端点)

## 测试覆盖

### 单元测试 ✅
- `backend/tests/unit/trigger/test_models.py` - TriggerExecutionLog 和 BatchScanTask 模型测试

### 集成测试 ✅
- `backend/tests/integration/test_trigger_integration.py` - 触发器自动创建关系和批量扫描功能测试

### 待补充 ⏳
- `backend/tests/unit/test_trigger_service.py` - 触发器匹配逻辑单元测试 (T010)
- `backend/tests/unit/test_batch_scan.py` - 批量扫描任务单元测试 (T015)

## 文件清单

### 后端文件
```
backend/
├── app/
│   ├── models/
│   │   └── cmdb_relation.py      # RelationTrigger, TriggerExecutionLog, BatchScanTask
│   ├── services/
│   │   └── trigger_service.py    # 触发器服务
│   ├── routes/
│   │   └── trigger.py            # 触发器 API 路由
│   └── tasks/
│       ├── __init__.py           # 任务模块初始化
│       ├── scheduler.py          # APScheduler 调度器
│       └── batch_scan.py         # 批量扫描任务
└── tests/
    ├── unit/trigger/test_models.py
    └── integration/test_trigger_integration.py
```

### 前端文件
```
frontend/
├── src/
│   ├── views/
│   │   ├── cmdb/
│   │   │   └── TriggerConfig.vue     # ✅ 触发器配置页面（含触发器列表管理）
│   │   └── config/
│   │       ├── batch-scan-config/
│   │       │   └── index.vue         # ✅ 批量扫描配置页面
│   │       └── batch-scan/
│   │           └── index.vue         # ✅ 批量扫描历史页面
│   ├── layouts/
│   │   └── BasicLayout.vue           # ✅ 菜单配置（含扫描配置、批量扫描菜单项）
│   └── api/
│       └── trigger.ts                # ✅ 触发器 API 调用
```

### 权限配置
```
cmdb:batch-scan        # 批量扫描模块
├── cmdb:batch-scan:view      # 查看批量扫描历史
├── cmdb:batch-scan:config    # 配置批量扫描（开关、Cron）
└── cmdb:batch-scan:trigger   # 手动触发批量扫描
```

## 下一步计划

### 中优先级
1. **T010** - 编写触发器匹配逻辑单元测试
2. **T015** - 编写批量扫描任务单元测试

### 低优先级
3. **T045** - 运行 quickstart.md 验证所有功能
4. **T046** - 更新 API 文档
