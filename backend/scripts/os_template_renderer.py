from __future__ import annotations

from scripts.os_template_profiles import OS_TEMPLATE_META


def _unix_template(app: str, name_zh: str, name_en: str) -> str:
    return f"""category: os
app: {app}
name:
  zh-CN: {name_zh}
  en-US: {name_en}
help:
  zh-CN: 使用 Arco Collector 的 SSH 协议采集主机基础、负载与内存指标，适用于统一主机监控基线。
  en-US: Collect host basic, load and memory metrics through Arco SSH protocol.
params:
  - field: host
    name:
      zh-CN: 目标 Host
      en-US: Target Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: SSH端口
      en-US: SSH Port
    type: number
    range: '[0,65535]'
    required: true
    defaultValue: 22
  - field: username
    name:
      zh-CN: 用户名
      en-US: Username
    type: text
    required: true
    defaultValue: root
  - field: password
    name:
      zh-CN: 密码
      en-US: Password
    type: password
    required: false
  - field: privateKey
    name:
      zh-CN: 私钥
      en-US: Private Key
    type: text
    required: false
    hide: true
  - field: privateKeyPassphrase
    name:
      zh-CN: 私钥口令
      en-US: Private Key Passphrase
    type: password
    required: false
    hide: true
  - field: strictHostKeyChecking
    name:
      zh-CN: 严格主机校验
      en-US: Strict Host Key Checking
    type: boolean
    required: false
    defaultValue: false
  - field: knownHostsPath
    name:
      zh-CN: known_hosts路径
      en-US: known_hosts Path
    type: text
    required: false
    hide: true
    defaultValue: ~/.ssh/known_hosts
  - field: reuseConnection
    name:
      zh-CN: 复用连接
      en-US: Reuse Connection
    type: boolean
    required: false
    defaultValue: true
  - field: timeout
    name:
      zh-CN: 超时时间(ms)
      en-US: Timeout(ms)
    type: number
    range: '[0,100000]'
    required: false
    defaultValue: 6000
metrics:
  - name: system_basic
    i18n:
      zh-CN: 系统基础信息
      en-US: System Basic
    priority: 0
    fields:
      - field: hostname
        type: 1
      - field: goos
        type: 1
      - field: kernel_release
        type: 1
      - field: cpu_cores
        type: 0
      - field: uptime_s
        type: 0
    protocol: ssh
    ssh:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      privateKey: ^_^privateKey^_^
      privateKeyPassphrase: ^_^privateKeyPassphrase^_^
      strictHostKeyChecking: ^_^strictHostKeyChecking^_^
      knownHostsPath: ^_^knownHostsPath^_^
      reuseConnection: ^_^reuseConnection^_^
      timeout: ^_^timeout^_^
      script: 'echo "hostname kernel_release uptime_s cpu_cores"; echo "$(hostname) $(uname -r) $(( $(date +%s) - $(who -b 2>/dev/null | awk ''{{print $3" "$4}}'' | xargs -I{{}} date -d "{{}}" +%s 2>/dev/null || echo $(date +%s)) )) $(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)"'
      parseType: oneRow
  - name: load
    i18n:
      zh-CN: 系统负载
      en-US: Load
    priority: 1
    fields:
      - field: load1
        type: 0
      - field: load5
        type: 0
      - field: load15
        type: 0
      - field: cpu_cores
        type: 0
    protocol: ssh
    ssh:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      privateKey: ^_^privateKey^_^
      privateKeyPassphrase: ^_^privateKeyPassphrase^_^
      strictHostKeyChecking: ^_^strictHostKeyChecking^_^
      knownHostsPath: ^_^knownHostsPath^_^
      reuseConnection: ^_^reuseConnection^_^
      timeout: ^_^timeout^_^
      script: 'echo "load1 load5 load15 cpu_cores"; uptime | sed "s/,//g" | awk ''{{for(i=NF-2;i<=NF;i++) printf "%s ", $i;}} END{{print ""}}'' | awk ''{{print $1, $2, $3}}'' | xargs -I{{}} sh -c ''echo "{{}}" $(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)'''
      parseType: oneRow
  - name: memory
    i18n:
      zh-CN: 内存
      en-US: Memory
    priority: 1
    fields:
      - field: memtotal_kb
        type: 0
      - field: memavailable_kb
        type: 0
      - field: mem_used_pct
        type: 0
        unit: '%'
    protocol: ssh
    ssh:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      privateKey: ^_^privateKey^_^
      privateKeyPassphrase: ^_^privateKeyPassphrase^_^
      strictHostKeyChecking: ^_^strictHostKeyChecking^_^
      knownHostsPath: ^_^knownHostsPath^_^
      reuseConnection: ^_^reuseConnection^_^
      timeout: ^_^timeout^_^
      script: 'total_kb=$(awk "/MemTotal/ {{print $2}}" /proc/meminfo 2>/dev/null); avail_kb=$(awk "/MemAvailable/ {{print $2}}" /proc/meminfo 2>/dev/null); if [ -z "$total_kb" ]; then total_b=$(sysctl -n hw.memsize 2>/dev/null || sysctl -n hw.physmem 2>/dev/null || echo 0); total_kb=$((total_b/1024)); pagesize=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096); free_p=$(vm_stat 2>/dev/null | awk "/Pages free/ {{gsub(/\\./, \"\", $3); print $3; exit}}"); inact_p=$(vm_stat 2>/dev/null | awk "/Pages inactive/ {{gsub(/\\./, \"\", $3); print $3; exit}}"); avail_kb=$(((free_p+inact_p)*pagesize/1024)); fi; [ -z "$total_kb" ] && total_kb=0; [ -z "$avail_kb" ] && avail_kb=0; used_pct=$(awk -v t="$total_kb" -v a="$avail_kb" ''BEGIN{{if(t>0) printf "%.2f", ((t-a)/t)*100; else print "0"}}''); echo "memtotal_kb memavailable_kb mem_used_pct"; echo "$total_kb $avail_kb $used_pct"'
      parseType: oneRow
"""


