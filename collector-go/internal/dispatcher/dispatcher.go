package dispatcher

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/pipeline"
	"collector-go/internal/protocol"
	"collector-go/internal/protocol/sshcollector"
	"collector-go/internal/queue"
	"collector-go/internal/scheduler"
	"collector-go/internal/worker"
)

type PrecomputeEvaluator interface {
	Enabled() bool
	Evaluate(task model.MetricsTask, fields map[string]string) (bool, string)
}

type Dispatcher struct {
	wheel *scheduler.Wheel
	pool  *worker.Pool
	queue queue.ResultQueue

	mu          sync.Mutex
	jobTimers   map[int64]int64
	jobs        map[int64]model.Job
	defaultWait time.Duration
	dropped     atomic.Int64
	precompute  PrecomputeEvaluator
}

var collectorDebugEnabled atomic.Bool

func New(wheel *scheduler.Wheel, pool *worker.Pool, q queue.ResultQueue) *Dispatcher {
	return &Dispatcher{
		wheel:       wheel,
		pool:        pool,
		queue:       q,
		jobTimers:   map[int64]int64{},
		jobs:        map[int64]model.Job{},
		defaultWait: 5 * time.Second,
	}
}

func (d *Dispatcher) SetPrecomputeEvaluator(ev PrecomputeEvaluator) {
	d.precompute = ev
}

func (d *Dispatcher) RegisterJob(job model.Job) {
	d.RemoveJob(job.ID)
	job = normalizeJob(job)
	id := d.wheel.ScheduleEvery(job.Interval, func(ctx context.Context) {
		d.submitWithRetry(ctx, func(ctx context.Context) {
			d.executeJobCycle(ctx, job)
		}, job, model.MetricsTask{Name: "job-cycle", Protocol: "dispatcher"})
	})

	d.mu.Lock()
	d.jobTimers[job.ID] = id
	d.jobs[job.ID] = job
	d.mu.Unlock()
}

func (d *Dispatcher) RunJobOnce(ctx context.Context, job model.Job) {
	job = normalizeJob(job)
	d.submitWithRetry(ctx, func(ctx context.Context) {
		d.executeJobCycle(ctx, job)
	}, job, model.MetricsTask{Name: "job-cycle", Protocol: "dispatcher"})
}

func (d *Dispatcher) RemoveJob(jobID int64) {
	d.mu.Lock()
	id, ok := d.jobTimers[jobID]
	delete(d.jobTimers, jobID)
	delete(d.jobs, jobID)
	d.mu.Unlock()
	if ok {
		d.wheel.Cancel(id)
	}
}

func (d *Dispatcher) DroppedResults() int64 {
	return d.dropped.Load()
}

func normalizeJob(job model.Job) model.Job {
	tasks := append([]model.MetricsTask(nil), job.Tasks...)
	// HertzBeat-like semantics: smaller priority means higher priority.
	sort.Slice(tasks, func(i, j int) bool { return tasks[i].Priority < tasks[j].Priority })
	job.Tasks = tasks
	return job
}

func (d *Dispatcher) executeJobCycle(ctx context.Context, job model.Job) {
	if len(job.Tasks) == 0 {
		return
	}
	redisCache := newRedisCycleCache()
	jdbcCache := newJDBCCycleCache()
	valueStore := newCycleValueStore()
	if d.executeSSHBundleCycle(ctx, job, valueStore) {
		return
	}
	for i := 0; i < len(job.Tasks); {
		p := job.Tasks[i].Priority
		j := i + 1
		for j < len(job.Tasks) && job.Tasks[j].Priority == p {
			j++
		}
		var wg sync.WaitGroup
		for _, t := range job.Tasks[i:j] {
			task := t
			wg.Add(1)
			go func() {
				defer wg.Done()
				d.executeTask(ctx, job, task, redisCache, jdbcCache, valueStore)
			}()
		}
		wg.Wait()
		i = j
	}
}

