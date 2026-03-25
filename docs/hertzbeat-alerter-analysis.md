# HertzBeat Alerter 告警模块架构分析报告

## 1. 概述

HertzBeat Alerter 是 HertzBeat 监控系统的**告警核心模块**，负责：
- **实时告警计算**：基于采集数据进行实时告警规则匹配
- **周期告警计算**：基于时序数据库进行周期性告警计算
- **告警收敛**：分组、抑制、静默等告警降噪处理
- **告警通知**：多渠道告警通知（邮件、钉钉、企业微信、飞书等）
- **外部告警接入**：支持 Prometheus、Zabbix、SkyWalking 等外部告警接入

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HertzBeat Alerter (告警模块)                           │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        告警计算层 (Calculate)                            │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │   │
│  │  │ 实时告警计算     │  │ 周期告警计算     │  │ Collector 告警处理       │  │   │
│  │  │ (RealTime)      │  │ (Periodic)      │  │                         │  │   │
│  │  │                 │  │                 │  │ • 采集器离线告警          │  │   │
│  │  │ • 消费队列数据   │  │ • 查询时序数据库 │  │ • 采集器恢复通知          │  │   │
│  │  │ • JEXL 表达式   │  │ • SQL/PromQL    │  │                         │  │   │
│  │  │ • 窗口聚合      │  │ • 定时调度      │  │                         │  │   │
│  │  └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘  │   │
│  │           │                    │                       │                │   │
│  │           └────────────────────┴───────────────────────┘                │   │
│  │                              │                                          │   │
│  │                              ▼                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    告警收敛层 (Reduce)                           │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │   │
│  │  │  │ 告警分组     │  │ 告警抑制     │  │ 告警静默                 │  │   │   │
│  │  │  │ (Group)     │  │ (Inhibit)   │  │ (Silence)               │  │   │   │
│  │  │  │             │  │             │  │                         │  │   │   │
│  │  │  │ • 分组等待   │  │ • 源目标抑制 │  │ • 一次性静默             │  │   │   │
│  │  │  │ • 分组间隔   │  │ • 优先级控制 │  │ • 周期性静默             │  │   │   │
│  │  │  │ • 重复抑制   │  │             │  │ • 标签匹配               │  │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                              │                                          │   │
│  │                              ▼                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    告警通知层 (Notice)                           │   │   │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │   │   │
│  │  │  │                    AlertNoticeDispatch                     │  │   │   │
│  │  │  │  (告警分发器)                                               │  │   │   │
│  │  │  └───────────────────────────────────────────────────────────┘  │   │   │
│  │  │                              │                                  │   │   │
│  │  │           ┌──────────────────┼──────────────────┐               │   │   │
│  │  │           ▼                  ▼                  ▼               │   │   │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │   │   │
│  │  │  │  邮件通知   │    │  钉钉机器人  │    │  企业微信   │         │   │   │
│  │  │  │  Email     │    │  DingTalk   │    │  WeCom      │         │   │   │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘         │   │   │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │   │   │
│  │  │  │  飞书通知   │    │  短信通知   │    │  WebHook    │         │   │   │
│  │  │  │  FeiShu    │    │  SMS        │    │             │         │   │   │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘         │   │   │
│  │  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │   │   │
│  │  │  │  Slack     │    │  Telegram  │    │  更多...    │         │   │   │
│  │  │  └─────────────┘    └─────────────┘    └─────────────┘         │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        数据存储层 (DAO)                                  │   │
│  │  • AlertDefine (告警规则)  • SingleAlert (单告警)  • GroupAlert (告警组) │   │
│  │  • AlertSilence (静默规则) • AlertInhibit (抑制规则)                     │   │
│  │  • NoticeReceiver (通知接收人) • NoticeTemplate (通知模板)               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 告警计算层 (Calculate)

### 3.1 实时告警计算

```
┌─────────────────────────────────────────────────────────────────┐
│                 MetricsRealTimeAlertCalculator                   │
│                      (实时告警计算器)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │ CommonData  │    │  3 个计算    │    │   AlarmCommonReduce │  │
│  │   Queue     │───▶│   线程      │───▶│    (告警收敛层)      │  │
│  │             │    │             │    │                     │  │
│  │ 消费采集数据 │    │ • JEXL 表达式 │    │ • 生成指纹         │  │
│  │             │    │   计算      │    │ • 进入收敛流程      │  │
│  └─────────────┘    │ • 阈值判断   │    └─────────────────────┘  │
│                     │ • 标签匹配   │                            │
│                     └─────────────┘                            │
│                                                                  │
│  计算流程：                                                       │
│  1. 从 CommonDataQueue 消费 MetricsData                         │
│  2. 查询匹配的 AlertDefine (告警规则)                            │
│  3. 使用 JEXL 表达式计算指标值                                   │
│  4. 判断是否触发告警                                             │
│  5. 生成 SingleAlert 进入收敛层                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**核心类**：
- `MetricsRealTimeAlertCalculator`：实时告警计算器
- `JexlExprCalculator`：JEXL 表达式计算器
- `AlarmCacheManager`：告警缓存管理（pending/firing 状态）

#### 3.1.1 告警规则配置 (AlertDefine)

**实体类**: `org.apache.hertzbeat.common.entity.alerter.AlertDefine`

**核心字段**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | Long | 规则ID | 1 |
| `name` | String | 规则名称 | "high_cpu_usage" |
| `type` | String | 规则类型 | realtime_metric, periodic_metric, realtime_log, periodic_log |
| `expr` | String | 告警表达式 (JEXL) | `equals(__app__,"Linux") && usage>90` |
| `period` | Integer | 执行周期/窗口大小(秒) | 300 |
| `times` | Integer | 触发阈值次数 | 3 (连续3次触发才告警) |
| `labels` | Map | 告警标签 | {severity:critical, team:ops} |
| `annotations` | Map | 告警注释 | {summary:"CPU使用率过高"} |
| `template` | String | 告警内容模板 | "Instance {{$labels.instance}} CPU is {{$value}}%" |
| `datasource` | String | 数据源类型 | PROMETHEUS, VICTORIA_METRICS |
| `enable` | boolean | 是否启用 | true |

#### 3.1.2 告警规则匹配逻辑

**规则匹配流程**：

```java
// 1. 从数据库加载所有启用的实时告警规则
List<AlertDefine> thresholds = alertDefineService.getMetricsRealTimeAlertDefines();

