# 自定义树形视图页面功能计划

## 功能编号
006-custom-tree-view

## 功能名称
自定义树形视图页面管理

## 背景与目标

### 背景
系统需要一个灵活的自定义视图功能，允许管理员创建树形结构的导航页面，将 CMDB 模型数据以树形结构组织展示，方便用户按业务维度查看和管理 CI。

### 目标
1. 支持管理员创建自定义树形视图页面
2. 支持树节点的增删改查操作
3. 支持为节点绑定模型筛选条件，展示符合条件的 CI 列表
4. 支持与角色权限系统集成

## 术语

| 术语 | 说明 |
|------|------|
| 树形视图 | 左侧为树形导航，右侧为 CI 列表的页面布局 |
| 视图定义 | 描述一个自定义页面的元数据（名称、标识等） |
| 树节点 | 视图中的层级节点，支持无限层级 |
| 节点条件 | 绑定到节点的模型筛选条件 |
| 视图权限 | 控制角色能否访问特定视图的权限 |

## 范围

### 包含
- 视图定义管理（增删改查）
- 树节点管理（增删改查、拖拽排序）
- 模型字段条件筛选
- CI 列表展示与操作
- 角色视图权限分配

### 不包含
- 复杂报表功能
- 数据导出功能
- 与其他系统的集成

## 用户故事

### US-001 视图管理
作为系统管理员，我希望创建自定义树形视图页面，以便为不同业务场景提供定制化的 CI 展示界面。

**验收标准**:
- [ ] 可以创建视图，设置名称和标识
- [ ] 可以修改视图基本信息
- [ ] 可以删除视图（需确认）
- [ ] 视图列表展示所有自定义视图

### US-002 树节点管理
作为系统管理员，我希望在视图中管理树形节点，以便构建层级化的导航结构。

**验收标准**:
- [ ] 可以添加根节点
- [ ] 可以为节点添加子节点
- [ ] 可以修改节点名称
- [ ] 可以删除节点（需确认）
- [ ] 可以拖拽调整节点顺序
- [ ] 可以拖拽移动节点到其他父节点

### US-003 节点条件配置
作为系统管理员，我希望为节点配置模型筛选条件，以便展示符合条件的 CI。

**验收标准**:
- [ ] 可以为节点选择绑定的模型
- [ ] 可以从模型的 form_config 中选择字段
- [ ] 可以设置字段的筛选条件（等于、包含等）
- [ ] 可以配置多个字段条件（AND 关系）
- [ ] 保存后条件生效

### US-004 CI 列表展示
作为普通用户，我希望在树形视图中查看 CI 列表，以便管理和操作配置项。

**验收标准**:
- [ ] 点击节点展示对应 CI 列表
- [ ] 列表展示 CI 的基本信息（编码、名称等）
- [ ] 支持分页和搜索
- [ ] 支持查看 CI 详情
- [ ] 支持编辑 CI（需权限）

### US-005 视图权限控制
作为系统管理员，我希望为角色分配视图权限，以便控制用户访问。

**验收标准**:
- [ ] 在角色管理中显示视图权限列表
- [ ] 可以为角色分配视图访问权限（查看视图下所有节点）
- [ ] 可以为角色分配特定节点的权限（只查看指定节点）
- [ ] 无权限的用户看不到对应菜单
- [ ] 直接访问 URL 时无权限提示

### US-006 节点权限过滤
作为普通用户，我只希望看到我有权限访问的节点及其分类路径。

**验收标准**:
- [ ] 用户只能看到被授权的节点
- [ ] 被授权节点的父级分类节点显示为导航（不可点击或提示无数据权限）
- [ ] 未被授权的兄弟节点不显示
- [ ] 权限变更后实时生效

## 技术方案

### 后端设计

#### 数据模型

```python
# CustomView - 视图定义
class CustomView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 视图名称
    code = db.Column(db.String(50), unique=True, nullable=False)  # 视图标识
    description = db.Column(db.Text)  # 描述
    icon = db.Column(db.String(50))  # 图标
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

# CustomViewNode - 树节点
class CustomViewNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    view_id = db.Column(db.Integer, db.ForeignKey('custom_views.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('custom_view_nodes.id'))
    name = db.Column(db.String(100), nullable=False)  # 节点名称
    sort_order = db.Column(db.Integer, default=0)
    
    # 筛选条件配置（JSON）
    # {
    #   "model_id": 1,
    #   "conditions": [
    #     {"field": "status", "operator": "eq", "value": "running"},
    #     {"field": "name", "operator": "contains", "value": "test"}
    #   ]
    # }
    filter_config = db.Column(db.JSON)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    view = db.relationship('CustomView', backref='nodes')
    parent = db.relationship('CustomViewNode', remote_side=[id], backref='children')
```

