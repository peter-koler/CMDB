# 自定义树形视图功能规格说明书

## 1. 概述

### 1.1 功能编号
006-custom-tree-view

### 1.2 功能名称
自定义树形视图页面管理

### 1.3 目标
提供一个灵活的自定义视图功能，允许管理员创建树形结构的导航页面，将 CMDB 模型数据以树形结构组织展示。

### 1.4 范围
- 视图定义管理（增删改查）
- 树节点管理（增删改查、拖拽排序）
- 模型字段条件筛选
- CI 列表展示与操作
- 角色视图权限分配

## 2. 数据模型

### 2.1 CustomView（视图定义）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Integer | 是 | 主键 |
| name | String(100) | 是 | 视图名称 |
| code | String(50) | 是 | 视图标识（唯一） |
| description | Text | 否 | 描述 |
| icon | String(50) | 否 | 图标 |
| is_active | Boolean | 否 | 是否启用（默认 true） |
| sort_order | Integer | 否 | 排序（默认 0） |
| created_at | DateTime | 否 | 创建时间 |
| updated_at | DateTime | 否 | 更新时间 |
| created_by | Integer | 否 | 创建人 ID |

### 2.2 CustomViewNode（树节点）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Integer | 是 | 主键 |
| view_id | Integer | 是 | 所属视图 ID |
| parent_id | Integer | 否 | 父节点 ID（null 为根节点） |
| name | String(100) | 是 | 节点名称 |
| sort_order | Integer | 否 | 排序（默认 0） |
| filter_config | JSON | 否 | 筛选条件配置 |
| is_active | Boolean | 否 | 是否启用（默认 true） |
| created_at | DateTime | 否 | 创建时间 |
| updated_at | DateTime | 否 | 更新时间 |

### 2.3 FilterConfig（筛选条件配置 JSON 结构）

```json
{
  "model_id": 1,
  "conditions": [
    {
      "field": "status",
      "operator": "eq",
      "value": "running"
    },
    {
      "field": "name",
      "operator": "contains",
      "value": "test"
    }
  ]
}
```

#### Operator 类型

| 操作符 | 说明 | 适用字段类型 |
|--------|------|--------------|
| eq | 等于 | 所有类型（字符串、数字、日期、布尔、枚举） |
| ne | 不等于 | 所有类型 |
| contains | 包含 | 字符串 |
| not_contains | 不包含 | 字符串 |
| gt | 大于 | 数字、日期时间 |
| gte | 大于等于 | 数字、日期时间 |
| lt | 小于 | 数字、日期时间 |
| lte | 小于等于 | 数字、日期时间 |
| in | 在列表中 | 字符串、数字、枚举 |
| not_in | 不在列表中 | 字符串、数字、枚举 |

#### 字段类型与操作符支持对照表

| 字段类型 | 支持的操作符 |
|----------|-------------|
| 字符串 | eq, ne, contains, not_contains, in, not_in |
| 数字 | eq, ne, gt, gte, lt, lte, in, not_in |
| 日期时间 | eq, ne, gt, gte, lt, lte |
| 布尔 | eq |
| 枚举 | eq, ne, in, not_in |

## 3. API 接口

### 3.1 视图管理

#### 3.1.1 获取视图列表

```
GET /api/v1/custom-views
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |
| keyword | string | 否 | 搜索关键词（名称/编码） |
| is_active | bool | 否 | 筛选状态 |

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "服务器视图",
        "code": "server-view",
        "description": "按业务维度展示服务器",
        "icon": "ServerOutlined",
        "is_active": true,
        "sort_order": 0,
        "created_at": "2026-02-24 10:00:00",
        "node_count": 10
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### 3.1.2 创建视图

```
POST /api/v1/custom-views
```

**请求体**:
```json
{
  "name": "服务器视图",
  "code": "server-view",
  "description": "按业务维度展示服务器",
  "icon": "ServerOutlined"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "服务器视图",
    "code": "server-view"
  }
}
```

#### 3.1.3 更新视图

```
PUT /api/v1/custom-views/{id}
```

**请求体**:
```json
{
  "name": "服务器视图（新）",
  "description": "更新后的描述",
  "icon": "DatabaseOutlined",
  "is_active": true
}
```

#### 3.1.4 删除视图

```
DELETE /api/v1/custom-views/{id}
```

**响应**:
```json
{
  "code": 200,
  "message": "删除成功"
}
```

#### 3.1.5 导出视图列表

```
GET /api/v1/custom-views/export
```

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键词 |
| is_active | bool | 否 | 筛选状态 |

**响应**: 返回 Excel 文件（.xlsx）

#### 3.1.6 下载导入模板

```
GET /api/v1/custom-views/import-template
```

**响应**: 返回 Excel 模板文件（.xlsx）

#### 3.1.7 导入视图

```
POST /api/v1/custom-views/import
```

**请求**: multipart/form-data

**表单字段**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | Excel/CSV 文件 |

**响应**:
```json
{
  "code": 200,
  "message": "导入成功",
  "data": {
    "success_count": 10,
    "fail_count": 0,
    "errors": []
  }
}
```

### 3.2 节点管理

#### 3.2.1 获取视图节点树

```
GET /api/v1/custom-views/{id}/nodes
```

**响应**:
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "生产环境",
      "sort_order": 0,
      "filter_config": null,
      "children": [
        {
          "id": 2,
          "name": "Web服务器",
          "sort_order": 0,
          "filter_config": {
            "model_id": 1,
            "conditions": [
              {"field": "type", "operator": "eq", "value": "web"}
            ]
          },
          "children": []
        }
      ]
    }
  ]
}
```

