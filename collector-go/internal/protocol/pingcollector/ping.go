package pingcollector

import (
	"context"
	"fmt"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("icmp", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := task.Params["host"]
	if host == "" {
		return nil, "", fmt.Errorf("missing host")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 3 * time.Second
	}

	args := pingArgs(host, timeout)
	cmd := exec.CommandContext(ctx, "ping", args...)
	out, err := cmd.CombinedOutput()
	s := string(out)
	if err != nil {
		return map[string]string{"output": s}, "ping failed", err
	}
	latency := parsePingLatencyMs(s)
	return map[string]string{
		"reachable":  "1",
		"latency_ms": fmt.Sprintf("%.2f", latency),
	}, "ok", nil
}

func pingArgs(host string, timeout time.Duration) []string {
	ms := int(timeout.Milliseconds())
	if ms < 1000 {
		ms = 1000
	}
	if runtime.GOOS == "windows" {
		return []string{"-n", "1", "-w", strconv.Itoa(ms), host}
	}
	// macOS uses milliseconds for -W, Linux commonly seconds.
	if runtime.GOOS == "darwin" {
		return []string{"-c", "1", "-W", strconv.Itoa(ms), host}
	}
	sec := int(timeout.Seconds())
	if sec < 1 {
		sec = 1
	}
	return []string{"-c", "1", "-W", strconv.Itoa(sec), host}
}

func parsePingLatencyMs(output string) float64 {
	// best effort parsing from common output forms: "time=12.3 ms"
	idx := strings.Index(output, "time=")
	if idx < 0 {
		return 0
	}
	s := output[idx+5:]
	end := strings.Index(s, " ms")
	if end < 0 {
		return 0
	}
	val := strings.TrimSpace(s[:end])
	f, err := strconv.ParseFloat(val, 64)
	if err != nil {
		return 0
	}
	return f
}