// 2. 根据表达式过滤匹配当前监控数据的规则
thresholds = filterThresholdsByAppAndMetrics(thresholds, app, metrics, labels, instance, priority);
```

**表达式解析与匹配**：

```java
// 表达式示例：匹配 Linux 应用的 CPU 使用率告警
equals(__app__,"Linux") && equals(__metrics__,"cpu") && usage > 80

// 内置变量（系统自动注入）
__instance__      // 监控实例ID
__instancename__  // 监控实例名称  
__instancehost__  // 监控目标主机
__app__           // 应用类型 (Linux, MySQL, etc.)
__metrics__       // 指标集名称 (cpu, memory, etc.)
__priority__      // 优先级
__code__          // 采集状态码
__available__     // 可用状态 (up/down)
__labels__        // 标签集合
__row__           // 数据行号

// 支持的函数
equals(field, "value")     // 精确匹配
contains(__labels__, "k:v") // 标签包含
```

**过滤逻辑** (`filterThresholdsByAppAndMetrics`)：

1. **App 匹配**（必需）：表达式必须包含 `equals(__app__,"xxx")`，且与当前监控数据匹配
2. **Available 匹配**（必需）：非可用性指标（priority != 0）会过滤掉可用性检查表达式
3. **Metrics 匹配**（可选）：如果表达式包含 `equals(__metrics__,"xxx")`，则必须匹配
4. **Instance 匹配**（可选）：支持按实例ID或标签过滤
   - `equals(__instance__, "123")` - 精确匹配实例
   - `contains(__labels__, "env:prod")` - 标签匹配

#### 3.1.3 告警触发机制

**触发次数控制 (Times)**：

```
首次匹配 ──▶ Pending 状态 ──▶ 连续匹配 N 次 ──▶ Firing 状态
              (缓存中)          (times >= N)      (发送告警)
```

**状态流转**：

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `PENDING` | 待触发 | 首次匹配，未达到触发次数 |
| `FIRING` | 触发中 | 达到触发次数阈值，正在告警 |
| `RESOLVED` | 已恢复 | 表达式不再匹配，告警恢复 |

**核心代码逻辑**：

```java
// 计算指纹 (唯一标识一个告警)
String fingerprint = AlertUtil.calculateFingerprint(fingerPrints);

// 检查是否已存在 Pending 告警
SingleAlert existingAlert = alarmCacheManager.getPending(defineId, fingerprint);

if (existingAlert == null) {
    // 首次触发，创建 Pending 告警
    if (requiredTimes <= 1) {
        // 触发次数为1，直接转为 Firing
        newAlert.setStatus(CommonConstants.ALERT_STATUS_FIRING);
        alarmCacheManager.putFiring(defineId, fingerprint, newAlert);
        alarmCommonReduce.reduceAndSendAlarm(newAlert.clone());
    } else {
        // 放入 Pending 队列等待
        alarmCacheManager.putPending(defineId, fingerprint, newAlert);
    }
} else {
    // 更新触发次数
    existingAlert.setTriggerTimes(existingAlert.getTriggerTimes() + 1);
    
    // 达到阈值，转为 Firing
    if (existingAlert.getTriggerTimes() >= requiredTimes) {
        existingAlert.setStatus(CommonConstants.ALERT_STATUS_FIRING);
        alarmCacheManager.putFiring(defineId, fingerprint, existingAlert);
        alarmCommonReduce.reduceAndSendAlarm(existingAlert.clone());
    }
}
```

#### 3.1.4 告警恢复处理

当表达式不再匹配时，触发恢复逻辑：

```java
private void handleRecoveredAlert(Long defineId, Map<String, String> fingerprints) {
    String fingerprint = AlertUtil.calculateFingerprint(fingerprints);
    
    // 从 Firing 缓存中移除
    SingleAlert firingAlert = alarmCacheManager.removeFiring(defineId, fingerprint);
    if (firingAlert != null) {
        firingAlert.setStatus(CommonConstants.ALERT_STATUS_RESOLVED);
        firingAlert.setEndAt(System.currentTimeMillis());
        alarmCommonReduce.reduceAndSendAlarm(firingAlert.clone());
    }
    
    // 清理 Pending 缓存
    alarmCacheManager.removePending(defineId, fingerprint);
}
```

**JEXL 表达式示例**：
```java
// 判断 CPU 使用率超过 80%
"usage > 80"

// 判断响应时间超过阈值
"responseTime > 5000"

// 多条件组合
"cpuUsage > 80 && memoryUsage > 90"

