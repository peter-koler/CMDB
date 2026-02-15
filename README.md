# CMDB / IT 运维平台

基于 `Flask + Vue 3 + Ant Design Vue` 的一体化运维平台，当前重点围绕 **CMDB 模型、CI 实例、关系管理、拓扑视图** 持续迭代。

## 当前状态（2026-02-15）

- 已具备完整的 CMDB 主流程：
  - 模型管理（动态表单设计）
  - CI 实例管理（配置仓库）
  - 关系类型管理
  - 关系触发器管理
  - 全局拓扑视图
  - CI 详情关系拓扑
- 关系管理近期优化已落地：
  - 模型图标支持内置+上传（png/svg）
  - 关键属性配置（最多 3 个）
  - 拓扑节点按模型图标渲染，支持拖拽
  - 拓扑节点点击可查看 CI 详情
  - CI 详情页关系管理与拓扑展示已对齐优化
  - CI 复制流程修复（避免 `/instances/null` 请求）

## 技术栈

- 后端
  - Python 3.11
  - Flask 3.0.0
  - Flask-SQLAlchemy 3.1.1
  - SQLAlchemy 2.0.36
  - Flask-JWT-Extended
- 前端
  - Vue 3 + TypeScript
  - Vite 5
  - Ant Design Vue 4
  - Pinia
  - AntV G6 5.x（拓扑）

## 目录结构

```text
.
├── backend/                    # Flask 后端
│   ├── app/
│   │   ├── models/             # 数据模型
│   │   ├── routes/             # API 路由
│   │   ├── services/           # 业务服务
│   │   └── utils/              # 工具与鉴权
│   ├── requirements.txt
│   └── run.py
├── frontend/                   # Vue 前端
│   ├── src/
│   │   ├── api/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── stores/
│   │   └── views/
│   ├── scripts/
│   │   └── vue-tsc-compat.cjs  # Node22 下 vue-tsc 兼容脚本
│   └── package.json
├── docs/                       # 需求与设计文档
└── start.sh                    # 一键启动脚本
```

## 快速启动

### 方式一：一键启动（推荐）

```bash
chmod +x start.sh
./start.sh
```

默认访问：

- 前端: [http://localhost:3000](http://localhost:3000)
- 后端: [http://localhost:5000](http://localhost:5000)
- 健康检查: [http://localhost:5000/api/v1/health](http://localhost:5000/api/v1/health)

### 方式二：手动启动

后端：

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 开发命令

后端：

```bash
cd backend
python run.py
```

前端：

```bash
cd frontend
npm run dev
npm run build
npm run typecheck
npm run lint
```

## 主要功能模块

- 配置管理
  - 模型管理（含动态表单设计、关键属性、图标配置）
  - 关系类型管理
  - 关系触发器管理
- CMDB
  - 配置仓库（CI 实例）
  - 全文搜索
  - 变更历史
  - 拓扑视图（全局）
- 系统管理
  - 用户、角色、部门
  - 系统配置
  - 日志审计

## CMDB 关系管理说明

- 支持关系类型约束校验（模型白名单、唯一性、自环等）
- 支持手动创建/删除关系
- 支持引用字段触发关系同步
- 支持全局拓扑与 CI 详情拓扑双场景展示
- 支持拓扑数据导出（CSV）

详细需求与变更记录见：

- `/Users/peter/Documents/arco/docs/CMDB关系管理功能需求规划.md`
- `/Users/peter/Documents/arco/docs/CMDB关系管理技术设计文档.md`

## 默认账号

- 用户名：`admin`
- 密码：`admin`

首次启动会自动初始化默认账号与系统配置项（见后端初始化逻辑）。

## API 基础信息

- Base URL: `http://localhost:5000/api/v1`
- Auth: `Bearer Token`

典型接口：

- `POST /auth/login`
- `GET /cmdb/models`
- `GET /cmdb/instances`
- `GET /cmdb/topology`
- `GET /cmdb/instances/:id/relations`

## 已知事项

- 当前仓库存在部分历史 TypeScript 告警/错误，`npm run typecheck` 未完全清零。
- 为兼容 Node 22 与旧版 `vue-tsc`，提供了 `frontend/scripts/vue-tsc-compat.cjs`。
- `build` 默认使用 `vite build`；类型检查请单独执行 `npm run typecheck`。

## 安全与部署建议

- 生产环境务必修改：
  - `backend/config.py` 中密钥配置
  - 默认管理员密码
  - 数据库连接配置
- 建议启用 HTTPS 与 CORS 白名单控制。

## License

MIT
