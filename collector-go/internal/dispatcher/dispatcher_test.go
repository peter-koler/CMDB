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