#### 3.2.2 创建节点

```
POST /api/v1/custom-view-nodes
```

**请求体**:
```json
{
  "view_id": 1,
  "parent_id": null,
  "name": "测试环境",
  "sort_order": 1,
  "filter_config": {
    "model_id": 1,
    "conditions": [
      {"field": "env", "operator": "eq", "value": "test"}
    ]
  }
}
```

#### 3.2.3 更新节点

```
PUT /api/v1/custom-view-nodes/{id}
```

**请求体**:
```json
{
  "name": "测试环境（新）",
  "filter_config": {
    "model_id": 1,
    "conditions": [
      {"field": "env", "operator": "eq", "value": "test"}
    ]
  }
}
```

#### 3.2.4 删除节点

```
DELETE /api/v1/custom-view-nodes/{id}
```

**说明**: 删除节点时会级联删除所有子节点。

#### 3.2.5 移动节点

```
PUT /api/v1/custom-view-nodes/{id}/move
```

**请求体**:
```json
{
  "parent_id": 2,
  "sort_order": 0
}
```

### 3.3 CI 查询

#### 3.3.1 获取节点筛选的 CI 列表

```
GET /api/v1/custom-view-nodes/{id}/cis?page=1&page_size=20&keyword=
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "code": "CI001",
        "name": "服务器01",
        "model_name": "服务器",
        "status": "running"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

## 4. 前端页面

### 4.1 视图管理列表页

**路径**: `/system/custom-views`

**功能**: 与现有 CI 列表页面保持一致

#### 4.1.1 工具栏功能

| 功能 | 说明 | 位置 |
|------|------|------|
| 搜索 | 支持按视图名称、编码搜索 | 搜索框 |
| 重置 | 清空所有筛选条件，恢复默认列表 | 按钮 |
| 新增 | 创建新视图 | 按钮 |
| 导入 | 批量导入视图配置（Excel/CSV） | 按钮 |
| 导出 | 导出视图列表（Excel） | 按钮 |

#### 4.1.2 表格功能

| 功能 | 说明 |
|------|------|
| 列表展示 | 展示视图名称、编码、状态、节点数、创建时间 |
| 排序 | 支持按各列排序 |
| 分页 | 支持分页，每页默认 20 条 |
| 查看 | 点击查看视图详情 |
| 编辑 | 编辑视图基本信息 |
| 删除 | 删除视图（需确认） |
| 进入设计器 | 进入视图设计器页面 |

#### 4.1.3 交互组件

| 组件 | 说明 |
|------|------|
| 详情弹窗 | 查看视图详细信息 |
| 编辑弹窗 | 编辑视图基本信息 |
| 导入弹窗 | 支持下载模板、批量导入 |
| 删除确认 | 删除前二次确认 |

### 4.2 视图设计器

**路径**: `/system/custom-views/{id}/designer`

**布局**:
```
┌─────────────────────────────────────────────────────────┐
│  视图设计器 - XXX视图                        [保存] [预览] │
├────────────────────┬────────────────────────────────────┤
│                    │                                    │
│  [+ 添加根节点]     │      节点配置                        │
│                    │                                    │
│  ├─ 节点1          │  节点名称: [________]               │
│  │   ├─ 子节点1    │                                    │
│  │   └─ 子节点2    │  绑定模型: [选择模型 ▼]            │
│  └─ 节点2          │                                    │
│      └─ 子节点3    │  筛选条件:                          │
│                    │  ┌────────────────────────────┐   │
│                    │  │ 字段      操作    值        │   │
│                    │  │ [字段▼]  [等于▼] [_____]  [×]│   │
│                    │  │ [字段▼]  [包含▼] [_____]  [×]│   │
│                    │  └────────────────────────────┘   │
│                    │  [+ 添加条件]                       │
│                    │                                    │
│                    │  [删除节点]                         │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
```

**功能**:
- 左侧树形结构展示节点
- 支持添加根节点和子节点
- 支持拖拽调整顺序和层级
- 右侧配置节点名称和筛选条件
- 保存配置

### 4.3 视图展示页

**路径**: `/custom-view/{code}`

**布局**: 与现有 CI 列表页面保持一致，添加左侧树形导航
```
┌─────────────────────────────────────────────────────────┐
│  自定义视图 - XXX视图                                     │
├────────────────────┬────────────────────────────────────┤
│  树形导航           │      CI 列表                        │
│                    │  ┌────────────────────────────────┐ │
│  [搜索...]          │  │ 工具栏：搜索、重置、新增、导出 │ │
│                    │  └────────────────────────────────┘ │
│  ▼ 节点1            │  ┌────────────────────────────┐   │
│    ├─ 子节点1       │  │ 编码    名称    状态...     │   │
│    │   └─ 子节点2   │  ├────────────────────────────┤   │
│    └─ 子节点3       │  │ CI001   测试1   运行中...   │   │
│  ▼ 节点2            │  │ CI002   测试2   已停止...   │   │
│    └─ 子节点4       │  └────────────────────────────┘   │
│                    │                                    │
│                    │  [分页控件]                         │
└────────────────────┴────────────────────────────────────┘
```

**功能**: 与现有 CI 列表页面保持一致

#### 4.3.1 左侧树形导航

| 功能 | 说明 |
|------|------|
| 节点搜索 | 支持搜索节点名称 |
| 树形展示 | 展示视图节点层级结构 |
| 节点点击 | 点击节点加载右侧 CI 列表 |
| 权限过滤 | 只显示用户有权限的节点 |

#### 4.3.2 右侧 CI 列表工具栏

| 功能 | 说明 | 位置 |
|------|------|------|
| 搜索 | 支持 CI 编码、名称搜索 | 搜索框 |
| 重置 | 清空筛选条件 | 按钮 |
| 新增 | 新增 CI（需权限） | 按钮 |
| 导出 | 导出 CI 列表 | 按钮 |
| 列设置 | 自定义显示列 | 按钮 |

#### 4.3.3 CI 列表表格

| 功能 | 说明 |
|------|------|
| 列表展示 | 展示 CI 编码、名称、状态等 |
| 排序 | 支持按各列排序 |
| 分页 | 支持分页，每页默认 20 条 |
| 查看 | 点击查看 CI 详情 |
| 编辑 | 编辑 CI（需权限） |
| 复制 | 复制 CI |
| 删除 | 删除 CI（需权限） |

#### 4.3.4 批量操作

| 功能 | 说明 |
|------|------|
| 批量选择 | 支持多选 |
| 批量编辑 | 批量编辑 CI |
| 批量删除 | 批量删除 CI |
| 导出选中 | 导出选中的 CI |

#### 4.3.5 交互组件

| 组件 | 说明 |
|------|------|
| CI 详情抽屉 | 查看 CI 详细信息 |
| CI 编辑弹窗 | 编辑 CI 属性 |
| 列设置弹窗 | 自定义表格显示列 |

## 5. 权限设计

### 5.1 权限标识

| 权限标识 | 说明 | 适用角色 |
|----------|------|----------|
| custom-view:manage | 管理自定义视图（创建、编辑、删除视图和节点） | 管理员 |
| custom-view:{code}:view | 查看特定视图（只读） | 普通用户 |
| custom-view:{code}:edit | 编辑特定视图的 CI | 普通用户 |
| custom-view:{code}:node:{node_id}:view | 查看特定节点 | 普通用户 |

### 5.2 权限注册

视图创建后，系统自动注册以下权限：
- `custom-view:{code}:view` - 视图访问权限
- `custom-view:{code}:edit` - 视图编辑权限

节点创建后，系统自动注册节点权限：
- `custom-view:{code}:node:{node_id}:view` - 节点查看权限

### 5.3 节点权限控制规则

#### 5.3.1 权限继承与过滤（已确认需求）

**权限继承规则**：
- **授权父节点自动包含所有子节点**（权限注册时自动包含子节点权限）
- 新建节点默认继承父节点权限
- 权限注册时，授权父节点会同时注册所有子节点的权限标识

**用户查看视图时，系统根据权限过滤节点树**：

1. **视图权限优先**：如果用户有 `custom-view:{code}:view` 权限，可以看到视图下所有节点
2. **节点权限**：如果用户没有视图权限，但有特定节点权限：
   - 显示有权限的节点
   - 显示父级节点作为分类导航（可点击展开，只显示有权限的子节点）
   - 不显示无权限的兄弟节点

#### 5.3.2 树形结构过滤示例

假设完整树结构：
```
根节点
├── 生产环境
│   ├── Web服务器
│   ├── 数据库服务器
│   └── 缓存服务器
├── 测试环境
│   ├── Web服务器
│   └── 数据库服务器
└── 开发环境
    └── Web服务器