// 带标签匹配的复杂表达式
equals(__app__,"Linux") && equals(__metrics__,"cpu") && usage > 80 && contains(__labels__, "env:production")
```

### 3.2 周期告警计算

```
┌─────────────────────────────────────────────────────────────────┐
│                 MetricsPeriodicAlertCalculator                   │
│                      (周期告警计算器)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ PeriodicAlert   │    │ DataSourceService│    │ AlarmCommon │ │
│  │ RuleScheduler   │───▶│   (数据源服务)   │───▶│   Reduce    │ │
│  │                 │    │                 │    │             │ │
│  │ • 定时调度      │    │ • 查询 Victoria │    │ 告警收敛    │ │
│  │ • 周期触发      │    │ • 查询 InfluxDB │    │             │ │
│  │                 │    │ • SQL/PromQL   │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                  │
│  适用场景：                                                       │
│  • 基于历史数据的聚合告警 (如：过去1小时平均CPU > 80%)            │
│  • 复杂 SQL/PromQL 查询告警                                      │
│  • 跨指标关联告警                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

#### 3.2.1 周期调度机制 (`PeriodicAlertRuleScheduler`)

**调度器职责**：
- 启动时加载所有启用的周期告警规则
- 为每个规则创建独立的定时任务
- 支持动态更新（新增、修改、删除规则时重新调度）

```java
// 规则类型判断
if (rule.getType().equals(METRIC_ALERT_THRESHOLD_TYPE_PERIODIC)
    || rule.getType().equals(LOG_ALERT_THRESHOLD_TYPE_PERIODIC)) {
    
    ScheduledFuture<?> future = scheduledExecutor.scheduleAtFixedRate(
        () -> metricsCalculator.calculate(rule),  // 执行计算
        0,                                        // 初始延迟
        rule.getPeriod(),                         // 周期(秒)
        TimeUnit.SECONDS
    );
    scheduledFutures.put(rule.getId(), future);
}
```

#### 3.2.2 周期计算逻辑 (`MetricsPeriodicAlertCalculator`)

**计算流程**：

1. **查询时序数据库**：根据规则配置的 `datasource` 和 `expr` 执行查询

```java
List<Map<String, Object>> results = dataSourceService.calculate(
    define.getDatasource(),  // 数据源: PROMETHEUS, VICTORIA_METRICS
    define.getExpr()         // 查询表达式: SQL/PromQL
);
```

2. **结果解析**：查询结果包含多个字段，特殊字段说明：
   - `__value__`: 阈值判断的核心值
   - `__timestamp__`: 数据时间戳
   - 其他字段: 用于生成告警标签

3. **阈值判断**：
   - `value == null`: 未触发阈值，检查是否需要恢复告警
   - `value != null`: 触发阈值，创建/更新告警

4. **告警触发机制**：与实时告警相同（支持 times 触发次数控制）

#### 3.2.3 周期告警规则配置示例

**规则类型**: `periodic_metric` 或 `periodic_log`

**PromQL 示例**：
```json
{
  "name": "high_avg_cpu_1h",
  "type": "periodic_metric",
  "expr": "avg_over_time(cpu_usage[1h]) > 80",
  "period": 300,
  "times": 1,
  "datasource": "PROMETHEUS",
  "labels": {
    "severity": "warning",
    "team": "ops"
  },
  "template": "过去1小时平均CPU使用率超过80%，当前值: {{$value}}%"
}
```

**SQL 示例**（VictoriaMetrics）：
```json
{
  "name": "disk_will_full_24h",
  "type": "periodic_metric", 
  "expr": "SELECT disk_usage, disk_total, (disk_usage/disk_total*100) as usage FROM disk WHERE time > now() - 24h AND usage > 90",
  "period": 3600,
  "times": 2,
  "datasource": "VICTORIA_METRICS",
  "template": "磁盘使用率超过90%，已用: {{$disk_usage}}GB，总计: {{$disk_total}}GB"
}
```

### 3.3 Collector 告警处理

```
┌─────────────────────────────────────────────────────────────────┐
│                    CollectorAlertHandler                         │
│                     (采集器告警处理器)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Collector 状态变化：                                             │
│                                                                  │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │  在线    │────────▶│  离线    │────────▶│  恢复    │        │
│  │  Online  │         │  Offline │         │  Recover │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│       │                    │                    │              │
│       │                    │                    │              │
│       ▼                    ▼                    ▼              │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │ 无操作   │         │ 生成告警  │         │ 恢复告警  │        │
│  │          │         │ 采集器离线│         │          │        │
│  └──────────┘         └──────────┘         └──────────┘        │
│                                                                  │
│  告警内容：                                                       │
│  • 告警名称：采集器 {name} 离线                                   │
│  • 告警级别：紧急                                                 │
│  • 标签：collectorName, collectorVersion, collectorHost          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 告警收敛层 (Reduce)

### 4.1 告警分组 (AlarmGroupReduce)

参考 Prometheus Alertmanager 的分组机制：

```
┌─────────────────────────────────────────────────────────────────┐
│                      AlarmGroupReduce                            │
│                       (告警分组收敛)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  分组配置 (AlertGroupConverge)：                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  group_wait: 30s        # 分组等待时间                   │   │
│  │  group_interval: 5m     # 分组发送间隔                   │   │
│  │  repeat_interval: 4h    # 重复告警间隔                   │   │
│  │  group_by: [alertname, instance]  # 分组标签            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  分组流程：                                                       │
│                                                                  │
│  告警1 ──┐                                                       │
│  告警2 ──┼──▶ 按标签分组 ──▶ 等待 30s ──▶ 合并发送 ──▶ 通知     │
│  告警3 ──┘          │                                         │
│                     │                                         │
│  告警4 ──┐          ▼                                         │
│  告警5 ──┼──▶ 另一组 ──▶ 等待 30s ──▶ 合并发送 ──▶ 通知        │
│                                                                  │
│  效果：5个告警 ──▶ 2条通知（按组聚合）                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 告警分组配置实体 (`AlertGroupConverge`)

