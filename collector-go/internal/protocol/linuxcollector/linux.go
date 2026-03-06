package linuxcollector

import (
	"context"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("linux", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	_ = ctx
	fields := map[string]string{
		"goos": runtime.GOOS,
		"cpu":  fmt.Sprintf("%d", runtime.NumCPU()),
	}
	if runtime.GOOS == "linux" {
		if b, err := os.ReadFile("/proc/loadavg"); err == nil {
			parts := strings.Fields(string(b))
			if len(parts) >= 3 {
				fields["load1"] = parts[0]
				fields["load5"] = parts[1]
				fields["load15"] = parts[2]
			}
		}
		if b, err := os.ReadFile("/proc/uptime"); err == nil {
			parts := strings.Fields(string(b))
			if len(parts) > 0 {
				fields["uptime_s"] = parts[0]
			}
		}
		if b, err := os.ReadFile("/proc/meminfo"); err == nil {
			mem := parseMemInfo(string(b))
			for k, v := range mem {
				fields[k] = v
			}
		}
	} else {
		var m runtime.MemStats
		runtime.ReadMemStats(&m)
		fields["mem_alloc_bytes"] = fmt.Sprintf("%d", m.Alloc)
		fields["unix_ms"] = fmt.Sprintf("%d", time.Now().UnixMilli())
	}
	return fields, "ok", nil
}

func parseMemInfo(s string) map[string]string {
	out := map[string]string{}
	for _, line := range strings.Split(s, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "MemTotal:") || strings.HasPrefix(line, "MemAvailable:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				k := strings.TrimSuffix(strings.ToLower(fields[0]), ":")
				out[k+"_kb"] = fields[1]
			}
		}
	}
	if total, ok1 := out["memtotal_kb"]; ok1 {
		if avail, ok2 := out["memavailable_kb"]; ok2 {
			t, err1 := strconv.ParseFloat(total, 64)
			a, err2 := strconv.ParseFloat(avail, 64)
			if err1 == nil && err2 == nil && t > 0 {
				usedPct := (t - a) / t * 100
				out["mem_used_pct"] = fmt.Sprintf("%.2f", usedPct)
			}
		}
	}
	return out
}