func (d *Dispatcher) executeSSHBundleCycle(ctx context.Context, job model.Job, valueStore *cycleValueStore) bool {
	if len(job.Tasks) == 0 {
		return false
	}
	for _, task := range job.Tasks {
		if strings.TrimSpace(strings.ToLower(task.Protocol)) != "ssh" {
			return false
		}
		if taskHasDynamicPlaceholders(task) {
			return false
		}
	}
	startAt := time.Now()
	outcome, err := sshcollector.CollectBundle(ctx, job.Tasks)
	if collectorDebugEnabled.Load() {
		debugf("[ssh-bundle-cmd] monitor_id=%d job_id=%d app=%s script=\n%s", job.Monitor, job.ID, job.App, outcome.Script)
		debugf("[ssh-bundle-output] monitor_id=%d job_id=%d app=%s output=\n%s", job.Monitor, job.ID, job.App, outcome.RawOutput)
	}
	if err != nil {
		debugf("[collect-fail] monitor_id=%d job_id=%d app=%s metrics=ssh_bundle protocol=ssh reason=%v",
			job.Monitor, job.ID, job.App, err)
		for _, task := range job.Tasks {
			d.pushResult(ctx, model.Result{
				JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
				Protocol: task.Protocol, Time: startAt, Success: false, Code: model.CodeCollectFailed,
				Message: fmt.Sprintf("ssh bundle failed: %v", err),
			})
		}
		return true
	}
	snapshotTime := startAt
	for _, bundleRes := range outcome.Results {
		task := bundleRes.Task
		fields := bundleRes.Fields
		msg := bundleRes.Message
		collectErr := bundleRes.Err
		if msg == "" {
			msg = "ok"
		}
		if collectErr == nil {
			var transformErr error
			fields, transformErr = pipeline.Apply(fields, task.Transform)
			if transformErr != nil {
				collectErr = transformErr
			}
		}
		debug := map[string]string{}
		debug["bundle.mode"] = "single_ssh_session"
		debug["bundle.total_latency_ms"] = strconv.FormatInt(outcome.RawLatency.Milliseconds(), 10)
		if collectErr == nil {
			var calcDebug map[string]string
			fields, calcDebug = pipeline.ApplyCalculates(fields, task.CalculateSpecs)
			mergeDebug(debug, calcDebug)
			var dropDebug map[string]string
			fields, dropDebug = pipeline.ApplyFieldWhitelist(fields, task.FieldSpecs, true)
			mergeDebug(debug, dropDebug)
		}
		res := model.Result{
			JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
			Protocol: task.Protocol, Time: snapshotTime, Success: collectErr == nil, Code: model.CodeSuccess,
			Message: msg, Fields: fields, Debug: debug, RawLatency: outcome.RawLatency,
		}
		if collectErr != nil {
			res.Code = model.CodeCollectFailed
			if errors.Is(collectErr, context.DeadlineExceeded) || errors.Is(collectErr, context.Canceled) {
				res.Code = model.CodeTimeout
			}
			res.Message = fmt.Sprintf("%s: %v", msg, collectErr)
			debugf("[collect-fail] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s code=%s message=%q reason=%v",
				job.Monitor, job.ID, job.App, task.Name, task.Protocol, res.Code, msg, collectErr)
		}
		if collectErr == nil && d.precompute != nil && d.precompute.Enabled() {
			triggered, summary := d.precompute.Evaluate(task, fields)
			if triggered {
				if res.Fields == nil {
					res.Fields = map[string]string{}
				}
				res.Fields["__precompute_triggered__"] = "true"
				res.Fields["__precompute_summary__"] = summary
			}
		}
		if collectErr == nil && valueStore != nil {
			valueStore.Save(fields)
		}
		d.pushResult(ctx, res)
	}
	return true
}

func (d *Dispatcher) submitWithRetry(ctx context.Context, task worker.Task, job model.Job, meta model.MetricsTask) {
	backoffs := []time.Duration{0, 20 * time.Millisecond, 50 * time.Millisecond}
	for i, b := range backoffs {
		if b > 0 {
			select {
			case <-ctx.Done():
				return
			case <-time.After(b):
			}
		}
		if err := d.pool.Submit(task); err == nil {
			return
		} else if !errors.Is(err, worker.ErrBusy) {
			break
		}
		if i == len(backoffs)-1 {
			d.pushResult(ctx, model.Result{
				JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: meta.Name,
				Protocol: meta.Protocol, Time: time.Now(), Success: false, Code: model.CodeWorkerBusy,
				Message: "worker pool queue is full",
			})
		}
	}
}

