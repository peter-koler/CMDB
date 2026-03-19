package linuxcollector

import (
	"context"
	"strings"
)

func gatherNvidia(ctx context.Context) map[string]string {
	out := map[string]string{}
	raw, err := runCommand(
		ctx,
		"nvidia-smi",
		"--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
		"--format=csv,noheader,nounits",
	)
	if err != nil {
		return out
	}
	lines := splitLines(raw)
	if len(lines) == 0 {
		return out
	}
	parts := strings.Split(lines[0], ",")
	if len(parts) < 5 {
		return out
	}
	out["gpu_name"] = strings.TrimSpace(parts[0])
	out["gpu_utilization_pct"] = strings.TrimSpace(parts[1])
	out["gpu_memory_used_mb"] = strings.TrimSpace(parts[2])
	out["gpu_memory_total_mb"] = strings.TrimSpace(parts[3])
	out["gpu_temperature_c"] = strings.TrimSpace(parts[4])
	return out
}
