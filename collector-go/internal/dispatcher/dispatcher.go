package dispatcher

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/pipeline"
	"collector-go/internal/protocol"
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
	tasks := append([]model.MetricsTask(nil), job.Tasks...)
	// HertzBeat-like semantics: smaller priority means higher priority.
	sort.Slice(tasks, func(i, j int) bool { return tasks[i].Priority < tasks[j].Priority })
	job.Tasks = tasks
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

func (d *Dispatcher) executeJobCycle(ctx context.Context, job model.Job) {
	if len(job.Tasks) == 0 {
		return
	}
	redisCache := newRedisCycleCache()
	jdbcCache := newJDBCCycleCache()
	valueStore := newCycleValueStore()
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
	redisCache.Set(key, fields)
	return materializeRedisFields(task, fields), msg, nil
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
		return cached, "ok(cache)", nil
	}
	fields, msg, err := collector.Collect(ctx, task)
	if err != nil {
		return nil, msg, err
	}
	jdbcCache.Set(key, fields)
	return cloneStringMap(fields), msg, nil
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

func (d *Dispatcher) pushResult(ctx context.Context, result model.Result) {
	pushCtx, cancel := context.WithTimeout(ctx, d.defaultWait)
	defer cancel()
	if err := d.queue.Push(pushCtx, result); err != nil {
		d.dropped.Add(1)
		log.Printf("push result failed code=%s job=%d metrics=%s err=%v", model.CodeQueueFailed, result.JobID, result.Metrics, err)
	}
}
