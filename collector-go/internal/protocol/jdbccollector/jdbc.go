package jdbccollector

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
	protocol.Register("jdbc", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	// Offline-friendly JDBC adapter: execute configured SQL client command.
	// params: command, query(optional)
	command := task.Params["command"]
	if command == "" {
		return nil, "", fmt.Errorf("missing command, e.g. 'mysql -h 127.0.0.1 -uroot -p*** -N -e \"select 1\"'")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx2, "sh", "-c", command)
	out, err := cmd.CombinedOutput()
	s := strings.TrimSpace(string(out))
	if err != nil {
		return map[string]string{"output": s}, "jdbc command failed", err
	}
	lines := strings.Split(s, "\n")
	first := ""
	if len(lines) > 0 {
		first = strings.TrimSpace(lines[0])
	}
	return map[string]string{"rows": fmt.Sprintf("%d", len(lines)), "first_row": first}, "ok", nil
}
