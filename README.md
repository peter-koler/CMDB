# IT运维平台

基于 Vue 3 + Flask 的现代化 IT 运维管理系统，支持用户管理、权限控制、系统配置、操作审计等功能。

## 项目结构

```
it-ops-platform/
├── backend/           # Flask 后端
│   ├── app/
│   │   ├── models/    # 数据库模型
│   │   ├── routes/    # API 路由
│   │   ├── services/  # 业务逻辑
│   │   └── utils/     # 工具函数
│   ├── config.py      # 配置文件
│   ├── requirements.txt
│   └── run.py         # 启动入口
├── frontend/          # Vue 3 前端
│   ├── src/
│   │   ├── api/       # API 接口
│   │   ├── components/# 组件
│   │   ├── i18n/      # 多语言
│   │   ├── layouts/   # 布局
│   │   ├── router/    # 路由
│   │   ├── stores/    # Pinia 状态管理
│   │   └── views/     # 页面
│   ├── package.json
│   └── vite.config.ts
└── start.sh           # 一键启动脚本
```

## 快速开始

### 方式一：一键启动（推荐）

```bash
# 给脚本添加执行权限（首次使用）
chmod +x start.sh

# 启动项目
./start.sh
```

脚本会自动：
- 创建 Python 虚拟环境
- 安装后端依赖
- 安装前端依赖
- 启动后端服务 (端口 5000)
- 启动前端服务 (端口 3000)

### 方式二：手动启动

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

后端运行在: http://localhost:5000

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在: http://localhost:3000

## 默认账号

- **用户名**: admin
- **密码**: admin

## 功能模块

### 1. 系统管理
- **用户管理**: 增删改查用户、重置密码、锁定/解锁账户
- **系统配置**: Token有效期、密码策略、登录安全、日志保留期
- **日志审计**: 查看操作日志、筛选、导出

### 2. 安全特性
- JWT Token 认证 (Access Token + Refresh Token)
- 密码 bcrypt 加密存储
- 登录失败锁定机制
- 密码历史检查
- 密码复杂度验证
- 操作日志审计

## API 文档

### 基础信息
- **基础URL**: `http://localhost:5000/api/v1`
- **认证方式**: Bearer Token

### 主要接口

#### 认证
- POST `/auth/login` - 用户登录
- POST `/auth/logout` - 用户登出
- GET `/auth/me` - 获取当前用户信息

#### 用户管理
- GET `/users` - 用户列表
- POST `/users` - 创建用户
- PUT `/users/:id` - 更新用户
- DELETE `/users/:id` - 删除用户
- POST `/users/:id/reset-password` - 重置密码
- POST `/users/:id/unlock` - 解锁用户

#### 系统配置
- GET `/configs` - 获取配置
- PUT `/configs` - 更新配置

#### 日志审计
- GET `/logs` - 日志列表
- GET `/logs/export` - 导出日志

## 开发计划

- [x] 项目基础架构搭建
- [x] 后端 API 开发（认证、用户、配置、日志）
- [x] 前端登录页面
- [x] 主页面框架（Ant Design Pro 风格）
- [x] 用户管理功能
- [x] 系统配置功能
- [x] 日志审计功能
- [x] 多语言支持
- [ ] 主题切换
- [ ] 更多系统管理功能

## 技术栈

### 后端
- **框架**: Flask 3.x
- **数据库**: SQLite (开发) / MySQL (生产)
- **ORM**: Flask-SQLAlchemy
- **认证**: Flask-JWT-Extended
- **密码加密**: bcrypt
- **迁移**: Alembic

### 前端
- **框架**: Vue 3.4 + TypeScript
- **构建工具**: Vite 5
- **UI组件库**: Ant Design Vue 4.x
- **状态管理**: Pinia 2.x
- **路由**: Vue Router 4
- **HTTP客户端**: Axios
- **国际化**: Vue I18n 9

## 注意事项

1. **生产环境部署前必须修改**:
   - `backend/config.py` 中的 SECRET_KEY 和 JWT_SECRET_KEY
   - 修改默认管理员密码
   - 配置生产环境数据库

2. **安全性**:
   - 生产环境必须使用 HTTPS
   - 配置 CORS 白名单
   - 定期更换密钥

## License

MIT
