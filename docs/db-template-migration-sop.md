# 数据库模板迁移 SOP（按 MySQL 流程扩展）

## 1. 目标

将 HertzBeat `hertzbeat-manager/src/main/resources/define` 下数据库类模板迁移到本项目，并同步到 `monitor_templates`，确保“监控模板菜单”可见。

本次范围：

- `postgresql`, `db2`, `mariadb`, `sqlserver`, `kingbase`, `greenplum`, `tidb`, `mongodb_atlas`, `oceanbase`, `vastbase`, `oracle`, `dm`, `opengauss`

## 2. 已实现的自动化脚本

脚本：

- `backend/scripts/sync_hertzbeat_db_templates.py`
- `backend/scripts/apply_db_default_alerts.py`

作用：

1. 从 HertzBeat `define/app-*.yml` 复制到 `backend/templates/app-*.yml`
2. 为数据库模板注入差异化 `alerts`（按数据库指标定制）
3. 按 `app/name/category/content` upsert 到 `monitor_templates`

执行方式：

```bash
cd backend
PYTHONPATH=. python scripts/sync_hertzbeat_db_templates.py
```

说明：`sync_hertzbeat_db_templates.py` 已内置调用 `apply_db_default_alerts` 的策略注入逻辑，避免覆盖后丢失 `alerts`。

## 3. 一库一库迁移步骤（模板层）

对每个数据库按相同步骤执行：

1. 确认源文件存在：`hertzbeat-master/.../define/app-<db>.yml`
2. 复制到：`backend/templates/app-<db>.yml`
3. 同步入库（执行脚本）
4. 在“监控模板菜单”确认显示
5. 打开“默认监控策略”页确认可编辑（若模板无 `alerts`，按产品策略使用回退默认项）

## 4. 本次数据库清单与回退策略

以下模板已迁移并默认归类为 `db`：

- `postgresql`
- `db2`
- `mariadb`
- `sqlserver`
- `kingbase`
- `greenplum`
- `tidb`
- `mongodb_atlas`
- `oceanbase`
- `vastbase`
- `oracle`
- `dm`
- `opengauss`

上述模板原始 YAML 均未包含 `alerts` 段，因此补充“默认策略兜底”：

1. 前端模板页（默认监控策略 tab）：按 `app` 回退到内置策略
2. 后端目标应用默认规则接口：按 `app` 回退到可用性规则

回退规则统一为：

- 指标：`<app>_server_up`
- 条件：`== 0`
- 级别：`critical`
- 周期：`60s`

## 5. 采集能力现状（商业版）

已参考本地 HertzBeat 源码目录：

- `hertzbeat-master/hertzbeat-collector/hertzbeat-collector-basic`
- `hertzbeat-master/hertzbeat-collector/hertzbeat-collector-mongodb`

并在 `collector-go` 完成以下协议能力：

1. JDBC 平台映射增强  
   `mariadb/tidb/oceanbase -> mysql`  
   `postgresql/kingbase/greenplum/vastbase/opengauss -> postgres`  
   `sqlserver -> sqlserver`  
   `oracle -> oracle`  
   `dm -> dm`
2. 新增 MongoDB 协议采集器  
   支持 `mongodb_atlas` 模板命令（`buildInfo`、`serverStatus.*`、`dbStats` 等）与子路径提取。
3. PostgreSQL 稳定性增强  
   对未启用 `pg_stat_statements` 的 `slow_sql` 指标做可预期跳过；`columns` 查询支持 2 列以上扫描。

## 6. 仍需单独驱动落地的数据库

以下数据库模板已迁移，但 `db2` 需要按“可选能力”方式启用：

1. `db2`（可选编译标签 `db2`）

说明：

- `dm` 已完成 Go 原生驱动接入（`platform: dm`）。
- `db2` 已完成 JDBC 逻辑接入（`platform: db2`，驱动名 `go_ibm_db`，支持 `DATABASE=...;HOSTNAME=...` 连接串，以及 `jdbc:db2://...` 转换）。
- 为避免默认构建受 cgo/DB2 客户端影响，`db2` 驱动采用 build tag 机制：
  - 构建时设置 `COLLECTOR_GO_BUILD_TAGS=db2`
  - 并配置 `IBM_DB_HOME`、`CGO_CFLAGS`、`CGO_LDFLAGS`、`LD_LIBRARY_PATH`（macOS 为 `DYLD_LIBRARY_PATH`）

## 7. 验收检查单（逐库）

每个数据库按以下检查项打勾：

1. `backend/templates/app-<db>.yml` 文件存在
2. 模板菜单可搜索到 `<db>`
3. 点击模板后，“默认监控策略”tab有至少 1 条规则展示
4. 保存模板后，YAML 内出现 `alerts` 段（若之前为空）
5. 新建该类型监控目标，执行“应用默认告警策略”成功