**实体类**: `org.apache.hertzbeat.common.entity.alerter.AlertGroupConverge`

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `id` | Long | 分组策略ID | - |
| `name` | String | 策略名称 | - |
| `groupLabels` | List<String> | 分组标签列表 | ["instance"] |
| `groupWait` | Long | 初次分组等待时间(秒) | 30 |
| `groupInterval` | Long | 分组发送间隔(秒) | 300 (5分钟) |
| `repeatInterval` | Long | 重复告警间隔(秒) | 14400 (4小时) |
| `enable` | Boolean | 是否启用 | true |

#### 4.1.2 分组机制详解

**分组流程**：

1. **标签匹配**：检查告警是否包含所有分组标签
   ```java
   boolean matched = hasRequiredLabels(alertLabels, ruleConfig.getGroupLabels());
   ```

2. **生成 Group Key**：根据分组标签值生成唯一标识
   ```java
   // 示例：按 instance 分组
   // 告警1 labels: {instance: "server-01", alertname: "cpu_high"}
   // 告警2 labels: {instance: "server-01", alertname: "mem_high"}
   // Group Key: "instance=server-01"
   ```

3. **缓存等待**：同一组的告警进入缓存，等待 `group_wait` 时间

4. **合并发送**：超时后合并为一条 GroupAlert 发送

5. **重复抑制**：已发送的组在 `repeat_interval` 内不再重复发送

**配置示例**：

```json
{
  "name": "instance-group",
  "groupLabels": ["instance", "app"],
  "groupWait": 30,
  "groupInterval": 300,
  "repeatInterval": 3600,
  "enable": true
}
```

### 4.2 告警抑制 (AlarmInhibitReduce)

参考 Prometheus 的抑制机制：

```
┌─────────────────────────────────────────────────────────────────┐
│                      AlarmInhibitReduce                          │
│                       (告警抑制收敛)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  抑制规则 (AlertInhibit)：                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  source_match:              # 源告警匹配条件             │   │
│  │    severity: critical                                   │   │
│  │  target_match:              # 目标告警匹配条件           │   │
│  │    severity: warning                                    │   │
│  │  equal: [instance]          # 必须相同的标签            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  抑制场景示例：                                                   │
│                                                                  │
│  ┌──────────────┐        ┌──────────────┐                      │
│  │ 源告警        │        │ 目标告警      │                      │
│  │              │        │              │                      │
│  │ 磁盘已满      │───────▶│ 磁盘使用率告警 │  ← 被抑制，不发送    │
│  │ severity:    │        │ severity:    │                      │
│  │  critical    │        │  warning     │                      │
│  │ instance:    │        │ instance:    │  (相同实例)          │
│  │  server-01   │        │  server-01   │                      │
│  └──────────────┘        └──────────────┘                      │
│                                                                  │
│  效果：当磁盘已满时，抑制磁盘使用率告警，避免告警风暴              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2.1 告警抑制配置实体 (`AlertInhibit`)

**实体类**: `org.apache.hertzbeat.common.entity.alerter.AlertInhibit`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 抑制规则ID |
| `name` | String | 规则名称 |
| `sourceLabels` | Map<String,String> | 源告警匹配标签 |
| `targetLabels` | Map<String,String> | 目标告警匹配标签 |
| `enable` | boolean | 是否启用 |

#### 4.2.2 抑制机制详解

**抑制判断逻辑**：

```java
// 1. 检查告警是否为源告警
if (isSourceAlert(alert, rule)) {
    cacheSourceAlert(alert, rule);  // 缓存源告警
}

