# 规格分析报告：站内通知模块

**功能**: 004-notification-module  
**分析日期**: 2026-02-19  
**分析范围**: spec.md, plan.md, tasks.md  
**状态**: 只读分析 - 未修改任何文件

---

## 执行摘要

本报告分析了站内通知模块的三个核心文档，识别出 **1个关键问题**、**3个高严重程度问题**、**6个中等严重程度问题** 和 **2个低严重程度问题**。

### 关键发现
- **宪法合规**: 发现1个关键违反（TDD原则V）
- **需求覆盖**: 18个功能需求中，13个(72%)完全覆盖，2个(11%)未覆盖
- **任务映射**: 64个任务中，2个任务无明确需求映射

---

## 详细发现列表

| ID | 类别 | 严重程度 | 位置 | 摘要 | 建议 |
|----|------|---------|------|------|------|
| C1 | 宪法 | **关键** | tasks.md:第8阶段 | TDD原则违反：测试任务(T059-T062)放在最后而非实现之前 | 将测试任务移至对应实现任务之前，符合原则V要求 |
| A1 | 模糊性 | 中 | spec.md:FR-007 | "实时或准实时"缺乏技术定义 | 统一使用SC-001的5秒标准 |
| A2 | 模糊性 | 中 | spec.md:FR-011 | "可配置保留期" - 配置机制未指定 | 指定配置存储位置（数据库表、环境变量或配置文件）|
| U1 | 规格不足 | 中 | spec.md | 速率限制仅在边界情况提及，无正式需求 | 添加明确的速率限制FR（每用户每分钟请求数）|
| U2 | 规格不足 | 中 | spec.md | WebSocket认证机制细节缺失 | 在WebSocket握手中指定JWT令牌验证流程 |
| U3 | 规格不足 | 高 | spec.md:关键实体 | NotificationPermission实体被引用但未建模 | 添加NotificationPermission到数据模型 |
| D1 | 重复 | 低 | spec.md | FR-008（未读计数）与SC-006（角标准确性）重叠 | 合并为单一可测量需求 |
| D2 | 重复 | 低 | spec.md | FR-004（已读状态跟踪）与SC-009（反馈时间）重叠 | 保留FR-004为功能，SC-009为性能 |
| I1 | 不一致 | 中 | plan.md vs 实际 | 计划显示`backend/src/`但项目使用`backend/app/` | 更新plan.md以匹配实际项目结构 |
| I2 | 不一致 | 中 | spec.md | 假设"富文本或Markdown"（第159行）但FR-012说"仅视觉区分" | 澄清：支持Markdown但无基于优先级的特殊处理 |
| G1 | 覆盖缺口 | 高 | tasks.md | 无NotificationPermission RBAC实现任务 | 添加权限检查任务（T065-T067）|
| G2 | 覆盖缺口 | 中 | spec.md | 无明确的自动清理需求 | 添加基于保留策略的自动清理作业FR |
| G3 | 覆盖缺口 | 中 | tasks.md | 前端WebSocket客户端连接处理规格不足 | 添加带指数退避的WebSocket重连任务 |

---

## 需求覆盖分析

### 功能需求覆盖表

| 需求键 | 需求描述 | 有任务？ | 任务ID | 覆盖状态 |
|-------|---------|---------|--------|---------|
| FR-001 | 向个人用户发送通知 | ✅ | T016, T020, T035 | 已覆盖 |
| FR-002 | 向部门发送通知 | ✅ | T032-T035 | 已覆盖 |
| FR-003 | 通知类型管理 | ✅ | T037-T040 | 已覆盖 |
| FR-004 | 已读/未读状态跟踪 | ✅ | T018, T022, T046-T048 | 已覆盖 |
| FR-005 | 历史查询与筛选 | ✅ | T017, T041-T042 | 已覆盖 |
| FR-006 | 必填字段 | ✅ | T007-T009 | 已覆盖 |
| FR-007 | 实时交付 | ✅ | T014-T015, T023-T024 | 已覆盖 |
| FR-008 | 未读计数 | ✅ | T019 | 已覆盖 |
| FR-009 | 标记已读/未读 | ✅ | T018, T046, T051 | 已覆盖 |
| FR-010 | 批量操作 | ⚠️ 部分 | T047-T048, T053 | 缺少：批量选择UI |
| FR-011 | 保留期 | ⚠️ 部分 | T054 | 缺少：配置机制 |
| FR-012 | 类型图标/颜色 | ✅ | T007, T039-T040 | 已覆盖 |
| FR-013 | 模板 | ✅ | T050-T052 | 已覆盖 |
| FR-014 | 审计日志 | ⚠️ 部分 | T056 | 缺少：OperationLog集成细节 |
| FR-015 | RBAC授权 | ❌ | 无 | **未覆盖** |
| FR-016 | 权限规则 | ❌ | 无 | **未覆盖** |
| FR-017 | 部门经理范围 | ❌ | 无 | **未覆盖** |
| FR-018 | 不可变通知 | ✅ | 隐式设计 | 已覆盖 |

