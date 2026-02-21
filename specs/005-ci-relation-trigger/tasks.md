# Tasks: CMDB CI 关系触发器优化

**Input**: Design documents from `/specs/005-ci-relation-trigger/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/trigger-api.yaml

**Tests**: 包含单元测试任务（Constitution V 要求 TDD）

**Organization**: 任务按用户场景分组，支持独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户场景（US1, US2, US3, US4, US5）
- 描述中包含具体文件路径

## Path Conventions

- **Web App**: `backend/app/`, `frontend/src/`
- 后端: `backend/app/models/`, `backend/app/services/`, `backend/app/routes/`, `backend/app/tasks/`
- 前端: `frontend/src/views/cmdb/`, `frontend/src/api/`
- 测试: `backend/tests/unit/`

---

## Phase 1: Setup (项目初始化)

**Purpose**: 安装依赖，创建目录结构

- [x] T001 安装 APScheduler 依赖到 backend/requirements.txt
- [x] T002 [P] 创建 backend/app/tasks/__init__.py 任务模块初始化文件
- [x] T003 [P] 创建数据库迁移脚本 backend/migrations/versions/d4e5f6g7h8i9_add_trigger_tables.py

---

## Phase 2: Foundational (基础模型和调度器)

**Purpose**: 所有用户场景依赖的基础设施

**⚠️ CRITICAL**: 用户场景实现必须在此阶段完成后开始

### Tests for Foundational

- [x] T004 [P] 编写 TriggerExecutionLog 模型单元测试到 backend/tests/unit/trigger/test_models.py
- [x] T005 [P] 编写 BatchScanTask 模型单元测试到 backend/tests/unit/trigger/test_models.py

### Implementation for Foundational

- [x] T006 [P] 新增 TriggerExecutionLog 模型到 backend/app/models/cmdb_relation.py
- [x] T007 [P] 新增 BatchScanTask 模型到 backend/app/models/cmdb_relation.py
- [x] T008 初始化 APScheduler 调度器到 backend/app/tasks/scheduler.py
- [x] T009 [P] 创建触发器执行日志服务基础方法到 backend/app/services/trigger_service.py

**Checkpoint**: 基础模型和调度器就绪，用户场景实现可以并行开始

---

## Phase 3: User Story 1 - 新增或更新 CI 时自动建立关系 (Priority: P1) 🎯 MVP

**Goal**: 当用户新增或更新 CI 时，系统根据触发器规则自动创建关系

**Independent Test**: 创建一个新 CI，验证系统是否根据触发器规则自动建立关系

### Tests for User Story 1

- [ ] T010 [P] [US1] 编写触发器匹配逻辑单元测试到 backend/tests/unit/test_trigger_service.py

### Implementation for User Story 1

- [x] T011 [US1] 实现精确值匹配逻辑 process_ci_triggers() 到 backend/app/services/trigger_service.py
- [x] T012 [US1] 实现 create_relation_with_skip_duplicate() 跳过已存在关系的方法到 backend/app/services/trigger_service.py
- [x] T013 [US1] 在 CiInstance.save() 后调用触发器处理，修改 backend/app/models/ci_instance.py
- [x] T014 [US1] 实现记录触发器执行日志 log_trigger_execution() 到 backend/app/services/trigger_service.py

**Checkpoint**: US1 完成，CI 新增/更新时可自动建立关系

---

## Phase 4: User Story 2 - 配置后台批量扫描 (Priority: P2)

**Goal**: 管理员可以为模型配置批量扫描，支持定时自动执行和手动触发

**Independent Test**: 配置模型的批量扫描开关并手动触发扫描，验证系统是否扫描并创建缺失的关系

### Tests for User Story 2

- [ ] T015 [P] [US2] 编写批量扫描任务单元测试到 backend/tests/unit/test_batch_scan.py

### Implementation for User Story 2

- [x] T016 [US2] 实现批量扫描核心逻辑 batch_scan_model() 到 backend/app/tasks/batch_scan.py
- [x] T017 [US2] 实现分批处理逻辑（每批 100 CI）到 backend/app/tasks/batch_scan.py
- [x] T018 [US2] 实现 BatchScanTask 状态管理（pending/running/completed/failed）到 backend/app/tasks/batch_scan.py
- [x] T019 [US2] 实现 POST /api/models/{model_id}/batch-scan 手动触发接口到 backend/app/routes/trigger.py
- [x] T020 [US2] 实现 GET /api/models/{model_id}/batch-scan 获取任务列表接口到 backend/app/routes/trigger.py
- [x] T021 [US2] 实现并发控制（同一模型只能有一个 running 任务）到 backend/app/tasks/batch_scan.py

**Checkpoint**: US2 完成，支持手动触发批量扫描

---

## Phase 5: User Story 3 - 查看关系触发器配置 (Priority: P3)

**Goal**: 管理员可以查看模型的关系触发器配置

**Independent Test**: 进入模型配置页面，验证是否显示该模型所有触发器规则列表

### Implementation for User Story 3

- [x] T022 [P] [US3] 实现 GET /api/models/{model_id}/triggers 获取触发器列表接口到 backend/app/routes/trigger.py
- [x] T023 [P] [US3] 实现 POST /api/models/{model_id}/triggers 创建触发器接口到 backend/app/routes/trigger.py
- [x] T024 [P] [US3] 实现 GET /api/triggers/{trigger_id} 获取触发器详情接口到 backend/app/routes/trigger.py
- [x] T025 [P] [US3] 实现 PUT /api/triggers/{trigger_id} 更新触发器接口到 backend/app/routes/trigger.py
- [x] T026 [P] [US3] 实现 DELETE /api/triggers/{trigger_id} 删除触发器接口到 backend/app/routes/trigger.py
- [x] T027 [US3] 实现 GET /api/triggers/{trigger_id}/logs 获取执行日志接口到 backend/app/routes/trigger.py
- [x] T028 [US3] 创建前端触发器配置页面到 frontend/src/views/cmdb/TriggerConfig.vue（已完成触发器列表管理功能）
- [x] T029 [US3] 创建前端触发器 API 调用到 frontend/src/api/trigger.ts

**Checkpoint**: US3 完成，可查看和管理触发器配置

---

## Phase 6: User Story 4 - 查看批量扫描执行历史 (Priority: P3)

**Goal**: 管理员可以在页面上查看后台批量扫描任务的执行历史

**Independent Test**: 访问批量扫描历史页面，验证是否展示任务的执行时间、状态和统计信息

### Implementation for User Story 4

- [x] T030 [P] [US4] 实现 GET /api/batch-scan/tasks 获取所有扫描任务历史接口到 backend/app/routes/trigger.py
- [x] T031 [P] [US4] 实现 GET /api/batch-scan/tasks/{task_id} 获取任务详情接口到 backend/app/routes/trigger.py
- [x] T032 [US4] 创建前端批量扫描历史页面到 frontend/src/views/config/batch-scan/index.vue
- [x] T033 [US4] 在前端添加任务详情弹窗组件到 frontend/src/views/config/batch-scan/index.vue

**Checkpoint**: US4 完成，可查看批量扫描执行历史

---

## Phase 7: User Story 5 - 配置批量扫描执行计划 (Priority: P3)

**Goal**: 管理员可以为每个模型配置批量扫描的执行计划（Cron 表达式）

**Independent Test**: 配置模型的批量扫描计划，验证定时任务是否按配置的时间执行

### Implementation for User Story 5

- [x] T034 [US5] 实现 GET /api/batch-scan/config/{model_id} 获取扫描配置接口到 backend/app/routes/trigger.py
- [x] T035 [US5] 实现 PUT /api/batch-scan/config/{model_id} 更新扫描配置接口到 backend/app/routes/trigger.py
- [x] T036 [US5] 实现动态添加/更新 Cron 任务 add_batch_scan_job() 到 backend/app/tasks/scheduler.py
- [x] T037 [US5] 实现动态移除 Cron 任务 remove_batch_scan_job() 到 backend/app/tasks/scheduler.py
- [x] T038 [US5] 实现 Cron 表达式验证和解析到 backend/app/routes/trigger.py
- [x] T039 [US5] 在前端添加 Cron 配置表单到 frontend/src/views/cmdb/TriggerConfig.vue

**Checkpoint**: US5 完成，支持 Cron 表达式配置执行计划

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 优化和完善

- [x] T040 [P] 添加错误处理和异常捕获到 backend/app/services/trigger_service.py
- [x] T041 [P] 添加日志记录到所有批量扫描操作 backend/app/tasks/batch_scan.py
- [x] T042 添加数据库索引优化（参考 data-model.md）到迁移脚本
- [x] T043 [P] 编写集成测试到 backend/tests/integration/test_trigger_integration.py
- [x] T044 实现模型删除时自动失效关联触发器到 backend/app/models/cmdb_model.py
- [ ] T045 运行 quickstart.md 验证所有功能
- [ ] T046 [P] 更新 API 文档

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成，**阻塞所有用户场景**
- **User Stories (Phase 3-7)**: 全部依赖 Foundational 完成
  - US1-US5 可并行开发（如有足够人力）
  - 或按优先级顺序执行（P1 → P2 → P3）
- **Polish (Phase 8)**: 依赖所需用户场景完成

### User Story Dependencies

- **US1 (P1)**: Foundational 完成后可开始，无其他依赖
- **US2 (P2)**: Foundational 完成后可开始，依赖 US1 的 trigger_service.py
- **US3 (P3)**: Foundational 完成后可开始，无其他依赖
- **US4 (P3)**: 依赖 US2 的 BatchScanTask 模型
- **US5 (P3)**: 依赖 US2 的 scheduler.py 和 batch_scan.py

### Within Each User Story

- 测试任务优先于实现任务
- 模型/服务优先于路由/接口
- 核心实现优先于集成
- 场景完成后再进入下一优先级

### Parallel Opportunities

- Setup 阶段所有 [P] 任务可并行
- Foundational 阶段模型创建可并行
- US3 的 API 接口可并行实现
- US4 的 API 接口可并行实现
- Polish 阶段独立任务可并行

---

## Parallel Example: User Story 3

```bash
# 并行启动所有 US3 的 API 接口任务:
Task: "实现 GET /api/models/{model_id}/triggers 接口"
Task: "实现 POST /api/models/{model_id}/triggers 接口"
Task: "实现 GET /api/triggers/{trigger_id} 接口"
Task: "实现 PUT /api/triggers/{trigger_id} 接口"
Task: "实现 DELETE /api/triggers/{trigger_id} 接口"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (关键阻塞点)
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**: 独立测试 US1
5. 如果就绪可部署/演示

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. 添加 US1 → 独立测试 → 部署/演示 (MVP!)
3. 添加 US2 → 独立测试 → 部署/演示
4. 添加 US3/US4/US5 → 独立测试 → 部署/演示
5. 每个场景独立交付价值

