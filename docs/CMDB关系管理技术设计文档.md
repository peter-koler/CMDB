# CMDB 关系管理技术设计文档

## 1. 概述

本文档详细描述 CMDB 关系管理功能的技术实现方案，包括数据模型调整、后端 API 设计、前端页面结构等。

## 2. 数据模型设计

### 2.1 RelationType 模型调整

现有模型需要新增以下字段：

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| source_model_ids | Text | JSON 数组，允许的源模型 ID 列表 | [1, 2, 3] |
| target_model_ids | Text | JSON 数组，允许的目标模型 ID 列表 | [4, 5] |
| cardinality | String(20) | 基数限制：one_one / one_many / many_many | one_many |
| allow_self_loop | Boolean | 是否允许自环，默认 False | False |

**调整后的完整模型**：

```python
class RelationType(db.Model):
    __tablename__ = 'relation_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    source_label = db.Column(db.String(100), nullable=False)
    target_label = db.Column(db.String(100), nullable=False)
    direction = db.Column(db.String(20), default='directed')
    
    # 新增字段
    source_model_ids = db.Column(db.Text, default='[]')
    target_model_ids = db.Column(db.Text, default='[]')
    cardinality = db.Column(db.String(20), default='many_many')
    allow_self_loop = db.Column(db.Boolean, default=False)
    
    description = db.Column(db.Text)
    style = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'source_label': self.source_label,
            'target_label': self.target_label,
            'direction': self.direction,
            'source_model_ids': json.loads(self.source_model_ids) if self.source_model_ids else [],
            'target_model_ids': json.loads(self.target_model_ids) if self.target_model_ids else [],
            'cardinality': self.cardinality,
            'allow_self_loop': self.allow_self_loop,
            'description': self.description,
            'style': json.loads(self.style) if self.style else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

### 2.2 数据库迁移

需要创建数据库迁移脚本，添加新增字段。

---

## 3. 后端 API 设计

### 3.1 统一响应格式

所有 API 遵循以下响应格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 3.2 关系类型接口

#### 3.2.1 获取关系类型列表

```
GET /api/v1/cmdb/relation-types
```

**请求参数**：
- page: 页码（默认 1）
- per_page: 每页数量（默认 20）
- keyword: 搜索关键词（可选）

**响应数据**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "code": "runs_on",
        "name": "运行在",
        "source_label": "运行",
        "target_label": "承载",
        "direction": "directed",
        "source_model_ids": [1, 2],
        "target_model_ids": [3],
        "cardinality": "many_many",
        "allow_self_loop": false,
        "description": "应用运行在主机上",
        "style": {"color": "#1890ff"},
        "created_at": "2026-02-14T10:00:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "per_page": 20
  }
}
```

#### 3.2.2 新增关系类型

```
POST /api/v1/cmdb/relation-types
```

**请求体**：
```json
{
  "code": "runs_on",
  "name": "运行在",
  "source_label": "运行",
  "target_label": "承载",
  "direction": "directed",
  "source_model_ids": [1, 2],
  "target_model_ids": [3],
  "cardinality": "many_many",
  "allow_self_loop": false,
  "description": "应用运行在主机上",
  "style": {"color": "#1890ff"}
}
```

#### 3.2.3 获取关系类型详情

```
GET /api/v1/cmdb/relation-types/:id
```

#### 3.2.4 更新关系类型

```
PUT /api/v1/cmdb/relation-types/:id
```

**请求体**：同新增

#### 3.2.5 删除关系类型

```
DELETE /api/v1/cmdb/relation-types/:id
```

**校验**：删除前检查是否有关联的关系实例或触发器，有则拒绝删除

---

### 3.3 关系实例接口

#### 3.3.1 获取 CI 的关联关系

```
GET /api/v1/cmdb/instances/:id/relations
```

**请求参数**：
- depth: 展开深度（1-4，默认 1）

