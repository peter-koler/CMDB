package dispatch

import (
	"context"
	"errors"
	"testing"
	"time"

	"manager-go/internal/model"
)

type mockSink struct {
	name         string
	failTimes    int
	callCount    int
	failAlways   bool
	lastWriteKey string
}

func (m *mockSink) Name() string { return m.name }

func (m *mockSink) Write(_ context.Context, key string, _ model.MetricPoint) error {
	m.callCount++
	m.lastWriteKey = key
	if m.failAlways {
		return errors.New("always failed")
	}
	if m.callCount <= m.failTimes {
		return errors.New("transient failed")
	}
	return nil
}

func basePoint() model.MetricPoint {
	return model.MetricPoint{
		MonitorID: 1,
		App:       "linux",
		Metrics:   "cpu",
		Field:     "usage",
		Value:     12.3,
		UnixMs:    1234567890,
		Instance:  "127.0.0.1:9100",
	}
}

func TestRetryAndIsolation(t *testing.T) {
	redis := &mockSink{name: "redis", failTimes: 1}
	vm := &mockSink{name: "victoria_metrics", failAlways: true}
	d := NewDispatcher(
		[]Sink{redis, vm},
		RetryPolicy{MaxAttempts: 3, Backoff: []time.Duration{time.Millisecond}},
		100,
	)
	res := d.Dispatch(context.Background(), basePoint())
	if res.Status["redis"] != "ok" {
		t.Fatalf("redis should succeed after retry, status=%s", res.Status["redis"])
	}
	if res.Status["victoria_metrics"] != "failed" {
		t.Fatalf("vm should fail, status=%s", res.Status["victoria_metrics"])
	}
	if redis.callCount != 2 {
		t.Fatalf("redis call count want=2 got=%d", redis.callCount)
	}
	if vm.callCount != 3 {
		t.Fatalf("vm call count want=3 got=%d", vm.callCount)
	}
}

func TestIdempotency(t *testing.T) {
	redis := &mockSink{name: "redis"}
	d := NewDispatcher(
		[]Sink{redis},
		RetryPolicy{MaxAttempts: 2, Backoff: []time.Duration{time.Millisecond}},
		100,
	)
	p := basePoint()
	r1 := d.Dispatch(context.Background(), p)
	r2 := d.Dispatch(context.Background(), p)
	if r1.Status["redis"] != "ok" {
		t.Fatalf("first dispatch should be ok, got=%s", r1.Status["redis"])
	}
	if r2.Status["redis"] != "deduplicated" {
		t.Fatalf("second dispatch should be deduplicated, got=%s", r2.Status["redis"])
	}
	if redis.callCount != 1 {
		t.Fatalf("sink should be called once, got=%d", redis.callCount)
	}
}
