# 云原生监控模板迁移 SOP（Docker/Kubernetes）

## 1. 目标

将 HertzBeat 云原生模板迁移到本项目，并完成可商用落地：

- 模板迁移（Docker/Kubernetes）
- collector 采集能力补齐（Bearer Token + HTTP Query Params）
- 默认告警策略（实时 + 周期）
- 分类入库同步（`cloud`）

## 2. 覆盖范围

- `docker`
- `kubernetes`

## 3. 采集能力落地

本次增强 `collector-go/internal/protocol/httpcollector`：

1. Bearer Token 鉴权
- 识别模板参数：`authorization.type=Bearer Token` + `authorization.bearerTokenToken`
- 自动写入 `Authorization: Bearer <token>`

2. HTTP Query Params
- 支持 `params.*` / `http.params.*`
- 自动拼接到请求 URL 查询串
- 解决 Docker `/containers/<id>/stats?stream=false` 与 K8s API 参数化场景

## 4. 模板与策略

1. 模板来源
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-docker.yml`
- `hertzbeat-master/hertzbeat-manager/src/main/resources/define/app-kubernetes.yml`

2. 分类策略
- 统一改为 `category: cloud`
- 同步时确保分类存在：`云服务(cloud)`

3. 默认策略
- `backend/scripts/apply_cloud_default_alerts.py`
- 每个模板均包含：
  - 可用性实时规则（`<app>_server_up == 0`）
  - 周期性能规则（CPU/内存/时延等）
  - 实时状态规则（节点/Pod/容器状态）

## 5. 新增/修改文件

### 5.1 backend

- `backend/templates/app-docker.yml`
- `backend/templates/app-kubernetes.yml`
- `backend/scripts/apply_cloud_default_alerts.py`
- `backend/scripts/sync_hertzbeat_cloud_templates.py`
- `backend/app/services/default_alert_policies.py`
- `backend/app/routes/monitoring_target.py`

### 5.2 collector-go

- `collector-go/internal/protocol/httpcollector/spec.go`
- `collector-go/internal/protocol/httpcollector/collect.go`
- `collector-go/internal/protocol/httpcollector/http_test.go`

## 6. 执行命令

### 6.1 模板同步并入库

```bash
cd /Users/peter/Documents/arco/backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_cloud_templates.py
```

### 6.2 collector 回归

```bash
cd /Users/peter/Documents/arco/collector-go
go test ./internal/protocol/httpcollector -run "Bearer|Digest|JSONPath|Prometheus|XMLPath" -count=1
```

### 6.3 backend 脚本语法检查

```bash
cd /Users/peter/Documents/arco/backend
python3 -m compileall scripts app
```

## 7. 验收点

1. 模板树出现 `cloud` 分类，且可见 `docker`、`kubernetes`。
2. Docker/Kubernetes 目标创建后可正常下发采集任务并回传数据。
3. K8s Bearer Token 可完成 API 认证采集。
4. 默认策略可一键应用，且含实时与周期规则。