#### API 设计

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 视图列表 | GET | /api/v1/custom-views | 获取所有视图（分页、搜索） |
| 创建视图 | POST | /api/v1/custom-views | 创建新视图 |
| 更新视图 | PUT | /api/v1/custom-views/{id} | 更新视图 |
| 删除视图 | DELETE | /api/v1/custom-views/{id} | 删除视图 |
| 导出视图 | GET | /api/v1/custom-views/export | 导出视图列表（Excel） |
| 下载模板 | GET | /api/v1/custom-views/import-template | 下载导入模板 |
| 导入视图 | POST | /api/v1/custom-views/import | 导入视图（Excel/CSV） |
| 获取节点树 | GET | /api/v1/custom-views/{id}/nodes | 获取视图节点树 |
| 创建节点 | POST | /api/v1/custom-view-nodes | 创建节点 |
| 更新节点 | PUT | /api/v1/custom-view-nodes/{id} | 更新节点 |
| 删除节点 | DELETE | /api/v1/custom-view-nodes/{id} | 删除节点 |
| 移动节点 | PUT | /api/v1/custom-view-nodes/{id}/move | 移动节点位置 |
| 获取节点 CI | GET | /api/v1/custom-view-nodes/{id}/cis | 获取节点筛选的 CI |

### 前端设计

#### 页面结构

```
views/
├── custom-view/
│   ├── index.vue          # 视图管理列表页
│   ├── designer.vue       # 视图设计器（树节点管理）
│   └── view.vue           # 视图展示页（用户使用）
```

#### 视图设计器布局

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

#### 视图展示页布局

```
┌─────────────────────────────────────────────────────────┐
│  自定义视图 - XXX视图                                     │
├────────────────────┬────────────────────────────────────┤
│  树形导航           │      CI 列表                        │
│                    │                                    │
│  [搜索...]          │  ┌────────────────────────────┐   │
│                    │  │ 编码    名称    状态...     │   │
│  ▼ 节点1            │  ├────────────────────────────┤   │
│    ├─ 子节点1       │  │ CI001   测试1   运行中...   │   │
│    │   └─ 子节点2   │  │ CI002   测试2   已停止...   │   │
│    └─ 子节点3       │  └────────────────────────────┘   │
│  ▼ 节点2            │                                    │
│    └─ 子节点4       │  [分页控件]                         │
│                    │                                    │
└────────────────────┴────────────────────────────────────┘
```

## 权限设计

### 权限标识

| 权限标识 | 说明 | 适用角色 |
|----------|------|----------|
| custom-view:manage | 管理自定义视图（创建、编辑、删除视图和节点） | 管理员 |
| custom-view:{code}:view | 查看特定视图（只读） | 普通用户 |
| custom-view:{code}:edit | 编辑特定视图的 CI | 普通用户 |
| custom-view:{code}:node:{node_id}:view | 查看特定节点 | 普通用户 |

### 菜单权限

视图创建后，**自动挂载在一级菜单 "CMDB" 目录下方**，管理员可在角色管理中分配。

### 权限继承

- 授权父节点自动包含所有子节点（权限注册时自动包含）
- 删除视图时级联删除相关权限

## 数据库迁移

```sql
-- 创建视图定义表
CREATE TABLE custom_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

-- 创建视图节点表
CREATE TABLE custom_view_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    view_id INTEGER NOT NULL REFERENCES custom_views(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES custom_view_nodes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    filter_config JSON,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 节点权限表
CREATE TABLE custom_view_node_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL REFERENCES custom_view_nodes(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, role_id)
);

-- 创建索引
CREATE INDEX idx_custom_views_code ON custom_views(code);
CREATE INDEX idx_custom_views_active ON custom_views(is_active);
CREATE INDEX idx_custom_view_nodes_view ON custom_view_nodes(view_id);
CREATE INDEX idx_custom_view_nodes_parent ON custom_view_nodes(parent_id);
CREATE INDEX idx_custom_view_node_permissions_node ON custom_view_node_permissions(node_id);
CREATE INDEX idx_custom_view_node_permissions_role ON custom_view_node_permissions(role_id);
```

## 任务分解

### 阶段 1：后端基础（2.5天）
- [ ] T001 创建数据模型 CustomView、CustomViewNode 和 CustomViewNodePermission
- [ ] T002 创建数据库迁移脚本
- [ ] T003 实现视图管理 API（CRUD、导入导出）
- [ ] T004 实现节点管理 API（CRUD、移动）
- [ ] T005 实现节点 CI 筛选查询 API
- [ ] T009-1 实现节点权限管理 API

### 阶段 2：前端基础（2.5天）
- [ ] T006 创建视图管理列表页（与 CI 列表一致）
- [ ] T007 创建视图设计器页面（树形结构管理）
- [ ] T008 实现节点条件配置组件
- [ ] T009 创建视图展示页面（与 CI 列表一致）

### 阶段 3：权限集成（1天）
- [ ] T010 实现视图和节点权限注册机制
- [ ] T011 更新角色管理页面，支持视图和节点权限分配
- [ ] T012 实现菜单动态权限控制（带节点权限过滤）

### 阶段 4：测试与优化（1天）
- [ ] T013 编写后端单元测试
- [ ] T014 集成测试
- [ ] T015 性能优化

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 树节点层级过深 | 查询性能下降 | 限制最大层级为 5 层 |
| 条件筛选复杂 | CI 查询慢 | 添加索引，限制条件数量 |
| 权限配置复杂 | 用户困惑 | 提供默认角色模板 |

## 依赖

- 现有 CMDB 模型和 CI 查询功能
- 现有角色权限系统
- Ant Design Vue 组件库

## 参考

- 现有模型管理功能
- 现有角色权限管理功能