```

**场景 1**：用户 A 有视图权限（查看所有节点）
```
根节点
├── 生产环境
│   ├── Web服务器
│   ├── 数据库服务器
│   └── 缓存服务器
├── 测试环境
│   ├── Web服务器
│   └── 数据库服务器
└── 开发环境
    └── Web服务器
```

**场景 2**：用户 B 只有节点权限（生产环境）
```
根节点
└── 生产环境  ← 可点击，显示所有子节点（继承）
    ├── Web服务器
    ├── 数据库服务器
    └── 缓存服务器
```

**场景 3**：用户 C 只有节点权限（生产环境/Web服务器、测试环境/Web服务器）
```
根节点
├── 生产环境  ← 可点击，只显示有权限的子节点
│   └── Web服务器  ✓
└── 测试环境  ← 可点击，只显示有权限的子节点
    └── Web服务器  ✓
```

#### 5.3.3 权限分配方式

在角色管理中，管理员可以：
1. 分配整个视图的权限（查看视图下所有节点）- **优先级最高**
2. 分配特定节点的权限（查看该节点及其所有子节点）- **继承子节点**

#### 5.3.4 权限检查逻辑

**说明**：由于采用"权限注册时自动包含"的实现方式，权限表中已包含所有子节点权限，因此查询时只需直接检查权限标识。

```python
def get_user_visible_nodes(user, view_code):
    """获取用户可见的节点树"""
    # 1. 检查是否有视图权限
    if user.has_permission(f'custom-view:{view_code}:view'):
        # 有视图权限，返回所有节点
        return get_all_nodes(view_code)
    
    # 2. 获取用户有权限的所有节点 ID（权限注册时已包含子节点）
    permitted_node_ids = get_user_node_permissions(user, view_code)
    
    # 3. 获取这些节点的所有父级节点 ID（用于导航）
    parent_ids = set()
    for node_id in permitted_node_ids:
        parents = get_node_ancestors(node_id)
        parent_ids.update(parents)
    
    # 4. 合并有权限节点和父级节点
    visible_node_ids = permitted_node_ids | parent_ids
    
    # 5. 构建树形结构（只包含可见节点）
    return build_tree(visible_node_ids)

