package linuxcollector

import (
	"context"
	"fmt"
	"testing"
)

func TestReplayLinuxProcAndNvidiaSample(t *testing.T) {
	origRead := readFile
	origRun := runCommand
	t.Cleanup(func() {
		readFile = origRead
		runCommand = origRun
	})

	readFile = func(path string) ([]byte, error) {
		switch path {
		case "/proc/loadavg":
			return []byte("1.42 1.15 0.88 2/1234 5678\n"), nil
		case "/proc/uptime":
			return []byte("86400.12 12345.67\n"), nil
		case "/proc/meminfo":
			return []byte("MemTotal:       32768000 kB\nMemAvailable:   8192000 kB\n"), nil
		default:
			return nil, fmt.Errorf("unexpected path %s", path)
		}
	}
	runCommand = func(ctx context.Context, name string, args ...string) (string, error) {
		if name == "uname" {
			return "6.8.0-test", nil
		}
		if name == "nvidia-smi" {
			return "NVIDIA RTX A6000, 75, 16384, 49152, 72", nil
		}
		return "", fmt.Errorf("unsupported cmd %s", name)
	}

	load := gatherLoadAndUptime(context.Background(), "linux")
	if load["load1"] != "1.42" || load["load5"] != "1.15" || load["load15"] != "0.88" {
		t.Fatalf("unexpected load: %+v", load)
	}
	if load["uptime_s"] != "86400.12" {
		t.Fatalf("unexpected uptime: %+v", load)
	}

	mem := gatherMemory("linux")
	if mem["memtotal_kb"] != "32768000" || mem["memavailable_kb"] != "8192000" {
		t.Fatalf("unexpected mem fields: %+v", mem)
	}
	if mem["mem_used_pct"] == "" {
		t.Fatalf("expected mem_used_pct, got %+v", mem)
	}

	kernel := gatherKernelRelease(context.Background())
	if kernel["kernel_release"] != "6.8.0-test" {
		t.Fatalf("unexpected kernel release: %+v", kernel)
	}

	gpu := gatherNvidia(context.Background())
	if gpu["gpu_name"] != "NVIDIA RTX A6000" {
		t.Fatalf("unexpected gpu name: %+v", gpu)
	}
	if gpu["gpu_utilization_pct"] != "75" || gpu["gpu_memory_used_mb"] != "16384" || gpu["gpu_temperature_c"] != "72" {
		t.Fatalf("unexpected gpu fields: %+v", gpu)
	}
}
