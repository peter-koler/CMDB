# Implementation Plan: CMDB 拓扑管理功能优化

**Date**: 2026-02-24  
**Spec**: [/Users/peter/Documents/arco/docs/CMDB 拓扑管理功能优化需求规格说明书.ini](/Users/peter/Documents/arco/docs/CMDB%20拓扑管理功能优化需求规格说明书.ini)  
**Input**: 功能规格说明书（物理/业务层级、聚合钻取、数据治理、视图管理与 RBAC）

## 1. Summary

本次实现目标是把当前 CMDB 拓扑从“单图展示”升级为“可治理、可分权、可钻取”的视图体系：
1. 支持物理层级树与业务层级树两种标准视图。
2. 支持分组容器框、智能聚合、层级钻取与面包屑导航。
3. 支持未分配资源池拖拽治理并实时回写 CMDB 关系数据。
4. 支持自定义视图（动态规则 / 静态集合）、自定义层级模型、按角色分配视图权限及默认首页视图。

---

## 2. 不清楚点与默认假设

以下是从规格中识别的关键不确定项；本计划先给默认实现口径，后续可按你确认调整。

### 2.1 需确认项
1. 物理层级与业务层级的数据映射字段是否已有统一规范（如 `dc_id/zone_id/rack_id`、`business_unit/app/service`）？
 回答：没有统一，参考 CMDB 数据模型
2. “实例资源 (Instance)”是否仅指 CI 实例，还是包含容器 Pod/云原生对象？
  回答：仅指 CI 实例
3. 聚合阈值是否全局统一（默认 10）还是允许按视图自定义？
  回答：允许按视图自定义
4. 静态集合视图是否需要保存节点坐标（用于汇报大屏）？
  回答：需要保存节点坐标、缩放比例和分组展开状态
5. 未分配资源池拖拽治理是否要求记录审计日志（建议必须记录）？
  回答：建议记录审计日志，对象：`ci_relation`/`ci_instance`，操作：`UPDATE`
6. RBAC 中“一个用户多个角色”时默认视图的选择优先级规则是什么？
  回答：按用户显式设置 > 角色优先级最高 > 系统默认视图
7. 全局搜索范围是否包含“已下线/停用 CI”？
  回答：不包含
8. 性能指标“1000+ 节点不卡顿”的验收口径是客户端 FPS 还是接口时延 + 首屏渲染时长？
  回答：客户端 

### 2.2 默认假设（若未特别说明按此执行）
1. 物理/业务层级均基于 CI 属性字段与 CI 关系推导，缺失字段的节点进入“未分配”。
2. 聚合阈值支持“全局默认 + 视图级覆盖”。
3. 静态视图保存节点坐标、缩放比例和分组展开状态。
4. 拖拽治理写入审计日志（对象：`ci_relation`/`ci_instance`，操作：`UPDATE`）。
5. 多角色默认视图按“用户显式设置 > 角色优先级最高 > 系统默认视图”解析。

### 2.3 已确认并固化的编码约束
1. 层级构建必须依赖“层级映射配置表”，禁止硬编码 `dc/zone/rack` 等字段。
2. 未分配资源统一基于关系事实判定（指定层级关系类型下无父关系），不引入双事实源。
3. 搜索多视图命中时按“用户默认 > 当前视图 > 角色优先级最高 > 系统默认”跳转。
4. 权限分为 `view/layout_edit/governance_edit` 三类，前后端双重校验。
5. 聚合按容器内同类型节点分桶计数，点击聚合默认进入列表浮层。
6. 拖拽治理必须落审计日志（old/new parent、view、operator、time）。

---

## 3. Technical Context

**Language/Version**: Python 3.11, TypeScript, Vue 3  
**Primary Dependencies**: Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, AntV G6 5.x, Ant Design Vue 4  
**Storage**: SQLite（开发）, PostgreSQL/MySQL（生产）  
**Testing**: pytest + 前端手工回归（后续补 Vitest/组件测试）  
**Target Platform**: Web（前后端分离）  
**Performance Goals**: 1000+ 节点聚合模式下首屏可交互 <= 2s、常规交互 FPS >= 30、下钻加载 <= 1s  
**Constraints**: 不破坏现有 CMDB 关系管理主流程与 CI 详情拓扑能力

---

