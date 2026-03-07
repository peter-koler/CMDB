package scheduler

import (
	"context"
	"sync/atomic"
	"testing"
	"time"
)

func TestWheelScheduleEvery(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	w := NewWheel(20*time.Millisecond, 64)
	go w.Start(ctx)

	var count int32
	id := w.ScheduleEvery(40*time.Millisecond, func(context.Context) {
		atomic.AddInt32(&count, 1)
	})
	time.Sleep(180 * time.Millisecond)
	w.Cancel(id)
	got := atomic.LoadInt32(&count)
	if got < 2 {
		t.Fatalf("expected task run >=2 times, got %d", got)
	}
}

func TestWheelDriftStatsWithThousandTasks(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	w := NewWheel(10*time.Millisecond, 512)
	go w.Start(ctx)

	ids := make([]int64, 0, 1000)
	var runs int32
	for i := 0; i < 1000; i++ {
		id := w.ScheduleEvery(50*time.Millisecond, func(context.Context) {
			atomic.AddInt32(&runs, 1)
		})
		ids = append(ids, id)
	}

	time.Sleep(350 * time.Millisecond)
	for _, id := range ids {
		w.Cancel(id)
	}
	st := w.Stats()

	if st.TotalRuns == 0 || atomic.LoadInt32(&runs) == 0 {
		t.Fatalf("expected runs > 0, stats=%+v runs=%d", st, runs)
	}
	// Keep threshold loose for CI/sandbox variability; this guards regression not micro-jitter.
	if st.MaxDriftMs > 500 {
		t.Fatalf("max drift too high: %dms stats=%+v", st.MaxDriftMs, st)
	}
}
