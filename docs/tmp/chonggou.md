任务：参考 vue-vben-admin 深度重构 BasicLayout.vue
角色设定：你是一位精通 Vue 3 (Setup)、TypeScript 和 Ant Design Vue 4.x 的顶级前端架构师，拥有极高的 UI/UX 审美，尤其擅长模仿 vue-vben-admin 的极简商务风格。我把 vue-vben-admin-main 的代码放在 vue-vben-admin-main/ 目录下面。你有需要可以参考
核心目标：
请基于我提供的 BasicLayout.vue 源码进行重构。目标是将其从目前的“深色渐变+传统布局”转型为“纯白商务+固定视口滚动”的 Vben 风格。
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
4. 业务逻辑严苛保留
权限系统：严禁修改或删除 hasPermission 和 hasAnyPermission 函数及其调用逻辑。
数据加载：保留 onMounted 中的站点配置加载、自定义视图获取以及 WebSocket 通知初始化逻辑。
路由同步：保留 watch 路由变化并执行 updateSelectedKeys 的逻辑，确保菜单高亮状态准确。
全量菜单：必须完整保留现有的 CMDB、监控管理、告警中心、系统设置等所有子菜单项。
交付要求：
请输出重构后的完整 <template>、<script setup> 和针对布局与菜单细节优化的 <style scoped> (建议使用 Less)