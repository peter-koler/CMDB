# 网络交换机模板迁移 SOP（Cisco/HPE/Huawei/TP-Link/H3C）

## 1. 目标

将 HertzBeat 网络交换机模板迁移到本项目，并完成商用级落地：

- 模板迁移与入库
- SNMP 采集能力补齐（重点是 SNMPv3）
- 差异化默认告警策略（实时 + 周期）
- 分类归档到 `network`

## 2. 覆盖范围

- `cisco_switch`
- `hpe_switch`
- `huawei_switch`
- `tplink_switch`
- `h3c_switch`

## 3. 采集能力落地

增强 `collector-go/internal/protocol/snmpcollector`：

1. SNMP v3 认证链
- 支持 `username/contextName/authPassphrase/privPassphrase`
- 支持加密映射：`authPasswordEncryption`(MD5/SHA)、`privPasswordEncryption`(DES/AES)
- 自动推导安全级别：`noAuthNoPriv` / `authNoPriv` / `authPriv`

2. 命令参数构建
- v1/v2c: `-c community`
- v3: `-l -u -a -A -x -X -n`

## 4. 模板与策略

1. 模板来源
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-cisco_switch.yml`
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-hpe_switch.yml`
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-huawei_switch.yml`
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-tplink_switch.yml`
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-h3c_switch.yml`

2. 分类
- 统一维护为 `category: network`
- 同步脚本自动确保分类 `网络设备(network)` 存在

3. 默认策略
- 新增：`backend/scripts/apply_network_default_alerts.py`
- 每个交换机模板都包含：
  - 实时可用性告警
  - 端口状态实时告警
  - 错包/丢包/响应时延周期告警
  - 厂商差异阈值策略

## 5. 新增/修改文件

### 5.1 backend

- `backend/scripts/apply_network_default_alerts.py`
- `backend/scripts/sync_hertzbeat_network_templates.py`
- `backend/app/services/default_alert_policies.py`
- `backend/app/routes/monitoring_target.py`
- `backend/templates/app-cisco_switch.yml`
- `backend/templates/app-hpe_switch.yml`
- `backend/templates/app-huawei_switch.yml`
- `backend/templates/app-tplink_switch.yml`
- `backend/templates/app-h3c_switch.yml`

### 5.2 collector-go

- `collector-go/internal/protocol/snmpcollector/options.go`
- `collector-go/internal/protocol/snmpcollector/command.go`
- `collector-go/internal/protocol/snmpcollector/snmp_test.go`

## 6. 执行命令

### 6.1 模板同步并入库

```bash
cd /Users/peter/Documents/arco/backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_network_templates.py
```

### 6.2 collector 回归

```bash
cd /Users/peter/Documents/arco/collector-go
go test ./internal/protocol/snmpcollector -count=1
```

### 6.3 全量回归

```bash
cd /Users/peter/Documents/arco/collector-go
go test ./...

cd /Users/peter/Documents/arco/backend
python3 -m compileall scripts app
```

## 7. 验收点

1. `network` 分类下可见 5 个交换机模板。
2. SNMPv3 交换机可成功采集。
3. 默认策略可一键应用，含实时与周期规则。
4. 首个采集周期后可在指标与告警页面看到数据与规则生效。
