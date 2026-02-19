# 任务分解与开发计划：站内通知模块

**功能**: 004-notification-module  
**分支**: `004-notification-module`  
**创建日期**: 2026-02-19  
**技术栈**: Python 3.11, Flask 3.0.0, SQLAlchemy 2.0.36, Vue 3 + TypeScript  
**数据库**: SQLite (开发) / PostgreSQL (生产)

---

## 依赖关系图

```
Phase 1: 项目初始化
    │
    ▼
Phase 2: 基础架构
    │
    ├──► Phase 3: US1 个人通知接收 (P1) [可独立测试]
    │       │
    │       └── 依赖: 基础模型、WebSocket连接
    │
    ├──► Phase 4: US2 部门级通知 (P1) [可独立测试]
    │       │
    │       └── 依赖: US1完成
    │
    ├──► Phase 5: US3 通知类型管理 (P2) [可独立测试]
    │       │
    │       └── 依赖: US1完成
    │
    ├──► Phase 6: US4 历史与搜索 (P2) [可独立测试]
    │       │
    │       └── 依赖: US1完成
    │
    └──► Phase 7: US5 已读/未读管理 (P3) [可独立测试]
            │
            └── 依赖: US1完成
```

**MVP范围**: Phase 1-3 (仅US1 - 个人通知接收)

---

## Phase 1: 项目初始化

**目标**: 建立通知模块的项目结构和开发环境

**独立测试**: 验证项目可以正常启动，无导入错误

- [ ] T001 创建通知模块目录结构
      在 `backend/src/` 下创建 `notifications/` 目录及子目录
      文件: `backend/src/notifications/__init__.py`

- [ ] T002 [P] 添加Flask-SocketIO依赖
      更新 `backend/requirements.txt` 添加 flask-socketio>=5.0.0
      文件: `backend/requirements.txt`

- [ ] T003 [P] 添加Markdown处理依赖
      更新 `backend/requirements.txt` 添加 markdown>=3.0.0, bleach>=6.0.0
      文件: `backend/requirements.txt`

- [ ] T004 [P] 创建前端通知组件目录
      在 `frontend/src/` 下创建 `components/notifications/` 目录
      文件: `frontend/src/components/notifications/.gitkeep`

- [ ] T005 创建模块初始化文件
      创建通知模块的Flask扩展初始化代码
      文件: `backend/src/notifications/__init__.py`

- [ ] T006 配置WebSocket CORS
      在Flask应用配置中添加SocketIO CORS设置
      文件: `backend/src/config.py`

---

## Phase 2: 基础架构 (阻塞性依赖)

**目标**: 建立所有用户故事共享的基础组件

**独立测试**: 验证数据库迁移成功，模型可以正常CRUD

### 2.1 数据库模型基础

- [ ] T007 创建NotificationType模型
      实现通知类型实体，包含name, description, icon, color字段
      文件: `backend/src/notifications/models.py`
      依赖: SQLAlchemy Base, UUID主键

- [ ] T008 [P] 创建Notification模型
      实现核心通知实体，包含title, content, content_html, sender等字段
      文件: `backend/src/notifications/models.py`
      依赖: T007

- [ ] T009 [P] 创建NotificationRecipient模型
      实现收件人联结表，包含is_read, read_at, delivery_status等字段
      文件: `backend/src/notifications/models.py`
      依赖: T008

- [ ] T010 创建数据库迁移脚本
      生成Alembic迁移文件，包含所有表和索引
      命令: `flask db migrate -m "create notification tables"`
      文件: `backend/migrations/versions/xxx_create_notification_tables.py`

- [ ] T011 运行数据库迁移
      执行迁移创建数据库表
      命令: `flask db upgrade`

### 2.2 工具与辅助函数

- [ ] T012 [P] 实现Markdown渲染工具
      创建markdown转HTML并净化的工具函数
      文件: `backend/src/notifications/utils.py`
      函数: `render_markdown(content: str) -> str`

- [ ] T013 [P] 实现日期时间工具
      创建时间格式化和解析工具函数
      文件: `backend/src/notifications/utils.py`

### 2.3 WebSocket基础架构

- [ ] T014 创建WebSocket连接管理器
      实现SocketIO连接认证和房间管理
      文件: `backend/src/notifications/websocket.py`
      功能: 用户认证、房间加入(user:{id}, dept:{id})

- [ ] T015 [P] 实现通知广播函数
      创建向特定用户或部门广播通知的工具函数
      文件: `backend/src/notifications/websocket.py`
      函数: `emit_to_user(user_id, event, data)`, `emit_to_department(dept_id, event, data)`

---

