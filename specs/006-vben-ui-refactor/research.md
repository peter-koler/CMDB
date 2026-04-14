# Research: Frontend Vben UI Refactor

## Decision 1: 使用 CSS 变量 + Ant Design Vue Token 的双层主题体系

**Decision**: 在 `frontend/src/assets/styles/index.css` 中定义亮色/暗色 CSS 变量，并在 `frontend/src/App.vue` 中同步 Ant Design Vue 的主题 token。

**Rationale**: 当前项目既有大量自定义样式，也依赖 Ant Design Vue 组件。仅靠组件 token 不足以覆盖布局、卡片、筛选栏、表格和业务容器；仅靠 CSS 变量又无法统一 Ant 组件内建视觉。双层方案改动成本最低，能保留主题切换。

**Alternatives considered**:
- 仅使用 Ant token：无法覆盖现有大量页面级自定义样式。
- 全量切换到 Less 变量体系：当前项目未建立成体系的 Less 管线，重构成本更高。

## Decision 2: 以 BasicLayout 为主切入固定视口架构

**Decision**: 在 `frontend/src/layouts/BasicLayout.vue` 内完成固定视口、固定头部、固定侧边栏和内容区独立滚动的骨架改造。

**Rationale**: 当前滚动与主题问题集中在布局根节点。先从主布局切入，可以在不改业务页面逻辑的前提下立即提升全局一致性。

**Alternatives considered**:
- 逐页修正滚动行为：重复劳动大，难以统一。
- 增加新的布局组件并切换所有路由：风险更高，涉及面更大。

## Decision 3: 通用页面表面优先，逐页特化其次

**Decision**: 先建立统一的页面容器、页面头、工具栏、筛选栏、内容卡片和表格容器样式，再把代表性页面接入这些通用表面。

**Rationale**: 本次覆盖范围大，如果每页完全手写重构，容易造成风格漂移，也不利于后续会话接力。

**Alternatives considered**:
- 每个页面独立设计：视觉收敛慢，维护成本高。
- 全量组件化重做：实现周期过长，不适合先完成第一阶段交付。

## Decision 4: 明暗主题都保留，但以亮色商务主题为主轴

**Decision**: 保留 `appStore.theme` 和现有切换入口，默认围绕亮色主题优化，同时为暗色主题提供可读性兼容。

**Rationale**: 用户明确要求保留明暗主题逻辑，且参考项目也支持主题切换。亮色主题是本次目标视觉，暗色主题以兼容稳定为目标。

**Alternatives considered**:
- 移除暗色主题：与用户要求冲突。
- 同时深度设计两套主题：会显著扩大改造范围与周期。

## Decision 5: 明确受保护逻辑边界，重构仅限模板结构与样式层

**Decision**: 将权限函数、菜单加载、站点配置、通知初始化、WebSocket、路由同步等定义为受保护逻辑，禁止改动其行为语义。

**Rationale**: 这是本次需求中最关键的风险控制点，避免 UI 重构引入功能回退。

**Alternatives considered**:
- 顺手整理这些逻辑：收益不高，且容易越界成业务重构。
