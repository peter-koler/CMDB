# 通用 YAML 驱动监控架构重构计划（兼容 HertzBeat 模板）

> 日期：2026-03-09  
> 目标：将当前“部分模板驱动 + 动态采集”改造成“通用 YAML 驱动采集与计算”架构，支持后续持续导入 HertzBeat YAML。

---

## 1. 背景与问题

当前链路已实现 Manager/Collector 双向通信和基础采集闭环，但仍有关键差距：

1. 采集执行并非严格由 YAML 定义驱动，Collector 会采集并上报运行时动态字段。
2. Manager 没有“模板运行时内存仓库 + 编译任务”能力。
3. Collector 缺少统一的协议执行框架（Redis/HTTP/SSH/MySQL 等统一抽象）。
4. `calculates`（例如 `query_cache_hit_rate=(Qcache_hits+1)/(Qcache_hits+Qcache_inserts+1)*100`）缺少通用执行链路。

这会导致：

1. YAML 兼容性不足，难以商用规模扩展。
2. 前后端指标口径难统一（模板字段与实际上报字段可能偏差）。
3. 计算负载集中在 Manager，无法充分利用 Collector 本地计算能力。

---

## 2. 重构目标（架构级）

### 2.1 总体目标

1. **Manager 启动加载模板到内存**（Template Runtime Registry）。
2. **创建监控实例时按模板编译任务**（Template + Params -> CollectTask Plan）。
3. **Collector 按任务配置执行采集/转换/计算**，仅返回最终结果与必要诊断信息。
4. **Manager 负责调度、聚合、存储与告警编排**，不承担重计算。
5. **兼容 HertzBeat YAML 导入**，并定义“支持级别矩阵”。

### 2.2 非目标（本阶段）

1. 不一次性实现 HertzBeat 全协议 100% 覆盖。
2. 不替换现有权限模型与前端导航结构。
3. 不破坏现有 `collector.v1` 已上线字段与 tag（仅 append）。

---

## 3. 目标架构（重构后）

```
YAML Files/DB
    -> Manager Template Registry (in-memory, versioned, hot-reload)
    -> Monitor Instance Create/Update (validate + bind template version)
    -> Task Compiler (per monitor -> CollectTask with executable config)
    -> gRPC dispatch to Collector
    -> Collector Protocol Engine (Redis/HTTP/SSH/MySQL plugin)
    -> Collector Transform & Calculates Engine (local compute)
    -> CollectRep (final fields + metadata)
    -> Manager Ingest (contract validate + write VM/Redis + alert)
```

核心原则：

1. 模板是单一事实源（source of truth）。
2. 任务是模板编译产物，不是手写拼接。
3. 采集与计算尽量下沉至 Collector。
4. 协议演进保持向后兼容。

---

## 4. 模板运行时设计（Manager）

### 4.1 Template Registry

新增 `manager-go/internal/template` 模块：

1. Loader：从 DB（monitor_template）和可选本地目录加载 YAML。
2. Parser：解析 HertzBeat 结构（app/category/params/metrics/fields/calculates）。
3. Validator：语义校验（字段重复、引用不存在、表达式合法性）。
4. Cache：内存存储，键为 `app + version/hash`。
5. Watcher：支持定时增量刷新和手工刷新接口。

建议元数据：

1. `template_runtime_version`（hash）。
2. `loaded_at`。
3. `compat_level`（strict/partial/fallback）。

### 4.2 Monitor 实例绑定策略

监控实例保存：

1. `template_app`
2. `template_version`
3. `params`
4. `labels`

原则：

1. 新建时固定版本，避免模板更新导致实例行为漂移。
2. 支持“升级到模板新版本”的显式操作（受控变更）。

### 4.3 Task Compiler

编译输入：

1. 模板定义（指定 version）。
2. 实例 params。
3. 系统默认参数（超时、重试、并发限额）。

编译输出：

1. `CollectTask`（包含多个 `MetricsTask`）。
2. 每个任务包含协议执行信息、字段映射、转换链、计算链。

