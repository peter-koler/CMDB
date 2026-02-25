# 自定义树视图 API 文档

## 概述

本文档描述了自定义树视图模块的 RESTful API 接口，用于管理自定义视图、视图节点、节点权限以及基于节点的 CI 查询。

**基础路径**: `/api/v1`

**认证方式**: JWT Token (Bearer Token)

---

## 视图管理 API

### 1. 获取当前用户的视图列表

获取当前登录用户有权限查看的自定义视图列表（用于菜单展示）。

**请求**

```http
GET /custom-views/my
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "服务器视图",
      "code": "server-view",
      "description": "服务器资源管理视图",
      "icon": "AppstoreOutlined",
      "is_active": true,
      "sort_order": 1,
      "node_count": 5
    }
  ]
}
```

---

### 2. 获取视图列表

获取所有自定义视图列表（需要管理权限）。

**请求**

```http
GET /custom-views?page=1&page_size=20
Authorization: Bearer {token}
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### 3. 创建视图

创建新的自定义视图（需要管理权限）。

**请求**

```http
POST /custom-views
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "服务器视图",
  "code": "server-view",
  "description": "服务器资源管理视图",
  "icon": "AppstoreOutlined",
  "is_active": true,
  "sort_order": 1
}
```

**请求体参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 视图名称 |
| code | string | 是 | 视图编码（唯一） |
| description | string | 否 | 视图描述 |
| icon | string | 否 | 图标，默认 "AppstoreOutlined" |
| is_active | bool | 否 | 是否激活，默认 true |
| sort_order | int | 否 | 排序顺序，默认 0 |

**响应**

```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "服务器视图",
    "code": "server-view",
    ...
  }
}
```

---

### 4. 获取视图详情

获取指定视图的详细信息。

**请求**

```http
GET /custom-views/{view_id}
Authorization: Bearer {token}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| view_id | int | 视图 ID |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "服务器视图",
    "code": "server-view",
    "description": "服务器资源管理视图",
    "icon": "AppstoreOutlined",
    "is_active": true,
    "sort_order": 1,
    "node_count": 5,
    "created_at": "2026-02-24 10:00:00",
    "updated_at": "2026-02-24 10:00:00"
  }
}
```

---

### 5. 更新视图

更新指定视图的信息（需要管理权限）。

**请求**

```http
PUT /custom-views/{view_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "服务器视图（更新）",
  "description": "更新后的描述",
  "is_active": true,
  "sort_order": 2
}
```

**响应**

```json
{
  "code": 200,
  "message": "更新成功",
  "data": { ... }
}
```

---

### 6. 删除视图

删除指定视图（需要管理权限）。

**请求**

```http
DELETE /custom-views/{view_id}
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

---

## 节点管理 API

### 7. 获取视图节点树

获取指定视图的节点树结构（带权限过滤，含缓存优化）。

**请求**

```http
GET /custom-views/{view_id}/nodes/tree
Authorization: Bearer {token}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| view_id | int | 视图 ID |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "view_id": 1,
      "parent_id": null,
      "name": "广州机房",
      "sort_order": 0,
      "filter_config": {
        "model_id": 4,
        "conditions": [
          {
            "field": "name",
            "operator": "contains",
            "value": "db"
          }
        ]
      },
      "is_active": true,
      "is_root": true,
      "level": 0,
      "children": [
        {
          "id": 2,
          "name": "数据库服务器",
          "parent_id": 1,
          ...
        }
      ]
    }
  ]
}
```

**说明**
- 返回的数据根据当前用户的权限进行过滤
- 管理员可以看到所有节点
- 普通用户只能看到被授予权限的节点及其父节点
- 响应包含缓存标识（首次请求后，缓存命中时响应更快）

---

### 8. 获取视图节点列表

获取指定视图的扁平化节点列表（需要管理权限）。

**请求**

```http
GET /custom-views/{view_id}/nodes
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "view_id": 1,
      "parent_id": null,
      "name": "广州机房",
      "sort_order": 0,
      "filter_config": { ... },
      "is_active": true,
      "level": 0
    }
  ]
}
```

