package linuxcollector

import (
	"fmt"
	"os"
	"runtime"
	"strconv"
)

func gatherBasicFields(goos string) map[string]string {
	out := map[string]string{
		"goos":      goos,
		"cpu":       fmt.Sprintf("%d", runtime.NumCPU()),
		"cpu_cores": fmt.Sprintf("%d", runtime.NumCPU()),
	}
	if host, err := os.Hostname(); err == nil && host != "" {
		out["hostname"] = host
	}
	return out
}

func parseMemInfo(s string) map[string]string {
	out := map[string]string{}
	lines := splitLines(s)
	for _, line := range lines {
		key, value, ok := splitKV(line)
		if !ok {
			continue
		}
		switch key {
		case "memtotal":
			out["memtotal_kb"] = value
		case "memavailable":
			out["memavailable_kb"] = value
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
