# 监控任务详情 Metrics Tab 重构计划（通用化）

## 1. 背景与目标
当前“监控任务详情 -> 指标 Tab”体验存在以下问题：
- 指标信息扁平，缺少按业务分类的导航。
- 无统一的指标列表视图（名称/状态/最新值/间隔/时间/操作）。
- 趋势查看能力弱，图表切换与时间范围选择不完整。
- 缺少通用设计，容易在不同监控类型重复开发。

本次目标：
1. 指标 Tab 下增加二级分类 Tab，来源于模板 YAML 的 `metrics[].name`（如 `server`、`clients`）。
2. 每个分类 Tab 提供统一页面结构：
   - 顶部工具栏：`添加`、`删除`、`刷新`
   - 指标列表：`名称(中文)`、`状态`、`最新值`、`间隔`、`时间`、`操作`
3. 操作列支持“查看趋势明细”，进入统一趋势详情弹窗：
   - 图表类型切换：折线图/柱状图/表格
   - 时间范围：最近1小时/1天/1周/1月/自定义
   - 表格模式支持导出 Excel（包含 `cid`、监控对象、监控指标、时间、值）
4. 方案必须可复用到所有监控类型，减少后续返工。

---

## 2. 设计原则（减少返工）
1. **模板驱动**：页面分类、字段中文名、数据类型都来自模板 YAML，不写死 Redis/MySQL 逻辑。
2. **组件通用化**：抽离成可复用组件，详情页仅传入 `monitorId + app + templateContent`。
3. **数据接口稳定**：优先复用已有接口，新增接口做“通用形态”（不绑定单一监控类型）。
4. **分阶段可交付**：先达成可用，再增强性能与持久化。

---

## 3. 目标页面结构

### 3.1 指标主页面（二级 Tab）
- 一级：监控详情页已有 `基本信息 / 指标 / 告警`
- 二级（本次新增）：`指标`页内部按 YAML 分类展示
  - 示例：`服务器信息` | `客户端信息` | `持久化信息` ...

### 3.2 每个分类 Tab 内容
1. 工具栏
- `添加`：从当前分类可用指标中勾选添加到展示列表
- `删除`：删除当前勾选指标（仅删除“展示项”，不删除模板定义）
- `刷新`：刷新当前分类指标最新值

2. 指标列表（表格）
- 名称（中文）
- 状态（正常/异常/未知）
- 最新值
- 间隔（继承 monitor interval）
- 时间（最后采样时间）
- 操作（查看趋势明细）

3. 趋势明细弹窗
- 图表类型：折线图、柱状图、表格
- 时间范围：1h / 1d / 1w / 1m / 自定义
- 表格模式支持导出 Excel

---

## 4. 通用数据模型（前端）
```ts
interface MetricGroupView {
  key: string              // yaml metrics[].name
  title: string            // 中文显示名（优先 i18n.zh-CN）
  metrics: MetricFieldView[]
}

interface MetricFieldView {
  field: string            // yaml field
  title: string            // 中文显示名
  type: 'number' | 'string' | 'time'
  metricName: string       // 最终查询名（与时序库一致）
  latestValue?: string | number
  latestTs?: number
  status: 'normal' | 'abnormal' | 'unknown'
}
```

### 4.1 metricName 映射规则（统一）
按优先级匹配：
1. `field`（原名）
2. `normalize(group_name + '_' + field)`
3. 派生字段：`field_ok`、`<app>_server_up`
4. 通过 `/metrics/series` 结果反查匹配（缓存）

---

## 5. 接口方案

## 5.1 复用接口
1. `GET /monitoring/targets/{id}`：任务基本信息
2. `GET /monitoring/targets/{id}/metrics/series`：发现可用时序名
3. `GET /monitoring/targets/{id}/metrics/query-range`：趋势数据

## 5.2 建议新增（通用）
1. `GET /monitoring/targets/{id}/metrics/latest`
- 入参：`names=xxx,yyy`
- 返回：每个指标最新值+时间+是否缺失
- 作用：避免当前表格 latest 走 N 次 query-range

2. `POST /monitoring/targets/{id}/metrics/export`
- 入参：`name`、`from`、`to`、`step`
- 返回：Excel 文件流
- 导出字段建议：`cid/monitor_id`、`monitor_name`、`app`、`target`、`metric_name`、`metric_title`、`timestamp`、`value`