编译校验失败时返回：

1. `MONITOR_INVALID_CONFIG`
2. 详细错误路径（metrics/fields/calculates 的定位信息）。

---

## 5. Collector 通用执行框架重构

### 5.1 插件化协议引擎

新增统一接口（示意）：

1. `Connector`：建立连接与认证（Redis/HTTP/SSH/MySQL...）。
2. `Fetcher`：执行采集动作，获取原始数据。
3. `Extractor`：从原始数据提取字段。
4. `Transformer`：字段转换（类型、单位、重命名）。
5. `Calculator`：执行表达式计算，输出派生指标。

执行流水线：

`connect -> fetch -> extract -> transform -> calculate -> emit`

### 5.2 计算引擎（calculates）

支持 YAML `calculates`：

1. 表达式变量引用字段值。
2. 支持 `+ - * / ()`、常量、基础函数（逐步扩展）。
3. 除零保护和 NaN/Inf 处理。
4. 失败降级策略（跳过该 calculate 并记录 reason）。

输出策略：

1. calculate 结果作为新 field 上报。
2. 保留原始 field（可按模板配置保留/不保留）。

### 5.3 本地计算与减负

Collector 默认执行：

1. 字段提取
2. 计算表达式
3. 可选预聚合（如同一轮采样局部聚合）

Manager 仅处理：

1. 存储
2. 告警评估
3. 审计与状态追踪

---

## 6. gRPC 协议演进方案（collector.v1 append-only）

遵循 `docs/api/collector-grpc-versioning.md`：

1. 仅追加字段，不改 tag，不删旧字段。
2. Manager/Collector proto 同步生成。

建议追加（示意）：

1. `MetricsTask.exec_kind`（pull/push/script/sql 等）。
2. `MetricsTask.spec_json`（编译后的执行计划，短期兼容策略）。
3. `MetricsTask.field_specs`（结构化字段定义，长期替代 spec_json）。
4. `MetricsTask.calculate_specs`（结构化计算定义）。
5. `CollectRep.debug`（可选，错误诊断与版本信息）。

兼容策略：

1. 新 Collector 兼容旧任务（无新字段时走旧逻辑）。
2. 新 Manager 下发新字段时，旧 Collector 显式 ACK_REJECTED 并带 reason。

---

## 7. 指标契约与命名一致性

遵循 `docs/api/metric-label-spec.md`：

1. 非 Prometheus 模式：`__name__={metrics}_{field}`。
2. 强制标签：`job` `instance` `__monitor_id__`。
3. 保留 `__metrics__` 和 `__metric__` 映射。
4. 屏蔽高基数黑名单标签。

新增规则：

1. 仅上报模板允许字段（白名单模式）。
2. calculate 字段进入白名单（由模板显式定义或编译注入）。
3. 不在白名单内的动态字段默认丢弃（可配 debug 模式观察）。

---

## 8. 数据模型与配置变更

建议新增（或扩展）：

1. `monitor_template_runtime`（可选，缓存快照与版本映射）。
2. `monitor_instances` 增加 `template_version`/`template_hash`（若现模型已含可复用字段则按现有模型映射）。
3. `monitor_compile_logs`（编译审计，便于定位模板问题）。

注意：

1. 继续与 Python Web 共用 metadata DB 约束（见 `m0-env-baseline.md`）。
2. 所有迁移需幂等，兼容 SQLite/PG/MySQL。

---

## 9. API 与前端影响

后端（Python Web）：

1. 新建/更新监控实例时增加模板版本字段透传。
2. 增加“预编译校验”接口（创建前校验 params 与模板匹配）。
3. 增加模板运行时状态查询接口（loaded version、compat level）。

前端：

1. 新建页显示模板版本和兼容状态。
2. 参数表单继续由 YAML `params` 驱动。
3. 指标展示优先用 YAML 字段定义，不在模板中的字段默认不展示（或单独“未映射指标”折叠区）。

---

## 10. 分阶段实施计划（可并行）

### Phase 0：设计冻结（2-3 天）