---

### 9. 创建节点

在指定视图下创建新节点（需要管理权限）。

**请求**

```http
POST /custom-view-nodes
Authorization: Bearer {token}
Content-Type: application/json

{
  "view_id": 1,
  "parent_id": null,
  "name": "深圳机房",
  "sort_order": 1,
  "is_active": true,
  "filter_config": {
    "model_id": 4,
    "conditions": [
      {
        "field": "location",
        "operator": "eq",
        "value": "shenzhen"
      }
    ]
  }
}
```

**请求体参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| view_id | int | 是 | 所属视图 ID |
| parent_id | int | 否 | 父节点 ID，null 表示根节点 |
| name | string | 是 | 节点名称 |
| sort_order | int | 否 | 排序顺序 |
| is_active | bool | 否 | 是否激活 |
| filter_config | object | 否 | 筛选配置（根节点不能设置） |

**filter_config 结构**

```json
{
  "model_id": 4,
  "conditions": [
    {
      "field": "name",
      "operator": "contains",
      "value": "db"
    }
  ]
}
```

**操作符说明**

| 操作符 | 说明 |
|--------|------|
| eq | 等于 |
| ne | 不等于 |
| contains | 包含（模糊匹配） |
| not_contains | 不包含 |
| gt | 大于 |
| gte | 大于等于 |
| lt | 小于 |
| lte | 小于等于 |
| in | 在列表中 |
| not_in | 不在列表中 |

**响应**

```json
{
  "code": 201,
  "message": "创建成功",
  "data": { ... }
}
```

---

### 10. 获取节点详情

获取指定节点的详细信息。

**请求**

```http
GET /custom-view-nodes/{node_id}
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "view_id": 1,
    "parent_id": null,
    "name": "广州机房",
    "sort_order": 0,
    "filter_config": { ... },
    "is_active": true,
    "is_root": true,
    "level": 0
  }
}
```

---

### 11. 更新节点

更新指定节点的信息（需要管理权限）。

**请求**

```http
PUT /custom-view-nodes/{node_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "广州机房（更新）",
  "sort_order": 2,
  "is_active": true,
  "filter_config": { ... }
}
```

**响应**

```json
{
  "code": 200,
  "message": "更新成功",
  "data": { ... }
}
```

---

### 12. 删除节点

删除指定节点及其所有子节点（需要管理权限）。

**请求**

```http
DELETE /custom-view-nodes/{node_id}
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

---

### 13. 移动节点

移动节点到新的父节点或调整排序（需要管理权限）。

**请求**

```http
PUT /custom-view-nodes/{node_id}/move
Authorization: Bearer {token}
Content-Type: application/json

{
  "parent_id": 2,
  "sort_order": 0
}
```

**请求体参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| parent_id | int | 否 | 新的父节点 ID，null 表示移动到根 |
| sort_order | int | 否 | 新的排序顺序 |

**响应**

```json
{
  "code": 200,
  "message": "移动成功",
  "data": { ... }
}
```

---

## CI 查询 API

### 14. 获取节点的 CI 列表

获取指定节点筛选条件下的 CI 实例列表（支持属性筛选和模糊搜索）。

**请求**

```http
GET /custom-view-nodes/{node_id}/cis?page=1&page_size=20&keyword=db&attr_field=name&attr_value=oracle
Authorization: Bearer {token}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| node_id | int | 节点 ID |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |
| keyword | string | 否 | 关键字搜索（搜索 CI 编码、名称和属性值） |
| attr_field | string | 否 | 属性字段名（用于属性筛选） |
| attr_value | string | 否 | 属性值（支持模糊搜索） |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 12,
        "code": "CI26022100000026",
        "name": "CI26022100000026",
        "model_id": 4,
        "model_name": "甲骨文",
        "model_code": "oracle",
        "attributes": {
          "name": "db3",
          "ipaddr": "192.168.1.2",
          "type": "oracle"
        },
        "department_id": 2,
        "department_name": "分公司",
        "created_at": "2026-02-21T12:48:25.366853",
        "updated_at": "2026-02-24T12:57:21.764460",
        "creator_name": "admin"
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

