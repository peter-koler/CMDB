package dispatcher

import (
	"context"
	"sync/atomic"
	"testing"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
	"collector-go/internal/queue"
	"collector-go/internal/scheduler"
	"collector-go/internal/worker"
)

type testCollector struct {
	count atomic.Int32
}

func (c *testCollector) Collect(context.Context, model.MetricsTask) (map[string]string, string, error) {
	c.count.Add(1)
	return map[string]string{"v": "1"}, "ok", nil
}

type redisCacheCollector struct {
	count atomic.Int32
}

func (c *redisCacheCollector) Collect(_ context.Context, task model.MetricsTask) (map[string]string, string, error) {
	c.count.Add(1)
	if task.Params["section"] == "" {
		return map[string]string{
			"used_memory":       "100",
			"connected_clients": "10",
			"identity":          "127.0.0.1:6379",
		}, "ok", nil
	}
	return map[string]string{
		"identity": task.Params["host"] + ":" + task.Params["port"],
		"section":  task.Params["section"],
	}, "ok", nil
}

type jdbcCacheCollector struct {
	count atomic.Int32
}

func (c *jdbcCacheCollector) Collect(_ context.Context, task model.MetricsTask) (map[string]string, string, error) {
	c.count.Add(1)
	return map[string]string{
		"query": task.Params["sql"],
		"rows":  "1",
	}, "ok", nil
}

type testPrecompute struct{}

func (testPrecompute) Enabled() bool { return true }
func (testPrecompute) Evaluate(task model.MetricsTask, fields map[string]string) (bool, string) {
	if task.Name == "m1" && fields["v"] == "1" {
		return true, "v high"
	}
	return false, ""
}

func TestRegisterAndRemoveJob(t *testing.T) {
	tc := &testCollector{}
	protocol.Register("mock_dispatcher", tc)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	wheel := scheduler.NewWheel(10*time.Millisecond, 64)
	pool := worker.New(2, 32)
	q := queue.NewMemoryQueue(128)
	d := New(wheel, pool, q)
	d.SetPrecomputeEvaluator(testPrecompute{})

	pool.Start(ctx)
	go wheel.Start(ctx)

	job := model.Job{
		ID:       1001,
		Monitor:  2001,
		App:      "test",
		Interval: 30 * time.Millisecond,
		Tasks: []model.MetricsTask{
			{
				Name:     "m1",
				Protocol: "mock_dispatcher",
				Timeout:  time.Second,
				Priority: 1,
			},
		},
	}
	d.RegisterJob(job)
	time.Sleep(150 * time.Millisecond)
	before := tc.count.Load()
	if before == 0 {
		t.Fatal("expected task executions before remove")
	}

	d.RemoveJob(job.ID)
	time.Sleep(120 * time.Millisecond)
	after := tc.count.Load()
	if after != before {
		t.Fatalf("expected no more executions after remove, before=%d after=%d", before, after)
	}

	popCtx, popCancel := context.WithTimeout(ctx, 100*time.Millisecond)
	defer popCancel()
	got, err := q.Pop(popCtx)
	if err != nil {
		t.Fatalf("expected one result to verify precompute fields, err=%v", err)
	}
	if got.Fields["v"] != "1" {
		t.Fatalf("raw field changed unexpectedly: %+v", got.Fields)
	}
	if got.Fields["__precompute_triggered__"] != "true" {
		t.Fatalf("expected precompute trigger marker, got %+v", got.Fields)
	}
	if got.Fields["__precompute_summary__"] == "" {
		t.Fatalf("expected precompute summary, got %+v", got.Fields)
	}
}

func TestRedisCycleCacheReuse(t *testing.T) {
	rc := &redisCacheCollector{}
	protocol.Register("redis", rc)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	wheel := scheduler.NewWheel(10*time.Millisecond, 64)
	pool := worker.New(2, 64)
	q := queue.NewMemoryQueue(128)
	d := New(wheel, pool, q)

	pool.Start(ctx)
	go wheel.Start(ctx)

	job := model.Job{
		ID:       2001,
		Monitor:  3001,
		App:      "redis",
		Interval: 40 * time.Millisecond,
		Tasks: []model.MetricsTask{
			{
				Name:     "memory",
				Protocol: "redis",
				Timeout:  time.Second,
				Priority: 1,
				Params: map[string]string{
					"host":    "127.0.0.1",
					"port":    "6379",
					"section": "memory",
				},
				FieldSpecs: []model.FieldSpec{{Field: "used_memory"}},
			},
			{
				Name:     "clients",
				Protocol: "redis",
				Timeout:  time.Second,
				Priority: 2,
				Params: map[string]string{
					"host":    "127.0.0.1",
					"port":    "6379",
					"section": "clients",
				},
				FieldSpecs: []model.FieldSpec{{Field: "connected_clients"}},
			},
		},
	}

	d.RegisterJob(job)
	time.Sleep(120 * time.Millisecond)
	d.RemoveJob(job.ID)

	// At least one cycle should execute; each cycle should fetch Redis once due to cache reuse.
	// With ~3 cycles in 120ms this should stay <= 4 (allowing timer jitter).
	if rc.count.Load() > 4 {
		t.Fatalf("expected redis collect reuse, too many collects: %d", rc.count.Load())
	}
}

func TestJDBCCycleCacheReuse(t *testing.T) {
	jc := &jdbcCacheCollector{}
	protocol.Register("jdbc", jc)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	wheel := scheduler.NewWheel(10*time.Millisecond, 64)
	pool := worker.New(2, 64)
	q := queue.NewMemoryQueue(128)
	d := New(wheel, pool, q)

	pool.Start(ctx)
	go wheel.Start(ctx)

	job := model.Job{
		ID:       3001,
		Monitor:  4001,
		App:      "mysql",
		Interval: 40 * time.Millisecond,
		Tasks: []model.MetricsTask{
			{
				Name:     "cache_a",
				Protocol: "jdbc",
				Timeout:  time.Second,
				Priority: 1,
				Params: map[string]string{
					"host":      "127.0.0.1",
					"port":      "3306",
					"username":  "root",
					"password":  "pwd",
					"database":  "mysql",
					"queryType": "columns",
					"sql":       "show global status like 'Qcache%';",
				},
			},
			{
				Name:     "cache_b",
				Protocol: "jdbc",
				Timeout:  time.Second,
				Priority: 2,
				Params: map[string]string{
					"host":      "127.0.0.1",
					"port":      "3306",
					"username":  "root",
					"password":  "pwd",
					"database":  "mysql",
					"queryType": "columns",
					"sql":       "show global status like 'Qcache%';",
				},
			},
		},
	}

	d.RegisterJob(job)
	time.Sleep(120 * time.Millisecond)
	d.RemoveJob(job.ID)

	// Each cycle should execute the same SQL once due to jdbc cache reuse.
	if jc.count.Load() > 4 {
		t.Fatalf("expected jdbc collect reuse, too many collects: %d", jc.count.Load())
	}
}
