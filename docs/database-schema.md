# IT Ops Platform 数据库表结构文档

> 数据库类型: SQLite
> 数据库文件: `backend/instance/it_ops.db`
> 生成时间: 2026-03-13

## 目录

1. [用户与权限](#1-用户与权限)
2. [CMDB 配置管理](#2-cmdb-配置管理)
3. [监控管理](#3-监控管理)
4. [告警管理](#4-告警管理)
5. [通知管理](#5-通知管理)
6. [任务与触发器](#6-任务与触发器)
7. [系统配置](#7-系统配置)
8. [其他表](#8-其他表)

---

## 1. 用户与权限

### 1.1 users - 用户表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| username | VARCHAR(80) | 用户名 |
| password_hash | VARCHAR(255) | 密码哈希 |
| email | VARCHAR(120) | 邮箱 |
| phone | VARCHAR(20) | 电话 |
| role | VARCHAR(20) | 角色 |
| status | VARCHAR(20) | 状态 |
| department_id | INTEGER | 部门ID |
| last_login | DATETIME | 最后登录时间 |
| login_failures | INTEGER | 登录失败次数 |
| locked_until | DATETIME | 锁定截止时间 |
| password_changed_at | DATETIME | 密码修改时间 |
| creator | VARCHAR(100) | 创建者 |
| modifier | VARCHAR(100) | 修改者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 1.2 roles - 角色表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(80) | 角色名称 |
| code | VARCHAR(50) | 角色代码 |
| description | VARCHAR(255) | 描述 |
| status | VARCHAR(20) | 状态 |
| menu_permissions | TEXT | 菜单权限(JSON) |
| data_permissions | TEXT | 数据权限(JSON) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 1.3 user_roles - 用户角色关联表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| user_id | INTEGER | 用户ID |
| role_id | INTEGER | 角色ID |

### 1.4 departments - 部门表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 部门名称 |
| code | VARCHAR(50) | 部门代码 |
| parent_id | INTEGER | 父部门ID |
| description | VARCHAR(255) | 描述 |
| sort_order | INTEGER | 排序 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 1.5 department_users - 部门用户关联表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| department_id | INTEGER | 部门ID |
| user_id | INTEGER | 用户ID |

### 1.6 department_roles - 部门角色关联表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| department_id | INTEGER | 部门ID |
| role_id | INTEGER | 角色ID |

### 1.7 password_histories - 密码历史表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户ID |
| password_hash | VARCHAR(255) | 密码哈希 |
| created_at | DATETIME | 创建时间 |

---

## 2. CMDB 配置管理

### 2.1 cmdb_models - CMDB模型表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 模型名称 |
| code | VARCHAR(50) | 模型代码 |
| icon | VARCHAR(100) | 图标 |
| category_id | INTEGER | 分类ID |
| model_type_id | INTEGER | 模型类型ID |
| description | VARCHAR(500) | 描述 |
| config | TEXT | 配置(JSON) |
| form_config | TEXT | 表单配置(JSON) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| created_by | VARCHAR(100) | 创建者 |

### 2.2 model_categories - 模型分类表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 分类名称 |
| code | VARCHAR(50) | 分类代码 |
| icon | VARCHAR(100) | 图标 |
| sort_order | INTEGER | 排序 |
| parent_id | INTEGER | 父分类ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.3 model_types - 模型类型表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 类型名称 |
| code | VARCHAR(50) | 类型代码 |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.4 model_fields - 模型字段表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| model_id | INTEGER | 模型ID |
| name | VARCHAR(100) | 字段名称 |
| code | VARCHAR(50) | 字段代码 |
| field_type | VARCHAR(50) | 字段类型 |
| required | BOOLEAN | 是否必填 |
| unique | BOOLEAN | 是否唯一 |
| default_value | VARCHAR(255) | 默认值 |
| options | TEXT | 选项(JSON) |
| sort_order | INTEGER | 排序 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.5 model_regions - 区域表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 区域名称 |
| code | VARCHAR(50) | 区域代码 |
| parent_id | INTEGER | 父区域ID |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.6 ci_instances - CI实例表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| model_id | INTEGER | 模型ID |
| name | VARCHAR(100) | 实例名称 |
| code | VARCHAR(50) | 实例代码 |
| data | TEXT | 数据(JSON) |
| region_id | INTEGER | 区域ID |
| status | VARCHAR(20) | 状态 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| created_by | VARCHAR(100) | 创建者 |

### 2.7 ci_history - CI变更历史表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| ci_id | INTEGER | CI实例ID |
| operation | VARCHAR(20) | 操作类型 |
| old_data | TEXT | 旧数据(JSON) |
| new_data | TEXT | 新数据(JSON) |
| operator | VARCHAR(100) | 操作人 |
| created_at | DATETIME | 创建时间 |

### 2.8 cmdb_relations - CMDB关系表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| source_ci_id | INTEGER | 源CI ID |
| target_ci_id | INTEGER | 目标CI ID |
| relation_type_id | INTEGER | 关系类型ID |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.9 relation_types - 关系类型表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 类型名称 |
| code | VARCHAR(50) | 类型代码 |
| source_model_id | INTEGER | 源模型ID |
| target_model_id | INTEGER | 目标模型ID |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.10 cmdb_dict_types - 字典类型表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 类型名称 |
| code | VARCHAR(50) | 类型代码 |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 2.11 cmdb_dict_items - 字典项表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| dict_type_id | INTEGER | 字典类型ID |
| name | VARCHAR(100) | 项名称 |
| value | VARCHAR(100) | 项值 |
| sort_order | INTEGER | 排序 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 3. 监控管理

### 3.1 monitors - 监控任务表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| job_id | VARCHAR(100) | 任务标识 |
| name | VARCHAR(100) | 任务名称 |
| app | VARCHAR(50) | 应用类型 |
| target | VARCHAR(255) | 监控目标 |
| interval | INTEGER | 采集间隔(秒) |
| enabled | BOOLEAN | 是否启用 |
| ci_code | VARCHAR(50) | CI编码 |
| ci_name | VARCHAR(100) | CI名称 |
| params | TEXT | 参数(JSON) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.2 monitor_templates - 监控模板表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| app | VARCHAR(50) | 应用类型 |
| name | VARCHAR(100) | 模板名称 |
| category | VARCHAR(50) | 分类 |
| content | TEXT | 模板内容(YAML) |
| version | INTEGER | 版本 |
| is_hidden | BOOLEAN | 是否隐藏 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.3 monitor_categories - 监控分类表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 分类名称 |
| code | VARCHAR(50) | 分类代码 |
| icon | VARCHAR(100) | 图标 |
| sort_order | INTEGER | 排序 |
| parent_id | INTEGER | 父分类ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.4 monitor_params - 监控参数表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| monitor_id | INTEGER | 监控任务ID |
| field | VARCHAR(100) | 参数字段 |
| value | TEXT | 参数值 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.5 monitor_binds - 监控绑定表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| key_str | VARCHAR(255) | 键值(ip:port) |
| biz_id | BIGINT | 业务ID |
| monitor_id | INTEGER | 监控任务ID |
| creator | VARCHAR(100) | 创建者 |
| modifier | VARCHAR(100) | 修改者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.6 monitor_defines - 监控定义表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| app | VARCHAR(50) | 应用类型 |
| name | VARCHAR(100) | 定义名称 |
| content | TEXT | 定义内容(YAML) |
| version | INTEGER | 版本 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.7 monitor_compile_logs - 编译日志表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| monitor_id | INTEGER | 监控任务ID |
| status | VARCHAR(20) | 状态 |
| message | TEXT | 消息 |
| created_at | DATETIME | 创建时间 |

### 3.8 monitor_view_prefs - 监控视图偏好表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户ID |
| view_type | VARCHAR(50) | 视图类型 |
| config | TEXT | 配置(JSON) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.9 collectors - 采集器表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 采集器名称 |
| code | VARCHAR(50) | 采集器代码 |
| host | VARCHAR(255) | 主机地址 |
| port | INTEGER | 端口 |
| status | VARCHAR(20) | 状态 |
| last_heartbeat | DATETIME | 最后心跳时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 3.10 collector_monitor_binds - 采集器监控绑定表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| collector_id | INTEGER | 采集器ID |
| monitor_id | INTEGER | 监控任务ID |
| created_at | DATETIME | 创建时间 |

### 3.11 metrics_history - 指标历史表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| monitor_id | INTEGER | 监控任务ID |
| metric_name | VARCHAR(100) | 指标名称 |
| value | REAL | 指标值 |
| timestamp | DATETIME | 时间戳 |
| created_at | DATETIME | 创建时间 |

---

## 4. 告警管理

### 4.1 alert_defines - 告警定义表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| app | VARCHAR(50) | 应用类型 |
| name | VARCHAR(100) | 定义名称 |
| expr | TEXT | 告警表达式 |
| severity | VARCHAR(20) | 严重程度 |
| summary | VARCHAR(255) | 摘要 |
| description | TEXT | 描述 |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.2 single_alerts - 单条告警表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| alert_define_id | INTEGER | 告警定义ID |
| monitor_id | INTEGER | 监控任务ID |
| severity | VARCHAR(20) | 严重程度 |
| status | VARCHAR(20) | 状态 |
| summary | VARCHAR(255) | 摘要 |
| description | TEXT | 描述 |
| labels | TEXT | 标签(JSON) |
| value | REAL | 当前值 |
| triggered_at | DATETIME | 触发时间 |
| resolved_at | DATETIME | 恢复时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.3 group_alerts - 分组告警表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| group_key | VARCHAR(255) | 分组键 |
| severity | VARCHAR(20) | 严重程度 |
| status | VARCHAR(20) | 状态 |
| alerts_count | INTEGER | 告警数量 |
| alerts_json | TEXT | 告警列表(JSON) |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.4 alert_history - 告警历史表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| alert_id | INTEGER | 告警ID |
| operation | VARCHAR(20) | 操作类型 |
| operator | VARCHAR(100) | 操作人 |
| comment | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |

### 4.5 alert_groups - 告警分组策略表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 策略名称 |
| group_labels | TEXT | 分组标签(JSON) |
| group_wait | INTEGER | 分组等待时间(秒) |
| group_interval | INTEGER | 分组间隔(秒) |
| repeat_interval | INTEGER | 重复间隔(秒) |
| match_all | BOOLEAN | 匹配所有 |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.6 alert_inhibits - 告警抑制规则表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 规则名称 |
| source_labels | TEXT | 源标签(JSON) |
| target_labels | TEXT | 目标标签(JSON) |
| equal_labels | TEXT | 相等标签(JSON) |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.7 alert_silences - 告警静默规则表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 规则名称 |
| matchers | TEXT | 匹配条件(JSON) |
| starts_at | DATETIME | 开始时间 |
| ends_at | DATETIME | 结束时间 |
| comment | TEXT | 备注 |
| created_by | VARCHAR(100) | 创建者 |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.8 alert_integrations - 告警集成表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 集成名称 |
| source_type | VARCHAR(50) | 源类型 |
| config | TEXT | 配置(JSON) |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.9 alert_labels - 告警标签表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| alert_id | INTEGER | 告警ID |
| key | VARCHAR(100) | 标签键 |
| value | VARCHAR(255) | 标签值 |
| created_at | DATETIME | 创建时间 |

---

## 5. 通知管理

### 5.1 notifications - 通知表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| type_id | INTEGER | 通知类型ID |
| title | VARCHAR(255) | 标题 |
| content | TEXT | 内容 |
| priority | VARCHAR(20) | 优先级 |
| status | VARCHAR(20) | 状态 |
| source_type | VARCHAR(50) | 源类型 |
| source_id | INTEGER | 源ID |
| is_read | BOOLEAN | 是否已读 |
| read_at | DATETIME | 读取时间 |
| is_archived | BOOLEAN | 是否归档 |
| archived_at | DATETIME | 归档时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.2 notification_types - 通知类型表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(50) | 类型名称 |
| description | VARCHAR(255) | 描述 |
| icon | VARCHAR(100) | 图标 |
| color | VARCHAR(20) | 颜色 |
| is_system | BOOLEAN | 是否系统类型 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.3 notification_templates - 通知模板表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 模板名称 |
| type | VARCHAR(50) | 模板类型 |
| subject | VARCHAR(255) | 主题 |
| content | TEXT | 内容 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.4 notification_recipients - 通知接收人表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| notification_id | INTEGER | 通知ID |
| user_id | INTEGER | 用户ID |
| channel | VARCHAR(50) | 渠道 |
| status | VARCHAR(20) | 状态 |
| sent_at | DATETIME | 发送时间 |
| error_msg | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |

### 5.5 notification_attachments - 通知附件表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| notification_id | INTEGER | 通知ID |
| file_name | VARCHAR(255) | 文件名 |
| file_path | VARCHAR(500) | 文件路径 |
| file_size | INTEGER | 文件大小 |
| created_at | DATETIME | 创建时间 |

### 5.6 notice_receivers - 通知接收渠道表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 渠道名称 |
| channel | VARCHAR(50) | 渠道类型 |
| config | TEXT | 配置(JSON) |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.7 notice_rules - 通知规则表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 规则名称 |
| receiver_channel_id | INTEGER | 接收渠道ID |
| receiver_name | VARCHAR(100) | 接收人名称 |
| receiver_type | INTEGER | 接收人类型 |
| notify_times | INTEGER | 通知次数 |
| notify_scale | VARCHAR(20) | 通知范围 |
| template_id | INTEGER | 模板ID |
| template_name | VARCHAR(100) | 模板名称 |
| filter_all | BOOLEAN | 是否过滤所有 |
| labels_json | TEXT | 标签(JSON) |
| days_json | TEXT | 日期(JSON) |
| period_start | VARCHAR(8) | 时段开始 |
| period_end | VARCHAR(8) | 时段结束 |
| enable | BOOLEAN | 是否启用 |
| creator | VARCHAR(100) | 创建者 |
| modifier | VARCHAR(100) | 修改者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| recipient_type | VARCHAR(20) | 接收者类型 |
| recipient_ids_json | TEXT | 接收者ID列表(JSON) |
| include_sub_departments | BOOLEAN | 是否包含子部门 |

### 5.8 notice_templates - 通知模板表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 模板名称 |
| type | VARCHAR(50) | 类型 |
| content | TEXT | 内容 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 5.9 alert_notifications - 告警通知记录表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| alert_id | INTEGER | 告警ID |
| channel | VARCHAR(50) | 通知渠道 |
| status | VARCHAR(20) | 状态 |
| content | TEXT | 内容 |
| sent_at | DATETIME | 发送时间 |
| error_msg | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |

---

## 6. 任务与触发器

### 6.1 batch_scan_tasks - 批量扫描任务表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 任务名称 |
| task_type | VARCHAR(50) | 任务类型 |
| status | VARCHAR(20) | 状态 |
| total_count | INTEGER | 总数 |
| success_count | INTEGER | 成功数 |
| fail_count | INTEGER | 失败数 |
| params | TEXT | 参数(JSON) |
| result | TEXT | 结果(JSON) |
| started_at | DATETIME | 开始时间 |
| completed_at | DATETIME | 完成时间 |
| created_by | VARCHAR(100) | 创建者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 6.2 relation_triggers - 关系触发器表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 触发器名称 |
| source_model_id | INTEGER | 源模型ID |
| target_model_id | INTEGER | 目标模型ID |
| trigger_type | VARCHAR(50) | 触发器类型 |
| condition | TEXT | 条件 |
| action | TEXT | 动作 |
| enabled | BOOLEAN | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 6.3 trigger_execution_logs - 触发器执行日志表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| trigger_id | INTEGER | 触发器ID |
| source_ci_id | INTEGER | 源CI ID |
| target_ci_id | INTEGER | 目标CI ID |
| status | VARCHAR(20) | 状态 |
| message | TEXT | 消息 |
| created_at | DATETIME | 创建时间 |

---

## 7. 系统配置

### 7.1 system_configs - 系统配置表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| key | VARCHAR(100) | 配置键 |
| value | TEXT | 配置值 |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 7.2 operation_logs - 操作日志表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户ID |
| username | VARCHAR(80) | 用户名 |
| operation | VARCHAR(50) | 操作类型 |
| resource_type | VARCHAR(50) | 资源类型 |
| resource_id | VARCHAR(100) | 资源ID |
| resource_name | VARCHAR(255) | 资源名称 |
| detail | TEXT | 详情(JSON) |
| ip_address | VARCHAR(50) | IP地址 |
| user_agent | VARCHAR(500) | 用户代理 |
| created_at | DATETIME | 创建时间 |

### 7.3 code_sequences - 编码序列表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| code_type | VARCHAR(50) | 编码类型 |
| prefix | VARCHAR(20) | 前缀 |
| current_value | INTEGER | 当前值 |
| length | INTEGER | 长度 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 8. 其他表

### 8.1 tags - 标签表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 标签名称 |
| tag_value | VARCHAR(2048) | 标签值 |
| description | VARCHAR(500) | 描述 |
| type | SMALLINT | 类型(0-Auto, 1-User, 2-System) |
| creator | VARCHAR(100) | 创建者 |
| modifier | VARCHAR(100) | 修改者 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.2 custom_views - 自定义视图表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 视图名称 |
| type | VARCHAR(50) | 视图类型 |
| config | TEXT | 配置(JSON) |
| is_default | BOOLEAN | 是否默认 |
| is_shared | BOOLEAN | 是否共享 |
| created_by | INTEGER | 创建者ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.3 custom_view_nodes - 自定义视图节点表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| view_id | INTEGER | 视图ID |
| parent_id | INTEGER | 父节点ID |
| name | VARCHAR(100) | 节点名称 |
| node_type | VARCHAR(50) | 节点类型 |
| config | TEXT | 配置(JSON) |
| sort_order | INTEGER | 排序 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.4 custom_view_node_permissions - 视图节点权限表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| node_id | INTEGER | 节点ID |
| user_id | INTEGER | 用户ID |
| permission | VARCHAR(50) | 权限 |
| created_at | DATETIME | 创建时间 |

### 8.5 status_page_orgs - 状态页组织表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(100) | 组织名称 |
| slug | VARCHAR(50) | 标识 |
| description | VARCHAR(255) | 描述 |
| logo | VARCHAR(255) | Logo |
| theme | VARCHAR(50) | 主题 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.6 status_page_components - 状态页组件表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| org_id | INTEGER | 组织ID |
| name | VARCHAR(100) | 组件名称 |
| description | VARCHAR(255) | 描述 |
| status | VARCHAR(20) | 状态 |
| monitor_ids | TEXT | 监控ID列表(JSON) |
| sort_order | INTEGER | 排序 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.7 status_page_incidents - 状态页事件表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| org_id | INTEGER | 组织ID |
| title | VARCHAR(255) | 标题 |
| description | TEXT | 描述 |
| status | VARCHAR(20) | 状态 |
| impact | VARCHAR(20) | 影响范围 |
| started_at | DATETIME | 开始时间 |
| resolved_at | DATETIME | 解决时间 |
| created_by | INTEGER | 创建者ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 8.8 alembic_version - 数据库版本表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| version_num | VARCHAR(32) | 版本号 |

---

## 统计信息

| 类别 | 表数量 |
|------|--------|
| 用户与权限 | 7 |
| CMDB 配置管理 | 11 |
| 监控管理 | 11 |
| 告警管理 | 9 |
| 通知管理 | 9 |
| 任务与触发器 | 3 |
| 系统配置 | 3 |
| 其他 | 8 |
| **总计** | **61** |

---

## 备注

1. 所有表都包含 `created_at` 和 `updated_at` 字段用于记录时间
2. JSON 类型的字段存储为 TEXT 格式
3. 布尔类型使用 INTEGER (0/1) 存储
4. 外键约束在 SQLite 中需要手动启用 `PRAGMA foreign_keys = ON;`