func (d *Dispatcher) executeTask(ctx context.Context, job model.Job, task model.MetricsTask, redisCache *redisCycleCache, jdbcCache *jdbcCycleCache, valueStore *cycleValueStore) {
	collector, err := protocol.Get(task.Protocol)
	if err != nil {
		debugf("[collect-fail] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s reason=%v params=%v",
			job.Monitor, job.ID, job.App, task.Name, task.Protocol, err, maskedTaskParams(task.Params))
		d.pushResult(ctx, model.Result{
			JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
			Protocol: task.Protocol, Time: time.Now(), Success: false, Code: model.CodeProtocolMissing, Message: err.Error(),
		})
		return
	}
	ctx2 := ctx
	if task.Timeout > 0 {
		cancelCtx, cancel := context.WithTimeout(ctx, task.Timeout)
		defer cancel()
		ctx2 = cancelCtx
	}
	start := time.Now()
	debugCollectStart(job, task)
	fields, msg, err := d.collectDynamicTask(ctx2, collector, task, redisCache, jdbcCache, valueStore)
	latency := time.Since(start)
	if err == nil {
		fields, err = pipeline.Apply(fields, task.Transform)
	}
	debug := map[string]string{}
	if err == nil {
		var calcDebug map[string]string
		fields, calcDebug = pipeline.ApplyCalculates(fields, task.CalculateSpecs)
		mergeDebug(debug, calcDebug)
		var dropDebug map[string]string
		// whitelist is enforced only when field_specs are provided by manager compiler.
		fields, dropDebug = pipeline.ApplyFieldWhitelist(fields, task.FieldSpecs, true)
		dropDebug = suppressAliasDropDebug(task, dropDebug)
		mergeDebug(debug, dropDebug)
	}
	res := model.Result{
		JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
		Protocol: task.Protocol, Time: time.Now(), Success: err == nil, Code: model.CodeSuccess, Message: msg,
		Fields: fields, Debug: debug, RawLatency: latency,
	}
	if err != nil {
		res.Code = model.CodeCollectFailed
		if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
			res.Code = model.CodeTimeout
		}
		res.Message = fmt.Sprintf("%s: %v", msg, err)
		debugf("[collect-fail] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s code=%s message=%q reason=%v params=%v",
			job.Monitor, job.ID, job.App, task.Name, task.Protocol, res.Code, msg, err, maskedTaskParams(task.Params))
	}
	if err == nil {
		debugf("[collect-ok] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s message=%q field_count=%d latency_ms=%d",
			job.Monitor, job.ID, job.App, task.Name, task.Protocol, msg, len(fields), latency.Milliseconds())
	}
	if err == nil && d.precompute != nil && d.precompute.Enabled() {
		triggered, summary := d.precompute.Evaluate(task, fields)
		if triggered {
			if res.Fields == nil {
				res.Fields = map[string]string{}
			}
			res.Fields["__precompute_triggered__"] = "true"
			res.Fields["__precompute_summary__"] = summary
		}
	}
	if err == nil && valueStore != nil {
		valueStore.Save(fields)
	}
	d.pushResult(ctx, res)
}

func debugCollectStart(job model.Job, task model.MetricsTask) {
	protocolName := strings.TrimSpace(strings.ToLower(task.Protocol))
	if protocolName == "jdbc" {
		debugf("[collect-start] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s queryType=%s sql=%q params=%v",
			job.Monitor,
			job.ID,
			job.App,
			task.Name,
			task.Protocol,
			strings.TrimSpace(task.Params["queryType"]),
			compactSQL(task.Params["sql"]),
			maskedTaskParams(task.Params),
		)
		return
	}
	debugf("[collect-start] monitor_id=%d job_id=%d app=%s metrics=%s protocol=%s params=%v",
		job.Monitor, job.ID, job.App, task.Name, task.Protocol, maskedTaskParams(task.Params))
}

func debugf(format string, args ...any) {
	if !collectorDebugEnabled.Load() {
		return
	}
	log.Printf("[DEBUG] "+format, args...)
}

