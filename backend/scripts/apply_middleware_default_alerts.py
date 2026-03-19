#!/usr/bin/env python3
"""
为中间件模板写入差异化默认告警策略（alerts）。

阶段说明：
1) 当前模板与默认策略覆盖全部中间件目标
2) collector-go 已完成 http / telnet / kclient 的正式支持
3) spring_gateway 动态展开、activemq/kafka jmx、rocketmq 原生协议在后续阶段继续补齐
"""

from __future__ import annotations

from pathlib import Path


def rule(
    *,
    key: str,
    name: str,
    metric: str,
    operator: str,
    threshold,
    level: str,
    period: int,
    times: int,
    mode: str,
    enabled: bool,
    template: str,
    expr: str | None = None,
    rule_type: str = "periodic_metric",
) -> dict:
    return {
        "key": key,
        "name": name,
        "type": rule_type,
        "metric": metric,
        "operator": operator,
        "threshold": threshold,
        "level": level,
        "period": period,
        "times": times,
        "mode": mode,
        "enabled": enabled,
        "expr": expr or f"{metric} {operator} {threshold}",
        "template": template,
    }


def availability_rule(app: str, display_name: str) -> dict:
    metric = f"{app}_server_up"
    return rule(
        key=f"{app}_unavailable",
        name=f"{display_name}实例不可用",
        metric=metric,
        operator="==",
        threshold=0,
        level="critical",
        period=60,
        times=1,
        mode="core",
        enabled=True,
        expr=f"{metric} == 0",
        template="实例不可用",
        rule_type="realtime_metric",
    )


def activemq_policies() -> list[dict]:
    app = "activemq"
    name = "ActiveMQ"
    return [
        availability_rule(app, name),
        rule(key="activemq_memory_usage_high", name="ActiveMQ内存使用率偏高", metric="MemoryPercentUsage", operator=">", threshold=75, level="warning", period=300, times=2, mode="core", enabled=True, template="内存使用率偏高"),
        rule(key="activemq_memory_usage_critical", name="ActiveMQ内存使用率过高", metric="MemoryPercentUsage", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="内存使用率过高"),
        rule(key="activemq_store_usage_high", name="ActiveMQ存储使用率偏高", metric="StorePercentUsage", operator=">", threshold=75, level="warning", period=300, times=2, mode="core", enabled=True, template="存储使用率偏高"),
        rule(key="activemq_store_usage_critical", name="ActiveMQ存储使用率过高", metric="StorePercentUsage", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="存储使用率过高"),
        rule(key="activemq_temp_usage_high", name="ActiveMQ临时存储使用率偏高", metric="TempPercentUsage", operator=">", threshold=70, level="warning", period=300, times=2, mode="core", enabled=True, template="临时存储使用率偏高"),
        rule(key="activemq_connections_high", name="ActiveMQ当前连接数偏高", metric="CurrentConnectionsCount", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="当前连接数偏高"),
        rule(key="activemq_producers_drop", name="ActiveMQ生产者数量异常下降", metric="TotalProducerCount", operator="<", threshold=1, level="warning", period=600, times=2, mode="extended", enabled=False, template="生产者数量异常下降"),
        rule(key="activemq_consumers_drop", name="ActiveMQ消费者数量异常下降", metric="TotalConsumerCount", operator="<", threshold=1, level="warning", period=600, times=2, mode="extended", enabled=False, template="消费者数量异常下降"),
        rule(key="activemq_queue_backlog", name="ActiveMQ消息积压扩大", metric="TotalEnqueueCount", operator=">", threshold=100000, level="warning", period=300, times=2, mode="extended", enabled=False, template="消息积压扩大", expr="(TotalEnqueueCount - TotalDequeueCount) > 100000"),
        rule(key="activemq_uptime_short", name="ActiveMQ疑似频繁重启", metric="UptimeMillis", operator="<", threshold=3600000, level="warning", period=600, times=1, mode="extended", enabled=False, template="疑似频繁重启"),
    ]


