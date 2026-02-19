# Data Model: Internal Notification Module

**Date**: 2026-02-19  
**Feature**: 004-notification-module  
**Format**: SQLAlchemy 2.0 declarative models

## Entity Relationship Diagram

```
┌──────────────────┐       ┌─────────────────────────┐       ┌──────────────┐
│  Notification    │       │   NotificationRecipient │       │     User     │
├──────────────────┤       ├─────────────────────────┤       ├──────────────┤
│ PK id: UUID      │◄──────┤ PK id: UUID             │──────►│ PK id: UUID  │
│ FK type_id: UUID │       │ FK notification_id: UUID│       │ username     │
│ FK sender_id:UUID│       │ FK user_id: UUID        │       │ email        │
│ title: str       │       │ is_read: bool           │       └──────────────┘
│ content: str     │       │ read_at: datetime       │
│ content_html:str │       │ delivery_status: enum   │
│ created_at: dt   │       │ delivery_attempts: int  │
│ expires_at: dt   │       │ last_attempt_at: dt     │
└────────┬─────────┘       └─────────────────────────┘
         │
         │ FK
         ▼
┌──────────────────┐
│ NotificationType │
├──────────────────┤
│ PK id: UUID      │
│ name: str        │
│ description: str │
│ icon: str        │
│ color: str       │
│ is_system: bool  │
└──────────────────┘
         ▲
         │ FK
┌──────────────────────┐
│ NotificationTemplate │
├──────────────────────┤
│ PK id: UUID          │
│ name: str            │
│ title_template: str  │
│ content_template: str│
│ FK type_id: UUID     │
│ variables: JSON      │
└──────────────────────┘
```

## Models

### Notification

Core entity representing a message sent to users.

```python
class Notification(Base):
    """A notification message sent to one or more users."""
    
    __tablename__ = 'notifications'
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Content Fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown
    content_html: Mapped[str] = mapped_column(Text, nullable=False)  # Rendered HTML
    
    # Foreign Keys
    type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('notification_types.id'), 
        nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('notification_templates.id'), 
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Relationships
    type: Mapped["NotificationType"] = relationship(back_populates="notifications")
    sender: Mapped["User"] = relationship(back_populates="sent_notifications")
    template: Mapped[Optional["NotificationTemplate"]] = relationship(back_populates="notifications")
    recipients: Mapped[List["NotificationRecipient"]] = relationship(
        back_populates="notification",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_notifications_created', 'created_at DESC'),
        Index('idx_notifications_expires', 'expires_at'),
        Index('idx_notifications_sender', 'sender_id'),
        Index('idx_notifications_type', 'type_id'),
    )
```

### NotificationRecipient

Junction entity tracking per-user receipt and read status.

```python
class NotificationRecipient(Base):
    """Tracks delivery and read status for each notification recipient."""
    
    __tablename__ = 'notification_recipients'
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Foreign Keys
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('notifications.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'),
        nullable=False
    )
    
    # Read Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Delivery Tracking
    delivery_status: Mapped[str] = mapped_column(
        String(20), 
        default='pending'  # pending, delivered, failed
    )
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    notification: Mapped["Notification"] = relationship(back_populates="recipients")
    user: Mapped["User"] = relationship(back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        # For "my notifications" queries with sorting
        Index('idx_recipients_user_created', 'user_id', 'created_at DESC'),
        # For unread count (fast)
        Index('idx_recipients_user_unread', 'user_id', 'is_read'),
        # For notification broadcast queries
        Index('idx_recipients_notification', 'notification_id'),
        # Unique constraint: one recipient record per user per notification
        UniqueConstraint('notification_id', 'user_id', name='uq_recipient_notification_user'),
    )
```

### NotificationType

Configuration entity for notification categories.

```python
class NotificationType(Base):
    """Defines categories of notifications with display properties."""
    
    __tablename__ = 'notification_types'
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Identification
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Display Properties
    icon: Mapped[str] = mapped_column(String(50), default='bell')
    color: Mapped[str] = mapped_column(String(20), default='#1890ff')
    
    # System Flag (cannot delete system types)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="type"
    )
    templates: Mapped[List["NotificationTemplate"]] = relationship(
        back_populates="type"
    )
```

