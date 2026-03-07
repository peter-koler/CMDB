package alert

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"
)

type flakySender struct {
	failFirst int32
	calls     int32
}

func (f *flakySender) Send(_ context.Context, _ NotifyTask) error {
	n := atomic.AddInt32(&f.calls, 1)
	if n <= f.failFirst {
		return errors.New("send failed")
	}
	return nil
}

func TestAsyncQueuesRetryFlow(t *testing.T) {
	sender := &flakySender{failFirst: 2}
	q := NewQueues(64, []time.Duration{10 * time.Millisecond, 10 * time.Millisecond}, 5)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	q.Start(ctx, sender, 1, 1)

	ok := q.EnqueueAlert(Event{
		RuleID:    1,
		RuleName:  "r1",
		MonitorID: 1001,
		Severity:  "warning",
		State:     StateFiring,
	})
	if !ok {
		t.Fatal("enqueue alert failed")
	}

	deadline := time.After(500 * time.Millisecond)
	for {
		if atomic.LoadInt32(&sender.calls) >= 3 {
			return
		}
		select {
		case <-deadline:
			t.Fatalf("expected retries to happen, calls=%d", atomic.LoadInt32(&sender.calls))
		case <-time.After(10 * time.Millisecond):
		}
	}
}
