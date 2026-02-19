<!--
  Sync Impact Report
  
  Version Change: 0.0.0 → 1.0.0 (Initial ratification)
  
  Modified Principles: None (initial creation)
  
  Added Sections:
  - Core Principles (all 5 principles newly defined)
  - Additional Constraints
  - Development Workflow
  - Governance
  
  Removed Sections: None
  
  Templates requiring updates:
  ✅ spec-template.md (no changes needed)
  ✅ plan-template.md (no changes needed)
  ✅ tasks-template.md (no changes needed)
  
  Follow-up TODOs: None
-->

# Arco CMDB 平台 Constitution

## Core Principles

### I. 模块化架构优先 (Modular Architecture First)

**MUST**: 新功能必须按独立模块设计，避免紧耦合；每个模块必须有清晰的接口定义；模块间通过标准 API 或服务层通信，禁止直接跨模块访问数据库。

**Rationale**: CMDB 平台功能复杂（模型、实例、关系、拓扑等），模块化设计确保各功能可以独立开发、测试和部署，同时方便后续扩展和维护。

### II. 通知中心基础设施 (Notification Infrastructure)

**MUST**: 所有用户相关操作（创建、更新、删除、审批等）必须通过统一的通知中心发送站内通知；通知必须支持按用户、角色、部门定向投递；必须提供通知查询、已读/未读管理、历史归档能力。

**Rationale**: 站内通知是平台的通用基础设施，后续所有功能（变更管理、工单系统、告警等）都依赖此能力。统一设计避免重复开发，保证用户体验一致性。

### III. API 优先设计 (API-First Design)

**MUST**: 任何功能必须先定义 API 契约（OpenAPI/Swagger），然后开发后端实现，最后对接前端；API 必须遵循 RESTful 规范；所有 API 变更必须向后兼容或提供版本控制。

**Rationale**: 前后端分离架构要求清晰的接口契约，API 优先确保前后端可以并行开发，同时为未来可能的第三方集成或移动端扩展预留空间。

### IV. 数据完整性与审计 (Data Integrity & Audit)

**MUST**: 所有核心业务数据（模型、CI、关系、配置等）的变更必须记录审计日志；关键操作必须支持软删除而非物理删除；必须提供数据变更历史查询和回溯能力。

**Rationale**: CMDB 是运维的核心数据源，数据准确性和可追溯性至关重要。审计日志帮助排查问题、满足合规要求，软删除防止误操作造成数据丢失。

### V. 测试驱动开发 (Test-Driven Development)

**MUST**: 核心业务逻辑必须先编写单元测试（失败），然后实现功能（通过），最后重构；集成测试必须覆盖关键用户流程；测试覆盖率目标：核心模块 ≥ 80%。

**Rationale**: TDD 确保代码质量和可维护性，自动化测试保障重构和迭代的安全性。CMDB 数据关系复杂，测试是防止回归的关键手段。

## 额外约束

### 技术栈约束

**MUST** 使用以下技术栈：
- 后端：Python 3.11, Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1
- 前端：Vue 3 + TypeScript, Vite 5, Ant Design Vue 4, Pinia
- 拓扑可视化：AntV G6 5.x
- 数据库：关系型数据库（开发使用 SQLite，生产推荐 PostgreSQL/MySQL）

**禁止** 未经评估引入新的框架或重大依赖项。

### 性能标准

**MUST** 满足以下性能指标：
- API 响应时间：P95 < 200ms（简单查询），P95 < 500ms（复杂查询）
- 页面加载时间：首屏 < 3s
- 拓扑渲染：支持 1000+ 节点流畅交互

### 安全要求

**MUST** 遵循以下安全实践：
- 所有 API 端点必须鉴权（JWT Token）
- 敏感操作需要权限校验
- 生产环境必须修改默认密钥和密码
- 用户密码必须使用 bcrypt 加密存储

## 开发流程

### 需求管理流程

1. **需求澄清** (/speckit.clarify): 用户提出需求后，首先澄清功能范围、优先级、验收标准
2. **需求规约** (/speckit.specify): 编写 spec.md，定义用户场景、功能需求、成功标准
3. **技术调研** (/speckit.plan Phase 0): 调研技术方案，识别风险和依赖
4. **数据建模** (/speckit.plan Phase 1): 设计数据模型和 API 契约
5. **任务分解** (/speckit.tasks): 将需求分解为可执行的任务列表

### 代码审查要求

- 所有代码变更必须通过 Pull Request
- PR 描述必须关联对应的需求文档 (spec.md)
- 必须包含测试用例（单元测试或集成测试）
- 必须通过 lint 检查（backend: ruff, frontend: eslint）
- 核心功能变更需要 Code Reviewer 批准

### 质量门禁

- 测试通过率 100%
- 代码风格检查通过
- TypeScript 类型检查通过（前端）
- 无明显的安全漏洞（依赖扫描）

## Governance

### 宪法权威

本 Constitution 是 Arco CMDB 平台开发的最高指导原则，所有技术决策、架构设计和开发实践都必须遵守。当其他文档与本 Constitution 冲突时，以本 Constitution 为准。

### 修订程序

1. **提案**: 任何开发者可以提出修订建议，需说明理由和影响范围
2. **评审**: 由项目负责人或技术负责人评审，评估对现有项目的影响
3. **批准**: 重大修订（影响多个原则）需要团队讨论一致同意
4. **实施**: 批准后更新 Constitution，同步更新相关模板和文档
5. **版本记录**: 在 Sync Impact Report 中记录修订内容

### 版本控制

- **MAJOR**: 原则性变更或移除，可能导致现有功能不符合新规范
- **MINOR**: 新增原则或扩展现有原则，向后兼容
- **PATCH**: 文字澄清、typo 修正、非语义性优化

### 合规检查

- 每个功能开发前必须检查 Constitution 合规性（Constitution Check）
- 代码审查时必须验证是否符合相关原则
- 定期回顾（每季度）检查 Constitution 执行情况和更新需求

**Version**: 1.0.0 | **Ratified**: 2026-02-19 | **Last Amended**: 2026-02-19
