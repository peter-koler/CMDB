package alert

import (
	"context"
	"testing"
	"time"
)

type mockQuerier struct {
	values []float64
	idx    int
}

func (m *mockQuerier) QueryValue(_ context.Context, _ string, _ time.Time) (float64, error) {
	if len(m.values) == 0 {
		return 0, nil
	}
	if m.idx >= len(m.values) {
		return m.values[len(m.values)-1], nil
	}
	v := m.values[m.idx]
	m.idx++
	return v, nil
}

func TestPeriodicRuleFiveMinuteWindowStableTrigger(t *testing.T) {
	engine := NewEngine()
	q := &mockQuerier{values: []float64{85, 86}}
	eval := NewPeriodicEvaluator(engine, q, []PeriodicRule{
		{
			ID:              2001,
			Name:            "cpu-5m-high",
			PromQL:          `avg_over_time(cpu_usage[5m])`,
			Expression:      "value > 80",
			DurationSeconds: 300,
			Severity:        "warning",
			Interval:        5 * time.Minute,
			Enabled:         true,
		},
	})
	t0 := time.Unix(1000, 0)
	r0 := eval.RunDue(context.Background(), 1001, t0)
	if len(r0) != 1 || r0[0].Event.State != StatePending {
		t.Fatalf("first run expect pending, got=%v", r0)
	}
	r1 := eval.RunDue(context.Background(), 1001, t0.Add(5*time.Minute))
	if len(r1) != 1 || r1[0].Event.State != StateFiring {
		t.Fatalf("second run expect firing, got=%v", r1)
	}
}
