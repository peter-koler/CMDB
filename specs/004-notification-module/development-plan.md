# 通知模块开发计划

**目标**: 完成通知模块剩余功能开发，达到生产可用状态
**预计工期**: 5-7 个工作日
**分支**: `004-notification-module-dev`

---

## 当前状态

- ✅ 后端API核心功能 (85%)
- ✅ WebSocket实时推送 (80%)
- ❌ 前端组件 (0%)
- ⚠️ 权限控制细化 (60%)
- ❌ 后台定时任务 (0%)

---

## Phase 1: 前端基础组件开发 (Day 1-2)

### 1.1 API客户端层

**文件**: `frontend/src/api/notifications.ts`

```typescript
// 需要实现的API函数:
- getNotifications(params) - 获取通知列表
- getUnreadCount() - 获取未读数量
- markAsRead(recipientId) - 标记已读
- markAsUnread(recipientId) - 标记未读
- markAllAsRead() - 全部标记已读
- searchNotifications(params) - 搜索通知
- getNotificationTypes() - 获取通知类型
- sendNotification(data) - 发送通知（管理员）
```

### 1.2 Pinia状态管理

**文件**: `frontend/src/stores/notifications.ts`

```typescript
// Store功能:
- notifications: 通知列表
- unreadCount: 未读数量
- loading: 加载状态
- fetchNotifications() - 获取通知
- fetchUnreadCount() - 获取未读数
- markAsRead() - 标记已读
- markAllAsRead() - 全部已读
- connectWebSocket() - WebSocket连接
- handleNewNotification() - 处理新通知
```

### 1.3 基础UI组件

**文件**: 
- `frontend/src/components/notifications/NotificationBadge.vue` - 通知角标
- `frontend/src/components/notifications/NotificationItem.vue` - 通知项
- `frontend/src/components/notifications/NotificationList.vue` - 通知列表

**功能**:
- 通知角标显示未读数量
- 通知项显示标题、内容、时间、类型图标
- 已读/未读状态视觉区分
- 点击标记已读
- 支持Markdown内容渲染

---

## Phase 2: 前端通知中心页面 (Day 3-4)

### 2.1 通知中心组件

**文件**: `frontend/src/components/notifications/NotificationCenter.vue`

**功能**:
- 弹出式通知中心面板
- 标签页：全部 / 未读
- 顶部显示未读数量
- 底部操作栏：全部已读、查看全部
- 空状态提示
- 加载更多（分页）

### 2.2 通知管理页面

**文件**: `frontend/src/views/notifications/index.vue`

**功能**:
- 完整通知列表页面
- 高级筛选：类型、日期范围、已读状态
- 搜索功能
- 批量操作：标记已读/未读
- 分页显示

### 2.3 发送通知页面（管理员）

**文件**: `frontend/src/views/notifications/send.vue`

**功能**:
- 选择接收者类型：用户/部门
- 用户选择器（多选）
- 部门选择器
- 通知类型选择
- 标题输入
- 内容编辑器（Markdown）
- 预览功能
- 发送按钮

### 2.4 布局集成

**文件**: `frontend/src/layouts/BasicLayout.vue`

**修改**:
- 在顶部导航栏添加通知角标
- 点击角标打开通知中心
- WebSocket连接初始化

---

## Phase 3: 后端功能完善 (Day 5)

### 3.1 权限控制细化

**文件**: `backend/app/notifications/permissions.py` (新建)

```python
# 权限检查函数:
- can_send_to_user(sender, target_user) - 检查是否可以发送给指定用户
- can_send_to_department(sender, department) - 检查是否可以发送给部门
- can_send_broadcast(sender) - 检查是否可以发送全员广播
- validate_department_manager_scope(sender, department) - 验证部门经理权限范围
```

**修改**: `backend/app/notifications/services.py`
- 在send_to_users/send_to_department中添加权限检查
- 部门经理只能发送给自己管理的部门

### 3.2 广播通知功能

**文件**: `backend/app/notifications/services.py`

```python
# 新增方法:
- send_broadcast(sender_id, type_id, title, content) - 发送全员广播
```

**文件**: `backend/app/notifications/api.py`

```python
# 新增端点:
- POST /api/v1/notifications/broadcast - 发送广播通知
```

### 3.3 后台定时任务

**文件**: `backend/app/notifications/tasks.py` (新建)

