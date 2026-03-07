package linuxcollector

import (
	"context"
	"testing"

	"collector-go/internal/model"
)

func TestParseMemInfo(t *testing.T) {
	meminfo := `MemTotal:       8000000 kB
MemAvailable:   2000000 kB
`
	got := parseMemInfo(meminfo)
	if got["memtotal_kb"] != "8000000" {
		t.Fatalf("memtotal_kb mismatch: %v", got["memtotal_kb"])
	}
	if got["memavailable_kb"] != "2000000" {
		t.Fatalf("memavailable_kb mismatch: %v", got["memavailable_kb"])
	}
	if got["mem_used_pct"] == "" {
		t.Fatalf("mem_used_pct should be generated: %+v", got)
	}
}

func TestCollectBasicFields(t *testing.T) {
	c := &Collector{}
	fields, msg, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "linux_basic",
		Protocol: "linux",
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("expected ok msg, got %s", msg)
	}
	if fields["goos"] == "" || fields["cpu"] == "" {
		t.Fatalf("expected goos/cpu fields, got %+v", fields)
	}
}
