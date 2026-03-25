# 缓存监控模板迁移 SOP（Memcached / Valkey）

## 1. 目标

把 HertzBeat 的 `memcached` 与 `valkey` 模板迁移到当前系统，并补齐采集与默认策略，确保“模板可见 + 能采到 + 可直接套用策略”。

## 2. 本次范围

- `memcached`
- `valkey`

## 3. 迁移策略

1. 模板迁移  
- 从 `hertzbeat-master/hertzbeat-manager/src/main/resources/define` 复制：
  - `app-memcached.yml`
  - `app-valkey.yml`
- 落地到 `backend/templates/`

2. collector 协议能力  
- `memcached`: 新增 `collector-go/internal/protocol/memcachedcollector` 协议实现（TCP 文本协议，命令 `stats` / `stats settings` / `stats sizes`）。
- `valkey`: 复用现有 `redis` 协议采集链路（`protocol: redis`），不新增重复协议。

3. 默认告警策略  
- 新增 `backend/scripts/apply_cache_default_alerts.py`
- 输出 `core + extended`，并同时覆盖 `realtime_metric + periodic_metric`
- `memcached` 和 `valkey` 分别独立阈值策略

4. 模板同步脚本  
- 新增 `backend/scripts/sync_hertzbeat_cache_templates.py`
- 固定流程：复制模板 -> 注入 alerts -> upsert 到 `monitor_templates`
- 同步时确保分类 `cache` 存在

## 4. 验收项

1. 模板树中出现 `memcached`、`valkey`。
2. 新建任务后，Collector 可下发并执行。
3. 默认告警策略可直接应用且规则数量符合预期。
4. `metrics/latest` 和历史指标可看到关键字段。

## 5. 命令

```bash
cd backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_cache_templates.py
```

```bash
cd collector-go
GOCACHE=/tmp/collector-go-gocache GOMODCACHE=/tmp/collector-go-gomodcache go test ./...
```

