# Research: Internal Notification Module

**Date**: 2026-02-19  
**Feature**: 004-notification-module  
**Purpose**: Technical research and architectural decisions

## RT-001: Real-Time Delivery Mechanism

### Decision
**Flask-SocketIO** with automatic fallback to long-polling

### Rationale
1. **Ecosystem Integration**: Native Flask extension that works seamlessly with Flask 3.0.0 and SQLAlchemy 2.0.36
2. **Broadcasting Support**: Room-based architecture perfect for department-wide notifications
3. **Automatic Fallback**: WebSocket with graceful degradation to long-polling for older browsers/proxies
4. **Authentication**: Maintains Flask session context, enabling JWT validation on connection
5. **Scalability**: Supports message queue adapters (Redis) for multi-server deployments

### Implementation Notes
- Use SocketIO rooms named by user_id for targeted delivery
- Use department_id rooms for efficient department broadcasts
- Emit events from service layer after database persistence
- Client joins user-specific room on connection (authenticated)

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Server-Sent Events (SSE)** | Simple, HTTP-based, auto-reconnect | One-way only (server→client), no delivery confirmation | ❌ Rejected - need bidirectional for delivery tracking |
| **Pure WebSocket** | Full-duplex, low latency | No fallback, requires additional infrastructure | ❌ Rejected - need browser compatibility |
| **Polling** | Simple, widely supported | High latency, battery drain, server load | ❌ Rejected - poor UX for real-time |
| **Flask-SocketIO** | Best of all worlds, Flask-native | Additional dependency | ✅ Selected |

## RT-002: Database Schema Strategy

### Decision
Normalized relational schema with junction table for read status tracking

### Schema Design

```sql
-- Core notification table
notifications (
    id: UUID PRIMARY KEY,
    title: VARCHAR(255) NOT NULL,
    content: TEXT NOT NULL,
    content_html: TEXT, -- rendered from markdown
    type_id: UUID FOREIGN KEY,
    sender_id: UUID FOREIGN KEY (users),
    template_id: UUID FOREIGN KEY (optional),
    created_at: TIMESTAMP,
    expires_at: TIMESTAMP -- for retention
)

-- Junction table for recipients and read status
notification_recipients (
    id: UUID PRIMARY KEY,
    notification_id: UUID FOREIGN KEY,
    user_id: UUID FOREIGN KEY (users),
    is_read: BOOLEAN DEFAULT FALSE,
    read_at: TIMESTAMP,
    delivery_status: ENUM ('pending', 'delivered', 'failed'),
    delivery_attempts: INTEGER DEFAULT 0,
    last_attempt_at: TIMESTAMP,
    created_at: TIMESTAMP
)

-- Notification types
notification_types (
    id: UUID PRIMARY KEY,
    name: VARCHAR(100) NOT NULL UNIQUE,
    description: TEXT,
    icon: VARCHAR(50), -- icon name/class
    color: VARCHAR(20), -- hex color code
    is_system: BOOLEAN DEFAULT FALSE,
    created_at: TIMESTAMP
)

-- Templates for common patterns
notification_templates (
    id: UUID PRIMARY KEY,
    name: VARCHAR(100) NOT NULL,
    title_template: VARCHAR(255) NOT NULL, -- with placeholders
    content_template: TEXT NOT NULL, -- with placeholders
    type_id: UUID FOREIGN KEY,
    variables: JSON, -- list of variable names
    created_at: TIMESTAMP
)
```

### Indexing Strategy
```sql
-- For "my notifications" queries
CREATE INDEX idx_recipients_user_read ON notification_recipients(user_id, is_read, created_at DESC);

-- For unread count (fast)
CREATE INDEX idx_recipients_user_unread ON notification_recipients(user_id, is_read) WHERE is_read = FALSE;

-- For notification broadcast queries
CREATE INDEX idx_recipients_notification ON notification_recipients(notification_id);

-- For retention cleanup
CREATE INDEX idx_notifications_expires ON notifications(expires_at) WHERE expires_at IS NOT NULL;

-- For history search
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

### Rationale
1. **Junction Table Pattern**: Enables efficient queries for "notifications for user X"
2. **Read Status per Recipient**: Each user has independent read status for shared notifications
3. **Delivery Tracking**: Track success/failure per recipient for retry logic
4. **Retention Support**: expires_at field enables efficient cleanup queries

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **JSON recipients array** | Simpler schema | Cannot index, slow queries for "my notifications" | ❌ Rejected |
| **Separate read_status table** | Clear separation | Extra join for every query, no benefit | ❌ Rejected |
| **Junction table (selected)** | Normalized, queryable, scalable | Slightly more complex | ✅ Selected |

## RT-003: Permission System Integration

### Decision
Extend existing RBAC with notification-specific permission verbs

### Permission Model

```python
# Permission verbs for notifications
NOTIFICATION_PERMISSIONS = [
    "notification.send_to_user",      # Send to specific users
    "notification.send_to_department", # Send to departments
    "notification.send_broadcast",     # Send to all users
    "notification.manage_types",       # CRUD notification types
    "notification.manage_templates",   # CRUD templates
    "notification.view_history",       # View send history (admin)
]
```

### Default Role Permissions

| Role | send_to_user | send_to_department | send_broadcast | manage_types | manage_templates | view_history |
|------|-------------|-------------------|----------------|--------------|------------------|--------------|
| **System Admin** | ✅ | ✅ (all depts) | ✅ | ✅ | ✅ | ✅ |
| **Department Manager** | ✅ | ✅ (own dept) | ❌ | ❌ | ❌ | ❌ |
| **Regular User** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Implementation Strategy
1. **Permission Decorators**: Use `@permission_required('notification.send_to_department')` on API endpoints
2. **Scope Validation**: In service layer, verify department manager only sends to own departments
3. **Audit Trail**: Log permission checks for security review

### Rationale
- Reuses existing RBAC infrastructure
- Granular control over notification capabilities
- Easy to extend with new roles

## RT-004: Background Task Processing

### Decision
APScheduler for periodic tasks (retention cleanup, retry failed deliveries)

### Tasks

```python
# Daily at 2 AM - Retention cleanup
@scheduler.task('cron', id='cleanup_expired', hour=2, minute=0)
def cleanup_expired_notifications():
    """Delete notifications past retention period"""
    pass