### 覆盖统计

| 指标 | 数值 |
|------|------|
| 总需求数 | 18 |
| 完全覆盖 | 13 (72%) |
| 部分覆盖 | 3 (17%) |
| 未覆盖 | 2 (11%) |
| **总覆盖率** | **89%** |

---

## 宪法合规分析

### 关键问题：原则V（TDD）违反

**问题描述**：
- 任务T059-T062（测试）被放置在第8阶段（最后阶段）
- 这违反了宪法原则V的明确要求："核心业务逻辑必须先编写单元测试（失败），然后实现功能（通过），最后重构"

**宪法原文**（第52-56行）：
> "MUST: 核心业务逻辑必须先编写单元测试（失败），然后实现功能（通过），最后重构；集成测试必须覆盖关键用户流程；测试覆盖率目标：核心模块 ≥ 80%。"

**影响**：
- 测试成为事后考虑而非设计驱动力
- 可能导致测试与实现脱节
- 难以保证80%覆盖率目标

**修复建议**：
```
当前顺序：T020-T022（服务实现）→ T059-T062（测试）
建议顺序：T059-T060（单元测试）→ T020-T022（服务实现）→ T061-T062（集成测试）
```

### 中等问题：原则IV（审计）缺口

**问题描述**：
- FR-014要求审计日志但任务T056过于通用
- 未明确与现有OperationLog系统的集成方式

**宪法原文**（第48-50行）：
> "MUST: 所有核心业务数据（模型、CI、关系、配置等）的变更必须记录审计日志"

**建议**：
在T056中明确指定：
- 使用现有的OperationLog模型
- 记录字段：sender_id, recipient_count, notification_type, timestamp
- 与app.models.operation_log集成

---

## 未映射任务

以下任务无明确需求映射或属于交付物而非实现任务：

| 任务ID | 描述 | 问题 | 建议 |
|--------|------|------|------|
| T058 | Redis缓存未读计数 | Redis未在spec依赖中提及；可能是过早优化 | 标记为[OPT]可选优化，或移除 |
| T063-T064 | 文档示例 | 这些是交付物，非实现任务 | 标记为[DOC]，不计入实现任务 |

---

## 详细问题分析

### 1. 关键问题 (Critical)

#### C1: TDD任务顺序违反

**位置**: tasks.md 第476-496行（第8阶段）

**当前状态**：
```markdown
### 8.4 测试完善

- [ ] T059 [P] 编写单元测试 - 服务层
- [ ] T060 [P] 编写单元测试 - API层
- [ ] T061 [P] 编写集成测试
- [ ] T062 [P] 编写WebSocket测试
```

**问题**：测试任务在所有实现之后，违反TDD原则。

**修复方案**：
```markdown
### 3.2 业务服务层（TDD方式）

- [ ] T059 编写NotificationService单元测试（先失败）
      测试send_to_users, get_user_notifications, mark_as_read方法
      文件: backend/tests/unit/notifications/test_services.py

- [ ] T020 [P] 实现NotificationService.send_to_users方法
      依赖: T059
      ...

- [ ] T060 编写API层单元测试
      测试所有HTTP端点
      文件: backend/tests/unit/notifications/test_api.py

- [ ] T016 [P] 实现发送通知API端点
      依赖: T060
      ...
```

---

### 2. 高严重度问题 (High)

#### U3: NotificationPermission实体缺失

**位置**: spec.md 第136行

**问题**：NotificationPermission实体在spec中被引用，但未在data-model.md中定义。

**建议添加**：
```python
class NotificationPermission:
    """通知权限配置"""
    id: UUID
    role_id: int  # 关联Role
    permission: str  # send_to_user, send_to_department, send_broadcast
    scope: str  # own_department, all_departments, all
    created_at: datetime
    updated_at: datetime
```

**相关任务**: 需添加T065-T067实现RBAC权限检查。

#### G1: RBAC实现任务缺失

**问题**: FR-015, FR-016, FR-017无对应实现任务。

**建议添加任务**：
```markdown
- [ ] T065 实现NotificationPermission模型
      创建RBAC权限配置实体
      文件: backend/app/notifications/models.py

- [ ] T066 实现权限检查装饰器
      创建@permission_required装饰器
      文件: backend/app/notifications/permissions.py

- [ ] T067 在API端点添加权限验证
      在发送通知API中验证sender权限
      文件: backend/app/notifications/api.py
```

