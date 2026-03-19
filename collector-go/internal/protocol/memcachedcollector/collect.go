package memcachedcollector

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
	protocol.Register("memcached", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	if host == "" {
		return nil, "", fmt.Errorf("missing host")
	}
	if port == "" {
		port = "11211"
	}
	timeout := resolveTimeout(task)
	address := net.JoinHostPort(host, port)
	start := time.Now()

	dialer := net.Dialer{Timeout: timeout}
	conn, err := dialer.DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, "", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	reader := bufio.NewReader(conn)
	fields := make(map[string]string, 128)

	if err := collectStats(conn, reader, "stats", func(line string) {
		parseKVLine(fields, line)
	}); err != nil {
		return nil, "", fmt.Errorf("stats command failed: %w", err)
	}
	if err := collectStats(conn, reader, "stats settings", func(line string) {
		parseKVLine(fields, line)
	}); err != nil {
		return nil, "", fmt.Errorf("stats settings command failed: %w", err)
	}
	if err := collectStats(conn, reader, "stats sizes", func(line string) {
		parseSizesLine(fields, line)
	}); err != nil {
		return nil, "", fmt.Errorf("stats sizes command failed: %w", err)
	}

	fields["responseTime"] = strconv.FormatInt(time.Since(start).Milliseconds(), 10)
	return fields, "ok", nil
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
	return 3 * time.Second
}

func collectStats(conn net.Conn, reader *bufio.Reader, cmd string, onLine func(string)) error {
	if _, err := fmt.Fprintf(conn, "%s\r\n", cmd); err != nil {
		return err
	}
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return err
		}
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if line == "END" {
			return nil
		}
		if line == "ERROR" || strings.HasPrefix(line, "CLIENT_ERROR") || strings.HasPrefix(line, "SERVER_ERROR") {
			return fmt.Errorf("server returned %q", line)
		}
		onLine(line)
	}
}