def kafka_jmx_policies() -> list[dict]:
    app = "kafka"
    name = "Kafka"
    return [
        availability_rule(app, name),
        rule(key="kafka_controller_missing", name="Kafka无活跃控制器", metric="ActiveControllerCount", operator="<", threshold=1, level="critical", period=60, times=1, mode="core", enabled=True, template="无活跃控制器", rule_type="realtime_metric"),
        rule(key="kafka_broker_drop", name="Kafka活跃Broker数量偏少", metric="ActiveBrokerCount", operator="<", threshold=3, level="warning", period=300, times=2, mode="core", enabled=True, template="活跃Broker数量偏少"),
        rule(key="kafka_offline_partitions", name="Kafka存在离线分区", metric="OfflinePartitionsCount", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="存在离线分区", rule_type="realtime_metric"),
        rule(key="kafka_replica_imbalance", name="Kafka副本不平衡偏高", metric="PreferredReplicaImbalanceCount", operator=">", threshold=10, level="warning", period=300, times=2, mode="core", enabled=True, template="副本不平衡偏高"),
        rule(key="kafka_fenced_brokers", name="Kafka存在被隔离Broker", metric="FencedBrokerCount", operator=">", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="存在被隔离Broker", rule_type="realtime_metric"),
        rule(key="kafka_delete_topics_pending", name="Kafka待删除主题过多", metric="TopicsToDeleteCount", operator=">", threshold=5, level="warning", period=600, times=2, mode="extended", enabled=False, template="待删除主题过多"),
        rule(key="kafka_delete_replicas_pending", name="Kafka待删除副本过多", metric="ReplicasToDeleteCount", operator=">", threshold=10, level="warning", period=600, times=2, mode="extended", enabled=False, template="待删除副本过多"),
        rule(key="kafka_global_topics_high", name="Kafka主题数量偏高", metric="GlobalTopicCount", operator=">", threshold=1000, level="warning", period=1800, times=1, mode="extended", enabled=False, template="主题数量偏高"),
        rule(key="kafka_global_partitions_high", name="Kafka分区数量偏高", metric="GlobalPartitionCount", operator=">", threshold=10000, level="warning", period=1800, times=1, mode="extended", enabled=False, template="分区数量偏高"),
        rule(key="kafka_jvm_restart", name="Kafka JVM运行时长过短", metric="Uptime", operator="<", threshold=3600000, level="warning", period=600, times=1, mode="extended", enabled=False, template="JVM运行时长过短"),
    ]


def kafka_client_policies() -> list[dict]:
    app = "kafka_client"
    name = "Kafka客户端"
    return [
        availability_rule(app, name),
        rule(key="kafka_client_topics_missing", name="Kafka主题数量异常偏少", metric="TopicName", operator="<", threshold=1, level="warning", period=1800, times=1, mode="extended", enabled=False, template="主题数量异常偏少", expr="row1_TopicName == ''"),
        rule(key="kafka_client_partition_small", name="Kafka主题分区配置偏小", metric="PartitionNum", operator="<", threshold=3, level="warning", period=1800, times=1, mode="extended", enabled=False, template="主题分区配置偏小"),
        rule(key="kafka_client_replication_small", name="Kafka副本因子偏小", metric="ReplicationFactorSize", operator="<", threshold=2, level="warning", period=1800, times=1, mode="core", enabled=True, template="副本因子偏小"),
        rule(key="kafka_client_lag_high", name="Kafka消费组积压偏高", metric="Lag", operator=">", threshold=10000, level="warning", period=300, times=2, mode="core", enabled=True, template="消费组积压偏高"),
        rule(key="kafka_client_lag_critical", name="Kafka消费组积压过高", metric="Lag", operator=">", threshold=50000, level="critical", period=300, times=1, mode="core", enabled=True, template="消费组积压过高"),
        rule(key="kafka_client_consumer_missing", name="Kafka消费组无成员", metric="group_member_num", operator="<", threshold=1, level="critical", period=300, times=1, mode="core", enabled=True, template="消费组无成员"),
        rule(key="kafka_client_consumer_small", name="Kafka消费组成员过少", metric="group_member_num", operator="<", threshold=2, level="warning", period=300, times=2, mode="extended", enabled=False, template="消费组成员过少"),
        rule(key="kafka_client_latest_offset_high", name="Kafka最新偏移量增长过快", metric="latest", operator=">", threshold=10000000, level="warning", period=600, times=2, mode="extended", enabled=False, template="最新偏移量增长过快"),
        rule(key="kafka_client_partition_offset_gap", name="Kafka分区偏移跨度过大", metric="latest", operator=">", threshold=1000000, level="warning", period=600, times=2, mode="extended", enabled=False, template="分区偏移跨度过大", expr="(latest - earliest) > 1000000"),
        rule(key="kafka_client_topic_name_empty", name="Kafka主题列表采集为空", metric="TopicName", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="主题列表采集为空", expr="TopicName == ''", rule_type="realtime_metric"),
    ]


