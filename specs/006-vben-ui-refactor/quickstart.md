# Quickstart: Frontend Vben UI Refactor

## Preconditions

- Working directory: `/Users/peter/Documents/arco/frontend`
- Use existing dependencies in `frontend/node_modules`
- Do not modify backend code or non-frontend services

## Phase A - Layout and Theme Foundation

1. Update `src/assets/styles/index.css` with global theme variables and page surface utilities.
2. Update `src/App.vue` to map light/dark theme state into Ant Design Vue tokens.
3. Refactor `src/layouts/BasicLayout.vue` to:
   - use fixed viewport layout
   - add breadcrumb rendering
   - preserve menu visibility and route syncing
   - preserve notification, language, theme, and user actions
4. Validate key routes manually:
   - `/dashboard`
   - `/cmdb/instance`
   - `/monitoring/dashboard`
   - `/system/user`

## Phase B - Core Page Surface Rollout

1. Apply global page classes to representative pages:
   - dashboard
   - notifications
   - profile
   - license
2. Normalize page headers, toolbars, cards, tables, and form sections.
3. Extend page-surface rules to additional CMDB, monitoring, config, and system pages.

## Phase C - Polish and Verification

1. Sweep remaining pages for spacing, borders, and dark theme readability.
2. Validate responsive behavior in narrow viewports.
3. Run:

```bash
cd /Users/peter/Documents/arco/frontend
npm run typecheck
npm run build
```

4. Perform manual regression:
   - login and logout
   - menu navigation and permission-controlled visibility
   - notification popover and unread count
   - language switching
   - theme switching

## Resume Guidance For Later Sessions

- Start from `specs/006-vben-ui-refactor/tasks.md`
- Check which phase tasks are already completed in code
- Continue from the first unchecked task in the active phase
- Use `specs/006-vben-ui-refactor/manual-regression.md` for T024 browser verification

## Progress Notes (2026-03-25)

