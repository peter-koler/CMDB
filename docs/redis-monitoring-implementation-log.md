# Redis 监控链路改造过程记录

## 0. 背景与目标
- 日期: 2026-03-09
- 目标:
  - 监控任务以 CMDB CI 作为监控对象创建
  - 任务基于监控模板（YAML）参数进行采集配置
  - 打通 Collector -> Manager -> VictoriaMetrics 数据链路（本次先验证 Redis）
  - 在监控任务详情提供指标图表展示（含时间范围和自动刷新）

## 1. 基线摸底
- 已阅读文档:
  - `docs/migration-plan-new.md`
  - `docs/api/*`（manager-openapi, grpc-versioning, metric-label-spec, env-baseline 等）
- 现状结论:
  - Flask 监控路由 `/api/v1/monitoring/targets` 目前主要代理到 Manager
  - Manager 具备 monitor CRUD 与 metric ingest 能力，但未形成“Collector 上报 -> ingest”闭环
  - Collector 已具备 gRPC 双向流与本地调度，但缺少 `redis` 协议采集器
  - 前端监控列表已支持新增/编辑，但未接入“模型->CI->模板参数”流程，也无指标详情图

## 2. 实施计划
1. 扩展 Manager monitor 模型与任务构建（含 redis 任务）
2. 新增 Collector redis 协议采集
3. 新增 Manager 指标查询 API（series/range）
4. 扩展 Flask 监控路由（创建参数适配 + 指标代理）
5. 改造前端监控新增流程与详情指标 Tab
6. 本机 Redis/VM 联调与验证

## 3. 风险与处理策略
- 风险: 现有工作区有未提交改动（frontend/manager-go）
- 策略: 本次仅增量改造，避免回滚或覆盖已有改动

## 4. Step-1：Manager 监控任务模型扩展
- 文件:
  - `manager-go/internal/model/monitor.go`
  - `manager-go/internal/store/monitor_store.go`
- 变更:
  - 监控任务新增字段：`job_id`, `ci_id`, `ci_model_id`, `ci_name`, `ci_code`, `params`, `labels`
  - 入参兼容：`interval` 与 `interval_seconds` 双字段
  - 新建任务自动生成唯一任务标识：`job-<monitor_id>-<unix_ms>`
  - 采集间隔下限统一为 `>= 10s`

## 5. Step-2：Manager Collector 调度能力增强
- 文件:
  - `manager-go/internal/collector/manager.go`
- 变更:
  - 增加双向通信回调注入方法：`SetReportHandler` / `SetAckHandler`
  - 增加任务与采集器绑定能力：`AssignCollector` / `UnassignCollector`
  - 任务分发支持固定绑定 + 自动负载
  - 新增 Redis 任务构建：
    - 协议：`redis`
    - 参数：`host/port/timeout/username/password/section`
    - 默认 section：`server,clients,memory,stats`

## 6. Step-3：Collector 新增 Redis 协议采集器
- 文件:
  - `collector-go/internal/protocol/rediscollector/redis.go`
  - `collector-go/internal/protocol/rediscollector/redis_test.go`
  - `collector-go/internal/bootstrap/register.go`
- 变更:
  - 新增 `redis` 协议注册与采集实现（RESP/TCP）
  - 支持 AUTH（密码或用户名+密码）
  - 支持 `INFO` 与 `INFO <section>` 采集
  - 解析 `commandstats` 复合字段为扁平 key（如 `cmdstat_get_calls`）
  - 返回身份字段：`identity=host:port`

## 7. Step-4：Manager 指标写入规范强化
- 文件:
  - `manager-go/internal/dispatch/vm_sink.go`
- 变更:
  - 指标名与标签键统一正则规范化
  - 屏蔽高基数危险标签（timestamp/uuid/trace_id/request_id 等）
  - 保留必要标签：`job`, `instance`, `__monitor_id__`, `__metrics__`, `__metric__`

