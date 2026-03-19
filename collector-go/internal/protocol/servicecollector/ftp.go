package servicecollector

import (
	"bufio"
	"context"
	"fmt"
	"strings"
	"time"

	"collector-go/internal/model"
)

type FTPCollector struct{}

func (c *FTPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "ftp.host")
	port := parsePort(params, "21", "port", "ftp.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "ftp.timeout")
	ssl := boolFrom(params, false, "ssl", "ftp.ssl")
	username := firstNonEmpty(params, "username", "ftp.username")
	password := firstNonEmpty(params, "password", "ftp.password")
	direction := firstNonEmpty(params, "direction", "ftp.direction")

	conn, latency, err := dialMailConn(ctx, host, port, timeout, ssl)
	if err != nil {
		return nil, "ftp dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	r := bufio.NewReader(conn)
	w := bufio.NewWriter(conn)

	line, err := readLine(r)
	if err != nil || !strings.HasPrefix(line, "220") {
		if err == nil {
			err = fmt.Errorf("unexpected banner: %s", line)
		}
		return nil, "ftp banner failed", err
	}
	if username != "" {
		if err := writeLine(w, "USER "+username); err != nil {
			return nil, "ftp user failed", err
		}
		line, err = readLine(r)
		if err != nil {
			return nil, "ftp user response failed", err
		}
		if strings.HasPrefix(line, "331") {
			if err := writeLine(w, "PASS "+password); err != nil {
				return nil, "ftp pass failed", err
			}
			line, err = readLine(r)
			if err != nil {
				return nil, "ftp pass response failed", err
			}
		}
		if !strings.HasPrefix(line, "230") {
			return nil, "ftp auth rejected", fmt.Errorf("auth rejected: %s", line)
		}
	}
	if direction != "" {
		_ = writeLine(w, "CWD "+direction)
		_, _ = readLine(r)
	}
	_ = writeLine(w, "NOOP")
	_, _ = readLine(r)
	_ = writeLine(w, "QUIT")
	_, _ = readLine(r)

	return map[string]string{
		"isActive":     "true",
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
	}, "ok", nil
}
