# Web 服务器默认告警策略基线

## 当前覆盖

- `tomcat`: 13 条
- `jetty`: 13 条

## 设计原则

- 可用性走 `realtime_metric`
- 线程池饱和、请求耗时、内存使用走 `periodic_metric`
- 高并发场景补充比率型规则（错误率、平均耗时、线程饱和度、排队压力）
- `core` 默认启用，`extended` 默认关闭

## 指标来源（Jolokia）

- Tomcat：`Catalina:type=ThreadPool`、`Catalina:type=GlobalRequestProcessor`、`java.lang:*`
- Jetty：`org.eclipse.jetty.server:type=server`、`org.eclipse.jetty.util.thread:type=queuedthreadpool`、`java.lang:*`