```python
# 定时任务:
- cleanup_expired_notifications() - 清理过期通知（每天运行）
- retry_failed_deliveries() - 重试失败推送（每小时运行）
- generate_notification_stats() - 生成统计报告（每天运行）
```

**文件**: `backend/app/__init__.py` 或 `backend/app/extensions.py`
- 集成APScheduler
- 注册定时任务

### 3.4 审计日志完善

**文件**: `backend/app/notifications/utils.py`

```python
# 新增:
- log_notification_send(notification, recipients) - 记录发送日志
- log_notification_read(recipient) - 记录阅读日志
- log_notification_delete(notification) - 记录删除日志
```

---

## Phase 4: 集成测试与优化 (Day 6-7)

### 4.1 单元测试

**文件**:
- `backend/tests/unit/notifications/test_models.py`
- `backend/tests/unit/notifications/test_services.py`
- `backend/tests/unit/notifications/test_api.py`

**覆盖率目标**: >80%

### 4.2 集成测试

**文件**: `backend/tests/integration/notifications/test_websocket.py`

**测试场景**:
- WebSocket连接认证
- 实时通知接收
- 多端同时在线
- 断线重连

### 4.3 前端测试

**文件**:
- `frontend/src/components/notifications/__tests__/NotificationBadge.spec.ts`
- `frontend/src/components/notifications/__tests__/NotificationItem.spec.ts`
- `frontend/src/stores/__tests__/notifications.spec.ts`

### 4.4 性能优化

**后端**:
- 添加数据库索引优化查询
- 实现通知列表缓存
- WebSocket连接池优化

**前端**:
- 虚拟滚动优化长列表
- 图片懒加载
- 防抖处理搜索输入

### 4.5 文档完善

**文件**:
- `docs/notifications/api.md` - API文档
- `docs/notifications/websocket.md` - WebSocket文档
- `docs/notifications/frontend.md` - 前端组件文档

---

## 文件清单

### 新建文件

```
frontend/src/
├── api/notifications.ts
├── stores/notifications.ts
├── components/notifications/
│   ├── NotificationBadge.vue
│   ├── NotificationItem.vue
│   ├── NotificationList.vue
│   └── NotificationCenter.vue
├── views/notifications/
│   ├── index.vue
│   └── send.vue
└── composables/useNotifications.ts (可选)

backend/app/notifications/
├── permissions.py (新建)
├── tasks.py (新建)
└── README.md (新建)

backend/tests/
├── unit/notifications/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
└── integration/notifications/
    └── test_websocket.py

docs/notifications/
├── api.md
├── websocket.md
└── frontend.md
```

### 修改文件

```
frontend/src/
├── layouts/BasicLayout.vue (添加通知角标)
└── router/index.ts (添加通知路由)

backend/app/notifications/
├── services.py (添加权限检查、广播功能)
└── api.py (添加广播端点)

backend/app/
├── __init__.py 或 extensions.py (添加定时任务)
└── app.py (注册WebSocket)
```

---

## 验收标准

### 功能验收

- [ ] 用户可以接收实时通知
- [ ] 用户可以查看通知列表（全部/未读）
- [ ] 用户可以标记通知已读/未读
- [ ] 用户可以搜索历史通知
- [ ] 管理员可以发送通知给用户
- [ ] 管理员可以发送通知给部门
- [ ] 管理员可以发送全员广播
- [ ] 部门经理只能发送给自己部门
- [ ] 通知类型可配置（图标、颜色）
- [ ] 支持Markdown内容格式

### 性能验收

- [ ] 通知列表加载 < 500ms
- [ ] 实时通知延迟 < 5s
- [ ] 支持1000+并发用户
- [ ] 支持1000+人部门广播

### 安全验收

- [ ] RBAC权限控制生效
- [ ] 部门经理权限限制生效
- [ ] 审计日志记录完整
- [ ] XSS防护（Markdown净化）

---

## 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| WebSocket连接不稳定 | 中 | 高 | 实现自动重连机制，降级到轮询 |
| 大数据量通知列表卡顿 | 中 | 中 | 实现虚拟滚动，分页加载 |
| 权限逻辑复杂 | 低 | 中 | 详细测试用例，代码审查 |
| 前端组件兼容性 | 低 | 低 | 使用Ant Design Vue组件 |

---

## 下一步行动

1. 创建开发分支 `004-notification-module-dev`
2. 按Phase 1开始开发前端API和组件
3. 每日同步进度，及时调整计划
