# 数据库默认监控策略基线（中档）

来源：`backend/scripts/apply_db_default_alerts.py`

> 档位：medium（中档）
> 说明：规则按数据库家族与单库指标特性生成，每库 10 条以上。

## db2
- 规则数：`11`
- `db2_unavailable` | `realtime_metric` | `core` | metric=`db2_server_up` | `== 0` | enabled=`true`
- `db2_tablespace_used_high` | `periodic_metric` | `core` | metric=`used_percentage` | `> 80` | enabled=`true`
- `db2_tablespace_used_critical` | `periodic_metric` | `core` | metric=`used_percentage` | `> 90` | enabled=`true`
- `db2_tablespace_free_low` | `periodic_metric` | `extended` | metric=`free` | `< 10` | enabled=`false`
- `db2_waiting_locks_detected` | `periodic_metric` | `core` | metric=`waiting_locks` | `> 0` | enabled=`true`
- `db2_waiting_locks_critical` | `periodic_metric` | `core` | metric=`waiting_locks` | `> 10` | enabled=`true`
- `db2_process_count_high` | `periodic_metric` | `core` | metric=`process_count` | `> 200` | enabled=`true`
- `db2_process_count_critical` | `periodic_metric` | `extended` | metric=`process_count` | `> 400` | enabled=`false`
- `db2_avg_exec_time_high` | `periodic_metric` | `extended` | metric=`avg_exe_time` | `> 300` | enabled=`false`
- `db2_avg_exec_time_critical` | `periodic_metric` | `extended` | metric=`avg_exe_time` | `> 800` | enabled=`false`
- `db2_status_count_high` | `periodic_metric` | `extended` | metric=`count` | `> 1000` | enabled=`false`

## dm
- 规则数：`11`
- `dm_unavailable` | `realtime_metric` | `core` | metric=`dm_server_up` | `== 0` | enabled=`true`
- `dm_sql_thread_high` | `periodic_metric` | `core` | metric=`dm_sql_thd` | `> 50` | enabled=`true`
- `dm_sql_thread_critical` | `periodic_metric` | `core` | metric=`dm_sql_thd` | `> 80` | enabled=`true`
- `dm_io_thread_high` | `periodic_metric` | `core` | metric=`dm_io_thd` | `> 50` | enabled=`true`
- `dm_io_thread_critical` | `periodic_metric` | `core` | metric=`dm_io_thd` | `> 80` | enabled=`true`
- `dm_quit_thread_detected` | `realtime_metric` | `core` | metric=`dm_quit_thd` | `> 0` | enabled=`true`
- `dm_thread_sum_high` | `periodic_metric` | `extended` | metric=`dm_sql_thd` | `> 120` | enabled=`false`
- `dm_thread_sum_critical` | `periodic_metric` | `extended` | metric=`dm_sql_thd` | `> 180` | enabled=`false`
- `dm_sql_thread_util_high` | `periodic_metric` | `extended` | metric=`dm_sql_thd` | `> 50` | enabled=`false`
- `dm_io_thread_util_high` | `periodic_metric` | `extended` | metric=`dm_io_thd` | `> 50` | enabled=`false`
- `dm_max_sessions_small` | `periodic_metric` | `extended` | metric=`MAX_SESSIONS` | `< 200` | enabled=`false`

## greenplum
- 规则数：`12`
- `greenplum_unavailable` | `realtime_metric` | `core` | metric=`greenplum_server_up` | `== 0` | enabled=`true`
- `greenplum_deadlocks_detected` | `realtime_metric` | `core` | metric=`deadlocks` | `> 0` | enabled=`true`
- `greenplum_conflicts_detected` | `periodic_metric` | `core` | metric=`conflicts` | `> 0` | enabled=`true`
- `greenplum_running_sessions_high` | `periodic_metric` | `core` | metric=`running` | `> 120` | enabled=`true`
- `greenplum_active_sessions_high` | `periodic_metric` | `core` | metric=`active` | `> 80` | enabled=`true`
- `greenplum_state_blocked_high` | `periodic_metric` | `extended` | metric=`num` | `> 30` | enabled=`false`
- `greenplum_blk_read_time_high` | `periodic_metric` | `core` | metric=`blk_read_time` | `> 500` | enabled=`true`
- `greenplum_blk_write_time_high` | `periodic_metric` | `core` | metric=`blk_write_time` | `> 500` | enabled=`true`
- `greenplum_query_avg_time_high` | `periodic_metric` | `extended` | metric=`avg_time` | `> 500` | enabled=`false`
- `greenplum_cache_hit_ratio_low` | `periodic_metric` | `core` | metric=`ratio` | `< 95` | enabled=`true`
- `greenplum_checkpoint_sync_high` | `periodic_metric` | `extended` | metric=`checkpoint_sync_time` | `> 1000` | enabled=`false`
- `greenplum_rollback_high` | `periodic_metric` | `extended` | metric=`rollbacks` | `> 100` | enabled=`false`

