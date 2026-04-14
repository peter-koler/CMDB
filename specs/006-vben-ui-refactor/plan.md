# Implementation Plan: Frontend Vben UI Refactor

**Branch**: `[006-vben-ui-refactor]` | **Date**: 2026-03-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-vben-ui-refactor/spec.md`

## Summary

基于现有 `frontend/` Vue 3 + Ant Design Vue 应用，参考 `vue-vben-admin-main/` 的商务化视觉与布局思路，对主布局、全局主题和核心业务页面进行分阶段重构。实现策略以“先统一设计系统与布局骨架，再统一页面表面，再做长尾收口和验证”为主线，严格保留现有权限、路由、API 请求和生命周期逻辑。

## Technical Context

**Language/Version**: TypeScript 5.3 + Vue 3.4 SFC  
**Primary Dependencies**: Ant Design Vue 4.1, Vue Router 4, Pinia 2, ECharts 6, @ant-design/icons-vue 7  
**Storage**: 浏览器本地存储（主题、语言、认证信息）+ 既有后端 API 提供的数据  
**Testing**: `npm run typecheck`, `npm run build`, 关键路径人工回归  
**Target Platform**: 桌面 Web 为主，兼容常见窄视口场景  
**Project Type**: 前后端分离 Web 应用（本次仅改 `frontend/`）  
**Performance Goals**: 首屏主布局稳定渲染；固定视口下滚动流畅；不引入明显额外渲染抖动  
**Constraints**: 不修改后端接口与业务逻辑；保留权限判断、通知初始化、主题切换、路由高亮和动态菜单逻辑；不把 `vue-vben-admin-main/` 直接迁入当前项目  
**Scale/Scope**: 覆盖主布局、全局样式、仪表盘、列表页、详情页、配置页及长尾页面收口

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **模块化架构优先**: 通过全局样式变量、通用页面容器和布局层抽象，避免把样式散落到各业务页面。
- **通知中心基础设施**: 保留通知角标、通知中心、通知初始化和 WebSocket 连接逻辑，不修改其功能边界。
- **API 优先设计**: 本次不修改任何后端 API 契约；仅在前端文档中定义 UI 层契约和受保护逻辑边界。
- **数据完整性与审计**: 不涉及核心业务数据结构和审计逻辑变更。
- **测试驱动开发**: 本次为 UI 重构，执行类型检查、构建验证和关键路径人工回归，确保功能不回退。

**Gate Result**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/006-vben-ui-refactor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-layout-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
frontend/
├── package.json
├── src/
│   ├── App.vue
│   ├── assets/
│   │   └── styles/
│   ├── components/
│   │   └── notifications/
│   ├── layouts/
│   │   └── BasicLayout.vue
│   ├── stores/
│   │   └── app.ts
│   └── views/
│       ├── dashboard/
│       ├── notifications/
│       ├── profile/
│       ├── license/
│       ├── cmdb/
│       ├── monitoring/
│       ├── config/
│       └── system/
└── vite.config.ts
```

**Structure Decision**: 采用现有前端单应用结构；以 `App.vue`、`assets/styles/index.css`、`layouts/BasicLayout.vue` 为全局入口，以页面级样式收口覆盖仪表盘和各业务页面。

## Phase 0: Research Summary

见 [research.md](./research.md)。核心决策包括：
- 使用 CSS 变量和 Ant Design Vue token 双层主题体系
- 在 `BasicLayout.vue` 内完成固定视口骨架与面包屑整合
- 通过全局页面表面类收敛列表/详情/配置页，而不是逐页重写结构
- 保留现有业务逻辑函数和调用顺序，只重构模板结构与样式层

## Phase 1: Design Artifacts

- [data-model.md](./data-model.md): UI 实体、状态与页面表面模型
- [contracts/ui-layout-contract.md](./contracts/ui-layout-contract.md): 布局和受保护逻辑契约
- [quickstart.md](./quickstart.md): 分阶段实施与验证步骤

## Delivery Strategy

### Phase A - 设计系统与布局骨架

- 统一 CSS 变量和 Ant token
- 重构 `BasicLayout.vue`
- 接入动态面包屑
- 固定视口与内容区滚动
- 校准头部、侧边栏、通知与用户操作区的亮暗主题表现

### Phase B - 核心页面统一

- 仪表盘卡片、图表面板、工具栏统一
- 列表页筛选区、操作区、表格容器统一
- 详情页/配置页/表单页容器统一
- 核心页面示范性覆盖并沉淀通用样式

### Phase C - 长尾收口与验证

- 长尾业务页面补齐
- 亮暗主题细节修正
- 响应式与滚动冲突修正
- `typecheck`、`build` 和关键路径回归

## Estimated Effort

- **时间**: 约 3 个阶段的连续重构工作，建议按会话逐步推进并在每阶段后验证
- **成本**: 主要为前端实现、样式整理和人工回归成本，不涉及后端迁移或数据库成本
- **资源**: 1 名前端实施者即可推进；若多人协作，可按布局层 / 页面层 / 验证层并行分工

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | - | - |
