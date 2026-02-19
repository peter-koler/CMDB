# WebSocket Events: Internal Notification Module

**Protocol**: Socket.IO  
**Namespace**: `/notifications`  
**Authentication**: JWT token in connection query parameter or header

## Connection

### Client Connection

```javascript
import { io } from 'socket.io-client';

const socket = io('/notifications', {
  transports: ['websocket', 'polling'],  // Automatic fallback
  auth: {
    token: ' Bearer <JWT_TOKEN>'  // From localStorage or cookie
  }
});

socket.on('connect', () => {
  console.log('Connected to notification service');
  console.log('Socket ID:', socket.id);
});

socket.on('connect_error', (error) => {
  console.error('Connection failed:', error.message);
  // Handle auth failure or server error
});

socket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
  // Reason: 'io server disconnect', 'io client disconnect', 'transport close', etc.
});
```

### Authentication Flow

1. **Connection**: Client connects with JWT token
2. **Validation**: Server validates token and extracts user_id
3. **Room Join**: Server automatically joins client to user-specific room
4. **Ready**: Client receives `authenticated` event, ready to receive notifications

```javascript
// Server-side authentication
socket.on('connection', (socket) => {
  try {
    const token = socket.handshake.auth.token;
    const user = jwt.verify(token, SECRET_KEY);
    
    // Join user-specific room for targeted notifications
    socket.join(`user:${user.id}`);
    
    // Join department rooms (if applicable)
    user.departments.forEach(deptId => {
      socket.join(`dept:${deptId}`);
    });
    
    socket.emit('authenticated', { user_id: user.id });
  } catch (error) {
    socket.emit('auth_error', { message: 'Invalid token' });
    socket.disconnect();
  }
});
```

## Events

### Server → Client Events

#### `notification:new`

**Description**: New notification received by the user

**Payload**:

```typescript
interface NewNotificationEvent {
  id: string;                    // UUID
  title: string;
  content: string;               // Plain text or markdown
  content_html: string;          // Sanitized HTML
  type: {
    id: string;
    name: string;
    icon: string;
    color: string;
  };
  sender: {
    id: string;
    username: string;
    display_name: string;
  };
  created_at: string;            // ISO 8601 datetime
  recipient_id: string;          // The recipient record ID
}
```

**Example**:

```javascript
socket.on('notification:new', (data) => {
  console.log('New notification:', data.title);
  
  // Show browser notification (if permitted)
  if (Notification.permission === 'granted') {
    new Notification(data.title, {
      body: data.content,
      icon: `/icons/${data.type.icon}.png`
    });
  }
  
  // Update unread count badge
  updateUnreadCount();
  
  // Add to notification list
  prependToNotificationList(data);
});
```

#### `notification:read`

**Description**: A notification has been marked as read (sync across tabs/devices)

**Payload**:

```typescript
interface NotificationReadEvent {
  recipient_id: string;          // The recipient record ID
  notification_id: string;       // The notification ID
  read_at: string;               // ISO 8601 datetime
}
```

**Example**:

```javascript
socket.on('notification:read', (data) => {
  // Update UI to show notification as read
  markAsReadInUI(data.notification_id);
  
  // Update unread count
  decrementUnreadCount();
});
```

#### `notification:unread`

**Description**: A notification has been marked as unread (sync across tabs/devices)

**Payload**:

```typescript
interface NotificationUnreadEvent {
  recipient_id: string;
  notification_id: string;
}
```

#### `notifications:read_all`

**Description**: All notifications have been marked as read

**Payload**:

```typescript
interface ReadAllEvent {
  marked_count: number;          // Number of notifications marked
  read_at: string;               // ISO 8601 datetime
}
```

#### `authenticated`

**Description**: Connection authenticated successfully

**Payload**:

```typescript
interface AuthenticatedEvent {
  user_id: string;
  connected_at: string;          // ISO 8601 datetime
}
```

#### `auth_error`

**Description**: Authentication failed

**Payload**:

```typescript
interface AuthErrorEvent {
  message: string;
  code: string;                  // 'INVALID_TOKEN', 'EXPIRED_TOKEN', 'SERVER_ERROR'
}
```

#### `error`

**Description**: General error occurred

**Payload**:

```typescript
interface ErrorEvent {
  message: string;
  code: string;
  details?: any;
}
```

### Client → Server Events

#### `notification:acknowledge`

**Description**: Acknowledge receipt of a notification (optional, for delivery tracking)

**Payload**:

```typescript
interface AcknowledgePayload {
  recipient_id: string;          // The recipient record ID
}
```

**Example**:

```javascript
socket.on('notification:new', (data) => {
  // Acknowledge receipt
  socket.emit('notification:acknowledge', {
    recipient_id: data.recipient_id
  });
});
```

#### `ping`

**Description**: Keep connection alive (optional, Socket.IO has built-in ping/pong)

**Response**: Server responds with `pong`

## Rooms

### Room Naming Convention