## kingbase
- 规则数：`12`
- `kingbase_unavailable` | `realtime_metric` | `core` | metric=`kingbase_server_up` | `== 0` | enabled=`true`
- `kingbase_deadlocks_detected` | `realtime_metric` | `core` | metric=`deadlocks` | `> 0` | enabled=`true`
- `kingbase_conflicts_detected` | `periodic_metric` | `core` | metric=`conflicts` | `> 0` | enabled=`true`
- `kingbase_running_sessions_high` | `periodic_metric` | `core` | metric=`running` | `> 120` | enabled=`true`
- `kingbase_active_sessions_high` | `periodic_metric` | `core` | metric=`active` | `> 80` | enabled=`true`
- `kingbase_state_blocked_high` | `periodic_metric` | `extended` | metric=`num` | `> 30` | enabled=`false`
- `kingbase_blk_read_time_high` | `periodic_metric` | `core` | metric=`blk_read_time` | `> 500` | enabled=`true`
- `kingbase_blk_write_time_high` | `periodic_metric` | `core` | metric=`blk_write_time` | `> 500` | enabled=`true`
- `kingbase_query_avg_time_high` | `periodic_metric` | `extended` | metric=`avg_time` | `> 500` | enabled=`false`
- `kingbase_cache_hit_ratio_low` | `periodic_metric` | `core` | metric=`ratio` | `< 95` | enabled=`true`
- `kingbase_checkpoint_sync_high` | `periodic_metric` | `extended` | metric=`checkpoint_sync_time` | `> 1000` | enabled=`false`
- `kingbase_rollback_high` | `periodic_metric` | `extended` | metric=`rollbacks` | `> 100` | enabled=`false`

## mariadb
- 规则数：`14`
- `mariadb_unavailable` | `realtime_metric` | `core` | metric=`mariadb_server_up` | `== 0` | enabled=`true`
- `mariadb_conn_util_high` | `periodic_metric` | `core` | metric=`max_used_connections` | `> 80` | enabled=`true`
- `mariadb_conn_util_critical` | `periodic_metric` | `core` | metric=`max_used_connections` | `> 90` | enabled=`true`
- `mariadb_threads_running_high` | `periodic_metric` | `core` | metric=`threads_running` | `> 60` | enabled=`true`
- `mariadb_threads_running_critical` | `periodic_metric` | `extended` | metric=`threads_running` | `> 120` | enabled=`false`
- `mariadb_aborted_connects_high` | `periodic_metric` | `core` | metric=`aborted_connects` | `> 10` | enabled=`true`
- `mariadb_aborted_clients_high` | `periodic_metric` | `extended` | metric=`aborted_clients` | `> 10` | enabled=`false`
- `mariadb_innodb_hit_low` | `periodic_metric` | `core` | metric=`innodb_buffer_hit_rate` | `< 95` | enabled=`true`
- `mariadb_query_cache_hit_low` | `periodic_metric` | `extended` | metric=`query_cache_hit_rate` | `< 60` | enabled=`false`
- `mariadb_tmp_disk_tables_high` | `periodic_metric` | `core` | metric=`created_tmp_disk_tables` | `> 100` | enabled=`true`
- `mariadb_table_locks_waited` | `periodic_metric` | `core` | metric=`table_locks_waited` | `> 0` | enabled=`true`
- `mariadb_select_scan_high` | `periodic_metric` | `extended` | metric=`select_scan` | `> 1000` | enabled=`false`
- `mariadb_sort_merge_high` | `periodic_metric` | `extended` | metric=`sort_merge_passes` | `> 50` | enabled=`false`
- `mariadb_slow_query_detected` | `periodic_metric` | `extended` | metric=`query_time` | `> 1000` | enabled=`false`

