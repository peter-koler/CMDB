# 通知模块 WebSocket 文档

## 连接信息

- **URL**: `ws://localhost:5000/notifications`
- **命名空间**: `/notifications`
- **认证方式**: JWT Token (Query参数或Header)

## 连接方式

### 方式一：Query参数

```javascript
const socket = io('ws://localhost:5000/notifications', {
  query: {
    token: 'your_jwt_token'
  }
});
```

### 方式二：Header

```javascript
const socket = io('ws://localhost:5000/notifications', {
  extraHeaders: {
    Authorization: 'Bearer your_jwt_token'
  }
});
```

## 事件列表

### 客户端事件（发送）

#### 连接

```javascript
socket.on('connect', () => {
  console.log('WebSocket连接成功');
});
```

#### 认证成功

```javascript
socket.on('authenticated', (data) => {
  console.log('认证成功:', data);
  // data: { user_id: 1, connected_at: "2026-02-19T10:00:00" }
});
```

#### 认证失败

```javascript
socket.on('auth_error', (data) => {
  console.error('认证失败:', data.message);
  // data: { message: "Token missing" | "Invalid token" | "User not found" }
});
```

#### 新通知

```javascript
socket.on('notification:new', (data) => {
  console.log('收到新通知:', data);
  // data: {
  //   id: 100,
  //   title: "通知标题",
  //   content: "通知内容",
  //   content_html: "<p>通知内容</p>",
  //   type: { id: 1, name: "系统", icon: "setting", color: "#1890ff" },
  //   sender: { id: 1, username: "admin" },
  //   recipient_id: 1,
  //   created_at: "2026-02-19T10:00:00"
  // }
});
```

#### 标记已读

```javascript
socket.on('notification:read', (data) => {
  console.log('通知已读:', data);
  // data: {
  //   recipient_id: 1,
  //   notification_id: 100,
  //   user_id: 1,
  //   read_at: "2026-02-19T10:30:00"
  // }
});
```

#### 标记未读

```javascript
socket.on('notification:unread', (data) => {
  console.log('通知未读:', data);
  // data: {
  //   recipient_id: 1,
  //   notification_id: 100,
  //   user_id: 1
  // }
});
```

#### 全部已读

```javascript
socket.on('notification:read_all', (data) => {
  console.log('全部已读:', data);
  // data: {
  //   user_id: 1,
  //   marked_count: 10
  // }
});
```

#### 断开连接

```javascript
socket.on('disconnect', () => {
  console.log('WebSocket连接断开');
});
```

## 前端使用示例

### Vue 3 + Pinia 集成

```typescript
// stores/notifications.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { io, Socket } from 'socket.io-client';

export const useNotificationStore = defineStore('notifications', () => {
  const socket = ref<Socket | null>(null);
  const notifications = ref<any[]>([]);
  const unreadCount = ref(0);
  const connected = ref(false);

  // 连接WebSocket
  const connectWebSocket = (token: string) => {
    if (socket.value?.connected) return;

    socket.value = io('ws://localhost:5000/notifications', {
      query: { token }
    });

    socket.value.on('connect', () => {
      connected.value = true;
      console.log('WebSocket连接成功');
    });

    socket.value.on('authenticated', () => {
      console.log('WebSocket认证成功');
    });

    socket.value.on('auth_error', (data) => {
      console.error('WebSocket认证失败:', data.message);
    });

    socket.value.on('notification:new', (data) => {
      // 添加新通知到列表
      notifications.value.unshift(data);
      unreadCount.value++;
      
      // 显示桌面通知
      showDesktopNotification(data);
    });

    socket.value.on('notification:read', (data) => {
      // 更新本地通知状态
      const notification = notifications.value.find(
        n => n.id === data.recipient_id
      );
      if (notification) {
        notification.is_read = true;
        notification.read_at = data.read_at;
      }
    });

    socket.value.on('notification:read_all', () => {
      // 更新所有通知为已读
      notifications.value.forEach(n => {
        n.is_read = true;
      });
      unreadCount.value = 0;
    });

    socket.value.on('disconnect', () => {
      connected.value = false;
      console.log('WebSocket连接断开');
    });
  };

  // 断开连接
  const disconnectWebSocket = () => {
    socket.value?.disconnect();
    socket.value = null;
    connected.value = false;
  };

  // 显示桌面通知
  const showDesktopNotification = (data: any) => {
    if (Notification.permission === 'granted') {
      new Notification(data.title, {
        body: data.content,
        icon: '/notification-icon.png'
      });
    }
  };

  return {
    notifications,
    unreadCount,
    connected,
    connectWebSocket,
    disconnectWebSocket
  };
});
```

### 组件中使用

```vue
<template>
  <div>
    <a-badge :count="unreadCount" @click="showNotificationCenter">
      <BellOutlined />
    </a-badge>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useNotificationStore } from '@/stores/notifications';
import { BellOutlined } from '@ant-design/icons-vue';

const store = useNotificationStore();

onMounted(() => {
  const token = localStorage.getItem('token');
  if (token) {
    store.connectWebSocket(token);
  }
  
  // 请求桌面通知权限
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
});

onUnmounted(() => {
  store.disconnectWebSocket();
});
</script>
```

## 重连机制

WebSocket连接断开时会自动重连：

```javascript
socket.on('disconnect', (reason) => {
  console.log('断开原因:', reason);
  
  if (reason === 'io server disconnect') {
    // 服务器主动断开，需要手动重连
    setTimeout(() => {
      socket.connect();
    }, 3000);
  }
  // 其他情况会自动重连
});
```

## 错误处理

```javascript
socket.on('error', (error) => {
  console.error('WebSocket错误:', error);
});

socket.on('connect_error', (error) => {
  console.error('连接错误:', error.message);
});
```

## 性能优化

1. **心跳检测**: 自动保持连接活跃
2. **房间机制**: 用户自动加入专属房间，只接收自己的通知
3. **批量推送**: 广播通知使用批量推送，减少服务器压力
4. **重连退避**: 重连间隔逐渐增加，避免服务器过载

## 安全说明

1. **Token验证**: 每个连接都需要有效的JWT Token
2. **用户隔离**: 用户只能接收自己的通知
3. **房间隔离**: 使用Socket.IO房间机制确保消息不泄露
4. **过期检查**: Token过期后连接会被断开