1. 冻结 YAML 支持子集（字段、表达式、协议能力）。
2. 冻结 proto 追加字段设计。
3. 冻结编译错误码与返回格式。

交付物：

1. Template Runtime Schema 文档
2. Proto 变更草案
3. Compatibility Matrix v1

### Phase 1：Manager 模板运行时与任务编译（4-6 天）

1. Template Registry + Loader + Validator。
2. 监控实例与模板版本绑定。
3. Task Compiler（先支持 Redis/HTTP/MySQL）。
4. 预编译校验 API。

交付物：

1. Manager 内存模板仓库可用
2. 编译日志与错误定位可用

### Phase 2：Collector 通用执行框架（6-10 天）

1. 协议插件框架重构。
2. Redis/HTTP/MySQL 首批协议适配。
3. Transform + Calculates 引擎落地。
4. 批量上报结构优化（减少冗余原始字段）。

交付物：

1. Collector 本地计算闭环可用
2. `calculates` 示例通过（含 MySQL query_cache_hit_rate）

### Phase 3：契约收口与灰度切换（4-6 天）

1. 双轨运行：legacy 与 yaml-driven 并存。
2. 开关控制（monitor 级别）。
3. 回归测试、压测、错误注入测试。
4. 默认模式切换为 yaml-driven。

交付物：

1. 灰度策略与回滚方案
2. 生产切换检查清单

---

## 11. 多 Codex 并行分工建议

进程 A（Manager Runtime）：

1. Template Registry
2. Task Compiler
3. Compile API
4. 错误码对齐

进程 B（Proto & Transport）：

1. proto append 字段
2. 双端 pb 生成
3. ACK 兼容与降级策略

进程 C（Collector Engine）：

1. 通用协议执行管线
2. Redis/HTTP/MySQL 适配器
3. transform/calculate 执行器

进程 D（Python Web & Frontend）：

1. 模板版本透传
2. 预编译校验接入
3. UI 的兼容状态与版本展示

进程 E（QA & Tooling）：

1. 合同测试（proto/openapi/metric）
2. 模板样例集与回归集
3. 压测与故障注入

---

## 12. 风险与对策

1. 风险：模板语义覆盖不全导致导入失败。  
对策：先定义支持级别矩阵；不支持项清晰报错并可降级。

2. 风险：proto 演进引发新老版本互操作问题。  
对策：严格 append-only；增加互操作集成测试。

3. 风险：Collector 本地计算引擎性能抖动。  
对策：表达式预编译缓存 + 采集超时隔离 + 限流。

4. 风险：指标口径切换造成历史面板波动。  
对策：双轨并行窗口 + 新旧字段映射层 + 迁移公告。

---

## 13. 验收标准（商用导向）

1. 任意新增 HertzBeat YAML（在支持子集内）可导入并成功编译任务。
2. 监控实例创建时可看到模板版本并通过编译校验。
3. Collector 按模板采集与计算，Manager 不再进行同等计算。
4. MySQL `calculates` 示例可稳定产出正确指标。
5. 指标命名与标签满足 `metric-label-spec`。
6. 端到端性能：
   - Manager CPU 降幅可观（相对当前基线）。
   - Collector 单实例吞吐达到预设目标。
7. 新老版本灰度与回滚可执行。

---

## 14. 第一批落地范围建议（M1）

1. 协议：Redis + HTTP + MySQL
2. 模板能力：params / fields / calculates
3. 模板来源：DB 为主，本地目录为辅
4. 运行模式：legacy + yaml-driven 双轨开关

---

## 15. 关键参考文档

1. `docs/migration-plan-new.md`
2. `docs/api/collector-grpc-versioning.md`
3. `docs/api/metric-label-spec.md`
4. `docs/api/manager-openapi.yaml`
5. `docs/api/manager-error-codes.md`
6. `docs/api/m0-env-baseline.md`

---

## 16. 实施进度（更新于 2026-03-11）

本节用于同步“计划”与“代码主线”当前真实状态。