func SetLogLevel(level string) {
	collectorDebugEnabled.Store(strings.EqualFold(strings.TrimSpace(level), "debug"))
}

func maskedTaskParams(params map[string]string) map[string]string {
	if len(params) == 0 {
		return map[string]string{}
	}
	out := make(map[string]string, len(params))
	for key, value := range params {
		lowerKey := strings.ToLower(strings.TrimSpace(key))
		if lowerKey == "password" || lowerKey == "passwd" || lowerKey == "secret" || lowerKey == "token" || strings.Contains(lowerKey, "password") || strings.Contains(lowerKey, "secret") || strings.Contains(lowerKey, "token") {
			out[key] = "***"
			continue
		}
		out[key] = value
	}
	return out
}

func (d *Dispatcher) collectDynamicTask(ctx context.Context, collector protocol.Collector, task model.MetricsTask, redisCache *redisCycleCache, jdbcCache *jdbcCycleCache, valueStore *cycleValueStore) (map[string]string, string, error) {
	variants := []model.MetricsTask{task}
	if valueStore != nil {
		resolved := valueStore.Resolve(task)
		if len(resolved) == 0 && taskHasDynamicPlaceholders(task) {
			return nil, "", fmt.Errorf("dynamic placeholder values missing")
		}
		if len(resolved) > 0 {
			variants = resolved
		}
	}
	if len(variants) == 1 {
		return d.collectWithCache(ctx, collector, variants[0], redisCache, jdbcCache)
	}
	parts := make([]map[string]string, 0, len(variants))
	msg := "ok"
	for _, variant := range variants {
		fields, oneMsg, err := d.collectWithCache(ctx, collector, variant, redisCache, jdbcCache)
		if err != nil {
			return nil, oneMsg, err
		}
		msg = oneMsg
		parts = append(parts, fields)
	}
	return mergeCollectedFields(parts), msg, nil
}

func (d *Dispatcher) collectWithCache(ctx context.Context, collector protocol.Collector, task model.MetricsTask, redisCache *redisCycleCache, jdbcCache *jdbcCycleCache) (map[string]string, string, error) {
	protocolName := strings.TrimSpace(strings.ToLower(task.Protocol))
	if protocolName == "redis" && redisCache != nil {
		return d.collectWithRedisCache(ctx, collector, task, redisCache)
	}
	if protocolName == "jdbc" && jdbcCache != nil {
		return d.collectWithJDBCCache(ctx, collector, task, jdbcCache)
	}
	return collector.Collect(ctx, task)
}

func (d *Dispatcher) collectWithRedisCache(ctx context.Context, collector protocol.Collector, task model.MetricsTask, redisCache *redisCycleCache) (map[string]string, string, error) {
	if strings.TrimSpace(strings.ToLower(task.Protocol)) != "redis" || redisCache == nil {
		return collector.Collect(ctx, task)
	}
	key := redisCacheKey(task.Params)
	if key == "" {
		return collector.Collect(ctx, task)
	}
	if cached, ok := redisCache.Get(key); ok {
		if needsRedisSectionFallback(task, cached) {
			fields, msg, err := collector.Collect(ctx, task)
			if err == nil {
				merged := cloneStringMap(cached)
				if merged == nil {
					merged = map[string]string{}
				}
				for k, v := range fields {
					merged[k] = v
				}
				redisCache.Set(key, merged)
				return materializeRedisFields(task, merged), msg, nil
			}
		}
		return materializeRedisFields(task, cached), "ok(cache)", nil
	}

	fetchTask := cloneMetricsTask(task)
	if fetchTask.Params != nil {
		delete(fetchTask.Params, "section")
	}
	fields, msg, err := collector.Collect(ctx, fetchTask)
	if err != nil {
		// Fallback to task-level section collect to keep compatibility.
		return collector.Collect(ctx, task)
	}
	if needsRedisSectionFallback(task, fields) {
		sectionFields, sectionMsg, sectionErr := collector.Collect(ctx, task)
		if sectionErr == nil {
			for k, v := range sectionFields {
				fields[k] = v
			}
			msg = sectionMsg
		}
	}
	redisCache.Set(key, fields)
	return materializeRedisFields(task, fields), msg, nil
}