### NotificationTemplate

Predefined message patterns with variable placeholders.

```python
class NotificationTemplate(Base):
    """Templates for common notification patterns with variable substitution."""
    
    __tablename__ = 'notification_templates'
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Template Content (with {variable} placeholders)
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    content_template: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Variable Definitions (JSON array of variable names)
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Foreign Key
    type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('notification_types.id'),
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    type: Mapped["NotificationType"] = relationship(back_populates="templates")
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="template"
    )
    
    # Methods
    def render(self, variables: dict) -> tuple[str, str]:
        """Render template with variable substitution."""
        title = self.title_template.format(**variables)
        content = self.content_template.format(**variables)
        return title, content
```

## State Transitions

### Notification Lifecycle

```
[Created] → [Recipients Resolved] → [Delivery Attempted]
                              ↓
                    ┌────────┴────────┐
                    ▼                 ▼
              [Delivered]        [Failed]
                    │                 │
                    │           [Retry x3]
                    │                 │
                    │            ┌────┴────┐
                    │            ▼         ▼
                    │      [Delivered]  [Permanent Failure]
                    │                        │
                    ▼                        ▼
              [Read/Unread]           [Audit Log]
```

### Delivery Status States

| Status | Description | Transitions |
|--------|-------------|-------------|
| **pending** | Initial state, awaiting delivery | → delivered, → failed |
| **delivered** | Successfully delivered via WebSocket | → read (user action) |
| **failed** | Delivery failed, will retry | → pending (retry), → permanent_failure (max retries) |
| **permanent_failure** | Max retries exceeded | terminal |

## Validation Rules

### Notification

1. **Title**: Required, 1-255 characters
2. **Content**: Required, 1-10000 characters (markdown)
3. **Type**: Must reference existing NotificationType
4. **Sender**: Must reference existing User with send permission
5. **Expires At**: Optional, must be in the future if set

### NotificationRecipient

1. **Notification + User**: Unique combination (one recipient record per notification per user)
2. **Read At**: Must be >= created_at if set
3. **Delivery Attempts**: 0-3 (max retries)

### NotificationType

1. **Name**: Required, unique, 1-100 characters
2. **System Types**: Cannot delete if is_system=True
3. **Color**: Valid hex color code

### NotificationTemplate

1. **Variables**: All variables in template must be defined in variables JSON
2. **Type**: Must reference existing NotificationType

## Indexes Summary

| Table | Index Name | Columns | Purpose |
|-------|-----------|---------|---------|
| notifications | idx_notifications_created | created_at DESC | History queries |
| notifications | idx_notifications_expires | expires_at | Retention cleanup |
| notifications | idx_notifications_sender | sender_id | Sender history |
| notifications | idx_notifications_type | type_id | Type filtering |
| notification_recipients | idx_recipients_user_created | user_id, created_at DESC | My notifications list |
| notification_recipients | idx_recipients_user_unread | user_id, is_read | Unread count (fast) |
| notification_recipients | idx_recipients_notification | notification_id | Broadcast queries |

## Constraints Summary

| Table | Constraint | Definition |
|-------|-----------|------------|
| notification_types | uq_type_name | UNIQUE(name) |
| notification_recipients | uq_recipient_notification_user | UNIQUE(notification_id, user_id) |

## Migration Notes

### Initial Data

```sql
-- Insert default notification types
INSERT INTO notification_types (id, name, description, icon, color, is_system) VALUES
  (gen_random_uuid(), 'system', 'System alerts and announcements', 'warning', '#ff4d4f', true),
  (gen_random_uuid(), 'task', 'Task assignments and updates', 'check-circle', '#52c41a', true),
  (gen_random_uuid(), 'message', 'Direct messages', 'message', '#1890ff', true),
  (gen_random_uuid(), 'announcement', 'General announcements', 'notification', '#faad14', true);
```

## Constitution Compliance

✅ **Modular Architecture**: Clear entity boundaries, no cross-module dependencies  
✅ **Data Integrity**: Foreign key constraints, audit fields, immutable notifications  
✅ **API-First**: Models designed to support REST API patterns  
✅ **Testability**: Simple model logic, testable validation rules
