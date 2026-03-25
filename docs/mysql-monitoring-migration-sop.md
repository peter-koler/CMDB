# MySQL 监控接入与迁移 SOP（可复用到其他对象）

## 1. 目标与适用范围

本 SOP 用于把一个监控对象（先以 MySQL 为例）从“模板可见”落地到“采集可用 + 告警可用 + 端到端可验证”。

适用范围：

- 模板来源为 HertzBeat 风格 YAML（`params/metrics/aliasFields/calculates/units`）
- 当前架构为 `Python Web + manager-go + collector-go`

---

## 2. 基线对照（以 MySQL 为例）

### 2.1 参考实现（HertzBeat）

参考路径：

- `hertzbeat-master/hertzbeat-collector/hertzbeat-collector-basic/src/main/java/org/apache/hertzbeat/collector/collect/database/JdbcCommonCollect.java`

关键行为：

1. `queryType=columns`：按两列结果（key/value）映射字段，字段匹配大小写不敏感。  
2. `queryType=oneRow/multiRow`：按 aliasFields/字段名映射输出。  
3. JDBC URL/平台处理、连接复用、超时与安全校验。  

### 2.2 当前系统发现的差距（本次已补齐）

1. `aliasFields` 没有下发到 collector，导致 JDBC 映射与模板字段不完全一致。  
2. `units` 没有编译为转换逻辑，模板单位语义未落地。  
3. `multiRow` 结果在字段白名单阶段被整体丢弃（`rowN_` 前缀与模板字段名不匹配）。  
4. MySQL 缺少像 Redis 一样的默认告警策略 fallback。  

---

## 3. 实施步骤（通用）

### Step A：模板语义编译（manager-go）

1. 在模板编译阶段把 `aliasFields` 编译到任务参数（`alias_fields`）。  
2. 把 `units` 编译为 `Transform`（如 `B->KB` => `mul:0.0009765625`）。  
3. 保持模板 SQL 合并优化（MySQL `show global status/variables`）。  

本次代码位置：

- `manager-go/internal/template/compiler.go`
- `manager-go/internal/template/metric_compile_extras.go`

### Step B：协议执行对齐（collector-go）

1. JDBC 采集器支持读取 `alias_fields`。  
2. `columns` 采集按 alias 做大小写不敏感映射。  
3. `oneRow` / `multiRow` 增加按 alias 投影输出。  
4. `multiRow` 保留首行 canonical 字段（便于 `calculates/field_specs`），同时输出 `rowN_` 字段。  

本次代码位置：

- `collector-go/internal/protocol/jdbccollector/jdbc.go`
- `collector-go/internal/protocol/jdbccollector/mapping.go`

### Step C：白名单策略修正（collector-go pipeline）

1. 白名单匹配允许 `rowN_<field>` 形式通过（当 `<field>` 在 field_specs 中时）。  

本次代码位置：

- `collector-go/internal/pipeline/calculate.go`

### Step D：默认告警策略（python-web）

1. 增加 MySQL 默认告警规则 fallback。  
2. 创建目标时勾选“应用默认告警策略”即可自动落规则。  

本次代码位置：

- `backend/app/services/monitoring_target_helpers.py`
- `backend/app/routes/monitoring_target.py`

---

## 4. MySQL 默认告警策略（本次建议值）

1. `mysql_server_up == 0`（critical）  
2. `(max_used_connections / max_connections) * 100 > 90`（warning）  
3. `threads_running > 100`（warning）  
4. `aborted_connects > 10`（warning）  
5. `innodb_buffer_hit_rate < 90`（warning）  
6. `table_locks_waited > 10`（warning）  

> 后续可按业务负载再调阈值；初版以“先可用、再精调”为原则。

---

## 5. 验证清单（每次迁移都执行）

1. 创建监控目标（勾选“应用默认告警策略”）。  
2. 确认 manager 编译出的 task 含 `field_specs/calculate_specs/alias_fields/transform`。  
3. 确认 collector 上报字段非空，且关键字段可落到 metrics/latest。  
4. 人工制造异常（停库/限连接/压测）验证告警触发与恢复。  
5. 确认前端详情页可看到关键字符串字段与数值字段。  

---

## 6. 迁移到其他对象的套用模板

把 `mysql` 替换为目标对象（如 `postgres/nginx/kafka`），按下面顺序执行：

1. 先补 **模板编译语义**（alias/calculates/units）。  
2. 再补 **collector 协议映射**（queryType/字段对齐）。  
3. 再补 **默认告警策略**（fallback 或模板 alerts 段）。  
4. 最后跑 **端到端验证清单**。  

这样可以避免“模板已上架但采集口径跑偏”。
