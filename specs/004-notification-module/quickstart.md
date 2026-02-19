# Quick Start: Internal Notification Module

**Prerequisites**: Python 3.11, Node.js 18+, Git

## Backend Setup

### 1. Clone and Navigate

```bash
cd /Users/peter/Documents/arco
git checkout 004-notification-module
```

### 2. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Run migrations
flask db upgrade

# Seed default notification types
flask seed-notification-types
```

### 4. Environment Configuration

Create `.env` file:

```bash
# Database
DATABASE_URL=sqlite:///arco.db

# JWT Secret (use strong secret in production)
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600

# SocketIO
SOCKETIO_ASYNC_MODE=threading
SOCKETIO_CORS_ALLOWED_ORIGINS=http://localhost:5173

# Notification Settings
NOTIFICATION_RETENTION_DAYS=90
NOTIFICATION_MAX_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAYS=60,300,900
```

### 5. Run Development Server

```bash
# Terminal 1: Flask API
flask run --port=5000

# Terminal 2: Flask-SocketIO (if separate process)
python -m src.notifications.websocket_server
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create `.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:5000/api/v1
VITE_SOCKETIO_URL=http://localhost:5000
```

### 3. Run Development Server

```bash
npm run dev
```

Frontend available at: http://localhost:5173

## Testing

### Backend Tests

```bash
cd backend
pytest tests/unit/notifications/ -v
pytest tests/integration/notifications/ -v
```

### Frontend Tests

```bash
cd frontend
npm run test:unit
npm run test:e2e
```

### Manual Testing Checklist

- [ ] Send notification to single user
- [ ] Send notification to department
- [ ] Receive real-time notification via WebSocket
- [ ] Mark notification as read/unread
- [ ] View notification history
- [ ] Search notifications
- [ ] Create notification type (admin)
- [ ] Permission denied for unauthorized send

## API Examples

### Send Notification (curl)

```bash
# Send to users
curl -X POST http://localhost:5000/api/v1/notifications \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_type": "users",
    "user_ids": ["user-uuid-1", "user-uuid-2"],
    "type_id": "type-uuid",
    "title": "Meeting Reminder",
    "content": "Team meeting in 15 minutes"
  }'

# Send to department
curl -X POST http://localhost:5000/api/v1/notifications \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_type": "department",
    "department_id": "dept-uuid",
    "type_id": "type-uuid",
    "title": "Department Update",
    "content": "New policy effective immediately"
  }'
```

### Get My Notifications

```bash
curl http://localhost:5000/api/v1/notifications/my \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

### Mark as Read

```bash
curl -X PATCH http://localhost:5000/api/v1/notifications/my/{id}/read \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

## Development Workflow

### Adding a New Feature

1. **Update Spec**: Edit `specs/004-notification-module/spec.md`
2. **Update Data Model**: Edit `data-model.md` if schema changes
3. **Update API Contract**: Edit `contracts/openapi.yaml`
4. **Implement Backend**: 
   - Model changes in `backend/src/notifications/models.py`
   - API endpoints in `backend/src/notifications/api.py`
   - Business logic in `backend/src/notifications/services.py`
5. **Implement Frontend**:
   - Vue components in `frontend/src/components/notifications/`
   - Store updates in `frontend/src/stores/notifications.ts`
6. **Write Tests**: Unit and integration tests
7. **Update Documentation**: This file and README

### Running Linters

```bash
# Backend
cd backend
ruff check src/notifications/
ruff format src/notifications/

# Frontend
cd frontend
npm run lint
npm run format
```

### Type Checking

```bash
# Backend (using mypy)
mypy src/notifications/

# Frontend
npm run type-check
```

## Debugging

### Backend Debug

```python
# Add to code
import pdb; pdb.set_trace()

# Or use Flask debug mode
FLASK_DEBUG=1 flask run
```

### WebSocket Debug

```bash
# Enable Socket.IO logging
export SOCKETIO_LOG_LEVEL=DEBUG

# Test with wscat
npm install -g wscat
wscat -c ws://localhost:5000/socket.io/?EIO=4&transport=websocket
```

### Frontend Debug

```bash
# Vue DevTools
# Install browser extension, then:
npm run dev -- --open

# Debug WebSocket
# In browser console:
socket.emit('notification:acknowledge', { recipient_id: 'test' })
```

## Common Issues

### Issue: WebSocket connection fails

**Solution**: 
- Check CORS settings in `.env`
- Verify JWT token is valid and not expired
- Check firewall/proxy settings

### Issue: Notifications not persisting

**Solution**:
- Verify database migrations applied: `flask db upgrade`
- Check SQLAlchemy model definitions
- Review audit logs for errors

### Issue: Permission denied errors

**Solution**:
- Verify user has required RBAC permissions
- Check permission decorator on API endpoints
- Review role-permission mappings

## Production Deployment

### Database Migration

```bash
# Production database
export DATABASE_URL=postgresql://user:pass@host:5432/arco
flask db upgrade
```

### Environment Variables

```bash
# Production settings
FLASK_ENV=production
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=<strong-random-secret>
SOCKETIO_ASYNC_MODE=gevent
SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/0
NOTIFICATION_RETENTION_DAYS=90
```

### Docker Deployment

```bash
# Build
docker build -t arco-notifications .

# Run
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://... \
  -e JWT_SECRET_KEY=... \
  arco-notifications
```

### Scaling

For high-traffic deployments:

1. **Use Redis Adapter**: Enable multi-server WebSocket broadcasting
2. **Database Read Replicas**: For notification history queries
3. **CDN**: For notification type icons and assets
4. **Monitoring**: Set up metrics and alerting

## Architecture Overview

```
┌─────────────┐      HTTP/REST      ┌──────────────┐
│   Frontend  │◄───────────────────►│ Flask API    │
│  (Vue 3)    │                     │              │
└──────┬──────┘                     │  ┌─────────┐ │
       │      WebSocket (Socket.IO) │  │ Models  │ │
       └────────────────────────────►│  │ Services│ │
                                    │  │ API     │ │
                                    │  └────┬────┘ │
                                    │       │      │
                                    │  ┌────▼────┐ │
                                    │  │Database │ │
                                    │  │(SQLAlch)│ │
                                    │  └─────────┘ │
                                    └──────────────┘
```

## Resources

- [Flask-SocketIO Docs](https://flask-socketio.readthedocs.io/)
- [Socket.IO Protocol](https://socket.io/docs/v4/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)

## Support

For issues or questions:
1. Check this document first
2. Review `specs/004-notification-module/spec.md`
3. Check test files for usage examples
4. Create issue in project tracker