// 2. 检查告警是否为目标告警且被抑制
if (isTargetAlert(alert, rule)) {
    // 检查是否存在匹配的源告警
    Map<String, SourceAlertEntry> sourceAlerts = sourceAlertCache.get(rule.getId());
    for (SourceAlertEntry entry : sourceAlerts.values()) {
        if (entry.isExpired()) continue;
        
        // 检查 equal 标签是否匹配
        if (matchEqualLabels(alert, entry.getAlert(), rule)) {
            return true;  // 被抑制
        }
    }
}
```

**抑制条件**：
1. 存在活跃的源告警（匹配 `sourceLabels`）
2. 当前告警匹配目标条件（`targetLabels`）
3. `equal` 标签的值完全相同

**配置示例**：

```json
{
  "name": "disk-full-inhibit-usage",
  "sourceLabels": {
    "alertname": "disk_full",
    "severity": "critical"
  },
  "targetLabels": {
    "alertname": "disk_high_usage",
    "severity": "warning"
  },
  "equal": ["instance", "mountpoint"],
  "enable": true
}
```

**典型应用场景**：

| 场景 | 源告警 | 目标告警 | Equal 标签 |
|------|--------|----------|------------|
| 磁盘满抑制使用率 | disk_full | disk_high_usage | instance, mountpoint |
| 网络中断抑制主机 | network_down | host_unreachable | instance |
| DB宕机抑制应用 | db_down | app_db_error | db_instance |

### 4.3 告警静默 (AlarmSilenceReduce)

参考 Prometheus 的静默机制：

```
┌─────────────────────────────────────────────────────────────────┐
│                      AlarmSilenceReduce                          │
│                       (告警静默收敛)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  静默规则类型：                                                   │
│                                                                  │
│  1. 一次性静默 (Type = 0)：                                      │
│     • 在指定时间段内静默告警                                      │
│     • 例如：2024-01-01 00:00 到 2024-01-01 06:00                │
│                                                                  │
│  2. 周期性静默 (Type = 1)：                                      │
│     • 按星期几 + 时间段循环静默                                   │
│     • 例如：每周六、周日 00:00-06:00                            │
│                                                                  │
│  静默匹配：                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  • 匹配所有告警 (match_all: true)                        │   │
│  │  • 或按标签匹配 (labels: {app: mysql, severity: warning})│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  静默效果：                                                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │ 告警触发  │───▶│ 检查静默  │───▶│ 静默匹配  │                  │
│  └──────────┘    └──────────┘    └────┬─────┘                  │
│                                       │                        │
│                              ┌────────┴────────┐               │
│                              ▼                 ▼               │
│                         ┌─────────┐      ┌─────────┐          │
│                         │  静默中  │      │ 未静默  │          │
│                         │ 不发送  │      │ 发送通知 │          │
│                         └─────────┘      └─────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.3.1 告警静默配置实体 (`AlertSilence`)

**实体类**: `org.apache.hertzbeat.common.entity.alerter.AlertSilence`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 静默策略ID |
| `name` | String | 策略名称 |
| `enable` | boolean | 是否启用 |
| `matchAll` | boolean | 是否匹配所有告警 |
| `type` | Byte | 静默类型: 0=一次性, 1=周期性 |
| `times` | Integer | 已静默告警次数(统计) |
| `labels` | Map<String,String> | 匹配标签(matchAll=false时使用) |
| `days` | List<Byte> | 周期性静默的星期几(1=周一, 7=周日) |
| `periodStart` | ZonedDateTime | 静默开始时间 |
| `periodEnd` | ZonedDateTime | 静默结束时间 |

#### 4.3.2 静默机制详解

**静默判断逻辑**：

```java
public void silenceAlarm(GroupAlert groupAlert) {
    for (AlertSilence alertSilence : alertSilenceList) {
        // 1. 检查是否匹配静默规则
        boolean match = alertSilence.isMatchAll();
        if (!match) {
            // 按标签匹配
            match = labels.entrySet().stream().anyMatch(item -> 
                alertLabels.containsKey(item.getKey()) && 
                item.getValue().equals(alertLabels.get(item.getKey()))
            );
        }
        
        if (match) {
            LocalDateTime now = LocalDateTime.now();
            
            if (alertSilence.getType() == 0) {
                // 一次性静默
                if (checkTimeRange(now, alertSilence)) {
                    return;  // 被静默，不发送
                }
            } else if (alertSilence.getType() == 1) {
                // 周期性静默
                int currentDayOfWeek = now.getDayOfWeek().getValue();
                if (alertSilence.getDays().contains((byte) currentDayOfWeek) 
                        && checkTimeRange(now, alertSilence)) {
                    return;  // 被静默，不发送
                }
            }
        }
    }
    
    // 未被静默，转发通知
    dispatcherAlarm.dispatchAlarm(groupAlert);
}
```

**配置示例**：

**一次性静默**：
```json
{
  "name": "maintenance-window",
  "type": 0,
  "matchAll": false,
  "labels": {
    "app": "mysql",
    "env": "production"
  },
  "periodStart": "2024-01-15T02:00:00+08:00",
  "periodEnd": "2024-01-15T06:00:00+08:00",
  "enable": true
}
```

**周期性静默**（周末凌晨）：
```json
{
  "name": "weekend-maintenance",
  "type": 1,
  "matchAll": true,
  "days": [6, 7],
  "periodStart": "2024-01-01T00:00:00+08:00",
  "periodEnd": "2024-01-01T06:00:00+08:00",
  "enable": true
}
```

#### 4.3.3 静默与抑制的区别

| 特性 | 告警静默 (Silence) | 告警抑制 (Inhibit) |
|------|-------------------|-------------------|
| **触发方式** | 基于时间配置 | 基于源告警存在 |
| **作用范围** | 所有匹配告警 | 仅目标告警 |
| **使用场景** | 计划内维护窗口 | 根因告警衍生 |
| **配置方式** | 时间段 + 标签 | 源标签 + 目标标签 |
| **时效性** | 预定义时间段 | 实时动态 |
| **典型用途** | 避免维护期间告警轰炸 | 避免重复/冗余告警 |

---

## 5. 告警通知层 (Notice)

### 5.1 通知渠道配置 (NoticeReceiver)

通知渠道配置用于定义告警和系统消息的发送方式。一个通知渠道可以被多个通知规则引用，实现配置的复用。

#### 5.1.1 支持的通知渠道类型

