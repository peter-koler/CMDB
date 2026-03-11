package pipeline

import (
	"testing"

	"collector-go/internal/model"
)

func TestApplyCalculates_MySQLQueryCacheHitRate(t *testing.T) {
	in := map[string]string{
		"Qcache_hits":    "100",
		"Qcache_inserts": "20",
	}
	calcs := []model.CalculateSpec{
		{
			Field:      "query_cache_hit_rate",
			Expression: "(Qcache_hits + 1) / (Qcache_hits + Qcache_inserts + 1) * 100",
		},
	}
	got, debug := ApplyCalculates(in, calcs)
	if len(debug) != 0 {
		t.Fatalf("unexpected debug: %+v", debug)
	}
	if got["query_cache_hit_rate"] != "83.47107438016529" {
		t.Fatalf("unexpected calculate result: %s", got["query_cache_hit_rate"])
	}
}

func TestApplyCalculates_KeepOriginalOnFailure(t *testing.T) {
	in := map[string]string{
		"cache_hits": "12",
	}
	calcs := []model.CalculateSpec{
		{
			Field:      "cache_hits",
			Expression: "unknown_field + 1",
		},
	}
	got, debug := ApplyCalculates(in, calcs)
	if got["cache_hits"] != "12" {
		t.Fatalf("expected original value kept, got: %s", got["cache_hits"])
	}
	if debug["calculate.cache_hits"] == "" {
		t.Fatalf("expected debug reason, got: %+v", debug)
	}
}

func TestApplyFieldWhitelist(t *testing.T) {
	in := map[string]string{
		"cache_hits":           "12",
		"query_cache_hit_rate": "80",
		"raw_dynamic_field":    "xxx",
	}
	specs := []model.FieldSpec{
		{Field: "cache_hits"},
		{Field: "query_cache_hit_rate"},
	}
	got, debug := ApplyFieldWhitelist(in, specs, true)
	if len(got) != 2 {
		t.Fatalf("expected 2 fields after whitelist, got: %+v", got)
	}
	if got["raw_dynamic_field"] != "" {
		t.Fatalf("unexpected raw field still exists: %+v", got)
	}
	if debug["dropped.raw_dynamic_field"] == "" {
		t.Fatalf("expected dropped debug, got: %+v", debug)
	}
}
