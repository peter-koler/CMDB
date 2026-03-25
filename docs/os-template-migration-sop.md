# 操作系统模板迁移 SOP（Linux/Windows/macOS/NVIDIA）

## 1. 目标

将 HertzBeat 的操作系统类模板迁移到当前系统，尽量保持指标覆盖与上游一致，同时保证 Arco Collector 可落地执行：

- Linux / Ubuntu / Debian / CentOS / AlmaLinux / OpenSUSE / FreeBSD / RedHat / Rocky Linux / EulerOS / Fedora / Darwin / macOS：走 `ssh` 协议，采用 HertzBeat OS 指标集
- Windows：走 `snmp` 协议，采用 HertzBeat Windows 指标集（并修正 `snmpVersion` 占位符）
- NVIDIA：保留 Arco renderer 模板（HertzBeat 原模板字段名不符合 Arco 编译器约束）

## 2. 同步流程

1. 尝试复制源模板（`hertzbeat-manager/src/main/resources/define`）
2. 对源模板做 Arco 兼容修正（如 Windows `version` 占位符）
3. 对缺失源模板的 app 使用派生/renderer 兜底（当前 `fedora<-linux`，`nvidia` 使用 renderer）
4. 注入默认 `alerts`
5. Upsert 到 `monitor_templates`

脚本：

- `backend/scripts/sync_hertzbeat_os_templates.py`
- `backend/scripts/apply_os_default_alerts.py`

## 3. 执行命令

```bash
cd backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_os_templates.py
```

## 4. 验收

1. 模板中心可见 15 个 OS 模板
2. Windows 模板协议为 `snmp`
3. 其余 OS 模板协议为 `ssh`
4. 每个模板包含默认 alerts（11 条）

## 5. 2026-03-24 优化记录（已同步）

### 5.1 操作系统模板指标优化（SSH）

针对以下 OS 模板统一优化：

- `linux` / `ubuntu` / `debian` / `centos` / `almalinux` / `opensuse`
- `freebsd` / `redhat` / `rockylinux` / `euleros` / `fedora`
- `darwin` / `macos`
- `windows`（保留 `snmp`，仅对展示逻辑做兼容）

重点改动：

1. `interface`（网卡信息）补充字段：
   - `interface_name`
   - `ip_address`
   - `mac_address`
   - `receive_bytes`
   - `transmit_bytes`
2. `disk_free`（文件系统）保留 `usage` 字段，前端兜底按 `used / (used + available)` 计算。
3. `memory`（内存信息）`usage` 统一按百分比展示，保留两位小数。
4. `top_cpu_process` / `top_mem_process` 采用行模式可识别字段（`pid/cpu_usage/mem_usage/command`）。
5. `basic/cpu/disk/interface/memory/disk_free` 统一维护 `*_success` 与 `*_raw_latency`，便于采集链路排障。

### 5.2 指标展示层优化（前端）

1. Top10 进程类指标从“按字段平铺”优化为“按行展示”。
2. “行模式”补充“按列查看趋势明细”入口。
3. “按列查看趋势明细”仅对数字型字段开放（字符串字段不展示趋势入口）。
4. 行模式字符串字段候选优先匹配 `group_rowN_*`，降低跨分组同名字段串值风险。
5. 内存使用率、文件系统使用率统一显示 `%` 且保留 2 位小数。

### 5.3 manager-go 字符串指标映射增强

在 `manager-go/cmd/manager/main.go` 增强字符串快照写入与读取逻辑：

1. 同一字段同步记录原始 key、规范化 key、`metrics_field` 前缀 key。
2. 读取时增加 fallback（规范化名、`rowN`、末尾字段名）。
3. 避免空字符串覆盖已有非空值。

目标：解决 `hostname/command/ip/mac` 等字符串字段在 UI 查询时偶发为空的问题。

## 6. 告警策略保护规则（防误删）

模板更新必须满足：

