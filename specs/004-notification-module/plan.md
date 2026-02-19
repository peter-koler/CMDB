# Implementation Plan: Internal Notification Module

**Branch**: `004-notification-module` | **Date**: 2026-02-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-notification-module/spec.md`

## Summary

Build a universal internal notification infrastructure for the Arco CMDB platform supporting user and department targeting, notification type management, read/unread status tracking, and historical search. The module serves as foundational infrastructure for future platform features (change management, ticketing, alerts).

**Technical Approach**: 
- Backend: Flask-based REST API with Flask-SocketIO for real-time delivery
- Database: SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)
- Frontend: Vue 3 + TypeScript notification center component
- Architecture: Modular service layer with clear API contracts

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-SocketIO 5.x, SQLAlchemy 2.0.36  
**Storage**: SQLite (development), PostgreSQL/MySQL (production)  
**Testing**: pytest with Flask test client  
**Target Platform**: Web application (backend API + frontend UI)  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: P95 API response < 200ms, 1000 concurrent recipients, 5s real-time delivery  
**Constraints**: Must integrate with existing RBAC system, support department hierarchy  
**Scale/Scope**: Enterprise platform supporting 1000+ users, 90-day retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Modular Architecture | ✅ PASS | Notification module is standalone with clear interfaces |
| II. Notification Infrastructure | ✅ PASS | This IS the notification center infrastructure |
| III. API-First Design | ✅ PASS | REST API contracts will be defined before implementation |
| IV. Data Integrity & Audit | ✅ PASS | Audit logging required (FR-014), immutable notifications (FR-018) |
| V. Test-Driven Development | ✅ PASS | Test plan will be created in tasks phase |

**Constitution Compliance**: ✅ ALL PRINCIPLES SATISFIED

**Technical Stack Compliance**:
- ✅ Python 3.11 + Flask 3.0.0 + SQLAlchemy 2.0.36 (per Constitution)
- ✅ Vue 3 + TypeScript frontend (per Constitution)

**Performance Standards Compliance**:
- ✅ P95 < 200ms (simple queries) - meets SC-007 (2s for complex history queries)
- ✅ Supports 1000+ concurrent users - meets SC-004

**Security Requirements Compliance**:
- ✅ JWT Token auth (existing platform auth system)
- ✅ RBAC permission validation (FR-015, FR-016, FR-017)
- ✅ Audit logging (FR-014)

## Project Structure

### Documentation (this feature)

```text
specs/004-notification-module/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── openapi.yaml     # OpenAPI 3.0 specification
│   └── websocket.md     # WebSocket events documentation
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── notifications/           # Notification module (NEW)
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── services.py          # Business logic layer
│   │   ├── api.py               # REST API endpoints
│   │   ├── websocket.py         # SocketIO event handlers
│   │   ├── permissions.py       # RBAC permission checks
│   │   └── tasks.py             # Background tasks (cleanup, retry)
│   ├── models/                  # Existing models
│   ├── services/                # Existing services
│   └── app.py                   # Flask app factory
└── tests/
    ├── unit/notifications/      # Unit tests
    └── integration/notifications/  # Integration tests

frontend/
├── src/
│   ├── components/notifications/  # Vue components (NEW)
│   │   ├── NotificationCenter.vue
│   │   ├── NotificationList.vue
│   │   ├── NotificationItem.vue
│   │   └── NotificationBadge.vue
│   ├── services/notifications.ts  # API client
│   ├── stores/notifications.ts    # Pinia store
│   └── views/notifications/       # Page views
└── tests/
    └── components/notifications/
