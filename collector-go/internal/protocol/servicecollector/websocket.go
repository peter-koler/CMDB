package servicecollector

import (
	"bufio"
	"context"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"net/http"
	"strings"
	"time"

	"collector-go/internal/model"
)

type WebsocketCollector struct{}

func (c *WebsocketCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "websocket.host")
	port := parsePort(params, "80", "port", "websocket.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "websocket.timeout")
	path := firstNonEmpty(params, "path", "websocket.path")
	if path == "" {
		path = "/"
	}
	conn, latency, err := dialTCP(ctx, host, port, timeout)
	if err != nil {
		return nil, "websocket dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	secKey, _ := randomSecKey()
	req := []string{
		"GET " + path + " HTTP/1.1",
		"Host: " + host,
		"Upgrade: websocket",
		"Connection: Upgrade",
		"Sec-WebSocket-Key: " + secKey,
		"Sec-WebSocket-Version: 13",
		"\r\n",
	}
	if _, err := conn.Write([]byte(strings.Join(req, "\r\n"))); err != nil {
		return nil, "websocket write failed", err
	}

	r := bufio.NewReader(conn)
	statusLine, err := r.ReadString('\n')
	if err != nil {
		return nil, "websocket read status failed", err
	}
	statusLine = strings.TrimSpace(statusLine)
	httpVersion, responseCode, statusMessage := parseStatusLine(statusLine)

	headers := map[string]string{}
	for {
		line, err := r.ReadString('\n')
		if err != nil {
			break
		}
		line = strings.TrimSpace(line)
		if line == "" {
			break
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 {
			headers[strings.ToLower(strings.TrimSpace(parts[0]))] = strings.TrimSpace(parts[1])
		}
	}
	if responseCode != "101" {
		return map[string]string{
			"responseTime":  fmt.Sprintf("%d", latency.Milliseconds()),
			"httpVersion":   httpVersion,
			"responseCode":  responseCode,
			"statusMessage": statusMessage,
			"connection":    headers["connection"],
			"upgrade":       headers["upgrade"],
		}, "websocket handshake failed", fmt.Errorf("status %s", responseCode)
	}
	return map[string]string{
		"responseTime":  fmt.Sprintf("%d", latency.Milliseconds()),
		"httpVersion":   httpVersion,
		"responseCode":  responseCode,
		"statusMessage": statusMessage,
		"connection":    headers["connection"],
		"upgrade":       headers["upgrade"],
	}, "ok", nil
}

func randomSecKey() (string, error) {
	raw := make([]byte, 16)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(raw), nil
}

func parseStatusLine(line string) (string, string, string) {
	parts := strings.SplitN(line, " ", 3)
	if len(parts) < 2 {
		return "HTTP/1.1", "0", line
	}
	status := ""
	if len(parts) >= 3 {
		status = parts[2]
	} else {
		status = http.StatusText(101)
	}
	return parts[0], parts[1], status
}
