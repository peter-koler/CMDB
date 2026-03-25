# OS/DB 模板回归验收清单（2026-03-24）

## 1. 验收范围

- 操作系统模板：
  - `linux`、`windows`、`ubuntu`、`debian`、`centos`、`almalinux`、`opensuse`、`freebsd`、`redhat`、`rockylinux`、`euleros`、`fedora`、`darwin`、`macos`
- 数据库模板：
  - `postgresql`、`db2`、`mariadb`、`sqlserver`、`kingbase`、`greenplum`、`tidb`、`mongodb_atlas`、`oceanbase`、`vastbase`、`oracle`、`dm`、`opengauss`

## 2. 前置条件

1. 管理端已重启并加载最新模板。
2. 模板已 upsert 到 `monitor_templates`。
3. 每类至少有 1 个可连通监控目标（OS 建议 Ubuntu/Windows/macOS 各 1 台）。

## 3. OS 指标页验收（重点）

## 3.1 Ubuntu（可代表 Linux 系模板）

1. 进入监控目标详情 -> `指标` 页。
2. 逐个打开分组，确认非空且可刷新：
   - `系统基本信息`
   - `CPU 信息`
   - `内存信息`
   - `磁盘信息`
   - `网卡信息`
   - `文件系统`
   - `Top10 CPU 进程`
   - `Top10 内存进程`
3. 核对关键字段：
   - `CPU 信息`：`info/cores/interrupt/load/context_switch/usage` 有值。
   - `磁盘信息`：`disk_num/partition_num/block_write/block_read/write_rate` 有值。
   - `网卡信息`：每行应含 `interface_name/ip_address/mac_address/receive_bytes/transmit_bytes`。
   - `文件系统`：`usage` 需有值（允许由前端计算得到，不应长期为空）。
4. `Top10 CPU 进程`、`Top10 内存进程` 必须以“行列表”展示，至少包含：
   - `序号`、`进程ID(pid)`、`CPU占用率`、`内存占用率`、`执行命令(command)`。

## 3.2 Windows

1. 打开 `interfaces` 分组。
2. 确认字段存在且有数据：
   - `ip_address`
   - `mac_address`
3. 确认其他分组仍可用：
   - `system/processes/services/installed/storages/devices`

## 3.3 macOS / darwin

1. 重复 Ubuntu 验收步骤，重点确认：
   - `basic/cpu/disk` 不为空。
   - `网卡信息`包含 `ip_address/mac_address`。
   - `Top10` 分组为行列表展示。

## 3.4 其余 OS 覆盖确认

1. 对下列模板至少做“创建任务 + 首次采集成功 + CPU/磁盘/网卡分组非空”抽检：
   - `debian/centos/almalinux/opensuse/freebsd/redhat/rockylinux/euleros/fedora`
2. 若抽检通过，可判定本轮脚本化改动已全量生效。

## 4. 行模式趋势入口规则验收

1. 在 OS 的“行模式”分组（如 Top10）确认有“按列查看趋势”入口。
2. 仅数字型列可打开趋势：
   - 应可点：`cpu_usage`、`mem_usage`、`receive_bytes`、`transmit_bytes` 等。
   - 不可点或提示限制：`command`、`pid`（字符串场景）等非数字列。

## 5. DB 模板策略误删回归

1. 对以下模板确认“指标分组数量、字段、参数”与 HertzBeat 同名模板一致：
   - `postgresql/db2/mariadb/sqlserver/kingbase/greenplum/tidb/mongodb_atlas/oceanbase/vastbase/oracle/dm/opengauss`
2. 允许差异：
   - `alerts` 增加（默认告警策略补齐）。
3. 不允许差异：
   - 指标组缺失。
   - 组内字段缺失。
   - 连接参数被误删。

## 6. 验收通过标准

1. OS：目标分组不为空，Top10 为行列表可辨识 10 个进程，网卡含 IP/MAC，文件系统 usage 有值。
2. 行模式趋势：OS 仅数字列可查趋势。
3. DB：无监控策略误删，仅新增告警策略。

## 7. 缺陷记录建议

1. 记录模板 `app`、分组 `name`、字段 `field`、采集时间、目标主机。
2. 附采集原始值（若有）与页面截图，便于快速定位 YAML 脚本还是前端渲染问题。

 - ‘系统基本信息’ 没有值
  - `CPU 信息`：`info/cores/interrupt/load/context_switch/usage`  没有值
   - `磁盘信息`：`disk_num/partition_num/block_write/block_read/write_rate` 没有值
   - `网卡信息`：每行应含 `interface_name/ip_address/mac_address/receive_bytes/transmit_bytes`。   IP地址和 MAC地址 为空
   - ‘内存信息’： 内存使用率位空。