## Phase 3: US1 个人通知接收 (P1 - MVP)

**用户故事**: 作为平台用户，我希望收到与我角色和活动相关的通知

**独立测试标准**:
1. 可以向特定用户发送通知
2. 用户登录后能看到通知角标
3. 用户能在通知中心查看通知内容
4. 已读/未读状态正确显示
5. 点击通知后标记为已读

**模型依赖**: Notification, NotificationRecipient, NotificationType

### 3.1 后端API实现

- [ ] T016 [P] 实现发送通知API端点
      创建POST /api/v1/notifications端点，支持发送到指定用户
      文件: `backend/src/notifications/api.py`
      端点: `POST /notifications`
      请求体: `{recipient_type: "users", user_ids: [...], type_id, title, content}`

- [ ] T017 [P] 实现获取我的通知API
      创建GET /api/v1/notifications/my端点
      文件: `backend/src/notifications/api.py`
      端点: `GET /notifications/my`
      返回: 当前用户的通知列表，包含is_read状态

- [ ] T018 [P] 实现标记已读API
      创建PATCH /api/v1/notifications/my/{id}/read端点
      文件: `backend/src/notifications/api.py`
      端点: `PATCH /notifications/my/{id}/read`

- [ ] T019 实现获取未读数量API
      创建GET /api/v1/notifications/my/unread-count端点
      文件: `backend/src/notifications/api.py`
      端点: `GET /notifications/my/unread-count`

### 3.2 业务服务层

- [ ] T020 [P] 实现NotificationService.send_to_users方法
      处理向多个用户发送通知的业务逻辑
      文件: `backend/src/notifications/services.py`
      方法: `send_to_users(sender_id, user_ids, type_id, title, content)`
      功能: 创建Notification记录，创建Recipient记录，触发WebSocket事件

- [ ] T021 [P] 实现NotificationService.get_user_notifications方法
      获取指定用户的通知列表
      文件: `backend/src/notifications/services.py`
      方法: `get_user_notifications(user_id, filters={})`
      返回: 分页的通知列表

- [ ] T022 [P] 实现NotificationService.mark_as_read方法
      标记通知为已读
      文件: `backend/src/notifications/services.py`
      方法: `mark_as_read(recipient_id, user_id)`
      功能: 验证权限，更新is_read和read_at，触发WebSocket同步事件

### 3.3 WebSocket实时推送

- [ ] T023 [P] 实现notification:new事件推送
      当用户收到新通知时通过WebSocket推送
      文件: `backend/src/notifications/websocket.py`
      事件: `notification:new`
      数据: {id, title, content, content_html, type, sender, created_at}

- [ ] T024 实现notification:read事件同步
      当通知标记为已读时同步到其他客户端
      文件: `backend/src/notifications/websocket.py`
      事件: `notification:read`

### 3.4 前端组件

- [ ] T025 [P] 创建NotificationBadge组件
      显示未读通知数量的角标组件
      文件: `frontend/src/components/notifications/NotificationBadge.vue`
      功能: 显示数字角标，实时更新

- [ ] T026 [P] 创建NotificationItem组件
      单个通知项展示组件
      文件: `frontend/src/components/notifications/NotificationItem.vue`
      功能: 显示标题、内容、发送者、时间，已读/未读样式区分

- [ ] T027 [P] 创建NotificationList组件
      通知列表组件
      文件: `frontend/src/components/notifications/NotificationList.vue`
      功能: 列表展示，下拉刷新，加载更多

- [ ] T028 创建NotificationCenter组件
      通知中心容器组件（下拉面板/抽屉）
      文件: `frontend/src/components/notifications/NotificationCenter.vue`
      功能: 包含列表、标记已读按钮、空状态

### 3.5 前端状态管理

- [ ] T029 [P] 创建通知API服务
      封装通知相关的HTTP API调用
      文件: `frontend/src/services/notifications.ts`
      方法: `getMyNotifications()`, `markAsRead(id)`, `getUnreadCount()`, `sendNotification(data)`

- [ ] T030 [P] 创建通知Pinia Store
      管理通知状态和WebSocket连接
      文件: `frontend/src/stores/notifications.ts`
      状态: notifications[], unreadCount, isConnected
      动作: fetchNotifications(), markAsRead(), connectWebSocket()

- [ ] T031 集成WebSocket客户端
      在前端建立SocketIO连接并处理事件
      文件: `frontend/src/stores/notifications.ts`
      事件处理: notification:new, notification:read

---

## Phase 4: US2 部门级通知 (P1)

**用户故事**: 作为部门经理，我希望向部门所有成员发送通知