**响应数据**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "nodes": [
      {
        "id": 1,
        "name": "应用A",
        "code": "APP001",
        "model_id": 1,
        "model_name": "应用",
        "model_icon": "AppstoreOutlined",
        "is_center": true
      },
      {
        "id": 2,
        "name": "主机1",
        "code": "HOST001",
        "model_id": 3,
        "model_name": "主机",
        "model_icon": "ServerOutlined",
        "is_center": false
      }
    ],
    "edges": [
      {
        "id": 1,
        "source": 1,
        "target": 2,
        "relation_type_id": 1,
        "relation_type_name": "运行在",
        "source_type": "manual",
        "direction": "directed",
        "style": {"color": "#1890ff"}
      }
    ],
    "out_relations": [
      {
        "id": 1,
        "relation_type_name": "运行在",
        "target_ci_id": 2,
        "target_ci_name": "主机1",
        "target_ci_code": "HOST001",
        "target_ci_model_name": "主机",
        "source_type": "manual",
        "created_at": "2026-02-14T10:00:00Z"
      }
    ],
    "in_relations": [
      {
        "id": 2,
        "relation_type_name": "包含",
        "source_ci_id": 3,
        "source_ci_name": "集群1",
        "source_ci_code": "CLUSTER001",
        "source_ci_model_name": "集群",
        "source_type": "manual",
        "created_at": "2026-02-14T10:00:00Z"
      }
    ]
  }
}
```

#### 3.3.2 新增关系

```
POST /api/v1/cmdb/relations
```

**请求体**：
```json
{
  "source_ci_id": 1,
  "target_ci_id": 2,
  "relation_type_id": 1
}
```

**约束检查**：
1. 唯一性检查：source_ci_id + target_ci_id + relation_type_id 不能重复
2. 自环检查：如果 allow_self_loop 为 false，source_ci_id 不能等于 target_ci_id
3. 模型白名单检查：源 CI 模型必须在 source_model_ids 中，目标 CI 模型必须在 target_model_ids 中
4. 基数限制检查：
   - one_one：源和目标都只能有一个此类型的关系
   - one_many：源可以有多个，目标只能有一个
   - many_many：无限制

**错误响应示例**：
```json
{
  "code": 400,
  "message": "该关系类型不允许此源模型",
  "data": null
}
```

#### 3.3.3 删除关系

```
DELETE /api/v1/cmdb/relations/:id
```

---

### 3.4 拓扑图数据接口

#### 3.4.1 获取全局拓扑图数据

```
GET /api/v1/cmdb/topology
```

**请求参数**：
- model_id: 模型 ID（可选）
- ci_id: CI ID（可选，作为起点）
- keyword: 搜索关键词（可选）
- depth: 展开深度（1-4，默认 1）

**响应数据**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "nodes": [
      {
        "id": 1,
        "name": "应用A",
        "code": "APP001",
        "model_id": 1,
        "model_name": "应用",
        "model_icon": "AppstoreOutlined"
      }
    ],
    "edges": [
      {
        "id": 1,
        "source": 1,
        "target": 2,
        "relation_type_id": 1,
        "relation_type_name": "运行在",
        "direction": "directed",
        "style": {"color": "#1890ff"}
      }
    ]
  }
}
```

#### 3.4.2 导出拓扑图数据

```
GET /api/v1/cmdb/topology/export
```

**请求参数**：
- format: excel / csv（默认 excel）
- 其他参数同获取拓扑图数据

**响应**：文件下载

---

### 3.5 关系触发器接口

#### 3.5.1 获取触发器列表

```
GET /api/v1/cmdb/relation-triggers
```

**请求参数**：
- page: 页码
- per_page: 每页数量
- keyword: 搜索关键词