### 16.1 已完成（本次）

1. **collector.v1 协议 append-only 扩展已落地（双端同步）**
   - `MetricsTask` 新增：
     - `exec_kind`
     - `spec_json`
     - `field_specs`
     - `calculate_specs`
   - `CollectRep` 新增：
     - `debug`（map，用于计算/白名单等诊断）
   - 文件：
     - `collector-go/proto/collector.proto`
     - `manager-go/proto/collector.proto`
     - 双端 pb 生成文件已同步更新

2. **Collector 结构化计算引擎（calculates）已落地**
   - 新增表达式执行能力（以 HertzBeat `calculates` 语义为基准）：
     - 变量引用
     - `+ - * / ()`
     - 基础函数：`abs/min/max/round`
   - 失败策略采用：
     - **单 calculate 跳过**
     - **保留原字段**
     - **写入 debug reason**
   - 文件：
     - `collector-go/internal/pipeline/calculate.go`
     - `collector-go/internal/pipeline/calculate_test.go`

3. **Collector 白名单字段输出已落地**
   - 当任务下发 `field_specs` 时，Collector 按白名单过滤最终上报字段。
   - 非白名单字段默认丢弃，并可在 `CollectRep.debug` 记录 dropped reason。
   - 执行链路：
     - `connect/fetch -> transform -> calculate -> whitelist -> emit`
   - 文件：
     - `collector-go/internal/dispatcher/dispatcher.go`
     - `collector-go/internal/transport/grpc_server.go`

4. **JDBC/MySQL 原生驱动采集已落地（替换 command 外部执行）**
   - 使用 `database/sql + github.com/go-sql-driver/mysql`。
   - 支持 `queryType`：
     - `columns`
     - `oneRow`
     - `multiRow`
   - 文件：
     - `collector-go/internal/protocol/jdbccollector/jdbc.go`
     - `collector-go/go.mod`
     - `collector-go/go.sum`

5. **Manager 默认任务构建补充**
   - `MetricsTask.exec_kind` 默认下发为 `pull`。
   - `app=mysql/mariadb/postgres/postgresql` 默认映射 `protocol=jdbc`。
   - 文件：
     - `manager-go/internal/collector/manager.go`

6. **Manager 模板编译链路已接入（首批 MySQL + Redis）**
   - `BuildCollectTask` 优先走模板编译（命中 `template registry`）：
     - `RuntimeTemplate.content` -> 结构化 `MetricsTask`
     - 产出 `field_specs/calculate_specs/params/priority`
   - 模板编译失败时自动回退旧逻辑，不阻断在线任务分发。
   - Redis 额外策略：
     - 当模板未显式给 `section` 时，按 metrics 名推断常见 INFO section（如 `memory/stats/replication/...`）。
   - 文件：
     - `manager-go/internal/template/compiler.go`
     - `manager-go/internal/template/compiler_test.go`
     - `manager-go/internal/collector/manager.go`
     - `manager-go/cmd/manager/main.go`

7. **Redis 单轮复用优化已落地（Collector）**
   - 在同一 `job cycle` 内，按 `host:port:auth` 维度缓存 Redis INFO 全量结果。
   - 同轮内多个 Redis metrics 复用缓存，避免重复网络采集。
   - 保持兼容策略：
     - 若缓存路径失败，自动回退到原 task 采集。
   - 文件：
     - `collector-go/internal/dispatcher/dispatcher.go`
     - `collector-go/internal/dispatcher/dispatcher_test.go`

8. **JDBC 单轮复用 + 连接池复用已落地（Collector）**
   - 在同一 `job cycle` 内，按连接参数 + SQL + queryType 维度缓存 JDBC 查询结果。
   - 同轮内重复 SQL 的 metrics 复用缓存结果，减少重复查询。
   - `jdbccollector` 侧新增 DSN 级 `*sql.DB` 连接池复用，减少重复建连成本。
   - 文件：
     - `collector-go/internal/dispatcher/dispatcher.go`
     - `collector-go/internal/dispatcher/dispatcher_test.go`
     - `collector-go/internal/protocol/jdbccollector/jdbc.go`