- 已完成：
  - `frontend/src/assets/styles/index.css` 已建立亮暗主题 CSS 变量、全局页面表面类和基础 Ant 组件外观收口
  - `frontend/src/App.vue` 已接入 `data-theme` 同步和 Ant Design Vue light/dark token
  - `frontend/src/layouts/BasicLayout.vue` 已改为固定视口布局、亮色商务化侧边栏、头部面包屑和统一动作区
  - `frontend/src/components/notifications/NotificationBadge.vue` 已接入新主题变量
  - 代表页面已接入新表面体系：`dashboard/index.vue`、`notifications/index.vue`、`profile/index.vue`、`license/index.vue`
  - 第二批核心页面已接入统一表面：`system/user`、`system/log`、`system/role`、`system/department`、`system/custom-view`、`config/model`、`config/relation-type`、`config/relation-trigger`、`config/batch-scan`、`config/batch-scan-config`、`config/dictionary`、`cmdb/instance`、`cmdb/search`、`cmdb/history`、`cmdb/topology`、`cmdb/topology-template`、`cmdb/topology-manage`、`cmdb/TriggerConfig`、`monitoring/dashboard`、`monitoring/bulletin`、`monitoring/collector`、`monitoring/labels`、`monitoring/status`、`monitoring/alert/index`、`monitoring/alert/group`、`monitoring/alert/inhibit`
  - 第三批告警长尾页已接入统一壳层：`monitoring/alert/notice`、`monitoring/alert/notice-receiver`、`monitoring/alert/setting`、`monitoring/alert/silence`、`monitoring/alert/integration`、`monitoring/alert/detail`
  - 通知辅助页已接入统一壳层：`notifications/send.vue`、`notifications/detail.vue`
  - 设计与自定义视图页已接入统一壳层：`system/custom-view/design.vue`、`custom-view/view.vue`、`cmdb/topology-template/edit.vue`
  - 已开始 T020/T021 收口：`BasicLayout.vue` 头部窄屏间距与尺寸已细调，全局小屏工具栏在 `index.css` 增加了自适应规则；`notifications/detail.vue`、`system/log/index.vue` 已替换一批浅色写死文本/表面样式
  - 第二轮 T020/T021 收口已覆盖：全局 `--app-*` 主题 alias、`system/config/index.vue`、`cmdb/topology-manage/index.vue`、`config/model/components/ModelDesigner.vue`、`config/model/index.vue`
  - 第三轮 T020/T021 收口已覆盖：`dashboard/index.vue` 的 KPI 内联色值、`system/user/index.vue` 的头像/按钮内联色值、`cmdb/topology/index.vue` 的图标与标签主色已改为主题驱动
  - T013/T024 代码侧回归已推进：`BasicLayout.vue` 已为 `SystemSendNotification`、`SystemNotificationDetail`、`SendNotification`、`NotificationDetail`、`TopologyTemplateEdit`、`CustomViewDesign`、`MonitoringTargetDetail`、`MonitoringAlertDetail` 补虚拟父级 breadcrumb，并统一 `/notifications*` 的菜单高亮归属
  - 第四轮 T020/T021 收口已覆盖：`profile/index.vue` 的卡片顶层高光、头像渐变、头像遮罩已切到主题变量；`cmdb/TriggerConfig.vue` 的触发器数量 badge 已切到主题成功色变量
  - 构建收口已推进：`frontend/vite.config.ts` 已为 `vue-core`、`echarts`、`@antv/g6`、`wangeditor`、`socket.io`、`yaml` 等重依赖补充稳定的 `manualChunks`；当前 `npm run build` 已不再输出 chunk 循环告警，非阻断输出仅剩 Sass legacy JS API deprecation
  - T024 清单已落地：新增 `specs/006-vben-ui-refactor/manual-regression.md`，已把登录、导航、通知、语言、主题、隐藏路由 breadcrumb 等检查项拆成 `Pending / Code-reviewed / Passed / Failed`；同时 `BasicLayout.vue` 去掉通知点击日志，通知弹层组件切到主题变量
  - 通知链路细修已继续推进：`components/notifications/NotificationItem.vue`、`NotificationCenter.vue`、`views/notifications/index.vue`、`views/notifications/detail.vue` 中通知标签默认色、未读高亮点、附件 hover、弹层头尾边框/背景等已切到主题变量；通知相关目录里这批明显浅色硬编码已清空
  - 登录页细修已推进：`views/login/index.vue` 的右侧表单区、输入框、按钮、锁定弹窗、验证码边框已切到主题变量；剩余保留的硬编码主要是品牌视觉区的背景图、玻璃层和少量阴影，不属于当前主题割裂问题
  - 通用组件层细修已推进：`components/RichEditor.vue` 已切到统一边框/表面变量；`components/monitoring/metrics/MetricTrendDialog.vue` 的图表主色和分割线改为 CSS 主题变量驱动，`MonitorMetricsPanel.vue` 的辅助文字色已统一到 `--app-text-muted`
  - 高频弹层组件细修已推进：`views/cmdb/instance/components/CiInstanceModal.vue` 的空态和字段分组卡片已切到主题变量；`CiDetailDrawer.vue` 的属性区表面、变更历史高亮、文件链接、拓扑图容器/G6 主色已切到主题变量；`components/notifications/NotificationList.vue` 的空态和加载区也已统一表面风格
  - CMDB/System 页面细修已继续推进：`views/cmdb/history/index.vue`、`search/index.vue`、`instance/index.vue` 里的查看链接、变更高亮、批量栏、树节点辅助文字、批量编辑标签等已切到主题变量；`views/system/log/index.vue` 的用户头像背景也已改为主题主色
  - `BasicLayout.vue` 的 header breadcrumb 已再次精修：从“标题 + 次级 breadcrumb”改成以 breadcrumb 为主的导航条，补路由 `meta.icon` 图标映射、当前项胶囊态、上级项 hover 态，以及移动端回退到当前页标题
  - 已参考 `vue-vben-admin-main` 的设计 token 与菜单实现，抬高当前系统的基础字号、Ant Design Vue `fontSize/controlHeight`、侧栏宽度与折叠宽度，并同步放大 `BasicLayout.vue` 的 logo、header、breadcrumb、菜单文字与菜单项高度，以改善高分辨率浏览器下的可读性和触达面积
  - 已继续处理一批低风险长尾暗色/响应式项：`components/notifications/NotificationCenter.vue` 的弹层宽度改为响应式；`views/config/dictionary/index.vue`、`views/config/batch-scan-config/index.vue`、`views/custom-view/view.vue`、`views/monitoring/alert/integration.vue`、`views/monitoring/alert/group.vue`、`views/monitoring/alert/notice.vue` 的硬编码辅助文字/背景/链接色已切到主题变量；`views/monitoring/bulletin/index.vue`、`views/monitoring/collector/index.vue`、`views/monitoring/target/detail.vue` 的统计色值已切到主题变量
  - 新一轮长尾暗色/响应式收口已推进：`views/system/config/index.vue` 已切到 `app-page` 壳层，底部保存栏从写死侧栏偏移改为 `sticky` 收口；`views/monitoring/target/index.vue` 已切到统一 page-surface、分类侧栏在窄屏下自动堆叠、筛选表单在小屏下改为单列；`views/monitoring/target/detail.vue` 已切到 `app-page` 壳层，详情头部和告警统计在窄屏下改为自适应布局
- 构建验证：
  - `npm run build` 已再次通过（本轮新增页面补齐后）
  - `npm run typecheck` 已通过（2026-03-26 本轮已清理请求类型导出、图形页/模板页窄类型和上传声明等阻塞项）
  - 非阻断提示仍存在：Sass legacy JS API deprecation
- 下一步优先级：
  1. 继续完成 T020-T021：优先处理仍含图形页运行时 fallback 色值或复杂画布逻辑的页面，如 `views/monitoring/template/index.vue`、`views/monitoring/alert/components/AlertTopology.vue`、`views/cmdb/topology-manage/index.vue`、`views/monitoring/dashboard/index.vue`
  2. 完成 T013/T024：执行真实浏览器人工回归，重点验证 dashboard / cmdb / monitoring / system 的壳层高亮、滚动、breadcrumb、通知弹层、主题切换和语言切换
  3. 如需交付收尾，再单独评估是否处理 `npm run typecheck` 的既有历史问题
