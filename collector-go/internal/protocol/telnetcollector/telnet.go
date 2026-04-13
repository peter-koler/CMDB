package telnetcollector

import (
	"bufio"
	"context"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("telnet", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	cmd := strings.TrimSpace(firstNonEmpty(task.Params["cmd"], task.Params["telnet.cmd"]))
	if host == "" || port == "" {
		return nil, "", fmt.Errorf("missing telnet host or port")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	address := net.JoinHostPort(host, port)
	dialer := &net.Dialer{Timeout: timeout}
	start := time.Now()
	conn, err := dialer.DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, "", err
	}
	defer conn.Close()
	latencyMs := time.Since(start).Milliseconds()
	if cmd == "" {
		return map[string]string{
			"responseTime": strconv.FormatInt(latencyMs, 10),
			"reachable":    "1",
		}, "ok", nil
	}
	_ = conn.SetDeadline(time.Now().Add(timeout))
	if _, err := conn.Write([]byte(cmd)); err != nil {
		return nil, "", err
	}
	if !strings.HasSuffix(cmd, "\n") {
		if _, err := conn.Write([]byte("\n")); err != nil {
			return nil, "", err
		}
	}
	reader := bufio.NewReader(conn)
	data, err := reader.ReadString(0)
	if err != nil && !strings.Contains(strings.ToLower(err.Error()), "timeout") {
		// Zookeeper four-letter commands generally end by connection close / timeout.
		if !strings.Contains(strings.ToLower(err.Error()), "closed") && !strings.Contains(strings.ToLower(err.Error()), "eof") {
			return nil, "", err
		}
	}
	fields := parseTelnetResult(task, data)
	if _, ok := fields["responseTime"]; !ok {
		fields["responseTime"] = strconv.FormatInt(latencyMs, 10)
	}
	if _, ok := fields["reachable"]; !ok {
		fields["reachable"] = "1"
	}
	return fields, "ok", nil
}

func parseTelnetResult(task model.MetricsTask, raw string) map[string]string {
	lines := strings.Split(strings.ReplaceAll(raw, "\r\n", "\n"), "\n")
	out := map[string]string{}
	if len(lines) > 0 && strings.TrimSpace(lines[0]) == "Environment:" {
		lines = lines[1:]
	}
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if strings.Contains(line, "=") {
			parts := strings.SplitN(line, "=", 2)
			out[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
			continue
		}
		if strings.Contains(line, "\t") {
			parts := strings.SplitN(line, "\t", 2)
			out[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
		}
	}
	return out
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}