**独立测试标准**:
1. 可以向部门发送通知
2. 部门所有成员都收到通知
3. 新加入部门的成员不会收到历史通知
4. 属于多个部门的用户不会收到重复通知

**依赖**: US1完成

### 4.1 后端服务扩展

- [ ] T032 [P] 扩展NotificationService.send_to_department方法
      支持向部门所有成员发送通知
      文件: `backend/src/notifications/services.py`
      方法: `send_to_department(sender_id, department_id, type_id, title, content)`
      功能: 查询部门成员，批量创建Recipient记录

- [ ] T033 [P] 实现部门成员查询服务
      创建获取部门活跃成员的辅助方法
      文件: `backend/src/notifications/services.py`
      方法: `get_department_members(department_id) -> List[user_id]`

- [ ] T034 [P] 实现部门广播WebSocket事件
      向部门房间广播通知
      文件: `backend/src/notifications/websocket.py`
      函数: `emit_to_department(department_id, event, data)`

### 4.2 API扩展

- [ ] T035 扩展发送通知API支持部门
      修改POST /api/v1/notifications端点支持department类型
      文件: `backend/src/notifications/api.py`
      新增请求体: `{recipient_type: "department", department_id, type_id, title, content}`

### 4.3 前端扩展

- [ ] T036 [P] 扩展发送通知界面支持部门选择
      在通知发送表单中添加部门选择器
      文件: `frontend/src/components/notifications/NotificationSender.vue` (新建)
      功能: 用户选择/部门选择切换，部门下拉列表

---

## Phase 5: US3 通知类型管理 (P2)

**用户故事**: 作为系统管理员，我希望定义和管理不同的通知类型

**独立测试标准**:
1. 可以创建通知类型
2. 可以编辑通知类型
3. 可以删除非系统类型
4. 通知类型有图标和颜色区分

**依赖**: US1完成（通知类型已在US1中创建）

### 5.1 后端API

- [ ] T037 [P] 实现通知类型CRUD API
      创建通知类型的增删改查端点
      文件: `backend/src/notifications/api.py`
      端点: 
      - `GET /notification-types`
      - `POST /notification-types` (管理员权限)
      - `GET /notification-types/{id}`
      - `PATCH /notification-types/{id}` (管理员权限)
      - `DELETE /notification-types/{id}` (管理员权限，不能删除系统类型)

### 5.2 业务逻辑

- [ ] T038 [P] 实现NotificationTypeService
      创建通知类型管理服务
      文件: `backend/src/notifications/services.py`
      方法: `create_type()`, `update_type()`, `delete_type()`, `get_types()`
      验证: 系统类型不能删除

### 5.3 前端管理界面

- [ ] T039 [P] 创建通知类型列表组件
      管理员界面展示所有通知类型
      文件: `frontend/src/views/notifications/NotificationTypeList.vue`
      功能: 表格展示，创建/编辑/删除按钮

- [ ] T040 [P] 创建通知类型编辑表单
      通知类型的创建和编辑表单
      文件: `frontend/src/components/notifications/NotificationTypeForm.vue`
      字段: name, description, icon, color

---

## Phase 6: US4 历史查询与搜索 (P2)

**用户故事**: 作为平台用户，我希望访问和搜索历史通知

**独立测试标准**:
1. 可以查看90天内的历史通知
2. 可以按关键词搜索
3. 可以按日期范围、类型、已读状态筛选
4. 搜索结果响应时间<2秒

**依赖**: US1完成

### 6.1 后端搜索功能

- [ ] T041 [P] 实现通知搜索服务
      创建支持多条件的通知搜索方法
      文件: `backend/src/notifications/services.py`
      方法: `search_notifications(user_id, query, filters={date_from, date_to, type_id, is_read})`
      功能: 全文搜索(title, content)，组合筛选

- [ ] T042 [P] 实现搜索API端点
      创建搜索端点
      文件: `backend/src/notifications/api.py`
      端点: `GET /notifications/my/search?q={query}&date_from=...&date_to=...&type_id=...&is_read=...`

- [ ] T043 [P] 添加搜索索引
      为notifications表的title和content字段添加全文搜索索引
      数据库: PostgreSQL使用tsvector，SQLite使用LIKE优化
      文件: `backend/migrations/versions/xxx_add_search_indexes.py`

### 6.2 前端搜索界面

- [ ] T044 [P] 创建搜索筛选组件
      通知搜索和筛选UI
      文件: `frontend/src/components/notifications/NotificationSearch.vue`
      功能: 搜索框，日期范围选择器，类型筛选下拉，已读状态筛选