9. **MySQL 模板级 SQL 合并编译已落地（Manager）**
   - 在模板编译阶段对 `protocol=jdbc` + `platform=mysql` + `queryType=columns` 执行保守合并：
     - `show global status ...` -> `show global status;`
     - `show global variables ...` -> `show global variables;`
   - 通过 Collector 白名单字段与 calculates 保证最终指标口径仍以模板字段定义为准。
   - 文件：
     - `manager-go/internal/template/compiler.go`
     - `manager-go/internal/template/compiler_test.go`

10. **Manager 监控任务持久化已落地（避免重启丢任务，且与 Python Web 对齐）**
   - 原先 `MonitorStore` 为纯内存实现，Manager 重启会导致监控列表清空。
   - 现已切换为默认持久化（SQLite），并对齐共享数据域：
     - 在 `PYTHON_WEB_DB` 指向的 DB 文件中直接读写 `monitors + monitor_params`
     - 启动时自动加载已有任务
     - Create/Update/Delete/Enable/Disable 自动落盘
   - 兼容迁移策略：
     - 若检测到历史 `manager_monitors` 表，且共享 `monitors` 为空，启动时自动迁移一次到 `monitors/monitor_params`
   - 若持久化初始化失败，自动回退内存模式（保持可用性）。
   - 文件：
     - `manager-go/internal/store/monitor_store.go`
     - `manager-go/cmd/manager/main.go`

11. **模板语义校验与编译审计已落地（Manager）**
   - 模板编译错误支持精确路径定位（`metrics[i].fields[j]`、`metrics[i].calculates[j]` 等）。
   - 创建/更新/启用监控时增加严格预编译校验：
     - 编译失败返回 `MONITOR_INVALID_CONFIG`（422）
     - 不再进入“创建成功但下发失败”的隐式漂移状态
   - 新增编译审计落盘表 `monitor_compile_logs`，记录阶段、状态、错误路径与原因。
   - 文件：
     - `manager-go/internal/template/compiler.go`
     - `manager-go/internal/httpapi/server.go`
     - `manager-go/internal/store/monitor_store.go`

12. **monitor 级手动重编译 API 已落地（Manager）**
   - 新增 `POST /api/v1/monitors/{id}/recompile`：
     - 按当前模板运行时做严格重编译
     - monitor 启用状态下自动重新下发任务到 Collector
   - 新增 `GET /api/v1/monitors/{id}/compile-logs`：
     - 查询最近编译审计记录，用于排障与变更审计
   - 文件：
     - `manager-go/internal/httpapi/server.go`
     - `manager-go/internal/collector/manager.go`
     - `manager-go/internal/store/monitor_store.go`

13. **monitor 级模板版本升级编排已落地（Manager）**
   - 模板运行时支持按 `template_id` 精确命中（不再仅按 `app` 取最新），并保留 `app` 回退策略。
   - 新增 `POST /api/v1/monitors/{id}/template-upgrade`：
     - 显式切换 monitor 的 `template_id`
     - 先执行严格预编译校验，再持久化升级，再按启用状态下发任务
   - 与编译审计联动：
     - 记录 `upgrade_validate` 与 `upgrade_apply` 阶段日志，支持审计与回溯。
   - 文件：
     - `manager-go/internal/template/registry.go`
     - `manager-go/internal/template/store.go`
     - `manager-go/internal/collector/manager.go`
     - `manager-go/internal/httpapi/server.go`
     - `manager-go/internal/httpapi/server_test.go`