## 4. Constitution Check

| 原则 | 状态 | 说明 |
|------|------|------|
| 模块化架构优先 | ✓ 通过 | 新增视图管理、拓扑查询、治理服务模块，避免路由层堆逻辑 |
| API 优先设计 | ✓ 通过 | 先定义视图/拓扑/治理接口，再落前端 |
| 数据完整性与审计 | ✓ 通过 | 拖拽治理、视图权限变更记录审计 |
| 可观测与可回滚 | ✓ 通过 | 关键操作留痕，可通过关系变更记录回溯 |
| 测试与验收闭环 | ✓ 通过 | P0/P1/P2 每阶段定义验收用例 |

---

## 5. Project Structure

### 5.1 Documentation

```text
docs/
├── CMDB 拓扑管理功能优化需求规格说明书.ini
└── plan.md  # 本文件
```

### 5.2 Source Code（规划）

```text
backend/app/
├── models/
│   ├── topology_view.py           # 新增：拓扑视图定义、授权映射、默认视图配置
│   ├── topology_hierarchy.py      # 新增：层级模型定义
│   └── ci_instance.py             # 扩展：归属字段/父子关联辅助方法
├── services/
│   ├── topology_query_service.py  # 新增：层级构建、聚合、钻取查询
│   ├── topology_view_service.py   # 新增：动态/静态视图解析
│   └── topology_governance.py     # 新增：未分配资源治理与拖拽落库
├── routes/
│   ├── cmdb_topology.py           # 新增：拓扑主 API
│   └── cmdb_view.py               # 新增：视图管理 + RBAC API

frontend/src/
├── api/
│   ├── topology.ts                # 扩展：钻取、搜索、聚合、治理
│   └── topology-view.ts           # 新增：视图管理与授权
├── views/cmdb/
│   ├── topology/index.vue         # 扩展：层级树、面包屑、聚合、搜索定位
│   ├── topology/components/
│   │   ├── GroupBoxPanel.vue      # 新增：容器框控制
│   │   ├── AggregateListModal.vue # 新增：聚合列表浮层
│   │   ├── UnassignedSidebar.vue  # 新增：未分配资源池
│   │   └── BreadcrumbNav.vue      # 新增：面包屑
│   └── topology-view/             # 新增：视图管理页面（动态/静态）
└── router/index.ts                # 扩展：视图菜单和权限挂载
```

---

## 6. Data Model Plan

## 6.1 新增实体
1. `topology_views`
- `id`, `name`, `code`, `view_type(dynamic/static)`, `hierarchy_model_id`, `rule_config(json)`, `layout_config(json)`, `is_active`, `created_by`, timestamps

2. `topology_hierarchy_models`
- `id`, `name`, `code`, `levels(json)`（如 `[{level:1,type:'dc'}, ...]`）, `is_system`, timestamps

3. `topology_view_roles`
- `id`, `view_id`, `role_id`

4. `topology_user_defaults`
- `id`, `user_id`, `view_id`

5. `topology_governance_logs`
- `id`, `ci_id`, `old_parent_id`, `new_parent_id`, `view_id`, `operator_id`, `created_at`

## 6.2 复用/扩展字段
1. `ci_instances` 复用现有关联属性；必要时增加 `parent_ci_id` 索引（若现有关系结构无法高效过滤未分配节点）。
2. `cmdb_relations` 继续作为关系事实源，拓扑层以查询聚合为主，不复制关系数据。

---

## 7. API Contract Plan

## 7.1 拓扑查询与交互
1. `GET /api/v1/cmdb/topology/views`：获取当前用户可见视图列表
2. `GET /api/v1/cmdb/topology/views/{view_id}/graph`：按层级返回当前层节点/边/分组
3. `GET /api/v1/cmdb/topology/views/{view_id}/drilldown`：按节点下钻
4. `GET /api/v1/cmdb/topology/views/{view_id}/search?q=`：全局搜索并返回定位路径
5. `GET /api/v1/cmdb/topology/views/{view_id}/aggregate/{group_id}`：聚合列表数据
6. `GET /api/v1/cmdb/topology/views/{view_id}/unassigned`：未分配资源池
7. `POST /api/v1/cmdb/topology/views/{view_id}/governance/reassign`：拖拽治理落库

