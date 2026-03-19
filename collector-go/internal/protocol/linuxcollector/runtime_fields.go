package linuxcollector

import (
	"context"
	"os"
	"runtime"
	"strconv"
	"strings"
)

var readFile = os.ReadFile

func gatherLoadAndUptime(ctx context.Context, goos string) map[string]string {
	out := map[string]string{}
	if goos == "linux" {
		if b, err := readFile("/proc/loadavg"); err == nil {
			parts := strings.Fields(string(b))
			if len(parts) >= 3 {
				out["load1"] = strings.TrimSpace(parts[0])
				out["load5"] = strings.TrimSpace(parts[1])
				out["load15"] = strings.TrimSpace(parts[2])
			}
		}
		if b, err := readFile("/proc/uptime"); err == nil {
			parts := strings.Fields(string(b))
			if len(parts) > 0 {
				out["uptime_s"] = strings.TrimSpace(parts[0])
			}
		}
		return out
	}
	if raw, err := runCommand(ctx, "uptime"); err == nil {
		l1, l5, l15 := parseUptimeLoads(raw)
		if l1 != "" {
			out["load1"] = l1
		}
		if l5 != "" {
			out["load5"] = l5
		}
		if l15 != "" {
			out["load15"] = l15
		}
	}
	return out
}

func gatherMemory(goos string) map[string]string {
	if goos != "linux" {
		var m runtime.MemStats
		runtime.ReadMemStats(&m)
		return map[string]string{
			"mem_alloc_bytes": strconv.FormatUint(m.Alloc, 10),
		}
	}
	if b, err := readFile("/proc/meminfo"); err == nil {
		return parseMemInfo(string(b))
	}
	return map[string]string{}
}

func gatherKernelRelease(ctx context.Context) map[string]string {
	out := map[string]string{}
	raw, err := runCommand(ctx, "uname", "-r")
	if err != nil {
		return out
	}
	if raw = strings.TrimSpace(raw); raw != "" {
		out["kernel_release"] = raw
	}
	return out
}
