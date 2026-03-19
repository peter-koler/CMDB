package snmpcollector

import (
	"context"
	"strings"
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

func TestCollectSnmpV3Args(t *testing.T) {
	orig := runSNMPCmd
	t.Cleanup(func() { runSNMPCmd = orig })
	runSNMPCmd = func(ctx context.Context, bin string, args ...string) (string, error) {
		joined := " " + strings.Join(args, " ") + " "
		required := []string{
			" -v3 ",
			" -l authPriv ",
			" -u ops-user ",
			" -a SHA ",
			" -A auth-pass ",
			" -x AES ",
			" -X priv-pass ",
			" -n ctx-1 ",
		}
		for _, token := range required {
			if !strings.Contains(joined, token) {
				t.Fatalf("missing token %q in args: %v", token, args)
			}
		}
		if strings.Contains(joined, " -c ") {
			t.Fatalf("v3 should not pass community args: %v", args)
		}
		return `iso = STRING: "core-switch-01"`, nil
	}

	c := &Collector{}
	fields, msg, err := c.Collect(context.Background(), model.MetricsTask{
		Protocol: "snmp",
		Timeout:  3 * time.Second,
		Params: map[string]string{
			"host":                   "10.0.0.10",
			"port":                   "161",
			"version":                "3",
			"username":               "ops-user",
			"contextName":            "ctx-1",
			"authPassphrase":         "auth-pass",
			"authPasswordEncryption": "1",
			"privPassphrase":         "priv-pass",
			"privPasswordEncryption": "1",
			"operation":              "get",
			"oids.name":              "1.3.6.1.2.1.1.5.0",
		},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("unexpected msg: %s", msg)
	}
	if fields["name"] != "core-switch-01" {
		t.Fatalf("unexpected fields: %+v", fields)
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