func needsRedisSectionFallback(task model.MetricsTask, fields map[string]string) bool {
	section := strings.TrimSpace(strings.ToLower(task.Params["section"]))
	if section == "" || len(task.FieldSpecs) == 0 {
		return false
	}
	for _, spec := range task.FieldSpecs {
		field := strings.TrimSpace(spec.Field)
		if field == "" {
			continue
		}
		if _, ok := fields[field]; ok {
			return false
		}
	}
	return true
}

func (d *Dispatcher) collectWithJDBCCache(ctx context.Context, collector protocol.Collector, task model.MetricsTask, jdbcCache *jdbcCycleCache) (map[string]string, string, error) {
	if strings.TrimSpace(strings.ToLower(task.Protocol)) != "jdbc" || jdbcCache == nil {
		return collector.Collect(ctx, task)
	}
	key := jdbcCacheKey(task.Params)
	if key == "" {
		return collector.Collect(ctx, task)
	}
	if cached, ok := jdbcCache.Get(key); ok {
		debugf("[jdbc-cache-hit] metrics=%s queryType=%s sql=%q key=%q field_count=%d",
			task.Name,
			strings.TrimSpace(task.Params["queryType"]),
			compactSQL(task.Params["sql"]),
			maskCacheKey(key),
			len(cached),
		)
		return materializeJDBCFields(task, cached), "ok(cache)", nil
	}
	fetchTask := cloneMetricsTask(task)
	if fetchTask.Params != nil {
		delete(fetchTask.Params, "alias_fields")
	}
	fields, msg, err := collector.Collect(ctx, fetchTask)
	if err != nil {
		return nil, msg, err
	}
	jdbcCache.Set(key, fields)
	debugf("[jdbc-cache-miss] metrics=%s queryType=%s sql=%q key=%q field_count=%d",
		task.Name,
		strings.TrimSpace(task.Params["queryType"]),
		compactSQL(task.Params["sql"]),
		maskCacheKey(key),
		len(fields),
	)
	return materializeJDBCFields(task, fields), msg, nil
}

func materializeRedisFields(task model.MetricsTask, cached map[string]string) map[string]string {
	out := cloneStringMap(cached)
	if out == nil {
		out = map[string]string{}
	}
	if section := strings.TrimSpace(task.Params["section"]); section != "" {
		out["section"] = section
	}
	return out
}

func materializeJDBCFields(task model.MetricsTask, cached map[string]string) map[string]string {
	out := cloneStringMap(cached)
	if out == nil {
		out = map[string]string{}
	}
	aliasFields := parseAliasFieldsFromParams(task.Params)
	if len(aliasFields) == 0 {
		return out
	}
	valuesByLower := make(map[string]string, len(cached))
	for key, value := range cached {
		valuesByLower[strings.ToLower(strings.TrimSpace(key))] = value
	}
	projected := make(map[string]string, len(aliasFields))
	for _, alias := range aliasFields {
		trimmed := strings.TrimSpace(alias)
		if trimmed == "" {
			continue
		}
		if value, ok := valuesByLower[strings.ToLower(trimmed)]; ok {
			projected[trimmed] = value
		}
	}
	return projected
}

func cloneMetricsTask(task model.MetricsTask) model.MetricsTask {
	dup := task
	dup.Params = cloneStringMap(task.Params)
	dup.Transform = append([]model.Transform(nil), task.Transform...)
	dup.FieldSpecs = append([]model.FieldSpec(nil), task.FieldSpecs...)
	dup.CalculateSpecs = append([]model.CalculateSpec(nil), task.CalculateSpecs...)
	return dup
}

func cloneStringMap(src map[string]string) map[string]string {
	if len(src) == 0 {
		return nil
	}
	dst := make(map[string]string, len(src))
	for k, v := range src {
		dst[k] = v
	}
	return dst
}

func parseAliasFieldsFromParams(params map[string]string) []string {
	if len(params) == 0 {
		return nil
	}
	raw := strings.TrimSpace(params["alias_fields"])
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		field := strings.TrimSpace(part)
		if field == "" {
			continue
		}
		out = append(out, field)
	}
	return out
}