- [ ] T045 [P] 扩展通知列表支持搜索
      修改NotificationList组件支持搜索和筛选
      文件: `frontend/src/components/notifications/NotificationList.vue`
      功能: 显示搜索结果，无结果状态，清除筛选

---

## Phase 7: US5 已读/未读状态管理 (P3)

**用户故事**: 作为平台用户，我希望手动控制已读/未读状态

**独立测试标准**:
1. 可以将已读通知标记为未读
2. 可以批量标记所有通知为已读
3. 批量操作应用到所有选中项

**依赖**: US1完成

### 7.1 后端批量操作

- [ ] T046 [P] 实现标记未读API
      创建标记通知为未读的端点
      文件: `backend/src/notifications/api.py`
      端点: `PATCH /notifications/my/{id}/unread`

- [ ] T047 [P] 实现全部标记已读API
      创建批量标记所有通知为已读的端点
      文件: `backend/src/notifications/api.py`
      端点: `PATCH /notifications/my/read-all`
      返回: {marked_count: number}

- [ ] T048 [P] 实现批量操作服务方法
      添加批量状态管理方法
      文件: `backend/src/notifications/services.py`
      方法: `mark_as_unread()`, `mark_all_as_read()`

### 7.2 WebSocket同步

- [ ] T049 [P] 实现notification:unread事件
      通知标记为未读时同步
      文件: `backend/src/notifications/websocket.py`
      事件: `notification:unread`

- [ ] T050 [P] 实现notifications:read_all事件
      全部标记已读时广播
      文件: `backend/src/notifications/websocket.py`
      事件: `notifications:read_all`

### 7.3 前端批量操作

- [ ] T051 [P] 添加标记未读功能
      在NotificationItem组件添加标记未读按钮
      文件: `frontend/src/components/notifications/NotificationItem.vue`
      功能: 更多菜单 -> 标记为未读

- [ ] T052 [P] 添加全部已读按钮
      在NotificationCenter组件添加"全部标记为已读"按钮
      文件: `frontend/src/components/notifications/NotificationCenter.vue`
      功能: 一键清除所有未读

- [ ] T053 [P] 实现批量选择功能
      添加通知批量选择功能
      文件: `frontend/src/components/notifications/NotificationList.vue`
      功能: 复选框选择，批量操作栏

---

## Phase 8: 完善与跨功能事项

**目标**: 完善功能，处理边界情况，性能优化

### 8.1 后台任务

- [ ] T054 [P] 实现过期通知清理任务
      使用APScheduler每天清理过期通知
      文件: `backend/src/notifications/tasks.py`
      功能: 删除超过90天的通知

- [ ] T055 [P] 实现失败投递重试任务
      定期重试投递失败的通知
      文件: `backend/src/notifications/tasks.py`
      功能: 指数退避重试，最多3次

### 8.2 审计日志

- [ ] T056 [P] 实现通知发送审计日志
      记录所有通知发送事件
      文件: `backend/src/notifications/services.py`
      记录: sender, recipients, timestamp, content_hash

### 8.3 性能优化

- [ ] T057 [P] 实现通知列表分页优化
      使用游标分页或键集分页处理大量通知
      文件: `backend/src/notifications/services.py`
      优化: 避免OFFSET在大数据量时性能下降

- [ ] T058 [P] 实现未读数缓存
      使用Redis缓存用户未读数
      文件: `backend/src/notifications/services.py`
      功能: 缓存未读数，WebSocket更新时失效

### 8.4 测试完善

- [ ] T059 [P] 编写单元测试 - 服务层
      测试所有Service方法
      文件: `backend/tests/unit/notifications/test_services.py`
      覆盖: send_to_users, mark_as_read, search_notifications

- [ ] T060 [P] 编写单元测试 - API层
      测试所有API端点
      文件: `backend/tests/unit/notifications/test_api.py`
      覆盖: 所有HTTP端点，权限验证

- [ ] T061 [P] 编写集成测试
      测试完整用户流程
      文件: `backend/tests/integration/notifications/test_flows.py`
      覆盖: 发送->接收->已读完整流程

- [ ] T062 [P] 编写WebSocket测试
      测试WebSocket事件
      文件: `backend/tests/integration/notifications/test_websocket.py`
      覆盖: 连接、认证、事件接收

### 8.5 文档与示例

- [ ] T063 [P] 创建API使用示例
      编写curl和JavaScript示例
      文件: `specs/004-notification-module/examples/` (新建目录)

- [ ] T064 [P] 更新README文档
      添加通知模块使用说明
      文件: `backend/src/notifications/README.md`

---

## 并行执行示例

### US1 个人通知接收 并行任务组

