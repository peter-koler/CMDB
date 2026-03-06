package snmpcollector

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("snmp", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := task.Params["host"]
	oid := task.Params["oid"]
	community := task.Params["community"]
	if community == "" {
		community = "public"
	}
	if host == "" || oid == "" {
		return nil, "", fmt.Errorf("missing host/oid")
	}
	port := task.Params["port"]
	if port == "" {
		port = "161"
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 3 * time.Second
	}
	sec := int(timeout.Seconds())
	if sec < 1 {
		sec = 1
	}
	cmd := exec.CommandContext(ctx, "snmpget", "-v2c", "-c", community, "-t", fmt.Sprintf("%d", sec), "-r", "0", fmt.Sprintf("%s:%s", host, port), oid)
	out, err := cmd.CombinedOutput()
	s := strings.TrimSpace(string(out))
	if err != nil {
		return map[string]string{"output": s}, "snmpget failed", err
	}
	// output usually: iso.3.6... = INTEGER: 1
	parts := strings.SplitN(s, "=", 2)
	if len(parts) != 2 {
		return map[string]string{"output": s}, "ok", nil
	}
	val := strings.TrimSpace(parts[1])
	return map[string]string{"oid": oid, "value": val}, "ok", nil
}