def pulsar_policies() -> list[dict]:
    app = "pulsar"
    name = "Pulsar"
    return [
        availability_rule(app, name),
        rule(key="pulsar_fd_usage_high", name="Pulsar文件描述符使用率偏高", metric="process_open_fds", operator=">", threshold=75, level="warning", period=300, times=2, mode="core", enabled=True, template="文件描述符使用率偏高", expr="(process_max_fds > 0) && ((process_open_fds / process_max_fds) * 100 > 75)"),
        rule(key="pulsar_fd_usage_critical", name="Pulsar文件描述符使用率过高", metric="process_open_fds", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="文件描述符使用率过高", expr="(process_max_fds > 0) && ((process_open_fds / process_max_fds) * 100 > 90)"),
        rule(key="pulsar_jvm_pool_used_high", name="Pulsar JVM内存池使用偏高", metric="value", operator=">", threshold=2147483648, level="warning", period=300, times=2, mode="core", enabled=True, template="JVM内存池使用偏高", expr="value > 2147483648"),
        rule(key="pulsar_jvm_pool_used_critical", name="Pulsar JVM内存池使用过高", metric="value", operator=">", threshold=4294967296, level="critical", period=300, times=1, mode="extended", enabled=False, template="JVM内存池使用过高", expr="value > 4294967296"),
        rule(key="pulsar_start_time_reset", name="Pulsar进程疑似重启", metric="process_start_time_seconds", operator="<", threshold=3600, level="warning", period=600, times=1, mode="extended", enabled=False, template="进程疑似重启", expr="process_start_time_seconds < 3600"),
        rule(key="pulsar_open_fds_burst", name="Pulsar打开文件数突增", metric="process_open_fds", operator=">", threshold=10000, level="warning", period=300, times=2, mode="extended", enabled=False, template="打开文件数突增"),
        rule(key="pulsar_pool_oldgen_high", name="Pulsar老年代内存占用偏高", metric="value", operator=">", threshold=3221225472, level="warning", period=300, times=2, mode="extended", enabled=False, template="老年代内存占用偏高", expr="(pool == 'G1 Old Gen' || pool == 'PS Old Gen') && value > 3221225472"),
        rule(key="pulsar_pool_metaspace_high", name="Pulsar元空间使用偏高", metric="value", operator=">", threshold=536870912, level="warning", period=600, times=2, mode="extended", enabled=False, template="元空间使用偏高", expr="(pool == 'Metaspace') && value > 536870912"),
        rule(key="pulsar_version_missing", name="Pulsar版本信息缺失", metric="version", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="版本信息缺失", expr="version == ''"),
        rule(key="pulsar_metrics_blank", name="Pulsar指标暴露异常", metric="value", operator="<", threshold=0, level="warning", period=300, times=1, mode="extended", enabled=False, template="指标暴露异常", expr="value == ''", rule_type="realtime_metric"),
    ]


