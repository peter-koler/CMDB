任务：参考 vue-vben-admin 深度重构 前端代码
角色设定：你是一位精通 Ant Design Vue 4.x 的高级前端专家，具备极强的系统性思维，擅长通过重构全局样式和组件规范来实现 vue-vben-admin 的高端商务感。拥有极高的 UI/UX 审美，尤其擅长模仿 vue-vben-admin 的极简商务风格。我把 vue-vben-admin-main 的代码放在 vue-vben-admin-main/ 目录下面。你有需要可以参考
核心目标：
请基于我的前端代码进行重构。请协助我重构整个监控平台的 UI。不仅仅是布局，还包括所有的列表页、详情页、配置页和仪表盘。 包括“深色渐变+传统布局”转型为“纯白商务+固定视口滚动”的 ，
1. 全局设计规范 (Global Design System)
配色方案：全站背景、卡片背景、容器背景统一使用纯白色 (#ffffff)。移除所有深色渐变和厚重的投影。
边框规范：统一使用 1px solid #f0f0f0 细边框替代阴影。
间距规范：内容区内边距统一为 16px 或 24px，确保视觉上的“呼吸感”。
主色调：使用 Vben 经典的业务蓝 (#0960bd) 作为主色，主要用于按钮、链接、进度条和激活状态
1. 布局骨架重构 (100vh Layout)
高度锁定：最外层 .basic-layout 必须设为 height: 100vh; overflow: hidden;。
侧边栏 (Sider)：固定高度为 100vh，背景设为纯白色。
头部 (Header)：固定在顶部，高度设为 48px 或 56px。
内容区 (Content)：设置 height: calc(100vh - header_height); overflow-y: auto;。确保只有内容区滚动，侧边栏和头部始终纹丝不动。
2. Vben 视觉规范 (Visual Aesthetics)
配色方案：彻底移除所有 linear-gradient 蓝色渐变。全站背景（Sider、Header、Menu）统一使用纯白色 (#ffffff)。
边框细节：移除所有 box-shadow 阴影，改用 1px solid #f0f0f0 的极细灰色边框来分隔 Sider、Header 和 Content。
菜单美化：
a-menu 切换为 theme="light"。
激活态 (Active)：参考 Vben 规范，选中项背景色使用 rgba(9, 96, 189, 0.1)，并在菜单项的左侧增加一个 3px 宽的蓝色垂直指示条（或根据折叠状态调整）。
图标与文字：默认颜色为 #666，激活时变为 Vben 标志性的业务蓝 (#0960bd)。
3. 交互与组件细节
禁止添加 Tabs 组件：保持顶部 Header 极致简洁，不要添加多页签功能。
面包屑 (Breadcrumb)：在 Header 左侧、折叠按钮旁增加动态面包屑。
Logo 区域：背景改为纯白，与菜单融为一体。优化折叠动画，确保折叠后 Logo 图标居中且美观。
用户信息与通知：保持现有的 NotificationBadge 和用户头像下拉菜单，但样式需调优为更扁平的商务风格。
逻辑严苛保留：在修改样式时，严禁改动任何 v-if 权限判断、API 请求逻辑和 Vue 生命周期。
TypeScript 规范：保持现有的类型定义，确保重构后的代码无 TS 报错。
样式方案：优先使用全局 less 变量定义颜色和间距，方便后期统一调整。
4. 业务逻辑严苛保留
权限系统：严禁修改或删除 hasPermission 和 hasAnyPermission 函数及其调用逻辑。
数据加载：保留 onMounted 中的站点配置加载、自定义视图获取以及 WebSocket 通知初始化逻辑。
路由同步：保留 watch 路由变化并执行 updateSelectedKeys 的逻辑，确保菜单高亮状态准确。
全量菜单：必须完整保留现有的 CMDB、监控管理、告警中心、系统设置等所有子菜单项。
禁止修改后端代码及 manage-go 和collect-go 等后端代码。
操作过程
1、请你使用 plan 模型先做一个 plan 计划，包括重构的范围、时间、成本、资源等。
2、根据 plan 计划，开始重构。
3、在重构过程中，保持与我保持沟通，及时反馈重构进度和问题。
4、重构完成后，进行测试，确保所有功能正常运行。
交付要求：
前端代码没有报错，能够正常运行。