> 说明：若先不做后端导出，可第一期前端用 `xlsx` 生成，后端导出作为第二期增强。

---

## 6. 状态计算规则（第一版）
1. 无数据：`unknown`
2. 数值型：
- 有值且时间新鲜（`now - latestTs <= 2 * interval`）=> `normal`
- 有值但过期 => `unknown`
3. 状态型（`*_ok` / `*_up`）
- `1 => normal`
- `0 => abnormal`

> 第二期可增强：联动告警规则结果，状态直接映射当前告警态。

---

## 7. 组件拆分（复用）
1. `MetricGroupTabs.vue`
- 职责：渲染分类 Tab、维护当前分组

2. `MetricGroupTable.vue`
- 职责：工具栏 + 指标表格 + 选择/添加/删除

3. `MetricTrendDialog.vue`
- 职责：趋势图/表切换、时间范围、导出

4. `useMonitorMetrics.ts`（composable）
- 职责：模板解析、metric 映射、latest 拉取、趋势查询、缓存

这样后续任何监控类型只要有模板 YAML 就能复用。

---

## 8. 分阶段实施计划

### Phase 1（基础改造，先可用）
- 指标页二级分类 Tab（来自 YAML metrics）
- 每分类下指标列表（中文名/状态/最新值/间隔/时间/操作）
- 趋势弹窗（折线+柱状+表格，时间范围切换）
- 前端导出 Excel（表格模式）

交付标准：
- Redis/MySQL 任一模板可自动生成分类 Tab
- 指标列表可刷新，趋势可查看，Excel 可下载

### Phase 2（性能与一致性）
- 新增 `metrics/latest` 批量接口
- 查询缓存与批量刷新优化
- 状态判定精细化（减少 unknown）

### Phase 3（运营增强）
- 指标展示项“添加/删除”配置持久化（按 monitor 保存）
- 与告警状态联动（状态列更准确）

---

## 9. 影响范围
前端：
- `frontend/src/views/monitoring/target/detail.vue`
- `frontend/src/components/monitoring/metrics/*`（新增）
- `frontend/src/composables/useMonitorMetrics.ts`（新增）
- `frontend/src/api/monitoring.ts`

后端（Phase 2 起）：
- `backend/app/routes/monitoring_target.py`（新增 latest/export 转发）
- `manager-go/internal/httpapi/server.go`（新增 latest/export 能力）
- `manager-go/internal/metrics/vm_client.go`（可选新增 instant query）

---

## 10. 风险与对策
1. **metricName 不一致导致无数据**
- 对策：统一映射规则 + series 反查 + fallback 别名

2. **查询性能问题（大时间窗 + 多指标）**
- 对策：限制默认步长、分页加载、批量 latest 接口

3. **导出数据量过大**
- 对策：导出前做时间范围校验；超过阈值提示缩小范围

---

## 11. 本轮执行顺序（建议）
1. 先完成 Phase 1 前端重构（不改后端接口）
2. 验证 Redis / MySQL 两类模板
3. 再补 Phase 2 接口优化，避免一次改太大

---

## 12. 验收清单
1. 指标页是否按 YAML 分类展示二级 Tab
2. 每个分类是否有 添加/删除/刷新
3. 列表列是否完整：名称(中文)/状态/最新值/间隔/时间/操作
4. 趋势弹窗是否支持折线/柱状/表格
5. 是否支持 1h/1d/1w/1m/自定义
6. 表格导出是否包含 cid、监控对象、监控指标、时间、值
7. Redis/MySQL 等不同模板是否无需改代码即可复用

---

## 13. 实施进度（更新于 2026-03-12）

### 13.1 已完成（Phase 1）
1. 监控任务详情已从列表页弹窗改为独立路由页面：
- 路由：`/monitoring/target/:id`
- 列表页点击“详情”进入新页面

2. 指标 Tab 已完成按模板 YAML `metrics[]` 的二级分类展示：
- 分类标题优先显示 `i18n.zh-CN`
- 不再写死 Redis/MySQL 分类

3. 每个分类页已实现统一工具栏与列表：
- 工具栏：`添加`、`删除`、`刷新`
- 列表列：`名称(中文)`、`状态`、`最新值`、`间隔`、`时间`、`操作`
- 状态型指标支持 `*_ok` / `*_up` 语义判定（1=正常，0=异常）