def rabbitmq_policies() -> list[dict]:
    app = "rabbitmq"
    name = "RabbitMQ"
    return [
        availability_rule(app, name),
        rule(key="rabbitmq_connections_high", name="RabbitMQ连接数偏高", metric="connections", operator=">", threshold=1000, level="warning", period=300, times=2, mode="core", enabled=True, template="连接数偏高"),
        rule(key="rabbitmq_consumers_drop", name="RabbitMQ消费者数量偏少", metric="consumers", operator="<", threshold=1, level="warning", period=300, times=2, mode="core", enabled=True, template="消费者数量偏少"),
        rule(key="rabbitmq_queue_depth_high", name="RabbitMQ队列堆积偏高", metric="messages", operator=">", threshold=100000, level="warning", period=300, times=2, mode="core", enabled=True, template="队列堆积偏高"),
        rule(key="rabbitmq_queue_depth_critical", name="RabbitMQ队列堆积过高", metric="messages", operator=">", threshold=500000, level="critical", period=300, times=1, mode="core", enabled=True, template="队列堆积过高"),
        rule(key="rabbitmq_unacked_high", name="RabbitMQ未确认消息偏高", metric="messages_unacknowledged", operator=">", threshold=50000, level="warning", period=300, times=2, mode="core", enabled=True, template="未确认消息偏高"),
        rule(key="rabbitmq_queue_consumers_zero", name="RabbitMQ队列无消费者", metric="consumers", operator="==", threshold=0, level="critical", period=300, times=1, mode="extended", enabled=False, template="队列无消费者", rule_type="realtime_metric"),
        rule(key="rabbitmq_node_mem_high", name="RabbitMQ节点内存使用偏高", metric="mem_used", operator=">", threshold=2147483648, level="warning", period=300, times=2, mode="core", enabled=True, template="节点内存使用偏高"),
        rule(key="rabbitmq_node_fd_high", name="RabbitMQ文件描述符使用偏高", metric="fd_used", operator=">", threshold=80, level="warning", period=300, times=2, mode="extended", enabled=False, template="文件描述符使用偏高", expr="(fd_total > 0) && ((fd_used / fd_total) * 100 > 80)"),
        rule(key="rabbitmq_node_disk_low", name="RabbitMQ磁盘剩余空间不足", metric="disk_free", operator="<", threshold=10737418240, level="critical", period=300, times=1, mode="core", enabled=True, template="磁盘剩余空间不足"),
        rule(key="rabbitmq_channels_high", name="RabbitMQ通道数偏高", metric="channels", operator=">", threshold=5000, level="warning", period=300, times=2, mode="extended", enabled=False, template="通道数偏高"),
        rule(key="rabbitmq_rate_drop", name="RabbitMQ吞吐明显失衡", metric="messages_ready", operator=">", threshold=10000, level="warning", period=300, times=2, mode="extended", enabled=False, template="吞吐明显失衡", expr="(messages_ready > 10000) && (messages_unacknowledged > 10000)"),
    ]


