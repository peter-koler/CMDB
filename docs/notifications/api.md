# 通知模块 API 文档

## 基础信息

- **Base URL**: `/api/v1/notifications`
- **认证方式**: JWT Token (Bearer)

## 用户通知接口

### 获取我的通知列表

```http
GET /api/v1/notifications/my
```

**Query Parameters**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_read | boolean | 否 | 筛选已读/未读 |
| type_id | integer | 否 | 通知类型ID |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |

**Response**:

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "notification_id": 100,
        "title": "系统通知",
        "content": "系统维护通知",
        "content_html": "<p>系统维护通知</p>",
        "type": {
          "id": 1,
          "name": "系统",
          "icon": "setting",
          "color": "#1890ff"
        },
        "sender": {
          "id": 1,
          "username": "admin"
        },
        "is_read": false,
        "read_at": null,
        "created_at": "2026-02-19T10:00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

### 获取未读通知数量

```http
GET /api/v1/notifications/my/unread-count
```

**Response**:

```json
{
  "code": 200,
  "data": {
    "count": 5
  }
}
```

### 标记通知为已读

```http
PATCH /api/v1/notifications/my/{recipient_id}/read
```

**Response**:

```json
{
  "code": 200,
  "message": "已标记为已读",
  "data": {
    "id": 1,
    "is_read": true,
    "read_at": "2026-02-19T10:30:00"
  }
}
```

### 标记通知为未读

```http
PATCH /api/v1/notifications/my/{recipient_id}/unread
```

### 标记所有通知为已读

```http
PATCH /api/v1/notifications/my/read-all
```

**Response**:

```json
{
  "code": 200,
  "message": "已标记 10 条通知为已读",
  "data": {
    "marked_count": 10
  }
}
```

### 搜索通知

```http
GET /api/v1/notifications/my/search
```

**Query Parameters**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 否 | 搜索关键词 |
| date_from | string | 否 | 开始日期 (YYYY-MM-DD) |
| date_to | string | 否 | 结束日期 (YYYY-MM-DD) |
| type_id | integer | 否 | 通知类型ID |
| is_read | boolean | 否 | 已读状态 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

## 通知发送接口

### 发送通知

```http
POST /api/v1/notifications
```

**Request Body**:

```json
{
  "recipient_type": "users",
  "user_ids": [1, 2, 3],
  "type_id": 1,
  "title": "通知标题",
  "content": "通知内容（支持Markdown）",
  "template_id": null,
  "variables": {}
}
```

**recipient_type 说明**:
- `users`: 发送给指定用户（需提供 user_ids）
- `department`: 发送给部门（需提供 department_id）

**权限要求**:
- 管理员：可以发送给任何用户/部门
- 部门经理：只能发送给本部门用户/部门
- 普通用户：无权限

**Response**:

```json
{
  "code": 201,
  "message": "通知发送成功",
  "data": {
    "notification": {
      "id": 100,
      "title": "通知标题",
      "content": "通知内容",
      "type": {...},
      "sender": {...},
      "created_at": "2026-02-19T10:00:00"
    },
    "recipient_count": 3
  }
}
```

### 发送全员广播

```http
POST /api/v1/notifications/broadcast
```

**Request Body**:

```json
{
  "type_id": 1,
  "title": "广播标题",
  "content": "广播内容",
  "template_id": null,
  "variables": {}
}
```

**权限要求**: 仅管理员

## 通知类型管理

### 获取通知类型列表

```http
GET /api/v1/notifications/types
```

### 创建通知类型

```http
POST /api/v1/notifications/types
```

**Request Body**:

```json
{
  "name": "新类型",
  "description": "类型描述",
  "icon": "bell",
  "color": "#1890ff"
}
```

**权限要求**: 管理员

### 更新通知类型

```http
PATCH /api/v1/notifications/types/{type_id}
```

**权限要求**: 管理员

### 删除通知类型

```http
DELETE /api/v1/notifications/types/{type_id}
```

**权限要求**: 管理员

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 权限矩阵

| 角色 | 发送给用户 | 发送给部门 | 全员广播 | 管理类型 |
|------|-----------|-----------|---------|---------|
| 管理员 | ✅ 任何人 | ✅ 任何部门 | ✅ | ✅ |
| 部门经理 | ✅ 本部门 | ✅ 本部门 | ❌ | ❌ |
| 普通用户 | ❌ | ❌ | ❌ | ❌ |
