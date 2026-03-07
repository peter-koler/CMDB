package precompute

import (
	"testing"

	"collector-go/internal/model"
)

func TestEvaluatorThreshold(t *testing.T) {
	ev := New(true, []Rule{
		{
			Metrics:   "cpu",
			Protocol:  "linux",
			Field:     "usage",
			Op:        ">",
			Threshold: 80,
			Summary:   "cpu high",
		},
	})
	task := model.MetricsTask{Name: "cpu", Protocol: "linux"}
	ok, summary := ev.Evaluate(task, map[string]string{"usage": "90"})
	if !ok {
		t.Fatal("expected precompute hit")
	}
	if summary != "cpu high" {
		t.Fatalf("summary mismatch: %s", summary)
	}
}

func TestEvaluatorDisabled(t *testing.T) {
	ev := New(false, []Rule{{
		Field:     "usage",
		Op:        ">",
		Threshold: 80,
	}})
	task := model.MetricsTask{Name: "cpu", Protocol: "linux"}
	ok, summary := ev.Evaluate(task, map[string]string{"usage": "90"})
	if ok || summary != "" {
		t.Fatalf("expected disabled evaluator no output, got ok=%v summary=%s", ok, summary)
	}
}
