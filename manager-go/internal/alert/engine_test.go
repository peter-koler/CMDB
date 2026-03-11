package alert

import (
	"testing"
	"time"
)

func TestExpressionOperatorsCoverage(t *testing.T) {
	e := NewEngine()
	rules := []Rule{
		{ID: 1, Name: "gt", Expression: "cpu > 80", DurationSeconds: 1, Enabled: true},
		{ID: 2, Name: "ge", Expression: "cpu >= 85", DurationSeconds: 1, Enabled: true},
		{ID: 3, Name: "lt", Expression: "mem < 60", DurationSeconds: 1, Enabled: true},
		{ID: 4, Name: "le", Expression: "mem <= 50", DurationSeconds: 1, Enabled: true},
		{ID: 5, Name: "eq", Expression: "err == 0", DurationSeconds: 1, Enabled: true},
		{ID: 6, Name: "ne", Expression: "disk != 90", DurationSeconds: 1, Enabled: true},
		{ID: 7, Name: "and", Expression: "cpu > 80 && mem < 60", DurationSeconds: 1, Enabled: true},
		{ID: 8, Name: "or", Expression: "cpu > 90 || mem < 60", DurationSeconds: 1, Enabled: true},
	}
	vars := map[string]float64{
		"cpu":  85,
		"mem":  50,
		"err":  0,
		"disk": 88,
	}
	now := time.Now()
	for _, r := range rules {
		ev, matched, err := e.Evaluate(r, 1001, vars, now)
		if err != nil {
			t.Fatalf("rule %s eval error: %v", r.Name, err)
		}
		if !matched {
			t.Fatalf("rule %s expected matched", r.Name)
		}
		if ev.State != StateFiring {
			t.Fatalf("rule %s first hit should be firing when times=1, got=%s", r.Name, ev.State)
		}
	}
}

func TestDurationDebounceWindow(t *testing.T) {
	e := NewEngine()
	rule := Rule{
		ID:              101,
		Name:            "cpu-high",
		Expression:      "cpu > 80",
		DurationSeconds: 3,
		Severity:        "critical",
		Enabled:         true,
	}
	vars := map[string]float64{"cpu": 95}
	t0 := time.Unix(1000, 0)

	ev, matched, err := e.Evaluate(rule, 1, vars, t0)
	if err != nil || !matched || ev.State != StatePending {
		t.Fatalf("t0 expect pending, got state=%s matched=%v err=%v", ev.State, matched, err)
	}
	ev, matched, err = e.Evaluate(rule, 1, vars, t0.Add(2*time.Second))
	if err != nil || !matched || ev.State != StatePending {
		t.Fatalf("t0+2s expect pending, got state=%s matched=%v err=%v", ev.State, matched, err)
	}
	ev, matched, err = e.Evaluate(rule, 1, vars, t0.Add(3*time.Second))
	if err != nil || !matched || ev.State != StateFiring {
		t.Fatalf("t0+3s expect firing, got state=%s matched=%v err=%v", ev.State, matched, err)
	}

	ev, matched, err = e.Evaluate(rule, 1, map[string]float64{"cpu": 20}, t0.Add(4*time.Second))
	if err != nil || !matched || ev.State != StateNormal {
		t.Fatalf("recover expect normal, got state=%s matched=%v err=%v", ev.State, matched, err)
	}
}

func TestArithmeticExpressionSupport(t *testing.T) {
	e := NewEngine()
	rule := Rule{
		ID:              201,
		Name:            "redis-memory-ratio",
		Expression:      "(used_memory / maxmemory) * 100 > 85 && (connected_clients / maxclients) > 0.8",
		DurationSeconds: 1,
		Enabled:         true,
	}
	vars := map[string]float64{
		"used_memory":       900,
		"maxmemory":         1000,
		"connected_clients": 85,
		"maxclients":        100,
	}
	ev, matched, err := e.Evaluate(rule, 77, vars, time.Unix(2000, 0))
	if err != nil {
		t.Fatalf("eval error: %v", err)
	}
	if !matched || ev.State != StateFiring {
		t.Fatalf("expected firing match when times=1, got matched=%v state=%s", matched, ev.State)
	}
}

func TestExpressionUnknownVariable(t *testing.T) {
	e := NewEngine()
	rule := Rule{
		ID:              202,
		Name:            "missing-var",
		Expression:      "(used_memory / maxmemory) > 0.9",
		DurationSeconds: 1,
		Enabled:         true,
	}
	_, _, err := e.Evaluate(rule, 1, map[string]float64{"used_memory": 1}, time.Now())
	if err == nil {
		t.Fatal("expected error for unknown variable")
	}
}
