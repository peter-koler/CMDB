package alert

import (
	"testing"
	"time"
)

func TestGroupReduce(t *testing.T) {
	r := NewReducer(60*time.Second, 5*time.Minute, nil)
	now := time.Unix(1000, 0)
	ev := Event{RuleID: 1, MonitorID: 10, Severity: "warning", State: StateFiring}

	d1 := r.Process(ev, now)
	if !d1.Emit {
		t.Fatalf("first should emit, got %+v", d1)
	}
	d2 := r.Process(ev, now.Add(10*time.Second))
	if d2.Emit || d2.SuppressedBy != "group" {
		t.Fatalf("second should be group suppressed, got %+v", d2)
	}
}

func TestInhibitReduce(t *testing.T) {
	r := NewReducer(60*time.Second, 5*time.Minute, nil)
	now := time.Unix(1000, 0)
	critical := Event{RuleID: 1, MonitorID: 10, Severity: "critical", State: StateFiring}
	warning := Event{RuleID: 2, MonitorID: 10, Severity: "warning", State: StateFiring}

	d1 := r.Process(critical, now)
	if !d1.Emit {
		t.Fatalf("critical should emit, got %+v", d1)
	}
	d2 := r.Process(warning, now.Add(time.Second))
	if d2.Emit || d2.SuppressedBy != "inhibit" {
		t.Fatalf("warning should be inhibited, got %+v", d2)
	}
}

func TestSilenceReduce(t *testing.T) {
	r := NewReducer(60*time.Second, 5*time.Minute, []SilenceRule{
		{MonitorID: 10, RuleID: 3, StartHour: 1, EndHour: 3},
	})
	// 02:00 local hour -> inside silence window.
	now := time.Date(2026, 3, 7, 2, 0, 0, 0, time.Local)
	ev := Event{RuleID: 3, MonitorID: 10, Severity: "critical", State: StateFiring}
	d := r.Process(ev, now)
	if d.Emit || d.SuppressedBy != "silence" {
		t.Fatalf("event should be silenced, got %+v", d)
	}
}

func TestConfiguredInhibitReduce(t *testing.T) {
	r := NewReducer(60*time.Second, 5*time.Minute, nil)
	r.UpdateRules(nil, []InhibitRule{
		{
			ID:           1,
			SourceLabels: map[string]string{"severity": "critical", "app": "redis"},
			TargetLabels: map[string]string{"severity": "warning", "app": "redis"},
			EqualLabels:  []string{"instance"},
		},
	}, nil)

	now := time.Unix(1000, 0)
	critical := Event{RuleID: 11, RuleName: "critical", MonitorID: 10, Severity: "critical", App: "redis", Instance: "10.0.0.1:6379", State: StateFiring}
	warning := Event{RuleID: 12, RuleName: "warning", MonitorID: 10, Severity: "warning", App: "redis", Instance: "10.0.0.1:6379", State: StateFiring}

	d1 := r.Process(critical, now)
	if !d1.Emit {
		t.Fatalf("critical should emit, got %+v", d1)
	}
	d2 := r.Process(warning, now.Add(time.Second))
	if d2.Emit || d2.SuppressedBy != "inhibit" {
		t.Fatalf("warning should be inhibited by configured rule, got %+v", d2)
	}
}

func TestConfiguredCyclicSilenceReduce(t *testing.T) {
	r := NewReducer(60*time.Second, 5*time.Minute, nil)
	r.UpdateRules(nil, nil, []SilenceRule{
		{
			ID:        1,
			Type:      1,
			MatchType: 1,
			Labels:    map[string]string{"app": "redis"},
			Days:      map[int]struct{}{6: {}},
			StartAtMs: time.Date(2026, 3, 7, 1, 0, 0, 0, time.Local).UnixMilli(),
			EndAtMs:   time.Date(2026, 3, 7, 3, 0, 0, 0, time.Local).UnixMilli(),
		},
	})
	now := time.Date(2026, 3, 7, 2, 0, 0, 0, time.Local) // Saturday
	ev := Event{RuleID: 3, MonitorID: 10, Severity: "critical", App: "redis", State: StateFiring}
	d := r.Process(ev, now)
	if d.Emit || d.SuppressedBy != "silence" {
		t.Fatalf("event should be silenced by cyclic rule, got %+v", d)
	}
}

func TestGroupRepeatIntervalReduce(t *testing.T) {
	r := NewReducer(10*time.Second, 5*time.Minute, nil)
	r.UpdateRules([]GroupRule{
		{
			ID:             1,
			GroupKey:       "redis-group",
			GroupLabels:    []string{"app"},
			GroupInterval:  5 * time.Second,
			RepeatInterval: 30 * time.Second,
		},
	}, nil, nil)
	now := time.Unix(1000, 0)
	ev := Event{RuleID: 10, MonitorID: 10, Severity: "warning", App: "redis", State: StateFiring}
	d1 := r.Process(ev, now)
	if !d1.Emit {
		t.Fatalf("first should emit, got %+v", d1)
	}
	d2 := r.Process(ev, now.Add(6*time.Second))
	if d2.Emit || d2.SuppressedBy != "repeat" {
		t.Fatalf("second should be repeat suppressed, got %+v", d2)
	}
	d3 := r.Process(ev, now.Add(31*time.Second))
	if !d3.Emit {
		t.Fatalf("third should emit after repeat interval, got %+v", d3)
	}
}