# Every 5 minutes - Retry failed deliveries
@scheduler.task('interval', id='retry_failed', minutes=5)
def retry_failed_deliveries():
    """Retry notifications with failed delivery status"""
    pass

# Hourly - Audit log rotation (if needed)
@scheduler.task('cron', id='audit_rotation', hour='*/1')
def rotate_audit_logs():
    """Archive old audit logs"""
    pass
```

### Rationale
1. **Lightweight**: APScheduler is simple, no message broker needed
2. **Integrated**: Runs in Flask process, easy deployment
3. **Sufficient for MVP**: Scale of 1000 users doesn't require Celery

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Celery + Redis** | Distributed, highly scalable | Additional infrastructure, complexity | ❌ Overkill for MVP |
| **System cron + CLI** | Simple, reliable | External dependency, harder to test | ❌ Less integrated |
| **APScheduler** | In-process, simple, sufficient | Limited to single server | ✅ Selected for MVP |

## RT-005: Notification Content Format

### Decision
Markdown input with HTML sanitization and rendering

### Implementation

```python
import markdown
from bleach import clean

# Allowed HTML tags
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

def render_notification_content(markdown_text: str) -> str:
    """Convert markdown to safe HTML"""
    # Convert markdown to HTML
    html = markdown.markdown(markdown_text, extensions=['nl2br'])
    # Sanitize HTML
    safe_html = clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return safe_html
```

### Rationale
1. **User-Friendly**: Markdown is familiar and easy to write
2. **Rich Formatting**: Supports links, lists, emphasis without security risks
3. **Safe**: bleach library prevents XSS attacks
4. **Storage Efficient**: Store markdown, render on demand (or cache HTML)

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Plain text only** | Simple, safe | No formatting capability | ❌ Too limiting |
| **HTML directly** | Full formatting | XSS risk, harder for users | ❌ Security risk |
| **Rich text editor** | WYSIWYG | Complex, heavy dependency | ❌ Overkill |
| **Markdown + sanitize** | Best balance | Requires rendering step | ✅ Selected |

## RT-006: Department Resolution Strategy

### Decision
Resolve department members at send time, store resolved user_ids

### Implementation

```python
def send_to_department(department_id: str, notification: Notification):
    """Resolve department members and create recipient records"""
    # Get current department members
    members = department_service.get_active_members(department_id)
    
    # Create notification_recipient records for each member
    for user_id in members:
        NotificationRecipient.create(
            notification_id=notification.id,
            user_id=user_id,
            delivery_status='pending'
        )
    
    # Broadcast via WebSocket
    socketio.emit('notification:new', notification.to_dict(), 
                  room=f'dept_{department_id}')
```

### Rationale
1. **Snapshot at Send Time**: Users who join later don't get old notifications (as per spec)
2. **Immutable History**: Notification recipients don't change after sending
3. **Performance**: Single query to get members, bulk insert recipients

## RT-007: Delivery Retry Strategy

### Decision
Exponential backoff with 3 max retries

### Implementation

```python
RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min
MAX_RETRIES = 3

def retry_failed_deliveries():
    """Retry notifications that failed to deliver"""
    failed = NotificationRecipient.query.filter_by(
        delivery_status='failed',
        delivery_attempts__lt=MAX_RETRIES
    ).all()
    
    for recipient in failed:
        # Check if enough time has passed
        delay = RETRY_DELAYS[recipient.delivery_attempts]
        if time_since_last_attempt > delay:
            attempt_delivery(recipient)
```

### Rationale
- 3 attempts balance reliability with resource usage
- Exponential backoff prevents overwhelming failing endpoints
- After 3 failures, mark as permanent failure and log

## Summary

All research decisions align with project constraints and Constitution requirements:

| Decision | Status | Impact |
|----------|--------|--------|
| Flask-SocketIO for real-time | ✅ Approved | Core delivery mechanism |
| Normalized DB schema | ✅ Approved | Data integrity, query performance |
| RBAC permission extension | ✅ Approved | Security, role management |
| APScheduler for tasks | ✅ Approved | Retention, retry logic |
| Markdown + sanitization | ✅ Approved | Content safety |
| Resolve at send time | ✅ Approved | Data consistency |
| Exponential backoff retry | ✅ Approved | Reliability |

**Next**: Proceed to Phase 1 (Data Model & API Contracts)