**组A - 后端核心 (无依赖)**:
- T016 发送通知API
- T017 获取我的通知API
- T020 发送服务方法
- T021 获取服务方法

**组B - WebSocket (依赖组A)**:
- T023 新通知推送
- T024 已读状态同步

**组C - 前端核心 (无依赖)**:
- T025 角标组件
- T026 通知项组件
- T029 API服务

**组D - 前端集成 (依赖组C)**:
- T027 列表组件
- T028 通知中心组件
- T030 Pinia Store

### 跨用户故事并行

当US1完成后，以下用户故事可以并行开发:
- US2 部门级通知 (T032-T036)
- US3 通知类型管理 (T037-T040)
- US4 历史与搜索 (T041-T045)
- US5 已读/未读管理 (T046-T053)

---

## 实施策略

### MVP优先 (Phase 1-3)

**MVP范围**: 仅实现US1 (个人通知接收)

**交付物**:
- ✅ 可以向用户发送通知
- ✅ 用户可以看到未读角标
- ✅ 用户可以在通知中心查看通知
- ✅ 用户可以标记通知为已读
- ✅ 支持实时WebSocket推送

**MVP价值**: 满足核心需求，后续功能可以增量添加

### 增量交付计划

| 阶段 | 用户故事 | 预计工期 | 价值 |
|------|---------|---------|------|
| Sprint 1 | Phase 1-2 (基础) | 2天 | 基础设施 |
| Sprint 2 | US1 (MVP) | 5天 | **核心功能可用** |
| Sprint 3 | US2 (部门) | 3天 | 群组通知能力 |
| Sprint 4 | US3 (类型) | 3天 | 分类管理能力 |
| Sprint 5 | US4 (搜索) | 4天 | 历史查询能力 |
| Sprint 6 | US5 (状态) | 2天 | 状态管理能力 |
| Sprint 7 | Phase 8 (完善) | 3天 | 生产就绪 |

**总计**: 约22天 (4-5周，含缓冲)

### 风险缓解

1. **WebSocket可靠性**: 实现HTTP轮询作为降级方案
2. **大数据量性能**: 早期实现分页，避免后期重构
3. **权限复杂性**: 延迟到US2-US3实现复杂RBAC，US1使用简单权限检查

---

## 测试策略

### 单元测试覆盖目标

- 服务层: ≥ 80% 覆盖率
- API层: ≥ 80% 覆盖率
- 模型层: ≥ 70% 覆盖率

### 集成测试场景

1. **端到端流程**: 发送 -> WebSocket推送 -> 前端显示 -> 标记已读
2. **高并发**: 1000个用户同时接收部门通知
3. **边界情况**: 用户删除、部门删除、过期清理
4. **故障恢复**: WebSocket断开重连、投递失败重试

### 手动测试清单

**US1 个人通知**:
- [ ] 向单个用户发送通知
- [ ] 向多个用户发送通知
- [ ] 未读角标实时更新
- [ ] 通知中心显示正确
- [ ] 标记已读后角标减少
- [ ] 多标签页状态同步

**US2 部门通知**:
- [ ] 向部门发送通知
- [ ] 所有成员收到通知
- [ ] 新成员不会收到历史通知

**US3 类型管理**:
- [ ] 创建新类型
- [ ] 编辑类型图标和颜色
- [ ] 删除非系统类型
- [ ] 系统类型不能被删除

**US4 历史搜索**:
- [ ] 查看90天内历史
- [ ] 关键词搜索
- [ ] 组合筛选

**US5 状态管理**:
- [ ] 标记单个通知未读
- [ ] 全部标记已读
- [ ] 批量选择操作

---

## 成功标准验证

根据规格说明中的成功标准(SC-001至SC-010):

- [ ] SC-001: 5秒内实时投递 (WebSocket优化)
- [ ] SC-002: 99.9%投递成功率 (重试机制)
- [ ] SC-003: 90天历史保留 (清理任务)
- [ ] SC-004: 1000并发支持 (测试验证)
- [ ] SC-005: 95%搜索成功率 (搜索优化)
- [ ] SC-006: 未读数准确率<1%误差 (测试验证)
- [ ] SC-007: 2秒内查询返回 (索引优化)
- [ ] SC-008: 5分钟创建类型 (UX设计)
- [ ] SC-009: 500ms反馈延迟 (前端优化)
- [ ] SC-010: 100%审计覆盖 (审计日志)

---

**生成日期**: 2026-02-19  
**任务总数**: 64个任务  
**并行机会**: 每用户故事内部4-5组可并行任务  
**MVP任务数**: 31个任务 (Phase 1-3)