def check_node_permission(user, node, view_code):
    """检查用户对特定节点的权限"""
    # 1. 视图权限优先
    if user.has_permission(f'custom-view:{view_code}:view'):
        return True
    
    # 2. 直接检查节点权限（子节点权限已在授权父节点时一并注册）
    return user.has_permission(f'custom-view:{view_code}:node:{node.id}:view')
```

#### 5.3.5 节点编辑权限（已确认需求）

节点编辑权限与视图权限关联：
- **管理员** (`custom-view:manage`)：可以编辑所有视图的节点
- **普通用户**：有 `custom-view:{code}:edit` 权限的用户可以编辑该视图的节点

#### 5.3.6 权限注册时的继承实现

```python
def grant_node_permission(role_id, node_id, view_code):
    """为角色授予节点权限（包含子节点继承）"""
    # 1. 授权当前节点
    permission_code = f'custom-view:{view_code}:node:{node_id}:view'
    add_permission(role_id, permission_code)
    
    # 2. 递归授权所有子节点
    for child in node.get_all_children():
        child_permission_code = f'custom-view:{view_code}:node:{child.id}:view'
        add_permission(role_id, child_permission_code)
    
    return True

def revoke_node_permission(role_id, node_id, view_code):
    """撤销角色节点权限（包含子节点）"""
    # 1. 撤销当前节点权限
    permission_code = f'custom-view:{view_code}:node:{node_id}:view'
    remove_permission(role_id, permission_code)
    
    # 2. 递归撤销所有子节点权限
    for child in node.get_all_children():
        child_permission_code = f'custom-view:{view_code}:node:{child.id}:view'
        remove_permission(role_id, child_permission_code)
    
    return True