## 8. Step-5：Manager 增加指标查询 API（供前端图表）
- 文件:
  - `manager-go/internal/metrics/vm_client.go`（新增）
  - `manager-go/internal/httpapi/server.go`
- 变更:
  - 新增 VM 查询客户端：
    - `GET /api/v1/series`
    - `GET /api/v1/query_range`
  - 新增 Manager 查询接口：
    - `GET /api/v1/metrics/series?monitor_id=...`
    - `GET /api/v1/metrics/query-range?monitor_id=...`
  - 支持 `from/to/step` 与 `name/names` 参数
  - 兼容按 monitor_id 聚合查询

## 9. Step-6：Manager 主程序接入 Collector 上报闭环
- 文件:
  - `manager-go/cmd/manager/main.go`
- 变更:
  - Collector 回调接入：
    - `CollectRep` -> 转换为 `MetricPoint` -> `pipeline.Submit` -> Redis + VictoriaMetrics
    - `CommandAck` 写入日志追踪
  - 新增 `WithVMQueryClient` 注入，前端可直接经 manager 查询 VM
  - 指标点转换策略：
    - 每次上报默认产出 `success` 与 `raw_latency_ms`
    - `fields` 中可解析数值字段逐个转为时序点
    - `identity` 作为 instance 优先来源
  - 当存在已连接 Collector 时，不再写入本地 fallback 的 `manager_dispatch` 点，避免干扰 Redis 验收图表

## 10. Step-7：Flask 监控目标代理增强
- 文件:
  - `backend/app/routes/monitoring_target.py`
- 变更:
  - 新建任务时兼容 `interval -> interval_seconds`
  - 采集间隔校验最小 `10s`
  - `target` 空值时按规则回填：
    - 优先 `params.host:params.port`
    - 回退 `ci_code` 或 `ci_id`
  - 新增前端代理接口：
    - `GET /api/v1/monitoring/targets/<id>/metrics/series`
    - `GET /api/v1/monitoring/targets/<id>/metrics/query-range`

## 11. Step-8：前端“监控任务详情-指标Tab”与新建流程改造
- 文件:
  - `frontend/src/api/monitoring.ts`
  - `frontend/src/views/monitoring/target/index.vue`
- 变更:
  - 新建/编辑任务改为：
    - 选择 CI 模型
    - 选择 CI 实例
    - 选择监控模板
    - 根据模板 YAML `params` 自动渲染参数输入项（手工填写，不做 CI 自动填充）
  - 新增任务详情抽屉，包含：
    - `基本信息` Tab
    - `指标` Tab（可视化曲线）
  - 指标 Tab 功能：
    - 默认最近 `1h`
    - 快捷范围：`5m / 1h / 24h / 7d / 30d / 自定义`
    - 支持开始/结束时间选择
    - 自动刷新开关与间隔（30s/60s/120s）
    - 多指标选择与单独刷新

## 12. Step-9：测试与构建验证
- Go:
  - `manager-go`: `go test ./...` 通过
  - `collector-go`: `go test ./...` 通过（包含新增 `rediscollector` 单测）
- Python:
  - `python3 -m py_compile backend/app/routes/monitoring_target.py` 通过
- Frontend:
  - `npm run build` 通过（页面可构建）
  - `npm run typecheck` 未通过，存在项目历史遗留 TS 错误（与本次改造无关，多个模块已有报错）

## 13. Step-10：本机 Redis/VM 容器环境尝试
- 执行:
  - `docker compose up -d redis victoria-metrics`
- 结果:
  - 失败，原因：本机 Docker daemon 未启动（无法连接 `/Users/peter/.docker/run/docker.sock`）
- 结论:
  - 代码链路已就绪，待本机启动 Docker Desktop 后可直接拉起容器复验

## 14. 当前验收建议（Redis 图表）
1. 若 Redis/VictoriaMetrics 未运行，则启动容器；若已运行则跳过
2. 启动 manager-go 与 collector-go（保持双向连接）
3. 在前端新增 Redis 监控任务（选择 CI + redis 模板 + host/port）
4. 打开任务详情 -> `指标` Tab，确认 1h 默认窗口下出现真实 Redis 指标曲线

