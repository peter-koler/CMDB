# 中间件默认告警策略基线

## 当前覆盖

- `activemq`: 11 条（模板采集通道：`Jolokia + HTTP`）
- `kafka`: 11 条（模板采集通道：`Jolokia + HTTP`）
- `kafka_client`: 11 条
- `pulsar`: 11 条
- `rabbitmq`: 12 条
- `rocketmq`: 11 条
- `shenyu`: 11 条
- `spring_gateway`: 11 条
- `zookeeper`: 11 条
- `apollo`: 11 条

## 设计原则

- 可用性规则全部走 `realtime_metric`
- 容量、积压、CPU、内存、FD、延迟类规则走 `periodic_metric`
- `core` 默认启用
- `extended` 默认关闭，作为扩展排障规则

## 当前阶段说明

这些规则已经写进模板 YAML 和 `monitor_templates`。

但“规则可展示”不等于“采集协议已全部完成”。当前阶段采集能力状态如下：

- 已完成：
  - `Apollo`
  - `Pulsar`
  - `RabbitMQ`
  - `ShenYu`
  - `Zookeeper`
  - `Kafka(基于客户端)`
- 待继续：
  - `Spring Cloud Gateway` 动态模板
