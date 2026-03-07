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
