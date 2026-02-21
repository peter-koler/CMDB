# Implementation Plan: CMDB CI 关系触发器优化

**Branch**: `005-ci-relation-trigger` | **Date**: 2026-02-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-ci-relation-trigger/spec.md`

## Summary

优化 CMDB 关系触发器功能，实现新增/更新 CI 时自动根据触发器规则创建关系，使用 APScheduler 配置后台批量扫描任务定期检测并建立缺失的关系，提供批量扫描执行历史页面和执行计划配置功能。

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, APScheduler 3.10  
**Storage**: SQLite (开发), PostgreSQL/MySQL (生产)  
**Testing**: pytest  
**Target Platform**: Linux Server  
**Project Type**: Web Application (前后端分离)  
**Performance Goals**: 关系创建 < 5s, 批量扫描 10,000 CI 不超时  
**Constraints**: API P95 < 500ms  
**Scale/Scope**: 支持 10,000+ CI 实例

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. 模块化架构优先 | ✓ 通过 | 触发器逻辑封装在独立 service 模块 |
| II. 通知中心基础设施 | ✓ 通过 | 不涉及用户通知 |
| III. API 优先设计 | ✓ 通过 | 已定义 API 契约 (contracts/trigger-api.yaml) |
| IV. 数据完整性与审计 | ✓ 通过 | 执行日志记录审计 (TriggerExecutionLog) |
| V. 测试驱动开发 | ✓ 通过 | 将编写单元测试和集成测试 |

**技术栈合规**: Python 3.11, Flask 3.0.0, SQLAlchemy 2.0.36, APScheduler 3.10 ✓

## Project Structure

### Documentation (this feature)

```text
specs/005-ci-relation-trigger/
├── plan.md              # 本文件
├── research.md          # 技术调研报告
├── data-model.md        # 数据模型设计
├── quickstart.md        # 快速开始指南
├── contracts/           # API 契约
│   └── trigger-api.yaml
└── tasks.md             # 任务分解 (待生成)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── cmdb_relation.py      # 扩展 RelationTrigger, 新增 TriggerExecutionLog, BatchScanTask
│   ├── services/
│   │   ├── relation_service.py   # 现有关系服务
│   │   └── trigger_service.py    # 新增触发器服务
│   ├── routes/
│   │   └── trigger.py            # 新增触发器 API
│   └── tasks/
│       ├── __init__.py           # 任务模块初始化
│       ├── scheduler.py          # APScheduler 调度器
│       └── batch_scan.py         # 批量扫描任务逻辑
└── tests/
    └── unit/
        └── test_trigger_service.py

frontend/
├── src/
│   ├── views/
│   │   └── cmdb/
│   │       ├── TriggerConfig.vue     # 触发器配置页面
│   │       └── BatchScanHistory.vue  # 批量扫描历史页面
│   └── api/
│       └── trigger.ts                # 触发器 API 调用
```

**Structure Decision**: 使用现有 Web 应用结构，后端在 backend/app 下新增 services 和 tasks 模块，前端在 frontend/src/views/cmdb 下新增页面组件

## Key Technical Decisions

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 触发器匹配 | 精确值匹配 | 简单可靠，避免过度设计 |
| 执行时机 | CI 保存后异步执行 | 避免阻塞，满足 5s 要求 |
| 定时调度 | APScheduler | 原生支持 Cron，动态配置，无需额外基础设施 |
| 日志存储 | 新增 TriggerExecutionLog 表 | 支持审计和问题排查 |

## Complexity Tracking

> 无 Constitution 违规，无需记录
