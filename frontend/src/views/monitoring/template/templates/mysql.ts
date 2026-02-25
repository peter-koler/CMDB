// HertzBeat MySQL 模板
export const mysqlTemplate = `# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The monitoring type category：service-application service monitoring db-database monitoring custom-custom monitoring os-operating system monitoring
category: db
# The monitoring type eg: linux windows tomcat mysql aws...
app: mysql
# The monitoring i18n name
name:
  zh-CN: Mysql数据库
  en-US: Mysql DB
# The description and help of this monitoring type
help:
  zh-CN: HertzBeat 使用 JDBC 协议通过配置 SQL 对 Mysql 数据库的通用性能指标(系统信息、性能状态、Innodb、缓存、事物、用户线程、慢SQL等)进行采集监控，支持版本为 Mysql5+。
  en-US: HertzBeat uses JDBC Protocol to collect general performance metrics of MySQL databases by configuring SQL. Supported versions include MySQL 5.0 and above.
helpLink:
  zh-CN: https://hertzbeat.apache.org/zh-cn/docs/help/mysql
  en-US: https://hertzbeat.apache.org/docs/help/mysql

# Input params define for monitoring(render web ui by the definition)
params:
  - field: host
    name:
      zh-CN: 目标Host
      en-US: Target Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: 端口
      en-US: Port
    type: number
    range: '[0,65535]'
    required: true
    defaultValue: 3306
  - field: timeout
    name:
      zh-CN: 查询超时时间(ms)
      en-US: Query Timeout(ms)
    type: number
    range: '[400,200000]'
    required: false
    hide: true
    defaultValue: 6000
  - field: database
    name:
      zh-CN: 数据库名称
      en-US: Database Name
    type: text
    required: false
  - field: username
    name:
      zh-CN: 用户名
      en-US: Username
    type: text
    limit: 50
    required: false
  - field: password
    name:
      zh-CN: 密码
      en-US: Password
    type: password
    required: false
  - field: url
    name:
      zh-CN: URL
      en-US: URL
    type: text
    required: false
    hide: true

# collect metrics config list
metrics:
  # metrics - basic
  - name: basic
    priority: 0
    i18n:
      zh-CN: 基础信息
      en-US: Basic Info
    fields:
      - field: version
        type: 1
        i18n:
          zh-CN: 版本
          en-US: Version
      - field: port
        type: 1
        i18n:
          zh-CN: 端口
          en-US: Port
      - field: datadir
        type: 1
        i18n:
          zh-CN: 存储目录
          en-US: Data Directory
      - field: max_connections
        type: 0
        i18n:
          zh-CN: 最大连接数
          en-US: Max Connections
      - field: thread_cache_size
        type: 0
        i18n:
          zh-CN: 连接池大小
          en-US: Thread Cache Size
      - field: innodb_buffer_pool_size
        type: 0
        unit: KB
        i18n:
          zh-CN: InnoDB缓冲池的大小
          en-US: Innodb Buffer Pool Size
    aliasFields:
      - version
      - version_compile_os
      - version_compile_machine
      - port
      - datadir
      - max_connections
      - thread_cache_size
      - table_open_cache
      - innodb_buffer_pool_size
    calculates:
      - port=port
      - datadir=datadir
      - max_connections=max_connections
      - version=version+"_"+version_compile_os+"_"+version_compile_machine
    units:
      - innodb_buffer_pool_size=B->KB
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global variables where Variable_name like 'version%' or Variable_name = 'max_connections' or Variable_name = 'datadir' or Variable_name = 'port' or Variable_name = 'thread_cache_size' or Variable_name = 'table_open_cache' or Variable_name = 'innodb_buffer_pool_size';

  - name: cache
    priority: 1
    i18n:
      zh-CN: 缓存信息
      en-US: Cache Info
    fields:
      - field: query_cache_hit_rate
        type: 0
        unit: '%'
        i18n:
          zh-CN: 缓存命中率
          en-US: Query Cache Hit Rate
      - field: cache_hits
        type: 0
        i18n:
          zh-CN: 缓存命中数
          en-US: Cache Hits
      - field: cache_inserts
        type: 0
        i18n:
          zh-CN: 缓存插入数
          en-US: Cache Inserts
      - field: cache_free_blocks
        type: 0
        i18n:
          zh-CN: 缓存空闲块数量
          en-US: Cache Free Blocks
      - field: cache_free_memory
        type: 0
        unit: KB
        i18n:
          zh-CN: 空闲缓存大小
          en-US: Cache Free Memory
    aliasFields:
      - Qcache_hits
      - Qcache_inserts
      - Qcache_free_blocks
      - Qcache_free_memory
    calculates:
      - query_cache_hit_rate= (Qcache_hits + 1) / (Qcache_hits + Qcache_inserts + 1) * 100
      - cache_hits=Qcache_hits
      - cache_inserts=Qcache_inserts
      - cache_free_blocks=Qcache_free_blocks
      - cache_free_memory=Qcache_free_memory
    units:
      - cache_free_memory=B->KB
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global status like 'QCache%';

  - name: performance
    priority: 2
    i18n:
      zh-CN: 性能信息
      en-US: Performance Info
    fields:
      - field: questions
        type: 0
        i18n:
          zh-CN: 查询总数
          en-US: Questions
      - field: qps
        type: 0
        i18n:
          zh-CN: 每秒处理查询数
          en-US: Queries Per Second
    aliasFields:
      - uptime
      - questions
    calculates:
      - qps=uptime / questions
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global status where Variable_name = 'questions' or Variable_name = 'uptime';

  - name: innodb
    priority: 3
    i18n:
      zh-CN: Innodb信息
      en-US: Innodb Info
    fields:
      - field: innodb_data_reads
        type: 0
        unit: Times
        i18n:
          zh-CN: 磁盘读取次数
          en-US: Innodb Data Reads
      - field: innodb_data_writes
        type: 0
        unit: Times
        i18n:
          zh-CN: 磁盘写入次数
          en-US: Innodb Data Writes
      - field: innodb_data_read
        type: 0
        unit: KB
        i18n:
          zh-CN: 磁盘读取数据量
          en-US: Innodb Data Read
      - field: innodb_data_written
        type: 0
        unit: KB
        i18n:
          zh-CN: 磁盘写入数据量
          en-US: Innodb Data Written
      - field: innodb_buffer_hit_rate
        type: 0
        unit: '%'
        i18n:
          zh-CN: Innodb 缓存命中数
          en-US: Innodb Buffer Hit Rate
    aliasFields:
      - Innodb_data_reads
      - Innodb_data_writes
      - Innodb_data_read
      - Innodb_data_written
      - Innodb_buffer_pool_read_requests
      - Innodb_buffer_pool_read_ahead
      - Innodb_buffer_pool_reads
    calculates:
      - innodb_buffer_hit_rate= (Innodb_buffer_pool_read_requests + 1) / (Innodb_buffer_pool_read_requests + Innodb_buffer_pool_read_ahead + Innodb_buffer_pool_reads + 1) * 100
      - innodb_data_reads=Innodb_data_reads
      - innodb_data_writes=Innodb_data_writes
      - innodb_data_read=Innodb_data_read
      - innodb_data_written=Innodb_data_written
    units:
      - innodb_data_read=B->KB
      - innodb_data_written=B->KB
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global status where Variable_name like 'innodb%';

  - name: status
    priority: 4
    i18n:
      zh-CN: 状态信息
      en-US: Status Info
    fields:
      - field: uptime
        type: 0
        unit: s
        i18n:
          zh-CN: 运行时间
          en-US: Uptime
      - field: com_select
        type: 0
        i18n:
          zh-CN: 查询次数
          en-US: Com Select
      - field: com_insert
        type: 0
        i18n:
          zh-CN: 插入次数
          en-US: Com Insert
      - field: com_update
        type: 0
        i18n:
          zh-CN: 更新次数
          en-US: Com Update
      - field: com_delete
        type: 0
        i18n:
          zh-CN: 删除次数
          en-US: Com Delete
      - field: com_commit
        type: 0
        i18n:
          zh-CN: 事务提交次数
          en-US: Com Commit
      - field: com_rollback
        type: 0
        i18n:
          zh-CN: 事务回滚次数
          en-US: Com Rollback
      - field: threads_created
        type: 0
        i18n:
          zh-CN: 线程创建数
          en-US: Threads Created
      - field: threads_connected
        type: 0
        i18n:
          zh-CN: 连接线程数
          en-US: Threads Connected
      - field: threads_cached
        type: 0
        i18n:
          zh-CN: 缓存线程数
          en-US: Threads Cached
      - field: threads_running
        type: 0
        i18n:
          zh-CN: 活动线程数
          en-US: Threads Running
      - field: qps
        type: 0
        i18n:
          zh-CN: 每秒处理查询数
          en-US: Com Insert
    aliasFields:
      - uptime
      - com_select
      - com_insert
      - com_update
      - com_delete
      - com_commit
      - com_rollback
      - threads_created
      - threads_connected
      - threads_cached
      - threads_running
      - questions
    calculates:
      - qps=uptime / questions
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global status where Variable_name like 'thread%' or Variable_name = 'com_select' or Variable_name = 'com_insert' or Variable_name = 'com_update' or Variable_name = 'com_delete' or Variable_name = 'com_commit' or Variable_name = 'com_rollback' or Variable_name = 'questions' or Variable_name = 'uptime';

  - name: slow_sql
    priority: 13
    i18n:
      zh-CN: 慢查询信息
      en-US: Slow Sql Info
    fields:
      - field: id
        type: 1
        label: true
        i18n:
          zh-CN: ID
          en-US: ID
      - field: sql_text
        type: 1
        i18n:
          zh-CN: SQL 文本
          en-US: SQL Text
      - field: start_time
        type: 1
        i18n:
          zh-CN: 开始时间
          en-US: Start Time
      - field: db
        type: 1
        i18n:
          zh-CN: 数据库
          en-US: Database
      - field: query_time
        type: 3
        i18n:
          zh-CN: 查询时间
          en-US: Query Time
    aliasFields:
      - sql_text
      - start_time
      - db
      - query_time
    calculates:
      - id= start_time + sql_text
    protocol: jdbc
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      platform: mysql
      username: ^_^username^_^
      password: ^_^password^_^
      database: ^_^database^_^
      timeout: ^_^timeout^_^
      queryType: multiRow
      sql: select sql_text, start_time, db, query_time from mysql.slow_log;`