| Room Pattern | Purpose | Example |
|-------------|---------|---------|
| `user:{user_id}` | Target a specific user | `user:550e8400-e29b-41d4-a716-446655440000` |
| `dept:{dept_id}` | Target all department members | `dept:550e8400-e29b-41d4-a716-446655440001` |
| `broadcast` | Target all connected users | `broadcast` |

### Server-Side Broadcasting

```python
from flask_socketio import emit

# Send to specific user
emit('notification:new', notification_data, room=f'user:{user_id}')

# Send to department (all members)
emit('notification:new', notification_data, room=f'dept:{dept_id}')

# Broadcast to all connected users (rarely used)
emit('notification:new', notification_data, broadcast=True)

# Send to multiple rooms
for dept_id in department_ids:
    emit('notification:new', notification_data, room=f'dept:{dept_id}')
```

## Error Handling

### Connection Errors

```javascript
socket.on('connect_error', (error) => {
  if (error.message === 'Authentication failed') {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.message === 'Server error') {
    // Retry with exponential backoff
    setTimeout(() => socket.connect(), 5000);
  }
});
```

### Reconnection Strategy

```javascript
const socket = io('/notifications', {
  transports: ['websocket', 'polling'],
  auth: { token: getJwtToken() },
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  randomizationFactor: 0.5
});

socket.on('reconnect', (attemptNumber) => {
  console.log('Reconnected after', attemptNumber, 'attempts');
  // Refresh notification list
  fetchNotifications();
});

socket.on('reconnect_failed', () => {
  console.error('Failed to reconnect');
  // Show offline indicator to user
  showOfflineMode();
});
```

## Delivery Guarantees

### At-Least-Once Delivery

1. Notification saved to database with `delivery_status='pending'`
2. WebSocket event emitted
3. Client acknowledges receipt (optional)
4. Server updates status to `delivered`
5. If no acknowledgement within timeout, retry logic applies

### Fallback Mechanism

If WebSocket delivery fails:

1. Mark as `failed` in database
2. Retry with exponential backoff (1min, 5min, 15min)
3. After 3 failures, mark as `permanent_failure`
4. User will see notification on next page load (HTTP API)

## Security Considerations

### Authentication

- JWT token validated on every connection
- Token must not expire during long-lived connections
- Re-authenticate on token refresh

### Authorization

- User can only receive their own notifications
- Server validates room membership before emitting
- Department membership verified on connection

### Rate Limiting

- Max 100 connections per user (prevent abuse)
- Max 1000 events per minute per connection
- Excessive connections trigger temporary ban

## Testing

### Mock Server (Development)

```javascript
// mock-socket-server.js
import { Server } from 'socket.io';

const io = new Server(3001, {
  cors: { origin: '*' }
});

io.of('/notifications').on('connection', (socket) => {
  console.log('Client connected');
  
  socket.emit('authenticated', { user_id: 'test-user' });
  
  // Simulate incoming notification
  setTimeout(() => {
    socket.emit('notification:new', {
      id: 'test-notif-1',
      title: 'Test Notification',
      content: 'This is a test',
      type: { name: 'system', icon: 'bell', color: '#1890ff' },
      sender: { username: 'admin', display_name: 'Admin User' },
      created_at: new Date().toISOString(),
      recipient_id: 'test-recipient-1'
    });
  }, 2000);
});
```

### Client Test Example

```javascript
// notification-socket.test.js
describe('Notification WebSocket', () => {
  let socket;
  
  beforeEach((done) => {
    socket = io('/notifications', {
      auth: { token: 'test-jwt-token' }
    });
    socket.on('authenticated', () => done());
  });
  
  afterEach(() => {
    socket.disconnect();
  });
  
  test('receives new notification', (done) => {
    socket.on('notification:new', (data) => {
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('title');
      expect(data).toHaveProperty('content');
      done();
    });
    
    // Trigger from server-side or mock
  });
});
```

## Performance Considerations

### Connection Pooling

- Socket.IO maintains persistent connections
- Each connection uses ~50KB memory
- Scale horizontally with Redis adapter for multi-server setups

### Event Batch Processing

For high-volume scenarios:

```javascript
// Batch notification updates
socket.on('notification:batch', (data) => {
  const { notifications, unread_count } = data;
  // Process batch instead of individual events
  notifications.forEach(processNotification);
  updateUnreadCount(unread_count);
});
```

### Debouncing UI Updates

```javascript
import { debounce } from 'lodash';

const debouncedUpdate = debounce((count) => {
  updateBadge(count);
}, 300);

socket.on('notification:new', () => {
  unreadCount++;
  debouncedUpdate(unreadCount);
});
```

## Migration Notes

### From Polling to WebSocket

If migrating from HTTP polling:

1. Implement WebSocket alongside existing HTTP API
2. Gradually migrate clients (feature flag)
3. Maintain HTTP as fallback
4. Remove polling after full migration

### Backward Compatibility

```javascript
// Check WebSocket support
if ('WebSocket' in window) {
  useWebSocketNotifications();
} else {
  usePollingFallback();
}
```