| 类型值 | 名称 | 配置字段 | 说明 |
|-------|------|---------|------|
| **0** | 短信 | sms_provider, sms_access_key, sms_secret_key, sms_sign_name, sms_template_code | 阿里云/腾讯云/华为云短信 |
| **1** | 邮件 | smtp_host, smtp_port, smtp_username, smtp_password, smtp_use_tls, email_from | SMTP 邮件发送 |
| **2** | Webhook | hook_url, hook_method, hook_content_type, hook_auth_type, hook_auth_token | 自定义 Webhook |
| **4** | 企业微信机器人 | wecom_key, wecom_mentioned_mobiles | Webhook 方式 |
| **5** | 钉钉机器人 | dingtalk_access_token, dingtalk_secret, dingtalk_at_mobiles, dingtalk_is_at_all | Webhook + 加签 |
| **6** | 飞书机器人 | feishu_webhook_token, feishu_secret | Webhook + 签名校验 |
| **8** | Slack | slack_webhook_url | Webhook 方式 |
| **9** | Discord | discord_webhook_url | Webhook 方式 |
| **10** | 企业微信应用 | wecom_corp_id, wecom_agent_id, wecom_app_secret, wecom_to_user, wecom_to_party, wecom_to_tag | 应用消息 |
| **11** | 华为云 SMN | smn_ak, smn_sk, smn_project_id, smn_region, smn_topic_urn | 短信/邮件/HTTP |
| **12** | Server酱 | serverchan_send_key | 微信推送 |
| **14** | 飞书应用 | feishu_app_id, feishu_app_secret, feishu_receive_type, feishu_user_id, feishu_chat_id | 应用消息 |

#### 5.1.2 通知渠道配置流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     通知渠道配置流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 选择渠道类型                                                  │
│     ├─ 邮件 (SMTP配置)                                           │
│     ├─ 即时通讯 (钉钉/企业微信/飞书)                               │
│     ├─ Webhook (自定义接口)                                       │
│     └─ 短信 (云服务商)                                            │
│                                                                  │
│  2. 填写配置参数                                                  │
│     ├─ 服务器地址/密钥                                            │
│     ├─ 认证信息 (Token/密钥)                                      │
│     └─ 接收人配置 (@成员/指定用户)                                 │
│                                                                  │
│  3. 测试发送                                                      │
│     └─ 验证配置是否正确                                            │
│                                                                  │
│  4. 启用渠道                                                      │
│     └─ 供通知规则引用                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.1.3 数据库模型 (notice_receivers)

```python
class NoticeReceiver:
    id: int                    # 主键
    name: str                  # 渠道名称
    type: int                  # 渠道类型 (0-14)
    enable: bool               # 是否启用
    description: str           # 描述
    
    # 邮件配置 (type=1)
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    email_from: str
    
    # Webhook配置 (type=2)
    hook_url: str
    hook_method: str          # GET/POST
    hook_content_type: str
    hook_auth_type: str       # None/Bearer/Basic
    hook_auth_token: str
    
    # 企业微信机器人 (type=4)
    wecom_key: str
    wecom_mentioned_mobiles: str
    
    # 钉钉机器人 (type=5)
    dingtalk_access_token: str
    dingtalk_secret: str      # 加签密钥
    dingtalk_at_mobiles: str
    dingtalk_is_at_all: bool
    
    # 飞书机器人 (type=6)
    feishu_webhook_token: str
    feishu_secret: str        # 签名校验密钥
    
    # 企业微信应用 (type=10)
    wecom_corp_id: str
    wecom_agent_id: str
    wecom_app_secret: str
    wecom_to_user: str        # 指定成员
    wecom_to_party: str       # 指定部门
    wecom_to_tag: str         # 指定标签
    
    # 飞书应用 (type=14)
    feishu_app_id: str
    feishu_app_secret: str
    feishu_receive_type: int  # 0-user, 1-chat
    feishu_user_id: str
    feishu_chat_id: str
    
    # 短信配置 (type=0)
    sms_provider: str         # aliyun/tencent/huawei
    sms_access_key: str
    sms_secret_key: str
    sms_sign_name: str
    sms_template_code: str
    
    # 华为云SMN (type=11)
    smn_ak: str
    smn_sk: str
    smn_project_id: str
    smn_region: str
    smn_topic_urn: str
    
    # Server酱 (type=12)
    serverchan_send_key: str
    
    # 审计字段
    creator: str
    modifier: str
    created_at: datetime
    updated_at: datetime
```

### 5.2 通知规则配置 (NoticeRule)

通知规则定义告警触发时的通知方式和条件，通过引用通知渠道来实现告警发送。

#### 5.2.1 通知规则字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| **name** | string | 规则名称 |
| **receiver_channel_id** | int | 关联的通知渠道ID |
| **notify_times** | int | 重试次数 |
| **notify_scale** | string | 发送规模: single(单条)/batch(批量) |
| **filter_all** | bool | 是否转发所有告警 |
| **labels** | dict | 标签过滤条件 {"severity": "critical"} |
| **days** | list | 生效星期 [1,2,3,4,5,6,7] |
| **period_start** | string | 生效时间开始 HH:MM:SS |
| **period_end** | string | 生效时间结束 HH:MM:SS |
| **enable** | bool | 是否启用 |

#### 5.2.2 通知规则配置流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     通知规则配置流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 基本信息                                                      │
│     ├─ 规则名称 (如：生产环境告警通知)                             │
│     └─ 选择通知渠道 (从已配置渠道中选择)                            │
│                                                                  │
│  2. 发送配置                                                      │
│     ├─ 发送规模 (单条/批量)                                       │
│     └─ 重试次数 (1-5次)                                          │
│                                                                  │
│  3. 告警过滤                                                      │
│     ├─ 全部告警 / 按标签过滤                                       │
│     └─ 标签条件 (severity=critical, app=nginx)                    │
│                                                                  │
│  4. 生效时间                                                      │
│     ├─ 生效星期 (周一至周日)                                       │
│     └─ 时间段 (如 09:00-18:00)                                    │
│                                                                  │
│  5. 启用规则                                                      │
│     └─ 匹配告警将通过指定渠道发送                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2.3 数据库模型 (notice_rules)

