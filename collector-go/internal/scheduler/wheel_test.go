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