## mongodb_atlas
- 规则数：`12`
- `mongodb_atlas_unavailable` | `realtime_metric` | `core` | metric=`mongodb_atlas_server_up` | `== 0` | enabled=`true`
- `mongodb_atlas_current_conn_high` | `periodic_metric` | `core` | metric=`current` | `> 600` | enabled=`true`
- `mongodb_atlas_current_conn_critical` | `periodic_metric` | `core` | metric=`current` | `> 900` | enabled=`true`
- `mongodb_atlas_available_conn_low` | `periodic_metric` | `core` | metric=`available` | `< 100` | enabled=`true`
- `mongodb_atlas_available_conn_critical` | `periodic_metric` | `core` | metric=`available` | `< 50` | enabled=`true`
- `mongodb_atlas_requests_high` | `periodic_metric` | `core` | metric=`numRequests` | `> 12000` | enabled=`true`
- `mongodb_atlas_bytes_in_high` | `periodic_metric` | `extended` | metric=`bytesIn` | `> 104857600` | enabled=`false`
- `mongodb_atlas_bytes_out_high` | `periodic_metric` | `extended` | metric=`bytesOut` | `> 104857600` | enabled=`false`
- `mongodb_atlas_query_ops_high` | `periodic_metric` | `extended` | metric=`query` | `> 8000` | enabled=`false`
- `mongodb_atlas_update_ops_high` | `periodic_metric` | `extended` | metric=`update` | `> 5000` | enabled=`false`
- `mongodb_atlas_storage_size_high` | `periodic_metric` | `extended` | metric=`storageSize` | `> 536870912000` | enabled=`false`
- `mongodb_atlas_index_size_high` | `periodic_metric` | `extended` | metric=`indexSize` | `> 107374182400` | enabled=`false`

## oceanbase
- 规则数：`12`
- `oceanbase_unavailable` | `realtime_metric` | `core` | metric=`oceanbase_server_up` | `== 0` | enabled=`true`
- `oceanbase_process_high` | `periodic_metric` | `core` | metric=`num` | `> 120` | enabled=`true`
- `oceanbase_process_critical` | `periodic_metric` | `core` | metric=`num` | `> 200` | enabled=`true`
- `oceanbase_conn_util_high` | `periodic_metric` | `core` | metric=`num` | `> 70` | enabled=`true`
- `oceanbase_conn_util_critical` | `periodic_metric` | `extended` | metric=`num` | `> 85` | enabled=`false`
- `oceanbase_select_high` | `periodic_metric` | `core` | metric=`sql_select_count` | `> 25000` | enabled=`true`
- `oceanbase_insert_high` | `periodic_metric` | `extended` | metric=`sql_insert_count` | `> 10000` | enabled=`false`
- `oceanbase_update_high` | `periodic_metric` | `extended` | metric=`sql_update_count` | `> 10000` | enabled=`false`
- `oceanbase_delete_high` | `periodic_metric` | `extended` | metric=`sql_delete_count` | `> 5000` | enabled=`false`
- `oceanbase_write_ops_high` | `periodic_metric` | `core` | metric=`sql_update_count` | `> 15000` | enabled=`true`
- `oceanbase_write_ops_critical` | `periodic_metric` | `extended` | metric=`sql_update_count` | `> 30000` | enabled=`false`
- `oceanbase_max_connections_small` | `periodic_metric` | `extended` | metric=`max_connections` | `< 200` | enabled=`false`

## opengauss
- 规则数：`11`
- `opengauss_unavailable` | `realtime_metric` | `core` | metric=`opengauss_server_up` | `== 0` | enabled=`true`
- `opengauss_deadlocks_detected` | `realtime_metric` | `core` | metric=`deadlocks` | `> 0` | enabled=`true`
- `opengauss_conflicts_detected` | `periodic_metric` | `core` | metric=`conflicts` | `> 0` | enabled=`true`
- `opengauss_running_sessions_high` | `periodic_metric` | `core` | metric=`running` | `> 120` | enabled=`true`
- `opengauss_running_sessions_critical` | `periodic_metric` | `extended` | metric=`running` | `> 180` | enabled=`false`
- `opengauss_blk_read_time_high` | `periodic_metric` | `core` | metric=`blk_read_time` | `> 500` | enabled=`true`
- `opengauss_blk_write_time_high` | `periodic_metric` | `core` | metric=`blk_write_time` | `> 500` | enabled=`true`
- `opengauss_blk_read_burst` | `periodic_metric` | `extended` | metric=`blks_read` | `> 10000` | enabled=`false`
- `opengauss_blk_hit_ratio_low` | `periodic_metric` | `core` | metric=`blks_hit` | `< 95` | enabled=`true`
- `opengauss_blk_hit_ratio_critical` | `periodic_metric` | `extended` | metric=`blks_hit` | `< 90` | enabled=`false`
- `opengauss_max_connections_small` | `periodic_metric` | `extended` | metric=`max_connections` | `< 200` | enabled=`false`

