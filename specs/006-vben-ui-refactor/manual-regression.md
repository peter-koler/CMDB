# Manual Regression Checklist

## Scope

- Feature: `006-vben-ui-refactor`
- Frontend root: `/Users/peter/Documents/arco/frontend`
- Purpose: execute T024 against the refactored shell, navigation, notification flow, language switch, and theme switch.

## Status Legend

- `Pending`: not yet validated in a real browser session
- `Code-reviewed`: implementation path inspected in code, but not clicked end-to-end
- `Passed`: manually validated in browser
- `Failed`: manually validated and needs a fix

## Preconditions

- Start frontend from `frontend/`
- Use a valid account with enough permissions to see dashboard, CMDB, monitoring, system, and notification pages
- Prefer checking in both light and dark theme
- Check desktop first, then narrow viewport around `768px` and `576px`
- Current repo does not include Playwright/Cypress/Puppeteer-based browser automation, so rows cannot be upgraded to `Passed` from this terminal-only session alone

## Checklist

| Area | Route / Action | Expected Result | Status |
| --- | --- | --- | --- |
| Auth | `/login` login with valid credentials | success toast, route jump to `/`, protected shell loads | Code-reviewed |
| Auth | `/login` login with invalid credentials | error toast shown, captcha refresh still works | Code-reviewed |
| Auth | login page click License entry | route jump to `/license` and page renders without shell | Code-reviewed |
| Auth | header user menu -> logout | token cleared, route returns to `/login` | Code-reviewed |
| Shell | `/dashboard` | header title and breadcrumb correct, content area scrolls independently from shell | Pending |
| Shell | collapse / expand sider | sider width changes, content layout remains stable, no shell overflow | Pending |
| Shell | narrow viewport around `768px` and `576px` | header actions stay usable, breadcrumb does not break layout | Pending |
| Navigation | `/cmdb/instance` | menu highlights `CMDB / 配置仓库` | Pending |
| Navigation | `/monitoring/dashboard` | menu highlights `监控管理 / 监控展示` | Pending |
| Navigation | `/system/user` | menu highlights `系统管理 / 用户管理` | Pending |
| Navigation | `/notifications` | left menu highlights `系统管理 / 通知管理` | Code-reviewed |
| Breadcrumb | `/system/notification/send` | breadcrumb includes `通知管理 / 发送通知` | Code-reviewed |
| Breadcrumb | `/system/notification/detail/:id` | breadcrumb includes `通知管理 / 通知详情` | Code-reviewed |
| Breadcrumb | `/notifications/send` | breadcrumb includes `通知中心 / 发送通知` | Code-reviewed |
| Breadcrumb | `/notifications/detail/:id` | breadcrumb includes `通知中心 / 通知详情` | Code-reviewed |
| Breadcrumb | `/cmdb/topology-template/edit/:id` | breadcrumb includes `拓扑模板 / 编辑拓扑模板` | Code-reviewed |
| Breadcrumb | `/custom-view-design/:id` | breadcrumb includes `视图管理 / 视图设计` | Code-reviewed |
| Breadcrumb | `/monitoring/target/:id` | breadcrumb includes `监控列表 / 监控任务详情` | Code-reviewed |
| Breadcrumb | `/alert-center/detail/:id` | breadcrumb includes `当前告警 / 告警明细` | Code-reviewed |
| Theme | header theme toggle | `data-theme` switches on `html`, Ant theme and CSS vars switch together | Code-reviewed |
| Theme | open notification popover in dark theme | popover header, list item, footer colors remain readable | Code-reviewed |
| Language | header language switch zh/en | locale stored in `localStorage`, page reloads, Ant locale updates | Code-reviewed |
| Notifications | click bell in header | popover opens, unread badge remains visible, layout does not shift | Pending |
| Notifications | click one notification item | popover closes and route jumps to notification detail | Code-reviewed |
| Notifications | click `查看全部` in popover | route jumps to `/notifications`, popover closes | Code-reviewed |
| Notifications | click `全部已读` | unread count updates and list state refreshes | Pending |
| Profile | `/profile` from header menu | page opens under shell and breadcrumb title is `个人中心` | Pending |
| License | `/license` direct visit | page opens outside shell and upload area remains styled | Pending |

## Notes

- Current code review result indicates T024 is only partially complete; browser execution is still required for any row marked `Pending`.
- If a hidden route fails breadcrumb or menu highlighting, the first file to inspect is `frontend/src/layouts/BasicLayout.vue`.
- Recommended execution order for real browser validation:
  1. `/login`
  2. `/dashboard`
  3. `/cmdb/instance`
  4. `/monitoring/dashboard`
  5. `/system/user`
  6. `/notifications`
  7. `/profile`
  8. `/license`
