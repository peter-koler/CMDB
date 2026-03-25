# 操作系统默认告警策略基线

## 覆盖对象

- Linux
- Ubuntu
- Debian
- CentOS
- AlmaLinux
- OpenSUSE
- FreeBSD
- RedHat
- Rocky Linux
- EulerOS
- Fedora
- Darwin
- macOS
- Windows（SNMP）
- NVIDIA

## 规则规模

- 每个模板 11 条默认规则
- `core` 默认启用，`extended` 默认关闭

## 指标策略差异

- Unix-like：负载、内存、可用内存、运行时长、内核采集完整性
- Windows：进程数、用户数、运行时长、主机信息完整性（SNMP OID）
- NVIDIA：GPU 利用率、温度、显存使用率 + 主机内存
