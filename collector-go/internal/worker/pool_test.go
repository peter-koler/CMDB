package worker

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestPoolLimitsConcurrency(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	p := New(2, 32)
	p.Start(ctx)
	defer p.Stop()

	var current int32
	var maxSeen int32
	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		err := p.Submit(func(ctx context.Context) {
			defer wg.Done()
			now := atomic.AddInt32(&current, 1)
			for {
				old := atomic.LoadInt32(&maxSeen)
				if now <= old || atomic.CompareAndSwapInt32(&maxSeen, old, now) {
					break
				}
			}
			time.Sleep(20 * time.Millisecond)
			atomic.AddInt32(&current, -1)
		})
		if err != nil {
			wg.Done()
		}
	}
	wg.Wait()
	if maxSeen > 2 {
		t.Fatalf("expected max concurrency <= 2, got %d", maxSeen)
	}
}