def _windows_template(app: str, name_zh: str, name_en: str) -> str:
    return f"""category: os
app: {app}
name:
  zh-CN: {name_zh}
  en-US: {name_en}
help:
  zh-CN: 使用 SNMP 方式采集 Windows 主机关键系统指标（名称、运行时长、进程数、用户数、内存）。
  en-US: Collect key Windows system metrics via SNMP.
params:
  - field: host
    name:
      zh-CN: 目标 Host
      en-US: Target Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: SNMP端口
      en-US: SNMP Port
    type: number
    range: '[0,65535]'
    required: true
    defaultValue: 161
  - field: community
    name:
      zh-CN: SNMP 团体字
      en-US: SNMP Community
    type: text
    required: true
    defaultValue: public
  - field: snmpVersion
    name:
      zh-CN: SNMP 版本
      en-US: SNMP Version
    type: radio
    required: true
    defaultValue: 1
    options:
      - label: SNMPv1
        value: 0
      - label: SNMPv2c
        value: 1
  - field: timeout
    name:
      zh-CN: 超时时间(ms)
      en-US: Timeout(ms)
    type: number
    range: '[0,100000]'
    required: false
    defaultValue: 6000
metrics:
  - name: system
    i18n:
      zh-CN: 系统
      en-US: System
    priority: 0
    fields:
      - field: name
        type: 1
      - field: descr
        type: 1
      - field: uptime
        type: 0
      - field: numUsers
        type: 0
      - field: processes
        type: 0
      - field: location
        type: 1
      - field: memory
        type: 0
    protocol: snmp
    snmp:
      host: ^_^host^_^
      port: ^_^port^_^
      timeout: ^_^timeout^_^
      community: ^_^community^_^
      version: ^_^snmpVersion^_^
      operation: get
      oids:
        name: 1.3.6.1.2.1.1.5.0
        descr: 1.3.6.1.2.1.1.1.0
        uptime: 1.3.6.1.2.1.25.1.1.0
        numUsers: 1.3.6.1.2.1.25.1.5.0
        processes: 1.3.6.1.2.1.25.1.6.0
        location: 1.3.6.1.2.1.1.6.0
        memory: 1.3.6.1.2.1.25.2.2.0
"""


