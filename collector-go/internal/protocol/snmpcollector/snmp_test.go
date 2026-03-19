package snmpcollector

import (
	"context"
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestParseSNMPValue(t *testing.T) {
	if got := parseSNMPValue("iso.3.6 = INTEGER: 42"); got != "42" {
		t.Fatalf("unexpected integer parse: %q", got)
	}
	if got := parseSNMPValue(`iso.3.6 = STRING: "WIN-HOST"`); got != "WIN-HOST" {
		t.Fatalf("unexpected string parse: %q", got)
	}
	if got := parseSNMPValue("iso.3.6 = Timeticks: (12345) 1 day"); got != "12345" {
		t.Fatalf("unexpected timeticks parse: %q", got)
	}
}

func TestCollectMultiGet(t *testing.T) {
	orig := runSNMPCmd
	t.Cleanup(func() { runSNMPCmd = orig })
	runSNMPCmd = func(ctx context.Context, bin string, args ...string) (string, error) {
		if args[len(args)-1] == "1.3.6.1.2.1.1.5.0" {
			return `iso = STRING: "host-a"`, nil
		}
		return "iso = INTEGER: 10", nil
	}

	c := &Collector{}
	fields, msg, err := c.Collect(context.Background(), model.MetricsTask{
		Protocol: "snmp",
		Timeout:  3 * time.Second,
		Params: map[string]string{
			"host":      "127.0.0.1",
			"community": "public",
			"operation": "get",
			"oids.name": "1.3.6.1.2.1.1.5.0",
			"oids.cpu":  "1.3.6.1.4.1.x.y",
		},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("unexpected msg: %s", msg)
	}
	if fields["name"] != "host-a" || fields["cpu"] != "10" {
		t.Fatalf("unexpected fields: %+v", fields)
	}
}