```python
class NoticeRule:
    id: int
    name: str
    receiver_channel_id: int    # 外键 -> notice_receivers.id
    receiver_name: str          # 冗余存储，用于显示
    receiver_type: int          # 冗余存储，用于显示
    notify_times: int
    notify_scale: str           # single/batch
    template_id: int            # 关联通知模板
    filter_all: bool
    labels_json: str            # JSON格式标签过滤
    days_json: str              # JSON格式生效星期
    period_start: str
    period_end: str
    enable: bool
    creator: str
    modifier: str
    created_at: datetime
    updated_at: datetime
```

### 5.3 通知流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      AlertNoticeDispatch                         │
│                        (告警通知分发)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  通知流程：                                                       │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ 告警收敛  │───▶│ 通知规则  │───▶│ 通知模板  │───▶│ 渠道发送  │  │
│  │ 完成     │    │ 匹配     │    │ 渲染     │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                       │                                         │
│                       ▼                                         │
│              ┌─────────────────┐                               │
│              │  NoticeRule     │                               │
│              │  (通知规则)      │                               │
│              │                 │                               │
│              │ • 匹配标签      │                               │
│              │ • 接收人列表    │                               │
│              │ • 通知方式      │                               │
│              │ • 优先级过滤    │                               │
│              └─────────────────┘                               │
│                                                                  │
│  模板渲染：                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  模板变量：                                               │   │
│  │  • ${alertName}     - 告警名称                           │   │
│  │  • ${priority}      - 告警级别                           │   │
│  │  • ${content}       - 告警内容                           │   │
│  │  • ${time}          - 触发时间                           │   │
│  │  • ${labels.app}    - 应用标签                           │   │
│  │  • ${labels.instance} - 实例标签                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  发送策略：                                                       │
│  • 异步发送：使用 notifyExecutor 线程池                          │
│  • 失败重试：支持配置重试次数                                     │
│  • 限流控制：防止通知风暴                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 通知模板示例

**邮件模板**：
```html
<h2>告警通知</h2>
<p><strong>告警名称：</strong>${alertName}</p>
<p><strong>告警级别：</strong>${priority}</p>
<p><strong>触发时间：</strong>${time}</p>
<p><strong>告警内容：</strong>${content}</p>
<hr>
<p><strong>标签：</strong></p>
<ul>
  <li>应用：${labels.app}</li>
  <li>实例：${labels.instance}</li>
  <li>指标：${labels.metrics}</li>
</ul>
```

**钉钉机器人模板**：
```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "告警通知",
    "text": "## ${alertName}\n**级别：**${priority}\n**时间：**${time}\n**内容：**${content}"
  }
}
```

---

## 6. 外部告警接入

### 6.1 支持的外部告警源

```
┌─────────────────────────────────────────────────────────────────┐
│                      外部告警接入层                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ Prometheus  │  │  Zabbix     │  │ SkyWalking  │  │ 更多... │ │
│  │ Alertmanager│  │             │  │             │  │        │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬────┘ │
│         │                │                │             │      │
│         └────────────────┴────────────────┴─────────────┘      │
│                              │                                  │
│                              ▼                                  │
│              ┌─────────────────────────────┐                   │
│              │   ExternAlertService        │                   │
│              │   (外部告警服务接口)          │                   │
│              └─────────────────────────────┘                   │
│                              │                                  │
│                              ▼                                  │
│              ┌─────────────────────────────┐                   │
│              │   AlarmCommonReduce         │                   │
│              │   (统一进入告警收敛流程)      │                   │
│              └─────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Prometheus Alertmanager 接入

```java
// Prometheus 告警格式转换
public class PrometheusExternAlertService implements ExternAlertService {
    
    @Override
    public void addExternAlerts(String content) {
        // 解析 Prometheus alert webhook JSON
        PrometheusExternAlert alert = JsonUtil.fromJson(content, PrometheusExternAlert.class);
        
        // 转换为 HertzBeat SingleAlert
        for (PrometheusAlert promAlert : alert.getAlerts()) {
            SingleAlert singleAlert = convertToSingleAlert(promAlert);
            alarmCommonReduce.reduceAndSendAlarm(singleAlert);
        }
    }
}
```

**Prometheus Webhook 配置**：
```yaml
# alertmanager.yml
receivers:
  - name: 'hertzbeat'
    webhook_configs:
      - url: 'http://hertzbeat:1157/api/alerts/prometheus'
        send_resolved: true
```

---

## 7. 线程池设计

### 7.1 AlerterWorkerPool

```
┌─────────────────────────────────────────────────────────────────┐
│                      AlerterWorkerPool                           │
│                      (告警模块线程池)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  workerExecutor (告警计算线程池)                         │   │
│  │  • 核心线程：10                                          │   │
│  │  • 最大线程：10                                          │   │
│  │  • 用途：实时告警计算、周期告警计算                       │   │
│  │  • 线程名：alerter-worker-%d                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  notifyExecutor (通知发送线程池)                         │   │
│  │  • 核心线程：6                                           │   │
│  │  • 最大线程：6                                           │   │
│  │  • 用途：异步发送告警通知                                 │   │
│  │  • 线程名：notify-worker-%d                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  logWorkerExecutor (日志告警线程池)                      │   │
│  │  • 用途：处理日志告警计算                                 │   │
│  │  • 线程名：log-worker-%d                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  reduceWorkerExecutor (收敛处理线程池)                   │   │
│  │  • 核心线程：2                                           │   │
│  │  • 最大线程：2                                           │   │
│  │  • 用途：告警收敛处理                                     │   │
│  │  • 线程名：alerter-reduce-worker-%d                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. 数据模型

