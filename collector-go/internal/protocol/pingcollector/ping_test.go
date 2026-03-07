package pingcollector

import (
	"context"
	"testing"

	"collector-go/internal/model"
)

func TestCollectMissingHost(t *testing.T) {
	c := &Collector{}
	_, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "m1",
		Protocol: "icmp",
		Params:   map[string]string{},
	})
	if err == nil {
		t.Fatal("expected missing host error")
	}
}

func TestParsePingLatency(t *testing.T) {
	s := "64 bytes from 1.1.1.1: icmp_seq=1 ttl=56 time=12.3 ms"
	got := parsePingLatencyMs(s)
	if got != 12.3 {
		t.Fatalf("want 12.3 got %.2f", got)
	}
}