func suppressAliasDropDebug(task model.MetricsTask, debug map[string]string) map[string]string {
	if len(debug) == 0 {
		return debug
	}
	aliases := parseAliasFieldsFromParams(task.Params)
	if len(aliases) == 0 {
		return debug
	}
	aliasSet := make(map[string]struct{}, len(aliases))
	for _, alias := range aliases {
		trimmed := strings.TrimSpace(alias)
		if trimmed == "" {
			continue
		}
		aliasSet["dropped."+trimmed] = struct{}{}
	}
	filtered := make(map[string]string, len(debug))
	for key, value := range debug {
		if _, skip := aliasSet[key]; skip {
			continue
		}
		filtered[key] = value
	}
	if len(filtered) == 0 {
		return nil
	}
	return filtered
}

type redisCycleCache struct {
	mu sync.RWMutex
	m  map[string]map[string]string
}

func newRedisCycleCache() *redisCycleCache {
	return &redisCycleCache{m: map[string]map[string]string{}}
}

func (c *redisCycleCache) Get(key string) (map[string]string, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok := c.m[key]
	if !ok {
		return nil, false
	}
	return cloneStringMap(v), true
}

func (c *redisCycleCache) Set(key string, fields map[string]string) {
	if key == "" || fields == nil {
		return
	}
	c.mu.Lock()
	c.m[key] = cloneStringMap(fields)
	c.mu.Unlock()
}

func redisCacheKey(params map[string]string) string {
	if len(params) == 0 {
		return ""
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		return ""
	}
	if port == "" {
		port = "6379"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	return strings.Join([]string{host, port, user, pass}, "|")
}

type jdbcCycleCache struct {
	mu sync.RWMutex
	m  map[string]map[string]string
}

func newJDBCCycleCache() *jdbcCycleCache {
	return &jdbcCycleCache{m: map[string]map[string]string{}}
}

func (c *jdbcCycleCache) Get(key string) (map[string]string, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok := c.m[key]
	if !ok {
		return nil, false
	}
	return cloneStringMap(v), true
}

func (c *jdbcCycleCache) Set(key string, fields map[string]string) {
	if key == "" || fields == nil {
		return
	}
	c.mu.Lock()
	c.m[key] = cloneStringMap(fields)
	c.mu.Unlock()
}

func jdbcCacheKey(params map[string]string) string {
	if len(params) == 0 {
		return ""
	}
	sqlText := strings.TrimSpace(params["sql"])
	queryType := strings.TrimSpace(strings.ToLower(params["queryType"]))
	if sqlText == "" {
		return ""
	}
	if queryType == "" {
		queryType = "columns"
	}
	platform := strings.TrimSpace(strings.ToLower(params["platform"]))
	if platform == "" {
		platform = strings.TrimSpace(strings.ToLower(params["driver"]))
	}
	if platform == "" {
		platform = "mysql"
	}
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		return strings.Join([]string{"url", rawURL, queryType, sqlText}, "|")
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	db := strings.TrimSpace(params["database"])
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	timeout := strings.TrimSpace(params["timeout"])
	return strings.Join([]string{platform, host, port, db, user, pass, timeout, queryType, sqlText}, "|")
}

func mergeDebug(target map[string]string, extra map[string]string) {
	if len(extra) == 0 {
		return
	}
	for k, v := range extra {
		target[k] = v
	}
}

func compactSQL(raw string) string {
	text := strings.Join(strings.Fields(strings.TrimSpace(raw)), " ")
	if len(text) > 180 {
		return text[:177] + "..."
	}
	return text
}

func maskCacheKey(key string) string {
	if key == "" {
		return ""
	}
	parts := strings.Split(key, "|")
	if len(parts) >= 6 {
		parts[5] = "***"
	}
	return strings.Join(parts, "|")
}

func (d *Dispatcher) pushResult(ctx context.Context, result model.Result) {
	pushCtx, cancel := context.WithTimeout(ctx, d.defaultWait)
	defer cancel()
	if err := d.queue.Push(pushCtx, result); err != nil {
		d.dropped.Add(1)
		log.Printf("push result failed code=%s job=%d metrics=%s err=%v", model.CodeQueueFailed, result.JobID, result.Metrics, err)
	}
}
