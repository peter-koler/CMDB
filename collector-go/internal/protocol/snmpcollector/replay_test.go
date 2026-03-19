package snmpcollector

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestReplayWindowsWalkSample(t *testing.T) {
	orig := runSNMPCmd
	t.Cleanup(func() { runSNMPCmd = orig })

	sampleName := strings.Join([]string{
		`HOST-RESOURCES-MIB::hrSWRunName.1 = STRING: "System Idle Process"`,
		`HOST-RESOURCES-MIB::hrSWRunName.2 = STRING: "System"`,
		`HOST-RESOURCES-MIB::hrSWRunName.3 = STRING: "smss.exe"`,
	}, "\n")
	sampleStatus := strings.Join([]string{
		"HOST-RESOURCES-MIB::hrSWRunStatus.1 = INTEGER: running(1)",
		"HOST-RESOURCES-MIB::hrSWRunStatus.2 = INTEGER: runnable(2)",
		"HOST-RESOURCES-MIB::hrSWRunStatus.3 = INTEGER: running(1)",
	}, "\n")

	runSNMPCmd = func(ctx context.Context, bin string, args ...string) (string, error) {
		oid := args[len(args)-1]
		if bin != "snmpwalk" {
			return "", fmt.Errorf("unexpected bin %s", bin)
		}
		switch oid {
		case "1.3.6.1.2.1.25.4.2.1.2":
			return sampleName, nil
		case "1.3.6.1.2.1.25.4.2.1.7":
			return sampleStatus, nil
		default:
			return "", fmt.Errorf("unexpected oid %s", oid)
		}
	}

	c := &Collector{}
	fields, msg, err := c.Collect(context.Background(), model.MetricsTask{
		Protocol: "snmp",
		Timeout:  3 * time.Second,
		Params: map[string]string{
			"host":               "127.0.0.1",
			"community":          "public",
			"operation":          "walk",
			"oids.hrSWRunName":   "1.3.6.1.2.1.25.4.2.1.2",
			"oids.hrSWRunStatus": "1.3.6.1.2.1.25.4.2.1.7",
		},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("unexpected msg: %s", msg)
	}
	if fields["hrSWRunName_count"] != "3" || fields["hrSWRunStatus_count"] != "3" {
		t.Fatalf("unexpected count fields: %+v", fields)
	}
	if fields["row1_hrSWRunName"] != "System Idle Process" || fields["row3_hrSWRunName"] != "smss.exe" {
		t.Fatalf("unexpected row fields: %+v", fields)
	}
	if fields["row2_hrSWRunStatus"] != "2" {
		t.Fatalf("unexpected status parse: %+v", fields)
	}
}
