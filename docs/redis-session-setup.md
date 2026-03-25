# Redis Session 配置说明

## 概述

项目已从文件 Session 切换到 Redis Session，以提高性能、可扩展性和安全性。

## 配置变更

### 1. 配置文件 (config.py)

```python
# Session 配置 - Redis
SESSION_TYPE = "redis"
SESSION_REDIS = redis.from_url(
    os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
)
SESSION_KEY_PREFIX = "itops:session:"
SESSION_USE_SIGNER = True
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

# Cookie 安全
SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False  # 生产环境设为 True
SESSION_COOKIE_HTTPONLY = True
```

### 2. 依赖安装

```bash
cd /Users/peter/Documents/arco/backend
pip install -r requirements.txt
```

新添加的依赖：`redis==5.0.1`

## 启动步骤

### 1. 启动 Redis

**macOS (使用 Homebrew):**
```bash
# 安装 Redis
brew install redis

# 启动 Redis 服务
brew services start redis

# 检查 Redis 状态
redis-cli ping
# 应该返回: PONG
```

**Docker:**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Linux:**
```bash
sudo systemctl start redis
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，确保包含：
REDIS_URL=redis://localhost:6379/0
```

### 3. 启动 Flask 应用

```bash
cd /Users/peter/Documents/arco/backend
python run.py
```

## 验证 Session 是否正常工作

### 1. 检查 Redis 中的 Session

```bash
# 连接到 Redis
redis-cli

# 查看所有 Session
KEYS itops:session:*

# 查看某个 Session 的内容
GET itops:session:<session_id>

# 查看 Session 过期时间
TTL itops:session:<session_id>
```

### 2. 浏览器验证

1. 登录系统
2. 检查浏览器 Cookie 中是否有 `session_id`
3. 刷新页面，确认登录状态保持

## 生产环境配置

### 1. 使用带密码的 Redis

```bash
# 环境变量
REDIS_URL=redis://:your-password@localhost:6379/0
```

### 2. 启用 HTTPS

```python
# config.py - ProductionConfig
SESSION_COOKIE_SECURE = True
```

### 3. Redis 配置建议

```bash
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## 故障排查

### 问题 1: Connection refused

**原因**: Redis 服务未启动

**解决**:
```bash
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

### 问题 2: ModuleNotFoundError: No module named 'redis'

**解决**:
```bash
pip install redis==5.0.1
```

### 问题 3: Session 丢失

**检查**:
1. Redis 连接是否正常
2. `SESSION_COOKIE_SECURE` 是否与协议匹配（HTTPS/HTTP）
3. `CORS_ORIGINS` 是否包含前端地址

## 切换回文件 Session（如需要）

如需临时切换回文件 Session，修改 `config.py`:

```python
SESSION_TYPE = "filesystem"
SESSION_FILE_DIR = "/tmp/flask_session"
```

## 注意事项

1. **Session 有效期**: 默认为 8 小时，可通过 `PERMANENT_SESSION_LIFETIME` 调整
2. **内存管理**: Redis 默认无内存限制，建议配置 `maxmemory`
3. **数据持久化**: Redis 默认开启 RDB 持久化，重启后 Session 不会丢失
4. **多实例部署**: Redis Session 支持多 Flask 实例共享 Session
