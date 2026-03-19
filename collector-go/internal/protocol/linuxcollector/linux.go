package linuxcollector

import (
	"context"
	"os/exec"
	"runtime"
	"strings"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

var runCommand = func(ctx context.Context, name string, args ...string) (string, error) {
	out, err := exec.CommandContext(ctx, name, args...).CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

func init() {
	protocol.Register("linux", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	fields := gatherBasicFields(runtime.GOOS)
	merge(fields, gatherLoadAndUptime(ctx, runtime.GOOS))
	merge(fields, gatherMemory(runtime.GOOS))
	merge(fields, gatherKernelRelease(ctx))
	merge(fields, gatherNvidia(ctx))
	return fields, "ok", nil
}