## oracle
- 规则数：`14`
- `oracle_unavailable` | `realtime_metric` | `core` | metric=`oracle_server_up` | `== 0` | enabled=`true`
- `oracle_tablespace_used_high` | `periodic_metric` | `core` | metric=`used_percentage` | `> 80` | enabled=`true`
- `oracle_tablespace_used_critical` | `periodic_metric` | `core` | metric=`used_percentage` | `> 90` | enabled=`true`
- `oracle_free_space_low` | `periodic_metric` | `core` | metric=`free_percentage` | `< 10` | enabled=`true`
- `oracle_process_count_high` | `periodic_metric` | `core` | metric=`process_count` | `> 500` | enabled=`true`
- `oracle_process_count_critical` | `periodic_metric` | `extended` | metric=`process_count` | `> 800` | enabled=`false`
- `oracle_qps_high` | `periodic_metric` | `core` | metric=`qps` | `> 5000` | enabled=`true`
- `oracle_tps_high` | `periodic_metric` | `extended` | metric=`tps` | `> 3000` | enabled=`false`
- `oracle_commit_wait_high` | `periodic_metric` | `core` | metric=`commit_wait_time` | `> 1000` | enabled=`true`
- `oracle_user_io_wait_high` | `periodic_metric` | `core` | metric=`user_io_wait_time` | `> 1000` | enabled=`true`
- `oracle_buffer_cache_low` | `periodic_metric` | `core` | metric=`buffer_cache_hit_ratio` | `< 95` | enabled=`true`
- `oracle_library_cache_low` | `periodic_metric` | `extended` | metric=`lib_cache_hit_ratio` | `< 95` | enabled=`false`
- `oracle_top_sql_cpu_high` | `periodic_metric` | `extended` | metric=`cpu_secs` | `> 60` | enabled=`false`
- `oracle_password_expiry_soon` | `periodic_metric` | `extended` | metric=`expiry_seconds` | `< 604800` | enabled=`false`

## postgresql
- 规则数：`12`
- `postgresql_unavailable` | `realtime_metric` | `core` | metric=`postgresql_server_up` | `== 0` | enabled=`true`
- `postgresql_deadlocks_detected` | `realtime_metric` | `core` | metric=`deadlocks` | `> 0` | enabled=`true`
- `postgresql_conflicts_detected` | `periodic_metric` | `core` | metric=`conflicts` | `> 0` | enabled=`true`
- `postgresql_running_sessions_high` | `periodic_metric` | `core` | metric=`running` | `> 120` | enabled=`true`
- `postgresql_active_sessions_high` | `periodic_metric` | `core` | metric=`active` | `> 80` | enabled=`true`
- `postgresql_state_blocked_high` | `periodic_metric` | `extended` | metric=`num` | `> 30` | enabled=`false`
- `postgresql_blk_read_time_high` | `periodic_metric` | `core` | metric=`blk_read_time` | `> 500` | enabled=`true`
- `postgresql_blk_write_time_high` | `periodic_metric` | `core` | metric=`blk_write_time` | `> 500` | enabled=`true`
- `postgresql_query_avg_time_high` | `periodic_metric` | `extended` | metric=`avg_time` | `> 500` | enabled=`false`
- `postgresql_cache_hit_ratio_low` | `periodic_metric` | `core` | metric=`ratio` | `< 95` | enabled=`true`
- `postgresql_checkpoint_sync_high` | `periodic_metric` | `extended` | metric=`checkpoint_sync_time` | `> 1000` | enabled=`false`
- `postgresql_rollback_high` | `periodic_metric` | `extended` | metric=`rollbacks` | `> 100` | enabled=`false`