## 15. 用户补充说明（2026-03-09）
- 用户说明：后台已有 Docker 运行环境，无需我代为启动容器。
- 已按说明停止容器启动动作，仅保留应用侧改造与联调路径。

## 16. Step-11：前端与任务更新稳定性修复
- 文件:
  - `frontend/src/views/monitoring/target/index.vue`
- 修复:
  - 编辑任务时，始终保证 `target` 有值（优先表单，其次 `params.host:port`，再回退历史 target/CI 编码）
  - 避免编辑回填时被 `ci_model_id` 的 watcher 清空 `ci_id`
  - Collector 固定分配逻辑调整为：仅在勾选“固定分配”时才调用绑定接口，未勾选则保持自动分配

## 17. Step-12：再次回归验证
- Go:
  - `manager-go`: `go test ./...` 通过
  - `collector-go`: `go test ./...` 通过
- Frontend:
  - `npm run build` 通过
- 说明:
  - `npm run typecheck` 的失败项仍为项目已有历史问题，不影响本次改造代码构建

## 18. Step-13：线上报错修复（legacy DB 缺少 pinned 列）
- 触发日志:
  - `create bind failed: table collector_monitor_binds has no column named pinned`
- 根因:
  - 旧库中的 `collector_monitor_binds` 表无 `pinned` 字段
  - `InitTable()` 只补了 `creator/modifier`，未补 `pinned`
- 修复:
  - 文件：`manager-go/internal/store/collector_store.go`
  - 在 `InitTable()` 增加自动迁移：`addColumnIfNotExists(..., \"pinned\", \"INTEGER NOT NULL DEFAULT 0\")`
  - 重写 `addColumnIfNotExists` 的列探测逻辑为 `PRAGMA table_info(table)` 扫描（避免旧写法在 SQLite 下探测不稳定）
- 回归测试:
  - 新增 `manager-go/internal/store/collector_store_test.go`
  - 用 legacy schema（无 pinned）构建临时库，验证 `InitTable()` 后可成功 `CreateBind(..., pinned=1)`
- 验证:
  - `manager-go go test ./...` 通过

## 19. Step-14：告警轮询查询空结果降噪
- 触发日志:
  - `periodic rule query error rule=manager_dispatch_tick_avg_5m_high err=vm query empty`
- 根因:
  - 告警周期评估里将 VM “空结果”当成错误日志输出
  - 在监控刚创建或时间窗口内暂无数据时，该现象属于预期，不应按错误打印
- 修复:
  - 文件：`manager-go/internal/alert/periodic.go`
  - 增加 `errors.Is(err, ErrVMQueryEmptyResult)` 判断，命中时直接按“无数据”跳过本轮，不打印 error 日志
- 回归测试:
  - 文件：`manager-go/internal/alert/periodic_test.go`
  - 新增 `TestPeriodicRuleSkipWhenVMEmptyResult`，验证空结果不会生成事件
  - 新增 `TestPeriodicRuleContinueLogOnNonEmptyError`，保留非空结果错误路径行为
- 验证:
  - `manager-go go test ./...` 通过

## 20. Step-15：当前运行库热修复（补 pinned 列）
- 背景:
  - 代码已支持启动时自动补列，但当前正在运行的 SQLite 库仍缺少 `pinned`
- 检查:
  - 执行 `PRAGMA table_info(collector_monitor_binds);`，确认无 `pinned`
- 热修复:
  - 执行 SQL：
    - `ALTER TABLE collector_monitor_binds ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0;`
- 结果:
  - 再次执行 `PRAGMA table_info(...)`，已出现 `pinned` 列
  - 新增任务时 `CreateBind` 不再因缺列失败

## 21. Step-16：监控模板菜单与 YAML 参数重复问题优化
- 用户反馈:
  - 监控模板菜单展示和 YAML 参数展示体验异常，感知到 `redis` 等模板存在“port 重复”问题