#### I1: 项目结构不一致

**位置**: plan.md 第74-86行

**问题**: Plan中描述的结构为`backend/src/`，但项目实际使用`backend/app/`。

**影响**: 可能导致开发人员找不到正确目录。

**修复**: 将plan.md中所有`backend/src/`替换为`backend/app/`。

---

### 3. 中严重度问题 (Medium)

#### A1: "实时"定义模糊

**位置**: spec.md 第115行 (FR-007)

**问题**: "实时或准实时"缺乏量化标准。

**修复**: 修改为：
```markdown
- **FR-007**: System MUST support delivery of notifications within 5 seconds 
  when users are actively using the platform (meeting SC-001)
```

#### U1: 速率限制未规格化

**位置**: spec.md 第98行（仅边界情况提及）

**问题**: 速率限制仅在边界情况中提到，无正式需求。

**修复**: 添加新FR：
```markdown
- **FR-019**: System MUST implement rate limiting of 60 notification sends 
  per minute per sender to prevent abuse
```

#### G2: 自动清理需求缺失

**问题**: FR-011提到保留期，但无自动清理机制需求。

**修复**: 添加：
```markdown
- **FR-020**: System MUST automatically delete notifications older than 
  the configured retention period via scheduled background jobs
```

---

## 指标汇总

| 指标类别 | 数值 |
|---------|------|
| 总功能需求 | 18 |
| 总任务数 | 64 |
| 总用户数故事 | 5 |
| 成功标准 | 10 |
| 边界情况 | 8 |

### 问题统计

| 严重程度 | 数量 |
|---------|------|
| 关键 (Critical) | 1 |
| 高 (High) | 3 |
| 中 (Medium) | 6 |
| 低 (Low) | 2 |
| **总计** | **12** |

### 问题分类

| 类别 | 数量 |
|------|------|
| 宪法违反 | 1 |
| 覆盖缺口 | 3 |
| 规格不足 | 3 |
| 不一致 | 2 |
| 模糊性 | 2 |
| 重复 | 2 |

---

## 下一步行动建议

### 实施前必须修复（关键问题）

1. **重新排序测试任务** (C1)
   - 将T059-T062移至对应实现任务之前
   - 确保TDD流程：测试（失败）→ 实现（通过）→ 重构

2. **添加RBAC实现任务** (G1, U3)
   - 添加T065-T067任务
   - 在data-model.md中添加NotificationPermission实体

3. **更新项目结构文档** (I1)
   - 将plan.md中`backend/src/`改为`backend/app/`

### 可选修复（中等/低问题）

4. **澄清模糊需求** (A1, A2)
   - 为FR-007添加量化指标
   - 为FR-011指定配置机制

5. **添加缺失需求** (U1, G2)
   - 添加速率限制FR
   - 添加自动清理FR

### 可继续实施的情况

如果选择不修复可选问题：
- MVP（US1）功能可以正常实现
- 核心通知功能不受影响
- 但RBAC权限控制将缺失，需后续补充

### 建议的命令序列

```bash
# 选项1：完整修复后再实施
/speckit.specify --refine --fix-tdd-order --add-rbac-tasks
/speckit.plan --update --fix-structure
/speckit.implement

# 选项2：仅修复关键问题
/speckit.implement --with-fixes=C1,G1,I1

# 选项3：先实施MVP，后续修复
/speckit.implement --mvp-only --skip-rbac
# 然后稍后：/speckit.specify --add-rbac
```

---

## 修复建议详情

### 您是否希望我提供以下具体修复方案？

1. **TDD任务重排序方案** - tasks.md第170-240行的具体重排建议
2. **RBAC任务添加方案** - 新增T065-T067的完整任务描述
3. **plan.md结构修正** - 所有路径更正的逐行对比

请回复数字（1/2/3）或"全部"来获取具体修复编辑建议。

---

## 附录

### A. 参考文档

- 规格文档: `specs/004-notification-module/spec.md`
- 计划文档: `specs/004-notification-module/plan.md`
- 任务文档: `specs/004-notification-module/tasks.md`
- 宪法文档: `.specify/memory/constitution.md`

### B. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-02-19 | 初始分析报告 |

### C. 分析方法

本报告基于以下检测方法：
1. **需求库存**: 提取所有功能和非功能需求
2. **任务映射**: 将任务映射到需求和用户故事
3. **宪法验证**: 对照宪法原则检查合规性
4. **覆盖分析**: 计算需求到任务的覆盖率
5. **一致性检查**: 验证跨文档术语和结构一致性

---

**报告生成**: /speckit.analyze  
**分析范围**: spec.md, plan.md, tasks.md, constitution.md  
**输出文件**: specs/004-notification-module/analysis-report.md