1. 不删除已有 `alerts`；仅允许新增或按显式变更单调整。
2. OS 模板升级后，执行 `apply_os_default_alerts.py` 做补齐而非覆盖清空。
3. 若用户要求“仅修指标不动策略”，则只更新 `metrics` 与 `params`，`alerts` 维持不变。

建议检查 SQL：

```sql
SELECT app, version, is_hidden, updated_at
FROM monitor_templates
WHERE category = 'os'
ORDER BY app, version DESC;
```

## 7. 一键诊断脚本（新增）

新增脚本：`backend/scripts/diagnose_os_monitor.py`

用途：给定 `monitor-id` 一次性诊断 `数据库 + manager-go API + 日志`，快速定位“模板、采集、映射、展示”哪一层出问题。

覆盖内容：

1. PostgreSQL：
   - `monitors`
   - `monitor_params`
   - `monitor_templates`
   - `monitor_compile_logs`
   - `metrics_history`
2. manager-go API：
   - `/api/v1/health`
   - `/api/v1/monitors/{id}`
   - `/api/v1/monitors/{id}/compile-logs`
   - `/api/v1/metrics/latest`
3. 日志扫描：
   - `logs/*.log`
   - `manager-go/logs/*.log`
   - `collector-go/logs/*.log`

执行示例：

```bash
cd /Users/peter/Documents/arco
python3 backend/scripts/diagnose_os_monitor.py --monitor-id 3
```

输出会给出分组级结论：`OK / EMPTY / FAIL / MAPPING / STALE / API`，并给出快速建议动作。

## 8. 2026-03-25 商用化改造（单 SSH Bundle 快照）

### 8.1 范围

以下模板统一改为“单连接 bundle 快照”语义（参考 Ubuntu）：

- `linux` / `ubuntu` / `debian` / `centos` / `almalinux` / `opensuse`
- `freebsd` / `redhat` / `rockylinux` / `euleros` / `fedora` / `darwin`

### 8.2 模板规则

1. 每个模板新增参数 `bundleScript`（隐藏参数，默认值为统一快照脚本）。
2. 每个 `protocol: ssh` 的指标组（metric）统一注入：
   - `bundleScript: ^_^bundleScript^_^`
   - `bundleSection: <metric-name>`
3. 移除各 metric 下旧的 `script:` 字段（pure bundle，不保留旧模式脚本）。
4. `interface` 指标统一保留：
   - `interface_name`
   - `ip_address`
   - `mac_address`
   - `receive_bytes`
   - `transmit_bytes`

### 8.3 执行行为（collector）

1. 逻辑上仍是“每个 metric 一个 task”（Manager 编译模型不变）。
2. 执行上为“同轮 SSH task 合并一次远端执行”（bundle 模式）。
3. 按 `bundleSection` 从统一输出拆分每个 metric 结果。
4. 同轮结果时间戳对齐为同一个快照时间。
5. collector debug 日志输出：
   - `ssh-bundle-cmd`
   - `ssh-bundle-output`

### 8.4 同步脚本行为

`sync_hertzbeat_os_templates.py` 已更新：

1. 对上述 OS 模板强制从上游源模板重建（避免历史本地漂移）。
2. 对 Unix 系模板统一补齐 `interface ip/mac` 字段。
3. 自动生成 bundle 脚本并写入 `bundleScript`。
4. 自动注入 `bundleSection` 并移除 per-metric `script`。
5. 注入默认 `alerts` 后 upsert 到 `monitor_templates`。

### 8.5 本次执行校验（2026-03-25）

1. 目标 OS 模板文件已验证 `script_count=0`（不再保留 per-metric script）。
2. 目标 OS 模板均包含 `field: bundleScript` 与 `bundleSection`。
3. PostgreSQL `monitor_templates` 已验证上述模板均为：
   - `has_bundle_param = yes`
   - `has_script = no`
4. 本次校验命令：`python3 backend/scripts/diagnose_os_monitor.py --monitor-id 3 --lookback-minutes 30`。