**说明**
- 返回的 CI 列表会应用节点配置的筛选条件
- 支持额外的属性筛选（attr_field + attr_value）
- 属性筛选支持模糊匹配（不区分大小写）
- 关键字搜索会在 CI 编码、名称和所有属性值中查找

---

## 权限管理 API

### 15. 获取节点权限列表

获取指定节点的角色权限列表（需要管理权限）。

**请求**

```http
GET /custom-view-nodes/{node_id}/permissions
Authorization: Bearer {token}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "node_id": 2,
      "role_id": 2,
      "created_at": "2026-02-24 10:00:00"
    }
  ]
}
```

---

### 16. 授予节点权限

为指定角色授予节点访问权限（需要管理权限）。

**请求**

```http
POST /custom-view-nodes/{node_id}/permissions
Authorization: Bearer {token}
Content-Type: application/json

{
  "role_id": 2
}
```

**请求体参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_id | int | 是 | 角色 ID |

**说明**
- 授权会自动应用到该节点的所有子节点
- 授权后会清除该视图的缓存

**响应**

```json
{
  "code": 201,
  "message": "授权成功",
  "data": {
    "id": 1,
    "node_id": 2,
    "role_id": 2,
    "created_at": "2026-02-24 10:00:00"
  }
}
```

---

### 17. 撤销节点权限

撤销指定角色的节点访问权限（需要管理权限）。

**请求**

```http
DELETE /custom-view-nodes/{node_id}/permissions/{role_id}
Authorization: Bearer {token}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| node_id | int | 节点 ID |
| role_id | int | 角色 ID |

**说明**
- 撤销权限会自动应用到该节点的所有子节点
- 撤销后会清除该视图的缓存

**响应**

```json
{
  "code": 200,
  "message": "撤销成功",
  "data": null
}
```

---

### 18. 获取权限树

获取用于权限配置的节点树（需要管理权限）。

**请求**

```http
GET /custom-views/permissions/tree?view_id=1
Authorization: Bearer {token}
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| view_id | int | 是 | 视图 ID |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "广州机房",
      "children": [
        {
          "id": 2,
          "name": "数据库服务器",
          "children": []
        }
      ]
    }
  ]
}
```

---

## 系统管理 API

### 19. 注销视图权限

注销自定义视图的权限配置（需要管理权限）。

**请求**

```http
POST /permissions/unregister
Authorization: Bearer {token}
Content-Type: application/json

{
  "view_code": "server-view"
}
```

**请求体参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| view_code | string | 是 | 视图编码 |

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未登录 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 性能优化说明

### 缓存机制

- **节点树缓存**: 视图节点树数据缓存 5 分钟
- **缓存键格式**: `view_nodes_tree:{view_id}:user:{user_id}`
- **缓存失效**: 节点增删改、权限变更时自动清除缓存

### 索引优化

数据库表 `custom_view_nodes` 已添加以下索引：

- `ix_custom_view_nodes_view_id` - 视图 ID 索引
- `ix_custom_view_nodes_parent_id` - 父节点 ID 索引
- `ix_custom_view_nodes_is_active` - 激活状态索引
- `ix_view_node_parent` - 复合索引 (view_id, parent_id)
- `ix_view_node_active` - 复合索引 (view_id, is_active)

---

## 权限说明

### 需要的权限码

| 权限码 | 说明 |
|--------|------|
| `custom-view:manage` | 管理自定义视图（创建、编辑、删除视图和节点） |
| `custom-view:{view_code}:view` | 查看指定视图的权限 |

### 权限继承

- 节点权限会自动继承到子节点
- 拥有视图查看权限的用户可以看到所有节点
- 普通用户只能看到被显式授权的节点及其父节点
