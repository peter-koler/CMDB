package ipmicollector

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("ipmi", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host, port, user, pass, typ, timeout, err := parseTaskParams(task)
	if err != nil {
		return nil, "", err
	}

	start := time.Now()

	fields, err := collectByNative(ctx, host, port, user, pass, typ, timeout)
	if err != nil {
		nativeErr := err
		if !allowToolFallback() {
			return nil, "", nativeErr
		}
		fields, err = collectByTool(ctx, host, port, user, pass, typ, timeout)
		if err != nil {
			return nil, "", errors.Join(nativeErr, err)
		}
	}

	fields["responseTime"] = strconv.FormatInt(time.Since(start).Milliseconds(), 10)
	return fields, "ok", nil
}

func parseTaskParams(task model.MetricsTask) (host, port, user, pass, typ string, timeout time.Duration, err error) {
	host = strings.TrimSpace(task.Params["host"])
	port = strings.TrimSpace(task.Params["port"])
	user = strings.TrimSpace(task.Params["username"])
	pass = strings.TrimSpace(task.Params["password"])
	typ = strings.TrimSpace(strings.ToLower(task.Params["type"]))
	if typ == "" {
		typ = strings.ToLower(strings.TrimSpace(task.Name))
	}
	timeout = resolveTimeout(task)

	if host == "" {
		return "", "", "", "", "", 0, fmt.Errorf("missing host")
	}
	if port == "" {
		port = "623"
	}
	if user == "" || pass == "" {
		return "", "", "", "", "", 0, fmt.Errorf("missing username or password")
	}
	if typ == "" {
		typ = "chassis"
	}
	return host, port, user, pass, typ, timeout, nil
}

func resolveTimeout(task model.MetricsTask) time.Duration {
	if task.Timeout > 0 {
		return task.Timeout
	}
	if raw := strings.TrimSpace(task.Params["timeout"]); raw != "" {
		if ms, err := strconv.Atoi(raw); err == nil && ms > 0 {
			return time.Duration(ms) * time.Millisecond
		}
	}
	return 6 * time.Second
}

func allowToolFallback() bool {
	v := strings.TrimSpace(os.Getenv("COLLECTOR_IPMI_FALLBACK_TOOL"))
	switch strings.ToLower(v) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}