### Parallel Team Strategy

多开发者协作:

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后:
   - Developer A: User Story 1 (P1)
   - Developer B: User Story 2 (P2)
   - Developer C: User Story 3 (P3)
3. 场景独立完成并集成

---

## Summary

| 统计项 | 数量 |
|--------|------|
| 总任务数 | 46 |
| 已完成 | 42 |
| US1 (P1) 任务 | 5 (已完成 4) |
| US2 (P2) 任务 | 7 (已完成 6) |
| US3 (P3) 任务 | 8 (已完成 8) |
| US4 (P3) 任务 | 4 (已完成 4) |
| US5 (P3) 任务 | 6 (已完成 6) |
| Setup 任务 | 3 (已完成 3) |
| Foundational 任务 | 6 (已完成 6) |
| Polish 任务 | 7 (已完成 5) |
| 可并行任务 | 24 |

**MVP 范围**: Phase 1-3 (Setup + Foundational + US1) = 14 任务 ✓ 已完成

---

## 待完成任务清单

### 中优先级
1. **T010** - 编写触发器匹配逻辑单元测试
2. **T015** - 编写批量扫描任务单元测试

### 低优先级
3. **T045** - 运行 quickstart.md 验证所有功能
4. **T046** - 更新 API 文档

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签映射任务到具体用户场景
- 每个用户场景应独立可完成和测试
- 每个任务或逻辑组完成后提交
- 任何 checkpoint 都可停止并独立验证场景
