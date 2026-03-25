# Web 服务器模板迁移 SOP（Tomcat / Jetty）

## 1. 目标

将 HertzBeat 的 `Tomcat`、`Jetty` 模板迁移到当前系统，并以 `Jolokia/HTTP` 方式落地可采集链路。

## 2. 范围

- `tomcat`
- `jetty`

## 3. 流程

1. 复制源模板  
   来源目录：`hertzbeat-master/hertzbeat-manager/src/main/resources/define`
2. 应用 override  
   覆盖目录：`backend/template_overrides/app-tomcat.yml`、`backend/template_overrides/app-jetty.yml`
3. 注入默认告警策略  
   规则来源：`backend/scripts/apply_webserver_default_alerts.py`
4. Upsert 到 `monitor_templates`  
   同步脚本：`backend/scripts/sync_hertzbeat_webserver_templates.py`

## 4. 设计约束

- 不直接依赖 Go 侧 `jmx` 协议（当前未实现）
- 使用 `http + jsonPath` 采集 Jolokia `read` 返回
- 模板字段、collector 可采指标、默认策略三者必须一致

## 5. 命令

```bash
cd backend
PYTHONPATH=. python3 scripts/sync_hertzbeat_webserver_templates.py
```

## 6. 验收

1. 模板中心出现 `Tomcat`、`Jetty`
2. 分类树有 `webserver` 分类
3. 默认策略页可见并能应用
4. 采集任务有 `jvm_basic / thread_pool / memory / gc` 数据