```

**Structure Decision**: Web application structure (Option 2) - separate backend API and frontend components following the existing Arco platform architecture. The notification module is a new standalone module under `backend/app/notifications/` with clear boundaries.

## Complexity Tracking

> No Constitution violations detected. All principles satisfied with standard architecture.

## Phase 0: Research & Technical Decisions

### Research Tasks Completed

#### RT-001: Real-Time Delivery Mechanism
**Decision**: Flask-SocketIO with fallback to polling

**Rationale**:
- Flask-SocketIO integrates seamlessly with Flask ecosystem
- Supports WebSocket with automatic fallback to long-polling for older browsers
- Room-based broadcasting perfect for department notifications
- Maintains session state and authentication context

**Alternatives considered**:
- Server-Sent Events (SSE): Simpler but one-way only (server→client), harder to track delivery status
- Pure WebSocket: Requires additional infrastructure, no automatic fallback
- Polling: Higher latency, more server load

#### RT-002: Database Schema Strategy
**Decision**: Separate `notification_recipients` junction table for read status tracking

**Rationale**:
- Normalized design supports efficient queries for "my notifications"
- Index on `(user_id, is_read)` for fast unread count
- Index on `(notification_id)` for broadcast queries
- Supports soft delete via status field for retry tracking

**Alternatives considered**:
- JSON array of recipients in notification row: Poor query performance, hard to index
- Separate read status table: Adds complexity without benefit

#### RT-003: Permission System Integration
**Decision**: Extend existing RBAC with notification-specific permissions

**Rationale**:
- Reuse existing permission framework
- Add granular permissions: `notification.send_to_user`, `notification.send_to_department`, `notification.send_broadcast`
- Check permissions in service layer before delivery

**Permission Matrix**:
| Role | send_to_user | send_to_department | send_broadcast | Scope |
|------|-------------|-------------------|----------------|-------|
| System Admin | ✅ | ✅ | ✅ | All |
| Dept Manager | ✅ | ✅ (own dept) | ❌ | Own dept |
| Regular User | ❌ | ❌ | ❌ | N/A |

#### RT-004: Background Task Processing
**Decision**: APScheduler for periodic cleanup and retry tasks

**Rationale**:
- Lightweight, integrates well with Flask
- Handles retention cleanup (daily job to delete expired notifications)
- Handles failed delivery retry (exponential backoff)
- No need for full Celery/RabbitMQ for MVP scale

#### RT-005: Notification Content Format
**Decision**: Markdown support with HTML sanitization

**Rationale**:
- Markdown is user-friendly for content creators
- Allows rich formatting (bold, links, lists) without security risks
- bleach library for HTML sanitization to prevent XSS
- Stored as Markdown, rendered to HTML on display

### Research Findings Summary

All technical decisions align with Constitution requirements:
- ✅ Uses approved Flask/SQLAlchemy stack
- ✅ Modular architecture with clear boundaries
- ✅ API-first with REST + WebSocket contracts
- ✅ Audit logging and data integrity built-in
- ✅ TDD approach with pytest

## Phase 1: Design & Contracts

### Data Model Design

See `data-model.md` for complete entity definitions.

**Key Relationships**:
```
Notification (1) ───< NotificationRecipient (N) >─── (1) User
     │
     (N) ─── (1) NotificationType
     │
     (N) ─── (1) NotificationTemplate
```

### API Contracts

See `contracts/openapi.yaml` for complete OpenAPI specification.

**Core Endpoints**:
- `POST /api/v1/notifications` - Send notification (RBAC protected)
- `GET /api/v1/notifications` - List my notifications with filters
- `PATCH /api/v1/notifications/{id}/read` - Mark as read
- `PATCH /api/v1/notifications/read-all` - Mark all as read
- `GET /api/v1/notifications/unread-count` - Get unread count
- `GET /api/v1/notifications/types` - List notification types

**WebSocket Events**:
- `connect` - Authenticate and join user room
- `notification:new` - Server → Client: New notification received
- `disconnect` - Leave room

### Quick Start

See `quickstart.md` for development setup and testing instructions.

## Phase 2: Planning Complete

**Status**: ✅ Phase 0 Research Complete  
**Status**: ✅ Phase 1 Design Complete  
**Next Step**: Run `/speckit.tasks` to generate task breakdown

**Generated Artifacts**:
1. ✅ `research.md` - Technical decisions and rationale
2. ✅ `data-model.md` - Entity definitions and relationships
3. ✅ `contracts/openapi.yaml` - API specification
4. ✅ `contracts/websocket.md` - WebSocket event documentation
5. ✅ `quickstart.md` - Development setup guide

**Agent Context Updated**: Yes (via update-agent-context.sh)

**Constitution Re-check Post-Design**:
| Principle | Status | Notes |
|-----------|--------|-------|
| I. Modular Architecture | ✅ PASS | Clear module boundaries, independent deployment |
| II. Notification Infrastructure | ✅ PASS | Foundation for future platform features |
| III. API-First Design | ✅ PASS | OpenAPI contracts defined before implementation |
| IV. Data Integrity & Audit | ✅ PASS | Audit logs, immutable design, retention policies |
| V. Test-Driven Development | ✅ PASS | Test structure defined, coverage targets set |

**All Gates**: ✅ PASSED - Ready for task generation
