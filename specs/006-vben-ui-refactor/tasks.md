# Tasks: Frontend Vben UI Refactor

**Input**: Design documents from `/specs/006-vben-ui-refactor/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 本次以类型检查、构建验证和关键路径人工回归为主。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立可恢复的文档与样式入口

- [x] T001 Create feature documentation set in `specs/006-vben-ui-refactor/`
- [x] T002 Audit current layout, theme, and representative pages in `frontend/src/layouts/BasicLayout.vue`, `frontend/src/App.vue`, and `frontend/src/assets/styles/index.css`
- [x] T003 [P] Inventory representative page surfaces under `frontend/src/views/dashboard`, `frontend/src/views/notifications`, `frontend/src/views/profile`, and `frontend/src/views/license`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立所有页面共享的主题与骨架能力

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Define global light/dark design tokens and utility page-surface classes in `frontend/src/assets/styles/index.css`
- [x] T005 Wire Ant Design Vue theme tokens to app theme state in `frontend/src/App.vue`
- [x] T006 Refactor fixed-viewport shell, content scroll behavior, and responsive structure in `frontend/src/layouts/BasicLayout.vue`
- [x] T007 Preserve and restyle notification, language, theme toggle, and user action area in `frontend/src/layouts/BasicLayout.vue`
- [x] T008 Add route-driven breadcrumb rendering without changing route sync behavior in `frontend/src/layouts/BasicLayout.vue`
- [x] T009 Verify protected logic remains intact in `frontend/src/layouts/BasicLayout.vue` for permissions, site config load, custom views, notification init, websocket connect, and route watch sync

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 重构全局布局与设计系统 (Priority: P1) 🎯 MVP

**Goal**: 交付统一的商务化布局骨架和主题基础

**Independent Test**: 登录后访问多个一级页面，确认固定头部、固定侧边栏、内容区独立滚动、菜单高亮正确、明暗主题切换正常。

### Implementation for User Story 1

- [x] T010 [US1] Apply global shell classes and state-driven theme hooks in `frontend/src/layouts/BasicLayout.vue`
- [x] T011 [US1] Normalize sider menu active, hover, collapsed, and submenu styles in `frontend/src/layouts/BasicLayout.vue`
- [x] T012 [US1] Normalize header spacing, breadcrumb alignment, and action surfaces in `frontend/src/layouts/BasicLayout.vue`
- [ ] T013 [US1] Validate dashboard, CMDB, monitoring, and system routes against the new shell in `frontend/src/layouts/BasicLayout.vue`

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 统一核心业务页面样式 (Priority: P2)

**Goal**: 用统一页面表面覆盖核心列表页、详情页、配置页和仪表盘

**Independent Test**: 打开仪表盘、通知中心、个人资料和授权页，确认页面容器、卡片、表格和表单风格一致且功能正常。

### Implementation for User Story 2

- [x] T014 [P] [US2] Refactor dashboard page surface and card hierarchy in `frontend/src/views/dashboard/index.vue`
- [x] T015 [P] [US2] Refactor notification list page surface, search toolbar, and detail modal styling in `frontend/src/views/notifications/index.vue`
- [x] T016 [P] [US2] Refactor profile page card, tab, and form section styling in `frontend/src/views/profile/index.vue`
- [x] T017 [P] [US2] Refactor license page container and upload section styling in `frontend/src/views/license/index.vue`
- [x] T018 [US2] Extend shared page-surface classes for list/detail/config patterns in `frontend/src/assets/styles/index.css`
- [ ] T019 [US2] Roll out shared page-surface classes to additional CMDB, monitoring, config, and system pages under `frontend/src/views/`

**Checkpoint**: User Stories 1 and 2 should both work independently

---

## Phase 5: User Story 3 - 完成长尾页面收口与回归验证 (Priority: P3)

**Goal**: 收口长尾页面、暗色主题和响应式细节，并完成交付验证

**Independent Test**: 主要页面在亮暗主题和窄视口下可用，且类型检查、构建通过。

### Implementation for User Story 3

- [ ] T020 [US3] Sweep remaining pages for spacing, border, and dark-theme readability issues under `frontend/src/views/`
- [ ] T021 [US3] Fix responsive edge cases for header, sider, breadcrumbs, and page content in `frontend/src/layouts/BasicLayout.vue` and `frontend/src/assets/styles/index.css`
- [x] T022 [US3] Run type validation with `frontend/package.json` script `npm run typecheck`
- [x] T023 [US3] Run production build with `frontend/package.json` script `npm run build`
- [ ] T024 [US3] Perform manual regression on login, navigation, notifications, language switch, and theme switch across `frontend/src/layouts/BasicLayout.vue` and representative pages

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 文档同步与后续接力准备

- [x] T025 [P] Update progress notes in `specs/006-vben-ui-refactor/quickstart.md`
- [x] T026 Summarize completed vs remaining rollout pages in `specs/006-vben-ui-refactor/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependency on other stories
- **User Story 2 (P2)**: Depends on the layout and theme foundation from User Story 1
- **User Story 3 (P3)**: Depends on User Stories 1 and 2 being substantially complete