- 先行核查（含 HertzBeat 源码）:
  - 对比 `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-redis.yml` 与 `backend/templates/app-redis.yml`
  - 结果：`params` 中 `field: port` 在 Redis 模板里仅出现一次，源 YAML 本身无重复
- 根因判断:
  - 重复感知主要来自前端模板管理/预览与参数渲染链路未做去重防护
  - 模板管理页分类与模板装载逻辑可维护性较差，容易造成菜单体验混乱
- 改造内容:
  - 文件：`frontend/src/views/monitoring/template/index.vue`
    - 分类树与模板装载改为后端数据驱动
    - 模板列表按 `app` 去重
    - 保存模板时解析 YAML 并对 `params.field` 去重（自动清洗并提示）
    - 新增/编辑分类改为调用后端分类 API
  - 文件：`frontend/src/views/monitoring/template/components/TemplatePreview.vue`
    - 预览时对 `params`、`metrics.fields` 按 field 去重
    - 预览参数默认过滤 `hide: true` 的隐藏参数
  - 文件：`frontend/src/views/monitoring/target/index.vue`
    - 新增监控任务时模板参数解析增加 `params.field` 去重保护
- 验证:
  - `cd frontend && npm run build` 通过

## 22. Step-17：模板管理交互回调（恢复树状子节点）
- 用户反馈:
  - 模板菜单应保持树状结构（如 `数据库 -> mysql / redis`），不希望在右侧以标签切换
- 调整:
  - 文件：`frontend/src/views/monitoring/template/index.vue`
  - 左侧树改为“分类节点 + 模板子节点”统一展示
  - 选择模板子节点时直接打开对应 YAML 编辑
  - 分类节点右键菜单仅对分类生效（模板节点不弹出分类操作菜单）
  - 保留此前的模板去重与 `params.field` 去重能力
- 验证:
  - `cd frontend && npm run build` 通过

## 23. Step-18：监控列表“监控分类”与模板树同步
- 用户反馈:
  - 监控列表页左侧“监控分类”未与监控模板树同步
- 调整:
  - 文件：`frontend/src/views/monitoring/target/index.vue`
  - 分类树改为由“分类 + 模板”共同构建，支持 `分类 -> 模板` 子节点展示
  - 树节点增加类型：
    - `category`：分类节点（显示聚合数量）
    - `template`：模板节点（如 `tpl:redis`）
  - 筛选逻辑按选中节点生效：
    - 选模板节点：按 `app` 精确过滤
    - 选分类节点：递归收集子树所有模板 `app` 后过滤
  - “刷新分类”改为同时刷新分类与模板，确保菜单与模板管理保持一致
- 验证:
  - `cd frontend && npm run build` 通过

## 24. Step-19：监控任务指标中文名映射与前端缓存优化
- 用户需求:
  - 监控任务详情“指标”图表需要显示 YAML 定义的中文指标名（示例：`clients_blocked_clients -> 阻塞客户端数量`）
  - 减少前后端交付压力，避免每次自动刷新都重复获取中文映射信息
- 调整:
  - 文件：`frontend/src/views/monitoring/target/index.vue`
  - 新增指标名展示规则：
    - 下拉选项与图表标题显示为 `中文名 (原指标名)`；无映射时回退原指标名
  - 映射来源：
    - 从当前监控模板 YAML 的 `metrics[].fields[].i18n`（兼容 `name`）解析中文名
    - 按 manager 的规范化规则生成映射键（与入库指标名一致）：`normalize(metrics + "_" + field)`
  - 性能优化：
    - 增加前端本地缓存 `metricLabelMapCache[app]`
    - 首次进入某 `app` 指标时解析一次模板内容并缓存
    - 后续自动刷新仅请求时序数据，不再重复请求/解析中文映射元数据
    - 模板列表刷新时自动清空缓存，避免旧映射污染
- 验证:
  - `cd frontend && npm run build` 通过