### 8.1 核心实体关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据模型关系                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐│
│  │ AlertDefine  │1────N │ AlertDefine  │N────1 │   Monitor    ││
│  │  (告警规则)   │       │   Bind       │       │  (监控对象)   ││
│  │              │       │  (绑定关系)   │       │              ││
│  │ • expr       │       │              │       │              ││
│  │ • priority   │       │              │       │              ││
│  │ • labels     │       │              │       │              ││
│  └──────────────┘       └──────────────┘       └──────────────┘│
│                                                                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐│
│  │ SingleAlert  │N────1 │  GroupAlert  │1────N │ NoticeRule   ││
│  │  (单条告警)   │       │  (告警组)     │       │  (通知规则)   ││
│  │              │       │              │       │              ││
│  │ • labels     │       │ • groupLabels│       │ • receiver   ││
│  │ • status     │       │ • status     │       │ • filter     ││
│  │ • fingerprint│       │ • alerts     │       │ • priority   ││
│  └──────────────┘       └──────────────┘       └──────────────┘│
│                                                                  │
│  ┌──────────────┐       ┌──────────────┐                       │
│  │NoticeReceiver│1────N │ NoticeRule   │                       │
│  │  (通知接收人) │       │              │                       │
│  │              │       │              │                       │
│  │ • type       │       │              │                       │
│  │ • email      │       │              │                       │
│  │ • phone      │       │              │                       │
│  └──────────────┘       └──────────────┘                       │
│                                                                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐│
│  │AlertSilence  │       │AlertInhibit  │       │AlertGroup    ││
│  │  (静默规则)   │       │  (抑制规则)   │       │  Converge    ││
│  │              │       │              │       │  (分组规则)   ││
│  └──────────────┘       └──────────────┘       └──────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 告警状态流转

```
┌─────────────────────────────────────────────────────────────────┐
│                       告警状态流转                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                         ┌──────────┐                           │
│                         │  触发    │                           │
│                         │ Trigger  │                           │
│                         └────┬─────┘                           │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐        │
│  │  恢复    │◀────────│  触发中  │────────▶│  静默中  │        │
│  │Resolved  │         │ Firing   │         │ Silenced │        │
│  └──────────┘         └────┬─────┘         └──────────┘        │
│                            │                                    │
│                            ▼                                    │
│                      ┌──────────┐                              │
│                      │  抑制中  │                              │
│                      │Inhibited │                              │
│                      └──────────┘                              │
│                                                                  │
│  状态说明：                                                       │
│  • PENDING：待触发（满足条件但持续时间不足）                      │
│  • FIRING：触发中（满足条件且持续时间足够）                       │
│  • RESOLVED：已恢复（不再满足条件）                              │
│  • SILENCED：静默中（匹配静默规则）                              │
│  • INHIBITED：抑制中（被其他告警抑制）                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 配置说明

### 9.1 告警模块配置

```yaml
# application.yml
alerter:
  # 告警评估间隔（秒）
  eval-interval: 60
  
  # 告警抑制配置
  inhibit:
    # 源告警 TTL（毫秒）
    source-ttl: 14400000  # 4小时
  
  # 告警缓存配置
  cache:
    # 触发中告警缓存大小
    firing-capacity: 10000
    # 待触发告警缓存大小
    pending-capacity: 5000
```

### 9.2 告警规则示例

```yaml
# 告警规则定义示例
alertDefine:
  name: "MySQL连接数过高"
  type: 0  # 0: 实时告警, 1: 周期告警
  expr: "connections > 80"
  priority: 1  # 0: 紧急, 1: 严重, 2: 警告
  times: 3  # 连续触发次数
  enable: true
  labels:
    app: mysql
    category: database
  annotations:
    summary: "MySQL连接数超过阈值"
    description: "当前连接数: ${connections}"
```

---

## 10. 总结

| 模块 | 核心技术 | 职责 |
|------|----------|------|
| **实时告警计算** | JEXL 表达式 + 队列消费 | 基于实时采集数据计算告警 |
| **周期告警计算** | SQL/PromQL + 定时调度 | 基于时序数据库计算告警 |
| **告警收敛** | 分组 + 抑制 + 静默 | 告警降噪，防止告警风暴 |
| **告警通知** | 多线程 + 模板渲染 | 多渠道告警通知 |
| **外部告警** | Webhook + 格式转换 | 接入第三方告警系统 |
| **线程池** | ThreadPoolExecutor | 异步处理，提升性能 |

### 核心设计思想

1. **分层架构**：计算层 → 收敛层 → 通知层，职责清晰
2. **异步处理**：全链路异步，不阻塞采集流程
3. **告警降噪**：分组、抑制、静默三层收敛机制
4. **可扩展性**：SPI 机制支持自定义通知渠道
5. **兼容性**：支持 Prometheus、Zabbix 等外部告警接入

HertzBeat Alerter 参考 Prometheus Alertmanager 设计，实现了完整的告警生命周期管理，是一个功能丰富、可扩展的告警模块。