4. 趋势明细弹窗已完成：
- 图表类型切换：折线图 / 柱状图 / 表格
- 时间范围：最近 1 小时 / 1 天 / 1 周 / 1 月 / 自定义
- 支持刷新

5. 表格导出已完成第一版：
- 提供 Excel 兼容 CSV 导出（UTF-8 BOM）
- 导出字段包含：`monitor_id`、`monitor_name`、`app`、`ci_code`、`target`、`metric_name`、`metric_title`、`timestamp`、`time`、`value`

6. 已完成通用化抽象，供后续监控类型复用：
- `frontend/src/composables/useMonitorMetrics.ts`
- `frontend/src/components/monitoring/metrics/MonitorMetricsPanel.vue`
- `frontend/src/components/monitoring/metrics/MetricTrendDialog.vue`

7. 本轮构建验证已通过：
- `frontend: npm run -s build`

### 13.2 暂未完成（后续增强）
1. 可选增强：指标状态与告警状态增加“告警级别染色（critical/warning/info）”细分展示（当前统一为异常）。

### 13.3 已完成（Phase 2，更新于 2026-03-12）
1. 已新增后端批量 latest 接口（Manager + Python Web 转发）：
- Manager: `GET /api/v1/metrics/latest`
- Web: `GET /api/v1/monitoring/targets/{id}/metrics/latest`
- 前端 latest 查询已优先走该接口，失败自动回退旧 `query-range`

2. 已新增后端导出接口（Manager + Python Web 转发）：
- Manager: `GET /api/v1/metrics/export`
- Web: `GET /api/v1/monitoring/targets/{id}/metrics/export`
- 导出格式：Excel 兼容 CSV 文件流（UTF-8 BOM，attachment）

3. 趋势弹窗导出已切换到后端导出接口：
- 前端不再本地拼装导出内容，改为请求后端文件流下载
- 保留通用字段：`monitor_id/monitor_name/app/ci_code/target/metric_name/timestamp/time/value`

4. 本轮回归验证通过：
- `manager-go: go test ./...`
- `python3 -m py_compile backend/app/routes/monitoring_target.py backend/app/services/manager_api_service.py`
- `frontend: npm run -s build`

### 13.4 已完成（Phase 3，更新于 2026-03-12）
1. 指标展示项已实现按 monitor 持久化：
- Manager 新增监控维度配置接口：`GET/PUT /api/v1/monitors/{id}/metrics-view`
- Python Web 新增转发接口：`GET/PUT /api/v1/monitoring/targets/{id}/metrics-view`
- 前端在“添加/删除指标”后自动保存并在下次进入详情页恢复展示项

2. 指标状态列已与当前告警链路联动：
- 指标页刷新时拉取实例当前告警（`monitor_id` 过滤）
- 命中当前告警的指标行优先标记为“异常”
- 未命中告警时沿用采样新鲜度 + `_ok/_up` 规则判定

### 13.5 已完成（字符串指标可见性修复，更新于 2026-03-12）
1. 修复“YAML 中字符串字段无数据显示”问题（如 `os`、`redis_version`、`config_file`、`executable`）：
- Manager 在接收 Collector 报告时维护 monitor 维度字符串 latest 快照
- `GET /api/v1/metrics/latest` 返回新增 `text` 字段（兼容原 `value` 数字字段）

2. 前端指标页已适配字符串 latest：
- 字符串字段在不命中时序名时，兜底按字段名请求 latest
- 最新值列优先显示 `text` 原值，避免把字符串误显示为科学计数

3. 本轮验证：
- `manager-go: go test ./...`
- `frontend: npm run build`

### 13.6 已完成（趋势弹窗体验优化，更新于 2026-03-12）
1. 字符串指标趋势明细改为“仅表格”：
- 若指标类型为 `string`，不再显示“折线图/柱状图”选项，默认直接展示表格
- 保留时间范围与刷新能力

2. 数值指标趋势图升级为 ECharts：
- 原生 SVG 折线/柱状图已替换为 ECharts 渲染
- 增加 tooltip、dataZoom（内置缩放 + 滑块）、平滑折线、柱状图样式优化

3. 字符串指标导出优化：
- 字符串指标在表格视图下支持本地 CSV（Excel 兼容）导出

4. 本轮验证：
- `frontend: npm run build`