**响应数据**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "应用-主机引用同步",
        "source_model_id": 1,
        "source_model_name": "应用",
        "target_model_id": 3,
        "target_model_name": "主机",
        "relation_type_id": 1,
        "relation_type_name": "运行在",
        "trigger_type": "reference",
        "trigger_condition": {"source_field": "host_id", "target_field": "id"},
        "is_active": true,
        "description": "应用的host_id字段变化时自动同步关系",
        "created_at": "2026-02-14T10:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "per_page": 20
  }
}
```

#### 3.5.2 新增触发器

```
POST /api/v1/cmdb/relation-triggers
```

**请求体**：
```json
{
  "name": "应用-主机引用同步",
  "source_model_id": 1,
  "target_model_id": 3,
  "relation_type_id": 1,
  "trigger_type": "reference",
  "trigger_condition": {"source_field": "host_id", "target_field": "id"},
  "description": "应用的host_id字段变化时自动同步关系"
}
```

#### 3.5.3 获取触发器详情

```
GET /api/v1/cmdb/relation-triggers/:id
```

#### 3.5.4 更新触发器

```
PUT /api/v1/cmdb/relation-triggers/:id
```

#### 3.5.5 删除触发器

```
DELETE /api/v1/cmdb/relation-triggers/:id
```

#### 3.5.6 启用/禁用触发器

```
PUT /api/v1/cmdb/relation-triggers/:id/toggle
```

---

## 4. 引用属性同步实现

### 4.1 集成点

在 CI 实例保存（创建/更新）时，检查是否有引用类型的触发器，执行同步逻辑。

### 4.2 同步逻辑

```
当 CI 保存时：
1. 获取该 CI 模型的所有启用的 reference 类型触发器
2. 对每个触发器：
   a. 获取源字段的当前值
   b. 获取源字段的旧值（如果是更新）
   c. 如果旧值存在且不等于新值：
      - 删除旧的引用关系
   d. 如果新值存在：
      - 检查目标 CI 是否存在
      - 创建新的引用关系（source_type = reference）
```

### 4.3 CI 删除时的集成

在 CI 删除前，检查是否有引用此字段的触发器，提示用户。

---

## 5. 前端设计

### 5.1 路由配置

在 `frontend/src/router/index.ts` 中添加：

```typescript
// 在 config 子路由中添加
{
  path: 'relation-type',
  name: 'RelationType',
  component: () => import('@/views/config/relation-type/index.vue'),
  meta: { title: '关系类型', icon: 'NodeIndexOutlined', permission: 'relation:view' }
},
{
  path: 'relation-trigger',
  name: 'RelationTrigger',
  component: () => import('@/views/config/relation-trigger/index.vue'),
  meta: { title: '关系触发器', icon: 'ThunderboltOutlined', permission: 'relation:view' }
}

// 在 cmdb 子路由中添加
{
  path: 'topology',
  name: 'Topology',
  component: () => import('@/views/cmdb/topology/index.vue'),
  meta: { title: '拓扑视图', icon: 'BranchOutlined', permission: 'instance:view' }
}
```

### 5.2 页面结构

```
frontend/src/views/
├── config/
│   ├── relation-type/
│   │   └── index.vue          # 关系类型管理页面
│   └── relation-trigger/
│       └── index.vue          # 关系触发器管理页面
└── cmdb/
    ├── topology/
    │   └── index.vue          # 全局拓扑视图
    └── instance/
        └── components/
            └── CiDetailDrawer.vue  # 增加关系拓扑 Tab
```

### 5.3 技术选型

| 功能 | 选型 | 说明 |
|------|------|------|
| 拓扑图库 | AntV G6 | 功能强大，适合关系图谱展示 |
| Excel 导出 | xlsx | 前端导出 Excel |
| CSV 导出 | 原生 | 前端导出 CSV |

### 5.4 新增 API 模块

创建 `frontend/src/api/cmdb-relation.ts`：

```typescript
import request from '@/utils/request'

// 关系类型
export function getRelationTypes(params: any) {
  return request.get('/api/v1/cmdb/relation-types', { params })
}

export function createRelationType(data: any) {
  return request.post('/api/v1/cmdb/relation-types', data)
}

export function updateRelationType(id: number, data: any) {
  return request.put(`/api/v1/cmdb/relation-types/${id}`, data)
}

export function deleteRelationType(id: number) {
  return request.delete(`/api/v1/cmdb/relation-types/${id}`)
}