def _nvidia_template(app: str, name_zh: str, name_en: str) -> str:
    return f"""category: os
app: {app}
name:
  zh-CN: {name_zh}
  en-US: {name_en}
help:
  zh-CN: 采集 NVIDIA GPU 主机基础指标，依赖主机安装 nvidia-smi。
  en-US: Collect NVIDIA GPU host metrics, requires nvidia-smi installed.
params:
  - field: host
    name:
      zh-CN: 目标 Host
      en-US: Target Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: SSH端口
      en-US: SSH Port
    type: number
    range: '[0,65535]'
    required: true
    defaultValue: 22
  - field: username
    name:
      zh-CN: 用户名
      en-US: Username
    type: text
    required: true
    defaultValue: root
  - field: password
    name:
      zh-CN: 密码
      en-US: Password
    type: password
    required: false
  - field: privateKey
    name:
      zh-CN: 私钥
      en-US: Private Key
    type: text
    required: false
    hide: true
  - field: privateKeyPassphrase
    name:
      zh-CN: 私钥口令
      en-US: Private Key Passphrase
    type: password
    required: false
    hide: true
  - field: strictHostKeyChecking
    name:
      zh-CN: 严格主机校验
      en-US: Strict Host Key Checking
    type: boolean
    required: false
    defaultValue: false
  - field: knownHostsPath
    name:
      zh-CN: known_hosts路径
      en-US: known_hosts Path
    type: text
    required: false
    hide: true
    defaultValue: ~/.ssh/known_hosts
  - field: reuseConnection
    name:
      zh-CN: 复用连接
      en-US: Reuse Connection
    type: boolean
    required: false
    defaultValue: true
  - field: timeout
    name:
      zh-CN: 超时时间(ms)
      en-US: Timeout(ms)
    type: number
    range: '[0,100000]'
    required: false
    defaultValue: 6000
metrics:
  - name: gpu_basic
    i18n:
      zh-CN: GPU 基础
      en-US: GPU Basic
    priority: 0
    fields:
      - field: hostname
        type: 1
      - field: gpu_name
        type: 1
      - field: gpu_utilization_pct
        type: 0
      - field: gpu_memory_used_mb
        type: 0
      - field: gpu_memory_total_mb
        type: 0
      - field: gpu_temperature_c
        type: 0
    protocol: ssh
    ssh:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      privateKey: ^_^privateKey^_^
      privateKeyPassphrase: ^_^privateKeyPassphrase^_^
      strictHostKeyChecking: ^_^strictHostKeyChecking^_^
      knownHostsPath: ^_^knownHostsPath^_^
      reuseConnection: ^_^reuseConnection^_^
      timeout: ^_^timeout^_^
      script: 'echo "hostname gpu_name gpu_utilization_pct gpu_memory_used_mb gpu_memory_total_mb gpu_temperature_c"; gpu_line=$(nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -n 1); if [ -z "$gpu_line" ]; then gpu_line="unknown,0,0,0,0"; fi; echo "$(hostname) $(echo $gpu_line | sed "s/,/ /g")"'
      parseType: oneRow
  - name: system_memory
    i18n:
      zh-CN: 主机内存
      en-US: Host Memory
    priority: 1
    fields:
      - field: memtotal_kb
        type: 0
      - field: memavailable_kb
        type: 0
      - field: mem_used_pct
        type: 0
        unit: '%'
    protocol: ssh
    ssh:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      privateKey: ^_^privateKey^_^
      privateKeyPassphrase: ^_^privateKeyPassphrase^_^
      strictHostKeyChecking: ^_^strictHostKeyChecking^_^
      knownHostsPath: ^_^knownHostsPath^_^
      reuseConnection: ^_^reuseConnection^_^
      timeout: ^_^timeout^_^
      script: 'total_kb=$(awk "/MemTotal/ {{print $2}}" /proc/meminfo 2>/dev/null || echo 0); avail_kb=$(awk "/MemAvailable/ {{print $2}}" /proc/meminfo 2>/dev/null || echo 0); used_pct=$(awk -v t="$total_kb" -v a="$avail_kb" ''BEGIN{{if(t>0) printf "%.2f", ((t-a)/t)*100; else print "0"}}''); echo "memtotal_kb memavailable_kb mem_used_pct"; echo "$total_kb $avail_kb $used_pct"'
      parseType: oneRow
"""


def render_os_template(app: str) -> str:
    app_key = str(app or "").strip().lower()
    meta = OS_TEMPLATE_META.get(app_key)
    if not meta:
        raise KeyError(app_key)
    profile = meta["profile"]
    if profile == "windows":
        return _windows_template(app_key, meta["name_zh"], meta["name_en"])
    if profile == "gpu":
        return _nvidia_template(app_key, meta["name_zh"], meta["name_en"])
    return _unix_template(app_key, meta["name_zh"], meta["name_en"])
