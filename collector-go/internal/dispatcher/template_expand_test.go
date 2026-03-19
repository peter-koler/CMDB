package dispatcher

import (
	"testing"

	"collector-go/internal/model"
)

func TestCycleValueStoreResolve(t *testing.T) {
	store := newCycleValueStore()
	store.Save(map[string]string{
		"state":      "RUNNABLE",
		"row2_state": "WAITING",
		"name":       "route-a",
	})
	task := model.MetricsTask{
		Name: "threads",
		Params: map[string]string{
			"url": "/metrics/jvm.threads.states?tag=state:^o^state^o^",
		},
		CalculateSpecs: []model.CalculateSpec{
			{Field: "state", Expression: "'^o^state^o^'"},
		},
	}
	variants := store.Resolve(task)
	if len(variants) != 2 {
		t.Fatalf("expected 2 variants got=%d", len(variants))
	}
	if variants[0].Params["url"] == variants[1].Params["url"] {
		t.Fatalf("expected distinct resolved urls: %+v", variants)
	}
}

func TestMergeCollectedFields(t *testing.T) {
	merged := mergeCollectedFields([]map[string]string{
		{"state": "RUNNABLE", "Size": "3"},
		{"state": "WAITING", "Size": "5"},
	})
	if merged["state"] != "RUNNABLE" {
		t.Fatalf("state want RUNNABLE got=%s", merged["state"])
	}
	if merged["row2_state"] != "WAITING" {
		t.Fatalf("row2_state want WAITING got=%s", merged["row2_state"])
	}
}