## 7.2 视图管理与授权
1. `POST /api/v1/cmdb/topology/view-builder`：创建视图（动态/静态）
2. `PUT /api/v1/cmdb/topology/view-builder/{id}`：更新视图规则/布局
3. `POST /api/v1/cmdb/topology/view-builder/{id}/roles`：绑定角色
4. `POST /api/v1/cmdb/topology/view-builder/{id}/default`：设置默认视图
5. `GET /api/v1/cmdb/topology/hierarchy-models`：层级模型列表

---

## 8. Phase Plan（按优先级）

## Phase P0（先解决“乱”）
范围：需求 1、2、3、5、9(A)

交付项：
1. 物理层级树、业务层级树基础查询。
2. 分组容器框渲染（标题、展开/收起）。
3. 下钻交互（双击进入下一层，仅渲染子层）。
4. 动态规则视图创建与保存。

验收标准：
1. 进入视图默认仅加载顶层节点。
2. 双击节点 1 秒内完成下钻渲染。
3. 同父节点资源在容器框内显示，不出现游离节点。

## Phase P1（治理 + 分权）
范围：需求 8、11

交付项：
1. 未分配资源池侧边栏与拖拽治理流程。
2. 拖拽确认后实时写库并刷新图。
3. 视图与角色绑定、菜单权限过滤、默认视图加载。

验收标准：
1. Parent_ID 为空资源可在侧栏完整列出。
2. 拖拽治理后 2 秒内图上位置与关系更新。
3. 不同角色登录后看到的视图集合严格隔离。

## Phase P2（体验增强）
范围：需求 4、6、7

交付项：
1. 智能聚合（阈值配置、聚合图标数量展示）。
2. 聚合点击弹出列表浮层，支持搜索定位。
3. 面包屑导航。
4. 全局搜索与自动展开定位高亮。

验收标准：
1. 聚合模式下 1000+ 节点可操作（拖拽/缩放/点击）。
2. 搜索命中后自动展开路径并高亮目标。
3. 面包屑点击可正确返回任意祖先层级。

---

## 9. 任务分解（可直接排期）

1. 后端数据层：新增 `topology_views`/`hierarchy_models`/授权/治理日志迁移脚本。  
2. 后端服务层：实现层级构建、聚合计算、钻取、搜索定位、未分配查询与重绑定。  
3. 后端接口层：完成视图管理 + 拓扑查询 + 治理 API 并接入 RBAC。  
4. 前端拓扑页：接入视图切换、下钻、面包屑、聚合浮层、未分配侧栏拖拽。  
5. 前端管理页：视图创建（动态/静态）、层级模型配置、角色授权、默认视图设置。  
6. 回归测试：功能、权限、性能、异常路径（无归属、环路、空层级）。  
7. 文档与培训：更新需求规划文档、操作手册、演示脚本。

---

## 10. 风险与对策

1. **关系数据质量不一致**：历史数据缺字段导致层级断裂。  
对策：提供“未分配资源池 + 批量修复脚本 + 数据质量看板”。

2. **大图渲染性能风险**：节点过多时 UI 卡顿。  
对策：默认顶层懒加载 + 聚合阈值 + 列表浮层替代“炸开”。

3. **RBAC 误配风险**：角色授权冲突导致越权/无权。  
对策：权限优先级规则固化，提供“权限预览”接口。

4. **拖拽治理误操作**：误拖导致关系错误。  
对策：二次确认 + 审计日志 + 可回滚（按治理日志反向操作）。

---

## 11. 验收测试计划

1. 功能验收：按 P0/P1/P2 用户故事逐条验收。  
2. 权限验收：机房运维、业务研发、管理员三类角色交叉验证。  
3. 性能验收：构造 1k/3k 节点样本数据，验证 `TTI<=2s`、`FPS>=30`、`下钻<=1s`。  
4. 数据一致性验收：拖拽治理后检查 `cmdb_relations` 与 CI 详情关系页一致。  
5. 回归验收：现有拓扑视图、CI 详情拓扑、关系管理不回退。

---

## 12. 里程碑建议

1. M1（P0 完成）：5-7 个工作日。  
2. M2（P1 完成）：4-5 个工作日。  
3. M3（P2 完成 + 验收）：4-6 个工作日。

总计建议：13-18 个工作日（单前后端并行开发节奏）。