def rocketmq_policies() -> list[dict]:
    app = "rocketmq"
    name = "RocketMQ"
    return [
        availability_rule(app, name),
        rule(key="rocketmq_route_error_exists", name="RocketMQ存在主题路由异常", metric="TopicRouteErrorCount", operator=">", threshold=0, level="critical", period=120, times=1, mode="core", enabled=True, template="存在主题路由异常", rule_type="realtime_metric"),
        rule(key="rocketmq_broker_coverage_low", name="RocketMQ Broker覆盖数偏少", metric="BrokerCount", operator="<", threshold=2, level="warning", period=300, times=2, mode="core", enabled=True, template="Broker覆盖数偏少"),
        rule(key="rocketmq_normal_topics_missing", name="RocketMQ业务主题数异常偏少", metric="NormalTopicCount", operator="<", threshold=1, level="critical", period=600, times=1, mode="core", enabled=True, template="业务主题数异常偏少"),
        rule(key="rocketmq_retry_topics_high", name="RocketMQ重试主题数量偏多", metric="RetryTopicCount", operator=">", threshold=100, level="warning", period=900, times=2, mode="extended", enabled=False, template="重试主题数量偏多"),
        rule(key="rocketmq_dead_letter_topics_high", name="RocketMQ死信主题数量偏多", metric="DeadLetterTopicCount", operator=">", threshold=20, level="warning", period=900, times=2, mode="extended", enabled=False, template="死信主题数量偏多"),
        rule(key="rocketmq_queue_count_low", name="RocketMQ队列总数偏少", metric="QueueCount", operator="<", threshold=4, level="warning", period=1800, times=1, mode="extended", enabled=False, template="队列总数偏少"),
        rule(key="rocketmq_avg_queue_small", name="RocketMQ平均每主题队列数偏小", metric="AvgQueueCountPerTopic", operator="<", threshold=2, level="warning", period=1800, times=1, mode="extended", enabled=False, template="平均每主题队列数偏小"),
        rule(key="rocketmq_max_queue_large", name="RocketMQ单主题队列数过大", metric="MaxQueueCountPerTopic", operator=">", threshold=64, level="warning", period=1800, times=1, mode="extended", enabled=False, template="单主题队列数过大"),
        rule(key="rocketmq_topic_count_high", name="RocketMQ主题总数偏高", metric="TopicCount", operator=">", threshold=2000, level="warning", period=1800, times=1, mode="core", enabled=True, template="主题总数偏高"),
        rule(key="rocketmq_route_status_abnormal", name="RocketMQ主题路由状态异常", metric="RouteStatus", operator="==", threshold=0, level="warning", period=300, times=1, mode="extended", enabled=False, template="主题路由状态异常", expr="RouteStatus != 'ok'", rule_type="realtime_metric"),
    ]


def shenyu_policies() -> list[dict]:
    app = "shenyu"
    name = "ShenYu"
    return [
        availability_rule(app, name),
        rule(key="shenyu_request_total_high", name="ShenYu请求量偏高", metric="value", operator=">", threshold=100000, level="warning", period=300, times=2, mode="core", enabled=True, template="请求量偏高", expr="value > 100000"),
        rule(key="shenyu_request_error_high", name="ShenYu异常请求偏高", metric="value", operator=">", threshold=100, level="warning", period=300, times=1, mode="core", enabled=True, template="异常请求偏高", expr="value > 100"),
        rule(key="shenyu_request_error_critical", name="ShenYu异常请求过高", metric="value", operator=">", threshold=1000, level="critical", period=300, times=1, mode="core", enabled=True, template="异常请求过高", expr="value > 1000"),
        rule(key="shenyu_process_fd_high", name="ShenYu文件描述符使用偏高", metric="value", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="文件描述符使用偏高", expr="(process_max_fds > 0) && ((process_open_fds / process_max_fds) * 100 > 80)"),
        rule(key="shenyu_cpu_high", name="ShenYu CPU时间累积过快", metric="value", operator=">", threshold=3600, level="warning", period=300, times=2, mode="extended", enabled=False, template="CPU时间累积过快", expr="value > 3600"),
        rule(key="shenyu_heap_used_high", name="ShenYu堆内存使用偏高", metric="value", operator=">", threshold=2147483648, level="warning", period=300, times=2, mode="core", enabled=True, template="堆内存使用偏高", expr="(area == 'heap') && value > 2147483648"),
        rule(key="shenyu_nonheap_used_high", name="ShenYu非堆内存使用偏高", metric="value", operator=">", threshold=1073741824, level="warning", period=300, times=2, mode="extended", enabled=False, template="非堆内存使用偏高", expr="(area == 'nonheap') && value > 1073741824"),
        rule(key="shenyu_jvm_info_missing", name="ShenYu JVM信息缺失", metric="runtime", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="JVM信息缺失", expr="runtime == ''"),
        rule(key="shenyu_old_pool_high", name="ShenYu老年代内存池使用偏高", metric="value", operator=">", threshold=2147483648, level="warning", period=300, times=2, mode="extended", enabled=False, template="老年代内存池使用偏高", expr="(pool == 'G1 Old Gen' || pool == 'PS Old Gen') && value > 2147483648"),
        rule(key="shenyu_metrics_missing", name="ShenYu指标暴露异常", metric="value", operator="==", threshold=0, level="warning", period=600, times=1, mode="extended", enabled=False, template="指标暴露异常", expr="value == ''", rule_type="realtime_metric"),
    ]