## sqlserver
- 规则数：`11`
- `sqlserver_unavailable` | `realtime_metric` | `core` | metric=`sqlserver_server_up` | `== 0` | enabled=`true`
- `sqlserver_connections_high` | `periodic_metric` | `core` | metric=`user_connection` | `> 300` | enabled=`true`
- `sqlserver_connections_critical` | `periodic_metric` | `core` | metric=`user_connection` | `> 500` | enabled=`true`
- `sqlserver_buffer_hit_low` | `periodic_metric` | `core` | metric=`buffer_cache_hit_ratio` | `< 95` | enabled=`true`
- `sqlserver_buffer_hit_critical` | `periodic_metric` | `extended` | metric=`buffer_cache_hit_ratio` | `< 90` | enabled=`false`
- `sqlserver_ple_low` | `periodic_metric` | `core` | metric=`page_life_expectancy` | `< 300` | enabled=`true`
- `sqlserver_ple_critical` | `periodic_metric` | `extended` | metric=`page_life_expectancy` | `< 120` | enabled=`false`
- `sqlserver_page_reads_high` | `periodic_metric` | `core` | metric=`page_reads_sec` | `> 5000` | enabled=`true`
- `sqlserver_page_writes_high` | `periodic_metric` | `extended` | metric=`page_writes_sec` | `> 3000` | enabled=`false`
- `sqlserver_checkpoint_pages_high` | `periodic_metric` | `extended` | metric=`checkpoint_pages_sec` | `> 1000` | enabled=`false`
- `sqlserver_target_pages_gap` | `periodic_metric` | `extended` | metric=`database_pages` | `< 80` | enabled=`false`

## tidb
- 规则数：`11`
- `tidb_unavailable` | `realtime_metric` | `core` | metric=`tidb_server_up` | `== 0` | enabled=`true`
- `tidb_connections_high` | `periodic_metric` | `core` | metric=`connections` | `> 400` | enabled=`true`
- `tidb_connections_critical` | `periodic_metric` | `core` | metric=`connections` | `> 700` | enabled=`true`
- `tidb_conn_util_high` | `periodic_metric` | `core` | metric=`connections` | `> 80` | enabled=`true`
- `tidb_conn_util_critical` | `periodic_metric` | `extended` | metric=`connections` | `> 90` | enabled=`false`
- `tidb_store_usage_high` | `periodic_metric` | `core` | metric=`used_size` | `> 80` | enabled=`true`
- `tidb_store_usage_critical` | `periodic_metric` | `core` | metric=`used_size` | `> 90` | enabled=`true`
- `tidb_available_low` | `periodic_metric` | `core` | metric=`available` | `< 21474836480` | enabled=`true`
- `tidb_available_critical` | `periodic_metric` | `extended` | metric=`available` | `< 10737418240` | enabled=`false`
- `tidb_uptime_short` | `periodic_metric` | `extended` | metric=`uptime` | `< 3600` | enabled=`false`
- `tidb_store_used_abs_high` | `periodic_metric` | `extended` | metric=`used_size` | `> 1099511627776` | enabled=`false`

## vastbase
- 规则数：`12`
- `vastbase_unavailable` | `realtime_metric` | `core` | metric=`vastbase_server_up` | `== 0` | enabled=`true`
- `vastbase_deadlocks_detected` | `realtime_metric` | `core` | metric=`deadlocks` | `> 0` | enabled=`true`
- `vastbase_conflicts_detected` | `periodic_metric` | `core` | metric=`conflicts` | `> 0` | enabled=`true`
- `vastbase_running_sessions_high` | `periodic_metric` | `core` | metric=`running` | `> 120` | enabled=`true`
- `vastbase_active_sessions_high` | `periodic_metric` | `core` | metric=`active` | `> 80` | enabled=`true`
- `vastbase_state_blocked_high` | `periodic_metric` | `extended` | metric=`num` | `> 30` | enabled=`false`
- `vastbase_blk_read_time_high` | `periodic_metric` | `core` | metric=`blk_read_time` | `> 500` | enabled=`true`
- `vastbase_blk_write_time_high` | `periodic_metric` | `core` | metric=`blk_write_time` | `> 500` | enabled=`true`
- `vastbase_query_avg_time_high` | `periodic_metric` | `extended` | metric=`avg_time` | `> 500` | enabled=`false`
- `vastbase_cache_hit_ratio_low` | `periodic_metric` | `core` | metric=`ratio` | `< 95` | enabled=`true`
- `vastbase_checkpoint_sync_high` | `periodic_metric` | `extended` | metric=`checkpoint_sync_time` | `> 1000` | enabled=`false`
- `vastbase_rollback_high` | `periodic_metric` | `extended` | metric=`rollbacks` | `> 100` | enabled=`false`