// 关系实例
export function getInstanceRelations(id: number, params?: any) {
  return request.get(`/api/v1/cmdb/instances/${id}/relations`, { params })
}

export function createRelation(data: any) {
  return request.post('/api/v1/cmdb/relations', data)
}

export function deleteRelation(id: number) {
  return request.delete(`/api/v1/cmdb/relations/${id}`)
}

// 拓扑图
export function getTopology(params: any) {
  return request.get('/api/v1/cmdb/topology', { params })
}

export function exportTopology(params: any) {
  return request.get('/api/v1/cmdb/topology/export', { params, responseType: 'blob' })
}

// 关系触发器
export function getRelationTriggers(params: any) {
  return request.get('/api/v1/cmdb/relation-triggers', { params })
}

export function createRelationTrigger(data: any) {
  return request.post('/api/v1/cmdb/relation-triggers', data)
}

export function updateRelationTrigger(id: number, data: any) {
  return request.put(`/api/v1/cmdb/relation-triggers/${id}`, data)
}

export function deleteRelationTrigger(id: number) {
  return request.delete(`/api/v1/cmdb/relation-triggers/${id}`)
}

export function toggleRelationTrigger(id: number) {
  return request.put(`/api/v1/cmdb/relation-triggers/${id}/toggle`)
}
```

---

## 6. 实施步骤

### 阶段 1：后端开发（5 天）

1. **数据模型调整**（0.5 天）
   - 修改 RelationType 模型
   - 创建数据库迁移脚本

2. **关系类型 API**（0.5 天）
   - 实现 CRUD 接口
   - 添加参数校验

3. **关系实例 API**（1 天）
   - 实现 CRUD 接口
   - 实现关系约束检查逻辑

4. **拓扑图 API**（1 天）
   - 实现拓扑图数据查询
   - 实现数据导出

5. **关系触发器 API**（0.5 天）
   - 实现 CRUD 接口

6. **引用属性同步**（1 天）
   - 集成到 CI 保存逻辑
   - 实现同步逻辑

7. **CI 删除处理**（0.5 天）
   - 集成到 CI 删除逻辑
   - 添加关系检查和提示

### 阶段 2：前端基础功能（3 天）

1. **关系类型管理页面**（1 天）
   - 列表页面
   - 新增/编辑表单

2. **CI 详情页关系 Tab**（1.5 天）
   - 拓扑图视图
   - 关系列表视图
   - 新增/删除关系功能

3. **前端基础**（0.5 天）
   - 新增 API 模块
   - 路由配置

### 阶段 3：拓扑图开发（7 天）

1. **集成 G6**（1 天）
   - 安装依赖
   - 基础组件封装

2. **CI 详情页拓扑**（2 天）
   - 基础展示
   - 层数选择
   - 节点点击侧边栏

3. **全局拓扑视图**（3 天）
   - 搜索过滤
   - 多种布局算法
   - 节点展开/收起

4. **编辑模式**（0.5 天）
   - 拖拽连线创建关系
   - 点击删除关系

5. **数据导出**（0.5 天）
   - Excel 导出
   - CSV 导出

### 阶段 4：关系触发器（2 天）

1. **触发器管理页面**（1.5 天）
   - 列表页面
   - 新增/编辑表单

2. **集成测试**（0.5 天）
   - 引用触发器测试

### 阶段 5：测试与联调（3 天）

1. **功能测试**（1.5 天）
2. **性能测试**（0.5 天）
3. **Bug 修复**（1 天）

---

## 7. 风险与注意事项

### 7.1 数据迁移
- 新增字段需要有默认值
- 考虑现有数据的兼容性

### 7.2 性能
- 拓扑图查询需要限制节点数量
- 考虑分页或懒加载

### 7.3 数据一致性
- 引用属性同步需要考虑事务
- 删除 CI 时要级联处理关系

---

## 8. 附录

### 8.1 错误码定义

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 关系约束冲突 |

### 8.2 基数限制枚举

| 值 | 说明 |
|----|------|
| one_one | 1:1 |
| one_many | 1:N |
| many_many | N:N |