def spring_gateway_policies() -> list[dict]:
    app = "spring_gateway"
    name = "Spring Gateway"
    return [
        availability_rule(app, name),
        rule(key="spring_gateway_unhealthy", name="Spring Gateway健康检查失败", metric="status", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="健康检查失败", expr="status != 'UP'", rule_type="realtime_metric"),
        rule(key="spring_gateway_response_high", name="Spring Gateway响应时间偏高", metric="responseTime", operator=">", threshold=1000, level="warning", period=300, times=2, mode="core", enabled=True, template="响应时间偏高"),
        rule(key="spring_gateway_response_critical", name="Spring Gateway响应时间过高", metric="responseTime", operator=">", threshold=3000, level="critical", period=300, times=1, mode="core", enabled=True, template="响应时间过高"),
        rule(key="spring_gateway_threads_blocked", name="Spring Gateway阻塞线程存在", metric="state", operator="==", threshold=0, level="warning", period=300, times=1, mode="extended", enabled=False, template="阻塞线程存在", expr="state == 'BLOCKED'", rule_type="realtime_metric"),
        rule(key="spring_gateway_waiting_threads_many", name="Spring Gateway等待线程偏多", metric="Size", operator=">", threshold=100, level="warning", period=300, times=2, mode="extended", enabled=False, template="等待线程偏多", expr="(state == 'WAITING' || state == 'TIMED_WAITING') && Size > 100"),
        rule(key="spring_gateway_memory_high", name="Spring Gateway内存使用偏高", metric="mem_used", operator=">", threshold=1024, level="warning", period=300, times=2, mode="core", enabled=True, template="内存使用偏高"),
        rule(key="spring_gateway_memory_critical", name="Spring Gateway内存使用过高", metric="mem_used", operator=">", threshold=2048, level="critical", period=300, times=1, mode="core", enabled=True, template="内存使用过高"),
        rule(key="spring_gateway_routes_missing", name="Spring Gateway路由信息为空", metric="route_id", operator="==", threshold=0, level="warning", period=1800, times=1, mode="extended", enabled=False, template="路由信息为空", expr="route_id == ''"),
        rule(key="spring_gateway_env_missing", name="Spring Gateway环境信息采集为空", metric="profile", operator="==", threshold=0, level="warning", period=1800, times=1, mode="extended", enabled=False, template="环境信息采集为空", expr="profile == ''"),
        rule(key="spring_gateway_jvm_version_missing", name="Spring Gateway JVM版本缺失", metric="jvm_version", operator="==", threshold=0, level="warning", period=3600, times=1, mode="extended", enabled=False, template="JVM版本缺失", expr="jvm_version == ''"),
    ]