14. **字符串指标 latest 链路补齐已落地（Manager + Frontend）**
   - 问题：Collector 上报 `fields` 中的非数字值（如 `redis_version/os/config_file/executable`）此前不会进入时序库，`metrics/latest` 仅查 VM，导致详情页看不到这些字段值。
   - 方案：
     - Manager 在接收 Collector report 时维护 monitor 维度的字符串最新值快照（内存）。
     - `GET /api/v1/metrics/latest` 增加字符串回填能力，返回 `text` 字段（与原 `value` 数字字段兼容并存）。
     - 当字段名不符合 PromQL 规范时，`latest` 接口自动降级走字符串快照，不因 VM 查询报错导致整批失败。
     - 前端指标页对字符串字段增加 fallback 名称解析（即使不在时序名列表也查询 latest），并优先展示 `text`。
   - 文件：
     - `manager-go/cmd/manager/main.go`
     - `manager-go/internal/httpapi/server.go`
     - `manager-go/internal/httpapi/server_test.go`
     - `frontend/src/composables/useMonitorMetrics.ts`
     - `frontend/src/components/monitoring/metrics/MonitorMetricsPanel.vue`
     - `frontend/src/api/monitoring.ts`

### 16.2 回归结果

1. `collector-go`：`go test ./...` 全通过。  
2. `manager-go`：`go test ./...` 全通过。  
3. `frontend`：`npm run build` 通过（仅保留 Vite chunk size 警告）。

### 16.3 与目标架构的剩余差距（下一步）

1. 仍需补充 `spec_json` 兼容模式与结构化 spec 的灰度开关策略。
2. Redis 已完成单轮复用；后续仍建议补充“跨轮短 TTL 复用 + 连接池化”以进一步降本。
3. JDBC 已完成单轮结果复用、连接池复用与 MySQL 模板级 SQL 合并编译；后续可继续扩展到 PostgreSQL 等模板族。

## 17. 2026-03-25 监控平台变更（OS SSH 单连接 Bundle）

### 17.1 目标

将 OS 类 SSH 采集从“按 metric 独立脚本”统一为“单 SSH 连接、单次 bundle 快照、按 section 拆分结果”，保证同轮时间对齐并提升商用可观测性。

### 17.2 影响范围

- 模板：`linux/ubuntu/debian/centos/almalinux/opensuse/freebsd/redhat/rockylinux/euleros/fedora/darwin`
- manager-go：模板编译模型不变（仍是每个 metric 一个 task）
- collector-go：保持 bundle 执行链路，debug 输出命令与原始结果

### 17.3 模板语义

1. 每个 OS 模板新增隐藏参数 `bundleScript`
2. 每个 SSH metric 统一注入：
   - `bundleScript: ^_^bundleScript^_^`
   - `bundleSection: <metric-name>`
3. 每个 SSH metric 移除 `script:`（pure bundle）
4. `interface` 统一字段：`interface_name/ip_address/mac_address/receive_bytes/transmit_bytes`

### 17.4 执行语义

1. Manager 下发仍为多 task（每个 metric 一个 task）
2. Collector 在同一 job 周期内将 SSH task 合并执行一次 bundle
3. Bundle 输出按 `bundleSection` 拆分回各 metric
4. 同轮 metric 结果共享同一快照时间戳
5. debug 日志包含：
   - `ssh-bundle-cmd`
   - `ssh-bundle-output`

### 17.5 同步与落库

`backend/scripts/sync_hertzbeat_os_templates.py` 已升级为：

1. 指定 OS 模板强制从上游 define 源重建
2. 自动做 Unix interface 字段增强
3. 自动生成/注入 bundleScript 与 bundleSection
4. 自动清理 per-metric script
5. upsert 到 `monitor_templates`

### 17.6 验证结果

1. 目标 OS 模板（linux/ubuntu/debian/centos/almalinux/opensuse/freebsd/redhat/rockylinux/euleros/fedora/darwin）均已切换为 bundle 语义。
2. 模板文件与 DB 模板内容均确认不再包含 per-metric `script:`。
3. 同轮采集日志可见 `ssh-bundle-cmd` 与 `ssh-bundle-output`，用于商用排障。
4. 典型故障排查入口：`backend/scripts/diagnose_os_monitor.py`（DB/API/日志一体诊断）。
4. 持久化已对齐共享 `monitors/monitor_params`；后续重点转向字段映射一致性巡检与 Python Web 列表筛选索引优化。
