# 通知模块

## 概述

通知模块是 Arco CMDB 平台的实时消息推送系统，支持多种接收者类型、权限控制和WebSocket实时推送。

## 功能特性

- ✅ **多种接收者类型**: 指定用户、部门、全员广播
- ✅ **实时推送**: WebSocket实时通知
- ✅ **权限控制**: 基于角色的细粒度权限
- ✅ **通知类型**: 可配置的通知分类
- ✅ **模板支持**: 支持变量替换的模板系统
- ✅ **已读/未读**: 完整的状态管理
- ✅ **搜索筛选**: 多维度搜索和筛选
- ✅ **后台任务**: 自动清理、重试、归档
- ✅ **Markdown支持**: 富文本内容格式

## 项目结构

```
backend/app/notifications/
├── __init__.py          # 模块初始化
├── models.py            # 数据模型
├── services.py          # 业务逻辑
├── api.py               # REST API
├── websocket.py         # WebSocket处理器
├── permissions.py       # 权限控制
├── tasks.py             # 后台定时任务
├── utils.py             # 工具函数
└── README.md            # 本文件
```

## 数据模型

### NotificationType (通知类型)
- 定义通知的分类（系统、告警、消息等）
- 支持自定义图标和颜色
- 支持系统类型保护

### Notification (通知实体)
- 存储通知的基本信息
- 支持Markdown内容和HTML渲染
- 支持过期时间和归档状态

### NotificationRecipient (接收者状态)
- 记录用户的通知接收状态
- 追踪已读/未读状态
- 记录推送状态（pending/delivered/failed）

### NotificationTemplate (通知模板)
- 支持变量替换的模板系统
- 提高通知发送效率

## 权限控制

| 角色 | 发送给用户 | 发送给部门 | 全员广播 | 管理类型 |
|------|-----------|-----------|---------|---------|
| 管理员 | ✅ 任何人 | ✅ 任何部门 | ✅ | ✅ |
| 部门经理 | ✅ 本部门 | ✅ 本部门 | ❌ | ❌ |
| 普通用户 | ❌ | ❌ | ❌ | ❌ |

## API 端点

### 用户通知
- `GET /api/v1/notifications/my` - 获取我的通知
- `GET /api/v1/notifications/my/unread-count` - 未读数量
- `PATCH /api/v1/notifications/my/{id}/read` - 标记已读
- `PATCH /api/v1/notifications/my/{id}/unread` - 标记未读
- `PATCH /api/v1/notifications/my/read-all` - 全部已读
- `GET /api/v1/notifications/my/search` - 搜索通知

### 通知发送
- `POST /api/v1/notifications` - 发送通知
- `POST /api/v1/notifications/broadcast` - 全员广播

### 类型管理
- `GET /api/v1/notifications/types` - 获取类型列表
- `POST /api/v1/notifications/types` - 创建类型
- `PATCH /api/v1/notifications/types/{id}` - 更新类型
- `DELETE /api/v1/notifications/types/{id}` - 删除类型

## WebSocket 事件

### 客户端接收
- `authenticated` - 认证成功
- `auth_error` - 认证失败
- `notification:new` - 新通知
- `notification:read` - 通知已读
- `notification:unread` - 通知未读
- `notification:read_all` - 全部已读

## 后台定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| cleanup_expired_notifications | 每天凌晨2点 | 清理过期通知 |
| retry_failed_deliveries | 每小时 | 重试失败推送 |
| generate_notification_stats | 每天凌晨1点 | 生成统计报告 |
| archive_old_notifications | 每周日凌晨 | 归档旧通知 |

## 配置项

```python
# 通知保留天数（默认90天）
NOTIFICATION_RETENTION_DAYS = 90

# 最大通知列表页大小
PAGE_MAX_SIZE = 100

# WebSocket CORS配置
SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
```

## 使用示例

### 发送通知给用户

```python
from app.notifications.services import NotificationService

notification, recipients = NotificationService.send_to_users(
    sender_id=1,
    user_ids=[2, 3, 4],
    type_id=1,
    title="系统通知",
    content="系统将于今晚维护"
)
```

### 发送部门通知

```python
notification, recipients = NotificationService.send_to_department(
    sender_id=1,
    department_id=1,
    type_id=1,
    title="部门通知",
    content="明天有部门会议"
)
```

### 发送全员广播

```python
notification, recipients = NotificationService.send_broadcast(
    sender_id=1,
    type_id=1,
    title="全员公告",
    content="公司年会通知"
)
```

## 前端集成

### 通知角标

```vue
<NotificationBadge
  :unread-count="unreadCount"
  @click="showNotificationCenter"
/>
```

### 通知中心

```vue
<NotificationCenter
  v-model:visible="visible"
  @click="handleNotificationClick"
/>
```

### WebSocket连接

```typescript
const store = useNotificationStore();
store.connectWebSocket(token);
```

## 测试

```bash
# 运行单元测试
cd backend
pytest tests/unit/notifications/ -v

# 运行覆盖率测试
pytest tests/unit/notifications/ --cov=app.notifications --cov-report=html
```

## 数据库迁移

```bash
# 应用迁移
flask db upgrade

# 创建新迁移（修改模型后）
flask db migrate -m "添加通知模块索引"
```

## 文档

- [API文档](../../docs/notifications/api.md)
- [WebSocket文档](../../docs/notifications/websocket.md)
- [开发计划](../../specs/004-notification-module/development-plan.md)

## 性能优化

1. **数据库索引**: 已添加复合索引优化查询
2. **WebSocket房间**: 使用房间机制减少广播
3. **批量操作**: 批量标记已读减少请求
4. **分页加载**: 通知列表分页展示

## 安全考虑

1. **XSS防护**: Markdown内容HTML净化
2. **权限验证**: 每次发送都验证权限
3. **Token验证**: WebSocket连接需要有效Token
4. **数据隔离**: 用户只能访问自己的通知

## 维护说明

1. 定期检查定时任务执行日志
2. 监控WebSocket连接数和消息推送成功率
3. 关注通知表数据量，及时归档旧数据
4. 根据使用情况调整保留天数配置
