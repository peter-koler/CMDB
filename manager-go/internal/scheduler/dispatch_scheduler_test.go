package scheduler

import (
	"context"
	"testing"
	"time"

	"manager-go/internal/model"
	"manager-go/internal/store"
)

func TestDisableStopsDispatchWithinTenSeconds(t *testing.T) {
	st := store.NewMonitorStore()
	m, err := st.Create(model.MonitorCreateInput{
		Name:            "m1",
		App:             "linux",
		Target:          "127.0.0.1",
		TemplateID:      1,
		IntervalSeconds: 10,
		Enabled:         true,
	})
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}

	out := make(chan int64, 16)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	s := NewDispatchScheduler(st, 100*time.Millisecond, out)
	go s.Start(ctx)

	select {
	case <-out:
	case <-time.After(2 * time.Second):
		t.Fatal("expected first dispatch event")
	}

	m, err = st.SetEnabled(m.ID, false, m.Version)
	if err != nil {
		t.Fatalf("disable failed: %v", err)
	}

	select {
	case got := <-out:
		t.Fatalf("expected no dispatch after disable, got id=%d", got)
	case <-time.After(1500 * time.Millisecond):
	}
}