def zookeeper_policies() -> list[dict]:
    app = "zookeeper"
    name = "ZooKeeper"
    return [
        availability_rule(app, name),
        rule(key="zookeeper_state_abnormal", name="ZooKeeper节点状态异常", metric="zk_server_state", operator="==", threshold=0, level="critical", period=60, times=1, mode="core", enabled=True, template="节点状态异常", expr="zk_server_state != 'leader' && zk_server_state != 'follower' && zk_server_state != 'standalone'", rule_type="realtime_metric"),
        rule(key="zookeeper_alive_connections_high", name="ZooKeeper存活连接偏高", metric="zk_num_alive_connections", operator=">", threshold=500, level="warning", period=300, times=2, mode="core", enabled=True, template="存活连接偏高"),
        rule(key="zookeeper_avg_latency_high", name="ZooKeeper平均延迟偏高", metric="zk_avg_latency", operator=">", threshold=50, level="warning", period=300, times=2, mode="core", enabled=True, template="平均延迟偏高"),
        rule(key="zookeeper_max_latency_high", name="ZooKeeper最大延迟过高", metric="zk_max_latency", operator=">", threshold=200, level="critical", period=300, times=1, mode="core", enabled=True, template="最大延迟过高"),
        rule(key="zookeeper_outstanding_requests_high", name="ZooKeeper未完成请求偏高", metric="zk_outstanding_requests", operator=">", threshold=100, level="warning", period=300, times=2, mode="core", enabled=True, template="未完成请求偏高"),
        rule(key="zookeeper_watch_count_high", name="ZooKeeper Watch数量偏高", metric="zk_watch_count", operator=">", threshold=100000, level="warning", period=600, times=2, mode="extended", enabled=False, template="Watch数量偏高"),
        rule(key="zookeeper_data_size_high", name="ZooKeeper数据量偏大", metric="zk_approximate_data_size", operator=">", threshold=1048576, level="warning", period=600, times=2, mode="extended", enabled=False, template="数据量偏大"),
        rule(key="zookeeper_fd_usage_high", name="ZooKeeper文件描述符使用偏高", metric="zk_open_file_descriptor_count", operator=">", threshold=80, level="warning", period=300, times=2, mode="extended", enabled=False, template="文件描述符使用偏高", expr="(zk_max_file_descriptor_count > 0) && ((zk_open_file_descriptor_count / zk_max_file_descriptor_count) * 100 > 80)"),
        rule(key="zookeeper_packets_in_burst", name="ZooKeeper入包量突增", metric="zk_packets_received", operator=">", threshold=100000, level="warning", period=300, times=2, mode="extended", enabled=False, template="入包量突增"),
        rule(key="zookeeper_packets_out_burst", name="ZooKeeper出包量突增", metric="zk_packets_sent", operator=">", threshold=100000, level="warning", period=300, times=2, mode="extended", enabled=False, template="出包量突增"),
    ]


