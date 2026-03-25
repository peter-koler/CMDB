# 中间件监控模板迁移 SOP

## 1. 目标

把 HertzBeat 中间件模板迁移到当前系统，并按“模板、采集、默认策略、验收”四个层面落地，避免只迁 YAML 不补链路。

## 2. 适用范围

当前已纳入本 SOP 的对象：

- `activemq`
- `kafka`
- `kafka_client`
- `pulsar`
- `rabbitmq`
- `rocketmq`
- `shenyu`
- `spring_gateway`
- `zookeeper`
- `apollo`

## 3. 标准步骤

### 3.1 盘点协议和模板特性

先确认每个模板依赖的协议与特殊能力：

- `http`: 需要确认 `parseType` 是否是 `default / jsonPath / prometheus`
- `telnet`: 需要确认命令输出格式是否是 `key=value` 或 `key\tvalue`
- `kclient`: 需要确认 Kafka Admin 场景的命令集合
- `jmx`: 需要确认 JMX RMI、对象名、复合属性
- 动态模板：确认是否存在 `^o^...^o^` 这类跨 metric 展开占位符

不要在没确认这些前就直接迁模板。

### 3.2 先补 collector 协议能力

原则：

- 协议逻辑单独拆目录，不往一个 Go 文件里堆代码
- 采集逻辑和解析逻辑拆开
- 每个协议至少补基础测试

本次阶段一已完成：

- `collector-go/internal/protocol/httpcollector`
- `collector-go/internal/protocol/telnetcollector`
- `collector-go/internal/protocol/kclientcollector`

当前仍需后续阶段补齐：

- 动态模板执行框架

### 3.3 建默认策略脚本

策略不要照抄 Redis，也不要只放一条可用性。

要求：

- 每个对象至少 `10` 条
- 包含 `core + extended`
- 包含 `realtime_metric + periodic_metric`
- 阈值要根据该对象模板里的真实可采指标来定

本次脚本：

- [apply_middleware_default_alerts.py](/Users/peter/Documents/arco/backend/scripts/apply_middleware_default_alerts.py)

### 3.4 建模板同步脚本

同步流程固定为：

1. 从 HertzBeat `define` 复制 YAML
2. 注入 `alerts`
3. Upsert 到 `monitor_templates`

不要手工一份一份改数据库。

如果 HertzBeat 原模板依赖的是 Java 私有 SDK / 管理面能力，而 Go 公共 SDK 无法等价实现：

- 必须新增 `backend/template_overrides/app-<app>.yml`
- 模板字段、collector 输出、默认策略三者必须同步收敛
- 禁止保留“页面有字段但 collector 永远采不到”的伪支持

如果 HertzBeat 原模板依赖的是 Java 私有 SDK / 管理面能力，而 Go 公共 SDK 无法等价实现：

- 必须新增 `backend/template_overrides/app-<app>.yml`
- 模板字段、collector 输出、默认策略三者必须同步收敛
- 禁止保留“页面有字段但 collector 永远采不到”的伪支持

本次脚本：

- [sync_hertzbeat_middleware_templates.py](/Users/peter/Documents/arco/backend/scripts/sync_hertzbeat_middleware_templates.py)

### 3.5 同步后验收

验收至少检查：

1. 模板菜单可见
2. “默认监控策略”页面能展示模板里的 `alerts`
3. 应用默认策略接口能正常取到规则
4. collector-go 对应协议能实际执行
5. 目标指标能在历史数据里看到

## 4. 当前阶段状态

### 已完成

- 模板迁移与入库：10 个中间件模板
- 默认策略：每个模板 11 条以上
- collector 协议：
  - `http`
  - `telnet`
  - `kclient`
  - `rocketmq`（当前为 Go 公共 Admin API 正式支持子集）
  - `activemq/kafka`（当前采用 `Jolokia + HTTP`）

### 待完成

- `spring_gateway` 动态占位符展开框架

## 5. 本次命令

```bash
cd backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_middleware_templates.py
```

```bash
cd collector-go
GOCACHE=/tmp/collector-go-gocache GOMODCACHE=/tmp/collector-go-gomodcache go test ./...
```

## 6. 后续迁移建议

迁移下一个中间件时，严格按下面顺序：

1. 先判定协议和模板是否静态
2. 再补 collector 协议
3. 再写默认策略
4. 再同步模板入库
5. 最后做 UI 和采集验收

不要反过来做。