```

### 5.4 菜单权限

视图启用后，自动在菜单系统中注册，**默认挂载在一级菜单 "CMDB" 目录下**。

#### 5.4.1 菜单入口设计（已确认需求）

- **菜单位置**：一级菜单 CMDB 目录下方
- **菜单项命名**：视图名称
- **示例**：
  ```
  CMDB
  ├── 模型管理
  ├── 实例管理
  ├── 关系管理
  ├── 服务器视图      ← 自动生成
  ├── 网络设备视图    ← 自动生成
  └── 业务系统视图    ← 自动生成
  ```

#### 5.4.2 菜单权限控制

1. 视图启用后自动在菜单中显示
2. 用户需有视图访问权限（`custom-view:{code}:view`）才能在菜单中看到该视图
3. 无权限的用户菜单中不显示该视图入口

### 5.5 权限数据模型

```python
# 节点权限表（新增）
class CustomViewNodePermission(db.Model):
    __tablename__ = 'custom_view_node_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey('custom_view_nodes.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    can_view = db.Column(db.Boolean, default=True)
    can_edit = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关联
    node = db.relationship('CustomViewNode', backref='role_permissions')
    role = db.relationship('Role', backref='view_node_permissions')
```

## 6. 业务规则

### 6.1 视图规则

1. 视图 code 必须唯一，只能包含字母、数字、下划线、中划线
2. 删除视图时级联删除所有节点
3. 删除视图时**级联删除相关权限**（权限标识一并清除）
4. 禁用视图后，用户无法访问对应页面

### 6.2 节点规则

1. 节点名称不能为空
2. 节点层级最多 5 层
3. 同一父节点下，节点名称不能重复
4. 删除节点时级联删除所有子节点
5. 节点可以没有筛选条件（仅作为分类）
6. **根节点只能作为顶级分类，不能设置筛选条件**
7. **子节点可以有筛选条件**

### 6.3 筛选规则

1. 筛选条件中的字段必须存在于模型的 form_config 中
2. 多个条件之间是 AND 关系
3. 值为空时忽略该条件
4. 模型变更后，不存在的字段条件自动忽略

### 6.4 CI 权限控制规则（已确认需求）

**基于模型的 CI 权限控制**：

1. **CI 访问权限由模型权限控制**：
   - 用户有模型权限 → 可以查看该模型的所有 CI
   - 用户无模型权限 → 无法查看该模型的 CI

2. **节点权限与 CI 权限的关系**：
   - 节点权限控制"能否看到这个分类节点"
   - CI 权限控制"能否查看 CI 详情"
   - 两者独立，互不影响

3. **示例场景**：
   - 用户甲有节点 A 权限，有模型 X 权限 → 可以看到节点 A，查看节点 A 筛选出的 CI
   - 用户乙无节点 A 权限，有模型 X 权限 → 看不到节点 A，但可以通过其他方式（如 CMDB 实例列表）查看模型 X 的 CI
   - 用户丙有节点 A 权限，无模型 X 权限 → 可以看到节点 A，但无法查看 CI 详情

4. **权限检查流程**：
   ```python
   def get_node_ci_list(user, node):
       # 1. 检查节点权限
       if not check_node_permission(user, node):
           raise PermissionDenied("无节点权限")
       
       # 2. 检查模型权限（CI 权限）
       model_id = node.filter_config.get('model_id')
       if not user.has_model_permission(model_id, 'view'):
           raise PermissionDenied("无模型权限")
       
       # 3. 查询 CI 列表
       return query_ci_by_filter(node.filter_config)
   ```

### 6.5 API 权限验证规则（已确认需求）

部分 API 公开用于管理，部分 API 需要权限验证：

| API | 方法 | 权限要求 | 说明 |
|-----|------|----------|------|
| 获取视图列表 | GET /custom-views | `custom-view:manage` | 管理用，需管理员权限 |
| 创建视图 | POST /custom-views | `custom-view:manage` | 管理用 |
| 更新视图 | PUT /custom-views/{id} | `custom-view:manage` | 管理用 |
| 删除视图 | DELETE /custom-views/{id} | `custom-view:manage` | 管理用 |
| 获取节点树 | GET /custom-views/{id}/nodes | `custom-view:manage` | 设计器用，需管理权限 |
| 创建节点 | POST /custom-view-nodes | `custom-view:manage` | 管理用 |
| 更新节点 | PUT /custom-view-nodes/{id} | `custom-view:manage` | 管理用 |
| 删除节点 | DELETE /custom-view-nodes/{id} | `custom-view:manage` | 管理用 |
| 获取节点 CI | GET /custom-view-nodes/{id}/cis | `custom-view:{code}:view` | 需视图或节点权限 + 模型权限 |

**说明**：
- 视图和节点的管理 API（增删改查）需要 `custom-view:manage` 权限
- CI 查询 API 需要用户有视图访问权限或节点权限，且有对应模型的查看权限

## 7. 性能要求

1. 视图节点树查询 < 100ms（已添加缓存优化）
2. CI 列表查询 < 500ms（单页 20 条）
3. 节点拖拽排序实时保存

### 7.1 性能优化实现

#### 7.1.1 缓存机制

- **节点树缓存**：视图节点树数据缓存 5 分钟
- **缓存键格式**：`view_nodes_tree:{view_id}:user:{user_id}`
- **缓存失效**：节点增删改、权限变更时自动清除缓存
- **实现文件**：`backend/app/utils/cache.py`

#### 7.1.2 数据库索引

为 `custom_view_nodes` 表添加以下索引：

| 索引名 | 字段 | 说明 |
|--------|------|------|
| ix_custom_view_nodes_view_id | view_id | 视图 ID 索引 |
| ix_custom_view_nodes_parent_id | parent_id | 父节点 ID 索引 |
| ix_custom_view_nodes_is_active | is_active | 激活状态索引 |
| ix_view_node_parent | view_id, parent_id | 复合索引 |
| ix_view_node_active | view_id, is_active | 复合索引 |

#### 7.1.3 查询优化

- 使用 JOIN 替代子查询
- 分页查询使用游标或延迟加载
- 属性筛选在应用层处理，减少数据库压力

## 8. 错误处理

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 400 | 参数错误 | 提示具体错误信息 |
| 403 | 无权限 | 提示无权限访问 |
| 404 | 视图/节点不存在 | 提示资源不存在 |
| 409 | 编码重复 | 提示更换编码 |
| 500 | 服务器内部错误 | 记录日志，提示联系管理员 |

## 9. 功能变更记录

### 2026-02-24 更新内容

#### 9.1 新增功能

1. **属性筛选功能**
   - CI 列表支持按属性字段筛选
   - 支持模糊搜索（不区分大小写）
   - 筛选条件与节点预设条件组合使用

2. **性能优化**
   - 添加节点树缓存机制（5 分钟过期）
   - 添加数据库索引优化查询
   - 优化 CI 列表查询逻辑

3. **列设置功能**
   - 支持自定义显示列
   - 支持拖拽调整列顺序
   - 列配置本地存储

4. **批量操作**
   - 批量编辑 CI
   - 批量删除 CI
   - 导出选中 CI

5. **导入导出**
   - CI 数据导入（支持 Excel/CSV）
   - CI 数据导出
   - 导入模板下载

#### 9.2 修复问题

1. **列设置按钮不显示**
   - 修复：正确解析 `form_config` 获取模型字段

2. **属性信息不显示**
   - 修复：实现 `getAttributeValue` 函数从 `attributes` 字段取值

3. **主机名显示错误**
   - 修复：优先从 `attributes` 获取属性值，而非顶层字段

4. **筛选条件不生效**
   - 修复：正确处理 JSON 属性字段的筛选逻辑

5. **403 权限错误**
   - 修复：使用 `role_links` 替代 `roles` 获取用户角色

#### 9.3 API 变更

1. **获取节点 CI 列表**
   - 新增查询参数：`attr_field`（属性字段名）
   - 新增查询参数：`attr_value`（属性值，支持模糊匹配）

2. **响应格式优化**
   - CI 列表响应包含 `attributes` 字段
   - 优化分页响应结构

#### 9.4 前端优化

1. **UI 组件**
   - 添加属性筛选下拉框和输入框
   - 优化工具栏布局（响应式换行）
   - 添加批量操作栏

2. **交互优化**
   - 列设置弹窗支持拖拽排序
   - 搜索支持回车触发
   - 添加加载状态提示