def apollo_policies() -> list[dict]:
    app = "apollo"
    name = "Apollo"
    return [
        availability_rule(app, name),
        rule(key="apollo_ready_time_high", name="Apollo启动耗时偏高", metric="metric_value", operator=">", threshold=60, level="warning", period=1800, times=1, mode="extended", enabled=False, template="启动耗时偏高"),
        rule(key="apollo_uptime_short", name="Apollo运行时长过短", metric="metric_value", operator="<", threshold=3600, level="warning", period=600, times=1, mode="extended", enabled=False, template="运行时长过短"),
        rule(key="apollo_process_cpu_high", name="Apollo进程CPU使用率偏高", metric="metric_value", operator=">", threshold=75, level="warning", period=300, times=2, mode="core", enabled=True, template="进程CPU使用率偏高"),
        rule(key="apollo_process_cpu_critical", name="Apollo进程CPU使用率过高", metric="metric_value", operator=">", threshold=90, level="critical", period=300, times=1, mode="core", enabled=True, template="进程CPU使用率过高"),
        rule(key="apollo_system_cpu_high", name="Apollo系统CPU使用率偏高", metric="metric_value", operator=">", threshold=80, level="warning", period=300, times=2, mode="core", enabled=True, template="系统CPU使用率偏高"),
        rule(key="apollo_system_load_high", name="Apollo系统负载偏高", metric="metric_value", operator=">", threshold=8, level="warning", period=300, times=2, mode="extended", enabled=False, template="系统负载偏高"),
        rule(key="apollo_heap_committed_high", name="Apollo堆内存提交量偏高", metric="metric_value", operator=">", threshold=2147483648, level="warning", period=300, times=2, mode="core", enabled=True, template="堆内存提交量偏高", expr="(area == 'heap') && metric_value > 2147483648"),
        rule(key="apollo_heap_used_high", name="Apollo堆内存使用偏高", metric="metric_value", operator=">", threshold=1717986918, level="warning", period=300, times=2, mode="core", enabled=True, template="堆内存使用偏高", expr="(area == 'heap') && metric_value > 1717986918"),
        rule(key="apollo_heap_used_critical", name="Apollo堆内存使用过高", metric="metric_value", operator=">", threshold=3221225472, level="critical", period=300, times=1, mode="extended", enabled=False, template="堆内存使用过高", expr="(area == 'heap') && metric_value > 3221225472"),
        rule(key="apollo_nonheap_used_high", name="Apollo非堆内存使用偏高", metric="metric_value", operator=">", threshold=1073741824, level="warning", period=300, times=2, mode="extended", enabled=False, template="非堆内存使用偏高", expr="(area == 'nonheap') && metric_value > 1073741824"),
    ]


POLICIES: dict[str, list[dict]] = {
    "activemq": activemq_policies(),
    "kafka": kafka_jmx_policies(),
    "kafka_client": kafka_client_policies(),
    "pulsar": pulsar_policies(),
    "rabbitmq": rabbitmq_policies(),
    "rocketmq": rocketmq_policies(),
    "shenyu": shenyu_policies(),
    "spring_gateway": spring_gateway_policies(),
    "zookeeper": zookeeper_policies(),
    "apollo": apollo_policies(),
}


def _yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _render_alerts(alerts: list[dict]) -> str:
    lines = ["alerts:"]
    for item in alerts:
        lines.append(f"  - key: {_yaml_scalar(item['key'])}")
        lines.append(f"    name: {_yaml_scalar(item['name'])}")
        lines.append(f"    type: {_yaml_scalar(item['type'])}")
        lines.append(f"    metric: {_yaml_scalar(item['metric'])}")
        lines.append(f"    operator: {_yaml_scalar(item['operator'])}")
        lines.append(f"    threshold: {_yaml_scalar(item['threshold'])}")
        lines.append(f"    level: {_yaml_scalar(item['level'])}")
        lines.append(f"    period: {_yaml_scalar(item['period'])}")
        lines.append(f"    times: {_yaml_scalar(item['times'])}")
        lines.append(f"    mode: {_yaml_scalar(item['mode'])}")
        lines.append(f"    enabled: {_yaml_scalar(item['enabled'])}")
        lines.append(f"    expr: {_yaml_scalar(item['expr'])}")
        lines.append(f"    template: {_yaml_scalar(item['template'])}")
    return "\n".join(lines) + "\n"


def _upsert_alerts(content: str, alerts_text: str) -> str:
    marker = "\nalerts:\n"
    if marker in content:
        return content.split(marker, 1)[0].rstrip() + "\n\n" + alerts_text
    return content.rstrip() + "\n\n" + alerts_text


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    template_dir = backend_dir / "templates"
    updated = 0
    for app, alerts in POLICIES.items():
        path = template_dir / f"app-{app}.yml"
        if not path.exists():
            print(f"[skip] missing template: {path}")
            continue
        raw = path.read_text(encoding="utf-8")
        merged = _upsert_alerts(raw, _render_alerts(alerts))
        path.write_text(merged, encoding="utf-8")
        updated += 1
        print(f"[ok] updated alerts: app-{app}.yml ({len(alerts)} rules)")
    print(f"[done] templates updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
