# Data Model: Frontend Vben UI Refactor

## Overview

本次功能不引入新的后端数据模型，数据模型聚焦于前端 UI 结构、主题状态和导航状态。

## Entities

### 1. ThemeTokenSet

表示系统在亮色或暗色模式下使用的一组主题变量。

**Fields**:
- `mode`: `light | dark`
- `colorPrimary`: 主业务色
- `colorBgApp`: 应用背景
- `colorBgContainer`: 卡片/容器背景
- `colorBorder`: 统一边框色
- `colorTextPrimary`: 主文本色
- `colorTextSecondary`: 次文本色
- `colorFillQuaternary`: 轻交互填充色
- `shadowPolicy`: 阴影替代策略（本次以细边框为主）
- `spacingScale`: 页面间距定义

**Relationships**:
- 被 `LayoutShell`、`PageSurface` 和 Ant Design Vue token 同时消费。

### 2. LayoutShell

表示应用级布局骨架。

**Fields**:
- `collapsed`: 侧边栏折叠状态
- `selectedKeys`: 当前菜单选中项
- `openKeys`: 当前菜单展开项
- `breadcrumbItems`: 当前路由对应的面包屑项
- `headerHeight`: 头部高度
- `siderWidth`: 展开侧边栏宽度
- `collapsedWidth`: 折叠侧边栏宽度
- `contentScrollMode`: 内容区独立滚动标识

**Relationships**:
- 依赖 `NavigationState`
- 依赖 `ThemeTokenSet`
- 承载 `ProtectedUILogic`

### 3. NavigationState

表示菜单、路由和面包屑间的同步状态。

**Fields**:
- `routePath`: 当前路由路径
- `selectedMenuKey`: 当前高亮菜单项
- `openMenuGroups`: 当前展开分组
- `customViews`: 动态自定义视图菜单项
- `permissionVisibility`: 基于权限的菜单可见性结果

**Validation Rules**:
- 权限可见性必须完全复用现有权限函数结果
- 自定义视图必须由现有接口加载结果驱动

### 4. PageSurface

表示页面级统一视觉容器。

**Fields**:
- `pageClass`: 页面容器类名
- `pageHeader`: 标题与辅助操作区
- `toolbar`: 按钮、搜索、筛选等操作区
- `contentBlocks`: 卡片、表格、表单、描述区等内容块
- `density`: 页面密度（紧凑 / 标准）
- `responsiveRules`: 窄视口下布局规则

**Relationships**:
- 被仪表盘、列表页、详情页和配置页复用
- 受 `ThemeTokenSet` 控制

### 5. ProtectedUILogic

表示本次重构中禁止修改行为语义的一组逻辑边界。

**Fields**:
- `permissionChecks`: `hasPermission`, `hasAnyPermission`
- `siteConfigLoad`: 站点配置加载逻辑
- `customViewLoad`: 自定义视图加载逻辑
- `notificationInit`: 通知初始化逻辑
- `websocketConnect`: 通知 WebSocket 连接逻辑
- `routeWatchSync`: 路由监听与菜单同步逻辑
- `themeState`: 主题状态切换逻辑

**State Transitions**:
- 可以调整调用位置附近的模板结构或样式绑定
- 不得改变其触发条件、输入输出语义和核心调用顺序