### Parallel Opportunities

- T003 can run while documenting
- T014-T017 can run in parallel after shared page-surface rules stabilize
- Validation tasks T022-T024 can be sequenced after implementation freeze

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate shell behavior before broad page rollout

### Incremental Delivery

1. Deliver shell and theme foundation
2. Roll out representative pages
3. Sweep long-tail pages and validate build/type safety

## Notes

- Do not modify backend code or API behavior
- Do not change permission semantics
- Prefer global styles and reusable page surfaces over one-off page patches
- Keep this file updated so later sessions can resume from the next unchecked task

## Rollout Snapshot (2026-03-25)

- Completed shell/theme foundation:
  - `frontend/src/App.vue`
  - `frontend/src/assets/styles/index.css`
  - `frontend/src/layouts/BasicLayout.vue`
  - `frontend/src/components/notifications/NotificationBadge.vue`
- Completed representative/core pages:
  - `frontend/src/views/dashboard/index.vue`
  - `frontend/src/views/notifications/index.vue`
  - `frontend/src/views/profile/index.vue`
  - `frontend/src/views/license/index.vue`
  - `frontend/src/views/system/user/index.vue`
  - `frontend/src/views/system/log/index.vue`
  - `frontend/src/views/system/role/index.vue`
  - `frontend/src/views/system/department/index.vue`
  - `frontend/src/views/system/custom-view/index.vue`
  - `frontend/src/views/config/model/index.vue`
  - `frontend/src/views/config/relation-type/index.vue`
  - `frontend/src/views/config/relation-trigger/index.vue`
  - `frontend/src/views/config/batch-scan/index.vue`
  - `frontend/src/views/config/batch-scan-config/index.vue`
  - `frontend/src/views/config/dictionary/index.vue`
  - `frontend/src/views/cmdb/instance/index.vue`
  - `frontend/src/views/cmdb/search/index.vue`
  - `frontend/src/views/cmdb/history/index.vue`
  - `frontend/src/views/cmdb/topology/index.vue`
  - `frontend/src/views/cmdb/topology-template/index.vue`
  - `frontend/src/views/cmdb/topology-manage/index.vue`
  - `frontend/src/views/monitoring/dashboard/index.vue`
  - `frontend/src/views/monitoring/bulletin/index.vue`
  - `frontend/src/views/monitoring/collector/index.vue`
  - `frontend/src/views/monitoring/labels/index.vue`
  - `frontend/src/views/monitoring/status/index.vue`
  - `frontend/src/views/monitoring/alert/index.vue`
  - `frontend/src/views/monitoring/alert/group.vue`
  - `frontend/src/views/monitoring/alert/inhibit.vue`
  - `frontend/src/views/monitoring/alert/notice.vue`
  - `frontend/src/views/monitoring/alert/notice-receiver.vue`
  - `frontend/src/views/monitoring/alert/setting.vue`
  - `frontend/src/views/monitoring/alert/silence.vue`
  - `frontend/src/views/monitoring/alert/integration.vue`
  - `frontend/src/views/monitoring/alert/detail.vue`
  - `frontend/src/views/cmdb/TriggerConfig.vue`
  - `frontend/src/views/notifications/send.vue`
  - `frontend/src/views/notifications/detail.vue`
  - `frontend/src/views/system/custom-view/design.vue`
  - `frontend/src/views/custom-view/view.vue`
  - `frontend/src/views/cmdb/topology-template/edit.vue`
- Remaining likely-next rollout targets:
  - top-level pages still needing final shell/page-surface convergence or targeted long-tail cleanup:
    - `frontend/src/views/system/config/index.vue`
    - `frontend/src/views/monitoring/target/index.vue`
    - `frontend/src/views/monitoring/target/detail.vue`
    - `frontend/src/views/monitoring/template/index.vue`
  - graph/chart-heavy files still containing runtime fallback colors or dark-theme edge cases:
    - `frontend/src/views/monitoring/alert/components/AlertTopology.vue`
    - `frontend/src/views/cmdb/topology-manage/index.vue`
    - `frontend/src/views/monitoring/dashboard/index.vue`
  - browser-only validation tasks still pending:
    - `T013`
    - `T024`
